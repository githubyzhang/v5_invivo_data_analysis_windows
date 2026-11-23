"""Build a portable retrospective report from frozen evidence; no redetection."""
from pathlib import Path
import base64
import hashlib
import html
import json
import os
import subprocess
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/invivo-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/detection_features_review'

def main():
    OUT.mkdir(exist_ok=True)
    sources={}
    def read(path):
        p=ROOT/path
        sources[path]=hashlib.sha256(p.read_bytes()).hexdigest()
        return json.loads(p.read_text())
    pilot=read('results/extra4_pilot_60_65/summary.json')
    ma=read('results/ma_window_comparison/extra4_60_65/summary.json')
    full=[read(f'results/spike_detection_ma50_adaptive/extra{n}/summary.json') for n in (4,5)]
    read('results/shared_artifact_review_extended/config.json')
    for path in ['docs/METHODS.md','docs/DECISIONS.md','docs/PROGRESS.md','docs/OUTPUTS.md','analysis/detect_recordings.py','analysis/shared_artifacts.py','docs/reviews/ma50_user_review.json']:
        sources[path]=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    fig,ax=plt.subplots(1,2,figsize=(11,4.2),layout='constrained')
    colors=['#007f82','#dc9433','#526eac']
    vals=[ma['methods'][f'ma{n}_mad']['largest_10ms_bin_candidates'] for n in (50,100,200)]
    ax[0].bar(['MA50','MA100','MA200'],vals,color=colors)
    ax[0].set(title='Baseline-transition example',ylabel='Candidates in 64.03–64.04 s',ylim=(0,850))
    for i,v in enumerate(vals): ax[0].text(i,v+12,str(v),ha='center')
    pv=[pilot['methods'][k]['events_in_suspect_flat_guard'] for k in ('context_rms','context_rms_floor')]
    ax[1].bar(['No median floor','With median floor'],pv,color=colors[:2])
    ax[1].set(title='Median-floor safeguard: matched RMS comparison',ylabel='Candidates inside suspected-flat guards',ylim=(0,240))
    for i,v in enumerate(pv): ax[1].text(i,v+4,str(v),ha='center')
    fig.suptitle('extra_4, 60–65 s • historical comparisons, not accuracy estimates',fontsize=13)
    for a in ax: a.spines[['top','right']].set_visible(False)
    fig.savefig(OUT/'evidence_summary.png',dpi=160)
    fig.savefig(OUT/'evidence_summary.pdf')
    plt.close(fig)
    def image(path,caption):
        p=Path(path)
        if not p.is_absolute(): p=ROOT/p
        if p.is_relative_to(ROOT) and not p.is_relative_to(OUT): sources[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        data=base64.b64encode(p.read_bytes()).decode()
        return f'<figure><img src="data:image/png;base64,{data}" alt="{html.escape(caption)}"><figcaption>{caption}</figcaption></figure>'
    sections=[]
    def section(id,title,body): sections.append((id,title,body))
    section('overview','1 · What changed, and what we retained', '''<p>We retained the legacy idea of subtracting a moving-average baseline and its across-channel median-noise safeguard. The new workflow adds explicit observation masks, robust noise estimation, reliable chunk boundaries, optional fixed-reference calibration, shared-disturbance annotations and auditable sparse event storage.</p>
<table><tr><th>Feature</th><th>Current role</th><th>Status</th></tr>
<tr><td>MA50 baseline subtraction</td><td>Suppress slower fluctuations before detection</td><td>Default; MA100/200 optional</td></tr>
<tr><td>Masked MAD + median floor</td><td>Set thresholds without using suspected-clipped samples</td><td>Adaptive default; fixed reference optional</td></tr>
<tr><td>Per-channel flat guards</td><td>Exclude unreliable observation intervals</td><td>Enabled; clipping proxy</td></tr>
<tr><td>Shared-disturbance flags</td><td>Label simultaneous widespread disturbances</td><td>Review only; partial coverage</td></tr>
<tr><td>Fast-noise / stimulation artifact removal</td><td>Would require separate validation</td><td>Not enabled</td></tr></table>
<div class="flow">Stored signal → MA residual → valid-sample noise estimate → threshold crossings → per-channel peak spacing → saved events + quality metadata</div>
<p>Flat guards affect both noise estimation and detection. Shared warnings are added to saved candidates without deleting them. The source recording is never rewritten.</p>''')
    section('baseline','2 · Baseline subtraction: faster computation and a shorter window', '''<p><strong>Residual = stored signal − centered moving average.</strong> At the nominal 10 kHz rate, MA50, MA100 and MA200 span 5, 10 and 20 ms. MA50 follows baseline changes more closely; MA200 smooths over a longer interval and can leave larger residuals around rapid changes.</p>
<p>The compiled uniform filter accelerates the calculation <em>at the same window size</em>. Switching from 200 to 50 samples is a separate scientific choice that changes the filtered waveform and its noise scale. For MA50, the window contains 25 preceding samples, the current sample and 24 following samples.</p>
<p>In the controlled extra_4 60–65 s comparison, the reviewed 64.03–64.04 s transition contains <strong>28 / 171 / 738</strong> MA50 / MA100 / MA200 MAD candidates. Observation support and estimator family were matched, but each filter has its own noise-derived threshold. This is evidence of different responses to that transition, not proof that all removed events were false.</p>
<p>Selected waveforms show narrower residuals and useful candidate preservation with MA50. A moving average also responds to the spike or fast disturbance itself: subtraction can alter amplitudes and produce surrounding lobes. MA50 is not a validated solution for fast “bubbling” noise, and no filter comparison establishes complete spike recovery.</p>'''+image('results/ma_window_comparison/extra4_60_65/waveforms.png','Historical extra_4 examples: stored traces and MA baselines at left, residuals and filter-specific thresholds at right. These deliberately selected examples illustrate differences; they are not a random accuracy sample.'))
    section('noise','3 · Noise thresholds: preserving the legacy safeguard', '''<pre>sigma = median(|residual − median(residual)|) / 0.67448975
threshold = 5 × max(channel sigma, median sigma across valid channels)</pre>
<p>The default uses centered MAD on eligible MA50 residual samples in each nominal second. Unlike the legacy RMS detector, this estimate uses deviations from the median. It can still be influenced by persistent or prevalent disturbance.</p>
<p>The across-channel median floor retains the intent of the legacy <code>apply_median_noise</code> feature: a channel with unusually small estimated noise should not receive an arbitrarily low threshold. In a matched MA200/RMS pilot comparison, adding only the floor reduced candidates inside suspected-flat guards from <strong>204 to 8</strong>. The separate masked method yields zero there because those samples are excluded by construction.</p>
<p>A median floor is a threshold safeguard, not proof of usable signal. It cannot reconstruct spikes lost to clipping, and it can reduce sensitivity on genuinely quiet channels. Widespread disturbance may also elevate the pooled floor.</p>'''+image(OUT/'evidence_summary.png','Two different historical comparisons on the same five-second pilot. Left: filter-window comparison with MAD thresholds. Right: floor-only comparison with RMS. The panels must not be interpreted as one controlled comparison of the entire legacy and final pipelines.'))
    section('clipping','4 · Per-channel clipping proxy and observation mask', '''<p>For each channel independently, detect exact repeated stored values lasting at least <strong>10 samples (1 nominal ms)</strong>. Expand the interval by <strong>500 samples (50 ms) on each side</strong>. Exclude this guarded interval from both noise estimation and candidate detection.</p>
<div class="flow">Channel A: normal → [50 ms guard | flat interval | 50 ms guard] → normal<br>Channel B: remains available unless its own quality checks fail</div>
<p>The extra_4 pilot contains repeated-value runs on 185 channels. Exact flatness occupies 0.770% of channel-samples; the expanded guards occupy 1.094%. These are pilot-specific values, not full-recording clipping prevalence.</p>
<p>Exact flatness can arise from clipping, float16 quantization, disconnected channels or missing data. We therefore call this a <strong>suspected-flat mask</strong>, not calibrated rail detection. It prevents interpretation of missing signal as low neural activity. The 50 ms guard is a conservative adopted parameter, not a proven recovery time.</p>
<p>A noise window additionally requires at least half its samples and at least 250 usable samples, plus a finite positive MAD. Failing windows are unavailable for detection. Rates must use usable channel-seconds; zero events in unavailable time do not imply neural silence.</p>''')
    section('shared','5 · Shared disturbances: two warning signals', '''<p>“Shared oscillation” is a useful informal description, but the implementation detects <strong>shared disturbances</strong>: an abrupt transition can trigger it without a periodic oscillation.</p>
<table><tr><th>Baseline method</th><th>Broadband method</th></tr><tr><td>Compute the MA200 baseline, average it in 10 ms bins, then compare neighboring bin averages. Normalize each channel’s differences by a robust temporal scale with an across-channel median floor.</td><td>Inspect positive and negative excursions of a 300 Hz high-pass residual within 1 ms bins. Normalize using its masked MAD noise estimate and across-channel median floor.</td></tr><tr><td>Looks for coordinated baseline movement. A qualifying difference flags both contributing 10 ms bins.</td><td>Looks for coordinated fast transients. High-pass filtering does not uniquely distinguish spikes from fast artifacts.</td></tr></table>
<p>The initial rule used 6× normalized excursions. An exploratory adjustment lowered the <em>baseline</em> criterion to 3× while keeping broadband at 6×, after the original rule missed reviewed transitions. The frozen follow-up used this adjusted rule. A same-sign response on at least 50% of eligible channels is required, with at least 1,024 eligible channels. Either baseline or broadband evidence can generate a warning.</p>
<p>These are <strong>artifact-review thresholds</strong>, separate from the 5× threshold that detects candidate eAPs. The MA200/HP300 warning calculations are also separate from the default MA50 detection residual.</p>
<p>Expand the detected shared intervals by ±10 or ±20 ms. For example, an interval from 100–110 ms becomes 90–120 ms with the 10 ms guard, or 80–130 ms with the 20 ms guard. The latter adds another 10 ms on each side; “20 ms” is not the total interval length.</p>
<p>Warnings apply globally at those times, while clipping masks remain per channel. Longer guards can include genuine spikes around a disturbance. Flags mean “review this event in context,” not “confirmed false detection”; synchrony alone is not proof of artifact or brain motion.</p>
<div class="notice">Only 35 of 300 nominal seconds per recording have shared-warning assessment. Outside those intervals, warning availability is false. Unflagged and unassessed are different states. Generic explicit-input runs do not automatically calculate or import these project-specific warnings.</div>''')
    section('fixed','6 · Adaptive versus fixed-reference thresholds', '''<p><strong>Adaptive (default):</strong> estimate noise and the median floor each nominal second. This follows changes in local noise but may raise thresholds during disturbance and hide otherwise detectable spikes.</p>
<p><strong>Fixed (optional):</strong> estimate a per-channel threshold from screened quiet-reference windows using the same selected MA residual. Include the reference median floor, then keep that threshold constant over target time. Fixed mode still applies target observability checks and excludes channels without eligible calibration. It does not substitute HP300 noise for MA50 noise.</p>
<p>The reference screen required agreement across multiple accepted intervals and MA filters. A stable MAD does not guarantee a quiet reference: extra_6 could pass some consistency checks while retaining fast disturbance.</p>
<p>In 42 deliberately selected user-reviewed examples, 38 were labeled plausible eAP, three uncertain and one likely artifact. Adaptive-only examples: 14 plausible. Fixed-only examples: 10 plausible, three uncertain, one likely artifact. Both-method examples: 14 plausible. This supports keeping both choices; it is not a precision or recall estimate. Adaptive remains the adopted default.</p>''')
    section('engineering','7 · Reliable processing and auditable event storage', '''<ul><li><strong>Chunk boundaries:</strong> actual neighboring samples provide filter context. No artificial one-second padding transitions. Global per-channel amplitude-priority peak spacing handles candidates across chunk boundaries.</li><li><strong>Recording edges and tails:</strong> MA50 excludes the first 25 and final 24 samples. Final partial noise windows are supported when they meet the same observation requirements; unsupported tails are explicitly unavailable.</li><li><strong>Peak spacing:</strong> 50 samples / 5 nominal ms, with earlier events winning equal-amplitude ties. An electrode may record multiple neurons, so this can suppress legitimate nearby events and is not a neuronal refractory-period criterion.</li><li><strong>Two-pass processing:</strong> bounded-memory noise/quality pass followed by candidate detection. This makes full 2,048-channel runs practical without loading the entire recording at once.</li><li><strong>Sparse HDF5:</strong> save channel IDs, authoritative sample indices, amplitudes, applied thresholds, warning availability, warning flags and observation exposure. Waveforms remain retrievable from the source, rather than duplicated in each event file.</li><li><strong>Validation:</strong> final files are published only after internal checks. Historical source audits checked selected amplitudes/noise windows and all median floors. These engineering checks do not certify biological accuracy.</li></ul>''')
    rows=''.join(f'<tr><td>extra_{i}</td><td>{s["candidates"]:,}</td><td>{s["channels_with_candidates"]:,}</td><td>{s["usable_channel_seconds"]:,.4f}</td><td>{s["candidates_flagged_shared10"]} / {s["candidates_flagged_shared20"]}</td></tr>' for i,s in zip((4,5),full))
    section('delivery','8 · Delivered scope and remaining work',f'''<table><tr><th>Recording</th><th>Saved candidates</th><th>Channels with candidates</th><th>Usable channel-seconds</th><th>Shared ±10 / ±20 ms flags</th></tr>{rows}</table>
<p>Each recording contains 2,048 channels × 300 nominal seconds, or 614,400 channel-seconds before exclusions. Flagged candidates remain saved; the ±20 ms count includes the ±10 ms subset, so the counts must not be added. All displayed times use nominal 10 kHz; physical sampling is 10,080 Hz. Stored conversion is trusted, not recalibrated here.</p>
<p>extra_4 and extra_5 are purely extracellular recordings; extra_5 followed stimulation experiments. Their count difference is not a demonstrated stimulation effect. extra_6 is excluded from the current delivery. Fast-noise removal, stimulation-period artifact correction and calibrated rail detection remain unresolved.</p>
<p><strong>Next priority:</strong> review raw signals around prominent extra_5 activity episodes, then extend quality assessment across the recording. Preserve detections and show the consequences of any proposed exclusion before adopting it. Mac continues this custom detector workflow independently of the Windows Kilosort project.</p>
<p>This report reviews existing results; it does not rerun detection, alter masks, change defaults or relabel events.</p>''')
    source_links=''.join(f'<li><code>{html.escape(p)}</code></li>' for p in sources)
    section('sources','Evidence and reproduction',f'<p>Prepared 2026-11-22 from local implementation, frozen summaries and historical figures. Historical experiment defaults may differ from the final adopted pipeline. Source SHA-256 hashes are stored in <code>manifest.json</code>; numerical excerpts in <code>evidence.json</code>. Rebuild with <code>.venv/bin/python analysis/report_detection_features.py</code>. Rebuilding replaces this generated report folder’s report/figure files, not detection results.</p><details><summary>Source inventory</summary><ul>{source_links}</ul></details>')
    css='''body{margin:0;background:#edf2f4;color:#203341;font:17px/1.65 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:36px 28px}header{background:#123747;color:white;padding:42px;border-radius:14px}h1{font-size:40px;line-height:1.15;margin:12px 0}h2{line-height:1.25;font-size:27px;color:#145d67}section{background:white;margin:24px 0;padding:30px;border-radius:12px}nav{display:flex;flex-wrap:wrap;gap:10px;margin:22px 0}nav a{padding:7px 12px;background:white;border-radius:20px;color:#145d67;text-decoration:none}table{width:100%;border-collapse:collapse;font-size:15px}td,th{text-align:left;padding:12px;border-bottom:1px solid #d8e2e7;vertical-align:top}th{background:#eaf4f4}figure{margin:24px 0}img{width:100%;height:auto}figcaption{font-size:14px;color:#526771}pre,.flow{white-space:pre-wrap;background:#eef7f5;padding:18px;border-radius:8px;overflow-wrap:anywhere}.notice{background:#fff2d7;padding:18px;border-left:5px solid #d6a147}code{font-size:.88em;overflow-wrap:anywhere}details{font-size:14px}li{margin:8px 0}@media(max-width:650px){main{padding:12px}section,header{padding:18px}h1{font-size:30px}table{display:block;overflow-x:auto}}@media print{body{background:white;font-size:11pt}main{max-width:none;padding:0}nav{display:none}section{break-before:page;padding:0}header{color:#123747;background:white;padding:0}figure{break-inside:avoid}h2{break-after:avoid}}'''
    nav=''.join(f'<a href="#{id}">{title.split(" · ")[-1]}</a>' for id,title,_ in sections)
    body=''.join(f'<section id="{id}"><h2>{title}</h2>{b}</section>' for id,title,b in sections)
    page=f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Spike detection: feature review</title><style>{css}</style><main><header><small>MAC WORKFLOW · METHODS & EVIDENCE REVIEW · 22 NOVEMBER 2026</small><h1>From legacy detection to quality-aware spike candidates</h1><p>Baseline subtraction • clipping masks • shared-disturbance flags</p><p>Better control over what we detect—and explicit records of when observation is unreliable.</p></header><nav>{nav}</nav><div class="notice"><strong>Scope:</strong> candidate eAP detection on extra_4 and extra_5. This is not spike sorting, a ground-truth accuracy study, or validated removal of every artifact.</div>{body}</main></html>'
    (OUT/'report.html').write_text(page)
    evidence={'ma_transition_candidates':dict(zip(['ma50','ma100','ma200'],vals)),'rms_flat_guard_candidates':dict(zip(['no_floor','floor'],pv)),'full_recordings':full}
    (OUT/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    (OUT/'manifest.json').write_text(json.dumps({'date':'2026-11-22','git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_sha256':sources,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'report_sha256':hashlib.sha256((OUT/'report.html').read_bytes()).hexdigest()},indent=2)+'\n')
    assert vals==[28,171,738] and pv==[204,8]
    assert [s['candidates'] for s in full]==[115992,173029]
    assert all(s['shared_warning_evaluated_seconds']==35 for s in full)
    print(OUT/'report.html')

if __name__=='__main__': main()
