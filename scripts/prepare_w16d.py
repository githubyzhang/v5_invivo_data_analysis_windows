"""Prepare, without adopting, the W16D subset/policy acceptance packet."""
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_sorting import ROOT, read, save, sha, verify_manifest
from review_sorting_baseline import table


def rows(p):
    with p.open(newline='') as f:
        return list(csv.DictReader(f))


def spans(mask):
    edges = np.diff(np.r_[False, mask, False].astype(int))
    return np.column_stack((np.where(edges == 1)[0], np.where(edges == -1)[0]))


def run(output):
    output = output.resolve()
    assert output.is_relative_to(ROOT/'results') and not output.exists()
    registry_path = ROOT/'configs/extra4_working_runs.v1.json'
    registry = read(registry_path)
    pins = {str(registry_path.relative_to(ROOT)): sha(registry_path)}
    quality = ROOT/'results/extra4/w14-quality01'
    shared = ROOT/'results/extra4_shank3/w15c-shared-review02'
    for p in [quality/'manifest.json', shared/'report-manifest.json']:
        verify_manifest(p); pins[str(p.relative_to(ROOT))] = sha(p)
    guards = np.load(quality/'intervals.npz')['guard']
    fixed = np.load(shared/'fixed_masks.npz')
    output.mkdir()
    summaries = []; sensitivity = []; units = []; omitted = []; intervals = {}; all_ledgers = []
    fig, axs = plt.subplots(3, 1, figsize=(14, 10), layout='constrained')
    for choice, letter, ax in zip(registry['runs'], 'abc', axs):
        s = choice['shank_zero_based']
        cp = ROOT/f'configs/extra4_shank{s}_curation_w16{letter}.proposed.json'
        checkpoint = read(cp)
        pins[str(cp.relative_to(ROOT))] = sha(cp)
        for p, digest in checkpoint['pinned_files'].items():
            assert sha(ROOT/p) == digest, p
        runpath = ROOT/choice['run_path']; baseline = ROOT/choice['baseline_report']
        review = ROOT/f'results/extra4_shank{s}/w16{letter}-review01'
        for p in [runpath/'output-manifest.json', baseline/'report-manifest.json', review/'report-manifest.json']:
            verify_manifest(p); pins[str(p.relative_to(ROOT))] = sha(p)
        assert sha(runpath/'output-manifest.json') == choice['run_manifest_sha256']
        c = read(runpath/'config.json'); n = c['samples']; fs = c['nominal_fs_hz']; physical = c['physical_fs_hz']
        assert (n, fs, physical) == (3000000, 10000, 10080)
        candidates = checkpoint['putative_candidate_ids']
        ledgerpath = next(ROOT/p for p in checkpoint['pinned_files'] if p.endswith('proposal-ledger.csv'))
        ledger = rows(ledgerpath); all_ledgers.extend(dict(shank=s,run_id=choice['run_id'],cluster_id=r['cluster_id'],proposal=r['proposal'],reason=r['reason'],accepted=False) for r in ledger)
        assert sorted(int(r['cluster_id']) for r in ledger if r['proposal']=='propose_putative') == candidates
        t = np.load(runpath/'kilosort4/spike_times.npy').ravel(); cl = np.load(runpath/'kilosort4/spike_clusters.npy').ravel()
        ann = np.load(baseline/'event_annotations.npz')
        np.testing.assert_array_equal(t, ann['sample_index']); np.testing.assert_array_equal(cl, ann['cluster_id'])
        metrics = {int(r['cluster_id']):r for r in rows(review/'unit_metrics.csv')}
        interior = np.zeros(n,bool); interior[100:n-100] = True
        shared_bad = ~fixed['away'] if s == 3 else np.zeros(n,bool)
        primary = interior & ~shared_bad
        intervals[f's{s}_interior'] = spans(interior)
        intervals[f's{s}_primary'] = spans(primary)
        payload = {k:ann[k] for k in ann.files}
        payload.update(candidate=np.isin(cl,candidates), interior=interior[t], primary_domain=primary[t],
                       shared_core=fixed['core'][t] if s==3 else np.zeros(len(t),bool),
                       shared_shoulder=fixed['shoulder'][t] if s==3 else np.zeros(len(t),bool))
        payload['proposed_inclusion'] = payload['candidate'] & primary[t]
        np.savez_compressed(output/f'shank{s}_event_preview.npz',**payload)
        for cid in candidates:
            ids = np.flatnonzero(cl==cid); r = metrics[cid]
            channels = np.load(review/f'unit_{cid}.npz')['channels']
            peak = int(r['peak_binary']); assert peak == channels[0]
            g = guards[guards[:,0]==s]
            peak_bad = np.zeros(n,bool); local_bad = np.zeros(n,bool)
            for a,b in g[g[:,1]==peak,3:5]: peak_bad[a:b] = True
            for a,b in g[np.isin(g[:,1],channels),3:5]: local_bad[a:b] = True
            np.testing.assert_array_equal(peak_bad[t[ids]],ann['peak_guard'][ids])
            variants = dict(interior=interior,primary=primary,primary_peak_clear=primary&~peak_bad,primary_local8_clear=primary&~local_bad)
            for name,mask in variants.items():
                count = int(mask[t[ids]].sum()); duration = int(mask.sum())
                intervals[f's{s}_c{cid}_{name}'] = spans(mask)
                sensitivity.append(dict(shank=s,run_id=choice['run_id'],cluster_id=cid,scenario=name,original_events=len(ids),included_events=count,omitted_events=len(ids)-count,exposure_samples=duration,nominal_seconds=duration/fs,physical_seconds=duration/physical,nominal_observed_rate=count*fs/duration,physical_observed_rate=count*physical/duration))
            included = ids[primary[t[ids]]]
            row = dict(shank=s,run_id=choice['run_id'],cluster_id=cid,accepted=False,original_events=len(ids),proposed_events=len(included),omitted_events=len(ids)-len(included),exposure_samples=int(primary.sum()),peak_binary=peak,peak_global=int(r['peak_global']))
            for key in ['peak_guard','any_active_guard','half_active_guard','broad_warning','tight_warning','incomplete_context']:
                row[key] = int(ann[key][included].sum())
            row['coincidence_unavailable'] = int((~ann['broad_available'][included]).sum())
            row['original_isi_lt_2ms'] = int(r['isi_lt_2ms'])
            units.append(row)
            for i in ids[~primary[t[ids]]]:
                omitted.append(dict(shank=s,run_id=choice['run_id'],original_event_index=int(i),sample_index=int(t[i]),cluster_id=cid,boundary=bool(~interior[t[i]]),shared_core=bool(payload['shared_core'][i]),shared_shoulder=bool(payload['shared_shoulder'][i])))
            ax.scatter(t[included]/fs,np.full(len(included),candidates.index(cid)),s=1,color='#187f85',rasterized=True)
        if s == 3:
            for a,b in spans(shared_bad): ax.axvspan(a/fs,b/fs,color='#ce7333',alpha=.3)
        ax.set(yticks=range(len(candidates)),yticklabels=[f'c{x}' for x in candidates],xlim=(0,300),xlabel='Nominal seconds on original sample axis',title=f'Shank{s}: proposed event preview; not accepted')
        ss=[r for r in units if r['shank']==s]
        summaries.append(dict(shank=s,run_id=choice['run_id'],candidate_ids=candidates,units=len(candidates),original_events=sum(r['original_events'] for r in ss),proposed_events=sum(r['proposed_events'] for r in ss),omitted_events=sum(r['omitted_events'] for r in ss),exposure_samples=int(primary.sum()),nominal_seconds=int(primary.sum())/fs,physical_seconds=int(primary.sum())/physical,primary_policy='interior_without_shared_core_and_shoulder' if s==3 else 'interior_annotated'))
    fig.savefig(output/'raster_preview.png',dpi=130); plt.close(fig)
    table(output/'unit_preview.csv', units); table(output/'sensitivity.csv', sensitivity)
    table(output/'omitted_event_preview.csv', omitted); table(output/'all_cluster_proposals.csv',all_ledgers)
    np.savez_compressed(output/'analysis_intervals.npz',**intervals)
    fig,axs=plt.subplots(3,1,figsize=(13,10),layout='constrained')
    for s,ax in enumerate(axs,1):
        candidates=next(x['candidate_ids'] for x in summaries if x['shank']==s)
        for name,marker in [('interior','o'),('primary','x'),('primary_peak_clear','+'),('primary_local8_clear','s')]:
            values=[next(r['nominal_observed_rate'] for r in sensitivity if r['shank']==s and r['cluster_id']==cid and r['scenario']==name) for cid in candidates]
            ax.plot(range(len(candidates)),values,marker=marker,label=name)
        ax.set(xticks=range(len(candidates)),xticklabels=[f'c{x}' for x in candidates],ylabel='Observed events / nominal second',title=f'Shank{s}: counts and denominators change together')
        ax.legend(fontsize=8,ncol=2)
    fig.savefig(output/'rate_sensitivity.png',dpi=130);plt.close(fig)
    proposal=dict(schema='extra4-w16d-subset-policy-proposal-v1',state='awaiting_user_acceptance',date='2026-11-24',recording='extra_4',shanks=summaries,
        units_accepted=False,policy_adopted=False,original_outputs_modified=False,merge_or_split=False,
        interior_half_open=[100,2999900],nominal_fs_hz=10000,physical_fs_hz=10080,
        shared_definition='Shank3 W15C core: >=256 original channels flat; shoulder: +/-500 samples around core, minus core.',
        mask_semantics='Half-open integer sample intervals; event-center selection; waveform windows may cross mask edges.',
        primary_annotations='Retain peak/active guards and full-2048 broad/tight warnings; unavailable stays unknown. No automatic removal for these annotations.',
        sensitivity_only=['primary_peak_clear','primary_local8_clear'],
        rationale='Shanks1/2 retain observed-event summaries with annotations; shank3 additionally omits demonstrated shared-loss episodes and a conservative operational shoulder. Neither domain is validated clean or a true-rate correction.',
        limitations=['Not definitive neuron identities or exhaustive recovery.','Shoulder duration is operational, not validated filter settling.','Eight nearest active electrodes are a diagnostic proxy, not measured unit footprint.','Residual clipping and shared disturbances can remain.','Short-bin, synchrony and event-triggered conclusions need specific checks; shared-loss gaps are not biological silence.','Shank0 frozen policy remains unchanged; combined release must disclose policy differences.'],
        required_reporting=['Original and proposed counts with omitted event identities','Exact interval arrays and matching nominal/physical exposure','Quality flags and availability','Guard-clear rate sensitivities','Original run-qualified identities and sample axis'],
        pinned_files=pins)
    proposal['pinned_files']['scripts/prepare_w16d.py']=sha(Path(__file__))
    save(output/'proposal.json',proposal)
    save(output/'summary.json',dict(state='proposal_preview_not_accepted',shanks=summaries,candidate_units=len(units),all_cluster_rows=len(all_ledgers),sensitivity_rows=len(sensitivity),omitted_event_rows=len(omitted)))
    cards=''.join(f'<section><h2>Shank{x["shank"]}</h2><b>{x["units"]} candidates</b><p>{x["original_events"]:,} → {x["proposed_events"]:,} events<br>{x["nominal_seconds"]:.4f} nominal seconds</p><p>IDs: {", ".join(map(str,x["candidate_ids"]))}</p></section>' for x in summaries)
    trs=''.join(f'<tr><td>s{r["shank"]}:c{r["cluster_id"]}</td><td>{r["original_events"]}</td><td>{r["proposed_events"]}</td><td>{r["omitted_events"]}</td><td>{r["peak_guard"]}</td><td>{r["broad_warning"]} / {r["tight_warning"]}</td><td>{r["coincidence_unavailable"]}</td></tr>' for r in units)
    body='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>W16D acceptance proposal</title><style>body{font:16px/1.6 system-ui;background:#f3f6f8;color:#213b43;margin:0}main{max-width:1200px;margin:auto;padding:32px}header{background:#173c45;color:white;padding:30px;border-radius:16px}.cards{display:flex;gap:16px;margin:24px 0}section{background:white;padding:22px;border-radius:12px;flex:1}b{font-size:1.3em}a{color:#126477}nav{display:flex;flex-wrap:wrap;gap:18px;margin:20px 0}.note{background:#fff4dd;padding:22px;border-left:5px solid #d39732}img{width:100%;background:white}table{width:100%;border-collapse:collapse;background:white}th,td{padding:10px;text-align:left;border-bottom:1px solid #d8e2e6}th{background:#dce9ec}@media(max-width:750px){.cards{display:block}main{padding:12px}}</style><main><header><p>EXTRA_4 · W16D · ACCEPTANCE CHECKPOINT</p><h1>30 proposed units, with explicit analysis domains</h1><p>Shanks1–3; shank0's accepted 11-unit release stays frozen.</p><strong>Preview only: neither these subsets nor these policies are accepted yet.</strong></header>'''
    body+='<div class="cards">'+cards+'</div><nav><a href="proposal.json">Exact proposal</a><a href="unit_preview.csv">Every candidate</a><a href="all_cluster_proposals.csv">All 128 cluster proposals</a><a href="omitted_event_preview.csv">Every proposed omission</a><a href="sensitivity.csv">Counts and exposures</a><a href="../w16d-validation01/checks.json">Independent checks</a></nav>'
    body+='''<h2>Recommended policy</h2><p><strong>All three shanks:</strong> require a complete +/-100-sample raw context: [100, 2,999,900). Preserve original event IDs and time; retain quality warnings as annotations, including unknown assessments.</p><p><strong>Shank3 additionally:</strong> omit the documented shared-flat core and its +/-500-sample shoulder from both event counts and duration. This is a conservative operational analysis domain, not a claim that the remaining time is clean.</p><p>Peak-guard and eight-neighbor guard exclusions remain sensitivity comparisons, not primary censoring rules. No merge, split, promotion of held units or import from alternative sorts is proposed.</p><div class="note"><h2>What acceptance would mean</h2><p>Accept the listed 5 + 17 + 8 clusters as putative units and the stated per-shank analysis policies. Then generate separately versioned accepted derived tables and summaries. The 51 holds and 47 withheld clusters remain outside this subset with their reasons preserved.</p><p>Rates describe observed events in the declared domain; they are not estimated true neuronal firing rates. Signal-loss gaps cannot establish neuronal silence. Residual clipping, ambiguous events and unknown quality remain disclosed.</p></div><h2>Candidate event preview</h2><p>Orange marks the shared-loss domain omitted on shank3. These previews do not alter the sorter output.</p><img src="raster_preview.png" alt="Candidate event preview by shank"><h2>Rate sensitivity</h2><p>Each scenario changes event counts and its own denominator together. Coincident curves can overlap.</p><img src="rate_sensitivity.png" alt="Observed rate sensitivities"><h2>Residual annotations after the proposed primary rules</h2><p>Flags overlap. Guard overlap is not an artifact verdict; no warning is not proof of clean data.</p><table><tr><th>Unit</th><th>Original</th><th>Proposed</th><th>Omitted</th><th>Peak guard</th><th>Broad / tight</th><th>Unknown coincidence</th></tr>'''+trs+'</table><p>See W16A/B/C for waveform and identity evidence. These are conservative putative subsets, not definitive neuron counts. Next after explicit acceptance: adopted derived revisions, then W17 combined release audit.</p></main></html>'
    (output/'index.html').write_text(body,encoding='utf-8')
    save(output/'manifest.json',{p.name:sha(p) for p in output.iterdir()})
    print(read(output/'summary.json'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    run(p.parse_args().output)
