import numpy as np
from matplotlib.colors import Normalize
import matplotlib.pyplot as plt

import h5py
import numpy as np
import matplotlib.pyplot as plt


def plot_channels_spaced(
        signals: np.ndarray,
        channels: list,
        fs: float,
        t_start: float = None,
        t_stop: float = None,
        xlines: list = None,
        traces: dict = None,
        spacing: float = 0.001
):
    if t_start is not None:
        i_start = t_start * fs
        i_stop = t_stop * fs
        time = np.arange(i_start, i_stop) / fs
    else:
        time = np.arange(signals.shape[1]) * fs

    plt.figure(figsize=(12, 6))
    for idx, ch in enumerate(channels):
        if t_start is not None:
            signal = np.asarray(signals[ch, i_start:i_stop])
        else:
            signal = np.asarray(signals[ch])
        plt.plot(time, signal - idx * spacing, label=f'{ch}', alpha=1)

    if xlines is not None:
        for x in xlines:
            plt.axvline(
                x,
                linestyle="--",
                linewidth=1,
                alpha=0.7,
            )

    if isinstance(traces, dict):
        for label in traces.keys():
            plt.plot(time, traces[label], label=label)

    plt.xlabel("Time (s)")
    plt.ylabel("Voltage (V)")
    plt.legend(loc='lower right')
    plt.show()


def plot_channel_traces(
    signals,
    channels,
    fs,
    t_start=None,
    t_stop=None,
    xlines=None,
    figsize=None,
    sharex=True,
    alpha=1.0,
    linewidth=1.0,
    title=None,
):
    """
    Plot selected channels as stacked subplots.

    signals can be:
        - h5py dataset, e.g. file["signals"]
        - zarr array
        - numpy memmap
        - numpy ndarray

    Only the requested channel/time slices are loaded.
    """

    channels = list(channels)

    if xlines is None:
        xlines = []

    if len(signals.shape) != 2:
        raise ValueError(f"signals must be 2D, got shape {signals.shape}")

    n_samples = signals.shape[1]

    i_start = 0 if t_start is None else int(round(t_start * fs))
    i_stop = n_samples if t_stop is None else int(round(t_stop * fs))

    i_start = max(0, i_start)
    i_stop = min(n_samples, i_stop)

    if i_stop <= i_start:
        raise ValueError("t_stop must be larger than t_start.")

    time = np.arange(i_start, i_stop) / fs

    if figsize is None:
        figsize = (12, max(2.0 * len(channels), 3))

    fig, axes = plt.subplots(
        len(channels),
        1,
        figsize=figsize,
        sharex=sharex,
        squeeze=False,
    )

    axes = axes[:, 0]

    for ax, ch in zip(axes, channels):
        # Only this small slice is loaded into memory
        signal = np.asarray(signals[ch, i_start:i_stop])

        ax.plot(
            time,
            signal,
            alpha=alpha,
            linewidth=linewidth,
        )

        ax.set_ylabel(f"Ch {ch}")

        for x in xlines:
            ax.axvline(
                x,
                linestyle="--",
                linewidth=1,
                alpha=0.7,
            )

        ax.grid(True, alpha=0.25)

    axes[-1].set_xlabel("Time (s)")

    if title is not None:
        fig.suptitle(title)

    fig.tight_layout()

    return fig, axes


def quick_plot_signals(
    signal: np.ndarray,
    fs: float,
    spikes: np.ndarray = None,
    traces: dict = None,
    x_lines: dict = None,
    y_lines: dict = None,
    t0: float = 0.0,
    label: str = None,
    title: str = None,
    xlabel: str = None,
    ylabel: str = None,
):
    """
    Create 2 subplots: AP and noise. Plot signal + scatter spike locations.
    """
    ap = np.asarray(signal)

    # Time axes
    t_ap = t0 + np.arange(ap.size) / fs

    plt.figure(figsize=(12, 6))

    # AP subplot
    plt.plot(t_ap, signal, linewidth=1, label=label)
    if spikes is not None:
        plt.scatter(t_ap[spikes], ap[spikes], s=18, color='red', zorder=3)  # default color

    if isinstance(y_lines, dict):

        for label, yval in y_lines.items():
            plt.axhline(y=yval, linestyle="--", label=label)

    if isinstance(x_lines, dict):

        for label, xval in x_lines.items():
            plt.axvline(x=xval, linestyle="--", label=label)

    if isinstance(traces, dict):
        for label in traces.keys():
            plt.plot(t_ap, traces[label], label=label)

    if title is not None:
        plt.title(title)

    if xlabel is not None:
        plt.xlabel(xlabel)
    if ylabel is not None:
        plt.ylabel(ylabel)
    plt.legend()

    plt.show()


def plot_signal_and_derivative(signal: np.ndarray, derivative: np.ndarray, fs: float,
                               ch: int = 0, t0: float = 0.0):
    """
    Plot original vs derivative in two subplots.

    For 2D input, plots channel `ch`.
    """
    x = np.asarray(signal)
    d = np.asarray(derivative)

    if x.shape != d.shape:
        raise ValueError("signal and derivative must have the same shape")

    if x.ndim == 2:
        if not (0 <= ch < x.shape[0]):
            raise ValueError(f"ch out of range: 0..{x.shape[0]-1}")
        x_plot = x[ch]
        d_plot = d[ch]
    elif x.ndim == 1:
        x_plot = x
        d_plot = d
    else:
        raise ValueError("signal must be 1D or 2D")

    t = t0 + np.arange(x_plot.size) / float(fs)

    fig, axs = plt.subplots(2, 1, figsize=(12, 6), constrained_layout=True)
    axs[0].plot(t, x_plot, linewidth=1)
    axs[0].set_title("Original signal")
    axs[0].set_xlabel("Time (s)")
    axs[0].set_ylabel("Amplitude")

    axs[1].plot(t, d_plot, linewidth=1)
    axs[1].set_title("Derivative (d/dt)")
    axs[1].set_xlabel("Time (s)")
    axs[1].set_ylabel("Amplitude / s")

    plt.show()


def raster_plot_from_spikes(spike_buffer, n_channels=None):
    """
    spike_buffer: np.ndarray of shape (4096, N), binary (0/1)
    n_channels: number of channels to plot from the start
    """

    plt.figure(figsize=(12, 6))

    if n_channels is None:
        n_channels = spike_buffer.shape[0]

    for ch in range(n_channels):
        spike_times = np.where(spike_buffer[ch] == 1)[0]
        plt.scatter(
            spike_times,
            np.full_like(spike_times, ch),
            s=4,
            c='k',
            marker='|'
        )

    plt.xlabel("Time (samples)")
    plt.ylabel("Channel")
    plt.title(f"Raster Plot (First {n_channels} Channels)")
    plt.ylim(-1, n_channels)
    plt.grid(False)
    plt.tight_layout()
    plt.show()


def raster_plot(events, n_channels=None):
    """
    spike_buffer: np.ndarray of shape (4096, N), binary (0/1)
    n_channels: number of channels to plot from the start
    """

    plt.figure(figsize=(12, 6))

    if n_channels is None:
        n_channels = len(events)

    for ch in range(n_channels):
        plt.scatter(
            events[ch],
            np.full_like(events[ch], ch),
            s=4,
            c='k',
            marker='|'
        )

    plt.xlabel("Time (samples)")
    plt.ylabel("Channel")
    plt.title(f"Raster Plot (First {n_channels} Channels)")
    plt.ylim(-1, n_channels)
    plt.grid(False)
    plt.tight_layout()
    plt.show()


def raster_plot_spikes(
        spike_buffer,
        interval=1,
        t_offset=0,
        title=None,
        time_unit='s',
        n_channels=None,
        x_lines: dict = None,
        line_height=0.8,
        line_width=0.8):
    """
    spike_buffer: (channels, time), binary
    line_height: vertical span of each spike
    """

    if n_channels is None:
        n_channels = spike_buffer.shape[0]

    events = [
        np.where(spike_buffer[ch] == 1)[0] * interval + t_offset
        for ch in range(n_channels)
    ]

    plt.figure(figsize=(12, 6))
    plt.eventplot(
        events,
        orientation='horizontal',
        lineoffsets=np.arange(n_channels),
        linelengths=line_height,
        linewidths=line_width,
        colors='k'
    )

    plt.xlabel(f"Time ({time_unit})")
    plt.ylabel("Channel")
    if title is None:
        title = f"Raster Plot ({n_channels} Channels)"
    else:
        title += f" ({n_channels} Channels)"
    plt.title(title)

    if isinstance(x_lines, dict):

        for label, xval in x_lines.items():
            if isinstance(xval, dict):
                color = xval['color']
                val = xval['val']
                plt.axvline(x=val, linestyle="--", label=label, color=color)
            else:
                plt.axvline(x=xval, linestyle="--", label=label)

    plt.ylim(-1, n_channels)
    plt.tight_layout()
    plt.show()


def raster_plot_shanks(spikes,
                       title=None,
                       interval=1, line_height=0.8, line_width=0.6, color="k"):
    """
    Raster plot for 4 shanks.

    Args:
        spikes: np.ndarray, shape (4, 512, N), dtype {uint8/bool}, values 0/1
        interval: seconds per sample (dt = 1/fs)
        line_height: vertical span of each spike line
        line_width: linewidth for each spike line
        color: spike color
    Produces:
        4 vertically stacked raster subplots (one per shank), sharing x-axis (seconds).
    """
    spikes = np.asarray(spikes)
    if spikes.ndim != 3 or spikes.shape[0] != 4 or spikes.shape[1] != 512:
        raise ValueError("spikes must have shape (4, 512, N)")
    if interval <= 0:
        raise ValueError("interval must be > 0")

    n_shank, n_ch, n_samp = spikes.shape
    t_end = (n_samp - 1) * interval if n_samp > 0 else 0.0

    fig, axes = plt.subplots(
        nrows=4, ncols=1,
        figsize=(12, 10),
        sharex=True
    )
    if n_shank == 1:
        axes = [axes]

    for s in range(4):
        ax = axes[s]

        # Convert sample indices -> seconds for each channel
        events = [np.flatnonzero(spikes[s, ch]) * interval for ch in range(n_ch)]

        ax.eventplot(
            events,
            orientation="horizontal",
            lineoffsets=np.arange(n_ch),
            linelengths=line_height,
            linewidths=line_width,
            colors=color
        )

        ax.set_ylabel(f"Shank {s+1}\nCh")
        ax.set_ylim(-1, n_ch)
        ax.grid(False)

    axes[-1].set_xlabel("Time (s)")
    if title is None:
        title = f"Raster Plot shanks"
    axes[0].set_title(title)
    axes[-1].set_xlim(0, t_end)

    plt.tight_layout()
    plt.show()


def raster_plot_eventplot(events, n_channels=None,
                          fs=10_000,
                          line_height=0.8, line_width=0.8):
    """
    spike_buffer: (channels, time), binary
    line_height: vertical span of each spike
    """

    if n_channels is None:
        n_channels = len(events)

    plt.figure(figsize=(12, 6))
    plt.eventplot(
        events,
        orientation='horizontal',
        lineoffsets=np.arange(n_channels),
        linelengths=line_height,
        linewidths=line_width,
        colors='k'
    )

    plt.xlabel("Time (samples)")
    plt.ylabel("Channel")
    plt.title(f"Raster Plot (First {n_channels} Channels)")
    plt.ylim(-1, n_channels)
    plt.tight_layout()
    plt.show()


def plot_spike_heatmap(spikes_slice, grid_shape=(64, 64)):
    """
    spikes_slice: (4096,) or (4096, 1), binary
    grid_shape: spatial layout, default (64, 64)
    """

    spikes_flat = np.squeeze(spikes_slice)
    assert spikes_flat.size == np.prod(grid_shape)

    spike_map = spikes_flat.reshape(grid_shape)

    plt.figure(figsize=(6, 6))
    plt.imshow(
        spike_map,
        cmap='hot',
        interpolation='nearest',
        origin='lower'
    )
    plt.colorbar(label='Spike')
    plt.title("Spatial Spike Heatmap")
    plt.axis('off')
    plt.tight_layout()
    plt.show()


def plot_slim_heatmaps(data):
    """
    Plot 4 slim heatmaps from a numpy array of shape (4, 512).
    Each 512 vector is reshaped to (128, 4) and plotted as a separate subplot.

    Parameters
    ----------
    data : np.ndarray
        Input array with shape (4, 512)
    """

    if data.shape != (4, 512) and data.shape != (2048,):
        raise ValueError("Input dimension incorrect.")

    # Create a tall figure for slim heatmaps
    fig, axes = plt.subplots(
        nrows=1, ncols=4,
        figsize=(6, 9),          # Taller figure for readability
        constrained_layout=True
    )

    for i in range(4):
        # Reshape 512 → (128, 4)
        heat = data[i].reshape(128, 4)

        ax = axes[i]
        im = ax.imshow(heat, aspect='auto', cmap='inferno')

        ax.set_title(f"Heatmap {i+1}", fontsize=12)
        ax.set_xticks([])
        ax.set_yticks([])

        # Add a colorbar on the right of each heatmap
        fig.colorbar(im, ax=ax, fraction=0.015, pad=0.02)

    plt.show()


import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, LogNorm


def plot_slim_heatmaps_shared_cbar(data, scale="linear"):
    """
    Plot 4 slim heatmaps from a numpy array of shape (4, 512)
    or (2048,), reshaped to (128, 4), all sharing a single colorbar.

    Parameters
    ----------
    data : np.ndarray
        Input data with shape (4, 512) or (2048,).

    scale : str, optional
        Color scale:
        - "linear" : linear color scale (default)
        - "log"    : logarithmic color scale
    """

    data = np.asarray(data)

    if data.shape != (4, 512) and data.shape != (2048,):
        raise ValueError(
            f"Input dimension incorrect. Got {data.shape}, "
            "expected (4, 512) or (2048,)."
        )

    # Convert flat input into 4 shanks
    if data.shape == (2048,):
        data = data.reshape(4, 512)

    # --------------------------------------------------
    # Shared normalization
    # --------------------------------------------------

    if scale == "linear":

        norm = Normalize(
            vmin=np.min(data),
            vmax=np.max(data)
        )

    elif scale == "log":

        positive_values = data[data > 0]

        if positive_values.size == 0:
            raise ValueError(
                "Log scale requires at least one positive value."
            )

        norm = LogNorm(
            vmin=np.min(positive_values),
            vmax=np.max(positive_values)
        )

    else:
        raise ValueError(
            "scale must be either 'linear' or 'log'."
        )

    # --------------------------------------------------
    # Plot
    # --------------------------------------------------

    fig, axes = plt.subplots(
        nrows=1,
        ncols=4,
        figsize=(6, 10),
        gridspec_kw={"wspace": 1}
    )

    im = None

    for i in range(4):

        heat = data[i].reshape(128, 4)

        ax = axes[i]

        im = ax.imshow(
            heat,
            aspect="auto",
            cmap="inferno",
            norm=norm
        )

        ax.set_title(f"Shank {i + 1}", fontsize=12)
        ax.set_xticks([])
        ax.set_yticks([])

    # Shared colorbar
    cbar = fig.colorbar(
        im,
        ax=axes.ravel().tolist(),
        fraction=0.03,
        pad=0.04
    )

    cbar.set_label("Spike count")

    plt.show()


def plot_distribution(
        x: np.ndarray,
        bins: int = 100,
        mode: str = "pdf",          # "hist" or "pdf"
        show_gaussian: bool = True,
        show_sigma_lines: bool = True,
        title: str = "Data Distribution"
):
    """
    Plot histogram or PDF of a 1D dataset.

    Args:
        x               : 1D ndarray
        bins            : histogram bins
        mode            : "hist" or "pdf"
        show_gaussian   : overlay Gaussian fit
        show_sigma_lines: show μ, μ±σ, μ±2σ
        title           : plot title
    """

    x = np.asarray(x, dtype=np.float64)

    if x.ndim != 1:
        raise ValueError("x must be 1D")

    mu = np.mean(x)
    sigma = np.std(x, ddof=1)
    rms = np.sqrt(np.mean(x**2))

    plt.figure(figsize=(8, 5))

    # histogram / pdf
    density = (mode == "pdf")

    plt.hist(
        x,
        bins=bins,
        density=density,
        alpha=0.6,
        label=f"N={len(x):,}"
    )

    # Gaussian fit
    if show_gaussian and sigma > 0:
        xx = np.linspace(np.min(x), np.max(x), 1000)

        pdf = (
            np.exp(-0.5 * ((xx - mu) / sigma) ** 2)
            / (sigma * np.sqrt(2 * np.pi))
        )

        if mode == "pdf":
            plt.plot(xx, pdf, linewidth=2, label="Gaussian Fit")

    # μ and σ lines
    if show_sigma_lines:
        plt.axvline(mu, color='r', linestyle='-', label=f'μ={mu:.3g}')
        plt.axvline(mu - sigma, color='orange', linestyle='--')
        plt.axvline(mu + sigma, color='orange', linestyle='--')

        plt.axvline(mu - 2 * sigma, color='gray', linestyle=':')
        plt.axvline(mu + 2 * sigma, color='gray', linestyle=':')

        plt.axvline(mu - 3 * sigma, color='gray', linestyle=':')
        plt.axvline(mu + 3 * sigma, color='gray', linestyle=':')

    plt.xlabel("Value")

    if mode == "pdf":
        plt.ylabel("Probability Density")
    else:
        plt.ylabel("Count")

    plt.title(
        f"{title}\n"
        f"Mean={mu:.4g}, Std={sigma:.4g}, RMS={rms:.4g}"
    )

    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()

    return mu, sigma, rms