# W16D - Accepted shanks1–3 derived revision v1

Date: 2026-11-24. State: **user-accepted subsets and policies; derived outputs built and validated**. W16D is complete. The user separately accepted the 30 putative-unit candidates and then explicitly answered “Accept the proposed analysis policy.” The user deferred held clusters for later review. Neither the frozen proposal nor earlier review ledgers were rewritten.

The [accepted revision](../../../configs/extra4_shanks123_curated_v1.json) records both authorizations and pins the original proposal. The [derived report](../../../results/extra4/w16d-curated-v1/index.html) provides event/unit tables, raster and rate overviews, waveform/amplitude summaries, omitted identities and residual quality annotations. The [tracked all-cluster ledger](../../reviews/2026-11-24-w16d-accepted-curation-ledger.csv) records 30 accepted putative units, 51 deferred holds and 47 withheld clusters across all 128 new-shank output clusters. Held/withheld source events remain intact.

| Shank | Accepted putative units | Original candidate events | Derived events | Omitted | Exposure per unit, nominal seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 5 | 9,816 | 9,816 | 0 | 299.9800 |
| 2 | 17 | 27,539 | 27,537 | 2 | 299.9800 |
| 3 | 8 | 6,453 | 6,443 | 10 | 291.8240 |
| Total | 30 | 43,808 | 43,796 | 12 | Per-unit domains, not additive recording duration |

Shank0 retains its frozen accepted 11-unit / 18,252-event revision. Together the four accepted subsets account for **41 putative units and 62,048 derived events**, but the combined release and cross-shank reproducibility audit remain W17 work. This accounting is not a claim of definitive biological identities or complete recovery.

## Adopted behavior and limitations

All new shanks use the half-open sample interval [100,2999900), requiring complete +/-100-sample context. Shanks1–2 retain quality flags as annotations. Shank3 additionally excludes the documented W15C shared-flat core and its +/-500-sample shoulder from both event counts and duration. This leaves 2,918,240 samples on shank3 versus 2,999,800 on shanks1–2. Exact nominal/physical exposures and all 12 omitted identities reproduce the [W16D proposal](2026-11-24-13-w16d-acceptance-proposal.md).

Events retain original sample indices, original sorter-event indices, cluster IDs and run-qualified unit identities. No events are imported from alternative sorts, no clusters are merged/split and no source labels are rewritten. The new ledger accepts only the already reviewed IDs. Other clusters remain outside the subset, with hold review deferred by the user.

The event table preserves guard flags, full-2048-channel coincidence warnings and assessment availability. Residual primary peak-guard counts remain 0 / 5 / 18 for shanks1/2/3; unknown coincidence assessments remain 11 / 14 / 0. Unknown does not become clean. Rates are observed-event rates in the adopted domain, not true neuronal firing-rate estimates; shared signal-loss gaps are not biological silence. The shared shoulder remains an operational margin, not validated filter settling. Guard-clear sensitivities remain diagnostic rather than additional adopted censoring.

## Derived output contract

`spikes.csv` supplies 43,796 run-qualified event records and flags. Per-shank `spikes.npz` provides the same original identities and numeric/Boolean arrays. `units.csv` records counts, omissions, physical/global peak mapping, median sorter amplitude, flags and both nominal/physical rates. `curation_ledger.csv` retains all 128 decisions and reasons; its tracked copy is byte-identical. `omitted_events.csv` lists the 12 excluded source identities and reasons. `sensitivity.csv` preserves the original policy-comparison table unchanged.

`rate_bins.csv` and per-shank `rate_bins.npz` contain 900 unit/bin rows on 30 original-axis bins of 100,000 samples. Each denominator intersects its bin with the accepted interval union. A fully excluded bin would receive an undefined rate, not a zero-rate silence claim; none of these 10-second bins is fully excluded. `quarters.csv` contains 120 original-recording-quarter rows, with matching exposure, counts, amplitude medians and raw correlations. Original time is never concatenated across exclusions.

Raw waveform summaries are recomputed from accepted-domain event centers, using deterministic chronological-rank selection: at most 256 pooled events and 128 per quarter, eight nearest active physical channels, +/-100 samples, input x1e6 and first-70-sample median baseline. Saved `unit_*.npz` packets retain selected indices, pooled raw windows/reference and quarter means/indices. Raw windows can cross internal mask edges because the accepted rule is center-based. Figures show peak-channel quarter means, amplitudes with peak-guard/broad-warning markers and rates with excluded-domain overlays. Numerical packets preserve the eight-channel data.

## Validation and preservation

```powershell
.venv\Scripts\python.exe scripts/build_w16d_curated.py --output results/extra4/w16d-curated-v1
.venv\Scripts\python.exe scripts/validate_w16d_curated.py --report results/extra4/w16d-curated-v1 --output results/extra4/w16d-curated-validation01
```

Commands identify completed outputs; reproduction requires fresh paths. The builder requires explicit accepted subset/policy state, verifies the frozen proposal/pins and source binary hashes, and writes only a new derived directory. The independent validator checks original event identity and flags, inclusion membership, interval arrays, physical geometry, both time conventions, per-bin counts/exposures, amplitudes, quarter means and original-time selection. Separate scalar channel reads reproduce **21,281 raw windows**. All **43,796 events, 30 units, 120 quarters, 900 bins, 128 ledger rows and 12 omissions** passed. The prior W16D proposal audit already independently reconstructed source masks and validated the 120 policy scenarios.

Visual layout checks covered the rate overview and representative unit-summary pages from each shank (shank1 page1, shank2 page4, shank3 page2); this is output QA, not a new exhaustive cluster review. The [independent checks](../../../results/extra4/w16d-curated-validation01/checks.json) and [revision provenance](../../../configs/extra4_shanks123_derived_v1.json) pin outputs and code. Prior source/proposal pins remain unchanged. Generated results still require separate preservation outside Git.

## Next

Proceed to **W17: combined four-shank release and reproducibility audit**. Combine accepted revisions using original sample time and run-qualified identities; verify mapping, policy differences, event/quality accounting and artifact provenance. Do not reopen held-cluster curation as part of W17. That is a later focused review with new evidence and an explicitly versioned revision if warranted.
