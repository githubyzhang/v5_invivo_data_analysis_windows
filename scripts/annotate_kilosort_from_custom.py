"""Add external detector quality annotations to the frozen pilot, without curation.

Requires a successful native full-recording detector run and exact source-to-binary
agreement. Candidate row flags are never copied onto sorter event rows.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import h5py
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def membership(samples,intervals):
    """Membership of integer samples in sorted disjoint half-open intervals."""
    intervals=np.asarray(intervals,dtype=np.int64).reshape(-1,2)
    if not len(intervals):return np.zeros(len(samples),dtype=bool)
    if np.any(intervals[:,1]<=intervals[:,0]) or np.any(intervals[1:,0]<intervals[:-1,1]):
        raise ValueError('Intervals must be sorted, nonempty and disjoint')
    index=np.searchsorted(intervals[:,0],samples,side='right')-1
    return (index>=0)&(samples<intervals[np.maximum(index,0),1])


def run(detector,evidence,binary,output):
    detector,evidence,binary,output=[p.resolve() for p in [detector,evidence,binary,output]]
    if output.exists() or not output.is_relative_to(ROOT/'results/custom_detector'):
        raise ValueError('Use a fresh directory in results/custom_detector')
    launch_path=detector.with_name(detector.name+'.launch.json');launch=json.loads(launch_path.read_text())
    if launch['action']!='detect' or launch['stage']!='complete' or not launch['source_hash_before_after_matches']:
        raise ValueError('Requires a completed, hash-verified native detection run')
    source=Path(launch['source']);source_hash=sha(source)
    if source_hash!=launch['source_sha256']:raise ValueError('Detector source changed')
    frozen=json.loads((evidence/'return-manifest.json').read_text())['files']
    for name,item in frozen.items():assert sha(evidence/name)==item['sha256'],name
    src=evidence/'outputs/pilot01/kilosort4'
    times=np.load(src/'spike_times.npy').ravel();clusters=np.load(src/'spike_clusters.npy').ravel()
    peaks=np.ptp(np.load(src/'templates.npy'),axis=1).argmax(axis=1)
    mapping=np.genfromtxt(evidence/'geometry/channel_map.csv',delimiter=',',names=True,dtype=int)
    gids=mapping['original_channel_id'];np.testing.assert_array_equal(mapping['binary_channel'],np.arange(512))
    assert len(times)==39620 and np.all((times>=0)&(times<3000000))
    binary_hash=sha(binary)
    if binary_hash!='11cd033eb0bda858f7598123a795f198078cc227d98d92543e8ea88f9e12eff0':raise ValueError('Not the frozen pilot binary')
    raw=np.memmap(binary,mode='r',dtype='<f4',shape=(3000000,512))
    # Verify all 1.536 billion mapped values, not merely filenames or a few excerpts.
    with h5py.File(source,'r') as f:
        d=f['signals'];assert d.shape==(2048,3000000) and d.dtype==np.float16
        for a in range(0,3000000,100000):
            block=d[:,a:a+100000]
            np.testing.assert_array_equal(block[gids].T.astype(np.float32),raw[a:a+100000])
            print(f'Source linkage verified through sample {a+100000}',flush=True)
    spikes=detector/'spikes.h5';warnings=detector/'coincidence/annotations.h5'
    hashes={str(p):sha(p) for p in [spikes,warnings,src/'spike_times.npy',src/'spike_clusters.npy']}
    masks={};interval_sets={}
    with h5py.File(spikes,'r') as f,h5py.File(warnings,'r') as w:
        assert f.attrs['complete'] and w.attrs['complete']
        assert f.attrs['source_channel_count']==2048 and f.attrs['source_sample_count']==3000000
        assert w.attrs['input_sha256']==hashes[str(spikes)]
        assert f.attrs['nominal_fs_hz']==10000 and f.attrs['physical_fs_hz']==10080
        for key in ['channel_id','sample_index']:np.testing.assert_array_equal(f['spikes/'+key][:],w['events/'+key][:])
        for profile in ['broad','tight']:
            group=w['warnings/'+profile]
            for field,flag in [('intervals','warning'),('available_intervals','available')]:
                ranges=group[field][:];masks[profile+'_'+flag]=membership(times,ranges);interval_sets[profile+'_'+flag]=ranges
            assert not np.any(masks[profile+'_warning']&~masks[profile+'_available'])
        for name in ['shared_available','shared10','shared20']:
            ranges=f['quality/'+name+'_intervals'][:];interval_sets[name]=ranges;masks[name]=membership(times,ranges)
        guards=f['quality/flat_guard_intervals'][:]
        masks['peak_channel_flat_guard']=np.zeros(len(times),bool)
        masks['peak_channel_detector_observable']=np.zeros(len(times),bool)
        valid=f['quality/valid_noise_window'][:];eligible=f['quality/reference_eligible'][:]
        for cid in np.unique(clusters):
            ids=np.flatnonzero(clusters==cid);gid=gids[peaks[cid]]
            guarded=membership(times[ids],guards[guards[:,0]==gid,1:])
            masks['peak_channel_flat_guard'][ids]=guarded
            masks['peak_channel_detector_observable'][ids]=eligible[gid]&valid[gid,times[ids]//10000]&~guarded&(times[ids]>=25)&(times[ids]<3000000-24)
        selected_default=str(w.attrs['default_warning'])
    output.mkdir(parents=True)
    sidecar=output/'external_quality.h5'
    with h5py.File(sidecar,'w') as f:
        f.attrs.update(schema='kilosort-external-detector-quality-v1',complete=False,annotation_only=True,
            source_sha256=source_hash,spike_times_sha256=hashes[str(src/'spike_times.npy')],spike_clusters_sha256=hashes[str(src/'spike_clusters.npy')],
            detector_spikes_sha256=hashes[str(spikes)],detector_annotations_sha256=hashes[str(warnings)],
            population_scope='2048-channel custom detector; applied by global time intervals to 512-channel shank0 sorter events',
            default_warning=selected_default,nominal_fs_hz=10000,physical_fs_hz=10080)
        f.create_dataset('events/final_event_index',data=np.arange(len(times)))
        f.create_dataset('events/sample_index',data=times);f.create_dataset('events/cluster_id',data=clusters)
        f.create_dataset('events/template_peak_global_channel',data=gids[peaks[clusters]])
        for key,value in masks.items():f.create_dataset('annotations/'+key,data=value)
        for key,value in interval_sets.items():f.create_dataset('intervals/'+key,data=value)
        f.attrs['complete']=True
    rows=[]
    for cid in np.unique(clusters):
        ids=clusters==cid
        rows.append(dict(cluster_id=int(cid),events=int(ids.sum()),**{k:int(v[ids].sum()) for k,v in masks.items()}))
    with (output/'cluster_overlap.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    # Independent interval-union oracle for all annotation columns sourced from time intervals.
    for key,ranges in interval_sets.items():
        oracle=np.zeros(3000000,dtype=bool)
        for a,b in ranges:oracle[int(a):int(b)]=True
        np.testing.assert_array_equal(masks[key],oracle[times])
    with h5py.File(sidecar,'r') as f:
        np.testing.assert_array_equal(f['events/sample_index'][:],times)
        np.testing.assert_array_equal(f['events/cluster_id'][:],clusters)
        for k,v in masks.items():np.testing.assert_array_equal(f['annotations/'+k][:],v)
    assert sha(source)==source_hash and sha(binary)==binary_hash
    for path,digest in hashes.items():assert sha(Path(path))==digest
    for name,item in frozen.items():assert sha(evidence/name)==item['sha256']
    summary=dict(schema='kilosort-external-detector-quality-v1',input_source=str(source),source_sha256=source_hash,
        source_linkage_all_1536000000_values_exact=True,detector_launch_sha256=sha(launch_path),script_sha256=sha(Path(__file__)),
        original_events=len(times),original_clusters=len(np.unique(clusters)),counts={k:int(v.sum()) for k,v in masks.items()},
        event_order_verified=True,interval_membership_independently_verified=True,frozen_payloads_unchanged=len(frozen),
        original_labels_changed=False,events_removed=0,sorting_rerun=False,
        caveat='Flags transfer by time intervals, not candidate row identity. Global 2048-channel coincidence is not shank-local evidence. Peak-channel observability is not sorted-unit exposure. Unavailable does not mean clean.')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (output/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in output.iterdir() if p.is_file()},indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['detector','evidence','binary','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.detector,a.evidence,a.binary,a.output)
