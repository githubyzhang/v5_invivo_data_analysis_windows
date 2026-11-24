"""Summarize all-channel W14 inventory and plot bounded raw/neighbor evidence."""
import argparse
import csv
import html
import json
from pathlib import Path
import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Arial"
from shank_input import ROOT,sha,channel_ids
from prepare_w14_inputs import SOURCE,SOURCE_SHA,save_json,save_csv


def run(inventory,inputs,output):
    if output.exists() or not output.resolve().is_relative_to(ROOT/'results'):
        raise ValueError('Fresh project result path required')
    for folder in [inventory,inputs]:
        for name,digest in json.loads((folder/'manifest.json').read_text()).items():assert sha(folder/name)==digest,name
    with (inventory/'channels.csv').open() as f:rows=list(csv.DictReader(f))
    intervals=np.load(inventory/'intervals.npz');ids=channel_ids();output.mkdir(parents=True)
    figures=[];focus=[];stats=[]
    with h5py.File(SOURCE,'r') as f:
        for s in (1,2,3):
            channels=[r for r in rows if int(r['shank'])==s]
            guard=np.array([float(r['guard_fraction']) for r in channels]);std=np.array([float(r['std']) for r in channels])
            order=np.argsort(guard)[::-1];chosen=order[:(4 if s==2 else 3)]
            stats.append(dict(shank=s,maximum_guard_fraction=float(guard.max()),median_guard_fraction=float(np.median(guard)),channels_guard_over_1_percent=int(sum(guard>.01)),channels_guard_over_5_percent=int(sum(guard>.05)),channels_guard_over_10_percent=int(sum(guard>.10)),minimum_std=float(std.min()),maximum_std=float(std.max()),shared_guard_ge256_samples=int(sum(intervals['guard_concurrency'][s-1]>=256))))
            fig,ax=plt.subplots(1,3,figsize=(18,8));fig.subplots_adjust(left=.05,right=.97,bottom=.10,top=.93,wspace=.65)
            im=ax[0].imshow(guard.reshape(128,4)*100,origin='lower',aspect='auto');fig.colorbar(im,ax=ax[0],label='Guard %')
            ax[0].set(title=f'Shank{s}: padded flat guards',xlabel='Physical column',ylabel='Physical row')
            im=ax[1].imshow(std.reshape(128,4)*1e6,origin='lower',aspect='auto');fig.colorbar(im,ax=ax[1],label='Input std x1e6')
            ax[1].set(title='Raw standard deviation',xlabel='Physical column',ylabel='Physical row')
            im=ax[2].imshow(intervals['guard_by_nominal_second'][s-1]/100,origin='lower',aspect='auto',extent=(0,300,-.5,511.5));fig.colorbar(im,ax=ax[2],label='Guard % per second')
            ax[2].set(title='All 512 channels; diagnostic only',xlabel='Original nominal seconds',ylabel='Binary channel')
            name=f'shank{s}_overview.png';fig.savefig(output/name,dpi=120,bbox_inches='tight');plt.close(fig);figures.append(name)
            for b in chosen:
                b=int(b);g=int(ids[s,b]);x=f['signals'][g,:].astype('f4');r=channels[b]
                spatial=np.column_stack((np.arange(512)%4,np.arange(512)//4));dist=((spatial-spatial[b])**2).sum(1)
                neighbor=int(np.argsort(dist,kind='stable')[1]);ng=int(ids[s,neighbor])
                flat=intervals['flat'];spans=flat[(flat[:,0]==s)&(flat[:,1]==b)]
                longest=spans[np.argmax(spans[:,4]-spans[:,3])];a,z=map(int,longest[3:5]);left=max(0,a-2000);right=min(len(x),a+8000)
                y=f['signals'][ng,left:right].astype('f4')
                fig,ax=plt.subplots(2,2,figsize=(14,9));fig.subplots_adjust(left=.08,right=.98,bottom=.08,top=.85,hspace=.40,wspace=.28)
                second=x.reshape(300,10000)
                ax[0,0].fill_between(np.arange(300),second.min(1)*1e6,second.max(1)*1e6,alpha=.5)
                ax[0,0].plot(np.arange(300),np.median(second,axis=1)*1e6,color='black',lw=.8)
                ax[0,0].set(title='One-second min/max envelope and median',xlabel='Original nominal seconds',ylabel='Input x1e6')
                ax[0,1].plot(np.arange(300),intervals['guard_by_nominal_second'][s-1,b]/100)
                ax[0,1].set(title='Padded guard fraction; not unusable-time estimate',xlabel='Original nominal seconds',ylabel='Guard %',ylim=(-2,102))
                axis=np.arange(left,right)/10000
                for panel,trace,label in [(ax[1,0],x[left:right],f'b{b}/global{g}'),(ax[1,1],y,f'nearest b{neighbor}/global{ng}')]:
                    panel.plot(axis,trace*1e6,lw=.7);panel.axvspan(a/10000,min(z,right)/10000,color='red',alpha=.18)
                    panel.set(title=label+' around longest-flat onset',xlabel='Original nominal seconds',ylabel='Input x1e6')
                fig.suptitle(f'Shank{s} b{b} / global{g}: zero {float(r["zero_fraction"]):.2%}, guard {float(r["guard_fraction"]):.2%}\nRed marks target exact-flat interval only. Numerical scaling, not calibrated microvolts; neighbor view is bounded.',fontsize=10)
                name=f'shank{s}_b{b}.png';fig.savefig(output/name,dpi=110,bbox_inches='tight');plt.close(fig);figures.append(name)
                focus.append(dict(shank=s,binary_channel=b,global_channel=g,neighbor_binary=neighbor,neighbor_global=ng,window_start=left,window_stop=right,longest_flat_start=a,longest_flat_stop=z))
                np.savez_compressed(output/f'shank{s}_b{b}.npz',sample_index=np.arange(left,right),target=x[left:right],neighbor=y,target_global=g,neighbor_global=ng)
    assert sha(SOURCE)==SOURCE_SHA
    save_csv(output/'focus_windows.csv',focus);save_json(output/'shank_summary.json',stats)
    save_json(output/'summary.json',dict(state='review_evidence_prepared',inventory_manifest_sha256=sha(inventory/'manifest.json'),inputs_manifest_sha256=sha(inputs/'manifest.json'),script_sha256=sha(Path(__file__)),focus_selection='Top guard-coverage channels: 3 on shanks1/3; 4 on shank2',overview_channels=1536,exclusions_adopted=False))
    body=['<!doctype html><meta charset="utf-8"><title>W14 channel review</title><style>body{font:16px system-ui;max-width:1450px;margin:30px auto}img{width:100%}td,th{padding:5px;border:1px solid #ccc}table{border-collapse:collapse}</style><h1>W14: remaining-shank inputs and channel review</h1>',
          '<p>All source data preserved. Separate full-width 512-channel exports; no sorting, channel removal or temporal masking performed. Guard fractions are diagnostic, not proven unusable time. Times are nominal (10000 Hz); physical rate is 10080 Hz.</p>',
          '<p><a href="../w14-quality01/channels.csv">All 1536 channel statistics</a> | <a href="shank_summary.json">Shank summary</a> | <a href="../../../docs/reviews/2026-11-24-w14-input-channel-review.md">Findings and proposals</a></p>']
    for n in figures:body.append(f'<h2>{html.escape(n)}</h2><img src="{n}">')
    (output/'index.html').write_text('\n'.join(body),encoding='utf-8')
    save_json(output/'manifest.json',{p.name:sha(p) for p in output.iterdir()})
    print(json.dumps(stats,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['inventory','inputs','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.inventory,a.inputs,a.output)
