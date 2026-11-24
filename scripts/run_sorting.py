"""Hash-bound single-shank Kilosort runner; explicit config and fresh outputs only."""
import argparse
import copy
import csv
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import traceback
import numpy as np
from shank_input import ROOT, sha, channel_ids


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def verify_manifest(path):
    for relative,digest in read(path).items():
        target=(path.parent/relative).resolve()
        if not target.is_relative_to(path.parent.resolve()) or sha(target)!=digest:
            raise ValueError(f'Manifest mismatch: {target}')


def validate_geometry(config, probe, mapping):
    n=config['binary_channels'];s=config['shank_zero_based'];bad=config['excluded_binary_channels']
    if n!=512 or s not in range(4):raise ValueError('Supported layout: four shanks, 512 binary channels each')
    if len(set(bad))!=len(bad) or any(type(b) is not int or b<0 or b>=n for b in bad) or len(bad)==n:
        raise ValueError('Invalid excluded channel list')
    np.testing.assert_array_equal(probe['chanMap'],np.arange(n))
    np.testing.assert_array_equal(probe['kcoords'],np.full(n,s))
    assert probe['n_chan']==n
    for field,expected in [('binary_channel',np.arange(n)),('shank_zero_based',np.full(n,s)),
                           ('original_channel_id',channel_ids()[s]),('x_um',np.arange(n)%4*30),('y_um',np.arange(n)//4*30)]:
        np.testing.assert_array_equal(mapping[field],expected)
    np.testing.assert_array_equal(probe['xc'],mapping['x_um']);np.testing.assert_array_equal(probe['yc'],mapping['y_um'])
    return np.delete(np.arange(n),bad)


def prepare(config_path):
    config=read(config_path)
    if config['schema']!='single-shank-sort-v1' or config['state']!='authorized_diagnostic_run':raise ValueError('Explicit run authorization record required')
    output=(ROOT/config['output_path']).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'results'):raise ValueError('Fresh project result directory required')
    if config['samples']<=0 or config['data_dtype']!='float32':raise ValueError('Invalid input shape/dtype')
    for name,digest in config['pinned_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError(f'Changed input: {name}')
    binary=ROOT/config['binary_path']
    if binary.stat().st_size!=config['samples']*config['binary_channels']*4:raise ValueError('Binary byte count mismatch')
    geometry=read(ROOT/config['probe_path'])
    mapping=np.genfromtxt(ROOT/config['mapping_path'],delimiter=',',names=True,dtype=int)
    active=validate_geometry(config,geometry,mapping)
    base=read(ROOT/config['settings_reference'])
    settings=copy.deepcopy(base['settings'])
    settings.update(config['settings_overrides'])
    if any(k in settings for k in ['filename','data_dir','results_dir']):raise ValueError('Paths must be explicit runner arguments')
    if settings['n_chan_bin']!=config['binary_channels'] or settings['fs']!=config['nominal_fs_hz']:raise ValueError('Settings/input disagreement')
    versions={n:importlib.metadata.version(n) for n in config['expected_versions']}
    if versions!=config['expected_versions']:raise ValueError('Runtime version mismatch')
    if sha(ROOT/'.venv/Lib/site-packages/kilosort/run_kilosort.py')!=config['sorter_source_sha256']:raise ValueError('Sorter source changed')
    if Path(sys.executable).resolve()!= (ROOT/'.venv/Scripts/python.exe').resolve():raise ValueError('Use root .venv')
    info=dict(config_sha256=sha(config_path),script_sha256=sha(Path(__file__)),input_pins_verified=len(config['pinned_files']),
        active_channels=active.tolist(),settings=settings,versions=versions,
        scientific_settings_equal_reference=settings==base['settings'],
        invocation_equal_reference=all(config[k]==base[k] for k in ['do_CAR','invert_sign','data_dtype']),
        source_reference= config['settings_reference'],binary_sha256=sha(binary))
    return config,output,binary,geometry,active,info


def run(config_path, preflight_output=None):
    c,out,binary,geometry,active,info=prepare(config_path)
    if preflight_output is not None:
        preflight_output=preflight_output.resolve()
        if preflight_output.exists() or not preflight_output.is_relative_to(ROOT/'results'):raise ValueError('Fresh preflight output required')
        preflight_output.parent.mkdir(parents=True,exist_ok=True);save(preflight_output,info);print(json.dumps(info,indent=2));return
    import torch
    import kilosort
    if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable')
    out.mkdir(parents=True)
    save(out/'config.json',c)
    save(out/'run_contract.json',dict(**info,recording=c['recording'],shank_zero_based=c['shank_zero_based'],run_id=c['run_id'],
        samples=c['samples'],binary_channels=c['binary_channels'],nominal_fs_hz=c['nominal_fs_hz'],physical_fs_hz=c['physical_fs_hz'],
        excluded_binary_channels=c['excluded_binary_channels'],do_CAR=c['do_CAR'],invert_sign=c['invert_sign'],data_dtype=c['data_dtype'],
        save_preprocessed_copy=c['save_preprocessed_copy'],seed_policy=c['seed_policy'],python=sys.version,gpu=torch.cuda.get_device_name(),
        sorter_source_sha256=c['sorter_source_sha256']))
    (out/'environment-lock.txt').write_bytes(subprocess.check_output([sys.executable,'-m','pip','freeze']))
    save(out/'status.json',dict(state='running'))
    try:
        kilosort.run_kilosort(settings=copy.deepcopy(info['settings']),probe={k:np.asarray(v) if isinstance(v,list) else v for k,v in geometry.items()},
            filename=binary,results_dir=out/'kilosort4',data_dtype=c['data_dtype'],do_CAR=c['do_CAR'],invert_sign=c['invert_sign'],
            device=torch.device('cuda'),save_preprocessed_copy=c['save_preprocessed_copy'],bad_channels=c['excluded_binary_channels'] or None,verbose_log=True)
        src=out/'kilosort4';load=lambda name:np.load(src/(name+'.npy'),allow_pickle=False)
        t,cl,amp=[load(n).ravel() for n in ['spike_times','spike_clusters','amplitudes']]
        assert len(t)==len(cl)==len(amp) and np.issubdtype(t.dtype,np.integer) and np.issubdtype(cl.dtype,np.integer)
        assert np.all((t>=0)&(t<c['samples'])) and np.all(np.diff(t)>=0) and np.isfinite(amp).all()
        np.testing.assert_array_equal(load('channel_map').ravel(),active)
        np.testing.assert_array_equal(load('channel_positions'),np.column_stack((geometry['xc'],geometry['yc']))[active])
        assert np.all((cl>=0)&(cl<len(load('templates'))))
        with (src/'cluster_KSLabel.tsv').open() as f:labels={int(r['cluster_id']):r['KSLabel'] for r in csv.DictReader(f,delimiter='\t')}
        assert set(labels)==set(np.unique(cl)) and set(labels.values())<={'good','mua'}
        from kilosort.io import load_ops
        ops=load_ops(src/'ops.npy',device=torch.device('cpu'))
        for key,value in info['settings'].items():assert ops['settings'][key]==value,key
        assert ops['n_chan_bin']==c['binary_channels']
        np.testing.assert_array_equal(ops['probe']['chanMap'],active)
        np.testing.assert_array_equal(ops['probe']['kcoords'],np.full(len(active),c['shank_zero_based']))
        for name,digest in c['pinned_files'].items():assert sha(ROOT/name)==digest,name
        status=dict(state='complete_review_pending',events=len(t),clusters=len(labels),automated_good=sum(v=='good' for v in labels.values()),
            automated_mua=sum(v=='mua' for v in labels.values()),active_channels=len(active),original_input_pins_unchanged=True,resolved_settings_match=True)
        save(out/'status.json',status)
        save(out/'output-manifest.json',{p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()})
        print(json.dumps(status),flush=True)
    except Exception:
        (out/'failure.txt').write_text(traceback.format_exc());save(out/'status.json',dict(state='failed'));raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--preflight-output',type=Path)
    a=p.parse_args();run(a.config.resolve(),a.preflight_output)
