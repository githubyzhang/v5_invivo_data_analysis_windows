"""Audit the focused review and regenerate its page after visual annotations.

Optional assistant annotations are read from assistant_annotations.json in the
result folder. These are interpretations, never user labels or ground truth.
"""
import hashlib,json,re
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from analysis.focused_ma50_review import ROOT,CAL,OLD,NEW_STARTS,report
from analysis.pilot import write_csv


def main():
    protocol=json.loads((ROOT/'protocol.json').read_text());summaries=json.loads((ROOT/'summary.json').read_text())
    refs=json.loads((ROOT/'reference_manifest.json').read_text());events=json.loads((ROOT/'review_manifest.json').read_text())
    assert protocol['recordings']==[4,5] and protocol['excluded_recordings']==[6]
    for p,h in protocol['code_sha256'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
    for rec in [4,5]:assert hashlib.sha256((CAL/'references'/f'extra{rec}_calibration.npz').read_bytes()).hexdigest()==protocol['calibration_sha256'][str(rec)]
    annotation_path=ROOT/'assistant_annotations.json'
    annotations=json.loads(annotation_path.read_text()) if annotation_path.exists() else {}
    assert set(annotations)<=set(e['id'] for e in events)
    for e in events:
        if e['id'] in annotations:
            label,note=annotations[e['id']];assert label in ['plausible eAP','likely artifact','uncertain']
            e['assistant_label']=label;e['assistant_note']=note
        assert e['user_label']=='unreviewed'
    validations={};coverage=[]
    for name,s in summaries.items():
        rec=int(name[5]);assert rec in [4,5];start=int(name.split('_')[1])*10000
        folder=CAL/name if name in OLD else ROOT/'paired'/name
        d=np.load(folder/'thresholds.npz');model=np.load(CAL/'references'/f'extra{rec}_calibration.npz')
        np.testing.assert_array_equal(d['fixed'],model['thresholds'])
        assert not d['common_support'][~model['eligible']].any()
        for mode in ['adaptive','fixed']:
            a=np.loadtxt(folder/f'ma50_{mode}.csv',delimiter=',',skiprows=1,ndmin=2).reshape(-1,5)
            ch=a[:,0].astype(int);p=a[:,1].astype(int)-start
            assert np.isfinite(a).all() and ((p>=0)&(p<50000)).all()
            assert d['common_support'][ch,p//10000].all()
            expected=d['fixed'][0,ch] if mode=='fixed' else d['adaptive'][0,ch,p//10000]
            np.testing.assert_array_equal(a[:,3],expected);assert (a[:,2]>=expected).all()
            assert len(a)==s['metrics']['ma50_'+mode]['candidates']
            for c in np.unique(ch):assert (np.diff(a[ch==c,1])>=50).all()
        validations[name]={'fixed_calibration_unchanged':True,'counts_thresholds_support_spacing_valid':True,'reviewed_cards':sum(e['segment']==name for e in events)}
        if name not in OLD:
            prior_diag=np.load(ROOT/'detector'/name/'diagnostics.npz')
            np.testing.assert_array_equal(d['common_support'],prior_diag['common_support']&model['eligible'][:,None])
            seconds=prior_diag['usable_seconds']*model['eligible']
            np.testing.assert_allclose(seconds.sum(),s['usable_channel_seconds'],atol=1e-8)
            coverage.extend((name,ch,int(model['eligible'][ch]),float(seconds[ch])) for ch in range(2048))
            source=json.loads((ROOT/'detector'/name/'summary.json').read_text());st=Path(source['source']).stat()
            assert st.st_size==source['file_size_bytes'] and st.st_mtime_ns==source['file_mtime_ns']
    write_csv(ROOT/'per_channel_coverage.csv',['segment','channel_id','reference_eligible','paired_usable_seconds'],coverage)
    assert len(events)==len(set(e['id'] for e in events))
    (ROOT/'review_manifest.json').write_text(json.dumps(events,indent=2)+'\n')
    report(summaries,refs,events)
    html=(ROOT/'review.html').read_text().replace('<h2>New-interval comparison</h2>','<h2>New-interval comparison</h2><p><a href="per_channel_coverage.csv">Per-channel usable-time coverage for new intervals</a></p>')
    reference_note='<h2>Reference observations from this review</h2><p>The inspected extra_4 reference traces on channels 1436 and 1378 show relatively steady residual backgrounds with discrete negative events. Failed-reference examples have more raw baseline movement; this does not establish that their filtered signals are unusable. In extra_5, residual variability rises locally near 244–245 s in several displayed channels, including screened windows. This deserves user review before accepting those seconds as quiet calibration data. No reference windows or thresholds were changed in response.</p>'
    html=html.replace('<h2>New-interval comparison</h2>',reference_note+'<h2>New-interval comparison</h2>')
    html=html.replace('<h2>Waveform review</h2>','<h2>Waveform review</h2><p><b>Terminology:</b> shared candidates means detected by both threshold methods. It is separate from the shared20 disturbance-warning flag.</p>')
    (ROOT/'review.html').write_text(html)
    for link in re.findall(r'(?:src|href)="([^"]+)"',html):assert (ROOT/link).exists(),link
    validation={'segments':validations,'review_cards':len(events),'reference_views':len(refs),'user_labels_received':False,
        'interpretation':'Visual annotations are provisional, not performance labels; no default change.',
        'auditor_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (ROOT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps(validation,indent=2))

if __name__=='__main__':main()
