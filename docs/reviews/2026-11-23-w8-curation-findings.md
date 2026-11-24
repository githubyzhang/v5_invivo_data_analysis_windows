# W8 — Focused curation checkpoint

State: AI-assisted review completed; explicit recommendations prepared for human scientific acceptance. No original labels, events, masks or primary baseline changed. This is a bounded checkpoint, not exhaustive curation of all clusters.

## Working-result recommendation

Recommend using `w7b-exclude248-01` as the working run for continued focused curation, retaining the full-channel control and frozen pilot as permanent references. This avoids relying on the persistently anomalous b248 channel while retaining the four promising populations. It is not a claim that exclusion improves every unit, nor adoption of the entire output as a validated neuronal population. Expansion to other shanks and full-population activity analysis remain premature.

Recommend retaining exclusion clusters **6, 10, 32 and 33 as putative single-unit candidates** in a future explicitly accepted curated subset. Their historical/control counterparts are 5, 12, 34 and 35. These are four reviewed candidates, not a total neuron count or ground-truth neuron identification. The [proposal ledger](2026-11-23-w8-curation-proposals.csv) covers every exclusion cluster plus control cluster 36, pins the exact source arrays, and records `proposed_not_applied` and human decision `pending`. Units outside the focused acceptance scope are not rejected.

## Evidence for the four candidates

Fourteen targeted exclusion-run pair reviews examine neighboring/high-template-similarity competitors and changed populations. Raw pair means use the same physical channels for both clusters. Stored PC indices are mapped through the 511-channel map before selecting common physical channels. Balanced joint PCA is descriptive and does not constitute a formal isolation-distance estimate.

| Exclusion cluster | Historical/control | Targeted competitors | Quarter-to-pooled central raw correlation | Recommendation |
| --- | --- | --- | --- | --- |
| 6 | 5 | 5, 3 | 0.9835–0.9892 | Putative single-unit candidate |
| 10 | 12 | 11 | 0.9676–0.9850 | Putative candidate; feature comparison has limited shared coverage |
| 32 | 34 | 29, 33 | 0.9703–0.9915 | Putative candidate; retain coupling caveat |
| 33 | 35 | 31, 32 | 0.9689–0.9836 | Putative candidate; retain prior internal-structure caveat |

All four retain narrow multichannel raw deflections across four 75-nominal-second quarters. Baseline slopes/tails vary, especially for 32, and are not grounds to claim identical full waveforms throughout. W7B supplies strong cross-run event agreement, low estimated contamination and retained automated good labels. W8 adds local competitor and within-run stability evidence; neither independently proves complete spike recovery or absence of contamination.

Cluster 6 separates from tested neighbors in common-channel features despite raw similarities. Cluster 10 has a distinct raw footprint from 11; only two common feature channels are available, and their two-dimensional projections overlap, so that projection alone cannot establish isolation. Cluster 32 separates from 29 and 33 in the tested features. Its cross-correlogram with 29 has a sharp lagged peak; do not infer a merge, a synaptic connection or artifact truth from this uncorrected pair histogram. Cluster 33 separates from tested neighbors, but retains internal feature structure analogous to the prior cluster-35 review; W5 did not support a split. No new split is justified here.

## Held populations and structural decisions

No merge or split is recommended from this checkpoint.

- Exclusion **0/1/2**: tested feature populations separate, but the cross-run redistribution and isolation concerns remain. Cluster 1's newly good label does not by itself justify adding it to the curated subset. Cluster 2 has estimated contamination R=0.3846 and remains held. Similar raw means do not imply that 0 and 2 should merge.
- **24/25**: only 59/89 events; raw/feature differences and sparse cross-event evidence do not support a merge. Cluster 24 remains low-count/unresolved despite a zero contamination estimate.
- **31**: contains almost the combined old 31/33 event population: 236 of their 237 combined events match within two samples to its 237 events (Dice 0.9958). This is an observed sorter consolidation, not an accepted biological merge. Hold its single-unit interpretation. It is unrelated to the weak old-36-to-new-31 ranking discussed in W7B.
- **44**, particularly versus **43**: overlapping feature structure and 49 cross-event pairs within two samples warrant dedicated overlap/duplicate review. R=0.2210 fails the automatic threshold. Do not merge or declare all such coincidences duplicates.
- **46/47**: similar raw shapes but separated tested feature populations; no merge supported. Cluster 46 remains held with R=0.32.
- **48/45**: similar raw waveforms, partially separated/overlapping low-count features and sparse cross-timing evidence do not justify a merge. Cluster 48 remains held; its R=3.2 is a relative estimator, not a literal 320% probability.
- Exclusion **35/54/57** each have only a sample-2 event. Recommend withholding these boundary-only clusters from future unit summaries while retaining every original event.
- Control **36** remains held for b248 dependence and absence of a convincing exclusion-run counterpart. This does not prove that every original event is artifact.

## Why automatic good falls from 24 to 19

The installed Kilosort 4.1.7 label calculation was reproduced for all **117 clusters across both runs**. It requires more than 10 events with nonzero time span, then **R < 0.2 and Q < 0.2**. R is the correlogram-based relative contamination estimate; Q is the algorithm's refractory-evidence statistic. Rounded `ContamPct` alone does not determine the label.

| Control → exclusion candidate | R before → after | Q before → after | Interpretation |
| --- | --- | --- | --- |
| 1 → 1 | 0 → 0 | 0.2771 → 0.1410 | Q crosses into good |
| 2 → 2 | 0.1956 → 0.3846 | both pass | R crosses out of good; population also changes |
| 26 → 24 | 0 → 0 | 0.1587 → 0.3176 | Q fails despite 59 events in each run and zero R |
| 44 → 44 | 0 → 0.2210 | both pass | R fails |
| 45 → 46 | 0.1653 → 0.3200 | both pass | R fails |
| 49 → 48 | 0 → 3.2000 | 0.1865 → 0.9590 | Both fail; low-count population changes |

Using W7B's highest-ranked candidate relations, five old good populations point to mua candidates, old 31 and 33 point to a single good candidate 31, and old mua 1 points to newly good candidate 1. This accounts for **24 − 5 − 1 + 1 = 19** automatic labels. It is bookkeeping of observed candidates, not proof that those relations identify neurons or that five neurons were lost. `good_label_accounting.csv`, `label_criteria.csv` and `old31_33_correspondence.json` preserve the evidence.

## What this checkpoint does and does not authorize scientifically

The concrete proposal is a preferred run for continued review and a four-candidate putative subset, with held, boundary-only and unreviewed populations explicitly distinguished. Human acceptance remains pending; original `cluster_KSLabel.tsv`/`cluster_group.tsv` files are untouched. Even an accepted putative subset would not establish a complete neuron count, validated firing-rate exposure during shared flat segments, or neuron identity across recordings.

Retain the Mac-derived flags as review annotations. No blanket coincidence rejection, whole-shank guard union, temporal censoring or denominator adjustment is recommended. Shared-flat and global-coincidence intervals remain separate phenomena. SpikeInterface remains deferred.

After accepting or revising this ledger, the next concrete work is a derived candidate-level summary for the chosen subset, retaining original sample indices, warning flags and explicit full-recording versus observable-time limitations. Further isolation/overlap work on held populations can extend that subset separately. Do not make other-shank expansion depend on an inflated automated-good count.

## Validation and artifacts

The [local report](../../results/extra4_shank0/w8-checkpoint01/index.html) contains all 18 visually reviewed figures, pair/quarter metrics, source-bound proposals and the working-run recommendation. Independent checks reread 9,617 raw windows (20,726,316 values including repeated pair/quarter windows), verify exact saved waveforms and quarter means, reconstruct physical-channel feature projections and brute-force all 14 cross-lag lists. Both run manifests and the full raw binary remain unchanged. Six existing tests for reused pair/PCA/matching helpers pass. The [quality contract](../WINDOWS_QUALITY.md#w8-focused-curation-checkpoint) owns execution and schema.
