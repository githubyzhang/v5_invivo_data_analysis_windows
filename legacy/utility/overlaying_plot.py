from typing import Optional, Sequence, Mapping, Any
import numpy as np
import matplotlib.pyplot as plt


def plot_overlay_signals(
    signals: Mapping[str, Any],
    x: Optional[Sequence[float]] = None,
    xlines: Optional[Sequence[Any]] = None,
    ylines: Optional[Sequence[Any]] = None,
    title: Optional[str] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    grid: bool = True,
    legend: bool = True,
):
    """
    Plot multiple 1D signals on the same Matplotlib axis.

    Supports both shorthand:

        signals = {
            "raw": raw_signal,
            "filtered": filtered_signal,
        }

    and full style specification:

        signals = {
            "raw": {
                "data": raw_signal,
                "color": "gray",
                "alpha": 0.3,
                "linewidth": 1.0,
                "linestyle": "-",
                "zorder": 1,
                "label": "Raw",
            },
        }

    Parameters
    ----------
    ax:
        Matplotlib axis object.

    signals:
        Dictionary of 1D signals.

    x:
        Optional x-axis values. If None, sample indices are used.

    xlines:
        Optional vertical reference lines.

        Examples:
            xlines=[100, 200, 300]

            xlines=[
                {"x": 100, "color": "red", "linestyle": "--", "label": "stim"},
                {"x": 250, "color": "blue", "alpha": 0.5},
            ]

    ylines:
        Optional horizontal reference lines.

        Examples:
            ylines=[0, threshold, -threshold]

            ylines=[
                {"y": threshold, "color": "red", "linestyle": "--", "label": "threshold"},
            ]

    legend:
        If True, show legend only when labeled objects exist.
    """
    fig, ax = plt.subplots()
    # ------------------------------
    # Plot signals
    # ------------------------------
    for name, spec in signals.items():

        # Shorthand form:
        # "raw": raw_signal
        if not isinstance(spec, dict):
            spec = {"data": spec}

        if "data" not in spec:
            raise ValueError(f"Signal '{name}' is missing required field 'data'.")

        y = np.asarray(spec["data"])

        if y.ndim != 1:
            raise ValueError(
                f"Signal '{name}' must be 1D, got shape {y.shape}."
            )

        plot_kwargs = {
            "label": spec.get("label", name),
            "color": spec.get("color", None),
            "alpha": spec.get("alpha", 1.0),
            "linewidth": spec.get("linewidth", spec.get("lw", 1.5)),
            "linestyle": spec.get("linestyle", spec.get("ls", "-")),
            "zorder": spec.get("zorder", 1),
        }

        if x is None:
            ax.plot(y, **plot_kwargs)
        else:
            x_arr = np.asarray(x)

            if x_arr.shape[0] != y.shape[0]:
                raise ValueError(
                    f"x and signal '{name}' must have same length. "
                    f"Got len(x)={x_arr.shape[0]}, len(y)={y.shape[0]}."
                )

            ax.plot(x_arr, y, **plot_kwargs)

    # ------------------------------
    # Plot vertical reference lines
    # ------------------------------
    if xlines is not None:
        for spec in xlines:

            # Shorthand form:
            # xlines=[100, 200, 300]
            if not isinstance(spec, dict):
                spec = {"x": spec}

            if "x" not in spec:
                raise ValueError("Each xline spec must contain field 'x'.")

            ax.axvline(
                x=spec["x"],
                color=spec.get("color", "black"),
                alpha=spec.get("alpha", 1.0),
                linewidth=spec.get("linewidth", spec.get("lw", 1.0)),
                linestyle=spec.get("linestyle", spec.get("ls", "--")),
                zorder=spec.get("zorder", 100),
                label=spec.get("label", None),
            )

    # ------------------------------
    # Plot horizontal reference lines
    # ------------------------------
    if ylines is not None:
        for spec in ylines:

            # Shorthand form:
            # ylines=[0, threshold, -threshold]
            if not isinstance(spec, dict):
                spec = {"y": spec}

            if "y" not in spec:
                raise ValueError("Each yline spec must contain field 'y'.")

            ax.axhline(
                y=spec["y"],
                color=spec.get("color", "black"),
                alpha=spec.get("alpha", 1.0),
                linewidth=spec.get("linewidth", spec.get("lw", 1.0)),
                linestyle=spec.get("linestyle", spec.get("ls", "--")),
                zorder=spec.get("zorder", 100),
                label=spec.get("label", None),
            )

    # ------------------------------
    # Axis formatting
    # ------------------------------
    if title is not None:
        ax.set_title(title)

    if xlabel is not None:
        ax.set_xlabel(xlabel)

    if ylabel is not None:
        ax.set_ylabel(ylabel)

    if grid:
        ax.grid(True)

    # Only show legend if there are labels
    if legend:
        handles, labels = ax.get_legend_handles_labels()

        if len(labels) > 0:
            ax.legend()

    return ax
