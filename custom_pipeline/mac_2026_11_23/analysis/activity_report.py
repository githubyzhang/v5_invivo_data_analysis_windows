"""Descriptive analysis of saved candidates; no re-detection or default changes."""
from pathlib import Path
import sys,json,csv,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analysis.pilot import moving_average
from analysis.detect_recordings import validate

ROOT=Path('results/extra45_activity_report');FIG=ROOT/'figures';TAB=ROOT/'tables'
COLORS={4:'#167D9A',5:'#D46A32'}
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','axes.titleweight':'bold','savefig.dpi':180})

def save(fig,name):
    fig.savefig(FIG/f'{name}.png',bbox_inches='tight');fig.savefig(FIG/f'{name}.pdf',bbox_inches='tight');plt.close(fig)

def csvwrite(path,fields,rows):
    with open(path,'w') as f:
        w=csv.writer(f);w.writerow(fields);w.writerows(rows)

def main():
    FIG.mkdir(parents=True,exist_ok=True);TAB.mkdir(exist_ok=True)
    data={};summaries={};manifest={'analysis_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'inputs':{},'waveform_selection':[]}
    for rec in [4,5]:
        p=Path(f'results/spike_detection_ma50_adaptive/extra{rec}/spikes.h5');validate(p)
        with h5py.File(p,'r') as f:
            cfg=json.loads(f.attrs['config_json']);n=int(f.attrs['source_sample_count']);nc=int(f.attrs['source_channel_count']);fs=float(f.attrs['nominal_fs_hz'])
            ch=f['spikes/channel_id'][:].astype(int);sample=f['spikes/sample_index'][:].astype(np.int64)
            amp=f['spikes/negative_amplitude'][:];threshold=f['spikes/threshold'][:];counts=f['spikes/counts_per_channel'][:]
            usable=f['quality/usable_samples_per_channel_window'][:]/fs;exposure=usable.sum(axis=1)
            valid=f['quality/valid_noise_window'][:];guards=f['quality/flat_guard_intervals'][:].astype(np.int64)
            available=f['spikes/shared_warning_available'][:];warning=f['spikes/shared20_warning'][:]
            threshold_grid=f['noise/threshold'][:];shared=f['quality/shared_available_intervals'][:].astype(np.int64)
        source=Path(cfg['source']);st=source.stat()
        assert st.st_size==cfg['source_size_bytes'] and st.st_mtime_ns==cfg['source_mtime_ns']
        rates=np.divide(counts,exposure,out=np.full(nc,np.nan),where=exposure>0)
        seconds=np.arange(usable.shape[1]);timecounts=np.bincount(sample//int(fs),minlength=len(seconds))
        channel_time=np.zeros_like(usable,dtype=int);np.add.at(channel_time,(ch,sample//int(fs)),1)
        assert counts.sum()==timecounts.sum()==channel_time.sum()==len(sample)
        poprate=np.divide(timecounts,usable.sum(axis=0),out=np.full(len(seconds),np.nan),where=usable.sum(axis=0)>0)
        high=np.sort(counts)[::-1];top_n=int(np.ceil(.1*nc))
        summ={'candidates':len(sample),'channels':nc,'nominal_seconds':n/fs,'channels_with_candidates':int((counts>0).sum()),'channels_with_exposure':int((exposure>0).sum()),'usable_channel_seconds':float(exposure.sum()),'usable_percent':float(exposure.sum()/(nc*n/fs)*100),'pooled_rate_per_usable_channel_second':float(len(sample)/exposure.sum()),'channel_rate_percentiles_0_25_50_75_90_95_100':np.nanpercentile(rates,[0,25,50,75,90,95,100]).tolist(),'top_10_percent_channels_event_share':float(high[:top_n].sum()/len(sample)),'median_amplitude_threshold_ratio':float(np.median(amp/threshold)),'shared_assessed_events':int(available.sum()),'shared20_flagged_events':int(warning.sum()),'shared_assessed_seconds':float(np.diff(shared,axis=1).sum()/fs),'peak_1s_time':int(np.argmax(poprate)),'peak_1s_rate':float(np.max(poprate))}
        summaries[str(rec)]=summ
        csvwrite(TAB/f'extra{rec}_channels.csv',['channel_id','candidate_count','usable_seconds','candidate_rate_hz'],zip(range(nc),counts,exposure,rates))
        csvwrite(TAB/f'extra{rec}_timecourse.csv',['nominal_start_s','candidate_count','usable_channel_seconds','candidates_per_usable_channel_second','channels_with_candidates'],zip(seconds,timecounts,usable.sum(axis=0),poprate,(channel_time>0).sum(axis=0)))
        data[rec]=dict(ch=ch,sample=sample,counts=counts,rates=rates,exposure=exposure,usable=usable,timecounts=timecounts,poprate=poprate,channel_time=channel_time,amp=amp,threshold=threshold,fs=fs,guards=guards,valid=valid,threshold_grid=threshold_grid,cfg=cfg,source=source,warning=warning,available=available,n=n)
        manifest['inputs'][str(rec)]={'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_path':str(source),'source_size':st.st_size,'source_mtime_ns':st.st_mtime_ns}
        # All candidates shown. Raster is not a neuron raster; no spatial mapping assumed.
        fig,ax=plt.subplots(figsize=(12,4.4));ax.scatter(sample/fs,ch,s=.35,color=COLORS[rec],alpha=.65,rasterized=True,linewidths=0)
        ax.set(xlim=(0,n/fs),ylim=(-.5,nc-.5),xlabel='Time (nominal s)',ylabel='Electrode channel (zero-based)',title=f'extra_{rec}: all {len(sample):,} detected candidates')
        save(fig,f'extra{rec}_raster')
    # Temporal rates and observation support.
    fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True,gridspec_kw={'height_ratios':[2,1]},layout='constrained')
    for rec,d in data.items():
        axes[0].plot(np.arange(len(d['poprate']))+.5,d['poprate'],label=f'extra_{rec}',color=COLORS[rec],lw=1.2)
        axes[1].plot(np.arange(d['usable'].shape[1])+.5,d['usable'].sum(axis=0)/2048*100,color=COLORS[rec],lw=1.2)
    axes[0].set(ylabel='Candidates / usable channel-second',title='Activity over time (1 s bins)');axes[0].legend()
    axes[1].set(ylabel='Usable channel-time (%)',xlabel='Time from each recording start (nominal s)',ylim=(0,101),xlim=(0,300));save(fig,'timecourse')
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    for rec,d in data.items():
        rr=np.sort(d['rates'][np.isfinite(d['rates'])]);axes[0].plot(rr,np.arange(1,len(rr)+1)/len(rr),color=COLORS[rec],label=f'extra_{rec}')
        cs=np.sort(d['counts'])[::-1];axes[1].plot(np.arange(1,len(cs)+1)/len(cs)*100,np.cumsum(cs)/cs.sum()*100,color=COLORS[rec],label=f'extra_{rec}')
    axes[0].set(xlabel='Candidates / usable second, per channel',ylabel='Fraction of channels with exposure',xlim=(0,None),title='Channel rate distribution');axes[0].set_xscale('symlog',linthresh=.01);axes[0].legend()
    axes[1].set(xlabel='Channels ranked by candidate count (%)',ylabel='Cumulative candidates (%)',title='Activity concentration');axes[1].plot([0,100],[0,100],':',color='grey');save(fig,'channel_rates')
    fig,axes=plt.subplots(2,1,figsize=(12,6.7),sharex=True,layout='constrained')
    five={r:np.divide(d['channel_time'].reshape(2048,60,5).sum(2),d['usable'].reshape(2048,60,5).sum(2),out=np.full((2048,60),np.nan),where=d['usable'].reshape(2048,60,5).sum(2)>0) for r,d in data.items()}
    vmax=float(np.nanpercentile(np.concatenate([v.flatten() for v in five.values()]),99))
    for ax,(rec,rates) in zip(axes,five.items()):
        im=ax.imshow(rates,aspect='auto',origin='lower',extent=(0,300,-.5,2047.5),vmin=0,vmax=vmax,cmap='viridis',interpolation='nearest');ax.set(ylabel='Electrode channel',title=f'extra_{rec}: 5 s bins')
    axes[-1].set_xlabel('Time (nominal s)');fig.colorbar(im,ax=axes,label=f'Candidates / usable second (color capped at pooled 99th percentile: {vmax:.2f})',shrink=.8);save(fig,'channel_time_heatmap')
    fig,axes=plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
    for rec,d in data.items():
        ratio=np.sort(d['amp']/d['threshold']);axes[0].plot(ratio,np.arange(1,len(ratio)+1)/len(ratio),color=COLORS[rec],label=f'extra_{rec}')
        e=np.sort(d['exposure']/300*100);axes[1].plot(e,np.arange(1,len(e)+1)/len(e),color=COLORS[rec])
    axes[0].set(xlabel='Peak magnitude / event threshold',ylabel='Fraction of candidates',xscale='log',title='Distance above detection threshold');axes[0].legend()
    axes[1].set(xlabel='Usable recording time per channel (%)',ylabel='Fraction of all channels',title='Recording coverage',xlim=(0,100));save(fig,'amplitude_quality')
    # Exemplars are selected by a reproducible rate criterion, not by waveform appearance.
    for rec,d in data.items():
        eligible=np.flatnonzero((d['counts']>=30)&(d['exposure']>=270))
        selected=[]
        for q in [.25,.5,.9]:
            target=np.quantile(d['rates'][eligible],q);choices=eligible[~np.isin(eligible,selected)]
            selected.append(int(choices[np.argmin(np.abs(d['rates'][choices]-target))]))
        fig,axes=plt.subplots(3,2,figsize=(12,8),layout='constrained')
        fig2,axes2=plt.subplots(1,3,figsize=(12,4),layout='constrained')
        with h5py.File(d['source'],'r') as src:
            for row,ch in enumerate(selected):
                pp=d['sample'][d['ch']==ch];center=int(pp[np.argmin(np.abs(pp-150*d['fs']))]);a=max(0,center-2500);b=min(d['n'],center+2500)
                lo=max(0,a-510);hi=min(d['n'],b+510);raw=src['signals'][ch,lo:hi].astype(float);baseline=moving_average(raw,50);y=raw-baseline
                t=np.arange(a,b)/d['fs'];local=pp[(pp>=a)&(pp<b)];indices=local-lo
                axes[row,0].plot(t,raw[a-lo:b-lo],lw=.8,color='#475569');axes[row,0].plot(t,baseline[a-lo:b-lo],lw=1,color='#D46A32',label='MA50 baseline')
                axes[row,0].scatter(local/d['fs'],raw[indices],s=16,color=COLORS[rec],zorder=3)
                axes[row,1].plot(t,y[a-lo:b-lo],lw=.8,color='#475569');axes[row,1].scatter(local/d['fs'],y[indices],s=18,color=COLORS[rec],zorder=3)
                thresholds=d['threshold_grid'][ch,np.arange(a,b)//10000];axes[row,1].plot(t,-thresholds,'--',lw=1,color='#B42318')
                for ax in axes[row]:ax.set(xlim=(a/d['fs'],b/d['fs']),ylabel='Stored signal units',title=f'Channel {ch} · rate {d["rates"][ch]:.3f}/s');ax.ticklabel_format(axis='y',style='sci',scilimits=(-2,2))
                axes[row,0].set_title(f'Channel {ch}: raw + baseline + detections');axes[row,1].set_title(f'Channel {ch}: MA50 residual + threshold')
                # Exclude snippets intersecting guards, missing noise support or filter edges.
                candidates=[]
                for p in pp:
                    if p<55 or p+54>=d['n']:continue
                    if not d['valid'][ch,(p-30)//10000:(p+31+9999)//10000].all():continue
                    gg=d['guards'][d['guards'][:,0]==ch,1:]
                    if ((gg[:,0]<p+31)&(gg[:,1]>p-30)).any():continue
                    candidates.append(int(p))
                candidates=np.asarray(candidates);chosen=candidates[np.unique(np.linspace(0,len(candidates)-1,min(40,len(candidates)),dtype=int))] if len(candidates) else candidates
                waves=[]
                for p in chosen:
                    lo=p-55;hi=p+55;rr=src['signals'][ch,lo:hi].astype(float);yy=rr-moving_average(rr,50);wave=yy[25:86];waves.append(wave)
                    idx=np.flatnonzero((d['ch']==ch)&(d['sample']==p))[0];np.testing.assert_allclose(-wave[30],d['amp'][idx],rtol=1e-8,atol=1e-12)
                if len(waves):
                    waves=np.asarray(waves);tt=np.arange(-30,31)/10
                    axes2[row].plot(tt,waves.T,color=COLORS[rec],alpha=.18,lw=.7);axes2[row].plot(tt,np.median(waves,axis=0),color='#152A3B',lw=2)
                    np.savez_compressed(ROOT/f'extra{rec}_channel{ch}_waveforms.npz',sample_indices=chosen,relative_ms=tt,residual_waveforms=waves)
                axes2[row].set(title=f'Channel {ch} · {len(chosen)} events',xlabel='Time from detected peak (ms)',ylabel='MA50 residual (stored units)');axes2[row].axvline(0,color='grey',ls=':',lw=.8);axes2[row].ticklabel_format(axis='y',style='sci',scilimits=(-2,2))
                manifest['waveform_selection'].append({'recording':rec,'channel':ch,'rate_quantile_target':[.25,.5,.9][row],'trace_start_sample':a,'trace_stop_sample':b,'overlay_sample_indices':chosen.tolist(),'selection':'Channels closest to 25th/50th/90th rate percentile among >=30 events and >=270 s usable; trace centered on event nearest 150 s; up to 40 evenly spaced eligible events by order, no waveform-based selection.'})
        for ax in axes[-1]:ax.set_xlabel('Time (nominal s)')
        save(fig,f'extra{rec}_trace_examples');save(fig2,f'extra{rec}_waveform_overlays')
    for rec,d in data.items():
        bins=np.bincount(d['sample']//10,minlength=d['n']//10)
        peak=int(np.argmax(bins));summaries[str(rec)]['maximum_channels_with_event_in_1ms']=int(bins[peak])
        summaries[str(rec)]['maximum_1ms_start_s']=peak/1000
        summaries[str(rec)]['median_1s_pooled_rate']=float(np.median(d['poprate']))
        summaries[str(rec)]['top_five_1s_bins_event_share']=float(np.sort(d['timecounts'])[-5:].sum()/len(d['sample']))
        csvwrite(TAB/f'extra{rec}_coincidence_1ms.csv',['nominal_start_s','channels_with_event'],zip(np.arange(len(bins))/1000,bins))
        # With >=5 ms per-channel spacing, a 1 ms bin contains at most one event/channel.
        assert bins.max()<=2048
    d=data[5];peak_s=summaries['5']['maximum_1ms_start_s'];a=peak_s-.1;b=peak_s+.1
    fig,axes=plt.subplots(2,1,figsize=(12,5.5),sharex=True,layout='constrained',gridspec_kw={'height_ratios':[2,1]})
    keep=(d['sample']/10000>=a)&(d['sample']/10000<b)
    axes[0].scatter(d['sample'][keep]/10000,d['ch'][keep],s=3,color=COLORS[5],linewidths=0)
    axes[0].set(ylabel='Electrode channel',title=f'extra_5: largest 1 ms coincidence ({peak_s:.3f} s)',ylim=(-.5,2047.5))
    bins=np.arange(int(a*1000),int(b*1000)+1)/1000
    axes[1].hist(d['sample'][keep]/10000,bins=bins,color=COLORS[5]);axes[1].set(xlabel='Time (nominal s)',ylabel='Channels / 1 ms',xlim=(a,b))
    save(fig,'extra5_coincidence_zoom')
    (ROOT/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(summaries,indent=2))

if __name__=='__main__':main()
