"""Evaluate shared-disturbance review flags without deleting or redetecting events.

Flags are heuristic: a population event can also be synchronous. Existing detector
outputs and source recordings are untouched. Nominal time base remains 10 kHz.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/invivo-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import h5py
import numpy as np
from scipy.signal import sosfiltfilt
from analysis.compare_detectors import FS, METHODS, SOS, CONTEXT
from analysis.pilot import flat_mask,dilate,write_csv

SIGMAS=(6,8)
BASE_SIGMAS=(3,6,8)
FRACTIONS=(.25,.50,.75)
GUARDS=(5,10,20)
MIN_CHANNELS=1024
PRIMARY='k6_f50_g10'


def intervals(mask):
    """Half-open intervals in samples."""
    edges=np.diff(np.r_[False,mask,False].astype(np.int8))
    return list(zip(np.flatnonzero(edges==1).tolist(),np.flatnonzero(edges==-1).tolist()))


def consensus(pos,neg,eligible,fraction,min_channels=MIN_CHANNELS):
    """A same-sign quorum, with an explicit minimum eligible-channel count."""
    return (eligible>=min_channels)&(np.maximum(pos,neg)>=fraction*eligible)


def build_mask(base_positive,base_negative,base_eligible,hp_positive,hp_negative,hp_eligible,
               fraction,guard_ms,n):
    b=consensus(base_positive,base_negative,base_eligible,fraction)
    h=consensus(hp_positive,hp_negative,hp_eligible,fraction)
    # A baseline difference uses two adjacent 10 ms averages. Cover both bins.
    baseline=np.zeros(n,bool)
    for i in np.flatnonzero(b):
        baseline[max(0,(i-1)*100):min(n,(i+1)*100)]=True
    broadband=np.repeat(h,10)[:n]
    radius=round(guard_ms*FS/1000)
    return dilate(baseline,radius),dilate(broadband,radius)


def ratio(numerator,denominator):
    return np.divide(numerator,denominator,out=np.zeros_like(numerator,dtype=float),where=denominator>0)


def evaluate_segment(name,s,prior,out):
    dest=out/name; dest.mkdir()
    start,stop=s['sample_start'],s['sample_stop']; n=stop-start
    if n%100: raise ValueError('This evaluation requires whole 10 ms bins')
    original=np.load(prior/name/'diagnostics.npz')
    baseline=original['baseline_bins']
    baseline_deltas=np.diff(baseline,axis=1,prepend=baseline[:,0:1])
    nbase=n//100; nhp=n//10
    hp_pos={k:np.zeros(nhp,np.int32) for k in SIGMAS}
    hp_neg={k:np.zeros(nhp,np.int32) for k in SIGMAS}
    hp_eligible=np.zeros(nhp,np.int32)
    baseline_valid=np.zeros((2048,nbase),bool)
    base_scale=np.full(2048,np.nan)
    exposure_by_sample=np.zeros(n,np.int32)
    with h5py.File(s['source'],'r') as file:
        ds=file['signals']
        for batch in range(0,2048,64):
            raw_batch=ds[batch:batch+64,start-CONTEXT:stop+CONTEXT].astype(float)
            if not np.isfinite(raw_batch).all(): raise ValueError('Nonfinite raw data')
            for i,raw in enumerate(raw_batch):
                ch=batch+i
                flat_guard=dilate(flat_mask(raw),500)[CONTEXT:-CONTEXT]
                allowed=(~flat_guard)&original['common_support'][ch,np.arange(n)//FS]
                exposure_by_sample+=allowed
                valid_bins=allowed.reshape(-1,100).all(axis=1)
                pair_valid=valid_bins&np.r_[False,valid_bins[:-1]]
                baseline_valid[ch]=pair_valid
                delta=baseline_deltas[ch,pair_valid]
                if len(delta)>=100:
                    scale=np.median(np.abs(delta-np.median(delta)))/.67448975
                    if scale>0 and np.isfinite(scale): base_scale[ch]=scale
                hp=sosfiltfilt(SOS,raw)[CONTEXT:-CONTEXT]
                sigma=np.maximum(original['sigma_hp300_mad'][ch],original['floor_hp300_mad'])
                threshold_scale=sigma[np.arange(n)//FS]
                valid_hp=allowed.reshape(-1,10).all(axis=1)&np.isfinite(threshold_scale[::10])&(threshold_scale[::10]>0)
                hp_eligible+=valid_hp
                # All samples within a 1 ms bin share a nominal-second scale.
                maxima=hp.reshape(-1,10).max(axis=1)
                minima=hp.reshape(-1,10).min(axis=1)
                for k in SIGMAS:
                    hp_pos[k]+=valid_hp&(maxima>k*threshold_scale[::10])
                    hp_neg[k]+=valid_hp&(minima<-k*threshold_scale[::10])
    finite=np.isfinite(base_scale)&(base_scale>0)
    baseline_valid &= finite[:,None]
    floor=float(np.median(base_scale[finite])) if finite.any() else None
    base_threshold=np.maximum(base_scale,floor) if floor is not None else np.full(2048,np.nan)
    base_pos={k:np.sum(baseline_valid&(baseline_deltas>k*base_threshold[:,None]),axis=0) for k in BASE_SIGMAS}
    base_neg={k:np.sum(baseline_valid&(baseline_deltas<-k*base_threshold[:,None]),axis=0) for k in BASE_SIGMAS}
    base_eligible=baseline_valid.sum(axis=0)
    exposure=float(exposure_by_sample.sum()/FS)
    if abs(exposure-s['usable_channel_seconds'])>1e-7:
        raise AssertionError('Recomputed exposure differs from controlled comparison')
    variants={}; masks={}; contributions={}
    settings=[(k,k,frac,guard,f'k{k}_f{round(frac*100)}_g{guard}')
              for k in SIGMAS for frac in FRACTIONS for guard in GUARDS]
    settings += [(3,6,frac,guard,f'b3_h6_f{round(frac*100)}_g{guard}')
                 for frac in FRACTIONS for guard in GUARDS]
    for bk,hk,frac,guard,key in settings:
        bm,hm=build_mask(base_pos[bk],base_neg[bk],base_eligible,hp_pos[hk],hp_neg[hk],hp_eligible,frac,guard,n)
        mask=bm|hm; masks[key]=mask
        removed_exposure=float(exposure_by_sample[mask].sum()/FS)
        variants[key]={'flagged_duration_s':float(mask.sum()/FS),
                       'additional_excluded_channel_seconds':removed_exposure,
                       'retained_channel_seconds':exposure-removed_exposure,
                       'fraction_of_previously_usable_time_flagged':removed_exposure/exposure if exposure else None,
                       'interval_count':len(intervals(mask)),
                       'baseline_flagged_s':float(bm.sum()/FS),'broadband_flagged_s':float(hm.sum()/FS),
                       'methods':{}}
        if key==PRIMARY: contributions={'baseline':bm,'broadband':hm}
    events={}
    for method in METHODS:
        a=np.loadtxt(prior/name/f'{method}.csv',delimiter=',',skiprows=1,ndmin=2)
        if not a.size: a=np.empty((0,4))
        pos=a[:,1].astype(int)-start; events[method]=a
        for key,mask in masks.items():
            flagged=int(mask[pos].sum())
            variants[key]['methods'][method]={'original':len(a),'flagged':flagged,'retained':len(a)-flagged}
        # Preserve every event. Annotation is independent of the old flat guard.
        write_csv(dest/f'annotated_{method}.csv',
                  ['channel_id','sample_index','negative_amplitude','threshold','shared_flag','baseline_flag','broadband_flag'],
                  ((int(ch),int(p),amp,thr,int(masks[PRIMARY][int(p)-start]),
                    int(contributions['baseline'][int(p)-start]),int(contributions['broadband'][int(p)-start]))
                   for ch,p,amp,thr in a))
    stable={}
    for ch in [1436,1378]:
        a=events['hp300_mad']; p=a[a[:,0]==ch,1].astype(int)-start
        stable[str(ch)]={'original_candidates':len(p),'flagged_candidates':int(masks[PRIMARY][p].sum()),
                         'retained_candidates':int((~masks[PRIMARY][p]).sum())}
    np.savez_compressed(dest/'flags_and_evidence.npz',**{'mask_'+k:v for k,v in masks.items()},
                        baseline_primary=contributions['baseline'],broadband_primary=contributions['broadband'],
                        hp_eligible=hp_eligible,baseline_eligible=base_eligible,
                        **{f'hp_positive_k{k}':hp_pos[k] for k in SIGMAS},
                        **{f'hp_negative_k{k}':hp_neg[k] for k in SIGMAS},
                        **{f'baseline_positive_k{k}':base_pos[k] for k in BASE_SIGMAS},
                        **{f'baseline_negative_k{k}':base_neg[k] for k in BASE_SIGMAS},
                        baseline_scale=base_scale,eligible_channels_per_sample=exposure_by_sample)
    rows=[]
    for a,b in intervals(masks[PRIMARY]):
        reasons=[]
        if contributions['baseline'][a:b].any(): reasons.append('baseline')
        if contributions['broadband'][a:b].any(): reasons.append('broadband')
        rows.append([start+a,start+b,(start+a)/FS,(start+b)/FS,(b-a)/FS,'+'.join(reasons)])
    write_csv(dest/'flagged_intervals.csv',['start_sample','stop_sample_exclusive','start_s','stop_s','duration_s','evidence'],rows)
    summary={'source':s['source'],'sample_start':start,'sample_stop':stop,
             'original_usable_channel_seconds':exposure,'baseline_noise_floor':floor,
             'hp_bins_with_insufficient_channels':int((hp_eligible<MIN_CHANNELS).sum()),
             'baseline_bins_with_insufficient_channels':int((base_eligible<MIN_CHANNELS).sum()),
             'variants':variants,'review_channels':stable}
    (dest/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    plot_segment(name,dest,start,n,base_pos[6],base_neg[6],base_eligible,hp_pos[6],hp_neg[6],hp_eligible,masks[PRIMARY],events)
    print(name, 'primary',variants[PRIMARY]['flagged_duration_s'],'s;',
          'HP/MAD flagged',variants[PRIMARY]['methods']['hp300_mad']['flagged'],'/',len(events['hp300_mad']),flush=True)
    return summary


def plot_segment(name,dest,start,n,bp,bn,be,hp,hn,he,mask,events):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,1,figsize=(12,8),sharex=True)
    bt=(start+np.arange(len(be))*100)/FS
    ht=(start+np.arange(len(he))*10)/FS
    axes[0].plot(bt,ratio(np.maximum(bp,bn),be),lw=1,color='#aa783c')
    axes[0].set_ylabel('Baseline quorum')
    axes[1].plot(ht,ratio(np.maximum(hp,hn),he),lw=1,color='#755389')
    axes[1].set_ylabel('Broadband quorum')
    for ax in axes[:2]:
        ax.axhline(.5,color='#8b1e1e',ls='--',lw=.8,label='Primary: 50%')
        ax.set_ylim(0,1.05); ax.legend(fontsize=8,loc='upper right')
    for method,label,color in [('ma200_mad','MA200/MAD','#386f95'),('hp300_mad','HP300/MAD','#8d637f')]:
        a=events[method]; bins=(a[:,1].astype(int)-start)//100
        counts=np.bincount(bins,minlength=n//100)
        axes[2].plot(bt,counts,label=label,color=color,lw=1)
    axes[2].set_ylabel('Candidates / 10 ms'); axes[2].legend(fontsize=8)
    axes[2].set_xlabel('Nominal recording time (s, 10 kHz)')
    for ax in axes:
        for a,b in intervals(mask): ax.axvspan((start+a)/FS,(start+b)/FS,color='#dfa33b',alpha=.22)
        ax.grid(alpha=.15)
    fig.suptitle(name+' — shaded = primary shared-disturbance review flag; not proven artifact',fontsize=13)
    fig.tight_layout(rect=(0,0,1,.96)); fig.savefig(dest/'evidence.png',dpi=140); plt.close(fig)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--comparison',type=Path,default=Path('results/controlled_comparison'))
    ap.add_argument('--output',type=Path,default=Path('results/shared_artifact_review'))
    args=ap.parse_args()
    if args.output.exists() and any(args.output.iterdir()): ap.error('output must be empty')
    args.output.mkdir(parents=True,exist_ok=True)
    previous=json.loads((args.comparison/'summary.json').read_text())
    prior_config=json.loads((args.comparison/'config.json').read_text())
    config={'primary':PRIMARY,'sigma_multipliers':SIGMAS,'exploratory_baseline_multipliers':BASE_SIGMAS,
            'exploratory_baseline_variant':'b3_h6 uses baseline 3x and broadband 6x; introduced after the initial 6x baseline rule missed reviewed transitions. Not independent validation.','quorum_fractions':FRACTIONS,'guards_ms':GUARDS,
            'minimum_eligible_channels':MIN_CHANNELS,'nominal_fs_hz':FS,
            'baseline':'Differences of adjacent 10 ms means of MA200 baseline; per-channel temporal MAD scale with across-channel median floor; same-sign quorum.',
            'broadband':'Positive or negative HP300 excursion in a 1 ms bin, normalized by existing masked HP300/MAD scale and median floor; same-sign quorum.',
            'exposure':'Common-support and per-channel flat guards from the prior comparison, recomputed exactly; shared flags annotated afterwards without threshold refitting.',
            'interpretation':'Exploratory review flags, not false-positive labels or validated automatic deletion. Population activity may also be shared.',
            'experimental_context':prior_config['experimental_context'],
            'comparison_directory':str(args.comparison.resolve()),'python':sys.executable,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'selection':'The original primary and 18-variant grid were set before the first run. Nine baseline-only 3x variants were added after inspecting misses; all results remain exploratory.',
            'limits':['No biological ground truth or causal attribution.',
                      'Not a full-recording streaming detector; first baseline bin has no predecessor in the saved segment.',
                      'No threshold re-estimation or detection rerun after flagging; original thresholds can remain artifact-influenced.',
                      'Large true neural population events could be flagged; genuine spikes during flagged time are not recovered.',
                      'Missing quorum evidence with fewer than 1024 eligible channels is unknown, not proof of clean data.']}
    (args.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    summaries={name:evaluate_segment(name,s,args.comparison,args.output) for name,s in previous.items()}
    (args.output/'summary.json').write_text(json.dumps(summaries,indent=2,allow_nan=False)+'\n')


if __name__=='__main__': main()
