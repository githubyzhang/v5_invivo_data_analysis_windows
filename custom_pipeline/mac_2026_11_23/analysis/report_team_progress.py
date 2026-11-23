"""Five-figure team update from frozen event files and read-only source excerpts."""
from pathlib import Path
import sys, os, json, hashlib, base64, subprocess
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/invivo-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from analysis.pilot import moving_average
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/team_pipeline_progress'
DATA=Path('/Volumes/YZ/recording/invivo/26-11-06/0192')
FS=10000; TEAL='#087f8c'; RED='#cf4b40'; GOLD='#d69423'; BLUE='#36699a'
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'white','savefig.facecolor':'white'})
manifest={}; evidence={}; figures=[]; cache={}
def tracked(p):
 p=ROOT/p;manifest[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest();return p
def raw(rec,ch,a,b):
 with h5py.File(DATA/f'extra_{rec}_signals.h5','r') as f:
  assert f['signals'].shape==(2048,3000000)
  x=f['signals'][ch,a-150:b+150].astype(float)
 cache[f'extra{rec}_ch{ch}_{a}_{b}_context150']=x
 return x,np.arange(a,b)/FS

def save(fig,name,title,caption):
 fig.savefig(OUT/f'{name}.png',dpi=190);fig.savefig(OUT/f'{name}.pdf');plt.close(fig)
 figures.append((name,title,caption))
def shade(ax,intervals,a,b,color=GOLD):
 for l,r in intervals:
  if l<b and r>a:ax.axvspan(max(l,a)/FS,min(r,b)/FS,color=color,alpha=.22,lw=0)
def load_events(rec):
 p=tracked(f'results/spike_detection_ma50_adaptive/extra{rec}/spikes.h5')
 q=tracked(f'results/coincidence_named_profiles/extra{rec}/annotations.h5')
 with h5py.File(p) as f,h5py.File(q) as w:
  assert w.attrs['input_sha256']==manifest[str(p.relative_to(ROOT))]
  c=f['spikes/channel_id'][:];s=f['spikes/sample_index'][:]
  np.testing.assert_array_equal(c,w['events/channel_id'][:]);np.testing.assert_array_equal(s,w['events/sample_index'][:])
  d={'c':c,'s':s,'broad':w['warnings/broad/event_warning'][:],'tight':w['warnings/tight/event_warning'][:],
     'available':w['warnings/broad/event_available'][:],'intervals':w['warnings/broad/intervals'][:],
     'tight_intervals':w['warnings/tight/intervals'][:],'available_intervals':w['warnings/broad/available_intervals'][:],
     'flat':f['quality/flat_guard_intervals'][:],'usable':f['quality/usable_samples_per_channel_window'][:],
     'threshold':f['noise/threshold'][:]}
  for key in ['broad','tight']:
   intervals=d['intervals' if key=='broad' else 'tight_intervals']; mask=np.zeros(3000000,bool)
   for a,b in intervals:mask[int(a):int(b)]=True
   np.testing.assert_array_equal(d[key],mask[s])
   assert not np.any(d[key]&~w[f'warnings/{key}/event_available'][:])
  flat=d['flat'];loss=float(np.sum(flat[:,2]-flat[:,1])/FS)
  evidence[f'extra{rec}']={'candidates':len(s),'broad_flagged':int(d['broad'].sum()),'tight_flagged':int(d['tight'].sum()),
   'outside_broad':int((~d['broad']).sum()),'unassessed_candidates':int((~d['available']).sum()),
   'broad_seconds':float(np.diff(d['intervals'],axis=1).sum()/FS),
   'assessed_seconds':float(np.diff(d['available_intervals'],axis=1).sum()/FS),
   'flat_guard_channel_seconds':loss,'usable_channel_seconds':float(d['usable'].sum()/FS),
   'total_channel_seconds':614400,'input_sha256':manifest[str(p.relative_to(ROOT))]}
 return d

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 all_data={r:load_events(r) for r in (4,5)}
 # Figure 1: controlled filter comparison, not a conflated legacy/final ablation.
 folder='results/ma_window_comparison/extra4_60_65/'
 diag=np.load(tracked(folder+'diagnostics.npz'))
 ev={k:np.loadtxt(tracked(folder+f'ma{k}_mad.csv'),delimiter=',',skiprows=1,ndmin=2) for k in (50,200)}
 sel=json.loads(tracked(folder+'waveform_selection.json').read_text())
 e=next(x for x in sel if x['channel_id']==1436)
 choices=[(1913,640350,600,'Baseline transition'),(1436,e['sample_index'],130,'Previously reviewed spike-like example')]
 fig,axs=plt.subplots(3,2,figsize=(13,9),layout='constrained')
 for col,(ch,p,half,label) in enumerate(choices):
  a,b=p-half,p+half+1;x,t=raw(4,ch,a,b);core=x[150:-150]
  axs[0,col].plot(t,core*1e3,color='#737b83',lw=.9,label='Stored signal')
  for row,k in [(1,200),(2,50)]:
   baseline=moving_average(x,k)[150:-150];y=core-baseline; color=BLUE if k==200 else TEAL
   axs[0,col].plot(t,baseline*1e3,color=color,label=f'MA{k}',lw=1.3)
   ax=axs[row,col];ax.plot(t,y*1e3,color=color,lw=.9)
   w=np.clip((np.arange(a,b)-600000)//FS,0,4)
   th=5*np.maximum(diag[f'sigma_ma{k}_mad'][ch,w],diag[f'floor_ma{k}_mad'][w])
   ax.plot(t,-th*1e3,'--',color=RED,lw=.9,label='Negative threshold')
   events=ev[k];peaks=events[(events[:,0]==ch)&(events[:,1]>=a)&(events[:,1]<b),1].astype(int)
   np.testing.assert_allclose(-y[peaks-a],events[(events[:,0]==ch)&(events[:,1]>=a)&(events[:,1]<b),2],atol=1e-10)
   ax.scatter(peaks/FS,y[peaks-a]*1e3,color=RED,s=24,zorder=4,label='Saved candidates')
   ax.set_title(f'MA{k} residual · {len(peaks)} candidate' + ('s' if len(peaks)!=1 else ''));ax.legend(fontsize=8,loc='upper right')
  lim=np.max(np.abs(np.concatenate([l.get_ydata() for ax in axs[1:,col] for l in ax.lines])))
  for ax in axs[1:,col]:ax.set_ylim(-lim*1.2,lim*1.2)
  axs[0,col].set_title(f'{label}\nextra_4 · channel {ch}');axs[0,col].legend(fontsize=8)
  for ax in axs[:,col]:ax.set(xlim=(a/FS,b/FS),ylabel='Stored units × 10³');ax.ticklabel_format(useOffset=False,axis='x');ax.grid(alpha=.15)
  axs[2,col].set_xlabel('Nominal recording time (s)')
 fig.suptitle('1 · Adapt baseline subtraction to in vivo fluctuations',fontsize=17)
 save(fig,'01_baseline','Baseline subtraction and detection',
 'Controlled historical MA200 versus MA50 comparison: identical observation support, masked MAD estimator, median floor and 5× multiplier; each filter has its own numerical threshold. MA200 is the legacy window size, but this controlled panel is not the complete legacy algorithm. In the reviewed 64.03–64.04 s transition, MA200 produced 738 candidates across all channels versus 28 with MA50. Fewer candidates do not establish accuracy. The current pipeline additionally uses adaptive masked MAD, the retained median floor, real neighboring filter context and global peak spacing. Selected spike-like waveforms are examples, not validated neurons.')
 # Figure 2: original plateau and historical detector, alongside current mask.
 z=np.load(tracked('results/extra4_pilot_60_65/review_traces.npz'));a,b=639500,641200;ix=slice(a-600000,b-600000);t=np.arange(a,b)/FS
 legacy=np.loadtxt(tracked('results/extra4_pilot_60_65/events_legacy_rms_floor.csv'),delimiter=',',skiprows=1,ndmin=2)
 d=all_data[4];ch=353;flat=d['flat'];ints=flat[flat[:,0]==ch,1:]
 fig,axs=plt.subplots(3,1,figsize=(13,8),sharex=True,layout='constrained')
 axs[0].plot(t,z['ch353_raw'][ix]*1e3,color='#576774');axs[0].set_title('Stored signal: nearly flat plateau and a transient · extra_4, channel 353')
 y=z['ch353_ma_residual'][ix];axs[1].plot(t,y*1e3,color=BLUE)
 peaks=legacy[(legacy[:,0]==ch)&(legacy[:,1]>=a)&(legacy[:,1]<b)]
 axs[1].scatter(peaks[:,1]/FS,y[peaks[:,1].astype(int)-a]*1e3,color=RED,s=55,label='Legacy candidate')
 axs[1].set_title('Historical MA200 residual: the median floor alone does not guarantee observability');axs[1].legend()
 x,_=raw(4,ch,a,b);y=(x-moving_average(x,50))[150:-150];axs[2].plot(t,y*1e3,color=TEAL)
 current=d['s'][(d['c']==ch)&(d['s']>=a)&(d['s']<b)]
 axs[2].scatter(current/FS,y[current-a]*1e3,color=RED,s=30)
 axs[2].set_title(f'Current MA50: {len(current)} saved candidates here; shaded samples excluded before detection')
 for ax in axs:shade(ax,ints,a,b);ax.set_ylabel('Stored units × 10³');ax.grid(alpha=.15)
 axs[2].set(xlabel='Nominal recording time (s)',xlim=(a/FS,b/FS));axs[2].ticklabel_format(useOffset=False,axis='x')
 fig.suptitle('2 · Mark unreliable observation, rather than treating flatness as quiet noise',fontsize=16)
 save(fig,'02_clipping','Per-channel clipping guard',
 'Gold shading is the saved per-channel flat guard: exact repeated values for ≥1 ms, expanded by ±50 ms. Those samples are excluded from noise estimation and candidate detection. The legacy median-noise safeguard is retained, but cannot restore signal lost to clipping. The panel contrasts complete methods; it does not isolate filtering from masking. In the matched historical RMS comparison, adding the median floor reduced candidates inside guards from 204 to 8; explicit masking excludes those intervals by construction. Exact flatness is a proxy, not calibrated rail detection, and can also reflect quantization or disconnected channels.')
 # Figure 3: reviewed shared event and nearby independent-looking candidate.
 rec=5;d=all_data[rec];a,b=798000,799100
 participating=np.unique(d['c'][(d['s']>=798520)&(d['s']<798570)])
 channels=participating[np.linspace(0,len(participating)-1,5,dtype=int)]
 fig,axs=plt.subplots(3,1,figsize=(13,9),layout='constrained',gridspec_kw={'height_ratios':[2,1.5,1]})
 traces=[]
 for ch in channels:
  x,t=raw(5,int(ch),a,b);traces.append(x[150:-150])
 scale=max(np.ptp(x) for x in traces)*1.2
 for i,(ch,y) in enumerate(zip(channels,traces)):
  axs[0].plot(t,(y-np.median(y)+i*scale)*1e3,lw=.8,label=f'Ch {ch}')
 axs[0].set(ylabel='Median-centered stored units × 10³\n(vertical offsets for display)',title='Similar deflections across widely separated channel IDs · extra_5');axs[0].legend(ncol=5,fontsize=8)
 keep=(d['s']>=a)&(d['s']<b);axs[1].scatter(d['s'][keep]/FS,d['c'][keep],s=4,color='#647381',rasterized=True)
 k=keep&d['broad'];axs[1].scatter(d['s'][k]/FS,d['c'][k],s=5,color=RED,rasterized=True)
 axs[1].set(ylabel='Channel ID',title='Saved candidate raster · red = broad warning',ylim=(-20,2068))
 axs[1].legend(handles=[Patch(color=RED,alpha=.22,label='Broad: 5 ms / 5%'),Patch(color=TEAL,alpha=.22,label='Tight: 1 ms / 5%')],loc='upper right',fontsize=8)
 for ax in axs[:2]:shade(ax,d['intervals'],a,b,RED);shade(ax,d['tight_intervals'],a,b,TEAL);ax.set_xlim(a/FS,b/FS);ax.ticklabel_format(useOffset=False,axis='x')
 # Separate selected plausible event: explicitly different recording/time, no implication of same neighborhood.
 ch=1436;p=e['sample_index'];aa,bb=p-130,p+131;x,tt=raw(4,ch,aa,bb);y=(x-moving_average(x,50))[150:-150]
 axs[2].plot(tt,y*1e3,color=TEAL,lw=.9)
 dd=all_data[4];kk=(dd['c']==ch)&(dd['s']>=aa)&(dd['s']<bb);ps=dd['s'][kk]
 axs[2].scatter(ps/FS,y[ps-aa]*1e3,color=RED,s=28)
 axs[2].set(title=f'Contrast example: extra_4, channel 1436 · {int(dd["broad"][kk].sum())}/{len(ps)} candidates broad-flagged',ylabel='MA50 units × 10³',xlabel='Nominal recording time (s)');axs[2].ticklabel_format(useOffset=False,axis='x')
 fig.suptitle('3 · Shared-disturbance warnings preserve candidates for review',fontsize=17)
 save(fig,'03_shared','Shared-disturbance warnings',
 'Top: a previously reviewed extra_5 shared event; five channels selected evenly across participating channel IDs, not physical distance. Red-tinted spans show broad 5 ms / 5% warnings; teal spans show tight 1 ms / 5% warnings. Each rule counts distinct channels observable throughout the window, with at least 1,024 eligible channels. Bottom: a separate previously reviewed spike-like example from extra_4, included as a contrast, not a nearby extra_5 event or an accuracy test. Baseline-change and high-pass excursion warnings also exist but cover only 35/300 s per recording; coincidence warnings are the full-recording overlay used here. Shared timing does not prove artifact or establish its physical cause.')
 # Figures 4/5 same scales; explicit unavailable retained in outside-warning view.
 for rec,d in all_data.items():
  m=evidence[f'extra{rec}'];fig,axs=plt.subplots(3,1,figsize=(14,10),sharex=True,layout='constrained',gridspec_kw={'height_ratios':[2.4,2.4,1]})
  t=d['s']/FS;c=d['c'];flag=d['broad'];un=~d['available']
  for ax,keep,title in [(axs[0],np.ones(len(t),bool),f'All {len(t):,} saved candidates; broad warnings highlighted in red'),(axs[1],~flag,f'{int((~flag).sum()):,} candidates outside broad warnings — illustrative view only')]:
   ax.scatter(t[keep],c[keep],s=.5,color='#556b7b',alpha=.55,rasterized=True)
   if ax==axs[0]:ax.scatter(t[flag],c[flag],s=1.4,color=RED,alpha=.85,rasterized=True)
   ax.scatter(t[keep&un],c[keep&un],s=2,color=GOLD,rasterized=True)
   ax.set(ylabel='Channel ID (not neuron ID)',ylim=(-20,2068),title=title)
  axs[0].legend(handles=[Line2D([],[],marker='.',ls='',color=RED,label='Broad-flagged'),Line2D([],[],marker='.',ls='',color=GOLD,label='Unassessed (retained)')],loc='upper right',fontsize=8)
  bins=np.arange(301);counts=np.histogram(t,bins)[0];kept=np.histogram(t[~flag],bins)[0]
  axs[2].plot(np.arange(300)+.5,counts,color='#657788',lw=.9,label='All candidates')
  axs[2].plot(np.arange(300)+.5,kept,color=TEAL,lw=.9,label='Outside broad warnings')
  axs[2].set(ylabel='Candidates / nominal s',xlabel='Nominal recording time (s)',xlim=(0,300),ylim=(0,16000));axs[2].legend(loc='upper right',fontsize=9)
  assert counts.max()<16000
  fig.suptitle(f'{rec} · extra_{rec} overview | broad warning: 5 ms / 5%\n{m["broad_flagged"]:,} flagged ({100*m["broad_flagged"]/m["candidates"]:.2f}%) across {m["broad_seconds"]:.4f} s; no saved events deleted',fontsize=16)
  save(fig,f'0{rec}_extra{rec}_raster',f'extra_{rec}: all candidates and illustrative exclusion',
   f'Identical channel/time/count axes across recordings. Red points are broad-flagged candidates. Gold points indicate unavailable coincidence assessment ({m["unassessed_candidates"]:,} candidates); these remain in the lower raster and must not be interpreted as clean. Warning durations are exact interval unions, not the width of visible raster strokes. Clipping guards already affected detection and cannot be undone by this display. The lower view excludes broad coincidence flags only, not every signal-based warning, and is not a cleaned or curated spike dataset. Tight warnings flag {m["tight_flagged"]:,} candidates. Raster dots can overlap at this scale; numerical totals are authoritative.')
 # Portable report with embedded PNGs.
 rows=''.join(f'<tr><td>extra_{r}</td><td>{m["candidates"]:,}</td><td>{m["broad_flagged"]:,}</td><td>{m["outside_broad"]:,}</td><td>{m["broad_seconds"]:.4f}</td><td>{m["flat_guard_channel_seconds"]:,.2f}</td><td>{m["usable_channel_seconds"]:,.2f}</td></tr>' for r in (4,5) for m in [evidence[f'extra{r}']])
 sections=''.join(f'<section><h2>{i}. {title}</h2><img alt="{title}" src="data:image/png;base64,{base64.b64encode((OUT/(name+".png")).read_bytes()).decode()}"><p>{caption}</p></section>' for i,(name,title,caption) in enumerate(figures,1))
 page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>In vivo spike detection — team progress</title><style>body{margin:0;background:#edf3f4;color:#203744;font:17px/1.65 system-ui}main{max-width:1250px;margin:auto;padding:32px}header,section{padding:30px;background:white;margin:24px 0;border-radius:12px}header{background:#173d4d;color:white}h1{font-size:38px;line-height:1.2}h2{color:#087f8c}img{width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;text-align:left;border-bottom:1px solid #ddd}.note{padding:18px;background:#fff1d5} @media print{body{background:white}main{padding:0}section{break-before:page}header{background:white;color:#203744}img{max-height:70vh;object-fit:contain}} </style><main><header><p>TEAM UPDATE · 23 NOVEMBER 2026</p><h1>Adapting spike detection from in vitro to in vivo recordings</h1><p>Baseline subtraction · per-channel clipping guards · shared-disturbance warnings</p></header><section><h2>Why the pipeline needed reworking</h2><p>The legacy code was developed for in vitro recordings with relatively little baseline fluctuation. Our in vivo recordings show larger fluctuations, episodes of flat/clipped signal and widespread simultaneous disturbances. Direct reuse can mistake low-noise flatness or transient residuals for eAP activity.</p><p>We retained moving-average subtraction and the median-noise safeguard, adjusted the filtering and noise estimation, added explicit per-channel observation guards, and introduced shared-disturbance warnings. These are complementary protections: filtering changes the signal, clipping masks determine when a channel is observable, and warnings annotate saved candidates.</p><div class="note"><b>Delivered:</b> full-recording candidate detection on extra_4 and extra_5, with broad coincidence warnings as the default annotation. <b>Boundary:</b> candidates are not validated spikes or isolated neurons; warnings are not confirmed artifacts. All original candidates remain saved.</div></section>'''+sections+'''<section><h2>Quantitative summary and tradeoffs</h2><table><tr><th>Recording</th><th>All candidates</th><th>Broad flagged</th><th>Outside broad</th><th>Broad duration (s)</th><th>Flat-guard loss (channel-s)</th><th>Usable channel-s</th></tr>'''+rows+'''</table><p>Each recording contains 614,400 nominal channel-seconds before exclusions. Flat-guard loss sums each channel's merged saved guard intervals; usable exposure also accounts for filter edges and insufficient noise-estimation support. These losses overlap and must not be added. Warning duration is global elapsed time, not channel-time loss, and annotation causes no actual exposure removal.</p><p>extra_4 and extra_5 are both purely extracellular recordings. extra_5 followed stimulation experiments; their differences are not a controlled stimulation effect. All times use nominal 10 kHz (physical acquisition: 10,080 Hz). Amplitudes are labeled in stored float units; no new calibration is assumed.</p><h2>What remains</h2><p>Extend signal-based baseline/broadband assessment beyond its current 35/300 s coverage, review overlaps between warning methods, and validate false-positive/false-negative tradeoffs before adopting automatic exclusion. Fast-noise removal and stimulation-period artifact correction remain unresolved; extra_6 is outside this report.</p><h2>Reproduction and files</h2><p>Run <code>.venv/bin/python analysis/report_team_progress.py</code> with the YZ drive mounted. Five PNGs and matching PDFs accompany this portable HTML report. JSON evidence/manifest/validation and cached source excerpts document provenance. Selected waveform examples illustrate mechanisms and are not a random accuracy sample.</p></section></main></html>'''
 (OUT/'report.html').write_text(page)
 np.savez_compressed(OUT/'source_excerpts.npz',**cache)
 (OUT/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
 # Verify inputs still unchanged and accounting identities before publishing validation.
 for p,digest in manifest.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest
 for m in evidence.values():assert m['candidates']==m['broad_flagged']+m['outside_broad']
 (OUT/'manifest.json').write_text(json.dumps({'date':'2026-11-23','git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_sha256':manifest,'raw_source_directory':str(DATA),'excerpt_context_samples':150,'raw_excerpt_sha256':hashlib.sha256((OUT/'source_excerpts.npz').read_bytes()).hexdigest(),'selection':'historical diagnostic transition, plateau and reviewed spike-like example; five evenly ranked participating channels in reviewed extra5 event'},indent=2)+'\n')
 (OUT/'validation.json').write_text(json.dumps({'event_identity_exact':True,'warning_masks_match_interval_unions':True,'flags_within_assessed_support':True,'source_hashes_unchanged':True,'candidate_totals_reconcile':True,'figure_count':len(figures),'visual_review':'pending'},indent=2)+'\n')
 print(OUT/'report.html')
if __name__=='__main__':main()
