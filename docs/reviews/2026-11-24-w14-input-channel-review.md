# W14 - Remaining-shank inputs and channel-quality proposals

Date: 2026-11-24. State: inputs implemented and verified; channel recommendations proposed, not adopted. Shank numbers here are zero-based (1, 2 and 3 are the remaining three shanks).

All three sample-major, little-endian float32 exports are complete under `data/w14-extra4-inputs01`. Each contains 3,000,000 samples x 512 channels, exactly 6,144,000,000 bytes. Export/readback checks and separate W13 preflight audits verified every value against the original HDF5: **4,608,000,000 values total**. Source identity, mapping, finite values and sample alignment passed. Source SHA-256 remains `3bedaa51bca65205dcc81e25ef48f249c9f1ea34346f4cfd7327e26269bd9755`. No filtering, resampling, channel removal, zero filling or temporal censoring was applied.

[Input and proposal metadata](../../configs/extra4_remaining_shanks_w14.proposed.json) pins the outputs and audit records. The [review report](../../results/extra4/w14-review03/index.html) contains spatial/time summaries and ten targeted raw/neighbor views. The [all-channel proposal ledger](2026-11-24-w14-channel-proposals.csv) covers every remaining channel; the [numeric inventory](../../results/extra4/w14-quality01/channels.csv) contains the measurements.

## Findings

| Shank | Median / maximum padded-guard fraction | Channels above 1% / 5% / 10% guard coverage | Proposed next sort |
| --- | --- | --- | --- |
| 1 | 0% / 0.1129% | 0 / 0 / 0 | All 512 channels; retain artifact annotations. |
| 2 | 0.0720% / 91.9860% | 192 / 6 / 4 | Matched all-channel control versus exclusion of b54/global872 and b148/global353. |
| 3 | 2.9124% / 49.5838% | 484 / 59 / 6 | Matched all-channel control versus exclusion of b259/global2045, with explicit shared-episode diagnostics. |

The 1%, 5% and 10% columns are descriptive summaries, **not adopted exclusion thresholds**. These are channel-time measurements, not counts of corrupted spikes or proven unusable neuronal exposure. All 1,536 replayed padded-guard interval sets match the previously computed native Mac detector intervals exactly (at least ten identical samples, padded by 500 samples on each side).

The three strongest persistent problems are:

| Channel | Exactly zero | Padded guard | Longest exact-flat run, nominal seconds | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Shank2 b148 / global353 | 90.2095% | 91.9860% | 45.2482 | Mostly flat throughout all four quarters, with only intermittent nonzero signal. |
| Shank2 b54 / global872 | 49.7517% | 52.5713% | 18.1144 | Repeated long plateaus in all quarters; burden increases through the recording. |
| Shank3 b259 / global2045 | 47.0856% | 49.5838% | 14.5808 | Repeated persistent plateaus across all quarters, exceeding its shank's already elevated background. |

In the bounded onset views, their nearest physical neighbors retain varying signals while the target stays flat. This supports channel-specific compromise in addition to shared episodes. The acquisition/source-processing cause remains unestablished; these findings do not distinguish hardware clipping from upstream processing. **One-sided values are not the selection criterion:** all remaining channels have zero positive-value fraction in this source. The long/repeated zero plateaus, temporal burden, neighborhood evidence and marked outliers support the proposed sensitivity tests.

Shank2 b10/global168 and b367/global301 retain 14.54% and 13.97% padded-guard coverage. Shank3 b403/global1788 and b486/global440 retain 15.42% and 13.64%; additional channels have substantial coverage. These are not declared clean. The proposal retains them for baseline comparison with annotations because W14 has not established a principled cutoff or the neuronal cost of broader exclusions. Any broadening needs its own evidence and condition.

## Shared episodes are a separate concern

| Shank | Time with >=256 channels exactly flat | Time with >=256 padded guards | Maximum simultaneous exact-flat channels |
| --- | ---: | ---: | ---: |
| 1 | 0 nominal s | 0 nominal s | 119 |
| 2 | 0.0820 nominal s | 0.1822 nominal s | 267 |
| 3 | 7.2005 nominal s | 8.2127 nominal s | 511 |

The longest contiguous shank3 episode meeting the exact-flat diagnostic is 1.7138 nominal seconds. The [shared-concurrency figure](../../results/extra4/w14-validation03/shared_concurrency.png) plots per-second maxima, not mean coverage. The half-population threshold is descriptive only, not a mask or validated artifact definition.

Shank1's highest-guard channels share a short disturbance near 99.5 nominal seconds; this does not justify removing those channels. Zero time above the half-population threshold does not mean no shared artifacts. Shank3 has much more widespread/recurrent zero/flat activity; excluding b259 alone will not fix that issue. Its future sorts must examine event concentration near shared intervals, saved preprocessing where available, waveform/cluster stability and quality sensitivity before selecting a working result. No claim about actual Kilosort detections on these shanks is possible yet because they have not been sorted.

Mac full-2048-channel coincidence warnings retain their original population and separate meaning. The new flat-concurrency diagnostics do not replace them or fill unavailable generic shared-signal warning coverage. No warning threshold was recalibrated on a 512-channel population.

## Verification and next step

Six exporter/mapping/guard tests passed. Independent interval accounting checked all 1,536 channel totals, 460,800 per-second cells, all quarter sums and concurrency arrays. Ten full raw-channel masks agree with the legacy implementation; all ten saved target/neighbor excerpts match the source. Three overviews, ten focus figures and the shared-concurrency figure were visually reviewed. Plot layout/font corrections left numerical results unchanged. Earlier local report drafts remain preserved; `w14-review03` and `w14-validation03` are the final packet references.

The frozen W13 release, shank0 results, source recordings, labels and archives remain unchanged. The original 512-channel width is retained in every new binary, even if a future sorter omits selected electrodes. No new unit curation or channel-selection acceptance is recorded here.

Recommend staging W15: **W15A** configuration-driven runner and shank1 all-channel baseline; **W15B** shank2 matched control/exclusion sorts and comparison; **W15C** shank3 matched sorts with explicit shared-episode assessment. These are engineering/diagnostic runs, not accepted neuron results. Review the named exclusion proposals before their use, and keep every condition in a distinct output path. Shared-episode masking and broader exclusions remain unadopted.
