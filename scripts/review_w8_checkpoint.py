"""W8 focused curation evidence; original labels and runs remain read-only."""
import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from review_pilot_round1 import sha,write_csv,RAW_SHA,selection
from review_pilot_round2 import cross_lags,features,pca_projection

TARGETS=[32,33,6,10,0,1,2,24,44,46,48]
PAIRS=[(32,29),(33,31),(32,33),(6,5),(6,3),(10,11),(0,1),(0,2),(1,2),(24,25),(44,43),(44,45),(46,47),(48,45)]


def run(output):
    output=output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'results/extra4_shank0'):
        raise ValueError('Fresh local result directory required')
    folders={label:ROOT/'results/extra4_shank0'/name for label,name in [('control','w7b-control01'),('exclude248','w7b-exclude248-01')]}
    manifests={label:json.loads((folder/'output-manifest.json').read_text()) for label,folder in folders.items()}
    for label,folder in folders.items():
        for name,digest in manifests[label].items():assert sha(folder/name)==digest
    prior=ROOT/'results/extra4_shank0/w7b-review01'
    for name,digest in json.loads((prior/'report-manifest.json').read_text()).items():assert sha(prior/name)==digest
    binary=ROOT/'data/extra4_shank0_float32.bin';assert sha(binary)==RAW_SHA
    raw=np.memmap(binary,mode='r',dtype='<f4',shape=(3000000,512))
    output.mkdir(parents=True)
    from kilosort.CCG import compute_CCG,CCG_metrics
    label_rows=[]
    for label,folder in folders.items():
        src=folder/'kilosort4'
        times=np.load(src/'spike_times.npy').ravel();clusters=np.load(src/'spike_clusters.npy').ravel()
        with (src/'cluster_KSLabel.tsv').open() as f:labels={int(r['cluster_id']):r['KSLabel'] for r in csv.DictReader(f,delimiter='\t')}
        for cid in np.unique(clusters):
            t=times[clusters==cid]/10000
            R=Q=None
            eligible=len(t)>10 and np.ptp(t)>0
            if eligible:
                K,T=compute_CCG(t,t,tbin=.001,nbins=500)
                R,Q,_=CCG_metrics(t,t,K,T,nbins=500,tbin=.001)
                R,Q=float(R),float(Q)
            passed=eligible and R<.2 and Q<.2
            assert ('good' if passed else 'mua')==labels[int(cid)]
            label_rows.append(dict(run=label,cluster_id=int(cid),events=len(t),eligible=eligible,R=R,Q=Q,
                R_pass=bool(eligible and R<.2),Q_pass=bool(eligible and Q<.2),automated_label=labels[int(cid)]))
    write_csv(output/'label_criteria.csv',label_rows)
    src=folders['exclude248']/'kilosort4'
    load=lambda n:np.load(src/(n+'.npy'),allow_pickle=False)
    times,clusters,amp=[load(n).ravel() for n in ['spike_times','spike_clusters','amplitudes']]
    templates,pos,pcs,pc_indices=[load(n) for n in ['templates','channel_positions','pc_features','pc_feature_ind']]
    chanmap=load('channel_map').ravel();peaks=np.ptp(templates,axis=1).argmax(1)
    # pc_feature_ind indexes the active channel array, not original binary columns.
    pc_binary=chanmap[pc_indices]
    rel=np.arange(-100,101);central=(rel>=-20)&(rel<=40)
    selections=[];pair_rows=[];pages=[]
    cached={}

    def waves(cid,channels):
        events=np.flatnonzero((clusters==cid)&(times>=100)&(times<2999900))
        chosen=selection(events[np.argsort(times[events],kind='stable')],256)
        key=(cid,tuple(channels))
        if key not in cached:
            a=np.asarray(raw[times[chosen,None]+rel[None,:]][:,:,channels],dtype=np.float32)*1e6
            a-=np.median(a[:,:70],axis=1)[:,None,:]
            cached[key]=(a,chosen)
        return cached[key]

    for ca,cb in PAIRS:
        key=f'pair_{ca}_{cb}'
        d=np.minimum(np.linalg.norm(pos-pos[peaks[ca]],axis=1),np.linalg.norm(pos-pos[peaks[cb]],axis=1))
        channels=chanmap[np.argsort(d,kind='stable')[:12]]
        wa,sa=waves(ca,channels);wb,sb=waves(cb,channels)
        ma,mb=wa.mean(axis=0),wb.mean(axis=0)
        ia,ib=np.flatnonzero(clusters==ca),np.flatnonzero(clusters==cb)
        ta,tb=np.sort(times[ia]),np.sort(times[ib]);lags=cross_lags(ta,tb)
        common=np.intersect1d(pc_binary[ca],pc_binary[cb])
        if len(common):
            _,fa=features(pcs,pc_binary,clusters,ca,common);_,fb=features(pcs,pc_binary,clusters,cb,common)
            projected,center,axes,var=pca_projection([fa,fb])
        else:
            projected=[np.empty((len(ia),0)),np.empty((len(ib),0))];center=axes=var=np.array([])
        np.savez_compressed(output/(key+'.npz'),channels=channels,relative_samples=rel,
            waves_a=wa,waves_b=wb,selected_a=sa,selected_b=sb,
            event_indices_a=ia,event_indices_b=ib,common_binary_channels=common,projection_a=projected[0],projection_b=projected[1],
            center=center,axes=axes,cross_lags=lags)
        for cid,ids in [(ca,sa),(cb,sb)]:
            selections.extend(dict(pair=key,cluster_id=cid,event_index=int(i),sample=int(times[i])) for i in ids)
        pair_rows.append(dict(cluster_a=ca,cluster_b=cb,events_a=len(ia),events_b=len(ib),
            peak_a_binary=int(chanmap[peaks[ca]]),peak_b_binary=int(chanmap[peaks[cb]]),
            raw_correlation=float(np.corrcoef(ma[central].ravel(),mb[central].ravel())[0,1]),
            shared_feature_channels=len(common),pca_variance=float(var.sum()),
            cross_pairs_abs_le2=int(np.sum(abs(lags)<=2)),cross_pairs_abs_lt10=int(np.sum(abs(lags)<10)),
            cross_pairs_abs_lt20=int(np.sum(abs(lags)<20)),hypothetical_union_isi_lt20=int(np.sum(np.diff(np.sort(np.r_[ta,tb]))<20))))
        fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        gap=max(float(np.max(np.ptp(np.stack([ma,mb])[:,:,:4],axis=1)))*1.1,1)
        for k,ch in enumerate(channels[:4]):
            ax[0,0].plot(rel/10,ma[:,k]+k*gap,color='C0',label=str(ca) if k==0 else None)
            ax[0,0].plot(rel/10,mb[:,k]+k*gap,color='C1',label=str(cb) if k==0 else None)
        ax[0,0].set(title=f'Raw means b{channels[:4].tolist()}; offsets {gap:.1f}',xlabel='Nominal ms',ylabel='Centered input x1e6');ax[0,0].legend()
        ax[0,1].hist(lags/10,bins=np.arange(-50.5,51,1));ax[0,1].set(title='All cross-event pairs; no chance correction',xlabel=f'{cb} minus {ca}, nominal ms')
        for cid,ids,pr in [(ca,ia,projected[0]),(cb,ib,projected[1])]:
            chosen=selection(np.arange(len(ids)),1500)
            if pr.shape[1]==2:ax[1,0].scatter(pr[chosen,0],pr[chosen,1],s=5,alpha=.4,label=str(cid))
            ax[1,1].scatter(times[ids]/10000,amp[ids],s=4,alpha=.4,label=str(cid))
        ax[1,0].set(title=f'{len(common)} common physical channels, balanced PCA ({var.sum():.0%})');
        if len(common):ax[1,0].legend()
        ax[1,1].set(xlabel='Nominal seconds',ylabel='Sorter feature amplitude');ax[1,1].legend()
        fig.suptitle(f'Exclusion-run clusters {ca} / {cb}: bounded isolation review; no merge applied')
        fig.savefig(output/(key+'.png'),dpi=125);plt.close(fig);pages.append(key+'.png')
        cached.clear()
        print(key+' complete',flush=True)
    write_csv(output/'pair_metrics.csv',pair_rows);write_csv(output/'raw_selection.csv',selections)
    # Quarter means for the four promising candidates are independent selections per quarter.
    quarter_rows=[]
    for cid in [32,33,6,10]:
        channels=chanmap[np.argsort(np.linalg.norm(pos-pos[peaks[cid]],axis=1),kind='stable')[:8]]
        pooled,chosen=waves(cid,channels);reference=pooled.mean(axis=0)
        means=[];saved_ids=[]
        for q in range(4):
            ids=np.flatnonzero((clusters==cid)&(times>=max(100,q*750000))&(times<min(2999900,(q+1)*750000)))
            ids=selection(ids,128)
            w=np.asarray(raw[times[ids,None]+rel[None,:]][:,:,channels],dtype=np.float32)*1e6
            w-=np.median(w[:,:70],axis=1)[:,None,:]
            mean=w.mean(axis=0);means.append(mean);saved_ids.append(ids)
            quarter_rows.append(dict(cluster_id=cid,quarter=q,selected=len(ids),raw_correlation_to_pooled=float(np.corrcoef(mean[central].ravel(),reference[central].ravel())[0,1])))
        np.savez_compressed(output/f'cluster_{cid}_quarters.npz',channels=channels,means=np.stack(means),reference=reference,
            **{f'event_indices_{q}':ids for q,ids in enumerate(saved_ids)},reference_events=chosen)
        fig,ax=plt.subplots(2,2,figsize=(11,7),layout='constrained')
        for j,axis in enumerate(ax.ravel()):
            for q,mean in enumerate(means):axis.plot(rel/10,mean[:,j],label=f'Quarter {q+1}')
            axis.set(title=f'Raw b{channels[j]}',xlabel='Nominal ms',ylabel='Centered input x1e6')
        ax[0,0].legend();fig.suptitle(f'Exclusion cluster {cid}: time stability, original data unchanged')
        name=f'cluster_{cid}_quarters.png';fig.savefig(output/name,dpi=125);plt.close(fig);pages.append(name)
        cached.clear()
    write_csv(output/'quarter_metrics.csv',quarter_rows)
    for label,folder in folders.items():
        for name,digest in manifests[label].items():assert sha(folder/name)==digest
    assert sha(binary)==RAW_SHA
    summary=dict(schema='w8-curation-checkpoint-v1',script_sha256=sha(Path(__file__)),raw_sha256=RAW_SHA,
        sorter_ccg_source_sha256=sha(ROOT/'.venv/Lib/site-packages/kilosort/CCG.py'),
        run_manifests={label:sha(folder/'output-manifest.json') for label,folder in folders.items()},
        w7b_report_manifest_sha256=sha(prior/'report-manifest.json'),
        pairs=PAIRS,targets=TARGETS,label_criteria_all117_reproduced=True,raw_pair_windows=len(selections),
        annotations_changed=False,labels_changed=False,merges_applied=0,
        caveat='PCA views are descriptive, not formal isolation metrics; correlations and timing are not neuron ground truth. Unreviewed units are not rejected.')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>W8 focused curation checkpoint</title><style>body{font:16px system-ui;max-width:1250px;margin:30px auto}img{width:100%}</style><h1>W8 focused curation checkpoint</h1><p>Exclusion-run IDs. AI-assisted diagnostic review; no original labels modified or human acceptance implied.</p><p><a href="label_criteria.csv">Exact automatic-label criteria</a> | <a href="pair_metrics.csv">Pair metrics</a> | <a href="quarter_metrics.csv">Quarter stability</a></p>'+''.join(f'<h2>{name}</h2><img src="{name}">' for name in pages),encoding='utf-8')
    (output/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in output.iterdir() if p.is_file()},indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    run(p.parse_args().output)
