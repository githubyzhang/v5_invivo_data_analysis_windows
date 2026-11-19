import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans


# Linear interpolation for more accurate crossing times
def interp_crossing(i1, i2, y_target, t, mu):
    x1, x2 = t[i1], t[i2]
    y1, y2 = mu[i1], mu[i2]
    if y2 == y1:
        return x1
    return x1 + (y_target - y1) * (x2 - x1) / (y2 - y1)


def find_peak_fwhm_from_mean_waveform(mu, t, half_window):
    n_samp = half_window * 2

    # Find dominant peak by absolute value
    peak_idx = half_window  # np.argmax(np.abs(mu))
    peak_amp = mu[peak_idx]
    peak_time = t[peak_idx]

    # Half-maximum relative to baseline=0
    half_amp = peak_amp / 2.0

    # Find left crossing
    left_idx = peak_idx
    while left_idx > 0:
        if (peak_amp >= 0 and mu[left_idx] < half_amp) or (peak_amp < 0 and mu[left_idx] > half_amp):
            break
        left_idx -= 1

    # Find right crossing
    right_idx = peak_idx
    while right_idx < n_samp - 1:
        if (peak_amp >= 0 and mu[right_idx] < half_amp) or (peak_amp < 0 and mu[right_idx] > half_amp):
            break
        right_idx += 1

    # Left crossing time
    if left_idx < peak_idx:
        t_left = interp_crossing(left_idx, left_idx + 1, half_amp, t, mu)
    else:
        t_left = t[peak_idx]

    # Right crossing time
    if right_idx > peak_idx:
        t_right = interp_crossing(right_idx - 1, right_idx, half_amp, t, mu)
    else:
        t_right = t[peak_idx]

    fwhm = t_right - t_left

    return peak_amp, peak_time, half_amp, fwhm, t_left, t_right


def plot_waveform_overlay(waveforms, fs, half_window, n=200):
    n_spikes, n_samp = waveforms.shape
    t = (np.arange(n_samp) - half_window) / fs

    idx = np.random.choice(n_spikes, size=min(n, n_spikes), replace=False)
    W = waveforms[idx]

    mu = waveforms.mean(axis=0)
    sd = waveforms.std(axis=0)

    plt.figure(figsize=(7,4))
    plt.plot(t, W.T, linewidth=0.5, alpha=0.15)
    plt.plot(t, mu, linewidth=2)
    plt.fill_between(t, mu - sd, mu + sd, alpha=0.2)
    plt.title(f"Waveforms overlay (n={len(idx)}) + mean ± std")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.show()


def plot_waveform_heatmap(waveforms, spike_amplitude):
    order = np.argsort(spike_amplitude)
    W = waveforms[order]

    plt.figure(figsize=(7, 5))
    plt.imshow(W, aspect="auto", interpolation="nearest")
    plt.title("Waveform heatmap (rows=spikes, sorted by amplitude)")
    plt.xlabel("Sample")
    plt.ylabel("Spike (sorted)")
    plt.show()


def plot_amplitude_and_examples(waveforms, amps, fs, half_window):
    n_samp = waveforms.shape[1]
    t = (np.arange(n_samp) - half_window) / fs

    plt.figure(figsize=(7,3))
    plt.hist(amps, bins=60)
    plt.title("Spike amplitude distribution")
    plt.xlabel("Amplitude")
    plt.ylabel("Count")
    plt.show()

    qs = [0.1, 0.3, 0.5, 0.7, 0.9]
    fig, axs = plt.subplots(1, len(qs), figsize=(14,3), constrained_layout=True, sharey=True)
    for ax, q in zip(axs, qs):
        lo = np.quantile(amps, q) - 1e-12
        hi = np.quantile(amps, q) + 1e-12
        # pick nearest spike to that quantile
        i = np.argmin(np.abs(amps - np.quantile(amps, q)))
        ax.plot(t, waveforms[i], linewidth=1)
        ax.set_title(f"~Q{int(q*100)} amp")
        ax.set_xlabel("s")
    axs[0].set_ylabel("Amplitude")
    plt.show()


def cluster_spikes_quick(waveforms, n_clusters=3):
    """
    waveforms: (n_spikes, n_samples)
    """

    n_spikes, n_samp = waveforms.shape

    # ---------- PCA ----------
    pca = PCA(n_components=3)
    X = pca.fit_transform(waveforms)   # (n_spikes, 3)

    print("Explained variance ratio:", pca.explained_variance_ratio_)

    # ---------- KMeans ----------
    km = KMeans(n_clusters=n_clusters, n_init=20, random_state=0)
    labels = km.fit_predict(X)

    return labels, X


def plot_pca_clusters(X, labels, title=None):
    plt.figure(figsize=(6,5))
    for k in np.unique(labels):
        sel = labels == k
        plt.scatter(X[sel, 0], X[sel, 1], s=8, label=f"C{k}")
    plt.xlabel("PC1")
    plt.ylabel("PC2")
    if title is None:
        title = "Spike clusters in PCA space"
    plt.title(title)
    plt.legend()
    plt.show()


def plot_cluster_waveforms(waveforms, labels, fs, half_window):
    n_samp = waveforms.shape[1]
    t = (np.arange(n_samp) - half_window) / fs

    clusters = np.unique(labels)

    plt.figure(figsize=(8, 5))
    for k in clusters:
        W = waveforms[labels == k]
        mu = W.mean(axis=0)
        plt.plot(t, mu, linewidth=2, label=f"C{k} (n={len(W)})")

    plt.title("Mean waveform per cluster")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.legend()
    plt.show()


def plot_cluster_waveforms_horizontal(waveforms, labels, fs, half_window):
    """
    Plot average waveform for each cluster in horizontal subplots
    sharing the same y-axis.

    Args:
        waveforms : ndarray (n_waveforms, n_samples)
        labels    : ndarray (n_waveforms,)
        fs        : sampling frequency
        half_window : index offset for time alignment
    """

    n_samp = waveforms.shape[1]
    t = (np.arange(n_samp) - half_window) / fs

    clusters = np.unique(labels)
    n_clusters = len(clusters)

    fig, axes = plt.subplots(
        1,
        n_clusters,
        figsize=(3*n_clusters, 4),
        sharey=True
    )

    if n_clusters == 1:
        axes = [axes]

    for ax, k in zip(axes, clusters):
        W = waveforms[labels == k]
        mu = W.mean(axis=0)

        ax.plot(t, mu, linewidth=2)
        ax.set_title(f"C{k}\n(n={len(W)})")
        ax.set_xlabel("Time (s)")

    axes[0].set_ylabel("Amplitude")

    fig.suptitle("Mean waveform per cluster")
    plt.tight_layout()
    plt.show()


def plot_cluster_waveforms_horizontal_annotated(waveforms, labels, fs, half_window, title=None):
    """
    Plot average waveform for each cluster in horizontal subplots
    sharing the same y-axis, with peak amplitude and FWHM annotated.

    Args:
        waveforms   : ndarray, shape (n_waveforms, n_samples)
        labels      : ndarray, shape (n_waveforms,)
        fs          : sampling frequency in Hz
        half_window : index offset for time alignment
    """
    n_samp = waveforms.shape[1]
    t = (np.arange(n_samp) - half_window) / fs

    clusters = np.unique(labels)
    n_clusters = len(clusters)

    fig, axes = plt.subplots(
        1,
        n_clusters,
        figsize=(3.5 * n_clusters, 4),
        sharey=True
    )

    if n_clusters == 1:
        axes = [axes]

    for ax, k in zip(axes, clusters):
        W = waveforms[labels == k]
        mu = W.mean(axis=0)

        # Plot mean waveform
        ax.plot(t, mu, linewidth=2)

        peak_amp, peak_time, half_amp, fwhm, t_left, t_right = find_peak_fwhm_from_mean_waveform(mu, t, half_window)

        # Overlay annotations
        ax.plot(peak_time, peak_amp, 'o')
        ax.hlines(half_amp, t_left, t_right, linestyles='--')
        # ax.vlines([t_left, t_right], 0, half_amp, linestyles=':', alpha=0.7)

        # Text annotation
        ax.text(
            0.02, 0.95,
            f"Peak: {peak_amp*1e3:.2f}\nFWHM: {fwhm*1e3:.2f} ms",
            transform=ax.transAxes,
            va='top',
            ha='left',
            fontsize=9,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.7)
        )

        ax.set_title(f"C{k}\n(n={len(W)})")
        ax.set_xlabel("Time (s)")
        # ax.axvline(0, linestyle=':', alpha=0.5)
        ax.grid(alpha=0.2)

    axes[0].set_ylabel("Amplitude")
    if title is None:
       title = "Mean waveform per cluster"
    fig.suptitle(title)
    plt.tight_layout()
    plt.show()


def compute_cluster_waveform_features(waveforms, labels, fs, half_window):
    """
    Compute peak amplitude and FWHM of the mean waveform for each cluster.

    Args:
        waveforms   : ndarray (n_waveforms, n_samples)
        labels      : ndarray (n_waveforms,)
        fs          : sampling frequency (Hz)
        half_window : index offset for time alignment

    Returns:
        dict:
            {
              cluster_id: {
                    "peak_amp": float,
                    "peak_time": float,
                    "fwhm": float,
                    "n_waveforms": int
              },
              ...
            }
    """

    n_samp = waveforms.shape[1]
    t = (np.arange(n_samp) - half_window) / fs
    clusters = np.unique(labels)

    results = {}

    for k in clusters:
        W = waveforms[labels == k]
        mu = W.mean(axis=0)

        peak_amp, peak_time, half_amp, fwhm, t_left, t_right = find_peak_fwhm_from_mean_waveform(mu, t, half_window)

        # compute maximum tilt (difference between left-most 10 sample average vs right-most 10 sample average)
        size = mu.shape[0]
        max_tilt = np.abs(np.average(mu[:10]) - np.average(mu[size-10:]))

        results[int(k)] = {
            "peak_amp": float(peak_amp),
            "peak_time": float(peak_time),
            "fwhm": float(fwhm),
            "max_tilt": max_tilt,
            "n_waveforms": int(len(W))
        }

    return results


def filter_clusters_by_features(features, amplitude=None, fwhm=None, max_baseline_tilt=None):
    """
    Filters clusters based on peak amplitude and FWHM ranges.

    Args:
        features  : dict returned by compute_cluster_waveform_features()
        amplitude : tuple (min_amp, max_amp) or None
        fwhm      : tuple (min_fwhm, max_fwhm) or None

    Returns:
        list[int]: cluster IDs that pass the filters
    """

    passed_clusters = []
    remaining = 0
    cluster_num = len(features)

    for cid, f in features.items():
        amp = f["peak_amp"]
        width = f["fwhm"]
        max_tilt = f["max_tilt"]

        # cluster id filter
        if cid < 0:
            continue

        # amplitude filter
        if amplitude is not None:
            amin, amax = amplitude
            if not (amin <= amp <= amax):
                continue

        # fwhm filter
        if fwhm is not None:
            wmin, wmax = fwhm
            if not (wmin <= width <= wmax):
                continue

        # max tilt filter
        if max_baseline_tilt is not None:
            if not max_tilt <= max_baseline_tilt:
                continue

        remaining += 1
        passed_clusters.append(cid)

    print(f'PCA filter: {remaining} / {cluster_num} clusters passed filter: {passed_clusters}.')
    return passed_clusters


def group_spike_times_by_cluster(labels: np.ndarray, spike_index: np.ndarray):
    """
    Args:
        labels: (n_spikes,) cluster id for each spike
        spike_index: (n_spikes,) original spike sample index

    Returns:
        dict:
            key   -> cluster id
            value -> array of spike indices belonging to that cluster
    """
    labels = np.asarray(labels)
    spike_index = np.asarray(spike_index)

    if labels.shape[0] != spike_index.shape[0]:
        raise ValueError("labels and spike_index must have same length")

    clusters = {}
    for k in np.unique(labels):
        clusters[int(k)] = spike_index[labels == k]

    return clusters


def get_labeled_spike_index(label_list, labels: np.ndarray, spike_index: np.ndarray):
    """
    Get spike indices corresponding to selected cluster labels.

    Args:
        label_list : iterable of cluster IDs to keep
        labels     : (n_spikes,) cluster id for each spike
        spike_index: (n_spikes,) original spike sample index

    Returns:
        np.ndarray: spike indices for selected labels
    """

    labels = np.asarray(labels)
    spike_index = np.asarray(spike_index)

    if labels.shape != spike_index.shape:
        raise ValueError("labels and spike_index must have the same shape")

    mask = np.isin(labels, label_list)

    return spike_index[mask]


def plot_signal_with_clustered_spikes(
    signal: np.ndarray,
    fs: float,
    spikes_by_cluster: dict[int, np.ndarray],
    *,
    t0: float = 0.0,
    label: str | None = None,
    title: str = "Signal with clustered spikes",
    s: float = 18,
    alpha: float = 1,
    show_legend: bool = True,
):
    """
    Plot a 1D recording and overlay spike markers with different colors per cluster.

    Args:
        signal: (n_samp,) recording
        fs: sampling rate (Hz)
        spikes_by_cluster: dict {cluster_id: spike_indices}, e.g. output of group_spike_times_by_cluster
        t0: start time offset (s)
        label: label for the signal trace
        title: plot title
        s: scatter marker size
        alpha: scatter alpha
        show_legend: whether to show legend
    """
    x = np.asarray(signal)
    if x.ndim != 1:
        raise ValueError("signal must be 1D")

    t = t0 + np.arange(x.size) / float(fs)

    plt.figure(figsize=(12, 6))
    plt.plot(t, x, linewidth=1, label=label)

    # Use Matplotlib's default color cycle so clusters get distinct colors automatically
    for k in sorted(spikes_by_cluster.keys()):
        idx = np.asarray(spikes_by_cluster[k], dtype=np.int64)
        if idx.size == 0:
            continue

        # clip to valid range (in case indices include out-of-window spikes)
        idx = idx[(idx >= 0) & (idx < x.size)]
        if idx.size == 0:
            continue

        plt.scatter(t[idx], x[idx], s=s, alpha=alpha, label=f"C{k} (n={idx.size})", zorder=2)

    plt.title(title)
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    if show_legend:
        plt.legend()
    plt.show()