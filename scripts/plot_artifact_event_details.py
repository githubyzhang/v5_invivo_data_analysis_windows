"""Add deterministic event closeups to a verified W7A packet; no new selections by shape."""
import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.review_pilot_round1 import sha, write_csv


def run(report):
    report = report.resolve()
    if not report.is_relative_to(ROOT/'results/extra4_shank0') or (report/'detail_selection.csv').exists():
        raise ValueError('Requires fresh closeups in a local review packet')
    for name, digest in json.loads((report/'report-manifest.json').read_text()).items():
        assert sha(report/name) == digest
    evidence = ROOT/'worker_returns/extra4_shank0/pilot01/received'
    frozen = json.loads((evidence/'return-manifest.json').read_text())['files']
    source = evidence/'outputs/pilot01/kilosort4'
    arrays = {}
    for name in ['spike_times', 'spike_clusters', 'templates', 'channel_positions']:
        path = source/(name+'.npy')
        assert sha(path) == frozen[str(path.relative_to(evidence)).replace('\\', '/')]['sha256']
        arrays[name] = np.load(path)
    times, clusters = [arrays[k].ravel() for k in ['spike_times', 'spike_clusters']]
    peaks = np.ptp(arrays['templates'], axis=1).argmax(axis=1)
    with (report/'flagged_events.csv').open() as stream:
        flagged = list(csv.DictReader(stream))
    groups = {}
    for j in range(1, 4):
        name = f'coincidence_{j}'
        with np.load(report/(name+'.npz')) as z:
            ids = [int(r['final_event_index']) for r in flagged if r['broad'] == 'True' and int(r['final_event_index']) in z['event_indices']]
        chosen = np.asarray(ids)[np.linspace(0, len(ids)-1, 3).astype(int)]
        groups[name] = [(name, int(i)) for i in chosen]
    for kind in ['guard', 'outside']:
        groups['cluster36_'+kind] = []
        for j in range(1, 4):
            name = f'cluster36_{kind}_{j}'
            with np.load(report/(name+'.npz')) as z:
                groups['cluster36_'+kind].append((name, int(z['event_index'])))
    ledger = []
    for group, selections in groups.items():
        fig, axes = plt.subplots(3, 2, figsize=(12, 9), layout='constrained')
        for row, (name, event) in enumerate(selections):
            cid = int(clusters[event])
            channels = np.argsort(np.linalg.norm(arrays['channel_positions']-arrays['channel_positions'][peaks[cid]], axis=1), kind='stable')[:4]
            with np.load(report/(name+'.npz')) as z:
                offsets = np.arange(-30, 51)
                columns = times[event]+offsets-z['sample_indices'][0]
                assert columns.min() >= 0 and columns.max() < len(z['sample_indices'])
                raw = z['raw_unscaled'][channels[:, None], columns]
                raw = (raw-np.median(raw[:, :10], axis=1)[:, None])*1e6
                processed = z['preprocessed'][channels[:, None], columns]
            gap = max(float(np.ptp(raw, axis=1).max())*1.1, 1)
            for rank, ch in enumerate(channels):
                axes[row, 0].plot(offsets/10, raw[rank]+rank*gap, label=f'b{ch}', lw=.9)
                axes[row, 1].plot(offsets/10, processed[rank]+rank*15, lw=.9)
            axes[row, 0].legend(ncol=4, fontsize=8)
            axes[row, 0].set(title=f'Event {event}, cluster {cid}, sample {times[event]}', ylabel=f'Raw x1e6; offsets {gap:.3g}')
            axes[row, 1].set(title='Saved preprocessing, same nearest four channels', ylabel='Transformed units; offsets 15')
            for ax in axes[row]:
                ax.axvline(0, color='gray', lw=.6)
                ax.set_xlabel('Nominal ms relative to original event sample')
            ledger.append(dict(group=group, context=name, final_event_index=event, sample_index=int(times[event]), cluster_id=cid,
                binary_channels=';'.join(map(str, channels)), relative_start=-30, relative_stop_inclusive=50))
        fig.savefig(report/(group+'_details.png'), dpi=140)
        plt.close(fig)
    write_csv(report/'detail_selection.csv', ledger)
    (report/'detail_provenance.json').write_text(json.dumps(dict(script_sha256=sha(Path(__file__)),
        selection='First/middle/last broad-warning event rank per interval; existing three guarded and three outside cluster36 events',
        selected_windows=len(ledger), raw_baseline='Median of offsets -30 through -21; x1e6 uncalibrated'), indent=2)+'\n')
    page = report/'index.html'
    page.write_text(page.read_text(encoding='utf-8')+'<h1>Event closeups</h1><p>Deterministic first/middle/last ranks; no shape-based selection. Near channels follow each original template peak.</p>'+''.join(f'<h2>{name}</h2><img src="{name}_details.png">' for name in groups), encoding='utf-8')
    (report/'report-manifest.json').write_text(json.dumps({p.name: sha(p) for p in report.iterdir() if p.is_file() and p.name != 'report-manifest.json'}, indent=2)+'\n')
    print(f'Saved {len(ledger)} event closeups in {len(groups)} figures')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    run(parser.parse_args().report)
