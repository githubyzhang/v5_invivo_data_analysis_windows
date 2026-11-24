"""Compare W7B conditions by event times and common-channel raw means, not IDs."""
import argparse
import csv
import json
from pathlib import Path
import sys
import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.review_pilot_round1 import sha, write_csv, RAW_SHA
from scripts.annotate_kilosort_from_custom import membership


def matched_pairs(a, b, tolerance=2):
    """Maximum cardinality chronological one-to-one match for a single cluster pair."""
    i = j = 0
    pairs = []
    while i < len(a) and j < len(b):
        if abs(int(a[i])-int(b[j])) <= tolerance:
            pairs.append((i, j)); i += 1; j += 1
        elif a[i] < b[j]:
            i += 1
        else:
            j += 1
    return np.asarray(pairs, dtype=np.int64).reshape(-1, 2)


def table(path, field):
    with path.open() as stream:
        return {int(r['cluster_id']): r[field] for r in csv.DictReader(stream, delimiter='\t')}


def run(control, exclusion, output):
    output = output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'results/extra4_shank0'):
        raise ValueError('Fresh review path required')
    evidence = ROOT/'worker_returns/extra4_shank0/pilot01/received'
    frozen = json.loads((evidence/'return-manifest.json').read_text())['files']
    for name, item in frozen.items():
        assert sha(evidence/name) == item['sha256']
    for path in [control, exclusion]:
        assert json.loads((path/'status.json').read_text())['state'] == 'complete_review_pending'
        for name, digest in json.loads((path/'output-manifest.json').read_text()).items():
            assert sha(path/name) == digest, name
    a, b = [json.loads((p/'run_contract.json').read_text()) for p in [control, exclusion]]
    for key in ['settings','versions','seed_policy','do_CAR','invert_sign','raw_sha256']:
        assert a[key] == b[key], key
    binary = ROOT/'data/extra4_shank0_float32.bin'
    assert sha(binary) == RAW_SHA
    raw = np.memmap(binary, mode='r', dtype='<f4', shape=(3000000,512))
    geometry = np.genfromtxt(evidence/'geometry/channel_map.csv', delimiter=',', names=True, dtype=int)
    positions = np.column_stack([geometry['x_um'],geometry['y_um']])
    sidecar = ROOT/'results/custom_detector/kilosort_pilot01_quality_windows01/external_quality.h5'
    with h5py.File(sidecar,'r') as f:
        intervals = {name:f['intervals/'+name][:] for name in ['broad_warning','tight_warning','broad_available']}
    guards = np.loadtxt(evidence/'outputs/preflight/prior_flat_guards.csv', delimiter=',', dtype=np.int64)
    output.mkdir(parents=True)
    runs = {}
    cluster_rows, selections, run_rows = [], [], []
    relative = np.arange(-100,101)
    highvar = np.array([64,99,100,106,152,155,169,225,267,282,296,297])
    for label, path in [('historical',evidence/'outputs/pilot01/kilosort4'),('control',control/'kilosort4'),('exclude248',exclusion/'kilosort4')]:
        times = np.load(path/'spike_times.npy').ravel()
        clusters = np.load(path/'spike_clusters.npy').ravel()
        channel_map = np.load(path/'channel_map.npy').ravel()
        templates = np.load(path/'templates.npy')
        peaks = channel_map[np.ptp(templates, axis=1).argmax(axis=1)]
        labels = table(path/'cluster_KSLabel.tsv','KSLabel')
        contam = table(path/'cluster_ContamPct.tsv','ContamPct')
        ids = np.unique(clusters)
        means = np.full((len(templates),512,201), np.nan, dtype=np.float32)
        counts = np.zeros((len(templates),30), dtype=int)
        flags = {name:membership(times, spans) for name, spans in intervals.items()}
        flags['highvar'] = np.isin(times//10000, highvar)
        guard248 = guards[guards[:,0]==1921,1:]
        flags['b248_guard_time'] = membership(times, guard248)
        for cid in ids:
            events = np.flatnonzero(clusters == cid)
            t = np.sort(times[events])
            complete = events[(times[events]>=100)&(times[events]<2999900)]
            selected = complete[np.unique(np.linspace(0,len(complete)-1,min(128,len(complete))).astype(int))] if len(complete) else complete
            if len(selected):
                snippets = np.asarray(raw[times[selected,None]+relative[None,:]], dtype=np.float32).transpose(0,2,1)
                snippets -= np.median(snippets[:,:,:70],axis=2)[:,:,None]
                means[cid] = snippets.mean(axis=0, dtype=np.float64)
            for index in selected:
                selections.append(dict(run=label,cluster_id=int(cid),final_event_index=int(index),sample_index=int(times[index])))
            counts[cid] = np.histogram(t,bins=np.arange(0,3000001,100000))[0]
            gid = int(geometry['original_channel_id'][peaks[cid]])
            g = guards[guards[:,0]==gid,1:]
            row = dict(run=label,cluster_id=int(cid),events=len(events),automated_label=labels[int(cid)],
                contamination_percent=float(contam[int(cid)]),template_peak_binary=int(peaks[cid]),template_peak_global=gid,
                raw_mean_events=len(selected),isi_lt10=int(np.sum(np.diff(t)<10)),isi_lt20=int(np.sum(np.diff(t)<20)),
                nominal_rate=len(t)/300,physical_rate=len(t)/(3000000/10080),peak_guard_events=int(membership(t,g).sum()),
                **{name+'_events':int(flag[events].sum()) for name,flag in flags.items()})
            cluster_rows.append(row)
        np.savez_compressed(output/(label+'_raw_means.npz'), means=means,relative_samples=relative,cluster_ids=ids,counts_10seconds=counts)
        runs[label] = dict(times=times,clusters=clusters,ids=ids,peaks=peaks,means=means,counts=counts)
        run_rows.append(dict(run=label,events=len(times),clusters=len(ids),good=sum(v=='good' for v in labels.values()),
            mua=sum(v=='mua' for v in labels.values()),active_channels=len(channel_map),
            **{name+'_events':int(flag.sum()) for name,flag in flags.items()}))
        print(f'Raw means and metrics complete: {label}',flush=True)
    write_csv(output/'cluster_metrics.csv',cluster_rows)
    write_csv(output/'run_metrics.csv',run_rows)
    write_csv(output/'raw_selection.csv',selections)
    comparisons = []
    targets = []
    for left,right in [('historical','control'),('control','exclude248'),('historical','exclude248')]:
        ra,rb = runs[left],runs[right]
        rows = []
        for ca in ra['ids']:
            ta = np.sort(ra['times'][ra['clusters']==ca])
            for cb in rb['ids']:
                tb = np.sort(rb['times'][rb['clusters']==cb])
                pairs = matched_pairs(ta,tb)
                n = len(pairs)
                if not n:
                    continue
                distance = np.minimum(np.linalg.norm(positions-positions[ra['peaks'][ca]],axis=1),np.linalg.norm(positions-positions[rb['peaks'][cb]],axis=1))
                channels = np.argsort(distance,kind='stable')
                channels = channels[channels!=248][:12]
                x,y = [r['means'][c,channels,80:141].ravel().astype(float) for r,c in [(ra,ca),(rb,cb)]]
                corr = float(np.corrcoef(x,y)[0,1]) if np.isfinite(x).all() and np.isfinite(y).all() and np.std(x)>0 and np.std(y)>0 else None
                rows.append(dict(left_run=left,right_run=right,left_cluster=int(ca),right_cluster=int(cb),
                    left_events=len(ta),right_events=len(tb),matched_within2=n,left_fraction=n/len(ta),right_fraction=n/len(tb),
                    dice=2*n/(len(ta)+len(tb)),exact_sample_matches=int(np.sum(ta[pairs[:,0]]==tb[pairs[:,1]])),
                    raw_mean_correlation=corr,peak_distance_um=float(np.linalg.norm(positions[ra['peaks'][ca]]-positions[rb['peaks'][cb]]))))
        write_csv(output/f'{left}_to_{right}_pairs.csv',rows)
        best = []
        for ca in ra['ids']:
            choices = sorted([r for r in rows if r['left_cluster']==ca],key=lambda r:(-r['dice'],-r['matched_within2'],r['right_cluster']))
            best.extend([dict(rank=i+1,**r) for i,r in enumerate(choices[:3])])
        write_csv(output/f'{left}_to_{right}_top3.csv',best)
        comparisons.append(dict(left=left,right=right,identical_times=np.array_equal(ra['times'],rb['times']),
            identical_cluster_ids=np.array_equal(ra['clusters'],rb['clusters']),
            left_clusters_with_best_dice_ge_point9=sum(r['rank']==1 and r['dice']>=.9 for r in best)))
        if left=='historical':
            targets.extend(r for r in best if r['left_cluster'] in [34,35,5,12,36,2] and r['rank']==1)
    write_csv(output/'target_correspondences.csv',targets)
    pages = []
    for cid in [34,35,5,12,36,2]:
        mapped = [('historical',cid)]+[(r['right_run'],r['right_cluster']) for r in targets if r['left_cluster']==cid]
        peak_positions = [positions[runs[name]['peaks'][c]] for name,c in mapped]
        distance = np.min([np.linalg.norm(positions-p,axis=1) for p in peak_positions],axis=0)
        channels = np.argsort(distance,kind='stable')
        channels = channels[channels!=248][:8]
        fig,axes = plt.subplots(3,3,figsize=(13,9),layout='constrained')
        for ax,ch in zip(axes.ravel()[:8],channels):
            for name,c in mapped:
                ax.plot(relative/10,runs[name]['means'][c,ch]*1e6,label=f'{name}: c{c}')
            ax.set(title=f'Common raw b{ch}',xlabel='Nominal ms',ylabel='Centered input x1e6')
            ax.axvline(0,color='gray',lw=.5)
        for name,c in mapped:
            axes.ravel()[8].plot(np.arange(30)*10,runs[name]['counts'][c],label=f'{name}: c{c}')
        axes.ravel()[8].set(title='Counts per 10 nominal seconds',xlabel='Nominal seconds')
        axes.ravel()[8].legend(fontsize=8)
        fig.suptitle(f'Historical cluster {cid}: highest time-overlap candidates, not accepted identities; b248 excluded from raw comparison')
        filename=f'target_{cid}.png'
        fig.savefig(output/filename,dpi=140);plt.close(fig);pages.append(filename)
    for path in [control,exclusion]:
        for name,digest in json.loads((path/'output-manifest.json').read_text()).items():
            assert sha(path/name)==digest
    assert sha(binary)==RAW_SHA
    summary = dict(schema='w7b-comparison-v1',runs=run_rows,comparisons=comparisons,
        source_hash=RAW_SHA,sidecar_sha256=sha(sidecar),script_sha256=sha(Path(__file__)),
        control_contract_sha256=sha(control/'run_contract.json'),exclusion_contract_sha256=sha(exclusion/'run_contract.json'),
        raw_selected_windows=len(selections),sorting_labels_changed=False,
        caveat='Pairwise chronological matching within +/-2 samples; matches can be reused across candidate cluster pairs. Top ranks are candidates, not accepted neuron identities. Raw means use up to 128 evenly spaced complete events, baseline offsets -100..-31, common-channel correlations -20..40. b248 excluded from every cross-run raw correlation.')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>W7B controlled comparison</title><style>body{font:16px system-ui;max-width:1300px;margin:30px auto}img{width:100%}</style><h1>W7B controlled comparison</h1><p>Original baseline preserved. Automated labels and time-overlap correspondences are not confirmed neuron identities.</p><p><a href="run_metrics.csv">Run metrics</a> | <a href="cluster_metrics.csv">Cluster metrics</a> | <a href="target_correspondences.csv">Target correspondence candidates</a> | <a href="summary.json">Provenance and limits</a></p>'+''.join(f'<img src="{p}">' for p in pages),encoding='utf-8')
    (output/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in output.iterdir() if p.is_file()},indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['control','exclusion','output']:
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.control,a.exclusion,a.output)
