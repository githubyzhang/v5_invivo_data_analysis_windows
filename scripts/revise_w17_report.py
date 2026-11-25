"""Presentation revision: consistent units and all-cluster evidence; no recuration."""
import csv,html,os,re,argparse
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np
from run_sorting import ROOT,read,save,sha,verify_manifest
from review_sorting_baseline import table

def rows(p,delimiter=','):
    with p.open(newline='') as f:return list(csv.DictReader(f,delimiter=delimiter))

def run(output):
    output=output.resolve();assert not output.exists() and output.is_relative_to(ROOT/'results')
    source=ROOT/'results/extra4/w17-release-v1';verify_manifest(source/'manifest.json')
    meta=read(ROOT/'configs/extra4_release.v1.json')
    for p,h in meta['pinned_files'].items():assert sha(ROOT/p)==h,p
    ledger=rows(source/'curation_ledger.csv');original=rows(source/'units.csv');events=rows(source/'spikes.csv');omissions=rows(source/'omitted_events.csv')
    grouped=defaultdict(list)
    for e in events:grouped[e['unit_id']].append(e)
    output.mkdir();allrows=[];stats=[];labels={};evidence_pins={}
    href=lambda p:os.path.relpath(p,output).replace('\\','/')
    for s in range(4):
        ll=[r for r in ledger if int(r['shank'])==s];runid=ll[0]['run_id'];src=ROOT/f'results/extra4_shank{s}'/runid/'kilosort4'
        labels[s]={int(r['cluster_id']):r['KSLabel'] for r in rows(src/'cluster_KSLabel.tsv','\t')}
        cl=np.load(src/'spike_clusters.npy').ravel();counts=Counter(map(int,cl))
        mua=sorted(cid for cid,label in labels[s].items() if label=='mua')
        for disposition,decision in [('accepted_putative','Accepted'),('hold_deferred','Hold'),('withhold','Withhold')]:
            ids=sorted(int(r['cluster_id']) for r in ll if r['disposition']==disposition)
            stats.append(dict(shank=s,decision=decision,clusters=len(ids),cluster_ids=', '.join(map(str,ids))))
        for r in ll:
            cid=int(r['cluster_id']);decision={'accepted_putative':'Accepted','hold_deferred':'Hold','withhold':'Withhold'}[r['disposition']]
            if s:
                folder=ROOT/f'results/extra4_shank{s}/w16{"abc"[s-1]}-review01';path=folder/f'screen_{cid//6+1}.png';position=f'row {cid%6+1} on screen'
            elif decision=='Accepted':
                path=ROOT/f'results/extra4_shank0/w12-curated-v1/unit_{cid}.png';position='accepted-domain summary'
            elif labels[s][cid]=='good':
                path=ROOT/f'results/extra4_shank0/w9-good-review01/unit_{cid}.png';position='original-event review'
            else:
                idx=mua.index(cid);path=ROOT/f'results/extra4_shank0/w10-population-review01/mua_screen_{idx//6+1}.png';position=f'row {idx%6+1} on screen'
            assert path.exists(),path
            evidence_pins[str(path.relative_to(ROOT))]=sha(path)
            allrows.append(dict(shank=s,run_id=runid,cluster_id=cid,automated_label=labels[s][cid],original_events=counts[cid],decision=decision,reason=r['reason'],waveform_evidence=href(path),evidence_location=position))
    corrected=[]
    for u in original:
        s=int(u['shank']);cid=int(u['cluster_id']);ee=grouped[u['unit_id']];oo=[r for r in omissions if r['unit_id']==u['unit_id']]
        r=dict(shank=s,cluster_id=cid,unit_id=u['unit_id'],run_id=u['run_id'],decision='Accepted',original_automated_label=labels[s][cid])
        for key in ['original_events','analysis_events','omitted_events','exposure_samples','peak_binary','peak_global']:r[key]=int(u[key])
        for key in ['nominal_duration_s','physical_duration_s','nominal_rate','physical_rate','amplitude_median']:r[key]=float(u[key])
        r['policy_id']=u['policy_id']
        r['boundary_events_omitted']=sum(x['boundary']=='True' for x in oo)
        r['shared_policy_events_omitted']=len(oo)-r['boundary_events_omitted']
        for key in ['peak_guard','any_active_guard','half_active_guard','broad_warning','tight_warning','incomplete_context']:
            assert all(e[key] in ['True','False'] for e in ee)
            r[key+'_events']=sum(e[key]=='True' for e in ee)
        for profile in ['broad','tight']:
            r[profile+'_assessed_events']=sum(e[profile+'_available']=='True' for e in ee)
            r[profile+'_unassessed_events']=len(ee)-r[profile+'_assessed_events']
        r['generic_shared_assessment']='not_assessed'
        r['shared_core_shoulder_assessment']='available' if s==3 else 'not_assessed'
        assert len(ee)==r['analysis_events'] and r['original_events']-len(ee)==len(oo)==r['omitted_events']
        for key in ['peak_guard','broad_warning','tight_warning']:assert int(u[key])==r[key+'_events']
        assert int(u['coincidence_unavailable'])==r['broad_unassessed_events']
        for name,fs in [('nominal',10000),('physical',10080)]:assert np.isclose(r[name+'_rate'],len(ee)*fs/r['exposure_samples'],rtol=1e-12)
        corrected.append(r)
    assert len(allrows)==186 and len(corrected)==41 and sum(r['analysis_events'] for r in corrected)==62048
    assert Counter(r['decision'] for r in allrows)==dict(Accepted=41,Hold=89,Withhold=56)
    assert all(v!='' and v is not None for r in corrected for v in r.values())
    table(output/'units.csv',corrected);table(output/'all_clusters.csv',allrows);table(output/'decision_summary.csv',stats)
    save(output/'units.json',corrected)
    definitions={k:k.replace('_',' ') for k in corrected[0]}
    definitions.update(shank='Zero-based shank (0 is first physical shank).',cluster_id='Original cluster ID; unique only within shank and run.',original_automated_label='Original Kilosort good/mua label, independent of manual acceptance.',original_events='All original sorter events in this cluster.',analysis_events='Events retained by the already accepted per-shank policy.',boundary_events_omitted='Original candidate events excluded for incomplete +/-100-sample context.',shared_policy_events_omitted='Events excluded by the adopted shared core/shoulder policy; zero outside shank3 means no such exclusion, not a clean assessment.',nominal_rate='Analysis events / retained nominal seconds (10000 Hz).',physical_rate='Analysis events / retained physical seconds (10080 Hz).',amplitude_median='Median sorter amplitude of retained events; not calibrated microvolts.',generic_shared_assessment='not_assessed for all shanks; never interpret warning absence as clean.',shared_core_shoulder_assessment='Explicit W15C mask available only for shank3; distinct from generic shared assessment.',peak_binary='Template peak channel in original 512-channel binary.',peak_global='Original acquisition channel ID, zero-based.')
    for k in definitions:
        if k.endswith('_events') and k not in ['original_events','analysis_events','omitted_events','boundary_events_omitted','shared_policy_events_omitted']:definitions[k]+='; count among retained analysis events, flags may overlap.'
    save(output/'column_definitions.json',definitions)
    def summary_html():
        trs=''.join(f'<tr><td>Shank{r["shank"]}</td><td>{r["decision"]}</td><td>{r["clusters"]}</td><td>{r["cluster_ids"]}</td></tr>' for r in stats)
        return '<h2 id="decisions">Per-shank curation decisions</h2><p>Cluster IDs are local to each selected run. Accepted = putative unit; Hold = deferred for later review; Withhold = insufficient support for this subset, not proof of artifact.</p><table><thead><tr><th>Shank</th><th>Decision</th><th>Clusters</th><th>Cluster IDs</th></tr></thead><tbody>'+trs+'</tbody></table><p><strong>Total: 41 accepted + 89 hold + 56 withhold = 186 clusters.</strong></p>'
    detail='<h2 id="all-clusters">All selected-run clusters</h2><p>Events are original sorter counts for every cluster, not filtered accepted-event counts. Evidence pages retain their historical captions; the decision here is current. Some sparse/boundary clusters have no complete raw window, which their evidence page states.</p><label>Filter by shank, cluster, label, decision or reason: <input id="search" type="search" placeholder="e.g. Shank2 or Hold" oninput="filterRows()"></label><p id="visible">186 clusters shown</p>'
    for s in range(4):
        detail+=f'<h3>Shank{s}</h3><div class="scroll"><table class="clusters"><thead><tr><th>Cluster</th><th>Auto label</th><th>Original events</th><th>Decision</th><th>Reason</th><th>Evidence</th></tr></thead><tbody>'
        for r in allrows:
            if r['shank']!=s:continue
            detail+=f'<tr data-search="{html.escape(" ".join(str(r[k]) for k in ["decision","reason","automated_label"])+f" Shank{s} c{r['cluster_id']}",quote=True)}"><td>c{r["cluster_id"]}</td><td>{r["automated_label"]}</td><td>{r["original_events"]:,}</td><td class="{r["decision"].lower()}">{r["decision"]}</td><td>{html.escape(r["reason"])}</td><td><a href="{r["waveform_evidence"]}" target="_blank" rel="noopener">Waveforms</a><br><small>{r["evidence_location"]}</small></td></tr>'
        detail+='</tbody></table></div>'
    body=(source/'index.html').read_text(encoding='utf-8')
    body=re.sub(r'(href|src)="([^"]+)"',lambda m:f'{m[1]}="{href((source/m[2]).resolve())}"',body)
    body=body.replace(href(source/'units.csv'),'units.csv')
    css='table{border-collapse:collapse;width:100%;background:white;margin:18px 0}th,td{padding:10px;border-bottom:1px solid #d8e2e6;text-align:left;vertical-align:top}th{background:#dce9ec}td:nth-child(5){min-width:340px}.accepted{color:#176442;font-weight:bold}.hold{color:#84560c}.withhold{color:#7c3f4a}.scroll{overflow-x:auto}input{font:inherit;padding:8px;width:330px}'
    body=body.replace('</style>',css+'</style>')
    notice='<p>Presentation revision 2: expanded decision tables and corrected unit-column schema. Scientific release v1, unit membership and events are unchanged.</p><nav><a href="#decisions">Decision summary</a><a href="#all-clusters">All-cluster review</a><a href="units.xlsx">Corrected 41-unit Excel workbook</a><a href="units.csv">Corrected unit CSV</a><a href="column_definitions.json">Column definitions</a></nav>'
    body=body.replace('</header>','</header>'+notice+summary_html())
    body=body.replace('<h2>Detailed accepted evidence</h2>',detail+'<h2>Detailed accepted evidence</h2>')
    body=body.replace('</main>','</main><script>function filterRows(){let q=document.getElementById("search").value.toLowerCase(),n=0;document.querySelectorAll("tr[data-search]").forEach(r=>{let ok=r.dataset.search.toLowerCase().includes(q);r.hidden=!ok;if(ok)n++});document.getElementById("visible").textContent=n+" clusters shown"}</script>')
    (output/'index.html').write_text(body,encoding='utf-8')
    save(output/'checks.json',dict(state='passed_data_checks',unit_rows=41,cluster_rows=186,summary_rows=12,events=62048,consistent_unit_columns=True,all_unit_cells_populated=True,evidence_images=len(evidence_pins),original_release_manifest_sha256=sha(source/'manifest.json'),evidence_pins=evidence_pins,script_sha256=sha(Path(__file__))))
    print({'units':41,'clusters':186,'evidence_images':len(evidence_pins)})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
