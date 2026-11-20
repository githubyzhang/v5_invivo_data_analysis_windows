"""Audit completed candidate files and selected measurements against source data."""
import argparse,hashlib,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import h5py
import numpy as np
from analysis.detect_recordings import validate,preprocess,window_scale,CONTEXT,FS


def audit(folder):
    folder=Path(folder);config=json.loads((folder/'config.json').read_text());summary=json.loads((folder/'summary.json').read_text())
    path=folder/'spikes.h5';validate(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==summary['output_sha256']
    for code,digest in config['source_code_sha256'].items():assert hashlib.sha256(Path(code).read_bytes()).hexdigest()==digest
    source=Path(config['source']);st=source.stat();assert st.st_size==config['source_size_bytes'] and st.st_mtime_ns==config['source_mtime_ns']
    n=config['shape'][1];ma=config['ma_samples'];event_checks=[];noise_checks=[]
    with h5py.File(path,'r') as out,h5py.File(source,'r') as rawfile:
        ds=rawfile['signals'];sp=out['spikes'];total=len(sp['sample_index'])
        assert total==summary['candidates']
        np.testing.assert_allclose(out['quality/usable_samples_per_channel_window'][:].sum()/FS,summary['usable_channel_seconds'])
        for i in np.unique(np.linspace(0,total-1,min(total,20),dtype=int)) if total else []:
            ch=int(sp['channel_id'][i]);p=int(sp['sample_index'][i]);a=max(0,p-1);b=min(n,p+2)
            lo=max(0,a-CONTEXT);hi=min(n,b+CONTEXT);raw=ds[ch,lo:hi].astype(float)
            residual,core,flat,invalid=preprocess(raw,lo,a,b,n,ma)
            np.testing.assert_allclose(-residual[p-lo],sp['negative_amplitude'][i],rtol=1e-9,atol=1e-12)
            assert not invalid[p-a];event_checks.append({'channel':ch,'sample_index':p})
        pairs=sorted({(e['channel'],e['sample_index']//FS) for e in event_checks})
        for ch,w in pairs[:6]:
            a=w*FS;b=min(n,a+FS);lo=max(0,a-CONTEXT);hi=min(n,b+CONTEXT)
            residual,core,flat,invalid=preprocess(ds[ch,lo:hi].astype(float),lo,a,b,n,ma)
            sigma,count=window_scale(residual[core],invalid)
            np.testing.assert_allclose(sigma,out['noise/mad'][ch,w],rtol=1e-9,atol=1e-12)
            assert count==out['quality/usable_samples_per_channel_window'][ch,w]
            noise_checks.append({'channel':ch,'window_index':w})
        if config['mode']=='adaptive':
            sig=out['noise/mad'][:];valid=out['quality/valid_noise_window'][:]
            for w in range(sig.shape[1]):
                expected=np.median(sig[:,w][valid[:,w]]) if valid[:,w].any() else np.nan
                np.testing.assert_allclose(expected,out['noise/median_floor'][w],equal_nan=True)
    return {'output':str(path),'candidates':summary['candidates'],'output_hash_verified':True,
        'source_metadata_and_code_hashes_verified':True,'all_saved_events_structurally_valid':True,
        'source_event_amplitude_checks':event_checks,'source_noise_window_checks':noise_checks,
        'scope':'Selected source measurements checked, not independent re-detection of every source sample; not biological accuracy validation.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path,nargs='?',default=Path('results/spike_detection_ma50_adaptive'))
    root=ap.parse_args().root;results={}
    for folder in sorted(root.glob('extra[45]')):
        results[folder.name]=audit(folder);print(folder.name,'verified',results[folder.name]['candidates'],flush=True)
    if not results:raise ValueError('No completed recording outputs found')
    (root/'validation.json').write_text(json.dumps(results,indent=2)+'\n')

if __name__=='__main__':main()
