"""Render the comprehensive W17 HTML content and embed its waveform evidence."""
from pathlib import Path
from html.parser import HTMLParser
from html import escape
import csv, json, hashlib, re
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'results/extra4/w17-report-revision02'
OUT=ROOT/'outputs/extra4-detailed-report-v1'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(base):
    for n,d in json.loads((base/'manifest.json').read_text()).items(): assert sha(base/n)==d,n
class Node:
    def __init__(self,tag='',attrs=()): self.tag=tag; self.attrs=dict(attrs); self.children=[]
    def text(self): return ''.join(c if isinstance(c,str) else c.text() for c in self.children)
    def all(self,tag):
        for c in self.children:
            if not isinstance(c,str):
                if c.tag==tag: yield c
                yield from c.all(tag)
class Parser(HTMLParser):
    def __init__(self): super().__init__(); self.root=Node(); self.stack=[self.root]
    def handle_starttag(self,t,a):
        n=Node(t,a);self.stack[-1].children.append(n)
        if t not in ['meta','link','img','input','br','hr']: self.stack.append(n)
    def handle_endtag(self,t):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==t: self.stack=self.stack[:i];break
    def handle_data(self,d): self.stack[-1].children.append(d)

def main():
    verify(SRC);verify(ROOT/'results/extra4/w17-release-v1')
    OUT.mkdir(parents=True,exist_ok=True)
    parser=Parser();parser.feed((SRC/'index.html').read_text(encoding='utf-8'))
    root=next(parser.root.all('main'))
    clusters=list(csv.DictReader((SRC/'all_clusters.csv').open(encoding='utf-8',newline='')))
    evidence={}
    for r in clusters:
        path=(SRC/r['waveform_evidence']).resolve()
        evidence.setdefault(path,[]).append(r)
    ids={path:f'E{i:02d}' for i,path in enumerate(evidence,1)}
    styles=getSampleStyleSheet()
    for name,size,leading in [('Body',10,14),('Cell',8,10.5),('Caption',8.5,11)]:
        styles.add(ParagraphStyle(name=name,fontName='Helvetica',fontSize=size,leading=leading,spaceAfter=7,textColor=colors.HexColor('#233b49')))
    for name in ['Title','Heading1','Heading2','Heading3']:
        styles[name].textColor=colors.HexColor('#126e80')
        styles[name].keepWithNext=True
    def clean(t): return escape(t.replace('\u2011','-').replace('\u2013','-').replace('\u2014',' - ').replace('≤','<=').replace('≥','>='))
    def p(t,style='Body'): return Paragraph(clean(t),styles[style])
    def rich(n):
        if isinstance(n,str): return clean(n)
        if n.tag=='br': return '<br/>'
        if n.tag=='a':
            href=n.attrs.get('href',''); path=(SRC/href).resolve()
            if path in ids: return f'<link href="#{ids[path]}" color="#126e80">Waveform {ids[path]}</link>'
            # Local data links are not usable in a standalone PDF. Keep their labels.
            return ''.join(rich(c) for c in n.children)
        txt=''.join(rich(c) for c in n.children)
        return f'<b>{txt}</b>' if n.tag in ['strong','b'] else (f'<i>{txt}</i>' if n.tag in ['em','i'] else txt)
    story=[p('extra_4 | Comprehensive reviewed report','Title'),p('24 November 2026 | Scientific release v1 | W17 presentation revision 2'),p('This PDF reproduces the comprehensive report narrative and tables, with all 48 linked cluster-waveform evidence figures embedded in an appendix. Blue waveform references jump to the corresponding appendix figure. Cluster identities are shank/run-specific. Original data, decisions and scientific acceptance are unchanged.'),p('Reading guide','Heading2'),p('Part I: comprehensive report, retained-event raster, accepted-unit statistics, decision summary and all 186 cluster reasons. Part II: historical waveform evidence, identified by E01-E48. Figure captions and reasons retain historical proposal wording; current decisions in Part I take precedence.'),p('The 41 accepted units remain putative. The 89 holds may yield additional units after review. A conditional 41-130 candidate-cluster range is not a bound on true neuron count: held populations can be artifacts, duplicates or mixtures. Hold review is deferred.'),p('Data downloads and interactive filtering in the HTML are not embedded datasets in this PDF. Use the accompanying team-sharing package for the corrected spreadsheet/CSV tables; retain the full project archive for event-level data and reproducibility.'),PageBreak()]
    counts={'tables':0,'report_images':0,'paragraphs':0}
    def add(n):
        if isinstance(n,str): return
        if n.tag in ['script','style','input','nav']: return
        if n.attrs.get('class')=='cards':
            data=[['Shank','Putative units','Analysis events','Hold','Withhold']]
            summary=json.loads((ROOT/'results/extra4/w17-release-v1/summary.json').read_text())
            data += [[str(s['shank']),str(s['units']),f"{s['events']:,}",str(s['holds']),str(s['withheld'])] for s in summary['shanks']]
            t=Table([[p(c,'Cell') for c in row] for row in data],colWidths=[60,115,130,100,102])
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dceef0')),('VALIGN',(0,0),(-1,-1),'TOP')]))
            story.extend([t,Spacer(1,12)])
        elif n.tag in ['h1','h2','h3','p']:
            if not n.text().strip(): return
            style={'h1':'Title','h2':'Heading1','h3':'Heading2','p':'Body'}[n.tag]
            item=Paragraph(rich(n),styles[style])
            story.append(KeepTogether([item]) if n.tag=='p' else item);counts['paragraphs']+=1
        elif n.tag=='img':
            path=(SRC/n.attrs['src']).resolve();w,h=ImageReader(str(path)).getSize();scale=min(507/w,590/h)
            story.extend([Image(str(path),width=w*scale,height=h*scale),Spacer(1,10)]);counts['report_images']+=1
        elif n.tag=='table':
            data=[]
            for row in n.all('tr'):
                cells=[c for c in row.children if not isinstance(c,str) and c.tag in ['td','th']]
                data.append([Paragraph(rich(c),styles['Cell']) for c in cells])
            cols=len(data[0]);headers=[c.text() for c in next(n.all('tr')).children if not isinstance(c,str)]
            if cols==6 and any('Reason' in x or 'reason' in x for x in headers): widths=[42,40,52,55,248,70]
            elif cols==4 and any('IDs' in x for x in headers): widths=[40,65,40,362]
            else: widths=[507/cols]*cols
            t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dceef0')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f6f8')]),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.extend([t,Spacer(1,12)]);counts['tables']+=1
        else:
            for c in n.children: add(c)
    add(root)
    for path,rs in evidence.items():
        eid=ids[path]
        story.extend([PageBreak(),Paragraph(f'<a name="{eid}"/>{eid} | Historical waveform evidence',styles['Heading1'])])
        story.append(p('Shank '+rs[0]['shank']+' | '+rs[0]['run_id'],'Caption'))
        story.append(p('; '.join('c'+r['cluster_id']+': '+r['decision']+' ('+r['evidence_location']+')' for r in rs),'Caption'))
        story.append(p('Historical figure reproduced unchanged. Use the current decisions above; screen rows identify individual clusters. Zoom for fine waveform detail.','Caption'))
        w,h=ImageReader(str(path)).getSize();scale=min(507/w,590/h)
        story.append(Image(str(path),width=w*scale,height=h*scale))
    def footer(c,doc):
        c.setFont('Helvetica',8);c.setFillColor(colors.HexColor('#526b78'));c.drawString(44,25,'extra_4 | Comprehensive report | scientific v1 unchanged');c.drawRightString(551,25,str(doc.page))
    pdf=OUT/'extra4-comprehensive-report.pdf'
    SimpleDocTemplate(str(pdf),rightMargin=44,leftMargin=44,topMargin=38,bottomMargin=45,title='extra_4 comprehensive reviewed report',author='extra_4 analysis project').build(story,onFirstPage=footer,onLaterPages=footer)
    reader=PdfReader(pdf);texts=[x.extract_text() for x in reader.pages];text=' '.join(texts)
    # Every recorded reason must survive conversion (whitespace normalized).
    norm=lambda s:re.sub(r'\s+','',s.replace('\u2011','-').replace('\u2013','-').replace('\u2014','-'))
    for r in clusters: assert norm(r['reason']) in norm(text),r['cluster_id']
    assert len(evidence)==48 and len(clusters)==186
    links=[a.get_object() for page in reader.pages for a in page.get('/Annots',[])]
    assert len(links)==186
    assert len({a['/Dest'][0].idnum for a in links})==48
    checks=dict(pages=len(reader.pages),cluster_reasons_verified=186,evidence_figures=48,internal_destinations=48,**counts)
    (OUT/'checks.json').write_text(json.dumps(checks,indent=2))
    (OUT/'manifest.json').write_text(json.dumps({p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json'},indent=2))
    print(json.dumps(checks))
if __name__=='__main__': main()
