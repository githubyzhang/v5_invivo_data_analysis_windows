# W8 follow-up — Working run selected

Date: 2026-11-23. State: user adopted the channel-248-excluded run for continued work.

The user explicitly chose `w7b-exclude248-01` following clarification of within-run neighbor review versus cross-run correspondence. Recorded the choice in [working-run metadata](../../../configs/extra4_shank0_working_run.json), pinned to its output manifest. This run contains 38,687 events and 58 clusters, with original automatic labels of 19 good / 39 mua.

This decision selects a run, not a curated cluster set. The four W8 candidate recommendations and all other cluster decisions remain pending. All 58 clusters remain available for curation. Do not mix in clusters from the all-channel run; preserve it and the frozen pilot as reference evidence. No merging, deletion, relabeling, temporal mask or new sorting was performed.

Going forward, identify clusters as `without-248 / cluster N` or `all-channel / cluster N`. Label comparisons explicitly as within-run neighbor review or cross-run matching. This prevents overlapping numeric IDs from implying either identity or a merge.

The preserved W8 proposal packet remains a record of the earlier proposed state. The roadmap and working-run metadata record this subsequent adoption. Verified the selected run's manifest and its payload hashes; no result artifacts changed. No commit or push performed.
