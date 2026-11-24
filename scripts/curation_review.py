"""Config-driven single-run curation evidence; no automatic scientific decisions."""
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_sorting import ROOT,read,save,sha,verify_manifest
from review_sorting_baseline import table
from review_pilot_round2 import cross_lags,features,pca_projection


def select(ids,maximum):
    return ids[np.unique(np.linspace(0,len(ids)-1,min(len(ids),maximum),dtype=int))] if len(ids) else ids


def extract(raw,t,ids,channels,maximum):
    ids=ids[(t[ids]>=100)&(t[ids]<len(raw)-100)]
    ids=select(ids[np.argsort(t[ids],kind='stable')],maximum)
    w=np.asarray(raw[t[ids,None]+np.arange(-100,101)[None,:]][:,:,channels],dtype=np.float32)*1e6
    if len(w):w-=np.median(w[:,:70],axis=1)[:,None,:]
    return ids,w


def acg(t):
    lags=cross_lags(t,t);zero=np.flatnonzero(lags==0)
    return np.delete(lags,zero[:len(t)])


def criteria(t,fs):
    from kilosort.CCG import compute_CCG,CCG_metrics
    eligible=len(t)>10 and np.ptp(t)>0
    if not eligible:return None,None,'mua'
    seconds=t/fs;K,T=compute_CCG(seconds,seconds,tbin=.001,nbins=500)
    R,Q,_=CCG_metrics(seconds,seconds,K,T,nbins=500,tbin=.001)
    return float(R),float(Q),'good' if R<.2 and Q<.2 else 'mua'


def corr(a,b):
    a=a[80:141].ravel();b=b[80:141].ravel()
    return float(np.corrcoef(a,b)[0,1]) if np.isfinite(a).all() and np.isfinite(b).all() and a.std()>0 and b.std()>0 else None


def run(shank,output):
    output=output.resolve();assert not output.exists() and output.is_relative_to(ROOT/'results')
    selected=read(ROOT/'configs/extra4_working_runs.v1.json');assert selected['state']=='user_selected'
    choice=next(x for x in selected['runs'] if x['shank_zero_based']==shank)
    runpath=ROOT/choice['run_path'];baseline=ROOT/choice['baseline_report'];c=read(runpath/'config.json')
    assert sha(runpath/'output-manifest.json')==choice['run_manifest_sha256'];verify_manifest(runpath/'output-manifest.json');verify_manifest(baseline/'report-manifest.json')
    assert sha(ROOT/c['binary_path'])==c['pinned_files'][c['binary_path']]
    src=runpath/'kilosort4';load=lambda name:np.load(src/(name+'.npy'),allow_pickle=False)
    t,cl,amp=[load(n).ravel() for n in ['spike_times','spike_clusters','amplitudes']]
    templates,pos,cmap,pcs,pci=[load(n) for n in ['templates','channel_positions','channel_map','pc_features','pc_feature_ind']];cmap=cmap.ravel();pcb=cmap[pci]
    raw=np.memmap(ROOT/c['binary_path'],mode='r',dtype='<f4',shape=(c['samples'],c['binary_channels']))
    with (baseline/'clusters.csv').open() as f:inventory={int(r['cluster_id']):r for r in csv.DictReader(f)}
    ids=np.unique(cl);assert set(ids)==set(inventory);peaks=np.ptp(templates,axis=1).argmax(1);fs=c['nominal_fs_hz'];N=c['samples'];qedges=np.linspace(0,N,5,dtype=int)
    output.mkdir(parents=True);unitrows=[];qrows=[];data={};pages=[]
    for cid in ids:
        allids=np.flatnonzero(cl==cid);times=t[allids];channels=cmap[np.argsort(np.linalg.norm(pos-pos[peaks[cid]],axis=1),kind='stable')[:8]]
        chosen,w=extract(raw,t,allids,channels,256);mean=w.mean(0) if len(w) else np.full((201,8),np.nan)
        R,Q,label=criteria(times,fs);assert label==inventory[cid]['automated_label']
        payload=dict(channels=channels,selected=chosen,waves=w,reference=mean,acg_lags=acg(times));means=[]
        for q,(a,b) in enumerate(zip(qedges[:-1],qedges[1:])):
            qi,qw=extract(raw,t,allids[(times>=a)&(times<b)],channels,128)
            qm=qw.mean(0) if len(qw) else np.full_like(mean,np.nan);means.append(qm);payload[f'quarter_events_{q}']=qi
            qrows.append(dict(cluster_id=int(cid),quarter=q+1,events=int(((times>=a)&(times<b)).sum()),selected=len(qi),raw_correlation_to_pooled=corr(qm,mean) if len(qi)>1 else None))
        payload['means']=np.array(means);np.savez_compressed(output/f'unit_{cid}.npz',**payload);data[cid]=payload
        unitrows.append(dict(inventory[cid],R=R,Q=Q,complete_events=int(((times>=100)&(times<N-100)).sum()),selected=len(chosen)))
    table(output/'unit_metrics.csv',unitrows);table(output/'quarter_metrics.csv',qrows)
    for start in range(0,len(ids),6):
        block=ids[start:start+6];fig,axes=plt.subplots(len(block),3,figsize=(15,3*len(block)),squeeze=False,layout='constrained')
        for row,cid in enumerate(block):
            d=data[cid];idx=np.flatnonzero(cl==cid);r=next(x for x in unitrows if int(x['cluster_id'])==cid)
            if len(d['waves']):axes[row,0].plot(np.arange(-100,101)/fs*1000,d['waves'][:60,:,0].T,color='gray',alpha=.1,lw=.5)
            for q,m in enumerate(d['means']):axes[row,0].plot(np.arange(-100,101)/fs*1000,m[:,0],label=f'Q{q+1}')
            axes[row,0].plot(np.arange(-100,101)/fs*1000,d['reference'][:,0],color='black',ls='--',label='pooled')
            if not len(d['waves']):axes[row,0].text(.1,.5,'No complete raw context',transform=axes[row,0].transAxes)
            axes[row,0].set(title=f'c{cid}: {r["automated_label"]}, n={len(idx)}, raw b{d["channels"][0]}',xlabel='Nominal ms',ylabel='Centered input x1e6');axes[row,0].legend(fontsize=7,ncol=3)
            axes[row,1].scatter(t[idx]/fs,amp[idx],s=5);axes[row,1].set(xlim=(0,N/fs),xlabel='Nominal seconds',ylabel='Sorter amplitude')
            axes[row,2].hist(d['acg_lags']/fs*1000,bins=np.arange(-50.5,51,1))
            axes[row,2].set(title=f'R={r["R"]}, Q={r["Q"]}\nISI<2 ms={r["isi_lt_2ms"]}; peak guard={r["peak_guard"]}',xlabel='ACG nominal ms; self removed')
        fig.suptitle(f'Shank{shank}: all-cluster screen; raw quarters, event time and ACG; no censoring')
        name=f'screen_{start//6+1}.png';fig.savefig(output/name,dpi=100);plt.close(fig);pages.append(name)
    v=templates.reshape(len(templates),-1).astype(float);v/=np.maximum(np.linalg.norm(v,axis=1,keepdims=True),1e-30);cosine=v@v.T
    screen=[];wanted=set()
    for cid in ids:
        candidates=[j for j in ids if j!=cid and int(inventory[j]['events'])>=20]
        distances=np.linalg.norm(pos-pos[peaks[cid]],axis=1);neighbors=set()
        if candidates:
            if int(inventory[cid]['events'])>=20:
                neighbors.update(j for j in sorted(candidates,key=lambda j:(-abs(cosine[cid,j]),j))[:2] if abs(cosine[cid,j])>=.05)
            close=min(candidates,key=lambda j:(distances[peaks[j]],j))
            if distances[peaks[close]]<=150:neighbors.add(close)
        for j in ids:
            if j!=cid:screen.append(dict(cluster_id=int(cid),neighbor=int(j),events=int(inventory[j]['events']),template_cosine=float(cosine[cid,j]),peak_distance_um=float(distances[peaks[j]]),selected=j in neighbors))
        wanted.update(tuple(sorted((int(cid),int(j)))) for j in neighbors)
    table(output/'neighbor_screen.csv',screen);pairrows=[]
    for a,b in sorted(wanted):
        ia,ib=[np.flatnonzero(cl==cid) for cid in [a,b]]
        distances=np.minimum(np.linalg.norm(pos-pos[peaks[a]],axis=1),np.linalg.norm(pos-pos[peaks[b]],axis=1))
        channels=cmap[np.argsort(distances,kind='stable')[:12]];sa,wa=extract(raw,t,ia,channels,256);sb,wb=extract(raw,t,ib,channels,256)
        ma=wa.mean(0) if len(wa) else np.full((201,12),np.nan);mb=wb.mean(0) if len(wb) else np.full((201,12),np.nan)
        lags=cross_lags(t[ia],t[ib]);common=np.intersect1d(pcb[a],pcb[b]);projections=[np.empty((len(ia),0)),np.empty((len(ib),0))];center=axes=var=np.array([])
        if len(common):
            _,fa=features(pcs,pcb,cl,a,common);_,fb=features(pcs,pcb,cl,b,common)
            if np.std(np.concatenate([fa,fb]))>0:projections,center,axes,var=pca_projection([fa,fb])
        np.savez_compressed(output/f'pair_{a}_{b}.npz',channels=channels,selected_a=sa,selected_b=sb,waves_a=wa,waves_b=wb,cross_lags=lags,common_binary_channels=common,event_indices_a=ia,event_indices_b=ib,projection_a=projections[0],projection_b=projections[1],center=center,axes=axes)
        pairrows.append(dict(cluster_a=a,cluster_b=b,events_a=len(ia),events_b=len(ib),shared_feature_channels=len(common),template_cosine=float(cosine[a,b]),raw_correlation=corr(ma,mb),cross_pairs_abs_le2=int((abs(lags)<=2).sum()),cross_pairs_abs_lt20=int((abs(lags)<20).sum())))
        fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained');finite=np.r_[ma[np.isfinite(ma)],mb[np.isfinite(mb)]];gap=max(float(np.ptp(finite))*1.1,1) if len(finite) else 1
        for k,ch in enumerate(channels[:4]):
            ax[0,0].plot(np.arange(-100,101)/fs*1000,ma[:,k]+k*gap,color='C0',label=str(a) if k==0 else None)
            ax[0,0].plot(np.arange(-100,101)/fs*1000,mb[:,k]+k*gap,color='C1',label=str(b) if k==0 else None)
        ax[0,0].legend();ax[0,0].set(title=f'Raw means bottom to top b{channels[:4].tolist()}',xlabel='Nominal ms',ylabel='Centered input x1e6 + offsets')
        ax[0,1].hist(lags/fs*1000,bins=np.arange(-50.5,51,1));ax[0,1].set(title='All cross-event pairs; no chance correction',xlabel=f'c{b} minus c{a}, nominal ms')
        for cid,idx,projection in zip([a,b],[ia,ib],projections):
            subset=select(np.arange(len(idx)),1500)
            if projection.shape[1]>=2:ax[1,0].scatter(projection[subset,0],projection[subset,1],s=5,alpha=.4,label=str(cid))
            ax[1,1].scatter(t[idx]/fs,amp[idx],s=5,alpha=.4,label=str(cid))
        ax[1,0].set(title=f'{len(common)} shared physical PC channels; balanced PCA');ax[1,1].legend();ax[1,1].set(xlabel='Nominal seconds',ylabel='Sorter amplitude')
        fig.suptitle(f'Shank{shank} c{a}/c{b}: WITHIN-RUN competitors; no merge or acceptance')
        name=f'pair_{a}_{b}.png';fig.savefig(output/name,dpi=100);plt.close(fig);pages.append(name)
    table(output/'pair_metrics.csv',pairrows)
    summary=dict(state='evidence_only_pending_review',shank_zero_based=shank,run_path=str(runpath.relative_to(ROOT)),baseline_report=str(baseline.relative_to(ROOT)),events=len(t),clusters=len(ids),pairs=sorted(wanted),run_manifest_sha256=sha(runpath/'output-manifest.json'),baseline_manifest_sha256=sha(baseline/'report-manifest.json'),selection_sha256=sha(ROOT/'configs/extra4_working_runs.v1.json'),script_sha256=sha(Path(__file__)),helper_sha256={n:sha(ROOT/'scripts'/n) for n in ['review_pilot_round1.py','review_pilot_round2.py']},limitations='No neuron truth or automatic decisions. Neighbor screen is bounded, not exhaustive isolation. Every directed competitor recorded, including sparse clusters; >=20-event clusters use two largest absolute template cosines >=.05 plus closest within 150um. Sparse clusters use closest >=20-event neighbor within 150um. R/Q reproduce automated labels, not curation. All-event ACG/CCG uncorrected for chance; raw sampling bounded.')
    save(output/'summary.json',summary)
    html='<html><meta charset="utf-8"><title>Single-shank curation evidence</title><style>body{font:16px system-ui;max-width:1400px;margin:30px auto}img{width:100%}</style><h1>Shank'+str(shank)+': full-cluster curation evidence</h1><p>Selected run only. All good and mua clusters reviewed separately from automated labels. Four quarters are equal original-duration segments. Raw x1e6 is numerical scaling, not calibrated voltage. Pair figures compare WITHIN-RUN competitors, not alternative sorts. No edits to original labels or events.</p><p><a href="unit_metrics.csv">All clusters and quality</a> | <a href="quarter_metrics.csv">Quarters</a> | <a href="neighbor_screen.csv">All competitors</a> | <a href="pair_metrics.csv">Focused pairs</a> | <a href="summary.json">Methods/provenance</a></p>'
    html+=''.join(f'<h2>{name}</h2><img src="{name}">' for name in pages);(output/'index.html').write_text(html,encoding='utf-8')
    verify_manifest(runpath/'output-manifest.json');save(output/'report-manifest.json',{p.name:sha(p) for p in output.iterdir()});print(summary)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--shank',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.shank,a.output)
