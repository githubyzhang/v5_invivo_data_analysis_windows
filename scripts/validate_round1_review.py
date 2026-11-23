"""Audit Round 1 selections directly against the immutable raw and sorted arrays."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate(report, evidence, binary):
    destination = report/'independent_checks.json'
    if destination.exists():
        raise ValueError('Independent audit already exists; do not overwrite')
    provenance = json.loads((report/'provenance.json').read_text())
    assert digest(binary) == provenance['raw_sha256']
    src = evidence/'outputs/pilot01/kilosort4'
    times = np.load(src/'spike_times.npy', allow_pickle=False).ravel()
    clusters = np.load(src/'spike_clusters.npy', allow_pickle=False).ravel()
    raw = np.memmap(binary, mode='r', dtype='<f4', shape=(3000000,512))
    with (report/'cluster_metrics.csv').open() as stream:
        metrics = {int(r['cluster_id']):r for r in csv.DictReader(stream)}
    with (evidence/'outputs/pilot01/review/cluster_review.csv').open() as stream:
        reference = {int(r['cluster_id']):r for r in csv.DictReader(stream)}
    total = 0
    for cid in provenance['target_clusters']:
        saved = np.load(report/f'cluster_{cid}_waveforms.npz', allow_pickle=False)
        ids, samples, channels = [saved[n] for n in ('final_event_indices','sample_indices','binary_channels')]
        assert len(np.unique(ids)) == len(ids)
        np.testing.assert_array_equal(clusters[ids], np.full(len(ids),cid))
        np.testing.assert_array_equal(times[ids], samples)
        assert np.all((samples >= 100)&(samples+100 < 3000000))
        np.testing.assert_array_equal(saved['relative_samples'],np.arange(-100,101))
        for n, sample in enumerate(samples):
            expected = np.array(raw[sample-100:sample+101,channels],dtype=np.float32)*1e6
            expected -= np.median(expected[:70],axis=0)
            np.testing.assert_array_equal(saved['centered_raw_scaled'][n],expected)
        if len(samples):
            np.testing.assert_allclose(saved['centered_raw_scaled'].mean(axis=0),
                                       saved['mean_all_channels'][:,channels],atol=1e-4,rtol=1e-5)
        m, r = metrics[cid], reference[cid]
        for new,old in [('events','events'),('automated_label','automated_label'),
                        ('isi_lt_10_samples','isi_lt_1ms'),('isi_lt_20_samples','isi_lt_2ms'),
                        ('template_peak_binary','peak_binary_channel'),('template_peak_global','peak_global_channel')]:
            assert m[new] == r[old],(cid,new)
        ts = times[clusters==cid]
        complete = np.count_nonzero((ts>=100)&(ts+100<3000000))
        assert len(samples) == min(complete,provenance['maximum_waveforms'])
        assert int(m['incomplete_raw_context_events']) == len(ts)-complete
        total += len(samples)
    # Follow up the flat trace visible in boundary_context.png, without masking it.
    prefix = np.asarray(raw[:20000,248])
    change = np.flatnonzero(prefix != prefix[0])
    boundary_ids = np.flatnonzero((times<61)|(times>=3000000-61))
    result = dict(schema='pilot-round1-independent-audit-v1',raw_waveforms_checked=total,
                  all_saved_raw_values_match_binary=True,selection_indices_match_final_arrays=True,
                  original_metric_columns_match=True,original_automated_labels_match=True,
                  boundary_events=[dict(cluster=int(clusters[i]),sample=int(times[i])) for i in boundary_ids],
                  channel_248_prefix=dict(global_channel=1921,search_samples=20000,initial_value=float(prefix[0]),
                      first_changed_sample=int(change[0]) if len(change) else None,
                      interpretation='Exact repeated raw value; observation only, not calibrated clipping or an adopted mask'),
                  validator_sha256=digest(Path(__file__)),raw_sha256=provenance['raw_sha256'])
    destination.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--binary',type=Path,required=True)
    args=parser.parse_args()
    validate(args.report,args.evidence,args.binary)
