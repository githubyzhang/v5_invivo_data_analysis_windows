"""Focused MA50 review: frozen calibration, new intervals, balanced review cards.

User labels are exported separately; no automatic default change or exclusions.
"""
import json,hashlib,os,sys
from pathlib import Path
from html import escape
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/invivo-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analysis.compare_detectors import run_segment, FS, CONTEXT
from analysis.compare_ma_windows import matched_members,ma_residuals
from analysis.shared_artifacts import evaluate_segment
from analysis.fixed_reference_thresholds import target, DATA, REFS

ROOT=Path('results/focused_ma50_review')
CAL=Path('results/fixed_reference_thresholds')
NEW_STARTS=[120,210]
OLD=['extra4_60_65','extra4_240_245','extra5_180_185']


def select_events(a,b):
    """One near-threshold and one large-amplitude event per category.

    Selection is deterministic, deliberately stratified, and not a population
    accuracy sample. Match tolerance remains 3 samples, within channel only.
    """
    groups=[('fixed-only',b[~matched_members(b[:,:4],a[:,:4])]),
            ('adaptive-only',a[~matched_members(a[:,:4],b[:,:4])]),
            ('shared',b[matched_members(b[:,:4],a[:,:4])])]
    selected=[]
    for category,arr in groups:
        seen=set()
        for stratum,order in [('near-threshold',np.argsort(arr[:,2]/arr[:,3],kind='stable')),
                              ('large-amplitude',np.argsort(-arr[:,2],kind='stable'))]:
            for i in order:
                key=(int(arr[i,0]),int(arr[i,1]))
                if key in seen:continue
                seen.add(key);selected.append((category,stratum,arr[i]));break
    return selected


def reference_views(rec):
    d=np.load(CAL/'references'/f'extra{rec}_calibration.npz');ok=d['eligible'];accepted=d['accepted']
    failed=np.flatnonzero(~ok);coverage=accepted.sum(axis=(0,2))
    # Two familiar eligible channels, one failed channel with most screened
    # windows, and one with least: selection is explicit, not representative.
    channels=[1436,1378]
    if len(failed):
        channels += [int(failed[np.argmax(coverage[failed])]),int(failed[np.argmin(coverage[failed])])]
    channels=list(dict.fromkeys(channels));items=[]
    with h5py.File(DATA/f'extra_{rec}_signals.h5','r') as f:
        for ch in channels:
            fig,axes=plt.subplots(3,2,figsize=(13,8),squeeze=False)
            for ri,start in enumerate(REFS[rec]):
                lo=start*FS;raw=f['signals'][ch,lo-CONTEXT:lo+5*FS+CONTEXT].astype(float)
                y=ma_residuals(raw)['ma50'];sl=slice(CONTEXT,-CONTEXT);t=np.arange(5*FS)/FS+start
                axes[ri,0].plot(t,raw[sl],lw=.35,color='#777');axes[ri,0].plot(t,(raw-y)[sl],lw=.7,color='#d58028')
                axes[ri,1].plot(t,y[sl],lw=.35)
                thr=d['thresholds'][0,ch]
                if np.isfinite(thr):axes[ri,1].axhline(-thr,color='#d58028',lw=1)
                for w in np.flatnonzero(accepted[ri,ch]):
                    for ax in axes[ri]:ax.axvspan(start+w,start+w+1,color='green',alpha=.09)
                axes[ri,0].set_title(f'{start}–{start+5}s: raw + MA50 baseline')
                axes[ri,1].set_title('MA50 residual; green = screened reference seconds')
                for ax in axes[ri]:ax.set_xlabel('Nominal time (s)');ax.set_ylabel('Stored float units');ax.grid(alpha=.15)
            fig.suptitle(f'extra_{rec}, channel {ch}: '+('reference eligible' if ok[ch] else 'reference unavailable')+f'; qualifying segments {d["reference_segment_count"][ch]}',fontsize=13)
            fig.tight_layout(rect=(0,0,1,.96));file=f'reference_extra{rec}_ch{ch}.png';fig.savefig(ROOT/file,dpi=125);plt.close(fig)
            items.append({'recording':rec,'channel':ch,'eligible':bool(ok[ch]),'qualifying_segments':int(d['reference_segment_count'][ch]),'image':file,'review_status':'awaiting user confirmation'})
    return items


def cards(name,folder):
    a=np.loadtxt(folder/'ma50_adaptive.csv',delimiter=',',skiprows=1,ndmin=2).reshape(-1,5)
    b=np.loadtxt(folder/'ma50_fixed.csv',delimiter=',',skiprows=1,ndmin=2).reshape(-1,5)
    chosen=select_events(a,b);th=np.load(folder/'thresholds.npz');rec=int(name[5]);start=int(name.split('_')[1])*FS
    rows=[];fig,axes=plt.subplots(max(1,len(chosen)),2,figsize=(13,2.8*max(1,len(chosen))),squeeze=False)
    with h5py.File(DATA/f'extra_{rec}_signals.h5','r') as f:
        for row,(category,stratum,e) in enumerate(chosen):
            ch,p=int(e[0]),int(e[1]);raw=f['signals'][ch,p-CONTEXT-1000:p+CONTEXT+1001].astype(float)
            y=ma_residuals(raw)['ma50'];sl=slice(CONTEXT,-CONTEXT);t=np.arange(-1000,1001)/FS*1000
            ident=f'{name}-ch{ch}-s{p}'
            axes[row,0].plot(t,raw[sl],lw=.6,color='#777');axes[row,0].plot(t,(raw-y)[sl],lw=.8,color='#d58028')
            axes[row,0].set_title(f'{category}, {stratum}: ch {ch}, {p/FS:.4f}s')
            axes[row,1].plot(t,y[sl],lw=.8);axes[row,1].set_xlim(-5,5)
            axes[row,1].axhline(-th['fixed'][0,ch],color='#d58028',label='Fixed')
            w=np.clip((p-start+np.arange(-1000,1001))//FS,0,4)
            axes[row,1].plot(t,-th['adaptive'][0,ch,w],ls=':',color='#2382b0',label='Adaptive');axes[row,1].legend(fontsize=8)
            axes[row,1].set_title(f'Event / detection threshold = {e[2]/e[3]:.3f}; shared20 flag {bool(e[4])}')
            for ax in axes[row]:ax.set_xlabel('Time from candidate (ms)');ax.set_ylabel('Stored float units');ax.grid(alpha=.15)
            rows.append({'id':ident,'segment':name,'category':category,'stratum':stratum,'channel':ch,'sample_index':p,
                'shared20_warning':bool(e[4]),'amplitude_threshold_ratio':float(e[2]/e[3]),
                'assistant_label':'uncertain','assistant_note':'Awaiting waveform review; no ground truth.',
                'user_label':'unreviewed','user_note':''})
    fig.tight_layout();fig.savefig(ROOT/f'{name}_events.png',dpi=125);plt.close(fig)
    return rows


def report(summaries,refs,events):
    table=[];detail=[]
    for name,s in summaries.items():
        a,b=[s['metrics']['ma50_'+mode] for mode in ['adaptive','fixed']]
        table.append(f'<tr><td>{name}</td><td>{"New" if name not in OLD else "Previously reviewed"}</td><td>{a["candidates"]:,}</td><td>{b["candidates"]:,}</td><td>{s["usable_channel_seconds"]:.1f}</td><td>{a["shared20_flagged"]:,} / {b["shared20_flagged"]:,}</td></tr>')
        event_rows=''
        for e in [e for e in events if e['segment']==name]:
            event_rows+=f'<tr><td>ch {e["channel"]}, {e["sample_index"]/FS:.4f}s<br>{e["category"]} / {e["stratum"]}</td><td>{escape(e["assistant_label"])}<br>{escape(e["assistant_note"])}</td><td><select data-id="{e["id"]}"><option>unreviewed</option><option>plausible eAP</option><option>likely artifact</option><option>uncertain</option></select><br><textarea data-note="{e["id"]}" placeholder="Your notes"></textarea></td></tr>'
        detail.append(f'<h2>{name}</h2><img src="{name}_events.png"><table><tr><th>Event</th><th>Provisional assistant interpretation</th><th>Your review</th></tr>{event_rows}</table>')
    refhtml=''.join(f'<details><summary>extra_{r["recording"]}, ch {r["channel"]}: {"eligible" if r["eligible"] else "unavailable"}; {r["qualifying_segments"]} qualifying segments</summary><img src="{r["image"]}"></details>' for r in refs)
    js='''<script>const events=EVENT_DATA;document.querySelector('#export').onclick=()=>{const labels=events.map(e=>({...e,user_label:document.querySelector(`[data-id="${e.id}"]`).value,user_note:document.querySelector(`[data-note="${e.id}"]`).value}));const b=new Blob([JSON.stringify({schema:'ma50-review-v1',labels},null,2)],{type:'application/json'});const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download='ma50_user_review.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);};</script>'''.replace('EVENT_DATA',json.dumps(events).replace('</','<\\/'))
    html='''<!doctype html><meta charset="utf-8"><title>Focused MA50 fixed-reference review</title><style>body{font:17px/1.55 system-ui;max-width:1250px;margin:35px auto;padding:20px;color:#243342}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #ddd}img{width:100%}select,textarea,button{font:inherit}textarea{width:95%}.note{background:#fff2d3;padding:18px}summary{cursor:pointer;padding:12px}</style><h1>Focused MA50 fixed-reference review: extra_4 and extra_5</h1><p class="note">extra_6 is excluded from this round. Calibration, eligibility, 5× multiplier, MA50 subtraction, 5 ms spacing, clipping guards, and shared-warning rules remain frozen. No new default or artifact removal is enabled. Labels are provisional waveform interpretations, not validated spike identities.</p><h2>Reference review</h2><p>Each expandable view shows all three original five-second reference intervals for one channel, including two previously reviewed eligible channels and failed-reference examples. Green regions passed the automated screening; they are not certified artifact-free. The plots show full traces without downsampling. Please assess whether these meet your practical definition of a quiet reference before adoption.</p>'''+refhtml+'''<h2>New-interval comparison</h2><p>120–125 and 210–215 s were fixed before reading them, in each recording. They do not overlap earlier reference or tested intervals. Same recordings, not independent biological replication or labeled accuracy validation. Fixed and adaptive counts below use identical eligible samples. The adaptive floor is recalculated on this subset; comparisons to older all-channel totals would be misleading. Shared flags annotate rather than remove events. New helper runs also compute MA100/200/HP300 diagnostics to preserve the existing support and shared-warning definitions; conclusions here concern MA50 only.</p><table><tr><th>Segment</th><th>Status</th><th>Adaptive</th><th>Fixed</th><th>Usable channel-seconds</th><th>Shared-flagged adaptive / fixed</th></tr>'''+''.join(table)+'''</table><h2>Waveform review</h2><p>For each segment, select one event nearest its detecting threshold and one largest-amplitude event from each of fixed-only, adaptive-only, and shared candidates, without duplicates within a category. Matching uses ±3 samples within channel. Missing categories supply fewer examples. This balanced diagnostic sample is deliberately selected, not random; label proportions must not be reported as detector accuracy. “Plausible eAP” means compatible morphology only; “likely artifact” needs a visible disturbance; ambiguous cases stay uncertain.</p><p>Selections and notes are not saved automatically. Export your labels before closing or refreshing this page. Export does not alter detections.</p><button id="export">Export my review labels</button><p><a href="protocol.json">Frozen protocol</a> · <a href="summary.json">Results</a> · <a href="review_manifest.json">Review selections</a></p>'''+''.join(detail)+js
    (ROOT/'review.html').write_text(html)


def main():
    for rec in [4,5]:assert (DATA/f'extra_{rec}_signals.h5').is_file()
    ROOT.mkdir(exist_ok=False)
    for folder in ['detector','flags','paired']:(ROOT/folder).mkdir()
    # Check disjointness including 250 ms filter context, using all prior
    # segment summaries carrying sample_start/stop and source.
    old_intervals=[]
    for p in Path('results').glob('*/*/summary.json'):
        s=json.loads(p.read_text())
        if all(k in s for k in ['source','sample_start','sample_stop']):old_intervals.append(s)
    for rec in [4,5]:
        for start in NEW_STARTS:
            assert all(not (s['source']==str(DATA/f'extra_{rec}_signals.h5') and start*FS-CONTEXT<s['sample_stop']+CONTEXT and (start+5)*FS+CONTEXT>s['sample_start']-CONTEXT) for s in old_intervals)
    protocol={'recordings':[4,5],'excluded_recordings':[6],'new_starts_s':NEW_STARTS,'duration_s':5,
        'reference_calibration':'unchanged from fixed_reference_thresholds','nominal_fs_hz':FS,'physical_fs_hz':10080,
        'calibration_sha256':{str(rec):hashlib.sha256((CAL/'references'/f'extra{rec}_calibration.npz').read_bytes()).hexdigest() for rec in [4,5]},
        'code_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path('analysis/fixed_reference_thresholds.py'),Path('analysis/compare_detectors.py'),Path('analysis/shared_artifacts.py'),Path('analysis/pilot.py')]},
        'selection':'one nearest-threshold plus one largest-amplitude event in each of fixed-only/adaptive-only/shared, per segment; duplicates skipped',
        'default_changed':False,'user_reference_confirmation':'pending'}
    (ROOT/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    refs=[]
    for rec in [4,5]:refs+=reference_views(rec)
    (ROOT/'reference_manifest.json').write_text(json.dumps(refs,indent=2)+'\n')
    summaries={name:json.loads((CAL/name/'summary.json').read_text()) for name in OLD};events=[]
    for name in OLD:events+=cards(name,CAL/name)
    for rec in [4,5]:
        model=np.load(CAL/'references'/f'extra{rec}_calibration.npz')
        for start in NEW_STARTS:
            name=f'extra{rec}_{start}_{start+5}';s=run_segment(DATA/f'extra_{rec}_signals.h5',start,5,ROOT/'detector'/name)
            evaluate_segment(name,s,ROOT/'detector',ROOT/'flags')
            summaries[name]=target(rec,start,model['eligible'],model['thresholds'],ROOT/'paired',prior_paths=(name,ROOT/'detector'/name,ROOT/'flags'/name))
            events+=cards(name,ROOT/'paired'/name)
            (ROOT/'progress.json').write_text(json.dumps({'completed':list(summaries)},indent=2)+'\n')
    (ROOT/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
    (ROOT/'review_manifest.json').write_text(json.dumps(events,indent=2)+'\n')
    report(summaries,refs,events)

if __name__=='__main__':main()
