# W7B — Matched channel-248 exclusion experiment

State: two new sorts and bounded comparison completed. Original evidence and automated labels preserved. This is a sensitivity experiment, not adoption of a replacement baseline or a curated unit set. SpikeInterface was not installed or added to the roadmap.

## Conditions and control

Both new runs used root `.venv`, Kilosort 4.1.7, FAISS 1.13.2, Torch 2.11.0+cu128 and the RTX 5090. The full 3,000,000-by-512 float32 input remained unchanged. Every scientific setting from the frozen resolved settings was explicitly retained, including nominal 10,000 Hz, scale 1e6, CAR, 300 Hz high-pass, whitening range 32, one drift block, thresholds and duplicate suppression. Physical rate remains 10,080 Hz. No external preprocessing or temporal mask was introduced.

The control uses all 512 channels. The exclusion condition passes `bad_channels=[248]` to Kilosort; the exported channel map contains exactly the other 511 original binary indices. Input width remains 512. Kilosort freshly estimates preprocessing in each condition. Internal NumPy/Torch/CUDA seeds remain 1, with cluster initialization seed 5; deterministic-algorithm overrides were not introduced.

The repaired-environment control is **byte-identical to the historical pilot** for spike times, cluster assignments, templates, amplitudes, channel map, automated labels and contamination table. This validates this bounded pilot under the repaired runtime; it is not a general equivalence claim for every Kilosort output or dataset. A further repeat control was not needed to interpret this observed contrast.

| Run | Events | Clusters | Automated good | Automated mua |
| --- | ---: | ---: | ---: | ---: |
| Historical pilot | 39,620 | 59 | 24 | 35 |
| New all-channel control | 39,620 | 59 | 24 | 35 |
| New exclusion of b248/global1921 | 38,687 | 58 | 19 | 39 |

The net decrease is 933 events and one cluster. It must not be described as removal of exactly 933 artifacts: event times and assignments can change in both directions.

## Target correspondence evidence

Event matching is one-to-one within each candidate cluster pair at inclusive +/-2 samples. Dice is `2 * matched / (left_count + right_count)`. Candidate pairs are evaluated independently, so these counts are not a global assignment of neurons. Raw correlations use 12 common physical channels around the two template peaks, always excluding b248, with offsets -20 through +40. Raw means use up to 128 evenly spaced complete events per cluster; differing selected samples and small alignment shifts can change means despite identical underlying input.

| Historical/control cluster | Exclusion candidate | Old/new events | Matched events | Dice | Common-channel raw correlation |
| --- | --- | --- | ---: | ---: | ---: |
| 34 | 32 | 4,679 / 4,680 | 4,677 | 0.9995 | 0.9833 |
| 35 | 33 | 3,887 / 3,889 | 3,887 | 0.9997 | 0.9881 |
| 5 | 6 | 3,728 / 3,754 | 3,518 | 0.9404 | 0.9762 |
| 12 | 10 | 2,816 / 2,808 | 2,665 | 0.9477 | 0.9781 |
| 2 | 2 (weak candidate) | 1,254 / 1,727 | 523 | 0.3509 | 0.9591 |
| 36 | No convincing counterpart | 339 / — | Best pair: 2 | Best pair: 0.0069 | Best pair: -0.0407 |

The four promising candidates retain narrow raw deflections, similar multichannel structure and similar 10-second activity profiles. All four exclusion candidates retain automated good labels. Contamination estimates are 1.3%, 0.6%, 3.2% and 0.0% for exclusion clusters 32/33/6/10 respectively; these are sorter estimates, not confirmed neuron purity. Retain the promising-candidate status without upgrading to confirmed neurons.

Historical cluster 36 does not survive as a convincing time-and-waveform counterpart. Its highest Dice pair is exclusion cluster 31, sharing only two events and having dissimilar raw means. The target-36 figure intentionally displays that weak candidate for inspection; it is **not** a mapping of cluster 36 to cluster 31. This supports the earlier concern that cluster 36 depends on the anomalous channel, but does not prove every one of its original events was non-neuronal.

Historical cluster 2 remains unresolved. Its event population is redistributed: candidate exclusion cluster 2 shares 523 events; exclusion cluster 0 shares 290. These pairwise matches are not a formal split decision. Similar raw mean shape alone is insufficient to establish identity. Exclusion cluster 2 is labeled mua with 38.5% estimated contamination versus the old good label and 19.6%. Keep this population held for isolation review.

Across all clusters, 34 of 59 control clusters have a highest-ranked counterpart with Dice at least 0.9; this is a descriptive threshold, not a curation rule. Changes extend beyond b248's immediate neighborhood. Other label/partition changes include old 26 to candidate 24 (Dice 0.9492, good to mua), old 45 to candidate 46 (0.9167, good to mua), and weaker correspondences for old 44 and 49. Therefore fewer automated good labels cannot be equated with either lost neurons or successful artifact removal. Full pair tables retain secondary candidates for future review.

## Warning intervals and remaining limits

The same full-2048-channel extra_4 coincidence intervals are joined by sample time onto each new output. Broad/tight warning overlaps change from 37/5 to 35/4 events. Coincidence assessment is unavailable for 19 control events and 17 exclusion events. Events within the historical 12 high-variability seconds change from 1,665 to 1,640. These descriptive counts do not establish an artifact-removal rate.

The b248-guard **time** overlaps in the run table concern all events at those times, irrespective of their spatial support; they are not b248-affected-event counts. Per-cluster peak guards are reported separately. No global union, event censoring, zero-filling or adjusted unit-exposure denominator is applied. Excluding b248 does not repair the brief shared flat episode near second 99 or validate a general coincidence-warning exclusion rule.

## Recommendation and evidence

Keep the original baseline and this exclusion condition as separate named evidence. Carry the b248-excluded condition forward as a candidate for focused curation, with promising correspondences 32/33/6/10 and explicit review of reorganized populations. Do not declare it universally better or overwrite the baseline. Next proposed work is a curation/acceptance checkpoint covering those four candidates, the held old-2 population and material label changes; shared-transient observability remains a separate policy decision. Expansion to other shanks is not implied.

The [local review](../../results/extra4_shank0/w7b-review01/index.html) contains all-cluster metrics, full pair tables, top-three candidates, selection ledgers, raw means and six visually inspected target figures. Fresh sorts: `results/extra4_shank0/w7b-control01` and `results/extra4_shank0/w7b-exclude248-01`. Independent checks reproduce all 17,543 selected raw windows/means (1,805,385,216 values including repeated windows), event identities, activity bins and short-ISI counts. All input manifests remain valid. Two matching tests pass, including comparison against a dynamic-programming oracle on 100 synthetic examples.
