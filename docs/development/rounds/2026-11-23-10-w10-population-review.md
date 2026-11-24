# W10 — All-mua screen and ambiguous-population review

Date: 2026-11-23. State: implemented, validated, visually reviewed; scientific recommendations remain proposed.

Screened all39 mua clusters in the selected without-248 run and inspected five internal-population probes plus six within-run overlap comparisons. The [findings](../../reviews/2026-11-23-w10-population-findings.md) document why consequential holds remain unresolved and why wholesale merges/splits are not supported. The [revised ledger](../../reviews/2026-11-23-w10-curation-proposals.csv) accounts for all58 selected-run clusters:11 putative candidates,38 holds, nine proposed withholds from future single-unit summaries. The original automated19 good /39 mua labels remain unchanged. No additional candidate is promoted.

All18 new figures were inspected. Independent validation reconstructed11,678 excerpts /19,928,748 values, all39 ACGs and six cross-correlograms, quarter/group means, physical feature mappings, projections, nearest-neighbor sets, maximum one-to-one counts and control31/33 correspondence within selected-run31. Six helper tests passed. Five input manifests and the raw binary SHA remained unchanged. The packet contains original-event-index diagnostic groups, not adopted curated splits.

```powershell
.venv\Scripts\python.exe scripts/review_w10_populations.py --output results/extra4_shank0/w10-population-review01
.venv\Scripts\python.exe scripts/validate_w10_populations.py --report results/extra4_shank0/w10-population-review01
.venv\Scripts\python.exe -m unittest tests.test_round2_review tests.test_w7b_review
```

Use a fresh report path for repeats. Final assembly copies the authored proposal ledger and visual-review record into the packet and refreshes its manifest. Scientific judgments are not generated automatically. [Windows quality](../../WINDOWS_QUALITY.md#w10-all-mua-and-population-review) owns the method/output contract.

No original data/results, worker history, selected-run metadata, labels, previous ledgers or evidence packets were modified. No merge/split, masking, event removal, installation, acceptance, commit or push. Next is W11: boundary/quality/exposure policy and sensitivity, with W10 subgroups and43/44 near-coincident events carried forward. Further curation of held populations can be a separate validated increment; documenting unresolved cases satisfies this conservative checkpoint.
