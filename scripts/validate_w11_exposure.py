"""Independent interval, denominator, event-flag and raw-excerpt audit for W11."""
import argparse
import json
from pathlib import Path
import numpy as np
import h5py
from review_w9_good import ROOT,RUN,rows,verify
from review_pilot_round1 import sha,RAW_SHA

N=3000000


def run(report):
    report=report.resolve()
    if not report.is_relative_to(ROOT/'results/extra4_shank0') or (report/'independent_checks.json').exists():
        raise ValueError('Fresh local audit required')
    verify(report,'report-manifest.json');summary=json.loads((report/'summary.json').read_text())
    src=RUN/'kilosort4';t=np.load(src/'spike_times.npy').ravel();cl=np.load(src/'spike_clusters.npy').ravel()
    cmap=np.load(src/'channel_map.npy').ravel();pos=np.load(src/'channel_positions.npy');templates=np.load(src/'templates.npy')
    w7a=ROOT/'results/extra4_shank0/pilot01-w7a-reviewed'
    guardrows=rows(w7a/'guard_intervals.csv');flatrows=rows(w7a/'flat_runs.csv')
    masks={};gcount=np.zeros(N,np.int16);fcount=np.zeros(N,np.int16)
    for ch in range(512):
        m=np.zeros(N,bool)
        for r in guardrows:
            if int(r['binary_channel'])==ch:m[int(r['start']):int(r['stop'])]=True
        if ch in cmap:gcount+=m
        masks[ch]=m
    # Direct slice increments instead of generator's endpoint/cumsum sweep.
    for r in flatrows:
        if int(r['binary_channel']) in cmap:fcount[int(r['start']):int(r['stop'])]+=1
    def from_spans(spans):
        m=np.zeros(N,bool)
        for a,b in spans:m[int(a):int(b)]=True
        return m
    sidecar=ROOT/'results/custom_detector/kilosort_pilot01_quality_windows01/external_quality.h5'
    assert sha(sidecar)==summary['annotation_source_sha256']
    with h5py.File(sidecar,'r') as f:gm={name:from_spans(f['intervals/'+name][:]) for name in ['broad_warning','tight_warning','broad_available','tight_available']}
    boundary=np.ones(N,bool);boundary[100:N-100]=False
    gm.update(boundary=boundary,active_guard_any=gcount>0,active_guard_ge50=gcount>=256,active_flat_ge50=fcount>=256,excluded248_guard=masks[248])
    zglobal=np.load(report/'global_intervals.npz');event=np.load(report/'event_annotations.npz');unit=np.load(report/'unit_intervals.npz')
    np.testing.assert_array_equal(t,event['sample_index']);np.testing.assert_array_equal(cl,event['cluster_id']);np.testing.assert_array_equal(np.arange(len(t)),event['event_indices'])
    np.testing.assert_array_equal(gcount,zglobal['active_guard_count']);np.testing.assert_array_equal(fcount,zglobal['active_flat_count'])
    for name,m in gm.items():
        np.testing.assert_array_equal(m,from_spans(zglobal[name]));np.testing.assert_array_equal(m[t],event[name])
    sensitivity=rows(report/'sensitivity.csv');support=json.loads((report/'support_channels.json').read_text());checked=0
    for cid in np.unique(cl):
        ids=np.flatnonzero(cl==cid);peak=int(np.argmax(np.ptp(templates[cid],axis=0)))
        nearest=cmap[np.argsort(np.sqrt(((pos-pos[peak])**2).sum(1)),kind='stable')[:8]]
        np.testing.assert_array_equal(nearest,support[str(cid)])
        pm=masks[int(cmap[peak])];any8=np.zeros(N,bool);all8=np.ones(N,bool)
        for ch in nearest:any8|=masks[int(ch)];all8&=masks[int(ch)]
        touch=np.zeros(N,bool)
        for r in guardrows:
            if int(r['binary_channel'])==cmap[peak]:touch[max(0,int(r['start'])-100):min(N,int(r['stop'])+100)]=True
        for name,m in [('peak_guard',pm),('support8_any_guard',any8),('support8_all_guard',all8),('peak_window_touch_guard',touch)]:
            np.testing.assert_array_equal(m[t[ids]],event[name][ids]);np.testing.assert_array_equal(m,from_spans(unit[f'c{cid}_{name}']))
        removals={'full_recording':np.zeros(N,bool),'interior_only':boundary,
            'interior_without_broad':boundary|gm['broad_warning'],'interior_without_peak_guard':boundary|pm,
            'interior_without_peak_or_broad':boundary|pm|gm['broad_warning'],
            'interior_without_shared_guard50':boundary|(gcount>=256),'interior_without_shared_flat50':boundary|(fcount>=256),
            'interior_without_support8_any':boundary|any8,'interior_without_support8_all':boundary|all8,
            'interior_without_peak_window_touch':boundary|touch,'interior_broad_assessed_only':boundary|~gm['broad_available']}
        for r in [r for r in sensitivity if int(r['cluster_id'])==cid]:
            keep=~removals[r['scenario']];spans=unit[f'c{cid}_keep_{r["scenario"]}']
            np.testing.assert_array_equal(keep,from_spans(spans))
            assert np.all(spans[:,1]>spans[:,0]) and np.all(spans[1:,0]>=spans[:-1,1])
            denominator=int(sum(int(b)-int(a) for a,b in spans));assert denominator==int(keep.sum())==int(r['exposure_samples'])
            # Direct half-open event comparisons, independent of mask indexing.
            kept=sum(int(np.sum((t[ids]>=a)&(t[ids]<b))) for a,b in spans)
            assert kept==int(r['retained_events']) and len(ids)-kept==int(r['removed_events'])
            np.testing.assert_allclose(kept*10000/denominator,float(r['nominal_rate']),rtol=1e-12)
            np.testing.assert_allclose(kept*10080/denominator,float(r['physical_rate']),rtol=1e-12)
            checked+=1
    assert checked==58*11
    raw=np.memmap(ROOT/'data/extra4_shank0_float32.bin',mode='r',dtype='<f4',shape=(N,512));windows=values=0
    for path in report.glob('candidate_*_flagged.npz'):
        cid=int(path.stem.split('_')[1])
        with np.load(path) as z:
            affected=event['peak_guard']|event['broad_warning']|event['support8_all_guard']
            expected=np.flatnonzero((cl==cid)&~boundary[t]&affected);np.testing.assert_array_equal(expected,z['flagged_events'])
            for label in ['flagged','comparison']:
                ids=z[label+'_events'];assert np.all(cl[ids]==cid)
                if label=='comparison':assert not affected[ids].any()
                for j,i in enumerate(ids):
                    a=np.array(raw[int(t[i])-100:int(t[i])+101,z['channels']],dtype=np.float32)*1e6
                    a-=np.median(a[:70],axis=0)[None,:]
                    np.testing.assert_array_equal(a,z[label+'_waves'][j]);windows+=1;values+=a.size
    with np.load(report/'boundary_raw.npz') as z:
        for r in rows(report/'boundary_events.csv'):
            i=int(r['event_index']);cid=int(cl[i]);ch=int(cmap[np.ptp(templates[cid],axis=0).argmax()])
            a=np.array(raw[max(0,int(t[i])-100):min(N,int(t[i])+101),ch],dtype=np.float32)*1e6
            np.testing.assert_array_equal(a,z[f'event_{i}']);values+=a.size;windows+=1
    for folder,digest in summary['inputs'].items():
        path=ROOT/folder;manifest='output-manifest.json' if (path/'output-manifest.json').exists() else 'report-manifest.json'
        assert sha(path/manifest)==digest;verify(path,manifest)
    assert sha(ROOT/'data/extra4_shank0_float32.bin')==RAW_SHA
    checks=dict(scenario_rows_independently_checked=checked,active_channel_counts_exact=True,event_flags_and_support_maps_exact=True,
        raw_windows_checked=windows,raw_values_checked=values,source_manifests_and_raw_unchanged=True,
        script_sha256=sha(Path(__file__)))
    (report/'independent_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    (report/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in report.iterdir() if p.is_file() and p.name!='report-manifest.json'},indent=2)+'\n')
    print(json.dumps(checks,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True)
    run(p.parse_args().report)
