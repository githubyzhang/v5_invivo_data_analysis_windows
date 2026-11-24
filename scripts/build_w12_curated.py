"""Build the explicitly accepted v1 subset without editing sorter outputs."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from review_w9_good import ROOT,RUN,rows,verify
from review_pilot_round1 import sha,write_csv,selection,RAW_SHA

W11=ROOT/'results/extra4_shank0/w11-exposure-review01'


def run(output):
    output=output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'results/extra4_shank0'):
        raise ValueError('Fresh derived result directory required')
    revision_path=ROOT/'configs/extra4_shank0_curated_v1.json';revision=json.loads(revision_path.read_text())
    policy_path=ROOT/revision['policy_path'];policy=json.loads(policy_path.read_text())
    assert revision['state']==policy['state']=='user_accepted'
    assert sha(policy_path)==revision['policy_sha256']
    assert sha(RUN/'output-manifest.json')==revision['run_manifest_sha256']
    assert sha(W11/'report-manifest.json')==revision['w11_report_manifest_sha256']
    verify(RUN,'output-manifest.json');verify(W11,'report-manifest.json')
    assert sha(ROOT/revision['proposal_ledger'])==revision['proposal_ledger_sha256']
    binary=ROOT/'data/extra4_shank0_float32.bin';assert sha(binary)==RAW_SHA
    src=RUN/'kilosort4';load=lambda n:np.load(src/(n+'.npy'),allow_pickle=False)
    t,cl,amp=[load(n).ravel() for n in ['spike_times','spike_clusters','amplitudes']]
    templates,pos,cmap=load('templates'),load('channel_positions'),load('channel_map').ravel()
    peak=np.ptp(templates,axis=1).argmax(1)
    ids=revision['accepted_cluster_ids'];start,stop=policy['primary_analysis_interval_half_open']
    accepted=np.isin(cl,ids);keep=accepted&(t>=start)&(t<stop)
    source_ids=np.flatnonzero(keep);omitted=np.flatnonzero(accepted&~keep)
    assert len(source_ids)==18252 and len(omitted)==2
    flags=np.load(W11/'event_annotations.npz');np.testing.assert_array_equal(t,flags['sample_index']);np.testing.assert_array_equal(cl,flags['cluster_id'])
    flag_names=[n for n in flags.files if n not in ['event_indices','sample_index','cluster_id']]
    output.mkdir(parents=True)
    for path in [revision_path,policy_path,ROOT/'docs/reviews/2026-11-24-w12-curation-ledger.csv']:(output/path.name).write_bytes(path.read_bytes())
    unit_key=lambda cid:f'extra_4:shank0:w7b-exclude248-01:cluster{cid}:v1'
    events=[dict(unit_id=unit_key(int(cl[i])),original_event_index=int(i),sample_index=int(t[i]),cluster_id=int(cl[i]),
        nominal_time_s=float(t[i]/10000),physical_time_s=float(t[i]/10080),sorter_amplitude=float(amp[i]),
        **{name:bool(flags[name][i]) for name in flag_names}) for i in source_ids]
    write_csv(output/'spikes.csv',events)
    np.savez_compressed(output/'spikes.npz',original_event_index=source_ids,sample_index=t[source_ids],cluster_id=cl[source_ids],sorter_amplitude=amp[source_ids],**{n:flags[n][source_ids] for n in flag_names})
    write_csv(output/'omitted_boundary_events.csv',[dict(original_event_index=int(i),sample_index=int(t[i]),cluster_id=int(cl[i]),reason='outside_accepted_analysis_domain') for i in omitted])
    # Bins retain the original sample axis; first/last-bin exposures are clipped.
    edges=np.arange(0,3000001,100000)
    exposure=np.maximum(0,np.minimum(edges[1:],stop)-np.maximum(edges[:-1],start))
    counts=np.array([np.histogram(t[keep&(cl==cid)],bins=edges)[0] for cid in ids])
    nominal_rates=counts/(exposure[None,:]/10000)
    physical_rates=counts/(exposure[None,:]/10080)
    np.savez_compressed(output/'rate_bins.npz',cluster_ids=ids,bin_edges_samples=edges,exposure_samples=exposure,counts=counts,nominal_rates=nominal_rates,physical_rates=physical_rates)
    bin_rows=[dict(cluster_id=cid,bin_start_sample=int(edges[j]),bin_stop_sample=int(edges[j+1]),exposure_samples=int(exposure[j]),events=int(counts[k,j]),nominal_rate=float(nominal_rates[k,j]),physical_rate=float(physical_rates[k,j])) for k,cid in enumerate(ids) for j in range(len(exposure))]
    write_csv(output/'rate_bins.csv',bin_rows)
    units=[];quarters=[];pages=[]
    raw=np.memmap(binary,mode='r',dtype='<f4',shape=(3000000,512));rel=np.arange(-100,101)
    interval_data=np.load(W11/'global_intervals.npz')
    def overlays(axis):
        for a,b in interval_data['active_guard_ge50']:axis.axvspan(a/10000,b/10000,color='red',alpha=.2)
        for a,b in interval_data['broad_warning']:axis.axvline(a/10000,color='purple',alpha=.45,lw=.7)
        # Availability complement is rendered separately from warnings.
        avail=interval_data['broad_available'];last=0
        for a,b in avail:
            if a>last:axis.axvspan(last/10000,a/10000,color='gray',alpha=.2)
            last=b
        if last<3000000:axis.axvspan(last/10000,300,color='gray',alpha=.2)
    for k,cid in enumerate(ids):
        ei=np.flatnonzero(keep&(cl==cid));channels=cmap[np.argsort(np.linalg.norm(pos-pos[peak[cid]],axis=1),kind='stable')[:8]]
        chosen=selection(ei,256)
        def read(selected):
            w=np.asarray(raw[t[selected,None]+rel[None,:]][:,:,channels],dtype=np.float32)*1e6
            w-=np.median(w[:,:70],axis=1)[:,None,:]
            return w
        w=read(chosen);reference=w.mean(0);means=[];saved={}
        for q in range(4):
            qi=ei[t[ei]//750000==q];selected=selection(qi,128);mean=read(selected).mean(0)
            means.append(mean);saved[f'quarter_{q}_events']=selected
            duration=max(0,min(stop,(q+1)*750000)-max(start,q*750000))
            correlation=float(np.corrcoef(mean[80:141].ravel(),reference[80:141].ravel())[0,1])
            quarters.append(dict(cluster_id=cid,quarter=q+1,events=len(qi),exposure_samples=duration,nominal_rate=len(qi)*10000/duration,
                amplitude_median=float(np.median(amp[qi])),raw_correlation_to_pooled=correlation))
        np.savez_compressed(output/f'unit_{cid}.npz',channels=channels,selected=chosen,waves=w,reference=reference,quarter_means=means,**saved)
        units.append(dict(unit_id=unit_key(cid),cluster_id=cid,status='accepted_putative_single_unit',original_automated_label='good',
            original_events=int(sum(cl==cid)),analysis_events=len(ei),boundary_events_omitted=int(sum((cl==cid)&accepted&~keep)),
            exposure_samples=stop-start,nominal_duration_s=(stop-start)/10000,physical_duration_s=(stop-start)/10080,
            nominal_rate=len(ei)*10000/(stop-start),physical_rate=len(ei)*10080/(stop-start),
            peak_binary=int(cmap[peak[cid]]),amplitude_median=float(np.median(amp[ei])),
            broad_warning_events=int(flags['broad_warning'][ei].sum()),tight_warning_events=int(flags['tight_warning'][ei].sum()),
            broad_unavailable_events=int((~flags['broad_available'][ei]).sum()),peak_guard_events=int(flags['peak_guard'][ei].sum())))
        fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        for j in range(2):
            for q,mean in enumerate(means):ax[0,j].plot(rel/10,mean[:,j],label=f'Q{q+1}')
            ax[0,j].plot(rel/10,reference[:,j],color='black',ls='--',label='pooled')
            ax[0,j].set(title=f'Raw means b{channels[j]}',xlabel='Nominal ms',ylabel='Centered input x1e6')
        ax[0,0].legend(fontsize=8)
        ax[1,0].scatter(t[ei]/10000,amp[ei],s=3,alpha=.4)
        marked=flags['peak_guard'][ei]|flags['broad_warning'][ei]
        ax[1,0].scatter(t[ei[marked]]/10000,amp[ei[marked]],facecolors='none',edgecolors='red',s=24)
        ax[1,0].set(xlim=(0,300),xlabel='Nominal seconds',ylabel='Sorter amplitude; red rings = peak guard/broad')
        ax[1,1].stairs(nominal_rates[k],edges/10000);ax[1,1].set(xlabel='Nominal seconds',ylabel='Events / retained nominal second')
        overlays(ax[1,0]);overlays(ax[1,1])
        fig.suptitle(f'Accepted putative unit: without-248 cluster {cid}; {len(ei)} events\nAnnotations retained; original sorter unchanged. Red band: shared guards; purple: broad; gray: unavailable.')
        name=f'unit_{cid}.png';fig.savefig(output/name,dpi=110);plt.close(fig);pages.append(name)
    write_csv(output/'units.csv',units);write_csv(output/'quarter_metrics.csv',quarters)
    write_csv(output/'quality_sensitivity.csv',[r for r in rows(W11/'sensitivity.csv') if int(r['cluster_id']) in ids])
    fig,ax=plt.subplots(figsize=(14,6),layout='constrained')
    for j,cid in enumerate(ids):
        ei=np.flatnonzero(keep&(cl==cid));ax.scatter(t[ei]/10000,np.full(len(ei),j),s=1,color='black')
        flagged=flags['peak_guard'][ei]|flags['broad_warning'][ei];ax.scatter(t[ei[flagged]]/10000,np.full(sum(flagged),j),s=12,color='red')
    overlays(ax);ax.set(yticks=np.arange(len(ids)),yticklabels=ids,xlabel='Original nominal seconds',ylabel='Without-248 cluster ID',title='Accepted putative subset v1: full event raster; red points = peak guard or broad warning')
    fig.savefig(output/'raster.png',dpi=130);plt.close(fig);pages.insert(0,'raster.png')
    fig,ax=plt.subplots(figsize=(14,6),layout='constrained')
    im=ax.imshow(nominal_rates,aspect='auto',origin='lower',extent=(0,300,-.5,len(ids)-.5));fig.colorbar(im,ax=ax,label='Events / retained nominal second')
    overlays(ax);ax.set(yticks=np.arange(len(ids)),yticklabels=ids,xlabel='Original nominal seconds (10-second bins)',ylabel='Without-248 cluster ID',title='Rate overview; matching first/last-bin exposure, no quality censoring')
    fig.savefig(output/'rates.png',dpi=130);plt.close(fig);pages.insert(1,'rates.png')
    verify(RUN,'output-manifest.json');verify(W11,'report-manifest.json');assert sha(binary)==RAW_SHA
    summary=dict(schema='w12-curated-summary-v1',state='user_accepted_derived_subset',revision_id=revision['revision_id'],
        accepted_cluster_ids=ids,event_count=len(source_ids),original_candidate_events=int(accepted.sum()),boundary_events_omitted=len(omitted),
        analysis_interval=[start,stop],exposure_samples=stop-start,nominal_seconds=(stop-start)/10000,physical_seconds=(stop-start)/10080,
        original_sorter_events=len(t),original_sorter_outputs_modified=False,quality_events_censored=False,
        run_manifest_sha256=sha(RUN/'output-manifest.json'),w11_manifest_sha256=sha(W11/'report-manifest.json'),
        revision_sha256=sha(revision_path),policy_sha256=sha(policy_path),script_sha256=sha(Path(__file__)),raw_sha256=RAW_SHA)
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>W12 accepted putative units</title><style>body{font:16px system-ui;max-width:1350px;margin:30px auto}img{width:100%}</style><h1>W12: accepted putative subset v1</h1><p>User accepted2026-11-24. Eleven putative units,18,252 events in[100,2999900) samples. Original sorter untouched. Two sample2 events from candidates32/38 are omitted only from this derived table. Quality flags remain annotations, not event removals.</p><p>Nominal duration299.98s; physical297.599206349s. Sample indices are authoritative. Rates use matching bin exposure; first and last nominal10s bins each contain9.99s. The sample axis is not shifted. Raw scaling x1e6 is numerical, not calibrated microvolts; sorter amplitudes are feature amplitudes.</p><p>Red bands: at least50% active-channel padded guards (diagnostic threshold); purple lines: broad warnings; gray: assessment unavailable. Narrow intervals may be visually subpixel. Unit figures use consecutive75 nominal second quarters and show two of eight saved channels. Waveform/reference selections can overlap. Whole-recording rate sensitivity does not establish local synchrony or event validity.</p><p><a href="units.csv">Unit table</a> | <a href="spikes.csv">Event table with original indices and flags</a> | <a href="rate_bins.csv">Rate bins</a> | <a href="quality_sensitivity.csv">W11 sensitivity</a> | <a href="omitted_boundary_events.csv">Omitted boundary events</a></p>'+''.join(f'<h2>{n}</h2><img src="{n}">' for n in pages),encoding='utf-8')
    (output/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in output.iterdir() if p.is_file()},indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    run(p.parse_args().output)
