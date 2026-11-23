"""Frozen low-quorum grid review; original events and warnings remain unchanged."""
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
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/coincidence_low_quorum'
KEYS=[f'w{w}ms_q{q}' for w in (1,3,5) for q in (5,10,25)]
LABELS=[f'{w} ms / {q}%' for w in (1,3,5) for q in (5,10,25)]+['5 ms / 50% reference']

def save(fig,name):
    fig.savefig(OUT/f'{name}.png',dpi=150)
    fig.savefig(OUT/f'{name}.pdf')
    plt.close(fig)

def main():
    evidence={};selections=[];audits=[];sections=[]
    prior_selection=json.loads((ROOT/'results/candidate_coincidence_review/selection.json').read_text())
    for rec in (4,5):
        folder=OUT/f'extra{rec}';old=ROOT/f'results/candidate_coincidence_review/extra{rec}'
        summary=json.loads((folder/'summary.json').read_text());protocol=json.loads((folder/'protocol.json').read_text())
        old_summary=json.loads((old/'summary.json').read_text());old_protocol=json.loads((old/'protocol.json').read_text())
        assert protocol['input_sha256']==old_protocol['input_sha256']==sha256(protocol['input'])
        variants={**summary['variants'],'reference':old_summary['variants']['w5ms_q50']}
        with h5py.File(folder/'annotations.h5','r') as f,h5py.File(old/'annotations.h5','r') as of,h5py.File(protocol['input'],'r') as source:
            times=f['events/sample_index'][:].astype(int);channels=f['events/channel_id'][:];n=summary['recording_samples']
            for field in ('sample_index','channel_id'):
                np.testing.assert_array_equal(f[f'events/{field}'][:],of[f'events/{field}'][:])
                np.testing.assert_array_equal(f[f'events/{field}'][:],source[f'spikes/{field}'][:])
            masks={k:f[f'variants/{k}/event_warning'][:].astype(bool) for k in KEYS}
            masks['reference']=of['variants/w5ms_q50/event_warning'][:].astype(bool)
            spans={k:f[f'variants/{k}/intervals'][:].astype(int) for k in KEYS}
            spans['reference']=of['variants/w5ms_q50/intervals'][:].astype(int)
            valid=source['quality/valid_noise_window'][:];reference=source['quality/reference_eligible'][:]
            guard=source['quality/flat_guard_intervals'][:];offset=source['spikes/channel_offsets'][:]
            gch=[guard[guard[:,0]==c,1:] for c in range(len(valid))]
            cfg=protocol['source_config'];tracks={}
            for w in (1,3,5):
                active=f[f'tracks/w{w}ms/active_channels'][:];eligible=f[f'tracks/w{w}ms/eligible_channels'][:]
                ratio=np.divide(active,eligible,out=np.full(len(active),np.nan),where=eligible>=1024);tracks[w]=ratio
                starts=np.r_[0,len(active)-1,np.nanargmax(ratio),np.random.default_rng(22+w).integers(0,len(active),20)]
                for a in starts:
                    a=int(a);b=a+w*10;num=den=0
                    for c in range(len(valid)):
                        g=gch[c];ok=reference[c] and a>=cfg['physical_edge_exclusion_samples'][0] and b<=n-cfg['physical_edge_exclusion_samples'][1]
                        ok=ok and valid[c,a//10000:(b-1)//10000+1].all() and not ((g[:,0]<b)&(g[:,1]>a)).any()
                        if ok:
                            den+=1;t=times[int(offset[c]):int(offset[c+1])];num+=int(((t>=a)&(t<b)).any())
                    assert (num,den)==(active[a],eligible[a])
                audits.append({'recording':rec,'width_ms':w,'independent_windows':len(starts)})
                # Lower quorum must include every warning at higher quorum for fixed width.
                assert not (masks[f'w{w}ms_q25']&~masks[f'w{w}ms_q10']).any()
                assert not (masks[f'w{w}ms_q10']&~masks[f'w{w}ms_q5']).any()
            for key in KEYS:
                reconstructed=np.zeros(len(times),bool)
                for a,b in spans[key]:reconstructed|=(times>=a)&(times<b)
                np.testing.assert_array_equal(reconstructed,masks[key])
                assert int(masks[key].sum())==variants[key]['flagged_candidates']
            subset=(times>=1805974)&(times<1806974) if rec==4 else None
            if rec==5:
                with h5py.File(ROOT/'results/candidate_coincidence_3ms25/extra5/annotations.h5','r') as prev:
                    np.testing.assert_array_equal(times,prev['events/sample_index'][:])
                    subset=masks['reference']&~prev['variants/w3ms_q25/event_warning'][:].astype(bool)
                assert subset.sum()==195
            capture={k:int((mask&subset).sum()) for k,mask in masks.items()}
            overlap={k:{'both_reference':int((mask&masks['reference']).sum()),'new_only':int((mask&~masks['reference']).sum()),'reference_only':int((masks['reference']&~mask).sum())} for k,mask in masks.items()}
            # Existing variants must reproduce exactly, rather than merely similar totals.
            for k in ('w1ms_q25','w5ms_q25'):np.testing.assert_array_equal(masks[k],of[f'variants/{k}/event_warning'][:])
            with h5py.File(ROOT/f'results/candidate_coincidence_3ms25/extra{rec}/annotations.h5','r') as prev:
                np.testing.assert_array_equal(masks['w3ms_q25'],prev['variants/w3ms_q25/event_warning'][:])
            evidence[f'extra{rec}']={'variants':variants,'reference_overlap':overlap,'review_subset_size':int(subset.sum()),'review_subset_capture':capture,'input_sha256':protocol['input_sha256']}
            fig,axes=plt.subplots(1,2,figsize=(11,4.8),layout='constrained')
            for ax,field,title in zip(axes,['flagged_candidates','flagged_seconds'],['Flagged candidates','Warning union (milliseconds)']):
                grid=np.array([[variants[f'w{w}ms_q{q}'][field] for q in (5,10,25)] for w in (1,3,5)])
                if field=='flagged_seconds':grid*=1000
                ax.imshow(grid,cmap='YlGnBu',aspect='auto',vmin=0)
                for i in range(3):
                    for j in range(3):ax.text(j,i,f'{grid[i,j]:,.0f}' if field=='flagged_candidates' else f'{grid[i,j]:.1f}',ha='center',va='center',color='white' if grid[i,j]>.55*max(grid.max(),1) else '#173d4c')
                ax.set(xticks=range(3),xticklabels=['5%','10%','25%'],yticks=range(3),yticklabels=['1 ms','3 ms','5 ms'],xlabel='Eligible-channel quorum',ylabel='Sliding window',title=title)
            fig.suptitle(f'extra_{rec} • reference 5 ms / 50%: {variants["reference"]["flagged_candidates"]:,} candidates, {variants["reference"]["flagged_seconds"]*1000:.1f} ms',fontsize=13)
            save(fig,f'extra{rec}_grid')
            fig,axes=plt.subplots(2,1,figsize=(12,7),layout='constrained')
            for key,color in [('w1ms_q5','#008879'),('w1ms_q10','#cb882e'),('w5ms_q5','#5473a6'),('reference','#333333')]:
                hist=np.histogram(times[masks[key]]/10000,np.arange(301))[0]
                axes[0].plot(np.arange(300)+.5,hist,label=key,color=color,lw=1)
            axes[0].set(xlabel='Nominal time (s)',ylabel='Flagged candidates / 1 s display bin',title='Selected settings across the full recording');axes[0].legend(fontsize=9)
            axes[1].barh(LABELS,[capture[k] for k in KEYS+['reference']],color=['#008879']*9+['#687d92'])
            axes[1].invert_yaxis();axes[1].set_xlabel('Candidates in reviewed subset that receive a warning')
            axes[1].set_title(f'Review subset: {int(subset.sum())} candidates '+('(extra_4, 180.5974–180.6974 s)' if rec==4 else '(extra_5, previous-only 5 ms / 50%)'))
            for i,k in enumerate(KEYS+['reference']):axes[1].text(capture[k]+max(1,subset.sum()*.01),i,str(capture[k]),va='center',fontsize=9)
            axes[1].set_xlim(0,max(1,subset.sum())*1.18)
            save(fig,f'extra{rec}_coverage')
            # Explicit known example plus highest new-only 100 ms bin outside previous plotted views.
            known=1806474 if rec==4 else 1547500
            eligible_events=masks['w5ms_q5']&~masks['reference']
            excluded=[(x['center_sample']-500,x['center_sample']+500) for x in prior_selection if x['recording']==rec]
            if rec==5:excluded.extend([(799000,800000),(1547000,1548000)])
            bins=np.arange(3000);ok=np.ones(3000,bool)
            for a,b in excluded:ok &= ~((bins*1000<b)&((bins+1)*1000>a))
            hist=np.bincount(times[eligible_events]//1000,minlength=3000);hist[~ok]=-1
            ix=int(np.argmax(hist));novel=ix*1000+500
            cases=[('Previously reviewed',known),('Additional review example',novel)]
            fig,axes=plt.subplots(3,2,figsize=(14,10),layout='constrained',sharex='col')
            for col,(label,center) in enumerate(cases):
                a=center-500;b=center+500;near=(times>=a)&(times<b)
                axes[0,col].scatter((times[near]-center)/10,channels[near],s=4,color='#cbd5dd')
                for k,color,name in [('w5ms_q5','#94baba','5 ms / 5%'),('w1ms_q5','#008879','1 ms / 5%'),('reference','#df9037','Reference')]:
                    use=near&masks[k];axes[0,col].scatter((times[use]-center)/10,channels[use],s=5,color=color,label=name)
                axes[0,col].set(title=f'{label}: {center/10000:.4f} s',ylabel='Global channel ID',ylim=(-20,2070));axes[0,col].legend(fontsize=8)
                for w,color in [(1,'#008879'),(3,'#cb882e'),(5,'#5473a6')]:
                    lo=max(0,a-w*10);hi=min(len(tracks[w]),b)
                    axes[1,col].plot((np.arange(lo,hi)+(w*10-1)/2-center)/10,tracks[w][lo:hi],color=color,label=f'{w} ms')
                for q in (.05,.10,.25,.5):axes[1,col].axhline(q,ls=':',color='gray',lw=.7)
                axes[1,col].set(ylabel='Active / eligible channels',ylim=(0,.55 if rec==4 else 1));axes[1,col].legend(fontsize=8)
                for row,k in enumerate(KEYS+['reference']):
                    for x,y in spans[k]:
                        x,y=max(x,a),min(y,b)
                        if x<y:axes[2,col].broken_barh([((x-center)/10,(y-x)/10)],(row-.3,.6),facecolors='#008879' if k!='reference' else '#df9037')
                axes[2,col].set(yticks=range(10),yticklabels=LABELS,xlabel='Time relative to center (ms)',xlim=(-50,50),ylim=(9.6,-.6))
                selections.append({'recording':rec,'kind':label,'center_sample':center,'start_sample':a,'stop_sample':b,'additional_rule':'highest new-only event count for 5 ms/5% vs reference in fixed 100 ms bins excluding overlap with prior plotted windows; earliest tie','additional_bin_new_count':int(hist[ix])})
            fig.suptitle(f'extra_{rec} • event raster, centered window fractions and exact warning unions',fontsize=14)
            save(fig,f'extra{rec}_examples')
        assert sha256(protocol['input'])==protocol['input_sha256']
    def image(name,caption):
        data=base64.b64encode((OUT/f'{name}.png').read_bytes()).decode()
        return f'<figure><img src="data:image/png;base64,{data}" alt="{caption}"><figcaption>{caption}</figcaption></figure>'
    body=''
    for rec in (4,5):
        r=evidence[f'extra{rec}'];rows=''
        for k,v in r['variants'].items():
            o=r['reference_overlap'][k]
            rows+=f'<tr><td>{k}</td><td>{v["flagged_candidates"]:,}</td><td>{v["interval_count"]}</td><td>{v["flagged_seconds"]:.4f}</td><td>{o["new_only"]:,}</td><td>{o["reference_only"]:,}</td></tr>'
        body+=f'<section><h2>extra_{rec}</h2>'+image(f'extra{rec}_grid','Nine settings on identical saved events. Counts and warning duration are descriptive; neither measures detection accuracy.')+image(f'extra{rec}_coverage','Timeline bins are for display only. Review-subset counts are coverage of selected candidates, not confirmed artifact recovery. Settings overlap and must not be added.')+image(f'extra{rec}_examples','The second example is selected from a high-count additional interval outside previous plotted windows. Raster overlays emphasize selected settings; exact interval rows show all ten. No raw-waveform classification is assigned. Window-fraction curves are located at window centers; interval bars are full qualifying-window unions.')+'<details><summary>Full counts and reference overlap</summary><table><tr><th>Setting</th><th>Flagged candidates</th><th>Intervals</th><th>Seconds</th><th>New vs reference</th><th>Reference flags lost</th></tr>'+rows+'</table></details></section>'
    report='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Low-quorum coincidence review</title><style>body{font:17px/1.6 system-ui;background:#eef3f5;color:#213e4a;margin:0}main{max-width:1180px;margin:auto;padding:28px}section,header{padding:28px;background:white;margin:20px 0;border-radius:12px}header{background:#173e4d;color:white}h1{font-size:34px}h2{color:#007e80}img{width:100%;height:auto}figure{margin:25px 0}figcaption{font-size:14px;color:#536d77}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:9px;border-bottom:1px solid #dce5e9;text-align:left}.notice{background:#fff0cf;padding:18px}@media(max-width:650px){main{padding:10px}section,header{padding:14px}table{display:block;overflow:auto}}</style><main><header><h1>Candidate coincidence: lower channel quorums</h1><p>1, 3 and 5 ms × 5%, 10% and 25% · 5 ms / 50% reference · 22 November 2026</p></header><section><h2>Purpose and fixed rules</h2><p>The user identified the strongest extra_4 example and extra_5 previous-only events as artifact-like. This follow-up measures how the requested settings annotate those examples and what else they flag. These are user-informed review cases, not independent ground truth.</p><p>Every sample start is evaluated. Each channel counts once; it must be observable throughout the full half-open window. At least 1,024 eligible channels are required. Warnings are the union of qualifying windows, with no added padding. Nominal timing is 10,000 Hz; physical sampling remains 10,080 Hz.</p><div class="notice">Annotation only: no candidate removal, re-detection or source modification. No new default is adopted. Each sidecar contains nine variants aligned to the same original event order. Baseline/broadband signal-warning coverage remains separately limited.</div></section><section><h2>What this comparison establishes</h2><p>Lower quorums flag the previously unflagged extra_4 activity. The 1 ms rules produce narrower intervals and may leave nearby detections outside the warning. Wider low-quorum windows capture more candidates and more observation time; they do not demonstrate better specificity.</p><p>extra_4 flags range from zero at 25% to 714 at 5 ms / 5%. extra_5 ranges from 30,407 to 42,155 flags, versus 19,158 for the reference. Counts are channel-level candidates, not distinct neurons or confirmed artifacts.</p><p>The extra_4 review subset is every candidate in 180.5974–180.6974 s, centered on the earlier strongest example. The extra_5 review subset is the exact 195 events flagged by 5 ms / 50% but not by 3 ms / 25% in the preceding comparison. Neither subset labels every event as an artifact.</p></section>'''+body+'''<section><h2>Validation and next interpretation step</h2><p>Exact input hashes and event identities match the historical reference. All nine warning arrays reconcile with interval unions. Direct audits independently recount 23 windows per width and recording (138 total); fixed-width lower-quorum flags contain higher-quorum flags. The 1/5 ms 25% results and prior 3 ms / 25% reproduce their historical event masks exactly.</p><p>The additional examples are diagnostic high-count selections, not a held-out accuracy sample. Event-only plots cannot establish that genuine eAPs are unaffected. Raw-waveform and expert review of newly flagged events, including plausible spikes, is needed before selecting a default or considering exclusions. Adaptive thresholding and original 5 ms event spacing remain limitations of the coincidence evidence.</p><p>Rebuild with <code>.venv/bin/python analysis/report_low_quorum.py</code>. Numerical comparisons, selections and validation are saved alongside the report; each recording retains its own protocol and annotations. PNG/PDF figure copies are also available. No raw data access is required to reproduce this event-based review.</p></section></main></html>'''
    (OUT/'report.html').write_text(report)
    (OUT/'comparison.json').write_text(json.dumps(evidence,indent=2)+'\n')
    (OUT/'selection.json').write_text(json.dumps(selections,indent=2)+'\n')
    (OUT/'validation.json').write_text(json.dumps({'direct_count_audits':audits,'input_hashes_unchanged':True,'historical_25percent_masks':'exact match','warning_intervals_and_event_identity':'passed','browser_layout':'not verified'},indent=2)+'\n')
    (OUT/'manifest.json').write_text(json.dumps({'generator_sha256':sha256(__file__),'files':{str(p.relative_to(OUT)):sha256(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='manifest.json'}},indent=2)+'\n')
    for r,e in evidence.items():print(r,'review subset',e['review_subset_size'],e['review_subset_capture'])

if __name__=='__main__':main()
