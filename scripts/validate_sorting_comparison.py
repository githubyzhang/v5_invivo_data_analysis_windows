"""Independently audit saved cross-run counts, matches and common-channel means."""
import argparse
import csv
from pathlib import Path
import numpy as np
from run_sorting import ROOT,read,save,sha,verify_manifest


def rows(path):
    with path.open() as f:return list(csv.DictReader(f))


def run(report, output):
    report=report.resolve();output=output.resolve()
    assert not output.exists() and output.is_relative_to(ROOT/'results')
    verify_manifest(report/'report-manifest.json');summary=read(report/'summary.json')
    source_reports=[ROOT/p for p in summary['report_manifests']]
    datasets={};window_count=0
    masks=np.load(report/'fixed_quality_masks.npz')
    selections=rows(report/'raw_selection.csv');metrics=rows(report/'cluster_metrics.csv')
    for label,p in zip(['control','exclusion'],source_reports):
        assert sha(p/'report-manifest.json')==summary['report_manifests'][str(p.relative_to(ROOT))]
        verify_manifest(p/'report-manifest.json')
        src=ROOT/read(p/'summary.json')['run_path'];c=read(src/'config.json');verify_manifest(src/'output-manifest.json')
        events=np.load(p/'event_annotations.npz');times=events['sample_index'];cl=events['cluster_id']
        raw=np.memmap(ROOT/c['binary_path'],mode='r',dtype='<f4',shape=(c['samples'],c['binary_channels']))
        means=np.load(report/(label+'_raw_means.npz'));ids=means['cluster_ids'];saved=means['means']
        for k,cid in enumerate(ids):
            idx=np.flatnonzero((cl==cid)&(times>=100)&(times<c['samples']-100))
            expected=idx[np.unique(np.linspace(0,len(idx)-1,min(128,len(idx))).astype(int))] if len(idx) else idx
            selected=[x for x in selections if x['run']==label and int(x['cluster_id'])==cid]
            np.testing.assert_array_equal([int(x['original_event_index']) for x in selected],expected)
            stack=[]
            for row,i in zip(selected,expected):
                t=int(times[i]);assert int(row['sample_index'])==t
                w=np.array(raw[t-100:t+101],copy=True);w-=np.median(w[:70],axis=0);stack.append(w);window_count+=1
            mean=np.mean(stack,axis=0,dtype=np.float64)*1e6 if stack else np.full(saved[k].shape,np.nan)
            np.testing.assert_allclose(saved[k],mean,rtol=0,atol=0,equal_nan=True)
            counts=[np.sum((cl==cid)&(times>=a)&(times<b)) for a,b in zip(np.linspace(0,c['samples'],31)[:-1],np.linspace(0,c['samples'],31)[1:])]
            np.testing.assert_array_equal(means['counts_10seconds'][k],counts)
            metric=next(x for x in metrics if x['run']==label and int(x['cluster_id'])==cid)
            for name in masks.files:assert int(metric[name])==int(masks[name][times[cl==cid]].sum())
        datasets[label]=(times,cl,dict(zip(ids,saved)))
    # Fixed masks rebuilt from interval slices, independent of cumulative deltas.
    quality=ROOT/'results/extra4/w14-quality01';assert sha(quality/'manifest.json')==summary['quality_manifest_sha256']
    z=np.load(quality/'intervals.npz')['guard'];z=z[z[:,0]==c['shank_zero_based']]
    common=np.setdiff1d(np.arange(c['binary_channels']),c['excluded_binary_channels'])
    concurrency=np.zeros(c['samples'],np.int32)
    for ch in range(c['binary_channels']):
        mask=np.zeros(c['samples'],bool)
        for a,b in z[z[:,1]==ch,3:5]:mask[a:b]=True
        if ch in common:concurrency+=mask
        else:np.testing.assert_array_equal(mask,masks[f'b{ch}_guard'])
    np.testing.assert_array_equal(concurrency>0,masks['any_common_guard'])
    np.testing.assert_array_equal(concurrency>=np.ceil(len(common)/2),masks['half_common_guard'])
    geometry=np.genfromtxt(ROOT/c['mapping_path'],delimiter=',',names=True,dtype=int);positions=np.column_stack((geometry['x_um'],geometry['y_um']))
    inventories=[{int(x['cluster_id']):x for x in rows(p/'clusters.csv')} for p in source_reports]
    pairrows=rows(report/'pairs.csv');lookup={(int(x['control_cluster']),int(x['exclusion_cluster'])):x for x in pairrows}
    for ca in np.unique(datasets['control'][1]):
        for cb in np.unique(datasets['exclusion'][1]):
            a=datasets['control'][0][datasets['control'][1]==ca];b=datasets['exclusion'][0][datasets['exclusion'][1]==cb]
            # Search eligible right events with an advancing lower bound.
            used=0;matched=[]
            for t in a:
                j=max(used,int(np.searchsorted(b,int(t)-2)))
                if j<len(b) and b[j]<=int(t)+2:matched.append((t,b[j]));used=j+1
            if not matched:assert (ca,cb) not in lookup;continue
            row=lookup[ca,cb];n=len(matched)
            assert int(row['matched_within2'])==n and int(row['exact_matches'])==sum(x==y for x,y in matched)
            assert float(row['dice'])==2*n/(len(a)+len(b))
            assert float(row['control_fraction'])==n/len(a) and float(row['exclusion_fraction'])==n/len(b)
            peaks=[int(inv[cid]['peak_binary']) for inv,cid in zip(inventories,[ca,cb])]
            ordered=sorted(common,key=lambda ch:(min(np.linalg.norm(positions[ch]-positions[p]) for p in peaks),ch))[:12]
            x,y=[datasets[label][2][cid][80:141,ordered].ravel() for label,cid in zip(['control','exclusion'],[ca,cb])]
            if np.isfinite(x).all() and np.isfinite(y).all() and x.std()>0 and y.std()>0:
                np.testing.assert_allclose(float(row['raw_correlation']),np.corrcoef(x,y)[0,1],rtol=1e-12)
            else:assert row['raw_correlation']==''
    assert sha(ROOT/c['binary_path'])==summary['source_binary_sha256']
    verify_manifest(report/'report-manifest.json')
    output.mkdir(parents=True)
    checks=dict(state='passed',raw_windows_verified=window_count,pairs_verified=len(pairrows),fixed_quality_masks_verified=len(masks.files),clusters_verified=len(metrics),report_manifest_sha256=sha(report/'report-manifest.json'),script_sha256=sha(Path(__file__)))
    save(output/'checks.json',checks);save(output/'manifest.json',{p.name:sha(p) for p in output.iterdir()});print(checks)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.report,a.output)
