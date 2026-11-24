"""Audit W10 evidence independently and add descriptive subgroup context."""
import argparse
import json
from pathlib import Path
import numpy as np
import h5py
from scipy.spatial.distance import cdist
from review_w9_good import ROOT,RUN,rows,verify
from review_pilot_round1 import sha,write_csv,RAW_SHA


def run(report):
    report=report.resolve()
    if not report.is_relative_to(ROOT/'results/extra4_shank0') or (report/'independent_checks.json').exists():
        raise ValueError('Fresh audit required')
    verify(report,'report-manifest.json')
    summary=json.loads((report/'summary.json').read_text())
    src=RUN/'kilosort4';t=np.load(src/'spike_times.npy').ravel();cl=np.load(src/'spike_clusters.npy').ravel()
    pcs=np.load(src/'pc_features.npy');pci=np.load(src/'pc_feature_ind.npy');cmap=np.load(src/'channel_map.npy').ravel()
    raw=np.memmap(ROOT/'data/extra4_shank0_float32.bin',mode='r',dtype='<f4',shape=(3000000,512))
    windows=values=0
    def read(ids,ch):
        nonlocal windows,values
        result=[]
        for i in ids:
            a=np.array(raw[int(t[i])-100:int(t[i])+101,ch],dtype=np.float32)*1e6
            a-=np.median(a[:70],axis=0)[None,:];result.append(a);windows+=1;values+=a.size
        return np.array(result) if len(result) else np.empty((0,201,len(ch)),dtype=np.float32)
    def brute(a,b,self_pairs=False):
        result=[]
        for start in range(0,len(a),128):
            delta=b[None,:]-a[start:start+128,None];mask=abs(delta)<=500
            if self_pairs:mask[np.arange(len(delta)),np.arange(start,start+len(delta))]=False
            result.extend(delta[mask].tolist())
        return np.sort(result)
    def feature(ids,cid,common):
        cols=[np.flatnonzero(pci[cid]==np.flatnonzero(cmap==ch)[0])[0] for ch in common]
        return pcs[ids][:,:,cols].reshape(len(ids),-1).astype(float)
    screen={int(r['cluster_id']):r for r in rows(report/'mua_screen.csv')}
    for cid in summary['mua_ids']:
        with np.load(report/f'mua_{cid}.npz') as z:
            ids=z['event_indices'];np.testing.assert_array_equal(ids,np.flatnonzero(cl==cid))
            np.testing.assert_array_equal(read(z['selected'],z['channels']),z['waves'])
            if len(z['selected']):np.testing.assert_array_equal(z['waves'].mean(0),z['mean'])
            else:assert np.isnan(z['mean']).all()
            np.testing.assert_array_equal(brute(t[ids],t[ids],True),np.sort(z['acg_lags']))
            for q in range(4):
                qi=z[f'q{q}_events'];assert np.all(cl[qi]==cid) and np.all(t[qi]//750000==q)
                if len(qi):np.testing.assert_array_equal(read(qi,z['channels']).mean(0),z['quarter_means'][q])
                else:assert np.isnan(z['quarter_means'][q]).all()
            r=screen[cid];assert len(ids)==int(r['events'])
            assert sum(np.diff(np.sort(t[ids]))<20)==int(r['isi_lt20'])
            assert sum((t[ids]<100)|(t[ids]>=2999900))==int(r['boundary_events'])
    sidecar=ROOT/'results/custom_detector/kilosort_pilot01_quality_windows01/external_quality.h5'
    assert sha(sidecar)=='df0289595e71f44b14a7755d6beea3a2b99a500cde3bec81fe8bc82d9d149d8f'
    with h5py.File(sidecar,'r') as f:intervals={n:f['intervals/'+n][:] for n in ['broad_warning','tight_warning','broad_available']}
    def annotations(ids):
        result={}
        for name,spans in intervals.items():
            mask=np.zeros(len(ids),bool)
            for start,stop in spans:mask|=(t[ids]>=start)&(t[ids]<stop)
            result[name]=int(mask.sum())
        return result
    context=[];shape=[]
    for cid in summary['diagnostic_populations']:
        with np.load(report/f'population_{cid}.npz') as z:
            ids=z['event_indices'];np.testing.assert_array_equal(ids,np.flatnonzero(cl==cid))
            np.testing.assert_array_equal(cmap[pci[cid]],z['feature_channels'])
            x=feature(ids,cid,z['feature_channels']);np.testing.assert_array_equal(x,z['feature_values'])
            np.testing.assert_allclose((x-z['center'])@z['axes'].T,z['projection'],atol=1e-10)
            labels=z['labels']
            if cid!=31:
                nearest=cdist(x,z['centroids'],'sqeuclidean').argmin(1);np.testing.assert_array_equal(nearest,labels)
                for g in [0,1]:np.testing.assert_allclose(x[labels==g].mean(0),z['centroids'][g],atol=1e-12)
            else:
                old=ROOT/'results/extra4_shank0/w7b-control01/kilosort4'
                ot=np.load(old/'spike_times.npy').ravel();oc=np.load(old/'spike_clusters.npy').ravel()
                hits=[(abs(t[ids,None]-ot[oc==c][None,:])<=2).any(1) for c in [31,33]]
                expected=np.where(hits[0],np.where(hits[1],3,0),np.where(hits[1],1,2))
                np.testing.assert_array_equal(expected,labels)
            for k,g in enumerate(z['groups']):
                gi=z[f'group_{g}_events'];np.testing.assert_array_equal(gi,ids[labels==g])
                selected=z[f'group_{g}_selected'];assert np.isin(selected,gi).all()
                w=read(selected,z['channels']);np.testing.assert_array_equal(w,z[f'group_{g}_waves'])
                np.testing.assert_array_equal(w.mean(0),z['means'][k])
                context.append(dict(kind='population',cluster=cid,group=str(g),events=len(gi),**annotations(gi)))
            a,b=z['means'][:2];a=a.astype(float);b=b.astype(float)
            for shift in range(-3,4):
                av=a[80:141].ravel();bv=b[80+shift:141+shift].ravel()
                shape.append(dict(cluster=cid,shift_samples=shift,correlation=float(np.corrcoef(av,bv)[0,1]),
                    least_squares_b_scale_to_a=float(np.dot(av,bv)/np.dot(bv,bv))))
    for ca,cb in summary['pairs']:
        with np.load(report/f'overlap_{ca}_{cb}.npz') as z:
            ia,ib=z['ids_a'],z['ids_b'];assert np.all(cl[ia]==ca) and np.all(cl[ib]==cb)
            np.testing.assert_array_equal(brute(t[ia],t[ib]),np.sort(z['cross_lags']))
            m=z['matches'];assert len(np.unique(m[:,0]))==len(m) and len(np.unique(m[:,1]))==len(m)
            assert np.all(abs(t[ia[m[:,0]]]-t[ib[m[:,1]]])<=2)
            # Independent dynamic-programming maximum-cardinality count.
            prev=np.zeros(len(ib)+1,int)
            for ta in t[ia]:
                current=prev.copy()
                for j,tb in enumerate(t[ib],1):current[j]=max(prev[j],current[j-1],prev[j-1]+int(abs(int(ta)-int(tb))<=2))
                prev=current
            assert len(m)==prev[-1]
            fa=feature(ia,ca,z['common_binary_channels']);fb=feature(ib,cb,z['common_binary_channels'])
            for letter,x in [('a',fa),('b',fb)]:
                np.testing.assert_array_equal(x,z['features_'+letter])
                np.testing.assert_allclose((x-z['center'])@z['axes'].T,z['projection_'+letter],atol=1e-10)
            x=np.r_[fa,fb];d=cdist(x,x,'sqeuclidean');np.fill_diagonal(d,np.inf)
            nn=np.argsort(d,axis=1,kind='stable')[:,:5];np.testing.assert_array_equal(nn,z['neighbor_indices'])
            origin=np.r_[np.zeros(len(fa),int),np.ones(len(fb),int)]
            np.testing.assert_array_equal((origin[nn]!=origin[:,None]).mean(1),z['other_fraction'])
            for label,ids in enumerate([ia,ib]):
                hit=np.zeros(len(ids),bool);hit[m[:,label]]=True
                for cohort,mask in [('matched',hit),('other',~hit)]:
                    selected=z[f'{label}_{cohort}_selected'];assert np.isin(selected,ids[mask]).all()
                    np.testing.assert_array_equal(read(selected,z['channels']),z[f'{label}_{cohort}_waves'])
                    context.append(dict(kind='overlap',cluster=[ca,cb][label],group=f'{ca}/{cb}:{cohort}',events=int(sum(mask)),**annotations(ids[mask])))
    write_csv(report/'population_shape_sensitivity.csv',shape);write_csv(report/'cohort_coincidence_annotations.csv',context)
    for folder,digest in summary['input_manifests'].items():
        path=ROOT/folder;manifest='output-manifest.json' if (path/'output-manifest.json').exists() else 'report-manifest.json'
        assert sha(path/manifest)==digest;verify(path,manifest)
    assert sha(ROOT/'data/extra4_shank0_float32.bin')==RAW_SHA
    checks=dict(raw_windows_checked=windows,raw_values_checked=values,mua_acgs_bruteforce_checked=39,
        quarter_means_pass=True,populations_checked=5,control31_33_membership_pass=True,forced_centroid_partition_consistency_pass=True,
        pairs_bruteforce_and_matching_dp_checked=6,physical_feature_mapping_projections_and_neighbors_pass=True,
        source_manifests_and_raw_unchanged=True,script_sha256=sha(Path(__file__)))
    (report/'independent_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    (report/'report-manifest.json').write_text(json.dumps({p.name:sha(p) for p in report.iterdir() if p.is_file() and p.name!='report-manifest.json'},indent=2)+'\n')
    print(json.dumps(checks,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True)
    run(p.parse_args().report)
