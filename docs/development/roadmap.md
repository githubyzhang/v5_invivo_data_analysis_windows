# Roadmap and current status

Updated: 2026-11-20. This is the single current-status tracker.

## Current checkpoint

The v1 detector and first extra_4/5 activity analysis are complete and committed: `2bffaf5` (pipeline) and `1eed96a` (activity analysis). Detector defaults are governed by [DECISIONS.md](../DECISIONS.md); numerical results and prior checks are preserved in the [investigation history](../PROGRESS.md). Documentation is now organized using the adapted convention in [the documentation map](../README.md).

| Work | State | Evidence / boundary |
|---|---|---|
| Detector comparisons and quiet-reference study | Reviewed; adaptive default adopted | [History](../PROGRESS.md), [decisions](../DECISIONS.md) |
| Full extra_4/5 detection and event storage | Implemented; saved-file/source checks passed | [Outputs](../OUTPUTS.md), [run audit](../../results/spike_detection_ma50_adaptive/validation.json) |
| Activity report | Completed; descriptive findings only | [HTML report](../../results/extra45_activity_report/report.html), [report validation](../../results/extra45_activity_report/validation.json), [deck identity](../../results/extra45_activity_report/presentation.json) |
| Viewer integration handoff | Documented; external viewer implementation not verified here | [Viewer guide](../VIEWER_HANDOFF.md) |
| Spike sorting | Proposed; not installed, run or adopted | Next step below |

Latest round: [Documentation organization](rounds/2026-11-20-01-documentation-organization.md). Earlier work remains in the historical ledger rather than being assigned invented round records.

## Next: sorting preparation

The user's next research direction is spike sorting. The proposed first pilot is one verified shank of extra_4 across its full five-minute recording, followed by a separate extra_5 run after reviewing its widespread disturbances. This is a recommendation, not an approved sorter configuration.

Before launching, resolve:

- **Geometry:** confirm the channel-to-shank mapping in [legacy shank utilities](../../legacy/utility/shank.py), physical row/column spacing and orientation. Index order alone does not establish geometry.
- **Compute environment:** establish whether an NVIDIA-GPU workstation is available or execution must remain on the Mac. Kilosort4 with SpikeInterface analysis is a candidate, not an adopted dependency. Recheck requirements when selecting/installing tools.
- **Sorting input and artifact handling:** use continuous converted recordings, retain original sample coordinates, and define usable channels/intervals. The saved detector events enforce 5 ms spacing, so clustering them alone would inherit censored close events and bias refractory-violation checks. Preserve them for comparison.
- **Preprocessing and review gate:** evaluate sorter filtering and waveform windows under the nominal sampling convention; do not assume MA50 detection preprocessing is automatically appropriate for sorting. Review templates across neighboring electrodes, stability, isolation and duplicate units before assigning neuronal interpretations.

Acceptance for the preparation round: a verified geometry file, selected execution environment, explicit input/preprocessing/artifact contract and bounded pilot plan. No neuronal identity matching between extra_4 and extra_5 is assumed.

## Open research and deferred scope

Full-recording shared-disturbance assessment remains incomplete: existing flags cover only 35/300 nominal seconds per recording. The activity report identifies extra_5 episodes at 154–155 s and 276.887 s for raw-signal review; these are not confirmed artifacts. Decide artifact policy before interpreting affected sorting output.

extra_6, stimulation-period artifact correction, raw uint16 conversion, validated fast-noise removal and cross-recording unit matching remain deferred. Spatial analysis requires verified geometry. Refer to [setup](setup.md) for source availability and run/restart instructions; the external drive must be mounted for waveform work.
