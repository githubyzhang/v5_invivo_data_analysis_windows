"""Independent raw-window, feature mapping, lag, zero-run and exposure audit."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np


def run(report,evidence,binary):
    destination=report/'independent_checks.json'
    if destination.exists():raise ValueError('Audit already exists')
    source=evidence/'outputs/pilot01/kilosort4'
    times=np.load(source/'spike_times.npy').ravel();clusters=np.load(source/'spike_clusters.npy').ravel()
    pcs=np.load(source/'pc_features.npy');channels=np.load(source/'pc_feature_ind.npy')
    raw=np.memmap(binary,mode='r',dtype='<f4',shape=(3000000,512))
    count=0
    for path in report.glob('*_raw.npz'):
        saved=np.load(path,allow_pickle=False)
        np.testing.assert_array_equal(times[saved['event_indices']],saved['sample_indices'])
        for i,sample in enumerate(saved['sample_indices']):
            expected=np.array(raw[int(sample)-100:int(sample)+101])[:,saved['channels']]*1e6
            expected-=np.median(expected[:70],axis=0)
            np.testing.assert_array_equal(expected,saved['waves'][i]);count+=1
    metrics=list(csv.DictReader((report/'pair_metrics.csv').open()))
    for row in metrics:
        a,b=int(row['cluster_a']),int(row['cluster_b'])
        saved=np.load(report/f'pair_{a}_{b}_features.npz',allow_pickle=False)
        ta,tb=times[clusters==a],times[clusters==b]
        brute=(tb[:,None]-ta[None,:]).ravel();brute=brute[abs(brute)<=500]
        np.testing.assert_array_equal(np.sort(brute),np.sort(saved['cross_lags']))
        for bound in [10,20]:assert np.sum(abs(brute)<bound)==int(row[f'cross_pairs_abs_lt_{bound}'])
        assert np.sum(abs(brute)<=2)==int(row['cross_pairs_abs_le_2'])
        for cid,suffix in [(a,'a'),(b,'b')]:
            ids=saved['event_indices_'+suffix];assert np.all(clusters[ids]==cid)
            cols=[list(channels[cid]).index(int(ch)) for ch in saved['common_channels']]
            values=np.stack([pcs[ids,:,col] for col in cols],axis=2).reshape(len(ids),-1).astype(float)
            np.testing.assert_allclose((values-saved['center'])@saved['axes'].T,saved['projection_'+suffix],atol=1e-10)
    saved=np.load(report/'raw_per_second.npz');total=np.zeros(512,dtype=np.int64)
    for sec in range(300):
        block=np.asarray(raw[sec*10000:(sec+1)*10000])
        zeros=np.count_nonzero(block==0,axis=0)
        np.testing.assert_array_equal(zeros,saved['zero_counts'][sec]);total+=zeros
    flat=np.array(raw[:,248]);runs=list(csv.DictReader((report/'channel248_constant_runs.csv').open()))
    for row in runs:
        a,b=int(row['start_sample']),int(row['stop_sample_exclusive'])
        assert b-a==int(row['length_samples']) and b-a>=100
        assert np.all(flat[a:b]==float(row['value']))
        assert a==0 or flat[a-1]!=flat[a]
        assert b==len(flat) or flat[b]!=flat[b-1]
    # Independent zero-mask edges establish completeness of long zero runs.
    mask=np.r_[False,flat==0,False].astype(np.int8);changes=np.diff(mask)
    starts=np.flatnonzero(changes==1);stops=np.flatnonzero(changes==-1);keep=stops-starts>=100
    observed=[(int(r['start_sample']),int(r['stop_sample_exclusive'])) for r in runs if float(r['value'])==0]
    assert observed==list(zip(starts[keep],stops[keep]))
    for row in csv.DictReader((report/'disturbance_cluster_metrics.csv').open()):
        cid=int(row['cluster_id']);ts=times[clusters==cid]
        assert len(ts)==int(row['events'])
        assert np.isin(ts//10000,saved['screen_seconds']).sum()==int(row['screen_events'])
    manifest=json.loads((report/'report-manifest.json').read_text())
    for name,expected in manifest.items():
        with (report/name).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected
    destination.write_text(json.dumps(dict(raw_windows_checked=count,all_saved_values_exact=True,pair_lags_bruteforce_verified=len(metrics),
        pair_feature_projections_verified=True,all_channel_zero_counts_verified=True,channel248_runs_verified=len(runs),
        zero_run_completeness_verified=True,all_cluster_screen_counts_verified=True,packet_hashes_verified=len(manifest)),indent=2)+'\n')
    print(destination.read_text())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--binary',type=Path,required=True)
    a=p.parse_args();run(a.report,a.evidence,a.binary)
