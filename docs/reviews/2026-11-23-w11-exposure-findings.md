# W11 — Boundary, quality and exposure policy proposal

Date: 2026-11-23. State: implemented, independently validated and visually reviewed; policy proposed, not adopted.

Recommend an **annotation-first primary analysis** over the half-open sample interval **[100, 2,999,900)**, retaining clipping/flatness and coincidence flags without automatically censoring those intervals. This domain requires a complete ±100-sample raw review window. It is not a measured filter-settling interval, nor a claim that every boundary event is artifact. The [machine-readable proposal](../../configs/extra4_shank0_analysis_policy.proposed.json) awaits W12 acceptance alongside the cluster subset. It does not execute event selection or modify the selected run.

The W10 recommendations remain **11 putative candidates, 38 holds and nine proposed withholds**. No curation labels, events or original files changed. The [local W11 packet](../../results/extra4_shank0/w11-exposure-review01/index.html) contains event-index-preserving annotations for all38,687 events, 11 exposure scenarios for each of58 clusters, saved interval sets, raw excerpts, nine figures and the independent audit.

## Boundary audit: an additional candidate affected

The all-cluster audit finds **five events at sample2**, belonging to selected-run clusters **38, 32, 54, 57 and35** (original event indices0–4, respectively). There are no other events outside the proposed analysis domain. W9/W10 highlighted candidate38; **candidate32 also has a sample2 event**, now explicitly accounted for. The frozen earlier records remain historical evidence.

The raw excerpts show the recording start without sufficient pre-event context; no padding or invented waveform was used for review. The same domain rule would omit all five from future derived event tables, including two events from the proposed11-candidate subset. The original sorter output remains38,687 events; the all-cluster analysis-domain count would be38,682. The proposed candidate subset would change from18,254 to **18,252 events**, with candidate32 retaining4,679 and candidate38 retaining378. This is a prospective count, not an accepted curated table.

The denominator must match: **2,999,800 samples =299.98 nominal seconds or297.599206349 physical seconds**. Keep the original sample indices/time origin; do not shift the recording start or concatenate retained intervals. The full-recording reference remains3,000,000 samples =300 nominal seconds. The shortened domain is a transparent review convention; it does not establish that all retained events are valid.

## What the quality annotations cover

All coincidence intervals retain the verified **2048-channel extra_4 population**. Per-channel guard rules remain ≥10 identical raw samples padded by500 samples each side; these are flatness proxies, not a calibrated clipping detector. Counts below refer to the selected without-248 run.

| Annotation | Covered samples / nominal duration | Events flagged across all58 clusters |
| --- | --- | ---: |
| Broad coincidence warning | 310 /0.031 s | 35 |
| Tight coincidence warning | 57 /0.0057 s | 4 |
| Coincidence assessment available | 2,997,275 /299.7275 s | 38,670 |
| Any active electrode's padded guard | 25,226 /2.5226 s | 325 |
| At least256 of511 active electrodes guarded (diagnostic50% threshold) | 2,750 /0.275 s | 13 |
| At least256 active electrodes exactly flat (same diagnostic threshold) | 1,587 /0.1587 s | 4 |
| Excluded b248's guards, context only | 2,392,588 /239.2588 s | 30,853 |

The shared padded episode is [994031,996781), near99.4–99.7 nominal seconds. Exact shared flatness occupies shorter, sometimes interrupted spans. They are different quantities. Neither diagnostic50% threshold is adopted as a universal masking rule. The generic Mac shared-signal/oscillation warning is **unavailable** here; it must not be replaced by an all-false “clean” annotation or confused with shared flatness.

Among the11 proposed candidates, there are nine broad warnings, zero tight warnings,19 peak-electrode guard events,43 events with at least one of the eight nearby electrodes guarded and six with all eight guarded. These categories overlap. Eleven candidate events lack broad assessment; two of those are the boundary events, leaving nine unavailable within the proposed domain. Availability remains separate from warning membership. Nearby electrodes are geometric proxies, not established sorted-unit observability footprints.

## Sensitivity: counts and denominators change together

Each scenario is defined by a saved half-open sample interval set, with event counts and time denominators derived from the same set. Results below are for the11 proposed candidates. Omitted-event counts include the two boundary events. Maximum rate change is the largest absolute relative change for any one candidate against its full-recording rate; it is not a pooled rate or an error estimate.

| Diagnostic scenario | Events retained | Events omitted | Maximum absolute whole-recording rate change |
| --- | ---: | ---: | ---: |
| Full-recording reference | 18,254 | 0 | 0% |
| Proposed interior domain, annotations only | 18,252 | 2 | 0.2572% |
| Interior, broad-warning intervals removed | 18,243 | 11 | 1.0943% |
| Interior, peak-electrode guards removed | 18,233 | 21 | 0.2111% |
| Interior, peak guards or broad warnings removed | 18,224 | 30 | 0.9717% |
| Interior, shared padded guards ≥50% removed | 18,243 | 11 | 0.1657% |
| Interior, shared exact flatness ≥50% removed | 18,250 | 4 | 0.2044% |
| Interior, any of eight nearby electrodes guarded | 18,209 | 45 | 0.2418% |
| Interior, all eight nearby electrodes guarded | 18,246 | 8 | 0.2572% |
| Interior, entire raw context must avoid peak guards | 18,233 | 21 | 0.2044% |
| Interior, broad-assessed time only | 18,243 | 11 | 0.1682% |

Removing time can increase a rate even when events are removed. Therefore a count-only sensitivity or unchanged denominator would answer a different question. Rates from censored scenarios describe activity within their retained intervals, not a recovered true neuronal rate. Per-unit guard-based scenarios have different denominators; do not sum unit exposures and call that recording duration.

The small changes in these whole-recording means **do not validate local timing, synchrony or short-bin rates**. These effects may concentrate in a small interval. All28 complete candidate events flagged by peak guard OR broad warning OR all-eight guard membership were plotted against up to128 comparison events per unit (seven affected candidates). Their raw excerpts include large slow ramps, steps and altered backgrounds, sometimes with a central spike-like component. This supports keeping visible event/time warnings; it does not establish that all flagged events are false detections or that all unflagged events are valid. All nine W11 figures were visually reviewed.

## What this does—and does not—resolve from W10

The lower-amplitude71-event group in12 contains its four broad/two tight warnings, but none of those71 events overlaps a peak/nearby guard or shared50% guard/flat episode. The57-event group in29, both groups in40 and the123-event group in45 are likewise not explained by these local/shared guards or coincidence warnings. Within31, one event in the136-event correspondence group overlaps a peak guard, which cannot explain the group as a whole.

Neither side of the49 near-coincident43/44 pairs has a peak/nearby guard, broad/tight warning or shared50% flag. One pair overlaps the guard of some other active channel, illustrating why a whole-shank union is too broad to attribute local detection quality. Existing annotations therefore do not resolve the43/44 question. All W10 holds remain; no subgroup is promoted, removed or split on the basis of this sensitivity review.

## Proposed policy and validation

For W12, propose the interior domain and unchanged quality-event annotations as the primary summary, with full-recording reference counts and named censoring sensitivities alongside it. Report nominal/physical timing explicitly. Keep unavailable assessment distinct from unflagged; overlay relevant intervals for temporal plots. Any short-bin, event-triggered or synchrony conclusion needs its own flagged-interval sensitivity rather than relying on these small whole-recording rate changes. Do not apply b248's guards to all units, use the whole-shank union automatically, treat flat padding as proven unusable time, or silently rerun sorting on masked data.

The independent validator checked **638 cluster/scenario rows**, interval membership, matching denominators and both rate conventions, all event flags, physical support maps and active-channel coverage tracks. It reconstructed **929 raw excerpts /1,486,307 values**, including the five truncated boundary excerpts. Six existing helper tests passed. The raw binary and W7B/W7A/W10 manifests remained unchanged. Selected-run metadata and the W10 proposal ledger are unchanged. No source recording, archived worker, original result, label or event was modified.

Next is W12: review the concrete11-candidate subset and proposed policy with the user, record explicit acceptance in a new revision, then build adopted derived summaries. This W11 proposal is not itself an adoption or a claim of artifact-free spikes, validated effective neuronal exposure, or complete neuron recovery.
