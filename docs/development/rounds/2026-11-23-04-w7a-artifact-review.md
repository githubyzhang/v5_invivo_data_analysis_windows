# W7A — All-channel guards and saved-preprocessing artifact review

Date: 2026-11-23. State: implemented and validated; scientific changes remain proposals.

Expanded the earlier 18-channel raw guard replay to all 512 pilot channels, matching both frozen and current-native detector intervals exactly. Added a fresh packet under `results/extra4_shank0/pilot01-w7a-reviewed`, three pilot-scoped generation/validation/detail scripts and three focused guard-boundary tests. The [findings](../../reviews/2026-11-23-w7a-artifact-findings.md) own interpretation and the proposed W7B comparison; the [quality contract](../../WINDOWS_QUALITY.md#w7a-all-channel-guard-and-saved-preprocessing-review) owns execution and schemas.

452 channels have some guarded time, but b248 alone has persistent coverage (79.7529%; next 0.8249%). A brief shared flat episode around nominal second 99 affects 451 other channels at some point, with 450 simultaneously exactly flat. This differs from the three global coincidence warnings, which cover 37 sorter events. Peak-channel guards cover 160; union 196, not an artifact count.

Reconstructed 12 selected windows using hash-verified saved Kilosort ops and the active CUDA runtime, without sorting. Historical preprocessing statistics for batches 0/16/49 match exactly in this execution (acceptance tolerance 1e-5). Visually reviewed the coverage figure, all 12 context figures and five event-detail figures. An exact-zero raw b248 excerpt contains a deflection after preprocessing, reinforcing the need for multichannel/raw support review rather than treating transformed-channel amplitude as direct electrode evidence.

Validation: all 169 frozen payloads and the full pilot binary unchanged before/after generation; both detector input files unchanged; 512 guard replays match; independent audit checks 6,150,144 raw values and the same number of reconstructed values, all selected event indices, all 7,769 saved maximal flat runs and count tracks. Three focused tests pass. The source-to-binary identity established in W6 is retained, not re-claimed from a new source-file scan. Current runtime: Kilosort 4.1.7, FAISS 1.13.2, Torch 2.11.0+cu128, RTX 5090.

The initial local packet `pilot01-w7a-artifacts` stopped after figures because the installed reader has no `close()` method. Replaced that cleanup call with object release and ran to a fresh destination; the incomplete packet is not authoritative. Tests initially exposed a historical Mac matplotlib-cache default; importing the diagnostic module before the historical helper avoided activating it during tests. Historical sources/environments were not edited.

Next proposed round: matched new all-channel control and b248-only exclusion sort, with preserved inputs, explicit environment provenance and common-channel/event-based comparison. No masking, label edits, unit acceptance, source edits, commits or pushes were performed.
