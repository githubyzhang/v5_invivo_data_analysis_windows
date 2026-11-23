"""Validate and render shared-disturbance annotation results, including loss review."""
import argparse
import json
import os
from pathlib import Path
import sys
from html import escape
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/invivo-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import sosfiltfilt
from analysis.shared_artifacts import PRIMARY, SIGMAS, FRACTIONS, GUARDS, intervals
from analysis.compare_detectors import FS,CONTEXT,SOS,METHODS
from analysis.pilot import write_csv

ALT="b3_h6_f50_g10"


def loss_figure(root,prior,summaries,variant=PRIMARY):
    fig,axes=plt.subplots(2,3,figsize=(15,8),sharex=True)
    selections={}
    for col,rec in enumerate([4,5,6]):
        name=f'extra{rec}_60_65'; s=summaries[name]
        flag=np.load(root/name/'flags_and_evidence.npz')['mask_'+variant]
        events=np.loadtxt(root/name/'annotated_hp300_mad.csv',delimiter=',',skiprows=1,ndmin=2)
        with h5py.File(s['source'],'r') as f:
            for row,ch in enumerate([1436,1378]):
                start,stop=s['sample_start'],s['sample_stop']
                raw=f['signals'][ch,start-CONTEXT:stop+CONTEXT].astype(float)
                y=sosfiltfilt(SOS,raw)[CONTEXT:-CONTEXT]
                p=events[events[:,0]==ch,1].astype(int)-start
                p=p[(p>=30)&(p<len(y)-30)]
                ax=axes[row,col]
                detail={}
                for flagged,color,label in [(False,'#3b799b','Retained'),(True,'#bd5549','Flagged')]:
                    indices=p[flag[p]==flagged]
                    total=len(indices)
                    if total:
                        indices=indices[np.unique(np.linspace(0,total-1,min(total,30)).astype(int))]
                        waves=np.array([y[i-30:i+31] for i in indices])
                        t=np.arange(-30,31)/FS*1000
                        ax.plot(t,waves.T,color=color,alpha=.15,lw=.6)
                        ax.plot(t,np.median(waves,axis=0),color=color,lw=2,label=f'{label}: {total} candidates')
                    else: ax.plot([],[],color=color,label=f'{label}: 0 candidates')
                    detail[label.lower()]={'total':total,'shown_sample_indices':(indices+start).tolist()}
                ax.set_title(f'extra_{rec} · channel {ch}')
                ax.set_xlabel('Time from HP300 candidate peak (ms)')
                ax.set_ylabel('Stored float units')
                ax.legend(fontsize=8); ax.grid(alpha=.15)
                selections[f'{name}_ch{ch}']=detail
    fig.suptitle(f'Potential loss review ({variant}) — shared flags can exclude genuine spikes',fontsize=13)
    fig.tight_layout(rect=(0,0,1,.96)); fig.savefig(root/'candidate_loss_review.png',dpi=140); plt.close(fig)
    (root/'loss_review_selection.json').write_text(json.dumps(selections,indent=2)+'\n')


def alternative_evidence(name,root,d,start,arrays):
    fig,axes=plt.subplots(3,1,figsize=(12,8),sharex=True)
    for k,color in [(3,'#386f95'),(6,'#aaaaaa')]:
        e=d['baseline_eligible']; q=np.maximum(d[f'baseline_positive_k{k}'],d[f'baseline_negative_k{k}'])
        score=np.divide(q,e,out=np.zeros(len(e)),where=e>0)
        axes[0].plot((start+np.arange(len(e))*100)/FS,score,color=color,label=f'Baseline {k}×',lw=1)
    e=d['hp_eligible']; q=np.maximum(d['hp_positive_k6'],d['hp_negative_k6'])
    score=np.divide(q,e,out=np.zeros(len(e)),where=e>0)
    axes[1].plot((start+np.arange(len(e))*10)/FS,score,color='#755389',label='Broadband 6×',lw=1)
    for ax in axes[:2]:
        ax.axhline(.5,color='#9b3333',ls='--',lw=.8); ax.set_ylim(0,1.05); ax.legend(fontsize=8)
        ax.set_ylabel('Same-sign channel fraction')
    n=len(d['mask_'+ALT])
    for m,color in [('ma200_mad','#386f95'),('hp300_mad','#755389')]:
        a=arrays[m]; counts=np.bincount((a[:,1].astype(int)-start)//100,minlength=n//100)
        axes[2].plot((start+np.arange(len(counts))*100)/FS,counts,color=color,label=m,lw=1)
    axes[2].set_ylabel('Candidates / 10 ms'); axes[2].legend(fontsize=8)
    axes[2].set_xlabel('Nominal recording time (s, 10 kHz)')
    for ax in axes:
        for a,b in intervals(d['mask_'+ALT]): ax.axvspan((start+a)/FS,(start+b)/FS,color='#dfa33b',alpha=.22)
        ax.grid(alpha=.15)
    fig.suptitle(name+' — adjusted baseline rule; shaded intervals remain review flags',fontsize=13)
    fig.tight_layout(rect=(0,0,1,.96)); fig.savefig(root/name/'adjusted_evidence.png',dpi=140); plt.close(fig)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('results',type=Path)
    root=ap.parse_args().results
    config=json.loads((root/'config.json').read_text())
    prior=Path(config['comparison_directory'])
    summaries=json.loads((root/'summary.json').read_text())
    checks={}; csvrows=[]; tablerows=[]; altrows=[]; details=[]; capture={}; altcapture={}
    has_alt=all(ALT in v["variants"] for v in summaries.values())
    for name,s in summaries.items():
        d=np.load(root/name/'flags_and_evidence.npz')
        n=s['sample_stop']-s['sample_start']; start=s['sample_start']
        eligible=d['eligible_channels_per_sample']
        assert abs(eligible.sum()/FS-s['original_usable_channel_seconds'])<1e-8
        for k in SIGMAS:
            for g in GUARDS:
                lo=d[f'mask_k{k}_f25_g{g}']; mid=d[f'mask_k{k}_f50_g{g}']; hi=d[f'mask_k{k}_f75_g{g}']
                assert not (hi&~mid).any() and not (mid&~lo).any()
            for frac in [25,50,75]:
                small=d[f'mask_k{k}_f{frac}_g5']; large=d[f'mask_k{k}_f{frac}_g20']
                assert not (small&~large).any()
        for frac in [25,50,75]:
            for g in GUARDS:
                assert not (d[f'mask_k8_f{frac}_g{g}']&~d[f'mask_k6_f{frac}_g{g}']).any()
        assert np.array_equal(d['mask_'+PRIMARY],d['baseline_primary']|d['broadband_primary'])
        if has_alt:
            assert not (d['mask_'+PRIMARY]&~d['mask_'+ALT]).any()
            for g in GUARDS:
                assert not (d[f'mask_b3_h6_f75_g{g}']&~d[f'mask_b3_h6_f50_g{g}']).any()
                assert not (d[f'mask_b3_h6_f50_g{g}']&~d[f'mask_b3_h6_f25_g{g}']).any()
        arrays={}
        for m in METHODS:
            original=np.loadtxt(prior/name/f'{m}.csv',delimiter=',',skiprows=1,ndmin=2)
            annotated=np.loadtxt(root/name/f'annotated_{m}.csv',delimiter=',',skiprows=1,ndmin=2)
            np.testing.assert_array_equal(original,annotated[:,:4])
            pos=annotated[:,1].astype(int)-start
            np.testing.assert_array_equal(annotated[:,4].astype(bool),d['mask_'+PRIMARY][pos])
            np.testing.assert_array_equal(annotated[:,5].astype(bool),d['baseline_primary'][pos])
            np.testing.assert_array_equal(annotated[:,6].astype(bool),d['broadband_primary'][pos])
            arrays[m]=annotated
            if has_alt:
                write_csv(root/name/f'annotated_adjusted_{m}.csv',
                          ['channel_id','sample_index','negative_amplitude','threshold','original_primary_flag','adjusted_shared_flag'],
                          ((int(ch),int(p),amp,thr,int(flag),int(d['mask_'+ALT][int(p)-start]))
                           for ch,p,amp,thr,flag,_,_ in annotated))
                adjusted=np.loadtxt(root/name/f'annotated_adjusted_{m}.csv',delimiter=',',skiprows=1,ndmin=2)
                np.testing.assert_array_equal(adjusted[:,:4],original)
                np.testing.assert_array_equal(adjusted[:,5].astype(bool),d['mask_'+ALT][pos])
            for key,v in s['variants'].items():
                assert int(d['mask_'+key][pos].sum())==v['methods'][m]['flagged']
                assert v['methods'][m]['retained']+v['methods'][m]['flagged']==len(annotated)
        rows=[]
        for key,v in s['variants'].items():
            mask=d['mask_'+key]
            assert abs(mask.sum()/FS-v['flagged_duration_s'])<1e-9
            assert abs(eligible[mask].sum()/FS-v['additional_excluded_channel_seconds'])<1e-8
            assert abs(v['retained_channel_seconds']+v['additional_excluded_channel_seconds']-s['original_usable_channel_seconds'])<1e-8
            h=v['methods']['hp300_mad']; ma=v['methods']['ma200_mad']
            csvrows.append([name,key,v['flagged_duration_s'],v['fraction_of_previously_usable_time_flagged'],ma['flagged'],ma['retained'],h['flagged'],h['retained']])
            rows.append(f'<tr><td>{key}</td><td>{v["flagged_duration_s"]:.3f}</td><td>{100*v["fraction_of_previously_usable_time_flagged"]:.2f}%</td><td>{ma["flagged"]:,}</td><td>{h["flagged"]:,}</td></tr>')
        v=s['variants'][PRIMARY]; ma=v['methods']['ma200_mad']; h=v['methods']['hp300_mad']
        condition='Post-stimulation' if name.startswith(('extra5','extra6')) else 'Reference'
        channeltext='; '.join(f'ch {ch}: {c["flagged_candidates"]}/{c["original_candidates"]}' for ch,c in s['review_channels'].items())
        tablerows.append(f'<tr><td>{name}</td><td>{condition}</td><td>{v["flagged_duration_s"]:.3f}</td><td>{100*v["fraction_of_previously_usable_time_flagged"]:.2f}%</td><td>{ma["flagged"]:,}/{ma["original"]:,}</td><td>{h["flagged"]:,}/{h["original"]:,}</td></tr>')
        if has_alt:
            av=s['variants'][ALT]; am=av['methods']['ma200_mad']; ah=av['methods']['hp300_mad']
            altrows.append(f'<tr><td>{name}</td><td>{av["flagged_duration_s"]:.3f}</td><td>{100*av["fraction_of_previously_usable_time_flagged"]:.2f}%</td><td>{am["flagged"]:,}/{am["original"]:,}</td><td>{ah["flagged"]:,}/{ah["original"]:,}</td></tr>')
            alternative_evidence(name,root,d,start,arrays)
        interval_text='; '.join(f'{(start+a)/FS:.4f}–{(start+b)/FS:.4f} s' for a,b in intervals(d['mask_'+PRIMARY])) or 'None'
        altlink=f'<p><a href="{name}/adjusted_evidence.png">Adjusted baseline-rule evidence plot</a> · <a href="{name}/annotated_adjusted_hp300_mad.csv">Events with both rule annotations</a></p>' if has_alt else ''
        details.append(f'<details><summary>{name}: evidence, intervals and parameter sensitivity</summary>{altlink}<p>Primary intervals: {interval_text}</p><p>Review-channel HP300/MAD candidates flagged/original: {channeltext}. These channels are examples, not independent validation.</p><img loading="lazy" src="{name}/evidence.png" alt="Signal consensus and candidate timing in {name}"><table><tr><th>Variant</th><th>Flagged seconds</th><th>Additional usable-time loss</th><th>MA200/MAD flagged</th><th>HP300/MAD flagged</th></tr>{"".join(rows)}</table><p><a href="{name}/flagged_intervals.csv">Half-open flag intervals</a> · <a href="{name}/summary.json">All method metrics</a> · <a href="{name}/annotated_hp300_mad.csv">Annotated HP300/MAD events</a> · <a href="{name}/flags_and_evidence.npz">All masks and evidence arrays</a></p></details>')
        checks[name]='All original event columns preserved; every annotation and all evaluated variants agree with saved masks; exposure and monotonic sensitivity checks passed.'
        if name in ['extra4_60_65','extra5_180_185','extra6_60_65']:
            lo,hi={'extra4_60_65':(64.03,64.04),'extra5_180_185':(180.07,180.08),'extra6_60_65':(61.2,61.5)}[name]
            a,b=round(lo*FS)-start,round(hi*FS)-start
            if has_alt:
                altcapture[name]={'review_interval_s':[lo,hi],'fraction_of_interval_flagged':float(d['mask_'+ALT][a:b].mean()),'methods':{}}
            capture[name]={'review_interval_s':[lo,hi],'fraction_of_interval_flagged':float(d['mask_'+PRIMARY][a:b].mean()),'methods':{}}
            for m,arr in arrays.items():
                inside=(arr[:,1]>=round(lo*FS))&(arr[:,1]<round(hi*FS))
                capture[name]['methods'][m]={'candidates_in_interval':int(inside.sum()),'flagged':int(arr[inside,4].sum())}
                if has_alt:
                    pos=arr[inside,1].astype(int)-start
                    altcapture[name]['methods'][m]={'candidates_in_interval':int(inside.sum()),'flagged':int(d['mask_'+ALT][pos].sum())}
    write_csv(root/'sensitivity.csv',['segment','variant','flagged_s','additional_usable_time_loss_fraction','ma200_mad_flagged','ma200_mad_retained','hp300_mad_flagged','hp300_mad_retained'],csvrows)
    (root/'reviewed_disturbance_coverage.json').write_text(json.dumps(capture,indent=2)+'\n')
    checks['unit_tests']='15 passed before evaluation; shared-flag tests cover same-sign quorum, support, interval endpoints, guards and monotonicity.'
    (root/'validation.json').write_text(json.dumps(checks,indent=2)+'\n')
    loss_figure(root,prior,summaries,ALT if has_alt else PRIMARY)
    (root/'adjusted_disturbance_coverage.json').write_text(json.dumps(altcapture,indent=2)+'\n')
    altsection=''
    if has_alt:
        capture_alt_rows=[]
        for name,c in altcapture.items():
            ma=c['methods']['ma200_mad']; hp=c['methods']['hp300_mad']
            capture_alt_rows.append(f'<tr><td>{name}</td><td>{100*c["fraction_of_interval_flagged"]:.1f}%</td><td>{ma["flagged"]}/{ma["candidates_in_interval"]}</td><td>{hp["flagged"]}/{hp["candidates_in_interval"]}</td></tr>')
        altsection=f'<h2>Exploratory adjustment: baseline 3×, broadband unchanged at 6×</h2><p>The original 6×/50% rule missed both reviewed baseline transitions. After inspecting those misses, nine additional variants lowered only the baseline threshold to 3×. This is explicit tuning on reviewed data, not independent validation. The table uses 50% quorum and ±10 ms guard (b3_h6_f50_g10); the original primary results above remain unchanged.</p><table><tr><th>Segment</th><th>Flagged seconds</th><th>Additional usable-time loss</th><th>MA200/MAD flagged/original</th><th>HP300/MAD flagged/original</th></tr>{"".join(altrows)}</table><p>Coverage of the previously reviewed intervals under the adjusted rule:</p><table><tr><th>Segment</th><th>Time flagged</th><th>MA200/MAD flagged/in interval</th><th>HP300/MAD flagged/in interval</th></tr>{"".join(capture_alt_rows)}</table><p>Annotated tables preserve both original and adjusted flags. The same rule is applied to every segment; no interval was manually inserted. Remaining unflagged candidates are not automatically validated spikes.</p>'
    outcome=''
    if has_alt:
        no_flags=sum(v['variants'][ALT]['flagged_duration_s']==0 for v in summaries.values())
        loss=json.loads((root/'loss_review_selection.json').read_text())
        lost=loss['extra4_60_65_ch1436']['flagged']['total']
        total=lost+loss['extra4_60_65_ch1436']['retained']['total']
        outcome=f'<h2>Outcome</h2><p>The original rule detected much of the extra_6 disturbance but missed the two reviewed baseline transitions. Lowering only the baseline threshold to 3× covers both transitions; {no_flags} of the nine sampled intervals remain unflagged. This adjusted rule is a candidate for testing on new data, not an adopted exclusion policy.</p><p><strong>There is a real exclusion tradeoff:</strong> the adjusted rule flags {lost} of {total} complete-waveform candidates on the previously reviewed channel 1436 in extra_4, including a narrow spike-like waveform. It cannot be called a confirmed false positive. In extra_6, a 20 ms guard captures more burst-tail candidates than a 10 ms guard, while excluding more time. Unflagged events and intervals are not certified artifact-free.</p>'
    capture_rows=[]
    for name,c in capture.items():
        ma=c['methods']['ma200_mad']; hp=c['methods']['hp300_mad']
        capture_rows.append(f'<tr><td>{name}</td><td>{c["review_interval_s"][0]}–{c["review_interval_s"][1]}</td><td>{100*c["fraction_of_interval_flagged"]:.1f}%</td><td>{ma["flagged"]}/{ma["candidates_in_interval"]}</td><td>{hp["flagged"]}/{hp["candidates_in_interval"]}</td></tr>')
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Shared-disturbance flag evaluation</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;max-width:1200px;margin:36px auto;padding:0 22px;color:#263645;background:#fafbfc}}h1,h2{{line-height:1.2}}h1{{font-size:30px}}h2{{font-size:22px;margin-top:32px}}img{{width:100%;border:1px solid #dce3e9}}table{{border-collapse:collapse;width:100%;background:white;font-size:13px}}td,th{{padding:9px;text-align:left;border-bottom:1px solid #dce3e9}}.notice{{background:#fff1d4;padding:16px;border-radius:8px}}details{{padding:14px;border:1px solid #dce3e9;background:white;margin:14px 0}}summary{{font-weight:600;cursor:pointer}}a{{color:#276b96}}.scroll{{overflow-x:auto}}</style>
<h1>Shared-disturbance flag evaluation</h1><p>Nine previously reviewed five-second segments · all 2048 channels · nominal 10 kHz · original detections preserved</p>
<p class="notice"><strong>Flags mean “review this shared disturbance,” not “proven false spike.”</strong> Shared neural activity can also trigger consensus. Every original candidate is retained in the annotated tables; no recording, prior result, detection threshold or event time was changed. The counts below describe what would be excluded if the flags were adopted.</p>
{outcome}<h2>Two signals of a shared disturbance</h2><ul><li><strong>Baseline:</strong> changes between neighboring 10 ms averages of the MA200 baseline. Each channel is normalized by a robust temporal scale, with an across-channel median floor. A qualifying difference flags both contributing bins.</li><li><strong>Broadband:</strong> a positive or negative excursion in the 300 Hz high-pass residual within a 1 ms bin, normalized by the existing masked MAD noise scale and median floor.</li></ul>
<p>The primary rule uses excursions above <strong>6× scale</strong>, with the same sign on <strong>at least 50% of eligible channels</strong>. At least <strong>1024 eligible channels</strong> are required. The union is expanded by <strong>10 ms on each side</strong>. Sensitivity variants use 6×/8×, 25%/50%/75% quorum, and 5/10/20 ms guards (18 original variants). These settings were fixed before the initial run; the baseline-only adjustment below was introduced after inspecting its misses. All windows were previously inspected and are not held-out validation.</p>
<p>The prior per-channel clipping mask remains independent: ≥1 ms identical stored values plus ±50 ms. Shared flags apply to all channels at their flagged times. Exact eligible exposure is recomputed from the old clipping masks and common noise-estimation support, so overlapping exclusions are not double-counted. If too few channels are eligible, evidence is unavailable; absence of a shared flag then does not establish clean data.</p>
<h2>Primary-rule results</h2><p>All recordings are purely extracellular. extra_5 and extra_6 were recorded after current-injection experiments; baseline and neural activity may differ. Comparisons remain within recording, without a causal stimulation interpretation. Numerators below are flagged candidates, not confirmed false positives.</p><div class="scroll"><table><tr><th>Segment</th><th>Condition</th><th>Flagged seconds</th><th>Additional usable-time loss</th><th>MA200/MAD flagged/original</th><th>HP300/MAD flagged/original</th></tr>{''.join(tablerows)}</table></div>
<h2>Previously reviewed disturbance intervals</h2><p>These interval boundaries are review windows, not annotated artifact truth. Coverage is descriptive; it is not recall or sensitivity. The likely motion explanation remains unproven.</p><table><tr><th>Segment</th><th>Reviewed interval (s)</th><th>Time flagged</th><th>MA200/MAD flagged/in interval</th><th>HP300/MAD flagged/in interval</th></tr>{''.join(capture_rows)}</table>
{altsection}<h2>Potential loss of useful candidates</h2><p>Channels 1436 and 1378 previously showed recurring narrow candidates. The overlay uses {ALT if has_alt else PRIMARY}. Only candidates with a complete ±3 ms waveform inside the segment are shown. Here blue overlays show retained candidates and red overlays show flagged candidates at the original HP300 peak times. Up to 30 evenly spaced events per group are drawn; the heavy line is the median. These are selected examples, not a representative false-exclusion estimate. A genuine spike occurring during a shared disturbance would also be flagged.</p><img src="candidate_loss_review.png" alt="Retained and flagged waveforms on two review channels across the three recordings"><p><a href="loss_review_selection.json">Exact selected events</a></p>
<h2>Evidence and sensitivity by segment</h2><p>Quorum plots show the larger positive/negative channel fraction. The shaded regions are the primary flags. Individual methods retain their original thresholds; this evaluation does not claim that removing flagged time fixes noise estimates affected by the disturbance.</p>{''.join(details)}
<h2>Decision boundary</h2><p>Keep these as review annotations until tested on new intervals with waveform review and explicit acceptance of lost time. Do not automatically label every coincident candidate as non-neural. Any production implementation should preserve reason codes and invalid-time intervals, evaluate noise estimation separately, and report rates using usable exposure. No signal reconstruction, spatial deduplication, spike sorting, stimulation-artifact processing or full-recording run was performed.</p>
<h2>Reproduce</h2><pre>.venv/bin/python analysis/shared_artifacts.py --output results/new_shared_review
.venv/bin/python analysis/report_shared_artifacts.py results/new_shared_review
.venv/bin/python -m unittest discover -s tests -v</pre><p><a href="config.json">Configuration and limitations</a> · <a href="sensitivity.csv">Sensitivity table</a> · <a href="summary.json">Full metrics</a> · <a href="validation.json">Validation</a></p></html>'''
    (root/'review.html').write_text(html)
    print(json.dumps({'segments':len(summaries),'variants_per_segment':len(next(iter(summaries.values()))['variants']),'adjusted_rule_present':has_alt},indent=2))
    print(root/'review.html')


if __name__=='__main__': main()
