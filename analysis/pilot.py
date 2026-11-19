"""Read-only extracellular pilot; writes local diagnostics, never source recordings.

Run with an environment containing numpy, scipy, h5py and matplotlib.
All time calculations intentionally use nominal 10 kHz (physical rate 10,080 Hz).
"""
from __future__ import annotations
import argparse
import csv
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/invivo-matplotlib')
import h5py
import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, find_peaks, sosfiltfilt

FS = 10_000
MA = 200
GUARD = 500  # Conservative 50 ms exclusion around flat runs; exploratory.
METHODS = ['legacy_rms_floor', 'context_rms', 'context_rms_floor',
           'context_mad_masked', 'highpass_mad_masked']


def moving_average(x, size=MA):
    # origin=0 matches the legacy left=100/right=99 padding for even size 200.
    return uniform_filter1d(np.asarray(x, dtype=np.float64), size, axis=-1,
                            mode='nearest', origin=0)


def flat_mask(x, min_run=10):
    """Exact repeated-value runs >=1 ms; diagnostic, not proof of ADC saturation.

    Operates on the original stored values before filtering. Float16 quantization,
    disconnected channels, or missing data can also produce these intervals.
    """
    x = np.asarray(x)
    edges = np.r_[0, np.flatnonzero(x[1:] != x[:-1]) + 1, len(x)]
    mask = np.zeros(len(x), dtype=bool)
    for a, b in zip(edges[:-1], edges[1:]):
        if b - a >= min_run:
            mask[a:b] = True
    return mask


def dilate(mask, radius):
    edges = np.diff(np.r_[False, mask, False].astype(np.int8))
    delta = np.zeros(len(mask) + 1, dtype=np.int32)
    a = np.maximum(0, np.flatnonzero(edges == 1) - radius)
    b = np.minimum(len(mask), np.flatnonzero(edges == -1) + radius)
    np.add.at(delta, a, 1)
    np.add.at(delta, b, -1)
    return np.cumsum(delta[:-1]) > 0


def spaced_peaks(indices, amplitudes, distance):
    """Amplitude-priority suppression over a complete pilot interval.

    Sparse occupancy avoids independent-window refractory resets. Ties resolve
    toward the earlier sample. This is peak spacing, not a claim of single units.
    """
    indices = np.asarray(indices, dtype=np.int64)
    if not len(indices):
        return np.empty(0, dtype=int)
    occupied = np.zeros(int(indices.max()) + distance + 1, dtype=bool)
    keep = []
    for j in np.lexsort((indices, -np.asarray(amplitudes))):
        p = indices[j]
        if not occupied[p]:
            keep.append(j)
            occupied[max(0, p-distance+1):p+distance] = True
    return np.asarray(sorted(keep, key=lambda j: indices[j]), dtype=int)


def noise_scales(y, invalid, n):
    rms, mad, usable = [], [], []
    for a in range(0, n, FS):
        b = min(n, a+FS)
        seg = y[a:b]
        rms.append(float(np.sqrt(np.mean(seg**2))))
        good = seg[~invalid[a:b]]
        # Require at least half a window and >=25 ms for a stable pilot estimate.
        enough = len(good) >= max(250, (b-a)//2)
        value = np.median(np.abs(good-np.median(good)))/0.67448975 if enough else np.nan
        mad.append(float(value) if value > 0 else np.nan)
        usable.append(len(good)/(b-a))
    return np.array(rms), np.array(mad), np.array(usable)


def candidate_peaks(y, sigma, invalid=None, windowed=False):
    n = len(y)
    if windowed:
        # Match the legacy driver's omission of a partial final second.
        groups = [find_peaks(-y[a:a+FS], distance=50)[0]+a
                  for a in range(0, n-FS+1, FS)]
        peaks = np.concatenate(groups) if groups else np.empty(0, dtype=int)
    else:
        peaks = find_peaks(-y)[0]
    amp = -y[peaks]
    sig = sigma[peaks//FS]
    keep = np.isfinite(sig) & (sig > 0) & (amp >= 5*sig)
    if invalid is not None:
        keep &= ~invalid[peaks]
    return peaks[keep], amp[keep]


def write_csv(p, names, rows):
    with open(p, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(names)
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, default=Path('/Volumes/YZ/recording/invivo/26-11-06/0192/extra_4_signals.h5'))
    ap.add_argument('--start', type=float, default=60)
    ap.add_argument('--duration', type=float, default=5)
    ap.add_argument('--output', type=Path, default=Path('results/extra4_pilot_60_65'))
    args = ap.parse_args()
    if args.start < 0 or args.duration < .1:
        ap.error('start must be nonnegative and duration >=0.1 seconds')
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        ap.error('output must be empty to prevent overwriting a prior run')
    start = round(args.start*FS)
    n = round(args.duration*FS)
    context = 2500
    sos = butter(3, 300, btype='highpass', fs=FS, output='sos')
    t0 = time.perf_counter()
    with h5py.File(args.source, 'r') as f:
        ds = f['signals']
        if ds.ndim != 2 or ds.shape[0] != 2048 or ds.dtype.kind != 'f':
            raise ValueError('This pilot expects converted float data, shape (2048, samples)')
        if start+n > ds.shape[1]:
            raise ValueError('Pilot interval exceeds recording')
        lo, hi = max(0, start-context), min(ds.shape[1], start+n+context)
        core = slice(start-lo, start-lo+n)
        metadata = {'source': str(args.source.resolve()), 'dataset': 'signals',
                    'shape': list(ds.shape), 'dtype': str(ds.dtype), 'chunks': list(ds.chunks) if ds.chunks else None,
                    'file_attributes': {k: str(v) for k,v in f.attrs.items()},
                    'dataset_attributes': {k: str(v) for k,v in ds.attrs.items()},
                    'nominal_fs_hz': FS, 'physical_fs_hz': 10080,
                    'start_sample': start, 'stop_sample': start+n,
                    'nominal_start_s': start/FS, 'nominal_duration_s': n/FS,
                    'context_samples': context, 'channels': 2048,
                    'units': 'stored float units; conversion accepted, physical unit not inferred',
                    'flat_min_samples': 10, 'flat_guard_samples': GUARD,
                    'threshold_multiplier': 5, 'ma_samples': MA,
                    'highpass': 'experimental third-order Butterworth 300 Hz, forward/backward',
                    'python': sys.executable}
        windows = (n+FS-1)//FS
        sigmas = {m: np.full((2048, windows), np.nan) for m in METHODS}
        candidates = {m: [] for m in METHODS}
        flat_fraction = np.zeros(2048)
        guarded_fraction = np.zeros(2048)
        ranges = np.zeros((2048, 2))
        baseline_span = np.zeros(2048)
        usable_fraction = np.zeros((2048, windows))
        for batch in range(0, 2048, 64):
            data = ds[batch:batch+64, lo:hi].astype(np.float64)
            if not np.isfinite(data).all():
                raise ValueError(f'Non-finite source values in channels {batch}:{batch+64}; investigate before detection')
            for i, raw in enumerate(data):
                ch = batch+i
                flat = flat_mask(raw)
                invalid = dilate(flat, GUARD)[core]
                x = raw[core]
                base = moving_average(raw)[core]
                y = x-base
                hp = sosfiltfilt(sos, raw)[core]
                legacy = np.empty(n)
                for a in range(0, n, FS):
                    legacy[a:a+FS] = x[a:a+FS]-moving_average(x[a:a+FS])
                flat_fraction[ch] = flat[core].mean()
                guarded_fraction[ch] = invalid.mean()
                ranges[ch] = [x.min(), x.max()]
                baseline_span[ch] = np.ptp(base)
                rms, mad, good = noise_scales(y, invalid, n)
                usable_fraction[ch] = good
                legacy_rms, _, _ = noise_scales(legacy, np.zeros(n, dtype=bool), n)
                _, hp_mad, _ = noise_scales(hp, invalid, n)
                for method, residual, scale in [
                    ('legacy_rms_floor', legacy, legacy_rms),
                    ('context_rms', y, rms), ('context_rms_floor', y, rms),
                    ('context_mad_masked', y, mad), ('highpass_mad_masked', hp, hp_mad)]:
                    sigmas[method][ch] = scale
                    candidates[method].append(candidate_peaks(
                        residual, scale, invalid if 'masked' in method else None,
                        windowed=method.startswith('legacy')))
            print(f'Processed channels {batch}–{batch+63}', flush=True)

        events = {}
        method_summaries = {}
        floors = {}
        for method in METHODS + ['context_mad_masked_1ms']:
            parent = method.removesuffix('_1ms')
            scale = sigmas[parent]
            floor = np.zeros(windows) if method == 'context_rms' else np.array([
                np.median(col[np.isfinite(col)])
                if np.any(np.isfinite(col)) else np.nan for col in scale.T])
            floors[method] = floor.tolist()
            all_events = []
            channel_counts = np.zeros(2048, dtype=int)
            invalid_events = 0
            near_boundary = 0
            for ch, (peaks, amp) in enumerate(candidates[parent]):
                keep = amp >= 5*floor[peaks//FS]
                peaks, amp = peaks[keep], amp[keep]
                if not method.startswith('legacy'):
                    keep = spaced_peaks(peaks, amp, 10 if method.endswith('_1ms') else 50)
                    peaks, amp = peaks[keep], amp[keep]
                # Re-read only the raw channel for masks later in a batched loop.
                channel_counts[ch] = len(peaks)
                near_boundary += int(np.sum((peaks % FS < 100) | (peaks % FS >= FS-100)))
                all_events.extend((ch, int(p+start), float(a),
                                   float(5*max(scale[ch,p//FS], floor[p//FS])))
                                  for p,a in zip(peaks, amp))
            events[method] = np.asarray(all_events, dtype=float).reshape(-1,4)
            method_summaries[method] = {'event_count': len(all_events),
                'channels_with_events': int(np.count_nonzero(channel_counts)),
                'count_per_channel': channel_counts.tolist(),
                'within_10ms_of_1s_window_edges': near_boundary,
                'channel_windows_without_noise_estimate': int(np.sum(~np.isfinite(scale))),
                'events_in_suspect_flat_guard': 0}

        # One small read per batch measures where unmasked methods place events.
        for batch in range(0, 2048, 64):
            raw_batch = ds[batch:batch+64, lo:hi]
            for i, raw in enumerate(raw_batch):
                ch = batch+i
                invalid = dilate(flat_mask(raw), GUARD)[core]
                for method, arr in events.items():
                    pos = arr[arr[:,0] == ch,1].astype(int)-start
                    method_summaries[method]['events_in_suspect_flat_guard'] += int(invalid[pos].sum())

        # Explicitly biased selections for diagnostic review, not accuracy estimates.
        selected = []
        for ch in [np.argmax(flat_fraction), np.argmax(baseline_span),
                   np.argmax(method_summaries['context_mad_masked']['count_per_channel']),
                   np.argsort(sigmas['context_rms'].mean(axis=1))[1024]]:
            if int(ch) not in selected:
                selected.append(int(ch))
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(len(selected), 3, figsize=(17, 3.2*len(selected)), squeeze=False)
        times = (start+np.arange(n))/FS
        examples = {}
        for row, ch in enumerate(selected):
            raw = ds[ch,lo:hi].astype(float)
            x = raw[core]
            base = moving_average(raw)[core]
            y = x-base
            hp = sosfiltfilt(sos, raw)[core]
            bad = dilate(flat_mask(raw),GUARD)[core]
            examples[f'ch{ch}_raw'] = x.astype(np.float32)
            examples[f'ch{ch}_ma_residual'] = y.astype(np.float32)
            examples[f'ch{ch}_hp_residual'] = hp.astype(np.float32)
            examples[f'ch{ch}_excluded'] = bad
            ax = axes[row,0]
            ax.plot(times,x,lw=.35,color='#62758a',label='Stored signal')
            ax.plot(times,base,lw=.8,color='#d77e16',label='200-sample baseline')
            ax.set_title(f'Channel {ch}: raw + baseline; flat {flat_fraction[ch]:.1%}')
            ax.legend(fontsize=7,loc='upper right')
            for col, residual, method, title in [(1,y,'context_mad_masked','Moving-average residual'),
                                                (2,hp,'highpass_mad_masked','Experimental 300 Hz high-pass')]:
                ax = axes[row,col]
                ax.plot(times,residual,lw=.35,color='#325c81')
                ev = events[method]
                p = ev[ev[:,0]==ch,1].astype(int)-start
                ax.scatter(times[p],residual[p],s=8,color='#bf3030',label='Candidate peak')
                ax.fill_between(times,0,1,where=bad,transform=ax.get_xaxis_transform(),
                                color='#edbf49',alpha=.3,label='Flat-run guard')
                ax.set_title(f'{title}: {len(p)} candidates')
                ax.legend(fontsize=7,loc='upper right')
            for ax in axes[row]:
                ax.set_xlabel('Nominal recording time (s, 10 kHz)')
                ax.set_ylabel('Stored float units')
                ax.grid(alpha=.15)
        fig.suptitle('Extracellular pilot — diagnostic selections, not validated eAPs',fontsize=14)
        fig.tight_layout(rect=(0,0,1,.97))
        fig.savefig(out/'diagnostics.png',dpi=150)
        plt.close(fig)
        np.savez_compressed(out/'review_traces.npz', sample_start=start, fs=FS, **examples)
        for method, arr in events.items():
            write_csv(out/f'events_{method}.csv', ['channel_id','sample_index','negative_peak_amplitude_stored_units','threshold_stored_units'],
                      ((int(ch),int(p),amp,thr) for ch,p,amp,thr in arr))
        write_csv(out/'channel_diagnostics.csv', ['channel_id','flat_fraction','guarded_fraction','minimum','maximum','baseline_span']+list(events),
                  ((ch,flat_fraction[ch],guarded_fraction[ch],*ranges[ch],baseline_span[ch],
                    *(method_summaries[m]['count_per_channel'][ch] for m in events)) for ch in range(2048)))
        metadata.update({'selected_channels': selected, 'selection_rule': 'maximum flat fraction, maximum baseline span, most MA/MAD candidates, median RMS',
                         'flat_channel_count': int(np.count_nonzero(flat_fraction)),
                         'flat_sample_fraction': float(flat_fraction.mean()),
                         'guarded_sample_fraction': float(guarded_fraction.mean()),
                         'channels_over_50pct_guarded': int(np.sum(guarded_fraction>.5)),
                         'median_noise_floors': floors,
                         'methods': {m:{k:v for k,v in s.items() if k!='count_per_channel'} for m,s in method_summaries.items()},
                         'elapsed_seconds': time.perf_counter()-t0,
                         'limitations': ['No ground truth or accuracy estimate; all events are candidates.',
                                         'Exact flat runs are not calibrated rail detection; float16 quantization can mimic flatness.',
                                         'Masking deliberately loses visibility near suspected clipping; no spike reconstruction.',
                                         '300 Hz cutoff, 1 ms flat length and 50 ms guard are exploratory parameters.',
                                         'Noise floor is pooled across channels, not spatially calibrated.',
                                         'No stimulation analysis; no spike sorting or across-channel deduplication.']})
        with open(out/'summary.json','w') as f:
            json.dump(metadata,f,indent=2,allow_nan=False)
        print(json.dumps({m:v for m,v in metadata['methods'].items()},indent=2),flush=True)
        print(f'Results: {out.resolve()}',flush=True)


if __name__ == '__main__':
    main()
