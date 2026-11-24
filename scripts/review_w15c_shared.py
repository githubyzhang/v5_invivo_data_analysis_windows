"""Fixed source-flat episodes, event exposure, raw support and saved preprocessing."""
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_sorting import ROOT,read,save,sha,verify_manifest
from review_sorting_baseline import table


def intervals(mask):
    edges=np.diff(np.r_[False,mask,False].astype(np.int8))
    return np.column_stack((np.flatnonzero(edges==1),np.flatnonzero(edges==-1)))


def masks_from_flat(flat,N):
    delta=np.zeros(N+1,dtype=np.int32)
    for a,b in flat[:,3:5].astype(int):delta[a]+=1;delta[b]-=1
    concurrency=delta[:-1].cumsum();core=concurrency>=256;expanded=core.copy()
    for a,b in intervals(core):expanded[max(0,a-500):min(N,b+500)]=True
    return concurrency,dict(core=core,shoulder=expanded & ~core,away=~expanded)


def run(control,exclusion,output):
    output=output.resolve();assert not output.exists() and output.is_relative_to(ROOT/'results')
    reports=[control.resolve(),exclusion.resolve()];runs=[ROOT/read(p/'summary.json')['run_path'] for p in reports]
    configs=[read(p/'config.json') for p in runs];c=configs[0];N=c['samples'];fs=c['nominal_fs_hz']
    assert c['shank_zero_based']==3 and configs[1]['excluded_binary_channels']==[259]
    for p,r in zip(reports,runs):verify_manifest(p/'report-manifest.json');verify_manifest(r/'output-manifest.json')
    quality=ROOT/'results/extra4/w14-quality01';verify_manifest(quality/'manifest.json')
    flat=np.load(quality/'intervals.npz')['flat'];flat=flat[flat[:,0]==3]
    concurrency,masks=masks_from_flat(flat,N);spans=intervals(masks['core'])
    output.mkdir(parents=True);np.savez_compressed(output/'fixed_masks.npz',flat_concurrency=concurrency,core_intervals=spans,**masks)
    raw=np.memmap(ROOT/c['binary_path'],mode='r',dtype='<f4',shape=(N,512))
    geometry=np.genfromtxt(ROOT/c['mapping_path'],delimiter=',',names=True,dtype=int);positions=np.column_stack((geometry['x_um'],geometry['y_um']))
    common=np.delete(np.arange(512),259);datasets=[];rows=[];runrows=[];episode_rows=[]
    for label,report,r in zip(['control','exclusion'],reports,runs):
        events=np.load(report/'event_annotations.npz');t=events['sample_index'];cl=events['cluster_id']
        inventory={int(x['cluster_id']):x for x in csv.DictReader((report/'clusters.csv').open())}
        # Saved preprocessing retains original binary width; excluded columns are
        # unwritten zeros. Batch-padded tail is not source data and is never analyzed.
        from kilosort.io import load_ops
        import torch
        ops=load_ops(r/'kilosort4/ops.npy',device=torch.device('cpu'))
        saved_samples=ops['batch_size']*ops['Nbatches'];path=r/'kilosort4/temp_wh.dat'
        assert path.stat().st_size==saved_samples*512*2 and saved_samples>=N
        pre=np.memmap(path,mode='r',dtype='<i2',shape=(saved_samples,512))
        active=np.load(r/'kilosort4/channel_map.npy').ravel()
        if label=='exclusion':assert not np.any(pre[:N,259])
        for cid in np.unique(cl):
            idx=np.flatnonzero(cl==cid);peak=int(inventory[cid]['peak_binary'])
            channels=common[np.argsort(np.linalg.norm(positions[common]-positions[peak],axis=1),kind='stable')[:8]]
            payload=dict(binary_channels=channels,global_channels=geometry['original_channel_id'][channels]);means={};selected_counts={}
            for zone,mask in masks.items():
                complete=idx[mask[t[idx]] & (t[idx]>=100)&(t[idx]<N-100)]
                chosen=complete[np.unique(np.linspace(0,len(complete)-1,min(64,len(complete))).astype(int))] if len(complete) else complete
                if len(chosen):
                    waves=np.asarray(raw[t[chosen,None]+np.arange(-100,101)[None,:]][:,:,channels],dtype=np.float32)*1e6
                    waves-=np.median(waves[:,:70],axis=1)[:,None,:];mean=waves.mean(axis=0)
                else:mean=np.full((201,len(channels)),np.nan)
                means[zone]=mean;selected_counts[zone]=len(chosen)
                payload[zone+'_event_indices']=chosen;payload[zone+'_mean']=mean
            np.savez_compressed(output/f'{label}_c{cid}_zone_means.npz',**payload)
            x,y=[means[z][80:141].ravel() for z in ['core','away']]
            corr=float(np.corrcoef(x,y)[0,1]) if np.isfinite(x).all() and np.isfinite(y).all() and x.std()>0 and y.std()>0 else None
            row=dict(run=label,cluster_id=int(cid),automated_label=inventory[cid]['automated_label'],events=len(idx),peak_binary=peak,core_away_raw_correlation=corr)
            for zone,mask in masks.items():
                count=int(mask[t[idx]].sum());exposure=int(mask.sum())
                row.update({zone+'_events':count,zone+'_exposure_samples':exposure,zone+'_nominal_rate':count*fs/exposure if exposure else None,zone+'_raw_windows':selected_counts[zone]})
            rows.append(row)
        # All episodes retained, even those not selected for detailed plots.
        for number,(a,b) in enumerate(spans):
            episode_rows.append(dict(run=label,episode=number,start_sample=int(a),stop_sample=int(b),events=int(((t>=a)&(t<b)).sum()),peak_flat_channels=int(concurrency[a:b].max())))
        runrows.append(dict(run=label,events=len(t),saved_samples=int(saved_samples),original_samples=N,preprocessed_sha256=sha(path),active_channels=len(active),**{z+'_events':int(m[t].sum()) for z,m in masks.items()}))
        datasets.append((t,cl,pre))
    table(output/'cluster_zones.csv',rows);table(output/'episodes.csv',episode_rows);table(output/'run_zones.csv',runrows)
    # Longest two source episodes plus two most event-rich control episodes.
    longest=np.argsort(-(spans[:,1]-spans[:,0]),kind='stable')[:2]
    control_counts=np.array([r['events'] for r in episode_rows if r['run']=='control'])
    richest=np.argsort(-control_counts,kind='stable')[:2]
    chosen_episodes=sorted(set(longest.tolist()+richest.tolist()));pages=[];excerpt_rows=[]
    for number in chosen_episodes:
        a,b=spans[number];start=max(0,int(a)-2500);stop=min(N,int(b)+2500)
        channels=np.array([259,255,258,403,486]);excerpt=np.array(raw[start:stop,channels]);time=np.arange(start,stop)/fs
        payload=dict(start_sample=start,stop_sample=stop,binary_channels=channels,raw=excerpt)
        fig,axes=plt.subplots(4,1,figsize=(13,10),layout='constrained',sharex=True)
        centered=excerpt*1e6;centered-=np.median(centered[:100],axis=0)
        for j,ch in enumerate(channels):axes[0].plot(time,centered[:,j],lw=.6,label=f'b{ch}')
        axes[0].legend(ncol=5);axes[0].set(ylabel='Centered input x1e6',title=f'Source episode {number}; raw target/neighbor and remaining concern channels')
        axes[1].plot(time,concurrency[start:stop]);axes[1].axhline(256,color='gray',ls='--');axes[1].set(ylabel='Exactly flat channels')
        for label,(t,cl,pre) in zip(['control','exclusion'],datasets):
            sample=np.asarray(pre[start:stop][:,common],dtype=np.float32)/200
            p99=np.percentile(np.abs(sample),99,axis=1);payload[label+'_preprocessed_p99']=p99
            payload[label+'_preprocessed_channels']=np.array(pre[start:stop,channels])
            axes[2].plot(time,p99,label=label,lw=.7)
            sel=(t>=start)&(t<stop);payload[label+'_event_indices']=np.flatnonzero(sel)
            axes[3].scatter(t[sel]/fs,cl[sel],s=4,label=label,alpha=.65)
        axes[2].set(ylabel='Saved preproc |x| p99\ncommon 511 channels');axes[2].legend()
        axes[3].set(ylabel='Run-specific cluster ID',xlabel='Original nominal seconds');axes[3].legend()
        for ax in axes:ax.axvspan(a/fs,b/fs,color='red',alpha=.1)
        name=f'episode_{number}';np.savez_compressed(output/(name+'.npz'),**payload)
        fig.savefig(output/(name+'.png'),dpi=110);plt.close(fig);pages.append(name+'.png')
        excerpt_rows.append(dict(episode=number,start_sample=start,stop_sample=stop,core_start_sample=int(a),core_stop_sample=int(b)))
    table(output/'excerpt_selection.csv',excerpt_rows)
    # Per-cluster exposure-adjusted rates and bounded raw support, outside vs inside.
    for label in ['control','exclusion']:
        r=[x for x in rows if x['run']==label]
        fig,ax=plt.subplots(2,1,figsize=(13,7),layout='constrained')
        ids=[x['cluster_id'] for x in r]
        for zone in masks:ax[0].plot(ids,[x[zone+'_nominal_rate'] for x in r],'.-',label=zone)
        ax[0].set_yscale('symlog',linthresh=1)
        ax[0].set(ylabel='Events / nominal second',title=f'{label}: full-exposure rates by fixed source zones');ax[0].legend()
        ax[1].bar(ids,[x['core_events']/x['events'] for x in r]);ax[1].axhline(masks['core'].mean(),color='red',ls='--',label='Core time fraction')
        ax[1].set(xlabel='Cluster ID',ylabel='Fraction of events in core');ax[1].legend()
        name=label+'_zone_overview.png';fig.savefig(output/name,dpi=110);plt.close(fig);pages.append(name)
    summary=dict(state='diagnostic_no_mask_adopted',source_shank=3,source_population=512,core_definition='At least 256 of original 512 channels in W14 exact-flat intervals; same mask for both sorts',shoulder_definition='Union of +/-500-sample expansion around core, excluding core; away is complement',exposure_samples={z:int(m.sum()) for z,m in masks.items()},episodes=len(spans),selected_episodes=chosen_episodes,runs=runrows,report_manifests={str(p.relative_to(ROOT)):sha(p/'report-manifest.json') for p in reports},quality_manifest_sha256=sha(quality/'manifest.json'),script_sha256=sha(Path(__file__)),source_binary_sha256=sha(ROOT/c['binary_path']),preprocessed_interpretation='Saved int16 / 200, whitened/filtered/drift-corrected visualization copy, not calibrated voltage or exact float sorter input. Original width 512; omitted channel is zero. Batch tail excluded. No preprocessing replay or clipping-proof claim.',raw_convention='Up to 64 complete chronological-rank events per zone, 8 nearest common channels; x1e6, baseline offsets -100..-31; correlations -20..40; zone membership determined by event center, not whole excerpt')
    save(output/'summary.json',summary)
    html='<html><meta charset="utf-8"><title>W15C shared episodes</title><style>body{font:16px system-ui;max-width:1400px;margin:30px auto}img{width:100%}</style><h1>W15C: shared source-flat episodes</h1><p>Fixed original-512-channel population in both conditions. Diagnostic zones, not an adopted mask. Core >=256 flat channels; shoulder +/-50 nominal ms; away outside both. Unavailable generic shared-signal warnings remain unavailable.</p><p><a href="cluster_zones.csv">Every cluster by zone</a> | <a href="episodes.csv">All episodes</a> | <a href="summary.json">Methods and provenance</a> | <a href="../w15c-comparison01/index.html">Matched comparison</a></p><p>Raw x1e6 is numerical scaling. Saved preprocessing is quantized int16/200 on common active channels, not calibrated voltage. Raster IDs belong to separate runs.</p>'
    html+=''.join(f'<img src="{name}">' for name in pages);(output/'index.html').write_text(html,encoding='utf-8')
    save(output/'report-manifest.json',{p.name:sha(p) for p in output.iterdir()});print(summary)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['control','exclusion','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.control,a.exclusion,a.output)
