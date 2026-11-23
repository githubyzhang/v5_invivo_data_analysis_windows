"""Read-only raw-waveform review of nine extra_4/shank0 pilot clusters.

No filtering, resampling, curation, sorting, or application of kept_spikes.
"""
import argparse
import csv
import hashlib
import html
import importlib.metadata
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

TARGETS = [34, 35, 5, 12, 2, 26, 29, 37, 58]
NSAMPLES, NCHANNELS, FS, PHYSICAL_FS = 3000000, 512, 10000, 10080
RAW_SHA = '11cd033eb0bda858f7598123a795f198078cc227d98d92543e8ea88f9e12eff0'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_table(path):
    with path.open() as stream:
        return {int(r['cluster_id']): r for r in csv.DictReader(stream, delimiter='\t')}


def selection(indices, maximum):
    """Evenly spread sorted event ranks, including both ends; deterministic."""
    return indices[np.unique(np.linspace(0, len(indices)-1, min(len(indices), maximum), dtype=int))] if len(indices) else indices


def acg_samples(times, radius=500):
    times = np.sort(times)
    pieces = [times[i+1:np.searchsorted(times, t+radius, side='right')]-t for i, t in enumerate(times)]
    positive = np.concatenate(pieces) if len(pieces) else np.array([], dtype=int)
    return np.concatenate([-positive, positive])


def run(evidence, binary, output, maximum=256):
    evidence, binary, output = evidence.resolve(), binary.resolve(), output.resolve()
    if output.exists() or output.is_relative_to(evidence) or output == binary or output.is_relative_to(binary.parent):
        raise ValueError('Choose a fresh report path outside evidence and raw-data storage')
    if maximum < 4:
        raise ValueError('At least four waveform examples are required')
    if binary.stat().st_size != NSAMPLES*NCHANNELS*4 or sha(binary) != RAW_SHA:
        raise ValueError('Unexpected pilot binary identity')
    manifest = json.loads((evidence/'return-manifest.json').read_text())['files']
    for name, item in manifest.items():
        if sha(evidence/name) != item['sha256']:
            raise ValueError(f'Frozen return mismatch: {name}')
    src = evidence/'outputs/pilot01/kilosort4'
    arr = lambda name: np.load(src/f'{name}.npy', allow_pickle=False)
    times, clusters, amplitudes = [arr(name).reshape(-1) for name in ('spike_times', 'spike_clusters', 'amplitudes')]
    templates, positions = arr('templates'), arr('channel_positions')
    pcs, pc_channels = arr('pc_features'), arr('pc_feature_ind')
    labels, contam = load_table(src/'cluster_KSLabel.tsv'), load_table(src/'cluster_ContamPct.tsv')
    mapping = np.genfromtxt(evidence/'geometry/channel_map.csv', delimiter=',', names=True, dtype=int)
    assert len(times) == len(clusters) == len(amplitudes) == len(pcs) == 39620
    assert np.issubdtype(times.dtype, np.integer) and np.issubdtype(clusters.dtype, np.integer)
    assert np.all((times >= 0) & (times < NSAMPLES)) and np.isfinite(pcs).all()
    assert templates.shape == (59, 61, 512) and len(np.unique(clusters)) == 59
    np.testing.assert_array_equal(positions, np.column_stack([mapping['x_um'], mapping['y_um']]))
    np.testing.assert_array_equal(arr('channel_map').ravel(), mapping['binary_channel'])
    peaks = np.ptp(templates, axis=1).argmax(axis=1)
    raw = np.memmap(binary, mode='r', dtype='<f4', shape=(NSAMPLES, NCHANNELS))
    output.mkdir(parents=True)
    relative = np.arange(-100, 101)
    central = (relative >= -20) & (relative <= 40)
    summaries, selections, comparisons, quarter_rows, pages = [], [], [], [], []
    for cid in TARGETS:
        ids = np.flatnonzero(clusters == cid)
        ids = ids[np.argsort(times[ids], kind='stable')]
        ts, amp = times[ids], amplitudes[ids]
        peak = int(peaks[cid])
        near = np.argsort(np.linalg.norm(positions-positions[peak], axis=1), kind='stable')[:8]
        valid = ids[(times[ids] >= 100) & (times[ids]+100 < NSAMPLES)]
        chosen = selection(valid, maximum)
        waveforms = np.empty((len(chosen), 201, NCHANNELS), dtype=np.float32)
        for n, event_id in enumerate(chosen):
            sample = int(times[event_id])
            segment = np.array(raw[sample-100:sample+101], dtype=np.float32)*1e6
            waveforms[n] = segment - np.median(segment[:70], axis=0)
            selections.append(dict(cluster_id=cid, final_event_index=int(event_id), sample_index=sample,
                                   nominal_s=sample/FS, physical_s=sample/PHYSICAL_FS,
                                   purpose='complete_raw_waveform', support_start=sample-100, support_stop_exclusive=sample+101))
        for event_id in ids[(times[ids] < 100) | (times[ids]+100 >= NSAMPLES)]:
            sample = int(times[event_id])
            selections.append(dict(cluster_id=cid, final_event_index=int(event_id), sample_index=sample,
                                   nominal_s=sample/FS, physical_s=sample/PHYSICAL_FS,
                                   purpose='incomplete_context_not_averaged', support_start=max(0,sample-100), support_stop_exclusive=min(NSAMPLES,sample+101)))
        mean = waveforms.mean(axis=0) if len(chosen) else None
        mean_peak_channel = int(np.ptp(mean[central], axis=0).argmax()) if mean is not None else None
        counts, _ = np.histogram(ts, np.arange(0, NSAMPLES+1, 100000))
        isi = np.diff(ts)
        row = dict(cluster_id=cid, automated_label=labels[cid]['KSLabel'], events=len(ids),
                   rate_hz_nominal=len(ids)/300, rate_hz_physical=len(ids)/(NSAMPLES/PHYSICAL_FS),
                   sorter_contamination_pct=float(contam[cid]['ContamPct']),
                   template_peak_binary=peak, template_peak_global=int(mapping['original_channel_id'][peak]),
                   isi_pairs=len(isi), isi_lt_10_samples=int(np.sum(isi<10)), isi_lt_20_samples=int(np.sum(isi<20)),
                   isi_lt_20_fraction=float(np.mean(isi<20)) if len(isi) else None,
                   minimum_isi_samples=int(isi.min()) if len(isi) else None,
                   occupied_10s_bins=int(np.count_nonzero(counts)),
                   first_sample=int(ts[0]), last_sample=int(ts[-1]),
                   incomplete_raw_context_events=len(ids)-len(valid), raw_waveforms_selected=len(chosen),
                   raw_mean_peak_binary=mean_peak_channel,
                   raw_mean_peak_global=int(mapping['original_channel_id'][mean_peak_channel]) if mean is not None else None,
                   raw_template_peak_distance_um=float(np.linalg.norm(positions[peak]-positions[mean_peak_channel])) if mean is not None else None)
        qmeans, qcounts = [], []
        for quarter in range(4):
            a, b = quarter*750000, (quarter+1)*750000
            qamp = amp[(ts >= a) & (ts < b)]
            selected_q = (times[chosen] >= a) & (times[chosen] < b)
            qmean = waveforms[selected_q].mean(axis=0) if selected_q.any() else np.full((201,512), np.nan)
            qmeans.append(qmean[:, near]); qcounts.append(int(selected_q.sum()))
            correlation = None
            if mean is not None and selected_q.sum() >= 4 and np.std(qmean[central,peak]) > 0 and np.std(mean[central,peak]) > 0:
                correlation = float(np.corrcoef(qmean[central,peak],mean[central,peak])[0,1])
            quarter_rows.append(dict(cluster_id=cid, quarter=quarter+1, start_sample=a, stop_sample_exclusive=b,
                                     events=len(qamp), selected_waveforms=int(selected_q.sum()),
                                     amplitude_median=float(np.median(qamp)) if len(qamp) else None,
                                     raw_peak_waveform_correlation_to_all_selected=correlation))
        np.savez_compressed(output/f'cluster_{cid}_waveforms.npz',
                            final_event_indices=chosen, sample_indices=times[chosen], relative_samples=relative,
                            binary_channels=near, global_channels=mapping['original_channel_id'][near],
                            centered_raw_scaled=waveforms[:,:,near],
                            mean_all_channels=mean if mean is not None else np.empty((0,512)),
                            quarter_means_near_channels=np.asarray(qmeans), quarter_selected_counts=qcounts)
        fig, ax = plt.subplots(4,2,figsize=(14,14),layout='constrained')
        fig.suptitle(f'Cluster {cid} — automated {row["automated_label"]}; n={len(ids)}; UNCURATED',fontsize=17)
        if mean is not None:
            for ch in near:
                ax[0,0].plot(relative/10,mean[:,ch],lw=1.1 if ch==peak else .7,alpha=1 if ch==peak else .55,label=f'b{ch}')
            p10,p90=np.percentile(waveforms[:,:,peak],[10,90],axis=0)
            ax[0,0].fill_between(relative/10,p10,p90,color='gray',alpha=.15,label='peak 10–90% events')
            ax[0,0].legend(ncol=3,fontsize=7)
        else:
            ax[0,0].text(.5,.5,'No full ±100-sample context\nDo not pad or average this event',ha='center',transform=ax[0,0].transAxes)
        ax[0,0].set(title=f'Raw triggered mean, {len(chosen)} selected events',xlabel='Nominal ms from event',ylabel='Source values ×1e6, baseline centered')
        ax[0,1].plot((np.arange(61)-20)/10,templates[cid][:,near],lw=.9)
        ax[0,1].set(title='Original whitened template, same 8 channels',xlabel='Nominal ms, index 20 origin',ylabel='Whitened units (not raw voltage)')
        ax[1,0].bar(np.arange(30)*10,counts/10,width=9,align='edge',color='#527caa')
        ax[1,0].set(xlabel='Nominal seconds',ylabel='Events/s per 10 s bin',title='Full-exposure event rate; no exclusions',xlim=(0,300))
        ax[1,1].scatter(ts/FS,amp,s=3,alpha=.35)
        for q in quarter_rows[-4:]:
            if q['amplitude_median'] is not None:ax[1,1].hlines(q['amplitude_median'],(q['quarter']-1)*75,q['quarter']*75,color='crimson')
        ax[1,1].set(xlabel='Nominal seconds',ylabel='Feature L2 amplitude',title='All event amplitudes; red = quarter median',xlim=(0,300))
        lags=acg_samples(ts)
        ax[2,0].hist(lags/10,bins=np.arange(-50.5,51,1),color='#527caa')
        ax[2,0].axvspan(-.2,.2,color='red',alpha=.18)
        ax[2,0].set(title=f'ACG: {row["isi_lt_20_samples"]}/{len(isi)} ISIs <20 samples',xlabel='Nominal lag ms; red ±2 sample suppression scale',ylabel='Pair counts (not normalized)')
        candidates=[int(c) for c in np.unique(clusters) if c!=cid and np.linalg.norm(positions[peaks[c]]-positions[peak])<=60]
        plotted=[]
        for other in candidates+[cid]:
            feature_col=np.flatnonzero(pc_channels[other]==peak)
            available=len(feature_col)==1
            comparisons.append(dict(target_cluster=cid, comparison_cluster=other,
                                    common_binary_channel=peak, feature_available=available,
                                    template_peak_distance_um=float(np.linalg.norm(positions[peaks[other]]-positions[peak]))))
            if not available:continue
            inds=selection(np.flatnonzero(clusters==other),1000)
            ax[2,1].scatter(pcs[inds,0,feature_col[0]],pcs[inds,1,feature_col[0]],s=7 if other==cid else 3,
                            alpha=.6 if other==cid else .22,label=f'{other}'+(' target' if other==cid else ''))
            plotted.append(other)
        row['pc_comparison_clusters']=','.join(map(str,[c for c in plotted if c!=cid]))
        ax[2,1].set(title=f'Common b{peak} PC projection; not full isolation',xlabel='PC1 (stored feature units)',ylabel='PC2 (stored feature units)')
        if plotted:ax[2,1].legend(fontsize=7,ncol=2)
        for quarter,qmean in enumerate(qmeans):
            if qcounts[quarter]:ax[3,0].plot(relative/10,qmean[:,np.flatnonzero(near==peak)[0]],label=f'Q{quarter+1}: {qcounts[quarter]} waveforms')
        ax[3,0].set(title=f'Raw peak b{peak}: four 75 s quarters',xlabel='Nominal ms from event',ylabel='Centered source values ×1e6')
        if len(chosen):ax[3,0].legend(fontsize=8)
        ax[3,1].axis('off')
        ax[3,1].text(0,.98,'\n'.join([
            f'Peak b{peak} / global {row["template_peak_global"]}',
            f'Sorter contamination estimate: {row["sorter_contamination_pct"]:.1f}%',
            f'Occupied bins: {row["occupied_10s_bins"]}/30',
            f'Incomplete ±100-sample contexts: {row["incomplete_raw_context_events"]}',
            f'Full exposure: 300 nominal / {NSAMPLES/PHYSICAL_FS:.6f} physical s',
            'No labels changed; no events removed.',
            'Raw: baseline median over event samples [-100,-31].',
            'No filtering/CAR applied to these raw windows.',
            '×1e6 is numerical scaling, not voltage calibration.',
            'Sparse ACGs cannot establish isolation.',
            'PC comparisons omit clusters without the common channel.',
            'Template similarity/merges are Round 2 scope.']),va='top',fontsize=10,linespacing=1.7)
        main_name=f'cluster_{cid}.png';fig.savefig(output/main_name,dpi=125);plt.close(fig)
        fig, axes=plt.subplots(1,4,figsize=(15,4),layout='constrained')
        if mean is not None:
            foot=np.ptp(mean[central],axis=0)
            nearby=np.linalg.norm(positions-positions[peak],axis=1)<=150
            plot=axes[0].scatter(positions[nearby,0],positions[nearby,1],c=foot[nearby],s=38)
            axes[0].scatter(*positions[peak],s=100,facecolors='none',edgecolors='red')
            axes[0].set_aspect('equal');fig.colorbar(plot,ax=axes[0],label='Raw mean peak-to-peak ×1e6')
            for axis,j in zip(axes[1:],selection(np.arange(len(chosen)),3)):
                axis.plot(relative/10,waveforms[j,:,near].T,lw=.8)
                axis.axvline(0,color='black',lw=.6)
                axis.set(title=f'Event sample {int(times[chosen[j]])}',xlabel='Nominal ms',ylabel='Centered source values ×1e6')
        else:
            start=max(0,int(ts[0])-100);stop=min(NSAMPLES,int(ts[0])+301)
            for axis,ch in zip(axes,near[:4]):
                axis.plot(np.arange(start,stop),np.asarray(raw[start:stop,ch])*1e6,lw=.8)
                axis.axvline(ts[0],color='red');axis.set(title=f'b{ch} / global {mapping["original_channel_id"][ch]}',xlabel='Original sample index',ylabel='Source values ×1e6 (uncentered)')
        if mean is not None:axes[0].set(title=f'Raw spatial mean; circle = template peak',xlabel='x (µm)',ylabel='y (µm)')
        fig.suptitle(f'Cluster {cid}: raw spatial support / individual traces')
        raw_name=f'cluster_{cid}_raw.png';fig.savefig(output/raw_name,dpi=125);plt.close(fig)
        summaries.append(row)
        pages.append(f'<h2 id="c{cid}">Cluster {cid}</h2><img src="{main_name}"><img src="{raw_name}">')
        print(f'Reviewed data for cluster {cid}: {len(ids)} events, {len(chosen)} raw windows',flush=True)

    # Contextual boundary screen covers all clusters, without expanding unit curation.
    boundary=np.flatnonzero((times<61)|(times>=NSAMPLES-61))
    boundary_rows=[dict(final_event_index=int(i),cluster_id=int(clusters[i]),sample_index=int(times[i]),
                        template_support_start=int(times[i])-20,template_support_stop_exclusive=int(times[i])+41,
                        template_support_complete=bool(times[i]>=20 and times[i]+40<NSAMPLES)) for i in boundary]
    write_csv(output/'boundary_events.csv',boundary_rows)
    fig,axes=plt.subplots(2,1,figsize=(14,7),layout='constrained')
    for ch in sorted(set(int(peaks[clusters[i]]) for i in boundary)):
        axes[0].plot(np.arange(500),np.asarray(raw[:500,ch])*1e6,label=f'b{ch}/g{mapping["original_channel_id"][ch]}',lw=.8)
    axes[0].set(title='Recording start: boundary-cluster peak electrodes',xlabel='Original sample index',ylabel='Uncentered source values ×1e6');axes[0].legend(ncol=3)
    centered=np.asarray(raw[:500],dtype=np.float32)*1e6
    centered-=np.median(centered[100:300],axis=0)
    p10,p50,p90=np.percentile(centered,[10,50,90],axis=1)
    axes[1].fill_between(np.arange(500),p10,p90,alpha=.25,label='10–90% across 512 channels')
    axes[1].plot(p50,label='Spatial median')
    for i in boundary:axes[1].axvline(times[i],color='red',alpha=.4)
    axes[1].set(title='Display baseline: per-channel median of samples [100,300)',xlabel='Original sample index; red = sorted boundary events',ylabel='Centered source values ×1e6');axes[1].legend()
    fig.savefig(output/'boundary_context.png',dpi=140);plt.close(fig)
    write_csv(output/'cluster_metrics.csv',summaries);write_csv(output/'raw_selection.csv',selections)
    write_csv(output/'quarter_metrics.csv',quarter_rows);write_csv(output/'pc_comparison_coverage.csv',comparisons)
    provenance=dict(schema='pilot-round1-review-v1',target_clusters=TARGETS,raw_path=str(binary),raw_sha256=RAW_SHA,
                    evidence_path=str(evidence),return_manifest_sha256=sha(evidence/'return-manifest.json'),
                    script_sha256=sha(Path(__file__)),python=sys.executable,
                    versions={p:importlib.metadata.version(p) for p in ['numpy','matplotlib','scipy','kilosort','faiss-cpu']},
                    nominal_fs=FS,physical_fs=PHYSICAL_FS,raw_context_samples=[-100,100],
                    baseline_samples_inclusive=[-100,-31],numerical_scale=1e6,voltage_calibration='not established',
                    selection='evenly spaced event ranks among complete contexts; no random selection',maximum_waveforms=maximum,
                    pc_comparison='PC1/2 at the target whitened-template peak, candidates within 60 um having that channel stored',
                    comparison_warning='2-D projection only; not an isolation score, classifier or complete neighboring population',
                    sorting_rerun=False,curation_applied=False,excluded_events=0)
    (output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    if sha(binary)!=RAW_SHA:raise ValueError('Raw input changed during review')
    for name,item in manifest.items():
        if sha(evidence/name)!=item['sha256']:raise ValueError(f'Evidence changed: {name}')
    (output/'validation.json').write_text(json.dumps(dict(raw_hash_before_after_matches=True,frozen_payloads_unchanged=len(manifest),
         final_events=39620,final_clusters=59,reviewed_clusters=TARGETS,labels_modified=False),indent=2)+'\n')
    nav=' | '.join(f'<a href="#c{c}">{c}</a>' for c in TARGETS)
    (output/'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>Pilot Round 1</title>
<style>body{font:16px system-ui;max-width:1500px;margin:30px auto;padding:20px;color:#172536}img{width:100%;height:auto}h2{margin-top:48px}p{max-width:1100px;line-height:1.6}</style>
<h1>extra_4 / shank0 — Round 1 evidence</h1>
<p>Nine targeted clusters. Original automated labels and every event are preserved. No curation or sorting was performed.
Raw traces use unchanged original sample indices; mean-waveform displays subtract each event/channel's pre-event baseline only.
No filtering, CAR, interpolation or padding is applied. Feature/template units are not raw voltage.
ACGs and all-event rates use the full 300 nominal seconds (297.619048 physical seconds). The sorter's two-sample duplicate suppression limits the shortest intervals.</p>
<p><a href="review_findings.md">Review findings and proposed decisions</a> |
<a href="cluster_metrics.csv">Metrics</a> | <a href="quarter_metrics.csv">Quarter metrics</a> |
<a href="raw_selection.csv">Exact raw selections</a> | <a href="pc_comparison_coverage.csv">PC coverage</a> |
<a href="provenance.json">Provenance</a> | <a href="validation.json">Validation</a></p><p>'''+nav+'</p>'+''.join(pages)+
        '<h2>Recording-start context</h2><p>Events at samples 2/3 lack a complete 61-sample waveform support. This is a boundary warning, not independent proof of artifact origin.</p><img src="boundary_context.png">',encoding='utf-8')
    # A human-readable findings file is added after visual inspection, separately
    # from this mechanical evidence generator. No generated proposal is auto-adopted.
    (output/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in output.iterdir() if p.is_file()},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--max-waveforms',type=int,default=256)
    args=parser.parse_args()
    run(args.evidence,args.binary,args.output,args.max_waveforms)
