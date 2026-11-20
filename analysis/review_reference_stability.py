"""Summarize fixed-reference stability and audit saved paired detections."""
import hashlib,json,os,re,sys
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/invivo-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analysis.fixed_reference_thresholds import ROOT,REFS,FILTERS


def main():
    root=ROOT;protocol=json.loads((root/'protocol.json').read_text());summaries=json.loads((root/'summary.json').read_text())
    for p,h in protocol['source_sha256'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
    for s in protocol['source_metadata'].values():
        st=Path(s['path']).stat();assert st.st_size==s['size'] and st.st_mtime_ns==s['mtime_ns']
    audit={};rows=[];fig,axes=plt.subplots(1,3,figsize=(13,4))
    for ax,rec in zip(axes,REFS):
        d=np.load(root/'references'/f'extra{rec}_calibration.npz');ok=d['eligible']
        q=np.percentile(d['segment_ratio'][:,ok],[50,90,100],axis=1) if ok.any() else np.full((3,3),np.nan)
        audit[str(rec)]={'eligible_channels':int(ok.sum()),'reference_ratio_quantiles_50_90_100':q.tolist()}
        for fi,fil in enumerate(FILTERS):
            vals=np.sort(d['segment_ratio'][fi,ok]);ax.plot(vals,np.arange(1,len(vals)+1)/max(1,len(vals)),label=fil)
            rows.append(f'<tr><td>extra_{rec}</td><td>{fil}</td><td>{q[0,fi]:.3f}</td><td>{q[1,fi]:.3f}</td><td>{q[2,fi]:.3f}</td></tr>')
        ax.set_title(f'extra_{rec}: {ok.sum()} eligible channels');ax.set_xlabel('Largest / smallest reference-segment MAD');ax.set_ylabel('Fraction of eligible channels');ax.legend();ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(root/'stability.png',dpi=140);plt.close(fig)
    for name,s in summaries.items():
        rec=int(name[5]);start=int(name.split('_')[1])*10000
        d=np.load(root/name/'thresholds.npz');model=np.load(root/'references'/f'extra{rec}_calibration.npz')
        np.testing.assert_array_equal(d['fixed'],model['thresholds'])
        for fi,fil in enumerate(FILTERS):
            for mode in ['adaptive','fixed']:
                arr=np.loadtxt(root/name/f'{fil}_{mode}.csv',delimiter=',',skiprows=1,ndmin=2).reshape(-1,5)
                assert np.isfinite(arr).all();ch=arr[:,0].astype(int);p=arr[:,1].astype(int)-start
                assert ((p>=0)&(p<50000)).all();assert d['common_support'][ch,p//10000].all()
                expected=d['fixed'][fi,ch] if mode=='fixed' else d['adaptive'][fi,ch,p//10000]
                np.testing.assert_array_equal(arr[:,3],expected);assert (arr[:,2]>=expected).all()
                assert len(arr)==s['metrics'][fil+'_'+mode]['candidates']
    audit['checks']='Source code hashes and source size/mtime verified; all event thresholds, support, sample bounds and counts verified; fixed thresholds identical across targets.'
    (root/'validation.json').write_text(json.dumps(audit,indent=2)+'\n')
    html=(root/'review.html').read_text();block='<h2>Measured reference stability</h2><p><b>Visual limitation:</b> the screened extra_6 reference example on channel 1919 still contains large fast fluctuations, despite passing the consistency gate. Stability does not certify a quiet reference. Treat the extra_6 fixed-threshold results as a diagnostic experiment, not an approved calibration. Review channels 1436 and 1378 fail the all-filter stability gate in extra_6 and are absent from its paired detections; zero counts there do not mean neural silence.</p><p>These ratios use raw reference MAD estimates before any across-channel floor. A ratio of 1.05 means the largest accepted segment estimate is 5% above the smallest. Only eligible channels appear here: rejected channels and unobserved times are not evidence of stability.</p><table><tr><th>Recording</th><th>Filter</th><th>Median ratio</th><th>90th percentile</th><th>Maximum</th></tr>'+''.join(rows)+'</table><img src="stability.png"><p>Stability among screened intervals supports testing fixed thresholds for these channels; it does not prove constant noise throughout the recording. <a href="validation.json">Validation and numerical summaries</a></p>'
    if '<h2>Measured reference stability</h2>' not in html:html=html.replace('<h2>Matched comparison</h2>',block+'<h2>Matched comparison</h2>')
    if '<h2>Decision from this round</h2>' not in html:
        outcome='<h2>Decision from this round</h2><p>Fixed references are feasible for the screened extra_4/extra_5 subsets, but their benefit is not yet validated. In extra_6, fixed thresholds expose many additional crossings, including broad, disturbed waveforms in the reviewed examples. They do not remove fast noise. Keep this experiment optional; review the selected references before adopting a calibration.</p>'
        outcome+='<p>MA50 adaptive → fixed candidate counts on identical support: '+ '; '.join(f'{name}: {v["metrics"]["ma50_adaptive"]["candidates"]:,} → {v["metrics"]["ma50_fixed"]["candidates"]:,}' for name,v in summaries.items())+'. These are candidates, not validated eAP counts.</p>'
        html=html.replace('<h2>Reference selection and stability</h2>',outcome+'<h2>Reference selection and stability</h2>')
    (root/'review.html').write_text(html)
    for link in re.findall(r'(?:src|href)="([^"]+)"',html):assert (root/link).exists(),link
    print(json.dumps(audit,indent=2))

if __name__=='__main__':main()
