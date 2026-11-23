"""Repeatable review of the extra_4/shank0 pilot contract; never curates inputs.

Derived from the frozen worker scripts/review_pilot.py (2026-11-21).
See handoffs/windows-kilosort-independent/SCRIPT_PROVENANCE.md.
"""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import h5py

import argparse, hashlib, platform, sys
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence',type=Path,required=True,help='Verified recovered worker return')
parser.add_argument('--output',type=Path,required=True,help='New report directory; must not exist')
args=parser.parse_args()
ROOT=args.evidence.resolve();out=args.output.resolve()
if out==ROOT or ROOT in out.parents:
    raise ValueError('Reports must be outside the preserved evidence tree')
src=ROOT/'outputs/pilot01/kilosort4'
out.mkdir(parents=True,exist_ok=False)
def arr(name):return np.load(src/(name+'.npy'),allow_pickle=False)
def table(name):
    with open(src/name) as f:return {int(r['cluster_id']):r for r in csv.DictReader(f,delimiter='\t')}
def dump(name,data): (out/name).write_text(json.dumps(data,indent=2,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else str(x)))
t=arr('spike_times').reshape(-1);cl=arr('spike_clusters').reshape(-1);amp=arr('amplitudes').reshape(-1)
templates=arr('templates');cm=arr('channel_map').reshape(-1);pos=arr('channel_positions')
mapping=np.genfromtxt(ROOT/'geometry/channel_map.csv',delimiter=',',names=True,dtype=int)
assert len(t)==len(cl)==len(amp)
assert np.issubdtype(t.dtype,np.integer) and np.issubdtype(cl.dtype,np.integer)
assert np.all((t>=0)&(t<3000000)) and np.isfinite(amp).all() and np.isfinite(templates).all()
assert templates.ndim==3 and templates.shape[1:]==(61,512)
assert cl.min()>=0 and cl.max()<len(templates)
np.testing.assert_array_equal(cm,np.arange(512));np.testing.assert_array_equal(pos,np.column_stack((mapping['x_um'],mapping['y_um'])))
labels=table('cluster_KSLabel.tsv');contam=table('cluster_ContamPct.tsv')
foot=np.ptp(templates,axis=1);peak=foot.argmax(axis=1)
rows=[];hist=[];ampbins=[]
with h5py.File(ROOT/'reference/extra4_candidates.h5','r') as f:
    rt=f['spikes/sample_index'][:].astype(np.int64);rc=f['spikes/channel_id'][:]
for c in np.unique(cl):
    sel=cl==c;ts=np.sort(t[sel]);a=amp[sel];isi=np.diff(ts)
    counts=np.histogram(ts,bins=np.arange(0,3000001,100000))[0];hist.append(counts)
    ab=np.array([np.median(amp[sel & (t>=i*100000)&(t<(i+1)*100000)]) if counts[i] else np.nan for i in range(30)])
    ampbins.append(ab)
    nearby=np.flatnonzero(np.linalg.norm(pos-pos[peak[c]],axis=1)<=45)
    prior=np.sort(rt[np.isin(rc,mapping['original_channel_id'][nearby])])
    if len(prior):
        idx=np.searchsorted(prior,ts);distance=np.minimum(abs(ts-prior[np.minimum(idx,len(prior)-1)]),abs(ts-prior[np.maximum(idx-1,0)]))
        match=float(np.mean(distance<=10))
    else:match=0.
    rows.append(dict(cluster_id=int(c),automated_label=labels[c]['KSLabel'],contamination_pct=float(contam[c]['ContamPct']),
                     events=len(ts),rate_hz_nominal=len(ts)/300,rate_hz_physical=len(ts)/(3000000/10080),
                     peak_binary_channel=int(peak[c]),peak_global_channel=int(mapping['original_channel_id'][peak[c]]),
                     peak_x_um=float(pos[peak[c],0]),peak_y_um=float(pos[peak[c],1]),
                     channels_above_half_peak=int(np.sum(foot[c]>=foot[c].max()/2)),
                     isi_lt_1ms=int(np.sum(isi<10)),isi_lt_2ms=int(np.sum(isi<20)),
                     isi_lt_2ms_fraction=float(np.mean(isi<20)) if len(isi) else None,
                     occupied_10s_bins=int(np.count_nonzero(counts)),amplitude_median=float(np.median(a)),
                     amplitude_10s_median_min=float(np.nanmin(ab)),amplitude_10s_median_max=float(np.nanmax(ab)),
                     prior_nearby_match_within_1ms_fraction=match,manual_label='unassigned'))
with open(out/'cluster_review.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
hist=np.asarray(hist);ampbins=np.asarray(ampbins)
np.savez_compressed(out/'stability_bins.npz',counts=hist,amplitude_medians=ampbins,cluster_ids=np.unique(cl))
similar=arr('similar_templates');pairs=np.argwhere(np.triu(similar,k=1)>.9)
pairrows=[]
for a,b in sorted(pairs,key=lambda ij:-similar[tuple(ij)])[:100]:
    ta=np.sort(t[cl==a]);tb=np.sort(t[cl==b])
    if not len(ta) or not len(tb):continue
    ix=np.searchsorted(tb,ta);dist=np.minimum(abs(ta-tb[np.minimum(ix,len(tb)-1)]),abs(ta-tb[np.maximum(ix-1,0)]))
    pairrows.append(dict(cluster_a=int(a),cluster_b=int(b),template_similarity=float(similar[a,b]),peak_distance_um=float(np.linalg.norm(pos[peak[a]]-pos[peak[b]])),a_fraction_near_b_1ms=float(np.mean(dist<=10))))
dump('near_duplicates.json',pairrows)
ops={'settings':json.loads((ROOT/'outputs/pilot01/review/resolved_settings.json').read_text())}
dump('resolved_settings.json',ops.get('settings',{}))
fig,axes=plt.subplots(3,1,figsize=(13,10))
axes[0].imshow(np.log1p(hist),aspect='auto',extent=(0,300,len(rows),0));axes[0].set(ylabel='Cluster row',title='log(1 + events per 10 nominal seconds)')
axes[1].imshow(ampbins/np.nanmedian(ampbins,axis=1)[:,None],aspect='auto',vmin=.5,vmax=1.5,extent=(0,300,len(rows),0));axes[1].set(ylabel='Cluster row',title='10-second median amplitude / cluster median of bins')
if 'dshift' in ops:
    drift=np.asarray(ops['dshift']);axes[2].plot(np.linspace(0,300,len(drift)),drift);axes[2].set(ylabel='Estimated drift (um)',xlabel='Nominal seconds')
fig.tight_layout();fig.savefig(out/'stability_drift.png',dpi=160);plt.close(fig)
ordered=sorted(rows,key=lambda r:-r['events'])
chosen=[r['cluster_id'] for r in ordered[:6]]
for label in ['good','mua']:
    chosen += [r['cluster_id'] for r in ordered if r['automated_label']==label and r['cluster_id'] not in chosen][:3]
chosen += [r['cluster_id'] for r in sorted(rows,key=lambda r:r['events']) if r['cluster_id'] not in chosen][:2]
chosen=[r['cluster_id'] for r in rows]  # Review every cluster; no curation implied.
for page in range(0,len(chosen),4):
    subset=chosen[page:page+4];fig,axes=plt.subplots(len(subset),4,figsize=(16,3.1*len(subset)),squeeze=False)
    for ax,c in zip(axes,subset):
        row=next(r for r in rows if r['cluster_id']==c);near=np.argsort(np.linalg.norm(pos-pos[peak[c]],axis=1))[:8]
        ax[0].plot((np.arange(61)-20)/10,templates[c,:,near].T);ax[0].set(title=f'Cluster {c}: {row["automated_label"]}, n={row["events"]}',xlabel='Relative nominal ms (index 20 origin)',ylabel='Whitened template')
        ax[1].scatter(pos[:,0],pos[:,1],c=foot[c],s=10);ax[1].set_ylim(max(-30,pos[peak[c],1]-180),min(3840,pos[peak[c],1]+180));ax[1].set(title=f'Footprint; peak b{peak[c]}',xlabel='x (um)',ylabel='y (um)')
        ts=np.sort(t[cl==c]);d=[]
        for i,ti in enumerate(ts):
            j=np.searchsorted(ts,ti+500,side='right');d.extend((ts[i+1:j]-ti).tolist())
        d=np.asarray(d);ax[2].hist(np.concatenate((-d,d))/10,bins=np.arange(-50.5,51,1));ax[2].set(title=f'ACG; contam {row["contamination_pct"]:.1f}%',xlabel='Nominal lag ms')
        s=np.flatnonzero(cl==c)[::max(1,row['events']//5000)];ax[3].scatter(t[s]/10000,amp[s],s=2,alpha=.4);ax[3].set(xlabel='Nominal seconds',ylabel='PC feature L2 amplitude')
    fig.tight_layout();fig.savefig(out/f'cluster_examples_{page//4+1}.png',dpi=150);plt.close(fig)
summary=dict(events=len(t),clusters=len(rows),automated_labels={lab:sum(r['automated_label']==lab for r in rows) for lab in ['good','mua']},
             sample_min=int(t.min()),sample_max=int(t.max()),array_alignment_passed=True,channel_mapping_passed=True,
             template_shape=list(templates.shape),full_nominal_seconds=300,full_physical_seconds=3000000/10080,
             exclusions=[],clusters_under_100_spikes=sum(r['events']<100 for r in rows),
             near_duplicate_pairs_above_09=len(pairs),examples=chosen,
             interpretation='Automated labels are not confirmed neurons. No curation or cluster removal performed. All rates use full exposure.')
dump('summary.json',summary);print(json.dumps(summary,indent=2))

# Recompute disturbance overlap on final arrays. These are review screens, not masks.
raw=np.load(ROOT/'outputs/preflight/raw_per_second.npz',allow_pickle=False)
variability=np.median(raw['std'],axis=1)
seconds=np.flatnonzero(variability>2*np.median(variability))
disturbed=np.isin(t//10000,seconds)
edge=(t<61)|(t>=3000000-61)
kept=arr('kept_spikes').reshape(-1)
assert kept.dtype==np.bool_ and int(kept.sum())==len(t)
assert len(kept)>=len(t)
priorities={34:'promising waveform',35:'promising waveform',5:'promising waveform',12:'promising waveform',
            2:'automated good despite contamination estimate',26:'sparse automated good',29:'sparse automated good',
            37:'boundary-only candidate',58:'boundary-only candidate',31:'review pair 31/33',33:'review pair 31/33',
            45:'review pair 45/48',48:'review pair 45/48'}
queue=[]
for row in rows:
    cid=row['cluster_id'];mask=cl==cid
    count=int(np.sum(mask&disturbed));outside=row['events']-count
    queue.append(dict(cluster_id=cid,original_label=row['automated_label'],events=row['events'],
                      priority=priorities.get(cid,'routine review'),boundary_events=int(np.sum(mask&edge)),
                      disturbance_events=count,disturbance_fraction=count/row['events'],
                      outside_screen_rate_hz_nominal=outside/(300-len(seconds)),
                      decision='pending',proposed_label='',reviewer='',rationale='',evidence=''))
with (out/'curation_queue.csv').open('w',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=queue[0]);writer.writeheader();writer.writerows(queue)
dump('exposure.json',dict(full_samples=3000000,nominal_fs=10000,physical_fs=10080,
     disturbance_nominal_seconds=seconds.tolist(),screen_samples=len(seconds)*10000,
     outside_screen_samples=3000000-len(seconds)*10000,screen_events=int(disturbed.sum()),
     prededup_events=len(kept),final_events=len(t),exclusions_applied=False,
     caveat='Outside this screen does not mean artifact-free. Shared-warning coverage is incomplete.'))
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
inputs=[p for p in src.iterdir() if p.is_file()]
inputs += [ROOT/'geometry/channel_map.csv', ROOT/'reference/extra4_candidates.h5',
           ROOT/'outputs/preflight/raw_per_second.npz',ROOT/'outputs/pilot01/review/resolved_settings.json']
dump('provenance.json',dict(evidence=str(ROOT),script_sha256=sha(Path(__file__)),
     python=sys.executable,python_version=platform.python_version(),numpy=np.__version__,
     matplotlib=matplotlib.__version__,h5py=h5py.__version__,
     inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},curation='none'))
import html
cells=''.join('<tr>'+''.join('<td>'+html.escape(str(q[k]))+'</td>' for k in
    ('cluster_id','original_label','events','priority','boundary_events','disturbance_events'))+'</tr>' for q in queue)
pages=''.join(f'<img src="cluster_examples_{i+1}.png" alt="Cluster diagnostic page {i+1}">' for i in range((len(chosen)+3)//4))
(out/'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>Pilot unit review</title>
<style>body{font:16px system-ui;max-width:1400px;margin:30px auto;padding:20px}td,th{padding:8px;border-bottom:1px solid #ddd}img{width:100%}</style>
<h1>extra_4 / shank0 — uncurated unit review</h1>
<p>39,620 final events; 59 clusters; 24 automated good, 35 mua. No confirmed neuron identities or curation decisions.</p>
<p>Full exposure: 300 nominal seconds (10,000 Hz), 297.619 physical seconds (10,080 Hz). Integer samples are authoritative.
The sorter suppressed 75 duplicates with a 2-sample setting; shortest-interval estimates are limited by this suppression and low event counts.</p>
<p>Whitened template and feature amplitudes are not calibrated raw voltages. Boundary and disturbance screens are review flags, not exclusions.
Only 35/300 seconds have prior shared-warning assessment; the rest are unassessed.</p>
<p><a href="cluster_review.csv">All unit metrics</a> | <a href="curation_queue.csv">Pending curation queue</a> |
<a href="exposure.json">Exposure and screens</a> | <a href="provenance.json">Input identities and environment</a></p>
<table><tr><th>Cluster</th><th>Original label</th><th>Events</th><th>Review priority</th><th>Boundary events</th><th>Disturbance events</th></tr>'''
    +cells+'</table><h2>All clusters</h2>'+pages,encoding='utf-8')
dump('report-manifest.json',{p.name:sha(p) for p in out.iterdir() if p.is_file()})
