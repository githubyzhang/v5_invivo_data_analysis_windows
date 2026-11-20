# Decisions and current defaults

## Adopted on 2026-11-20

The user chose to retain both threshold options and make **adaptive thresholds the default**. The first delivery priority is a usable detection pipeline and saved candidates for extra_4 and extra_5. Investigation of threshold variants is no longer a prerequisite for producing those outputs.

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
