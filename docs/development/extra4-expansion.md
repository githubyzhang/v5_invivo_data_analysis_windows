# extra_4 release and expansion procedure

W13 engineering gate, 2026-11-24: **go to W14 input preparation and channel-quality review**. The accepted shank0 v1 subset is frozen by [release metadata](../../configs/extra4_shank0_release.v1.json). This is a provenance freeze, not a filesystem permission change or a claim of complete neuron recovery. Original sorter files and the accepted W12 packet remain unchanged. Future revisions need new paths, explicit decisions and new manifests.

## Input and identity contract

Use `C:/DATA/cnea_data/invivo/26-11-06/0192/extra_4_signals.h5` read-only. Its full SHA-256 is `3bedaa51bca65205dcc81e25ef48f249c9f1ea34346f4cfd7327e26269bd9755`; `signals` is float16, channels × samples, `(2048,3000000)`. Do not infer source identity from a matching filename or header alone.

For W14, use **separate 512-channel binaries**, one per shank, as in the validated pilot: sample-major, little-endian float32, exact float16-to-float32 conversion, no additional scaling, filtering, interpolation, masking or resampling during export. Each full binary is 6,144,000,000 bytes; the three new binaries require 18,432,000,000 bytes plus workspace for sorting and review. Build to new partial paths, verify full readback and source identity, and publish a final manifest only after success. Keep failed/partial exports separate from ready inputs. The generalized Windows exporter itself remains W14 work; do not invoke the old Mac portable-worker packager.

`scripts/shank_input.py` provides reusable read-only validation for shanks 0–3. It compares every exported value against its source channel/sample and checks source/binary hashes before and after. It derives all four pad-ordered maps, independently agrees with the retained legacy LUT, and checks that all 2,048 global IDs occur exactly once. Its real-data validation in W13 covers shank0; synthetic tests cover all four shanks, reversal boundaries, channel-order corruption, truncated binaries and a final partial chunk.

Geometry is four columns × 128 rows, with 30 µm horizontal and vertical pitch. The legacy mapping reverses rows when the global column index exceeds 10; do not generate the other shanks by adding 512 to shank0 global IDs. `kcoords` in each new single-shank probe is the actual zero-based shank ID. `chanMap` remains local binary indices 0–511, and `n_chan_bin` stays 512 even when electrodes are excluded. Use the single-shank probe directly; do not also assume a different `shank_idx` convention. Preserve local binary index, global electrode ID, shank and physical coordinates in reports. There is no adopted cross-shank x offset or spatial deduplication rule.

Original integer sample indices are authoritative. Retain samples 0–2,999,999 on the same source axis in every export. Nominal sorting frequency remains 10,000 Hz; physical frequency is 10,080 Hz. Never mix these denominators or shift one shank's origin. The W12 analysis domain `[100,2999900)` provides complete ±100-sample raw windows; it is not a filter-settling claim. Apply a boundary policy to new derived results only with a documented review, keeping original events intact.

Example preflight after a W14 export (replace the binary hash with its independently recorded readback hash and choose a fresh output):

```powershell
.venv\Scripts\python.exe scripts/shank_input.py --source C:/DATA/cnea_data/invivo/26-11-06/0192/extra_4_signals.h5 --source-sha256 3bedaa51bca65205dcc81e25ef48f249c9f1ea34346f4cfd7327e26269bd9755 --binary data/extra4_shank1_float32.bin --binary-sha256 VERIFIED_EXPORT_SHA256 --shank 1 --samples 3000000 --output results/extra4_shank1/input-audit01
```

## Per-shank gates

| Stage | Required evidence before proceeding |
| --- | --- |
| W14 input preparation | Full source hash, complete mapping, finite values, exact full binary/source comparison, sample alignment, byte size, readback hash and fresh input manifest for each shank. |
| W14 channel-quality review | Examine all 512 channels: flat/zero fractions, exact-flat and padded-guard durations, time distribution, raw values and local neighbor support. Record global/local IDs and a reason for every proposed exclusion; identify brief shared episodes separately. |
| W15 sorting | Explicit channel-selection decision and hash-bound input; new condition/run path; resolved settings and runtime/environment provenance. Verify output channel map, positions, sample bounds, labels, event counts and manifest before comparison or curation. |
| W16 review | Cover every cluster from the selected run, including all automated mua. Review waveform support, refractory/isolation evidence, competitors, internal structure, temporal stability and artifact exposure. Use run-qualified IDs; holds are allowed. Prepare a complete reasoned ledger and seek explicit subset/policy acceptance. |
| W17 combined checkpoint | Accepted revision per shank, matching sample axes, full provenance, original counts and derived counts, quality availability and limitations. Combine distinct shanks; never combine alternative sorts of the same shank. Cross-shank neuron uniqueness is not assumed. |

There is **no automatic clipping-percentage exclusion threshold**. A large padded-guard fraction prioritizes inspection but is not proven unusable neuronal time. Propose exclusion for persistent raw-channel compromise supported by the waveform/value history and acquisition context; use a matched sensitivity sort when consequential uncertainty remains. Brief widespread episodes do not justify eliminating all affected channels. The shank0 channel248/global1921 decision does not transfer to local index248 elsewhere.

## Sorting and quality policy

The full settings in the frozen `results/extra4_shank0/w7b-exclude248-01/run_contract.json` are the engineering starting point, not just the small pilot config. Important values include `fs=10000`, `n_chan_bin=512`, `scale=1000000`, high-pass 300 Hz, `nt=61`, `nblocks=1`, CAR enabled and no sign inversion. Save the complete resolved settings, exclusion list, versions, script and installed sorter hashes, seed policy and GPU information for every fresh run. Settings suitability, including drift handling, must be checked on each shank; changes need an explicit rationale and a distinct condition. Do not silently inherit the Mac detector defaults or channel248 exclusion.

Kilosort performs its own preprocessing. The Mac quality sidecar supplies annotations, not replacement sorter input. Reuse extra_4 coincidence warnings from their full 2,048-channel population and project intervals by original sample time; do not recompute the same thresholds on 512 channels. Recompute/project per-channel guards using each shank's actual global IDs. Unknown warning coverage stays unknown. Generic shared signal warnings remain unavailable. Annotation-only handling is the starting proposal for new shanks, with sensitivity checks where required; shank0's human acceptance does not accept new units or policies automatically.

## Reuse boundaries and release verification

Generalized now: mapping/probe construction and full source-to-binary preflight. **Still pilot-specific:** `run_w7b.py`, W8–W12 review builders/validators and their hard-coded run, cluster, event-count and duration expectations. Preserve these as repeatable shank0 evidence. W15 must introduce a configuration-driven runner with per-run settings/probe/input contracts; W16 must adapt review/report builders and validate against the shank0 reference before using them elsewhere. Do not run the existing pilot scripts on new shanks by merely substituting a path.

W13 replay rebuilt W12 in `results/extra4_shank0/w13-replay01`, independently audited it, then applied the same plot-layout finalizer. All 38 compared payloads match byte-for-byte, including tables, NPZ waveform arrays and all 13 PNGs. HTML navigation and the manual visual-review record are excluded from replay equality; their original hashes are verified separately. Nine upstream/result manifests were checked. Current CUDA/FAISS operations and pinned sorter versions/source pass. W13 did not repeat GPU sorting: the W7B control-equivalence experiment remains the prior evidence, and GPU identity across different hardware/software is not promised.

The [W13 report](../../results/extra4_shank0/w13-release01/index.html) contains an all-58-cluster decision/reason table and machine-readable audit. It preserves historical reason wording while showing current acceptance status separately. The W12 ledger remains the authoritative accepted decision record.

All local result/data packets are ignored by Git. The tracked release record pins their identities; it does not contain or back them up. Reproducibility requires retaining these local artifacts, the source recording, the root environment/locks and the corresponding committed code.
