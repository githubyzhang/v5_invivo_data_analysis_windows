"""Assemble the accepted four-shank release without changing frozen revisions."""
import argparse,csv,shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_sorting import ROOT,read,save,sha,verify_manifest
from shank_input import channel_ids


def rows(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))


def table(p,rs):
    fields=list(dict.fromkeys(k for r in rs for k in r))
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rs)


def run(output):
    output=output.resolve();assert output.is_relative_to(ROOT/'results') and not output.exists()
    pins={}
    for name,field in [('extra4_shank0_release.v1.json','payloads'),('extra4_shanks123_derived_v1.json','pinned_files')]:
        p=ROOT/'configs'/name;pins[str(p.relative_to(ROOT))]=sha(p)
        for rel,h in read(p)[field].items():assert sha(ROOT/rel)==h,rel
    old=ROOT/'results/extra4_shank0/w12-curated-v1';new=ROOT/'results/extra4/w16d-curated-v1'
    for p in [old/'report-manifest.json',new/'manifest.json']:
        verify_manifest(p);pins[str(p.relative_to(ROOT))]=sha(p)
    a0=read(ROOT/'configs/extra4_shank0_curated_v1.json');a123=read(ROOT/'configs/extra4_shanks123_curated_v1.json')
    assert a0['state']==a123['state']=='user_accepted'
    choices=[dict(shank_zero_based=0,run_id=a0['run_id'],run_path='results/extra4_shank0/'+a0['run_id'])]+read(ROOT/'configs/extra4_working_runs.v1.json')['runs']
    maps=channel_ids();events=[];units=[];quarters=[];bins=[];omitted=[];ledger=[];intervals={};summaries=[]
    output.mkdir();(output/'waveforms').mkdir()
    for choice in choices:
        s=choice['shank_zero_based'];source=old if s==0 else new;runid=choice['run_id'];runpath=ROOT/choice['run_path']
        verify_manifest(runpath/'output-manifest.json');pins[str((runpath/'output-manifest.json').relative_to(ROOT))]=sha(runpath/'output-manifest.json')
        key=lambda cid:f'extra_4:shank{s}:{runid}:cluster{cid}:v1'
        spans=np.array([[100,2999900]]) if s==0 else np.load(new/f'shank{s}/analysis_intervals.npz')['primary']
        intervals[f'shank{s}']=spans
        for r in rows(source/'spikes.csv'):
            if s and int(r['shank'])!=s:continue
            r.update(shank=s,run_id=runid)
            if s==0:
                for dst,src in [('any_active_guard','active_guard_any'),('half_active_guard','active_guard_ge50'),('incomplete_context','boundary')]:r[dst]=r[src]
            events.append(r)
        for r in rows(source/'units.csv'):
            if s and int(r['shank'])!=s:continue
            r.update(shank=s,run_id=runid);cid=int(r['cluster_id']);assert r['unit_id']==key(cid)
            if s==0:
                r['omitted_events']=r['boundary_events_omitted'];r['peak_global']=int(maps[s,int(r['peak_binary'])])
                for dst,src in [('peak_guard','peak_guard_events'),('broad_warning','broad_warning_events'),('tight_warning','tight_warning_events'),('coincidence_unavailable','broad_unavailable_events')]:r[dst]=r[src]
            r['policy_id']='interior_annotated' if s<3 else 'interior_without_shared_core_and_shoulder';units.append(r)
            packet=source/f'unit_{cid}.npz' if s==0 else source/f'shank{s}/unit_{cid}.npz'
            shutil.copyfile(packet,output/f'waveforms/shank{s}_cluster{cid}.npz')
        for r in rows(source/('quarter_metrics.csv' if s==0 else 'quarters.csv')):
            if s and int(r['shank'])!=s:continue
            r.update(shank=s,run_id=runid,unit_id=key(int(r['cluster_id'])))
            if s==0:r['physical_rate']=int(r['events'])*10080/int(r['exposure_samples'])
            quarters.append(r)
        for r in rows(source/'rate_bins.csv'):
            if s and int(r['shank'])!=s:continue
            r.update(shank=s,run_id=runid,unit_id=key(int(r['cluster_id'])))
            if s==0:r['start_sample']=r.pop('bin_start_sample');r['stop_sample']=r.pop('bin_stop_sample')
            bins.append(r)
        for r in rows(source/('omitted_boundary_events.csv' if s==0 else 'omitted_events.csv')):
            if s and int(r['shank'])!=s:continue
            r.update(shank=s,run_id=runid,unit_id=key(int(r['cluster_id'])))
            if s==0:r.update(boundary=True,shared_core='',shared_shoulder='')
            omitted.append(r)
        source_ledger=ROOT/'docs/reviews/2026-11-24-w12-curation-ledger.csv' if s==0 else new/'curation_ledger.csv'
        for r in rows(source_ledger):
            if s and int(r['shank'])!=s:continue
            if s==0 and r['run']!=runid:continue
            accepted=r['included_in_accepted_subset']=='True' if s==0 else r['accepted']=='True'
            decision=('accepted_putative' if accepted else 'hold_deferred' if r['recommendation'].startswith('hold') else 'withhold') if s==0 else r['disposition']
            ledger.append(dict(shank=s,run_id=runid,cluster_id=r['cluster_id'],accepted=accepted,disposition=decision,reason=r['reason'],source_ledger=str(source_ledger.relative_to(ROOT))))
        uu=[r for r in units if r['shank']==s];ll=[r for r in ledger if r['shank']==s]
        summaries.append(dict(shank=s,run_id=runid,units=len(uu),events=sum(int(r['analysis_events']) for r in uu),original_candidate_events=sum(int(r['original_events']) for r in uu),omitted=sum(int(r['omitted_events']) for r in uu),original_clusters=len(ll),holds=sum(r['disposition']=='hold_deferred' for r in ll),withheld=sum(r['disposition']=='withhold' for r in ll),exposure_samples=int(np.diff(spans,axis=1).sum()),policy=uu[0]['policy_id']))
    assert (len(events),len(units),len(ledger),len(omitted),len(bins),len(quarters))==(62048,41,186,14,1230,164)
    for name,rs in [('spikes',events),('units',units),('curation_ledger',ledger),('omitted_events',omitted),('rate_bins',bins),('quarters',quarters)]:table(output/(name+'.csv'),rs)
    table(output/'historical_control_ledger.csv',[r for r in rows(ROOT/'docs/reviews/2026-11-24-w12-curation-ledger.csv') if r['run']!=a0['run_id']])
    np.savez_compressed(output/'analysis_intervals.npz',**intervals)
    np.savez_compressed(output/'spikes.npz',shank=np.array([int(r['shank']) for r in events]),cluster_id=np.array([int(r['cluster_id']) for r in events]),original_event_index=np.array([int(r['original_event_index']) for r in events]),sample_index=np.array([int(r['sample_index']) for r in events]),sorter_amplitude=np.array([float(r['sorter_amplitude']) for r in events]))
    mapping=[dict(shank=s,binary_channel=b,original_channel_id=int(maps[s,b]),local_x_um=(b%4)*30,local_y_um=(b//4)*30) for s in range(4) for b in range(512)]
    table(output/'channel_map.csv',mapping)
    save(output/'schema.json',dict(missing_fields='Empty means not supplied by that frozen revision; never interpret as false or clean.',common_aliases_shank0=dict(any_active_guard='active_guard_any',half_active_guard='active_guard_ge50',incomplete_context='boundary'),native_fields='All source event fields retained; aliases do not replace originals.',generic_shared_assessment='Unavailable; shank3 shared_core/shoulder are separate explicit masks, not generic availability.',time='Sample index is authoritative; nominal 10000 Hz, physical 10080 Hz; no gap concatenation.',geometry='Local probe coordinates only; no inter-shank spacing or cross-shank neuron uniqueness inferred.',waveforms='Byte-identical accepted per-unit packets; selections and eight-channel means remain revision-specific.'))
    fig,axs=plt.subplots(4,1,figsize=(15,13),layout='constrained')
    for s,ax in enumerate(axs):
        uu=[r for r in units if r['shank']==s]
        for j,u in enumerate(uu):
            tt=[int(r['sample_index'])/10000 for r in events if r['unit_id']==u['unit_id']];ax.scatter(tt,np.full(len(tt),j),s=1,color='#197e85')
        mask=np.zeros(3000000,bool)
        for lo,hi in intervals[f'shank{s}']:mask[lo:hi]=True
        d=np.diff(np.r_[False,~mask,False].astype(int))
        for lo,hi in zip(np.where(d==1)[0],np.where(d==-1)[0]):ax.axvspan(lo/10000,hi/10000,color='#d88137',alpha=.3)
        ax.set(xlim=(0,300),yticks=range(len(uu)),yticklabels=['c'+str(r['cluster_id']) for r in uu],xlabel='Original nominal seconds',title=f'Shank{s}: {len(uu)} accepted putative units; orange = excluded domain')
    fig.savefig(output/'raster.png',dpi=110);plt.close(fig)
    save(output/'summary.json',dict(state='combined_accepted_release_pending_audit',date='2026-11-24',units=41,events=62048,original_clusters=186,holds=89,withheld=56,omitted_events=14,shanks=summaries,samples=3000000,source_channels=2048,source='C:/DATA/cnea_data/invivo/26-11-06/0192/extra_4_signals.h5',source_sha256=read(ROOT/'configs/extra4_shank0_release.v1.json')['source_sha256'],pinned_inputs=pins,builder_sha256=sha(Path(__file__)),limits=['Putative units, not proven distinct neurons.','Independent per-shank sorting; no cross-shank merging.','Shank3 has a different accepted time domain.','Quality flags remain; unknown is not clean.','Held clusters deferred; no claims of complete neuron recovery.']))
    cards=''.join(f'<section><h2>Shank{s["shank"]}</h2><b>{s["units"]} putative units</b><p>{s["events"]:,} events<br>{s["holds"]} held · {s["withheld"]} withheld</p></section>' for s in summaries)
    body='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>extra_4 four-shank release v1</title><style>body{font:16px/1.6 system-ui;background:#f3f6f8;color:#203b43;margin:0}main{max-width:1250px;margin:auto;padding:30px}header{background:#173c45;color:white;border-radius:16px;padding:30px}.cards{display:flex;gap:16px;margin:24px 0}section{flex:1;background:white;border-radius:12px;padding:20px}nav{display:flex;gap:18px;flex-wrap:wrap;margin:24px 0}a{color:#126477}.note{background:#fff3dc;border-left:5px solid #d39732;padding:22px}img{width:100%}@media(max-width:800px){.cards{display:block}}</style><main><header><p>EXTRA_4 · W17 · REVIEWED FOUR-SHANK RELEASE v1</p><h1>41 putative units · 62,048 analysis events</h1><p>All four shanks of the supplied 2,048-channel, 3,000,000-sample extra_4 recording. Original source and sorter outputs preserved.</p></header>'''
    body+='<div class="cards">'+cards+'</div><nav>'+''.join(f'<a href="{f}">{label}</a>' for f,label in [('units.csv','41-unit table'),('spikes.csv','Combined events'),('curation_ledger.csv','All 186 cluster decisions'),('omitted_events.csv','14 omitted identities'),('rate_bins.csv','Exposure-aware rate bins'),('quarters.csv','Quarter summaries'),('channel_map.csv','Physical channel mapping'),('schema.json','Fields and missing values'),('../w17-validation01/checks.json','Reproducibility audit')])+'</nav>'
    body+='''<div class="note"><h2>What this milestone means</h2><p>Every selected-run cluster has a disposition and reason: 41 accepted putative units, 89 holds deferred for later review, and 56 withheld from the subset. No additional unit decisions or merges were made in W17.</p><p>Shanks0–2 use the interior [100,2999900). Shank3 additionally omits documented shared signal loss and its shoulder. Rates use each unit’s own exposure; do not interpret gaps as neuronal silence or compare raw counts as if all durations were identical. The remaining time is not certified clean.</p><p>Nominal duration is 300 seconds at 10,000 Hz; physical duration is 297.619048 seconds at 10,080 Hz. Integer sample indices stay unchanged. This release does not establish cross-shank neuron uniqueness or complete neuron recovery.</p></div><h2>Four-shank event overview</h2><img src="raster.png" alt="Four-shank accepted event raster"><h2>Detailed accepted evidence</h2><p><a href="../../extra4_shank0/w12-curated-v1/index.html">Frozen shank0 waveform and quality report</a> · <a href="../w16d-curated-v1/index.html">Accepted shanks1–3 waveform, amplitude and rate report</a></p><p>Waveform packets in the waveforms folder are byte-identical copies of accepted source packets. The combined CSV retains native quality fields; empty fields mean unavailable in that revision, never false. See schema.json for explicit aliases.</p><h2>Preservation and continuation</h2><p>Git stores code, decisions and provenance. Raw data and generated artifacts need their separate backup; this report is not evidence of an external backup. The artifact inventory lists the dependencies needed to reproduce this release.</p><p><a href="artifact_inventory.csv">Artifact inventory</a>. Held-cluster review remains a later task. Future changes require a new accepted revision; v1 and its originals stay preserved.</p></main></html>'''
    (output/'index.html').write_text(body,encoding='utf-8')
    table(output/'artifact_inventory.csv',[dict(path=rel,sha256=h,role='frozen_input_manifest_or_metadata',storage='Local project; generated data not backed up by Git') for rel,h in pins.items()]+[dict(path=str(output.relative_to(ROOT)),sha256='see manifest.json',role='combined_release_payload',storage='Local ignored results; preserve separately')])
    save(output/'manifest.json',{str(p.relative_to(output)).replace('\\','/'):sha(p) for p in output.rglob('*') if p.is_file()})
    print(summaries)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
