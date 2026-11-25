# Windows Kilosort4 roadmap

Updated: 2026-11-24. This is the single current tracker. **W17 is complete: reviewed four-shank extra_4 release v1 contains 41 accepted putative units and 62,048 analysis events. All 186 selected-run clusters are accounted for; 89 holds remain deferred and 56 are withheld. The agreed release milestone is achieved.**

## Current state and decisions

| Scope | Current state | Authoritative evidence |
| --- | --- | --- |
| Shank0 (first shank) | Selected `w7b-exclude248-01`: 58 original clusters. Accepted v1: 11 putative units / 18,252 derived events. Other 38 hold and nine withhold proposals remain outside the subset, with original labels/events preserved. | [Working run](../../configs/extra4_shank0_working_run.json), [W12 ledger](../reviews/2026-11-24-w12-curation-ledger.csv), [adopted policy](../../configs/extra4_shank0_analysis_policy.v1.json), [W13 freeze](../../configs/extra4_shank0_release.v1.json) |
| Shank1 | Selected all-channel run: 11,324 events / 33 clusters (7 automated good, 26 mua). Accepted v1: 5 putative units / 9,816 derived events. 13 holds deferred; 15 withheld. | [W15A record](rounds/2026-11-24-06-w15a-shank1-baseline.md), [result metadata](../../configs/extra4_shank1_baseline.v1.json) |
| Shank2 | Selected exclusion of b54/global872 and b148/global353. 53 clusters (22 good, 31 mua). Accepted v1: 17 putative units / 27,537 derived events. 19 holds deferred; 17 withheld. | [W16B record](rounds/2026-11-24-11-w16b-shank2-curation.md), [proposal checkpoint](../../configs/extra4_shank2_curation_w16b.proposed.json) |
| Shank3 | Selected b259-exclusion run: accepted v1 has 8 putative units / 6,443 events. Shared core/shoulder omitted with matching exposure. 19 holds deferred; 15 withheld. | [W16C record](rounds/2026-11-24-12-w16c-shank3-curation.md), [proposal checkpoint](../../configs/extra4_shank3_curation_w16c.proposed.json) |
| Shared episodes | Shank3 shared-flat core totals 7.2005 nominal seconds, with a marked detection deficit in both conditions; excluding b259 does not repair it. W16D adopts core/shoulder exclusion for shank3 only; no universal clipping-percentage cutoff. | [W14 shared-episode findings](../reviews/2026-11-24-w14-input-channel-review.md#shared-episodes-are-a-separate-concern) |

**Decision boundary:** The selected runs remain fixed in the [run registry](../../configs/extra4_working_runs.v1.json). The user separately accepted the 30 putative units and the W16D analysis policy, recorded in [accepted v1](../../configs/extra4_shanks123_curated_v1.json). Historical W16A/B/C and W16D proposal files remain unchanged. The [accepted ledger](../reviews/2026-11-24-w16d-accepted-curation-ledger.csv) records 30 accepted, 51 deferred holds and 47 withheld; no merge or source relabeling. Automatic good labels are not curated neurons. Shank0's W12 acceptance remains unchanged.

Latest record: [W17 presentation revision 2](rounds/2026-11-24-16-w17-report-revision.md), [revised report](../../results/extra4/w17-report-revision02/index.html), [presentation provenance](../../configs/extra4_report_revision02.json). Scientific release remains unchanged. Previous [W17 four-shank release](rounds/2026-11-24-15-w17-four-shank-release.md), [release report](../../results/extra4/w17-release-v1/index.html), [release metadata](../../configs/extra4_release.v1.json), [all-cluster ledger](../reviews/2026-11-24-w17-four-shank-ledger.csv). Previous [W16D accepted derived revision](rounds/2026-11-24-14-w16d-accepted-derived.md), [derived report](../../results/extra4/w16d-curated-v1/index.html), [provenance](../../configs/extra4_shanks123_derived_v1.json). Previous [W16D acceptance proposal](rounds/2026-11-24-13-w16d-acceptance-proposal.md), [acceptance report](../../results/extra4/w16d-proposal01/index.html), [exact policy](../../configs/extra4_w16d_acceptance.proposed.json). Previous [W16C full shank3 review](rounds/2026-11-24-12-w16c-shank3-curation.md), [all-cluster ledger](../reviews/2026-11-24-w16c-shank3-proposal-ledger.csv), [checkpoint report](../../results/extra4_shank3/w16c-checkpoint01/index.html). Previous [W16B full shank2 review](rounds/2026-11-24-11-w16b-shank2-curation.md), [all-cluster proposal ledger](../reviews/2026-11-24-w16b-shank2-proposal-ledger.csv), [checkpoint report](../../results/extra4_shank2/w16b-checkpoint01/index.html). Previous [W16A shank1 review](rounds/2026-11-24-10-w16a-shank1-curation.md). Prior [W15D checkpoint](rounds/2026-11-24-09-w15d-working-run-checkpoint.md) retains its pending-at-the-time wording. Planning history: [post-W14 plan](rounds/2026-11-24-04-extra4-release-plan.md) and [original W9-W17 plan](rounds/2026-11-23-08-extra4-roadmap-plan.md). Older records describe their own date and scope, not current pending work.

<a id="planned-rounds-extra_4-through-a-full-recording-checkpoint"></a>
<a id="proposed-next-milestone-reviewed-four-shank-extra_4-release-v1"></a>

## Completed milestone: reviewed four-shank extra_4 release v1

The user accepted this sequence after W14. Achieved at W17: a selected run per analyzed shank, a decision/reason for every output cluster, explicitly accepted putative-unit subsets and analysis policies, and combined event/unit tables and summaries on the original sample axis. Reuse shank0's frozen v1. Review coverage, not a target neuron count, determines completion.

| Round | Bounded work | Exit condition |
| --- | --- | --- |
| W15A - Complete: reusable runner and shank1 baseline | Parameterize verified input/probe/settings/output identity; validate against shank0's run contract and mapping expectations. Sort shank1 with all 512 channels and generate baseline quality annotations and diagnostics. | Verified first new-shank sort; complete provenance; no transfer of pilot cluster IDs or hard-coded counts. |
| W15B - Complete: shank2 sensitivity | Following explicit condition authorization, compare all channels with exclusion of b54/global872 and b148/global353, keeping settings matched. Review waveform support, population redistribution and artifact exposure rather than optimizing the automatic-good count. | Evidence-backed working-run recommendation; document benefits, losses and unresolved channels. |
| W15C - Complete: shank3 sensitivity and shared episodes | Compare all channels with exclusion of b259/global2045 if authorized. Evaluate detections and preprocessing around W14's shared flat episodes, plus cluster stability away from them. | State whether a usable working result is supported; distinguish channel-specific and shared-episode problems. No automatic temporal mask. |
| W15D - Complete: working runs selected | Reconcile the three baseline/comparison reports and present one run recommendation per shank, with any further diagnostic experiment justified explicitly. Record the user's selections separately from cluster acceptance. | Intermediate milestone: a documented working-run set ready for curation, or a named shank deferred with its reason and next experiment. |
| W16A - Complete: reusable curation and shank1 proposals | Generalize pilot review/report tools and verify transferred calculations against shank0 reference outputs. Review all shank1 good/mua clusters, focused competitors, raw support, temporal stability and artifact exposure. | Full shank1 proposal ledger; no automatic-good-as-neuron shortcut. |
| W16B - Complete: shank2 proposals | Review every cluster in the selected shank2 run using the validated tools; prioritize altered populations and remaining channel-quality concerns. | Full shank2 proposal ledger with accept-as-putative, hold and withhold reasons. |
| W16C - Complete: shank3 proposals and exposure review | Review every selected-run cluster with explicit attention to shared episodes, local event concentration and waveform/temporal support. | Full shank3 proposal ledger; identify whether annotation-only handling is sufficient for each proposed analysis or further evidence is needed. |
| W16D - Complete: accepted subsets, policies and derived v1 | Present concrete per-shank subsets and exposure policies for explicit acceptance. Then create versioned derived tables, rasters, rates, waveform/amplitude summaries and omission/quality records. | Accepted revisions with preserved original identities and auditable denominators; proposals remain separate from adopted decisions. |
| W17 - Complete: combined release and reproducibility audit | Combine accepted shank0-3 revisions; check common time axis, run-qualified identities, mapping, counts, flags and manifests; replay derived summaries and issue a recording-wide report. | Reviewed extra_4 release v1, with accepted units, all-cluster ledgers, holds/withholds, quality limitations and reproducible provenance. |

Allow approximately **nine substantive working rounds**, not necessarily nine chats. W16A-C may split into screening and focused follow-up once cluster counts are known; W16D may split at acceptance. **W15D is the earlier checkpoint:** working-run recommendations/decisions ready for curation.

If W15C or W16C cannot support a defensible shank3 result, add a bounded diagnostic/sensitivity round. Preserve original inputs and baselines, state the hypothesis and validate any proposed intervention and its exposure consequences. Other shanks can proceed independently. A result omitting unresolved shank3 is partial; a fully reviewed shank may legitimately yield no accepted units, with explicit reasons.

Release requires complete cluster accounting, explicit subset/policy acceptance, checked mapping/time/counts, quality availability distinguished from clean data, matching event/exposure denominators and reproducible provenance. Do not infer cross-shank neuron uniqueness or complete neuron recovery.

## Next work

No additional sorting or curation round is automatically scheduled. Use the accepted release for a separately scoped analysis, or return to held clusters in a later focused review. Any unit/policy changes require a new accepted revision; preserve v1. Generated artifacts still require separate backup outside Git.

## Implementation references and boundaries

Use independent sorting per shank and the verified separate 512-channel binaries. Keep binary width and original sample axis intact when omitting electrodes in the sorter. The [W13 expansion procedure](extra4-expansion.md) is a **frozen design snapshot**; its future-tense W14 statements are superseded by the [W14 input/quality contract](../WINDOWS_QUALITY.md#w14-remaining-shank-input-and-quality-contract). W15A implemented the [configuration-driven runner and baseline contract](../WINDOWS_QUALITY.md#w15-configuration-driven-sorting-and-baseline-contract); W16A implemented and validated the [generalized curation evidence contract](../WINDOWS_QUALITY.md#w16a-generalized-curation-evidence-contract). Existing pilot scripts must not be applied to another shank by changing paths alone.

The [Windows quality reference](../WINDOWS_QUALITY.md) owns scientific methods and output definitions; [Windows setup](windows-setup.md) owns environments/storage; [the detector guide](../CUSTOM_PIPELINE_WINDOWS.md) owns imported Mac execution and sidecar semantics. Preserve full-2048-channel coincidence definitions when projecting annotations onto individual shanks. Accepted W16D policies apply only to their versioned subsets; they are not automatically transferred to future units.

Scope remains extra_4's four shanks. extra_5/extra_6, stimulation-specific handling, SpikeInterface adoption, cross-recording neuron matching and biological synchrony conclusions are deferred.

## Completed checkpoints and history

| Checkpoint | Evidence |
| --- | --- |
| Independent Windows root and preserved worker | [Consolidation](rounds/2026-11-22-02-project-consolidation.md) |
| FAISS repair with Windows protections retained | [Runtime repair](rounds/2026-11-22-03-windows-dll-repair.md); active locks/runtime instructions in Windows setup |
| Historical all-channel pilot and matched control/exclusion sorts | [W7B findings](../reviews/2026-11-23-w7b-sensitivity-findings.md); reference runs are not the accepted subset |
| Shank0 reviews and accepted derived subset | [W12 findings](../reviews/2026-11-24-w12-curated-subset.md), [W13 release audit](../../results/extra4_shank0/w13-release01/index.html) |
| Remaining-shank input and quality review | [W14 findings](../reviews/2026-11-24-w14-input-channel-review.md) |

Detailed older counts, diagnostic thresholds and pending-at-the-time recommendations remain in their dated findings/rounds. They are not repeated here as competing status summaries.
