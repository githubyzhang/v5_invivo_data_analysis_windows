"""Validate portable saved fixtures without raw recordings."""
from pathlib import Path
import hashlib,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import h5py,numpy as np
from analysis.detect_recordings import validate
root=Path(__file__).resolve().parent
for rec,total,tight,broad,active in [(4,115992,577,714,244),(5,173029,41175,42155,325)]:
    p=root/f'reference_outputs/extra{rec}/spikes.h5'
    validate(p)
    with h5py.File(p) as f,h5py.File(p.parent/'coincidence/annotations.h5') as w:
        assert w.attrs['complete']
        assert w.attrs['input_sha256']==hashlib.sha256(p.read_bytes()).hexdigest()
        for key in ('channel_id','sample_index'):
            np.testing.assert_array_equal(f['spikes/'+key][:],w['events/'+key][:])
        assert len(f['spikes/sample_index'])==total
        assert int((f['spikes/counts_per_channel'][:]>50).sum())==active
        assert w['warnings/default'].id==w['warnings/broad'].id
        for name,count in [('tight',tight),('broad',broad)]:
            mask=w[f'warnings/{name}/event_warning'][:];av=w[f'warnings/{name}/event_available'][:]
            assert int(mask.sum())==count and not np.any(mask&~av)
    print(f'extra_{rec}: structure, identity, warning counts and active counts passed')
print('Reference checks passed; this does not establish biological accuracy.')
