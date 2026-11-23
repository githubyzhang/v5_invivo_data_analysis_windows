# Saved spike candidate outputs

The default output root is `results/spike_detection_ma50_adaptive/`. Each recording directory (`extra4`, `extra5`) contains:

| File | Purpose |
|---|---|
| `spikes.h5` | Validated event arrays, noise estimates and quality metadata |
| `config.json` | Parameters, source identity, code hashes and annotation provenance |
| `summary.json` | Counts, observation exposure, warning coverage, duration and output hash |
| `progress.json` | Current stage or completion marker |

`spikes.partial.h5` is an unfinished intermediate, not a completed recording. The runner renames it to `spikes.h5` only after validation. It refuses existing per-recording output directories; use a distinct output root for reruns. No resume or overwrite operation is implicit.

## HDF5 schema

The schema identifier is `extracellular-candidates-v1`. Root attributes include `complete`, the source dimensions, nominal and physical sampling rates, zero-based indexing, event ordering, configuration and summary JSON.

All `/spikes/` event arrays below have the same length and are ordered by channel, then sample index:

| Dataset | Meaning |
|---|---|
| `channel_id` | Zero-based electrode channel, uint16 |
| `sample_index` | Zero-based source sample index, uint64 |
| `time_s` | Nominal seconds, sample index / 10,000 |
| `negative_amplitude` | Positive magnitude of the negative MA residual at the peak, in stored converted units |
| `threshold` | Positive threshold applied to that event, in the same units |
| `shared_warning_available` | Whether shared-disturbance evaluation covers this event time |
| `shared10_warning` | Existing shared warning with ±10 ms padding |
| `shared20_warning` | Existing shared warning with ±20 ms padding |

`/spikes/channel_offsets` has `n_channels + 1` entries. Events for channel `c` occupy `[offsets[c], offsets[c+1])`. `/spikes/counts_per_channel` is the difference of adjacent offsets.

`/noise/mad` and `/noise/threshold` have shape `(channels, nominal_seconds)`, including a final partial second if present. Invalid estimates/thresholds are NaN. `/noise/median_floor` contains the per-second adaptive median; its `used_for_detection` attribute is false in fixed mode. Fixed mode additionally saves `/noise/fixed_threshold_per_channel`; its thresholds come directly from the frozen calibration, not from the diagnostic adaptive floor.

Quality datasets:

- `/quality/valid_noise_window`: channel-by-window availability used for detection.
- `/quality/usable_samples_per_channel_window`: actual observable samples after exclusions; zero for unavailable windows/channels.
- `/quality/reference_eligible`: all true in adaptive mode because no reference gate applies; the frozen reference eligibility in fixed mode. It is not a general good-channel label.
- `/quality/flat_guard_intervals`: rows `(channel_id, start_sample, stop_sample_exclusive)`.
- `/quality/shared_available_intervals`, `/quality/shared10_intervals`, `/quality/shared20_intervals`: global half-open sample intervals.

Physical filter-edge exclusion widths are recorded in `config.json`. Shared-warning coverage is partial; unknown times are represented explicitly. Per-event warning arrays alone cannot distinguish evaluated-clean from unevaluated without `shared_warning_available`.

## Read a channel

```python
import h5py

path = "results/spike_detection_ma50_adaptive/extra4/spikes.h5"
with h5py.File(path, "r") as f:
    assert f.attrs["complete"]
    channel = 1436
    lo, hi = map(int, f["spikes/channel_offsets"][channel:channel + 2])
    sample_indices = f["spikes/sample_index"][lo:hi]
    nominal_times = f["spikes/time_s"][lo:hi]
    amplitudes = f["spikes/negative_amplitude"][lo:hi]
    warning_available = f["spikes/shared_warning_available"][lo:hi]
    warning20 = f["spikes/shared20_warning"][lo:hi]
    usable_seconds = f["quality/usable_samples_per_channel_window"][channel].sum() / 10000
```

These outputs are sparse event arrays, not a dense channel-by-sample spike matrix. Raw and filtered waveform snippets are not embedded; use sample indices to read the original signal with appropriate filter context.

For candidate rates, use usable channel-seconds rather than nominal duration when exclusions matter. If you later exclude shared-warning periods, also subtract their observable exposure from the denominator. A zero count on an unavailable channel does not imply neural silence.

## Validate an existing file

```sh
.venv/bin/python -c "from analysis.detect_recordings import validate; validate('results/spike_detection_ma50_adaptive/extra4/spikes.h5')"
```

Validation checks saved-file consistency. It does not establish biological detection accuracy or independently verify the entire source file by content hash. Source provenance records path, dimensions, dtype, size and modification time; output and code hashes are recorded separately.

To additionally verify output/code hashes and selected event amplitudes and noise estimates against the source recordings:

```sh
.venv/bin/python analysis/audit_spike_outputs.py results/spike_detection_ma50_adaptive
```

This writes `validation.json` in the project batch output root and requires the source drive to be mounted. It samples source measurements rather than independently re-detecting the entire recording. The audit deliberately requires the original detector code hashes: later code edits require checking out the generating version to repeat that exact provenance audit. The completed extra_4/5 audit predates the explicit-input CLI enhancement; its saved validation remains the record of that run. The standalone `validate` function above can still check structural consistency using the current code.

For an explicit `--input` run, the `--output` directory itself contains the four recording files (no `extra4`/`extra5` subdirectory). See [the viewer handoff](VIEWER_HANDOFF.md) for integration requirements.

## Candidate-coincidence sidecar

Named-profile defaults are widths 1/5 ms with a 5% quorum: `tight = w1ms_q5`, `broad = w5ms_q5`. Broad is selected by default. Both are saved even if tight is selected. `protocol.json` and `summary.json` record `default_warning`, `primary`, `named_warnings` and (protocol) `policy_version`. Explicit custom grids have null `default_warning` and `primary`; they do not silently select a profile.

This is an additive extension of `candidate-coincidence-v1`. Historical sidecars retain their original protocols and may lack the named groups. Do not infer a historical default from a current policy name.

Schema `candidate-coincidence-v1`, produced by `analysis/candidate_coincidence.py`. A new output directory contains `annotations.h5`, `protocol.json` and `summary.json`. Input v1 files remain unchanged. The exact input SHA-256, generator hash and source configuration bind the sidecar to a particular detection output; check this hash before joining another file's events.

- `/events/channel_id` and `/events/sample_index`: identical row order and identities to the original v1 event arrays.
- `/tracks/w{width}ms/active_channels` and `eligible_channels`: counts indexed by every integer full-window start, length `n_samples - width_samples + 1`. Only channels usable throughout a window contribute to either count. Width in samples is a group attribute.
- `/tracks/w{width}ms/available_intervals`: global half-open sample ranges covered by at least one window with enough eligible channels; `/event_available` is the corresponding per-event boolean.
- `/variants/w{width}ms_q{percent}/intervals`: merged global half-open warning intervals, union of qualifying windows without extra padding. `/event_warning` labels every original event within that union.
- `/warnings/broad` and `/warnings/tight`, when their variants exist, expose `intervals`, `event_warning`, `available_intervals` and `event_available` as HDF5 hard links to the corresponding variant/track data. Each group has a `variant` attribute. They do not duplicate arrays.
- In named-profile runs, `/warnings/default` links to the selected profile group. Root attributes `default_warning` and `primary` identify the selection. Custom grids have no default alias, even if both named variants happen to be present.
- Root attributes include schema, complete, input SHA-256 and protocol JSON. A partial HDF5 file is not a completed result.

`protocol.json` defines eligibility, timing, thresholds and limits. `summary.json` distinguishes old-warning overlap within assessed time from new flags outside old coverage. Potential usable channel-seconds affected is hypothetical exposure loss if exclusion were adopted; this workflow excludes nothing. Overlapping variant counts must not be added. Event availability is global evidence availability, not an assertion that its particular channel contributed to a qualifying window.

Outputs are channel-level candidate annotations, not unit identity or confirmed artifact labels. Source waveforms are not needed for annotation itself. The review script reads the source separately and saves selected context snippets in the report folder.


### Detection CLI integration

New detection CLI outputs retain the original `spikes.h5`, configuration, summary and detection-progress files, and add `coincidence/` plus `pipeline_progress.json`. The latter distinguishes annotation pending/failed/complete or explicitly disabled. Detection `progress.json = complete` alone does not certify completion of the annotation stage. Annotation failures preserve the validated spike file and exit with an error; retry the standalone annotator against that file into a fresh output directory. Do not rerun detection merely to retry annotations.

`run_pipeline(...)` is the integrated Python entry point. Low-level `detect(...)` deliberately remains detection-only for existing callers and exact detector testing. Original spike-file hashes, schema and exposure denominators are not rewritten by annotation. Named warnings label events; they never alter the set of saved candidates. Availability must accompany warning booleans: false warning with false availability means unknown, not clean.
