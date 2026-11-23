"""Build the portable extra4/shank0 assignment without altering source data."""
import argparse,ast,csv,hashlib,json,shutil,sys
from pathlib import Path
import h5py,numpy as np
REPO=Path(__file__).resolve().parents[1]
SOURCE=Path('/Volumes/YZ/recording/invivo/26-11-06/0192/extra_4_signals.h5')
def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def channel_map():
    # Execute only the self-contained legacy mapping function, avoiding unrelated imports.
    tree=ast.parse((REPO/'legacy/utility/shank.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='look_up_table')
    scope={};exec(compile(ast.Module(body=[node],type_ignores=[]),'legacy_mapping','exec'),scope)
    mapping=np.asarray(scope['look_up_table']());assert mapping.shape==(2048,2)
    assert len(np.unique(mapping,axis=0))==2048
    ids=np.flatnonzero(mapping[:,0]==0);ids=ids[np.argsort(mapping[ids,1])]
    np.testing.assert_array_equal(mapping[ids,1],np.arange(512))
    return ids,mapping

def build(dest,resume=False):
    if dest.exists() and not resume:raise FileExistsError(dest)
    if resume and ((dest/"manifest.json").exists() or not any((dest/('data/extra4_shank0_float32'+suffix)).exists() for suffix in ['.partial','.bin'])):raise ValueError("Resume requires an unfinished package with an exported binary")
    before=SOURCE.stat();ids,mapping=channel_map()
    shutil.copytree(REPO/'handoffs/kilosort4-extra4-shank0',dest,dirs_exist_ok=resume,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ['data','geometry','reference','outputs','docs/rounds']:(dest/name).mkdir(parents=True,exist_ok=True)
    shutil.copy2(REPO/'docs/documentation-workflow.md',dest/'docs/documentation-workflow.md')
    shutil.copy2(REPO/'docs/OUTPUTS.md',dest/'reference/OUTPUTS.md')
    shutil.copy2(REPO/'docs/VIEWER_HANDOFF.md',dest/'reference/VIEWER_HANDOFF.md')
    shutil.copy2(REPO/'legacy/utility/shank.py',dest/'reference/legacy_shank.py')
    shutil.copy2(REPO/'results/spike_detection_ma50_adaptive/extra4/spikes.h5',dest/'reference/extra4_candidates.h5')
    with open(dest/'geometry/channel_map.csv','w',newline='') as f:
        w=csv.writer(f);w.writerow(['binary_channel','original_channel_id','shank_zero_based','row','column','x_um','y_um'])
        for local,original in enumerate(ids):w.writerow([local,int(original),0,local//4,local%4,(local%4)*30,(local//4)*30])
    probe={'chanMap':list(range(512)),'xc':[(i%4)*30 for i in range(512)],'yc':[(i//4)*30 for i in range(512)],'kcoords':[0]*512,'n_chan':512}
    (dest/'geometry/probe.json').write_text(json.dumps(probe,indent=2)+'\n')
    p=dest/'data/extra4_shank0_float32.bin';h=hashlib.sha256()
    partial=p if resume and p.exists() else p.with_suffix('.partial')
    existing=partial.stat().st_size if resume else 0
    if existing%2048:raise ValueError('Partial binary ends within a sample; preserve for diagnosis')
    completed=existing//2048
    if completed>3000000:raise ValueError('Oversized partial binary')
    prior=np.memmap(partial,dtype='<f4',mode='r',shape=(completed,512)) if completed else None
    print(f'Resuming after source verification of {completed} saved samples' if resume else 'Starting export',flush=True)
    with h5py.File(SOURCE,'r') as src,open(partial,'ab' if resume else 'xb') as out:
        ds=src['signals'];assert ds.shape==(2048,3000000) and ds.dtype==np.float16
        for a in range(0,3000000,25000):
            b=min(a+25000,3000000);block=ds[:,a:b][ids].T.astype('<f4',order='C')
            if not np.isfinite(block).all():raise ValueError('Nonfinite source data')
            skip=max(0,min(b,completed)-a)
            if skip:np.testing.assert_array_equal(block[:skip],prior[a:a+skip])
            payload=block.tobytes(order='C');out.write(payload[skip*2048:]);h.update(payload)
            (dest/'export_progress.json').write_text(json.dumps({'stage':'export','samples_verified_or_written':b,'total_samples':3000000})+'\n')
            if b%250000==0:print(f'Exported {b}/3000000 samples',flush=True)
    assert before.st_size==SOURCE.stat().st_size and before.st_mtime_ns==SOURCE.stat().st_mtime_ns
    if prior is not None:del prior
    if partial!=p:partial.rename(p)
    print('Verifying binary hash and source samples',flush=True)
    assert p.stat().st_size==6144000000 and digest(p)==h.hexdigest()
    sample_checks=[0,1,9999,10000,1499999,1500000,2999998,2999999]
    binary=np.memmap(p,dtype='<f4',mode='r',shape=(3000000,512))
    with h5py.File(SOURCE,'r') as src:
        for sample in sample_checks:np.testing.assert_array_equal(binary[sample],src['signals'][:,sample][ids].astype('<f4'))
    del binary
    manifest={'schema':'kilosort-worker-package-v1','prepared_date':'2026-11-21','source':{'path':str(SOURCE),'size_bytes':before.st_size,'mtime_ns':before.st_mtime_ns,'dataset':'signals','shape':[2048,3000000],'dtype':'float16','full_source_file_hashed':False},'export':{'recording':'extra_4','shank_zero_based':0,'shape_samples_channels':[3000000,512],'dtype':'little-endian float32','numerical_change':'exact float16 to float32 cast only','nominal_fs_hz':10000,'physical_fs_hz':10080,'row_pitch_um':30,'column_pitch_um':30,'geometry_confirmation':'User confirmed legacy spatial arrangement and both pitches on 2026-11-20'},'validation':{'legacy_mapping_bijective':True,'export_full_hash_readback_verified':True,'all_channels_source_exact_sample_checks':sample_checks,'finite_source_values_checked':True,'windows_kilosort_tested':False},'files':{}}
    for path in sorted(dest.rglob('*')):
        if path.is_file() and path.name!='export_progress.json':manifest['files'][path.relative_to(dest).as_posix()]={'bytes':path.stat().st_size,'sha256':digest(path) if path!=p else h.hexdigest()}
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (dest/'export_progress.json').write_text('{"stage":"complete"}\n')
    print('COMPLETE '+str(dest),flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--resume',action='store_true');args=ap.parse_args();build(args.output,args.resume)
