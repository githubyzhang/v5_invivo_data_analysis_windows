# W15D - Working-run selection checkpoint

Date: 2026-11-24. State: **recommendation assembled and audited; explicit user selection pending**. The user's request to proceed with W15D authorizes reconciliation and preparation of this decision, not acceptance of future units or policies.

## Concrete decision

Recommend the following one-run-per-shank set for continued curation. Shank numbers are zero-based.

| Shank | Proposed run | Omitted binary / global channels | Events | Clusters | Automated good / mua |
| --- | --- | --- | ---: | ---: | --- |
| 1 (second shank) | `w15a-allchannels01` | None | 11,324 | 33 | 7 / 26 |
| 2 (third shank) | `w15b-exclude54-14801` | b54 / 872; b148 / 353 | 43,316 | 53 | 22 / 31 |
| 3 (fourth shank) | `w15c-exclude25901` | b259 / 2045 | 17,666 | 42 | 14 / 28 |

Total prospective curation workload: **128 clusters, 72,306 observed events, 43 automated good and 85 mua**. These are not accepted neurons or a combined curated release. Every cluster, including mua and sparse/boundary clusters, is retained in the curation inventory. No automatic label determines acceptance.

The [proposal](../../../configs/extra4_working_runs_w15d.proposed.json) records exact run identities, channel mappings and cluster-specific follow-up priorities. The [checkpoint report](../../../results/extra4/w15d-checkpoint01/index.html) links the [complete inventory](../../../results/extra4/w15d-checkpoint01/curation_inventory.csv) and [audit](../../../results/extra4/w15d-checkpoint01/checks.json). [Checkpoint metadata](../../../configs/extra4_w15d_checkpoint.v1.json) pins this round's artifacts.

Shank0 remains unchanged: selected `w7b-exclude248-01`, accepted v1 subset of 11 putative units / 18,252 derived events, with its original 58-cluster sorter output preserved. Its existing policy does not automatically apply to shanks1-3. The new inventory excludes shank0 because its acceptance ledger already exists.

## Why this set, and what selection does not settle

- **Shank1:** W14 found no persistent channel-specific exclusion target, and W15A supports proceeding from the all-channel baseline. All 33 clusters still need full review; c2, c18 and c30 lack complete raw context. There is no evidence-based need for an additional sensitivity sort before curation.
- **Shank2:** W15B supports omitting the two persistently compromised electrodes. The major b148-peaking control populations have weak exclusion correspondences, while control good populations have similar-waveform counterparts. Costs remain: exclusion c6 loses events relative to its control counterpart; c27 and c38 become mua with increased contamination estimates; c39 improves its automated label without becoming accepted. Remaining-channel guard exposure does not show a general improvement. Retain control runs as sensitivity evidence, not a second source of units to mix into this run.
- **Shank3:** W15C supports bounded curation from the b259-exclusion run, but not a claim of overall artifact improvement. Both conditions retain a major detection deficit during the 7.2005 nominal seconds of shared-flat core. Review exclusion c1/c2 jointly as a possible split, c26's changed population, sparse c25 and other temporal/quality concerns. Selecting this run does not validate whole-recording rates or adopt the diagnostic core/shoulder as an exposure mask. Away time is not guaranteed clean.

Authoritative observations remain in [W15A](2026-11-24-06-w15a-shank1-baseline.md), [W15B](2026-11-24-07-w15b-shank2-sensitivity.md) and [W15C](2026-11-24-08-w15c-shank3-shared-episodes.md). Priority notes in this inventory organize review; they are not accept/hold/withhold decisions. Unflagged clusters still require the complete review. Earlier automatic-good counts from alternative sorts are not additional units.

No additional GPU experiment is currently justified before choosing this curation set. Shank3 need not be deferred entirely: its bounded away-zone waveform support is sufficient to begin curation, while observability and exposure-policy conclusions remain unresolved. If W16C cannot support a defensible subset/policy, document that limitation and propose a specific diagnostic experiment or partial release; do not infer that a run choice guarantees a usable final unit set.

## Audit and preserved scope

`build_w15d_checkpoint.py` verifies the proposal's pinned W13/W15A-C checkpoints, recursively checks their manifests and referenced content, and reads original event arrays, channel maps and automated labels for the three proposed runs. It checks exclusions against global mapping, common 3,000,000-sample axis, nominal 10000 Hz and physical 10080 Hz, every baseline inventory count/label, unique run-qualified cluster identities and generated-inventory readback. Exact file/manifest counts and totals are saved in the audit. This is a provenance/accounting audit; earlier raw-waveform and annotation audits are retained rather than represented as newly replayed calculations.

No sorter was rerun, no cluster was merged or accepted, and no event was removed. Original data, prior outputs/labels, manifests, accepted shank0 release and archives are unchanged. Source/configuration paths remain within the independent project. The new packet is a proposal and bookkeeping inventory, not a derived accepted event table.

## Acceptance and continuation

The concrete remaining question is whether the user selects **all three named runs above for continued curation**, with these limitations retained. The documented W15D decision boundary requires explicit selection separate from implementation of the checkpoint. Until that reply, all new selection fields remain `proposed_awaiting_user`; no active accepted working-run registry is created.

On acceptance, retain this proposal and its audit, and write a separate accepted run-set record referencing the checked manifests. Do not rewrite frozen W15A-C metadata to imply earlier acceptance. Then proceed to W16A: validate generalized curation tools against shank0 references and review every shank1 good/mua cluster. W16B and W16C cover shanks2/3; W16D separately requests acceptance of concrete putative-unit subsets and per-unit analysis policies. W17 combines accepted revisions only.
