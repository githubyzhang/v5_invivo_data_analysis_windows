# Windows pilot quality report contract

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
