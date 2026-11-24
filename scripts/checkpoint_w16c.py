"""Package W16C's manual proposals and independently audit exposure interval unions.

This dated review recipe is not an automatic curation classifier. Reproduction
requires a fresh output directory; the reviewed ledger remains authoritative.
"""
import argparse
import csv
import html
from collections import Counter
from pathlib import Path
import numpy as np
from run_sorting import ROOT, read, save, sha, verify_manifest
from review_sorting_baseline import table

CANDIDATES = {5, 10, 14, 16, 20, 26, 30, 34}
WITHHOLD = {6, 9, 17, 18, 27, 28, 29, 33, 35, 36, 37, 38, 39, 40, 41}
REASONS = {
0: 'Stable localized waveform, but R about 0.360 and three short intervals leave single-unit confidence unresolved; distinct from c2 does not establish purity.',
1: 'Stable waveform and feature separation from c2 support a population, but the shared control origin and same-peak split remain unresolved; hold both without merging.',
2: 'Stable waveform, but identity relative to c1 remains unresolved; six short intervals and clipped/shared-ramp examples add event-quality concerns. No merge.',
3: '32 events on the c0 peak, variable quarter backgrounds and partial feature overlap: insufficient separation evidence.',
4: '30 events with localized troughs but sparse quarter evidence and Q about 0.5: retain for further review.',
5: 'Localized waveform persists across all and away quarters and guard-clear sensitivities; supportive refractory evidence. Five peak-guard events need explicit event policy.',
6: 'Seven events, weak variable raw support, two boundary events and a four-sample boundary doublet; insufficient unit evidence.',
7: '14 events with localized morphology but sparse temporal evidence and Q about 0.309; confidence unresolved.',
8: '12 events with localized troughs but variable quarter backgrounds and Q about 0.5; confidence unresolved.',
9: 'Eight events with substantial variable background and insufficient reproducible temporal support for this subset.',
10: 'Stable localized negative-positive waveform through all and away quarters; c11 has a different footprint and separated features. One peak-guard ramp event requires event policy.',
11: '98 events with localized quarter support but Q about 0.330; separation from c10 alone does not establish isolation.',
12: 'Same peak and similar raw mean to c13 (correlation about 0.901); feature tails overlap and split identity remains unresolved. No merge.',
13: 'Stable population, but identity relative to c12 is unresolved; clipped peak and shared-ramp examples require event-quality handling. Hold without merging.',
14: 'Stable localized waveform through all and away quarters and guard-clear sensitivity; no short intervals. Thirteen peak-guard events remain an explicit limitation.',
15: 'Stable quarter means, but a detached subgroup in the c15/c16 feature projection remains unexplained; three short intervals and 14 peak-guard events. Hold pending attribution, without splitting.',
16: 'Stable localized waveform through all and away quarters, supportive refractory evidence and dominant feature separation from c15. One shared-core event and two peak-guard events require policy.',
17: 'Four events with variable background and inadequate repeatable temporal evidence.',
18: 'Eight events with variable quarter backgrounds and inadequate repeatable temporal evidence.',
19: '34 events with localized troughs but Q about 0.5 and one incomplete context; separation from c20 remains limited by sparse evidence.',
20: 'Strong localized waveform persists across all and away quarters and guard-clear sensitivity; no short intervals and distinct footprint from sparse c19.',
21: '70 events (25/26/9/10 by quarter), weaker late support and limited two-channel feature comparison with c22; hold despite automated good.',
22: '38 localized events with Q about 0.309 and limited separation evidence from c21; hold.',
23: '54 localized events with variable quarter backgrounds and Q about 0.421; confidence unresolved.',
24: '23 events, variable amplitudes and overlapping limited features with c25; one broad warning. Sparse evidence does not justify a merge or inclusion.',
25: '29 events, absent Q1, variable backgrounds and overlap with c24; two broad warnings. Automated good is insufficient.',
26: 'Stable localized negative-positive waveform across all and away quarters and guard-clear sensitivity despite changed cross-run membership; no events imported. One peak-guard event requires policy.',
30: 'Stable sharp localized waveform across all and away quarters; very different raw footprint from c31 despite feature overlap. Two core events and one peak-guard event require policy.',
31: '91 localized events but Q about 0.264 and variable quarter backgrounds; distinct footprint from c30 does not establish purity.',
32: '23 events with localized troughs, variable backgrounds and Q about 0.421; confidence unresolved.',
33: 'Ten events with a four-sample complex overlapping deflection and unstable background; insufficient single-unit support.',
34: 'Positive-leading localized waveform persists across all and away quarters and guard-clear sensitivity; polarity alone is not rejection. Three peak-guard examples include shared ramps.',
35: 'Single complete event with oscillatory/noisy background; no reproducible unit evidence.',
40: 'Four events concentrated in one quarter with matching slow background; insufficient independent temporal support.',
}
for _cid in (27, 28, 29, 36, 37, 38, 39, 41):
    REASONS[_cid] = 'Single boundary event without a complete raw window; insufficient unit evidence.'


def rows(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def union(spans):
    merged = []
    for a, b in sorted((int(a), int(b)) for a, b in spans):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(b, merged[-1][1])
        else:
            merged.append([a, b])
    return merged


def membership(times, spans):
    # Interval search rather than the generator's full sample Boolean arrays.
    if not spans:
        return np.zeros(len(times), bool)
    a, b = np.asarray(spans).T
    pos = np.searchsorted(a, times, side='right') - 1
    return (pos >= 0) & (times < b[np.maximum(pos, 0)])


def run(output):
    output = output.resolve()
    assert output.is_relative_to(ROOT/'results') and not output.exists()
    base = ROOT/'results/extra4_shank3'
    review, exposure = base/'w16c-review01', base/'w16c-exposure01'
    manifests = [review/'report-manifest.json', exposure/'manifest.json',
                 base/'w16c-validation01/manifest.json', base/'w16c-exceptions01/manifest.json']
    for path in manifests:
        verify_manifest(path)
    inventory = rows(review/'unit_metrics.csv')
    quarters = rows(review/'quarter_metrics.csv')
    erows = {int(r['cluster_id']): r for r in rows(exposure/'exposure.csv')}
    source = ROOT/read(review/'summary.json')['run_path']
    config = read(source/'config.json')
    times = np.load(source/'kilosort4/spike_times.npy').ravel()
    clusters = np.load(source/'kilosort4/spike_clusters.npy').ravel()
    masks = np.load(base/'w15c-shared-review02/fixed_masks.npz')
    edge = np.diff(np.r_[False, ~masks['away'], False].astype(int))
    shared = list(zip(np.where(edge == 1)[0], np.where(edge == -1)[0]))
    guards = np.load(ROOT/'results/extra4/w14-quality01/intervals.npz')['guard']
    guards = guards[guards[:, 0] == 3]
    ledger = []
    assert set(REASONS) == set(range(42))
    for r in inventory:
        cid = int(r['cluster_id']); e = erows[cid]
        ct = times[clusters == cid]
        assert len(ct) == int(r['events']) == int(e['all_events'])
        channels = np.load(review/f'unit_{cid}.npz')['channels']
        for variant, extra in [('away', []), ('away_peak_clear', [int(r['peak_binary'])]), ('away_local_clear', channels)]:
            spans = union(shared + guards[np.isin(guards[:, 1], extra), 3:5].tolist())
            count = int((~membership(ct, spans)).sum())
            duration = config['samples'] - sum(b-a for a, b in spans)
            assert count == int(e[variant+'_events'])
            assert duration == int(e[variant+'_exposure_samples'])
            assert np.isclose(count*config['nominal_fs_hz']/duration, float(e[variant+'_nominal_rate']))
        q = [v for v in quarters if int(v['cluster_id']) == cid]
        assert sum(int(v['events']) for v in q) == len(ct)
        decision = 'propose_putative' if cid in CANDIDATES else 'withhold' if cid in WITHHOLD else 'hold'
        row = dict(recording='extra_4', shank_zero_based=3, run_id=r['run_id'], cluster_id=cid,
                   events=len(ct), automated_label=r['automated_label'], proposal=decision, accepted=False,
                   reason=REASONS[cid], quarter_counts='/'.join(v['events'] for v in q),
                   quarter_correlations='/'.join(v['raw_correlation_to_pooled'] for v in q))
        for key in ['R','Q','peak_binary','peak_global','isi_lt_1ms','isi_lt_2ms','peak_guard','any_active_guard','half_active_guard','broad_warning','tight_warning','incomplete_context']:
            row[key] = r[key]
        row['coincidence_unavailable'] = len(ct)-int(r['broad_available'])
        row['shared_assessment_available'] = r['shared_available']
        for key in ['core_events','shoulder_events','away_events']:
            row[key] = e[key]
        row['screen_page'] = f'screen_{cid//6+1}.png'
        row['analysis_limitation'] = 'Shared loss limits observability; event/exposure policy pending W16D. Away is not guaranteed clean.'
        ledger.append(row)
    assert len(ledger) == 42 and sum(r['events'] for r in ledger) == 17666
    output.mkdir()
    table(output/'proposal-ledger.csv', ledger)
    counts = Counter(r['proposal'] for r in ledger)
    totals = {k: sum(r['events'] for r in ledger if r['proposal'] == k) for k in counts}
    summary = dict(state='proposed_not_accepted', run_id='w15c-exclude25901', clusters=42, events=17666,
                   proposal_counts=dict(counts), proposal_event_counts=totals,
                   putative_candidate_ids=sorted(CANDIDATES), held_ids=[r['cluster_id'] for r in ledger if r['proposal']=='hold'],
                   withheld_ids=sorted(WITHHOLD), units_accepted=False, events_removed=False, merge_applied=False, policy_adopted=False,
                   visually_reviewed=dict(cluster_screens=7, away_screens=6, short_isi_pages=2, peak_guard_pages=13,
                       pairs=[[1,2],[0,2],[0,3],[12,13],[15,16],[10,11],[21,22],[24,25],[25,26],[30,31],[14,16],[19,20]]),
                   pair_metric_rows_reviewed=28,
                   limitation='Bounded competitor review; no claim of exhaustive isolation or clean exposure.')
    summary['candidate_quality_counts'] = {k:sum(int(r[k]) for r in ledger if r['cluster_id'] in CANDIDATES) for k in ['events','isi_lt_1ms','isi_lt_2ms','peak_guard','any_active_guard','half_active_guard','broad_warning','tight_warning','incomplete_context','coincidence_unavailable','core_events','shoulder_events']}
    save(output/'summary.json', summary)
    save(output/'checks.json',dict(state='passed', ledger_rows=42, events=17666, interval_union_count_exposure_checks=126,
          input_manifests={str(p.relative_to(ROOT)):sha(p) for p in manifests}, script_sha256=sha(Path(__file__))))
    links = [('All-cluster evidence','../w16c-review01/index.html'),('Raw exception review','../w16c-exceptions01/index.html'),('Exposure sensitivities','../w16c-exposure01/index.html'),('Evidence validation','../w16c-validation01/checks.json'),('Complete proposal ledger','proposal-ledger.csv'),('Accounting checks','checks.json')]
    cards = ''.join(f'<section class="card"><b>{counts[k]}</b><h2>{title}</h2><p>{totals[k]:,} original events</p></section>' for k,title in [('propose_putative','Putative candidates'),('hold','Hold'),('withhold','Withhold from subset')])
    trs = ''.join(f'<tr><td>c{r["cluster_id"]}</td><td>{r["automated_label"]}</td><td>{r["events"]:,}</td><td class="{r["proposal"]}">{r["proposal"]}</td><td>{html.escape(r["reason"])}</td><td><a href="../w16c-review01/{r["screen_page"]}">Waveforms</a></td></tr>' for r in ledger)
    body = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>W16C · Shank3 curation checkpoint</title><style>
body{font:16px/1.6 system-ui;background:#f3f6f8;color:#20353d;margin:0}main{max-width:1250px;margin:auto;padding:36px}header{background:#173c45;color:white;padding:30px;border-radius:16px}h1{font-size:2.2rem;margin:.2em 0}.cards{display:flex;gap:18px;margin:24px 0}.card{background:white;padding:20px;border-radius:12px;flex:1}.card b{font-size:2.3rem}.card h2{font-size:1.1rem}a{color:#126477}header a{color:#b7eff0}.note{border-left:5px solid #d6a13a;background:#fff7e5;padding:20px;margin:24px 0}table{border-collapse:collapse;width:100%;background:white}td,th{padding:12px;border-bottom:1px solid #d9e1e5;text-align:left;vertical-align:top}th{background:#dce9ec}.propose_putative{color:#176440;font-weight:bold}.hold{color:#865a0c}.withhold{color:#7c3f4a}nav{display:flex;gap:16px;flex-wrap:wrap;margin:20px 0}@media(max-width:700px){.cards{display:block}main{padding:12px}.table{overflow:auto}}</style><main><header><p>EXTRA_4 · FOURTH PHYSICAL SHANK · 2026-11-24</p><h1>W16C: waveform support, with exposure limits</h1><p>Selected run: w15c-exclude25901 · 42 clusters · 17,666 original events · 14 automated good / 28 mua</p><strong>Manual proposals only. No units accepted, events removed or clusters merged.</strong></header>'''
    body += '<div class="cards">'+cards+'</div><nav>'+''.join(f'<a href="{url}">{name}</a>' for name,url in links)+'</nav>'
    body += '<h2>Proposed candidates: c5, c10, c14, c16, c20, c26, c30, c34</h2><p>Localized waveforms persist through the recording quarters and diagnostic guard-clear comparisons. Candidate status does not accept every event. c1/c2 and c12/c13 remain held for unresolved split identity; c15 has an unexplained feature subgroup. No merge is proposed.</p>'
    body += '<div class="note"><h2>Signal loss is not neuronal silence</h2><p>The shared-flat core spans 7.2005 nominal seconds and the diagnostic shoulder another 0.9555 seconds. Only 17 events occur in the core, versus 17,625 away from core and shoulder. Excluding channel 259 did not restore observability. Annotations suffice to preserve exploratory flagged observations, but do not justify unqualified full-duration biological firing rates.</p><p>W16D must propose matching event and exposure rules for acceptance. Away and eight-neighbor guard-clear comparisons are diagnostics, not validated clean time.</p></div>'
    body += '<h2>Every cluster has a proposal and reason</h2><p>Hold means unresolved evidence. Withhold means insufficient support for this subset, not proof of artifact. Counts below are original, unfiltered events.</p><div class="table"><table><tr><th>Cluster</th><th>Auto label</th><th>Events</th><th>Proposal</th><th>Reason</th><th>Evidence</th></tr>'+trs+'</table></div><h2>Validation and next step</h2><p>Independent evidence audit: 42 clusters, 168 quarters, 28 pairs, 17,626 raw windows. Exception packet: 113 excerpts, six incomplete. Exposure extraction: 13,391 raw windows; independent interval-union audit: 126 count/denominator comparisons. All passed.</p><p>Next: W16D concrete subset and exposure-policy acceptance checkpoint for shanks1–3. Shank0 remains frozen. Original data and sorter results are preserved.</p></main></html>'
    (output/'index.html').write_text(body,encoding='utf-8')
    save(output/'report-manifest.json',{p.name:sha(p) for p in output.iterdir()})
    print(summary)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
