"""Controlled short-segment comparison for converted extracellular recordings.

Source HDF5 files are read-only. No event is labeled as a validated neuron/spike.
Common observation support across methods prevents exposure-confounded counts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/invivo-matplotlib')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import h5py
import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt
from analysis.pilot import FS, flat_mask, dilate, moving_average, spaced_peaks, write_csv

FILTERS = ['ma100', 'ma200', 'hp300']
METHODS = [f'{f}_{s}' for f in FILTERS for s in ['rms', 'mad']]
CONTEXT = 2500
GUARD = 500
SOS = butter(3, 300, btype='highpass', fs=FS, output='sos')


def residuals(raw):
    return {'ma100':raw-moving_average(raw,100),
            'ma200':raw-moving_average(raw,200),
            'hp300':sosfiltfilt(SOS,raw)}


def controlled_scales(ys, invalid):
    """Both estimators use exactly the same unmasked data; no zero-scale fallback."""
    n=len(invalid)
    nw=(n+FS-1)//FS
    scales={m:np.full(nw,np.nan) for m in METHODS}
    good_counts=np.zeros(nw,dtype=int)
    for w,a in enumerate(range(0,n,FS)):
        b=min(n,a+FS)
        valid=~invalid[a:b]
        good_counts[w]=valid.sum()
        if valid.sum()<max(250,(b-a+1)//2):
            continue
        for f,y in ys.items():
            good=y[a:b][valid]
            scales[f+'_rms'][w]=np.sqrt(np.mean(good**2))
            scales[f+'_mad'][w]=np.median(np.abs(good-np.median(good)))/0.67448975
    common=np.all(np.array([np.isfinite(s)&(s>0) for s in scales.values()]),axis=0)
    for s in scales.values():
        s[~common]=np.nan
    return scales,common,good_counts


def match_indices(a,b,tolerance=3):
    """Ordered one-to-one temporal matches; inputs sorted, same channel only."""
    i=j=0; ia=[]; ib=[]
    while i<len(a) and j<len(b):
        if abs(a[i]-b[j])<=tolerance:
            ia.append(i); ib.append(j); i+=1; j+=1
        elif a[i]<b[j]: i+=1
        else: j+=1
    return np.asarray(ia,dtype=int),np.asarray(ib,dtype=int)


def compare_events(a,b):
    matched=0
    for ch in np.union1d(a[:,0],b[:,0]):
        x=a[a[:,0]==ch,1]; y=b[b[:,0]==ch,1]
        matched+=len(match_indices(x,y)[0])
    union=len(a)+len(b)-matched
    return {'a_count':len(a),'b_count':len(b),'matched_within_0_3ms':matched,
            'a_only':len(a)-matched,'b_only':len(b)-matched,
            'jaccard':matched/union if union else None}


def event_metrics(arr,start,n,exposure):
    bins=(arr[:,1].astype(int)-start)//100
    counts=np.bincount(bins,minlength=(n+99)//100)
    peak=int(np.argmax(counts))
    return {'candidates':len(arr),'channels':len(np.unique(arr[:,0])),
            'candidates_per_usable_channel_second':len(arr)/exposure if exposure else None,
            'largest_10ms_bin_start_s':(start+100*peak)/FS,
            'largest_10ms_bin_candidates':int(counts[peak]),
            'largest_10ms_bin_channels':len(np.unique(arr[bins==peak,0])),
            'largest_10ms_bin_fraction':float(counts[peak]/len(arr)) if len(arr) else 0}


def run_segment(source,start_s,duration,out):
    start=round(start_s*FS); n=round(duration*FS)
    out.mkdir()
    nw=(n+FS-1)//FS
    scales={m:np.full((2048,nw),np.nan) for m in METHODS}
    seeds={m:[] for m in METHODS}
    guard_counts=np.zeros(2048,dtype=int)
    flat_counts=np.zeros(2048,dtype=int)
    exposures=np.zeros(2048)
    common_support=np.zeros((2048,nw),dtype=bool)
    baseline_bins=np.zeros((2048,(n+99)//100))
    begin=time.perf_counter()
    with h5py.File(source,'r') as file:
        ds=file['signals']
        if ds.shape[0]!=2048 or ds.dtype.kind!='f':
            raise ValueError('Expected converted 2048-channel floating-point signals')
        if start<CONTEXT or start+n+CONTEXT>ds.shape[1]:
            raise ValueError('Comparison requires 250 ms of real context on each side')
        lo,hi=start-CONTEXT,start+n+CONTEXT
        core=slice(CONTEXT,CONTEXT+n)
        provenance={'source':str(source.resolve()),'shape':list(ds.shape),'dtype':str(ds.dtype),
                    'file_size_bytes':source.stat().st_size,'file_mtime_ns':source.stat().st_mtime_ns,
                    'sample_start':start,'sample_stop':start+n,'nominal_fs_hz':FS,
                    'physical_fs_hz':10080,'nominal_duration_s':n/FS,'context_samples':CONTEXT}
        for batch in range(0,2048,64):
            raw_batch=ds[batch:batch+64,lo:hi].astype(float)
            if not np.isfinite(raw_batch).all():
                raise ValueError('Nonfinite source data: stop for investigation')
            for i,raw in enumerate(raw_batch):
                ch=batch+i
                flat=flat_mask(raw)
                bad=dilate(flat,GUARD)[core]
                flat_counts[ch]=flat[core].sum(); guard_counts[ch]=bad.sum()
                padded=residuals(raw)
                ys={f:y[core] for f,y in padded.items()}
                sigma,common,good_counts=controlled_scales(ys,bad)
                common_support[ch]=common
                exposures[ch]=good_counts[common].sum()/FS
                allowed=(~bad)&common[np.arange(n)//FS]
                for f in FILTERS:
                    # Detect with real context, then keep only peaks inside the core.
                    peaks=find_peaks(-padded[f])[0]-CONTEXT
                    peaks=peaks[(peaks>=0)&(peaks<n)]
                    peaks=peaks[allowed[peaks]]
                    amps=-ys[f][peaks]
                    for estimator in ['rms','mad']:
                        method=f+'_'+estimator
                        scales[method][ch]=sigma[method]
                        keep=amps>=5*sigma[method][peaks//FS]
                        seeds[method].append((peaks[keep],amps[keep]))
                baseline=raw[core]-ys['ma200']
                baseline_bins[ch]=[np.mean(baseline[a:a+100]) for a in range(0,n,100)]
            if batch%512==0:
                print(f'{out.name}: channels {batch}–{batch+63}',flush=True)
        events={}; metrics={}; floors={}
        for method in METHODS:
            floors[method]=np.array([np.median(col[np.isfinite(col)]) if np.isfinite(col).any() else np.nan
                                     for col in scales[method].T])
            rows=[]; floor_removed=0
            for ch,(p,a) in enumerate(seeds[method]):
                keep=a>=5*floors[method][p//FS]
                floor_removed+=int((~keep).sum())
                p,a=p[keep],a[keep]
                keep=spaced_peaks(p,a,50)
                p,a=p[keep],a[keep]
                rows.extend((ch,int(t+start),float(amp),float(5*max(scales[method][ch,t//FS],floors[method][t//FS]))) for t,amp in zip(p,a))
            arr=np.asarray(rows,dtype=float).reshape(-1,4)
            events[method]=arr
            metrics[method]=event_metrics(arr,start,n,exposures.sum())
            metrics[method]['pre_spacing_candidates_removed_by_floor']=floor_removed
            write_csv(out/f'{method}.csv',['channel_id','sample_index','negative_amplitude','threshold'],
                      ((int(ch),int(p),a,t) for ch,p,a,t in arr))
        pairs={}
        for est in ['rms','mad']:
            for alt in ['ma100','hp300']:
                a,b='ma200_'+est,alt+'_'+est
                pairs[a+'__'+b]=compare_events(events[a],events[b])
        for f in FILTERS:
            a,b=f+'_rms',f+'_mad'
            pairs[a+'__'+b]=compare_events(events[a],events[b])
        np.savez_compressed(out/'diagnostics.npz',**{'sigma_'+k:v for k,v in scales.items()},
                            **{'floor_'+k:v for k,v in floors.items()},baseline_bins=baseline_bins,
                            common_support=common_support,usable_seconds=exposures,
                            flat_samples=flat_counts,guard_samples=guard_counts)
        provenance.update({'total_channel_seconds':2048*n/FS,'usable_channel_seconds':float(exposures.sum()),
                           'flat_fraction':float(flat_counts.sum()/(2048*n)),
                           'guard_fraction':float(guard_counts.sum()/(2048*n)),
                           'usable_fraction':float(exposures.sum()/(2048*n/FS)),
                           'excluded_channel_windows':int((~common_support).sum()),
                           'methods':metrics,'comparisons':pairs,
                           'duration_wall_s':time.perf_counter()-begin})
        (out/'summary.json').write_text(json.dumps(provenance,indent=2,allow_nan=False)+'\n')
        review_waveforms(ds,events,out,start,n)
    print(f'{out.name}: done; usable {provenance["usable_fraction"]:.2%}',flush=True)
    return provenance


def review_waveforms(ds,events,out,start,n):
    """Six deterministic diagnostic examples: shared, MA-only, HP-only.

    Selection targets a busy bin for MA-only and large amplitudes otherwise.
    It is deliberately biased; no accuracy/sensitivity estimates follow.
    """
    a,b=events['ma200_mad'],events['hp300_mad']
    a_shared=np.zeros(len(a),bool); b_shared=np.zeros(len(b),bool)
    for ch in np.union1d(a[:,0],b[:,0]):
        ai=np.flatnonzero(a[:,0]==ch); bi=np.flatnonzero(b[:,0]==ch)
        ia,ib=match_indices(a[ai,1],b[bi,1])
        a_shared[ai[ia]]=True; b_shared[bi[ib]]=True
    busy=event_metrics(a,start,n,1)['largest_10ms_bin_start_s']
    groups=[('Shared MA200 / HP300',a[a_shared]),('MA200-only',a[~a_shared]),('HP300-only',b[~b_shared])]
    chosen=[]
    for label,arr in groups:
        if label=='MA200-only':
            in_bin=(arr[:,1]>=round(busy*FS))&(arr[:,1]<round(busy*FS)+100)
            order=np.lexsort((-arr[:,2],~in_bin))
        else:
            order=np.argsort(-arr[:,2],kind='stable')
        used=set()
        for idx in order:
            ch=int(arr[idx,0])
            if ch in used: continue
            used.add(ch); chosen.append((label,arr[idx]))
            if len(used)==2: break
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(max(len(chosen),1),2,figsize=(12,2.5*max(len(chosen),1)),squeeze=False)
    manifest=[]
    for row,(label,event) in enumerate(chosen):
        ch,p=int(event[0]),int(event[1])
        raw=ds[ch,p-CONTEXT-500:p+CONTEXT+501].astype(float)
        ys=residuals(raw)
        loc=slice(CONTEXT,CONTEXT+1001)
        x=raw[loc]
        t=np.arange(-500,501)/FS*1000
        ax=axes[row,0]
        ax.plot(t,x,lw=.65,color='#617b8e',label='Stored signal')
        ax.plot(t,x-ys['ma200'][loc],lw=1,color='#bd841d',label='MA200 baseline')
        ax.set_title(f'{label}: ch {ch}, {p/FS:.4f} s')
        ax.set_xlabel('Time relative to candidate (ms)')
        ax.legend(fontsize=7)
        ax=axes[row,1]
        for f,color in [('ma100','#999999'),('ma200','#276d98'),('hp300','#b84b41')]:
            ax.plot(t,ys[f][loc],label=f,color=color,lw=.9)
        ax.set_xlim(-5,5)
        ax.set_title('Same event, three residuals (±5 ms)')
        ax.set_xlabel('Time relative to candidate (ms)')
        ax.legend(fontsize=7)
        for ax in axes[row]:
            ax.set_ylabel('Stored float units'); ax.grid(alpha=.2)
        manifest.append({'category':label,'channel_id':ch,'sample_index':p,
                         'time_s':p/FS,'selection':'two distinct channels; largest amplitude; MA-only prioritizes busiest MA200/MAD bin'})
    if not chosen:
        axes[0,0].text(.2,.5,'No candidates'); axes[0,1].axis('off')
    fig.suptitle(out.name+' — diagnostic waveform examples, not ground truth',fontsize=13)
    fig.tight_layout(rect=(0,0,1,.97))
    fig.savefig(out/'waveforms.png',dpi=130)
    plt.close(fig)
    (out/'waveform_selection.json').write_text(json.dumps(manifest,indent=2)+'\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--directory',type=Path,default=Path('/Volumes/YZ/recording/invivo/26-11-06/0192'))
    ap.add_argument('--output',type=Path,default=Path('results/controlled_comparison'))
    ap.add_argument('--starts',type=float,nargs='+',default=[30,60,180])
    ap.add_argument('--duration',type=float,default=5)
    args=ap.parse_args()
    if args.duration<1 or not np.isfinite(args.duration) or not all(np.isfinite(args.starts)):
        ap.error('finite starts and duration >=1 s required')
    if args.output.exists() and any(args.output.iterdir()):
        ap.error('output must be empty')
    args.output.mkdir(parents=True,exist_ok=True)
    config={'nominal_fs_hz':FS,'physical_fs_hz':10080,'filters':FILTERS,
            'estimators':['rms','mad'],'threshold_multiplier':5,'peak_spacing_ms':5,
            'flat_min_samples':10,'guard_ms':50,'context_ms':250,
            'support':'identical across methods: flat guards excluded; >=half-window and >=250 samples; positive finite scales for all methods',
            'floor':'per-method median scale across common-support channels in each nominal second',
            'starts_s':args.starts,'duration_s':args.duration,'recordings':[4,5,6],
            'experimental_context':{'extra4':'Pure extracellular reference recording; earlier stimulation history not specified.',
                                    'extra5':'Pure extracellular recording acquired after current-injection stimulation experiments.',
                                    'extra6':'Pure extracellular recording acquired after current-injection stimulation experiments.'},
            'interpretation':'Compare methods within the same segment. Keep recordings separate: post-stimulation baseline and neural activity may differ; no causal pre/post inference.',
            'event_match_tolerance_samples':3,'python':sys.executable,
            'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(__file__).with_name('pilot.py')]},
            'limitations':['No ground truth; counts and agreement do not measure accuracy.',
                           'Fixed noise estimator does not imply fixed absolute voltage threshold across filters.',
                           'Flatness is a proxy, not calibrated clipping detection; invalid intervals are not reconstructed.',
                           'Three prespecified times per recording are not representative of the entire recording.',
                           'No global motion-artifact exclusion, spatial deduplication, spike sorting or stimulation processing.',
                           'Independent short segments; this is not a full-recording streaming detector.']}
    (args.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    summaries={}
    for rec in [4,5,6]:
        for start in args.starts:
            name=f'extra{rec}_{start:g}_{start+args.duration:g}'
            summaries[name]=run_segment(args.directory/f'extra_{rec}_signals.h5',start,args.duration,args.output/name)
    (args.output/'summary.json').write_text(json.dumps(summaries,indent=2,allow_nan=False)+'\n')
    print('Completed all segments:',args.output.resolve(),flush=True)


if __name__=='__main__': main()
