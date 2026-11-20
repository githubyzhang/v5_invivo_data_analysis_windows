# In vivo extracellular spike detection

This project analyzes simultaneous 2048-channel extracellular recordings. The current practical pipeline uses **MA50 baseline subtraction and adaptive MAD thresholds**, with a per-window median noise floor. Fixed per-channel quiet-reference thresholds remain an explicit alternative.

The current recording scope is **extra_4 and extra_5**. extra_6 is excluded from the current pipeline work by user decision because of its unusually disturbed signals. Detected events are candidate eAPs, not sorted neurons or validated spike identities.

## Start here

- [Methods and quality handling](docs/METHODS.md)
- [Decisions and current defaults](docs/DECISIONS.md)
- [Progress and experiment history](docs/PROGRESS.md)
- [Saved output schema and reading examples](docs/OUTPUTS.md)
- [Viewer project handoff](docs/VIEWER_HANDOFF.md)
- [User waveform labels](docs/reviews/ma50_user_review.json)

Source recordings are outside the repository at `/Volumes/YZ/recording/invivo/26-11-06/0192/`. Converted floating-point `extra_4_signals.h5` and `extra_5_signals.h5` are trusted inputs. The original `legacy/` code remains a reference implementation.

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

## Storage and interpretation

Source HDF5 files are opened read-only. Generated results and the local environment are ignored by Git; documentation, code, tests and the small user-label export are versioned. Local report links require the corresponding generated results directory.

All analysis uses **nominal 10,000 Hz**, by project convention; physical sampling is **10,080 Hz**. Channels and sample indices are zero-based. The pipeline saves negative-going candidates and their thresholds, timestamps and quality annotations. It does not perform spike sorting, spatial deduplication, waveform reconstruction, stimulation-artifact removal or fast-noise subtraction.

Shared-disturbance warnings currently cover only the previously evaluated intervals. Outside that coverage, the output records the warning assessment as **unavailable**, not artifact-free. See the output schema before filtering candidates or calculating rates.
