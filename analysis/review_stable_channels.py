"""Review repeated candidates on relatively low-baseline-excursion channels.

Selection is deterministic and biased for review, not an accuracy sample.
"""
import os
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/invivo-matplotlib')
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analysis.compare_detectors import residuals, CONTEXT, FS


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('results',type=Path)
    root=ap.parse_args().results
    selections={}
    for rec in [4,5,6]:
        segment=root/f'extra{rec}_60_65'
        s=json.loads((segment/'summary.json').read_text())
        d=np.load(segment/'diagnostics.npz')
        a=np.loadtxt(segment/'hp300_mad.csv',delimiter=',',skiprows=1,ndmin=2)
        if not a.size: a=np.empty((0,4))
        counts=np.bincount(a[:,0].astype(int),minlength=2048)
        span=np.ptp(d['baseline_bins'],axis=1)
        eligible=np.flatnonzero((counts>=10)&(d['guard_samples']==0)&d['common_support'].all(axis=1))
        if len(eligible)==0:
            selections[f'extra{rec}']={'channels':[],'reason':'No channels satisfy the review eligibility rule.'}
            continue
        cutoff=float(np.median(span[eligible]))
        low=eligible[span[eligible]<=cutoff]
        chosen=low[np.lexsort((low,-counts[low]))][:2]
        selection={'rule':'At least 10 HP300/MAD candidates, no flat guards, all windows usable; baseline-bin span at or below median among eligible channels; choose two highest-count channels.',
                   'eligible_channels':len(eligible),'baseline_span_cutoff':cutoff,'channels':[]}
        fig,axes=plt.subplots(len(chosen),3,figsize=(15,3.5*len(chosen)),squeeze=False)
        with h5py.File(s['source'],'r') as f:
            ds=f['signals']
            for row,ch in enumerate(chosen):
                start,stop=s['sample_start'],s['sample_stop']
                raw=ds[ch,start-CONTEXT:stop+CONTEXT].astype(float)
                ys=residuals(raw)
                x=raw[CONTEXT:-CONTEXT]
                ys={k:v[CONTEXT:-CONTEXT] for k,v in ys.items()}
                p=a[a[:,0]==ch,1].astype(int)-start
                p=p[(p>=30)&(p<len(x)-30)]
                # Evenly spaced in event order; deterministic maximum 30 overlays.
                p=p[np.unique(np.linspace(0,len(p)-1,min(30,len(p))).astype(int))]
                tt=np.arange(-30,31)/FS*1000
                ax=axes[row,0]
                t=(start+np.arange(len(x)))/FS
                ax.plot(t,x,lw=.35,color='#617b8e')
                ax.plot(t,x-ys['ma200'],lw=.8,color='#bd841d')
                ax.set_title(f'Ch {ch}: stored signal + MA200 baseline')
                ax.set_xlabel('Nominal recording time (s)')
                for col,method,color in [(1,'ma200','#276d98'),(2,'hp300','#b84b41')]:
                    waves=np.array([ys[method][i-30:i+31] for i in p])
                    ax=axes[row,col]
                    ax.plot(tt,waves.T,color=color,alpha=.18,lw=.7)
                    ax.plot(tt,np.median(waves,axis=0),color=color,lw=2)
                    ax.set_title(f'{method}: same {len(p)} HP-selected events')
                    ax.set_xlabel('Time from HP300 peak (ms)')
                for ax in axes[row]:
                    ax.set_ylabel('Stored float units'); ax.grid(alpha=.2)
                selection['channels'].append({'channel_id':int(ch),'hp300_mad_candidate_count':int(counts[ch]),
                                               'baseline_span_stored_units':float(span[ch]),
                                               'overlay_sample_indices':(p+start).tolist()})
        fig.suptitle(f'extra_{rec}, 60–65 s: relatively low baseline excursion — selected examples, not validated units',fontsize=13)
        fig.tight_layout(rect=(0,0,1,.95)); fig.savefig(segment/'stable_waveforms.png',dpi=140); plt.close(fig)
        selections[f'extra{rec}']=selection
    (root/'stable_channel_selection.json').write_text(json.dumps(selections,indent=2)+'\n')
    print(json.dumps(selections,indent=2))


if __name__=='__main__': main()
