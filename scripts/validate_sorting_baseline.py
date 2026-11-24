"""Independent baseline table, interval projection and raw-excerpt audit."""
import argparse
import csv
from pathlib import Path
import h5py
import numpy as np
from run_sorting import ROOT,read,save,sha,verify_manifest


def rows(path,delimiter=','):
    with path.open() as f:return list(csv.DictReader(f,delimiter=delimiter))


def run(report,output):
    report=report.resolve();output=output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'results'):raise ValueError('Fresh audit output required')
    verify_manifest(report/'report-manifest.json');summary=read(report/'summary.json');run_path=ROOT/summary['run_path']
    assert sha(run_path/'output-manifest.json')==summary['run_manifest_sha256'];verify_manifest(run_path/'output-manifest.json')
    c=read(run_path/'config.json');src=run_path/'kilosort4';N=c['samples'];fs=c['nominal_fs_hz'];physical=c['physical_fs_hz'];s=c['shank_zero_based']
    t=np.load(src/'spike_times.npy').ravel();cl=np.load(src/'spike_clusters.npy').ravel();amp=np.load(src/'amplitudes.npy').ravel()
    z=np.load(report/'event_annotations.npz');np.testing.assert_array_equal(z['original_event_index'],np.arange(len(t)))
    np.testing.assert_array_equal(z['sample_index'],t);np.testing.assert_array_equal(z['cluster_id'],cl)
    cmap=np.load(src/'channel_map.npy').ravel();positions=np.load(src/'channel_positions.npy');templates=np.load(src/'templates.npy')
    peaks=(templates.max(axis=1)-templates.min(axis=1)).argmax(1);mapping=np.genfromtxt(ROOT/c['mapping_path'],delimiter=',',names=True,dtype=int)
    np.testing.assert_array_equal(z['template_peak_binary'],cmap[peaks[cl]])
    np.testing.assert_array_equal(z['template_peak_global'],mapping['original_channel_id'][cmap[peaks[cl]]])
    detector=ROOT/'results/custom_detector/extra4_windows01';assert sha(detector/'spikes.h5')==summary['detector_sha256'];assert sha(detector/'coincidence/annotations.h5')==summary['warning_sha256']
    expected={};interval_file=np.load(report/'intervals.npz')
    def mask(spans):
        result=np.zeros(N,dtype=bool)
        for a,b in spans:result[int(a):int(b)]=True
        return result
    with h5py.File(detector/'spikes.h5','r') as f,h5py.File(detector/'coincidence/annotations.h5','r') as w:
        for profile in ['broad','tight']:
            for name,suffix in [('intervals','warning'),('available_intervals','available')]:
                spans=w[f'warnings/{profile}/{name}'][:];key=profile+'_'+suffix
                np.testing.assert_array_equal(interval_file[key],spans);expected[key]=mask(spans)[t]
        for field in ['shared_available','shared10','shared20']:
            spans=f['quality/'+field+'_intervals'][:];np.testing.assert_array_equal(interval_file[field],spans);expected[field]=mask(spans)[t]
        guards=f['quality/flat_guard_intervals'][:]
    expected['peak_guard']=np.zeros(len(t),bool);concurrency=np.zeros(N,dtype=np.int16)
    for b in cmap:
        gid=mapping['original_channel_id'][b];m=mask(guards[guards[:,0]==gid,1:]);concurrency+=m
        selected=z['template_peak_binary']==b;expected['peak_guard'][selected]=m[t[selected]]
    expected['any_active_guard']=concurrency[t]>0;expected['half_active_guard']=concurrency[t]>=np.ceil(len(cmap)/2)
    expected['incomplete_context']=(t<100)|(t+100>=N)
    np.testing.assert_array_equal(concurrency,interval_file['active_guard_concurrency'])
    for name,value in expected.items():np.testing.assert_array_equal(z[name],value);assert summary['flags'][name]==int(value.sum())
    for profile in ['broad','tight']:assert not np.any(expected[profile+'_warning']&~expected[profile+'_available'])
    labels={int(r['cluster_id']):r['KSLabel'] for r in rows(src/'cluster_KSLabel.tsv','\t')}
    contamination={int(r['cluster_id']):float(r['ContamPct']) for r in rows(src/'cluster_ContamPct.tsv','\t')}
    inventory=rows(report/'clusters.csv');assert {int(r['cluster_id']) for r in inventory}==set(np.unique(cl))
    bins=np.load(report/'counts.npz');quarter_rows=rows(report/'quarters.csv');raw=np.memmap(ROOT/c['binary_path'],mode='r',dtype='<f4',shape=(N,c['binary_channels']))
    windows=0;values=0
    for r in inventory:
        cid=int(r['cluster_id']);idx=np.flatnonzero(cl==cid);assert len(idx)==int(r['events']) and r['automated_label']==labels[cid]
        assert r['review_state']=='unreviewed_not_accepted' and r['run_id']==c['run_id'] and int(r['shank_zero_based'])==s
        assert int(r['peak_binary'])==cmap[peaks[cid]] and int(r['peak_global'])==mapping['original_channel_id'][cmap[peaks[cid]]]
        assert float(r['sorter_contam_pct'])==contamination[cid]
        np.testing.assert_allclose([float(r['nominal_rate']),float(r['physical_rate']),float(r['amplitude_median'])],[len(idx)*fs/N,len(idx)*physical/N,np.median(amp[idx])],rtol=1e-12)
        for name,value in expected.items():assert int(r[name])==int(value[idx].sum())
        for ms in [1,2]:assert int(r[f'isi_lt_{ms}ms'])==np.count_nonzero(np.diff(t[idx])<fs*ms/1000)
        k=list(bins['cluster_ids']).index(cid)
        oracle=[np.count_nonzero((t[idx]>=a)&(t[idx]<b)) for a,b in zip(bins['bin_edges_samples'][:-1],bins['bin_edges_samples'][1:])]
        np.testing.assert_array_equal(oracle,bins['counts'][k]);assert sum(oracle)==len(idx)
        for row in [q for q in quarter_rows if int(q['cluster_id'])==cid]:
            q=int(row['quarter'])-1;edges=np.linspace(0,N,5,dtype=int);a,b=edges[q:q+2];sel=idx[(t[idx]>=a)&(t[idx]<b)]
            assert int(row['events'])==len(sel) and int(row['exposure_samples'])==b-a
            np.testing.assert_allclose(float(row['nominal_rate']),len(sel)*fs/(b-a))
            if len(sel):assert float(row['amplitude_median'])==np.median(amp[sel])
            else:assert row['amplitude_median']==''
        with np.load(report/f'raw_cluster_{cid}.npz') as w:
            chosen=w['original_event_index'];assert np.all(cl[chosen]==cid) and len(chosen)==int(r['raw_events_displayed'])
            np.testing.assert_array_equal(w['sample_index'],t[chosen]);channels=w['binary_channels']
            wanted=cmap[np.argsort(((positions-positions[peaks[cid]])**2).sum(1),kind='stable')[:8]]
            np.testing.assert_array_equal(channels,wanted);np.testing.assert_array_equal(w['global_channels'],mapping['original_channel_id'][channels])
            if len(chosen):
                measured=[]
                for i in chosen:
                    a=np.array(raw[int(t[i])-100:int(t[i])+101,channels],dtype=np.float32)*1e6
                    a-=np.median(a[:70],axis=0)[None,:];measured.append(a)
                measured=np.array(measured);np.testing.assert_array_equal(w['waves'],measured);np.testing.assert_array_equal(w['mean'],measured.mean(0));values+=measured.size
            else:assert w['waves'].shape==(0,201,len(channels)) and np.isnan(w['mean']).all()
            windows+=len(chosen)
    assert len(t)==summary['events'] and len(inventory)==summary['clusters'] and windows==summary['raw_windows']
    assert sum(v=='good' for v in labels.values())==summary['good'];assert sum(v=='mua' for v in labels.values())==summary['mua']
    for name,digest in c['pinned_files'].items():assert sha(ROOT/name)==digest,name
    verify_manifest(run_path/'output-manifest.json');verify_manifest(report/'report-manifest.json')
    output.mkdir(parents=True)
    checks=dict(state='passed',original_events_verified=len(t),annotation_columns_verified=len(expected),cluster_rows_verified=len(inventory),quarter_rows_verified=len(quarter_rows),one_second_bins_verified=int(bins['counts'].size),raw_windows_verified=windows,raw_values_verified=values,original_pins_unchanged=True,script_sha256=sha(Path(__file__)),report_manifest_sha256=sha(report/'report-manifest.json'))
    save(output/'checks.json',checks);save(output/'manifest.json',{p.name:sha(p) for p in output.iterdir()});print(checks)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.report,a.output)
