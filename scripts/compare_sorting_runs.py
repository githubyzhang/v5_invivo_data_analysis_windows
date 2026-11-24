"""Matched single-shank sensitivity screen; cross-run candidates, never merges."""
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_sorting import ROOT, read, save, sha, verify_manifest
from review_sorting_baseline import table


def matches(a, b, tolerance=2):
    """Chronological maximum-cardinality one-to-one matching for sorted times."""
    i = j = 0
    pairs = []
    while i < len(a) and j < len(b):
        if abs(int(a[i])-int(b[j])) <= tolerance:
            pairs.append((i,j)); i += 1; j += 1
        elif a[i] < b[j]:
            i += 1
        else:
            j += 1
    return np.asarray(pairs,dtype=np.int64).reshape(-1,2)


def run(control, exclusion, output):
    reports = [p.resolve() for p in [control,exclusion]]
    output = output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'results'):
        raise ValueError('Fresh project output required')
    summaries = [read(p/'summary.json') for p in reports]
    runs = [ROOT/s['run_path'] for s in summaries]
    configs = [read(p/'config.json') for p in runs]
    contracts = [read(p/'run_contract.json') for p in runs]
    for p,r in zip(reports,runs):
        verify_manifest(p/'report-manifest.json');verify_manifest(r/'output-manifest.json')
    for key in ['settings','versions','seed_policy','do_CAR','invert_sign','binary_sha256','sorter_source_sha256','save_preprocessed_copy']:
        assert contracts[0][key] == contracts[1][key],key
    for key in ['binary_path','mapping_path','samples','binary_channels','shank_zero_based','nominal_fs_hz','physical_fs_hz']:
        assert configs[0][key] == configs[1][key],key
    c = configs[0];N=c['samples'];fs=c['nominal_fs_hz'];s=c['shank_zero_based']
    assert not c['excluded_binary_channels'] and configs[1]['excluded_binary_channels']
    assert sha(ROOT/c['binary_path']) == contracts[0]['binary_sha256']
    common = np.setdiff1d(np.arange(c['binary_channels']),configs[1]['excluded_binary_channels'])
    geometry = np.genfromtxt(ROOT/c['mapping_path'],delimiter=',',names=True,dtype=int)
    pos = np.column_stack((geometry['x_um'],geometry['y_um']))
    raw = np.memmap(ROOT/c['binary_path'],mode='r',dtype='<f4',shape=(N,c['binary_channels']))
    quality=ROOT/'results/extra4/w14-quality01'
    verify_manifest(quality/'manifest.json')
    spans=np.load(quality/'intervals.npz')['guard'];spans=spans[spans[:,0]==s]
    masks={f'b{ch}_guard':np.zeros(N,bool) for ch in configs[1]['excluded_binary_channels']}
    common_delta=np.zeros(N+1,dtype=np.int32)
    for _,ch,_,a,b in spans:
        if ch in common: common_delta[a]+=1;common_delta[b]-=1
        else:masks[f'b{ch}_guard'][a:b]=True
    masks['any_common_guard']=common_delta[:-1].cumsum()>0
    masks['half_common_guard']=common_delta[:-1].cumsum()>=int(np.ceil(len(common)/2))
    output.mkdir(parents=True)
    np.savez_compressed(output/'fixed_quality_masks.npz',**masks)
    data=[];inventory=[];selections=[];runrows=[]
    for label,report,r,summary in zip(['control','exclusion'],reports,runs,summaries):
        events=np.load(report/'event_annotations.npz');t=events['sample_index'];cl=events['cluster_id'];ids=np.unique(cl)
        rows={int(x['cluster_id']):x for x in csv.DictReader((report/'clusters.csv').open())}
        means={};counts={};times={};peaks={}
        for cid in ids:
            idx=np.flatnonzero(cl==cid);times[cid]=t[idx];peaks[cid]=int(rows[cid]['peak_binary'])
            complete=idx[(t[idx]>=100)&(t[idx]<N-100)]
            chosen=complete[np.unique(np.linspace(0,len(complete)-1,min(128,len(complete))).astype(int))] if len(complete) else complete
            if len(chosen):
                wave=np.asarray(raw[t[chosen,None]+np.arange(-100,101)[None,:]],dtype=np.float32)
                wave-=np.median(wave[:,:70,:],axis=1)[:,None,:]
                means[cid]=wave.mean(axis=0,dtype=np.float64)*1e6
            else:means[cid]=np.full((201,c['binary_channels']),np.nan)
            counts[cid]=np.histogram(t[idx],bins=np.linspace(0,N,31))[0]
            for i in chosen:selections.append(dict(run=label,cluster_id=int(cid),original_event_index=int(i),sample_index=int(t[i])))
            inventory.append(dict(run=label,**rows[cid],**{k:int(v[t[idx]].sum()) for k,v in masks.items()}))
        np.savez_compressed(output/(label+'_raw_means.npz'),cluster_ids=ids,means=np.array([means[i] for i in ids]),counts_10seconds=np.array([counts[i] for i in ids]))
        data.append(dict(times=times,peaks=peaks,means=means,counts=counts,rows=rows,ids=ids))
        runrows.append(dict(run=label,run_id=summary['run_id'],events=len(t),clusters=len(ids),good=summary['good'],mua=summary['mua'],**{k:int(v[t].sum()) for k,v in masks.items()},**summary['flags']))
    pairs=[]
    for ca in data[0]['ids']:
        for cb in data[1]['ids']:
            a,b=data[0]['times'][ca],data[1]['times'][cb];matched=matches(a,b);n=len(matched)
            if not n:continue
            distances=np.minimum(np.linalg.norm(pos-pos[data[0]['peaks'][ca]],axis=1),np.linalg.norm(pos-pos[data[1]['peaks'][cb]],axis=1))
            channels=common[np.argsort(distances[common],kind='stable')[:12]]
            x,y=[d['means'][cid][80:141,channels].ravel() for d,cid in zip(data,[ca,cb])]
            corr=float(np.corrcoef(x,y)[0,1]) if np.isfinite(x).all() and np.isfinite(y).all() and np.std(x)>0 and np.std(y)>0 else None
            pairs.append(dict(control_cluster=int(ca),exclusion_cluster=int(cb),control_events=len(a),exclusion_events=len(b),matched_within2=n,exact_matches=int(np.sum(a[matched[:,0]]==b[matched[:,1]])),control_fraction=n/len(a),exclusion_fraction=n/len(b),dice=2*n/(len(a)+len(b)),raw_correlation=corr,peak_distance_um=float(np.linalg.norm(pos[data[0]['peaks'][ca]]-pos[data[1]['peaks'][cb]]))))
    best=[]
    for side in ['control','exclusion']:
        for cid in data[side=='exclusion']['ids']:
            choices=sorted([p for p in pairs if p[side+'_cluster']==cid],key=lambda p:(-p['dice'],-p['matched_within2'],p['control_cluster'],p['exclusion_cluster']))
            if choices:best.append(dict(direction=side,**choices[0]))
    table(output/'pairs.csv',pairs);table(output/'best_candidates.csv',best);table(output/'cluster_metrics.csv',inventory);table(output/'run_metrics.csv',runrows);table(output/'raw_selection.csv',selections)
    # Show best candidates for every automated-good cluster in either condition,
    # and control clusters peaking on either omitted electrode.
    focus=set()
    for row in best:
        side=row['direction'];j=int(side=='exclusion');cid=row[side+'_cluster']
        if data[j]['rows'][cid]['automated_label']=='good' or (j==0 and data[j]['peaks'][cid] in configs[1]['excluded_binary_channels']):
            focus.add((row['control_cluster'],row['exclusion_cluster']))
    pages=[]
    for ca,cb in sorted(focus):
        p=next(p for p in pairs if p['control_cluster']==ca and p['exclusion_cluster']==cb)
        dist=np.minimum(np.linalg.norm(pos-pos[data[0]['peaks'][ca]],axis=1),np.linalg.norm(pos-pos[data[1]['peaks'][cb]],axis=1))
        channels=common[np.argsort(dist[common],kind='stable')[:4]]
        fig,axes=plt.subplots(2,3,figsize=(13,7),layout='constrained')
        for axis,ch in zip(axes.ravel()[:4],channels):
            for label,d,cid in zip(['control','exclusion'],data,[ca,cb]):axis.plot(np.arange(-100,101)/fs*1000,d['means'][cid][:,ch],label=f'{label} c{cid}')
            axis.set(title=f'Common raw b{ch}',xlabel='Nominal ms',ylabel='Centered input x1e6')
        axes[0,0].legend(fontsize=8)
        for label,d,cid in zip(['control','exclusion'],data,[ca,cb]):axes.ravel()[4].stairs(d['counts'][cid],np.linspace(0,N/fs,31),label=label)
        axes.ravel()[4].set(xlabel='Nominal seconds',ylabel='Events / 10 nominal s');axes.ravel()[4].legend()
        axes.ravel()[5].axis('off');axes.ravel()[5].text(0,1,f'Control c{ca}: {p["control_events"]} events\nExclusion c{cb}: {p["exclusion_events"]} events\nMatched +/-2 samples: {p["matched_within2"]}\nDice: {p["dice"]:.3f}\nCommon-channel correlation: {p["raw_correlation"]}\nCandidate correspondence, not a merge.\nNo unit acceptance.\nRaw means: at most 128 complete events.\nNumerical scale, not voltage calibration.',va='top',fontsize=9,wrap=True)
        fig.suptitle(f'Shank{s} cross-run comparison: control c{ca} / exclusion c{cb}')
        name=f'pair_{ca}_{cb}.png';fig.savefig(output/name,dpi=110);plt.close(fig);pages.append(name)
    summary=dict(state='diagnostic_comparison_not_curated',runs=runrows,matched_settings=True,common_channels=len(common),fixed_mask_exposure_samples={k:int(v.sum()) for k,v in masks.items()},raw_windows=len(selections),focus_pairs=[list(p) for p in sorted(focus)],script_sha256=sha(Path(__file__)),source_binary_sha256=sha(ROOT/c['binary_path']),report_manifests={str(p.relative_to(ROOT)):sha(p/'report-manifest.json') for p in reports},quality_manifest_sha256=sha(quality/'manifest.json'),caveat='Pairwise one-to-one +/-2 sample matches may reuse events across different candidate pairs; not unique population recovery. Correlations use 12 common channels nearest either template peak, offsets -20..40; omitted channels excluded. Fixed-mask exposure uses the same electrodes/time for both runs; active-shank flags have different channel support. No censoring or neuron acceptance.')
    save(output/'summary.json',summary)
    html='<html><meta charset="utf-8"><title>Shank2 matched comparison</title><style>body{font:16px system-ui;max-width:1400px;margin:30px auto}img{width:100%}</style><h1>W15B: shank2 matched conditions</h1><p>Cross-run correspondences, not within-run merge proposals. No accepted neurons or selected working run.</p>'
    html+='<p><a href="run_metrics.csv">Run metrics</a> | <a href="cluster_metrics.csv">All clusters</a> | <a href="best_candidates.csv">Best candidates in both directions</a> | <a href="pairs.csv">All overlapping pairs</a> | <a href="summary.json">Methods/provenance</a></p>'
    html+='<p>Both conditions use the identical 512-channel binary and settings. The exclusion condition omits b54/global872 and b148/global353 in the sorter. Warning overlaps are not artifact classifications. Raw means are bounded samples.</p>'
    html+=''.join(f'<img src="{p}">' for p in pages)
    (output/'index.html').write_text(html,encoding='utf-8')
    for p in reports:verify_manifest(p/'report-manifest.json')
    save(output/'report-manifest.json',{p.name:sha(p) for p in output.iterdir()})
    print(summary)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--control',type=Path,required=True);p.add_argument('--exclusion',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.control,a.exclusion,a.output)
