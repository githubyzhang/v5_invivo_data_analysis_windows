"""Save every short adjacent ISI and peak-guard event for bounded raw review."""
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_sorting import ROOT, read, save, sha, verify_manifest
from review_sorting_baseline import table


def run(report, output):
    report = report.resolve()
    output = output.resolve()
    assert not output.exists() and output.is_relative_to(ROOT / 'results')
    verify_manifest(report / 'report-manifest.json')
    meta = read(report / 'summary.json')
    source = ROOT / meta['run_path']
    config = read(source / 'config.json')
    baseline = ROOT / meta['baseline_report']
    verify_manifest(baseline / 'report-manifest.json')
    assert sha(ROOT / config['binary_path']) == config['pinned_files'][config['binary_path']]
    t = np.load(source / 'kilosort4/spike_times.npy').ravel()
    cl = np.load(source / 'kilosort4/spike_clusters.npy').ravel()
    flags = np.load(baseline / 'event_annotations.npz')
    np.testing.assert_array_equal(t, flags['sample_index'])
    np.testing.assert_array_equal(cl, flags['cluster_id'])
    raw = np.memmap(ROOT / config['binary_path'], mode='r', dtype='<f4',
                    shape=(config['samples'], config['binary_channels']))
    fs = config['nominal_fs_hz']
    entries = []
    for cid in np.unique(cl):
        ids = np.flatnonzero(cl == cid)
        for k in np.flatnonzero(np.diff(t[ids]) < fs * .002):
            entries.append(('short_isi', int(cid), int(ids[k]), int(ids[k + 1])))
    entries += [('peak_guard', int(cl[i]), int(i), int(i)) for i in np.flatnonzero(flags['peak_guard'])]
    output.mkdir(parents=True)
    rows, pages, verified = [], [], 0
    for kind in ['short_isi', 'peak_guard']:
        group = [e for e in entries if e[0] == kind]
        for start in range(0, len(group), 8):
            fig, axes = plt.subplots(4, 2, figsize=(14, 13), layout='constrained')
            page = f'{kind}_{start // 8 + 1}.png'
            for ax, (_, cid, i, j) in zip(axes.ravel(), group[start:start + 8]):
                channels = np.load(report / f'unit_{cid}.npz')['channels'][:3]
                a, b = max(0, int(t[i]) - 100), min(len(raw), int(t[j]) + 101)
                complete = a == t[i] - 100 and b == t[j] + 101
                values = np.array(raw[a:b][:, channels], dtype=np.float32) * 1e6
                # Incomplete boundary excerpts remain explicitly uncentered.
                offsets = np.median(values[:70], axis=0) if complete else np.zeros(3, np.float32)
                values -= offsets
                name = f'{kind}_c{cid}_{i}_{j}.npz'
                np.savez_compressed(output / name, event_indices=[i, j], sample_indices=t[[i, j]],
                                    start=a, stop=b, channels=channels, values=values,
                                    baseline_offsets=offsets, complete_context=complete)
                # Independent channel-by-channel readback checks exact saved numbers.
                z = np.load(output / name)
                for k, ch in enumerate(channels):
                    expected = np.asarray(raw[a:b, int(ch)], dtype=np.float32) * 1e6
                    if complete: expected -= np.median(expected[:70])
                    np.testing.assert_array_equal(z['values'][:, k], expected)
                verified += 1
                x = (np.arange(a, b) - t[i]) / fs * 1000
                for k, ch in enumerate(channels): ax.plot(x, values[:, k], label=f'b{ch}')
                ax.axvline(0, color='black', ls='--', lw=.8)
                if j != i: ax.axvline((t[j] - t[i]) / fs * 1000, color='red', ls='--', lw=.8)
                ax.set(title=f'c{cid} event {i}' + (f' / {j}; delta={t[j]-t[i]} samples' if j != i else '')
                       + ('' if complete else ' INCOMPLETE / UNCENTERED'),
                       xlabel='Nominal ms from first event', ylabel='Input x1e6, centered if complete')
                ax.legend(fontsize=7)
                row = dict(kind=kind, cluster_id=cid, event_a=i, event_b=j, sample_a=int(t[i]),
                           sample_b=int(t[j]), delta_samples=int(t[j]-t[i]), complete_context=bool(complete),
                           artifact=name, page=page)
                for flag in ['peak_guard', 'any_active_guard', 'broad_warning', 'broad_available', 'half_active_guard']:
                    row[flag + '_a'] = bool(flags[flag][i]); row[flag + '_b'] = bool(flags[flag][j])
                rows.append(row)
            for ax in axes.ravel()[len(group[start:start+8]):]: ax.set_visible(False)
            fig.suptitle(f'Shank{meta["shank_zero_based"]}: {kind}; diagnostic only, no censoring')
            fig.savefig(output / page, dpi=110); plt.close(fig); pages.append(page)
    table(output / 'exceptions.csv', rows)
    checks = dict(state='passed_raw_readback', excerpts_verified=verified,
                  short_isi_pairs=sum(e[0] == 'short_isi' for e in entries),
                  peak_guard_events=sum(e[0] == 'peak_guard' for e in entries),
                  incomplete_excerpts=sum(not r['complete_context'] for r in rows),
                  report_manifest_sha256=sha(report / 'report-manifest.json'),
                  baseline_manifest_sha256=sha(baseline / 'report-manifest.json'),
                  script_sha256=sha(Path(__file__)), pages=pages,
                  limitation='Diagnostic subset; flags are annotations, no events removed. Boundary snippets uncentered.')
    save(output / 'checks.json', checks)
    (output / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Curation exceptions</title>'
        '<h1>Raw exception review — no censoring</h1><p>Every adjacent interval below 2 nominal ms and every '
        'template-peak guard event. Dashed markers show event centers. Incomplete boundary context is uncentered.</p>'
        '<p><a href="exceptions.csv">Event inventory and flags</a> · <a href="checks.json">Readback checks</a></p>'
        + ''.join(f'<h2>{p}</h2><img style="width:100%;max-width:1400px" src="{p}">' for p in pages), encoding='utf-8')
    save(output / 'manifest.json', {p.name: sha(p) for p in output.iterdir()})
    print(checks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.report, args.output)
