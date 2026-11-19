"""Render controlled-comparison tables and per-recording diagnostics locally."""
import argparse
import json
import os
from pathlib import Path
import sys
from html import escape
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/invivo-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analysis.compare_detectors import METHODS, write_csv

LABELS={'ma100_rms':'MA100 · RMS','ma100_mad':'MA100 · MAD',
        'ma200_rms':'MA200 · RMS','ma200_mad':'MA200 · MAD',
        'hp300_rms':'HP300 · RMS','hp300_mad':'HP300 · MAD'}
COLORS=['#9dc5db','#407fa2','#d9b17b','#ad773b','#bcabc9','#785291']


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('results',type=Path)
    args=ap.parse_args(); root=args.results
    summary=json.loads((root/'summary.json').read_text())
    config=json.loads((root/'config.json').read_text())
    figure,axes=plt.subplots(3,2,figsize=(13,11))
    table_rows=[]; flat_rows=[]; all_metrics=[]; validation={}
    for row,rec in enumerate([4,5,6]):
        items=[(name,s) for name,s in summary.items() if name.startswith(f'extra{rec}_')]
        x=np.arange(len(items))
        ax=axes[row,0]
        for i,m in enumerate(METHODS):
            ax.bar(x+(i-2.5)*.12,[s['methods'][m]['candidates'] for _,s in items],width=.12,
                   color=COLORS[i],label=LABELS[m])
        title=f'extra_{rec}'+(' — post-stimulation' if rec in [5,6] else ' — reference recording')
        ax.set_title(title); ax.set_ylabel('Candidate channel-events')
        ax.set_xticks(x,[f'{s["sample_start"]/10000:g}–{s["sample_stop"]/10000:g} s' for _,s in items])
        ax.grid(axis='y',alpha=.2)
        if row==0:
            ax.set_ylim(0,1.3*max(s['methods'][m]['candidates'] for _,s in items for m in METHODS))
            ax.legend(fontsize=8,ncol=2)
        ax=axes[row,1]
        ax.bar(x,[100*s['flat_fraction'] for _,s in items],width=.24,label='Exact flat runs',color='#487fa2')
        ax.bar(x+.25,[100*s['guard_fraction'] for _,s in items],width=.24,label='Flat runs + guard',color='#c69a57')
        ax.bar(x+.50,[100*(1-s['usable_fraction']) for _,s in items],width=.24,label='Total excluded',color='#a65c60')
        ax.set_xticks(x+.25,[f'{s["sample_start"]/10000:g}–{s["sample_stop"]/10000:g} s' for _,s in items])
        ax.set_ylabel('% of channel-time'); ax.set_title('Data availability, identical across all six methods')
        ax.grid(axis='y',alpha=.2)
        if row==0: ax.legend(fontsize=8)
    figure.suptitle('Controlled detector comparison — interpret each recording separately',fontsize=15)
    figure.tight_layout(rect=(0,0,1,.97)); figure.savefig(root/'overview.png',dpi=150); plt.close(figure)
    for name,s in summary.items():
        diag=np.load(root/name/'diagnostics.npz')
        total=s['total_channel_seconds']; exposure=s['usable_channel_seconds']
        assert abs(float(diag['usable_seconds'].sum())-exposure)<1e-8
        assert 0<=exposure<=total
        assert (diag['flat_samples']<=diag['guard_samples']).all()
        assert s['guard_fraction']<=1-s['usable_fraction']+1e-12
        start=s['sample_start']; stop=s['sample_stop']
        for m in METHODS:
            arr=np.loadtxt(root/name/f'{m}.csv',delimiter=',',skiprows=1,ndmin=2)
            if not arr.size: arr=np.empty((0,4))
            assert len(arr)==s['methods'][m]['candidates']
            assert np.isfinite(arr).all()
            assert ((arr[:,1]>=start)&(arr[:,1]<stop)).all()
            assert ((arr[:,0]>=0)&(arr[:,0]<2048)).all()
            assert (arr[:,2]>=arr[:,3]).all()
            for ch in np.unique(arr[:,0]).astype(int):
                rows=arr[arr[:,0]==ch]
                assert (np.diff(rows[:,1])>=50).all()
                windows=(rows[:,1].astype(int)-start)//10000
                assert diag['common_support'][ch,windows].all()
                expected=5*np.maximum(diag['sigma_'+m][ch,windows],diag['floor_'+m][windows])
                np.testing.assert_allclose(rows[:,3],expected,rtol=1e-12)
            all_metrics.append([name,m,len(arr),s['methods'][m]['channels'],exposure,
                                s['methods'][m]['candidates_per_usable_channel_second']])
        validation[name]='All six event tables passed count, finite-value, bounds, spacing, common-support and threshold checks; exposure verified.'
        condition='Post-stimulation' if name.startswith(('extra5','extra6')) else 'Reference'
        table_rows.append('<tr><td>'+escape(name)+'</td><td>'+condition+'</td>'+''.join(f'<td>{s["methods"][m]["candidates"]:,}</td>' for m in METHODS)+'</tr>')
        flat_rows.append(f'<tr><td>{name}</td><td>{100*s["flat_fraction"]:.3f}%</td><td>{100*s["guard_fraction"]:.3f}%</td><td>{100*s["usable_fraction"]:.3f}%</td><td>{exposure:,.2f}</td><td>{s["excluded_channel_windows"]}</td></tr>')
    write_csv(root/'method_metrics.csv',['segment','method','candidate_channel_events','channels_with_events','usable_channel_seconds','candidates_per_usable_channel_second'],all_metrics)
    validation['unit_tests']='10 passed before processing; see tests/test_pilot.py and tests/test_comparison.py'
    (root/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    # Quantify the same previously noted bin under fixed-estimator comparisons.
    event_bin={}
    for m in METHODS:
        a=np.loadtxt(root/'extra4_60_65'/f'{m}.csv',delimiter=',',skiprows=1,ndmin=2)
        event_bin[m]=int(np.sum((a[:,1]>=640300)&(a[:,1]<640400))) if a.size else 0
    (root/'known_transient_counts.json').write_text(json.dumps(event_bin,indent=2)+'\n')
    stable_sections=''.join(f'<details><summary>extra_{rec}, 60–65 s: relatively low baseline excursion</summary><img loading="lazy" src="extra{rec}_60_65/stable_waveforms.png" alt="Repeated candidate waveforms in extra_{rec}"></details>' for rec in [4,5,6] if (root/f'extra{rec}_60_65/stable_waveforms.png').exists())
    disturbance={}
    for name,lo,hi in [('extra4_60_65',64.03,64.04),('extra5_180_185',180.07,180.08),('extra6_60_65',61.2,61.5)]:
        disturbance[name]={'interval_s':[lo,hi],'methods':{}}
        for m in METHODS:
            a=np.loadtxt(root/name/f'{m}.csv',delimiter=',',skiprows=1,ndmin=2)
            mask=(a[:,1]>=round(lo*10000))&(a[:,1]<round(hi*10000))
            disturbance[name]['methods'][m]={'events':int(mask.sum()),'channels':len(np.unique(a[mask,0]))}
    (root/'reviewed_disturbances.json').write_text(json.dumps(disturbance,indent=2)+'\n')
    details=[]
    for name,s in summary.items():
        rows=[]
        for pair,p in s['comparisons'].items():
            a,b=pair.split('__'); agreement='—' if p['jaccard'] is None else f'{100*p["jaccard"]:.1f}%'
            rows.append(f'<tr><td>{LABELS[a]} vs {LABELS[b]}</td><td>{p["matched_within_0_3ms"]}</td><td>{p["a_only"]}</td><td>{p["b_only"]}</td><td>{agreement}</td></tr>')
        peaks='; '.join(f'{LABELS[m]}: {s["methods"][m]["largest_10ms_bin_candidates"]} events at {s["methods"][m]["largest_10ms_bin_start_s"]:.2f} s' for m in ['ma200_mad','hp300_mad'])
        details.append(f'<details><summary>{name}: method agreement and waveform examples</summary><p>Busiest 10 ms bins: {peaks}. These are descriptive coincidence counts, not automatic artifact labels.</p><table><tr><th>Pair</th><th>Matched</th><th>First only</th><th>Second only</th><th>Jaccard</th></tr>{"".join(rows)}</table><p>Matches require the same channel and peaks within ±0.3 ms, one to one. Different filters can shift peaks or change threshold eligibility. Examples prioritize large amplitudes and, for MA-only events, the busiest MA200/MAD bin. They are a diagnostic selection, not an accuracy sample.</p><img loading="lazy" src="{name}/waveforms.png" alt="Diagnostic candidate waveforms for {name}"><p><a href="{name}/waveform_selection.json">Exact example selection</a> · <a href="{name}/summary.json">Segment metrics</a> · <a href="{name}/diagnostics.npz">Noise scales, exposure and baseline diagnostics</a></p></details>')
    transient_rows=''.join(f'<tr><td>{LABELS[m]}</td><td>{event_bin[m]}</td></tr>' for m in METHODS)
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Controlled extracellular detector comparison</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;max-width:1200px;margin:36px auto;padding:0 20px;color:#263645;background:#fafbfc}}h1,h2{{line-height:1.2}}h1{{font-size:30px}}h2{{font-size:22px;margin-top:32px}}img{{width:100%;border:1px solid #dce3e9}}table{{border-collapse:collapse;width:100%;background:white;font-size:13px}}td,th{{padding:9px;text-align:left;border-bottom:1px solid #dce3e9}}.notice{{padding:16px;background:#fff1d4;border-radius:8px}}details{{background:white;border:1px solid #dce3e9;border-radius:7px;margin:14px 0;padding:14px}}summary{{cursor:pointer;font-weight:600}}a{{color:#276b96}}code{{overflow-wrap:anywhere}}.scroll{{overflow-x:auto}}</style>
<h1>Controlled extracellular detector comparison</h1><p>All 2048 channels · nine five-second segments · nominal 10 kHz · project-local Python environment</p>
<p class="notice"><strong>Experimental conditions remain separate.</strong> All three files are purely extracellular recordings. The user identifies extra_5 and extra_6 as acquired after current-injection stimulation experiments, with potentially worse baseline fluctuations and perturbed neural activity. extra_4 is the reference for this comparison; its earlier stimulation history is not asserted. Compare detector variants within the same segment. Changes across recordings cannot be interpreted as detector accuracy or a causal stimulation effect.</p>
<h2>Findings from waveform inspection</h2><ul>
<li><strong>Moving-average window length matters.</strong> In the known extra_4 transient bin, MA200/MAD yields {event_bin['ma200_mad']} candidates, MA100/MAD {event_bin['ma100_mad']}, and HP300/MAD {event_bin['hp300_mad']}. The RMS comparison shows the same direction. Reviewed MA-only examples show broad deflections alongside a changing baseline; the high-pass attenuates these deflections. This does not prove that every removed candidate is false.</li>
<li><strong>A similar issue appears in extra_5.</strong> At 180.07–180.08 s, MA200/MAD yields {disturbance['extra5_180_185']['methods']['ma200_mad']['events']} candidates, versus {disturbance['extra5_180_185']['methods']['hp300_mad']['events']} for HP300/MAD. Selected raw traces again show a baseline transition.</li>
<li><strong>High-pass filtering is insufficient for extra_6.</strong> In 60–65 s, HP300/MAD yields {summary["extra6_60_65"]["methods"]["hp300_mad"]["candidates"]:,} candidates; {disturbance["extra6_60_65"]["methods"]["hp300_mad"]["events"]:,} ({100*disturbance["extra6_60_65"]["methods"]["hp300_mad"]["events"]/summary["extra6_60_65"]["methods"]["hp300_mad"]["candidates"]:.1f}%) lie within 61.2–61.5 s and involve {disturbance["extra6_60_65"]["methods"]["hp300_mad"]["channels"]:,} channels. Reviewed raw traces show a shared oscillatory disturbance. Its origin is not established. Neither the filter nor the flat guard excludes it.</li>
<li><strong>MAD is not an artifact classifier.</strong> In the same extra_6 segment, HP300/RMS yields {summary["extra6_60_65"]["methods"]["hp300_rms"]["candidates"]:,} candidates, compared with {summary["extra6_60_65"]["methods"]["hp300_mad"]["candidates"]:,} for HP300/MAD on identical observation support. Large disturbances can affect RMS and MAD very differently. Fewer RMS detections do not establish greater accuracy, since true spikes may also be suppressed.</li>
<li><strong>Repeated narrow candidates remain visible.</strong> Channels 1436 and 1378 in extra_4 and extra_5 have recurring narrow negative waveforms in the selected examples. This is promising morphology, not verified unit isolation. In extra_6 even relatively low-baseline-excursion selections are contaminated by the shared disturbance.</li></ul>
<h2>What changed in this comparison</h2><p>The original pilot changed filtering and threshold estimation together. Here every filter is paired with both RMS and MAD estimates. Both estimates use the same unmasked samples. All methods use the same per-channel flat mask (≥1 ms of identical stored values), ±50 ms guard, 5× threshold multiplier, across-channel median noise floor, and 5 ms peak spacing. Noise floors are recomputed for each method, so absolute voltage thresholds still differ.</p>
<p>Filters: 100-sample moving-average subtraction (10 ms), 200-sample subtraction (20 ms), and third-order Butterworth 300 Hz high-pass applied forward and backward. Each segment includes 250 ms of real context on both sides. Estimation windows need at least half their samples and at least 250 unmasked samples. If any method has a nonpositive or nonfinite scale, that channel-window is excluded from every method. Thus observation time is identical across the comparison.</p>
<h2>Counts and availability</h2><img src="overview.png" alt="Candidate counts and excluded observation time, with recordings kept separate">
<p>Each event is a channel detection; the same neural event may appear on multiple electrodes. Neither counts nor cross-method agreement establish true-positive rates, neuron counts or sensitivity.</p><div class="scroll"><table><tr><th>Segment</th><th>Condition</th>{''.join(f'<th>{LABELS[m]}</th>' for m in METHODS)}</tr>{''.join(table_rows)}</table></div>
<h2>Usable recording time</h2><p>The explicit flat guard and unavailable noise-estimation windows both reduce exposure. Below, usable channel-seconds sum eligible time across all electrodes; a full five-second segment supplies 10,240 channel-seconds.</p><div class="scroll"><table><tr><th>Segment</th><th>Flat samples</th><th>Flat + guard</th><th>Usable</th><th>Usable channel-s</th><th>Excluded channel-windows</th></tr>{''.join(flat_rows)}</table></div>
<h2>Known baseline transient: 64.03–64.04 s in extra_4</h2><p>The user considers relative brain–shank motion a likely explanation, not a proven cause. This bin is examined because it dominated the original pilot. No global artifact mask has been applied: these counts remain visible for review. Compare the filters with the same estimator below to separate filtering from the RMS/MAD choice.</p><table><tr><th>Method</th><th>Candidates in the same 10 ms bin</th></tr>{transient_rows}</table>
<h2>Relatively stable-channel review</h2><p>These selections have ≥10 HP300/MAD candidates, no flat guards, all windows usable, and a baseline excursion at or below the median among eligible channels. Two channels with the largest candidate counts are shown per recording. The same HP-selected event times are overlaid under MA200 and HP300, avoiding different event sets in the two panels. This selection favors HP detections and is not an unbiased filter evaluation. “Relatively stable” does not mean artifact-free, especially in extra_6.</p>{stable_sections}<p><a href="stable_channel_selection.json">Selection criteria and exact waveform indices</a></p>
<h2>Waveform review and event agreement</h2><p>Expand each segment for shared, MA200-only and high-pass-only examples. “Only” means absent from the other detector within the matching tolerance; it does not mean false or true. Stored float units are preserved, accepting the existing conversion.</p>{''.join(details)}
<h2>Interpretation limits and next decision</h2><p>The comparison supports inspection of robustness to baseline changes and clipping, not a final biological ground truth. In particular, post-stimulation recordings can have genuinely different activity as well as worse artifacts. Do not choose the method with the fewest or most events solely from these tables. Retain explicit invalid-time reporting, review disputed waveforms, and validate artifact rejection before scaling to full recordings. A global motion-artifact mask, if added, should be evaluated separately from per-channel clipping masks.</p>
<h2>Reproduce and inspect</h2><pre>.venv/bin/python analysis/compare_detectors.py --output results/new_comparison
.venv/bin/python analysis/review_stable_channels.py results/new_comparison
.venv/bin/python analysis/report_comparison.py results/new_comparison
.venv/bin/python -m unittest discover -s tests -v</pre><p>Default sampling is 30–35, 60–65 and 180–185 s from each converted file. Outputs refuse overwrite; recordings are opened read-only. Results are ignored by Git, while analysis code and tests are available for version control.</p>
<p><a href="config.json">Configuration and experimental context</a> · <a href="method_metrics.csv">Counts and usable-time rates</a> · <a href="summary.json">Full summaries</a> · <a href="validation.json">Validation checks</a> · <a href="known_transient_counts.json">Known-transient counts</a></p></html>'''
    (root/'review.html').write_text(html)
    print(json.dumps({'known_transient_counts':event_bin,'segments':len(summary)},indent=2))
    print(root/'review.html')


if __name__=='__main__': main()
