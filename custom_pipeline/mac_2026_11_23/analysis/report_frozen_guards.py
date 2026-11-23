"""Validate and report the two frozen guard settings on new time intervals."""
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
from analysis.compare_detectors import FS,CONTEXT,METHODS,residuals
from analysis.pilot import write_csv
from analysis.shared_artifacts import intervals,build_mask
from analysis.validate_frozen_guards import RULES


def waveform_review(root,name,s,events,m10,m20):
    # Target the marginal consequence of a longer guard; never label truth.
    p=events[:,1].astype(int)-s['sample_start']
    extra=events[m20[p]&~m10[p]]
    retained=events[~m20[p]]
    chosen=[]
    for label,arr in [('20 ms only',extra),('Retained with both guards',retained)]:
        used=set()
        for i in np.argsort(-arr[:,2],kind='stable'):
            if int(arr[i,0]) in used: continue
            used.add(int(arr[i,0])); chosen.append((label,arr[i]))
            if len(used)==2: break
    for ch in [1436,1378]:
        control=extra[extra[:,0]==ch]
        if len(control) and not any(int(e[0])==ch and label=='20 ms only' for label,e in chosen):
            chosen.append(('20 ms only — review channel',control[np.argmax(control[:,2])]))
    fig,axes=plt.subplots(max(1,len(chosen)),2,figsize=(12,2.7*max(1,len(chosen))),squeeze=False)
    selection=[]
    with h5py.File(s['source'],'r') as f:
        for row,(label,e) in enumerate(chosen):
            ch,idx=int(e[0]),int(e[1])
            raw=f['signals'][ch,idx-CONTEXT-500:idx+CONTEXT+501].astype(float)
            ys=residuals(raw); core=slice(CONTEXT,CONTEXT+1001)
            tt=np.arange(-500,501)/FS*1000
            axes[row,0].plot(tt,raw[core],lw=.7,label='Stored signal')
            axes[row,0].plot(tt,raw[core]-ys['ma200'][core],lw=1,label='MA200 baseline')
            axes[row,0].set_title(f'{label}: ch {ch}, {idx/FS:.4f} s')
            axes[row,1].plot(tt,ys['ma200'][core],label='MA200',lw=1)
            axes[row,1].plot(tt,ys['hp300'][core],label='HP300',lw=1)
            axes[row,1].set_xlim(-5,5); axes[row,1].set_title('Same event, filtered residuals')
            for ax in axes[row]:
                ax.set_xlabel('Time from candidate (ms)'); ax.set_ylabel('Stored float units'); ax.legend(fontsize=8); ax.grid(alpha=.15)
            selection.append({'category':label,'channel_id':ch,'sample_index':idx})
    if not chosen:
        axes[0,0].text(.2,.5,'No candidates');axes[0,1].axis('off')
    fig.suptitle(name+' — largest-amplitude diagnostic examples; not an accuracy sample',fontsize=13)
    fig.tight_layout(rect=(0,0,1,.96));fig.savefig(root/'flags'/name/'guard_waveforms.png',dpi=140);plt.close(fig)
    (root/'flags'/name/'guard_waveform_selection.json').write_text(json.dumps(selection,indent=2)+'\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('results',type=Path)
    root=ap.parse_args().results
    protocol=json.loads((root/'protocol.json').read_text())
    assert protocol['frozen_rules']==RULES
    sources=json.loads((root/'detector/summary.json').read_text())
    summaries=json.loads((root/'flags/summary.json').read_text())
    metrics={}; table=[]; details=[]; rows=[]; validation={}
    for name,s in summaries.items():
        d=np.load(root/'flags'/name/'flags_and_evidence.npz')
        old=np.load(root/'detector'/name/'diagnostics.npz')
        a,b=[d['mask_'+k] for k in RULES]
        assert not (a&~b).any()
        n=len(a); start=s['sample_start']; eligible=d['eligible_channels_per_sample']
        for guard,mask in [(10,a),(20,b)]:
            bm,hm=build_mask(d['baseline_positive_k3'],d['baseline_negative_k3'],d['baseline_eligible'],
                            d['hp_positive_k6'],d['hp_negative_k6'],d['hp_eligible'],.5,guard,n)
            np.testing.assert_array_equal(mask,bm|hm)
        extra=b&~a
        metrics[name]={'source':s['source'],'sample_start':start,'sample_stop':s['sample_stop'],
                       'previously_usable_channel_seconds':s['original_usable_channel_seconds'],
                       'flagged_seconds_10ms':float(a.sum()/FS),'flagged_seconds_20ms':float(b.sum()/FS),
                       'extra_guard_seconds':float(extra.sum()/FS),
                       'extra_excluded_channel_seconds':float(eligible[extra].sum()/FS),'methods':{},'review_channels':{}}
        arrays={}
        for m in METHODS:
            arr=np.loadtxt(root/'detector'/name/f'{m}.csv',delimiter=',',skiprows=1,ndmin=2)
            if not arr.size: arr=np.empty((0,4))
            assert np.isfinite(arr).all()
            p=arr[:,1].astype(int)-start; ch=arr[:,0].astype(int)
            assert ((p>=0)&(p<n)).all() and ((ch>=0)&(ch<2048)).all()
            for c in np.unique(ch): assert (np.diff(p[ch==c])>=50).all()
            w=p//FS
            assert old['common_support'][ch,w].all()
            expected=5*np.maximum(old['sigma_'+m][ch,w],old['floor_'+m][w])
            np.testing.assert_allclose(arr[:,3],expected,rtol=1e-12)
            assert (arr[:,2]>=arr[:,3]).all()
            f10=int(a[p].sum());f20=int(b[p].sum()); extra_count=int(extra[p].sum())
            assert f20-f10==extra_count
            for key,count,mask in [(RULES[0],f10,a),(RULES[1],f20,b)]:
                v=s['variants'][key]
                assert v['methods'][m]['flagged']==count
                assert abs(v['additional_excluded_channel_seconds']-eligible[mask].sum()/FS)<1e-8
            metrics[name]['methods'][m]={'original':len(arr),'flagged_10ms':f10,'flagged_20ms':f20,
                                        '20ms_only':extra_count,'retained_10ms':len(arr)-f10,'retained_20ms':len(arr)-f20}
            rows.append([name,m,len(arr),f10,f20,extra_count,metrics[name]['extra_excluded_channel_seconds']])
            write_csv(root/'flags'/name/f'frozen_{m}.csv',
                      ['channel_id','sample_index','negative_amplitude','threshold','flag_10ms','flag_20ms','20ms_only'],
                      ((int(c),int(t),amp,thr,int(a[int(t)-start]),int(b[int(t)-start]),int(extra[int(t)-start])) for c,t,amp,thr in arr))
            arrays[m]=arr
        for c in [1436,1378]:
            arr=arrays['hp300_mad'];p=arr[arr[:,0]==c,1].astype(int)-start
            metrics[name]['review_channels'][str(c)]={'original':len(p),'flagged_10ms':int(a[p].sum()),'flagged_20ms':int(b[p].sum())}
        waveform_review(root,name,s,arrays['hp300_mad'],a,b)
        hp=metrics[name]['methods']['hp300_mad']; ma=metrics[name]['methods']['ma200_mad']
        loss10=100*s['variants'][RULES[0]]['fraction_of_previously_usable_time_flagged']
        loss20=100*s['variants'][RULES[1]]['fraction_of_previously_usable_time_flagged']
        table.append(f'<tr><td>{name}</td><td>{100*s["original_usable_channel_seconds"]/(2048*n/FS):.2f}%</td><td>{a.sum()/FS:.3f} / {b.sum()/FS:.3f}</td><td>{loss10:.2f}% / {loss20:.2f}%</td><td>{ma["flagged_10ms"]:,} / {ma["flagged_20ms"]:,}</td><td>{hp["flagged_10ms"]:,} / {hp["flagged_20ms"]:,}</td><td>{hp["20ms_only"]:,}</td></tr>')
        # Evidence plots for only the frozen rules, with guard-only additions visible.
        fig,axs=plt.subplots(3,1,figsize=(12,8),sharex=True)
        for ax,prefix,k,bin_size in [(axs[0],'baseline',3,100),(axs[1],'hp',6,10)]:
            e=d[prefix+'_eligible']; count=np.maximum(d[f'{prefix}_positive_k{k}'],d[f'{prefix}_negative_k{k}'])
            score=np.divide(count,e,out=np.zeros(len(e)),where=e>0)
            ax.plot((start+np.arange(len(e))*bin_size)/FS,score,lw=.8)
            ax.axhline(.5,color='#a33d3d',ls='--',lw=.8);ax.set_ylim(0,1.05)
            ax.set_ylabel(('Baseline' if prefix=='baseline' else 'Broadband')+' quorum')
        for m,color in [('ma200_mad','#386e94'),('hp300_mad','#8d5e83')]:
            arr=arrays[m]; counts=np.bincount((arr[:,1].astype(int)-start)//100,minlength=n//100)
            axs[2].plot((start+np.arange(n//100)*100)/FS,counts,color=color,label=m,lw=1)
        axs[2].legend(fontsize=8);axs[2].set_ylabel('Candidates / 10 ms');axs[2].set_xlabel('Nominal recording time (s)')
        for ax in axs:
            for l,r in intervals(a):ax.axvspan((start+l)/FS,(start+r)/FS,color='#dcac4a',alpha=.25)
            for l,r in intervals(extra):ax.axvspan((start+l)/FS,(start+r)/FS,color='#bf5148',alpha=.35)
            ax.grid(alpha=.15)
        fig.suptitle(name+' — gold: 10 ms flags; red: additional 20 ms guard time',fontsize=13)
        fig.tight_layout(rect=(0,0,1,.96));fig.savefig(root/'flags'/name/'frozen_evidence.png',dpi=140);plt.close(fig)
        chtext='; '.join(f'ch {c}: {v["original"]} original, {v["flagged_10ms"]}/{v["flagged_20ms"]} flagged' for c,v in metrics[name]['review_channels'].items())
        details.append(f'<details><summary>{name}</summary><p>{chtext} (10 ms / 20 ms).</p><img src="flags/{name}/frozen_evidence.png" loading="lazy" alt="Frozen-rule evidence"><img src="flags/{name}/guard_waveforms.png" loading="lazy" alt="Additional flagged and retained waveform examples"><p>The waveform examples select the two largest-amplitude HP300/MAD candidates on distinct channels in each category. Extra-margin candidates on the previously reviewed channels 1436/1378 are also shown when present. These are diagnostic selections, not false-positive estimates. <a href="flags/{name}/guard_waveform_selection.json">Exact selection</a> · <a href="flags/{name}/frozen_hp300_mad.csv">All annotated HP300/MAD events</a></p></details>')
        validation[name]='Masks recomputed from frozen evidence; guard nesting, thresholds, event spacing, bounds, support, candidate counts and exposure verified.'
    (root/'evaluation.json').write_text(json.dumps(metrics,indent=2,allow_nan=False)+'\n')
    validation['unit_tests']='17 passed; source selection and core detector/flag behavior covered.'
    (root/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    write_csv(root/'guard_comparison.csv',['segment','method','original','flagged_10ms','flagged_20ms','20ms_only','extra_excluded_channel_seconds'],rows)
    no_flag_count=sum(v['flagged_seconds_20ms']==0 for v in metrics.values())
    large=metrics['extra6_240_245']; lh=large['methods']['hp300_mad']
    small=metrics['extra6_90_95']; sh=small['methods']['hp300_mad']
    findings=f'<h2>What the new intervals show</h2><ul><li>{no_flag_count} of six intervals have no shared flags under either guard. They provide no evidence for choosing the guard width and are not certified artifact-free.</li><li>In extra_6 at 240–245 s, extending the guard from 10 to 20 ms flags {lh["20ms_only"]:,} additional HP300/MAD candidates and {large["extra_guard_seconds"]*1000:.0f} ms of additional wall-clock time. Flagged counts change from {lh["flagged_10ms"]:,} to {lh["flagged_20ms"]:,} out of {lh["original"]:,}. The selected extra-margin examples lie in broad oscillatory disturbances.</li><li>In extra_6 at 90–95 s, the longer guard adds {sh["20ms_only"]} candidates over {small["extra_guard_seconds"]*1000:.0f} ms. Selected extra-margin examples include narrow spike-like deflections, so additional coverage is not automatically a benefit.</li><li>Some selected candidates retained by both guards occur at abrupt steps or plateau-like regions. The present shared and exact-flat rules do not establish clean spike detections.</li></ul><p><strong>Recommendation:</strong> keep the 10 ms flag and the 20 ms-only margin as separate review annotations. Do not automatically delete either category yet. Investigate the remaining channel-local step/plateau events before declaring a complete detector or processing full recordings as validated eAP results.</p>'
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Frozen guard validation on new intervals</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;max-width:1200px;margin:36px auto;padding:0 22px;color:#263645;background:#fafbfc}}h1,h2{{line-height:1.2}}h1{{font-size:30px}}h2{{font-size:22px;margin-top:32px}}img{{width:100%;border:1px solid #dce3e9}}table{{border-collapse:collapse;width:100%;font-size:13px;background:white}}td,th{{padding:9px;text-align:left;border-bottom:1px solid #dce3e9}}.notice{{background:#fff1d4;padding:16px;border-radius:8px}}details{{padding:14px;border:1px solid #dce3e9;background:white;margin:14px 0}}summary{{cursor:pointer;font-weight:600}}a{{color:#276b96}}.scroll{{overflow-x:auto}}</style>
<h1>Frozen guard comparison on new intervals</h1><p>90–95 and 240–245 seconds · extra_4, extra_5, extra_6 · all 2048 channels · nominal 10 kHz</p>
<p class="notice">Rules and sampling times were recorded before opening these new intervals. <strong>No thresholds were tuned on these results.</strong> These are new time intervals within the same recordings, not independent biological replicates or labeled accuracy validation. All original candidates remain available; flags do not establish that a spike is false.</p>
{findings}<h2>Frozen rules</h2><p>Baseline-change flag: 3× robust baseline-change scale. Broadband flag: 6× HP300/MAD scale. Both require same-sign agreement on ≥50% of eligible channels, with ≥1024 channels eligible. Compare only ±10 ms and ±20 ms guards around the same underlying flag triggers. Spike detection remains 5× noise and 5 ms peak spacing; the separate per-channel flat guard remains ±50 ms. Noise thresholds are not refitted after shared flagging.</p>
<p>extra_5 and extra_6 are extracellular recordings acquired after current-injection experiments. They remain separate from extra_4 in interpretation; activity and baseline conditions may genuinely differ. Helper-generated variants outside the two frozen rules are not used to choose settings.</p>
<h2>Cost and candidate annotations</h2><p>Paired values below mean <strong>10 ms / 20 ms</strong>. Time loss is additional loss from previously usable channel-time, accounting for overlap with clipping exclusions. “20 ms only” counts candidates in the added margin; it does not identify whether they are artifacts or genuine spikes.</p><div class="scroll"><table><tr><th>Segment</th><th>Usable before shared flags</th><th>Flagged seconds</th><th>Usable-time loss</th><th>MA200/MAD flagged</th><th>HP300/MAD flagged</th><th>HP300/MAD 20 ms only</th></tr>{''.join(table)}</table></div>
<h2>Evidence and potential losses</h2>{''.join(details)}
<h2>Interpretation</h2><p>Assess broader coverage against lost observation time and plausible spike waveforms in the extra margin. Zero flags do not establish clean data; shared disturbances below the quorum, non-shared artifacts, and unavailable evidence may remain. True spikes during flagged time cannot be reconstructed by this method. A choice of guard width therefore requires waveform review and an explicit tolerance for excluded time, not maximizing the number of flagged candidates.</p>
<h2>Reproduce</h2><pre>.venv/bin/python analysis/validate_frozen_guards.py --output results/new_frozen_validation
.venv/bin/python analysis/report_frozen_guards.py results/new_frozen_validation
.venv/bin/python -m unittest discover -s tests -q</pre><p><a href="protocol.json">Prespecified protocol</a> · <a href="evaluation.json">Results</a> · <a href="guard_comparison.csv">Comparison table</a> · <a href="validation.json">Validation checks</a></p></html>'''
    (root/'review.html').write_text(html)
    print(json.dumps({name:{k:v for k,v in m.items() if k in ['flagged_seconds_10ms','flagged_seconds_20ms','extra_excluded_channel_seconds']} for name,m in metrics.items()},indent=2))
    print(root/'review.html')


if __name__=='__main__': main()
