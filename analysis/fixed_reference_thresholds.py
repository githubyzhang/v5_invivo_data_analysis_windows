"""Fixed quiet-reference MAD versus adaptive MAD, on matched observation support.

Run with project Python. Sources read-only; prior results untouched. Reference
quality/stability gates are exploratory and do not prove artifact-free signals.
"""
import json, hashlib, os, sys, warnings
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/invivo-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import h5py
from scipy.signal import find_peaks
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analysis.pilot import FS, flat_mask, dilate, spaced_peaks, write_csv
from analysis.compare_detectors import CONTEXT, compare_events
from analysis.compare_ma_windows import ma_residuals, FILTERS, matched_members

REFS={4:[30,90,180],5:[30,90,240],6:[30,90,180]}
TARGETS={4:[60,240],5:[180],6:[60,240]}
ROOT=Path('results/fixed_reference_thresholds')
DATA=Path('/Volumes/YZ/recording/invivo/26-11-06/0192')


def prior(rec,start):
    name=f'extra{rec}_{start}_{start+5}'
    if start in [90,240]:
        return name,Path('results/frozen_guard_validation/detector')/name,Path('results/frozen_guard_validation/flags')/name
    return name,Path('results/controlled_comparison')/name,Path('results/shared_artifact_review_extended')/name


def mad(x,axis=None):
    med=np.median(x,axis=axis,keepdims=True)
    return np.median(np.abs(x-med),axis=axis)/.67448975


def calibrate(scales,accepted):
    """scales: segments x filters x channels x seconds; gate shared by filters.

    Median within each reference segment, then median across accepted segments.
    Every filter must have max/min <=1.5 across >=2 reference segments.
    """
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',RuntimeWarning)
        segment=np.nanmedian(np.where(accepted[:,None,:,:],scales,np.nan),axis=3)
        estimate=np.nanmedian(segment,axis=0)
        ratio=np.nanmax(segment,axis=0)/np.nanmin(segment,axis=0)
    count=np.isfinite(segment).all(axis=1).sum(axis=0)
    stable=(count>=2)&np.all(np.isfinite(estimate)&(estimate>0)&(ratio<=1.5),axis=0)
    floor=np.array([np.median(v[stable]) if stable.any() else np.nan for v in estimate])
    threshold=5*np.maximum(estimate,floor[:,None]);threshold[:,~stable]=np.nan
    return segment,estimate,ratio,count,stable,threshold


def reference(rec,start,out):
    name,old,flags=prior(rec,start);summary=json.loads((old/'summary.json').read_text())
    shared=np.load(flags/'flags_and_evidence.npz')['mask_b3_h6_f50_g20']
    scales=np.zeros((3,2048,5));accepted=np.zeros((2048,5),bool)
    swing=np.zeros((2048,5));burst=swing.copy();flatfree=np.zeros_like(accepted)
    lo=start*FS;core=slice(CONTEXT,CONTEXT+5*FS)
    with h5py.File(summary['source'],'r') as f:
        for batch in range(0,2048,64):
            rawbatch=f['signals'][batch:batch+64,lo-CONTEXT:lo+5*FS+CONTEXT].astype(float)
            if not np.isfinite(rawbatch).all():raise ValueError('Nonfinite source')
            for j,raw in enumerate(rawbatch):
                ch=batch+j;ys=ma_residuals(raw)
                bad=dilate(flat_mask(raw),500)[core]
                base=(raw-ys['ma200'])[core].reshape(5,FS)
                for fi,fil in enumerate(FILTERS):scales[fi,ch]=mad(ys[fil][core].reshape(5,FS),axis=1)
                bmad=mad(ys['ma50'][core].reshape(5,100,100),axis=2)
                swing[ch]=(np.percentile(base,95,axis=1)-np.percentile(base,5,axis=1))/np.maximum(scales[0,ch],np.finfo(float).tiny)
                burst[ch]=np.percentile(bmad,95,axis=1)/np.maximum(np.median(bmad,axis=1),np.finfo(float).tiny)
                flatfree[ch]=~bad.reshape(5,FS).any(axis=1)
                accepted[ch]=flatfree[ch]&~shared.reshape(5,FS).any(axis=1)&(swing[ch]<=6)&(burst[ch]<=2)&np.all(np.isfinite(scales[:,ch])&(scales[:,ch]>0),axis=0)
            if batch%1024==0:print('reference',name,batch,flush=True)
    np.savez_compressed(out/(name+'.npz'),scales=scales,accepted=accepted,baseline_swing_ratio=swing,fast_variability_ratio=burst,flat_guard_free=flatfree)
    return scales,accepted


def reference_plots(rec,accepted,out):
    fig,axes=plt.subplots(4,2,figsize=(12,10));selection=[]
    with h5py.File(DATA/f'extra_{rec}_signals.h5','r') as f:
        for row,ch in enumerate([1436,1378,1919,1591]):
            candidates=np.argwhere(accepted[:,ch,:]);ok=len(candidates)>0
            seg,w=candidates[0] if ok else (0,0);t=REFS[rec][seg]+int(w)+.5;idx=round(t*FS)
            raw=f['signals'][ch,idx-CONTEXT-1000:idx+CONTEXT+1000].astype(float)
            ys=ma_residuals(raw);sl=slice(CONTEXT,-CONTEXT);tt=np.arange(-1000,1000)/FS*1000
            axes[row,0].plot(tt,raw[sl],lw=.7);axes[row,0].plot(tt,(raw-ys['ma200'])[sl],lw=1)
            for fil in FILTERS:axes[row,1].plot(tt,ys[fil][sl],lw=.6,label=fil)
            axes[row,0].set_title(f'ch {ch}, {t:.1f}s: '+('accepted reference window' if ok else 'no accepted reference; example only'))
            for ax in axes[row]:ax.set_xlabel('Time from window center (ms)');ax.set_ylabel('Stored float units');ax.grid(alpha=.2)
            axes[row,1].legend(fontsize=8);selection.append({'channel':ch,'time_s':t,'accepted_window':ok})
    fig.tight_layout();fig.savefig(out/f'extra{rec}_reference_examples.png',dpi=130);plt.close(fig)
    (out/f'extra{rec}_reference_selection.json').write_text(json.dumps(selection,indent=2)+'\n')


def target(rec,start,stable,threshold,out, *, prior_paths=None):
    name,old,flags=prior(rec,start) if prior_paths is None else prior_paths
    dest=out/name;dest.mkdir()
    oldd=np.load(old/'diagnostics.npz');shared=np.load(flags/'flags_and_evidence.npz')['mask_b3_h6_f50_g20']
    n=5*FS;lo=start*FS;core=slice(CONTEXT,CONTEXT+n)
    sigmas=np.full((3,2048,5),np.nan);support=np.zeros((2048,5),bool)
    seeds={fil:[] for fil in FILTERS};exposure=0.;rows=[]
    with h5py.File(DATA/f'extra_{rec}_signals.h5','r') as f:
        for batch in range(0,2048,64):
            rawbatch=f['signals'][batch:batch+64,lo-CONTEXT:lo+n+CONTEXT].astype(float)
            if not np.isfinite(rawbatch).all():raise ValueError('Nonfinite source')
            for j,raw in enumerate(rawbatch):
                ch=batch+j;ys=ma_residuals(raw);bad=dilate(flat_mask(raw),500)[core]
                for w in range(5):
                    good=~bad[w*FS:(w+1)*FS]
                    if good.sum()>=5000:
                        for fi,fil in enumerate(FILTERS):sigmas[fi,ch,w]=mad(ys[fil][core][w*FS:(w+1)*FS][good])
                support[ch]=stable[ch]&oldd['common_support'][ch]&np.all(np.isfinite(sigmas[:,ch])&(sigmas[:,ch]>0),axis=0)
                allowed=~bad&support[ch,np.arange(n)//FS];exposure+=allowed.sum()/FS
                for fil in FILTERS:
                    peaks=find_peaks(-ys[fil])[0]-CONTEXT;peaks=peaks[(peaks>=0)&(peaks<n)];peaks=peaks[allowed[peaks]]
                    seeds[fil].append((peaks,-ys[fil][peaks+CONTEXT]))
            if batch%1024==0:print('target',name,batch,flush=True)
    metrics={};events={};adaptive_thresholds=np.full((3,2048,5),np.nan)
    for fi,fil in enumerate(FILTERS):
        floors=np.array([np.median(sigmas[fi,:,w][support[:,w]]) if support[:,w].any() else np.nan for w in range(5)])
        adaptive_thresholds[fi]=5*np.maximum(sigmas[fi],floors[None,:])
        for mode in ['adaptive','fixed']:
            rows=[]
            for ch,(p,a) in enumerate(seeds[fil]):
                thr=np.full(len(p),threshold[fi,ch]) if mode=='fixed' else adaptive_thresholds[fi,ch,p//FS]
                keep=a>=thr;p2,a2,t2=p[keep],a[keep],thr[keep]
                chosen=spaced_peaks(p2,a2,50)
                rows.extend((ch,int(t+lo),float(amp),float(th),int(shared[t])) for t,amp,th in zip(p2[chosen],a2[chosen],t2[chosen]))
            arr=np.asarray(rows,float).reshape(-1,5);events[fil+'_'+mode]=arr
            write_csv(dest/(fil+'_'+mode+'.csv'),['channel_id','sample_index','negative_amplitude','threshold','shared20_warning'],rows)
            metrics[fil+'_'+mode]={'candidates':len(arr),'shared20_flagged':int(arr[:,4].sum()),
                'outside_shared20':int((arr[:,4]==0).sum()),'review_channels':{str(c):int((arr[:,0]==c).sum()) for c in [1436,1378]}}
            for ch in np.unique(arr[:,0].astype(int)):
                e=arr[arr[:,0]==ch];assert (np.diff(e[:,1])>=50).all()
                if mode=='fixed':np.testing.assert_array_equal(e[:,3],np.full(len(e),threshold[fi,ch]))
        metrics[fil+'_overlap']=compare_events(events[fil+'_adaptive'][:,:4],events[fil+'_fixed'][:,:4])
    np.savez_compressed(dest/'thresholds.npz',fixed=threshold,adaptive=adaptive_thresholds,common_support=support)
    summary={'usable_channel_seconds':exposure,'prior_usable_channel_seconds':json.loads((old/'summary.json').read_text())['usable_channel_seconds'],
             'reference_eligible_channels':int(stable.sum()),'metrics':metrics}
    (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    # MA50 review: largest added/removed events, distinct channels per category.
    a,b=events['ma50_adaptive'],events['ma50_fixed'];chosen=[]
    for label,arr in [('Fixed-only',b[~matched_members(b[:,:4],a[:,:4])]),('Adaptive-only',a[~matched_members(a[:,:4],b[:,:4])])]:
        used=set()
        for i in np.argsort(-arr[:,2],kind='stable'):
            ch=int(arr[i,0])
            if ch in used:continue
            used.add(ch);chosen.append((label,arr[i]))
            if len(used)==2:break
    fig,axes=plt.subplots(max(1,len(chosen)),2,figsize=(12,2.7*max(1,len(chosen))),squeeze=False)
    selection=[]
    with h5py.File(DATA/f'extra_{rec}_signals.h5','r') as f:
        for row,(label,e) in enumerate(chosen):
            ch,p=int(e[0]),int(e[1]);raw=f['signals'][ch,p-CONTEXT-500:p+CONTEXT+501].astype(float);ys=ma_residuals(raw)
            sl=slice(CONTEXT,-CONTEXT);tt=np.arange(-500,501)/FS*1000
            axes[row,0].plot(tt,raw[sl],lw=.7);axes[row,0].plot(tt,(raw-ys['ma50'])[sl],lw=1)
            axes[row,0].set_title(f'{label}: ch {ch}, {p/FS:.4f}s; shared flag {bool(e[4])}')
            axes[row,1].plot(tt,ys['ma50'][sl],lw=.8);axes[row,1].set_xlim(-5,5)
            axes[row,1].axhline(-threshold[0,ch],color='#d76b20',label='Fixed threshold')
            # Show the adaptive threshold on both sides if a 1 s boundary occurs.
            ix=np.clip((p-lo+np.arange(-500,501))//FS,0,4)
            axes[row,1].plot(tt,-adaptive_thresholds[0,ch,ix],color='#2867a2',ls=':',label='Adaptive threshold')
            axes[row,1].legend(fontsize=8)
            for ax in axes[row]:ax.set_xlabel('Time from candidate (ms)');ax.set_ylabel('Stored float units');ax.grid(alpha=.2)
            selection.append({'category':label,'channel':ch,'sample_index':p})
    if not chosen:axes[0,0].text(.1,.5,'No discordant candidates');axes[0,1].axis('off')
    fig.tight_layout();fig.savefig(dest/'waveforms.png',dpi=130);plt.close(fig)
    (dest/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
    return summary


def report(out,calibrations,summaries):
    rows=[];details=[]
    for name,s in summaries.items():
        for fil in FILTERS:
            a,b=[s['metrics'][fil+'_'+m] for m in ['adaptive','fixed']]
            rows.append(f'<tr><td>{name}</td><td>{fil}</td><td>{a["candidates"]:,}</td><td>{b["candidates"]:,}</td><td>{a["outside_shared20"]:,} / {b["outside_shared20"]:,}</td><td>{s["usable_channel_seconds"]:.1f}</td></tr>')
        details.append(f'<h2>{name}</h2><p>Largest-amplitude MA50 disagreements on distinct channels; biased review examples, not accuracy estimates. Prior usable exposure {s["prior_usable_channel_seconds"]:.1f} channel-seconds; paired experiment {s["usable_channel_seconds"]:.1f}.</p><img src="{name}/waveforms.png"><p><a href="{name}/summary.json">Metrics and review-channel counts</a></p>')
    refs=''.join(f'<h2>extra_{rec}: reference calibration</h2><p>Reference starts: {REFS[rec]} s; each 5 s. {c["stable_channels"]} / 2048 channels eligible; {c["insufficient_reference_channels"]} lack two qualifying segments; {c["unstable_channels"]} have sufficient segments but inconsistent scales.</p><img src="references/extra{rec}_reference_examples.png">' for rec,c in calibrations.items())
    html='''<!doctype html><meta charset="utf-8"><title>Fixed quiet-reference thresholds</title><style>body{font:17px/1.55 system-ui;max-width:1250px;margin:35px auto;padding:20px;color:#243342}table{border-collapse:collapse;width:100%}td,th{padding:9px;border-bottom:1px solid #ddd}img{width:100%}.note{background:#fff2d3;padding:18px}</style><h1>Fixed per-channel quiet-reference thresholds</h1><p class="note">Exploratory calibration, not a validated clean-reference library. No detector default changed. Raw data and prior candidates preserved. Fast-noise subtraction remains disabled.</p><h2>Reference selection and stability</h2><p>Reference intervals are separate from comparison intervals within each recording. All use nominal 10 kHz. extra_5/6 are purely extracellular recordings acquired after stimulation experiments; no noise calibration is transferred between recordings.</p><p>Candidate 1 s reference windows must have no exact-flat ±50 ms guard and no existing shared20 flag. MA200 baseline 95–5 percentile range must be ≤6× MA50 MAD; the 95th percentile of 10 ms MA50 MAD must be ≤2× its median. All filter scales must be finite and positive. These are exploratory screening rules, not proof of clean data; persistent noise can pass.</p><p>For each filter and channel, take the median MAD across accepted seconds within each reference interval, then the median across intervals. Require at least two intervals and max/min segment scale ≤1.5 for every filter. Stability is evaluated before the across-channel floor, so the floor cannot hide disagreement. Fixed threshold = 5× max(channel reference MAD, median reference MAD across eligible channels), separately for MA50/100/200.</p><p>Unavailable channels are not silently assigned another recording's estimate. The adaptive comparator recomputes its per-second median floor on the same eligible channels. Both modes use identical clipping guards, prior common support, reference eligibility, negative-peak selection and 5 ms spacing. This paired subset differs from prior all-channel candidate totals. Shared flags annotate candidates but do not exclude target samples. Fixed thresholds are constant over time within each filter; they are not the same voltage threshold across filters.</p><h2>Matched comparison</h2><table><tr><th>Interval</th><th>Filter</th><th>Adaptive</th><th>Fixed</th><th>Outside shared20: adaptive / fixed</th><th>Paired channel-seconds</th></tr>'''+''.join(rows)+'''</table><p>More candidates may reveal previously masked eAPs or more artifact crossings. Fewer candidates may remove artifacts or true spikes. Counts and reference stability do not establish detection accuracy. Persistent fast noise, uncalibrated saturation, and spike contamination remain possible. Reference selections are not user-confirmed. See <a href="protocol.json">protocol</a>, <a href="calibration_summary.json">calibration coverage</a>, and <a href="summary.json">all results</a>.</p>'''+refs+''.join(details)
    (out/'review.html').write_text(html)


def main():
    for rec in REFS:
        if not (DATA/f'extra_{rec}_signals.h5').is_file():raise FileNotFoundError(DATA)
        assert not set(REFS[rec])&set(TARGETS[rec])
    ROOT.mkdir(exist_ok=False);out=ROOT/'references';out.mkdir()
    protocol={'reference_starts_s':REFS,'target_starts_s':TARGETS,'duration_s':5,'reference_gate_baseline_ratio':6,
        'reference_gate_fast_ratio':2,'minimum_reference_segments':2,'maximum_segment_scale_ratio':1.5,
        'threshold_multiplier':5,'nominal_fs_hz':10000,'physical_fs_hz':10080,'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path('analysis/pilot.py'),Path('analysis/compare_ma_windows.py')]},
        'source_metadata':{str(rec):{'path':str(DATA/f'extra_{rec}_signals.h5'),'size':(DATA/f'extra_{rec}_signals.h5').stat().st_size,'mtime_ns':(DATA/f'extra_{rec}_signals.h5').stat().st_mtime_ns} for rec in REFS},
        'defaults_changed':False,'reference_status':'Algorithm-screened candidates, not manually certified clean'}
    (ROOT/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    calibrations={};models={}
    # Freeze all recording calibrations before detecting targets.
    for rec,starts in REFS.items():
        arrays=[reference(rec,start,out) for start in starts];scales=np.stack([a[0] for a in arrays]);accepted=np.stack([a[1] for a in arrays])
        seg,est,ratio,count,stable,thr=calibrate(scales,accepted)
        models[rec]=(stable,thr)
        np.savez_compressed(out/f'extra{rec}_calibration.npz',segment_scales=seg,reference_mad=est,segment_ratio=ratio,accepted=accepted,reference_segment_count=count,eligible=stable,thresholds=thr)
        calibrations[rec]={'stable_channels':int(stable.sum()),'insufficient_reference_channels':int((count<2).sum()),'unstable_channels':int(((count>=2)&~stable).sum())}
        write_csv(out/f'extra{rec}_channels.csv',['channel_id','eligible','reference_segment_count','ma50_ratio','ma100_ratio','ma200_ratio','ma50_threshold','ma100_threshold','ma200_threshold'],((ch,int(stable[ch]),int(count[ch]),*ratio[:,ch],*thr[:,ch]) for ch in range(2048)))
        reference_plots(rec,accepted,out)
        print('calibration',rec,calibrations[rec],flush=True)
    (ROOT/'calibration_summary.json').write_text(json.dumps(calibrations,indent=2)+'\n')
    summaries={}
    for rec,starts in TARGETS.items():
        for start in starts:summaries[prior(rec,start)[0]]=target(rec,start,*models[rec],ROOT)
    (ROOT/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
    report(ROOT,calibrations,summaries)

if __name__=='__main__':main()
