"""Independent evidence audit plus transfer checks against frozen shank0 results."""
import argparse
import csv
from pathlib import Path
import numpy as np
from run_sorting import ROOT,read,save,sha,verify_manifest
from curation_review import extract,acg,criteria


def rows(path):
    with path.open() as f:return list(csv.DictReader(f))


def brute_lags(a,b,self_pairs=False):
    parts=[]
    for start in range(0,len(a),128):
        delta=b[None,:]-a[start:start+128,None];keep=abs(delta)<=500
        if self_pairs:keep[np.arange(len(delta)),np.arange(start,start+len(delta))]=False
        parts.append(delta[keep])
    return np.sort(np.concatenate(parts)) if parts else np.array([],int)


def run(report,output):
    report=report.resolve();output=output.resolve();assert not output.exists() and output.is_relative_to(ROOT/'results')
    verify_manifest(report/'report-manifest.json');meta=read(report/'summary.json');r=ROOT/meta['run_path'];c=read(r/'config.json');verify_manifest(r/'output-manifest.json')
    src=r/'kilosort4';t=np.load(src/'spike_times.npy').ravel();cl=np.load(src/'spike_clusters.npy').ravel();cmap=np.load(src/'channel_map.npy').ravel();pcb=cmap[np.load(src/'pc_feature_ind.npy')];pcs=np.load(src/'pc_features.npy')
    raw=np.memmap(ROOT/c['binary_path'],mode='r',dtype='<f4',shape=(c['samples'],c['binary_channels']))
    unitrows=rows(report/'unit_metrics.csv');qrows={(int(x['cluster_id']),int(x['quarter'])):x for x in rows(report/'quarter_metrics.csv')};windows=0
    def reread(indices,channels):
        nonlocal windows
        w=[]
        for i in indices:
            v=np.array(raw[t[i]-100:t[i]+101][:,channels],dtype=np.float32)*1e6;v-=np.median(v[:70],axis=0);w.append(v);windows+=1
        return np.array(w) if w else np.empty((0,201,len(channels)),np.float32)
    def selected(cid,maximum,a=0,b=None):
        if b is None:b=len(raw)
        eligible=np.flatnonzero((cl==cid)&(t>=max(100,a))&(t<min(len(raw)-100,b)))
        return eligible[np.unique(np.linspace(0,len(eligible)-1,min(len(eligible),maximum),dtype=int))] if len(eligible) else eligible
    for row in unitrows:
        cid=int(row['cluster_id']);times=t[cl==cid];z=np.load(report/f'unit_{cid}.npz');np.testing.assert_array_equal(z['selected'],selected(cid,256))
        w=reread(z['selected'],z['channels']);np.testing.assert_array_equal(w,z['waves'])
        expected=w.mean(0) if len(w) else np.full(z['reference'].shape,np.nan);np.testing.assert_allclose(expected,z['reference'],atol=0,rtol=0,equal_nan=True)
        np.testing.assert_array_equal(brute_lags(times,times,True),np.sort(z['acg_lags']))
        for q,(a,b) in enumerate(zip(np.linspace(0,len(raw),5,dtype=int)[:-1],np.linspace(0,len(raw),5,dtype=int)[1:])):
            np.testing.assert_array_equal(z[f'quarter_events_{q}'],selected(cid,128,a,b));qw=reread(z[f'quarter_events_{q}'],z['channels'])
            qm=qw.mean(0) if len(qw) else np.full(z['reference'].shape,np.nan);np.testing.assert_allclose(qm,z['means'][q],atol=0,rtol=0,equal_nan=True)
            assert int(qrows[cid,q+1]['events'])==int(((times>=a)&(times<b)).sum())
            if len(qw)>1:np.testing.assert_allclose(float(qrows[cid,q+1]['raw_correlation_to_pooled']),np.corrcoef(qm[80:141].ravel(),expected[80:141].ravel())[0,1],atol=1e-12)
    for row in rows(report/'pair_metrics.csv'):
        a,b=int(row['cluster_a']),int(row['cluster_b']);z=np.load(report/f'pair_{a}_{b}.npz');means=[]
        for suffix,cid in [('a',a),('b',b)]:
            idx=np.flatnonzero(cl==cid);np.testing.assert_array_equal(z['event_indices_'+suffix],idx);np.testing.assert_array_equal(z['selected_'+suffix],selected(cid,256))
            w=reread(z['selected_'+suffix],z['channels']);np.testing.assert_array_equal(w,z['waves_'+suffix]);means.append(w.mean(0) if len(w) else np.full((201,len(z['channels'])),np.nan))
            if z['projection_'+suffix].shape[1]:
                common=z['common_binary_channels'];cols=[list(pcb[cid]).index(ch) for ch in common];f=pcs[idx][:,:,cols].reshape(len(idx),-1).astype(float)
                np.testing.assert_allclose((f-z['center'])@z['axes'].T,z['projection_'+suffix],rtol=1e-10,atol=1e-10)
        np.testing.assert_array_equal(z['common_binary_channels'],np.intersect1d(pcb[a],pcb[b]))
        lags=brute_lags(t[cl==a],t[cl==b]);np.testing.assert_array_equal(lags,np.sort(z['cross_lags']))
        assert int(row['cross_pairs_abs_le2'])==int((abs(lags)<=2).sum()) and int(row['cross_pairs_abs_lt20'])==int((abs(lags)<20).sum())
        if row['raw_correlation']:np.testing.assert_allclose(float(row['raw_correlation']),np.corrcoef(means[0][80:141].ravel(),means[1][80:141].ravel())[0,1],atol=1e-12)
    # Replay new extraction, ACG and automated criteria on immutable pilot evidence.
    pilot=ROOT/'results/extra4_shank0/w7b-exclude248-01';w9=ROOT/'results/extra4_shank0/w9-good-review01';w8=ROOT/'results/extra4_shank0/w8-checkpoint01'
    for p,m in [(pilot,'output-manifest.json'),(w9,'report-manifest.json'),(w8,'report-manifest.json')]:verify_manifest(p/m)
    pt=np.load(pilot/'kilosort4/spike_times.npy').ravel();pc=np.load(pilot/'kilosort4/spike_clusters.npy').ravel()
    praw=np.memmap(ROOT/'data/extra4_shank0_float32.bin',mode='r',dtype='<f4',shape=(3000000,512));reference_units=0;reference_quarters=0
    for p in sorted(w9.glob('unit_*.npz')):
        cid=int(p.stem.split('_')[1]);z=np.load(p);idx=np.flatnonzero(pc==cid);chosen,w=extract(praw,pt,idx,z['channels'],256)
        np.testing.assert_array_equal(chosen,z['selected']);np.testing.assert_array_equal(w,z['waves']);np.testing.assert_array_equal(w.mean(0),z['reference']);np.testing.assert_array_equal(acg(pt[idx]),z['acg_lags'])
        for q in range(4):
            qi,qw=extract(praw,pt,idx[pt[idx]//750000==q],z['channels'],128);np.testing.assert_array_equal(qi,z[f'quarter_events_{q}']);np.testing.assert_array_equal(qw.mean(0),z['means'][q]);reference_quarters+=1
        reference_units+=1
    label_rows=[x for x in rows(w8/'label_criteria.csv') if x['run']=='exclude248']
    for row in label_rows:
        R,Q,label=criteria(pt[pc==int(row['cluster_id'])],10000);assert label==row['automated_label']
        if R is not None:np.testing.assert_allclose([R,Q],[float(row['R']),float(row['Q'])],rtol=1e-12,atol=1e-12)
    assert sha(ROOT/c['binary_path'])==c['pinned_files'][c['binary_path']];verify_manifest(report/'report-manifest.json')
    checks=dict(state='passed',unit_rows=len(unitrows),quarter_rows=len(qrows),pair_rows=len(meta['pairs']),raw_windows_verified=windows,reference_shank0_units_replayed=reference_units,reference_shank0_quarters_replayed=reference_quarters,reference_shank0_labels_replayed=len(label_rows),report_manifest_sha256=sha(report/'report-manifest.json'),script_sha256=sha(Path(__file__)))
    output.mkdir(parents=True);save(output/'checks.json',checks);save(output/'manifest.json',{p.name:sha(p) for p in output.iterdir()});print(checks)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.report,a.output)
