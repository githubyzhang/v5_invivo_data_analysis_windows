# W16C - Full shank3 curation and shared-exposure review

Date: 2026-11-24. State: **reviewed proposals, not accepted units or analysis policy**. Shank3 is the fourth physical shank. The user authorized this round after committing and pushing W16B. The selected run remains `w15c-exclude25901`; no runs are mixed.

## Outcome

Reviewed all 42 clusters and preserved all 17,666 original events (14 automated good / 28 mua). The [checkpoint report](../../../results/extra4_shank3/w16c-checkpoint01/index.html) links the evidence and the [complete ledger](../../reviews/2026-11-24-w16c-shank3-proposal-ledger.csv) records every proposal, reason, original label, quarter support and quality counts.

| Proposal | IDs | Clusters | Original events |
| --- | --- | ---: | ---: |
| Putative candidates | 5, 10, 14, 16, 20, 26, 30, 34 | 8 | 6,453 |
| Hold | 0, 1, 2, 3, 4, 7, 8, 11, 12, 13, 15, 19, 21, 22, 23, 24, 25, 31, 32 | 19 | 11,163 |
| Withhold from subset | 6, 9, 17, 18, 27, 28, 29, 33, 35, 36, 37, 38, 39, 40, 41 | 15 | 50 |
| Total | 0–41 | 42 | 17,666 |

All eight candidates are automated good. Six other good and 13 mua clusters remain held; 15 mua clusters are withheld. Withhold means insufficient support for this subset, not proof that all events are artifacts. Acceptance fields remain false. These are original counts, not filtered accepted events.

## Identity and waveform findings

Candidates retain localized raw waveforms through all four original-time quarters and the away-quarter review. Their eight-neighbor guard-clear mean correlations to the all-event reference range approximately 0.980–0.998. This sensitivity supports waveform persistence; it does not establish clean time or exhaustive isolation. All eight have zero adjacent intervals below 20 samples in the original output. c34's positive-leading waveform is not rejected on polarity. c26 remains supported despite changed cross-run membership; no missing control events are imported.

**c1/c2 remain held without merging.** They have stable but different same-peak mean shapes and separated features on ten shared PC channels. Their common control population and unresolved split interpretation remain relevant. The bounded evidence supports populations but does not settle whether both should enter the conservative unit subset. A common control origin alone is not proof of one neuron. Six c2 short intervals show two troughs, while other c2 examples lie on clipping and shared ramps. A future focused identity review could revise these holds.

**c12/c13 remain held without merging.** Their raw mean correlation is about 0.901, peak identity is shared, and seven-channel feature tails overlap. c13's stable quarters and automated good do not settle the split; its exception examples include a flat peak with neighbor troughs and shared ramps.

**c15 is held for an unexplained feature subgroup.** Its main cloud separates from c16 in the six-channel projection, but a detached c15 subgroup remains unattributed. Stable quarter means do not resolve that subgroup. The three short intervals and 14 peak-guard events add disclosed event-quality concerns; no claim that the subgroup is a second neuron or an artifact is made. c16 retains independent waveform/refractory support. No split or merge is applied.

c10/c11 have different footprints and separated features; c11 still lacks sufficient single-unit confidence. c30/c31 overlap in the limited feature projection but have very different raw footprints (correlation about 0.079); c31's Q and background variability remain unresolved. c21 has only 70 events, with 25/26/9/10 by quarter and weaker late support. c25 has only 29 events and no Q1 events, with limited overlapping features against c24. Both remain held despite good labels. The ledger records the remaining sparse, elevated-R/Q and boundary concerns individually.

## Shared episodes and the analysis boundary

The fixed W15C shared-flat core is reconstructed from W14 source intervals: at least 256 of the original 512 channels flat simultaneously. It spans **72,005 samples / 7.2005 nominal seconds**. The diagnostic +/-500-sample expansion adds **9,555 samples / 0.9555 seconds** of shoulder. Away exposure is **2,918,440 samples / 291.844 seconds**. These definitions are diagnostic, not adopted censoring rules.

The selected run has 17 core events (c2:14, c16:1, c30:2), 24 shoulder events and 17,625 away events. The observed core rate is about 2.36 events/s versus 60.39 away. Together with W15C's source and saved-preprocessing evidence, this is an observability limitation, not evidence of biological silence. Excluding channel259 did not repair the shared signal loss.

The [exposure supplement](../../../results/extra4_shank3/w16c-exposure01/index.html) computes every cluster's matching count and denominator for all time, away time, away plus peak guard-clear time, and away plus eight-neighbor guard-clear time. The eight nearest active physical channels are a diagnostic neighborhood, not a measured unit footprint. Selection uses event centers; waveform windows can cross mask boundaries. Partial disturbances remain outside the shared core. No variant is claimed to recover a true firing rate.

Across the eight candidates: **26 peak-guard events, 4,233 any-active-guard events, ten half-active-guard events, one broad warning, zero tight warnings, two unavailable coincidence assessments and zero incomplete raw contexts**. Three events lie in the shared core and seven in its shoulder. Flags overlap and cannot be added as unique artifacts. Any-active guard often concerns distant electrodes. Full-2048-channel coincidence semantics are retained; generic shared assessment remains unavailable and is not confused with this explicit W15C mask.

The [exception packet](../../../results/extra4_shank3/w16c-exceptions01/index.html) covers all 16 adjacent intervals below 20 samples and all 97 peak-guard events. It shows both localized troughs in padded guards and compromised flat/clipped or shared-ramp contexts. Six of 113 excerpts are incomplete: one short-interval boundary example and five peak-guard examples. Negative annotations do not prove clean data.

**Annotation-only handling is sufficient for preserving exploratory, explicitly flagged observations and this proposal review. It is insufficient for unqualified full-duration biological firing rates or silence claims.** W16D must present concrete event/exposure rules with matched denominators and sensitivity limits before derived summaries are accepted. No mask, removal, merge, new unit subset or transfer of shank0 policy is adopted here. Unresolved units can remain held without blocking a conservative shank3 subset; another GPU sort is not required to finish this proposal checkpoint.

## Implementation and validation

Reused the unchanged W16A curation builder/validator and W16B exception extractor. Added the dated exposure and checkpoint recipes:

```powershell
.venv\Scripts\python.exe scripts/curation_review.py --shank 3 --output results/extra4_shank3/w16c-review01
.venv\Scripts\python.exe scripts/validate_curation_review.py --report results/extra4_shank3/w16c-review01 --output results/extra4_shank3/w16c-validation01
.venv\Scripts\python.exe scripts/review_curation_exceptions.py --report results/extra4_shank3/w16c-review01 --output results/extra4_shank3/w16c-exceptions01
.venv\Scripts\python.exe scripts/review_w16c_exposure.py --output results/extra4_shank3/w16c-exposure01
.venv\Scripts\python.exe scripts/checkpoint_w16c.py --output results/extra4_shank3/w16c-checkpoint01
```

These identify completed packets; reruns require fresh output paths. The independent evidence audit passed 42 unit rows, 168 quarters, 28 pairs and **17,626 raw windows**, plus frozen shank0 replay (15 units, 60 quarters, 58 labels). Exception scalar readback passed 113 excerpts. Exposure raw readback passed **13,391 windows**; fixed masks reproduce W15C exactly. The checkpoint independently recomputes **126 event-count/exposure comparisons** through sorted interval unions and search, rather than the exposure generator's full-sample Boolean arrays. It also verifies cluster accounting and original quarter totals. These checks validate calculations, not scientific certainty.

Visual coverage: all seven cluster screens, six away-quarter screens, two short-ISI pages and 13 peak-guard pages. All 28 pair metric rows were reviewed numerically; 12 pair figures were visually inspected: c1/2, c0/2, c0/3, c12/13, c15/16, c10/11, c21/22, c24/25, c25/26, c30/31, c14/16 and c19/20. Other generated pair figures are available but not represented as individually inspected. The competitor screen remains bounded.

The [methods reference](../../WINDOWS_QUALITY.md#w16c-shared-exposure-sensitivity) owns output semantics. [Checkpoint metadata](../../../configs/extra4_shank3_curation_w16c.proposed.json) pins scripts, manifests, this record, the ledger and accepted run registry. Original data, sorter outputs, prior checkpoints and archives remain unchanged. Generated results remain outside Git and require separate preservation.

## Next

**W16D:** prepare concrete shank1–3 unit subsets and event/exposure policy proposals, with counts and denominators for user acceptance before generating adopted derived revisions. Shank1 proposes five candidates, shank2 17 and shank3 eight; none is newly accepted. Shank0's accepted 11-unit release remains frozen. Remaining holds do not imply those neurons are absent and are not silently promoted or discarded.
