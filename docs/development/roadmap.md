# Windows Kilosort4 roadmap

Updated: 2026-11-22. This is the single current tracker. The repository, data, runtimes and viewers live directly under `C:\Projects\invivo_extracellular_data_analysis`. The DLL blocker is resolved in the active environments. Latest evidence: [Windows runtime repair](rounds/2026-11-22-03-windows-dll-repair.md); prior [consolidation](rounds/2026-11-22-02-project-consolidation.md). Commands and paths: [Windows setup](windows-setup.md).

## Adopted direction

Windows independently develops a Kilosort4-centered sorting and neural-activity workflow. Mac continues its custom detector and electrode-level analysis. Shared checkpoint: `92da0b2c30c70132a8cd4f44a6bb545e59fc463f`; Windows repository: independent clone, initially on `master`, with no remote. See `handoffs/windows-kilosort-independent/START_HERE.md` for contract and bootstrap.

## Current evidence

extra_4/shank0 baseline completed: 39,620 events / 59 clusters, 24 automated good and 35 mua. Transfer integrity checked on Mac and Windows. Bounded diagnostic review is complete; human curation and scientific acceptance remain pending. Full report, original outputs and locks remain in frozen return storage and the complete `worker_returns/worker-snapshot`. All 127,447 snapshot files match the pre-migration inventory. No extra_5 or other-shank sorting is established by this pilot.

Runtime repair validated: active FAISS 1.13.2 replaces the blocked 1.16.0 build. Kilosort 4.1.7 imports, exact-neighbor/graph checks, CUDA and offscreen GUI startup pass with Smart App Control enabled. Original evidence and locks retain 1.16.0; new active locks record 1.13.2. A scoped launcher adapter now enforces the intended local INI settings. No upstream package code, security policy or scientific defaults were changed; no sorting rerun or full-run equivalence claim.

## Next

1. Completed: independent root checkout, local runtime/data/viewers, complete preserved worker and repaired FAISS runtime. Keep active dependency locks distinct from the historical pilot, and use the root viewer launchers. New runs must record the changed FAISS version.
2. In progress: all 59 clusters have metrics and plots; pending curation queue preserves automated labels. Initial visual review covered new pages for clusters 32–35 and 56–58. Priorities remain 2, 5/12, 26/29, 34/35, boundary-only 37/58, pairs 31/33 and 45/48, and raw channel 248/global1921. Next: raw-waveform and pair/feature review in a separate working copy, then explicit human curation revisions. No relabeling or merge adopted.
3. Completed for this pilot: [quality contract](../WINDOWS_QUALITY.md) and [locally regenerated report](../../results/extra4_shank0/pilot01-review02-local/index.html). Sensitivity sorting is deferred pending targeted raw/feature review: current screens alone do not justify a masking or threshold change. Generalize the pilot-scoped script before applying it elsewhere.
4. Expand to other shanks/extra_5 once pilot review supports it and required data are available; retain independent per-recording identities.
5. Build downstream unit activity summaries with clear uncertainty and curated versus uncurated distinctions.

## Deferred / boundaries

No confirmed cross-recording neuron matching, universal artifact removal or complete neuron recovery. extra_6 and stimulation-period artifact handling remain separate future research. Shared artifact references cover only part of each recording. Preserve all source data and baseline outputs. Coordinate selected fixes/results with Mac without making either workflow depend on the other's milestones.
