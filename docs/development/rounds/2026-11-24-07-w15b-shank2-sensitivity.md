# W15B - Shank2 matched channel-exclusion sensitivity

Date: 2026-11-24. Authorized by the user's request to proceed with documented W15B conditions. Shank2 is the third shank.

## Outcome and recommendation

Recommend **`w15b-exclude54-14801` for W15D's working-run decision**, carrying the changes below into W16B curation. This is a recommendation, not a selection or accepted subset. Do not combine clusters across runs.

| Condition | Active electrodes | Events | Clusters | Automated good | Automated mua |
| --- | ---: | ---: | ---: | ---: | ---: |
| `w15b-allchannels01` | 512 | 51,396 | 57 | 24 | 33 |
| `w15b-exclude54-14801` | 510 | 43,316 | 53 | 22 | 31 |

Both use the same unchanged 512-column binary, 3,000,000 samples, scientific settings, runtime and seed policy. Only sorter electrode inclusion and output identity differ. No temporal mask or quality censoring was applied. [Checkpoint metadata](../../../configs/extra4_shank2_sensitivity.v1.json) pins the configurations, reports and audits. See the [comparison report](../../../results/extra4_shank2/w15b-comparison01/index.html), [visual supplement](../../../results/extra4_shank2/w15b-visual-review01/index.html), [control baseline](../../../results/extra4_shank2/w15b-control-review01/index.html) and [exclusion baseline](../../../results/extra4_shank2/w15b-exclusion-review01/index.html).

## Benefits and limits

W14 established persistent channel-specific compromise: b148/global353 has 91.9860% padded-guard coverage and b54/global872 has 52.5713%. Four control b148-peaking mua clusters (16, 17, 18, 20) contain **9,313 events**, with sorter contamination estimates of 89.4-103.6%. Their 10-second count profiles rise and fall together, with long quiet intervals. Best exclusion matches have Dice overlap only 0.006-0.061; they must not be interpreted as the same neurons. Raw averages show structure, including some neighbor support. Disappearance does not prove every event is an artifact.

Only 1,277 of those 9,313 events overlap b148's padded guard: most detections occur outside its flat intervals. Guard overlap alone would miss much of this compromised-channel population. The net decrease of 8,080 events is not an artifact-removal count. Control c5 peaks on b54 (30 events, five guard overlaps); its weak best match is exclusion c5 (43 events, Dice 0.192). Testing both exclusions together does not isolate their individual causal contributions.

All 24 control automated-good clusters have candidate counterparts with common-channel raw-mean correlation >=0.951; 19 have Dice >=0.9. No control good cluster peaks on an omitted electrode. These are encouraging preservation screens, not proof of identity or complete recovery. Means share matched events and are not independent confirmations.

## Changed populations for curation

These are **cross-run correspondences**, not within-run merge proposals.

| Control → exclusion | Events | Label | Dice | Follow-up |
| --- | --- | --- | ---: | --- |
| c6 → c6 | 134 → 95 | good → mua | 0.716 | Similar waveform (correlation 0.972), but only 82 matched events. Investigate sensitivity loss/redistribution near b54. |
| c30 → c27 | 926 → 1,025 | good → mua | 0.894 | Similar waveform (0.979); contamination estimate rises from 0 to 28.3%. Review added events, refractory structure and competitors. |
| c41 → c38 | 352 → 366 | good → mua | 0.933 | Similar waveform (0.969); contamination estimate rises from 0 to 71.4%. Strong time overlap does not settle single-unit quality. |
| c42 → c39 | 170 → 158 | mua → good | 0.793 | Similar waveform (0.954); improved label is not acceptance. |

Thus 24→22 good labels includes three good-to-mua and one mua-to-good candidate; it does not establish loss of two neurons. Other lower-overlap good candidates include c19→c17 (0.811), c29→c26 (0.831) and c9→c9 (0.899). All 110 condition-specific clusters remain in the inventory and await full curation.

## Quality exposure and unresolved channels

| Event annotation | Control | Exclusion |
| --- | ---: | ---: |
| Template-peak guard | 1,309 | 22 |
| Any guard on the same 510 common electrodes | 7,308 (14.22%) | 7,074 (16.33%) |
| At least half of those common electrodes guarded | 12 | 14 |
| Full-2048-channel broad warning | 28 | 20 |
| Tight warning | 7 | 3 |
| Coincidence assessment unavailable | 24 | 27 |
| Incomplete +/-100-sample context | 8 | 9 |

Peak-guard burden depends on surviving clusters/electrodes. The baseline any-active-guard count falls from 40,518 to 7,074 partly because two channels are omitted. The fixed-common-electrode comparison avoids this mechanical effect and shows **no general improvement in the proportion of events exposed to remaining-channel guards**. Fixed exposure is 543,840 samples for common-any and 1,759 for common-half. All annotations remain diagnostic; no events are censored.

Generic shared-signal warning assessment is unavailable. Coincidence warnings retain their 2048-channel population; warnings and flat guards are not automatic artifact labels. Other compromised channels remain, including b10/global168 and b367/global301 with W14 guard burdens around 14%. Exclusion c0 peaks on b10 (492 events, mua); c43 peaks on b367 (one boundary event, mua). No broader exclusion or universal cutoff is adopted.

## Implementation and validation

Reused W15A's runner/baseline tools unchanged. Added comparison generator, independent validator and matching/condition tests. Four runner/comparison tests passed, including matching against dynamic programming and exact geometry/exclusion identity. Both sorter postchecks passed with input pins unchanged and settings matched.

Baseline audits verified all 94,712 events, 110 cluster rows, 440 quarter rows and 4,686 raw excerpts. The comparison audit independently reconstructed **8,967 full-channel raw windows**, checked **940 overlapping cluster pairs**, 110 cluster inventories and four fixed quality masks. [Comparison checks](../../../results/extra4_shank2/w15b-comparison-validation01/checks.json) pin the report. Pairwise +/-2-sample matches can reuse events across candidate pairs; do not sum these as unique recovered populations. Correlations use 12 common channels nearest either template peak and offsets -20 through +40 samples.

Visually reviewed both control-good correspondence summaries, all four b148 target/neighbor/time-count panels and detailed c16→c18, c6→c6, c30→c27, c41→c38 and c42→c39 figures. The supplement plots audited saved means/counts. Other generated pair pages remain for later curation; this is not visual acceptance of every cluster.

Shank0 release, shank1 baseline, W14 evidence, source data, original labels and archives remain unchanged. No shank3 sort was performed. Next: W15C's documented shank3 matched comparison and shared-episode diagnostics, followed by W15D working-run selection.
