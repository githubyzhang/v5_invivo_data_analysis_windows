# W7A — Full-shank guard and targeted artifact review

State: diagnostic review complete; recommendations proposed, not applied. Scope: frozen extra_4/shank0 pilot, 3,000,000 samples, 512 channels, 39,620 final events. No new sorting, mask, rate denominator, label change or confirmed neuron count.

The [local review packet](../../results/extra4_shank0/pilot01-w7a-reviewed/index.html) contains all-channel coverage, maximal flat runs, original event identities, deterministic selection ledgers, saved raw/preprocessed excerpts, 18 figures and independent checks. Methods and execution live in the [quality contract](../WINDOWS_QUALITY.md#w7a-all-channel-guard-and-saved-preprocessing-review).

## Channel findings

All 512 raw traces reproduce both the frozen historical guard intervals and the current native Mac-detector intervals exactly. The rule remains at least 10 identical samples, expanded by 500 samples each side and merged, using half-open intervals. This is a flatness proxy, not proof of ADC clipping or a hardware diagnosis.

452 channels trigger at least one guard; 60 trigger none. These are not 452 persistently bad electrodes:

| Binary channel | Original/global channel | Guarded recording time |
| --- | --- | --- |
| 248 | 1921 | 79.7529% |
| 252 | 1985 | 0.8249% |
| 240 | 1793 | 0.7792% |
| 244 | 1857 | 0.6801% |
| 124 | 1984 | 0.6500% |
| 236 | 1729 | 0.6432% |

b248 remains the sole persistent outlier: 1,827,501 exact-zero samples (60.9167%), 4,513 maximal flat runs of at least 10 samples and 94 merged guards covering 2,392,588 samples. Every other channel has less than 0.825% guarded time. Sign alone is not distinguishing evidence: the source recording values are nonpositive more generally.

Brief shared episodes explain much of the other-channel coverage. Of the 1,694,035 guarded channel-samples excluding b248, 1,459,633 (about 86.2%) fall in nominal seconds 99 and 100. During nominal second 99, 451 other channels have a flat run; the maximum simultaneous exact-flat count is 450 at sample 995019. The padded-guard maximum is 451 at sample 994840. Those counts describe different quantities. Across the recording, the union of guards excluding b248 covers 25,226 samples (2.5226 nominal seconds); this union is descriptive and is not applied to units.

The selected largest shared-guard episode visibly includes multiple flat raw traces near 99.5 nominal seconds, with suppression of their transformed activity. Other selected guard-concurrency peaks are at samples 2677865 and 2970288 (41 and 24 other channels guarded). Eight fixed spatially spread traces illustrate context; saved excerpts contain all 512 channels. These displays do not establish cause or missed-spike counts.

## Coincidence warnings and cluster 36

All three full-population broad coincidence intervals were reviewed, including all events in their surrounding 100.1 nominal ms contexts. Nine first/middle/last event ranks were additionally inspected at offsets -30 through +50 samples on each event's four nearest template-peak channels.

| Half-open sample interval | Sorter events in interval | Peak-channel guard overlaps |
| --- | --- | --- |
| [1332630, 1332729) | 9 | 1 |
| [1466744, 1466825) | 18 | 0 |
| [1806413, 1806543) | 10 | 0 |

None of these intervals intersects any other-channel guard when b248 is excluded. Thus coincidence warnings and the shared flat episode around second 99 detect distinct phenomena. The 37 broad-warning events and 160 peak-guard events overlap at one event, giving 196 unique flagged events. Five tight-warning events are within the broad-warning set. These are annotations, not 196 identified artifacts. The 19 events with unavailable coincidence assessment remain unavailable.

Slow shared raw fluctuations are reduced in the reconstructed preprocessing displays, while some event-centered deflections remain. This bounded selection does not separate genuine synchronized activity from shared interference across all 37 warning events, and does not justify deleting them as a group.

One particularly informative example is final event index 16420, cluster 36, sample 1332689. The b248 raw trace is exactly zero throughout offsets -30 through +50. Its transformed b248 trace ranges from -6.1831 to +5.0569 units over the same support and contains an event-centered deflection. This establishes that the transformed channel is not direct evidence of a measured raw waveform on that electrode. CAR, spatial whitening/drift transforms and temporal filtering must be considered; the individual contribution of each stage was not isolated. It does not establish that all multichannel evidence for that event is artifactual.

Three first/middle/last guarded cluster-36 events and three outside-guard events were also reviewed with wide context and closeups. They retain the prior concerns about broad baseline fluctuations and b248's altered signal. Guarded events can lie in the padding around a flat segment rather than at a flat sample. Outside-guard status does not establish a well-isolated neuron. Retain the W5 proposal to hold cluster 36; no automatic deletion or acceptance follows.

## Proposed next experiment: W7B

Run two new bounded sorts in the repaired root environment: an all-512-channel control and an otherwise matched run excluding binary channel 248 / global channel 1921. Keep the original 512-column binary unchanged; exclude through the supported sorter channel-selection mechanism and verify the resulting channel map. Do not zero-fill or rewrite raw input. Re-estimate preprocessing for each condition through the normal sorter path; do not recycle 512-channel whitening into the exclusion condition.

Record input hashes, explicit resolved settings, random-seed behavior, geometry, software versions and fresh output paths for both. Compare the new full-channel control against the frozen historical pilot first, because FAISS changed from 1.16.0 to 1.13.2. Then compare the new control with the exclusion run. A paired experiment characterizes sensitivity, not an isolated FAISS effect or definitive neuron truth; repeat controls if run variability makes the contrast ambiguous.

Evaluate cluster correspondences by event-time agreement and raw waveforms on common physical channels, allowing split/merge/unmatched outcomes. Original numeric cluster IDs are not cross-run identities. Review retained candidates 34/35/5/12, the neighborhood of original cluster 36, contamination/refractory diagnostics, time stability, and behavior inside/outside the named warning intervals. Do not use higher automated-good counts alone as evidence of improvement.

Do not add a multiple-channel exclusion group solely because many channels briefly flatten. Treat shared transient intervals as a separate observability question, requiring a Kilosort-specific policy that accounts for multichannel support and filtering. No whole-shank guard union, censoring rule or adjusted firing-rate denominator is adopted in W7A.
