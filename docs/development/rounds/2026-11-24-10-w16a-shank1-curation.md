# W16A - Selected working runs and full shank1 curation proposals

Date: 2026-11-24. State: **working runs accepted; shank1 review complete; unit decisions remain proposals**. Shank numbers are zero-based (shank1 is the second physical shank).

## Accepted run set

The user said: “I accept these three runs for continued curation.” The new [accepted registry](../../../configs/extra4_working_runs.v1.json) records shank1 `w15a-allchannels01`, shank2 `w15b-exclude54-14801` and shank3 `w15c-exclude25901`, with checked source-manifest hashes. The W15D proposal, audit and earlier metadata retain their historical state. This acceptance selects one run per shank; it does not accept clusters, mix alternative runs, adopt masks or change shank0's frozen release.

## Complete shank1 accounting

The [checkpoint report](../../../results/extra4_shank1/w16a-checkpoint01/index.html) and [33-row proposal ledger](../../reviews/2026-11-24-w16a-shank1-proposal-ledger.csv) cover every original cluster, including all 7 automated good and 26 mua clusters. Each ledger row preserves original label, event count, explicit reason, quality availability and review reference. All acceptance fields remain false.

| Proposal | Cluster IDs | Clusters | Original events |
| --- | --- | ---: | ---: |
| Putative candidates | 1, 4, 7, 11, 23 | 5 | 9,816 |
| Hold | 3, 5, 6, 8, 9, 10, 15, 16, 17, 24, 27, 28, 29 | 13 | 1,471 |
| Withhold from proposed subset | 0, 2, 12, 13, 14, 18, 19, 20, 21, 22, 25, 26, 30, 31, 32 | 15 | 37 |
| Total | All original IDs 0–32 | 33 | 11,324 |

These event counts are original observations, not a filtered accepted event table. Withholding means insufficient support for inclusion in this putative-unit proposal, not proof of artifact or absence of neuronal activity. No merge, relabeling or event removal was applied.

The five candidates have reproducible localized raw waveforms across all four equal recording quarters, supportive automated refractory statistics and no compelling merge requirement in the bounded competitor review. Quarter-to-pooled correlations on eight channels range approximately 0.965–0.990. Counts can vary over time: c4's quarter counts are 313/538/568/668. Waveform stability is not a claim of stationary firing or complete isolation.

Two automated-good clusters remain held. **c9/c10** have similar raw means (correlation 0.905), seven shared physical PC channels and partly overlapping features; the sparse cross-event histogram cannot settle a possible split. Hold both; do not merge. **c24** has stable raw support but two adjacent event pairs only 3 and 4 samples apart. Raw inspection leaves duplicate/collision attribution unresolved. Its distinct footprint relative to c23 does not resolve those within-cluster events. c23 remains a candidate; c24 is conservatively held pending event-policy review.

The mua cluster **c5** is promising: 295 events, reproducible positive waveform and four-quarter support. It remains held because its automated confidence criterion fails (Q approximately 0.277); polarity alone is not a rejection criterion. Sparse **c16/c17** also have similar waveforms (correlation 0.861) and overlapping features, with too few events to settle identity. Other sparse clusters have explicit individual reasons in the ledger. Boundary-only c2/c18/c30 cannot supply complete raw excerpts.

## Review coverage and quality limits

All six screen pages were visually inspected, covering every cluster's raw support, quarter means, amplitude over time and autocorrelogram. All 21 selected pair metrics were inspected numerically; focused pair figures inspected visually were c1/c3, c6/c7, c9/c10, c10/c11, c16/c17 and c23/c24. This is a bounded competitor screen, not exhaustive proof of isolation. Within-run pair comparisons here assess possible split populations; W15B/C compared alternative runs.

All seven within-cluster adjacent intervals below 20 samples were inspected in [raw context](../../../results/extra4_shank1/w16a-short-isi01/short_isi.png). Besides c0, c24 and c28, c4 and c7 each have one 14-sample interval and c23 one 18-sample interval. These residual exceptions remain disclosed for the proposed candidates; no claim is made that every event is clean. The short-ISI packet saves exact indices, raw excerpts, independent scalar readback checks and its reconstruction recipe.

Baseline annotations remain diagnostic. Across all 11,324 events there are 15 broad and four tight coincidence warnings, 18 events lacking that assessment, no template-peak guard events and 16 events overlapping any active-channel guard. Generic shared-signal assessment is unavailable, not negative. Full-2048-channel coincidence definitions remain intact. Incomplete raw context affects six events, including the three boundary-only clusters. No annotation-based censoring, clean-duration denominator or shank0 policy is adopted for shank1.

## Implementation and validation

The [methods contract](../../WINDOWS_QUALITY.md#w16a-generalized-curation-evidence-contract) documents `curation_review.py` and `validate_curation_review.py`. The evidence builder resolves the accepted registry, verifies source identities and generates all-cluster/quarter evidence plus bounded competitor pairs. It reuses pinned pilot PC/cross-lag helpers with explicit physical-channel mapping; missing evidence stays unavailable.

The [independent audit](../../../results/extra4_shank1/w16a-validation01/checks.json) passed: 33 cluster rows, 132 quarter rows, 21 pairs and 10,285 raw windows checked. Independent scalar source reads verify selections and raw values; brute-force cross-lag reconstruction checks time-pair calculations, and physical-channel PC reconstruction checks saved projections. Transfer validation exactly reproduces 15 frozen shank0 waveform reviews, 60 quarter summaries and all 58 shank0 automated labels/criteria. All 33 shank1 labels are also reproduced. This validates the transferred calculations, not biological identity or all historical scientific decisions.

[Checkpoint metadata](../../../configs/extra4_shank1_curation_w16a.proposed.json) pins the scripts, accepted registry, ledger, this record and result manifests. Generated results remain local ignored artifacts and require their usual separate preservation; Git alone does not back them up. Original data, source run labels/events, historical manifests and accepted shank0 release remain unchanged.

## Continuation

Next is **W16B: review all 53 clusters in selected shank2**, prioritizing changed populations and remaining channel-quality concerns. W16C covers shank3 and its shared episodes. W16D presents concrete subsets and analysis policies for explicit acceptance before building derived summaries. W16A does not ask for early acceptance of these five candidates.
