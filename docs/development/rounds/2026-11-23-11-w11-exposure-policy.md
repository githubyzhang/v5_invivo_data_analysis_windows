# W11 — Boundary and exposure policy proposal

Date: 2026-11-23. State: implemented, independently validated, visually reviewed; policy proposed, not adopted.

Assessed all selected-run events against boundary, full-population coincidence, per-channel guard and shared flatness annotations. Added11 matched-count/denominator scenarios for each of58 clusters and checked W10's diagnostic cohorts. [Findings](../../reviews/2026-11-23-w11-exposure-findings.md) own the scientific interpretation; the [policy proposal](../../../configs/extra4_shank0_analysis_policy.proposed.json) records the concrete pending-W12 decision.

Recommend annotation-only quality handling over [100,2999900) samples to require complete centered raw review context. Expanded boundary audit found sample2 events in both candidates32 and38, plus boundary-only35/54/57. The11-candidate analysis-domain count would be18,252 rather than18,254; no derived accepted subset was created. Whole-recording rate sensitivity is at most1.0943% per candidate across tested scenarios, which does not establish reliability of short-bin or synchrony analyses. W10 holds remain unexplained by available flags and unchanged.

Nine figures reviewed. Independent audit validated638 scenario rows, all event flags/support maps/coverage tracks, and929 raw excerpts /1,486,307 values. Six helper tests passed. Raw SHA and W7B/W7A/W10 manifests remained unchanged. The W10 ledger, selected-run metadata, original events/labels, source data and archive remain untouched. No mask, merge/split, adoption, commit or push.

```powershell
.venv\Scripts\python.exe scripts/review_w11_exposure.py --output results/extra4_shank0/w11-exposure-review01
.venv\Scripts\python.exe scripts/validate_w11_exposure.py --report results/extra4_shank0/w11-exposure-review01
.venv\Scripts\python.exe -m unittest tests.test_round2_review tests.test_w7b_review
```

Use fresh paths for repeats. Final assembly copies the authored policy and visual-review record into the report and refreshes its manifest. [Windows quality](../../WINDOWS_QUALITY.md#w11-quality-and-exposure-sensitivity) owns the output/method contract. Next: W12 explicit user acceptance of a concrete cluster subset and policy, followed by versioned derived summaries. No acceptance is inferred from committing this proposal.
