"""Independent source-interval, event-zone, raw-mean and saved-copy readback audit."""
import argparse
import csv
from pathlib import Path
import numpy as np
from run_sorting import ROOT,read,save,sha,verify_manifest


def rows(path):
    with path.open() as f:return list(csv.DictReader(f))


def run(report,output):
    report=report.resolve();output=output.resolve();assert not output.exists() and output.is_relative_to(ROOT/'results')
    verify_manifest(report/'report-manifest.json');summary=read(report/'summary.json');N=3000000
    quality=ROOT/'results/extra4/w14-quality01';assert sha(quality/'manifest.json')==summary['quality_manifest_sha256']
    verify_manifest(quality/'manifest.json');flat=np.load(quality/'intervals.npz')['flat'];flat=flat[flat[:,0]==3]
    concurrency=np.zeros(N,np.int32)
    for ch in range(512):
        mask=np.zeros(N,bool)
        for a,b in flat[flat[:,1]==ch,3:5].astype(int):mask[a:b]=True
        concurrency+=mask
    core=concurrency>=256
    edges=np.diff(np.r_[0,core.astype(int),0]);spans=np.column_stack((np.flatnonzero(edges==1),np.flatnonzero(edges==-1)))
    expanded=core.copy()
    for a,b in spans:expanded[max(0,a-500):min(N,b+500)]=True
    masks=dict(core=core,shoulder=expanded & ~core,away=~expanded)
    saved=np.load(report/'fixed_masks.npz');np.testing.assert_array_equal(saved['flat_concurrency'],concurrency);np.testing.assert_array_equal(saved['core_intervals'],spans)
    for name,mask in masks.items():
        np.testing.assert_array_equal(saved[name],mask);assert int(mask.sum())==summary['exposure_samples'][name]
    assert sum(int(m.sum()) for m in masks.values())==N
    metrics=rows(report/'cluster_zones.csv');episode_rows=rows(report/'episodes.csv');excerpts=rows(report/'excerpt_selection.csv');windows=0;excerpt_values=0
    for label,p in zip(['control','exclusion'],summary['report_manifests']):
        p=ROOT/p;assert sha(p/'report-manifest.json')==summary['report_manifests'][str(p.relative_to(ROOT))];verify_manifest(p/'report-manifest.json')
        r=ROOT/read(p/'summary.json')['run_path'];c=read(r/'config.json');assert c['samples']==N and c['shank_zero_based']==3;verify_manifest(r/'output-manifest.json')
        t=np.load(r/'kilosort4/spike_times.npy').ravel();cl=np.load(r/'kilosort4/spike_clusters.npy').ravel()
        raw=np.memmap(ROOT/c['binary_path'],mode='r',dtype='<f4',shape=(N,512));prepath=r/'kilosort4/temp_wh.dat'
        runrow=next(x for x in summary['runs'] if x['run']==label);assert sha(prepath)==runrow['preprocessed_sha256']
        pre=np.memmap(prepath,mode='r',dtype='<i2').reshape(-1,512);assert len(pre)==runrow['saved_samples'] and len(pre)>=N
        common=np.delete(np.arange(512),259)
        geometry=np.genfromtxt(ROOT/c['mapping_path'],delimiter=',',names=True,dtype=int);pos=np.column_stack((geometry['x_um'],geometry['y_um']))
        for row in [x for x in metrics if x['run']==label]:
            cid=int(row['cluster_id']);idx=np.flatnonzero(cl==cid);assert len(idx)==int(row['events'])
            z=np.load(report/f'{label}_c{cid}_zone_means.npz');peak=int(row['peak_binary'])
            channels=sorted(common,key=lambda ch:(np.linalg.norm(pos[ch]-pos[peak]),ch))[:8]
            np.testing.assert_array_equal(z['binary_channels'],channels);np.testing.assert_array_equal(z['global_channels'],geometry['original_channel_id'][channels])
            for name,mask in masks.items():
                n=int(mask[t[idx]].sum());exposure=int(mask.sum());assert int(row[name+'_events'])==n and int(row[name+'_exposure_samples'])==exposure
                assert float(row[name+'_nominal_rate'])==n*10000/exposure
                eligible=idx[mask[t[idx]] & (t[idx]>=100)&(t[idx]<N-100)]
                chosen=eligible[np.unique(np.linspace(0,len(eligible)-1,min(64,len(eligible))).astype(int))] if len(eligible) else eligible
                np.testing.assert_array_equal(z[name+'_event_indices'],chosen);assert len(chosen)==int(row[name+'_raw_windows'])
                stack=[]
                for i in chosen:
                    w=np.array(raw[t[i]-100:t[i]+101,channels],copy=True)*1e6
                    w-=np.median(w[:70],axis=0);stack.append(w);windows+=1
                mean=np.mean(stack,axis=0) if stack else np.full((201,8),np.nan)
                np.testing.assert_allclose(z[name+'_mean'],mean,rtol=0,atol=0,equal_nan=True)
            x,y=[z[name+'_mean'][80:141].ravel() for name in ['core','away']]
            if np.isfinite(x).all() and np.isfinite(y).all() and x.std()>0 and y.std()>0:
                np.testing.assert_allclose(float(row['core_away_raw_correlation']),np.corrcoef(x,y)[0,1],rtol=1e-12)
            else:assert row['core_away_raw_correlation']==''
        for row in [x for x in episode_rows if x['run']==label]:
            a,b=spans[int(row['episode'])];assert a==int(row['start_sample']) and b==int(row['stop_sample'])
            assert int(row['events'])==int(((t>=a)&(t<b)).sum())
        for name,mask in masks.items():assert runrow[name+'_events']==int(mask[t].sum())
        for row in excerpts:
            z=np.load(report/f'episode_{row["episode"]}.npz');a,b=int(row['start_sample']),int(row['stop_sample']);ch=z['binary_channels']
            np.testing.assert_array_equal(z['raw'],raw[a:b,ch]);np.testing.assert_array_equal(z[label+'_preprocessed_channels'],pre[a:b,ch])
            expected=np.percentile(np.abs(np.asarray(pre[a:b][:,common],dtype=np.float32)/200),99,axis=1)
            np.testing.assert_array_equal(z[label+'_preprocessed_p99'],expected);np.testing.assert_array_equal(z[label+'_event_indices'],np.flatnonzero((t>=a)&(t<b)))
            excerpt_values+=(b-a)*(len(ch)*2+len(common))
        assert sha(ROOT/c['binary_path'])==summary['source_binary_sha256']
    verify_manifest(report/'report-manifest.json');output.mkdir(parents=True)
    checks=dict(state='passed',fixed_source_masks_verified=3,clusters_verified=len(metrics),episode_rows_verified=len(episode_rows),raw_windows_verified=windows,excerpt_source_values_checked=excerpt_values,report_manifest_sha256=sha(report/'report-manifest.json'),script_sha256=sha(Path(__file__)))
    save(output/'checks.json',checks);save(output/'manifest.json',{p.name:sha(p) for p in output.iterdir()});print(checks)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.report,a.output)
