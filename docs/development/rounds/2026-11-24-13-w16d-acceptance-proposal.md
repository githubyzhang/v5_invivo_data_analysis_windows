# W16D - Concrete subset and analysis-policy acceptance proposal

Date: 2026-11-24. State: **implemented and validated proposal preview; awaiting user acceptance**. The user authorized the next round after committing W16C. That authorizes preparing this checkpoint, not recording acceptance of its new scientific policy. No accepted derived revision is issued yet.

## Recommendation

Accept the conservative W16A/B/C candidate subsets, with the explicit analysis domains below. The [acceptance report](../../../results/extra4/w16d-proposal01/index.html) includes raster previews, residual annotations, exact omissions and rate sensitivities. The [tracked proposal](../../../configs/extra4_w16d_acceptance.proposed.json) pins the evidence and exact policy. The existing shank0 11-unit release remains unchanged.

| Shank (zero-based) | Proposed IDs | Units | Original candidate events | Proposed events | Nominal exposure per unit |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | 1, 4, 7, 11, 23 | 5 | 9,816 | 9,816 | 299.9800 s |
| 2 | 1, 2, 3, 8, 9, 12, 15, 17, 18, 19, 20, 21, 22, 23, 25, 26, 41 | 17 | 27,539 | 27,537 | 299.9800 s |
| 3 | 5, 10, 14, 16, 20, 26, 30, 34 | 8 | 6,453 | 6,443 | 291.8240 s |
| Total | Run-qualified identities; no mixing | 30 | 43,808 | 43,796 | Per-unit domains; do not sum as recording duration |

All 128 new-shank clusters retain proposals: 30 candidates, 51 holds, 47 withheld. Their reasons are copied from the pinned ledgers into `all_cluster_proposals.csv`; no identities are reclassified, merged or split. Withheld does not mean proven artifact. Accepting these candidates would yield 41 accepted putative units across four shanks including the existing 11, not proof of 41 distinct biological neurons or complete recovery.

## Concrete policy for acceptance

1. All three shanks use the half-open integer-sample interior **[100, 2,999,900)**, requiring complete +/-100-sample raw context. This is a context rule, not a validated filter-settling period. Preserve original sample indices, event indices and run-qualified cluster IDs.
2. Shanks1–2 retain quality annotations without additional primary censoring. Their per-unit denominator is 2,999,800 samples: 299.98 nominal seconds at 10,000 Hz or 297.59920635 physical seconds at 10,080 Hz.
3. Shank3 additionally omits W15C's shared-flat core and shoulder from both events and duration. The core requires at least 256 original channels flat simultaneously; the shoulder expands each core interval by 500 samples on either side. This omits 81,560 additional samples, leaving **2,918,240 samples**, or 291.824 nominal / 289.50793651 physical seconds per unit. The 50-nominal-ms shoulder is a conservative operational margin, not validated settling or a claim of clean remaining time.
4. Preserve peak/active-channel guards, full-2048-channel broad/tight coincidence annotations and assessment availability. Unavailable remains unknown. Do not automatically remove events for those annotations. Peak and eight-neighbor guard-clear rules are mandatory sensitivity comparisons, with matching event counts and denominators, not primary acceptance rules.
5. Report rates as **observed-event rates in the declared domain**, not estimated true neuronal firing rates. Show original counts, proposed omissions, flags, domains and sensitivity results. Signal-loss gaps cannot establish neuronal silence. Short-bin, synchrony or event-triggered conclusions require specific evidence and exposure-aware analysis.

The new shank3 policy differs deliberately from frozen shank0 and proposed shanks1–2 because W15C/W16C evidence demonstrates shared loss of observability on shank3. Local guard proxies do not establish a validated unit footprint, so imposing them as universal primary rules would be stronger than the evidence supports. Excluding a sorter channel did not repair shared loss. Partial disturbances and questionable events can remain in every primary domain.

## Exact effects and residual concerns

The [omission preview](../../../results/extra4/w16d-proposal01/omitted_event_preview.csv) lists all 12 original event identities. Shank2 omits c3 event6 at sample2 and c21 event7 at sample46 for incomplete context. Shank3 omits three core events (c16:1, c30:2) and seven shoulder events (c5:2, c10:1, c14:1, c16:2, c34:1). No shank1 candidate event is omitted. Source events remain intact; these are proposed analysis exclusions only.

Residual primary flags, which overlap and must not be summed as artifact counts:

| Shank | Peak guard | Any-active guard | Half-active guard | Broad / tight | Coincidence unavailable |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 | 15 | 0 | 10 / 2 | 11 |
| 2 | 5 | 4,589 | 10 | 10 / 1 | 14 |
| 3 | 18 | 4,223 | 0 | 1 / 0 | 0 |

No proposed primary event has incomplete raw context. Generic shared-signal assessment remains unavailable; the shank3 core is a separate explicit diagnostic definition. W16A/B's residual short intervals and attribution concerns remain disclosed in the original reviews; this proposal does not use censoring to claim improved isolation or rewrite automated labels.

Eight-neighbor sensitivity retains 9,811 / 27,202 / 6,309 events for shanks1/2/3, respectively. Its unit-specific nominal exposure ranges are 299.7405–299.98 / 286.6319–299.98 / 274.5879–287.1348 seconds. The [120-row sensitivity table](../../../results/extra4/w16d-proposal01/sensitivity.csv) records interior, proposed primary, primary peak-clear and primary local8-clear counts and denominators for all 30 candidates. A rate can increase when its denominator shrinks; this is not evidence of recovered spikes or a corrected true rate.

## Implementation and validation

`prepare_w16d.py` verifies the selected run registry, pinned W16A/B/C records, source/baseline/curation manifests, W14 intervals and W15C masks before constructing fresh proposal previews. It preserves source event identities and flags, exports exact half-open interval arrays, candidate accounting, all-cluster proposals and omission identities. It makes no adoption entry.

```powershell
.venv\Scripts\python.exe scripts/prepare_w16d.py --output results/extra4/w16d-proposal01
.venv\Scripts\python.exe scripts/validate_w16d.py --report results/extra4/w16d-proposal01 --output results/extra4/w16d-validation01
```

Use fresh output paths for reproduction. The independent validator reconstructs the core from per-channel flat unions, reproduces shoulder masks, independently resolves peaks/eight nearest active channels from sorter geometry, computes exclusion unions and direct event-time membership, checks full interval masks, both time conventions, residual flags and every omitted identity. All **120 scenario checks**, **72,306 original source-event identities**, **128 cluster rows**, **30 candidates** and **12 omissions** passed. Synthetic half-open/overlap/adjacency checks also passed. Both scientific figures were visually inspected. These are calculation checks, not scientific validation of clean exposure.

Original inputs, selected sorter outputs, prior review packets and shank0 release remain unchanged. Generated previews are ignored by Git and require separate artifact preservation. The [methods reference](../../WINDOWS_QUALITY.md#w16d-subset-and-policy-proposal-preview) defines output semantics.

## Acceptance boundary and next step

Ask the user to accept the listed 30 putative candidates and this per-shank policy together, or specify revisions. The agreed roadmap requires explicit acceptance before adoption. After acceptance, continue W16D with versioned accepted event/unit tables, omitted-event and quality records, exposure-aware bin summaries, rasters and waveform/amplitude summaries. W17 then combines and audits the four-shank release, disclosing per-shank policy differences. W16D is not fully complete until those accepted derived revisions exist.
