"""Independently audit accepted event identity, exposure, bins and raw summaries."""
import argparse
import csv
from pathlib import Path
import numpy as np
from run_sorting import ROOT,read,save,sha,verify_manifest


def rows(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))


def run(report,output):
    report=report.resolve();output=output.resolve()
    assert output.is_relative_to(ROOT/'results') and not output.exists()
    verify_manifest(report/'manifest.json');a=read(report/'acceptance.json')
    assert a['state']=='user_accepted' and a['units_accepted'] and a['policy_adopted']
    assert sha(report/'acceptance.json')==sha(ROOT/'configs/extra4_shanks123_curated_v1.json')
    for p,h in a['pinned_files'].items():assert sha(ROOT/p)==h,p
    events=rows(report/'spikes.csv');units=rows(report/'units.csv');quarters=rows(report/'quarters.csv');bins=rows(report/'rate_bins.csv')
    registry=read(ROOT/'configs/extra4_working_runs.v1.json');preview=ROOT/'results/extra4/w16d-proposal01'
    windows=0;binchecks=0;quarterchecks=0;eventchecks=0
    for spec,choice in zip(a['shanks'],registry['runs']):
        s=spec['shank'];src=ROOT/choice['run_path']/'kilosort4';c=read(src.parent/'config.json')
        t=np.load(src/'spike_times.npy').ravel();cl=np.load(src/'spike_clusters.npy').ravel();amp=np.load(src/'amplitudes.npy').ravel()
        with np.load(ROOT/choice['baseline_report']/'event_annotations.npz') as loaded:
            baseline={name:loaded[name] for name in loaded.files}
        pr=np.load(preview/f'shank{s}_event_preview.npz')
        spans=np.load(report/f'shank{s}/analysis_intervals.npz')['primary'];domain=np.zeros(c['samples'],bool)
        for lo,hi in spans:domain[lo:hi]=True
        original_spans=np.load(preview/'analysis_intervals.npz')[f's{s}_primary'];np.testing.assert_array_equal(spans,original_spans)
        ids=np.flatnonzero(np.isin(cl,spec['candidate_ids'])&domain[t]);z=np.load(report/f'shank{s}/spikes.npz')
        np.testing.assert_array_equal(z['original_event_index'],ids);np.testing.assert_array_equal(z['sorter_amplitude'],amp[ids])
        for name in pr.files:np.testing.assert_array_equal(z[name],pr[name][ids])
        er=[r for r in events if int(r['shank'])==s];assert len(er)==len(ids)
        for r,i in zip(er,ids):
            assert int(r['sample_index'])==t[i] and int(r['original_event_index'])==i and int(r['cluster_id'])==cl[i]
            assert r['unit_id']==f'extra_4:shank{s}:{choice["run_id"]}:cluster{cl[i]}:v1'
            assert float(r['sorter_amplitude'])==float(amp[i])
            assert float(r['nominal_time_s'])==t[i]/10000 and float(r['physical_time_s'])==t[i]/10080
            for name in baseline:
                if baseline[name].dtype==bool:assert (r[name]=='True')==bool(baseline[name][i])
            eventchecks+=1
        raw=np.memmap(ROOT/c['binary_path'],mode='r',dtype='<f4',shape=(c['samples'],512))
        templates=np.load(src/'templates.npy');cmap=np.load(src/'channel_map.npy').ravel();pos=np.load(src/'channel_positions.npy')
        mapping=np.genfromtxt(ROOT/c['mapping_path'],delimiter=',',names=True,dtype=int)
        rb=np.load(report/f'shank{s}/rate_bins.npz');np.testing.assert_array_equal(rb['cluster_ids'],spec['candidate_ids'])
        for j,cid in enumerate(spec['candidate_ids']):
            ei=ids[cl[ids]==cid];u=next(r for r in units if int(r['shank'])==s and int(r['cluster_id'])==cid)
            assert u['status']=='accepted_putative_single_unit' and int(u['analysis_events'])==len(ei)
            assert int(u['original_events'])==int((cl==cid).sum()) and int(u['omitted_events'])==int((cl==cid).sum())-len(ei)
            assert int(u['exposure_samples'])==int(domain.sum())
            for name,fs in [('nominal',10000),('physical',10080)]:
                assert np.isclose(float(u[name+'_rate']),len(ei)*fs/domain.sum(),rtol=1e-12)
            assert float(u['amplitude_median'])==float(np.median(amp[ei]))
            for name in baseline:
                if baseline[name].dtype==bool: assert int(u[name])==int(baseline[name][ei].sum())
            packet=np.load(report/f'shank{s}/unit_{cid}.npz');peak=np.ptp(templates[cid],axis=0).argmax();ch=cmap[np.argsort(np.linalg.norm(pos-pos[peak],axis=1),kind='stable')[:8]]
            np.testing.assert_array_equal(ch,packet['channels']);assert int(u['peak_binary'])==ch[0] and int(u['peak_global'])==mapping['original_channel_id'][ch[0]]
            def verify_wave(selected,eligible,maximum):
                nonlocal windows
                expected=eligible[np.unique(np.linspace(0,len(eligible)-1,min(len(eligible),maximum),dtype=int))]
                np.testing.assert_array_equal(selected,expected)
                wave=[]
                for i in selected:
                    # Scalar channel reads independent of builder's indexed multidimensional extraction.
                    w=np.column_stack([np.array(raw[t[i]-100:t[i]+101,int(channel)]) for channel in ch])*1e6
                    w-=np.median(w[:70],axis=0);wave.append(w);windows+=1
                return np.array(wave)
            waves=verify_wave(packet['selected'],ei,256);np.testing.assert_array_equal(waves,packet['waves']);np.testing.assert_array_equal(waves.mean(0),packet['reference'])
            for q in range(4):
                lo,hi=q*750000,(q+1)*750000;qi=ei[(t[ei]>=lo)&(t[ei]<hi)]
                qw=verify_wave(packet[f'quarter_{q}_events'],qi,128);qm=qw.mean(0)
                np.testing.assert_array_equal(qm,packet['quarter_means'][q])
                r=next(r for r in quarters if int(r['shank'])==s and int(r['cluster_id'])==cid and int(r['quarter'])==q+1)
                d=int(domain[lo:hi].sum());assert int(r['events'])==len(qi) and int(r['exposure_samples'])==d
                assert np.isclose(float(r['nominal_rate']),len(qi)*10000/d,rtol=1e-12)
                assert float(r['amplitude_median'])==float(np.median(amp[qi]))
                cor=np.corrcoef(qm[80:141].ravel(),packet['reference'][80:141].ravel())[0,1]
                assert np.isclose(float(r['raw_correlation_to_pooled']),cor,rtol=1e-12);quarterchecks+=1
            for b,(lo,hi) in enumerate(zip(rb['bin_edges_samples'][:-1],rb['bin_edges_samples'][1:])):
                count=int(((t[ei]>=lo)&(t[ei]<hi)).sum());d=int(domain[lo:hi].sum())
                assert rb['counts'][j,b]==count and rb['exposure_samples'][b]==d
                r=next(r for r in bins if int(r['shank'])==s and int(r['cluster_id'])==cid and int(r['start_sample'])==lo)
                assert int(r['events'])==count and int(r['exposure_samples'])==d
                for name,fs in [('nominal',10000),('physical',10080)]:
                    assert np.isclose(rb[name+'_rates'][j,b],count*fs/d,rtol=1e-12)
                    assert np.isclose(float(r[name+'_rate']),count*fs/d,rtol=1e-12)
                binchecks+=1
            assert rb['counts'][j].sum()==len(ei)
    assert len({(r['shank'],r['run_id'],r['original_event_index']) for r in events})==43796
    assert (eventchecks,quarterchecks,binchecks)==(43796,120,900)
    assert rows(report/'omitted_events.csv')==rows(preview/'omitted_event_preview.csv')
    ledger=rows(report/'curation_ledger.csv');assert len(ledger)==128
    assert sum(r['accepted']=='True' for r in ledger)==30
    assert sum(r['disposition']=='hold_deferred' for r in ledger)==51
    assert sum(r['disposition']=='withhold' for r in ledger)==47
    output.mkdir();save(output/'checks.json',dict(state='passed',event_identities=eventchecks,units=30,quarters=quarterchecks,bins=binchecks,raw_windows_scalar_verified=windows,ledger_rows=128,omissions=12,source_pins_unchanged=True,report_manifest_sha256=sha(report/'manifest.json'),validator_sha256=sha(Path(__file__))))
    save(output/'manifest.json',{p.name:sha(p) for p in output.iterdir()});print(read(output/'checks.json'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.report,a.output)
