# W16B - Full selected-run shank2 curation proposals

Date: 2026-11-24. State: **reviewed proposals, not accepted units or analysis policy**. Shank2 is the third physical shank. The user authorized W16B after committing W16A; the previously accepted working-run registry remains unchanged.

## Outcome and complete accounting

Reviewed all 53 clusters in selected `w15b-exclude54-14801`, preserving its 43,316 original events and 22 good / 31 mua labels. The [checkpoint report](../../../results/extra4_shank2/w16b-checkpoint01/index.html) links the evidence; the [complete proposal ledger](../../reviews/2026-11-24-w16b-shank2-proposal-ledger.csv) gives each cluster's reason, original label, counts, quarter support and quality flags. Every acceptance field is false.

| Proposal | Cluster IDs | Clusters | Original events |
| --- | --- | ---: | ---: |
| Putative candidates | 1, 2, 3, 8, 9, 12, 15, 17, 18, 19, 20, 21, 22, 23, 25, 26, 41 | 17 | 27,539 |
| Hold | 0, 4, 5, 6, 7, 10, 11, 13, 14, 16, 24, 27, 28, 29, 30, 36, 37, 38, 39 | 19 | 15,738 |
| Withhold from proposed subset | 31, 32, 33, 34, 35, 40, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52 | 17 | 39 |
| Total | All IDs 0–52 | 53 | 43,316 |

All 17 candidates are automated good, but five other good clusters remain held. Fourteen mua clusters remain held; 17 mua clusters are withheld. This is a manual evidence proposal, not a conversion of automated labels. Withholding indicates insufficient support for this subset, not proof of artifact or absence of neuronal activity. Original event totals are not filtered accepted counts.

## Evidence behind the distinctions

Candidate clusters have reproducible localized raw waveforms through all four quarters, supportive refractory statistics and no compelling merge requirement in the bounded competitor review. Positive-dominant c3 is not rejected on polarity. Nonstationary counts or burst-shaped autocorrelograms alone are not artifact labels. Feature-space separation supports retaining distinct populations for pairs including c1/c2, c14/c15, c18/c21, c20/c21 and c25/c26; it is not proof of complete isolation. c14 is held for its own event-quality concerns even though it separates from c15.

**Changed W15B populations remain explicit.** c6 retains localized waveform support after 134 control events became 95 selected-run events, but Q approximately 0.240 and sparse quarter evidence leave confidence unresolved. c27 retains stable means but R approximately 0.283 after its good-to-mua change; c27/c28 feature tails overlap. Hold both without merging. c38's R approximately 0.714 and Q approximately 0.368, four short intervals and overlapping c37/c39 features do not support single-unit inclusion. c39's improved automated label does not resolve that overlap, its 158-event evidence limit, weaker third-quarter waveform support or a peak-guard ramp event. c17 and c26 retain selected-run candidate support despite lower cross-run correspondence; no missing events are imported from the control.

**Short-interval evidence changes some good-cluster proposals.** c10, c14 and c16 have stable means but unresolved three-sample event pairs on complex raw deflections. c14/c16 also have compromised raw contexts. They remain held pending attribution and an explicit event policy, consistent with treating shank1 c24 as unresolved. No universal minimum-ISI exclusion rule is adopted. c1's single eight-sample interval shows two troughs and remains a disclosed contamination concern within its otherwise supportive population evidence; it is not evidence that both events came from one neuron. Other candidate short intervals remain in the original events as well.

c4/c5 share a peak, similar means and overlapping features with sparse evidence and failed R/Q criteria; hold both, no merge. Stable means in c0, c11, c13, c24 and c30 do not resolve elevated contamination estimates or complex close events. c7, c29, c36 and c37 retain possible neuronal support with insufficient confidence. Sparse withheld populations generally lack reproducible compact morphology or temporal coverage. c32/c43 are boundary-only. c34 has one boundary event and two complete excerpts flat on the peak and its two nearest channels.

The c0/c1 cross-event histogram has a central peak despite distinct mean footprints. A [focused supplement](../../../results/extra4_shank2/w16b-coincidence01/coincidence.png) inspects all eight pairs within +/-2 samples on both peaks and neighbors. Shared raw deflections remain attribution-ambiguous. Available coincidence and guard flags are negative for these examples, which does not prove cleanliness. Retain this limitation for c1; neither biological synchrony, duplicate identity nor a merge follows from the uncorrected histogram. c0 stays held independently.

## Remaining quality concerns and policy boundary

The [exception packet](../../../results/extra4_shank2/w16b-exceptions01/index.html) covers all 71 adjacent intervals below 20 samples (two nominal milliseconds) and all 22 template-peak guard events. Raw inspection includes ramps, flat/clipped traces, flat neighbors accompanying localized troughs, and two incomplete boundary examples. Padded guard overlap does not mean every flagged event lacks a spike; absence of a guard does not establish clean data. b10/global168 remains compromised; removing b54/b148 did not repair other channels.

Across the proposed 17 candidates there are **16 short intervals, five peak-guard events, 4,591 any-active-guard events, ten half-active-guard events, ten broad warnings, one tight warning and 15 unavailable coincidence assessments**. Flags overlap and must not be summed as unique artifacts. Any-active guard often concerns electrodes other than the unit's peak. Generic shared-signal assessment remains unavailable. Full-2048-channel coincidence definitions are preserved.

Two candidate events have incomplete raw context (c3 and c21). Candidate peak-guard examples occur in c18, c21, c22 and c25; c22 has two. Thus candidate status does not accept all events or justify an unqualified clean-duration firing rate. W16D must resolve boundary and quality/event-exposure policy explicitly. No temporal mask, event removal, quality-denominator subtraction or transfer of shank0's adopted policy occurs here. No source labels or clusters are rewritten.

## Implementation, validation and coverage

Reused W16A's pinned curation builder and independent validator unchanged:

```powershell
.venv\Scripts\python.exe scripts/curation_review.py --shank 2 --output results/extra4_shank2/w16b-review01
.venv\Scripts\python.exe scripts/validate_curation_review.py --report results/extra4_shank2/w16b-review01 --output results/extra4_shank2/w16b-validation01
.venv\Scripts\python.exe scripts/review_curation_exceptions.py --report results/extra4_shank2/w16b-review01 --output results/extra4_shank2/w16b-exceptions01
```

These identify completed packets; reproduction requires fresh output paths. The [methods reference](../../WINDOWS_QUALITY.md#w16b-raw-exception-review) owns the new exception contract. [Independent evidence checks](../../../results/extra4_shank2/w16b-validation01/checks.json) passed for 53 clusters, 212 quarters, 37 pairs and **37,910 raw windows**, with replay of 15 frozen shank0 unit packets, 60 quarters and all 58 labels/criteria. All 53 shank2 automated labels also reproduce. Exception extraction independently rereads each channel for 93 snippets; two boundary snippets are explicitly uncentered. The eight coincidence snippets have scalar readback and a saved reconstruction recipe.

Visually reviewed all nine cluster screens, all nine short-ISI pages, all three peak-guard pages and the c0/c1 supplement. All 37 pair metric rows were reviewed numerically; 23 focused pair figures were visually reviewed, with exact IDs recorded in checkpoint `summary.json`. Other generated pairs are available but are not represented as individually visually reviewed. The competitor screen is bounded and cannot establish exhaustive isolation.

[Checkpoint metadata](../../../configs/extra4_shank2_curation_w16b.proposed.json) pins the accepted registry, scripts, ledger, this record and output manifests. The accounting audit checks every ledger identity, source label/count, quality field and quarter total. Original data, sorter outputs, W15B sensitivity evidence, shank0 release, W16A packet and archives remain unchanged. Git tracks the small provenance/decision files; generated results retain their separate storage requirement.

## Next

Proceed to **W16C**, reviewing every selected-run shank3 cluster with explicit attention to shared flat episodes and observability. W16D then presents concrete subsets and analysis policies for acceptance before creating derived tables. This round completes shank2 proposal coverage; it does not accept 17 neurons or settle every held population.
