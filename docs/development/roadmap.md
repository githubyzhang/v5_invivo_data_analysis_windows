# Roadmap and current status

Updated: 2026-11-21. This is the single current-status tracker.

## Current checkpoint

The v1 detector and first extra_4/5 activity analysis are complete and committed: `2bffaf5` (pipeline) and `1eed96a` (activity analysis). Detector defaults are governed by [DECISIONS.md](../DECISIONS.md); numerical results and prior checks are preserved in the [investigation history](../PROGRESS.md). Documentation is now organized using the adapted convention in [the documentation map](../README.md).

| Work | State | Evidence / boundary |
|---|---|---|
| Detector comparisons and quiet-reference study | Reviewed; adaptive default adopted | [History](../PROGRESS.md), [decisions](../DECISIONS.md) |
| Full extra_4/5 detection and event storage | Implemented; saved-file/source checks passed | [Outputs](../OUTPUTS.md), [run audit](../../results/spike_detection_ma50_adaptive/validation.json) |
| Activity report | Completed; descriptive findings only | [HTML report](../../results/extra45_activity_report/report.html), [report validation](../../results/extra45_activity_report/validation.json), [deck identity](../../results/extra45_activity_report/presentation.json) |
| Viewer integration handoff | Documented; external viewer implementation not verified here | [Viewer guide](../VIEWER_HANDOFF.md) |
| Spike sorting | Kilosort4 selected; Windows worker package prepared and export verified | [Worker round](rounds/2026-11-21-01-kilosort-worker-package.md); no sorter run yet |

Latest round: [Windows worker preparation](rounds/2026-11-21-01-kilosort-worker-package.md). Earlier work remains in the historical ledger rather than being assigned invented round records.

## Next: Windows sorting pilot

The user selected Kilosort4 and authorized a portable worker folder under `/Volumes/YZ/`. Mac remains the research/curation home; the Area-51 Windows desktop runs the bounded job. The first pilot is extra_4, zero-based shank0, all 3,000,000 samples. Legacy spatial mapping and both 30 µm pitches are confirmed. Anatomical direction is not inferred.

[Worker instructions](../../handoffs/kilosort4-extra4-shank0/START_HERE.md) own the assignment, preprocessing starting choices, environment requirements and return contract. The verified package is at `/Volumes/YZ/kilosort4-extra4-shank0-worker-2026-11-21/` (about 6.15 GB). Its manifest records completed binary readback and source-value checks. Windows must establish the actual GPU/driver/CUDA combination and exact dependency lock before running. Kilosort4 is selected, but baseline settings and unit labels are not scientifically validated.

Continuous signals are the sorting input. Previous detected candidates are comparison evidence only: their 5 ms spacing censors close events and must not bias refractory-quality assessment. Preserve source sample coordinates and review spatial templates, stability, contamination and duplicate clusters. Additional shanks and extra_5 wait for Mac-side review of the pilot return.

## Open research and deferred scope

Full-recording shared-disturbance assessment remains incomplete: existing flags cover only 35/300 nominal seconds per recording. The activity report identifies extra_5 episodes at 154–155 s and 276.887 s for raw-signal review; these are not confirmed artifacts. Decide artifact policy before interpreting affected sorting output.

extra_6, stimulation-period artifact correction, raw uint16 conversion, validated fast-noise removal and cross-recording unit matching remain deferred. Spatial analysis requires verified geometry. Refer to [setup](setup.md) for source availability and run/restart instructions; the external drive must be mounted for waveform work.
