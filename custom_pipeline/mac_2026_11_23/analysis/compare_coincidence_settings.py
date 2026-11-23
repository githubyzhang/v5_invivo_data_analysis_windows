"""Compare user-requested 3ms/25% against frozen 5ms variants, without redetection."""
from pathlib import Path
import json,sys,os,base64
os.environ.setdefault("MPLCONFIGDIR","/private/tmp/invivo-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import h5py
import numpy as np
from analysis.candidate_coincidence import sha256
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/candidate_coincidence_3ms25'

def extra5_figures(result):
    """Static scientific plots from saved annotations; no new detection."""
    labels=['5 ms / 50%','3 ms / 50%','5 ms / 25%','3 ms / 25%']
    keys=['w5ms_q50','w3ms_q50','w5ms_q25','w3ms_q25']
    colors=['#46699d','#a3b5ce','#83b9b2','#008779']
    def save(fig,name):
        fig.savefig(OUT/(name+'.png'),dpi=160)
        fig.savefig(OUT/(name+'.pdf'))
        plt.close(fig)
    v=result['variants'];over=result['event_overlap_with_5ms50']
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    for ax,field,title in zip(axes,['flagged_candidates','flagged_seconds'],['Flagged candidates','Total warning time (ms)']):
        values=[v[k][field]*(1000 if field=='flagged_seconds' else 1) for k in keys]
        ax.barh(labels,values,color=colors);ax.invert_yaxis();ax.set_title(title);ax.set_xlim(0,max(values)*1.26)
        for i,x in enumerate(values):ax.text(x+max(values)*.02,i,f'{x:,.0f}' if field=='flagged_candidates' else f'{x:.1f}',va='center')
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('extra_5 • parameter effects on candidates and warning duration',fontsize=14)
    save(fig,'extra5_parameter_effects')
    with h5py.File(OUT/'extra5/annotations.h5','r') as nf,h5py.File(ROOT/'results/candidate_coincidence_review/extra5/annotations.h5','r') as of:
        times=nf['events/sample_index'][:].astype(int);channels=nf['events/channel_id'][:]
        masks={k:(nf if k.startswith('w3') else of)[f'variants/{k}/event_warning'][:].astype(bool) for k in keys}
        a=masks['w5ms_q50'];b=masks['w3ms_q25']
        categories=[a&b,b&~a,a&~b]
        names=['Both settings','New only: 3 ms / 25%','Previous only: 5 ms / 50%']
        palette=['#63788e','#008779','#d18236']
        fig,axes=plt.subplots(2,1,figsize=(12,7),layout='constrained',gridspec_kw={'height_ratios':[1,2]})
        counts=[int(x.sum()) for x in categories]
        axes[0].barh(names,counts,color=palette);axes[0].invert_yaxis();axes[0].set_xlim(0,max(counts)*1.2)
        for i,x in enumerate(counts):axes[0].text(x+250,i,f'{x:,}',va='center')
        axes[0].set_title('Exact event overlap (same channel and sample index)')
        for mask,name,color in zip(categories,names,palette):
            hist=np.histogram(times[mask]/10000,bins=np.arange(301))[0]
            axes[1].plot(np.arange(300)+.5,hist,label=name,color=color,lw=1.2)
        axes[1].set(xlabel='Nominal time (s)',ylabel='Candidates per 1 s display bin',title='Where candidate annotations differ across the recording')
        axes[1].legend(fontsize=9)
        for ax in axes:ax.spines[['top','right']].set_visible(False)
        save(fig,'extra5_overlap_timeline')
        # Select greatest additions and greatest losses in fixed 100 ms bins.
        selected=[]
        for category,label in [(categories[1],'Largest additions'),(categories[2],'Largest losses')]:
            hist=np.bincount(times[category]//1000,minlength=3000)
            index=int(np.argmax(hist));selected.append((index*1000,index*1000+1000,label,int(hist[index])))
        fig,axes=plt.subplots(3,2,figsize=(14,9),layout='constrained',sharex='col')
        for col,(start,stop,label,count) in enumerate(selected):
            near=(times>=start)&(times<stop)
            axes[0,col].scatter((times[near]-start)/10,channels[near],s=3,color='#d5dde1',label='Other candidates')
            for mask,name,color in zip(categories,names,palette):
                use=near&mask
                axes[0,col].scatter((times[use]-start)/10,channels[use],s=5,color=color,label=name)
            axes[0,col].set(title=f'{label}: {start/10000:.1f}–{stop/10000:.1f} s ({count:,} changed)',ylabel='Global channel ID',ylim=(-20,2070))
            for width,f,color in [(3,nf,'#008779'),(5,of,'#46699d')]:
                g=f[f'tracks/w{width}ms'];lo=max(0,start-width*10);hi=min(len(g['active_channels']),stop)
                active=g['active_channels'][lo:hi];eligible=g['eligible_channels'][lo:hi]
                ratio=np.divide(active,eligible,out=np.full(len(active),np.nan),where=eligible>=1024)
                centers=(np.arange(lo,hi)+(width*10-1)/2-start)/10
                axes[1,col].plot(centers,ratio,color=color,label=f'{width} ms windows')
            for q in (.25,.5):axes[1,col].axhline(q,color='gray',ls=':',lw=1)
            axes[1,col].set(ylabel='Active / eligible channels',ylim=(0,1));axes[1,col].legend(fontsize=9)
            for row,k in enumerate(keys):
                f=nf if k.startswith('w3') else of
                for x,y in f[f'variants/{k}/intervals'][:]:
                    x,y=max(int(x),start),min(int(y),stop)
                    if x<y:axes[2,col].broken_barh([((x-start)/10,(y-x)/10)],(row-.3,.6),facecolors=colors[row])
            axes[2,col].set(yticks=range(4),yticklabels=labels,xlabel=f'Milliseconds after {start/10000:.1f} s',xlim=(0,100),ylim=(3.6,-.6))
        axes[0,0].legend(loc='lower left',fontsize=7,markerscale=2)
        fig.suptitle('extra_5 • examples selected by changed-event counts, not waveform appearance',fontsize=14)
        save(fig,'extra5_difference_examples')
    (OUT/'figure_selection.json').write_text(json.dumps({'selection':'greatest new-only and previous-only candidate counts in fixed 100 ms bins; earliest bin on ties','examples':[{'start_sample':a,'stop_sample':b,'category':c,'changed_candidates':d} for a,b,c,d in selected],'curve_x':'window center; flags are unions of full qualifying windows','raw_waveforms':'not re-read in this comparison'},indent=2)+'\n')
    def embed(name,caption):
        data=base64.b64encode((OUT/(name+'.png')).read_bytes()).decode()
        return f'<figure><img src="data:image/png;base64,{data}" alt="{caption}"><figcaption>{caption}</figcaption></figure>'
    return '<section><h2>Visual comparison: extra_5</h2>'+embed('extra5_parameter_effects','The four settings separate window-width and quorum effects. Warning time is a union, not a sum over overlapping windows.')+embed('extra5_overlap_timeline','Categories are mutually exclusive: both, new-only, and previous-only. One-second bins are for display only; the method evaluates every sample start. Neither-setting candidates are omitted from these counts.')+embed('extra5_difference_examples','Top: event rasters colored by annotation change. Middle: 3 ms and 5 ms coincidence fractions plotted at window centers, with 25% and 50% thresholds. Bottom: exact warning-interval unions. Examples use fixed 100 ms bins with the most newly flagged and no-longer-flagged events. These are annotation comparisons, not raw-waveform artifact classifications.')+'</section>'


def main():
    results={};rows=''
    for rec in (4,5):
        new=OUT/f'extra{rec}';old=ROOT/f'results/candidate_coincidence_review/extra{rec}'
        ns=json.loads((new/'summary.json').read_text());os=json.loads((old/'summary.json').read_text())
        np_=json.loads((new/'protocol.json').read_text());op=json.loads((old/'protocol.json').read_text())
        assert np_['input_sha256']==op['input_sha256']==sha256(np_['input'])
        variants={k:(ns if k.startswith('w3') else os)['variants'][k] for k in ['w5ms_q50','w3ms_q50','w5ms_q25','w3ms_q25']}
        with h5py.File(new/'annotations.h5','r') as nf,h5py.File(old/'annotations.h5','r') as of,h5py.File(np_['input'],'r') as src:
            np.testing.assert_array_equal(nf['events/sample_index'][:],of['events/sample_index'][:])
            np.testing.assert_array_equal(nf['events/channel_id'][:],of['events/channel_id'][:])
            masks={k:(nf if k.startswith('w3') else of)[f'variants/{k}/event_warning'][:].astype(bool) for k in variants}
            wanted=masks['w3ms_q25'];base=masks['w5ms_q50']
            overlap={'both':int((wanted&base).sum()),'new_only':int((wanted&~base).sum()),'baseline_only':int((base&~wanted).sum())}
            times=nf['events/sample_index'][:].astype(int);channels=nf['events/channel_id'][:]
            spans=nf['variants/w3ms_q25/intervals'][:]
            intervals=[{'start_s':int(a)/10000,'stop_s':int(b)/10000,'candidates':int(((times>=a)&(times<b)).sum())} for a,b in spans]
            reconstructed=np.zeros(len(times),bool)
            for a,b in spans:reconstructed|=(times>=a)&(times<b)
            np.testing.assert_array_equal(wanted,reconstructed)
            # Independent direct count checks from original quality arrays.
            active=nf['tracks/w3ms/active_channels'][:];eligible=nf['tracks/w3ms/eligible_channels'][:]
            score=np.divide(active,eligible,out=np.zeros(len(active),float),where=eligible>=1024)
            starts=np.r_[0,len(active)-1,np.argmax(score),np.random.default_rng(3).integers(0,len(active),20)]
            cfg=np_['source_config'];valid=src['quality/valid_noise_window'][:];ref=src['quality/reference_eligible'][:]
            guards=src['quality/flat_guard_intervals'][:];offsets=src['spikes/channel_offsets'][:]
            bychannel=[guards[guards[:,0]==c,1:] for c in range(len(valid))]
            for a in starts:
                a=int(a);b=a+30;num=den=0
                for c in range(len(valid)):
                    g=bychannel[c]
                    ok=ref[c] and a>=cfg['physical_edge_exclusion_samples'][0] and b<=cfg['shape'][1]-cfg['physical_edge_exclusion_samples'][1]
                    ok=ok and valid[c,a//10000:(b-1)//10000+1].all() and not ((g[:,0]<b)&(g[:,1]>a)).any()
                    if ok:
                        den+=1;t=times[int(offsets[c]):int(offsets[c+1])];num+=int(((t>=a)&(t<b)).any())
                assert (num,den)==(active[a],eligible[a])
            result={'variants':variants,'event_overlap_with_5ms50':overlap,'requested_intervals':intervals,'independent_windows_checked':len(starts),'input_sha256':np_['input_sha256']}
            results[f'extra{rec}']=result
            for k,v in variants.items():
                rows+=f'<tr><td>extra_{rec}</td><td>{k}</td><td>{v["flagged_candidates"]:,}</td><td>{v["interval_count"]}</td><td>{v["flagged_seconds"]:.4f}</td><td>{v["potential_usable_channel_seconds_affected"]:.4f}</td></tr>'
    figures=extra5_figures(results['extra5'])
    detail=''
    for name,r in results.items():
        o=r['event_overlap_with_5ms50'];v=r['variants']['w3ms_q25']
        detail+=f'<h3>{name}</h3><p>Requested-setting assessment: {v["assessed_seconds"]:.4f} nominal seconds. Compared with 5 ms / 50%: <b>{o["both"]:,} candidates flagged by both</b>, {o["new_only"]:,} newly flagged, and {o["baseline_only"]:,} previously flagged candidates no longer flagged.</p>'
        detail+=f'<p>Requested flags outside old signal-based assessment: {v["flagged_candidates_outside_old_assessment"]:,}; overlapping old shared20 warnings: {v["flagged_candidates_also_shared20"]:,}. Outside old coverage does not mean the older methods missed those events.</p>'
        detail+='<details><summary>Requested-setting intervals (nominal seconds)</summary><table><tr><th>Start</th><th>Stop, exclusive</th><th>Candidates</th></tr>'
        for x in r['requested_intervals']:detail+=f'<tr><td>{x["start_s"]:.4f}</td><td>{x["stop_s"]:.4f}</td><td>{x["candidates"]:,}</td></tr>'
        detail+='</table></details>'
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>3 ms / 25% coincidence comparison</title><style>body{font:17px/1.65 system-ui;background:#eef4f5;color:#203e49;margin:0}main{max-width:1050px;margin:auto;padding:30px}section{background:white;padding:28px;margin:20px 0;border-radius:12px}h1,h2{color:#096c78}figure{margin:24px 0}img{width:100%;height:auto}figcaption{font-size:14px;color:#526d76}table{border-collapse:collapse;width:100%;font-size:15px}td,th{padding:10px;border-bottom:1px solid #dce6e9;text-align:left}.note{background:#fff0d3;padding:18px}@media(max-width:650px){main{padding:10px}section{padding:14px}table{display:block;overflow:auto}}</style><main><h1>Candidate coincidence: 3 ms / 25%</h1><p>User-requested sensitivity comparison · 22 November 2026</p><section><h2>What changed</h2><p>Compared the requested 3 ms sliding window / at least 25% of eligible channels against the previous exploratory 5 ms / 50% rule. The intermediate settings 3 ms / 50% and 5 ms / 25% separate the effect of window width from quorum.</p><p>All other rules remain fixed: one-sample stride, distinct channels counted once, full-window observability, minimum 1,024 eligible channels, no added guard, and annotation only. The original events, old warning files and detector defaults are unchanged. This follow-up was requested after seeing the first results; it is not held-out validation.</p><div class="note">A shorter window asks for tighter coincidence; a lower quorum accepts less widespread participation. Because the denominator also depends on full-window eligibility, the combined result should be measured rather than assumed. These are warnings, not confirmed artifact removals.</div></section><section><h2>Matched parameter comparison</h2><table><tr><th>Recording</th><th>Setting</th><th>Flagged candidates</th><th>Intervals</th><th>Union seconds</th><th>Potential affected channel-seconds</th></tr>'''+rows+'''</table><p>Potential affected exposure is hypothetical: no time or events were excluded. Counts overlap across settings and must not be added. Intervals are the union of all qualifying windows, not necessarily one window wide.</p></section>'''+figures+'''<section><h2>Event overlap and interval locations</h2>'''+detail+'''</section><section><h2>Verification and interpretation</h2><p>Original event hashes and row identities match both rounds. Every requested warning is reconciled with its saved intervals. Twenty-three windows per recording, including the strongest and recording endpoints, were independently recounted directly from the original event and quality arrays. All input files remain unchanged.</p><p>New extra_4 warnings should not be expected if its maximum participation stays below 25%; zero warnings do not imply clean data. Differences in extra_5 indicate sensitivity to parameter choices, not improved accuracy. This report does not introduce new raw-waveform labels; the preceding report retains its original raw panels.</p><p>See comparison.json for numerical evidence, each recording’s protocol.json for provenance, and annotations.h5 for aligned event warnings. No new default has been adopted.</p></section></main></html>'''
    (OUT/'report.html').write_text(page)
    (OUT/'comparison.json').write_text(json.dumps(results,indent=2)+'\n')
    (OUT/'manifest.json').write_text(json.dumps({'generator_sha256':sha256(__file__),'files':{str(p.relative_to(OUT)):sha256(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='manifest.json'}},indent=2)+'\n')
    print(json.dumps({k:{'requested':v['variants']['w3ms_q25'],'overlap':v['event_overlap_with_5ms50']} for k,v in results.items()},indent=2))

if __name__=='__main__':main()
