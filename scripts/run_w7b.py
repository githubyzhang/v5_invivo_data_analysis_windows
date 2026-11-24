"""Run a fresh, hash-bound W7B condition using the frozen pilot settings."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import traceback
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.review_pilot_round1 import sha, RAW_SHA


def run(condition, output):
    output = output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'results/extra4_shank0'):
        raise ValueError('Fresh local results directory required')
    evidence = ROOT/'worker_returns/extra4_shank0/pilot01/received'
    frozen = json.loads((evidence/'return-manifest.json').read_text())['files']
    for name, item in frozen.items():
        assert sha(evidence/name) == item['sha256'], name
    binary = ROOT/'data/extra4_shank0_float32.bin'
    assert sha(binary) == RAW_SHA
    settings = json.loads((evidence/'outputs/pilot01/review/resolved_settings.json').read_text())
    for name in ['filename', 'data_dir', 'results_dir']:
        settings.pop(name)
    probe = {k: np.asarray(v) if isinstance(v, list) else v for k, v in json.loads((evidence/'geometry/probe.json').read_text()).items()}
    excluded = [] if condition == 'control' else [248]
    import torch
    import kilosort
    assert kilosort.__version__ == '4.1.7' and torch.cuda.is_available()
    output.mkdir(parents=True)
    metadata = dict(condition=condition, excluded_binary_channels=excluded, raw_sha256=RAW_SHA,
        settings=settings, do_CAR=True, invert_sign=False, data_dtype='float32',
        seed_policy='Kilosort internally sets NumPy/Torch/CUDA seeds to 1 after preprocessing; cluster_init_seed=5. No extra deterministic-algorithm override.',
        versions={n: importlib.metadata.version(n) for n in ['kilosort','torch','numpy','scipy','faiss-cpu']},
        python=sys.version, gpu=torch.cuda.get_device_name(), script_sha256=sha(Path(__file__)),
        sorter_source_sha256=sha(ROOT/'.venv/Lib/site-packages/kilosort/run_kilosort.py'))
    (output/'run_contract.json').write_text(json.dumps(metadata, indent=2)+'\n')
    (output/'environment-lock.txt').write_bytes(subprocess.check_output([sys.executable,'-m','pip','freeze']))
    (output/'status.json').write_text('{"state":"running"}\n')
    try:
        kilosort.run_kilosort(settings=settings.copy(), probe=probe, filename=binary,
            results_dir=output/'kilosort4', data_dtype='float32', do_CAR=True,
            invert_sign=False, device=torch.device('cuda'), save_preprocessed_copy=False,
            bad_channels=excluded or None, verbose_log=True)
        source = output/'kilosort4'
        times = np.load(source/'spike_times.npy').ravel()
        clusters = np.load(source/'spike_clusters.npy').ravel()
        channel_map = np.load(source/'channel_map.npy').ravel()
        np.testing.assert_array_equal(channel_map, np.delete(np.arange(512), excluded))
        assert len(times) == len(clusters) and np.all((times >= 0) & (times < 3000000))
        assert np.issubdtype(times.dtype, np.integer)
        from kilosort.io import load_ops
        ops = load_ops(source/'ops.npy', device=torch.device('cpu'))
        for key, value in settings.items():
            assert ops['settings'][key] == value, key
        assert ops['n_chan_bin'] == 512 and len(ops['probe']['chanMap']) == 512-len(excluded)
        assert sha(binary) == RAW_SHA
        for name, item in frozen.items():
            assert sha(evidence/name) == item['sha256'], name
        state = dict(state='complete_review_pending', events=len(times), clusters=len(np.unique(clusters)),
            active_channels=len(channel_map), frozen_payloads_unchanged=len(frozen), raw_unchanged=True,
            resolved_scientific_settings_match=True)
        (output/'status.json').write_text(json.dumps(state, indent=2)+'\n')
        (output/'output-manifest.json').write_text(json.dumps({p.relative_to(output).as_posix():sha(p) for p in output.rglob('*') if p.is_file()}, indent=2)+'\n')
        print(json.dumps(state), flush=True)
    except Exception:
        (output/'failure.txt').write_text(traceback.format_exc())
        (output/'status.json').write_text('{"state":"failed"}\n')
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--condition', choices=['control','exclude248'], required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    run(args.condition, args.output)
