"""Annotation-only sliding-window candidate coincidence from v1 saved events.

Every integer window start is evaluated. The denominator counts channels usable
throughout the entire window; the numerator counts those channels with >=1 event.
No raw filtering, re-detection, event removal, or input-file writes occur.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import h5py
import numpy as np
from analysis.detect_recordings import merge_intervals, runs


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def sliding_counts(events, usable_intervals, n_samples, width):
    """Return distinct active / eligible channel counts at all full-window starts.

    events and usable_intervals are lists indexed by channel. Intervals must be
    sorted, disjoint half-open integer sample ranges. Event order is immaterial.
    A window is [start, start+width); event at its stop is excluded.
    """
    if not 1 <= width <= n_samples:raise ValueError('Window width outside recording')
    if len(events)!=len(usable_intervals):raise ValueError('Channel count mismatch')
    m=n_samples-width+1
    num_delta=np.zeros(m+1,np.int32);den_delta=np.zeros(m+1,np.int32)
    for times, intervals in zip(events,usable_intervals):
        times=np.sort(np.asarray(times,dtype=np.int64))
        if np.any((times<0)|(times>=n_samples)):raise ValueError('Event outside recording')
        prior_stop=0
        for a,b in intervals:
            a,b=int(a),int(b)
            if not 0<=a<b<=n_samples or a<prior_stop:raise ValueError('Invalid usable intervals')
            prior_stop=b
            if b-a<width:continue
            end=b-width+1
            den_delta[a]+=1;den_delta[end]-=1
            lo,hi=np.searchsorted(times,[a,b])
            spans=[]
            for t in times[lo:hi]:
                x=max(a,int(t)-width+1);y=min(end,int(t)+1)
                if x<y:spans.append((x,y))
            for x,y in merge_intervals(spans):
                num_delta[int(x)]+=1;num_delta[int(y)]-=1
    active=np.cumsum(num_delta[:-1]);eligible=np.cumsum(den_delta[:-1])
    assert np.all((active>=0)&(active<=eligible))
    return active.astype(np.uint16),eligible.astype(np.uint16)


def expand_windows(starts,width,n):
    """Union sample support of selected windows, with no extra time padding."""
    delta=np.zeros(n+1,np.int32)
    for a,b in runs(starts):
        delta[int(a)]+=1;delta[int(b)+width-1]-=1
    return np.cumsum(delta[:-1])>0


def usable_from_file(f,config):
    channels,n=map(int,config['shape']);step=int(config['noise_window_samples'])
    valid=f['quality/valid_noise_window'][:].astype(bool)
    guards=f['quality/flat_guard_intervals'][:]
    edge_left,edge_right=config['physical_edge_exclusion_samples']
    reference=f['quality/reference_eligible'][:].astype(bool)
    result=[]
    for ch in range(channels):
        mask=np.repeat(valid[ch],step)[:n]
        if not reference[ch]:mask[:]=False
        mask[:edge_left]=False
        if edge_right:mask[n-edge_right:]=False
        for _,a,b in guards[guards[:,0]==ch]:mask[int(a):int(b)]=False
        # Check reconstructed observation support against saved exact exposure.
        expected=f['quality/usable_samples_per_channel_window'][ch]
        actual=np.array([mask[a:min(a+step,n)].sum() for a in range(0,n,step)])
        np.testing.assert_array_equal(actual,expected)
        result.append(runs(mask))
    return result


def run(input_path,output,*,profile=None,widths_ms=None,fractions=None,min_channels=1024):
    custom=widths_ms is not None or fractions is not None
    if profile is not None and custom:raise ValueError('Choose a named profile or an explicit grid, not both')
    if custom:
        if widths_ms is None or fractions is None:raise ValueError('Custom grids require both widths and quorums')
        selected=None
    else:
        profile=profile or 'broad'
        if profile not in ('broad','tight'):raise ValueError('Unknown warning profile')
        widths_ms=(1,5);fractions=(.05,)
        selected={'broad':'w5ms_q5','tight':'w1ms_q5'}[profile]
    names={name:key for name,key in {'broad':'w5ms_q5','tight':'w1ms_q5'}.items()
           if int(key.split('ms')[0][1:]) in widths_ms and .05 in fractions}
    input_path=Path(input_path).resolve();output=Path(output)
    if output.exists():raise FileExistsError(f'Refusing existing output: {output}')
    if not widths_ms or not fractions:raise ValueError('Empty parameter grid')
    if any(not np.isfinite(ms) or ms<=0 or int(ms)!=ms for ms in widths_ms):raise ValueError('Widths must be positive integer milliseconds')
    if any(not np.isfinite(q) or abs(q*100-round(q*100))>1e-9 for q in fractions):raise ValueError('Quorums must be whole percentages')
    if len(set(fractions))!=len(fractions):raise ValueError('Duplicate quorums')
    if min_channels<1:raise ValueError('min_channels must be positive')
    if any(not 0 < q <= 1 for q in fractions):raise ValueError('Invalid quorum')
    source_hash=sha256(input_path);begin=time.time()
    with h5py.File(input_path,'r') as f:
        if not f.attrs.get('complete',False):raise ValueError('Input detection is incomplete')
        config=json.loads(f.attrs['config_json'])
        channels,n=map(int,config['shape']);fs=int(config['nominal_fs_hz'])
        if channels>65535:raise ValueError('Count storage supports up to 65535 channels')
        if min_channels>channels:raise ValueError('Minimum exceeds channel count')
        widths=[int(round(ms*fs/1000)) for ms in widths_ms]
        if len(set(widths))!=len(widths) or any(w<1 or w>n for w in widths):raise ValueError('Invalid widths')
        channel=f['spikes/channel_id'][:];sample=f['spikes/sample_index'][:]
        offsets=f['spikes/channel_offsets'][:]
        events=[sample[int(offsets[ch]):int(offsets[ch+1])] for ch in range(channels)]
        usable=usable_from_file(f,config)
        old_available=np.zeros(n,bool);old20=np.zeros(n,bool)
        for a,b in f['quality/shared_available_intervals'][:]:old_available[int(a):int(b)]=True
        for a,b in f['quality/shared20_intervals'][:]:old20[int(a):int(b)]=True
        if np.any(old20&~old_available):raise ValueError('Old warnings outside assessed time')
    output.mkdir(parents=True)
    protocol={'schema':'candidate-coincidence-v1','input':str(input_path),'input_sha256':source_hash,
        'generator_sha256':sha256(__file__),'nominal_fs_hz':fs,'physical_fs_hz':config['physical_fs_hz'],
        'source_config':config,'widths_ms':list(widths_ms),'fractions':list(fractions),
        'minimum_eligible_channels':min_channels,'primary':selected,'default_warning':profile,
        'named_warnings':names,'policy_version':'2026-11-23-broad-default',
        'eligibility':'channel usable throughout full half-open window; exact saved support reconstructed',
        'numerator':'distinct eligible channels with at least one candidate in window',
        'stride_samples':1,'extra_guard_samples':0,'policy':'annotation only; no events removed',
        'selection':('Adopted named annotation profiles; both retained, selected profile is the default warning' if selected else 'Explicit research grid; no selected default warning'),
        'availability':'a sample/event is assessed if covered by at least one window meeting minimum channel count',
        'limits':['Candidate/threshold dependent; can miss shared signals without detected events.',
          'No ground truth; genuine synchronized activity can be flagged.',
          'Full-window eligibility is stricter than sample-wise eligibility; boundary channels may be absent.',
          'No raw waveform reconstruction; existing baseline/broadband coverage remains partial.']}
    summaries={}
    with h5py.File(output/'annotations.partial.h5','w') as dest:
        dest.attrs['schema']='candidate-coincidence-v1';dest.attrs['input_sha256']=source_hash
        dest.attrs['protocol_json']=json.dumps(protocol);dest.attrs['complete']=False
        dest.create_dataset('events/channel_id',data=channel,compression='gzip')
        dest.create_dataset('events/sample_index',data=sample,compression='gzip')
        for ms,w in zip(widths_ms,widths):
            active,eligible=sliding_counts(events,usable,n,w)
            available_starts=eligible>=min_channels
            available=expand_windows(available_starts,w,n)
            tg=dest.create_group(f'tracks/w{ms}ms')
            tg.attrs['width_samples']=w
            tg.create_dataset('active_channels',data=active,compression='gzip')
            tg.create_dataset('eligible_channels',data=eligible,compression='gzip')
            tg.create_dataset('available_intervals',data=runs(available),compression='gzip')
            tg.create_dataset('event_available',data=available[sample],compression='gzip')
            ratio=np.divide(active,eligible,out=np.zeros(len(active),float),where=eligible>0)
            score=np.where(available_starts,ratio,-1)
            peak=int(np.argmax(score)) if available_starts.any() else None
            for q in fractions:
                name=f'w{ms}ms_q{round(q*100)}'
                hits=available_starts&(active>=np.ceil(q*eligible))
                mask=expand_windows(hits,w,n)
                group=dest.create_group(f'variants/{name}')
                group.create_dataset('intervals',data=runs(mask),compression='gzip')
                group.create_dataset('event_warning',data=mask[sample],compression='gzip')
                # Potential exposure affected, not an actual exclusion.
                prefix=np.r_[0,np.cumsum(mask,dtype=np.int64)]
                affected=sum(int(np.sum(prefix[r[:,1]]-prefix[r[:,0]])) for r in usable if len(r))
                summaries[name]={'flagged_seconds':float(mask.sum()/fs),'interval_count':len(runs(mask)),
                    'flagged_candidates':int(mask[sample].sum()),'assessed_seconds':float(available.sum()/fs),
                    'assessed_candidates':int(available[sample].sum()),'potential_usable_channel_seconds_affected':affected/fs,
                    'flagged_candidates_in_old_assessment':int((mask[sample]&old_available[sample]).sum()),
                    'flagged_candidates_also_shared20':int((mask[sample]&old20[sample]).sum()),
                    'flagged_candidates_outside_old_assessment':int((mask[sample]&~old_available[sample]).sum()),
                    'old_shared20_candidates_assessed':int((old20[sample]&available[sample]).sum()),
                    'peak_window_start_sample':peak,'peak_fraction':float(score[peak]) if peak is not None else None,
                    'peak_active_channels':int(active[peak]) if peak is not None else None,
                    'peak_eligible_channels':int(eligible[peak]) if peak is not None else None}
                assert not (mask&~available).any()
        for label,key in names.items():
            group=dest.create_group(f'warnings/{label}')
            group.attrs['variant']=key
            track='w5ms' if label=='broad' else 'w1ms'
            for field in ('intervals','event_warning'):group[field]=dest[f'variants/{key}/{field}']
            for field in ('available_intervals','event_available'):group[field]=dest[f'tracks/{track}/{field}']
        if selected:
            dest['warnings/default']=dest[f'warnings/{profile}']
            dest.attrs['default_warning']=profile
            dest.attrs['primary']=selected
        dest.attrs['complete']=True
    if sha256(input_path)!=source_hash:raise RuntimeError('Input changed during annotation')
    (output/'annotations.partial.h5').rename(output/'annotations.h5')
    summary={'input_candidates':len(sample),'recording_samples':n,'channels':channels,
        'old_shared_assessed_seconds':float(old_available.sum()/fs),'old_shared20_candidates':int(old20[sample].sum()),
        'default_warning':profile,'primary':selected,'named_warnings':names,
        'variants':summaries,'elapsed_seconds':time.time()-begin,'annotations_sha256':sha256(output/'annotations.h5')}
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--min-channels',type=int,default=1024)
    p.add_argument('--widths-ms',type=int,nargs='+',default=None)
    p.add_argument('--quorums-percent',type=int,nargs='+',default=None)
    p.add_argument('--profile',choices=['broad','tight'],help='Default: broad; both profiles are saved')
    a=p.parse_args()
    if (a.widths_ms is None)!=(a.quorums_percent is None):p.error('Custom grids require both --widths-ms and --quorums-percent')
    if a.profile and a.widths_ms is not None:p.error('--profile cannot be combined with a custom grid')
    print(json.dumps(run(a.input,a.output,min_channels=a.min_channels,profile=a.profile,
        widths_ms=None if a.widths_ms is None else tuple(a.widths_ms),
        fractions=None if a.quorums_percent is None else tuple(q/100 for q in a.quorums_percent)),indent=2))
