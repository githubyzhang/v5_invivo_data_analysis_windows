"""Fresh Windows exports and source-level quality inventory; no sorting or masking."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import h5py
import numpy as np
from shank_input import ROOT, sha, channel_ids, probe
from review_pilot_artifacts import flat_intervals, expand_union

SOURCE = Path('C:/DATA/cnea_data/invivo/26-11-06/0192/extra_4_signals.h5')
SOURCE_SHA = '3bedaa51bca65205dcc81e25ef48f249c9f1ea34346f4cfd7327e26269bd9755'


def save_json(path, obj):
    path.write_text(json.dumps(obj, indent=2)+'\n', encoding='utf-8')


def save_csv(path, rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def export(source, expected_sha, output, shanks=(1,2,3), samples=3000000, chunk=25000):
    if output.exists() or not shanks or len(set(shanks))!=len(shanks) or any(s not in range(4) for s in shanks):
        raise ValueError('Fresh destination and distinct valid shanks required')
    if sha(source)!=expected_sha:raise ValueError('Source identity mismatch')
    if shutil.disk_usage(output.parent).free < samples*512*4*len(shanks)+1024**3:
        raise ValueError('Insufficient free space for exports plus 1 GiB reserve')
    ids=channel_ids();output.mkdir(parents=True)
    paths={s:output/f'extra4_shank{s}_float32.partial' for s in shanks}
    digests={s:hashlib.sha256() for s in shanks}
    with h5py.File(source,'r') as f:
        ds=f['signals']
        if ds.shape!=(2048,samples) or ds.dtype!=np.dtype('float16'):raise ValueError('Source shape/dtype mismatch')
        handles={s:p.open('xb') for s,p in paths.items()}
        try:
            for a in range(0,samples,chunk):
                block=ds[:,a:min(a+chunk,samples)]
                for s in shanks:
                    values=block[ids[s]].T.astype('<f4',order='C')
                    if not np.isfinite(values).all():raise ValueError('Nonfinite source')
                    payload=values.tobytes();handles[s].write(payload);digests[s].update(payload)
                if a%250000==0:print(f'Exported through {min(a+chunk,samples)}/{samples}',flush=True)
        finally:
            for handle in handles.values():handle.close()
    hashes={s:sha(p) for s,p in paths.items()}
    for s in shanks:
        assert paths[s].stat().st_size==samples*512*4
        assert hashes[s]==digests[s].hexdigest()
    # Independent readback: original source samples and mapping, not write buffers.
    arrays={s:np.memmap(p,mode='r',dtype='<f4',shape=(samples,512)) for s,p in paths.items()}
    with h5py.File(source,'r') as f:
        for a in range(0,samples,chunk):
            b=min(a+chunk,samples);block=f['signals'][:,a:b]
            for s in shanks:np.testing.assert_array_equal(arrays[s][a:b],block[ids[s]].T.astype('<f4'))
    for arr in arrays.values():arr._mmap.close()
    assert sha(source)==expected_sha
    outputs={}
    for s,p in paths.items():
        final=p.with_suffix('.bin');p.rename(final)
        save_json(output/f'probe_shank{s}.json',probe(s))
        save_csv(output/f'channel_map_shank{s}.csv',[dict(binary_channel=b,original_channel_id=int(g),shank_zero_based=s,row=b//4,column=b%4,x_um=(b%4)*30,y_um=(b//4)*30) for b,g in enumerate(ids[s])])
        outputs[str(s)]=dict(binary=final.name,sha256=hashes[s],samples=samples,channels=512,bytes=samples*512*4,source_values_verified=samples*512)
    save_json(output/'export.json',dict(state='verified',source=str(source),source_sha256=expected_sha,shanks=outputs,dtype='little-endian float32',conversion='exact cast only',nominal_fs_hz=10000,physical_fs_hz=10080,script_sha256=sha(Path(__file__))))
    save_json(output/'manifest.json',{p.name:sha(p) for p in output.iterdir()})
    return outputs


def quality(source, expected_sha, output):
    if output.exists():raise ValueError('Fresh quality output required')
    assert sha(source)==expected_sha
    detector=ROOT/'results/custom_detector/extra4_windows01/spikes.h5'
    detector_sha=sha(detector)
    with h5py.File(detector,'r') as f:prior=f['quality/flat_guard_intervals'][:]
    ids=channel_ids();rows=[];flats=[];guards=[];by_second=np.zeros((3,512,300),dtype=np.int32)
    concurrency=np.zeros((3,3000000),dtype=np.int16)
    output.mkdir(parents=True)
    with h5py.File(source,'r') as f:
        for s in (1,2,3):
            for b,gid in enumerate(ids[s]):
                x=f['signals'][gid,:].astype(np.float32);assert np.isfinite(x).all()
                spans=flat_intervals(x);padded=expand_union(spans,len(x))
                np.testing.assert_array_equal(padded,prior[prior[:,0]==gid,1:])
                mask=np.zeros(len(x),bool)
                for a,z in padded:mask[a:z]=True;guards.append((s,b,int(gid),int(a),int(z)))
                for a,z in spans:flats.append((s,b,int(gid),int(a),int(z),float(x[a])))
                by_second[s-1,b]=mask.reshape(300,10000).sum(1);concurrency[s-1]+=mask
                rows.append(dict(shank=s,binary_channel=b,global_channel=int(gid),zero_fraction=float(np.mean(x==0)),positive_fraction=float(np.mean(x>0)),negative_fraction=float(np.mean(x<0)),minimum=float(x.min()),maximum=float(x.max()),mean=float(x.mean(dtype=np.float64)),std=float(x.std(dtype=np.float64)),flat_samples=int(np.diff(spans,axis=1).sum()),longest_flat_samples=int(np.diff(spans,axis=1).max(initial=0)),guard_samples=int(mask.sum()),guard_fraction=float(mask.mean()),seconds_with_guard=int(np.count_nonzero(by_second[s-1,b])),guarded_quarters=[int(v) for v in by_second[s-1,b].reshape(4,75).sum(1)]))
                if b%128==0:print(f'Quality shank{s} channel{b}/512',flush=True)
    assert sha(source)==expected_sha and sha(detector)==detector_sha
    save_csv(output/'channels.csv',rows)
    np.savez_compressed(output/'intervals.npz',flat=np.asarray(flats),guard=np.asarray(guards,dtype=np.int64),guard_by_nominal_second=by_second,guard_concurrency=concurrency)
    save_json(output/'summary.json',dict(state='inventory_complete_review_pending',source_sha256=expected_sha,detector_sha256=detector_sha,channels=1536,samples_per_channel=3000000,all_native_guards_match=True,flat_minimum_samples=10,guard_padding_samples=500,script_sha256=sha(Path(__file__)),guard_helper_sha256=sha(ROOT/'scripts/review_pilot_artifacts.py'),quality_censoring=False,exclusions_adopted=False))
    save_json(output/'manifest.json',{p.name:sha(p) for p in output.iterdir()})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['export','quality']);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();allowed=ROOT/('data' if a.mode=='export' else 'results')
    if not out.is_relative_to(allowed):raise ValueError('Output outside designated project directory')
    (export if a.mode=='export' else quality)(SOURCE,SOURCE_SHA,out)
