"""Single-shank baseline inventory and annotations, without curation or censoring."""
import argparse
import csv
import json
from pathlib import Path
import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family']='Arial'
from run_sorting import ROOT,read,save,sha,verify_manifest
from annotate_kilosort_from_custom import membership


def table(path, rows):
    if not rows:return
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def run(run_path,output):
    run_path=run_path.resolve();output=output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'results'):raise ValueError('Fresh project report required')
    verify_manifest(run_path/'output-manifest.json');c=read(run_path/'config.json');s=c['shank_zero_based'];N=c['samples'];fs=c['nominal_fs_hz'];physical=c['physical_fs_hz']
    assert read(run_path/'status.json')['state']=='complete_review_pending'
    src=run_path/'kilosort4';load=lambda n:np.load(src/(n+'.npy'),allow_pickle=False)
    t,cl,amp=[load(n).ravel() for n in ['spike_times','spike_clusters','amplitudes']]
    templates=load('templates');cmap=load('channel_map').ravel();positions=load('channel_positions')
    peaks=np.ptp(templates,axis=1).argmax(1);binary_peak=cmap[peaks]
    mapping=np.genfromtxt(ROOT/c['mapping_path'],delimiter=',',names=True,dtype=int);global_peak=mapping['original_channel_id'][binary_peak]
    labels={int(r['cluster_id']):r['KSLabel'] for r in csv.DictReader((src/'cluster_KSLabel.tsv').open(),delimiter='\t')}
    contam={int(r['cluster_id']):float(r['ContamPct']) for r in csv.DictReader((src/'cluster_ContamPct.tsv').open(),delimiter='\t')}
    detector=ROOT/'results/custom_detector/extra4_windows01';launch=read(detector.with_name(detector.name+'.launch.json'))
    input_meta=read(ROOT/'configs/extra4_remaining_shanks_w14.proposed.json')
    assert launch['stage']=='complete' and launch['source_hash_before_after_matches'] and launch['source_sha256']==input_meta['source_sha256']
    quality=ROOT/'results/extra4/w14-quality01';assert sha(quality/'manifest.json')==input_meta['evidence_sha256']['results/extra4/w14-quality01/manifest.json']
    verify_manifest(quality/'manifest.json');q=read(quality/'summary.json');detector_hash=sha(detector/'spikes.h5');assert detector_hash==q['detector_sha256']
    warning_hash=sha(detector/'coincidence/annotations.h5');intervals={};flags={}
    with h5py.File(detector/'spikes.h5','r') as f,h5py.File(detector/'coincidence/annotations.h5','r') as w:
        assert f.attrs['complete'] and w.attrs['complete'] and w.attrs['input_sha256']==detector_hash
        assert f.attrs['source_channel_count']==2048 and f.attrs['source_sample_count']==N
        assert f.attrs['nominal_fs_hz']==fs and f.attrs['physical_fs_hz']==physical
        for profile in ['broad','tight']:
            for field,suffix in [('intervals','warning'),('available_intervals','available')]:
                name=profile+'_'+suffix;intervals[name]=w['warnings/'+profile+'/'+field][:];flags[name]=membership(t,intervals[name])
        guards=f['quality/flat_guard_intervals'][:]
        for field in ['shared_available','shared10','shared20']:
            intervals[field]=f['quality/'+field+'_intervals'][:];flags[field]=membership(t,intervals[field])
    flags['peak_guard']=np.zeros(len(t),bool)
    ids=np.unique(cl)
    for cid in ids:
        sel=cl==cid;gid=global_peak[cid];flags['peak_guard'][sel]=membership(t[sel],guards[guards[:,0]==gid,1:])
    z=np.load(quality/'intervals.npz');delta=np.zeros(N+1,dtype=np.int32)
    spans=z['guard'];spans=spans[(spans[:,0]==s)&np.isin(spans[:,1],cmap)]
    np.add.at(delta,spans[:,3],1);np.add.at(delta,spans[:,4],-1);concurrency=delta[:-1].cumsum()
    flags['any_active_guard']=concurrency[t]>0;flags['half_active_guard']=concurrency[t]>=int(np.ceil(len(cmap)/2))
    flags['incomplete_context']=(t<100)|(t>=N-100)
    output.mkdir(parents=True)
    np.savez_compressed(output/'event_annotations.npz',original_event_index=np.arange(len(t)),sample_index=t,cluster_id=cl,template_peak_binary=binary_peak[cl],template_peak_global=global_peak[cl],**flags)
    np.savez_compressed(output/'intervals.npz',**intervals,active_guard_concurrency=concurrency)
    raw=np.memmap(ROOT/c['binary_path'],mode='r',dtype='<f4',shape=(N,c['binary_channels']))
    edges=np.r_[np.arange(0,N,fs),N];counts=[];rows=[];quarters=[];means=[];selections={};nearby={}
    for cid in ids:
        idx=np.flatnonzero(cl==cid);complete=idx[(t[idx]>=100)&(t[idx]<N-100)]
        chosen=complete[np.unique(np.linspace(0,len(complete)-1,min(64,len(complete))).astype(int))] if len(complete) else np.array([],dtype=int)
        channels=cmap[np.argsort(np.linalg.norm(positions-positions[peaks[cid]],axis=1),kind='stable')[:8]]
        if len(chosen):
            w=np.asarray(raw[t[chosen,None]+np.arange(-100,101)[None,:]][:,:,channels],dtype=np.float32)*1e6
            w-=np.median(w[:,:70],axis=1)[:,None,:];mean=w.mean(0)
        else:w=np.empty((0,201,len(channels)),dtype=np.float32);mean=np.full((201,len(channels)),np.nan)
        np.savez_compressed(output/f'raw_cluster_{cid}.npz',original_event_index=chosen,sample_index=t[chosen],binary_channels=channels,global_channels=mapping['original_channel_id'][channels],waves=w,mean=mean)
        means.append(mean);counts.append(np.histogram(t[idx],bins=edges)[0])
        isi=np.diff(t[idx]);r=dict(run_id=c['run_id'],shank_zero_based=s,cluster_id=int(cid),automated_label=labels[cid],review_state='unreviewed_not_accepted',events=len(idx),nominal_rate=len(idx)*fs/N,physical_rate=len(idx)*physical/N,peak_binary=int(binary_peak[cid]),peak_global=int(global_peak[cid]),sorter_contam_pct=contam[cid],isi_lt_1ms=int(sum(isi<fs*.001)),isi_lt_2ms=int(sum(isi<fs*.002)),amplitude_median=float(np.median(amp[idx])),raw_events_displayed=len(chosen),**{name:int(value[idx].sum()) for name,value in flags.items()})
        rows.append(r)
        qedges=np.linspace(0,N,5,dtype=int)
        for quarter,(a,b) in enumerate(zip(qedges[:-1],qedges[1:]),1):
            qi=idx[(t[idx]>=a)&(t[idx]<b)];quarters.append(dict(cluster_id=int(cid),quarter=quarter,events=len(qi),exposure_samples=int(b-a),nominal_rate=len(qi)*fs/(b-a),amplitude_median=float(np.median(amp[qi])) if len(qi) else None))
    table(output/'clusters.csv',rows);table(output/'quarters.csv',quarters)
    np.savez_compressed(output/'counts.npz',cluster_ids=ids,bin_edges_samples=edges,counts=counts)
    figures=[]
    fig,ax=plt.subplots(2,2,figsize=(14,9));fig.subplots_adjust(left=.08,right=.96,bottom=.08,top=.92,wspace=.30,hspace=.35)
    ax[0,0].bar(ids,[r['events'] for r in rows],color=['tab:blue' if labels[i]=='good' else 'gray' for i in ids]);ax[0,0].set(yscale='log',xlabel='Cluster ID',ylabel='Events (log)',title='Automated labels: blue good, gray mua; not curated')
    for label,color in [('good','tab:blue'),('mua','gray')]:
        chosen=ids[[labels[i]==label for i in ids]];p=peaks[chosen];ax[0,1].scatter(positions[p,0],positions[p,1],s=15,color=color,label=label,alpha=.6)
    ax[0,1].set(xlabel='x (um)',ylabel='y (um)',title='Whitened-template peaks; locations can overlap');ax[0,1].legend()
    ax[1,0].stairs(np.sum(counts,axis=0)/(np.diff(edges)/fs),edges/fs,label='All events')
    ax[1,0].stairs(np.histogram(t[flags['broad_warning']],edges)[0]/(np.diff(edges)/fs),edges/fs,label='Broad-warning events')
    ax[1,0].set(xlabel='Original nominal seconds',ylabel='Events / nominal second',title='Full recording; no quality censoring');ax[1,0].legend()
    for name,color in [('broad_warning','purple'),('peak_guard','red'),('incomplete_context','orange')]:
        ax[1,1].plot(ids,[r[name]/r['events']*100 for r in rows],'.',color=color,label=name)
    ax[1,1].set(xlabel='Cluster ID',ylabel='Events flagged (%)',title='Diagnostic annotations; not artifact classifications');ax[1,1].legend()
    fig.suptitle(f'{c["recording"]} shank{s} baseline: {len(t)} events / {len(ids)} clusters');fig.savefig(output/'overview.png',dpi=120,bbox_inches='tight');plt.close(fig);figures.append('overview.png')
    for start in range(0,len(ids),12):
        fig,axes=plt.subplots(4,3,figsize=(14,11));fig.subplots_adjust(left=.07,right=.97,bottom=.06,top=.92,wspace=.30,hspace=.70)
        for k,axis in enumerate(axes.ravel()):
            j=start+k
            if j>=len(ids):axis.axis('off');continue
            cid=ids[j];axis.plot(np.arange(-100,101)/fs*1000,means[j][:,:3]);axis.set_title(f'c{cid}: {labels[cid]}, n={rows[j]["events"]}',fontsize=10);axis.set(xlabel='Nominal ms',ylabel='Centered input x1e6')
        fig.suptitle('Diagnostic raw means: up to 64 complete events, three nearest channels\nNumerical scaling only; not voltage calibration or unit acceptance',fontsize=11)
        name=f'raw_means_{start//12+1}.png';fig.savefig(output/name,dpi=110,bbox_inches='tight');plt.close(fig);figures.append(name)
    verify_manifest(run_path/'output-manifest.json')
    assert sha(ROOT/c['binary_path'])==c['pinned_files'][c['binary_path']]
    assert sha(detector/'spikes.h5')==detector_hash and sha(detector/'coincidence/annotations.h5')==warning_hash
    summary=dict(schema='single-shank-baseline-review-v1',run_id=c['run_id'],run_path=str(run_path.relative_to(ROOT)),shank_zero_based=s,events=len(t),clusters=len(ids),good=sum(v=='good' for v in labels.values()),mua=sum(v=='mua' for v in labels.values()),raw_windows=sum(r['raw_events_displayed'] for r in rows),flags={name:int(value.sum()) for name,value in flags.items()},run_manifest_sha256=sha(run_path/'output-manifest.json'),detector_sha256=detector_hash,warning_sha256=warning_hash,quality_manifest_sha256=sha(quality/'manifest.json'),script_sha256=sha(Path(__file__)),warning_population_channels=2048,generic_shared_signal_warning_available=bool(len(intervals['shared_available'])),accepted_units=0,acceptance_state='not_curated',quality_censoring=False,original_outputs_modified=False)
    save(output/'summary.json',summary)
    body='<html><meta charset="utf-8"><title>Single-shank baseline</title><style>body{font:16px system-ui;max-width:1400px;margin:30px auto}img{width:100%}</style>'
    body+=f'<h1>{c["recording"]} shank{s}: diagnostic baseline</h1><p>{len(t)} events, {len(ids)} clusters, {summary["good"]} automated good / {summary["mua"]} mua. No units accepted or events removed. Cluster IDs belong only to this run.</p>'
    body+='<p>All rates use the full source duration. Sample indices are authoritative. Nominal fs=10000 Hz, physical fs=10080 Hz. Quality warnings are annotations, not artifact labels. Unavailable assessment is not clean time. Raw means are a bounded screen; curation is pending.</p><p><a href="clusters.csv">All-cluster inventory</a> | <a href="quarters.csv">Quarter summaries</a> | <a href="summary.json">Provenance/summary</a> | <a href="event_annotations.npz">Original event identities and flags</a></p>'
    body+=''.join(f'<h2>{n}</h2><img src="{n}">' for n in figures);(output/'index.html').write_text(body,encoding='utf-8')
    save(output/'report-manifest.json',{p.name:sha(p) for p in output.iterdir()})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.run,a.output)
