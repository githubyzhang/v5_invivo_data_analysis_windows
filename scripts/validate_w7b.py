"""Independent raw-mean, metric and historical-control identity checks for W7B."""
import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.review_pilot_round1 import sha, RAW_SHA


def run(report,control,exclusion):
    report=report.resolve()
    if not report.is_relative_to(ROOT/'results/extra4_shank0') or (report/'independent_checks.json').exists():
        raise ValueError('Fresh audit in local review required')
    for name,digest in json.loads((report/'report-manifest.json').read_text()).items():
        assert sha(report/name)==digest
    evidence=ROOT/'worker_returns/extra4_shank0/pilot01/received'
    paths=dict(historical=evidence/'outputs/pilot01/kilosort4',control=control/'kilosort4',exclude248=exclusion/'kilosort4')
    identity={}
    for name in ['spike_times.npy','spike_clusters.npy','templates.npy','amplitudes.npy','channel_map.npy','cluster_KSLabel.tsv','cluster_ContamPct.tsv']:
        identity[name]=sha(paths['historical']/name)==sha(paths['control']/name)
        assert identity[name],name
    binary=ROOT/'data/extra4_shank0_float32.bin'
    assert sha(binary)==RAW_SHA
    raw=np.memmap(binary,mode='r',dtype='<f4',shape=(3000000,512))
    with (report/'raw_selection.csv').open() as f: selections=list(csv.DictReader(f))
    with (report/'cluster_metrics.csv').open() as f: metrics=list(csv.DictReader(f))
    checked=0
    for label,path in paths.items():
        times=np.load(path/'spike_times.npy').ravel();clusters=np.load(path/'spike_clusters.npy').ravel()
        with np.load(report/(label+'_raw_means.npz')) as z:
            for cid in z['cluster_ids']:
                selected=[r for r in selections if r['run']==label and int(r['cluster_id'])==cid]
                total=np.zeros((512,201),np.float64)
                for row in selected:
                    event,sample=int(row['final_event_index']),int(row['sample_index'])
                    assert times[event]==sample and clusters[event]==cid
                    window=np.array(raw[sample-100:sample+101].T)
                    window-=np.median(window[:,:70],axis=1)[:,None]
                    total+=window
                    checked+=window.size
                if selected:
                    np.testing.assert_array_equal((total/len(selected)).astype(np.float32),z['means'][cid])
                else:
                    assert np.isnan(z['means'][cid]).all()
                t=times[clusters==cid]
                row=next(r for r in metrics if r['run']==label and int(r['cluster_id'])==cid)
                assert int(row['events'])==len(t)
                assert int(row['isi_lt10'])==sum(np.diff(np.sort(t))<10)
                np.testing.assert_array_equal(z['counts_10seconds'][cid],np.bincount(t//100000,minlength=30))
        print(f'Independent raw mean audit passed: {label}',flush=True)
    np.testing.assert_array_equal(np.load(paths['exclude248']/'channel_map.npy').ravel(),np.delete(np.arange(512),248))
    for name,item in json.loads((evidence/'return-manifest.json').read_text())['files'].items():
        assert sha(evidence/name)==item['sha256']
    for folder in [control,exclusion]:
        for name,digest in json.loads((folder/'output-manifest.json').read_text()).items():
            assert sha(folder/name)==digest
    assert sha(binary)==RAW_SHA
    checks=dict(historical_control_byte_identity=identity,raw_values_independently_checked=checked,
        raw_selected_windows=len(selections),means_exact=True,counts_and_isi_checked=True,
        exclusion_channel_map_verified=True,all_input_manifests_unchanged=True,script_sha256=sha(Path(__file__)))
    (report/'independent_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    (report/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in report.iterdir() if p.is_file() and p.name!='report-manifest.json'},indent=2)+'\n')
    print(json.dumps(checks,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['report','control','exclusion']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();run(a.report,a.control,a.exclusion)
