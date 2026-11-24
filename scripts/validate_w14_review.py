"""Independent interval accounting, shared-flat diagnostics and raw focus audit."""
import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shank_input import ROOT,sha,channel_ids
from prepare_w14_inputs import SOURCE,SOURCE_SHA,save_json
sys.path.insert(0,str(ROOT))
from analysis.pilot import flat_mask,dilate


def run(output):
    if output.exists():raise ValueError('Fresh output required')
    inventory=ROOT/'results/extra4/w14-quality01';review=ROOT/'results/extra4/w14-review03'
    for folder in [inventory,review]:
        for name,digest in json.loads((folder/'manifest.json').read_text()).items():assert sha(folder/name)==digest
    rows=list(csv.DictReader((inventory/'channels.csv').open()));z=np.load(inventory/'intervals.npz')
    ids=channel_ids();N=3000000;shared=[];full_flat=[];full_guard=[]
    fig,ax=plt.subplots(3,1,figsize=(14,9),layout='constrained')
    for s in [1,2,3]:
        flat=z['flat'][z['flat'][:,0]==s];guard=z['guard'][z['guard'][:,0]==s]
        diffs=[]
        for spans in [flat,guard]:
            d=np.zeros(N+1,dtype=np.int32);np.add.at(d,spans[:,3].astype(int),1);np.add.at(d,spans[:,4].astype(int),-1);diffs.append(d[:-1].cumsum())
        fc,gc=diffs;np.testing.assert_array_equal(gc,z['guard_concurrency'][s-1]);full_flat.append(fc);full_guard.append(gc)
        for r in [r for r in rows if int(r['shank'])==s]:
            b=int(r['binary_channel']);assert int(r['global_channel'])==ids[s,b]
            exact=flat[flat[:,1]==b];pad=guard[guard[:,1]==b]
            assert int(r['flat_samples'])==int(sum(exact[:,4]-exact[:,3]))
            assert int(r['longest_flat_samples'])==int(np.max(exact[:,4]-exact[:,3],initial=0))
            assert int(r['guard_samples'])==int(sum(pad[:,4]-pad[:,3]))
            bins=np.zeros(300,dtype=np.int64)
            for a,e in pad[:,3:5].astype(int):
                for second in range(a//10000,(e-1)//10000+1):bins[second]+=max(0,min(e,(second+1)*10000)-max(a,second*10000))
            np.testing.assert_array_equal(bins,z['guard_by_nominal_second'][s-1,b])
            np.testing.assert_array_equal(bins.reshape(4,75).sum(1),json.loads(r['guarded_quarters']))
        def longest(mask):
            edges=np.flatnonzero(np.diff(np.r_[False,mask,False].astype(int)))
            return int(np.max(edges[1::2]-edges[::2],initial=0))
        shared.append(dict(shank=s,exact_flat_ge256_samples=int(sum(fc>=256)),padded_guard_ge256_samples=int(sum(gc>=256)),longest_shared_exact_flat_samples=longest(fc>=256),longest_shared_guard_samples=longest(gc>=256),maximum_exact_flat_channels=int(fc.max()),maximum_guard_channels=int(gc.max())))
        # Per-second maxima reveal short shared episodes without a 3M-point plot.
        ax[s-1].plot(np.arange(300),fc.reshape(300,10000).max(1),label='Exact-flat concurrency: per-second maximum')
        ax[s-1].plot(np.arange(300),gc.reshape(300,10000).max(1),label='Padded-guard concurrency: per-second maximum',alpha=.7)
        ax[s-1].axhline(256,color='gray',ls='--');ax[s-1].set(title=f'Shank{s}: shared activity diagnostic, no censoring',xlabel='Original nominal seconds',ylabel='Channels',ylim=(0,520));ax[s-1].legend(fontsize=8)
    focus=list(csv.DictReader((review/'focus_windows.csv').open()))
    with h5py.File(SOURCE,'r') as f:
        for r in focus:
            s,b,g=map(int,[r['shank'],r['binary_channel'],r['global_channel']]);x=f['signals'][g,:].astype('f4')
            expected=dilate(flat_mask(x,min_run=10),500)
            saved=np.zeros(N,bool)
            spans=z['guard'][(z['guard'][:,0]==s)&(z['guard'][:,1]==b)]
            for a,e in spans[:,3:5]:saved[a:e]=True
            np.testing.assert_array_equal(expected,saved)
            stat=next(row for row in rows if int(row['shank'])==s and int(row['binary_channel'])==b)
            assert float(stat['zero_fraction'])==np.count_nonzero(x==0)/N
            a,e=int(r['window_start']),int(r['window_stop'])
            with np.load(review/f'shank{s}_b{b}.npz') as w:
                np.testing.assert_array_equal(w['target'],x[a:e]);np.testing.assert_array_equal(w['neighbor'],f['signals'][int(r['neighbor_global']),a:e].astype('f4'))
    assert sha(SOURCE)==SOURCE_SHA
    output.mkdir(parents=True);fig.savefig(output/'shared_concurrency.png',dpi=120);plt.close(fig)
    save_json(output/'checks.json',dict(state='passed',all_channel_interval_totals_checked=1536,per_second_cells_checked=460800,focus_raw_and_legacy_masks_checked=len(focus),shared_diagnostics=shared,source_sha256=SOURCE_SHA,script_sha256=sha(Path(__file__))))
    save_json(output/'manifest.json',{p.name:sha(p) for p in output.iterdir()})
    print(json.dumps(shared,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if not a.output.resolve().is_relative_to(ROOT/'results'):raise ValueError('Project results path required')
    run(a.output)
