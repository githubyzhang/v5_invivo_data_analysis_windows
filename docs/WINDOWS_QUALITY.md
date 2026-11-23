# Windows pilot quality report contract

Scope: extra_4/shank0 pilot01, 3,000,000 samples and 512 channels. `scripts/review_units.py` is repeatable with explicit evidence and fresh output paths. Generalize dimensions, rates and run selection before applying it to another recording.

Inputs are final aligned arrays, automated labels, supplied channel mapping, archived readable resolved settings, raw per-second SD and historical per-electrode candidates. Positions are checked against the mapping. `kept_spikes` describes the pre-deduplication list and is checked but never reapplied. Inputs are not modified. Arrays load without pickle; serialized ops objects are not executed.

`cluster_review.csv`: one row per cluster; full-exposure nominal/physical rates, template peak binary/global channel, ISIs, amplitude stability and descriptive prior matches. ISI thresholds are <10/<20 samples; ACG bins are nominal 1 ms. Two-sample duplicate suppression, low counts and short recording duration limit refractory/contamination interpretation. Prior matches are many-to-many without chance correction, not accuracy or recall. Whitened templates and feature amplitudes are not calibrated voltages.

`curation_queue.csv`: original labels, review priorities, boundary/disturbance counts and pending decision fields. No decision is adopted. Copy into a new revision before editing; record source hashes, reviewer/date, old/new IDs, proposal/adoption state, rationale and evidence. Merges require explicit ID maps. Preserve original labels and sample indices. Cluster IDs do not identify matching neurons across recordings.

`exposure.json`: exact sample counts for the 12 high-variability seconds (median-channel SD >2x its temporal median). No exclusions applied. Outside-screen rate divides outside-screen events by 288 nominal seconds; corresponding physical exposure is 2,880,000/10,080 seconds. It is a descriptive comparison, not a replacement rate. Outside-screen does not mean clean. Prior shared-warning assessment covers only 35/300 seconds; flat guards are not calibrated clipping rails.

`index.html` links metrics and all 15 plot pages. `near_duplicates.json` reports similarity candidates, not automatic merges. `stability_bins.npz` stores 10-nominal-second counts/median amplitudes (missing values are NaN). `resolved_settings.json` retains the original Python JSON Infinity convention, not strict JSON. Original drift evidence remains in the return; it is not regenerated.

`provenance.json` records input/script SHA-256, interpreter and analysis-library versions. `report-manifest.json` hashes every generated file except itself and is written last. Source/config/sorter identity also resides in the verified return manifest and RUN_REPORT. CPU diagnostics do not establish new GPU validation or confirmed neuron identities.
