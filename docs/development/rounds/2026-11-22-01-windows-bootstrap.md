# W1 — Independent Windows bootstrap and pilot quality workflow

Date: 2026-11-22. State: bootstrap/recovery validated; report implemented and validated for extra_4/shank0; scientific curation pending.

Created a new checkout at `C:\Projects\invivo_extracellular_data_analysis\windows-kilosort` from the supplied bundle, preserving HEAD `92da0b2c30c70132a8cd4f44a6bb545e59fc463f`, master and common history. Removed the bundle-path origin. The parent transfer directory and original worker remain separate. No commit/push was made. Updated ownership, setup, current tracker and contract; the supplied handoff is preserved under `handoffs/windows-kilosort-independent/`.

Recovery verified the 6,144,000,000-byte input SHA-256 `11cd033eb0bda858f7598123a795f198078cc227d98d92543e8ea88f9e12eff0`, frozen return archive SHA-256 `087ba85cb9c195a9e1b401b8dc0f46d1969537e0f728addde33a72cc0f4df73d`, and all 169 payload files. The ZIP was copied and extracted into ignored `worker_returns/extra4_shank0/pilot01/`; the binary remains in place. The live worker was read only. Original automated labels and output arrays were not modified.

Reused worker `.venv` Python 3.12.10; `pip check` passed. No environment installations, GPU reruns or export repetitions. Ported the original review script into versioned `scripts/review_units.py`, with explicit paths, fresh-output guards, all-cluster plots, curation queue, exposure screens, HTML and hashed provenance. Original script identity and adaptation are documented in SCRIPT_PROVENANCE. Recovered readable settings replace pickled ops loading; archived drift evidence remains the reference.

## Validation and findings

Executed report at `results/extra4_shank0/pilot01-review01/`: 39,620 final events, 59 clusters, 24 automated good/35 mua, 16 clusters below 100 events. All 59 metric rows exactly match the frozen CSV. Array/sample/mapping checks passed; 39,695 pre-dedup events and 75 removed duplicates confirmed without applying the mask again. All 169 recovered payload hashes still match after report execution. Report hashes, four delivery-manifest hashes and copied environment-lock identity pass. Existing recovery/report paths and attempted report output inside the evidence tree are rejected. Evidence and outputs are Git-ignored.

Generated 15 pages covering every cluster. Visual inspection this round covered pages for clusters 32–35 and 56–58 (not every generated page). Clusters 34/35 retain localized negative-going templates, central ACG troughs and stable amplitude bands; cluster 58 has one boundary event and no meaningful ACG evidence. These observations do not establish curated identities. The original report supplies broader prior diagnostic observations.

The high-variability screen again covers 12 nominal seconds/120,000 samples, containing 1,665 events (about 4.20% of events in 4% of exposure). Cluster 34 has 209/4,679 events and cluster 35 has 182/3,887 in those windows. This coarse overlap is insufficient evidence for blanket exclusion. Outside-screen rates use the corresponding 288-second nominal denominator and do not imply artifact-free exposure. Five boundary-screen events remain preserved; clusters 37 and 58 each consist of one such event. Similar-template candidates remain 31/33 and 45/48; no merge is justified by similarity alone.

## Decisions and next step

Retain the unchanged baseline. Defer new sensitivity sorting until targeted raw-waveform/pair/feature review identifies a specific hypothesis; do not adopt artifact removal from aggregate screens. Human curation and scientific acceptance are pending. The report queue includes original labels and blank decisions; future revisions require reviewer/date, rationale, evidence and explicit ID mappings for merges.

The current report is pilot-scoped, not arbitrary-recording software. Other-shank and extra_5 data are not present in the supplied worker. Expansion requires those sources and pilot acceptance. Downstream curated burst/timing analyses should follow the curation decision; full-exposure uncurated rates and spatial summaries are already available. See the single [roadmap](../roadmap.md) for current priorities.
