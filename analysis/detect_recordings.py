"""Bounded-memory full-recording extracellular candidate detection.

Default: MA50, adaptive per-second MAD, across-channel median floor, negative
peaks, global 5 ms spacing. Fixed-reference calibration is an explicit option.
Two sequential passes; raw HDF5 opened read-only; completed outputs atomic.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import h5py
import numpy as np
from scipy.signal import find_peaks
from analysis.pilot import moving_average,flat_mask,dilate,spaced_peaks

FS=10000
CONTEXT=510
DEFAULT_DATA=Path('/Volumes/YZ/recording/invivo/26-11-06/0192')
DEFAULT_OUT=Path('results/spike_detection_ma50_adaptive')
EVENT_DTYPES={'channel_id':'u2','sample_index':'u8','time_s':'f8','negative_amplitude':'f8',
              'threshold':'f8','shared_warning_available':'?', 'shared10_warning':'?', 'shared20_warning':'?'}


def runs(mask):
    edge=np.diff(np.r_[False,mask,False].astype(np.int8))
    return np.column_stack((np.flatnonzero(edge==1),np.flatnonzero(edge==-1)))


def preprocess(raw,lo,a,b,n,ma):
    """Context includes flat-run evidence beyond the 50 ms guard.

    Filter edges at the physical record boundaries are unobservable and excluded.
    """
    core=slice(a-lo,b-lo)
    residual=raw-moving_average(raw,ma)
    flat=dilate(flat_mask(raw),500)[core]
    invalid=flat.copy();positions=np.arange(a,b)
    invalid |= (positions<ma//2)|(positions>=n-(ma//2-1))
    return residual,core,flat,invalid


def window_scale(y,invalid):
    good=y[~invalid]
    if len(good)<max(250,(len(y)+1)//2):return np.nan,len(good)
    sigma=np.median(np.abs(good-np.median(good)))/.67448975
    return (float(sigma) if np.isfinite(sigma) and sigma>0 else np.nan),len(good)


def merge_intervals(intervals):
    if not len(intervals):return np.empty((0,2),dtype=np.uint64)
    out=[]
    for a,b in sorted(intervals):
        if out and a<=out[-1][1]:out[-1][1]=max(out[-1][1],b)
        else:out.append([int(a),int(b)])
    return np.asarray(out,dtype=np.uint64)


def known_shared(rec,n,source):
    available=np.zeros(n,bool);m10=available.copy();m20=available.copy();provenance=[]
    roots=[(Path('results/shared_artifact_review_extended'),Path('results/controlled_comparison')), (Path('results/frozen_guard_validation/flags'),Path('results/frozen_guard_validation/detector')), (Path('results/focused_ma50_review/flags'),Path('results/focused_ma50_review/detector'))]
    for root,detector_root in roots:
        for p in sorted(root.glob(f'extra{rec}_*/flags_and_evidence.npz')):
            s=json.loads((p.parent/'summary.json').read_text())
            if Path(s['source']).resolve()!=source.resolve():continue
            original=json.loads((detector_root/p.parent.name/'summary.json').read_text());st=source.stat()
            if st.st_size!=original['file_size_bytes'] or st.st_mtime_ns!=original['file_mtime_ns']:raise ValueError('Shared warnings refer to changed source metadata')
            a,b=s['sample_start'],s['sample_stop'];assert 0<=a<b<=n
            with np.load(p) as data:
                x=data['mask_b3_h6_f50_g10'];y=data['mask_b3_h6_f50_g20']
            assert len(x)==b-a and len(y)==b-a and not (x&~y).any()
            overlap=available[a:b]
            if overlap.any():
                np.testing.assert_array_equal(m10[a:b][overlap],x[overlap]);np.testing.assert_array_equal(m20[a:b][overlap],y[overlap])
            available[a:b]=True;m10[a:b]=x;m20[a:b]=y
            provenance.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sample_start':a,'sample_stop':b})
    return available,m10,m20,provenance


def detect(source,out,*,mode='adaptive',ma=50,calibration=None,batch_channels=64,chunk_seconds=5,rec=None,annotate_shared=True):
    """Run a full source; output directory must not already exist."""
    begin=time.perf_counter();source=Path(source);out=Path(out)
    if chunk_seconds<1 or int(chunk_seconds)!=chunk_seconds:raise ValueError('Chunk seconds must be a positive integer')
    if batch_channels<1:raise ValueError('Positive channel batch size required')
    if ma not in [50,100,200]:raise ValueError('Supported MA sizes: 50, 100, 200')
    if mode not in ['adaptive','fixed']:raise ValueError('mode must be adaptive or fixed')
    with h5py.File(source,'r') as f:
        ds=f['signals'];channels,n=ds.shape;dtype=str(ds.dtype)
        if ds.ndim!=2 or ds.dtype.kind!='f':raise ValueError('Expected converted floating signals (channels, samples)')
        if channels>65536:raise ValueError('channel_id storage capacity exceeded')
    stat=source.stat();nw=(n+FS-1)//FS;step=int(chunk_seconds)*FS
    fixed=None;reference_eligible=np.ones(channels,bool);cal_meta=None
    if mode=='fixed':
        if calibration is None:raise ValueError('Fixed mode requires an explicit calibration file')
        with np.load(calibration) as cal:
            reference_eligible=cal['eligible'].astype(bool);fixed=cal['thresholds'][[50,100,200].index(ma)].copy()
        if len(fixed)!=channels or len(reference_eligible)!=channels:raise ValueError('Calibration channel count mismatch')
        if not np.all(np.isfinite(fixed[reference_eligible])&(fixed[reference_eligible]>0)):raise ValueError('Invalid eligible calibration thresholds')
        if not np.all(np.isnan(fixed[~reference_eligible])):raise ValueError('Unavailable references must have NaN thresholds')
        cal_meta={'path':str(Path(calibration).resolve()),'sha256':hashlib.sha256(Path(calibration).read_bytes()).hexdigest()}
        if rec is not None:
            cp=Path(calibration).parent.parent/'protocol.json'
            provenance=json.loads(cp.read_text());original=provenance['source_metadata'][str(rec)]
            if Path(original['path']).resolve()!=source.resolve() or original['size']!=stat.st_size or original['mtime_ns']!=stat.st_mtime_ns:raise ValueError('Calibration belongs to a different or modified source')
            if provenance['threshold_multiplier']!=5:raise ValueError('Calibration multiplier must be 5')
            cal_meta['protocol_sha256']=hashlib.sha256(cp.read_bytes()).hexdigest()
    if annotate_shared and rec is not None:
        shared_available,shared10,shared20,shared_sources=known_shared(rec,n,source)
    else:
        shared_available=np.zeros(n,bool);shared10=shared_available.copy();shared20=shared_available.copy();shared_sources=[]
    out.mkdir(parents=True,exist_ok=False)
    config={'schema':'extracellular-candidates-v1','source':str(source.resolve()),'source_size_bytes':stat.st_size,'source_mtime_ns':stat.st_mtime_ns,
        'shape':[channels,n],'source_dtype':dtype,'nominal_fs_hz':FS,'physical_fs_hz':10080,'mode':mode,'ma_samples':ma,
        'threshold_multiplier':5,'noise_window_samples':FS,'flat_min_samples':10,'flat_guard_samples_each_side':500,
        'peak_spacing_samples':50,'polarity':'negative','physical_edge_exclusion_samples':[ma//2,ma//2-1],
        'chunk_seconds':chunk_seconds,'batch_channels':batch_channels,'fixed_calibration':cal_meta,
        'adaptive_support':'MA residual only; does not require quiet-reference eligibility or other filter estimates',
        'shared_warning_sources':shared_sources,'shared_warning_policy':'annotations only; outside available intervals is unknown, not clean',
        'waveforms_saved':False,'amplitude_units':'stored converted signal units; conversion trusted',
        'source_code_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path('analysis/pilot.py')]}}
    (out/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    sigma=np.full((channels,nw),np.nan);good_counts=np.zeros((channels,nw),np.uint32);flat_intervals=[[] for _ in range(channels)]
    with h5py.File(source,'r') as f:
        ds=f['signals']
        for c0 in range(0,channels,batch_channels):
            c1=min(channels,c0+batch_channels)
            for a in range(0,n,step):
                b=min(n,a+step);lo=max(0,a-CONTEXT);hi=min(n,b+CONTEXT)
                block=ds[c0:c1,lo:hi].astype(np.float64)
                if not np.isfinite(block).all():raise ValueError(f'Nonfinite raw values at channels {c0}:{c1}, samples {lo}:{hi}')
                for j,raw in enumerate(block):
                    ch=c0+j;y,core,flat,invalid=preprocess(raw,lo,a,b,n,ma);y=y[core]
                    flat_intervals[ch].extend((int(x+a),int(z+a)) for x,z in runs(flat))
                    for local in range(0,b-a,FS):
                        w=(a+local)//FS;v,count=window_scale(y[local:local+FS],invalid[local:local+FS])
                        sigma[ch,w]=v;good_counts[ch,w]=count
            print(f'{source.stem} noise channels {c0}:{c1}/{channels}',flush=True)
            (out/'progress.json').write_text(json.dumps({'stage':'noise','channels_complete':c1,'channels_total':channels})+'\n')
    valid=np.isfinite(sigma)&(sigma>0)&reference_eligible[:,None]
    floor=np.array([np.median(sigma[:,w][valid[:,w]]) if valid[:,w].any() else np.nan for w in range(nw)])
    thresholds=5*np.maximum(sigma,floor[None,:]) if mode=='adaptive' else np.broadcast_to(fixed[:,None],sigma.shape).copy()
    thresholds[~valid]=np.nan
    usable=good_counts*valid
    partial=out/'spikes.partial.h5';final=out/'spikes.h5'
    with h5py.File(partial,'w') as dest:
        dest.attrs['schema']='extracellular-candidates-v1';dest.attrs['complete']=False
        dest.attrs['config_json']=json.dumps(config);dest.attrs['nominal_fs_hz']=FS;dest.attrs['physical_fs_hz']=10080
        dest.attrs['channel_indexing']='zero-based';dest.attrs['event_order']='channel_id then sample_index'
        dest.attrs['interpretation']='Detected candidates, not sorted units or validated eAP identities'
        dest.attrs['source_sample_count']=n;dest.attrs['source_channel_count']=channels
        dest.create_dataset('noise/mad',data=sigma,compression='gzip')
        floor_ds=dest.create_dataset('noise/median_floor',data=floor)
        floor_ds.attrs['used_for_detection']=mode=='adaptive'
        floor_ds.attrs['description']='Per-window adaptive floor; fixed mode uses frozen calibration thresholds instead'
        if fixed is not None:dest.create_dataset('noise/fixed_threshold_per_channel',data=fixed)
        dest.create_dataset('noise/threshold',data=thresholds,compression='gzip')
        dest.create_dataset('quality/valid_noise_window',data=valid,compression='gzip')
        dest.create_dataset('quality/usable_samples_per_channel_window',data=usable,compression='gzip')
        dest.create_dataset('quality/reference_eligible',data=reference_eligible)
        guard_rows=np.asarray([(ch,int(a),int(b)) for ch in range(channels) for a,b in merge_intervals(flat_intervals[ch])],dtype=np.uint64).reshape(-1,3)
        g=dest.create_dataset('quality/flat_guard_intervals',data=guard_rows,compression='gzip');g.attrs['columns']='channel_id,start_sample,stop_sample_exclusive'
        for name,mask in [('shared_available',shared_available),('shared10',shared10),('shared20',shared20)]:
            x=dest.create_dataset('quality/'+name+'_intervals',data=runs(mask).astype(np.uint64));x.attrs['columns']='start_sample,stop_sample_exclusive'
        event_ds={k:dest.create_dataset('spikes/'+k,shape=(0,),maxshape=(None,),chunks=True,compression='gzip',dtype=dt) for k,dt in EVENT_DTYPES.items()}
        offsets=np.zeros(channels+1,np.uint64);total=0;seed_total=0
        with h5py.File(source,'r') as f:
            ds=f['signals']
            for c0 in range(0,channels,batch_channels):
                c1=min(channels,c0+batch_channels);seeds=[[] for _ in range(c1-c0)]
                for a in range(0,n,step):
                    b=min(n,a+step);lo=max(0,a-CONTEXT);hi=min(n,b+CONTEXT)
                    block=ds[c0:c1,lo:hi].astype(np.float64)
                    if not np.isfinite(block).all():raise ValueError('Nonfinite data during candidate pass')
                    for j,raw in enumerate(block):
                        ch=c0+j
                        if not valid[ch,(a//FS):((b+FS-1)//FS)].any():continue
                        y,core,_,invalid=preprocess(raw,lo,a,b,n,ma)
                        p=find_peaks(-y)[0]+lo;p=p[(p>=a)&(p<b)]
                        p=p[~invalid[p-a]&valid[ch,p//FS]]
                        amp=-y[p-lo];th=thresholds[ch,p//FS];keep=amp>=th
                        if keep.any():seeds[j].append((p[keep],amp[keep]))
                for j,ch in enumerate(range(c0,c1)):
                    offsets[ch]=total
                    if not seeds[j]:continue
                    p=np.concatenate([x[0] for x in seeds[j]]);amp=np.concatenate([x[1] for x in seeds[j]]);seed_total+=len(p)
                    selected=spaced_peaks(p,amp,50);p=p[selected];amp=amp[selected]
                    assert len(p)<2 or np.diff(p).min()>=50
                    size=len(p);values={'channel_id':np.full(size,ch,dtype=np.uint16),'sample_index':p,'time_s':p/FS,
                        'negative_amplitude':amp,'threshold':thresholds[ch,p//FS],
                        'shared_warning_available':shared_available[p],'shared10_warning':shared10[p],'shared20_warning':shared20[p]}
                    for key,dataset in event_ds.items():dataset.resize((total+size,));dataset[total:total+size]=values[key]
                    total+=size
                print(f'{source.stem} candidates channels {c0}:{c1}/{channels}; saved {total}',flush=True)
                dest.flush();(out/'progress.json').write_text(json.dumps({'stage':'candidates','channels_complete':c1,'channels_total':channels,'candidates':total})+'\n')
        offsets[-1]=total;dest.create_dataset('spikes/channel_offsets',data=offsets)
        dest.create_dataset('spikes/counts_per_channel',data=np.diff(offsets))
        st=source.stat()
        if st.st_size!=stat.st_size or st.st_mtime_ns!=stat.st_mtime_ns:raise RuntimeError('Source metadata changed during run')
        summary={'source':str(source.resolve()),'mode':mode,'ma_samples':ma,'channels':channels,'samples_per_channel':n,
            'nominal_duration_s':n/FS,'candidates':total,'channels_with_candidates':int((np.diff(offsets)>0).sum()),
            'threshold_crossings_before_global_spacing':seed_total,'usable_channel_seconds':float(usable.sum()/FS),
            'total_channel_seconds':channels*n/FS,'valid_channel_windows':int(valid.sum()),'invalid_channel_windows':int((~valid).sum()),
            'shared_warning_evaluated_seconds':float(shared_available.sum()/FS),
            'candidates_with_shared_assessment':int(event_ds['shared_warning_available'][:].sum()),
            'candidates_flagged_shared10':int(event_ds['shared10_warning'][:].sum()),
            'candidates_flagged_shared20':int(event_ds['shared20_warning'][:].sum()),
            'elapsed_seconds':time.perf_counter()-begin,'output':str(final.resolve()),'waveforms_saved':False}
        dest.attrs['summary_json']=json.dumps(summary);dest.attrs['complete']=True
    validate(partial)
    os.replace(partial,final)
    summary['output_sha256']=hashlib.sha256(final.read_bytes()).hexdigest()
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'progress.json').write_text(json.dumps({'stage':'complete','candidates':total})+'\n')
    return summary


def validate(path):
    with h5py.File(path,'r') as f:
        assert f.attrs['complete'];n=int(f.attrs['source_sample_count']);channels=int(f.attrs['source_channel_count'])
        s=f['spikes'];offset=s['channel_offsets'][:];assert len(offset)==channels+1 and offset[0]==0 and offset[-1]==len(s['sample_index'])
        assert np.all(offset[1:]>=offset[:-1]);np.testing.assert_array_equal(np.diff(offset),s['counts_per_channel'][:])
        threshold=f['noise/threshold'][:];valid=f['quality/valid_noise_window'][:]
        available=np.zeros(n,bool);m10=available.copy();m20=available.copy()
        for name,mask in [('shared_available',available),('shared10',m10),('shared20',m20)]:
            for a,b in f['quality/'+name+'_intervals'][:]:mask[int(a):int(b)]=True
        assert not (m10&~m20).any() and not (m20&~available).any()
        guards=f['quality/flat_guard_intervals'][:]
        for ch in range(channels):
            lo,hi=map(int,offset[ch:ch+2]);p=s['sample_index'][lo:hi].astype(np.int64)
            assert np.all(s['channel_id'][lo:hi]==ch);assert ((p>=0)&(p<n)).all()
            assert len(p)<2 or (np.diff(p)>=50).all()
            assert valid[ch,p//FS].all()
            amp=s['negative_amplitude'][lo:hi];th=s['threshold'][lo:hi]
            assert np.isfinite(amp).all() and np.isfinite(th).all() and (amp>=th).all()
            np.testing.assert_array_equal(th,threshold[ch,p//FS]);np.testing.assert_array_equal(s['time_s'][lo:hi],p/FS)
            for a,b in guards[guards[:,0]==ch,1:]:assert not ((p>=a)&(p<b)).any()
            for key,mask in [('shared_warning_available',available),('shared10_warning',m10),('shared20_warning',m20)]:np.testing.assert_array_equal(s[key][lo:hi],mask[p])
    return True


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    inputs=ap.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--input',type=Path,help='Converted HDF5 file, with any filename; output is the recording directory')
    inputs.add_argument('--recordings',type=int,nargs='+',choices=[4,5],help='Legacy project batch shortcut')
    ap.add_argument('--directory',type=Path,default=DEFAULT_DATA);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--mode',choices=['adaptive','fixed'],default='adaptive');ap.add_argument('--ma',type=int,choices=[50,100,200],default=50)
    ap.add_argument('--calibration-directory',type=Path,default=Path('results/fixed_reference_thresholds/references'))
    ap.add_argument('--calibration',type=Path,help='Explicit calibration NPZ for --input in fixed mode')
    ap.add_argument('--chunk-seconds',type=int,default=5);ap.add_argument('--batch-channels',type=int,default=64)
    args=ap.parse_args(argv)
    if args.input is not None:
        if args.mode=='fixed' and args.calibration is None:ap.error('--input with fixed mode requires --calibration')
        if args.mode=='adaptive' and args.calibration is not None:ap.error('--calibration requires fixed mode')
        # Match source identity, never infer a recording identity from its filename.
        rec=None
        if args.calibration is not None:
            protocol=json.loads((args.calibration.parent.parent/'protocol.json').read_text())
            matches=[key for key,value in protocol['source_metadata'].items()
                     if Path(value['path']).resolve()==args.input.resolve()]
            if len(matches)!=1:raise ValueError('Calibration protocol must identify exactly one matching source')
            rec=matches[0]
        summary=detect(args.input,args.output,mode=args.mode,ma=args.ma,calibration=args.calibration,
                       chunk_seconds=args.chunk_seconds,batch_channels=args.batch_channels,rec=rec,
                       annotate_shared=False)
        print('COMPLETE',json.dumps({'source':summary['source'],'candidates':summary['candidates']}),flush=True)
        return
    if args.calibration is not None:ap.error('--calibration is only supported with --input')
    sources={rec:args.directory/f'extra_{rec}_signals.h5' for rec in args.recordings}
    for source in sources.values():
        if not source.is_file():raise FileNotFoundError(source)
    args.output.mkdir(parents=True,exist_ok=True)
    for rec in sources:
        if (args.output/f'extra{rec}').exists():raise FileExistsError(f'Output already exists: extra{rec}; choose a new output root')
    summaries={}
    for rec,source in sources.items():
        cal=args.calibration_directory/f'extra{rec}_calibration.npz' if args.mode=='fixed' else None
        summaries[str(rec)]=detect(source,args.output/f'extra{rec}',mode=args.mode,ma=args.ma,calibration=cal,
                                  chunk_seconds=args.chunk_seconds,batch_channels=args.batch_channels,rec=rec)
        (args.output/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
    print('COMPLETE',json.dumps({r:s['candidates'] for r,s in summaries.items()}),flush=True)

if __name__=='__main__':main()
