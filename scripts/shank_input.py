"""Read-only source/binary preflight for the four-shank recording layout.

No filtering, masking, sorting or export is performed. Hashes must be supplied
from independently recorded provenance, not inferred from the file being checked.
"""
import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def channel_ids():
    """Derive all four pad-ordered maps and check against retained legacy LUT."""
    original = np.arange(2048)
    vertical = (original % 64) * 32 + original // 64
    column = vertical // 128
    row = np.where(column > 10, 127 - vertical % 128, vertical % 128)
    mapping = np.column_stack((vertical // 512, row * 4 + column % 4))
    tree = ast.parse((ROOT/'legacy/utility/shank.py').read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'look_up_table')
    scope = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'legacy_mapping', 'exec'), scope)
    np.testing.assert_array_equal(mapping, scope['look_up_table']())
    ids = np.empty((4, 512), dtype=int)
    for shank in range(4):
        group = np.flatnonzero(mapping[:, 0] == shank)
        group = group[np.argsort(mapping[group, 1])]
        np.testing.assert_array_equal(mapping[group, 1], np.arange(512))
        ids[shank] = group
    np.testing.assert_array_equal(np.sort(ids.ravel()), original)
    return ids


def probe(shank):
    if shank not in range(4):
        raise ValueError('Shank must be 0..3')
    return dict(chanMap=list(range(512)), xc=[(i % 4)*30 for i in range(512)],
                yc=[(i // 4)*30 for i in range(512)], kcoords=[shank]*512, n_chan=512)


def check_binary(ds, binary, ids, samples, chunk_samples=25000):
    if binary.stat().st_size != samples * len(ids) * 4:
        raise ValueError('Binary byte size does not match declared sample/channel shape')
    raw = np.memmap(binary, mode='r', dtype='<f4', shape=(samples, len(ids)))
    checked = 0
    for a in range(0, samples, chunk_samples):
        b = min(samples, a + chunk_samples)
        expected = ds[:, a:b][ids].T.astype('<f4')
        if not np.isfinite(expected).all():
            raise ValueError('Nonfinite source values')
        np.testing.assert_array_equal(raw[a:b], expected)
        checked += expected.size
    return checked


def run(source, source_sha, binary, binary_sha, shank, samples, output):
    if shank not in range(4) or samples <= 0:
        raise ValueError('Invalid shank or sample count')
    output = output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'results'):
        raise ValueError('Fresh project results directory required')
    if sha(source) != source_sha or sha(binary) != binary_sha:
        raise ValueError('Input hash mismatch')
    ids = channel_ids()
    with h5py.File(source, 'r') as f:
        ds = f['signals']
        if ds.shape != (2048, samples) or ds.dtype != np.dtype('float16'):
            raise ValueError('Unexpected source shape/dtype')
        checked = check_binary(ds, binary, ids[shank], samples)
    if sha(source) != source_sha or sha(binary) != binary_sha:
        raise ValueError('Input changed during audit')
    output.mkdir(parents=True)
    with (output/'channel_map.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['shank_zero_based', 'binary_channel', 'original_channel_id', 'row', 'column', 'x_um', 'y_um'])
        for s in range(4):
            for b, gid in enumerate(ids[s]):
                writer.writerow([s, b, gid, b//4, b%4, (b%4)*30, (b//4)*30])
            (output/f'probe_shank{s}.json').write_text(json.dumps(probe(s), indent=2)+'\n')
    summary = dict(schema='shank-input-audit-v1', source=str(source.resolve()),
        source_sha256=source_sha, binary=str(binary.resolve()), binary_sha256=binary_sha,
        binary_shank=shank, samples=samples, binary_channels=512,
        binary_dtype='little-endian float32', conversion='exact float16-to-float32 cast only',
        source_values_compared=checked, original_sample_axis_preserved=True,
        all_four_maps_bijective=True, geometry_pitch_um=[30, 30],
        nominal_fs_hz=10000, physical_fs_hz=10080,
        other_shank_binaries_verified=False, script_sha256=sha(Path(__file__)),
        legacy_mapping_sha256=sha(ROOT/'legacy/utility/shank.py'))
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    (output/'manifest.json').write_text(json.dumps({p.name:sha(p) for p in output.iterdir()}, indent=2)+'\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--source-sha256', required=True)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--binary-sha256', required=True)
    p.add_argument('--shank', type=int, choices=range(4), required=True)
    p.add_argument('--samples', type=int, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    run(a.source, a.source_sha256, a.binary, a.binary_sha256, a.shank, a.samples, a.output)
