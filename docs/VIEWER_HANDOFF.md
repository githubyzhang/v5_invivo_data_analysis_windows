# Viewer integration: extracellular-candidates-v1

Give the viewer project a `spikes.h5` file, this guide and [OUTPUTS.md](OUTPUTS.md). The HDF5 file is self-contained for event raster/count viewing: configuration, dimensions, timing and quality metadata are embedded. Neighboring `config.json` and `summary.json` are useful human-readable companions. Original signal files are needed only for waveform/trace views; waveform snippets are not included.

## Reader contract

- Require root attribute `schema == "extracellular-candidates-v1"` and `complete == True`.
- `/spikes` is a group, not the legacy two-dimensional dataset. Detect the schema before selecting a reader; retain the legacy reader separately.
- Read channel count and recording length from root attributes `source_channel_count` and `source_sample_count`; do not infer duration from the last event or channel count from channels containing events.
- Channels and sample indices are zero-based. Channels are electrodes, not sorted neurons. Spatial electrode geometry is not included; use the viewer's verified mapping separately.
- `/spikes/channel_offsets[c:c+2]` gives the half-open event row range for channel `c`. Every event array uses the same row order, channel then sample. Each channel's sample indices are sorted.
- Use integer `sample_index` as the exact coordinate. Use `nominal_fs_hz` for time axes and binning, consistent with `time_s`. Current outputs use 10,000 Hz nominal; physical 10,080 Hz is separately recorded. Do not silently mix these conventions.
- `negative_amplitude` is the positive magnitude of a negative filtered peak. Units are the converted source units, not automatically microvolts. Display conversions must be explicit.

## Efficient window display

Read a channel's event indices using its offsets; use `searchsorted` to select `[start_sample, stop_sample)`. Draw a raster directly, or histogram the selected indices into display bins. Avoid allocating a full recording-sized binary matrix. Binned counts may exceed one; use boolean occupancy only when the display explicitly represents any-event presence.

```python
import h5py
import numpy as np

with h5py.File("spikes.h5", "r") as f:
    assert f.attrs["schema"] == "extracellular-candidates-v1"
    assert f.attrs["complete"]
    channel = 0
    start_sample, stop_sample = 10000, 20000
    lo, hi = map(int, f["spikes/channel_offsets"][channel:channel + 2])
    samples = f["spikes/sample_index"][lo:hi]
    left, right = np.searchsorted(samples, [start_sample, stop_sample])
    visible_times = samples[left:right] / float(f.attrs["nominal_fs_hz"])
    # Other event fields use the identical row selection:
    available = f["spikes/shared_warning_available"][lo + left:lo + right]
    warning = f["spikes/shared20_warning"][lo + left:lo + right]
```

## Quality semantics

Display saved candidates by default; warnings do not establish false positives. Distinguish shared-warning states: unassessed (`available=False`), assessed/unflagged, and flagged. Current extra_4/5 files have 35 seconds assessed per 300 nominal seconds. Generic explicit-input runs have no shared assessment. Do not interpret unassessed times as clean.

Flat guards and invalid noise windows already exclude detection. An empty interval can mean unavailable data, not silence. `/quality/valid_noise_window`, `/quality/flat_guard_intervals` and configured physical filter edges describe those exclusions. For rates use `/quality/usable_samples_per_channel_window` for complete windows; partial display windows require intersecting exclusions with the requested interval. If users exclude warning times, update the exposure denominator too.

## Acceptance checks for the adapted viewer

1. Counts per channel agree with `/spikes/counts_per_channel`; total counts agree with the embedded summary (current extra_4: 115,992; extra_5: 173,029).
2. First/last samples in a selected interval obey `[start, stop)`; zero-based channel and sample indices are preserved.
3. Empty channels remain visible and recording duration includes trailing silence/unavailable time.
4. Zooming and binning preserve total event counts; unassessed warnings and unavailable signal time remain distinguishable.

The viewer adaptation itself has not been implemented or tested in this repository.
