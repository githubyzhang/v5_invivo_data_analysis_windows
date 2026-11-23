"""Launch the isolated Mac detector snapshot using the Windows detector venv."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'custom_pipeline/mac_2026_11_23'
PYTHON = ROOT/'.venv-detector/Scripts/python.exe'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def checked_output(path, input_path):
    path=path.resolve()
    if not path.is_relative_to(ROOT/'results/custom_detector') or path==ROOT/'results/custom_detector':
        raise ValueError('Use a new directory inside results/custom_detector')
    if path.exists() or path==input_path.resolve():raise ValueError('Output must not exist')
    return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['detect','annotate'])
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--profile',choices=['broad','tight'],default='broad')
    parser.add_argument('--min-channels',type=int,default=1024)
    args=parser.parse_args()
    source=args.input.resolve();output=checked_output(args.output,source)
    if not source.is_file():raise FileNotFoundError(source)
    if not PYTHON.is_file():raise FileNotFoundError('Create .venv-detector with the documented lock first')
    upstream=json.loads((SOURCE/'UPSTREAM_FILES.json').read_text())
    for rel,digest in upstream['files'].items():
        if sha(SOURCE/rel)!=digest:raise ValueError(f'Upstream source changed: {rel}')
    command=[str(PYTHON),'-B',str(SOURCE/'analysis'/('detect_recordings.py' if args.action=='detect' else 'candidate_coincidence.py')),
             '--input',str(source),'--output',str(output)]
    if args.action=='detect':
        command+=['--mode','adaptive','--ma','50','--coincidence-warning',args.profile,'--coincidence-min-channels',str(args.min_channels)]
    else:command+=['--profile',args.profile,'--min-channels',str(args.min_channels)]
    output.parent.mkdir(parents=True,exist_ok=True)
    record_path=output.with_name(output.name+'.launch.json')
    log_path=output.with_name(output.name+'.log')
    if record_path.exists() or log_path.exists():raise ValueError('Choose a fresh launch name')
    metadata=dict(schema='windows-custom-detector-launch-v1',action=args.action,source=str(source),
        source_sha256=sha(source),source_size=source.stat().st_size,output=str(output),command=command,
        started_utc=datetime.now(timezone.utc).isoformat(),upstream_manifest_sha256=upstream['source_manifest_sha256'],
        upstream_git_head=upstream['git_head'],adapter_sha256=sha(Path(__file__)),
        detector_lock_sha256=sha(ROOT/'requirements-windows-detector-lock.txt'),
        default_profile=args.profile,minimum_eligible_channels=args.min_channels,
        signal_based_warning_imported=False,stage='running')
    record_path.write_text(json.dumps(metadata,indent=2)+'\n')
    env=os.environ.copy();env['MPLCONFIGDIR']=str(ROOT/'results/matplotlib-cache');env['PYTHONNOUSERSITE']='1'
    # A subprocess with its own import root prevents mixing with historical root analysis/.
    with log_path.open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=SOURCE,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        for line in process.stdout:
            log.write(line);log.flush();print(line,end='',flush=True)
        code=process.wait()
    unchanged=sha(source)==metadata['source_sha256']
    metadata.update(stage='complete' if code==0 and unchanged else 'failed',returncode=code,
                    source_hash_before_after_matches=unchanged,finished_utc=datetime.now(timezone.utc).isoformat())
    if output.is_dir() and (output/'pipeline_progress.json').exists():
        metadata['pipeline_status']=json.loads((output/'pipeline_progress.json').read_text())
    record_path.write_text(json.dumps(metadata,indent=2)+'\n')
    if code!=0 or not unchanged:raise SystemExit(code or 1)


if __name__=='__main__':main()
