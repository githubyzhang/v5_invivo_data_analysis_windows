"""Review frozen candidate coincidence annotations and selected source traces."""
from pathlib import Path
import base64,html,json,os,sys
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/invivo-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analysis.pilot import moving_average
from analysis.candidate_coincidence import sha256
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/candidate_coincidence_review'


def main():
    summaries={r:json.loads((OUT/f'extra{r}/summary.json').read_text()) for r in (4,5)}
    assert summaries[4]['variants']['w5ms_q50']['flagged_candidates']==0
    assert summaries[5]['variants']['w5ms_q50']['flagged_candidates']==19158
    assert summaries[5]['variants']['w5ms_q50']['interval_count']==13
    selections=[];audit=[]
    fig,axes=plt.subplots(2,1,figsize=(12,7),layout='constrained')
    for rec,ax in zip((4,5),axes):
        with h5py.File(OUT/f'extra{rec}/annotations.h5','r') as f:
            a=f['tracks/w5ms/active_channels'][:];e=f['tracks/w5ms/eligible_channels'][:]
            ratio=np.divide(a,e,out=np.full(len(a),np.nan),where=e>=1024)
            # Per-second maxima are for display only; detection used every sample.
            maxima=[np.nanmax(ratio[t:t+10000]) for t in range(0,len(a),10000)]
            ax.plot(np.arange(len(maxima)),maxima,color='#087f8c',lw=1)
            ax.axhline(.5,color='#d3842c',ls='--',label='Exploratory 50% quorum')
            ax.set(title=f'extra_{rec}: maximum 5 ms coincidence fraction in each nominal second',ylabel='Distinct active / eligible channels',ylim=(0,1))
            ax.legend(loc='upper right');ax.set_xlabel('Nominal time (s)')
    fig.savefig(OUT/'overview.png',dpi=160);plt.close(fig)
    for rec in (4,5):
        folder=OUT/f'extra{rec}'
        protocol=json.loads((folder/'protocol.json').read_text())
        cfg=protocol['source_config'];n=cfg['shape'][1];fs=cfg['nominal_fs_hz']
        inp=Path(protocol['input'])
        assert sha256(inp)==protocol['input_sha256']
        with h5py.File(inp,'r') as d,h5py.File(folder/'annotations.h5','r') as f:
            ch=d['spikes/channel_id'][:];ts=d['spikes/sample_index'][:].astype(np.int64)
            np.testing.assert_array_equal(ch,f['events/channel_id'][:]);np.testing.assert_array_equal(ts,f['events/sample_index'][:])
            valid=d['quality/valid_noise_window'][:];ref=d['quality/reference_eligible'][:]
            guards=d['quality/flat_guard_intervals'][:];offset=d['spikes/channel_offsets'][:]
            eligible_ranges=[guards[guards[:,0]==c,1:].astype(np.int64) for c in range(len(valid))]
            rng=np.random.default_rng(20261122)
            for ms in (1,5,10):
                width=ms*10;g=f[f'tracks/w{ms}ms'];act=g['active_channels'][:];elig=g['eligible_channels'][:]
                starts=np.r_[rng.integers(0,len(act),20),np.argmax(np.divide(act,elig,out=np.zeros(len(act),float),where=elig>=1024)),0,len(act)-1]
                # Independent direct sample/window checks, not interval sweep.
                for start in starts:
                    start=int(start);stop=start+width;nc=dc=0
                    for c in range(len(valid)):
                        ok=bool(ref[c]) and start>=cfg['physical_edge_exclusion_samples'][0] and stop<=n-cfg['physical_edge_exclusion_samples'][1]
                        ok=ok and valid[c,start//fs:(stop-1)//fs+1].all()
                        rr=eligible_ranges[c]
                        ok=ok and not np.any((rr[:,0]<stop)&(rr[:,1]>start))
                        if ok:
                            dc+=1;t=ts[int(offset[c]):int(offset[c+1])]
                            nc+=int(np.any((t>=start)&(t<stop)))
                    assert (nc,dc)==(act[start],elig[start]),(rec,ms,start,nc,dc)
                # Roundtrip every stored warning against independently expanded intervals.
                for q in (25,50,75):
                    group=f[f'variants/w{ms}ms_q{q}'];mask=np.zeros(n,bool)
                    for a,b in group['intervals'][:]:mask[int(a):int(b)]=True
                    np.testing.assert_array_equal(group['event_warning'][:],mask[ts])
                audit.append({'recording':rec,'width_ms':ms,'independent_window_counts_checked':len(starts),'event_alignment':'exact','warning_interval_roundtrip':'passed'})
            a=f['tracks/w5ms/active_channels'][:];e=f['tracks/w5ms/eligible_channels'][:]
            score=np.divide(a,e,out=np.full(len(a),-1.),where=e>=1024)
            centers=[('strongest_5ms',int(np.argmax(score))+25)]
            if rec==5:
                lo,hi=154*fs,155*fs
                centers += [('episode_154_155',lo+int(np.argmax(score[lo:hi]))+25),('episode_276887',2768870)]
            rawpath=Path(cfg['source'])
            stat=rawpath.stat()
            assert (stat.st_size,stat.st_mtime_ns)==(cfg['source_size_bytes'],cfg['source_mtime_ns'])
            with h5py.File(rawpath,'r') as raw:
                for tag,center in centers:
                    start=max(100,center-500);stop=min(n-100,center+500)
                    eventmask=(ts>=center-25)&(ts<center+25)
                    candidates=np.unique(ch[eventmask])
                    if not len(candidates):candidates=np.unique(ch[(ts>=start)&(ts<stop)])
                    chosen=candidates[np.unique(np.linspace(0,len(candidates)-1,min(6,len(candidates))).astype(int))]
                    data=raw['signals'][chosen.tolist(),start-100:stop+100].astype(float)
                    t=(np.arange(start,stop)-center)/10
                    fig,axes=plt.subplots(3,1,figsize=(12,9),sharex=True,layout='constrained')
                    near=(ts>=start)&(ts<stop)
                    axes[0].scatter((ts[near]-center)/10,ch[near],s=2,color='#123f59',rasterized=True)
                    axes[0].set(ylabel='Global channel ID',ylim=(-10,2058),title=f'extra_{rec}: {center/fs:.4f} nominal s • {tag}')
                    intervals=f['variants/w5ms_q50/intervals'][:]
                    for x,y in intervals:
                        if x<stop and y>start:
                            for ax in axes:ax.axvspan((max(int(x),start)-center)/10,(min(int(y),stop)-center)/10,color='#edb768',alpha=.3)
                    thresholds=d['noise/threshold'][:]
                    for k,c in enumerate(chosen):
                        trace=data[k,100:-100];r=(data[k]-moving_average(data[k],50))[100:-100]
                        scale=np.percentile(trace,95)-np.percentile(trace,5)
                        if not np.isfinite(scale) or scale<=0:scale=1
                        axes[1].plot(t,(trace-np.median(trace))/scale+3*k,lw=.65)
                        th=thresholds[c,np.arange(start,stop)//fs]
                        axes[2].plot(t,r/th+6*k,lw=.65)
                        axes[2].axhline(6*k-1,color='gray',ls=':',lw=.6)
                        ix=np.flatnonzero((ch==c)&near)
                        axes[2].scatter((ts[ix]-center)/10,(r/th)[ts[ix]-start]+6*k,s=15,color='#cc403c')
                    axes[1].set_yticks(np.arange(len(chosen))*3,chosen);axes[1].set_ylabel('Raw, centered/scaled\nchannel ID + display offset')
                    axes[2].set_yticks(np.arange(len(chosen))*6,chosen);axes[2].set_ylabel('MA50 residual / threshold\nchannel ID + display offset');axes[2].set_xlabel('Time relative to center (ms)')
                    name=f'extra{rec}_{tag}.png';fig.savefig(OUT/name,dpi=150);plt.close(fig)
                    np.savez_compressed(OUT/f'extra{rec}_{tag}_traces.npz',channel_id=chosen,raw_with_100_sample_context=data,start_sample=start,stop_sample=stop,center_sample=center)
                    selections.append({'recording':rec,'tag':tag,'center_sample':center,'channels':chosen.tolist(),'image':name,'selection':'global maximum 5ms fraction, maximum within pre-existing 154–155 s episode, or pre-existing 276.887 s episode; six evenly ranked event-channel IDs, not waveform appearance','source':str(rawpath),'source_size':stat.st_size,'source_mtime_ns':stat.st_mtime_ns})
            assert (rawpath.stat().st_size,rawpath.stat().st_mtime_ns)==(stat.st_size,stat.st_mtime_ns)
        assert sha256(inp)==protocol['input_sha256']
    def image(name,caption):
        data=base64.b64encode((OUT/name).read_bytes()).decode()
        return f'<figure><img src="data:image/png;base64,{data}" alt="{html.escape(caption)}"><figcaption>{caption}</figcaption></figure>'
    rows=''
    for rec,s in summaries.items():
        for key,v in s['variants'].items():
            rows+=f'<tr><td>extra_{rec}</td><td>{key}</td><td>{v["flagged_candidates"]:,}</td><td>{v["interval_count"]}</td><td>{v["flagged_seconds"]:.4f}</td><td>{v["assessed_seconds"]:.4f}</td></tr>'
    figures=''.join(image(s['image'],f'extra_{s["recording"]}: {s["tag"]}. Orange: primary coincidence windows; red markers: saved detections. Raw traces are individually centered and scaled only for display. Residuals are divided by their saved adaptive threshold; dotted lines indicate −1. Channels are evenly selected from event-channel IDs, not selected for convincing waveforms.') for s in selections)
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Candidate coincidence review</title><style>body{background:#edf3f5;color:#193846;font:17px/1.65 system-ui;margin:0}main{max-width:1100px;margin:auto;padding:30px}section,header{background:white;padding:28px;margin:20px 0;border-radius:12px}header{background:#143f50;color:white}h1{font-size:36px;line-height:1.2}h2{color:#087881}img{width:100%}figure{margin:24px 0}figcaption{font-size:14px;color:#516c76}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:9px;border-bottom:1px solid #d6e1e6;text-align:left}.note{background:#fff0d1;padding:18px}code{overflow-wrap:anywhere}@media(max-width:650px){main{padding:10px}section,header{padding:15px}table{display:block;overflow:auto}}</style><main><header><small>22 NOVEMBER 2026 · ANNOTATION-ONLY EVALUATION</small><h1>Widespread candidate coincidence</h1><p>A third warning method across complete extra_4 and extra_5 event lists.</p></header>
<section><h2>Result and interpretation</h2><p>The exploratory primary rule—at least 50% of eligible channels with candidates in a sliding 5 ms window—flags <strong>13 intervals and 19,158 candidates in extra_5</strong>, spanning a union of 0.1270 nominal seconds. That is approximately 11.1% of its saved candidates. It flags no intervals in extra_4.</p><p>All primary extra_5 flags lie outside the older 35-second shared-warning assessment. This is additional assessment coverage, <strong>not evidence that the older methods missed those events</strong>: those times were not evaluated by them. Within previously assessed time, the new primary flags do not overlap the old shared20 warnings. All original candidates remain saved.</p><div class="note">These are widespread candidate coincidences, not confirmed artifacts or neuron-level synchrony. No event deletion, threshold changes or reference subtraction was performed. A zero warning count does not establish clean data.</div></section>
<section><h2>Exact rule, fixed before this evaluation</h2><p>Evaluate every integer sample start for full half-open windows [start, start + width). Count distinct channels with at least one saved event; multiple events on one channel count once. A channel enters both numerator and denominator only if its entire window is observable under the original detector’s noise-window validity, calibration eligibility, flat guards and physical edge exclusions.</p><p>Require at least 1,024 eligible channels. Evaluate 1/5/10 ms widths and 25/50/75% quorums; primary is 5 ms / 50%. These are exploratory review settings, not calibrated false-positive controls. The warning interval is the union of qualifying windows, with <strong>no extra padding</strong>. Overlapping windows can form longer intervals. A candidate is annotated if its sample lies in that union. Availability means at least one sufficiently supported window covers the sample.</p><p>Nominal fs is 10,000 Hz; physical fs remains 10,080 Hz. The original 5 ms per-channel detector spacing remains part of the input and limits what this method can observe. Threshold inflation can hide candidates and reduce coincidence.</p></section>'''+image('overview.png','Full-recording display uses per-second maxima of sample-stride 5 ms window fractions. The plotted line is not itself the detector binning.')+'''
<section><h2>Coverage and sensitivity</h2><p>Primary assessment covers 299.7275/300 seconds and 115,584/115,992 candidates in extra_4, versus 299.9951 seconds and all 173,029 candidates in extra_5. The unavailable time reflects filter edges and insufficient fully eligible channels. This does not complete full-recording baseline/broadband assessment; those remain separately partial.</p><p>The strongest extra_4 window reaches 405/2,044 channels (19.8%): visibly widespread activity can remain below a global majority threshold. The strongest extra_5 window reaches 1,981/2,045 (96.9%), near 79.85 s. Different window widths and quorums materially change flagged counts; no tuning was performed after observing these outcomes.</p><table><tr><th>Recording</th><th>Variant</th><th>Flagged candidates</th><th>Intervals</th><th>Flagged seconds</th><th>Assessed seconds</th></tr>'''+rows+'''</table><p>Variant counts overlap and must not be added. Primary extra_5 flags intersect 259.3917 usable channel-seconds; this is potential exposure affected by a hypothetical exclusion, not exposure actually removed. If exclusions are ever adopted, both events and exposure denominators must change consistently.</p></section>
<section><h2>Raw-signal review panels</h2><p>Selections are deterministic: strongest 5 ms fraction in each recording, strongest window within the previously identified extra_5 154–155 s episode, and the pre-existing 276.887 s episode. These are diagnostic selections, not a random accuracy sample. In the selected extra_5 traces, several negative deflections and surrounding waveform features align across widely separated channel IDs; this supports investigating shared contamination, without proving its physical cause. The extra_4 example shows coherent candidates below the majority rule, illustrating its limited sensitivity. The panels allow comparison of shared waveforms, baseline movement and narrow transients; they do not assign final artifact labels.</p>'''+figures+'''</section>
<section><h2>How this joins the workflow</h2><p>Baseline and broadband warnings use the signal; this third method uses thresholded event coincidence. Their evidence and availability remain separate. Original v1 spike files are unchanged. Each recording has an <code>annotations.h5</code> sidecar with identical event order/identity, per-window counts, availability, nine variant masks and interval lists. Input hashes bind each sidecar to its exact detection file. No coincidence field is silently added to the original schema.</p><p>Independent direct calculations check 23 windows per width per recording, including the peak and recording endpoints. Every event identity and warning-to-interval assignment is reconciled. The original usable exposure is reconstructed exactly, and input hashes match before/after. Synthetic tests cover duplicate-channel counting, bin boundaries, partial support and half-open edges. These checks establish implementation consistency, not biological accuracy.</p><p><strong>Next:</strong> user review of the raw panels and warning selectivity; consider a separately specified per-shank coincidence criterion if global majority misses spatially restricted disturbances. Complete signal-based full-recording warnings in a separate round; preserve the frozen evaluation here.</p><p>Reproduce annotations with <code>analysis/candidate_coincidence.py --input PATH --output NEW_FOLDER</code>; rebuild this project report with <code>.venv/bin/python analysis/report_candidate_coincidence.py</code>. Existing annotation folders are never overwritten. Report rebuild replaces its generated figures/HTML. Source recordings are required only for the raw panels.</p></section></main></html>'''
    (OUT/'report.html').write_text(page)
    (OUT/'selection.json').write_text(json.dumps(selections,indent=2)+'\n')
    (OUT/'validation.json').write_text(json.dumps({'direct_count_audits':audit,'original_inputs_unchanged':True,'raw_source_metadata_unchanged':True,'scientific_labels':'none assigned','browser_layout':'not verified','figure_visual_review':'overview and four waveform panels inspected; no final artifact labels assigned'},indent=2)+'\n')
    (OUT/'report_manifest.json').write_text(json.dumps({'generator_sha256':sha256(__file__),'files':{str(p.relative_to(OUT)):sha256(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='report_manifest.json'}},indent=2)+'\n')
    print(OUT/'report.html')

if __name__=='__main__':main()
