"""Windows baseline launcher; validate installed Kilosort version before use."""
from pathlib import Path
import argparse,json,platform,subprocess,sys,traceback
import numpy as np
from verify_package import ROOT,verify

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-name',required=True);args=ap.parse_args()
    if not args.run_name.replace('-','').replace('_','').isalnum():raise ValueError('Use letters, numbers, hyphens or underscores for run name')
    verify()
    import torch,kilosort
    if not str(kilosort.__version__).startswith('4.'):raise RuntimeError('Kilosort4 required')
    if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable; no silent CPU fallback')
    (torch.ones((32,32),device='cuda')@torch.ones((32,32),device='cuda')).sum().item();torch.cuda.synchronize()
    cfg=json.loads((ROOT/'config.json').read_text());probe={k:np.asarray(v) if isinstance(v,list) else v for k,v in json.loads((ROOT/'geometry/probe.json').read_text()).items()}
    out=ROOT/'outputs'/args.run_name;out.mkdir(parents=True,exist_ok=False)
    env={'python':sys.version,'platform':platform.platform(),'kilosort':kilosort.__version__,'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),'gpu_memory_bytes':torch.cuda.get_device_properties(0).total_memory,'cuda_computation_passed':True}
    (out/'environment.json').write_text(json.dumps(env,indent=2)+'\n')
    (out/'environment-lock.txt').write_bytes(subprocess.check_output([sys.executable,'-m','pip','freeze']))
    (out/'config_used.json').write_text(json.dumps(cfg,indent=2)+'\n')
    (out/'status.json').write_text(json.dumps({'state':'running'})+'\n')
    try:
        kilosort.run_kilosort(settings=cfg['settings'].copy(),probe=probe,filename=ROOT/cfg['data_file'],results_dir=out/'kilosort4',data_dtype=cfg['data_dtype'],do_CAR=cfg['do_CAR'],invert_sign=cfg['invert_sign'],device=torch.device('cuda'),save_preprocessed_copy=cfg['save_preprocessed_copy'],verbose_log=True)
        times=np.load(out/'kilosort4/spike_times.npy').reshape(-1);clu=np.load(out/'kilosort4/spike_clusters.npy').reshape(-1)
        assert len(times)==len(clu) and np.isfinite(times).all() and np.isfinite(clu).all()
        assert ((times>=0)&(times<cfg['shape_samples_channels'][0])).all() and (times==np.floor(times)).all()
        assert (clu==np.floor(clu)).all()
        result={'state':'sorter_completed_review_pending','events':len(times),'clusters':len(np.unique(clu)),'sample_bounds_checked':True}
        (out/'status.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
    except Exception:
        (out/'failure.txt').write_text(traceback.format_exc());(out/'status.json').write_text('{"state":"failed"}\n');raise
if __name__=='__main__':main()
