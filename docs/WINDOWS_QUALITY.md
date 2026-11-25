# Windows quality methods and output contracts

This reference retains each round's method/output contract. Statements such as "pending acceptance" or "no exclusions adopted" apply to that named round, not to the whole project today. The [roadmap](development/roadmap.md) owns current status. Use fresh output paths for reproduction; examples naming completed packets identify those packets and must not overwrite them.

| Task | Contract |
| --- | --- |
| Accepted shank0 derived tables | [W12](#w12-adopted-derived-subset) and [adopted policy](../configs/extra4_shank0_analysis_policy.v1.json) |
| Shank0 provenance freeze | [W13](#w13-release-and-expansion-gate) |
| Remaining-shank input and quality work | [W14](#w14-remaining-shank-input-and-quality-contract) |
| Historical pilot/condition review reproduction | The named sections below; scope remains pilot-specific unless explicitly generalized |

## Historical pilot baseline

Scope: extra_4/shank0 pilot01, 3,000,000 samples and 512 channels. `scripts/review_units.py` is repeatable with explicit evidence and fresh output paths. Generalize dimensions, rates and run selection before applying it to another recording.

Inputs are final aligned arrays, automated labels, supplied channel mapping, archived readable resolved settings, raw per-second SD and historical per-electrode candidates. Positions are checked against the mapping. `kept_spikes` describes the pre-deduplication list and is checked but never reapplied. Inputs are not modified. Arrays load without pickle; serialized ops objects are not executed.

`cluster_review.csv`: one row per cluster; full-exposure nominal/physical rates, template peak binary/global channel, ISIs, amplitude stability and descriptive prior matches. ISI thresholds are <10/<20 samples; ACG bins are nominal 1 ms. Two-sample duplicate suppression, low counts and short recording duration limit refractory/contamination interpretation. Prior matches are many-to-many without chance correction, not accuracy or recall. Whitened templates and feature amplitudes are not calibrated voltages.

`curation_queue.csv`: original labels, review priorities, boundary/disturbance counts and pending decision fields. No decision is adopted. Copy into a new revision before editing; record source hashes, reviewer/date, old/new IDs, proposal/adoption state, rationale and evidence. Merges require explicit ID maps. Preserve original labels and sample indices. Cluster IDs do not identify matching neurons across recordings.

`exposure.json`: exact sample counts for the 12 high-variability seconds (median-channel SD >2x its temporal median). No exclusions applied. Outside-screen rate divides outside-screen events by 288 nominal seconds; corresponding physical exposure is 2,880,000/10,080 seconds. It is a descriptive comparison, not a replacement rate. Outside-screen does not mean clean. Prior shared-warning assessment covers only 35/300 seconds; flat guards are not calibrated clipping rails.

`index.html` links metrics and all 15 plot pages. `near_duplicates.json` reports similarity candidates, not automatic merges. `stability_bins.npz` stores 10-nominal-second counts/median amplitudes (missing values are NaN). `resolved_settings.json` retains the original Python JSON Infinity convention, not strict JSON. Original drift evidence remains in the return; it is not regenerated.

`provenance.json` records input/script SHA-256, interpreter and analysis-library versions. `report-manifest.json` hashes every generated file except itself and is written last. Source/config/sorter identity also resides in the verified return manifest and RUN_REPORT. CPU diagnostics do not establish new GPU validation or confirmed neuron identities.

## Targeted Round 1 raw review

`scripts/review_pilot_round1.py` generates a separate pilot-specific packet for clusters 34/35, 5/12, 2, 26/29 and 37/58. It verifies the binary SHA-256 and all frozen payloads before/after, opens raw data in read-only mode, and refuses an existing report destination or a destination inside evidence/data storage. No preprocessing reconstruction or sorter execution is used.

`raw_selection.csv` records selected final-array indices, original sample indices, both time conventions and available support. Up to 256 evenly spaced event ranks per cluster are selected among windows with full offsets [-100,+100]. Incomplete contexts are logged and never padded. Per-event/channel subtraction uses the raw median over [-100,-31]; displays multiply by 1e6 without asserting voltage calibration. All-event rates/ISIs are unchanged by this diagnostic selection.

`cluster_N_waveforms.npz` saves near-channel raw windows, binary/global IDs, selected event/sample indices, relative samples, all-channel mean and quarter means/counts. The eight displayed channels are nearest to the original whitened-template peak. The independent raw peak searches all 512 channels using peak-to-peak of the selected mean over offsets [-20,+40]. Quarter means refer to four 75-nominal-second blocks; their correlations with the pooled mean are descriptive and not independent validation. Empty selections/quarters have empty arrays or NaN means rather than fabricated waveforms.

`cluster_metrics.csv`, `quarter_metrics.csv`, `pc_comparison_coverage.csv` and `boundary_events.csv` own numeric diagnostics. PC projections use PC1/2 at a shared physical channel, mapping each cluster through its pc_feature_ind. Neighbor candidates have template peaks within 60 µm; missing features are recorded, not interpreted as separation. Plotting is capped at 1,000 event ranks per cluster. This is not a formal isolation-distance estimate or complete neighbor search. Boundary context includes other clusters only to show original events near the recording edges.

`scripts/validate_round1_review.py` independently rereads every saved near-channel window from the binary, verifies original array indices, reproduces baseline columns and records the initial channel-248 flat prefix. It writes a new `independent_checks.json`, refusing overwrite. The three focused synthetic tests check ACG self-pair exclusion/radius handling and deterministic sample selection.

The generator produces mechanical evidence; findings and proposal ledgers are added after visual review. The completed packet includes `review_findings.md` and the copied proposal CSV, and its final manifest is refreshed to cover these additions plus independent checks. Versioned [Round 1 findings](reviews/2026-11-23-kilosort-round1-findings.md) own interpretation. Proposals use `proposed_not_applied` with human decisions pending, retain original labels and pin source spike-array/report hashes. They do not alter the baseline or constitute confirmed neuron identities.

## Round 2 pair, disturbance and guard review

`scripts/review_pilot_round2.py` examines 31/33, 45/48, 5/6, 2 versus 0/1/3 and 26/27, cluster 35's internal features and contextual cluster 36. Fresh-output and frozen-input hash protections match Round 1. Each pair uses 12 nearest channels to either template peak, with the same channels for both raw averages; raw support/baseline/scaling follow Round 1. Saved raw NPZs pin event indices, original samples, channel identities and centered values. Selection is capped at 256 evenly spaced complete-context event ranks per population. Repeated selections across pairings are counted as windows, not unique events.

`pair_metrics.csv` records original template similarity, central raw-mean correlation, common-channel coverage, cross-pairs with |lag|≤2, <10 and <20 samples, and hypothetical union ISIs. `pair_*_features.npz` retains every lag within inclusive ±500 samples and PCA parameters/projections. Correlograms use 1 nominal ms bins and are not chance normalized. Feature vectors align all three stored PCs through each cluster's physical channel mapping. PCA uses the common-channel intersection, unstandardized units, a mean-centered SVD, and balanced min(256,n_a,n_b) event ranks per population. The two-dimensional projection is not independent isolation validation. Cluster 35's b232-PC2 median grouping is descriptive only; its all-channel projection, quarter counts and raw means do not constitute a proposed split.

`raw_per_second.npz` recomputes SD in float64 and exact-zero counts across all raw values. The SD screen must reproduce the frozen set of 12 seconds; small differences from historical float32 SD are recorded. `channel248_constant_runs.csv` inventories ≥100-sample runs without padding, distinct from the inherited guard threshold. `disturbance_cluster_metrics.csv` uses 12/288 nominal seconds for screen/outside rates, with no censoring; counts at a zero sample on b248 do not establish that another cluster is affected. Context plots preserve min/max envelopes of the spatial median in 10-sample display bins; b248 is plotted uncentered without decimation. Optional HDF5 comparison checks the full b248/global1921 trace and 12,000 additional excerpt values; it does not hash or claim identity of the full source file.

`scripts/validate_round2_review.py` independently rereads all saved raw values, brute-forces cross-lags, reconstructs feature mapping/projections, checks all-channel zero counts and long zero-run completeness, and verifies all cluster screen counts. Four focused synthetic tests cover cross-lag endpoints/orientation, constant-run boundaries, physical feature mapping and PCA reconstruction.

`scripts/review_pilot_clipping_guard.py` reuses `analysis.pilot.flat_mask` (≥10 identical samples) and `dilate` (500 samples each side), as documented by the inherited [methods](METHODS.md#quality-and-observability). Full-recording replay is limited to 18 selected channels and must exactly match the frozen prior guard masks; a separate interval-union implementation also verifies them. The other channels use the 633 frozen intervals. `clipping-guard/channel_guard_coverage.csv` records per-electrode exposure, and `cluster_guard_overlap.csv` annotates original event-center and [-20,+40] support overlap with the cluster's template-peak-channel guard. This is not a validated unit mask or a unit-rate denominator. No global union, zero-filling or channel exclusion is adopted.

The completed Round 2 packet adds reviewed findings, a pending proposal ledger, an independent audit and a guard supplement. Its final manifest is recursive (relative POSIX paths), including the supplement's own manifest but excluding the root manifest itself. [Round 2 findings](reviews/2026-11-23-kilosort-round2-findings.md) own interpretation and the decision checkpoint. Original labels and IDs remain authoritative until an explicitly versioned curation is accepted.

## External current-detector annotations

W6 adds a separate `kilosort-external-detector-quality-v1` sidecar without modifying the frozen sort or prior reviews. The [custom-pipeline guide](CUSTOM_PIPELINE_WINDOWS.md#kilosort-annotation-adapter) owns its schema and source-linkage requirements. It projects 2048-channel detector coincidence warning/availability intervals onto the original 512-channel pilot event sample indices, and separately records peak-channel guard/observability diagnostics. Candidate row flags are never reused as sorter row flags. The generic native detector's historical baseline/broadband warning fields are explicitly unavailable; the old partial reference masks remain in their own artifacts. None of these external annotations is an adopted label, exclusion, accuracy estimate or unit exposure denominator.

## W7A all-channel guard and saved-preprocessing review

This pilot-scoped diagnostic extends raw replay to all 512 channels. Run in the root `.venv`, with a fresh result destination:

```powershell
.venv\Scripts\python.exe scripts/review_pilot_artifacts.py --output results/extra4_shank0/pilot01-w7a-reviewed
.venv\Scripts\python.exe scripts/validate_artifact_review.py --report results/extra4_shank0/pilot01-w7a-reviewed
.venv\Scripts\python.exe scripts/plot_artifact_event_details.py --report results/extra4_shank0/pilot01-w7a-reviewed
.venv\Scripts\python.exe -m unittest tests.test_artifact_review
```

The completed destination already exists and must not be overwritten; use a new name for another generation. The generator verifies the pilot binary, 169 frozen payloads and detector-sidecar identities before/after, compares every channel's independent flat-run interval union against frozen and native guards, and writes `channel_coverage.csv`, `flat_runs.csv`, `guard_intervals.csv` and `guard_tracks.npz`. Counts of simultaneous flat channels and simultaneous padded guards are distinct. Guards remain annotations, never applied masks.

`window_selection.csv` selects all broad coincidence intervals, the three largest other-channel guard-concurrency peaks (earliest ties, centers more than 10,000 samples apart), and first/middle/last cluster-36 event ranks inside/outside its peak guard with complete context. Each NPZ saves all 512 raw and transformed channels over center ±500 samples, absolute sample indices and original event indices. Fixed eight-channel spatial coverage is displayed for shared episodes; nearest eight channels to b248 for cluster 36. Raw context displays subtract each channel's first-200-sample median and multiply by 1e6, with stated offsets and no voltage calibration. Transformed channels have 15-unit offsets. Red bands show global broad warnings, not artifact truth. `flagged_events.csv` is the union of broad, tight and peak-channel guard flags.

Unlike the baseline CPU report, this explicitly authorized reconstruction loads the **hash-verified local saved `ops.npy`** using Kilosort's loader. It overrides the obsolete binary path and uses saved filter, CAR, whitening and drift parameters through `bfile_from_ops`, with no sorter run or upstream package edits. Three historical batch-statistic anchors must match within rtol/atol 1e-5. Excerpts use the corresponding batch cores; no excerpt-level filtering or fabricated context. The audit independently maps absolute indices through reader-returned batch bounds and checks reconstructed values within 1e-6, rereads every saved raw value, verifies event identities, tests all saved flat-run boundaries and rebuilds guard concurrency via difference arrays. This checks saved preprocessing reconstruction, not full sorter equivalence under the repaired environment.

`window_metrics.csv` describes all events and amplitudes in each context. Its count of channels ever exceeding absolute transformed amplitude 6 is an exploratory descriptor, not a detection threshold or an exclusion criterion. `coincidence_interval_audit.csv` separates event counts inside warnings from surrounding-context counts. `independent_checks.json` records validation and exact-flat concurrency.

Event details select first/middle/last broad-warning event ranks per interval plus the six existing cluster-36 events. `detail_selection.csv` pins identities and nearest four channels to each original template peak. Details cover offsets -30 through +50; raw baseline uses -30 through -21. These are descriptive closeups without shape-based selection or new labels. The final manifest covers all figures, CSV/NPZ files, audit and detail provenance; findings are versioned [separately](reviews/2026-11-23-w7a-artifact-findings.md).

## W7B matched channel-exclusion experiment

Pilot-specific execution in root `.venv`; completed destinations below must not be overwritten:

```powershell
.venv\Scripts\python.exe scripts/run_w7b.py --condition control --output results/extra4_shank0/w7b-control01
.venv\Scripts\python.exe scripts/run_w7b.py --condition exclude248 --output results/extra4_shank0/w7b-exclude248-01
.venv\Scripts\python.exe scripts/review_w7b.py --control results/extra4_shank0/w7b-control01 --exclusion results/extra4_shank0/w7b-exclude248-01 --output results/extra4_shank0/w7b-review01
.venv\Scripts\python.exe scripts/validate_w7b.py --report results/extra4_shank0/w7b-review01 --control results/extra4_shank0/w7b-control01 --exclusion results/extra4_shank0/w7b-exclude248-01
.venv\Scripts\python.exe -m unittest tests.test_w7b_review
```

The launcher reads frozen resolved settings, removes obsolete path fields, and explicitly passes all scientific settings to Kilosort 4.1.7. It checks the binary and frozen return before/after. `bad_channels=[248]` is the only experimental channel-selection change; the binary remains 512 columns. Each fresh condition has its own preprocessing, `run_contract.json`, dependency lock, status, Kilosort logs/outputs and output manifest. Internal seed behavior is recorded, without claiming universal GPU determinism. Hash-verified newly generated ops are read to check resolved settings and channel counts; no historical ops are modified.

The review verifies both run manifests and matched contracts. `run_metrics.csv` and `cluster_metrics.csv` retain original IDs within each run, automated labels, estimated contamination, <10/<20-sample ISI counts, full-exposure nominal/physical rates and warning counts. Coincidence intervals retain their 2048-channel extra_4 population; unavailable assessment is distinguished from unflagged time. `b248_guard_time_events` counts all events occurring during b248's guards, irrespective of spatial support. `peak_guard_events` uses each run's own template-peak electrode. Neither defines an exclusion or a rate denominator.

`raw_selection.csv` records up to 128 evenly spaced complete event ranks per cluster over [-100,+100]. Every raw channel is retained in `*_raw_means.npz`, with median baseline over [-100,-31], original sample units and 10-second counts. Display scaling is x1e6 without voltage calibration. Comparisons use original physical channel IDs, never array-column equality after channel removal. Each pair's correlation uses 12 channels nearest either template peak, excluding b248, over [-20,+40]. Empty-context raw means are NaN, not fabricated waveforms.

`*_pairs.csv` enumerates nonzero pairwise event-time matches within inclusive +/-2 samples. Chronological matching maximizes one-to-one match count within each pair, without reusing an event inside that pair; exact-match counts refer to that chosen matching, not an independently optimized exact-match assignment. Different candidate pairs can reuse events. `*_top3.csv` ranks by Dice, matched count, then right cluster ID. Rankings, even rank 1, are not accepted identities or a forced global matching. Six target figures compare historical clusters 34/35/5/12/36/2 with their highest-ranked candidates and time profiles; a weak candidate can explicitly mean no supported counterpart.

Independent validation compares seven historical/control payloads byte-for-byte, rereads all selected raw windows to reproduce means, verifies event identities/counts/ISIs/bins, checks the exclusion map and re-verifies every input manifest. `report-manifest.json` covers the final review plus audit, excluding itself. Interpretation and adoption limits live in the [W7B findings](reviews/2026-11-23-w7b-sensitivity-findings.md).

## W8 focused curation checkpoint

Use root `.venv` with a fresh report path; existing completed output is immutable evidence for this checkpoint:

```powershell
.venv\Scripts\python.exe scripts/review_w8_checkpoint.py --output results/extra4_shank0/w8-checkpoint01
.venv\Scripts\python.exe scripts/validate_w8_checkpoint.py --report results/extra4_shank0/w8-checkpoint01
.venv\Scripts\python.exe -m unittest tests.test_round2_review tests.test_w7b_review
```

The generator pins both W7B run manifests and the earlier review, then recomputes the installed Kilosort label criteria for every cluster. `label_criteria.csv` stores eligibility (>10 events and nonzero span), R, Q and both strict <0.2 tests; no label is overwritten. This is reproduction of the algorithm, not independent validation that its labels are biologically correct.

Fourteen named pair selections in the script cover promising candidates, selected high-template-similarity neighbors, changed populations and their competitors. The list is bounded, not an exhaustive neighbor/duplicate search. Up to 256 evenly spaced complete event ranks per cluster/pair are extracted over [-100,+100], on the same 12 nearest physical channels to either peak. Raw windows are scaled by 1e6 then centered using the median over [-100,-31]. Saved NPZs contain raw windows, original event indices, physical channel IDs, feature projections, PCA parameters and all b-a cross-lags within inclusive ±500 samples. PCA uses balanced up-to-256-per-group training and all shared stored PC dimensions; the plot caps each group at 1,500 events. **Convert `pc_feature_ind` through the active channel map** before combining physical channels after exclusion. A small shared-feature intersection limits interpretation even when spatial raw support differs.

`pair_metrics.csv` includes raw correlation over [-20,+40], common-feature coverage, pair counts within ≤2 / <10 / <20 samples and hypothetical union ISIs. These are descriptive, without chance normalization or merge adoption. Quarter files use up to 128 complete events per 75-second quarter and compare with a separately selected pooled up-to-256 reference on eight nearest channels. Reference/quarter selections can overlap, so their correlations are not independent statistical tests.

The independent audit rereads every saved pair window and quarter/reference selection, reproduces means, inverts the binary channel map to reconstruct features, verifies projections, and brute-forces pair-lag lists. It also records old31/33's union correspondence and candidate-level automatic-good bookkeeping. Six existing helper tests cover the reused interval, lag, feature/PCA and matching functions.

After visual review, the versioned [proposal ledger](reviews/2026-11-23-w8-curation-proposals.csv) is copied into the packet, and `working_run_recommendation.json` explicitly records proposed/not-adopted state, pending human acceptance and unchanged originals. Final report assembly adds links and refreshes the manifest. Rerunning evidence generation alone does not reproduce scientific review decisions; those are authored in the versioned [findings](reviews/2026-11-23-w8-curation-findings.md). Every exclusion cluster is accounted for as recommended, held, boundary-only or outside acceptance scope; outside scope is not rejection. The ledger pins source arrays and preserves original automated labels separately from recommendations. Human adoption must be recorded in a new revision, never by silently rewriting these proposals or sorter output labels.

## W9 broader good-cluster review

Use root `.venv` with a fresh output path:

```powershell
.venv\Scripts\python.exe scripts/review_w9_good.py --output results/extra4_shank0/w9-good-review01
.venv\Scripts\python.exe scripts/validate_w9_good.py --report results/extra4_shank0/w9-good-review01
.venv\Scripts\python.exe -m unittest tests.test_round2_review tests.test_w7b_review
```

The generator verifies the selected W7B output, W7B comparison and W8 report manifests, and raw SHA before/after. It asserts that its 15 targets are exactly the automated-good IDs other than W8's four candidates. It reuses W8's hash-bound reproduction of R/Q criteria and W7B annotations; these retain the full2048-channel population. `unit_metrics.csv` preserves automatic labels, warning/availability counts and full-exposure rates. No new scientific label or exposure correction is calculated automatically.

`neighbor_screen.csv` records all 57 competitors per target, signed template cosine, peak distance, event count and selection/evidence provenance. The screen selects the two largest absolute cosines of at least .05 plus the nearest peak within 150 micrometers among clusters with at least 20 events. These are bounded review-prioritization choices, not acceptance cutoffs. Sparse neighbors remain for W10. Relevant existing W8 comparisons are linked; 12 missing pairs are newly generated. Pairs are within the selected run, not cross-run matches.

Unit NPZs retain up to 256 complete chronological-rank-selected raw windows on eight nearest physical channels, the pooled mean, independent up-to128 selections per quarter, quarter means and all autocorrelation lags within inclusive +/-500 samples. Raw baseline/scaling and quarter conventions match W8. Exact self-pairs are removed from ACGs; distinct events at equal sample times would remain. Pair NPZs retain12 physical channels, original event indices, raw windows, PCA parameters/projections and full cross-lag lists. Plotting shows bounded excerpts and selected spatial channels, not every waveform/event. Missing common stored feature channels yield an empty PCA panel explicitly titled zero channels; that is unavailable evidence, not established separation.

The validator independently rereads windows, brute-forces auto/cross event differences, inverts the physical PC map, recomputes quarter means/correlations and recalculates guard/coincidence membership with direct half-open inequalities. Existing helpers have six focused unittest checks. The packet is finalized with the versioned proposal ledger and `visual_review.json`; a final manifest covers all artifacts except itself. The generator alone does not reproduce authored scientific recommendations. [W9 findings](reviews/2026-11-23-w9-good-cluster-findings.md) own those judgments; [the revised ledger](reviews/2026-11-23-w9-curation-proposals.csv) preserves original labels and pending human decisions. Older packets and ledgers remain unchanged.

## W10 all-mua and population review

Use root `.venv` and a fresh report path:

```powershell
.venv\Scripts\python.exe scripts/review_w10_populations.py --output results/extra4_shank0/w10-population-review01
.venv\Scripts\python.exe scripts/validate_w10_populations.py --report results/extra4_shank0/w10-population-review01
.venv\Scripts\python.exe -m unittest tests.test_round2_review tests.test_w7b_review
```

The generator verifies both W7B run manifests and W7B/W8/W9 report manifests, plus the raw binary SHA before/after. It screens all 39 selected-run mua clusters, retaining inherited R/Q, annotation counts, automatic labels and event counts in `mua_screen.csv`. Each `mua_N.npz` saves original event indices, up to 128 complete raw excerpts on eight nearest physical channels, pooled means, up to 64 excerpts per quarter, quarter means and full self-excluded ACG lag lists within +/-500 samples. Empty quarters or boundary-only clusters produce NaN means, not zero-valued evidence. Seven overview figures display the peak raw channel, time/amplitude and ACG; saved arrays retain eight channels. Raw baseline, numerical x1e6 scaling and nominal quarter/sample conventions match W9.

`population_N.npz` probes12/29/31/40/45. For12/29/40/45, a deterministic two-centroid Lloyd procedure operates on all 30 own-channel stored PC values, initialized at extrema along the leading centered singular axis; it requires nonempty groups and convergence within 100 iterations. These forced partitions are diagnostic only: no cluster-count model selection, biological split or curated event labels are implied. Cluster31 instead maps selected-run event times within 2 samples to control31/33, preserving unmatched/ambiguous groups separately. Group raw means, original event indices, PCs, centroids/projections and counts are saved. No control events enter the selected run.

`overlap_A_B.npz` covers43/44,41/42,45/48,52/53,26/27 and29/30. It saves full cross-lags, maximum chronological one-to-one matches within inclusive2 samples, all common physical-channel features, balanced PCA and five-nearest-neighbor identities/fractions excluding self. Distances use all shared stored PC dimensions without new scaling; unbalanced counts and sorter-derived features limit interpretation. These are descriptive measures with no acceptance cutoff. Raw matched/unmatched cohorts use up to 128 complete excerpts and12 channels nearest the first cluster's template peak. Closely matched raw windows sample nearly identical original data, so similar means are not independent evidence of duplicate detection.

The independent audit reconstructs all saved raw excerpts/means, brute-forces ACG/cross-lags, uses dynamic programming for maximum matching counts, inverts physical PC mappings, reproduces projections and uses SciPy `cdist` for neighbor checks. It verifies diagnostic centroid consistency and control-correspondence membership. Supplementary outputs record full-population coincidence annotations per cohort and eight-channel mean-correlation sensitivity over integer shifts -3 through+3 samples. These checks validate calculations, not biological identity or the appropriateness of an imposed split.

After visual review, the authored [W10 ledger](reviews/2026-11-23-w10-curation-proposals.csv) and `visual_review.json` are copied into the packet; final assembly refreshes the manifest. [Findings](reviews/2026-11-23-w10-population-findings.md) own the interpretation. The generator alone does not reproduce review judgments. Pending human acceptance and unchanged original labels/events remain explicit. Prior ledgers/packets and working-run selection metadata are preserved.

## W11 quality and exposure sensitivity

Use root `.venv` with a fresh report directory:

```powershell
.venv\Scripts\python.exe scripts/review_w11_exposure.py --output results/extra4_shank0/w11-exposure-review01
.venv\Scripts\python.exe scripts/validate_w11_exposure.py --report results/extra4_shank0/w11-exposure-review01
.venv\Scripts\python.exe -m unittest tests.test_round2_review tests.test_w7b_review
```

The generator verifies W7B selected-run, W7A all-channel evidence and W10 report manifests, the original binary SHA, the full-population sidecar hash and the W10 ledger. `event_annotations.npz` preserves all 38,687 original event indices, sample indices and cluster IDs. It adds broad/tight warning and availability flags, incomplete +/-100-sample context, per-unit peak guard, any/all of eight nearest active channels guarded, peak-context-touching-guard, active-shank shared guard/flatness and excluded-b248 context flags. No event or sorter label is edited. The eight-channel neighborhood is a geometric proxy, not a measured unit support/observability footprint.

`global_intervals.npz` retains exact half-open interval sets and active-channel counts for padded guards and exact-flat runs separately. Removed channel248 is excluded from active counts. Shared50% diagnostics require at least 256 of511 active channels; they are not an adopted threshold or the unavailable generic shared-signal warning. Coincidence intervals retain their 2048-channel population. Unknown availability is not unflagged/clean time.

`unit_intervals.npz` stores per-unit guard proxies and every retained interval set used by the 11 scenarios. `sensitivity.csv` has638 rows: each of58 clusters crossed with full recording, interior only, interior minus broad, peak, peak-or-broad, shared padded50%, shared exact-flat50%, any-eight, all-eight, peak-context-touch and assessed-only scenarios. Each row records both retained/removed event counts and the matching sample denominator, nominal/physical durations/rates and relative rate change versus the full-recording reference. Rate denominators are retained analysis durations, not validated effective neuronal exposure. The context-touch scenario expands guard intervals by100 samples each side because the event window includes both endpoints; the primary context-complete domain is [100,2999900). Original sample origin is preserved.

`w10_cohort_annotations.csv` annotates original-index diagnostic groups and the 43/44 near-coincident subset without accepting those groups as units. `boundary_events.csv` inventories all five sample 2 events, including candidates32/38. `boundary_raw.npz` saves available truncated excerpts without inventing pre-recording samples. Seven candidate NPZs save all 28 complete events flagged by peak guard OR broad warning OR all-eight guards and up to 128 unaffected comparison events on eight nearby channels. Numerical x1e6 scaling and median baseline match W9/W10. Nine figures visualize coverage, rate sensitivity, boundary evidence and flagged waveforms; plots are descriptive, not artifact labels.

The independent validator reconstructs active coverage through direct interval slices, verifies physical support and all event flags, and checks every scenario's retained intervals, event membership, denominator and both rate conventions. It independently rereads saved raw excerpts. Final assembly copies the authored [policy proposal](../configs/extra4_shank0_analysis_policy.proposed.json) and visual-review record into the packet and refreshes the manifest. [W11 findings](reviews/2026-11-23-w11-exposure-findings.md) own the scientific interpretation. No accepted curated table is produced. Explicit W12 acceptance must be recorded separately before adopting the proposed domain/policy and subset; committing this proposal does not itself record acceptance.

## W12 adopted derived subset

The user explicitly accepted the 11-candidate subset and W11 policy on 2026-11-24. `configs/extra4_shank0_curated_v1.json` records that authorization and source hashes; `configs/extra4_shank0_analysis_policy.v1.json` records the adopted policy while preserving the earlier proposal. The versioned W12 ledger marks only the 11 selected units accepted. Remaining clusters keep their previous proposals and original labels; omission from this subset is not noise classification.

```powershell
.venv\Scripts\python.exe scripts/build_w12_curated.py --output results/extra4_shank0/w12-curated-v1
.venv\Scripts\python.exe scripts/validate_w12_curated.py --report results/extra4_shank0/w12-curated-v1
.venv\Scripts\python.exe scripts/finalize_w12_report.py --report results/extra4_shank0/w12-curated-v1
.venv\Scripts\python.exe -m unittest tests.test_round2_review tests.test_w7b_review
```

Use a fresh path for a repeat. The builder checks accepted state, revision/policy/source hashes, original run/W11 manifests and raw binary SHA. It selects only accepted cluster IDs with sample 100 <= t <2999900. `spikes.csv`/NPZ retain original event indices, sample indices, cluster IDs, sorter feature amplitudes and every W11 quality flag; CSV also carries composite unit identities and both timing conventions. `omitted_boundary_events.csv` accounts for the two sample 2 candidate events separately. No source spike file or label table is rewritten.

`units.csv` contains 11 putative-unit counts, matching nominal/physical durations/rates and warning/availability counts. `rate_bins.csv`/NPZ retain original-axis 100,000-sample bins with exposure clipped to the accepted interval; first/last bins have 99,900 samples, other bins 100,000. Rates divide by these actual sample durations. Empty-count bins remain zero rates with their full retained exposure. Quality-based denominator subtraction is not applied. W11 diagnostic sensitivities are copied for the accepted IDs, keeping their full-recording reference basis explicit.

Each unit NPZ retains up to 256 complete chronological-rank-selected raw windows on eight nearest active channels, pooled means, up to 128 selections per quarter and quarter means. Baseline/scale conventions match W11; raw x1e6 is not calibrated microvolts. `quarter_metrics.csv` records counts, clipped exposure, nominal rates, median sorter amplitudes and central eight-channel correlations to the pooled reference. Reference and quarter samples can overlap. Unit figures show two channels, time/amplitude and rates; the raster includes all 18,252 events. Diagnostic shared-guard bands, broad-warning markers and assessment-availability shading accompany temporal views; very narrow intervals may be subpixel, and saved intervals/flags are authoritative.

The validator independently selects source events, checks CSV and NPZ contents/flags against originals, recomputes unit/bin/quarter summaries and rereads all saved raw selections. A separate layout-only finalizer makes heatmap labels readable without changing numerical artifacts. Final assembly records visual review and refreshes the manifest; working-run metadata points to its digest. The completed v1 packet and earlier evidence must not be overwritten; future scientific changes require a new revision. [W12 findings](reviews/2026-11-24-w12-curated-subset.md) own interpretation and remaining limitations. The completed W13 release below owns the reproducibility/expansion freeze.


## W13 release and expansion gate

The accepted W12 subset and packet remain unchanged. The [W13 release record](../configs/extra4_shank0_release.v1.json) pins the provenance freeze; the [release audit](../results/extra4_shank0/w13-release01/index.html) verifies nine manifests, exact replay of 38 payloads and full source-to-shank0 equality. No new GPU sort was performed. The [expansion procedure](development/extra4-expansion.md) owns reusable input checks, per-shank gates and tooling limits. W13 clears W14 preparation, not automatic acceptance or exclusion on other shanks.


## W14 remaining-shank input and quality contract

The [W14 findings](reviews/2026-11-24-w14-input-channel-review.md) and [input/proposal metadata](../configs/extra4_remaining_shanks_w14.proposed.json) extend the frozen W13 expansion procedure without modifying it. `prepare_w14_inputs.py` creates fresh exact-cast exports and source-level quality inventories; `shank_input.py` independently verifies complete source/binary equality. Full-width binaries remain unchanged by proposed electrode exclusions. `review_w14_channels.py` creates all-channel overview and bounded neighbor evidence; `validate_w14_review.py` checks interval accounting and saved raw examples. Each output path must be fresh.

All-channel CSVs own measured guard/zero fractions and channel proposals; exact intervals and per-second counts are in the quality NPZ. The 10-sample flat / 500-sample padding definition is inherited diagnostic metadata, not a unit exposure mask. Shared concurrency thresholds are descriptive. Full-population coincidence annotations retain their 2048-channel definition. Three named channel-exclusion sensitivities remain proposals; no temporal mask or universal clipping cutoff is adopted. W15 is staged into runner/shank1 baseline, shank2 matched comparison and shank3 matched/shared-episode review.

## W15 configuration-driven sorting and baseline contract

`scripts/run_sorting.py` accepts an explicit authorized configuration with pinned source files, mapping, settings reference, runtime versions and installed sorter-source hash. The current adapter supports this recording's four 512-channel shanks. It validates geometry and full binary width, applies only explicit excluded channels, rejects existing output paths, records resolved settings/environment, verifies outputs and rechecks input hashes before writing the completed manifest. Failed partial runs are preserved and require a fresh destination. A reference run supplies scientific settings, not its exclusion list or cluster identities. Do not use Python optimization mode: validation includes assertions.

The completed example is [W15A configuration](../configs/extra4_shank1_w15a.json); [W15A record](development/rounds/2026-11-24-06-w15a-shank1-baseline.md) owns observations. Commands below document that execution; existing outputs must not be overwritten. A rerun needs a new configuration/output identity.

```powershell
.venv\Scripts\python.exe scripts/run_sorting.py --config configs/extra4_shank1_w15a.json --preflight-output results/extra4_shank1/w15a-preflight01.json
.venv\Scripts\python.exe scripts/run_sorting.py --config configs/extra4_shank1_w15a.json
.venv\Scripts\python.exe scripts/review_sorting_baseline.py --run results/extra4_shank1/w15a-allchannels01 --output results/extra4_shank1/w15a-baseline-review01
.venv\Scripts\python.exe scripts/validate_sorting_baseline.py --report results/extra4_shank1/w15a-baseline-review01 --output results/extra4_shank1/w15a-validation01
```

The baseline adapter uses W14 quality sources and the full-2048-channel native detector annotations. Event indices and original samples remain authoritative. Flags record coincidence warning/availability, template-peak guard, any/half-active-shank guard concurrency and incomplete +/-100-sample context. Shared-signal assessment availability is explicit. Flags annotate; they neither remove events nor accept/reject clusters. `clusters.csv` includes every output cluster and original automated label; `quarters.csv` uses four equal sample-axis quarters; `counts.npz` uses nominal one-second bins. Full-duration rates use nominal 10000 Hz or physical 10080 Hz as labeled, with no quality censoring.

Raw excerpts select up to 64 evenly spaced chronological ranks with complete context per cluster, eight nearest active channels, and 201 samples centered on each event. Values are multiplied by 1e6 and each excerpt/channel subtracts its median over offsets -100 through -31. Means display three nearest channels. This is numerical scaling, not microvolt calibration. Zero-excerpt clusters retain empty arrays and NaN means; their plots are empty. The validator independently reconstructs interval masks, event identities, summaries and raw excerpts. Completed report and validation manifests remain separate so review documentation does not invalidate the audited packet.


## Matched-condition comparison contract (W15B)

`compare_sorting_runs.py --control <baseline-report> --exclusion <baseline-report> --output <fresh-result>` verifies matched settings, runtime, input and manifests. It inventories every cluster in both runs. Chronological one-to-one event matching uses +/-2 samples for each pair; Dice is twice matched events divided by the sum of cluster counts. Matches can be reused across different pairs. Best candidates are ranked by Dice, then matched count and IDs; ranks are diagnostic, not accepted identities or merge instructions.

Raw means use up to 128 evenly spaced complete events per cluster over all original binary channels, offsets -100..100, per-event/channel median subtraction over -100..-31, and numerical x1e6 scaling. Pair correlations use offsets -20..40 on the 12 common active channels nearest either template peak, excluding omitted electrodes. Missing complete windows produce unavailable correlations. Ten nominal-second histograms retain all events. Focus figures cover best candidates for every automated-good cluster in either run and control clusters peaking on omitted electrodes. A sparse cluster's best match can be weak or coincidental.

Fixed quality masks preserve each omitted channel's guard intervals and common-electrode any/half guard concurrency for both conditions. They distinguish changes in detections from mechanical changes in the active-electrode denominator. Baseline annotations, including full-2048-channel coincidence availability, remain separate. Neither comparison nor annotations perform censoring or unit acceptance.

`validate_sorting_comparison.py --report <comparison> --output <fresh-audit>` independently checks raw selections/means/counts, fixed masks, event-time pair matching and common-channel correlations, alongside the separately validated baseline packets. [W15B record](development/rounds/2026-11-24-07-w15b-shank2-sensitivity.md) owns observations and recommendation; working-run selection remains a separate decision.


## W15C shared-episode and away-stability contract

Both shank3 conditions use `save_preprocessed_copy=true`. The scientific settings are unchanged; the saved copy is a diagnostic output. Kilosort writes int16 scaled by 200 with original binary width, leaving omitted columns zero and potentially padding to full batches. Analyses divide saved values by 200, use common active channels and stop at original sample count. This is a quantized visualization copy, not calibrated voltage or exact internal float preprocessing; checking its readback does not prove absence of conversion overflow or recover lost input signal.

`review_w15c_shared.py --control <baseline> --exclusion <baseline> --output <fresh-report>` derives fixed source zones from W14 exact-flat intervals: core is >=256 of the original 512 shank3 electrodes, shoulder is the union of +/-500-sample core expansions minus core, and away is their complement. These descriptive thresholds are identical for both conditions and are not adopted masks. Each event retains its original sample index. The report records every cluster's zone counts and nominal rates with matching sample-exposure denominators, plus every contiguous core episode. Generic shared-signal warning availability is not changed by this separate diagnostic.

Raw zone means sample up to 64 complete chronological-rank events on eight nearest common channels. They use the baseline x1e6 and -100..-31 median convention, with correlation on offsets -20..40. Zone membership is based on the event center, so excerpts can cross boundaries. Detailed views select the union of the two longest and two most event-rich control episodes; they include +/-2500-sample context, raw b259/255/258/403/486, original flat concurrency, saved-preprocessing absolute p99 over the common 511 channels, and both event rasters. The independent `validate_w15c_shared.py --report <report> --output <fresh-audit>` reconstructs masks per electrode, verifies counts and raw means, and rereads saved preprocessing/source excerpt values.

`review_w15c_stability.py --shared <report> --output <fresh-report>` screens every exclusion automated-good cluster in four equal original-duration quarters, using only away-zone event centers. Counts use quarter-specific away exposure; raw means use at most 32 complete excerpts per quarter on the same eight common channels. The tool separately rereads each selected source excerpt. Missing quarters remain unavailable, not zero-valued waveforms. Pooled and quarter selections may overlap; correlation is descriptive, not independent unit validation. Away time is not guaranteed clean. [W15C record](development/rounds/2026-11-24-08-w15c-shank3-shared-episodes.md) owns observations, review coverage and limits.


## W15D run-selection checkpoint contract

`build_w15d_checkpoint.py --proposal configs/extra4_working_runs_w15d.proposed.json --output <fresh-report>` audits pinned checkpoint/manifest content, original candidate-run counts and labels, exclusion/global mapping, sample-axis agreement and complete run-qualified cluster inventory. It does not rerun sorting or scientific waveform analyses. `curation_inventory.csv` lists every proposed-run cluster, preserves automated labels and assigns only review priorities; it is not a curation decision ledger. All acceptance fields remain false and selection state remains proposed until explicit user selection. Shank0's frozen accepted release stays separate. Adoption must use a new accepted run-set record referencing checked manifests, retaining the proposal and original evidence unchanged. [W15D decision brief](development/rounds/2026-11-24-09-w15d-working-run-checkpoint.md) owns the recommendation, qualifications and next step.
## W16A generalized curation evidence contract

The accepted working-run registry is `configs/extra4_working_runs.v1.json`; its acceptance selects runs only. Frozen W15D proposal fields are historical. `curation_review.py --shank <zero-based-index> --output <fresh-report>` verifies the selected run manifest, baseline manifest and binary hash. `validate_curation_review.py --report <report> --output <fresh-audit>` checks the generated evidence independently. Completed output directories must not be overwritten.

Each cluster retains all original events and its automated label. Raw evidence uses at most 256 evenly spaced chronological-rank events with complete +/-100-sample context on eight nearest active physical channels; four equal original-sample-axis quarters use at most 128 each. Excerpts use x1e6 numerical scaling and per-event/channel median subtraction over offsets -100..-31, not calibrated microvolts. Missing means are NaN. Quarter/pooled samples can overlap. Correlations use offsets -20..40 across the eight channels. No censoring or exposure correction is applied.

Autocorrelograms retain all event pairs within +/-500 samples, removing exactly one self-pair per event while retaining distinct simultaneous events. Local Kilosort CCG R/Q calculations reproduce original good/mua labels (eligible populations exceed ten events with nonzero duration; good requires both R and Q below 0.2). These labels do not determine scientific acceptance.

The competitor screen inventories directed template similarities. For clusters with at least 20 events it selects up to two partners above absolute template cosine 0.05 plus the nearest qualifying spatial neighbor within 150 micrometers; sparse clusters use the nearest sufficiently populated neighbor within that distance. Pair evidence uses up to 256 raw events per cluster on twelve common active channels, central raw correlations, all cross-event time pairs without chance correction, and shared-physical-channel PC projections. A missing shared-PC projection is unavailable evidence. Balanced PC training uses at most 256 events per group; pinned pilot helpers own its implementation. These bounded screens cannot prove exhaustive isolation or establish merge decisions automatically.

The validator uses independent scalar raw reads, brute-force time-pair enumeration and physical-channel PC reconstruction. Transfer checks replay 15 frozen shank0 unit packets, 60 quarter summaries and all 58 automated labels/criteria; they do not replay every historical scientific judgment. Baseline annotations preserve original full-2048-channel coincidence definitions and assessment availability. Manual decisions, reasons, visual coverage and limitations belong to the [W16A record](development/rounds/2026-11-24-10-w16a-shank1-curation.md) and its complete proposal ledger. W16D separately owns future subset/policy acceptance.

## W16B raw exception review

`review_curation_exceptions.py --report <curation-report> --output <fresh-report>` preserves the W16A contract and adds event-level review evidence. It verifies input identities, then inventories every within-cluster adjacent interval below two nominal milliseconds and every baseline template-peak guard event. These categories can overlap. The complete sample-index inventory, flags, snippets and figure-page references are saved; nothing is censored.

Each snippet spans 100 samples before the first event through 100 after the second event (inclusive), using the first three nearest active channels in the audited unit packet. Complete snippets use float32 x1e6 scaling and per-channel median subtraction over the first 70 samples. Incomplete boundary snippets are clipped to the source extent, explicitly marked and left uncentered; they must not be compared as centered waveform means. Black/red dashed markers indicate the first/second event centers. Channel-by-channel scalar readback checks exact saved values. This verifies extraction, not neuronal origin, duplicate attribution or guard correctness; baseline guard validation remains separate.

W16B's additional c0/c1 supplement inventories all cross-pairs within +/-2 samples on b10/23/6/19, with the same complete-window scaling/centering and scalar readback. Its saved `checks.json` records the exact reconstruction recipe, original indices and flags. Its uncorrected coincidence evidence does not establish synchrony or merge identity. The [W16B record](development/rounds/2026-11-24-11-w16b-shank2-curation.md) owns scientific proposals, visual coverage and residual concerns; the complete ledger is authoritative for individual reasons. Future acceptance and event/exposure policies remain separate.
## W16C shared-exposure sensitivity

W16C adds `scripts/review_w16c_exposure.py`, a dated diagnostic for selected shank3. It verifies input manifests and reconstructs W15C's core (flat on at least 256 original channels) and +/-500-sample shoulder from W14 intervals. It computes cluster-specific counts and matching sample denominators for all time, away from core/shoulder, away plus padded peak-guard clearance, and away plus padded clearance on the eight nearest active physical channels used by the curation packet. This neighborhood is not an estimated unit footprint. Masks apply to event centers; raw windows may cross their edges. Away does not mean clean, and the rates are observed-event sensitivities, not corrected biological rates. No rule is adopted by running the script.

`exposure.csv` and `away_quarters.csv` preserve original-time counts/exposures; `unit_*.npz` preserves selected event indices and raw means. Selection is deterministic chronological rank, at most 128 complete windows per variant and 64 per away quarter. Windows use +/-100 samples, input x1e6, first-70-sample median baseline, and central -20..40-sample correlation against the existing pooled reference. Raw readback is checked for each selected window. `checks.json`, figures and `manifest.json` record provenance and limitations.

`scripts/checkpoint_w16c.py` packages explicitly authored manual reasons; it is not an automatic curation classifier. It independently checks count/exposure arithmetic using sorted interval unions and event-time searches, verifies quarter accounting, and emits a complete proposal ledger, summary, report and manifest. Both scripts require fresh result paths. Scientific adoption is separate: W16D must present subsets and matching event/exposure rules for explicit acceptance. See the [W16C dated record](development/rounds/2026-11-24-12-w16c-shank3-curation.md) for outcomes and visual coverage.

## W16D subset and policy proposal preview

`prepare_w16d.py` packages pinned W16A/B/C subsets and selected-run source annotations without adoption. `proposal.json` specifies the exact per-shank domains. `shank*_event_preview.npz` preserves all original event identities/flags and adds candidate, interior, shared-core/shoulder, primary-domain and proposed-inclusion Boolean fields. `analysis_intervals.npz` stores half-open included intervals. `unit_preview.csv`, `sensitivity.csv` and `omitted_event_preview.csv` distinguish original/proposed counts, exact omissions and matching sample/nominal/physical denominators. `all_cluster_proposals.csv` preserves all 128 decisions and reasons with acceptance false. Figures are proposal previews.

The proposed primary domain is [100,2999900) for shanks1–2 and that interior minus the W15C shared core/shoulder for shank3. Guard-clear sensitivities use the template peak or eight nearest active physical electrodes; they are not primary censoring or validated observable-time corrections. Event centers determine membership; raw windows may cross mask boundaries. Full-2048 coincidence semantics and unknown assessments remain intact. Rates describe observed events in the declared domain. Shank0's frozen policy is unchanged.

`validate_w16d.py` independently reconstructs the shared core, resolves physical-channel neighborhoods, uses interval unions and direct time membership to check all candidate scenarios, and verifies source identities, flags, omissions and nominal/physical rates. It writes a separate fresh audit; it does not mutate the preview manifest. Neither successful validation nor committing the proposal records scientific adoption. See the [W16D record](development/rounds/2026-11-24-13-w16d-acceptance-proposal.md) for effects, limitations and the explicit acceptance boundary.

## W16D accepted derived revision v1

`configs/extra4_shanks123_curated_v1.json` records explicit acceptance of both subsets and policies separately from the frozen proposal. `build_w16d_curated.py` requires that accepted state and pinned inputs; it writes fresh event/unit tables, an all-cluster ledger, original-axis exposure-aware bins and quarters, omission/quality records and raw waveform packets. Rates use matching interval-union exposures, with undefined rather than zero rates for zero-exposure bins. Unit IDs include recording, shank, run, original cluster and revision. No source labels, events or data are modified.

`validate_w16d_curated.py` audits CSV/NPZ identities and annotations against source arrays, resolves geometry independently, checks event inclusion and exposure arithmetic, and rereads raw values channel by channel for the saved selections and means. The prior proposal validator owns independent reconstruction of the adopted masks. The [accepted-round record](development/rounds/2026-11-24-14-w16d-accepted-derived.md) specifies outputs, checked counts and remaining limitations. Shank0 remains separately frozen; W17 must disclose the different adopted domains when combining revisions. Held clusters are deferred, not deleted or silently accepted.

## W17 four-shank release contract

`build_w17_release.py` combines accepted shank0 and W16D revisions into a fresh directory. It preserves native event fields in a union CSV schema, adds explicit shank0 aliases for common guards/context, and leaves unavailable revision-specific fields blank. The compact event NPZ contains identity/amplitude arrays; use CSV for annotations. Original sample time, run-qualified identities and distinct per-shank policy domains are retained. Local probe coordinates do not imply inter-shank geometry. Waveform packets are byte-identical copies of accepted packets.

The selected-run ledger filters the old shank0 ledger by run ID; its additional control-run row is retained separately as historical evidence. Every selected-run cluster remains accounted for without importing control clusters. Combined rate bins/quarters retain matching exposure and both time conventions. No new acceptance, merge or censoring occurs at assembly.

`validate_w17_release.py` audits native field preservation, source identities/amplitudes, all channel mappings, accepted domains, rates/counts, ledger accounting and raw means, and verifies the source HDF5 and four binary hashes. The immutable assembly manifest is followed by a separate audit; `configs/extra4_release.v1.json` records final release status and pins both. See the [W17 record](development/rounds/2026-11-24-15-w17-four-shank-release.md) for coverage, checked counts and preservation requirements.
