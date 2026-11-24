"""Audit the shank0 release and a fresh W12 replay without editing either."""
import argparse
import csv
import html
import importlib.metadata
import json
from pathlib import Path
import subprocess
import numpy as np
from shank_input import ROOT, sha, channel_ids, probe

BASE = ROOT/'results/extra4_shank0'


def read(path):
    return json.loads(path.read_text())


def verify(folder, name):
    manifest = read(folder/name)
    for relative, digest in manifest.items():
        path = (folder/relative).resolve()
        if not path.is_relative_to(folder.resolve()) or sha(path) != digest:
            raise ValueError(f'Manifest mismatch: {path}')
    return len(manifest)


def run(replay, inputs, runtime, output):
    output = output.resolve()
    if output.exists() or not output.is_relative_to(BASE):
        raise ValueError('Fresh shank0 result directory required')
    work = read(ROOT/'configs/extra4_shank0_working_run.json')
    revision = read(ROOT/work['curation_revision_path'])
    accepted = set(revision['accepted_cluster_ids'])
    original = ROOT/work['derived_results_path']
    assert sha(original/'report-manifest.json') == work['derived_report_manifest_sha256']
    assert sha(ROOT/revision['policy_path']) == revision['policy_sha256']
    assert sha(ROOT/revision['proposal_ledger']) == revision['proposal_ledger_sha256']
    manifests = {}
    for directory in ['w7b-exclude248-01','w7b-control01','pilot01-w7a-reviewed',
                      'w7b-review01','w8-checkpoint01','w9-good-review01',
                      'w10-population-review01','w11-exposure-review01','w12-curated-v1']:
        folder = BASE/directory
        name = 'output-manifest.json' if directory in ['w7b-exclude248-01','w7b-control01'] else 'report-manifest.json'
        count = verify(folder, name)
        manifests[str((folder/name).relative_to(ROOT))] = dict(sha256=sha(folder/name), files_verified=count)
        summary = read(folder/'summary.json') if (folder/'summary.json').exists() else {}
        for key in ['input_manifests', 'inputs']:
            for relative, digest in summary.get(key, {}).items():
                target = ROOT/relative
                candidate = target/('output-manifest.json' if (target/'output-manifest.json').exists() else 'report-manifest.json')
                assert sha(candidate) == digest, str(candidate)
    w9 = read(BASE/'w9-good-review01/summary.json')
    for key, relative in [('w8_manifest_sha256','w8-checkpoint01/report-manifest.json'),
                          ('w7_manifest_sha256','w7b-review01/report-manifest.json')]:
        assert w9[key] == sha(BASE/relative)
    assert revision['run_manifest_sha256'] == sha(BASE/'w7b-exclude248-01/output-manifest.json')
    assert revision['w11_report_manifest_sha256'] == sha(BASE/'w11-exposure-review01/report-manifest.json')
    verify(replay, 'report-manifest.json'); verify(inputs, 'manifest.json')
    comparison = {}
    # HTML has manual findings links; visual-review record is human-authored.
    # All other artifacts, including numerical tables, NPZs and final PNGs, must match.
    for path in original.iterdir():
        if path.name in ['index.html','visual_review.json','report-manifest.json']:
            continue
        assert sha(path) == sha(replay/path.name), path.name
        comparison[path.name] = sha(path)
    visual = read(original/'visual_review.json')
    assert sha(ROOT/visual['findings_path']) == visual['findings_sha256']
    with (ROOT/'docs/reviews/2026-11-24-w12-curation-ledger.csv').open(newline='') as f:
        ledger = list(csv.DictReader(f))
    selected = [r for r in ledger if r['run'] == work['run_id']]
    assert len(selected) == 58 and len({int(r['cluster_id']) for r in selected}) == 58
    assert {int(r['cluster_id']) for r in selected if r['included_in_accepted_subset'] == 'True'} == accepted
    for r in selected:
        is_accepted = int(r['cluster_id']) in accepted
        assert (r['decision_status'] == 'accepted_putative_subset') == is_accepted
        assert r['human_decision'] == ('accepted_2026-11-24' if is_accepted else 'pending')
    src = BASE/'w7b-exclude248-01/kilosort4'
    cmap = np.load(src/'channel_map.npy').ravel()
    np.testing.assert_array_equal(cmap, np.delete(np.arange(512), 248))
    geometry = probe(0)
    np.testing.assert_array_equal(np.load(src/'channel_positions.npy'), np.column_stack((geometry['xc'],geometry['yc']))[cmap])
    oldmap = np.genfromtxt(ROOT/'configs/pilot01/geometry/channel_map.csv', delimiter=',', names=True, dtype=int)
    np.testing.assert_array_equal(oldmap['original_channel_id'], channel_ids()[0])
    assert channel_ids()[0,248] == 1921
    assert geometry == read(ROOT/'configs/pilot01/geometry/probe.json')
    contract = read(BASE/'w7b-exclude248-01/run_contract.json')
    versions = {name:importlib.metadata.version(name) for name in contract['versions']}
    assert versions == contract['versions']
    assert sha(ROOT/'.venv/Lib/site-packages/kilosort/run_kilosort.py') == contract['sorter_source_sha256']
    assert sha(ROOT/'scripts/run_w7b.py') == contract['script_sha256']
    rt = read(runtime)
    assert all(rt[k] for k in ['nearest_neighbors_match_numpy','kilosort_neighbor_graph_passed','cuda_passed'])
    audit = read(inputs/'summary.json')
    assert audit['source_values_compared'] == 1536000000 and audit['binary_shank'] == 0
    assert audit['binary_sha256'] == contract['raw_sha256']
    policy = read(ROOT/revision['policy_path'])
    assert [policy['nominal_fs_hz'],policy['physical_fs_hz']] == [10000,10080]
    assert policy['primary_analysis_interval_half_open'] == [100,2999900]
    assert policy['primary_exposure_samples'] == 2999800
    assert not policy['quality_based_event_removal'] and not policy['quality_based_denominator_removal']
    code_paths = sorted((ROOT/'scripts').glob('*.py')) + sorted((ROOT/'configs').glob('*.json'))
    code_paths += [ROOT/'legacy/utility/shank.py', ROOT/'tests/test_shank_input.py',
                   ROOT/'docs/reviews/2026-11-24-w12-curation-ledger.csv']
    code = {p.relative_to(ROOT).as_posix():sha(p) for p in code_paths}
    output.mkdir(parents=True)
    result = dict(schema='w13-shank0-release-audit-v1', state='passed',
        gate='go_to_W14_preparation; sorting_requires_per_shank_input_and_quality_gates',
        baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        manifests=manifests, replay_path=str(replay.relative_to(ROOT)), exact_replay_payloads=comparison,
        input_audit_manifest_sha256=sha(inputs/'manifest.json'), runtime_sha256=sha(runtime),
        code_and_config_sha256=code, versions=versions,
        original_sorter_events=38687, selected_run_clusters=58, accepted_units=11,
        accepted_events=18252, held_clusters=38, withhold_proposals=9,
        all_four_maps_verified=True, full_source_to_shank0_comparison_values=1536000000,
        original_outputs_modified=False, fresh_sort_performed=False,
        limitations=['GPU sorter not rerun in W13; W7B control equivalence remains prior evidence',
                    'Replay HTML navigation and human visual-review record are not byte-reproduced',
                    'Other-shank binary exports, quality decisions and sorts remain pending',
                    'W8-W12 review builders remain pilot-specific; do not run them on other shanks'])
    (output/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    lines = ['<!doctype html><meta charset="utf-8"><title>W13 shank0 release</title>',
        '<style>body{font:16px system-ui;max-width:1200px;margin:30px auto}td,th{padding:8px;border:1px solid #ccc}table{border-collapse:collapse}</style>',
        '<h1>W13: shank0 release checkpoint</h1><p>11 accepted putative units; 18,252 derived events. Original sorter and quality annotations preserved.</p>',
        '<p>Gate: proceed to W14 input preparation and channel-quality review. Remaining-shank sorting is conditional on those checks.</p>',
        '<p><a href="audit.json">Machine-readable audit</a> | <a href="../w12-curated-v1/index.html">Accepted W12 report</a> | <a href="../../../docs/development/extra4-expansion.md">Expansion procedure</a></p>',
        '<h2>All 58 selected-run clusters</h2><p>Reasons retain their original review wording. Current status below supersedes historical phrases such as “no acceptance applied”. Withhold proposals are not definitive noise labels.</p>',
        '<table><tr><th>Cluster</th><th>Sorter label</th><th>Current status</th><th>Recommendation</th><th>Reason</th></tr>']
    for r in selected:
        status = 'Accepted putative unit' if int(r['cluster_id']) in accepted else 'Outside subset; proposal pending'
        lines.append('<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in [r['cluster_id'],r['original_automated_label'],status,r['recommendation'],r['reason']])+'</tr>')
    (output/'index.html').write_text('\n'.join(lines)+'</table>',encoding='utf-8')
    (output/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in output.iterdir()},indent=2)+'\n')
    print(json.dumps(dict(state='passed',exact_replay_files=len(comparison),manifests_checked=len(manifests),accepted_units=11,accepted_events=18252)),flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['replay','inputs','runtime','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    run(a.replay.resolve(),a.inputs.resolve(),a.runtime.resolve(),a.output)
