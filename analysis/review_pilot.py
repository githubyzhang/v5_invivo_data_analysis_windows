"""Build a local HTML review and focused figures from completed pilot outputs."""
import os
os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/invivo-matplotlib')
import argparse
import json
from html import escape
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('results',type=Path)
    args=ap.parse_args()
    root=args.results
    s=json.loads((root/'summary.json').read_text())
    fs=s['nominal_fs_hz']; start=s['start_sample']; n=s['stop_sample']-start
    methods=list(s['methods'])
    arrays={m:np.loadtxt(root/f'events_{m}.csv',delimiter=',',skiprows=1,ndmin=2) for m in methods}
    sync={}
    for m,a in arrays.items():
        bins=(a[:,1].astype(int)-start)//100
        counts=np.bincount(bins,minlength=(n+99)//100)
        i=int(np.argmax(counts))
        sync[m]={'largest_10ms_bin_start_s':(start+100*i)/fs,
                 'events_in_bin':int(counts[i]),'unique_channels_in_bin':len(np.unique(a[bins==i,0])),
                 'events_64_03_to_64_04':int(np.sum((a[:,1]>=640300)&(a[:,1]<640400)))}
    # The focused review is intentionally specific to the initial 60–65 s pilot.
    z=np.load(root/'review_traces.npz')
    if start != 600000 or n != 50000 or not all(f'ch{c}_raw' in z for c in [353,1913,1436]):
        raise ValueError('This focused review currently targets the initial extra_4 60–65 s pilot only.')
    fig,axes=plt.subplots(2,2,figsize=(13,8))
    t=(start+np.arange(n))/fs
    # Local plateau detail: locate an end of a long flat interval in channel 353.
    ax=axes[0,0]
    select=(t>=62.65)&(t<=62.95)
    ax.plot(t[select],z['ch353_raw'][select],lw=.8,label='Stored signal')
    ax.plot(t[select],z['ch353_ma_residual'][select],lw=.8,label='MA residual')
    ax.fill_between(t[select],0,1,where=z['ch353_excluded'][select],transform=ax.get_xaxis_transform(),color='#e5b444',alpha=.25)
    ax.set_title('Ch 353: flat signal and transition (shaded = excluded)')
    ax.legend(fontsize=8)
    ax=axes[0,1]
    select=(t>=64.00)&(t<=64.10)
    ax.plot(t[select],z['ch1913_ma_residual'][select],label='MA residual',lw=1)
    ax.plot(t[select],z['ch1913_hp_residual'][select],label='300 Hz high-pass',lw=1)
    ax.axvspan(64.03,64.04,color='#e5b444',alpha=.25,label='Shared-event bin')
    ax.set_title('Ch 1913: baseline-associated transient')
    ax.legend(fontsize=8)
    ax=axes[1,0]
    for m,label in [('context_rms_floor','MA / RMS + floor'),('highpass_mad_masked','High-pass / masked MAD')]:
        counts=np.bincount((arrays[m][:,1].astype(int)-start)//100,minlength=500)
        ax.plot(60+np.arange(500)*.01,counts,label=label,lw=1)
    ax.set_title('Candidate events across 2048 channels per 10 ms')
    ax.set_ylabel('Event count')
    ax.legend(fontsize=8)
    ax=axes[1,1]
    m='highpass_mad_masked'
    a=arrays[m]
    p=a[a[:,0]==1436,1].astype(int)-start
    p=p[(p>=30)&(p<n-30)]
    waveforms=np.array([z['ch1436_hp_residual'][i-30:i+31] for i in p])
    tt=np.arange(-30,31)/fs*1000
    ax.plot(tt,waveforms.T,color='#487ca0',alpha=.2,lw=.7)
    ax.plot(tt,np.median(waveforms,axis=0),color='#173b58',lw=2,label='Median')
    ax.set_title(f'Ch 1436: {len(p)} candidate waveforms, high-pass')
    ax.set_xlabel('Time from detected negative peak (ms)')
    ax.legend(fontsize=8)
    for ax in axes.flat:
        ax.grid(alpha=.2)
        if ax!=axes[1,0]: ax.set_ylabel('Stored float units')
        if ax!=axes[1,1]: ax.set_xlabel('Nominal recording time (s, 10 kHz)')
    fig.suptitle('Pilot review: clipping risk, baseline transient, and candidate waveforms',fontsize=14)
    fig.tight_layout(rect=(0,0,1,.96))
    fig.savefig(root/'focused_review.png',dpi=150)
    plt.close(fig)
    (root/'synchrony_review.json').write_text(json.dumps(sync,indent=2)+'\n')
    names={'legacy_rms_floor':'Legacy MA + RMS floor, 5 ms',
           'context_rms':'Context MA + RMS, no floor, 5 ms',
           'context_rms_floor':'Context MA + RMS floor, 5 ms',
           'context_mad_masked':'Context MA + masked MAD floor, 5 ms',
           'highpass_mad_masked':'300 Hz high-pass + masked MAD floor, 5 ms',
           'context_mad_masked_1ms':'Context MA + masked MAD floor, 1 ms'}
    rows=''.join(f'<tr><td>{names[m]}</td><td>{v["event_count"]:,}</td><td>{v["channels_with_events"]:,}</td><td>{v["events_in_suspect_flat_guard"]}</td><td>{sync[m]["events_64_03_to_64_04"]}</td></tr>' for m,v in s['methods'].items())
    links=''.join(f'<li><a href="events_{m}.csv">{names[m]} event table</a></li>' for m in methods)
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Extracellular pilot review</title><style>body{{font:16px/1.55 system-ui,sans-serif;max-width:1150px;margin:36px auto;padding:0 22px;color:#243342;background:#fafbfc}}h1,h2{{line-height:1.2}}h1{{font-size:30px}}h2{{font-size:22px;margin-top:32px}}img{{width:100%;background:white;border:1px solid #dce3e9}}table{{border-collapse:collapse;width:100%;background:white;font-size:14px}}td,th{{text-align:left;padding:10px;border-bottom:1px solid #dce3e9}}.note{{background:#fff3d5;padding:16px;border-radius:8px}}code{{overflow-wrap:anywhere}}a{{color:#216393}}</style>
<h1>Extracellular pilot: extra_4, 60–65 seconds</h1>
<p>All 2048 channels; nominal 10 kHz throughout. Physical rate is 10,080 Hz. Existing float conversion is accepted. Source opened read-only: <code>{escape(s['source'])}</code>. Source array: 2048 × 3,000,000, float16. Channel IDs are zero-based.</p>
<p class="note"><strong>These are candidate events, not validated eAP counts.</strong> This short, single-recording pilot has no ground truth. Diagnostic channels were deliberately selected for flatness, baseline movement, candidate abundance and median noise; they are not a random accuracy sample.</p>
<h2>What the pilot shows</h2>
<ul><li><strong>The median-noise safeguard helps:</strong> using identical context MA and RMS settings, adding the across-channel median floor reduced candidates inside suspected-flat guards from 204 to 8. This is evidence of suppression in risky intervals, not proof that all removed events were false.</li>
<li><strong>Clipping requires an observability flag as well as a threshold:</strong> 185 channels contain exact repeated-value runs ≥1 ms. These runs occupy 0.770% of channel-samples; adding a provisional ±50 ms guard excludes 1.094%. Channel 353 is flat for 81.7% of this segment. Exact flatness can also result from float16 quantization, disconnected channels or missing data, so calibrated rail detection remains unresolved.</li>
<li><strong>A shared baseline-associated event dominates the legacy count:</strong> 768 of 1,460 legacy candidates occur on 768 different channels during 64.03–64.04 s. Reviewed raw traces show a baseline shift at this time. This strongly motivates transient/artifact review; synchrony alone does not establish non-neural origin.</li>
<li><strong>Moving-average implementation can be faster without changing its definition:</strong> a compiled uniform filter matches the legacy convolution numerically, including the even-window alignment. Real neighboring samples remove artificial one-second padding boundaries; global peak spacing and final partial windows are handled in the context methods.</li>
<li><strong>The filter choice is not settled:</strong> the experimental high-pass method produces fewer widespread events and candidate waveforms worth reviewing, but the comparison also changes the noise scale. Counts alone cannot establish improved accuracy or justify committing to a 300 Hz cutoff.</li></ul>
<h2>Method comparison</h2><table><thead><tr><th>Method</th><th>Candidates</th><th>Channels</th><th>Inside flat guard</th><th>64.03–64.04 s</th></tr></thead><tbody>{rows}</tbody></table>
<p>All thresholds are 5× the estimated noise. RMS floors use the across-channel median within each nominal second. Masked MAD floors use channels with finite, positive estimates from unmasked samples; a window requires at least half its samples and at least 250 samples to estimate MAD. 116 channel-windows lacked an estimate and produced no candidates. This adds exposure loss beyond the explicit flat guards. Masked methods exclude suspect intervals before peak-spacing selection. One-millisecond spacing is a sensitivity comparison, not an adopted default.</p>
<h2>Focused visual review</h2><img src="focused_review.png" alt="Flat interval, common transient, event counts and candidate waveform overlay">
<h2>Full diagnostic traces</h2><img src="diagnostics.png" alt="Four selected channels with raw traces, moving-average and high-pass residuals">
<h2>Next analysis decision</h2><p>Review accepted and rejected waveform examples around the common transient and on stable channels; compare filter and threshold changes separately, then repeat on other times and extracellular recordings before choosing full-recording defaults. Use explicit invalid-time masks and report usable recording duration. Keep the median floor as an additional safeguard during validation. Stimulation analysis and raw conversion remain deferred.</p>
<h2>Reproduce and inspect</h2><p>From the project folder, using Python with <code>requirements.txt</code> installed:</p><pre>python analysis/pilot.py --output results/new_pilot_run
python analysis/review_pilot.py results/new_pilot_run
python -m unittest discover -s tests -v</pre>
<p>The focused review script targets this initial interval and the selected channels. The pilot refuses to overwrite a nonempty output folder. Its detector is a segment-level research prototype, not yet a full-recording streaming pipeline. The existing scientific environment was used without installing into or changing it. No legacy source or external recording was modified.</p>
<ul><li><a href="summary.json">Parameters, source metadata and method summaries</a></li><li><a href="channel_diagnostics.csv">Per-channel diagnostics</a></li><li><a href="synchrony_review.json">Coincidence counts</a></li><li><a href="review_traces.npz">Selected review traces and masks</a></li>{links}</ul></html>'''
    (root/'review.html').write_text(html)
    print(json.dumps(sync,indent=2))
    print(root/'review.html')


if __name__=='__main__':
    main()
