from enum import Enum
from multiprocessing import Event, Value
import time
import numpy as np
from scipy.signal import find_peaks
import matplotlib.pyplot as plt


# =============================================================================
# Alternative method
# =============================================================================
def robust_sigma_mad(x: np.ndarray) -> float:
    """
    Robust noise sigma estimate using MAD.
    sigma ~= MAD / 0.6745 for Gaussian noise.
    """
    x = np.asarray(x)
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    return mad / 0.6745 if mad > 0 else np.std(x)


def calculate_rms(x: np.ndarray, keepdims: bool = False) -> float:

    x = np.asarray(x, dtype=np.float64)

    if x.ndim == 1:

        return np.sqrt(np.mean(np.square(x)))

    elif x.ndim == 2:

        return np.sqrt(np.mean(np.square(x), axis=1, keepdims=keepdims))

    else:

        raise ValueError("signal must be 1D or 2D (n_ch, n_samples)")


def detect_spikes(
    signal              : np.ndarray,
    fs                  : float,
    chunk_size          : int | None = None,     # ← optional
    polarity            : str = "neg",
    thr_k               : float = 5.0,
    refractory_ms       : float = 5.0,
    center              : bool = False,
    apply_median_noise  : bool = False,
):
    """
    Spike detection using scipy.signal.find_peaks.

    Accepts:
      - 1D: (n_samples,)
      - 2D: (n_ch, n_samples)

    Returns:
      1D input:
        spikes: (n_samples,) uint8
      2D input:
        spikes: (n_ch, n_samples) uint8
    """

    x = np.asarray(signal).astype(np.float64, copy=False)

    min_dist = max(1, int(round(refractory_ms * 1e-3 * fs)))

    # --------- 1D CASE ---------
    if x.ndim == 1:

        if center:
            x = x - np.median(x)

        n_samp = x.size
        spikes = np.zeros(n_samp, dtype=np.uint8)

        # If no chunking → process entire signal
        if chunk_size is None:
            chunk_starts = [0]
            chunk_ends = [n_samp]
        else:
            chunk_starts = range(0, n_samp, chunk_size)
            chunk_ends = [min(n_samp, s + chunk_size) for s in chunk_starts]

        for start, end in zip(chunk_starts, chunk_ends):
            chunk = x[start:end]

            # threshold calculation - either MAD or RMS
            # sigma = robust_sigma_mad(chunk)
            sigma = calculate_rms(chunk)
            thr = thr_k * sigma

            if polarity == "neg":
                peaks, _ = find_peaks(-chunk, height=thr, distance=min_dist)
            elif polarity == "pos":
                peaks, _ = find_peaks(chunk, height=thr, distance=min_dist)
            else:
                raise ValueError("polarity must be 'neg' or 'pos'")

            if peaks.size:
                spikes[start + peaks] = 1

        return spikes

    # --------- 2D CASE ---------
    elif x.ndim == 2:

        n_ch, n_samp = x.shape
        spikes = np.zeros((n_ch, n_samp), dtype=np.uint8)

        if center:
            x = x - np.median(x, axis=1, keepdims=True)

        if chunk_size is None:
            chunk_starts = [0]
            chunk_ends = [n_samp]
        else:
            chunk_starts = range(0, n_samp, chunk_size)
            chunk_ends = [min(n_samp, s + chunk_size) for s in chunk_starts]

        for start, end in zip(chunk_starts, chunk_ends):

            chunk = x[:, start:end]

            # threshold calculation - either MAD or RMS
            # mad = robust_sigma_mad(chunk)
            sigmas = calculate_rms(chunk)

            if apply_median_noise:
                med_sigma = np.median(sigmas)
                sigmas = np.maximum(sigmas, med_sigma)

            thrs = thr_k * sigmas

            for ch in range(n_ch):

                s = chunk[ch]

                if polarity == "neg":
                    peaks, _ = find_peaks(-s, height=thrs[ch], distance=min_dist)
                elif polarity == "pos":
                    peaks, _ = find_peaks(s, height=thrs[ch], distance=min_dist)
                else:
                    raise ValueError("polarity must be 'neg' or 'pos'")

                if peaks.size:
                    spikes[ch, start + peaks] = 1

        return spikes

    else:
        raise ValueError("signal must be 1D or 2D (n_ch, n_samples)")


def detect_spikes_chunked(
    signal: np.ndarray,
    fs: float,
    chunk_size: int,
    polarity: str = "neg",              # "neg" (typical extracellular) or "pos"
    thr_k: float = 5.0,                 # threshold multiplier in units of robust sigma
    refractory_ms: float = 1.0,         # min distance between spikes
    center: bool = True,
    apply_median_noise: bool = False,   # only used when signal is 2D
):
    """
    Spike detection using scipy.signal.find_peaks, run chunk-by-chunk.

    Accepts:
      - 1D: (n_samples,)
      - 2D: (n_ch, n_samples)

    Returns:
      If input is 1D:
        spikes: (n_samples,) uint8  (0/1)
      If input is 2D:
        spikes: (n_ch, n_samples) uint8  (0/1)
    """
    x = np.asarray(signal)

    if x.ndim == 1:
        x = x.astype(np.float64, copy=False)
        n_samp = x.size

        # output raster
        spikes = np.zeros(n_samp, dtype=np.uint8)

        if center:
            x = x - np.median(x)

        min_dist = max(1, int(round(refractory_ms * 1e-3 * fs)))

        for start in range(0, n_samp, chunk_size):
            end = min(n_samp, start + chunk_size)
            chunk = x[start:end]

            sigma = robust_sigma_mad(chunk)
            thr = thr_k * sigma

            if polarity == "neg":
                peaks, _ = find_peaks(-chunk, height=thr, distance=min_dist)
            elif polarity == "pos":
                peaks, _ = find_peaks(chunk, height=thr, distance=min_dist)
            else:
                raise ValueError("polarity must be 'neg' or 'pos'")

            if peaks.size:
                spikes[start + peaks] = 1

        return spikes

    elif x.ndim == 2:
        x = x.astype(np.float64, copy=False)
        n_ch, n_samp = x.shape

        # output raster
        spikes = np.zeros((n_ch, n_samp), dtype=np.uint8)

        if center:
            x = x - np.median(x, axis=1, keepdims=True)

        min_dist = max(1, int(round(refractory_ms * 1e-3 * fs)))

        for start in range(0, n_samp, chunk_size):
            end = min(n_samp, start + chunk_size)
            chunk = x[:, start:end]  # (n_ch, chunk_len)

            # per-channel robust sigma for this chunk
            sigmas = np.array([robust_sigma_mad(chunk[ch]) for ch in range(n_ch)],
                              dtype=np.float64)

            if apply_median_noise:
                med_sigma = np.median(sigmas)
                sigmas = np.maximum(sigmas, med_sigma)

            thrs = thr_k * sigmas  # (n_ch,)

            for ch in range(n_ch):
                s = chunk[ch]

                if polarity == "neg":
                    peaks, _ = find_peaks(-s, height=thrs[ch], distance=min_dist)
                elif polarity == "pos":
                    peaks, _ = find_peaks(s, height=thrs[ch], distance=min_dist)
                else:
                    raise ValueError("polarity must be 'neg' or 'pos'")

                if peaks.size:
                    spikes[ch, start + peaks] = 1

        return spikes

    else:
        raise ValueError("signal must be 1D (n_samples,) or 2D (n_ch, n_samples)")


def detect_spikes_timing_chunked(
    signal: np.ndarray,
    fs: float,
    chunk_size: int,
    polarity: str = "neg",              # "neg" (typical extracellular) or "pos"
    thr_k: float = 5.0,                 # threshold multiplier in units of robust sigma
    refractory_ms: float = 1.0,         # min distance between spikes
    center: bool = True,
    apply_median_noise: bool = False,   # only used when signal is 2D
    skip_channels: list = None          # in multichannel mode, channels to skip
):
    """
    Spike detection using scipy.signal.find_peaks, run chunk-by-chunk.

    Accepts:
      - 1D: (n_samples,)
      - 2D: (n_ch, n_samples)

    Returns:
      If input is 1D:
        spike_idx: (n_spikes,) int64

      If input is 2D:
        spike_idx_list: list of length n_ch, each is (n_spikes_ch,) int64
    """
    x = np.asarray(signal)

    if x.ndim == 1:
        x = x.astype(np.float64, copy=False)
        if center:
            x = x - np.median(x)

        min_dist = max(1, int(round(refractory_ms * 1e-3 * fs)))
        all_idx = []
        n = x.size

        for start in range(0, n, chunk_size):
            end = min(n, start + chunk_size)
            chunk = x[start:end]

            sigma = robust_sigma_mad(chunk)
            thr = thr_k * sigma

            if polarity == "neg":
                peaks, _ = find_peaks(-chunk, height=thr, distance=min_dist)
            elif polarity == "pos":
                peaks, _ = find_peaks(chunk, height=thr, distance=min_dist)
            else:
                raise ValueError("polarity must be 'neg' or 'pos'")

            if peaks.size:
                all_idx.append(start + peaks)

        if all_idx:
            spike_idx = np.concatenate(all_idx).astype(np.int64, copy=False)
        else:
            spike_idx = np.array([], dtype=np.int64)

        return spike_idx

    elif x.ndim == 2:
        x = x.astype(np.float64, copy=False)
        n_ch, n_samp = x.shape

        if center:
            # per-channel centering
            x = x - np.median(x, axis=1, keepdims=True)

        min_dist = max(1, int(round(refractory_ms * 1e-3 * fs)))

        all_idx = [[] for _ in range(n_ch)]

        for start in range(0, n_samp, chunk_size):
            end = min(n_samp, start + chunk_size)
            chunk = x[:, start:end]  # (n_ch, chunk_len)

            # per-channel robust sigma for this chunk
            sigmas = np.array([robust_sigma_mad(chunk[ch]) for ch in range(n_ch)],
                              dtype=np.float64)

            if apply_median_noise:
                med_sigma = np.median(sigmas)
                # raise very-low-noise channels to median
                sigmas = np.maximum(sigmas, med_sigma)

            thrs = thr_k * sigmas

            for ch in range(n_ch):
                skipping = False
                if skip_channels is not None:
                    if ch in skip_channels:
                        skipping = True

                if not skipping:
                    s = chunk[ch]

                    if polarity == "neg":
                        peaks, _ = find_peaks(-s, height=thrs[ch], distance=min_dist)
                    elif polarity == "pos":
                        peaks, _ = find_peaks(s, height=thrs[ch], distance=min_dist)
                    else:
                        raise ValueError("polarity must be 'neg' or 'pos'")

                    if peaks.size:
                        all_idx[ch].append(start + peaks)

        spike_idx_list = []
        for ch in range(n_ch):
            if all_idx[ch]:
                idx = np.concatenate(all_idx[ch]).astype(np.int64, copy=False)
            else:
                idx = np.array([], dtype=np.int64)
            spike_idx_list.append(idx)

        return spike_idx_list

    else:
        raise ValueError("signal must be 1D (n_samples,) or 2D (n_ch, n_samples)")


def get_n_highest_indices(arr, n):
    """
    Returns the indices of the N highest values in a 1D numpy array.
    """
    # np.argsort returns indices that would sort the array in ascending order.
    # We take the last 'n' elements and reverse them to get descending order.
    indices = np.argsort(arr)[-n:][::-1]

    return indices


def filter_spikes_by_amplitude(
    signal: np.ndarray,
    spike_mask: np.ndarray,
    amp_threshold: float,
    *,
    use_absolute: bool = True,
) -> np.ndarray:
    """
    Remove spikes whose amplitude is smaller than threshold.

    Args:
        signal: float signal, shape (n_samp,) or (n_ch, n_samp)
        spike_mask: uint8/bool spike detections, same shape
        amp_threshold: minimum amplitude required
        use_absolute: if True, compare |signal| vs threshold

    Returns:
        filtered_spikes: uint8 array, same shape as input
    """
    x = np.asarray(signal)
    s = np.asarray(spike_mask)

    if x.shape != s.shape:
        raise ValueError("signal and spike_mask must have the same shape")

    # amplitude at detected positions
    if use_absolute:
        keep = np.abs(x) >= amp_threshold
    else:
        keep = x >= amp_threshold

    # only keep spikes where both:
    #   1) originally detected
    #   2) amplitude large enough
    filtered = (s.astype(bool) & keep)

    return filtered.astype(np.uint8)


def compress_spikes_bin(spikes: np.ndarray, N: int) -> np.ndarray:
    """
    Compress a binary spike raster by factor N along the time axis.

    Input:
      spikes: (n_ch, n_samples) uint8 with values {0,1}
      N: compression ratio (number of samples per output bin)

    Output:
      out: (n_ch, n_samples//N) uint8 with values {0,1}
           out[ch, t] = 1 if any spike occurred within that N-sample bin else 0
    """
    x = np.asarray(spikes)
    if x.ndim != 2:
        raise ValueError("spikes must be 2D (n_ch, n_samples)")
    if x.dtype != np.uint8:
        raise ValueError("spikes must be dtype np.uint8")
    if N <= 0:
        raise ValueError("N must be >= 1")

    n_ch, n_samp = x.shape
    n_out = n_samp // N
    if n_out == 0:
        return np.zeros((n_ch, 0), dtype=np.uint8)

    # Drop the remainder (loss is acceptable per your note)
    x_trim = x[:, :n_out * N]

    # Reshape into bins and OR (any spike in bin -> 1)
    out = (x_trim.reshape(n_ch, n_out, N).any(axis=2)).astype(np.uint8)

    return out


def compute_derivative(signal: np.ndarray, fs: float, method: str = "gradient") -> np.ndarray:
    """
    Compute time-derivative of a 1D or 2D signal.

    Args:
        signal: shape (n_samp,) or (n_ch, n_samp)
        fs: sampling frequency in Hz
        method: "gradient" (recommended) or "diff"

    Returns:
        dsignal_dt with same shape as input.
    """
    x = np.asarray(signal, dtype=np.float64)

    if x.ndim not in (1, 2):
        raise ValueError("signal must be 1D or 2D")

    dt = 1.0 / float(fs)

    if method == "gradient":
        # preserves shape (central differences inside, 1st order at edges)
        return np.gradient(x, dt, axis=-1)
    elif method == "diff":
        # simple forward difference; pad to preserve shape
        dx = np.diff(x, axis=-1) / dt
        pad = [(0, 0)] * x.ndim
        pad[-1] = (1, 0)  # pad one sample at the beginning
        return np.pad(dx, pad_width=pad, mode="edge")
    else:
        raise ValueError("method must be 'gradient' or 'diff'")


def is_local_peak(signal, i, w=3, polarity="neg"):
    lo = max(0, i - w)
    hi = min(len(signal), i + w + 1)

    if polarity == "neg":
        return signal[i] == np.min(signal[lo:hi])
    else:
        return signal[i] == np.max(signal[lo:hi])

