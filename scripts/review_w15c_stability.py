"""Bounded away-zone quarter waveforms for every exclusion automated-good cluster."""
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_sorting import ROOT,read,save,sha,verify_manifest
from review_sorting_baseline import table


def run(shared,output):
    shared=shared.resolve();output=output.resolve();assert not output.exists() and output.is_relative_to(ROOT/'results')
    verify_manifest(shared/'report-manifest.json');meta=read(shared/'summary.json')
    report=ROOT/list(meta['report_manifests'])[1];verify_manifest(report/'report-manifest.json')
    r=ROOT/read(report/'summary.json')['run_path'];c=read(r/'config.json');N=c['samples'];fs=c['nominal_fs_hz']
    assert c['excluded_binary_channels']==[259];verify_manifest(r/'output-manifest.json')
    away=np.load(shared/'fixed_masks.npz')['away'];t=np.load(r/'kilosort4/spike_times.npy').ravel();cl=np.load(r/'kilosort4/spike_clusters.npy').ravel()
    inv=list(csv.DictReader((report/'clusters.csv').open()));ids=[int(x['cluster_id']) for x in inv if x['automated_label']=='good']
    raw=np.memmap(ROOT/c['binary_path'],mode='r',dtype='<f4',shape=(N,512));edges=np.linspace(0,N,5,dtype=int)
    output.mkdir(parents=True);rows=[];plots={};windows=0
    for cid in ids:
        z=np.load(shared/f'exclusion_c{cid}_zone_means.npz');channels=z['binary_channels'];reference=z['away_mean'];payload=dict(binary_channels=channels,reference=reference);means=[]
        for q,(a,b) in enumerate(zip(edges[:-1],edges[1:]),1):
            eligible=np.flatnonzero((cl==cid)&away[t]&(t>=max(a,100))&(t<min(b,N-100)))
            selected=eligible[np.unique(np.linspace(0,len(eligible)-1,min(32,len(eligible))).astype(int))] if len(eligible) else eligible
            if len(selected):
                waves=np.asarray(raw[t[selected,None]+np.arange(-100,101)[None,:]][:,:,channels],dtype=np.float32)*1e6
                waves-=np.median(waves[:,:70],axis=1)[:,None,:];mean=waves.mean(axis=0)
            else:mean=np.full(reference.shape,np.nan)
            # Separate scalar source reads verify all vectorized excerpts/means.
            reread=[]
            for i in selected:
                assert cl[i]==cid and a<=t[i]<b and away[t[i]]
                v=np.array(raw[t[i]-100:t[i]+101][:,channels])*1e6;v-=np.median(v[:70],axis=0);reread.append(v)
            if reread:np.testing.assert_array_equal(mean,np.mean(reread,axis=0))
            payload[f'q{q}_mean']=mean;payload[f'q{q}_event_indices']=selected;means.append(mean);windows+=len(selected)
            x,y=mean[80:141].ravel(),reference[80:141].ravel()
            corr=float(np.corrcoef(x,y)[0,1]) if np.isfinite(x).all() and np.isfinite(y).all() and x.std()>0 and y.std()>0 else None
            count=int(((cl==cid)&away[t]&(t>=a)&(t<b)).sum());exposure=int(away[a:b].sum())
            rows.append(dict(cluster_id=cid,quarter=q,away_events=count,away_exposure_samples=exposure,nominal_rate=count*fs/exposure,raw_windows=len(selected),correlation_to_pooled_away=corr))
        np.savez_compressed(output/f'c{cid}_quarters.npz',**payload);plots[cid]=(channels,reference,means)
    table(output/'quarter_metrics.csv',rows);pages=[]
    for start in range(0,len(ids),8):
        fig,axes=plt.subplots(4,2,figsize=(13,12),layout='constrained')
        for ax in axes.ravel():ax.axis('off')
        for ax,cid in zip(axes.ravel(),ids[start:start+8]):
            ax.axis('on');channels,reference,means=plots[cid]
            ax.plot(np.arange(-100,101)/fs*1000,reference[:,0],color='black',ls='--',label='pooled away')
            for q,mean in enumerate(means,1):ax.plot(np.arange(-100,101)/fs*1000,mean[:,0],label=f'Q{q}',alpha=.8)
            ax.set(title=f'Exclusion c{cid}, common raw b{channels[0]}',xlabel='Nominal ms',ylabel='Centered input x1e6')
        axes[0,0].legend(ncol=3,fontsize=8);fig.suptitle('Away-zone quarter means: automated-good candidates, not accepted units')
        name=f'away_quarters_{start//8+1}.png';fig.savefig(output/name,dpi=105);plt.close(fig);pages.append(name)
    summary=dict(state='bounded_diagnostic_verified',run_id=c['run_id'],clusters=ids,quarter_rows=len(rows),raw_windows_independently_reread=windows,shared_manifest_sha256=sha(shared/'report-manifest.json'),baseline_manifest_sha256=sha(report/'report-manifest.json'),script_sha256=sha(Path(__file__)),source_binary_sha256=sha(ROOT/c['binary_path']),limitations='Event centers in away zone; excerpts can cross zone edges. Away does not mean clean. At most 32 excerpts per quarter; low counts limit correlation. Reference selections overlap quarter samples. Common channels exclude b259. No unit acceptance or exposure-policy adoption.')
    save(output/'summary.json',summary)
    html='<html><meta charset="utf-8"><title>W15C away stability</title><style>body{font:16px system-ui;max-width:1400px;margin:30px auto}img{width:100%}</style><h1>W15C: exclusion-run away-zone stability</h1><p>Four equal original sample-axis quarters. Event centers outside shared core and its +/-500-sample expansion. Away is not guaranteed clean; x1e6 is numerical scaling, not voltage calibration.</p><p><a href="quarter_metrics.csv">Counts, exposure and correlations</a> | <a href="summary.json">Validation and limits</a></p>'
    html+=''.join(f'<img src="{n}">' for n in pages);(output/'index.html').write_text(html,encoding='utf-8')
    verify_manifest(shared/'report-manifest.json');save(output/'report-manifest.json',{p.name:sha(p) for p in output.iterdir()});print(summary)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--shared',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.shared,a.output)
