"""Read-only, pilot-specific pair/feature/disturbance evidence; no curation."""
import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from review_pilot_round1 import sha, write_csv, selection, load_table, RAW_SHA, NSAMPLES, NCHANNELS

PAIRS = [(31,33),(45,48),(5,6),(2,0),(2,1),(2,3),(26,27)]


def cross_lags(a, b, radius=500):
    """Every b-a pair within inclusive radius, including simultaneous events."""
    b = np.sort(b)
    parts = [b[np.searchsorted(b,t-radius):np.searchsorted(b,t+radius,side='right')]-t for t in np.sort(a)]
    return np.concatenate(parts) if parts else np.empty(0,dtype=np.int64)


def constant_runs(values, minimum=100):
    edges = np.r_[0,np.flatnonzero(values[1:] != values[:-1])+1,len(values)]
    starts, stops = edges[:-1], edges[1:]
    keep = stops-starts >= minimum
    return starts[keep], stops[keep]


def features(pcs, pc_channels, clusters, cid, common):
    ids = np.flatnonzero(clusters == cid)
    cols = [int(np.flatnonzero(pc_channels[cid] == ch)[0]) for ch in common]
    return ids, pcs[ids][:,:,cols].reshape(len(ids),-1).astype(np.float64)


def pca_projection(groups):
    # Equal event counts per group prevent the larger cluster dominating the fit.
    n = min(256,*(len(g) for g in groups))
    training = np.concatenate([g[selection(np.arange(len(g)),n)] for g in groups])
    center = training.mean(axis=0)
    _, singular, vt = np.linalg.svd(training-center,full_matrices=False)
    return [(g-center)@vt[:2].T for g in groups], center, vt[:2], singular[:2]**2/np.sum(singular**2)


def run(evidence, binary, output, source_h5=None):
    evidence,binary,output = evidence.resolve(),binary.resolve(),output.resolve()
    if output.exists() or output.is_relative_to(evidence) or output.is_relative_to(binary.parent):
        raise ValueError('Use a fresh output outside frozen evidence and data')
    assert binary.stat().st_size == NSAMPLES*NCHANNELS*4 and sha(binary)==RAW_SHA
    manifest=json.loads((evidence/'return-manifest.json').read_text())['files']
    for name,item in manifest.items():
        assert sha(evidence/name)==item['sha256'],name
    src=evidence/'outputs/pilot01/kilosort4'
    arr=lambda n: np.load(src/f'{n}.npy',allow_pickle=False)
    times,clusters,amp=[arr(n).ravel() for n in ['spike_times','spike_clusters','amplitudes']]
    templates,pos,pcs,pc_channels=[arr(n) for n in ['templates','channel_positions','pc_features','pc_feature_ind']]
    similarity=arr('similar_templates')
    mapping=np.genfromtxt(evidence/'geometry/channel_map.csv',delimiter=',',names=True,dtype=int)
    np.testing.assert_array_equal(pos,np.column_stack([mapping['x_um'],mapping['y_um']]))
    assert len(times)==len(clusters)==len(pcs)==39620
    labels=load_table(src/'cluster_KSLabel.tsv')
    peaks=np.ptp(templates,axis=1).argmax(axis=1)
    raw=np.memmap(binary,mode='r',dtype='<f4',shape=(NSAMPLES,NCHANNELS))
    output.mkdir(parents=True)
    pages=[]; selections=[]
    rel=np.arange(-100,101); central=(rel>=-20)&(rel<=40)

    def raw_windows(cid, channels, ids=None, key=None):
        ids=np.flatnonzero(clusters==cid) if ids is None else ids
        valid=ids[(times[ids]>=100)&(times[ids]+100<NSAMPLES)]
        chosen=selection(valid[np.argsort(times[valid],kind='stable')],256)
        waves=np.asarray([np.asarray(raw[int(times[i])-100:int(times[i])+101,channels])*1e6 for i in chosen],dtype=np.float32)
        waves-=np.median(waves[:,:70],axis=1)[:,None,:]
        key=key or f'cluster_{cid}'
        np.savez_compressed(output/f'{key}_raw.npz',event_indices=chosen,sample_indices=times[chosen],channels=channels,waves=waves)
        selections.extend(dict(key=key,cluster_id=cid,event_index=int(i),sample=int(times[i])) for i in chosen)
        return waves.mean(axis=0),chosen

    # A single consistent 12-channel footprint for each pair, shared between clusters.
    pairrows=[]
    for a,b in PAIRS:
        key=f'pair_{a}_{b}'
        distance=np.minimum(np.linalg.norm(pos-pos[peaks[a]],axis=1),np.linalg.norm(pos-pos[peaks[b]],axis=1))
        channels=np.argsort(distance,kind='stable')[:12]
        ma,sa=raw_windows(a,channels,key=key+'_a'); mb,sb=raw_windows(b,channels,key=key+'_b')
        ia,ib=np.flatnonzero(clusters==a),np.flatnonzero(clusters==b)
        ta,tb=np.sort(times[ia]),np.sort(times[ib]); lags=cross_lags(ta,tb)
        merged=np.diff(np.sort(np.r_[ta,tb])); common=np.intersect1d(pc_channels[a],pc_channels[b])
        _,fa=features(pcs,pc_channels,clusters,a,common); _,fb=features(pcs,pc_channels,clusters,b,common)
        projections,center,axes,variance=pca_projection([fa,fb])
        np.savez_compressed(output/f'{key}_features.npz',common_channels=common,event_indices_a=ia,event_indices_b=ib,
                            center=center,axes=axes,projection_a=projections[0],projection_b=projections[1],cross_lags=lags)
        row=dict(cluster_a=a,cluster_b=b,events_a=len(ia),events_b=len(ib),label_a=labels[a]['KSLabel'],label_b=labels[b]['KSLabel'],
                 original_similarity=float(similarity[a,b]),peak_distance_um=float(np.linalg.norm(pos[peaks[a]]-pos[peaks[b]])),
                 raw_correlation=float(np.corrcoef(ma[central].ravel(),mb[central].ravel())[0,1]),shared_feature_channels=len(common),
                 pca_variance_2d=float(variance.sum()),cross_pairs_abs_le_2=int(np.sum(abs(lags)<=2)),
                 cross_pairs_abs_lt_10=int(np.sum(abs(lags)<10)),cross_pairs_abs_lt_20=int(np.sum(abs(lags)<20)),
                 merged_isi_lt_20=int(np.sum(merged<20)),merged_isi_pairs=len(merged))
        pairrows.append(row)
        fig,ax=plt.subplots(2,3,figsize=(15,8),layout='constrained')
        fig.suptitle(f'{a} / {b}: diagnostic comparison, no merge applied')
        for j,ch in enumerate(channels[:4]):
            ax[0,0].plot(rel/10,ma[:,j]+j*10,color='C0',label=f'{a}' if j==0 else None)
            ax[0,0].plot(rel/10,mb[:,j]+j*10,color='C1',label=f'{b}' if j==0 else None)
        ax[0,0].set(title=f'Raw means: b{channels[:4].tolist()}; offsets 10',xlabel='Nominal ms',ylabel='Centered source ×1e6');ax[0,0].legend()
        ax[0,1].hist(lags/10,bins=np.arange(-50.5,51,1));ax[0,1].axvspan(-2,2,color='red',alpha=.1)
        ax[0,1].set(title='Cross-correlogram, full exposure',xlabel=f'{b} minus {a}, nominal ms',ylabel='Pair counts')
        for cid,ids,pr in zip([a,b],[ia,ib],projections):
            chosen=selection(np.arange(len(ids)),1500)
            ax[0,2].scatter(pr[chosen,0],pr[chosen,1],s=5,alpha=.4,label=str(cid))
            ax[1,0].plot(np.arange(30)*10+5,np.histogram(times[ids],np.arange(0,NSAMPLES+1,100000))[0]/10,label=str(cid))
            ax[1,1].scatter(times[ids]/10000,amp[ids],s=4,alpha=.4,label=str(cid))
        ax[0,2].set(title=f'{len(common)} shared channels × 3 PCs → PCA ({variance.sum():.0%})',xlabel='Joint axis 1',ylabel='Joint axis 2');ax[0,2].legend()
        ax[1,0].set(title='10-second event rates',xlabel='Nominal s',ylabel='Events/s');ax[1,0].legend()
        ax[1,1].set(title='Feature amplitudes through time',xlabel='Nominal s',ylabel='Stored feature amplitude');ax[1,1].legend()
        ax[1,2].axis('off');ax[1,2].text(0,1,'\n'.join(f'{k}: {v:.4g}' if isinstance(v,float) else f'{k}: {v}' for k,v in row.items()),va='top',fontsize=9)
        fig.savefig(output/f'{key}.png',dpi=130);plt.close(fig);pages.append((f'Pair {a}/{b}',f'{key}.png'))
        print(f'Pair {a}/{b} complete',flush=True)
    write_csv(output/'pair_metrics.csv',pairrows)

    # Median split is a descriptive sensitivity view, deliberately not a clustering decision.
    ids=np.flatnonzero(clusters==35); peak=int(peaks[35]); col=int(np.flatnonzero(pc_channels[35]==peak)[0])
    pc2=pcs[ids,1,col]; cutoff=float(np.median(pc2)); lower=pc2<=cutoff
    channels=np.argsort(np.linalg.norm(pos-pos[peak],axis=1),kind='stable')[:12]
    means=[]; splitrows=[]
    fig,ax=plt.subplots(2,2,figsize=(13,8),layout='constrained')
    for flag,name,color in [(True,'lower','C0'),(False,'upper','C1')]:
        sub=ids[lower==flag]; mean,chosen=raw_windows(35,channels,sub,key='cluster35_'+name);means.append(mean)
        ax[0,0].scatter(times[sub]/10000,pcs[sub,1,col],s=4,alpha=.35,label=name)
        for j in range(4):ax[0,1].plot(rel/10,mean[:,j]+j*10,color=color,label=name if j==0 else None)
        ax[1,0].hist(amp[sub],bins=50,histtype='step',density=True,label=name)
        for q in range(4):
            inq=sub[(times[sub]>=q*750000)&(times[sub]<(q+1)*750000)]
            splitrows.append(dict(group=name,quarter=q+1,events=len(inq),median_amplitude=float(np.median(amp[inq]))))
    _,f=features(pcs,pc_channels,clusters,35,np.sort(pc_channels[35]));projections,center,axes,var=pca_projection([f])
    ax[1,1].scatter(projections[0][:,0],projections[0][:,1],c=np.where(lower,0,1),cmap='coolwarm',s=4,alpha=.4)
    ax[0,0].set(title=f'b{peak} PC2, median split {cutoff:.4g}',xlabel='Nominal s',ylabel='Stored PC2')
    ax[0,1].set(title='Raw group means, four nearest channels; offsets 10',xlabel='Nominal ms',ylabel='Centered source ×1e6')
    ax[1,0].set(title='Amplitude distribution by descriptive group',xlabel='Feature amplitude',ylabel='Density')
    ax[1,1].set(title=f'All stored channels × 3 PCs → PCA ({var.sum():.0%})',xlabel='Axis 1',ylabel='Axis 2')
    for axis in ax.ravel()[:3]:axis.legend()
    fig.suptitle('Cluster 35: internal feature structure; median split is NOT a proposed unit split')
    fig.savefig(output/'cluster35_structure.png',dpi=130);plt.close(fig);pages.append(('Cluster 35 feature structure','cluster35_structure.png'))
    write_csv(output/'cluster35_quarters.csv',splitrows)
    split_summary=dict(pc2_channel=peak,pc2_median=cutoff,raw_group_correlation=float(np.corrcoef(means[0][central].ravel(),means[1][central].ravel())[0,1]),
                       lower_events=int(lower.sum()),upper_events=int((~lower).sum()),pca_variance_2d=float(var.sum()))
    (output/'cluster35_summary.json').write_text(json.dumps(split_summary,indent=2)+'\n')
    np.savez_compressed(output/'cluster35_features.npz',event_indices=ids,lower=lower,projection=projections[0],center=center,axes=axes)

    # All-channel raw audit: no sampling, no filtering; count exact zero including signed zero.
    std=np.empty((300,512));zeros=np.empty((300,512),dtype=np.int32)
    for sec in range(300):
        block=np.asarray(raw[sec*10000:(sec+1)*10000])
        std[sec]=np.std(block,axis=0,dtype=np.float64);zeros[sec]=np.sum(block==0,axis=0)
    prior=np.load(evidence/'outputs/preflight/raw_per_second.npz',allow_pickle=False)['std']
    variability=np.median(std,axis=1);screen=np.flatnonzero(variability>2*np.median(variability))
    prior_screen=np.flatnonzero(np.median(prior,axis=1)>2*np.median(np.median(prior,axis=1)))
    np.testing.assert_array_equal(screen,prior_screen)
    flat=np.asarray(raw[:,248]).copy(); starts,stops=constant_runs(flat)
    flatrows=[dict(start_sample=int(a),stop_sample_exclusive=int(b),length_samples=int(b-a),value=float(flat[a])) for a,b in zip(starts,stops)]
    write_csv(output/'channel248_constant_runs.csv',flatrows)
    np.savez_compressed(output/'raw_per_second.npz',std=std,zero_counts=zeros,screen_seconds=screen)
    zero_rows=[dict(binary_channel=ch,global_channel=int(mapping['original_channel_id'][ch]),zero_samples=int(zeros[:,ch].sum()),zero_fraction=float(zeros[:,ch].sum()/NSAMPLES)) for ch in range(512)]
    write_csv(output/'channel_zero_fractions.csv',zero_rows)
    flagged=np.isin(times//10000,screen);flat_event=flat[times]==0
    disturbance_rows=[]
    for cid in range(59):
        sel=clusters==cid;n=int(sel.sum());inside=int(np.sum(sel&flagged));outside=n-inside
        disturbance_rows.append(dict(cluster_id=cid,events=n,screen_events=inside,outside_events=outside,
            screen_rate=inside/len(screen),outside_rate=outside/(300-len(screen)),
            screen_rate_ratio=(inside/len(screen))/(outside/(300-len(screen))) if outside else None,
            events_at_channel248_zero=int(np.sum(sel&flat_event)),template_peak=int(peaks[cid])))
    write_csv(output/'disturbance_cluster_metrics.csv',disturbance_rows)
    # Cluster 36 peaks on the anomalous channel; contextual review, not relabeling.
    near36=np.argsort(np.linalg.norm(pos-pos[248],axis=1),kind='stable')[:12]
    mean36,chosen36=raw_windows(36,near36,key='cluster36_context')
    fig,ax=plt.subplots(2,2,figsize=(14,8),layout='constrained')
    for j,ch in enumerate(near36[:5]):ax[0,0].plot(rel/10,mean36[:,j],label=f'b{ch}')
    ax[0,0].set(title='Cluster 36: centered raw mean',xlabel='Nominal ms',ylabel='Source ×1e6');ax[0,0].legend()
    ids36=np.flatnonzero(clusters==36)
    ax[0,1].scatter(times[ids36]/10000,flat[times[ids36]]*1e6,s=8)
    ax[0,1].set(title='Uncentered b248 at every cluster-36 event',xlabel='Nominal s',ylabel='Source ×1e6')
    for axis,i in zip(ax[1],selection(chosen36,2)):
        sample=int(times[i]);segment=np.asarray(raw[sample-100:sample+101,near36[:5]])*1e6
        axis.plot(rel/10,segment,lw=.8);axis.set(title=f'Uncentered event sample {sample}',xlabel='Nominal ms',ylabel='Source ×1e6')
    fig.suptitle('Cluster 36 / anomalous b248: contextual evidence; original events preserved')
    fig.savefig(output/'cluster36_context.png',dpi=130);plt.close(fig);pages.append(('Cluster 36 channel-248 context','cluster36_context.png'))
    write_csv(output/'raw_selection.csv',selections)
    fig,ax=plt.subplots(3,1,figsize=(14,10),layout='constrained')
    ax[0].plot(variability/np.median(variability));ax[0].axhline(2,color='red',label='existing screen threshold');ax[0].legend()
    ax[0].set(title='All-channel raw audit: median channel SD per nominal second',ylabel='Ratio to temporal median')
    near=np.argsort(np.linalg.norm(pos-pos[248],axis=1),kind='stable')[:5]
    for ch in near:ax[1].plot(zeros[:,ch]/10000,label=f'b{ch}')
    ax[1].set(title='Exact-zero fractions (no calibration assumed)',ylabel='Fraction');ax[1].legend(ncol=5)
    ax[2].scatter(np.arange(512),zeros.sum(axis=0)/NSAMPLES,s=8);ax[2].axvline(248,color='red')
    ax[2].set(title='Whole-recording zero fractions for all 512 channels',xlabel='Binary channel',ylabel='Fraction')
    fig.savefig(output/'disturbance_overview.png',dpi=130);plt.close(fig);pages.append(('Disturbance and zero-value overview','disturbance_overview.png'))
    # Inspect all 12 screened seconds plus start, previous flat second 226 and quiet controls.
    contexts=sorted(set([0,30,200,226]+screen.tolist()))
    for first in range(0,len(contexts),4):
        fig,axes=plt.subplots(4,2,figsize=(15,12),layout='constrained')
        for axrow,sec in zip(axes,contexts[first:first+4]):
            a=max(0,sec*10000-2500);b=min(NSAMPLES,(sec+1)*10000+2500)
            block=np.asarray(raw[a:b],dtype=np.float32)*1e6
            centered=block-np.median(block,axis=0)
            # Envelope every 10 samples, preserving extrema of the spatial median.
            spatial=np.median(centered,axis=1);n=len(spatial)//10
            tt=(a+np.arange(n)*10)/10000
            axrow[0].fill_between(tt,spatial[:n*10].reshape(n,10).min(axis=1),spatial[:n*10].reshape(n,10).max(axis=1),label='Spatial median envelope')
            axrow[0].plot(np.arange(a,b)/10000,block[:,248],lw=.5,alpha=.7,label='b248 uncentered')
            axrow[0].axvspan(sec,sec+1,color='red' if sec in screen else 'gray',alpha=.08)
            axrow[0].set(title=f'Second {sec}: raw source ×1e6',xlabel='Nominal seconds',ylabel='Numerically scaled');axrow[0].legend(fontsize=7)
            take=(times>=a)&(times<b);axrow[1].scatter(times[take]/10000,clusters[take],s=7)
            axrow[1].set(title='All original sorted events, no exclusions',xlabel='Nominal seconds',ylabel='Cluster ID',ylim=(-1,59))
        name=f'disturbance_context_{first//4+1}.png';fig.savefig(output/name,dpi=130);plt.close(fig);pages.append(('Raw disturbance context',name))
    print('Full raw scan and disturbance figures complete',flush=True)
    # Source check is bounded to the full channel 248 and three independent channel excerpts.
    source_check={'checked':False}
    if source_h5:
        import h5py
        with h5py.File(source_h5,'r') as h5:
            d=h5['signals'];assert d.shape==(2048,3000000) and d.dtype==np.float16
            original=np.asarray(d[int(mapping['original_channel_id'][248]),:],dtype=np.float32)
            np.testing.assert_array_equal(original,flat)
            for ch in [0,234,337]:
                for a in [0,1000000,2250000,2820000]:
                    np.testing.assert_array_equal(np.asarray(d[int(mapping['original_channel_id'][ch]),a:a+1000],dtype=np.float32),np.asarray(raw[a:a+1000,ch]))
            source_check=dict(checked=True,path=str(source_h5.resolve()),size_bytes=source_h5.stat().st_size,
                              dataset='signals',shape=list(d.shape),dtype=str(d.dtype),full_file_hashed=False,
                              full_channel_248_exact_match=True,additional_excerpt_values=12000,
                              scope='Full b248/global1921 plus 1000-sample excerpts at 0/1000000/2250000/2820000 on b0/234/337; not full-source identity')
    flat_summary=dict(channel=248,global_channel=int(mapping['original_channel_id'][248]),zero_samples=int(np.sum(flat==0)),
        zero_fraction=float(np.mean(flat==0)),runs_ge_100=len(starts),samples_in_runs_ge_100=int(np.sum(stops-starts)),
        positive_samples=int(np.sum(flat>0)),negative_samples=int(np.sum(flat<0)),minimum=float(flat.min()),maximum=float(flat.max()),
        longest_run_samples=int(np.max(stops-starts)),screen_seconds=screen.tolist(),screen_events=int(flagged.sum()),
        prior_sd_max_absolute_difference=float(np.max(abs(std-prior))),source_check=source_check)
    (output/'disturbance_summary.json').write_text(json.dumps(flat_summary,indent=2)+'\n')
    for name,item in manifest.items():assert sha(evidence/name)==item['sha256'],name
    assert sha(binary)==RAW_SHA
    provenance=dict(schema='pilot-round2-v1',script_sha256=sha(Path(__file__)),helper_sha256=sha(Path(__file__).with_name('review_pilot_round1.py')),
        raw_sha256=RAW_SHA,return_manifest_sha256=sha(evidence/'return-manifest.json'),
        spike_times_sha256=sha(src/'spike_times.npy'),spike_clusters_sha256=sha(src/'spike_clusters.npy'),python=sys.executable,
        numpy=np.__version__,nominal_fs=10000,physical_fs=10080,pairs=PAIRS,raw_context=[-100,100],raw_baseline=[-100,-31],raw_scale=1e6,
        raw_windows=len(selections),frozen_payloads_unchanged=len(manifest),raw_hash_before_after_matches=True,
        pca='All 3 stored PCs on intersection of physical channels; unstandardized, mean-centered SVD; balanced min(256,n_a,n_b) event ranks per group; projections of all events',
        labels_modified=False,events_removed=0,sorting_rerun=False)
    (output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    links=['pair_metrics.csv','cluster35_summary.json','cluster35_quarters.csv','disturbance_summary.json','disturbance_cluster_metrics.csv','channel_zero_fractions.csv','channel248_constant_runs.csv','raw_selection.csv','provenance.json']
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Pilot Round 2</title><style>body{font:16px system-ui;max-width:1500px;margin:30px auto;padding:20px}img{width:100%}p{line-height:1.6}</style><h1>Round 2: pairs, feature structure and disturbances</h1><p>Diagnostic evidence only. No merges, splits, masks, channel exclusions or label changes. Raw data are baseline centered only; no filtering/CAR. ×1e6 does not imply voltage calibration. Two-dimensional projections and low-count correlograms cannot establish isolation. Time axes use nominal 10,000 Hz; physical rate is 10,080 Hz.</p><p>'+ ' | '.join(f'<a href="{p}">{p}</a>' for p in links)+'</p>'+''.join(f'<h2>{title}</h2><img src="{name}">' for title,name in pages),encoding='utf-8')
    (output/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in output.iterdir() if p.is_file()},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',type=Path,required=True);p.add_argument('--binary',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--source-h5',type=Path)
    a=p.parse_args();run(a.evidence,a.binary,a.output,a.source_h5)
