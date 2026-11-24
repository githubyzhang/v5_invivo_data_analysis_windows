"""W7A: all-channel flat-guard replay and bounded saved-preprocessing review.

Pilot-specific, read-only inputs; no sorting, censoring or scientific adoption.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import sys

import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.review_pilot_round1 import sha, write_csv, RAW_SHA
from scripts.annotate_kilosort_from_custom import membership

N, C = 3000000, 512


def flat_intervals(values, minimum=10):
    edges = np.r_[0, np.flatnonzero(values[1:] != values[:-1]) + 1, len(values)]
    spans = np.column_stack((edges[:-1], edges[1:]))
    return spans[np.diff(spans, axis=1).ravel() >= minimum]


def expand_union(spans, length, padding=500):
    merged = []
    for a, b in spans:
        a, b = max(0, int(a)-padding), min(length, int(b)+padding)
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return np.asarray(merged, dtype=np.int64).reshape(-1, 2)


def choose_ranks(ids, maximum=3):
    return ids[np.unique(np.linspace(0, len(ids)-1, min(maximum, len(ids))).astype(int))] if len(ids) else ids


def run(output):
    output = output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'results/extra4_shank0'):
        raise ValueError('Use a fresh results/extra4_shank0 directory')
    evidence = ROOT/'worker_returns/extra4_shank0/pilot01/received'
    source = evidence/'outputs/pilot01/kilosort4'
    binary = ROOT/'data/extra4_shank0_float32.bin'
    detector = ROOT/'results/custom_detector/extra4_windows01/spikes.h5'
    sidecar = ROOT/'results/custom_detector/kilosort_pilot01_quality_windows01/external_quality.h5'
    frozen = json.loads((evidence/'return-manifest.json').read_text())['files']
    for name, item in frozen.items():
        assert sha(evidence/name) == item['sha256'], name
    assert sha(binary) == RAW_SHA
    input_hashes = {str(p.relative_to(ROOT)): sha(p) for p in [detector, sidecar]}
    times = np.load(source/'spike_times.npy').ravel()
    clusters = np.load(source/'spike_clusters.npy').ravel()
    peaks = np.ptp(np.load(source/'templates.npy'), axis=1).argmax(axis=1)
    mapping = np.genfromtxt(evidence/'geometry/channel_map.csv', delimiter=',', names=True, dtype=int)
    np.testing.assert_array_equal(mapping['binary_channel'], np.arange(C))
    positions = np.column_stack([mapping['x_um'], mapping['y_um']])
    old_guards = np.loadtxt(evidence/'outputs/preflight/prior_flat_guards.csv', delimiter=',', dtype=np.int64)
    with h5py.File(detector, 'r') as f:
        native_guards = f['quality/flat_guard_intervals'][:]
    with h5py.File(sidecar, 'r') as f:
        assert f.attrs['complete'] and f.attrs['annotation_only']
        assert f.attrs['detector_spikes_sha256'] == input_hashes[str(detector.relative_to(ROOT))]
        assert f.attrs['spike_times_sha256'] == sha(source/'spike_times.npy')
        assert f.attrs['spike_clusters_sha256'] == sha(source/'spike_clusters.npy')
        np.testing.assert_array_equal(f['events/sample_index'][:], times)
        np.testing.assert_array_equal(f['events/cluster_id'][:], clusters)
        flags = {name: ds[:] for name, ds in f['annotations'].items()}
        broad = f['intervals/broad_warning'][:]
        tight = f['intervals/tight_warning'][:]
    raw = np.memmap(binary, mode='r', dtype='<f4', shape=(N, C))
    output.mkdir(parents=True)
    coverage, runs, guard_rows = [], [], []
    concurrency = np.zeros(N, np.int16)
    by_second = np.zeros((C, 300), np.int32)
    channel248_mask = None
    for first in range(0, C, 32):
        block = np.array(raw[:, first:first+32].T, order='C')
        for ch in range(first, first+len(block)):
            x = block[ch-first]
            assert np.isfinite(x).all()
            flat = flat_intervals(x)
            guards = expand_union(flat, N)
            gid = int(mapping['original_channel_id'][ch])
            np.testing.assert_array_equal(guards, old_guards[old_guards[:, 0] == gid, 1:])
            np.testing.assert_array_equal(guards, native_guards[native_guards[:, 0] == gid, 1:])
            mask = np.zeros(N, bool)
            for a, b in guards:
                mask[a:b] = True
                guard_rows.append(dict(binary_channel=ch, global_channel=gid, start=int(a), stop=int(b)))
            for a, b in flat:
                runs.append(dict(binary_channel=ch, global_channel=gid, start=int(a), stop=int(b), value=float(x[a])))
            concurrency += mask
            by_second[ch] = mask.reshape(300, 10000).sum(axis=1)
            if ch == 248:
                channel248_mask = mask.copy()
            coverage.append(dict(binary_channel=ch, global_channel=gid,
                zero_samples=int(np.count_nonzero(x == 0)), flat_runs=len(flat),
                flat_samples=int(np.diff(flat, axis=1).sum()),
                longest_flat_samples=int(np.diff(flat, axis=1).max()) if len(flat) else 0,
                guard_intervals=len(guards), guard_samples=int(mask.sum()), guard_fraction=float(mask.mean()),
                seconds_touched=int(np.count_nonzero(by_second[ch])),
                raw_matches_frozen_and_native=True))
        print(f'Raw guard replay verified: {first+len(block)}/512 channels', flush=True)
    other_concurrency = concurrency - channel248_mask
    write_csv(output/'channel_coverage.csv', coverage)
    write_csv(output/'flat_runs.csv', runs)
    write_csv(output/'guard_intervals.csv', guard_rows)
    np.savez_compressed(output/'guard_tracks.npz', guarded_samples_per_second=by_second,
        concurrent_channels=concurrency, concurrent_channels_except248=other_concurrency)
    top = np.argsort([-row['guard_samples'] for row in coverage], kind='stable')[:12]
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), layout='constrained')
    axes[0].bar(np.arange(11), [coverage[i]['guard_fraction']*100 for i in top[1:]])
    axes[0].set(xticks=np.arange(11), xticklabels=[f'b{i}' for i in top[1:]], ylabel='Guarded time (%)',
        title='Highest guard coverage excluding b248 (b248 separately: 79.7529%)')
    im = axes[1].imshow(by_second[top]/10000, aspect='auto', vmin=0, vmax=1, extent=[0, 300, 12, 0])
    axes[1].set(yticks=np.arange(12)+.5, yticklabels=[f'b{i}' for i in top], xlabel='Nominal seconds', title='Guarded fraction per second')
    fig.colorbar(im, ax=axes[1])
    axes[2].plot(np.arange(300), other_concurrency.reshape(300, 10000).max(axis=1))
    axes[2].set(xlabel='Nominal seconds', ylabel='Channels guarded', title='Maximum concurrent guards each second, excluding b248; not a censoring mask')
    fig.savefig(output/'guard_overview.png', dpi=140)
    plt.close(fig)

    # Deterministic selections are based on annotations/time, before waveform inspection.
    windows = []
    for i, (a, b) in enumerate(broad):
        windows.append(dict(name=f'coincidence_{i+1}', reason='Every broad warning interval', center=int((a+b)//2), start=int(a), stop=int(b), event_index=-1))
    remaining = other_concurrency.copy()
    for i in range(3):
        center = int(np.argmax(remaining))
        if remaining[center] <= 1:
            break
        windows.append(dict(name=f'guard_episode_{i+1}', reason='Highest remaining concurrent guard count except248; ties earliest; centers separated by >1 nominal second', center=center, start=center, stop=center+1, event_index=-1))
        remaining[max(0, center-10000):min(N, center+10001)] = 0
    for guarded in [True, False]:
        ids = np.flatnonzero((clusters == 36) & (flags['peak_channel_flat_guard'] == guarded) & (times >= 500) & (times < N-500))
        for i, event in enumerate(choose_ranks(ids)):
            t = int(times[event])
            windows.append(dict(name=f'cluster36_{"guard" if guarded else "outside"}_{i+1}',
                reason='First/middle/last event rank with complete context in this annotation stratum', center=t, start=t, stop=t+1, event_index=int(event)))
    write_csv(output/'window_selection.csv', windows)
    event_ids = np.flatnonzero(flags['broad_warning'] | flags['tight_warning'] | flags['peak_channel_flat_guard'])
    write_csv(output/'flagged_events.csv', [dict(final_event_index=int(i), sample_index=int(times[i]), cluster_id=int(clusters[i]),
        peak_binary=int(peaks[clusters[i]]), broad=bool(flags['broad_warning'][i]), tight=bool(flags['tight_warning'][i]),
        peak_guard=bool(flags['peak_channel_flat_guard'][i])) for i in event_ids])

    # The only pickle-bearing input is the explicitly hash-verified local pilot ops.
    import torch
    from kilosort.io import load_ops, bfile_from_ops
    device = torch.device('cuda')
    ops = load_ops(source/'ops.npy', device=device)
    np.testing.assert_array_equal(ops['probe']['chanMap'], np.arange(C))
    bf = bfile_from_ops(ops=ops, filename=binary, device=device)
    assert bf.NT == 60000 and bf.nt == 61 and bf.imin == 0
    references = json.loads((evidence/'outputs/pilot01/review/preprocessed_stats.json').read_text())
    anchors = []
    cache = {}

    def batch_read(batch):
        if batch not in cache:
            # Bound host memory; windows may revisit a batch.
            cache.clear()
            tensor, inds = bf.padded_batch_to_torch(batch, ops=ops, return_inds=True)
            a = tensor.cpu().numpy()
            assert np.isfinite(a).all() and inds[0] == batch*60000-61
            cache[batch] = a
        return cache[batch]

    for reference in references:
        a = batch_read(reference['batch'])
        current = dict(batch=reference['batch'], minimum=float(a.min()), maximum=float(a.max()),
            std_percentiles=np.percentile(a.std(axis=1), [0, 25, 50, 75, 100]).tolist())
        for field in ['minimum', 'maximum', 'std_percentiles']:
            np.testing.assert_allclose(current[field], reference[field], rtol=1e-5, atol=1e-5)
        anchors.append(current)
    print('Saved preprocessing matches all three historical batch-statistic anchors', flush=True)
    metrics = []
    for window in windows:
        center = window['center']
        start, stop = max(0, center-500), min(N, center+501)
        processed = np.empty((C, stop-start), np.float32)
        for batch in range(start//60000, (stop-1)//60000+1):
            lo, hi = max(start, batch*60000), min(stop, (batch+1)*60000)
            a = batch_read(batch)
            processed[:, lo-start:hi-start] = a[:, lo-batch*60000+61:hi-batch*60000+61]
        unscaled = np.array(raw[start:stop].T)
        ids = np.flatnonzero((times >= start) & (times < stop))
        if window['event_index'] >= 0:
            channels = np.argsort(np.linalg.norm(positions-positions[248], axis=1), kind='stable')[:8]
        else:
            # Fixed spatial spread plus most guarded channel; avoid selecting traces by amplitude.
            channels = np.array([0, 64, 128, 192, 248, 320, 384, 511])
        np.savez_compressed(output/(window['name']+'.npz'), raw_unscaled=unscaled, preprocessed=processed,
            sample_indices=np.arange(start, stop), displayed_channels=channels, event_indices=ids,
            center=center, event_index=window['event_index'])
        axis = (np.arange(start, stop)-center)/10
        fig, axes = plt.subplots(3, 1, figsize=(12, 9), layout='constrained')
        centered = (unscaled-np.median(unscaled[:, :min(200, stop-start)], axis=1)[:, None])*1e6
        raw_offset = max(float(np.percentile(np.ptp(centered[channels], axis=1), 80))*1.2, 1)
        for j, ch in enumerate(channels):
            axes[0].plot(axis, centered[ch]+j*raw_offset, lw=.6, label=f'b{ch}')
            axes[1].plot(axis, processed[ch]+j*15, lw=.6)
        axes[0].legend(ncol=8, fontsize=8)
        axes[0].set(title=f'{window["name"]}: raw; separate-channel offsets {raw_offset:.3g}', ylabel='Centered input x1e6 (uncalibrated)')
        axes[1].set(title='Saved highpass / CAR / whitening / drift reconstruction; offsets 15', ylabel='Transformed units')
        axes[2].scatter((times[ids]-center)/10, clusters[ids], s=12, c=np.where(flags['broad_warning'][ids], 'red', 'black'))
        axes[2].set(xlabel=f'Nominal ms relative to sample {center}', ylabel='Original cluster ID', ylim=(-1, 59))
        for ax in axes:
            ax.axvline(0, color='gray', lw=.7)
            for lo, hi in broad:
                if lo < stop and hi > start:
                    ax.axvspan((max(lo, start)-center)/10, (min(hi, stop)-center)/10, color='red', alpha=.12)
            ax.set_xlim(axis[0], axis[-1])
        fig.savefig(output/(window['name']+'.png'), dpi=140)
        plt.close(fig)
        metrics.append(dict(window=window['name'], start=start, stop=stop, events=len(ids),
            broad_events=int(flags['broad_warning'][ids].sum()), peak_guard_events=int(flags['peak_channel_flat_guard'][ids].sum()),
            concurrent_guards_except248_at_center=int(other_concurrency[center]),
            max_abs_processed=float(np.abs(processed).max()), channels_exceeding_abs6=int(np.any(np.abs(processed)>6, axis=1).sum())))
        print(f'Saved review window {window["name"]}', flush=True)
    del bf
    write_csv(output/'window_metrics.csv', metrics)
    assert sha(binary) == RAW_SHA
    for name, digest in input_hashes.items():
        assert sha(ROOT/name) == digest
    for name, item in frozen.items():
        assert sha(evidence/name) == item['sha256'], name
    summary = dict(schema='pilot-w7a-artifact-review-v1', raw_sha256=RAW_SHA, input_sha256=input_hashes,
        script_sha256=sha(Path(__file__)), frozen_payloads_unchanged=len(frozen),
        raw_channels_replayed=C, all_guards_match_both_frozen_and_native=True,
        channels_with_guards=sum(r['guard_samples']>0 for r in coverage),
        top_channels=[coverage[i] for i in top],
        maximum_concurrent_guards_except248=int(other_concurrency.max()),
        samples_any_guard_except248=int(np.count_nonzero(other_concurrency)),
        samples_at_least_two_guards_except248=int(np.count_nonzero(other_concurrency>=2)),
        broad_intervals=broad.tolist(), tight_intervals=tight.tolist(), flagged_events=len(event_ids),
        broad_events=int(flags['broad_warning'].sum()), tight_events=int(flags['tight_warning'].sum()),
        peak_guard_events=int(flags['peak_channel_flat_guard'].sum()),
        reconstructed_windows=len(windows), preprocessing_anchor_tolerance=dict(rtol=1e-5, atol=1e-5),
        preprocessing_anchors=anchors, ops_sha256=sha(source/'ops.npy'),
        environment={name: importlib.metadata.version(name) for name in ['numpy', 'scipy', 'torch', 'kilosort', 'faiss-cpu']},
        python=sys.version, device=torch.cuda.get_device_name(), events_removed=0, labels_changed=False, sorting_rerun=False,
        interpretation='Guards/warnings are diagnostics, not clipping or artifact ground truth; no unit mask or exposure adopted.')
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    figures = ['guard_overview']+[w['name'] for w in windows]
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>W7A artifact review</title><style>body{font:16px system-ui;max-width:1250px;margin:30px auto}img{width:100%}</style><h1>W7A: guard and saved-preprocessing review</h1><p>Annotation-only evidence. No sorting, masking or relabeling. Red bands show global broad coincidence warnings, not proven artifacts. All times nominal; integer samples authoritative.</p><p><a href="summary.json">Summary</a> | <a href="channel_coverage.csv">All-channel coverage</a> | <a href="window_selection.csv">Selection ledger</a> | <a href="flagged_events.csv">Flagged events</a></p>'+''.join(f'<h2>{name}</h2><img src="{name}.png">' for name in figures), encoding='utf-8')
    (output/'report-manifest.json').write_text(json.dumps({p.name: sha(p) for p in output.iterdir() if p.is_file()}, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
