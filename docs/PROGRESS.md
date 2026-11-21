# Investigation history through 2026-11-20

Historical snapshot consolidated before the documentation reorganization. This is an evidence ledger, not the current tracker. For present status and open work, use the [roadmap](development/roadmap.md); for commands, use [setup](development/setup.md). Test counts below describe their respective rounds, not checks rerun today. Earlier experiments retain their original scope and defaults.

## Delivery decision at this checkpoint

On 2026-11-20, the user chose adaptive thresholds as the default, retained fixed-reference thresholds as an option, and prioritized finishing detection and saving candidates for extra_4 and extra_5. MA50 is the practical baseline-subtraction choice. extra_6 is excluded from this delivery.

Full-recording detection is complete. The local jobs finished despite the chat/network interruption; the completed files were recovered and audited without rerunning detection.

## Completed full-recording delivery

Both recordings were processed across all 2,048 channels and 3,000,000 samples per channel (300 nominal seconds), using MA50 and adaptive thresholds. Fixed-reference mode remains available.

| Recording | Saved candidates | Channels with candidates | Usable channel-seconds | Output |
|---|---:|---:|---:|---|
| extra_4 | 115,992 | 1,578 | 606,186.5553 | [spikes.h5](../results/spike_detection_ma50_adaptive/extra4/spikes.h5) |
| extra_5 | 173,029 | 2,042 | 607,495.2182 | [spikes.h5](../results/spike_detection_ma50_adaptive/extra5/spikes.h5) |

Each recording has 614,400 nominal channel-seconds before quality exclusions. Counts describe candidate events, not confirmed eAPs or distinct neurons. Different recording conditions and observation support prevent interpreting the count difference as a biological effect.

The [saved-file audit](../results/spike_detection_ma50_adaptive/validation.json) passed for both files: output hashes, source metadata, code hashes, event ordering/spacing, thresholds, flat guards and warning annotations. Per recording, 20 event amplitudes and six noise windows were checked against the source, and all saved per-second median floors were recomputed. These checks verify implementation consistency, not biological accuracy or an independent full re-detection. All 32 automated tests passed at that delivery checkpoint.

Shared-disturbance assessment covers only 35 of 300 nominal seconds in each recording. The remaining times are explicitly unassessed. The ±10/±20 ms warnings label 67/80 candidates in extra_4 and 19/22 in extra_5; these events remain saved. Waveform arrays are not embedded; sample indices allow retrieval from the original recordings. Results remain local and Git-ignored; code, documentation and the user-label export were subsequently included in the v1 pipeline checkpoint (`2bffaf5`).

## Completed investigations

| Stage | What changed or was learned | Local evidence |
|---|---|---|
| Legacy review and pilot | Preserved legacy sources; checked moving-average alignment, clipping proxies, median-noise safeguards and window boundaries. Candidate counts are not validated eAP counts. | [Pilot](../results/extra4_pilot_60_65/review.html) |
| Controlled detector comparison | Compared moving-average and high-pass residuals, RMS and MAD using matched observation support. Large common disturbances can dominate candidate counts. | [Controlled comparison](../results/controlled_comparison/review.html) |
| Shared-disturbance evaluation | Added baseline/broadband consensus warnings. Adjusted baseline sensitivity and compared guard widths; warnings stayed separate from detections. | [Shared warning review](../results/shared_artifact_review_extended/review.html) |
| Frozen guard comparison | Tested unchanged 10/20 ms guard choices on new intervals. Longer guards also affect plausible spike-like events; no automatic exclusion adopted. | [Frozen guard review](../results/frozen_guard_validation/review.html) |
| Per-channel disturbance review | Evaluated fast variability, step and low-variability warnings. Relative noise rules missed persistent disturbance in extra_6. | [Local review](../results/local_artifact_review/review.html) |
| MA50/100/200 comparison | MA50 reduced candidates at two reviewed baseline transitions while preserving narrow example waveforms. Shorter windows did not resolve extra_6 fast noise. MA100/200 reproduced earlier results. | [MA comparison](../results/ma_window_comparison/review.html) |
| Quiet-reference threshold study | Compared fixed and adaptive thresholds with reference eligibility and matched support. Eligible channels: extra_4 1,925; extra_5 1,307; extra_6 421. Stable reference estimates did not guarantee clean data. | [Fixed reference review](../results/fixed_reference_thresholds/review.html) |
| Focused MA50 review | Excluded extra_6, inspected eight longer reference views and 42 selected events, and tested frozen calibration at 120–125 and 210–215 s in extra_4/5. | [Focused review](../results/focused_ma50_review/review.html) |
| User waveform labeling | Verified all 42 exported event identities: 38 plausible eAP, three uncertain, one likely artifact. Both threshold methods contribute plausible candidates. | [Versioned labels](reviews/ma50_user_review.json) |

The reports deliberately separate candidate counts, provisional waveform interpretation and adopted defaults. The selected waveform sample is not a random accuracy assessment. Reference-window acceptance was not collected by the event-label export.

## Focused new-interval comparison

Counts below are from the matched reference-eligible subset, not the completed all-channel adaptive run.

| Recording and nominal interval | Adaptive MA50 | Fixed MA50 |
|---|---:|---:|
| extra_4, 120–125 s | 1,291 | 1,377 |
| extra_4, 210–215 s | 1,404 | 1,486 |
| extra_5, 120–125 s | 1,467 | 1,218 |
| extra_5, 210–215 s | 1,472 | 1,233 |

The user labeled all 14 adaptive-only review examples plausible eAPs; fixed-only examples included ten plausible eAPs, three uncertain and one likely artifact. This motivated retaining both options with adaptive as default, rather than selecting a method by total count.

## Implementation scope at this checkpoint

`analysis/detect_recordings.py` provides bounded-memory full-recording processing, full-recording per-channel peak spacing, explicit partial-window handling, both threshold modes and validated HDF5 output. Synthetic tests cover cross-boundary competition, long flat runs, final partial windows and agreement with a whole-signal calculation. Earlier experiment scripts remain available for reproduction.

The default pipeline excludes suspected-flat guards and unavailable noise windows. Shared-disturbance warnings are imported for already evaluated intervals only; full-recording shared-warning coverage remains unfinished. Fast-noise correction, stimulation-period analysis, spike sorting, spatial deduplication and full waveform export are not part of this delivery.

At this checkpoint, the recommended next activity was analysis of saved candidates and coverage metadata; the activity report below followed. This was not a sorting-input contract.

## V1 interface and viewer handoff

The CLI now accepts arbitrary input filenames via `--input` and requires an explicit `--output`. The previous `--recordings 4 5` batch shortcut is retained. Explicit-file runs do not import the project-specific shared-warning cache; fixed mode requires an explicit calibration and matching source provenance. Input dataset and sampling conventions are unchanged. Existing completed detection files were not rerun or modified.

The [viewer handoff](VIEWER_HANDOFF.md) documents the schema, efficient event access, nominal timing, channel identity and quality-display requirements. CLI integration and source-mismatch rejection tests bring the suite to 34 passing tests. “In vivo extracellular spike detection v1 pipeline” describes this practical candidate-detection release; it does not imply validated spike identities or solved stimulation/fast-noise artifact removal.

## First full-recording activity report

Descriptive analysis is saved in [the local activity report](../results/extra45_activity_report/report.html), with PNG/PDF figures, per-channel and per-time-bin tables, selected waveform arrays, source hashes and selection provenance. A 15-slide presentation is identified in `results/extra45_activity_report/presentation.json` and can be exported as PowerPoint from its viewer.

The report includes complete rasters, exposure-normalized candidate rates, time trends, channel concentration, a channel/time heatmap, raw traces with detections, aligned waveform examples and threshold/coverage distributions. No detection defaults or saved candidates changed. extra_4's top 205 channels contain 90.7% of candidates versus 69.4% in extra_5. extra_5's five busiest seconds contain 17.1% of its candidates; a 1 ms bin at 276.887 s contains candidates on 1,479 channels and is outside the existing shared-warning assessment. These are descriptive findings, not confirmed neural effects or artifact classifications.

The activity report was committed as `1eed96a` (`extracellular detected spikes analysis`). See [setup](development/setup.md) for reproduction commands and presentation limitations.
