# W12 — Accepted v1 subset and derived summaries

Date: 2026-11-24. State: explicitly accepted by the user, implemented, validated and visually reviewed.

Recorded the user's acceptance of the 11-candidate subset and W11 policy in new versioned curation/policy files and an acceptance ledger. Built 18,252 derived events with original identities and quality flags,11 unit summaries, sample-exposure-correct rate bins, quarter waveform/amplitude summaries, raster and rate overview. Two sample 2 events in 32/38 are omitted only from the derived domain; no original event is deleted. [Findings/output guide](../../reviews/2026-11-24-w12-curated-subset.md), [curation revision](../../../configs/extra4_shank0_curated_v1.json), [adopted policy](../../../configs/extra4_shank0_analysis_policy.v1.json).

Independent source-to-derived audit passed for all 18,252 event rows/flags,11 units, 330 rate bins,44 quarter summaries and 7,312 raw excerpts / 11,757,696 values. Six helper tests passed. All 13 final figures reviewed; a separate layout-only finalizer fixes clipped labels on the heatmap. Raw SHA and source W7B/W11 manifests unchanged. The original 38,687 events / 58 clusters / 19 good / 39 mua labels, previous ledgers/proposals and worker history remain intact. Other cluster decisions were not silently accepted or converted to noise.

```powershell
.venv\Scripts\python.exe scripts/build_w12_curated.py --output results/extra4_shank0/w12-curated-v1
.venv\Scripts\python.exe scripts/validate_w12_curated.py --report results/extra4_shank0/w12-curated-v1
.venv\Scripts\python.exe scripts/finalize_w12_report.py --report results/extra4_shank0/w12-curated-v1
.venv\Scripts\python.exe -m unittest tests.test_round2_review tests.test_w7b_review
```

Repeat in a fresh output path; never overwrite this completed revision. Final assembly adds the visual-review record and refreshes the report manifest. The current working-run metadata now points to the accepted subset and policy. [Windows quality](../../WINDOWS_QUALITY.md#w12-adopted-derived-subset) owns the methods/output contract. No new sorting, merge/split, quality censoring, resampling, installation, commit or push. Next: W13 provenance/reproducibility audit and remaining-shank expansion gate.
