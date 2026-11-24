# W15A - Reusable runner and shank1 baseline

Date: 2026-11-24. Authorized by the user's request to proceed with W15A after the documentation cleanup.

## Outcome

Completed the all-512-channel sort for **shank1 (the second shank)**: **11,324 events, 33 clusters, seven automated good and 26 mua**. Run identity is `extra_4/shank1/w15a-allchannels01`. No clusters are curated or accepted, no working-run selection is recorded, and no events are removed. Shank0's accepted release is unchanged.

The [configuration](../../../configs/extra4_shank1_w15a.json) pins the input, geometry, runtime and scientific settings reference. [Result metadata](../../../configs/extra4_shank1_baseline.v1.json) pins the completed packets. [Baseline report](../../../results/extra4_shank1/w15a-baseline-review01/index.html) includes all-cluster inventory, quarter summaries and raw means; [independent checks](../../../results/extra4_shank1/w15a-validation01/checks.json) record validation.

## Implementation and validation

- Added configuration-driven `run_sorting.py`, baseline report generator and independent validator. Fresh output paths are mandatory. Scientific settings match the shank0 reference contract; its channel exclusion is not inherited. All 512 shank1 channels remain active.
- Four unit tests passed across the runner and shank-input modules, including real mappings for all four shanks and rejection of incorrect geometry/exclusions. This validates the transfer contract, not bitwise equivalence to a fresh shank0 GPU sort.
- Preflight and post-sort checks passed for 19 pinned inputs, active channels, event/cluster arrays and resolved settings. Runtime and sorter source are recorded. Kilosort finished successfully; its sparse-tensor warning did not interrupt execution.
- Independent audit checked 11,324 event identities, 11 annotation columns, 33 cluster rows, 132 quarter rows, 9,900 count bins and all 885 saved raw windows (1,423,080 values). Source pins and both packet manifests passed.

## Baseline observations and limitations

Visually reviewed `overview.png`, all three `raw_means` pages and the sorter's `drift_amount.png`. Several clusters show compact spike-shaped raw averages, including the seven automated-good clusters (1, 4, 7, 10, 11, 23, 24). These are screening observations, not single-unit acceptance. Several sparse clusters show slow background structure or insufficient events; waveform similarity and possible competitors still require W16A review. Drift estimates remain within approximately +/-0.5 micrometres; this estimator output does not prove tissue stability.

Fifteen events overlap broad coincidence warnings, four overlap tight warnings, and 18 lack coincidence assessment coverage. These use the existing full-2048-channel detector population, not a recalculated 512-channel threshold. No event overlaps its template-peak channel guard; 16 overlap a guard somewhere on the active shank, and none overlap guard concurrency of at least half the shank. Generic shared-signal warning assessment is unavailable, not evidence of no shared activity. W14's separate source-quality evidence remains applicable.

Six events lack the full +/-100-sample raw context. Clusters 2, 18 and 30 have no complete excerpt, so their raw-mean panels are intentionally empty; panel `n` is total cluster events, while `raw_events_displayed` in the inventory gives the excerpt count. All original events remain in the inventory and sorter output. Raw means sample up to 64 events and show three nearby channels; they cannot establish all-event consistency. Numerical scaling by 1e6 is not voltage calibration.

## Adoption and next step

Only a diagnostic baseline was implemented. No exclusion, temporal mask, subset, merge or exposure policy was adopted. Shanks2/3 were not sorted. Next is W15B: explicitly authorized matched shank2 all-channel and b54/global872 plus b148/global353 exclusion conditions. Later W15D owns working-run selection and W16A owns full shank1 curation.
