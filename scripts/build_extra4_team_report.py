"""Portable presentation of frozen W17 results; never changes scientific inputs.

Run --figures with the project Python, then run without arguments using the
bundled document Python (ReportLab/pypdf). Outputs are a fresh versioned package.
"""
from pathlib import Path
import csv, hashlib, html, json, shutil, sys, zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'results/extra4/w17-report-revision02'
RELEASE = ROOT / 'results/extra4/w17-release-v1'
OUT = ROOT / 'outputs/extra4-team-sharing-v1'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p): return list(csv.DictReader(p.open(encoding='utf-8', newline='')))
def verify(base):
    for name, digest in read(base/'manifest.json').items():
        assert sha(base/name) == digest, name

def figures():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    OUT.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    units = read(SOURCE/'units.json')
    for s, ax in enumerate(axes.flat):
        # Deterministic illustrative selection, not a quality ranking.
        u = min((u for u in units if u['shank'] == s), key=lambda u:u['cluster_id'])
        z = np.load(RELEASE/f"waveforms/shank{s}_cluster{u['cluster_id']}.npz")
        channel = list(z['channels']).index(u['peak_binary'])
        for q, color in enumerate(['#147d92','#e49436','#5c5aaa','#527f3e']):
            # Frozen packets already store source values scaled by 1e6.
            ax.plot(np.arange(-100,101)/10, z['quarter_means'][q,:,channel],
                    color=color, label=f'Quarter {q+1}', lw=1.4)
        ax.set(title=f"Shank {s} / cluster {u['cluster_id']} / b{u['peak_binary']}",
               xlabel='Time from event (nominal ms)', ylabel='Source value x 1,000,000')
        ax.grid(alpha=.18)
    axes[0,0].legend(fontsize=8)
    fig.savefig(OUT/'waveform_examples.png', dpi=180)
    plt.close(fig)

def build():
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from pypdf import PdfReader
    verify(SOURCE); verify(RELEASE)
    units = read(SOURCE/'units.json'); decisions = rows(SOURCE/'decision_summary.csv')
    clusters = rows(SOURCE/'all_clusters.csv'); summary = read(RELEASE/'summary.json')
    assert len(units)==41 and len(clusters)==186 and sum(u['analysis_events'] for u in units)==62048
    assert len({(r['shank'],r['run_id'],r['cluster_id']) for r in clusters})==186
    for r in decisions:
        found=sorted(int(c['cluster_id']) for c in clusters if c['shank']==r['shank'] and c['decision']==r['decision'])
        assert found==[int(x) for x in r['cluster_ids'].split(',')] and len(found)==int(r['clusters'])
    assert {(str(u['shank']),str(u['cluster_id'])) for u in units} == {(c['shank'],c['cluster_id']) for c in clusters if c['decision']=='Accepted'}
    OUT.mkdir(parents=True,exist_ok=True); (OUT/'evidence').mkdir(exist_ok=True)
    for name in ['units.csv','units.xlsx','decision_summary.csv','column_definitions.json']:
        shutil.copy2(SOURCE/name,OUT/name)
    shutil.copy2(RELEASE/'raster.png',OUT/'raster.png')
    evidence = {}
    for r in clusters:
        original = (SOURCE/r['waveform_evidence']).resolve()
        filename = sha(original)[:16]+'.png'
        shutil.copy2(original,OUT/'evidence'/filename)
        evidence[str(original.relative_to(ROOT))] = sha(original)
        r['waveform_evidence'] = 'evidence/'+filename
    with (OUT/'all_clusters.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=clusters[0]); w.writeheader(); w.writerows(clusters)
    h = html.escape
    head = '<!doctype html><meta charset="utf-8"><title>extra_4 cluster decisions</title><style>body{font:15px Arial;margin:32px;color:#183343}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd5da;padding:8px;text-align:left}th{background:#edf3f5}a{color:#006c80}</style>'
    intro = '<h1>extra_4: all 186 selected-run clusters</h1><p>Current decisions: 41 Accepted, 89 Hold, 56 Withhold. Original events are sorter counts, not retained analysis counts. Cluster IDs are local to the shank and run. Historical reasons and figure captions may contain proposal-era wording (including “no acceptance applied”); the Decision column gives current status. Waveform screens may contain multiple clusters: use the indicated row. These are historical review figures, not new reviews.</p><p><a href="extra4-team-summary.pdf">PDF summary</a> | <a href="units.xlsx">Corrected 41-unit workbook</a></p>'
    table = '<table><tr>'+''.join('<th>'+x+'</th>' for x in ['Shank / run','Cluster','Auto label','Original events','Decision','Recorded reason','Waveform evidence'])+'</tr>'
    for r in clusters:
        cells=[h(r['shank']+' / '+r['run_id']),r['cluster_id'],r['automated_label'],r['original_events'],r['decision'],h(r['reason']),f'<a href="{r["waveform_evidence"]}">{h(r["evidence_location"])}</a>']
        table+='<tr>'+''.join('<td>'+x+'</td>' for x in cells)+'</tr>'
    (OUT/'all_clusters.html').write_text(head+intro+table+'</table>',encoding='utf-8')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyTeam',fontName='Helvetica',fontSize=10.5,leading=15,spaceAfter=10,textColor=colors.HexColor('#233b49')))
    styles.add(ParagraphStyle(name='SmallTeam',fontSize=8,leading=11,textColor=colors.HexColor('#233b49')))
    styles['Title'].textColor=styles['Heading1'].textColor=colors.HexColor('#126e80')
    story=[]
    def p(t,style='BodyTeam'): return Paragraph(t,styles[style])
    def para(t): story.append(p(t))
    def title(n,t): story.extend([p(n.upper(),'SmallTeam'),Spacer(1,12),p(t,'Title'),Spacer(1,12)])
    def table(data,widths):
        t=Table([[p(str(c),'SmallTeam') for c in row] for row in data],colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dceef0')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),1,colors.HexColor('#126e80')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f6f8')])]))
        story.extend([t,Spacer(1,12)])
    def page(): story.append(PageBreak())
    title('Team summary | 24 November 2026','extra_4<br/>Reviewed four-shank results')
    para('<b>41 accepted putative units; 62,048 retained analysis events.</b> All 186 clusters from the four selected Kilosort4 runs have a recorded decision. This is the reviewed v1 result for the supplied extra_4 recording, not a claim of complete neuron recovery.')
    table([['Shank','Clusters','Accepted','Hold','Withhold','Analysis events']]+[[s['shank'],s['original_clusters'],s['units'],s['holds'],s['withheld'],f"{s['events']:,}"] for s in summary['shanks']]+[['Total',186,41,89,56,'62,048']],[48,65,65,55,65,109])
    para('<b>Scope.</b> Recording 26-11-06 / 0192, file extra_4_signals.h5: 2,048 channels and 3,000,000 samples. Four 512-channel shanks were sorted independently. Shanks are numbered 0-3; shank0 is the first shank.')
    para('<b>What acceptance means.</b> The accepted subset has evidence consistent with single-unit activity. These are putative units, not confirmed individual neurons. Automated good/mua labels remain separate from curated decisions.')
    para('<b>Potential additional units.</b> The 89 held clusters may contain neuronal activity; further review could increase the accepted count. A simple candidate-cluster envelope is <b>41 to 130 (41 accepted + 89 held)</b>, if each retained cluster ultimately contributes at most one distinct unit. This is not a bound on the true neuron count: holds may be artifacts, duplicates or mixed populations, and accepted units remain putative. The 56 withheld clusters are outside this envelope, not proven non-neuronal. Holds remain deferred; no new acceptance is made here.')
    para('<b>Package.</b> This PDF is self-contained. Supporting files include the corrected 41-unit workbook, per-shank decision IDs, all 186 reasons and a portable HTML table linking 48 historical waveform evidence images.')
    page(); title('Methods and identity','One selected run per shank')
    table([['Shank','Selected run','Electrodes omitted from sorting']]+[[s['shank'],s['run_id'],['b248 / global1921','None','b54 / global872; b148 / global353','b259 / global2045'][s['shank']]] for s in summary['shanks']],[42,220,245-0])
    para('The channel-specific exclusions follow matched sensitivity comparisons and quality review. They preserve the 512-column binary layout. Alternative runs are not mixed, and cluster numbers do not identify the same neuron across runs or shanks. Use shank + run + cluster as the identity.')
    para('<b>Workflow.</b> Verified channel mapping and inputs; independent Kilosort4 sorting; channel/artifact annotation and matched comparisons; all-cluster review; explicit subset and exposure-policy acceptance; derived summaries and reproducibility audit.')
    para('Review combined raw spatial waveform support, stability across recording quarters, amplitude and event-time diagnostics, refractory/isolation evidence, selected competing-cluster comparisons, raw short-interval exceptions and quality exposure. It was a project-specific evidence review, not automatic acceptance of the sorter labels. No cluster merges or source-label changes were adopted.')
    para('The imported Mac custom detector supports independent detection and quality annotations. Its scientific defaults were not silently substituted for Kilosort settings. Full-recording coincidence annotations retain their 2,048-channel definitions; warnings alone do not delete events.')
    para('<b>Time and geometry.</b> Nominal sampling rate: 10,000 Hz (300 s). Physical rate: 10,080 Hz (297.619 s). Integer sample indices are authoritative. Local electrode pitch is 30 micrometers in x and y; local coordinates do not establish inter-shank spacing or cross-shank neuron uniqueness.')
    page(); title('Complete decision accounting','Cluster IDs by shank and decision')
    table([['Shank','Decision','Count','Cluster IDs']]+[[r['shank'],r['decision'],r['clusters'],r['cluster_ids']] for r in decisions],[38,65,38,366])
    para('Accepted = included in the explicitly accepted putative-unit subset. Hold = unresolved, outside the subset and deferred. Withhold = not supported for inclusion in this release. Original sorter outputs and labels remain preserved. Historical control clusters are not extra members of this selected-run table.')
    page(); title('Activity overview','Retained events on the original time axis')
    story.append(Image(str(OUT/'raster.png'),width=507,height=439.4))
    para('Each panel shows accepted units from one shank. The raster is copied from the audited W17 release; unit labels retain local cluster identity. Gaps are not concatenated. Differences in observed activity can reflect both neuronal activity and recording/detection limitations.')
    para('Shank3 has less retained exposure because its shared-loss core and shoulder are excluded from both events and duration. Missing activity during those intervals must not be interpreted as biological silence. Cross-shank synchrony has not been established by this overview.')
    page(); title('Illustrative raw-waveform evidence','Waveform stability across four quarters')
    story.append(Image(str(OUT/'waveform_examples.png'),width=507,height=354.9))
    para('One accepted unit per shank is shown: the lowest accepted cluster ID, chosen deterministically for illustration, not as a quality ranking. Curves are mean raw waveforms on the listed peak binary channel, aligned to detected events. Q1-Q4 are successive quarters of the original 3,000,000-sample recording, not four sorting runs.')
    para('Each mean uses retained events in its quarter (up to 128 sampled windows). Each window spans +/-100 samples and is baseline-adjusted using its first 70 samples. The plotted source values are multiplied by 1,000,000 for readability; this is not a claim of calibrated microvolts. Overlay similarity supports waveform consistency but does not by itself prove isolation or neuron identity.')
    para('All-cluster supporting evidence is included in all_clusters.html and the evidence folder. Historical figure captions may show earlier proposal statuses. Current decisions are recorded in the supporting table and on page 3.')
    page(); title('Analysis policy and limits','Match event counts to retained exposure')
    table([['Shank','Exposure samples','Nominal seconds','Physical seconds','Events omitted']]+[[s['shank'],f"{s['exposure_samples']:,}",f"{s['exposure_samples']/10000:.4f}",f"{s['exposure_samples']/10080:.6f}",s['omitted']] for s in summary['shanks']],[45,115,112,115,120])
    para('All shanks retain the half-open interior sample interval [100, 2,999,900), excluding incomplete boundary context. Shank3 additionally excludes the shared-flat core and its shoulder from both event counts and duration: 72,005 core samples plus 9,555 shoulder-only samples. The core uses at least 256 of the original 512 channels flat simultaneously; the shoulder extends it by +/-500 samples. This is a conservative operational margin, not a validated filter-settling time.')
    para('The accepted clusters originally contained 62,062 events; the adopted policies omit 14, retaining 62,048. Rates equal retained observed events divided by the matching exposure. They are not estimates corrected for missed spikes or residual recording loss.')
    para('Other quality warnings remain annotations. Generic shared assessment is not available across all shanks; the separate documented core/shoulder assessment applies to shank3 only. A zero omission or warning count is not evidence that unassessed data are clean.')
    para('<b>Audit.</b> W17 verified source and binary hashes, all 2,048 mapped channels, event identities/counts, 41 units, 1,230 rate bins, 164 unit-quarter records and 28,593 raw waveform windows. This presentation rechecks the frozen release and corrected-export manifests and reconciles its supporting tables.')
    para('<b>Next.</b> W18 preservation/handoff follows this sharing package. Held clusters remain deferred. Further unit or policy changes require a new accepted revision; cross-shank identity, biological synchrony and other recordings remain separate work.')
    for start in [0,21]:
        page(); title('Supporting unit table | '+('1 of 2' if start==0 else '2 of 2'),'Accepted putative units')
        para('All rows retain original automated label good. Rates below use physical exposure (10,080 Hz); the workbook also supplies nominal rates and quality counts. Peak global is the recorded global channel identifier. Run identities are listed on page 2.')
        table([['Shank','Cluster','Original events','Analysis events','Omitted','Peak global','Rate / s']]+[[u['shank'],u['cluster_id'],u['original_events'],u['analysis_events'],u['omitted_events'],u['peak_global'],f"{u['physical_rate']:.3f}"] for u in units[start:start+21]],[40,48,90,90,65,80,94])
        if start==21:
            para('<b>Source record.</b> Reviewed extra_4 four-shank release v1; corrected presentation revision 2, 24 November 2026. W12/W16D record subset and policy acceptance; W17 records release validation. This package preserves those decisions. The included provenance.json records exact source and output hashes; the full analysis archive remains in the project.')
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#d2dfe4'));canvas.line(44,40,551,40)
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#526b78'))
        canvas.drawString(44,27,'extra_4 | reviewed release v1 | team sharing | 24 Nov 2026')
        canvas.drawRightString(551,27,str(doc.page))
    pdf=OUT/'extra4-team-summary.pdf'
    SimpleDocTemplate(str(pdf),pagesize=A4,rightMargin=44,leftMargin=44,topMargin=40,bottomMargin=54,title='extra_4 - Reviewed four-shank results',author='extra_4 analysis project').build(story,onFirstPage=footer,onLaterPages=footer)
    reader=PdfReader(pdf); assert len(reader.pages)==8, len(reader.pages)
    text='\n'.join(page.extract_text() for page in reader.pages)
    for term in ['62,048','186','41','Accepted putative units']: assert term in text
    (OUT/'README.txt').write_text('extra_4 team sharing v1 | 24 November 2026\n\nStart with extra4-team-summary.pdf (8 pages).\nOpen all_clusters.html for all 186 decisions and local waveform links.\nunits.xlsx and units.csv contain the same corrected 41-unit table.\ndecision_summary.csv lists every decision and cluster ID.\ncolumn_definitions.json defines the unit fields.\nUnzip the entire package and keep evidence/ beside the HTML. No network or project paths are required. Historical reasons/figures retain proposal-era wording; the current Decision column is authoritative.\n\nThis is a presentation of accepted release v1, not new curation. Hold review remains deferred. Source signals and event-level datasets are not bundled; this summary package does not replace the full reproducibility archive.\n',encoding='utf-8')
    verify(SOURCE); verify(RELEASE)
    checks={'pages':8,'units':len(units),'clusters':len(clusters),'decision_rows':len(decisions),'analysis_events':62048,'evidence_images':len(evidence),'source_manifests_verified':True,'scientific_decisions_changed':False}
    (OUT/'checks.json').write_text(json.dumps(checks,indent=2))
    provenance={'scientific_release':'extra4-reviewed-four-shank-v1','presentation':'team-sharing-v1','date':'2026-11-24','source_manifests':{str(x.relative_to(ROOT)):sha(x) for x in [SOURCE/'manifest.json',RELEASE/'manifest.json']},'builder_sha256':sha(Path(__file__)),'evidence_sources':evidence}
    (OUT/'provenance.json').write_text(json.dumps(provenance,indent=2))
    manifest={str(p.relative_to(OUT)).replace('\\','/'):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    archive=OUT.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(OUT.rglob('*')):
            if path.is_file(): z.write(path,OUT.name+'/'+path.relative_to(OUT).as_posix())
    print(json.dumps(checks)); print(pdf); print(archive)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,digest in read(OUT/'manifest.json').items():
            assert hashlib.sha256(z.read(OUT.name+'/'+name)).hexdigest()==digest
        for r in clusters: assert OUT.name+'/'+r['waveform_evidence'] in z.namelist()

if __name__=='__main__':
    if '--figures' in sys.argv: figures()
    else: build()
