"""Finalize W12 rate overview layout; preserve all numerical artifacts."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from review_w9_good import ROOT,verify
from review_pilot_round1 import sha


def run(report):
    report=report.resolve()
    if not report.is_relative_to(ROOT/'results/extra4_shank0') or (report/'plot_finalization.json').exists():
        raise ValueError('Fresh local finalization required')
    verify(report,'report-manifest.json')
    with np.load(report/'rate_bins.npz') as z:
        rate=z['nominal_rates'];ids=z['cluster_ids']
    # Fixed left margin avoids the clipped y labels seen with constrained layout.
    fig,ax=plt.subplots(figsize=(14,6));fig.subplots_adjust(left=.10,right=.89,bottom=.15,top=.89)
    im=ax.imshow(rate,aspect='auto',origin='lower',extent=(0,300,-.5,len(ids)-.5))
    with np.load(ROOT/'results/extra4_shank0/w11-exposure-review01/global_intervals.npz') as z:
        for a,b in z['active_guard_ge50']:ax.axvspan(a/10000,b/10000,color='red',alpha=.2)
        for a,b in z['broad_warning']:ax.axvline(a/10000,color='purple',alpha=.45,lw=.7)
        last=0
        for a,b in z['broad_available']:
            if a>last:ax.axvspan(last/10000,a/10000,color='gray',alpha=.2)
            last=b
        if last<3000000:ax.axvspan(last/10000,300,color='gray',alpha=.2)
    ax.set_yticks(np.arange(len(ids)),labels=[str(c) for c in ids]);ax.set_ylim(-.5,len(ids)-.5)
    ax.set(xlabel='Original nominal seconds (10-second bins)',ylabel='Without-248 cluster ID',title='Rate overview; matching first/last-bin exposure, no quality censoring')
    fig.colorbar(im,ax=ax,label='Events / retained nominal second',fraction=.035,pad=.025)
    fig.savefig(report/'rates.png',dpi=130,bbox_inches='tight');plt.close(fig)
    (report/'plot_finalization.json').write_text(json.dumps(dict(script_sha256=sha(Path(__file__)),change='Rate overview margin/labels only; numerical tables unchanged'),indent=2)+'\n')
    (report/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in report.iterdir() if p.is_file() and p.name!='report-manifest.json'},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True)
    run(p.parse_args().report)
