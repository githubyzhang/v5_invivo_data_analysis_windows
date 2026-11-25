"""Independent W16D interval/event accounting; never adopts the proposal."""
import argparse
import csv
from pathlib import Path
import numpy as np
from run_sorting import ROOT, read, save, sha, verify_manifest


def rows(p):
    with p.open(newline='') as f: return list(csv.DictReader(f))


def merge(spans):
    out=[]
    for a,b in sorted((int(a),int(b)) for a,b in spans):
        if out and a <= out[-1][1]: out[-1][1]=max(b,out[-1][1])
        else: out.append([a,b])
    return out


def inside(t,spans):
    result=np.zeros(len(t),bool)
    for a,b in spans: result |= (t>=a)&(t<b)
    return result


def run(report,output):
    report=report.resolve();output=output.resolve()
    assert output.is_relative_to(ROOT/'results') and not output.exists()
    verify_manifest(report/'manifest.json');p=read(report/'proposal.json')
    for path,digest in p['pinned_files'].items(): assert sha(ROOT/path)==digest,path
    assert p['state']=='awaiting_user_acceptance' and not p['units_accepted'] and not p['policy_adopted']
    # Half-open boundaries, overlaps, and adjacent interval union.
    assert merge([[3,5],[1,4],[5,7],[9,10]])==[[1,7],[9,10]]
    np.testing.assert_array_equal(inside(np.arange(9),[[2,5]]),[False,False,True,True,True,False,False,False,False])
    n=3000000;z=np.load(ROOT/'results/extra4/w14-quality01/intervals.npz')
    flat=z['flat'];flat=flat[flat[:,0]==3]
    concurrency=np.zeros(n,np.int16)
    # Per-channel union avoids counting a channel twice even if intervals overlap.
    for ch in range(512):
        for a,b in merge(flat[flat[:,1]==ch,3:5]): concurrency[a:b]+=1
    core=concurrency>=256
    edges=np.diff(np.r_[False,core,False].astype(int))
    expanded=merge([[max(0,int(a)-500),min(n,int(b)+500)] for a,b in zip(np.where(edges==1)[0],np.where(edges==-1)[0])])
    fixed=np.load(ROOT/'results/extra4_shank3/w15c-shared-review02/fixed_masks.npz')
    np.testing.assert_array_equal(core,fixed['core'])
    reconstructed=np.zeros(n,bool)
    for a,b in expanded: reconstructed[a:b]=True
    np.testing.assert_array_equal(reconstructed,~fixed['away'])
    intervals=np.load(report/'analysis_intervals.npz');sensitivity=rows(report/'sensitivity.csv');units=rows(report/'unit_preview.csv')
    registry=read(ROOT/'configs/extra4_working_runs.v1.json');checked=0;omissions=[];source_events=0
    for choice,summary in zip(registry['runs'],p['shanks']):
        s=choice['shank_zero_based'];src=ROOT/choice['run_path']/'kilosort4'
        t=np.load(src/'spike_times.npy').ravel();cl=np.load(src/'spike_clusters.npy').ravel();source_events+=len(t)
        preview=np.load(report/f'shank{s}_event_preview.npz');baseline=np.load(ROOT/choice['baseline_report']/'event_annotations.npz')
        for key in baseline.files: np.testing.assert_array_equal(preview[key],baseline[key])
        np.testing.assert_array_equal(preview['sample_index'],t)
        np.testing.assert_array_equal(preview['original_event_index'],np.arange(len(t)))
        np.testing.assert_array_equal(preview['candidate'],np.isin(cl,summary['candidate_ids']))
        shared=expanded if s==3 else []
        excluded=merge([[0,100],[n-100,n]]+shared)
        primary=~inside(t,excluded)
        np.testing.assert_array_equal(preview['primary_domain'],primary)
        np.testing.assert_array_equal(preview['proposed_inclusion'],primary&preview['candidate'])
        assert summary['exposure_samples']==n-sum(b-a for a,b in excluded)
        templates=np.load(src/'templates.npy');cmap=np.load(src/'channel_map.npy').ravel();pos=np.load(src/'channel_positions.npy')
        for cid in summary['candidate_ids']:
            ids=np.flatnonzero(cl==cid);peak=int(np.ptp(templates[cid],axis=0).argmax())
            near=cmap[np.argsort(np.linalg.norm(pos-pos[peak],axis=1),kind='stable')[:8]]
            guards=z['guard'];guards=guards[guards[:,0]==s]
            unit=next(r for r in units if int(r['shank'])==s and int(r['cluster_id'])==cid)
            assert int(unit['peak_binary'])==cmap[peak]
            for scenario,extra in [('interior',[]),('primary',[]),('primary_peak_clear',[cmap[peak]]),('primary_local8_clear',near)]:
                bad=merge([[0,100],[n-100,n]]+(shared if scenario!='interior' else [])+guards[np.isin(guards[:,1],extra),3:5].tolist())
                keep=~inside(t[ids],bad);duration=n-sum(b-a for a,b in bad)
                r=next(r for r in sensitivity if int(r['shank'])==s and int(r['cluster_id'])==cid and r['scenario']==scenario)
                assert int(r['included_events'])==int(keep.sum()) and int(r['exposure_samples'])==duration
                assert int(r['omitted_events'])+int(r['included_events'])==len(ids)==int(r['original_events'])
                for name,fs in [('nominal',10000),('physical',10080)]:
                    assert np.isclose(float(r[name+'_observed_rate']),keep.sum()*fs/duration,rtol=1e-12)
                    assert np.isclose(float(r[name+'_seconds']),duration/fs,rtol=1e-12)
                stored=intervals[f's{s}_c{cid}_{scenario}']
                np.testing.assert_array_equal(inside(t[ids],stored),keep)
                mask=np.zeros(n,bool)
                for a,b in stored: mask[a:b]=True
                expected=np.ones(n,bool)
                for a,b in bad: expected[a:b]=False
                np.testing.assert_array_equal(mask,expected)
                checked+=1
            retained=ids[primary[ids]]
            assert int(unit['original_events'])==len(ids) and int(unit['proposed_events'])==len(retained)
            for key in ['peak_guard','any_active_guard','half_active_guard','broad_warning','tight_warning','incomplete_context']:
                assert int(unit[key])==int(baseline[key][retained].sum())
            assert int(unit['coincidence_unavailable'])==int((~baseline['broad_available'][retained]).sum())
            omissions.extend((s,int(i),int(t[i]),cid,t[i]<100 or t[i]>=n-100,bool(core[t[i]]) if s==3 else False,bool(reconstructed[t[i]] and not core[t[i]]) if s==3 else False) for i in ids[~primary[ids]])
        assert summary['original_events']==int(preview['candidate'].sum())
        assert summary['proposed_events']==int(preview['proposed_inclusion'].sum())
    stored_omissions=rows(report/'omitted_event_preview.csv')
    actual=[(int(r['shank']),int(r['original_event_index']),int(r['sample_index']),int(r['cluster_id']),r['boundary']=='True',r['shared_core']=='True',r['shared_shoulder']=='True') for r in stored_omissions]
    assert sorted(actual)==sorted(omissions)
    ledger=rows(report/'all_cluster_proposals.csv')
    assert len(ledger)==128 and len({(r['shank'],r['run_id'],r['cluster_id']) for r in ledger})==128
    assert sum(r['proposal']=='propose_putative' for r in ledger)==30
    assert all(r['accepted']=='False' for r in ledger)
    assert checked==120 and len(omissions)==12
    output.mkdir()
    save(output/'checks.json',dict(state='passed',candidate_units=30,all_cluster_rows=128,scenario_checks=checked,original_source_events_verified=source_events,omitted_event_identities_verified=len(omissions),shared_core_reconstructed=True,half_open_boundary_checks=True,report_manifest_sha256=sha(report/'manifest.json'),validator_sha256=sha(Path(__file__)),limitations='Checks validate calculations and identity preservation, not scientific cleanliness or adoption.'))
    save(output/'manifest.json',{f.name:sha(f) for f in output.iterdir()})
    print(read(output/'checks.json'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.report,a.output)
