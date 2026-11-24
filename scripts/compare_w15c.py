"""Reuse the frozen matched-run calculations with W15C-specific presentation."""
import argparse
from pathlib import Path
from compare_sorting_runs import run
from run_sorting import read,save,sha


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['control','exclusion','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.control,a.exclusion,a.output)
    index=a.output/'index.html'
    html=index.read_text(encoding='utf-8').replace('Shank2 matched comparison','Shank3 matched comparison').replace('W15B: shank2','W15C: shank3').replace('b54/global872 and b148/global353','b259/global2045')
    index.write_text(html,encoding='utf-8')
    summary=read(a.output/'summary.json');summary['presentation_script_sha256']=sha(Path(__file__))
    save(a.output/'summary.json',summary)
    save(a.output/'report-manifest.json',{p.name:sha(p) for p in a.output.iterdir() if p.name!='report-manifest.json'})
