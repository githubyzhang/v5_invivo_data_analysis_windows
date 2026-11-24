"""Shank3 per-cluster diagnostic exposure and away-quarter support; no policy adoption."""
import csv
from pathlib import Path
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_sorting import ROOT, read, save, sha, verify_manifest
from review_sorting_baseline import table
from curation_review import extract, corr


def run(output):
    output = output.resolve()
    assert not output.exists() and output.is_relative_to(ROOT/'results')
    review=ROOT/'results/extra4_shank3/w16c-review01'
    shared=ROOT/'results/extra4_shank3/w15c-shared-review02'
    quality=ROOT/'results/extra4/w14-quality01'
    for p,m in [(review,'report-manifest.json'),(shared,'report-manifest.json'),(quality,'manifest.json')]: verify_manifest(p/m)
    meta=read(review/'summary.json'); source=ROOT/meta['run_path']; c=read(source/'config.json')
    assert c['shank_zero_based']==3
    t=np.load(source/'kilosort4/spike_times.npy').ravel();cl=np.load(source/'kilosort4/spike_clusters.npy').ravel()
    N=c['samples'];fs=c['nominal_fs_hz']; masks=np.load(shared/'fixed_masks.npz')
    raw=np.memmap(ROOT/c['binary_path'],mode='r',dtype='<f4',shape=(N,512))
    inventory=list(csv.DictReader((review/'unit_metrics.csv').open()))
    intervals=np.load(quality/'intervals.npz'); flat=intervals['flat'];flat=flat[flat[:,0]==3];guards=intervals['guard'];guards=guards[guards[:,0]==3]
    # Independently reconstruct fixed core and expanded union from source intervals.
    concurrency=np.zeros(N,np.int16)
    for ch in range(512):
        bit=np.zeros(N,bool)
        for a,b in flat[flat[:,1]==ch,3:5].astype(int):bit[a:b]=True
        concurrency+=bit
    core=concurrency>=256; expanded=core.copy()
    edge=np.diff(np.r_[False,core,False].astype(int));spans=np.column_stack((np.where(edge==1)[0],np.where(edge==-1)[0]))
    for a,b in spans:expanded[max(0,a-500):min(N,b+500)]=True
    for name,mask in [('core',core),('shoulder',expanded&~core),('away',~expanded)]:np.testing.assert_array_equal(mask,masks[name])
    prior={int(x['cluster_id']):x for x in csv.DictReader((shared/'cluster_zones.csv').open()) if x['run']=='exclusion'}
    output.mkdir();rows=[];quarter=[];windows=0;plots={}
    for entry in inventory:
        cid=int(entry['cluster_id']);peak=int(entry['peak_binary']);idx=np.where(cl==cid)[0];z=np.load(review/f'unit_{cid}.npz');channels=z['channels']
        guard=np.zeros(N,bool)
        for a,b in guards[guards[:,1]==peak,3:5]:guard[a:b]=True
        local=np.zeros(N,bool)
        for a,b in guards[np.isin(guards[:,1],channels),3:5]:local[a:b]=True
        variants=dict(all=np.ones(N,bool),away=~expanded,away_peak_clear=~(expanded|guard),away_local_clear=~(expanded|local))
        payload=dict(channels=channels);row=dict(cluster_id=cid,peak_binary=peak)
        for zone in ['core','shoulder','away']:
            count=int(masks[zone][t[idx]].sum());assert count==int(prior[cid][zone+'_events']);row[zone+'_events']=count
        row['peak_guard_samples']=int(guard.sum());row['local_guard_samples']=int(local.sum())
        for name,mask in variants.items():
            selected,w=extract(raw,t,idx[mask[t[idx]]],channels,128)
            mean=w.mean(0) if len(w) else np.full((201,8),np.nan)
            for i,v in zip(selected,w):
                expected=np.array(raw[t[i]-100:t[i]+101][:,channels])*1e6;expected-=np.median(expected[:70],axis=0);np.testing.assert_array_equal(expected,v);windows+=1
            count=int(mask[t[idx]].sum());exposure=int(mask.sum())
            row[name+'_events']=count;row[name+'_exposure_samples']=exposure;row[name+'_nominal_rate']=count*fs/exposure if exposure else None
            row[name+'_correlation_to_all']=corr(mean,z['reference']) if len(w)>1 else None
            payload[name+'_mean']=mean;payload[name+'_event_indices']=selected
        means=[]
        for q in range(4):
            a,b=q*N//4,(q+1)*N//4;eligible=idx[(t[idx]>=a)&(t[idx]<b)&(~expanded[t[idx]])]
            selected,w=extract(raw,t,eligible,channels,64);mean=w.mean(0) if len(w) else np.full((201,8),np.nan)
            for i,v in zip(selected,w):
                expected=np.array(raw[t[i]-100:t[i]+101][:,channels])*1e6;expected-=np.median(expected[:70],axis=0);np.testing.assert_array_equal(expected,v);windows+=1
            quarter.append(dict(cluster_id=cid,quarter=q+1,away_events=len(eligible),away_exposure_samples=int((~expanded[a:b]).sum()),raw_windows=len(w),correlation_to_all=corr(mean,z['reference']) if len(w)>1 else None))
            payload[f'q{q+1}_mean']=mean;payload[f'q{q+1}_indices']=selected;means.append(mean)
        np.savez_compressed(output/f'unit_{cid}.npz',**payload);rows.append(row);plots[cid]=(channels,means,z['reference'])
    table(output/'exposure.csv',rows);table(output/'away_quarters.csv',quarter);pages=[]
    for start in range(0,len(inventory),8):
        fig,axes=plt.subplots(4,2,figsize=(14,12),layout='constrained')
        block=inventory[start:start+8]
        for ax,e in zip(axes.ravel(),block):
            cid=int(e['cluster_id']);ch,means,reference=plots[cid]
            ax.plot(np.arange(-100,101)/10,reference[:,0],color='black',ls='--',label='all-event reference')
            for q,m in enumerate(means):ax.plot(np.arange(-100,101)/10,m[:,0],label=f'away Q{q+1}')
            ax.set(title=f'c{cid}, {e["automated_label"]}, raw b{ch[0]}',xlabel='Nominal ms',ylabel='Centered input x1e6')
        for ax in axes.ravel()[len(block):]:ax.set_visible(False)
        axes.ravel()[0].legend(fontsize=7);fig.suptitle('Away-quarter evidence; away is not guaranteed clean; no mask adopted')
        name=f'away_{start//8+1}.png';fig.savefig(output/name,dpi=100);plt.close(fig);pages.append(name)
    save(output/'checks.json',dict(state='passed',clusters=len(rows),quarter_rows=len(quarter),raw_windows_scalar_verified=windows,core_samples=int(core.sum()),shoulder_samples=int((expanded&~core).sum()),away_samples=int((~expanded).sum()),script_sha256=sha(Path(__file__)),source_binary_sha256=sha(ROOT/c['binary_path']),review_manifest_sha256=sha(review/'report-manifest.json'),shared_manifest_sha256=sha(shared/'report-manifest.json'),quality_manifest_sha256=sha(quality/'manifest.json'),limitations='Diagnostic center-based masks; raw windows can cross boundaries. Local means eight nearest active channels, not measured unit footprint. No corrected true rate, event removal, accepted unit or policy.'))
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>W16C exposure sensitivity</title><style>body{font:16px system-ui;max-width:1400px;margin:30px auto}img{width:100%}</style><h1>Shank3 diagnostic exposure and away-quarter support</h1><p>No exposure policy adopted. Away excludes the W15C shared core and shoulder; peak/local-clear additionally exclude padded guards on the peak/eight nearest active channels. These are sensitivities, not validated clean time or corrected true firing rates.</p><p><a href="exposure.csv">All-cluster counts and matching denominators</a> · <a href="away_quarters.csv">Away quarters</a> · <a href="checks.json">Checks</a></p>'+''.join(f'<img src="{p}">' for p in pages),encoding='utf-8')
    save(output/'manifest.json',{p.name:sha(p) for p in output.iterdir()});print(read(output/'checks.json'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
