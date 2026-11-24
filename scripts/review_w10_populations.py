"""W10 all-mua screen and diagnostic population probes; no sorting edits."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from review_w9_good import ROOT, RUN, W7, W8, rows, verify
from review_pilot_round1 import sha, selection, write_csv, RAW_SHA
from review_pilot_round2 import cross_lags, features, pca_projection
from review_w7b import matched_pairs

W9=ROOT/'results/extra4_shank0/w9-good-review01'
PAIRS=[(43,44),(41,42),(45,48),(52,53),(26,27),(29,30)]


def two_groups(x):
    """Forced two-centroid diagnostic; never a biological split decision."""
    centered=x-x.mean(0)
    axis=np.linalg.svd(centered,full_matrices=False)[2][0]
    projection=centered@axis
    centers=x[[np.argmin(projection),np.argmax(projection)]].copy()
    labels=np.zeros(len(x),dtype=int)
    for _ in range(100):
        updated=((x[:,None]-centers[None,:])**2).sum(2).argmin(1)
        if len(np.unique(updated))<2:raise ValueError('Degenerate diagnostic partition')
        new=np.array([x[updated==i].mean(0) for i in range(2)])
        if np.array_equal(updated,labels):return updated,new
        labels,centers=updated,new
    raise ValueError('Diagnostic partition did not converge')


def run(output):
    output=output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'results/extra4_shank0'):
        raise ValueError('Fresh report required')
    inputs=[(RUN,'output-manifest.json'),(W7,'report-manifest.json'),(W8,'report-manifest.json'),(W9,'report-manifest.json')]
    control=ROOT/'results/extra4_shank0/w7b-control01';inputs.append((control,'output-manifest.json'))
    for folder,manifest in inputs:verify(folder,manifest)
    binary=ROOT/'data/extra4_shank0_float32.bin';assert sha(binary)==RAW_SHA
    raw=np.memmap(binary,mode='r',dtype='<f4',shape=(3000000,512))
    load=lambda name:np.load(RUN/'kilosort4'/(name+'.npy'),allow_pickle=False)
    t,cl,amp=[load(n).ravel() for n in ['spike_times','spike_clusters','amplitudes']]
    templates,pos,pcs,pci=[load(n) for n in ['templates','channel_positions','pc_features','pc_feature_ind']]
    cmap=load('channel_map').ravel();pcb=cmap[pci];peaks=np.ptp(templates,axis=1).argmax(1)
    metrics={int(r['cluster_id']):r for r in rows(W7/'cluster_metrics.csv') if r['run']=='exclude248'}
    criteria={int(r['cluster_id']):r for r in rows(W8/'label_criteria.csv') if r['run']=='exclude248'}
    mua=sorted(c for c,r in metrics.items() if r['automated_label']=='mua');assert len(mua)==39
    output.mkdir(parents=True)
    rel=np.arange(-100,101);central=(rel>=-20)&(rel<=40)
    def channels(cid,n=8):
        return cmap[np.argsort(np.linalg.norm(pos-pos[peaks[cid]],axis=1),kind='stable')[:n]]
    def extract(ids,ch,maximum=128):
        ids=ids[(t[ids]>=100)&(t[ids]<2999900)]
        ids=selection(ids[np.argsort(t[ids],kind='stable')],maximum)
        w=np.asarray(raw[t[ids,None]+rel[None,:]][:,:,ch],dtype=np.float32)*1e6
        if len(ids):w-=np.median(w[:,:70],axis=1)[:,None,:]
        return ids,w
    pages=[];screen=[]
    for start in range(0,len(mua),6):
        block=mua[start:start+6];fig,ax=plt.subplots(len(block),3,figsize=(15,3.2*len(block)),squeeze=False,layout='constrained')
        for row,cid in enumerate(block):
            ids=np.flatnonzero(cl==cid);times=np.sort(t[ids]);ch=channels(cid)
            selected,w=extract(ids,ch);mean=w.mean(0) if len(w) else np.full((201,len(ch)),np.nan)
            qm=[];qids={};correlations=[]
            for q in range(4):
                qi,qw=extract(ids[t[ids]//750000==q],ch,64);qids[f'q{q}_events']=qi
                m=qw.mean(0) if len(qw) else np.full_like(mean,np.nan);qm.append(m)
                correlations.append(float(np.corrcoef(m[central].ravel(),mean[central].ravel())[0,1]) if len(qw)>1 else np.nan)
                ax[row,0].plot(rel/10,m[:,0],label=f'Q{q+1} n={sum(times//750000==q)}',alpha=.8)
            ax[row,0].plot(rel/10,mean[:,0],color='black',lw=1.5,label='pooled')
            ax[row,0].set(title=f'Without-248 {cid}: n={len(ids)}, raw b{ch[0]}',xlabel='Nominal ms',ylabel='Centered input x1e6');ax[row,0].legend(fontsize=6)
            if not len(w):ax[row,0].text(.1,.5,'No complete centered raw windows',transform=ax[row,0].transAxes)
            ax[row,1].scatter(times/10000,amp[ids[np.argsort(t[ids])]],s=5);ax[row,1].set(xlim=(0,300),xlabel='Nominal seconds',ylabel='Sorter amplitude')
            lags=cross_lags(times,times);zeros=np.flatnonzero(lags==0);lags=np.delete(lags,zeros[:len(times)])
            ax[row,2].hist(lags/10,bins=np.arange(-50.5,51,1))
            r=criteria[cid];R=float(r['R']) if r['R'] else None;Q=float(r['Q']) if r['Q'] else None
            failure='ineligible' if r['eligible']=='False' else 'R+Q' if R>=.2 and Q>=.2 else 'R' if R>=.2 else 'Q'
            ax[row,2].set(title=f'Fail {failure}; R={R if R is None else round(R,3)}, Q={Q if Q is None else round(Q,3)}; ISI<2ms={sum(np.diff(times)<20)}',xlabel='ACG nominal ms; self removed')
            np.savez_compressed(output/f'mua_{cid}.npz',event_indices=ids,channels=ch,selected=selected,waves=w,mean=mean,quarter_means=np.array(qm),acg_lags=lags,**qids)
            result=dict(metrics[cid]);result.update(R=R,Q=Q,label_failure=failure,complete_events=int(sum((times>=100)&(times<2999900))),
                boundary_events=int(sum((times<100)|(times>=2999900))),quarter_counts=';'.join(str(sum(times//750000==q)) for q in range(4)),
                quarter_correlations=';'.join(str(v) for v in correlations))
            screen.append(result)
        name=f'mua_screen_{start//6+1}.png';fig.savefig(output/name,dpi=100);plt.close(fig);pages.append(name)
    write_csv(output/'mua_screen.csv',screen)
    # Probe whether previously seen feature structure corresponds to raw changes.
    # Two groups are imposed for diagnosis, never taken as proof of two neurons.
    subgroup_rows=[]
    oldt=np.load(control/'kilosort4/spike_times.npy').ravel();oldcl=np.load(control/'kilosort4/spike_clusters.npy').ravel()
    for cid in [12,29,31,40,45]:
        ids=np.flatnonzero(cl==cid);x=pcs[ids].reshape(len(ids),-1).astype(float)
        if cid==31:
            labels=np.full(len(ids),2,dtype=int)
            matches={}
            for label,oldcid in enumerate([31,33]):
                old=np.sort(oldt[oldcl==oldcid]);m=matched_pairs(old,t[ids]);matches[str(oldcid)]=m
                newids=m[:,1];labels[newids]=np.where(labels[newids]==2,label,3)
            centers=np.empty((0,0));mode='control31 / control33 time correspondence; unmatched/ambiguous separate'
        else:
            labels,centers=two_groups(x);mode='forced two-centroid diagnostic, NOT proposed split'
        projection,center,axes,var=pca_projection([x])
        ch=channels(cid);means=[];saved={};unique=np.unique(labels)
        fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        for label in unique:
            gi=ids[labels==label];selected,w=extract(gi,ch,128);m=w.mean(0);means.append(m)
            saved[f'group_{label}_events']=gi;saved[f'group_{label}_selected']=selected;saved[f'group_{label}_waves']=w
            title=f'group{label} n={len(gi)}'
            ax[0,0].scatter(projection[0][labels==label,0],projection[0][labels==label,1],s=6,label=title,alpha=.5)
            ax[0,1].plot(rel/10,m[:,0],label=title)
            ax[1,0].scatter(t[gi]/10000,amp[gi],s=6,label=title,alpha=.5)
            ax[1,1].hist(t[gi]/10000,bins=np.arange(0,301,25),histtype='step',label=title)
            subgroup_rows.append(dict(cluster_id=cid,group=int(label),events=len(gi),isi_lt20=int(sum(np.diff(np.sort(t[gi]))<20)),
                amplitude_median=float(np.median(amp[gi])),quarter_counts=';'.join(str(sum(t[gi]//750000==q)) for q in range(4)),mode=mode))
        ax[0,0].set(title=f'Own physical PC channels; PCA {var.sum():.0%}');ax[0,0].legend(fontsize=8)
        ax[0,1].set(title=f'Group raw means b{ch[0]}',xlabel='Nominal ms',ylabel='Centered input x1e6');ax[0,1].legend(fontsize=8)
        ax[1,0].set(xlabel='Nominal seconds',ylabel='Sorter amplitude');ax[1,1].set(xlabel='Nominal seconds',ylabel='Events / 25 seconds')
        fig.suptitle(f'Without-248 {cid}: {mode}')
        name=f'population_{cid}.png';fig.savefig(output/name,dpi=110);plt.close(fig);pages.append(name)
        np.savez_compressed(output/f'population_{cid}.npz',event_indices=ids,labels=labels,feature_channels=pcb[cid],centroids=centers,
            feature_values=x,projection=projection[0],center=center,axes=axes,channels=ch,means=np.array(means),groups=unique,**saved)
    write_csv(output/'population_metrics.csv',subgroup_rows)
    pair_rows=[]
    for ca,cb in PAIRS:
        ia,ib=[np.flatnonzero(cl==c) for c in [ca,cb]]
        ia=ia[np.argsort(t[ia],kind='stable')];ib=ib[np.argsort(t[ib],kind='stable')]
        matches=matched_pairs(t[ia],t[ib]);lags=cross_lags(t[ia],t[ib])
        common=np.intersect1d(pcb[ca],pcb[cb]);assert len(common)
        _,fa=features(pcs,pcb,cl,ca,common);_,fb=features(pcs,pcb,cl,cb,common)
        # features follow original event order; enforce the time-sorted index order.
        fa=fa[np.argsort(t[cl==ca],kind='stable')];fb=fb[np.argsort(t[cl==cb],kind='stable')]
        projected,center,axes,var=pca_projection([fa,fb])
        x=np.concatenate([fa,fb]);origin=np.r_[np.zeros(len(fa),int),np.ones(len(fb),int)]
        other=[];nearest=[]
        for start in range(0,len(x),128):
            distances=((x[start:start+128,None,:]-x[None,:,:])**2).sum(2)
            distances[np.arange(len(distances)),np.arange(start,start+len(distances))]=np.inf
            nn=np.argsort(distances,axis=1,kind='stable')[:,:5];nearest.append(nn)
            other.extend((origin[nn]!=origin[start:start+len(distances),None]).mean(1))
        other=np.array(other);nearest=np.concatenate(nearest)
        ch=channels(ca,12);saved={};fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        for label,(cid,ids,pr) in enumerate([(ca,ia,projected[0]),(cb,ib,projected[1])]):
            hit=np.zeros(len(ids),bool);hit[matches[:,label]]=True
            ax[0,0].scatter(pr[:,0],pr[:,1],s=6,alpha=.4,label=str(cid))
            ax[0,0].scatter(pr[hit,0],pr[hit,1],s=25,facecolors='none',edgecolors=f'C{label}')
            for cohort,mask in [('matched',hit),('other',~hit)]:
                selected,w=extract(ids[mask],ch)
                saved[f'{label}_{cohort}_selected']=selected;saved[f'{label}_{cohort}_waves']=w
                if len(w):ax[0,1].plot(rel/10,w.mean(0)[:,0],color=f'C{label}',ls='-' if cohort=='other' else '--',label=f'{cid} {cohort} n={sum(mask)}')
            subset=other[:len(ia)] if label==0 else other[len(ia):]
            ax[1,1].hist(subset,bins=np.arange(-.1,1.11,.2),histtype='step',label=str(cid))
        ax[0,0].set(title=f'{len(common)} shared channels; circles = one-to-one +/-2 matches');ax[0,0].legend()
        ax[0,1].set(title=f'Raw b{ch[0]} cohort means',xlabel='Nominal ms');ax[0,1].legend(fontsize=8)
        ax[1,0].hist(lags/10,bins=np.arange(-5.05,5.1,.1));ax[1,0].set(title='All cross-pairs, uncorrected',xlabel=f'{cb} minus {ca}, nominal ms')
        ax[1,1].set(title='Full shared-PC 5-neighbor label mixing',xlabel='Fraction other-cluster neighbors');ax[1,1].legend()
        fig.suptitle(f'Without-248 {ca}/{cb}: diagnostic overlap; no merge/deletion')
        name=f'overlap_{ca}_{cb}.png';fig.savefig(output/name,dpi=110);plt.close(fig);pages.append(name)
        np.savez_compressed(output/f'overlap_{ca}_{cb}.npz',ids_a=ia,ids_b=ib,matches=matches,cross_lags=lags,
            common_binary_channels=common,features_a=fa,features_b=fb,projection_a=projected[0],projection_b=projected[1],
            center=center,axes=axes,neighbor_indices=nearest,other_fraction=other,channels=ch,**saved)
        pair_rows.append(dict(cluster_a=ca,cluster_b=cb,shared_feature_channels=len(common),matches_within2=len(matches),
            all_pairs_within2=int(sum(abs(lags)<=2)),fraction_a_other_neighbors=float(other[:len(ia)].mean()),
            fraction_b_other_neighbors=float(other[len(ia):].mean()),union_isi_lt20=int(sum(np.diff(np.sort(np.r_[t[ia],t[ib]]))<20))))
    write_csv(output/'overlap_metrics.csv',pair_rows)
    for folder,manifest in inputs:verify(folder,manifest)
    assert sha(binary)==RAW_SHA
    summary=dict(schema='w10-population-review-v1',mua_ids=mua,diagnostic_populations=[12,29,31,40,45],pairs=PAIRS,
        raw_sha256=RAW_SHA,script_sha256=sha(Path(__file__)),input_manifests={str(f.relative_to(ROOT)):sha(f/m) for f,m in inputs},
        labels_or_events_changed=False,diagnostic_partitions_are_curated_splits=False,
        caveats='Forced partitions and stored-feature nearest neighbors are diagnostic, not validated isolation or neuron truth; no chance correction.')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>W10 population review</title><style>body{font:16px system-ui;max-width:1350px;margin:30px auto}img{width:100%}</style><h1>W10: all mua and ambiguous populations</h1><p>Selected without-248 IDs only. All 39 mua screened; diagnostic partitions are NOT curated splits. Original labels/events unchanged. Q1–4 are consecutive75 nominal seconds; x1e6 is numerical scaling, not calibrated microvolts. Raw means use complete windows only; empty quarters are unavailable, not zero waveforms.</p><p>Population31 groups0/1 match control31/33 by time, group2 is unmatched and group3 would be ambiguous. Other population groups are forced two-centroid diagnostic partitions. No cross-run event mixing.</p><p>Nearest-neighbor mixing uses stored sorter features and unbalanced cluster sizes; it has no acceptance threshold and is not independent validation of the sorter. Matched events within2 samples are candidates for coincidence review, not automatically duplicate detections.</p>'+''.join(f'<h2>{n}</h2><img src="{n}">' for n in pages),encoding='utf-8')
    (output/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in output.iterdir() if p.is_file()},indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    run(p.parse_args().output)
