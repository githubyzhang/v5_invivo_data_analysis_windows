"""Audit prior evidence and assemble a proposed run set, without scientific adoption."""
import argparse
import csv
import html
from pathlib import Path
import numpy as np
from run_sorting import ROOT,read,save,sha
from review_sorting_baseline import table


def build(proposal,output):
    proposal=proposal.resolve();output=output.resolve()
    assert not output.exists() and output.is_relative_to(ROOT/'results')
    config=read(proposal);assert config['state']=='proposed_awaiting_user'
    checked={};visited=set();manifest_count=0
    def pin(path,digest):
        path=path.resolve();assert path.is_relative_to(ROOT),path
        if path not in checked:checked[path]=sha(path)
        assert checked[path]==digest,path
    def evidence(path,digest):
        nonlocal manifest_count
        path=path.resolve();pin(path,digest)
        if path in visited:return
        visited.add(path)
        if path.suffix!='.json':return
        obj=read(path)
        if not isinstance(obj,dict):return
        if path.name.endswith('manifest.json'):
            manifest_count+=1
            for name,h in obj.items():
                child=(path.parent/name).resolve();assert child.is_relative_to(path.parent)
                evidence(child,h)
        else:
            for key in ['pinned_files','payloads','evidence_sha256']:
                for name,h in obj.get(key,{}).items():evidence(ROOT/name,h)
    evidence(ROOT/config['shank0_release'],config['shank0_release_sha256'])
    runrows=[];inventory=[];identities=set()
    for candidate in config['recommendations']:
        assert candidate['selection_state']=='proposed_awaiting_user' and candidate['cluster_acceptance_state']=='not_curated'
        evidence(ROOT/candidate['checkpoint'],candidate['checkpoint_sha256'])
        run=ROOT/candidate['run_path'];report=ROOT/candidate['baseline_report'];c=read(run/'config.json');summary=read(report/'summary.json')
        assert summary['run_manifest_sha256']==sha(run/'output-manifest.json')
        s=candidate['shank_zero_based'];assert c['shank_zero_based']==s and c['run_id']==candidate['run_id']
        assert c['excluded_binary_channels']==candidate['excluded_binary_channels']
        assert c['samples']==3000000 and c['nominal_fs_hz']==10000 and c['physical_fs_hz']==10080
        mapping=np.genfromtxt(ROOT/c['mapping_path'],delimiter=',',names=True,dtype=int)
        assert mapping['original_channel_id'][candidate['excluded_binary_channels']].tolist()==candidate['excluded_global_channels']
        src=run/'kilosort4';t=np.load(src/'spike_times.npy').ravel();cl=np.load(src/'spike_clusters.npy').ravel()
        active=np.load(src/'channel_map.npy').ravel();np.testing.assert_array_equal(active,np.delete(np.arange(512),candidate['excluded_binary_channels']))
        assert len(t)==len(cl) and np.all((t>=0)&(t<c['samples']))
        with (src/'cluster_KSLabel.tsv').open() as f:labels={int(r['cluster_id']):r['KSLabel'] for r in csv.DictReader(f,delimiter='\t')}
        with (report/'clusters.csv').open() as f:baseline=list(csv.DictReader(f))
        assert set(labels)==set(np.unique(cl))=={int(r['cluster_id']) for r in baseline}
        assert set(map(int,candidate['priority_clusters'])).issubset(labels)
        for row in baseline:
            cid=int(row['cluster_id']);count=int((cl==cid).sum())
            assert count==int(row['events']) and labels[cid]==row['automated_label']
            assert row['review_state']=='unreviewed_not_accepted'
            identity=f'extra_4/shank{s}/{c["run_id"]}/cluster{cid}';assert identity not in identities;identities.add(identity)
            inventory.append(dict(identity=identity,shank_zero_based=s,run_id=c['run_id'],cluster_id=cid,events=count,automated_label=labels[cid],selection_state='proposed_awaiting_user',curation_state='not_curated',accepted=False,review_priority_reason=candidate['priority_clusters'].get(str(cid),'Standard full-cluster review; no prior acceptance.')))
        good=sum(x=='good' for x in labels.values());mua=sum(x=='mua' for x in labels.values())
        assert (len(t),len(labels),good,mua)==(summary['events'],summary['clusters'],summary['good'],summary['mua'])
        runrows.append(dict(shank_zero_based=s,run_id=c['run_id'],events=len(t),clusters=len(labels),automated_good=good,automated_mua=mua,active_channels=len(active),excluded_binary_channels=','.join(map(str,c['excluded_binary_channels'])) or 'none',selection_state='proposed_awaiting_user',reason=candidate['reason']))
    assert len(runrows)==3 and {r['shank_zero_based'] for r in runrows}=={1,2,3}
    assert not config['new_units_accepted'] and not config['temporal_mask_adopted'] and not config['mix_clusters_across_runs']
    output.mkdir(parents=True);table(output/'proposed_runs.csv',runrows);table(output/'curation_inventory.csv',inventory)
    # Readback verifies generated coverage and totals without trusting CSV row order.
    with (output/'curation_inventory.csv').open() as f:reloaded=list(csv.DictReader(f))
    assert {x['identity'] for x in reloaded}==identities and len(reloaded)==len(identities)
    assert all(x['accepted']=='False' and x['curation_state']=='not_curated' for x in reloaded)
    totals={k:sum(r[k] for r in runrows) for k in ['events','clusters','automated_good','automated_mua']}
    assert sum(int(x['events']) for x in reloaded)==totals['events']
    checks=dict(state='passed',unique_pinned_files_verified=len(checked),manifests_verified=manifest_count,proposed_run_count=len(runrows),inventory_rows=len(inventory),totals=totals,source_axis_samples=3000000,nominal_fs_hz=10000,physical_fs_hz=10080,prior_evidence_unchanged=True,new_units_accepted=False,working_runs_selected=False,proposal_sha256=sha(proposal),script_sha256=sha(Path(__file__)),audit_scope='Manifest/content integrity, run identity, mapping, label/event counts, common sample axis and inventory readback. Existing raw-waveform/annotation audits retained; no new sort or replay of every scientific calculation.')
    save(output/'checks.json',checks)
    save(output/'verified_files.json',{str(p.relative_to(ROOT)):h for p,h in checked.items()})
    body='<html><meta charset="utf-8"><title>W15D working-run proposal</title><style>body{font:16px system-ui;max-width:1150px;margin:35px auto;line-height:1.5}table{border-collapse:collapse}td,th{padding:10px;border:1px solid #bbb}</style><h1>W15D: working runs proposed for curation</h1><p><strong>Awaiting explicit user selection. No new units accepted.</strong> Shank numbers are zero-based. Shank0 remains the frozen accepted v1 release.</p><table><tr><th>Shank</th><th>Proposed run</th><th>Events</th><th>Clusters</th><th>Good / mua</th></tr>'
    for r in runrows:body+=f'<tr><td>{r["shank_zero_based"]}</td><td>{html.escape(r["run_id"])}</td><td>{r["events"]:,}</td><td>{r["clusters"]}</td><td>{r["automated_good"]} / {r["automated_mua"]}</td></tr>'
    body+='</table><p>128 clusters await review; automated labels are not neuron counts. Every proposed-run cluster remains in the inventory. Alternative sorts remain evidence and are not combined into this set.</p><p><a href="curation_inventory.csv">All-cluster curation inventory</a> | <a href="proposed_runs.csv">Proposed runs</a> | <a href="checks.json">Audit</a> | <a href="../../../docs/development/rounds/2026-11-24-09-w15d-working-run-checkpoint.md">Decision brief and limitations</a></p>'
    for candidate in config['recommendations']:
        import os
        link=Path(os.path.relpath(ROOT/candidate['baseline_report']/'index.html',output)).as_posix()
        body+=f'<h2>Shank{candidate["shank_zero_based"]}</h2><p>{html.escape(candidate["reason"])}</p><p><a href="{link}">Baseline report</a></p>'
    body+='<p>Shank2: retain good-to-mua and event-loss concerns for curation. Shank3: 7.2005 nominal seconds of shared-flat core retain a detection deficit in both runs; b259 exclusion does not repair this. Review c1/c2 jointly, sparse populations and per-unit exposure. No temporal mask or new analysis policy is adopted.</p><p>After run selection: W16A shank1 full curation, W16B shank2, W16C shank3, then explicit subset/policy acceptance in W16D. No additional sort is currently required before selection.</p>'
    (output/'index.html').write_text(body,encoding='utf-8');save(output/'report-manifest.json',{p.name:sha(p) for p in output.iterdir()});print(checks)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--proposal',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.proposal,a.output)
