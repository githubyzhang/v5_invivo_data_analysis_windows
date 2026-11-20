"""Add descriptive comparisons and explicit failure review to the local QC report."""
import json
import os
from pathlib import Path
import sys
import warnings
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/invivo-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analysis.local_artifact_review import channel_flags


def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else 'results/local_artifact_review')
    s=json.loads((root/'summary.json').read_text()); distributions={}; examples=[]
    known={'extra6_90_95':[(1911,90.6992),(761,94.5509)],
           'extra6_240_245':[(1919,240.6709),(1591,240.4835),(1984,242.9163)]}
    for name in s:
        f=np.load(root/name/'features.npz')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',RuntimeWarning)
            med=np.nanmedian(np.where(f['eligible_bins'],f['fast_mad'],np.nan),axis=1)
        distributions[name]={'channel_median_hp_mad_quantiles':np.nanpercentile(med,[10,50,90]).tolist(),
                              'channel_1919_median_hp_mad':float(med[1919])}
        for ch,t in known.get(name,[]):
            masks=channel_flags(f['fast_mad'][ch],f['baseline'][ch],f['eligible_bins'][ch],
                                f['fast_reference'][ch],f['step_reference'][ch])
            p=round(t*10000)-s[name]['sample_start']
            examples.append({'segment':name,'channel_id':ch,'nominal_time_s':t,
                             'warnings':{k:bool(v[p]) for k,v in masks.items()}})
    ratio=distributions['extra6_240_245']['channel_1919_median_hp_mad']/distributions['extra4_30_35']['channel_1919_median_hp_mad']
    (root/'descriptive_comparison.json').write_text(json.dumps({'distributions':distributions,
        'channel_1919_late_extra6_over_early_extra4_ratio':ratio,'reviewed_examples':examples},indent=2)+'\n')
    fig,ax=plt.subplots(figsize=(10,4.5)); names=list(distributions)
    for i,name in enumerate(names):
        a,b,c=distributions[name]['channel_median_hp_mad_quantiles']
        ax.errorbar(i,b,yerr=[[b-a],[c-b]],fmt='o',capsize=5,color='#2563ad')
        ax.scatter(i,distributions[name]['channel_1919_median_hp_mad'],marker='x',color='#c45d22')
    ax.set_xticks(range(len(names)),names,rotation=15);ax.set_yscale('log')
    ax.set_ylabel('HP300 bin MAD, stored float units')
    ax.set_title('Within-channel median across eligible 10 ms bins\nBlue: across-channel median and 10–90% range; orange: channel 1919')
    ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(root/'scale_comparison.png',dpi=140);plt.close(fig)
    outcome=f'''<h2>Observed outcome: insufficient for automatic cleanup</h2><p>The fast warning flags 12 of 41,643 HP300/MAD candidates in extra6_240_245, including 7 outside the shared 20 ms guard. It adds 2.288 channel-seconds of warning coverage outside that guard. The other four intervals have no local warnings on usable samples. Step and low-variability rules add no warnings in any tested interval.</p><p>The previously reviewed step-like candidate times on ch 1911 (90.6992 s), ch 1919 (240.6709 s), and ch 1591 (240.4835 s) remain unflagged. None of the original candidates on review channels 1436 and 1378 is flagged. This preserves those examples but does not demonstrate sensitivity or accuracy.</p><p>Persistent variability is a key limitation: channel 1919's median HP300 bin MAD is {ratio:.1f}× larger in extra6_240_245 than extra4_30_35. This describes signal variability, including potential neural contributions; it is not a measurement of pure artifact or evidence of a particular mechanism. The within-segment reference also rises, making a relative burst rule insensitive to persistently abnormal channels.</p><img src="scale_comparison.png"><p><b>Decision:</b> retain these as optional exploratory annotations only. Do not enable automatic removal or claim restored eAPs. A next assessment should focus on persistent channel quality over longer reference periods and manually reviewed waveform examples, rather than simply reducing these thresholds. Saturated information cannot be recovered by these masks. No threshold was retuned in response to these results.</p>'''
    p=root/'review.html';html=p.read_text();marker='<h2>Observed outcome: insufficient for automatic cleanup</h2>'
    if marker not in html: html=html.replace('<h2>Independent channel warnings</h2>',outcome+'<h2>Independent channel warnings</h2>')
    p.write_text(html)
    print(json.dumps({'channel_1919_ratio':ratio,'reviewed_examples':examples},indent=2))

if __name__=='__main__': main()
