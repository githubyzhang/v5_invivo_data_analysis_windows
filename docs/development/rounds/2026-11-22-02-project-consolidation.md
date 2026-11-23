# W2 — Project history review and one-root Windows consolidation

Date: 2026-11-22. State: file/runtime migration validated; prior scientific results preserved; Kilosort execution blocked by Windows policy.

## Recovered understanding of the project

Reviewed the Mac investigation ledger, adopted decisions, methods, documentation map, worker-preparation round and experiment contract, independent handoff, Windows RUN_REPORT, worker tracker and post-return viewer round. The record distinguishes completed engineering work from scientific acceptance:

| Stage | Established progress | Limits and availability here |
|---|---|---|
| Mac detector research | MA50 baseline subtraction; adaptive MAD thresholds adopted, fixed-reference option retained. User reviewed 42 selected examples: 38 plausible, three uncertain, one likely artifact. | Selected examples do not establish population accuracy. Flat guards are proxies; shared-warning coverage is only 35/300 seconds. |
| Mac full-recording delivery | extra_4: 115,992 candidates; extra_5: 173,029, across 2,048 channels. Validated saved-candidate pipeline, viewer schema and descriptive activity report. | Counts are electrode candidates, not sorted units. Full source HDF5 files, extra_5 outputs and most historical reports were not transferred. The worker includes the all-channel extra_4 candidate reference. |
| Windows pilot | Verified lossless export of extra_4/shank0; Kilosort 4.1.7 on RTX 5090; 39,620 final events, 59 clusters (24 automated good, 35 mua). Full 300 nominal seconds and 512 channels retained. | No curation or confirmed neuron identities. Two-sample sorter deduplication and sparse clusters constrain short-interval interpretation. Other shanks/extra_5 were not sorted. |
| Later worker viewing | Phy 2.1.0/Qt5 and Kilosort Qt6 GUI installed and visually checked, with a separate Phy playground and local conventions. | This work happened after the frozen return ZIP. Preserving only that ZIP would have lost later viewer setup and documentation. No curation was recorded. |
| Independent Windows bootstrap | Verified return/binary and ported repeatable diagnostics, all-cluster plots, pending curation queue and provenance. | Current report is pilot-scoped; targeted raw/feature review and scientific acceptance remain pending. |

The shared data contract remains unchanged: authoritative integer samples, nominal 10,000 Hz/physical 10,080 Hz, original binary/global mappings and 30 micrometre pitch. No stimulation causality, calibrated voltage, complete neuron recovery or cross-recording matching is established. Mac detector defaults are historical references, not sorter defaults.

## Consolidation

The active Git checkout was moved from the temporary nested `windows-kilosort` directory directly into `C:\Projects\invivo_extracellular_data_analysis`. HEAD, master, uncommitted work and no-remote state were preserved. The original delivery remains ignored under `get_started/`.

Before relocating the worker, recorded SHA-256 and length for **127,447 files / 18,301,773,103 bytes**, including its approximately 6 GB Git history, environments, data, outputs, viewer workspace and later docs. The complete worker now lives under ignored `worker_returns/worker-snapshot/`. A directory move stopped on protected files; a preservation copy completed it. The full snapshot exactly matched the initial manifest. Every remaining source file was then independently checked against that manifest before the old sibling folder was removed. No directory link or dependency on the old location remains.

Copied the raw binary to root `data/` and config/geometry to `configs/pilot01/`, verifying their byte identities. Rebuilt root `.venv`, `.venv-gui`, `.venv-phy` against local `.python`, copying installed distributions offline and regenerating launchers, activation paths and the GUI dependency .pth. All package lists match the returned locks. The complete original environments remain unchanged in the snapshot as historical evidence; do not execute those path-frozen copies.

Copied the later Phy playground and viewer assets into ignored root `viewing/`. Updated only its working params.py, guide and compatibility launcher. Added versioned root launch buttons and adapted Kilosort launcher with new exploration outputs. Original baseline labels, results, configs, manifests and archive remain untouched. Current setup/viewer docs and AGENTS.md carry forward operating and computer-use cleanup conventions.

## Validation and outstanding issue

- All 169 frozen-return payloads and the 6,144,000,000-byte raw binary match expected SHA-256. Full worker snapshot equality passed before deletion.
- Three local environments pass pip check and exactly match their saved dependency lists. Active launch/activation files contain no old worker path.
- Root-local report regeneration succeeded at `results/extra4_shank0/pilot01-review02-local`; every cluster metric row equals the frozen review, and report hashes pass.
- All 34 inherited tests passed. Their Mac plotting-cache default produced a fallback warning; Windows setup now supplies an explicit local MPLCONFIGDIR for those tests without changing scientific code.
- CUDA matrix computation passes on RTX 5090. Qt6 imports pass. Phy CLI and model load all 39,620 events/59 clusters and retrieve finite `(3,61,512)` raw waveform samples using root data. GUI rendering was not rechecked visually.
- **Kilosort imports fail:** Windows Smart App Control rejects FAISS `_swigfaiss.pyd` in both the original and new environments. Code Integrity events 3033/3077 confirm a signing/policy block. An approved outside-sandbox check fails identically. This is not a new data/path failure. No security setting, upstream library or dependency version was changed to bypass it. The Kilosort GUI/new sorting await resolution of that policy/trusted-package issue; CPU diagnostics and Phy remain usable.

Detailed local evidence: `results/migration-2026-11-22/worker-before.json`, `snapshot-copy.log`, and `verification.json`. Historical absolute paths inside original reports/manifests and archived environments remain preserved as provenance, not operational instructions. Nothing was committed or published.

## Next

Resolve the FAISS system-policy issue before new Kilosort execution. Continue targeted Phy/raw-feature review and explicit curation revisions; no baseline rerun is needed. Expansion still requires other-shank/extra_5 source data and pilot acceptance. The [roadmap](../roadmap.md) remains the single current tracker; [setup](../windows-setup.md) owns actual paths and commands.
