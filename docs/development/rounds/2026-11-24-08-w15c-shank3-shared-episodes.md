# W15C - Shank3 matched sensitivity and shared episodes

Date: 2026-11-24. The user authorized the documented W15C all-channel and b259/global2045 exclusion conditions. Shank3 is the fourth shank.

## Outcome and recommendation

Recommend **`w15c-exclude25901` as the provisional shank3 run for W15D's selection decision and subsequent curation**. Avoid the severely compromised b259, while retaining evidence of shared signal loss and changed populations. The exclusion is not demonstrated to improve overall artifact burden. The result supports bounded curation, especially away from the shared episodes; it does **not** support treating the entire recording as uniformly observable neuronal activity. No run selection, subset, merge or exposure mask is adopted here.

| Condition | Active electrodes | Events | Clusters | Automated good | Automated mua |
| --- | ---: | ---: | ---: | ---: | ---: |
| `w15c-allchannels01` | 512 | 16,819 | 39 | 13 | 26 |
| `w15c-exclude25901` | 511 | 17,666 | 42 | 14 | 28 |

Both use identical original samples, the same unchanged 512-column binary, scientific settings, seed policy and runtime. Both save Kilosort's preprocessed visualization copy. This extra output differs from W15A/B's storage choice but does not introduce a new filter or mask. Original labels/events are preserved. [Checkpoint metadata](../../../configs/extra4_shank3_sensitivity.v1.json) pins outputs and scripts.

Evidence: [matched comparison](../../../results/extra4_shank3/w15c-comparison01/index.html), [shared episodes and saved preprocessing](../../../results/extra4_shank3/w15c-shared-review02/index.html), [away-zone quarter waveforms](../../../results/extra4_shank3/w15c-stability01/index.html), [control baseline](../../../results/extra4_shank3/w15c-control-review01/index.html), [exclusion baseline](../../../results/extra4_shank3/w15c-exclusion-review01/index.html).

## Shared activity is a signal-availability limitation

The fixed source mask uses W14 exact-flat intervals and **at least 256 of the original 512 electrodes**, unchanged between sorts. Its 77 contiguous fragments total **72,005 samples / 7.2005 nominal seconds** (2.4002% of the recording). This is a descriptive threshold, not an adopted exposure policy. A diagnostic shoulder expands the union by 500 samples on each side, excludes the core, and totals 9,555 samples / 0.9555 nominal seconds. The remaining 2,918,440 samples / 291.8440 nominal seconds are called away. Physical durations use 10080 Hz; nominal figures here use 10000 Hz.

| Zone | Control events | Control events / nominal s | Exclusion events | Exclusion events / nominal s |
| --- | ---: | ---: | ---: | ---: |
| Shared-flat core | 14 | 1.94 | 17 | 2.36 |
| Shoulder | 17 | 17.79 | 24 | 25.12 |
| Away | 16,788 | 57.52 | 17,625 | 60.39 |

Both conditions show a substantial detection deficit in shared-flat time. This is not evidence of biological silence or of successful artifact removal. The three detailed episode views, selected from the two longest and two most event-rich control fragments (three unique selections), show sustained source plateaus, reduced saved-preprocessing magnitude and sparse detections in both conditions. Core spans are 99.4383-101.1521, 155.0534-156.0808 and 267.6456-269.0593 nominal seconds. Their matched preprocessing traces are very similar; omitting b259 does not repair the shared disturbance.

The exclusion's 17 core events belong to c2 (14), c16 (one) and c30 (two). Some channels may retain signal while others are flat. These events are neither automatically rejected nor validated by their zone membership. Core-versus-away raw correlations use very few core examples and cannot establish clean single-unit support. At most two core events outside c2 support each comparison.

**Away does not mean clean.** The half-population threshold misses partial-shank disturbances, and a fixed 50 ms shoulder does not establish recovery of every electrode. Waveform windows are classified by their event center and can cross zone boundaries. Do not convert the 7.2005-second diagnostic into a universal dropped-time rule. W16C must assess per-unit exposure and shared-episode sensitivity before any W16D policy is accepted. Full-duration rates in baseline tables remain descriptive observed-event rates, not corrected underlying neuronal rates.

## Cross-run populations and curation priorities

All 13 control good clusters have good-labeled best candidates in the exclusion run. Ten have Dice >=0.9; 12 have common-channel raw correlation >=0.954. These are candidate correspondences, not accepted neuron identities. Common-event means are not independent validation.

- **Control c0 → exclusion c1 and c2:** c0 has 5,044 events. Exclusion c2 has 4,582 events with 4,503 matched to c0 (Dice 0.936; correlation 0.978). Exclusion c1 has 430 events, 421 matching c0 (97.9% of c1; correlation 0.644 over the full comparison footprint). Both peak at b2. This is consistent with redistribution/splitting of the large control population. It is not evidence of one additional neuron, and no merge is adopted. Review c1/c2 jointly during within-run curation.
- **Control c23 → exclusion c26:** 177→296 events; 153 matched, Dice 0.647 and correlation 0.768. Central raw shapes look similar, but increased detection and changed spatial/background support need targeted review.
- **Exclusion c25:** 29 events, with away-quarter counts 0/8/13/8. Its good label does not establish sustained single-unit evidence; first-quarter waveform is unavailable.
- **Control c8 → exclusion c10** and **control c31 → exclusion c34** have lower Dice (0.861 and 0.889), despite high pooled waveform correlations. Exclusion c21 has only 70 events, with quarter counts 25/26/9/10. Include temporal/sparse support in curation.

The away-quarter screen covers all 14 exclusion good clusters. Central waveform structure is broadly retained across available quarters, but this is bounded sampling, not acceptance: 32 excerpts maximum per quarter, eight common channels, and pooled reference selections can overlap quarter selections. Nonempty quarter-to-reference correlations range approximately 0.808-1; counts and rates vary. c25 has no Q1 mean and visibly variable sparse-quarter background. All 81 condition-specific clusters, including mua, remain available for the later full ledger.

Only two control events form the b259-peaking mua cluster c26; it has no +/-2-sample cross-run match in the pair inventory. Unlike shank2's b148, this electrode does not create a large peak-defined control population. W14's persistent local compromise supports its omission, but this experiment alone does not demonstrate increased neuron recovery or isolate all downstream consequences of the change.

## Quality annotations are not an overall improvement score

| Event annotation | Control | Exclusion |
| --- | ---: | ---: |
| Template-peak guard | 83 | 97 |
| Any guard on the same common 511 electrodes | 10,856 (64.55%) | 11,386 (64.45%) |
| At least half of the same common electrodes guarded | 31 | 41 |
| Full-2048-channel broad warning | 12 | 11 |
| Tight warning | 0 | 0 |
| Coincidence assessment unavailable | 15 | 17 |
| Incomplete +/-100-sample raw context | 10 | 11 |

Peak-guard and shared-guard counts do not improve. The lower any-active-guard count (13,263→11,386) partly reflects removal of b259 from that measure; fixed-common-electrode exposure is the fairer comparison. Full-population coincidence warnings retain their 2048-channel definition and address a different phenomenon. Generic shared-signal warning assessment remains unavailable; the W14-derived flat diagnostic does not fill that missing field.

Other channel-specific concerns remain, including b403/global1788 and b486/global440. Each has a one-event peak-defined mua cluster in the exclusion result (c38 and c41 respectively), with guard overlap. This does not establish that their effects are confined to those clusters. No wider channel exclusion is adopted.

## Validation, preservation and next step

Six condition/geometry/matching/zone tests passed. Both sorter postchecks passed with unchanged input pins and resolved settings matched. Independent baseline audits verified 34,485 events, 81 cluster rows, 324 quarter rows and 2,668 raw excerpts. [Comparison audit](../../../results/extra4_shank3/w15c-comparison-validation01/checks.json) verified 290 overlapping pairs, 4,453 full-channel raw windows and three fixed comparison masks. [Shared audit](../../../results/extra4_shank3/w15c-shared-validation01/checks.json) verified all three source-zone masks, 154 episode rows, 81 cluster-zone rows, 2,740 raw windows and 58,924,058 source values used in detailed excerpts. The stability tool separately reread all 1,630 selected quarter excerpts and records 56 quarter rows.

Saved preprocessing was checked for original width, length and omitted-column zeros, and selected values were reread exactly. It is Kilosort's int16 visualization copy divided by 200, not calibrated voltage or an exact replay of internal float tensors. No claim of absent conversion overflow or faithful reconstruction of lost raw signal is made. Source geometry and original sample indices remain authoritative.

Visually reviewed all three detailed shared-episode pages, both away-quarter pages and cross-run c0→c1, c0→c2 and c23→c26 pages. The first shared-report attempt stopped at a plotting API error; its partial output is preserved as `w15c-shared-review01`. The corrected, audited packet is `w15c-shared-review02`; numerical inputs and sorter packets were not changed. Frozen W15A/B scripts were reused; a small presentation adapter corrects their W15B-specific heading without modifying them.

Prior releases, W14 inputs/evidence, source recordings, sorter labels and archives remain unchanged. Next is **W15D**, the working-run selection checkpoint across shanks1-3. Present this qualified recommendation and W15B's tradeoffs for explicit selection; full curation and unit/exposure acceptance remain later rounds.
