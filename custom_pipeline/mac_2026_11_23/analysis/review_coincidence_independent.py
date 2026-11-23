"""Independent event/quality audit and 1ms per-second maximum plots.

No raw drive required; reviews cached evidence without rerunning detection.
"""
from pathlib import Path
import base64,json,os,sys
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/invivo-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analysis.candidate_coincidence import sha256
from analysis.pilot import moving_average
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/coincidence_independent_review'
KEYS=[f'w{w}ms_q{q}' for w in (1,3,5) for q in (5,10,25)]

def plot(ax,rows,rec,log=False):
    x=np.array([r['second_start']+.5 for r in rows]);y=np.array([np.nan if r['fraction'] is None else r['fraction'] for r in rows])
    # Log cannot represent zero: omit without introducing a pseudocount.
    display=np.where(y>0,y,np.nan) if log else y
    ax.plot(x,display,color='#087e88' if rec==4 else '#526fa5',lw=1.1)
    for q in (.05,.10,.25,.50):ax.axhline(q,color='#a8a8a8',ls=':',lw=.7)
    if log:ax.set_yscale('log');ax.set_ylim(1e-4,1)
    else:ax.set_ylim(0,1)
    ax.set(xlim=(0,300),xlabel='Nominal time (s)',ylabel='Maximum active / eligible channel fraction',title=f'extra_{rec} • '+('logarithmic y-axis' if log else 'linear y-axis'))
    ax.spines[['top','right']].set_visible(False)
    unavailable=int(np.isnan(y).sum());zero=int((y==0).sum())
    ax.text(.02,.97,f'Unavailable seconds: {unavailable}; zero maxima: {zero}',transform=ax.transAxes,va='top',fontsize=9,bbox=dict(facecolor='white',edgecolor='none',alpha=.85))

def raw_review():
    selections=json.loads((ROOT/'results/coincidence_low_quorum/selection.json').read_text())
    provenance=[]
    for selection in selections:
        if selection['kind']!='Additional review example':continue
        rec=selection['recording'];folder=ROOT/f'results/coincidence_low_quorum/extra{rec}'
        protocol=json.loads((folder/'protocol.json').read_text());cfg=protocol['source_config'];path=Path(cfg['source'])
        if not path.exists():continue
        stat=path.stat();assert (stat.st_size,stat.st_mtime_ns)==(cfg['source_size_bytes'],cfg['source_mtime_ns'])
        start,stop=selection['start_sample'],selection['stop_sample'];center=selection['center_sample']
        with h5py.File(folder/'annotations.h5','r') as f,h5py.File(protocol['input'],'r') as events,h5py.File(path,'r') as raw:
            times=f['events/sample_index'][:].astype(int);channels=f['events/channel_id'][:]
            a=f['tracks/w1ms/active_channels'][start:stop];e=f['tracks/w1ms/eligible_channels'][start:stop]
            score=np.divide(a,e,out=np.full(len(a),-1.),where=e>=1024);peak=start+int(np.argmax(score))
            candidates=np.unique(channels[(times>=peak)&(times<peak+10)])
            chosen=candidates[np.unique(np.linspace(0,len(candidates)-1,min(6,len(candidates))).astype(int))]
            data=raw['signals'][chosen.tolist(),start-100:stop+100].astype(float)
            th=events['noise/threshold'][:];t=(np.arange(start,stop)-center)/10
            fig,axes=plt.subplots(3,1,figsize=(12,9),sharex=True,layout='constrained')
            near=(times>=start)&(times<stop)
            axes[0].scatter((times[near]-center)/10,channels[near],s=3,color='#355a73');axes[0].set(ylabel='Global channel ID',ylim=(-20,2070),title=f'extra_{rec} additional interval • {center/10000:.4f} nominal s')
            for ax in axes:
                for x,y in f['variants/w1ms_q5/intervals'][:]:
                    if x<stop and y>start:ax.axvspan((max(int(x),start)-center)/10,(min(int(y),stop)-center)/10,color='#ddb14f',alpha=.25)
            for i,c in enumerate(chosen):
                trace=data[i,100:-100];scale=np.percentile(trace,95)-np.percentile(trace,5)
                residual=(data[i]-moving_average(data[i],50))[100:-100]
                threshold=th[c,np.arange(start,stop)//10000]
                axes[1].plot(t,(trace-np.median(trace))/(scale if scale>0 else 1)+3*i,lw=.7)
                axes[2].plot(t,residual/threshold+6*i,lw=.7);axes[2].axhline(6*i-1,color='gray',ls=':',lw=.6)
                idx=times[near&(channels==c)]-start
                axes[2].scatter(t[idx],(residual/threshold)[idx]+6*i,s=14,color='#c54332')
            axes[1].set_yticks(np.arange(len(chosen))*3,chosen);axes[1].set_ylabel('Centered/scaled raw signal\nchannel ID + display offset')
            axes[2].set_yticks(np.arange(len(chosen))*6,chosen);axes[2].set_ylabel('MA50 residual / threshold\nchannel ID + display offset');axes[2].set_xlabel('Relative time (ms)')
            for ext in ('png','pdf'):fig.savefig(OUT/f'extra{rec}_additional_raw.{ext}',dpi=160)
            plt.close(fig)
            np.savez_compressed(OUT/f'extra{rec}_additional_raw.npz',raw_with_context=data,channel_id=chosen,start_sample=start,stop_sample=stop,context_samples=100)
            provenance.append({'recording':rec,'start_sample':start,'stop_sample':stop,'peak_1ms_start_sample':peak,'channels':chosen.tolist(),'source':str(path),'size':stat.st_size,'mtime_ns':stat.st_mtime_ns,'selection':'Previously selected additional interval; six evenly ranked event-channel IDs in its strongest supported 1ms window. Not chosen for waveform shape.'})
        assert (path.stat().st_size,path.stat().st_mtime_ns)==(stat.st_size,stat.st_mtime_ns)
    (OUT/'raw_review_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    return provenance


def main():
    OUT.mkdir(exist_ok=True);allrows={};review={};label_rows=[];inputs={}
    labels=json.loads((ROOT/'docs/reviews/ma50_user_review.json').read_text())['labels']
    for rec in (4,5):
        folder=ROOT/f'results/coincidence_low_quorum/extra{rec}'
        protocol=json.loads((folder/'protocol.json').read_text());inp=Path(protocol['input'])
        inputs[str(inp.relative_to(ROOT))]=sha256(inp);assert inputs[str(inp.relative_to(ROOT))]==protocol['input_sha256']
        inputs[str((folder/'annotations.h5').relative_to(ROOT))]=sha256(folder/'annotations.h5')
        with h5py.File(folder/'annotations.h5','r') as f,h5py.File(inp,'r') as src:
            times=src['spikes/sample_index'][:].astype(np.int64);ch=src['spikes/channel_id'][:]
            np.testing.assert_array_equal(times,f['events/sample_index'][:]);np.testing.assert_array_equal(ch,f['events/channel_id'][:])
            order=np.argsort(times,kind='stable');sorted_times=times[order];sorted_ch=ch[order]
            valid=src['quality/valid_noise_window'][:].astype(bool);ref=src['quality/reference_eligible'][:].astype(bool)
            guards=src['quality/flat_guard_intervals'][:].astype(np.int64)
            cfg=protocol['source_config'];n=cfg['shape'][1];fs=cfg['nominal_fs_hz']
            width=int(f['tracks/w1ms'].attrs['width_samples']);assert width==10 and fs==10000
            active=f['tracks/w1ms/active_channels'][:];eligible=f['tracks/w1ms/eligible_channels'][:]
            supported=eligible>=protocol['minimum_eligible_channels']
            ratio=np.divide(active,eligible,out=np.full(len(active),np.nan),where=supported)
            rows=[];peakstarts=[]
            for second,a in enumerate(range(0,n,fs)):
                b=min(a+fs,len(ratio));segment=ratio[a:b]
                peak=a+int(np.nanargmax(segment)) if np.isfinite(segment).any() else None
                if peak is not None:peakstarts.append(peak)
                rows.append({'second_start':second,'fraction':None if peak is None else float(ratio[peak]),'peak_window_start_sample':peak,'active_channels':None if peak is None else int(active[peak]),'eligible_channels':None if peak is None else int(eligible[peak]),'supported_window_starts':int(supported[a:b].sum()),'total_window_starts':max(0,b-a)})
            # Different algorithm from the interval sweep: vector quality predicate
            # plus time-sorted event slice and unique IDs, independently at each peak.
            rng=np.random.default_rng(20261122+rec)
            starts=np.unique(np.r_[peakstarts,rng.integers(0,len(active),100),0,len(active)-1])
            for a in starts:
                a=int(a);b=a+width
                ok=ref & valid[:,a//fs] & valid[:,(b-1)//fs]
                if a<cfg['physical_edge_exclusion_samples'][0] or b>n-cfg['physical_edge_exclusion_samples'][1]:ok[:]=False
                intersect=(guards[:,1]<b)&(guards[:,2]>a);ok[guards[intersect,0]]=False
                lo,hi=np.searchsorted(sorted_times,[a,b]);participating=np.unique(sorted_ch[lo:hi])
                assert (int(ok[participating].sum()),int(ok.sum()))==(int(active[a]),int(eligible[a]))
            for key in KEYS:
                mask=np.zeros(len(times),bool)
                for a,b in f[f'variants/{key}/intervals'][:]:mask|=(times>=a)&(times<b)
                np.testing.assert_array_equal(mask,f[f'variants/{key}/event_warning'][:])
            for lab in labels:
                if not lab['segment'].startswith(f'extra{rec}_'):continue
                match=np.flatnonzero((times==lab['sample_index'])&(ch==lab['channel']))
                entry={'id':lab['id'],'recording':rec,'user_label':lab['user_label'],'exact_match_in_current_adaptive':len(match)==1,'warnings':{}}
                if len(match)==1:
                    for key in KEYS:entry['warnings'][key]=bool(f[f'variants/{key}/event_warning'][int(match[0])])
                label_rows.append(entry)
            finite=ratio[np.isfinite(ratio)];globalpeak=int(np.nanargmax(ratio))
            review[f'extra{rec}']={'peak_fraction':float(ratio[globalpeak]),'peak_window_start_s':globalpeak/fs,'peak_active':int(active[globalpeak]),'peak_eligible':int(eligible[globalpeak]),'supported_start_fraction':float(supported.mean()),'audited_windows':len(starts),'per_second_max_median':float(np.median([r['fraction'] for r in rows if r['fraction'] is not None])),'seconds_at_or_above':{str(q):sum(r['fraction'] is not None and r['fraction']>=q for r in rows) for q in (.05,.1,.25,.5)}}
            allrows[rec]=rows
        assert sha256(inp)==protocol['input_sha256']
    fig,axes=plt.subplots(2,2,figsize=(14,8),layout='constrained')
    for i,rec in enumerate((4,5)):
        plot(axes[i,0],allrows[rec],rec);plot(axes[i,1],allrows[rec],rec,True)
    fig.suptitle('Maximum 1 ms coincidence fraction in each nominal second',fontsize=15)
    for ext in ('png','pdf'):fig.savefig(OUT/f'maximum_1ms_linear_log.{ext}',dpi=160)
    plt.close(fig)
    for rec in (4,5):
        fig,axes=plt.subplots(2,1,figsize=(12,7),layout='constrained')
        plot(axes[0],allrows[rec],rec);plot(axes[1],allrows[rec],rec,True)
        for ext in ('png','pdf'):fig.savefig(OUT/f'extra{rec}_maximum_1ms.{ext}',dpi=160)
        plt.close(fig)
    raw_provenance=raw_review()
    matched=[x for x in label_rows if x['exact_match_in_current_adaptive']]
    plausible=[x for x in matched if x['user_label']=='plausible eAP']
    label_summary={'historical_labels':len(labels),'exact_matches':len(matched),'matched_plausible':len(plausible),'plausible_flagged_by_variant':{k:sum(x['warnings'][k] for x in plausible) for k in KEYS},'limit':'Selected historical labels mostly outside new warning episodes; not specificity validation. Unmatched labels are not scored as unflagged.'}
    def image(name,caption):
        return '<figure><img alt="'+caption+'" src="data:image/png;base64,'+base64.b64encode((OUT/name).read_bytes()).decode()+'"><figcaption>'+caption+'</figcaption></figure>'
    raw_section='<section><h2>Additional raw-signal review</h2><p>The reconnected source drive permits fresh inspection of the previously selected additional intervals. Six channels are selected evenly by ID among events in the strongest 1 ms window, not by waveform appearance. Raw values are centered/scaled only for display; residuals are divided by the saved threshold. Orange indicates 1 ms / 5% warnings; red marks original detections. The extra_4 panel shows a temporally aligned narrow negative deflection across the selected channels; the extra_5 panel shows repeated aligned deflections, some with broader surrounding baseline changes. These observations strengthen the case for shared-disturbance review, but do not identify the cause or prove that every coincident candidate is false. These deliberately selected panels do not establish accuracy.</p>'+''.join(image(f'extra{r["recording"]}_additional_raw.png',f'extra_{r["recording"]}: additional interval, source unchanged; channel selection recorded in raw_review_provenance.json.') for r in raw_provenance)+'</section>' if raw_provenance else ''
    raw_note='The source drive was reconnected during this review. Fresh raw panels for the additional extra_4 and extra_5 intervals are included below, alongside cached prior evidence.' if len(raw_provenance)==2 else 'Source access was incomplete; raw_review_provenance.json identifies any fresh raw panels available in this run.'
    facts=''.join(f'<tr><td>{rec}</td><td>{r["peak_active"]}/{r["peak_eligible"]}</td><td>{r["peak_fraction"]*100:.2f}%</td><td>{r["peak_window_start_s"]:.4f}</td><td>{r["per_second_max_median"]*100:.3f}%</td></tr>' for rec,r in review.items())
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Independent coincidence review and 1ms plots</title><style>body{font:17px/1.65 system-ui;background:#eef4f5;color:#203d49;margin:0}main{max-width:1200px;margin:auto;padding:28px}section,header{padding:26px;background:white;margin:20px 0;border-radius:12px}h1,h2{color:#087f88}img{width:100%;height:auto}figure{margin:20px 0}figcaption{font-size:14px;color:#536e78}table{border-collapse:collapse;width:100%}td,th{padding:10px;text-align:left;border-bottom:1px solid #dae3e7}.note{background:#fff0d1;padding:18px}@media(max-width:650px){main{padding:10px}section{padding:14px}}</style><main><header><h1>Independent review of coincidence warnings</h1><p>Maximum 1 ms coincidence per nominal second • linear and log scales • 23 November 2026</p></header><section><h2>My assessment</h2><p><strong>The lower-quorum method identifies a useful class of widespread, tightly timed detections that the original majority rule missed. It is supported as a review warning; these results do not establish a safe automatic artifact-removal setting.</strong></p><p>The cached extra_5 raw panels show similar deflections across widely separated channels. Together with the very broad event coincidence, this is consistent with shared contamination. The extra_4 example also warrants artifact review, although its participation is much smaller. Waveform similarity and coincidence do not establish a physical cause or exclude genuine spikes in the same interval.</p><p>The parameter comparison reveals a real tradeoff: 1 ms / 5% flags 114 of the 195 extra_5 previous-only candidates; 5 ms / 5–25% flags all 195. Wider windows cover nearby detections around a shared event. That wider coverage should not be mistaken for independently identifying each covered candidate as an artifact.</p><p>The median per-second maximum is 0.538% in extra_4 and 0.636% in extra_5. The distinction is more pronounced in large excursions: 1 ms maxima reach 5% in 2 nominal seconds of extra_4 and 27 seconds of extra_5. A second counted here may contain only a brief excursion; this is not flagged duration.</p><p>At 5%, roughly 100 eligible electrodes can trigger a warning when about 2,000 are available. Channels are not independent neurons. Local units, common electronics, broad neural activity and disturbance can all affect this count. These results do not identify an optimal quorum.</p><div class="note">'''+raw_note+''' This is a second assessment using a different count-check algorithm, not an independent ground-truth dataset.</div></section><section><h2>Requested plots</h2><p>Each point is the maximum ratio among supported 10-sample windows whose <strong>start sample</strong> falls in that nominal second. Every start advances one sample; windows can cross a second boundary. Each denominator counts only channels observable throughout that window, with at least 1,024 eligible channels. Ratios are computed before taking their maximum; maximum numerator divided by a separate maximum denominator would be incorrect.</p><p>Time points are plotted at second centers. Linear axes share 0–1 limits; logarithmic axes share 10⁻⁴–1 limits. Dotted reference lines indicate 5%, 10%, 25% and 50%. No pseudocount is used: zero maxima would be omitted on log axes, and wholly unassessed seconds would be missing on both. Both recordings have zero such seconds in these outputs; partially unassessed seconds remain documented in the numeric table.</p>'''+image('maximum_1ms_linear_log.png','Same maximum fractions on two scales. Log scaling reveals lower-level coincidence without changing the data. A maximum is an extreme-value summary, not the mean participation or duration of an event.')+'''<table><tr><th>Recording</th><th>Peak channels</th><th>Peak fraction</th><th>Peak window start (s)</th><th>Median of per-second maxima</th></tr>'''+facts+'''</table></section>'''+raw_section+'''<section><h2>What passed independent checks</h2><p>Recomputed every per-second peak window plus 100 random windows and record endpoints per recording using a different algorithm: time-sorted event slices, unique channel IDs and direct quality predicates. Counts matched the stored tracks. All nine variants' event flags reconcile with saved interval unions; original event hashes and identities are unchanged.</p>'''+f'<p>Historical review cross-check: {len(matched)} of {len(labels)} labels match current adaptive detections exactly, including {len(plausible)} plausible-eAP labels. Per-variant overlaps are saved in labels.json. Fixed-only or shifted/unmatched historical events are not treated as unflagged. This deliberately selected, small set cannot certify preservation of genuine spikes near the newly flagged disturbances.</p>'+'''<p>None of the 26 exactly matched plausible-eAP examples is flagged by any of the nine variants. This is reassuring for those examples, but does not establish specificity at warning boundaries or in newly flagged episodes.</p><p>Observed changes in flagged counts are not accuracy improvements by themselves. No event was deleted, no detection threshold was changed, and no new default was adopted.</p></section><section><h2>Next decision</h2><p>Keep separate evidence for a narrow coincidence core and wider surrounding warning intervals while reviewing their selectivity. Inspect raw traces for newly flagged episodes and plausible spikes near warning boundaries before choosing one setting or any exclusion policy. A baseline or broadband signal check would provide complementary evidence; the existing partial signal-based coverage must not be interpreted as a negative result elsewhere.</p><p>Outputs include PNG/PDF plots, per-second numeric JSON with support counts and peak locations, historical-label matches, audit summary and input/output hashes. Rebuild with <code>.venv/bin/python analysis/review_coincidence_independent.py</code>; event/quality plots need no raw source; additional raw panels require the original recordings.</p></section></main></html>'''
    (OUT/'report.html').write_text(page)
    (OUT/'per_second_maxima.json').write_text(json.dumps(allrows,indent=2)+'\n')
    (OUT/'labels.json').write_text(json.dumps({'summary':label_summary,'events':label_rows},indent=2)+'\n')
    (OUT/'review.json').write_text(json.dumps(review,indent=2)+'\n')
    (OUT/'manifest.json').write_text(json.dumps({'generator_sha256':sha256(__file__),'input_sha256':inputs,'files':{str(p.relative_to(OUT)):sha256(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='manifest.json'}},indent=2)+'\n')
    print(json.dumps({'review':review,'label_summary':label_summary},indent=2))

if __name__=='__main__':main()
