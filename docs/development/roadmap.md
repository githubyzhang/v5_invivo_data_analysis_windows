# Windows Kilosort4 roadmap

Updated: 2026-11-24. This is the single current tracker. **W16C is complete: all 42 shank3 clusters have proposals (8 putative candidates, 19 holds, 15 withheld). Shanks1–3 now have complete proposal ledgers. Next: W16D, concrete subset and event/exposure policy proposals for acceptance.** No new-shank unit subset or analysis policy has been accepted.

## Current state and decisions

| Scope | Current state | Authoritative evidence |
| --- | --- | --- |
| Shank0 (first shank) | Selected `w7b-exclude248-01`: 58 original clusters. Accepted v1: 11 putative units / 18,252 derived events. Other 38 hold and nine withhold proposals remain outside the subset, with original labels/events preserved. | [Working run](../../configs/extra4_shank0_working_run.json), [W12 ledger](../reviews/2026-11-24-w12-curation-ledger.csv), [adopted policy](../../configs/extra4_shank0_analysis_policy.v1.json), [W13 freeze](../../configs/extra4_shank0_release.v1.json) |
| Shank1 | Selected all-channel run: 11,324 events / 33 clusters (7 automated good, 26 mua). W16A proposes 5 putative candidates, 13 holds and 15 withheld; none accepted. | [W15A record](rounds/2026-11-24-06-w15a-shank1-baseline.md), [result metadata](../../configs/extra4_shank1_baseline.v1.json) |
| Shank2 | Selected exclusion of b54/global872 and b148/global353. 53 clusters (22 good, 31 mua). W16B proposes 17 putative candidates, 19 holds and 17 withheld; none accepted. | [W16B record](rounds/2026-11-24-11-w16b-shank2-curation.md), [proposal checkpoint](../../configs/extra4_shank2_curation_w16b.proposed.json) |
| Shank3 | Selected b259-exclusion run: W16C proposes 8 putative candidates, 19 holds and 15 withheld. Shared signal-loss exposure remains a policy concern; none accepted. | [W16C record](rounds/2026-11-24-12-w16c-shank3-curation.md), [proposal checkpoint](../../configs/extra4_shank3_curation_w16c.proposed.json) |
| Shared episodes | Shank3 shared-flat core totals 7.2005 nominal seconds, with a marked detection deficit in both conditions; excluding b259 does not repair it. No temporal mask or universal clipping-percentage cutoff adopted. | [W14 shared-episode findings](../reviews/2026-11-24-w14-input-channel-review.md#shared-episodes-are-a-separate-concern) |

**Decision boundary:** The user explicitly accepted shank1 `w15a-allchannels01`, shank2 `w15b-exclude54-14801` and shank3 `w15c-exclude25901` for continued curation. The [accepted run registry](../../configs/extra4_working_runs.v1.json) records this decision separately from the frozen W15D proposal. Runs are not mixed. Run selection and cluster acceptance remain separate: W16A's shank1, W16B's shank2 and W16C's shank3 ledgers contain proposals only. W16D presents concrete subsets and analysis policies for acceptance. Automatic `good` labels are not curated neurons. Shank0's W12 acceptance remains unchanged.

Latest record: [W16C full shank3 review](rounds/2026-11-24-12-w16c-shank3-curation.md), [all-cluster ledger](../reviews/2026-11-24-w16c-shank3-proposal-ledger.csv), [checkpoint report](../../results/extra4_shank3/w16c-checkpoint01/index.html). Previous [W16B full shank2 review](rounds/2026-11-24-11-w16b-shank2-curation.md), [all-cluster proposal ledger](../reviews/2026-11-24-w16b-shank2-proposal-ledger.csv), [checkpoint report](../../results/extra4_shank2/w16b-checkpoint01/index.html). Previous [W16A shank1 review](rounds/2026-11-24-10-w16a-shank1-curation.md). Prior [W15D checkpoint](rounds/2026-11-24-09-w15d-working-run-checkpoint.md) retains its pending-at-the-time wording. Planning history: [post-W14 plan](rounds/2026-11-24-04-extra4-release-plan.md) and [original W9-W17 plan](rounds/2026-11-23-08-extra4-roadmap-plan.md). Older records describe their own date and scope, not current pending work.

<a id="planned-rounds-extra_4-through-a-full-recording-checkpoint"></a>
<a id="proposed-next-milestone-reviewed-four-shank-extra_4-release-v1"></a>

## Next milestone: reviewed four-shank extra_4 release v1

The user accepted this sequence after W14. Target: a selected run per analyzed shank, a decision/reason for every output cluster, explicitly accepted putative-unit subsets and analysis policies, and combined event/unit tables and summaries on the original sample axis. Reuse shank0's frozen v1. Review coverage, not a target neuron count, determines completion.

| Round | Bounded work | Exit condition |
| --- | --- | --- |
| W15A - Complete: reusable runner and shank1 baseline | Parameterize verified input/probe/settings/output identity; validate against shank0's run contract and mapping expectations. Sort shank1 with all 512 channels and generate baseline quality annotations and diagnostics. | Verified first new-shank sort; complete provenance; no transfer of pilot cluster IDs or hard-coded counts. |
| W15B - Complete: shank2 sensitivity | Following explicit condition authorization, compare all channels with exclusion of b54/global872 and b148/global353, keeping settings matched. Review waveform support, population redistribution and artifact exposure rather than optimizing the automatic-good count. | Evidence-backed working-run recommendation; document benefits, losses and unresolved channels. |
| W15C - Complete: shank3 sensitivity and shared episodes | Compare all channels with exclusion of b259/global2045 if authorized. Evaluate detections and preprocessing around W14's shared flat episodes, plus cluster stability away from them. | State whether a usable working result is supported; distinguish channel-specific and shared-episode problems. No automatic temporal mask. |
| W15D - Complete: working runs selected | Reconcile the three baseline/comparison reports and present one run recommendation per shank, with any further diagnostic experiment justified explicitly. Record the user's selections separately from cluster acceptance. | Intermediate milestone: a documented working-run set ready for curation, or a named shank deferred with its reason and next experiment. |
| W16A - Complete: reusable curation and shank1 proposals | Generalize pilot review/report tools and verify transferred calculations against shank0 reference outputs. Review all shank1 good/mua clusters, focused competitors, raw support, temporal stability and artifact exposure. | Full shank1 proposal ledger; no automatic-good-as-neuron shortcut. |
| W16B - Complete: shank2 proposals | Review every cluster in the selected shank2 run using the validated tools; prioritize altered populations and remaining channel-quality concerns. | Full shank2 proposal ledger with accept-as-putative, hold and withhold reasons. |
| W16C - Complete: shank3 proposals and exposure review | Review every selected-run cluster with explicit attention to shared episodes, local event concentration and waveform/temporal support. | Full shank3 proposal ledger; identify whether annotation-only handling is sufficient for each proposed analysis or further evidence is needed. |
| W16D - Acceptance and derived summaries | Present concrete per-shank subsets and exposure policies for explicit acceptance. Then create versioned derived tables, rasters, rates, waveform/amplitude summaries and omission/quality records. | Accepted revisions with preserved original identities and auditable denominators; proposals remain separate from adopted decisions. |
| W17 - Combined release and reproducibility audit | Combine accepted shank0-3 revisions; check common time axis, run-qualified identities, mapping, counts, flags and manifests; replay derived summaries and issue a recording-wide report. | Reviewed extra_4 release v1, with accepted units, all-cluster ledgers, holds/withholds, quality limitations and reproducible provenance. |

Allow approximately **nine substantive working rounds**, not necessarily nine chats. W16A-C may split into screening and focused follow-up once cluster counts are known; W16D may split at acceptance. **W15D is the earlier checkpoint:** working-run recommendations/decisions ready for curation.

If W15C or W16C cannot support a defensible shank3 result, add a bounded diagnostic/sensitivity round. Preserve original inputs and baselines, state the hypothesis and validate any proposed intervention and its exposure consequences. Other shanks can proceed independently. A result omitting unresolved shank3 is partial; a fully reviewed shank may legitimately yield no accepted units, with explicit reasons.

Release requires complete cluster accounting, explicit subset/policy acceptance, checked mapping/time/counts, quality availability distinguished from clean data, matching event/exposure denominators and reproducible provenance. Do not infer cross-shank neuron uniqueness or complete neuron recovery.

## Implementation references and boundaries

Use independent sorting per shank and the verified separate 512-channel binaries. Keep binary width and original sample axis intact when omitting electrodes in the sorter. The [W13 expansion procedure](extra4-expansion.md) is a **frozen design snapshot**; its future-tense W14 statements are superseded by the [W14 input/quality contract](../WINDOWS_QUALITY.md#w14-remaining-shank-input-and-quality-contract). W15A implemented the [configuration-driven runner and baseline contract](../WINDOWS_QUALITY.md#w15-configuration-driven-sorting-and-baseline-contract); W16A implemented and validated the [generalized curation evidence contract](../WINDOWS_QUALITY.md#w16a-generalized-curation-evidence-contract). Existing pilot scripts must not be applied to another shank by changing paths alone.

The [Windows quality reference](../WINDOWS_QUALITY.md) owns scientific methods and output definitions; [Windows setup](windows-setup.md) owns environments/storage; [the detector guide](../CUSTOM_PIPELINE_WINDOWS.md) owns imported Mac execution and sidecar semantics. Preserve full-2048-channel coincidence definitions when projecting annotations onto individual shanks. No quality-based censoring is automatically transferred to new units.

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
