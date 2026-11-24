# W12 — Accepted putative-unit subset v1

Date: 2026-11-24. State: explicitly accepted by the user, implemented and independently validated.

The user accepted the proposed 11-candidate subset and W11 analysis policy. [Curation revision v1](../../configs/extra4_shank0_curated_v1.json) records that authorization and pins the selected run, prior proposal ledger, W11 packet and [adopted analysis policy](../../configs/extra4_shank0_analysis_policy.v1.json). The prior proposal documents remain unchanged.

**Accepted putative units:** without-248 clusters **1, 5, 6, 10, 32, 33, 38, 39, 47, 49 and 50**, all from `w7b-exclude248-01`. The [new ledger](2026-11-24-w12-curation-ledger.csv) records acceptance for these 11 only. The other 47 selected-run clusters remain outside this subset with their W10 hold/withhold proposals preserved; they have not been relabeled noise or deleted. The historical control 36 reference is not part of the selected run. Putative-unit acceptance is not neuron ground truth or proof that every event is valid.

The [derived report](../../results/extra4_shank0/w12-curated-v1/index.html) contains **18,252 events** over **[100,2999900) samples**, corresponding to 299.98 nominal seconds or 297.599206349 physical seconds. The source subset contains 18,254 events; only the two sample 2 events in 32/38 are omitted from this derived table. Original event indices and sample times are retained, without shifting the time origin. The original sorter still contains 38,687 events / 58 clusters with 19 good / 39 mua labels.

## Accepted-unit summaries

| Without-248 cluster | Derived events | Mean rate, nominal Hz |
| --- | ---: | ---: |
| 1 | 241 | 0.803 |
| 5 | 1,095 | 3.650 |
| 6 | 3,754 | 12.514 |
| 10 | 2,808 | 9.361 |
| 32 | 4,679 | 15.598 |
| 33 | 3,889 | 12.964 |
| 38 | 378 | 1.260 |
| 39 | 343 | 1.143 |
| 47 | 180 | 0.600 |
| 49 | 440 | 1.467 |
| 50 | 445 | 1.483 |

Rates use included events divided by the matching analysis duration, not estimated true neuronal exposure. Physical-time rates are also available in the tables; physical sampling is 10080 Hz versus nominal 10000 Hz. Per-unit identity includes recording, shank, selected run, cluster and revision; integer cluster IDs are never interpreted across runs by themselves.

All quality flags are retained. The subset includes nine broad-warning events, zero tight-warning events,19 peak-guard events and nine events with unavailable broad assessment. These categories can overlap and are not artifact counts. No quality-based event or denominator censoring is applied. W11's named sensitivity scenarios remain linked/copied alongside the primary summary.

The raster displays all 18,252 events. Rate bins preserve the original sample axis and use 10 nominal seconds except that the first and last bins each have 9.99 seconds of retained exposure. Figures overlay shared padded-guard diagnostics, broad-warning times and unavailable-assessment intervals; narrow intervals may be subpixel at full-recording scale, so the saved W11 intervals and per-event flags remain authoritative. Red event markers identify peak-guard or broad-warning membership, not all possible quality problems.

Each unit figure shows quarter raw means, pooled reference, sorter-feature amplitude versus time and binned rate. Quarter 1–4 remain consecutive 75 nominal seconds; the first/last quarter exposure is clipped to the adopted domain. Eight-channel central waveform correlations to the pooled reference range .9618–.9938 across 44 quarter summaries. This is descriptive and not an independent statistical test: selected reference and quarter events can overlap. Raw means use numerical ×1e6 scaling and median centering, not calibrated microvolts. Two of eight saved physical channels are shown per unit.

The four larger populations 6/10/32/33 dominate the raster/rate overview. Smaller populations show appreciable count variation across bins; no stationarity, response, cross-unit synchrony or cross-neuron independence claim is made. Slow waveform-background differences remain visible in some quarter views, especially 32/33, as documented in prior review. Acceptance preserves those limitations rather than silently masking them.

## Outputs and verification

The packet includes `spikes.csv`/`spikes.npz` with original event identities and all W11 flags; `units.csv`; `rate_bins.csv`/NPZ with exact sample exposures; `quarter_metrics.csv`; 11 raw-waveform NPZs/figures; raster and rate overview; the two-event boundary-omission table; copied acceptance/policy/ledger; W11 sensitivity rows; and independent checks. Original sorter files are never used as output destinations.

The independent audit compared every derived event and flag to the selected run/W11 source, checked all 11 unit summaries, 330 rate-bin counts/exposures/rates and 44 quarter summaries, and reconstructed **7,312 raw excerpts / 11,757,696 values**. Source labels, raw SHA and W7B/W11 manifests remained unchanged. Six helper tests passed. All 13 final figures were visually reviewed; the rate overview received a layout-only finalization to prevent clipped unit labels. No numerical artifact changed during that layout fix.

This is the accepted v1 analysis subset, not the W13 reproducibility/expansion freeze or completion of all extra_4. Next is W13: audit the complete provenance and repeatability chain, establish the expansion procedure, and decide whether remaining-shank work can proceed. No additional shank was sorted here; SpikeInterface remains deferred.
