"""W11 annotation/exposure sensitivity; all scenarios are proposed diagnostics."""
import argparse
import json
from pathlib import Path
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from review_w9_good import ROOT,RUN,rows,verify
from review_pilot_round1 import sha,write_csv,RAW_SHA,selection

N=3000000
W7A=ROOT/'results/extra4_shank0/pilot01-w7a-reviewed'
W10=ROOT/'results/extra4_shank0/w10-population-review01'
CANDIDATES=[1,5,6,10,32,33,38,39,47,49,50]


def intervals(mask):
    edges=np.diff(np.r_[False,mask,False].astype(np.int8))
    return np.column_stack((np.flatnonzero(edges==1),np.flatnonzero(edges==-1)))


def mask_from(spans):
    mask=np.zeros(N,bool)
    for start,stop in spans:mask[int(start):int(stop)]=True
    return mask


def run(output):
    output=output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'results/extra4_shank0'):
        raise ValueError('Fresh review directory required')
    for folder,manifest in [(RUN,'output-manifest.json'),(W7A,'report-manifest.json'),(W10,'report-manifest.json')]:verify(folder,manifest)
    binary=ROOT/'data/extra4_shank0_float32.bin';assert sha(binary)==RAW_SHA
    raw=np.memmap(binary,mode='r',dtype='<f4',shape=(N,512))
    src=RUN/'kilosort4';load=lambda n:np.load(src/(n+'.npy'),allow_pickle=False)
    t,cl=load('spike_times').ravel(),load('spike_clusters').ravel()
    cmap=load('channel_map').ravel();pos=load('channel_positions');peaks=np.ptp(load('templates'),axis=1).argmax(1)
    assert len(cmap)==511 and 248 not in cmap
    ledger=ROOT/'docs/reviews/2026-11-23-w10-curation-proposals.csv'
    proposed=[int(r['cluster_id']) for r in rows(ledger) if r['run']=='w7b-exclude248-01' and r['recommendation']=='recommend_putative_single_unit']
    assert sorted(proposed)==CANDIDATES
    guards=rows(W7A/'guard_intervals.csv');flat=rows(W7A/'flat_runs.csv')
    spans={int(ch):np.array([[int(r['start']),int(r['stop'])] for r in guards if int(r['binary_channel'])==ch],dtype=int).reshape(-1,2) for ch in range(512)}
    def counts(table):
        delta=np.zeros(N+1,dtype=np.int32)
        for r in table:
            if int(r['binary_channel']) in cmap:delta[int(r['start'])]+=1;delta[int(r['stop'])]-=1
        return np.cumsum(delta[:-1])
    guard_count=counts(guards);flat_count=counts(flat)
    sidecar=ROOT/'results/custom_detector/kilosort_pilot01_quality_windows01/external_quality.h5'
    assert sha(sidecar)=='df0289595e71f44b14a7755d6beea3a2b99a500cde3bec81fe8bc82d9d149d8f'
    with h5py.File(sidecar,'r') as f:
        global_masks={n:mask_from(f['intervals/'+n][:]) for n in ['broad_warning','tight_warning','broad_available','tight_available']}
        assert len(f['intervals/shared_available'])==0
    global_masks.update(boundary=(np.arange(N)<100)|(np.arange(N)>=N-100),
        active_guard_any=guard_count>0,active_guard_ge50=guard_count>=256,
        active_flat_ge50=flat_count>=256,excluded248_guard=mask_from(spans[248]))
    output.mkdir(parents=True)
    global_rows=[dict(annotation=name,samples=int(m.sum()),nominal_seconds=float(m.sum()/10000),physical_seconds=float(m.sum()/10080),events=int(m[t].sum())) for name,m in global_masks.items()]
    write_csv(output/'global_coverage.csv',global_rows)
    np.savez_compressed(output/'global_intervals.npz',**{k:intervals(m) for k,m in global_masks.items()},active_guard_count=guard_count,active_flat_count=flat_count)
    flags={name:m[t] for name,m in global_masks.items()}
    for name in ['peak_guard','support8_any_guard','support8_all_guard','peak_window_touch_guard']:flags[name]=np.zeros(len(t),bool)
    sensitivity=[];unit_rows=[];saved_intervals={};channels_by_unit={}
    interior=~global_masks['boundary'];global_saved={}
    for cid in np.unique(cl):
        ids=np.flatnonzero(cl==cid);ch=int(cmap[peaks[cid]])
        support=cmap[np.argsort(np.linalg.norm(pos-pos[peaks[cid]],axis=1),kind='stable')[:8]]
        channels_by_unit[str(cid)]=support.tolist()
        peak=mask_from(spans[ch]);union=np.zeros(N,bool);intersection=np.ones(N,bool)
        for c in support:
            m=mask_from(spans[int(c)]);union|=m;intersection&=m
        touch=mask_from([(max(0,int(a)-100),min(N,int(b)+100)) for a,b in spans[ch]])
        for name,m in [('peak_guard',peak),('support8_any_guard',union),('support8_all_guard',intersection),('peak_window_touch_guard',touch)]:
            flags[name][ids]=m[t[ids]];saved_intervals[f'c{cid}_{name}']=intervals(m)
        scenarios=dict(full_recording=np.ones(N,bool),interior_only=interior,
            interior_without_broad=interior&~global_masks['broad_warning'],
            interior_without_peak_guard=interior&~peak,
            interior_without_peak_or_broad=interior&~(peak|global_masks['broad_warning']),
            interior_without_shared_guard50=interior&~global_masks['active_guard_ge50'],
            interior_without_shared_flat50=interior&~global_masks['active_flat_ge50'],
            interior_without_support8_any=interior&~union,
            interior_without_support8_all=interior&~intersection,
            interior_without_peak_window_touch=interior&~touch,
            interior_broad_assessed_only=interior&global_masks['broad_available'])
        baseline=len(ids)/300
        for name,keep in scenarios.items():
            count=int(keep[t[ids]].sum());exposure=int(keep.sum())
            rate=count/(exposure/10000) if exposure else None
            sensitivity.append(dict(cluster_id=int(cid),proposed_candidate=int(cid) in CANDIDATES,scenario=name,
                original_events=len(ids),retained_events=count,removed_events=len(ids)-count,exposure_samples=exposure,
                nominal_seconds=exposure/10000,physical_seconds=exposure/10080,nominal_rate=rate,
                physical_rate=count/(exposure/10080) if exposure else None,relative_rate_change=rate/baseline-1 if rate is not None else None))
            saved_intervals[f'c{cid}_keep_{name}']=intervals(keep)
        unit_rows.append(dict(cluster_id=int(cid),proposed_candidate=int(cid) in CANDIDATES,events=len(ids),peak_binary=ch,
            **{name:int(f[ids].sum()) for name,f in flags.items()}))
    write_csv(output/'unit_annotations.csv',unit_rows);write_csv(output/'sensitivity.csv',sensitivity)
    np.savez_compressed(output/'unit_intervals.npz',**saved_intervals)
    np.savez_compressed(output/'event_annotations.npz',event_indices=np.arange(len(t)),sample_index=t,cluster_id=cl,**flags)
    (output/'support_channels.json').write_text(json.dumps(channels_by_unit,indent=2)+'\n')
    # Carry W10 diagnostic groups forward without making them curated groups.
    contexts=[]
    for cid in [12,29,31,40,45]:
        with np.load(W10/f'population_{cid}.npz') as z:
            for group in z['groups']:
                ids=z[f'group_{group}_events']
                contexts.append(dict(context=f'population_{cid}_group{group}',events=len(ids),**{name:int(f[ids].sum()) for name,f in flags.items()}))
    with np.load(W10/'overlap_43_44.npz') as z:
        for letter,index in [('a',0),('b',1)]:
            ids=z['ids_'+letter][z['matches'][:,index]]
            contexts.append(dict(context=f'43_44_matched_{letter}',events=len(ids),**{name:int(f[ids].sum()) for name,f in flags.items()}))
    write_csv(output/'w10_cohort_annotations.csv',contexts)
    boundary_ids=np.flatnonzero(flags['boundary'])
    write_csv(output/'boundary_events.csv',[dict(event_index=int(i),sample=int(t[i]),cluster_id=int(cl[i]),proposed_candidate=int(cl[i]) in CANDIDATES) for i in boundary_ids])
    pages=[]
    fig,ax=plt.subplots(2,1,figsize=(12,8),layout='constrained')
    ax[0].plot(np.arange(N)/10000,guard_count,label='Padded guard channels');ax[0].plot(np.arange(N)/10000,flat_count,label='Exact-flat channels');ax[0].legend();ax[0].set(xlabel='Nominal seconds',ylabel='Active channels',title='511 active channels only; b248 excluded')
    for name in ['interior_only','interior_without_peak_guard','interior_without_peak_or_broad','interior_without_support8_any']:
        subset=[r for r in sensitivity if r['scenario']==name and r['proposed_candidate']]
        ax[1].plot([r['cluster_id'] for r in subset],[100*r['relative_rate_change'] for r in subset],marker='.',label=name)
    ax[1].legend(fontsize=8);ax[1].set(xlabel='Without-248 candidate ID',ylabel='Rate change versus full recording (%)',title='Scenario counts and matching time denominator; no policy adopted')
    fig.savefig(output/'exposure_sensitivity.png',dpi=120);plt.close(fig);pages.append('exposure_sensitivity.png')
    # Boundary evidence uses available samples only, never manufactured pre-recording data.
    fig,ax=plt.subplots(len(boundary_ids),1,figsize=(12,2.5*len(boundary_ids)),squeeze=False,layout='constrained')
    saved={}
    for k,i in enumerate(boundary_ids):
        cid=int(cl[i]);ch=int(cmap[peaks[cid]]);start=max(0,int(t[i])-100);stop=min(N,int(t[i])+101)
        wave=np.array(raw[start:stop,ch],dtype=np.float32)*1e6;saved[f'event_{i}']=wave
        ax[k,0].plot(np.arange(start,stop)/10,wave);ax[k,0].axvline(t[i]/10,color='red')
        ax[k,0].set(title=f'Without-248 {cid}, event{i}, sample{t[i]}, raw b{ch}; pre-event context unavailable',xlabel='Absolute nominal ms',ylabel='Input x1e6')
    fig.savefig(output/'boundary_events.png',dpi=110);plt.close(fig);pages.append('boundary_events.png');np.savez_compressed(output/'boundary_raw.npz',**saved)
    # Review warning/guard events in the proposed subset against unaffected event means.
    rel=np.arange(-100,101);wave_rows=[]
    affected=flags['peak_guard']|flags['broad_warning']|flags['support8_all_guard']
    for cid in CANDIDATES:
        ids=np.flatnonzero((cl==cid)&~flags['boundary']);bad=ids[affected[ids]]
        if not len(bad):continue
        good=selection(ids[~affected[ids]],128);ch=np.array(channels_by_unit[str(cid)])
        fig,ax=plt.subplots(1,2,figsize=(12,4),layout='constrained');saved={}
        for label,selected in [('flagged',bad),('comparison',good)]:
            w=np.asarray(raw[t[selected,None]+rel[None,:]][:,:,ch],dtype=np.float32)*1e6
            w-=np.median(w[:,:70],axis=1)[:,None,:]
            saved[label+'_events']=selected;saved[label+'_waves']=w
            for j in range(2):
                ax[j].plot(rel/10,w.mean(0)[:,j],label=f'{label} n={len(selected)}')
                if label=='flagged':ax[j].plot(rel/10,w[:,:,j].T,color='gray',alpha=.15,lw=.5)
                ax[j].set(title=f'Raw b{ch[j]}',xlabel='Nominal ms',ylabel='Centered input x1e6');ax[j].legend()
        name=f'candidate_{cid}_flagged.png';fig.suptitle(f'Without-248 {cid}: peak guard OR broad warning OR all8 guards; not artifact labels')
        fig.savefig(output/name,dpi=110);plt.close(fig);pages.append(name)
        np.savez_compressed(output/f'candidate_{cid}_flagged.npz',channels=ch,**saved)
        wave_rows.append(dict(cluster_id=cid,flagged_events=len(bad),comparison_events=len(good)))
    write_csv(output/'waveform_cohorts.csv',wave_rows)
    for folder,manifest in [(RUN,'output-manifest.json'),(W7A,'report-manifest.json'),(W10,'report-manifest.json')]:verify(folder,manifest)
    assert sha(binary)==RAW_SHA
    summary=dict(schema='w11-exposure-review-v1',script_sha256=sha(Path(__file__)),raw_sha256=RAW_SHA,
        inputs={str(f.relative_to(ROOT)):sha(f/m) for f,m in [(RUN,'output-manifest.json'),(W7A,'report-manifest.json'),(W10,'report-manifest.json')]},
        annotation_source_sha256=sha(sidecar),ledger_sha256=sha(ledger),candidates=CANDIDATES,scenario_count=11,
        proposed_primary='interior_only with annotation-only quality flags; pending W12 acceptance',analysis_interval=[100,N-100],
        shared_generic_signal_warning_available=False,shared50_threshold_diagnostic_only=True,original_events_or_labels_changed=False)
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>W11 quality and exposure</title><style>body{font:16px system-ui;max-width:1300px;margin:30px auto}img{width:100%}</style><h1>W11 quality / exposure sensitivity</h1><p>All scenarios are diagnostic and pending adoption. Selected without-248 IDs; original outputs unchanged. Counts and time denominators use identical half-open sample intervals. Global coincidence warnings retain their2048-channel population. Padded guards and exact flatness are separate; neither defines a validated unit-observability mask.</p><p>Proposed primary: [100,2999900) sample analysis domain with quality flags retained as annotations. This requires full +/-100-sample raw context; it is not a validated filter-settling interval. No other quality censoring recommended yet.</p>'+''.join(f'<h2>{n}</h2><img src="{n}">' for n in pages),encoding='utf-8')
    (output/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in output.iterdir() if p.is_file()},indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    run(p.parse_args().output)
