"""Four-shank source-to-release identity, summary and preservation audit."""
import argparse,csv
from pathlib import Path
import h5py
import numpy as np
from run_sorting import ROOT,read,save,sha,verify_manifest
from shank_input import channel_ids


def rows(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))


def run(report,output):
    report=report.resolve();output=output.resolve();assert output.is_relative_to(ROOT/'results') and not output.exists()
    verify_manifest(report/'manifest.json');summary=read(report/'summary.json')
    for p,h in summary['pinned_inputs'].items():assert sha(ROOT/p)==h,p
    for name,field in [('extra4_shank0_release.v1.json','payloads'),('extra4_shanks123_derived_v1.json','pinned_files')]:
        for p,h in read(ROOT/'configs'/name)[field].items():assert sha(ROOT/p)==h,p
    assert sha(Path(summary['source']))==summary['source_sha256']
    with h5py.File(summary['source'],'r') as f:assert f['signals'].shape==(2048,3000000)
    mapping=channel_ids();mr=rows(report/'channel_map.csv');assert len(mr)==2048
    for r in mr:
        s,b=int(r['shank']),int(r['binary_channel']);assert int(r['original_channel_id'])==mapping[s,b]
    assert len({r['original_channel_id'] for r in mr})==2048
    events=rows(report/'spikes.csv');units=rows(report/'units.csv');bins=rows(report/'rate_bins.csv');quarters=rows(report/'quarters.csv');ledger=rows(report/'curation_ledger.csv');omitted=rows(report/'omitted_events.csv')
    intervals=np.load(report/'analysis_intervals.npz');packed=np.load(report/'spikes.npz')
    for key in packed.files:np.testing.assert_array_equal(packed[key],np.array([float(r[key]) if key=='sorter_amplitude' else int(r[key]) for r in events]))
    old=ROOT/'results/extra4_shank0/w12-curated-v1';new=ROOT/'results/extra4/w16d-curated-v1'
    registry=read(ROOT/'configs/extra4_working_runs.v1.json')
    checks=dict(events=0,units=0,bins=0,quarters=0,raw_windows=0,omissions=0,source_clusters=0)
    for spec in summary['shanks']:
        s=spec['shank'];source=old if s==0 else new;runpath=ROOT/f'results/extra4_shank{s}'/spec['run_id'];src=runpath/'kilosort4'
        t=np.load(src/'spike_times.npy').ravel();cl=np.load(src/'spike_clusters.npy').ravel();amp=np.load(src/'amplitudes.npy').ravel()
        cmap=np.load(src/'channel_map.npy').ravel();pos=np.load(src/'channel_positions.npy');templates=np.load(src/'templates.npy')
        if s==0:
            binary=ROOT/'data/extra4_shank0_float32.bin';digest=read(ROOT/'configs/extra4_shank0_release.v1.json')['binary_sha256']
        else:
            c=read(runpath/'config.json');binary=ROOT/c['binary_path'];digest=c['pinned_files'][c['binary_path']]
        assert sha(binary)==digest
        raw=np.memmap(binary,mode='r',dtype='<f4',shape=(3000000,512))
        uu=[r for r in units if int(r['shank'])==s];ids=[int(r['cluster_id']) for r in uu];spans=intervals[f'shank{s}']
        expected_spans=np.array([[100,2999900]]) if s<3 else np.load(new/'shank3/analysis_intervals.npz')['primary']
        np.testing.assert_array_equal(spans,expected_spans)
        domain=np.zeros(3000000,bool)
        for lo,hi in spans:domain[lo:hi]=True
        keep=np.isin(cl,ids)&domain[t];ei=np.flatnonzero(keep);er=[r for r in events if int(r['shank'])==s]
        expected_omitted=np.flatnonzero(np.isin(cl,ids)&~domain[t]);oo=[r for r in omitted if int(r['shank'])==s]
        assert sorted(int(r['original_event_index']) for r in oo)==expected_omitted.tolist();checks['omissions']+=len(oo)
        original_rows=rows(source/'spikes.csv');original_rows=[r for r in original_rows if s==0 or int(r['shank'])==s]
        assert len(er)==len(ei)==len(original_rows)
        for r,original,i in zip(er,original_rows,ei):
            # Every native frozen value survives; union-schema empty fields are never synthesized as false.
            for k,v in original.items():assert r[k]==v,(s,k)
            assert r['run_id']==spec['run_id'] and int(r['original_event_index'])==i and int(r['sample_index'])==t[i] and int(r['cluster_id'])==cl[i]
            assert float(r['sorter_amplitude'])==float(amp[i]) and float(r['nominal_time_s'])==t[i]/10000 and float(r['physical_time_s'])==t[i]/10080
            if s==0:
                for alias,native in [('any_active_guard','active_guard_any'),('half_active_guard','active_guard_ge50'),('incomplete_context','boundary')]:assert r[alias]==r[native]
                assert r['shared_core']=='' and r['shared_shoulder']==''
            checks['events']+=1
        ll=[r for r in ledger if int(r['shank'])==s]
        assert {int(r['cluster_id']) for r in ll}==set(np.unique(cl)) and len(ll)==len(np.unique(cl))
        assert all(r['run_id']==spec['run_id'] for r in ll)
        assert sorted(int(r['cluster_id']) for r in ll if r['accepted']=='True')==sorted(ids)
        checks['source_clusters']+=len(ll)
        br={(r['unit_id'],int(r['start_sample'])):r for r in bins if int(r['shank'])==s}
        qr={(r['unit_id'],int(r['quarter'])):r for r in quarters if int(r['shank'])==s}
        for u in uu:
            cid=int(u['cluster_id']);ii=ei[cl[ei]==cid];peak=np.ptp(templates[cid],axis=0).argmax();ch=cmap[np.argsort(np.linalg.norm(pos-pos[peak],axis=1),kind='stable')[:8]]
            assert int(u['peak_binary'])==ch[0] and int(u['peak_global'])==mapping[s,ch[0]]
            assert int(u['analysis_events'])==len(ii) and int(u['exposure_samples'])==domain.sum()
            for name,fs in [('nominal',10000),('physical',10080)]:assert np.isclose(float(u[name+'_rate']),len(ii)*fs/domain.sum(),rtol=1e-12)
            assert float(u['amplitude_median'])==float(np.median(amp[ii]))
            for lo in range(0,3000000,100000):
                hi=lo+100000;r=br[u['unit_id'],lo];n=int(((t[ii]>=lo)&(t[ii]<hi)).sum());duration=int(domain[lo:hi].sum())
                assert int(r['events'])==n and int(r['exposure_samples'])==duration
                for name,fs in [('nominal',10000),('physical',10080)]:assert np.isclose(float(r[name+'_rate']),n*fs/duration,rtol=1e-12)
                checks['bins']+=1
            target=report/f'waveforms/shank{s}_cluster{cid}.npz';native=source/f'unit_{cid}.npz' if s==0 else source/f'shank{s}/unit_{cid}.npz'
            assert sha(target)==sha(native);z=np.load(target);np.testing.assert_array_equal(z['channels'],ch)
            for group in range(5):
                selected=z['selected'] if group==0 else z[f'quarter_{group-1}_events'];assert np.isin(selected,ii).all()
                waves=[]
                for i in selected:
                    w=np.column_stack([np.array(raw[t[i]-100:t[i]+101,int(b)]) for b in ch])*1e6;w-=np.median(w[:70],axis=0);waves.append(w);checks['raw_windows']+=1
                mean=np.array(waves).mean(0);np.testing.assert_array_equal(mean,z['reference'] if group==0 else z['quarter_means'][group-1])
                if group:
                    lo=(group-1)*750000;hi=group*750000;qi=ii[(t[ii]>=lo)&(t[ii]<hi)];r=qr[u['unit_id'],group]
                    assert int(r['events'])==len(qi) and int(r['exposure_samples'])==domain[lo:hi].sum()
                    assert float(r['amplitude_median'])==float(np.median(amp[qi]))
                    cor=np.corrcoef(mean[80:141].ravel(),z['reference'][80:141].ravel())[0,1]
                    assert np.isclose(float(r['raw_correlation_to_pooled']),cor,rtol=1e-12);checks['quarters']+=1
            checks['units']+=1
    assert len({r['unit_id'] for r in units})==41
    assert len({(r['shank'],r['run_id'],r['original_event_index']) for r in events})==62048
    assert (checks['events'],checks['units'],checks['bins'],checks['quarters'],checks['omissions'],checks['source_clusters'])==(62048,41,1230,164,14,186)
    assert sum(r['disposition']=='hold_deferred' for r in ledger)==89 and sum(r['disposition']=='withhold' for r in ledger)==56
    historical=rows(report/'historical_control_ledger.csv');assert len(historical)==1 and historical[0]['run']=='w7b-control01'
    verify_manifest(report/'manifest.json')
    output.mkdir();save(output/'checks.json',dict(state='passed',**checks,source_h5_hash_verified=True,four_binary_hashes_verified=True,native_event_fields_preserved=True,all_2048_channel_mapping_verified=True,historical_control_separate=True,original_revisions_unchanged=True,report_manifest_sha256=sha(report/'manifest.json'),validator_sha256=sha(Path(__file__))))
    save(output/'manifest.json',{p.name:sha(p) for p in output.iterdir()});print(read(output/'checks.json'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.report,a.output)
