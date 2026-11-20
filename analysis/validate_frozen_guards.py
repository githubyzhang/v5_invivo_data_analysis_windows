"""Apply previously chosen rules to prespecified, newly inspected intervals.

Run protocol is saved before opening recordings. No parameter search is performed
on the new intervals. Existing helpers compute diagnostic variants, but only the
two frozen keys are used for conclusions in the companion report.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis.compare_detectors import run_segment
from analysis.shared_artifacts import evaluate_segment

RULES=['b3_h6_f50_g10','b3_h6_f50_g20']
STARTS=[90,240]
DURATION=5


def assert_disjoint(intervals,previous):
    for source,a,b in intervals:
        for old in previous.values():
            if str(Path(source).resolve())==str(Path(old['source']).resolve()):
                if max(a,old['sample_start'])<min(b,old['sample_stop']):
                    raise ValueError('New evaluation overlaps a previously inspected interval')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--directory',type=Path,default=Path('/Volumes/YZ/recording/invivo/26-11-06/0192'))
    ap.add_argument('--output',type=Path,default=Path('results/frozen_guard_validation'))
    args=ap.parse_args()
    missing=[args.directory/f'extra_{rec}_signals.h5' for rec in [4,5,6] if not (args.directory/f'extra_{rec}_signals.h5').is_file()]
    if missing: ap.error('Recording files unavailable; reconnect the source drive or supply --directory. Missing: '+', '.join(str(p) for p in missing))
    if args.output.exists() and any(args.output.iterdir()): ap.error('output must be empty')
    previous=json.loads(Path('results/controlled_comparison/summary.json').read_text())
    plan=[(str(args.directory/f'extra_{r}_signals.h5'),t*10000,(t+DURATION)*10000) for r in [4,5,6] for t in STARTS]
    assert_disjoint(plan,previous)
    args.output.mkdir(parents=True,exist_ok=True)
    detector=args.output/'detector'; detector.mkdir()
    flags=args.output/'flags'; flags.mkdir()
    context={'extra4':'Pure extracellular reference; prior stimulation history not asserted.',
             'extra5':'Pure extracellular, acquired after current-injection experiments.',
             'extra6':'Pure extracellular, acquired after current-injection experiments.'}
    protocol={'date':'2026-11-19','frozen_rules':RULES,'baseline_multiplier':3,'broadband_multiplier':6,
              'same_sign_fraction':.5,'minimum_eligible_channels':1024,'guard_ms':[10,20],
              'flat_guard_ms':50,'flat_min_samples':10,'spike_threshold_multiplier':5,'spike_spacing_ms':5,
              'nominal_fs_hz':10000,'physical_fs_hz':10080,'starts_s':STARTS,'duration_s':DURATION,
              'planned_intervals':[{'source':s,'sample_start':a,'sample_stop':b} for s,a,b in plan],
              'experimental_context':context,'python':sys.executable,
              'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                               [Path(__file__),Path('analysis/compare_detectors.py'),Path('analysis/shared_artifacts.py'),Path('analysis/pilot.py')]},
              'evaluation':'Rules and times fixed before reading these intervals. Compare event annotations, usable time, and 20-ms-only candidate waveforms. No tuning on these intervals.',
              'limits':['Same recordings, new intervals; not independent biological replication or labeled accuracy validation.',
                        'All events preserved. Thresholds are not refitted after shared flagging.',
                        'Additional helper variants are saved for reproducibility but are not selected or evaluated for conclusions.',
                        'Shared activity is not necessarily artifact; true spikes during flagged time can be lost.',
                        'No full-recording processing, unit sorting, spatial deduplication or stimulation-artifact removal.']}
    (args.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    summaries={}; flag_summaries={}
    for rec in [4,5,6]:
        for start in STARTS:
            name=f'extra{rec}_{start}_{start+DURATION}'
            summaries[name]=run_segment(args.directory/f'extra_{rec}_signals.h5',start,DURATION,detector/name)
            flag_summaries[name]=evaluate_segment(name,summaries[name],detector,flags)
            chosen={k:flag_summaries[name]['variants'][k] for k in RULES}
            print('FROZEN',name,{k:(v['flagged_duration_s'],v['methods']['hp300_mad']['flagged']) for k,v in chosen.items()},flush=True)
            (args.output/'progress.json').write_text(json.dumps({'completed':list(summaries),'planned':6},indent=2)+'\n')
    (detector/'summary.json').write_text(json.dumps(summaries,indent=2,allow_nan=False)+'\n')
    (flags/'summary.json').write_text(json.dumps(flag_summaries,indent=2,allow_nan=False)+'\n')
    print('Completed frozen-guard evaluation:',args.output.resolve(),flush=True)


if __name__=='__main__': main()
