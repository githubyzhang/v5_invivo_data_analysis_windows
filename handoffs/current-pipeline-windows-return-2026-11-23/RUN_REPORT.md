# Current Mac pipeline — Windows acceptance return

2026-11-23. Native numerical acceptance passed. This report is prepared for handoff, not automatically sent to Mac. No Git commit or push was performed.

## Package and adaptation

Input: `current_pipeline_windows/current_pipeline_windows`, prepared on Mac 2026-11-23. All **106 payload files** verified against the supplied manifest, with no unexpected files. Manifest SHA-256: `7b6ae7b17c22f3a00d67ccf4e1c0ea5eb6526188ebccd0f3cf684cc96d1911f8`. Generating HEAD: `fbe30269513ed21318efd901afebee3086e755d9`; working-tree changes are part of the package identity.

Preserved the full package at `worker_returns/mac-current-pipeline-2026-11-23/received/` inside the single Windows root. Imported **45 unchanged upstream files** into `custom_pipeline/mac_2026_11_23/`, including production code, research dependencies, tests and four contract documents. `UPSTREAM_FILES.json` pins their hashes; Git attributes preserve exact bytes. No upstream algorithm changes were required. Historical root `analysis/`, old results and the original worker snapshot remain unchanged.

Windows adaptations are separate:

- `scripts/run_custom_pipeline.py`: dedicated interpreter/subprocess, explicit generic input, adaptive MA50/named profiles, fresh result destinations, source hashes before/after, logs and status.
- `scripts/annotate_kilosort_from_custom.py`: pilot-scoped source verification and external annotation sidecar, with no sorting or curation.
- `scripts/validate_custom_pipeline.py`: fixture/native numerical acceptance and captured test evidence.
- `tests/test_custom_pipeline_adapter.py`: interval joining and protected-output checks.
- Separate Windows dependency lock, integration guide, roadmap/quality updates and W6 record.

The [adaptation provenance](ADAPTATION_PROVENANCE.json) records exact file hashes, launch commands and input/output identities. The [guide](../../docs/CUSTOM_PIPELINE_WINDOWS.md) owns setup and schema details.

## Environment and commands

Windows 11 build 26300, x86-64; root Python **3.12.10**, versus the Mac handoff's Python 3.11. Created `.venv-detector` independently of all Kilosort/viewer environments. The four requested pins installed without substitution: NumPy **2.4.6**, SciPy **1.17.1**, h5py **3.16.0**, Matplotlib **3.11.2**. Transitive versions are pinned in `requirements-windows-detector-lock.txt`; pip check passes. Initial sandbox DNS failed; installation succeeded after approved network access. There was no unavailable-pin fallback or change to the sorter environment.

Commands ran from `C:\Projects\invivo_extracellular_data_analysis` (upstream tests use the imported source root):

```powershell
& ./.venv/Scripts/python.exe -B C:/Users/yucha/Downloads/current_pipeline_windows/current_pipeline_windows/verify_package.py
& ./.python/python.exe -m venv .venv-detector
& ./.venv-detector/Scripts/python.exe -m pip install -r custom_pipeline/mac_2026_11_23/requirements.txt
& ./.venv-detector/Scripts/python.exe -B scripts/run_custom_pipeline.py detect --input C:/DATA/cnea_data/invivo/26-11-06/0192/extra_4_signals.h5 --output results/custom_detector/extra4_windows01
& ./.venv-detector/Scripts/python.exe -B scripts/run_custom_pipeline.py annotate --input worker_returns/mac-current-pipeline-2026-11-23/received/reference_outputs/extra4/spikes.h5 --output results/custom_detector/reference_extra4_annotation_windows01
& ./.venv-detector/Scripts/python.exe -B scripts/run_custom_pipeline.py annotate --input worker_returns/mac-current-pipeline-2026-11-23/received/reference_outputs/extra5/spikes.h5 --output results/custom_detector/reference_extra5_annotation_windows01
& ./.venv-detector/Scripts/python.exe -B scripts/validate_custom_pipeline.py --native-extra4 results/custom_detector/extra4_windows01 --output results/custom_detector/acceptance_windows01
& ./.venv-detector/Scripts/python.exe -B scripts/annotate_kilosort_from_custom.py --detector results/custom_detector/extra4_windows01 --evidence worker_returns/extra4_shank0/pilot01/received --binary data/extra4_shank0_float32.bin --output results/custom_detector/kilosort_pilot01_quality_windows01
```

These destinations now exist; reproduction requires fresh names and corresponding validator reference-path adjustments if names change.

## Native results and exact comparisons

**42 upstream tests and three adapter tests pass.** Both bundled spike/sidecar fixtures pass structural, identity and expected-count validation. Regenerating annotations from the extra_4/5 reference spikes on Windows exactly reproduces all 14 stored datasets per sidecar, including active/eligible count tracks, interval unions, event availability and warnings. Named default links select broad.

| Recording / execution | Candidate count | Tight warnings | Broad warnings | Broad duration |
| --- | ---: | ---: | ---: | ---: |
| extra_4 native redetection, all 2048 channels | 115,992 | 577 | 714 | 0.0310 nominal s |
| extra_5 annotation of supplied Mac candidates | 173,029 | 41,175 | 42,155 | 0.7252 nominal s |

The native extra_4 source is `C:\DATA\cnea_data\invivo\26-11-06\0192\extra_4_signals.h5`, 12,313,887,776 bytes, float16 `signals` shaped `(2048,3000000)`. Full-file SHA-256 is **`3bedaa51bca65205dcc81e25ef48f249c9f1ea34346f4cfd7327e26269bd9755`**, unchanged before/after. Native detection took approximately 219.5 seconds, excluding subsequent coincidence and wrapper hashing. Nominal duration is 300 s; physical duration 297.619048 s. No retiming was applied.

Fourteen native spike/noise/quality datasets match the Mac extra_4 fixture **exactly**, including event identities, amplitudes, thresholds, MAD/floor estimates, flat guards, valid windows and usable exposure. Both named coincidence profiles' intervals, masks and availability also match exactly. extra_4 retains 408 candidate events with unavailable broad assessment. All 115,992 candidates survive the coincidence step.

Expected differences: generic `--input` does not import Mac source-bound baseline/broadband masks. Its three per-event signal-warning fields are false and three signal-warning interval arrays are empty, meaning **unavailable**, not clean. The reference preserves 35 seconds of historical signal-based assessment. These differences do not change detector candidates or coincidence masks. File bytes also differ due to source paths, timestamps and provenance; no whole-file byte-equivalence claim is made. [validation.json](validation.json) enumerates comparisons, with captured logs beside it.

## Kilosort integration

Before joining annotations, every one of the **1,536,000,000** mapped float32 shank0 values was compared with the corresponding HDF5 samples after exact float16 conversion; all match. The pilot binary retains SHA-256 `11cd033eb0bda858f7598123a795f198078cc227d98d92543e8ea88f9e12eff0`. All **169 frozen pilot payloads** remain unchanged.

The new `external_quality.h5` annotates the original 39,620 events / 59 clusters:

- Broad coincidence warning: **37** sorter events; tight warning: **5**.
- Coincidence assessed: **39,601** events; **19** unavailable.
- Template-peak-electrode flat-guard overlap: **160** events, including **131/339** cluster-36 events.
- Peak-electrode detector-observable: **39,405** events; this is not sorted-unit exposure or an accepted-event set.
- Historical signal-warning availability: **zero** in this new native sidecar, without modifying the older partial annotations.

Warnings transfer by half-open integer **time intervals**, not candidate row flags. The warning population is all 2048 electrodes; the target sorter population is one 512-channel shank. Interval membership is independently checked against sample masks, and sidecar event order/identity is verified. Source, detector, warning and sorter arrays are hash-bound. [kilosort_annotation_validation.json](kilosort_annotation_validation.json) records results.

This is an offline quality sidecar; Phy/Kilosort GUI overlays are not implemented. No raw preprocessing, common subtraction, blanking, event exclusion, label change, merge/split or sorter rerun was performed. Quality flags are not artifact truth. Original Kilosort and detector observations remain separately interpretable.

## Remaining limits and next step

Native acceptance here covers adaptive MA50 extra_4 and annotation of both reference datasets. It does not establish native full extra_5 redetection, fixed-mode calibration migration, stimulation handling, extra_6 acceptance, complete signal-based disturbance coverage or biological precision/recall. Coincidence settings remain annotation-only; lower channel quorum would be an explicit new choice.

Use the integrated warnings to review the pending Windows pilot proposals and design unit-level observability rules. Do not automatically apply per-electrode exposure to multichannel units, treat 115,992 electrode events as neurons, or interpret portability equivalence as a newly measured performance improvement.
