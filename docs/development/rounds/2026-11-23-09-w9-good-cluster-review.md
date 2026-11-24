# W9 — Broaden selected-run good-cluster review

Date: 2026-11-23. State: implemented, numerically validated and visually reviewed; recommendations proposed, not adopted.

Reviewed the remaining15 automated-good clusters in the user-selected `w7b-exclude248-01` run. Added a reproducible unit/quarter/neighbor report and independent validator. Twenty-seven new figures and eight reused W8 pair figures were inspected. Seven additional putative-candidate proposals bring the total to11; eight of19 automated-good clusters remain held for sparse evidence, consolidation, internal structure or isolation. [Findings](../../reviews/2026-11-23-w9-good-cluster-findings.md) own the interpretation; the [revised ledger](../../reviews/2026-11-23-w9-curation-proposals.csv) records proposals for all58 selected-run clusters plus the historical control36 reference.

Independent checks reconstructed14,368 excerpts /27,815,988 raw values, all60 quarter means/correlations,15 autocorrelograms,12 pair correlograms, physical feature mappings/projections and event/ISI/warning counts. Six existing helper tests passed. Input raw SHA and original run/report manifests remained unchanged. One sample2 event in candidate38 is explicitly retained and flagged for the later boundary/exposure policy.

Commands from the project root:

```powershell
.venv\Scripts\python.exe scripts/review_w9_good.py --output results/extra4_shank0/w9-good-review01
.venv\Scripts\python.exe scripts/validate_w9_good.py --report results/extra4_shank0/w9-good-review01
.venv\Scripts\python.exe -m unittest tests.test_round2_review tests.test_w7b_review
```

Generators require a fresh path for repeats. The local packet's final manifest also covers the copied proposal ledger and visual-review record; recommendations are a review product, not computed automatically by the generator. Method and artifact contracts are in [Windows quality](../../WINDOWS_QUALITY.md#w9-broader-good-cluster-review).

No raw/source data, archived worker, sorter arrays/labels, selected-run metadata or prior evidence were changed. No sorting, masking, merge/split, human acceptance, commit or push. Next is W10: all-mua screening and targeted ambiguous-population review, including the additional W9 holds. The long-range extra_4 plan remains unchanged.
