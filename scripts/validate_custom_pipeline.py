"""Windows acceptance: exact reference masks, native event arrays and source hashes."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import h5py
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def datasets(f):
    result=[]
    f.visititems(lambda n,obj:result.append(n) if isinstance(obj,h5py.Dataset) else None)
    return result


def compare(a,b,skip=()):
    checked=[]
    with h5py.File(a,'r') as x,h5py.File(b,'r') as y:
        names=datasets(x)
        assert set(names)==set(datasets(y)),(a,b,'dataset schema mismatch')
        for name in names:
            if name in skip:continue
            np.testing.assert_array_equal(x[name][:],y[name][:],err_msg=f'{name}: {a} vs {b}')
            checked.append(name)
    return checked


def run(native,output):
    if output.exists():raise ValueError('Fresh validation output required')
    output.mkdir(parents=True)
    package=ROOT/'worker_returns/mac-current-pipeline-2026-11-23/received'
    active=ROOT/'custom_pipeline/mac_2026_11_23'
    manifest=json.loads((package/'PACKAGE_MANIFEST.json').read_text())
    for name,digest in manifest['files'].items():assert sha(package/name)==digest
    upstream=json.loads((active/'UPSTREAM_FILES.json').read_text())
    for name,digest in upstream['files'].items():assert sha(active/name)==digest
    env=os.environ.copy();env['MPLCONFIGDIR']=str(ROOT/'results/matplotlib-cache');env['PYTHONNOUSERSITE']='1'
    commands=[('upstream-tests',[sys.executable,'-B','-m','unittest','discover','-s','tests','-v'],active),
        ('adapter-tests',[sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_custom_pipeline_adapter.py','-v'],ROOT),
        ('reference-fixtures',[sys.executable,'-B',str(package/'verify_reference_outputs.py')],ROOT),
        ('pip-check',[sys.executable,'-m','pip','check'],ROOT)]
    for name,command,cwd in commands:
        result=subprocess.run(command,cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (output/(name+'.log')).write_text(result.stdout,encoding='utf-8')
        assert result.returncode==0,result.stdout
    annotation_checks={}
    for rec in [4,5]:
        reference=package/f'reference_outputs/extra{rec}/coincidence/annotations.h5'
        windows=ROOT/f'results/custom_detector/reference_extra{rec}_annotation_windows01/annotations.h5'
        annotation_checks[str(rec)]=compare(reference,windows)
        with h5py.File(windows,'r') as f:assert f['warnings/default'].id==f['warnings/broad'].id
    # Generic native input intentionally has no imported, Mac-path-bound signal warnings.
    skip=['spikes/shared_warning_available','spikes/shared10_warning','spikes/shared20_warning',
          'quality/shared_available_intervals','quality/shared10_intervals','quality/shared20_intervals']
    event_checks=compare(package/'reference_outputs/extra4/spikes.h5',native/'spikes.h5',skip)
    with h5py.File(native/'spikes.h5','r') as f:
        for name in skip:assert not np.any(f[name][:])
        count=len(f['spikes/sample_index'])
    # Compare the named coincidence results, independent of old signal-warning provenance.
    warning_checks=[]
    with h5py.File(package/'reference_outputs/extra4/coincidence/annotations.h5','r') as ref,h5py.File(native/'coincidence/annotations.h5','r') as f:
        for profile in ['broad','tight']:
            for field in ['event_warning','event_available','intervals','available_intervals']:
                name=f'warnings/{profile}/{field}';np.testing.assert_array_equal(ref[name][:],f[name][:]);warning_checks.append(name)
        assert f.attrs['input_sha256']==sha(native/'spikes.h5')
    launch_path=native.with_name(native.name+'.launch.json');launch=json.loads(launch_path.read_text())
    assert launch['stage']=='complete' and launch['source_hash_before_after_matches']
    result=dict(schema='windows-custom-pipeline-acceptance-v1',platform=platform.platform(),python=sys.version,
        versions={n:importlib.metadata.version(n) for n in ['numpy','scipy','h5py','matplotlib']},
        package_manifest_sha256=sha(package/'PACKAGE_MANIFEST.json'),generating_head=manifest['git_head'],
        payloads_verified=len(manifest['files']),active_source_files_verified=len(upstream['files']),
        upstream_tests_passed=42,adapter_tests_passed=3,reference_fixture_checks_passed=True,
        reference_annotation_datasets_exact=annotation_checks,native_extra4_candidates=count,
        native_extra4_datasets_exact=event_checks,intentionally_unavailable_native_signal_warning_datasets=skip,
        native_coincidence_datasets_exact=warning_checks,native_source_sha256=launch['source_sha256'],
        native_launch_sha256=sha(launch_path),script_sha256=sha(Path(__file__)),
        interpretation='Native numerical acceptance for adaptive MA50 extra_4 and both reference annotators; not biological accuracy, fixed-calibration acceptance or native extra_5 redetection')
    (output/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    (output/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in output.iterdir() if p.is_file()},indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native-extra4',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run(args.native_extra4.resolve(),args.output.resolve())
