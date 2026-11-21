# Setup and operating instructions

Run commands from the repository root. For current work and pending decisions, see the [roadmap](roadmap.md). Detection definitions belong in [METHODS.md](../METHODS.md); the saved-file contract belongs in [OUTPUTS.md](../OUTPUTS.md).

Use the project-local `.venv`. Dependencies are pinned in `requirements.txt`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests
```

## Full-recording detection

```sh
.venv/bin/python analysis/detect_recordings.py \
  --input "/absolute/path/to/any_recording_name.h5" \
  --output "results/my_recording" --mode adaptive --ma 50
```

Input and output paths are explicit; filenames are unrestricted. Adaptive thresholds and MA50 are the defaults. The input must contain a floating-point `signals` dataset shaped `(channels, samples)`, already converted to signal units. This v1 retains the project's nominal 10,000 Hz / physical 10,080 Hz convention; arbitrary sampling rates and raw uint16 conversion are not supported.

The output directory directly contains `spikes.h5`, `config.json`, `summary.json` and `progress.json`. The HDF5 file becomes final only after validation. Existing recording output directories are never overwritten; choose a new output directory for a rerun. Explicit-file runs do not import project-specific shared warnings: shared assessment is unavailable throughout, while per-channel flat guards still apply.

For an explicit input in fixed mode, add `--mode fixed --calibration /path/to/references/calibration.npz`. The calibration must follow the existing reference NPZ schema and have a `protocol.json` one directory above its containing directory, identifying the exact source path, size, modification time and threshold multiplier. A calibration for a different source is rejected.

The original project batch shortcut remains available to reproduce extra_4/5 runs and import their previously evaluated shared warnings:

```sh
.venv/bin/python analysis/detect_recordings.py \
  --recordings 4 5 --mode adaptive --ma 50 \
  --output results/spike_detection_ma50_adaptive
```

The alternative fixed mode uses the previously screened reference calibration:

```sh
.venv/bin/python analysis/detect_recordings.py \
  --recordings 4 5 --mode fixed --ma 50 \
  --calibration-directory results/fixed_reference_thresholds/references \
  --output results/spike_detection_ma50_fixed
```

Fixed mode requires the generated calibration files and their source-provenance protocol. Channels without eligible calibration are unavailable in this mode. Adaptive mode does not require quiet-reference eligibility.

## Long-running detection jobs

Watch terminal progress or the output directory's `progress.json`. The runner makes a noise pass followed by a candidate pass. A `spikes.partial.h5` file is unfinished; a successful recording has `spikes.h5`, `summary.json` and a completion marker. The final HDF5 rename follows structural validation. Inspect the summary and validation evidence before declaring an analysis accepted.

To stop a foreground run, use Ctrl-C in its terminal. There is no checkpoint resume: retain unfinished output for diagnosis and choose a new output directory to restart. For a batch interrupted between recordings, retain and validate completed recordings, then request only the unfinished recording in a new output root. A disconnected chat does not necessarily stop a local job; inspect progress and final files before launching another run. Source files are read-only and must remain available and unchanged throughout detection.

Generated output directories are never implicitly overwritten by the detector. The example batch output already exists locally; choose a new path when rerunning. Structural and source-audit commands, including the original-code-hash requirement, are documented in [OUTPUTS.md](../OUTPUTS.md).

## Activity report reproduction

These scripts target the saved extra_4/5 run, rather than arbitrary input files:

```sh
.venv/bin/python analysis/activity_report.py
.venv/bin/python analysis/finalize_activity_report.py
```

They write or replace generated analysis files in `results/extra45_activity_report/`. Preserve a copy first if comparing report versions. The source drive is required for waveform extraction. The first script calculates statistics, figures and waveform selections; the second produces HTML and reconciles counts and exposure. It contains presentation-specific narrative for this report and is not a generic report engine.

`analysis/activity_slides.mjs` is an Artifact Session callback for the connected deck, not a standalone PowerPoint builder. Its slide content and deck identifier are recorded in the generated folder's `slides.json` and `presentation.json`. Regenerating figures does not automatically update the saved presentation. Numerical/figure sources are reproducible; the final deck also includes editorial and layout work.

## Storage

Recordings live outside Git at `/Volumes/YZ/recording/invivo/26-11-06/0192/`. The project-local `.venv/` and generated `results/` are ignored. Keep source code, documentation and small review manifests in Git. Local evidence links require generated results; a fresh clone does not contain those results or the external data. Do not overwrite frozen calibrations, original labels or checksum-pinned evidence when starting a new experiment.
