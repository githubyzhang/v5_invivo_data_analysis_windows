"""Exploratory per-channel warnings; preserves every original candidate.

No correction/exclusion is enabled in the detector. Thresholds are diagnostic
choices, not calibrated probabilities or a validated artifact classifier.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/invivo-matplotlib')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import sosfiltfilt
from analysis.compare_detectors import FS, CONTEXT, SOS
from analysis.pilot import moving_average, flat_mask, dilate, write_csv
from analysis.shared_artifacts import intervals

BIN = 100  # nominal 10 ms
SEGMENTS = [('controlled_comparison', 'extra4_30_35'),
            ('frozen_guard_validation/detector', 'extra4_240_245'),
            ('frozen_guard_validation/detector', 'extra5_240_245'),
            ('frozen_guard_validation/detector', 'extra6_90_95'),
            ('frozen_guard_validation/detector', 'extra6_240_245')]


def sustained(mask, minimum=2):
    """Keep complete runs of at least minimum consecutive bins."""
    out = np.zeros_like(mask, dtype=bool)
    for a, b in intervals(mask):
        if b-a >= minimum:
            out[a:b] = True
    return out


def channel_flags(fast_scale, baseline, valid, fast_reference, step_reference):
    """Return independent channel masks; bins wholly outside support cannot vote.

    Step warnings cover both bins of a qualifying difference. Each warning gets
    10 ms padding, clipped to this segment. A low scale is a warning, not a rail.
    """
    fast = sustained(valid & (fast_scale > 6*fast_reference))
    collapse = sustained(valid & (fast_scale < .1*fast_reference))
    step = np.zeros(len(valid), bool)
    hit = valid[1:] & valid[:-1] & (np.abs(np.diff(baseline)) > 6*step_reference)
    step[:-1] |= hit
    step[1:] |= hit
    return {k: dilate(np.repeat(v, BIN), BIN) for k, v in
            [('fast', fast), ('step', step), ('low_variability', collapse)]}


def review_traces(out, source, start, selected):
    fig, axes = plt.subplots(len(selected), 2, figsize=(13, 2.6*len(selected)), squeeze=False)
    with h5py.File(source, 'r') as f:
        for row, (ch, t, reason) in enumerate(selected):
            idx = round(t*FS)
            raw = f['signals'][ch, idx-CONTEXT-1000:idx+CONTEXT+1000].astype(float)
            hp = sosfiltfilt(SOS, raw)[CONTEXT:-CONTEXT]
            base = moving_average(raw)[CONTEXT:-CONTEXT]
            x = raw[CONTEXT:-CONTEXT]; tt = np.arange(-1000,1000)/FS*1000
            axes[row,0].plot(tt, x, lw=.6, label='Stored signal')
            axes[row,0].plot(tt, base, lw=1, label='MA200 baseline')
            axes[row,1].plot(tt, hp, lw=.7, label='HP300 residual')
            axes[row,0].set_title(f'Ch {ch}, {t:.4f} s — {reason}')
            for ax in axes[row]:
                ax.set_xlabel('Time from selection (ms)'); ax.set_ylabel('Stored float units')
                ax.legend(fontsize=8); ax.grid(alpha=.2)
    fig.tight_layout(); fig.savefig(out/'traces.png', dpi=130); plt.close(fig)


def run(root, prior_root, name):
    prior = prior_root/name; out = root/name; out.mkdir()
    s = json.loads((prior/'summary.json').read_text())
    old = np.load(prior/'diagnostics.npz')
    start, stop = s['sample_start'], s['sample_stop']; n = stop-start
    assert n % BIN == 0
    nb = n//BIN
    scales = np.full((2048, nb), np.nan); base = scales.copy()
    valid = np.zeros((2048, nb), bool); allowed = np.zeros((2048,n), bool)
    with h5py.File(s['source'], 'r') as f:
        for batch in range(0,2048,64):
            raw_batch = f['signals'][batch:batch+64,start-CONTEXT:stop+CONTEXT].astype(float)
            if not np.isfinite(raw_batch).all(): raise ValueError('Nonfinite source')
            for j, raw in enumerate(raw_batch):
                ch = batch+j; core = slice(CONTEXT, CONTEXT+n)
                allowed[ch] = ~dilate(flat_mask(raw),500)[core] & old['common_support'][ch,np.arange(n)//FS]
                valid[ch] = allowed[ch].reshape(nb,BIN).all(axis=1)
                h = sosfiltfilt(SOS, raw)[core].reshape(nb,BIN)
                scales[ch] = np.median(np.abs(h-np.median(h,axis=1)[:,None]),axis=1)/.67448975
                base[ch] = moving_average(raw)[core].reshape(nb,BIN).mean(axis=1)
            if batch % 512 == 0: print(name, batch, flush=True)
    # Lower-quartile within-channel reference detects intermittent changes, not
    # continuous noise. Floor prevents small scales from magnifying ratios.
    refs = np.full(2048,np.nan); steprefs = refs.copy()
    for ch in range(2048):
        v = scales[ch,valid[ch]]
        d = np.diff(base[ch])[valid[ch,1:] & valid[ch,:-1]]
        if len(v)>=100 and len(d)>=100:
            refs[ch] = np.percentile(v,25)
            steprefs[ch] = np.median(np.abs(d-np.median(d)))/.67448975
    for arr in (refs,steprefs):
        positive = np.isfinite(arr)&(arr>0)
        if not positive.any(): raise ValueError('No positive reference scale')
        arr[np.isfinite(arr)] = np.maximum(arr[np.isfinite(arr)],np.median(arr[positive]))
    shared_path = (Path('results/shared_artifact_review_extended')/name/'flags_and_evidence.npz'
                   if prior_root.name=='controlled_comparison' else
                   Path('results/frozen_guard_validation/flags')/name/'flags_and_evidence.npz')
    shared = np.load(shared_path)['mask_b3_h6_f50_g20']
    events = {m:np.loadtxt(prior/f'{m}.csv',delimiter=',',skiprows=1,ndmin=2).reshape(-1,4)
              for m in ['hp300_mad','ma200_mad']}
    annotations = {m:np.zeros((len(e),3),bool) for m,e in events.items()}
    totals = {k:0 for k in ['fast','step','low_variability','union','additional_to_shared20']}
    rows=[]; mask_rows=[]
    for ch in range(2048):
        flags = channel_flags(scales[ch],base[ch],valid[ch],refs[ch],steprefs[ch])
        union = np.logical_or.reduce(list(flags.values()))
        allflags = dict(flags,union=union,additional_to_shared20=union&~shared)
        for k, mask in allflags.items(): totals[k] += int((mask&allowed[ch]).sum())
        for k,mask in flags.items():
            mask_rows.extend((ch,k,(a+start)/FS,(b+start)/FS) for a,b in intervals(mask))
        rows.append((ch,refs[ch],steprefs[ch],int(valid[ch].sum()),
                     *[int((v&allowed[ch]).sum())/FS for v in allflags.values()]))
        for m,e in events.items():
            ix=np.flatnonzero(e[:,0]==ch); p=e[ix,1].astype(int)-start
            assert allowed[ch,p].all()
            annotations[m][ix]=np.array([v[p] for v in flags.values()]).T
    metrics={'source':s['source'],'sample_start':start,'sample_stop':stop,
             'source_file_size_bytes':s['file_size_bytes'],'source_mtime_ns':s['file_mtime_ns'],
             'usable_channel_seconds':float(allowed.sum()/FS),
             'channel_seconds_under_warning':{k:v/FS for k,v in totals.items()},
             'channels_without_reference':int((~np.isfinite(refs)).sum()),'methods':{}}
    np.testing.assert_allclose(metrics['usable_channel_seconds'],s['usable_channel_seconds'])
    for m,e in events.items():
        a=annotations[m]; p=e[:,1].astype(int)-start; u=a.any(axis=1)
        metrics['methods'][m]={'original':len(e),'fast':int(a[:,0].sum()),'step':int(a[:,1].sum()),
            'low_variability':int(a[:,2].sum()),'union':int(u.sum()),
            'additional_to_shared20':int((u&~shared[p]).sum()),
            'review_channels':{str(ch):{'original':int((e[:,0]==ch).sum()),
                'flagged':int((u&(e[:,0]==ch)).sum())} for ch in [1436,1378]}}
        write_csv(out/f'annotated_{m}.csv', ['channel_id','sample_index','negative_amplitude','threshold',
                 'fast_warning','step_warning','low_variability_warning','shared20_warning'],
                  ((int(r[0]),int(r[1]),r[2],r[3],*map(int,a[i]),int(shared[p[i]])) for i,r in enumerate(e)))
        check=np.loadtxt(out/f'annotated_{m}.csv',delimiter=',',skiprows=1,ndmin=2)
        np.testing.assert_array_equal(check[:,:4],e)
    write_csv(out/'channel_metrics.csv',['channel_id','fast_reference','step_reference','eligible_10ms_bins',
              'fast_seconds','step_seconds','low_variability_seconds','union_seconds','additional_to_shared20_seconds'],rows)
    write_csv(out/'warning_intervals.csv',['channel_id','warning','start_nominal_s','stop_nominal_s'],mask_rows)
    np.savez_compressed(out/'features.npz',fast_mad=scales,baseline=base,eligible_bins=valid,
                        fast_reference=refs,step_reference=steprefs)
    # Selection deliberately targets known failures and a stable review channel.
    selected=[(1436,(start+stop)/2/FS,'previous review channel')]
    if name=='extra6_240_245': selected += [(1919,240.6709,'previously unflagged step'),(1591,240.4835,'previously unflagged step'),(1984,242.9163,'previous fast disturbance')]
    elif name=='extra6_90_95': selected += [(1911,90.6992,'previously unflagged step'),(761,94.5509,'previous narrow candidate')]
    else: selected += [(1919,(start+stop)/2/FS,'same channel ID; no identity assumption')]
    e=events['hp300_mad']; a=annotations['hp300_mad']; eligible=np.flatnonzero(a[:,0]&~shared[e[:,1].astype(int)-start])
    if len(eligible):
        i=eligible[np.argmax(e[eligible,2])]; selected.append((int(e[i,0]),e[i,1]/FS,'largest fast-flag candidate outside shared20'))
    review_traces(out,s['source'],start,selected)
    (out/'selection.json').write_text(json.dumps(selected,indent=2)+'\n')
    (out/'summary.json').write_text(json.dumps(metrics,indent=2)+'\n')
    return metrics


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=Path('results/local_artifact_review'))
    root=ap.parse_args().out
    root.mkdir(exist_ok=False)
    protocol={'status':'Exploratory, previously reviewed intervals; no held-out validation',
        'segments':SEGMENTS,'nominal_fs_hz':FS,'physical_fs_hz':10080,'enabled_in_detector':False,
        'user_hypothesis':'Post-injection electrode surface/electrochemical conditions may cause lab-termed bubbling noise; cause unverified.',
        'rules':'10ms HP300 MAD >6x floored own-segment lower-quartile scale for >=2 bins; low variability <0.1x same reference for >=2 bins; adjacent MA200 10ms mean difference >6x floored temporal MAD. Each gets +/-10ms guard. Require 100 eligible bins/differences for references.',
        'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (root/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    summaries={name:run(root,Path('results')/parent,name) for parent,name in SEGMENTS}
    (root/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
    table=[];details=[]
    for name,s in summaries.items():
        m=s['methods']['hp300_mad'];t=s['channel_seconds_under_warning']
        table.append(f'<tr><td>{name}</td><td>{m["original"]:,}</td><td>{m["fast"]:,}</td><td>{m["step"]:,}</td><td>{m["low_variability"]:,}</td><td>{m["additional_to_shared20"]:,}</td><td>{100*t["additional_to_shared20"]/s["usable_channel_seconds"]:.2f}%</td></tr>')
        details.append(f'<h2>{name}</h2><p>Deliberately selected examples, not a random accuracy sample. Channel IDs are zero-based.</p><img src="{name}/traces.png"><p><a href="{name}/annotated_hp300_mad.csv">All HP300/MAD candidates with warnings</a> · <a href="{name}/channel_metrics.csv">Per-channel metrics</a> · <a href="{name}/warning_intervals.csv">Warning intervals</a></p>')
    html='''<!doctype html><meta charset="utf-8"><title>Per-channel disturbance review</title><style>body{font:17px/1.55 system-ui;max-width:1250px;margin:36px auto;padding:20px;color:#243342}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #ddd}img{width:100%}.note{background:#fff2d3;padding:18px}</style><h1>Per-channel disturbance review</h1><p class="note">Optional exploratory warnings only. No original candidates, signal samples, shared rules, or detection thresholds were changed. A warning is not proof of a false spike. No artifact subtraction or reconstruction has been attempted.</p><p>extra_5 and extra_6 are extracellular recordings acquired after stimulation experiments. The user reports possible “bubbling noise” related to electrode surface conditions; this is a hypothesis, not an identified mechanism. Fast fluctuations are evaluated separately from slow baseline changes.</p><h2>Independent channel warnings</h2><ul><li><b>Fast:</b> HP300 residual MAD within each 10 ms bin exceeds 6× that channel's reference for at least two adjacent bins. Reference is the lower quartile of eligible bin scales in this five-second segment, with an across-channel median floor.</li><li><b>Step:</b> difference between adjacent 10 ms means of the MA200 baseline exceeds 6× its robust temporal scale (also floored). Both contributing bins are flagged.</li><li><b>Low variability:</b> HP300 bin MAD below 0.1× the fast reference for at least two adjacent bins. This is not calibrated saturation detection.</li></ul><p>All three use independent channel masks and ±10 ms padding. References require at least 100 eligible bins and 100 adjacent eligible differences. Old clipping and noise-support exclusions determine eligibility; invalid bins cannot seed warnings. Padding can overlap excluded data; exposure counts use eligible samples only.</p><h2>Overlap and cost</h2><p>Columns may overlap. Additional means the union of local warnings outside the existing shared 20 ms guard, among previously usable samples. Numbers are flagged candidates, not confirmed false positives.</p><table><tr><th>Interval</th><th>HP candidates</th><th>Fast</th><th>Step</th><th>Low variability</th><th>Additional candidates</th><th>Additional usable-time loss</th></tr>'''+''.join(table)+'''</table><h2>Limits</h2><p>These intervals were already reviewed. The numerical choices are exploratory and were not retuned after this run. A quiet reference is not guaranteed: persistent fast noise can raise its own reference and escape detection. True neural bursts may also increase fast variability. A baseline step can mark a plateau edge without identifying its full interior. This does not reliably separate overlapping noise from eAPs, establish an electrochemical cause, or validate automatic exclusion.</p><p>All times use nominal 10 kHz. Recordings remain separate; channel identity does not establish stable neuron identity across recordings. See <a href="protocol.json">protocol</a> and <a href="summary.json">full metrics including MA200/MAD and review channels</a>.</p>'''+''.join(details)
    (root/'review.html').write_text(html)

if __name__=='__main__': main()
