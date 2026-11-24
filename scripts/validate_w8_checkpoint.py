"""Independent audit of W8 raw excerpts, physical feature mapping and cross-lags."""
import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from review_pilot_round1 import sha,RAW_SHA,write_csv
from review_w7b import matched_pairs


def run(report):
    report=report.resolve()
    if not report.is_relative_to(ROOT/'results/extra4_shank0') or (report/'independent_checks.json').exists():
        raise ValueError('Fresh audit required')
    for name,digest in json.loads((report/'report-manifest.json').read_text()).items():assert sha(report/name)==digest
    src=ROOT/'results/extra4_shank0/w7b-exclude248-01/kilosort4'
    t=np.load(src/'spike_times.npy').ravel();cl=np.load(src/'spike_clusters.npy').ravel()
    pcs=np.load(src/'pc_features.npy');pcinds=np.load(src/'pc_feature_ind.npy');channel_map=np.load(src/'channel_map.npy').ravel()
    raw=np.memmap(ROOT/'data/extra4_shank0_float32.bin',mode='r',dtype='<f4',shape=(3000000,512))
    values=windows=pairs_checked=0

    def read(ids,channels):
        nonlocal values,windows
        out=[]
        for i in ids:
            a=np.array(raw[int(t[i])-100:int(t[i])+101,channels],dtype=np.float32)*1e6
            a-=np.median(a[:70],axis=0)[None,:]
            out.append(a);values+=a.size;windows+=1
        return np.asarray(out)

    for path in sorted(report.glob('pair_*.npz')):
        with np.load(path) as z:
            ca,cb=map(int,path.stem.split('_')[1:])
            for letter,cid in [('a',ca),('b',cb)]:
                ids=z['selected_'+letter];assert np.all(cl[ids]==cid)
                np.testing.assert_array_equal(read(ids,z['channels']),z['waves_'+letter])
                full=z['event_indices_'+letter];np.testing.assert_array_equal(full,np.flatnonzero(cl==cid))
                # Invert the binary map independently, then locate the original PC columns.
                cols=[np.flatnonzero(pcinds[cid]==np.flatnonzero(channel_map==ch)[0])[0] for ch in z['common_binary_channels']]
                features=pcs[full][:,:,cols].reshape(len(full),-1).astype(float)
                np.testing.assert_allclose((features-z['center'])@z['axes'].T,z['projection_'+letter],atol=1e-10)
            ta=t[cl==ca];tb=t[cl==cb];lags=[]
            for start in range(0,len(ta),128):
                delta=tb[None,:]-ta[start:start+128,None]
                lags.extend(delta[abs(delta)<=500].tolist())
            np.testing.assert_array_equal(np.sort(lags),np.sort(z['cross_lags']))
            pairs_checked+=1
    for path in report.glob('cluster_*_quarters.npz'):
        with np.load(path) as z:
            cid=int(path.stem.split('_')[1])
            for q in range(4):
                ids=z[f'event_indices_{q}'];assert np.all(cl[ids]==cid) and np.all(t[ids]//750000==q)
                np.testing.assert_array_equal(read(ids,z['channels']).mean(axis=0),z['means'][q])
            np.testing.assert_array_equal(read(z['reference_events'],z['channels']).mean(axis=0),z['reference'])
    # Explain the many-to-one candidate relation that contributes to the net label count change.
    old=ROOT/'results/extra4_shank0/w7b-control01/kilosort4'
    ot=np.load(old/'spike_times.npy').ravel();oc=np.load(old/'spike_clusters.npy').ravel()
    union=np.sort(ot[np.isin(oc,[31,33])]);nt=np.sort(t[cl==31]);matches=matched_pairs(union,nt)
    supplement=dict(control_clusters=[31,33],control_counts=[int(np.sum(oc==c)) for c in [31,33]],
        exclusion_candidate=31,exclusion_events=len(nt),union_events=len(union),union_matches_within2=len(matches),
        union_dice=2*len(matches)/(len(union)+len(nt)),status='Candidate consolidation, not an accepted neuron merge')
    (report/'old31_33_correspondence.json').write_text(json.dumps(supplement,indent=2)+'\n')
    prior=ROOT/'results/extra4_shank0/w7b-review01'
    with (prior/'cluster_metrics.csv').open() as f:metric={(r['run'],r['cluster_id']):r for r in csv.DictReader(f)}
    with (prior/'control_to_exclude248_top3.csv').open() as f:
        accounting=[dict(old_cluster=r['left_cluster'],candidate=r['right_cluster'],dice=r['dice'],
            old_label='good',candidate_label=metric['exclude248',r['right_cluster']]['automated_label'],status='candidate_not_identity')
            for r in csv.DictReader(f) if r['rank']=='1' and metric['control',r['left_cluster']]['automated_label']=='good']
    write_csv(report/'good_label_accounting.csv',accounting)
    for folder in [src.parent,old.parent]:
        for name,digest in json.loads((folder/'output-manifest.json').read_text()).items():assert sha(folder/name)==digest
    assert sha(ROOT/'data/extra4_shank0_float32.bin')==RAW_SHA
    checks=dict(raw_windows_checked=windows,raw_values_checked=values,pair_cross_lags_bruteforce_checked=pairs_checked,
        feature_physical_channel_mapping_and_projections_pass=True,quarter_means_exact=True,
        original_run_manifests_unchanged=True,script_sha256=sha(Path(__file__)))
    (report/'independent_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    (report/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in report.iterdir() if p.is_file() and p.name!='report-manifest.json'},indent=2)+'\n')
    print(json.dumps(checks,indent=2));print(json.dumps(supplement,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True)
    run(p.parse_args().report)
