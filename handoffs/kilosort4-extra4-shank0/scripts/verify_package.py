"""Verify immutable package payload after copying to Windows. No GPU required."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()
def verify():
    manifest=json.loads((ROOT/'manifest.json').read_text())
    for rel,info in manifest['files'].items():
        path=ROOT/rel
        if not path.is_file() or path.stat().st_size!=info['bytes'] or digest(path)!=info['sha256']:
            raise ValueError('Package mismatch: '+rel)
    import numpy as np
    probe=json.loads((ROOT/'geometry/probe.json').read_text());cfg=json.loads((ROOT/'config.json').read_text())
    n,c=cfg['shape_samples_channels'];path=ROOT/cfg['data_file']
    assert path.stat().st_size==n*c*4
    np.testing.assert_array_equal(probe['chanMap'],np.arange(c))
    coords=np.column_stack((probe['xc'],probe['yc']));assert len(np.unique(coords,axis=0))==c
    assert set(probe['kcoords'])=={0} and probe['n_chan']==c
    print('PASS: payload hashes, binary size and probe indexing',flush=True)
    return manifest
if __name__=='__main__':verify()
