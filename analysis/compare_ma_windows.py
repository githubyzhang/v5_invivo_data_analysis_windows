"""Matched MA50/100/200 subtraction experiment, preserving prior results.

Run: .venv/bin/python analysis/compare_ma_windows.py
No new local/shared warnings are exclusions. Counts are candidate counts only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/invivo-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analysis.compare_detectors import run_segment, match_indices, compare_events, CONTEXT, FS
from analysis.pilot import moving_average

SIZES=[50,100,200]
FILTERS=[f'ma{k}' for k in SIZES]
SEGMENTS=[('controlled_comparison','extra4_30_35'),
          ('controlled_comparison','extra4_60_65'),
          ('controlled_comparison','extra5_180_185'),
          ('controlled_comparison','extra6_60_65'),
          ('frozen_guard_validation/detector','extra6_240_245')]


def ma_residuals(raw):
    return {f'ma{k}':raw-moving_average(raw,k) for k in SIZES}


def matched_members(a,b):
    mask=np.zeros(len(a),bool)
    for ch in np.unique(a[:,0]):
        ai=np.flatnonzero(a[:,0]==ch);bi=np.flatnonzero(b[:,0]==ch)
        ia,_=match_indices(a[ai,1],b[bi,1]);mask[ai[ia]]=True
    return mask


def review(ds,events,out,start,n):
    a,b=events['ma50_mad'],events['ma200_mad']
    groups=[('MA50-only vs MA200',a[~matched_members(a,b)]),
            ('MA200-only vs MA50',b[~matched_members(b,a)]),
            ('Matched MA200 / MA50',b[matched_members(b,a)])]
    chosen=[]
    for label,arr in groups:
        used=set()
        for i in np.argsort(-arr[:,2],kind='stable'):
            ch=int(arr[i,0])
            if ch in used:continue
            used.add(ch);chosen.append((label,arr[i]))
            if len(used)==2:break
    for ch in [1436,1378]:
        arr=b[b[:,0]==ch]
        if len(arr):chosen.append(('Previously reviewed channel',arr[np.argmax(arr[:,2])]))
    fig,axes=plt.subplots(max(1,len(chosen)),2,figsize=(13,2.6*max(1,len(chosen))),squeeze=False)
    manifest=[];diag=np.load(out/'diagnostics.npz')
    for row,(label,e) in enumerate(chosen):
        ch,p=int(e[0]),int(e[1]);raw=ds[ch,p-CONTEXT-500:p+CONTEXT+501].astype(float)
        ys=ma_residuals(raw);core=slice(CONTEXT,CONTEXT+1001);tt=np.arange(-500,501)/FS*1000
        axes[row,0].plot(tt,raw[core],color='#777',lw=.7,label='Stored signal')
        samples={}
        for f,col in zip(FILTERS,['#d66b24','#32936f','#2365a0']):
            axes[row,0].plot(tt,raw[core]-ys[f][core],color=col,lw=.9,label=f+' baseline')
            axes[row,1].plot(tt,ys[f][core],color=col,lw=.9,label=f+' residual')
            w=(p-start)//FS;thr=5*max(diag['sigma_'+f+'_mad'][ch,w],diag['floor_'+f+'_mad'][w])
            axes[row,1].axhline(-thr,color=col,ls=':',lw=.7)
            samples[f]={'negative_amplitude_at_selected_sample':float(-ys[f][CONTEXT+500]),'mad_threshold':float(thr)}
        axes[row,0].set_title(f'{label}: ch {ch}, {p/FS:.4f} s')
        axes[row,1].set_xlim(-5,5);axes[row,1].set_title('Residuals ±5 ms; dotted lines = negative thresholds')
        for ax in axes[row]:
            ax.set_xlabel('Time from selected candidate (ms)');ax.set_ylabel('Stored float units');ax.legend(fontsize=7);ax.grid(alpha=.2)
        manifest.append({'category':label,'channel_id':ch,'sample_index':p,'measurements':samples})
    fig.tight_layout();fig.savefig(out/'waveforms.png',dpi=125);plt.close(fig)
    (out/'waveform_selection.json').write_text(json.dumps(manifest,indent=2)+'\n')


def finish(root,summaries):
    rows=[];details=[];validation={}
    for parent,name in SEGMENTS:
        s=summaries[name];old=Path('results')/parent/name
        d=np.load(root/name/'diagnostics.npz');prev=np.load(old/'diagnostics.npz')
        same_support=np.array_equal(d['common_support'],prev['common_support'])
        checks={}
        for m in ['ma100_mad','ma200_mad','ma100_rms','ma200_rms']:
            a=np.loadtxt(root/name/f'{m}.csv',delimiter=',',skiprows=1,ndmin=2).reshape(-1,4)
            b=np.loadtxt(old/f'{m}.csv',delimiter=',',skiprows=1,ndmin=2).reshape(-1,4)
            checks[m]=bool(np.array_equal(a,b))
            if same_support:np.testing.assert_array_equal(a,b)
        validation[name]={'same_support_as_prior':same_support,'identical_prior_candidates':checks}
        s['comparisons']['ma50_mad__ma100_mad']=compare_events(
            np.loadtxt(root/name/'ma50_mad.csv',delimiter=',',skiprows=1,ndmin=2).reshape(-1,4),
            np.loadtxt(root/name/'ma100_mad.csv',delimiter=',',skiprows=1,ndmin=2).reshape(-1,4))
        counts=[s['methods'][f+'_mad']['candidates'] for f in FILTERS]
        rms=[s['methods'][f+'_rms']['candidates'] for f in FILTERS]
        pair=s['comparisons']['ma200_mad__ma50_mad']
        rows.append(f'<tr><td>{name}</td>'+''.join(f'<td>{v:,}</td>' for v in counts)+
                    f'<td>{pair["matched_within_0_3ms"]:,}</td><td>{pair["a_only"]:,}</td><td>{pair["b_only"]:,}</td></tr>')
        # Count the known common transient bins without applying shared flags.
        known={'extra4_60_65':64.03,'extra5_180_185':180.07,'extra6_60_65':61.2,'extra6_240_245':242.88}
        counts_text=''
        if name in known:
            lo=round(known[name]*FS);hi=lo+(3000 if name=='extra6_60_65' else 100)
            cc={}
            for f in FILTERS:
                e=np.loadtxt(root/name/(f+'_mad.csv'),delimiter=',',skiprows=1,ndmin=2).reshape(-1,4)
                cc[f]=int(((e[:,1]>=lo)&(e[:,1]<hi)).sum())
            s['reviewed_interval']={'start_s':lo/FS,'stop_s':hi/FS,'mad_counts':cc}
            counts_text=f'<p>Previously reviewed time {lo/FS:.3f}–{hi/FS:.3f} s: MA50 / MA100 / MA200 candidates = '+ ' / '.join(str(cc[f]) for f in FILTERS)+'. This interval is a review target, not a truth label.</p>'
        details.append(f'<h2>{name}</h2><p>RMS sensitivity comparison, MA50 / MA100 / MA200: {rms[0]:,} / {rms[1]:,} / {rms[2]:,}. Usable channel-seconds: {s["usable_channel_seconds"]:.3f}.</p>'+counts_text+f'<img src="{name}/waveforms.png"><p>Examples deliberately selected for largest-amplitude disagreements, agreements, and prior review channels. Not an accuracy sample. <a href="{name}/waveform_selection.json">Selection and amplitudes</a> · <a href="{name}/summary.json">Segment metrics</a></p>')
    (root/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    (root/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    for i,f in enumerate(FILTERS):
        x=np.arange(len(summaries))+(i-1)*.24
        axes[0].bar(x,[s['methods'][f+'_mad']['candidates'] for s in summaries.values()],.24,label=f)
        noise=[]
        for name in summaries:
            d=np.load(root/name/'diagnostics.npz');noise.append(float(np.nanmedian(d['floor_'+f+'_mad'])))
        axes[1].plot(range(len(noise)),noise,'o-',label=f)
    for ax in axes:
        ax.set_xticks(range(len(summaries)),list(summaries),rotation=25,ha='right');ax.legend();ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('MAD candidate count');axes[1].set_ylabel('MAD floor (stored units)')
    axes[0].set_title('Same usable samples and threshold multiplier');axes[1].set_title('Median noise floor across seconds; varies with MA width')
    fig.tight_layout();fig.savefig(root/'overview.png',dpi=140);plt.close(fig)
    html='''<!doctype html><meta charset="utf-8"><title>Moving-average window comparison</title><style>body{font:17px/1.55 system-ui;max-width:1250px;margin:35px auto;padding:20px;color:#243342}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #ddd}img{width:100%}.note{background:#fff2d3;padding:18px}</style><h1>MA50 / MA100 / MA200 baseline subtraction</h1><p>50, 100, and 200 samples = 5, 10, and 20 ms at nominal 10 kHz. Physical sampling rate remains 10,080 Hz.</p><p class="note">These are candidate comparisons, not spike-detection accuracy measurements. No default has changed. Original source files and prior results are preserved. Fast-noise removal remains disabled.</p><h2>Controlled settings</h2><p>Each channel uses a centered moving average with the same even-window alignment and real neighboring context. Negative peaks, 5× noise threshold, 5 ms global peak spacing, identical flat guards (≥1 ms repeated values plus ±50 ms), and identical noise-estimation support across all six filter/estimator combinations. MAD is primary; RMS is a sensitivity comparison. Each method estimates its own noise on the same eligible samples and uses its own across-channel median floor. Thus the multiplier is matched, but the absolute voltage threshold can change. Shared and exploratory per-channel warnings are not exclusion steps.</p><p>These five segments were previously reviewed and deliberately cover quieter examples, baseline transitions, and disturbed extra_6 activity. This is not held-out validation. extra_5/6 were acquired after stimulation experiments, but all three recordings here are purely extracellular. No causal stimulation or electrochemical interpretation is established.</p><h2>MAD candidate comparison</h2><p>One-to-one same-channel matching within ±3 samples (0.3 ms). “Only” refers to the MA50 versus MA200 pair; it does not establish truth.</p><table><tr><th>Interval</th><th>MA50</th><th>MA100</th><th>MA200</th><th>Matched 50/200</th><th>200 only</th><th>50 only</th></tr>'''+''.join(rows)+'''</table><img src="overview.png"><p>A shorter average follows faster signal components. Its subtraction may reduce some baseline-related residuals while changing eAP shape, amplitude, and noise scale. Fewer candidates alone cannot justify choosing a smaller window. Inspect matched narrow waveforms as well as disagreements. <a href="protocol.json">Protocol</a> · <a href="summary.json">All metrics</a> · <a href="validation.json">Prior-result reproduction checks</a></p>'''+''.join(details)
    outcome = '<h2>What this round shows</h2><ul>'
    for name in ['extra4_60_65','extra5_180_185']:
        r=summaries[name]['reviewed_interval']; c=r['mad_counts']
        outcome += f'<li>At the reviewed {name} baseline transition ({r["start_s"]:.2f}–{r["stop_s"]:.2f} s), MA200 / MA100 / MA50 produce {c["ma200"]:,} / {c["ma100"]:,} / {c["ma50"]:,} candidates.</li>'
    outcome += '<li>The selected extra4_30_35 plots show reduced broad residuals with MA50 and narrow spike-like events still visible. Some additional events cross the lower MA50 threshold. These examples do not establish sensitivity or waveform fidelity across all spikes.</li><li>Both extra_6 intervals produce more candidates with shorter windows. This does not solve their fast disturbance, and fewer MA200 detections do not prove cleaner detection.</li><li>MA100 and MA200 candidates exactly reproduce the prior runs when common support is unchanged; see the validation file. No new default is adopted.</li></ul>'
    html=html.replace('<h2>Controlled settings</h2>',outcome+'<h2>Controlled settings</h2>')
    (root/'review.html').write_text(html)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=Path('results/ma_window_comparison'));args=ap.parse_args()
    sources={name:json.loads((Path('results')/parent/name/'summary.json').read_text()) for parent,name in SEGMENTS}
    for s in sources.values():
        if not Path(s['source']).is_file():raise FileNotFoundError(s['source'])
    args.out.mkdir(exist_ok=False)
    protocol={'sizes_samples':SIZES,'nominal_fs_hz':FS,'physical_fs_hz':10080,'segments':SEGMENTS,
              'threshold_multiplier':5,'peak_spacing_samples':50,'primary_estimator':'mad','secondary_estimator':'rms',
              'warnings_used_as_exclusions':False,'new_default_adopted':False,
              'python':sys.executable,'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                  [Path(__file__),Path('analysis/compare_detectors.py'),Path('analysis/pilot.py')]}}
    (args.out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    summaries={}
    for name,s in sources.items():
        summaries[name]=run_segment(Path(s['source']),s['sample_start']/FS,(s['sample_stop']-s['sample_start'])/FS,
                args.out/name,filter_names=FILTERS,transform=ma_residuals,waveform_reviewer=review)
    finish(args.out,summaries)

if __name__=='__main__':main()
