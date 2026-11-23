# Windows Kilosort4 roadmap

Updated: 2026-11-23. This is the single current tracker. Rounds 1 and 2 diagnostic pilot reviews are complete; scientific curation remains pending. Latest evidence: [Round 2 record](rounds/2026-11-23-02-pilot-review-round2.md), [findings/proposals](../reviews/2026-11-23-kilosort-round2-findings.md), and [reviewed packet](../../results/extra4_shank0/pilot01-round2-reviewed/index.html). Next is the curation/observability decision checkpoint, especially the inherited per-channel clipping guard. The DLL blocker remains resolved. Commands and paths: [Windows setup](windows-setup.md).

## Adopted direction

Windows independently develops a Kilosort4-centered sorting and neural-activity workflow. Mac continues its custom detector and electrode-level analysis. Shared checkpoint: `92da0b2c30c70132a8cd4f44a6bb545e59fc463f`; Windows repository: independent clone, initially on `master`, with no remote. See `handoffs/windows-kilosort-independent/START_HERE.md` for contract and bootstrap.

## Current evidence

extra_4/shank0 baseline completed: 39,620 events / 59 clusters, 24 automated good and 35 mua. Transfer integrity checked on Mac and Windows. Bounded diagnostic review is complete; human curation and scientific acceptance remain pending. Full report, original outputs and locks remain in frozen return storage and the complete `worker_returns/worker-snapshot`. All 127,447 snapshot files match the pre-migration inventory. No extra_5 or other-shank sorting is established by this pilot.

Runtime repair validated: active FAISS 1.13.2 replaces the blocked 1.16.0 build. Kilosort 4.1.7 imports, exact-neighbor/graph checks, CUDA and offscreen GUI startup pass with Smart App Control enabled. Original evidence and locks retain 1.16.0; new active locks record 1.13.2. A scoped launcher adapter now enforces the intended local INI settings. No upstream package code, security policy or scientific defaults were changed; no sorting rerun or full-run equivalence claim.

## Next

1. Completed: independent root checkout, local runtime/data/viewers, complete preserved worker and repaired FAISS runtime. Keep active dependency locks distinct from the historical pilot, and use the root viewer launchers. New runs must record the changed FAISS version.
2. Round 1 complete for 34/35, 5/12, 2, 26/29 and 37/58: 1,373 complete raw windows independently checked, all target figures reviewed, nine traceable proposals saved. 34/35/12 remain promising; 5 needs further neighboring-cluster isolation review; 2 is held for isolation concerns; 26/29 are low-count/unresolved. Propose withholding boundary-only 37/58 from future unit summaries, without deleting their events or changing labels. All proposals await human acceptance.
3. Round 2 complete: seven pair comparisons, cluster-35 structure, all 12 high-variability seconds and b248/source/guard review. No merge or split is supported; 5/6 separate more clearly in multichannel features; 2 and sparse clusters remain held. b248 is 60.9167% exactly zero and otherwise negative, matching the full original HDF5 channel. The historical ≥10-sample flat + ±500-sample per-channel guard matches raw replay on 18 channels; it covers 79.7529% of b248 and 131/339 cluster-36 event centers. Propose holding cluster 36 pending investigation. Next: review proposals with the user and define a Kilosort-specific observability policy; do not automatically transfer an electrode detector mask to sorted units or apply its whole-shank union. A named bad-channel sensitivity experiment is justified for consideration, with matched repaired-environment controls to separate FAISS and channel-selection effects. No mask, exclusion, rerun or curation is adopted.
4. Completed for this pilot: [quality contract](../WINDOWS_QUALITY.md) and [all-cluster baseline diagnostics](../../results/extra4_shank0/pilot01-review02-local/index.html). Generalize the pilot-scoped scripts before applying them elsewhere.
5. Expand to other shanks/extra_5 once pilot review supports it. User located full recordings at `C:\DATA\cnea_data\invivo\26-11-06\0192`; extra_4/5/6 signals headers match `(2048, 3000000)` float16. Full source identity/hash checks remain pending before export. Retain independent per-recording identities; see [source setup](windows-setup.md#source-recordings-located-on-windows).
6. Build downstream unit activity summaries with clear uncertainty and curated versus uncurated distinctions.

## Deferred / boundaries

No confirmed cross-recording neuron matching, universal artifact removal or complete neuron recovery. extra_6 and stimulation-period artifact handling remain separate future research. Shared artifact references cover only part of each recording. Preserve all source data and baseline outputs. Coordinate selected fixes/results with Mac without making either workflow depend on the other's milestones.
