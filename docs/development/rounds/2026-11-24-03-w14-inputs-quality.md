# W14 - Verified remaining-shank inputs and channel-quality review

Date: 2026-11-24. State: implemented and validated inputs; proposed channel decisions. No sorting or scientific adoption of exclusions.

Created fresh exact-cast Windows exports for shanks1-3 under `data/w14-extra4-inputs01`, with maps, probes and manifests. Readback and separate reusable preflights verify all 4.608 billion values against the full source. Recorded all-channel quality statistics, exact-flat/padded intervals and per-second/quarter distributions, agreeing with native Mac guards on all 1,536 channels. [Findings and proposals](../../reviews/2026-11-24-w14-input-channel-review.md) own this round's conclusions; [input/proposal metadata](../../../configs/extra4_remaining_shanks_w14.proposed.json) pins evidence.

Shank1 supports an all-channel baseline. Propose matched exclusion tests for shank2 b54/global872 and b148/global353, and shank3 b259/global2045. Shank3 also has 7.2005 nominal seconds with at least half its channels exactly flat; a channel exclusion alone is insufficient to resolve that distinct issue. No clipping-percentage cutoff, temporal mask or clean-channel claim was adopted.

Six tests passed. Independent audit checked 1,536 channel totals, 460,800 temporal cells and ten raw/neighbor examples against source/legacy masks. Visually reviewed 14 final figures. Fresh report revisions corrected rendering problems without changing numerical payloads. Fixed mojibake and stale W13 completion wording in the current tracker using explicit UTF-8; did not alter checksum-pinned historical documentation or manifests.

```powershell
.venv\Scripts\python.exe -m unittest tests.test_artifact_review tests.test_w14_inputs tests.test_shank_input
.venv\Scripts\python.exe scripts/prepare_w14_inputs.py export --output data/w14-extra4-inputs01
.venv\Scripts\python.exe scripts/prepare_w14_inputs.py quality --output results/extra4/w14-quality01
.venv\Scripts\python.exe scripts/review_w14_channels.py --inventory results/extra4/w14-quality01 --inputs data/w14-extra4-inputs01 --output results/extra4/w14-review03
.venv\Scripts\python.exe scripts/validate_w14_review.py --output results/extra4/w14-validation03
```

Separate `shank_input.py` preflights were run for each shank with the source hash, corresponding exported binary/hash, 3,000,000 samples and `results/extra4_shankN/w14-input-audit01` output. Exact hashes and paths are in the tracked metadata. Choose new output paths for repeats. The validation script is scoped to these W14 inventory/report identities; the exporter core and W13 preflight support all four shanks. Large data/results remain ignored by Git.

Next: W15A generalized runner and shank1 baseline, then staged matched conditions for shanks2/3 with their distinct artifact questions. Original data, accepted shank0 artifacts, source/worker history and frozen release unchanged. No commit or push performed.
