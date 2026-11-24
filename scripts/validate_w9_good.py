"""Independent W9 raw, timing, feature-map and annotation audit."""
import argparse
import json
from pathlib import Path
import numpy as np
import h5py
from review_w9_good import ROOT, RUN, W7, W8, TARGETS, rows, verify
from review_pilot_round1 import sha, RAW_SHA


def run(report):
    report=report.resolve()
    if not report.is_relative_to(ROOT/'results/extra4_shank0') or (report/'independent_checks.json').exists():
        raise ValueError('Fresh local audit required')
    verify(report,'report-manifest.json')
    src=RUN/'kilosort4'
    t=np.load(src/'spike_times.npy').ravel();cl=np.load(src/'spike_clusters.npy').ravel()
    cmap=np.load(src/'channel_map.npy').ravel();pci=np.load(src/'pc_feature_ind.npy');pcs=np.load(src/'pc_features.npy')
    raw=np.memmap(ROOT/'data/extra4_shank0_float32.bin',mode='r',dtype='<f4',shape=(3000000,512))
    windows=values=0

    def read(ids,channels):
        nonlocal windows,values
        snippets=[]
        for i in ids:
            a=np.array(raw[int(t[i])-100:int(t[i])+101,channels],dtype=np.float32)*1e6
            a-=np.median(a[:70],axis=0)[None,:]
            windows+=1;values+=a.size;snippets.append(a)
        return np.asarray(snippets)

    def lags(a,b,self_pairs=False):
        result=[]
        for start in range(0,len(a),128):
            delta=b[None,:]-a[start:start+128,None]
            keep=abs(delta)<=500
            if self_pairs:
                keep[np.arange(len(delta)),np.arange(start,start+len(delta))]=False
            result.extend(delta[keep].tolist())
        return np.sort(result)

    qrows={(int(r['cluster_id']),int(r['quarter'])):r for r in rows(report/'quarter_metrics.csv')}
    for cid in TARGETS:
        with np.load(report/f'unit_{cid}.npz') as z:
            ids=z['selected'];assert np.all(cl[ids]==cid)
            np.testing.assert_array_equal(read(ids,z['channels']),z['waves'])
            np.testing.assert_array_equal(z['waves'].mean(0),z['reference'])
            times=t[cl==cid]
            np.testing.assert_array_equal(lags(times,times,True),np.sort(z['acg_lags']))
            for q in range(4):
                qi=z[f'quarter_events_{q}'];assert np.all(cl[qi]==cid) and np.all(t[qi]//750000==q)
                mean=read(qi,z['channels']).mean(0)
                np.testing.assert_array_equal(mean,z['means'][q])
                r=qrows[cid,q+1]
                assert int(r['events'])==sum(times//750000==q) and int(r['selected'])==len(qi)
                central=slice(80,141)
                corr=np.corrcoef(mean[central].ravel(),z['reference'][central].ravel())[0,1]
                np.testing.assert_allclose(corr,float(r['raw_correlation_to_pooled']),atol=1e-12)
    pairs=0
    for path in report.glob('pair_*.npz'):
        ca,cb=map(int,path.stem.split('_')[1:])
        with np.load(path) as z:
            for label,cid in [('a',ca),('b',cb)]:
                ids=z['selected_'+label];assert np.all(cl[ids]==cid)
                np.testing.assert_array_equal(read(ids,z['channels']),z['waves_'+label])
                full=z['event_indices_'+label];np.testing.assert_array_equal(full,np.flatnonzero(cl==cid))
                if len(z['common_binary_channels']):
                    cols=[np.flatnonzero(pci[cid]==np.flatnonzero(cmap==ch)[0])[0] for ch in z['common_binary_channels']]
                    f=pcs[full][:,:,cols].reshape(len(full),-1).astype(float)
                    np.testing.assert_allclose((f-z['center'])@z['axes'].T,z['projection_'+label],atol=1e-10)
                else:assert z['projection_'+label].shape==(len(full),0)
            np.testing.assert_array_equal(lags(t[cl==ca],t[cl==cb]),np.sort(z['cross_lags']))
        pairs+=1
    # Recalculate interval membership directly from sample inequalities, independent
    # of the adapter's membership/searchsorted implementation and W7 CSV values.
    evidence=ROOT/'worker_returns/extra4_shank0/pilot01/received'
    guards=np.loadtxt(evidence/'outputs/preflight/prior_flat_guards.csv',delimiter=',',dtype=np.int64)
    geometry=np.genfromtxt(evidence/'geometry/channel_map.csv',delimiter=',',names=True,dtype=int)
    sidecar=ROOT/'results/custom_detector/kilosort_pilot01_quality_windows01/external_quality.h5'
    assert sha(sidecar)=='df0289595e71f44b14a7755d6beea3a2b99a500cde3bec81fe8bc82d9d149d8f'
    def count(times,intervals):
        mask=np.zeros(len(times),bool)
        for start,stop in intervals:mask|=(times>=start)&(times<stop)
        return int(mask.sum())
    with h5py.File(sidecar,'r') as f:
        intervals={n:f['intervals/'+n][:] for n in ['broad_warning','tight_warning','broad_available']}
    for r in rows(report/'unit_metrics.csv'):
        cid=int(r['cluster_id']);times=np.sort(t[cl==cid]);assert len(times)==int(r['events'])
        assert sum(np.diff(times)<10)==int(r['isi_lt10']) and sum(np.diff(times)<20)==int(r['isi_lt20'])
        gid=int(geometry['original_channel_id'][int(r['template_peak_binary'])])
        assert gid==int(r['template_peak_global'])
        assert count(times,guards[guards[:,0]==gid,1:])==int(r['peak_guard_events'])
        for name,spans in intervals.items():assert count(times,spans)==int(r[name+'_events'])
    for folder,manifest in [(RUN,'output-manifest.json'),(W7,'report-manifest.json'),(W8,'report-manifest.json')]:verify(folder,manifest)
    assert sha(ROOT/'data/extra4_shank0_float32.bin')==RAW_SHA
    checks=dict(raw_windows_checked=windows,raw_values_checked=values,unit_acgs_bruteforce_checked=len(TARGETS),
        pair_cross_lags_bruteforce_checked=pairs,physical_pc_mapping_and_projections_pass=True,
        quarter_means_and_correlations_pass=True,unit_event_counts_isi_and_annotations_pass=True,
        source_manifests_and_raw_unchanged=True,script_sha256=sha(Path(__file__)),
        annotation_source_sha256=sha(sidecar),guards_sha256=sha(evidence/'outputs/preflight/prior_flat_guards.csv'))
    (report/'independent_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    (report/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in report.iterdir() if p.is_file() and p.name!='report-manifest.json'},indent=2)+'\n')
    print(json.dumps(checks,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True)
    run(p.parse_args().report)
