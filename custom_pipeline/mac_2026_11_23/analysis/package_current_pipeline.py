"""Create an isolated Windows handoff with exact working-tree provenance."""
from pathlib import Path
import hashlib,json,shutil,subprocess,zipfile,argparse
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'results/windows_pipeline_handoff_2026-11-23');a=ap.parse_args()
    out=a.output.resolve()
    if out.exists():raise FileExistsError('Choose a fresh handoff destination')
    out.mkdir(parents=True)
    package=out/'current_pipeline_windows';package.mkdir()
    def cp(src,dst):
        target=package/dst;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/src,target)
    for folder in ('analysis','tests','docs','legacy'):
        for p in sorted((ROOT/folder).rglob('*')):
            if p.is_file() and p.suffix in ('.py','.md','.json','.mjs') and '__pycache__' not in p.parts:
                cp(p.relative_to(ROOT),p.relative_to(ROOT))
    for name in ('requirements.txt','.gitignore'):cp(name,name)
    cp('README.md','MAC_PROJECT_README.md')
    for name in ('START_HERE.md','VALIDATION.md','verify_package.py','verify_reference_outputs.py'):cp('handoffs/current-pipeline/'+name,name)
    for rec in (4,5):
        for name in ('spikes.h5','config.json','summary.json'):
            cp(f'results/spike_detection_ma50_adaptive/extra{rec}/{name}',f'reference_outputs/extra{rec}/{name}')
        for name in ('annotations.h5','protocol.json','summary.json'):
            cp(f'results/coincidence_named_profiles/extra{rec}/{name}',f'reference_outputs/extra{rec}/coincidence/{name}')
    for p in sorted((ROOT/'results/team_pipeline_progress').iterdir()):
        if p.name in ('report.html','evidence.json','validation.json','activity_summary.json') or p.suffix in ('.png','.pdf'):
            cp(p.relative_to(ROOT),'team_report/'+p.name)
    hashes={str(p.relative_to(package)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(package.rglob('*')) if p.is_file()}
    meta={'date':'2026-11-23','git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
          'git_status_porcelain':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
          'scope':'working-tree snapshot with reference outputs; no raw recordings, environment or Git history',
          'windows_validation':'pending native acceptance','files':hashes}
    (package/'PACKAGE_MANIFEST.json').write_text(json.dumps(meta,indent=2)+'\n')
    archive=out/'current_pipeline_windows.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(package.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(out))
    (out/'ZIP_SHA256.txt').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
    print(archive)
if __name__=='__main__':main()
