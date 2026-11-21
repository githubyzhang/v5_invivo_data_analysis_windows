# Input, sorting and interpretation contract

## Portable data contract

`data/extra4_shank0_float32.bin` is little-endian float32, C-order `(3000000 samples, 512 channels)`. Each time sample contains 512 consecutive values. It is exactly 6,144,000,000 bytes. Values are losslessly cast from the stored float16 converted signal; no MA subtraction, high-pass, resampling, interpolation, clipping repair, time excision or gain correction was applied during export. All sample indices refer to the original full recording, starting at zero.

`geometry/channel_map.csv` maps binary channel index to original zero-based channel ID, shank, row and column. Binary channels are sorted by pad index (`row * 4 + column`) on shank 0. `geometry/probe.json` contains `chanMap` (binary indices, never original global IDs), `xc`, `yc`, `kcoords`, and `n_chan`. Coordinates are relative: x = column × 30 µm; y = row × 30 µm. The verified legacy ordering is retained; anatomical insertion direction is not inferred. Other shanks and absolute inter-shank spacing are irrelevant to this single-shank run.

Nominal rate is **10000 Hz**, physical rate **10080 Hz**. Use nominal rate in the sorter to stay consistent with the project; retain integer sample coordinates and both rates in metadata. Do not resample. The source is trusted converted data; numerical units are unchanged. The configured scale is a numerical multiplier, not a new ADC calibration or assertion of microvolt units.

`reference/extra4_candidates.h5` is the previous **all-2048-channel** detection/quality file, for comparison and artifact review only. Its event channel IDs are global. Use `channel_map.csv` to select this shank. Its flat guards and unavailable noise windows are detector observation masks, not proven sorter artifact truth. Existing shared flags cover only 35 seconds of the 300-second recording; absence outside those intervals means unassessed.

## Baseline configuration and preflight

The supplied baseline uses Kilosort4's own preprocessing, common-average reference enabled, no sign inversion, 300 Hz high-pass, 61-sample waveform window (6.1 nominal ms), one drift block and numerical scale 1e6. These are explicit starting choices, not established optimal settings for this probe or 10 kHz data. Leave detection thresholds at the installed Kilosort4 defaults and save the fully resolved settings. Verify compatibility with the installed version, waveform support and measured amplitude range before execution. Do not apply MA50 before Kilosort or impose a separate 5 ms candidate spacing.

Inspect raw traces, channel coverage, geometry and Kilosort preprocessing diagnostics. The initial diagnostic run retains the full timeline and channels with no custom interval zeroing or destructive artifact subtraction. Record significant flat/noisy channels and disturbance intervals. If these prevent a meaningful run, the worker may exclude demonstrably unusable channels or conduct a clearly labeled sensitivity run, keeping the original binary intact and recording exact binary/global channel IDs, intervals, settings and rationale. Do not silently cut and concatenate time, inject zeros into source data, or present a changed run as the baseline. Shared consensus alone is insufficient to label a false spike.

Sort only extra_4/shank0. Preserve baseline output and use distinct directories for every alternative. If memory fails, first record the error and GPU memory; document batch-size changes. Do not keep reducing settings to obtain a desired unit count. Use the upstream Kilosort API directly for the first run to avoid introducing a wrapper compatibility layer; SpikeInterface/Phy may be added separately for inspection if useful.

## Review and acceptance

Check sample bounds, aligned event arrays, integer cluster IDs, channel maps and template dimensions. Review multichannel waveform templates, spike amplitudes over time, autocorrelograms, contamination/refractory measures, spatial localization, drift diagnostics and near-duplicate clusters. Separate automated labels, manual review and suggested exclusions. Report low-spike-count/unstable clusters rather than promising complete neuron recovery from five minutes.

Compare sorted timing and spatial footprints with prior detections as a diagnostic; agreement is not ground truth. Do not compare raw total counts as if sorting and per-electrode detection counted the same objects. Any rate metric that excludes quality intervals must use matching exposure. Preserve units and events before curation so the Mac project can revisit decisions.

The assignment completes when either a reviewed reproducible baseline is returned, or a concrete blocker is returned with logs, environment, attempted remedies and the smallest required next action. No automatic adoption of 'good' labels as confirmed neurons; no cross-recording unit matching.
