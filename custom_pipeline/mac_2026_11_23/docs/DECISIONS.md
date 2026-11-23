# Decisions and current defaults

This reference owns adopted detector choices and their rationale. The [roadmap](development/roadmap.md) owns delivery status and open proposals; sorting recommendations do not change these defaults.

## Adopted on 2026-11-20

The user chose to retain both threshold options and make **adaptive thresholds the default**. The initial delivery priority was a usable detection pipeline and saved candidates for extra_4 and extra_5. Further threshold investigation was not a prerequisite for that delivery.

| Setting | Current choice |
|---|---|
| Recordings | extra_4 and extra_5 |
| Baseline subtraction | Centered MA50, nominal 5 ms |
| Threshold mode | Adaptive by default; fixed quiet-reference calibration optional |
| Noise estimate | Centered MAD divided by 0.67448975 |
| Noise window | Each nominal second; supported final partial window included |
| Threshold | 5 × max(channel noise, median noise across valid channels) |
| Candidate polarity | Negative |
| Minimum peak spacing | 50 samples, nominal 5 ms, applied across the whole recording per channel |
| Suspected clipping | Exact repeated stored values for ≥10 samples, plus ±500-sample guard |
| Shared disturbances | Annotate where assessed; do not automatically remove candidates |
| Fast-noise correction | Disabled; no validated removal method adopted |
| extra_6 | Excluded from this delivery; retained as a separate research case |

MA100 and MA200 remain available for comparisons and explicit pipeline runs. The new runner defaults to MA50. Legacy scripts and historical experiment defaults remain unchanged.

## Why retain both threshold options

The user reviewed 42 deliberately selected waveform examples: 38 plausible eAPs, three uncertain events and one likely artifact.

| Candidate group | Plausible eAP | Uncertain | Likely artifact |
|---|---:|---:|---:|
| Fixed-only | 10 | 3 | 1 |
| Adaptive-only | 14 | 0 | 0 |
| Detected by both | 14 | 0 | 0 |

Fixed calibration adds plausible candidates but also misses plausible candidates found by adaptive detection. These selected examples do not establish population accuracy or sensitivity. Retaining both options is justified; replacing adaptive detection outright is not supported by this review. The user's labels are preserved separately from the original assistant interpretations in [the exported review](reviews/ma50_user_review.json).

The one likely artifact is extra_5, zero-based channel 962, sample 1,218,542, nominal 121.8542 s. All three uncertain examples are fixed-only extra_4 candidates.

## Boundaries of the decision

- The fixed-reference calibration remains exploratory. Accepting the adaptive default does not certify every screened reference window as clean.
- Full adaptive detection uses valid MA50 data from all channels. It is not restricted to the 1,925 extra_4 or 1,307 extra_5 channels eligible for the fixed-reference study.
- The controlled studies used common support across several filters to isolate comparison effects. The practical runner uses MA-only validity, so full-run counts are not expected to reproduce those restricted comparison totals exactly.
- extra_4/5/6 are all purely extracellular recordings. extra_5 and extra_6 followed current-injection experiments. Differences do not establish a causal stimulation effect.
- The proposed electrochemical “bubbling noise” explanation for extra_6 is a user hypothesis, not a confirmed mechanism.
- Stimulation-period recordings, conversion from raw uint16, sorting, spatial deduplication and automatic artifact exclusion remain separate tasks.

## Adopted on 2026-11-22: independent research tracks

Mac continues the custom detector and electrode-level analysis; Windows independently develops Kilosort4 sorting, curation and unit-level analysis. This replaces the earlier compute-worker-only arrangement. Mac scientific progress does not wait for sorting acceptance. Keep shared sample coordinates, channel geometry, source identity and provenance compatible; retain separate method definitions and quality decisions. Compare results only with stated counting units, observation support and preprocessing. Do not assume cross-recording cluster identity or automatically merge Windows changes into Mac.

The [handoff](../handoffs/windows-kilosort-independent/START_HERE.md) owns the repository/transfer instructions. No detector defaults changed in this split.

## Adopted on 2026-11-22: third warning evidence source

The user approved adding widespread candidate coincidence alongside baseline and broadband shared-disturbance evidence. It is implemented as an annotation-only sidecar, preserving all original candidates. The first 1/5/10 ms × 25/50/75% evaluation uses an exploratory 5 ms / 50% primary rule and at least 1024 fully eligible channels. Adding the method does not adopt automatic exclusion, establish optimal parameters, or imply that every shared event is artifactual. Existing detector defaults and signal-based warning coverage remain unchanged.

## Adopted on 2026-11-23: named coincidence profiles

The user adopted **tight-coincidence warning = 1 ms / 5%** and **broad warning = 5 ms / 5%**, with **broad as default**. Both remain annotation-only. Keep the minimum 1024 fully eligible channels, sample-stride scanning and no additional guard. Both masks are saved in named-profile runs; selection determines the default display/consumer warning, not whether events survive. No automated deletion or artifact classification is adopted.

Detection CLI runs now generate both profiles in a separate `coincidence/` sidecar after candidate detection, selecting broad unless `--coincidence-warning tight` or explicit `none` is requested. Standalone annotation defaults to broad; `--profile tight` changes selection while preserving both masks. Explicit grids are research mode with no selected primary. The original 5 ms / 50% reference and historical studies remain unchanged. Original detector thresholds and event counts do not change.
