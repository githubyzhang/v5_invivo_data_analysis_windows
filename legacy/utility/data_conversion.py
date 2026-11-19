import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize


def compute_noise_floor(signal: np.ndarray, noise_factor: float = 2.0):
    """
    Computes noise floor window based on number of sigmas.

    Supports:
        1D: (n_samples,)
        2D: (n_ch, n_samples)

    Args:
        signal: ndarray
        noise_factor: number of sigmas (1.0 ≈ 68%, 2.0 ≈ 95% for Gaussian)

    Returns:
        1D input:
            low (float), high (float)

        2D input:
            low (n_ch,), high (n_ch,)
    """
    x = np.asarray(signal, dtype=np.float64)

    if x.ndim == 1:
        mu = np.mean(x)
        sigma = np.std(x, ddof=1)
        low = mu - noise_factor * sigma
        high = mu + noise_factor * sigma
        return low, high

    elif x.ndim == 2:
        # compute per-channel stats
        mu = np.mean(x, axis=1)
        sigma = np.std(x, axis=1, ddof=1)

        low = mu - noise_factor * sigma
        high = mu + noise_factor * sigma
        return low, high

    else:
        raise ValueError("signal must be 1D or 2D (n_ch, n_samples)")


def compute_moving_average(x: np.ndarray, N: int) -> np.ndarray:
    """
    Moving average with SAME output length.

    Supports:
        1D: (n_samples,)
        2D: (n_ch, n_samples)  -> applied per channel (axis=1)

    Edges handled by padding with edge values.
    """
    x = np.asarray(x, dtype=np.float64)

    if N <= 0:
        raise ValueError("N must be >= 1")
    if N == 1:
        return x.copy()

    kernel = np.ones(N, dtype=np.float64) / N
    pad_left = N // 2
    pad_right = N - 1 - pad_left

    if x.ndim == 1:
        x_pad = np.pad(x, (pad_left, pad_right), mode="edge")
        return np.convolve(x_pad, kernel, mode="valid")

    elif x.ndim == 2:
        # Pad along sample axis only
        x_pad = np.pad(x, ((0, 0), (pad_left, pad_right)), mode="edge")

        # Apply convolution per channel
        out = np.empty_like(x, dtype=np.float64)
        for ch in range(x.shape[0]):
            out[ch] = np.convolve(x_pad[ch], kernel, mode="valid")

        return out

    else:
        raise ValueError("x must be 1D or 2D (n_ch, n_samples)")


def convert_to_float16(raw_data_uint16,
                       multiplier,
                       gain,
                       remove_baseline: bool=False,
                       baseline_size: int=200):

    voltage = raw_data_uint16 * multiplier
    signals = voltage / gain
    if remove_baseline:
        baseline = compute_moving_average(signals, N=baseline_size)
        signals -= baseline

    return signals

