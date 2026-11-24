"""Bounded W9 review of the remaining good clusters; no curation is applied."""
import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from review_pilot_round1 import sha, selection, write_csv, RAW_SHA
from review_pilot_round2 import cross_lags, features, pca_projection

TARGETS = [1,5,12,27,29,31,38,39,40,41,45,47,49,50,53]
RUN = ROOT/'results/extra4_shank0/w7b-exclude248-01'
W8 = ROOT/'results/extra4_shank0/w8-checkpoint01'
W7 = ROOT/'results/extra4_shank0/w7b-review01'


def rows(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def verify(folder, manifest):
    for name, digest in json.loads((folder/manifest).read_text()).items():
        assert sha(folder/name) == digest, name


def run(output):
    output = output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'results/extra4_shank0'):
        raise ValueError('Fresh report directory required')
    for folder, manifest in [(RUN,'output-manifest.json'),(W8,'report-manifest.json'),(W7,'report-manifest.json')]:
        verify(folder, manifest)
    binary = ROOT/'data/extra4_shank0_float32.bin'
    assert sha(binary) == RAW_SHA
    raw = np.memmap(binary, mode='r', dtype='<f4', shape=(3000000,512))
    load = lambda name: np.load(RUN/'kilosort4'/(name+'.npy'), allow_pickle=False)
    t, cl, amp = [load(n).ravel() for n in ['spike_times','spike_clusters','amplitudes']]
    templates, pos, pcs, pci = [load(n) for n in ['templates','channel_positions','pc_features','pc_feature_ind']]
    cmap = load('channel_map').ravel(); pcb = cmap[pci]
    peaks = np.ptp(templates,axis=1).argmax(axis=1)
    metrics = {int(r['cluster_id']):r for r in rows(W7/'cluster_metrics.csv') if r['run']=='exclude248'}
    criteria = {int(r['cluster_id']):r for r in rows(W8/'label_criteria.csv') if r['run']=='exclude248'}
    assert set(TARGETS) == {c for c,r in metrics.items() if r['automated_label']=='good'}-{6,10,32,33}
    output.mkdir(parents=True)
    rel = np.arange(-100,101); center = (rel>=-20)&(rel<=40)

    def event_ids(cid, quarter=None, maximum=256):
        mask = (cl==cid)&(t>=100)&(t<2999900)
        if quarter is not None:
            mask &= t//750000==quarter
        ids = np.flatnonzero(mask)
        return selection(ids[np.argsort(t[ids],kind='stable')], maximum)

    def waves(ids, channels):
        w = np.asarray(raw[t[ids,None]+rel[None,:]][:,:,channels],dtype=np.float32)*1e6
        w -= np.median(w[:,:70],axis=1)[:,None,:]
        return w

    def nearest(cid, n=8):
        return cmap[np.argsort(np.linalg.norm(pos-pos[peaks[cid]],axis=1),kind='stable')[:n]]

    # Screen every other cluster, with no cross-run matching. Absolute template
    # cosine includes opposite-polarity competitors. Nearby sparse events remain
    # in the screening table but require W10 review rather than arbitrary PCA.
    v = templates.reshape(len(templates),-1).astype(float)
    v /= np.maximum(np.linalg.norm(v,axis=1,keepdims=True),1e-30)
    cosine = v@v.T
    old_pairs = {tuple(sorted((int(r['cluster_a']),int(r['cluster_b'])))) for r in rows(W8/'pair_metrics.csv')}
    screen = []; wanted = set()
    for cid in TARGETS:
        candidates = [j for j in metrics if j!=cid and int(metrics[j]['events'])>=20]
        distance = np.linalg.norm(pos[peaks]-pos[peaks[cid]],axis=1)
        similar = sorted(candidates,key=lambda j:(-abs(cosine[cid,j]),j))[:2]
        selected = {j for j in similar if abs(cosine[cid,j])>=.05}
        close = min(candidates,key=lambda j:(distance[j],j))
        if distance[close]<=150:
            selected.add(close)
        wanted.update(tuple(sorted((cid,j))) for j in selected)
        for j in metrics:
            if j==cid: continue
            pair=tuple(sorted((cid,j)))
            screen.append(dict(cluster_id=cid,neighbor=j,events=int(metrics[j]['events']),
                template_cosine=float(cosine[cid,j]),peak_distance_um=float(distance[j]),
                selected=j in selected,evidence='W8' if pair in old_pairs else 'W9' if j in selected else 'screen_only'))
    write_csv(output/'neighbor_screen.csv',screen)
    unit_rows=[]; quarter_rows=[]; pages=[]
    for cid in TARGETS:
        channels=nearest(cid); ids=event_ids(cid); w=waves(ids,channels); reference=w.mean(axis=0)
        allids=np.flatnonzero(cl==cid); times=np.sort(t[allids]); isi=np.diff(times)
        lags=cross_lags(times,times)
        # Remove exactly one self-pair per event; retain distinct same-time events.
        zero=np.flatnonzero(lags==0); lags=np.delete(lags,zero[:len(times)])
        means=[]; qids=[]
        for q in range(4):
            qi=event_ids(cid,q,128); qids.append(qi)
            mean=waves(qi,channels).mean(axis=0) if len(qi) else np.full(reference.shape,np.nan)
            means.append(mean)
            correlation=float(np.corrcoef(mean[center].ravel(),reference[center].ravel())[0,1]) if len(qi)>1 else None
            quarter_rows.append(dict(cluster_id=cid,quarter=q+1,events=int(np.sum((cl==cid)&(t//750000==q))),
                selected=len(qi),raw_correlation_to_pooled=correlation))
        np.savez_compressed(output/f'unit_{cid}.npz',channels=channels,relative_samples=rel,
            selected=ids,waves=w,reference=reference,means=np.array(means),acg_lags=lags,
            **{f'quarter_events_{q}':qi for q,qi in enumerate(qids)})
        row=dict(metrics[cid]);row.update(R=criteria[cid]['R'],Q=criteria[cid]['Q'],selected=len(ids))
        unit_rows.append(row)
        fig,ax=plt.subplots(2,3,figsize=(15,8),layout='constrained')
        for k in range(2):
            ax[0,k].plot(rel/10,w[:min(60,len(w)),:,k].T,color='gray',alpha=.12,lw=.5)
            ax[0,k].plot(rel/10,reference[:,k],color='black',lw=2,label='Pooled mean')
            for q,mean in enumerate(means):ax[0,k].plot(rel/10,mean[:,k],label=f'Q{q+1} (n={len(qids[q])})')
            ax[0,k].set(title=f'Raw b{channels[k]}: selected events + quarter means',xlabel='Nominal ms',ylabel='Centered input x1e6')
        ax[0,0].legend(fontsize=7)
        ax[0,2].hist(lags/10,bins=np.arange(-50.5,51,1));ax[0,2].set(title='ACG: all pairs minus self; no chance correction',xlabel='Nominal ms')
        ax[1,0].scatter(t[allids]/10000,amp[allids],s=6,alpha=.5)
        ax[1,0].set(xlim=(0,300),xlabel='Nominal seconds',ylabel='Sorter feature amplitude')
        ax[1,1].hist(times/10000,bins=np.arange(0,301,10));ax[1,1].set(xlabel='Nominal seconds',ylabel='Events / 10 s')
        ax[1,2].hist(isi[isi<1000]/10,bins=np.arange(0,101,1));ax[1,2].set(xlabel='Adjacent ISI, nominal ms',title=f'ISI <1 ms: {sum(isi<10)}, <2 ms: {sum(isi<20)}')
        fig.suptitle(f'Without-248 cluster {cid}: n={len(times)}, automated good; R={float(row["R"]):.3g}, Q={float(row["Q"]):.3g}\nPeak guards={row["peak_guard_events"]}, broad/tight={row["broad_warning_events"]}/{row["tight_warning_events"]}; no censoring')
        name=f'unit_{cid}.png';fig.savefig(output/name,dpi=110);plt.close(fig);pages.append(name)
        print(f'unit {cid} complete',flush=True)
    write_csv(output/'unit_metrics.csv',unit_rows);write_csv(output/'quarter_metrics.csv',quarter_rows)
    pair_rows=[]
    for ca,cb in sorted(wanted-old_pairs):
        distance=np.minimum(np.linalg.norm(pos-pos[peaks[ca]],axis=1),np.linalg.norm(pos-pos[peaks[cb]],axis=1))
        channels=cmap[np.argsort(distance,kind='stable')[:12]]
        sa,sb=event_ids(ca),event_ids(cb);wa,wb=waves(sa,channels),waves(sb,channels)
        ma,mb=wa.mean(axis=0),wb.mean(axis=0)
        ia,ib=np.flatnonzero(cl==ca),np.flatnonzero(cl==cb)
        lags=cross_lags(np.sort(t[ia]),np.sort(t[ib]))
        common=np.intersect1d(pcb[ca],pcb[cb])
        if len(common):
            _,fa=features(pcs,pcb,cl,ca,common);_,fb=features(pcs,pcb,cl,cb,common)
            projections,mean,axes,var=pca_projection([fa,fb])
        else:
            projections=[np.empty((len(ia),0)),np.empty((len(ib),0))];mean=axes=var=np.array([])
        key=f'pair_{ca}_{cb}'
        np.savez_compressed(output/(key+'.npz'),channels=channels,relative_samples=rel,
            selected_a=sa,selected_b=sb,waves_a=wa,waves_b=wb,event_indices_a=ia,event_indices_b=ib,
            common_binary_channels=common,center=mean,axes=axes,projection_a=projections[0],projection_b=projections[1],cross_lags=lags)
        pair_rows.append(dict(cluster_a=ca,cluster_b=cb,shared_feature_channels=len(common),
            raw_correlation=float(np.corrcoef(ma[center].ravel(),mb[center].ravel())[0,1]),
            cross_pairs_abs_le2=int(sum(abs(lags)<=2)),cross_pairs_abs_lt20=int(sum(abs(lags)<20))))
        fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        gap=max(float(np.max(np.ptp(np.stack([ma,mb])[:,:,:4],axis=1)))*1.1,1)
        for k,ch in enumerate(channels[:4]):
            ax[0,0].plot(rel/10,ma[:,k]+k*gap,color='C0',label=str(ca) if k==0 else None)
            ax[0,0].plot(rel/10,mb[:,k]+k*gap,color='C1',label=str(cb) if k==0 else None)
        ax[0,0].set(title=f'Raw means: bottom to top b{channels[:4].tolist()}',xlabel='Nominal ms',ylabel='Centered input x1e6 + offsets');ax[0,0].legend()
        ax[0,1].hist(lags/10,bins=np.arange(-50.5,51,1));ax[0,1].set(title='All cross-event pairs; no chance correction',xlabel=f'{cb} minus {ca}, nominal ms')
        for cid,ids,pr in [(ca,ia,projections[0]),(cb,ib,projections[1])]:
            subset=selection(np.arange(len(ids)),1500)
            if pr.shape[1]==2:ax[1,0].scatter(pr[subset,0],pr[subset,1],s=5,alpha=.4,label=str(cid))
            ax[1,1].scatter(t[ids]/10000,amp[ids],s=5,alpha=.4,label=str(cid))
        ax[1,0].set(title=f'{len(common)} physical PC channels; balanced PCA {var.sum():.0%}')
        if len(common):ax[1,0].legend()
        ax[1,1].legend();ax[1,1].set(xlabel='Nominal seconds',ylabel='Sorter feature amplitude')
        fig.suptitle(f'Without-248 {ca} / {cb}: WITHIN-RUN neighbors, no merge applied')
        fig.savefig(output/(key+'.png'),dpi=110);plt.close(fig);pages.append(key+'.png')
        print(key+' complete',flush=True)
    write_csv(output/'pair_metrics.csv',pair_rows)
    summary=dict(schema='w9-good-review-v1',targets=TARGETS,new_pairs=sorted(wanted-old_pairs),
        reused_w8_pairs=sorted(wanted&old_pairs),raw_sha256=RAW_SHA,script_sha256=sha(Path(__file__)),
        helper_sha256={n:sha(ROOT/'scripts'/n) for n in ['review_pilot_round1.py','review_pilot_round2.py']},
        run_manifest_sha256=sha(RUN/'output-manifest.json'),w8_manifest_sha256=sha(W8/'report-manifest.json'),
        w7_manifest_sha256=sha(W7/'report-manifest.json'),labels_changed=False,human_acceptance='pending',
        limitations='Bounded excerpts and descriptive PCA, not exhaustive isolation or neuron ground truth. Guards annotate event centers; no exposure correction.')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    reused=''.join(f'<li><a href="../w8-checkpoint01/pair_{a}_{b}.png">W8 {a}/{b}</a></li>' if (W8/f'pair_{a}_{b}.png').exists() else f'<li><a href="../w8-checkpoint01/pair_{b}_{a}.png">W8 {a}/{b}</a></li>' for a,b in sorted(wanted&old_pairs))
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>W9 good-cluster review</title><style>body{font:16px system-ui;max-width:1300px;margin:30px auto}img{width:100%}</style><h1>W9: remaining 15 automated-good clusters</h1><p>Selected without-248 run only. Recommendations pending acceptance; no labels or events changed. Quarter1–4 are consecutive 75 nominal seconds. Scaling x1e6 is numerical, not established microvolts. Gray traces are up to 60 selected events.</p><p>Neighbor selection: two largest absolute template cosines (at least .05) plus closest peak within 150 um, among clusters with at least 20 events. All competitors recorded in neighbor_screen.csv. This screen is not proof of isolation; sparse populations remain for W10.</p><h2>Reused W8 neighbor figures</h2><ul>'+reused+'</ul>'+''.join(f'<h2>{name}</h2><img src="{name}">' for name in pages),encoding='utf-8')
    verify(RUN,'output-manifest.json');assert sha(binary)==RAW_SHA
    (output/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in output.iterdir() if p.is_file()},indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
