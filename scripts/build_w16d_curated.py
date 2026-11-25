"""Build accepted shanks1-3 derived v1; preserve source output and sample axes."""
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_sorting import ROOT,read,save,sha,verify_manifest
from review_sorting_baseline import table
from curation_review import extract,corr


def exposure(spans,a,b):
    return int(np.maximum(0,np.minimum(spans[:,1],b)-np.maximum(spans[:,0],a)).sum())


def run(output):
    output=output.resolve();assert output.is_relative_to(ROOT/'results') and not output.exists()
    acceptance=ROOT/'configs/extra4_shanks123_curated_v1.json';a=read(acceptance)
    assert a['state']=='user_accepted' and a['units_accepted'] and a['policy_adopted']
    assert sha(ROOT/a['source_proposal'])==a['source_proposal_sha256']
    for p,h in a['pinned_files'].items():assert sha(ROOT/p)==h,p
    preview=ROOT/'results/extra4/w16d-proposal01';verify_manifest(preview/'manifest.json')
    registry=read(ROOT/'configs/extra4_working_runs.v1.json');domains=np.load(preview/'analysis_intervals.npz')
    output.mkdir();(output/'acceptance.json').write_bytes(acceptance.read_bytes())
    units=[];quarters=[];bins=[];events=[];omitted=[];ledger=[];raw_checks=0;pages=[]
    fig_raster,rax=plt.subplots(3,1,figsize=(14,10),layout='constrained')
    fig_rate,hax=plt.subplots(3,1,figsize=(14,10),layout='constrained')
    with (preview/'all_cluster_proposals.csv').open() as f:
        for r in csv.DictReader(f):
            r['accepted']=r['proposal']=='propose_putative'
            r['disposition']='accepted_putative' if r['accepted'] else 'hold_deferred' if r['proposal']=='hold' else 'withhold'
            ledger.append(r)
    with (preview/'omitted_event_preview.csv').open() as f:omitted=list(csv.DictReader(f))
    for spec,choice,axr,axh in zip(a['shanks'],registry['runs'],rax,hax):
        s=spec['shank'];assert s==choice['shank_zero_based'] and spec['run_id']==choice['run_id']
        runpath=ROOT/choice['run_path'];verify_manifest(runpath/'output-manifest.json')
        c=read(runpath/'config.json');src=runpath/'kilosort4';ids=spec['candidate_ids'];n=c['samples']
        assert sha(ROOT/c['binary_path'])==c['pinned_files'][c['binary_path']]
        t=np.load(src/'spike_times.npy').ravel();cl=np.load(src/'spike_clusters.npy').ravel();amp=np.load(src/'amplitudes.npy').ravel()
        flags=np.load(preview/f'shank{s}_event_preview.npz');np.testing.assert_array_equal(t,flags['sample_index'])
        keep=flags['proposed_inclusion'];included=np.flatnonzero(keep);spans=domains[f's{s}_primary']
        assert len(included)==spec['proposed_events']
        templates=np.load(src/'templates.npy');pos=np.load(src/'channel_positions.npy');cmap=np.load(src/'channel_map.npy').ravel()
        mapping=np.genfromtxt(ROOT/c['mapping_path'],delimiter=',',names=True,dtype=int)
        raw=np.memmap(ROOT/c['binary_path'],mode='r',dtype='<f4',shape=(n,512))
        sub=output/f'shank{s}';sub.mkdir()
        np.savez_compressed(sub/'spikes.npz',**{k:flags[k][included] for k in flags.files},sorter_amplitude=amp[included])
        np.savez_compressed(sub/'analysis_intervals.npz',primary=spans)
        flag_names=[k for k in flags.files if flags[k].dtype==bool and k not in ['candidate','interior','primary_domain','proposed_inclusion']]
        key=lambda cid:f'extra_4:shank{s}:{choice["run_id"]}:cluster{cid}:v1'
        for i in included:
            events.append(dict(unit_id=key(int(cl[i])),shank=s,run_id=choice['run_id'],cluster_id=int(cl[i]),original_event_index=int(i),sample_index=int(t[i]),nominal_time_s=float(t[i]/10000),physical_time_s=float(t[i]/10080),sorter_amplitude=float(amp[i]),**{k:bool(flags[k][i]) for k in flag_names}))
        edges=np.arange(0,n+1,100000);dur=np.array([exposure(spans,x,y) for x,y in zip(edges[:-1],edges[1:])]);count=np.array([np.histogram(t[keep&(cl==cid)],edges)[0] for cid in ids])
        nr=np.divide(count*10000,dur[None,:],out=np.full(count.shape,np.nan),where=dur[None,:]>0)
        pr=nr*1.008
        np.savez_compressed(sub/'rate_bins.npz',cluster_ids=ids,bin_edges_samples=edges,exposure_samples=dur,counts=count,nominal_rates=nr,physical_rates=pr)
        for j,cid in enumerate(ids):
            for b in range(len(dur)):bins.append(dict(unit_id=key(cid),shank=s,cluster_id=cid,start_sample=int(edges[b]),stop_sample=int(edges[b+1]),events=int(count[j,b]),exposure_samples=int(dur[b]),nominal_rate=float(nr[j,b]),physical_rate=float(pr[j,b])))
        plots=[]
        for j,cid in enumerate(ids):
            ei=np.flatnonzero(keep&(cl==cid));peak=int(np.ptp(templates[cid],axis=0).argmax());ch=cmap[np.argsort(np.linalg.norm(pos-pos[peak],axis=1),kind='stable')[:8]]
            selected,w=extract(raw,t,ei,ch,256);reference=w.mean(0);payload=dict(channels=ch,selected=selected,reference=reference,waves=w);means=[]
            for idx,wave in zip(selected,w):
                direct=np.array(raw[t[idx]-100:t[idx]+101][:,ch])*1e6;direct-=np.median(direct[:70],axis=0);np.testing.assert_array_equal(direct,wave);raw_checks+=1
            for q in range(4):
                lo,hi=q*n//4,(q+1)*n//4;qi=ei[(t[ei]>=lo)&(t[ei]<hi)]
                selected_q,wq=extract(raw,t,qi,ch,128);mean=wq.mean(0) if len(wq) else np.full((201,8),np.nan)
                for idx,wave in zip(selected_q,wq):
                    direct=np.array(raw[t[idx]-100:t[idx]+101][:,ch])*1e6;direct-=np.median(direct[:70],axis=0);np.testing.assert_array_equal(direct,wave);raw_checks+=1
                duration=exposure(spans,lo,hi);means.append(mean);payload[f'quarter_{q}_events']=selected_q
                quarters.append(dict(unit_id=key(cid),shank=s,cluster_id=cid,quarter=q+1,events=len(qi),exposure_samples=duration,nominal_rate=len(qi)*10000/duration if duration else None,physical_rate=len(qi)*10080/duration if duration else None,amplitude_median=float(np.median(amp[qi])) if len(qi) else None,raw_correlation_to_pooled=corr(mean,reference)))
            payload['quarter_means']=np.array(means);np.savez_compressed(sub/f'unit_{cid}.npz',**payload)
            row=dict(unit_id=key(cid),shank=s,run_id=choice['run_id'],cluster_id=cid,status='accepted_putative_single_unit',original_events=int((cl==cid).sum()),analysis_events=len(ei),omitted_events=int((cl==cid).sum())-len(ei),exposure_samples=spec['exposure_samples'],nominal_duration_s=spec['nominal_seconds'],physical_duration_s=spec['physical_seconds'],nominal_rate=len(ei)*10000/spec['exposure_samples'],physical_rate=len(ei)*10080/spec['exposure_samples'],peak_binary=int(ch[0]),peak_global=int(mapping['original_channel_id'][ch[0]]),amplitude_median=float(np.median(amp[ei])),**{k:int(flags[k][ei].sum()) for k in flag_names})
            row['coincidence_unavailable']=int((~flags['broad_available'][ei]).sum());units.append(row)
            plots.append((cid,ei,ch,reference,means,j))
            axr.scatter(t[ei]/10000,np.full(len(ei),j),s=1,color='#167e85')
        # Quality and missing-domain overlays preserve the original sample axis.
        excluded=np.ones(n,bool)
        for lo,hi in spans:excluded[lo:hi]=False
        edge=np.diff(np.r_[False,excluded,False].astype(int));bad=list(zip(np.where(edge==1)[0],np.where(edge==-1)[0]))
        for lo,hi in bad:axr.axvspan(lo/10000,hi/10000,color='#d98338',alpha=.25)
        axr.set(yticks=range(len(ids)),yticklabels=[f'c{x}' for x in ids],xlim=(0,300),xlabel='Original nominal seconds',title=f'Shank{s}: accepted putative units; orange = excluded domain')
        im=axh.imshow(nr,aspect='auto',origin='lower',extent=(0,300,-.5,len(ids)-.5));axh.set(yticks=range(len(ids)),yticklabels=[f'c{x}' for x in ids],xlabel='Original nominal seconds; 10-second bins',title=f'Shank{s}: observed event rates with matching bin exposure')
        fig_rate.colorbar(im,ax=axh,label='Events / retained nominal second')
        for start in range(0,len(plots),5):
            block=plots[start:start+5];fig,axs=plt.subplots(len(block),3,figsize=(15,3*len(block)),squeeze=False,layout='constrained')
            for ax,(cid,ei,ch,reference,means,j) in zip(axs,block):
                for q,m in enumerate(means):ax[0].plot(np.arange(-100,101)/10,m[:,0],label=f'Q{q+1}')
                ax[0].plot(np.arange(-100,101)/10,reference[:,0],ls='--',color='black');ax[0].set(title=f'c{cid}, raw b{ch[0]}',xlabel='Nominal ms',ylabel='Centered input x1e6');ax[0].legend(fontsize=7)
                ax[1].scatter(t[ei]/10000,amp[ei],s=3);marked=flags['peak_guard'][ei]|flags['broad_warning'][ei]
                ax[1].scatter(t[ei[marked]]/10000,amp[ei[marked]],s=22,facecolors='none',edgecolors='red')
                ax[1].set(xlim=(0,300),xlabel='Nominal seconds',ylabel='Sorter amplitude; red = peak/broad')
                ax[2].stairs(nr[j],edges/10000);ax[2].set(xlim=(0,300),xlabel='Nominal seconds',ylabel='Observed events / retained second')
                for lo,hi in bad:
                    for aa in ax[1:]:aa.axvspan(lo/10000,hi/10000,color='#d98338',alpha=.25)
            fig.suptitle(f'Shank{s}: accepted v1 summaries; residual quality limits remain')
            name=f'shank{s}/units_{start//5+1}.png';fig.savefig(output/name,dpi=100);plt.close(fig);pages.append(name)
    fig_raster.savefig(output/'raster.png',dpi=120);plt.close(fig_raster);fig_rate.savefig(output/'rates.png',dpi=120);plt.close(fig_rate)
    table(output/'spikes.csv',events);table(output/'units.csv',units);table(output/'quarters.csv',quarters);table(output/'rate_bins.csv',bins);table(output/'omitted_events.csv',omitted);table(output/'curation_ledger.csv',ledger)
    (output/'sensitivity.csv').write_bytes((preview/'sensitivity.csv').read_bytes())
    summary=dict(state='accepted_derived_v1',units=len(units),events=len(events),omitted_events=len(omitted),quarters=len(quarters),rate_bins=len(bins),raw_windows_verified=raw_checks,shanks=a['shanks'],acceptance_sha256=sha(acceptance),builder_sha256=sha(Path(__file__)),source_preview_manifest_sha256=sha(preview/'manifest.json'),original_outputs_modified=False,hold_clusters_deferred=True,limitations=a['limitations'])
    assert (len(units),len(events),len(omitted))==(30,43796,12)
    save(output/'summary.json',summary)
    cards=''.join(f'<section><h2>Shank{s["shank"]}</h2><b>{s["units"]} putative units</b><p>{s["proposed_events"]:,} events<br>{s["nominal_seconds"]:.4f} nominal seconds per unit</p></section>' for s in a['shanks'])
    body='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>W16D accepted derived v1</title><style>body{font:16px/1.6 system-ui;background:#f3f6f8;color:#203b42;margin:0}main{max-width:1250px;margin:auto;padding:30px}header{background:#173c45;color:white;padding:30px;border-radius:16px}.cards{display:flex;gap:16px;margin:24px 0}section{background:white;padding:20px;border-radius:12px;flex:1}a{color:#126477}nav{display:flex;gap:16px;flex-wrap:wrap;margin:24px 0}img{width:100%}.note{background:#fff3dc;border-left:5px solid #d39732;padding:20px}@media(max-width:700px){.cards{display:block}}</style><main><header><p>EXTRA_4 · W16D · ACCEPTED DERIVED REVISION v1</p><h1>30 putative units · 43,796 analysis events</h1><p>Shanks1–3. Unit subsets and analysis policies accepted by the user. Original sorter results preserved.</p></header>'''
    body+='<div class="cards">'+cards+'</div><nav>'+''.join(f'<a href="{path}">{label}</a>' for path,label in [('units.csv','Unit table'),('spikes.csv','Event table'),('curation_ledger.csv','All 128 cluster decisions'),('omitted_events.csv','12 omitted identities'),('quarters.csv','Quarter summaries'),('rate_bins.csv','Bin counts and exposure'),('sensitivity.csv','Guard sensitivities'),('acceptance.json','Accepted policy'),('../w16d-curated-validation01/checks.json','Independent audit')])+'</nav>'
    body+='<div class="note"><p>These are putative units, not definitive neuron identities. Rates describe observed events in the accepted domain, not true firing-rate estimates. Shared loss is not neuronal silence. Shanks1–2 use the interior window; shank3 also excludes the documented shared core and shoulder. Other quality flags remain annotations, and unknown assessments remain unknown.</p><p>51 held and 47 withheld clusters remain outside the subset. Held clusters are deferred for later review. Shank0 retains its separate frozen 11-unit release; W17 will audit the combined release and its policy differences.</p></div><h2>Accepted event raster</h2><img src="raster.png"><h2>Exposure-aware binned rates</h2><img src="rates.png"><h2>Waveform, amplitude and rate summaries</h2><p>Waveforms use selected accepted-domain events; Q1–Q4 retain the original recording quarters. Red amplitude rings mark peak-guard or broad-warning events; orange marks excluded domains. Mean waveform windows may cross mask edges.</p>'
    body+=''.join(f'<h3>{p.split("/")[0]} · page {p.split("_")[-1].split(".")[0]}</h3><img src="{p}" loading="lazy">' for p in pages)+'</main></html>'
    (output/'index.html').write_text(body,encoding='utf-8')
    save(output/'manifest.json',{str(p.relative_to(output)).replace('\\','/'):sha(p) for p in output.rglob('*') if p.is_file()})
    print(summary)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);run(p.parse_args().output)
