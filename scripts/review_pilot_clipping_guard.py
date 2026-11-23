"""Replay the historical flat guard diagnostically; never censor sorted events."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from analysis.pilot import flat_mask, dilate
from scripts.review_pilot_round1 import sha, write_csv, RAW_SHA


def run(evidence,binary,output):
    evidence,binary,output=evidence.resolve(),binary.resolve(),output.resolve()
    if output.exists() or output.is_relative_to(evidence) or output.is_relative_to(binary.parent):raise ValueError('Fresh diagnostic output required')
    assert sha(binary)==RAW_SHA
    prior_path=evidence/'outputs/preflight/prior_flat_guards.csv'
    prior_hash=sha(prior_path)
    guards=np.loadtxt(prior_path,delimiter=',',dtype=np.int64)
    mapping=np.genfromtxt(evidence/'geometry/channel_map.csv',delimiter=',',names=True,dtype=int)
    source=evidence/'outputs/pilot01/kilosort4'
    times=np.load(source/'spike_times.npy').ravel();clusters=np.load(source/'spike_clusters.npy').ravel()
    peaks=np.ptp(np.load(source/'templates.npy'),axis=1).argmax(axis=1)
    positions=np.column_stack([mapping['x_um'],mapping['y_um']])
    # Full-recording raw replay for reviewed-cluster peaks and immediate b248 neighbors.
    targets=[0,1,2,3,5,6,12,26,27,29,31,33,34,35,36,45,48]
    selected=np.unique(np.r_[peaks[targets],np.argsort(np.linalg.norm(positions-positions[248],axis=1),kind='stable')[:5]])
    raw=np.memmap(binary,mode='r',dtype='<f4',shape=(3000000,512))
    output.mkdir(parents=True)
    channel_rows=[];event_rows=[];mask248=None
    for ch in range(512):
        gid=int(mapping['original_channel_id'][ch]);mask=np.zeros(3000000,dtype=bool)
        intervals=guards[guards[:,0]==gid,1:]
        for a,b in intervals:mask[a:b]=True
        flat_count=None;checked=bool(ch in selected)
        if checked:
            values=np.array(raw[:,ch]);flat=flat_mask(values,min_run=10);replayed=dilate(flat,500)
            np.testing.assert_array_equal(replayed,mask)
            # Independent interval-union calculation checks the historical helper.
            edges=np.r_[0,np.where(values[1:]!=values[:-1])[0]+1,len(values)]
            direct=np.zeros(len(values),dtype=bool)
            for a,b in zip(edges[:-1],edges[1:]):
                if b-a>=10:direct[max(0,a-500):min(len(values),b+500)]=True
            np.testing.assert_array_equal(mask,direct)
            flat_count=int(flat.sum())
        channel_rows.append(dict(binary_channel=ch,global_channel=gid,guard_intervals=len(intervals),guard_samples=int(mask.sum()),
            guard_fraction=float(mask.mean()),outside_guard_nominal_seconds=float((~mask).sum()/10000),
            replayed_from_raw=checked,flat_samples_ge_10=flat_count))
        for cid in np.flatnonzero(peaks==ch):
            ids=np.flatnonzero(clusters==cid)
            # Center and full [-20,+40] support overlap are separate descriptive quantities.
            prefix=np.r_[0,np.cumsum(mask,dtype=np.int64)]
            a=np.maximum(0,times[ids]-20);b=np.minimum(len(mask),times[ids]+41)
            event_rows.append(dict(cluster_id=int(cid),template_peak_binary=ch,template_peak_global=gid,events=len(ids),
                event_centers_in_peak_channel_guard=int(mask[times[ids]].sum()),
                event_supports_intersect_peak_channel_guard=int(np.sum(prefix[b]>prefix[a])),
                peak_channel_guard_samples=int(mask.sum()),guard_policy_applied=False))
        if ch==248:mask248=mask.copy()
    write_csv(output/'channel_guard_coverage.csv',channel_rows);write_csv(output/'cluster_guard_overlap.csv',event_rows)
    np.savez_compressed(output/'channel248_guard.npz',intervals=guards[guards[:,0]==1921,1:],guarded_per_second=mask248.reshape(300,10000).sum(axis=1))
    fig,ax=plt.subplots(2,1,figsize=(13,7),layout='constrained')
    ax[0].plot(np.arange(300),mask248.reshape(300,10000).mean(axis=1));ax[0].set(title='b248/global1921: historical 10-sample flat + 500-sample guard',xlabel='Nominal seconds',ylabel='Guarded fraction')
    entries=sorted(event_rows,key=lambda r:r['cluster_id'])
    ax[1].bar([r['cluster_id'] for r in entries],[r['event_centers_in_peak_channel_guard']/r['events'] for r in entries])
    ax[1].set(title='Sorted-event centers overlapping each cluster’s template-peak channel guard',xlabel='Original cluster ID',ylabel='Fraction; annotation only')
    fig.savefig(output/'guard_overlap.png',dpi=130);plt.close(fig)
    assert sha(binary)==RAW_SHA and sha(prior_path)==prior_hash
    summary=dict(schema='pilot-round2-clipping-guard-v1',source_method='analysis.pilot.flat_mask + dilate',
        minimum_run_samples=10,padding_samples_each_side=500,scope='Historical intervals for all 512 pilot channels; full raw replay on selected channels only',
        raw_replayed_binary_channels=selected.tolist(),all_replayed_masks_match_frozen=True,independent_interval_union_matches=True,
        frozen_guard_rows=len(guards),raw_sha256=RAW_SHA,prior_guards_sha256=prior_hash,
        script_sha256=sha(Path(__file__)),legacy_helper_sha256=sha(Path(__file__).resolve().parents[1]/'analysis/pilot.py'),
        channel248=channel_rows[248],cluster36=next(r for r in event_rows if r['cluster_id']==36),
        applied_to_kilosort=False,events_removed=0,
        caveat='A per-electrode detector guard is not a validated sorted-unit exposure mask. Multiple-channel support, CAR/whitening and temporal filtering require a separate policy; no automatic global union or zero-filling.')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (output/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in output.iterdir() if p.is_file()},indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.evidence,a.binary,a.output)
