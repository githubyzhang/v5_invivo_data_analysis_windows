"""Audit W7A saved values, event identities and sample indexing; add diagnostics."""
import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np
import h5py
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.review_pilot_round1 import sha, write_csv


def run(report):
    report = report.resolve()
    if not report.is_relative_to(ROOT/'results/extra4_shank0') or (report/'independent_checks.json').exists():
        raise ValueError('Requires a local report without an existing audit')
    summary = json.loads((report/'summary.json').read_text())
    for name, digest in json.loads((report/'report-manifest.json').read_text()).items():
        assert sha(report/name) == digest, name
    evidence = ROOT/'worker_returns/extra4_shank0/pilot01/received'
    src = evidence/'outputs/pilot01/kilosort4'
    binary = ROOT/'data/extra4_shank0_float32.bin'
    assert sha(binary) == summary['raw_sha256']
    assert sha(src/'ops.npy') == summary['ops_sha256']
    raw = np.memmap(binary, mode='r', dtype='<f4', shape=(3000000, 512))
    times = np.load(src/'spike_times.npy').ravel()
    clusters = np.load(src/'spike_clusters.npy').ravel()
    with (report/'window_selection.csv').open() as stream:
        windows = list(csv.DictReader(stream))
    from kilosort.io import load_ops, bfile_from_ops
    ops = load_ops(src/'ops.npy', device=torch.device('cuda'))
    bf = bfile_from_ops(ops=ops, filename=binary, device=torch.device('cuda'))
    checked_values = 0
    for row in windows:
        with np.load(report/(row['name']+'.npz')) as z:
            indices = z['sample_indices']
            np.testing.assert_array_equal(indices, np.arange(indices[0], indices[-1]+1))
            np.testing.assert_array_equal(z['raw_unscaled'], raw[indices[0]:indices[-1]+1].T)
            expected_ids = np.flatnonzero((times >= indices[0]) & (times <= indices[-1]))
            np.testing.assert_array_equal(z['event_indices'], expected_ids)
            event = int(z['event_index'])
            if event >= 0:
                assert times[event] == int(z['center']) and clusters[event] == 36
            # Use the reader's returned absolute start, independently of the generator's +61 offset.
            for batch in np.unique(indices//ops['batch_size']):
                tensor, bounds = bf.padded_batch_to_torch(int(batch), ops=ops, return_inds=True)
                columns = np.flatnonzero(indices//ops['batch_size'] == batch)
                reference = tensor.cpu().numpy()[:, indices[columns]-bounds[0]]
                np.testing.assert_allclose(z['preprocessed'][:, columns], reference, atol=1e-6, rtol=1e-6)
            checked_values += z['raw_unscaled'].size
    del bf
    # Rebuild count tracks from stored intervals using an independent difference array.
    with (report/'guard_intervals.csv').open() as stream:
        guards = list(csv.DictReader(stream))
    delta = np.zeros(3000001, np.int32)
    channel_samples = np.zeros(512, np.int64)
    for row in guards:
        ch, a, b = [int(row[k]) for k in ['binary_channel', 'start', 'stop']]
        channel_samples[ch] += b-a
        if ch != 248:
            delta[a] += 1
            delta[b] -= 1
    concurrency = np.cumsum(delta[:-1])
    with np.load(report/'guard_tracks.npz') as z:
        np.testing.assert_array_equal(concurrency, z['concurrent_channels_except248'])
        np.testing.assert_array_equal(channel_samples, z['guarded_samples_per_second'].sum(axis=1))
    # Exact-flat time and padded-guard time are different quantities.
    delta[:] = 0
    affected_99 = set()
    with (report/'flat_runs.csv').open() as stream:
        flat_runs = list(csv.DictReader(stream))
    for row in flat_runs:
        ch, a, b = [int(row[k]) for k in ['binary_channel', 'start', 'stop']]
        assert b-a >= 10 and np.all(raw[a:b, ch] == float(row['value']))
        assert a == 0 or raw[a-1, ch] != raw[a, ch]
        assert b == len(raw) or raw[b, ch] != raw[b-1, ch]
        if ch != 248:
            delta[a] += 1
            delta[b] -= 1
            if a < 1000000 and b > 990000:
                affected_99.add(ch)
    flat_concurrency = np.cumsum(delta[:-1])
    with h5py.File(ROOT/'results/custom_detector/kilosort_pilot01_quality_windows01/external_quality.h5', 'r') as f:
        broad = f['annotations/broad_warning'][:]
        guarded = f['annotations/peak_channel_flat_guard'][:]
        interval_rows = []
        for i, (a, b) in enumerate(f['intervals/broad_warning'][:]):
            ids = np.flatnonzero((times >= a) & (times < b))
            interval_rows.append(dict(interval=i+1, start=int(a), stop=int(b), events=len(ids),
                clusters=';'.join(map(str, np.unique(clusters[ids]))), peak_guard_events=int(guarded[ids].sum()),
                max_concurrent_flat_channels_except248=int(flat_concurrency[a:b].max()),
                max_concurrent_guard_channels_except248=int(concurrency[a:b].max())))
    write_csv(report/'coincidence_interval_audit.csv', interval_rows)
    checks = dict(schema='pilot-w7a-independent-checks-v1', saved_windows=len(windows),
        raw_values_checked=checked_values, processed_values_rechecked=checked_values,
        event_indices_and_sample_alignment_pass=True, guard_concurrency_and_totals_pass=True,
        all_saved_flat_runs_maximal_and_exact=True, flat_runs_checked=len(flat_runs),
        maximum_simultaneous_flat_channels_except248=int(flat_concurrency.max()),
        earliest_maximum_flat_sample=int(flat_concurrency.argmax()),
        channels_flat_during_nominal_second99_except248=len(affected_99),
        broad_and_peak_guard_events=int(np.count_nonzero(broad & guarded)),
        broad_or_peak_guard_events=int(np.count_nonzero(broad | guarded)),
        script_sha256=sha(Path(__file__)))
    (report/'independent_checks.json').write_text(json.dumps(checks, indent=2)+'\n')
    (report/'report-manifest.json').write_text(json.dumps({p.name: sha(p) for p in report.iterdir() if p.is_file() and p.name != 'report-manifest.json'}, indent=2)+'\n')
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report', type=Path, required=True)
    run(p.parse_args().report)
