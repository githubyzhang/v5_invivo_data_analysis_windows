"""Independent source-to-derived audit of accepted W12 tables and waveform means."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from review_w9_good import ROOT,RUN,rows,verify
from review_pilot_round1 import sha,RAW_SHA


def run(report):
    report=report.resolve()
    if not report.is_relative_to(ROOT/'results/extra4_shank0') or (report/'independent_checks.json').exists():
        raise ValueError('Fresh local audit required')
    verify(report,'report-manifest.json')
    revision=json.loads((ROOT/'configs/extra4_shank0_curated_v1.json').read_text());policy=json.loads((ROOT/revision['policy_path']).read_text())
    ids=revision['accepted_cluster_ids'];start,stop=policy['primary_analysis_interval_half_open']
    src=RUN/'kilosort4';t=np.load(src/'spike_times.npy').ravel();cl=np.load(src/'spike_clusters.npy').ravel();amp=np.load(src/'amplitudes.npy').ravel()
    expected=np.array([i for i,(sample,cid) in enumerate(zip(t,cl)) if cid in ids and start<=sample<stop])
    w11=ROOT/'results/extra4_shank0/w11-exposure-review01';flags=np.load(w11/'event_annotations.npz')
    derived=np.load(report/'spikes.npz');np.testing.assert_array_equal(expected,derived['original_event_index'])
    assert len(expected)==18252 and len(np.unique(expected))==len(expected)
    for name,source in [('sample_index',t),('cluster_id',cl),('sorter_amplitude',amp)]:np.testing.assert_array_equal(source[expected],derived[name])
    flag_names=[n for n in flags.files if n not in ['event_indices','sample_index','cluster_id']]
    for name in flag_names:np.testing.assert_array_equal(flags[name][expected],derived[name])
    table=rows(report/'spikes.csv');assert len(table)==len(expected)
    for r,i in zip(table,expected):
        assert int(r['original_event_index'])==i and int(r['sample_index'])==t[i] and int(r['cluster_id'])==cl[i]
        assert r['unit_id']==f'extra_4:shank0:w7b-exclude248-01:cluster{cl[i]}:v1'
        np.testing.assert_allclose([float(r['nominal_time_s']),float(r['physical_time_s']),float(r['sorter_amplitude'])],[t[i]/10000,t[i]/10080,amp[i]],rtol=1e-12)
        for n in flag_names:assert (r[n]=='True')==bool(flags[n][i])
    omitted=rows(report/'omitted_boundary_events.csv')
    assert sorted(int(r['cluster_id']) for r in omitted)==[32,38]
    np.testing.assert_array_equal(sorted(int(r['original_event_index']) for r in omitted),[i for i in range(len(t)) if cl[i] in ids and not start<=t[i]<stop])
    with (src/'cluster_KSLabel.tsv').open() as f:labels={int(r['cluster_id']):r['KSLabel'] for r in csv.DictReader(f,delimiter='\t')}
    for r in rows(report/'units.csv'):
        cid=int(r['cluster_id']);selected=expected[cl[expected]==cid];count=len(selected)
        assert r['original_automated_label']==labels[cid]
        assert count==int(r['analysis_events']) and sum(cl==cid)==int(r['original_events'])
        assert int(r['exposure_samples'])==stop-start
        np.testing.assert_allclose([float(r['nominal_rate']),float(r['physical_rate'])],[count*10000/(stop-start),count*10080/(stop-start)],rtol=1e-12)
        for column,flag in [('broad_warning_events','broad_warning'),('tight_warning_events','tight_warning'),('peak_guard_events','peak_guard')]:assert int(r[column])==sum(flags[flag][selected])
        assert int(r['broad_unavailable_events'])==sum(~flags['broad_available'][selected])
    bins=np.load(report/'rate_bins.npz');np.testing.assert_array_equal(bins['cluster_ids'],ids)
    for k,cid in enumerate(ids):
        values=t[expected[cl[expected]==cid]]
        for j,(a,b) in enumerate(zip(bins['bin_edges_samples'][:-1],bins['bin_edges_samples'][1:])):
            duration=max(0,min(b,stop)-max(a,start));count=int(sum((values>=a)&(values<b)))
            assert duration==bins['exposure_samples'][j] and count==bins['counts'][k,j]
            np.testing.assert_allclose([bins['nominal_rates'][k,j],bins['physical_rates'][k,j]],[count*10000/duration,count*10080/duration],rtol=1e-12)
        assert sum(bins['counts'][k])==len(values)
    for r in rows(report/'rate_bins.csv'):
        k=ids.index(int(r['cluster_id']));j=list(bins['bin_edges_samples'][:-1]).index(int(r['bin_start_sample']))
        assert int(r['events'])==bins['counts'][k,j] and int(r['exposure_samples'])==bins['exposure_samples'][j]
        np.testing.assert_allclose([float(r['nominal_rate']),float(r['physical_rate'])],[bins['nominal_rates'][k,j],bins['physical_rates'][k,j]])
    raw=np.memmap(ROOT/'data/extra4_shank0_float32.bin',mode='r',dtype='<f4',shape=(3000000,512));windows=values=0
    qrows={(int(r['cluster_id']),int(r['quarter'])):r for r in rows(report/'quarter_metrics.csv')}
    def read(indices,ch):
        nonlocal windows,values
        out=[]
        for i in indices:
            assert i in expected
            a=np.array(raw[int(t[i])-100:int(t[i])+101,ch],dtype=np.float32)*1e6
            a-=np.median(a[:70],axis=0)[None,:];out.append(a);windows+=1;values+=a.size
        return np.array(out)
    for cid in ids:
        with np.load(report/f'unit_{cid}.npz') as z:
            assert np.all(cl[z['selected']]==cid)
            w=read(z['selected'],z['channels']);np.testing.assert_array_equal(w,z['waves']);np.testing.assert_array_equal(w.mean(0),z['reference'])
            for q in range(4):
                indices=z[f'quarter_{q}_events'];assert np.all(t[indices]//750000==q) and np.all(cl[indices]==cid)
                mean=read(indices,z['channels']).mean(0);np.testing.assert_array_equal(mean,z['quarter_means'][q])
                allq=expected[(cl[expected]==cid)&(t[expected]//750000==q)];r=qrows[cid,q+1]
                assert len(allq)==int(r['events'])
                duration=max(0,min(stop,(q+1)*750000)-max(start,q*750000));assert duration==int(r['exposure_samples'])
                np.testing.assert_allclose([np.median(amp[allq]),np.corrcoef(mean[80:141].ravel(),z['reference'][80:141].ravel())[0,1]],[float(r['amplitude_median']),float(r['raw_correlation_to_pooled'])],rtol=1e-12)
    assert rows(report/'quality_sensitivity.csv')==[r for r in rows(w11/'sensitivity.csv') if int(r['cluster_id']) in ids]
    verify(RUN,'output-manifest.json');verify(w11,'report-manifest.json');assert sha(ROOT/'data/extra4_shank0_float32.bin')==RAW_SHA
    checks=dict(derived_event_rows_verified=len(expected),all_quality_flags_preserved=True,source_labels_unchanged=True,
        bin_counts_exposures_and_rates_checked=330,unit_summaries_checked=11,quarter_summaries_checked=44,
        raw_windows_checked=windows,raw_values_checked=values,boundary_omissions_exact=True,raw_and_source_manifests_unchanged=True,
        script_sha256=sha(Path(__file__)))
    (report/'independent_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    (report/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in report.iterdir() if p.is_file() and p.name!='report-manifest.json'},indent=2)+'\n')
    print(json.dumps(checks,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True)
    run(p.parse_args().report)
