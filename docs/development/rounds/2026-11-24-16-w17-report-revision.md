# W17 follow-up - Combined decision tables and corrected unit export

Date: 2026-11-24. State: presentation revision 2 validated; scientific release v1 unchanged. The user requested a per-shank accepted/hold/withhold summary with cluster counts and IDs, an all-cluster reason/evidence table, and correction of the inconsistent 41-unit spreadsheet columns.

The [revised report](../../../results/extra4/w17-report-revision02/index.html) is the current presentation entry point. It retains the frozen release's figures, data links and scientific limitations, adds 12 shank/decision summary rows with explicit IDs, and displays all 186 selected-run clusters grouped by shank. Each row shows original cluster ID, original automated label, original event count, current decision, reason and a waveform evidence link. A text filter searches shank, cluster, label, decision and reason. Counts in this table are original sorter counts, not accepted-domain event counts. Historical evidence captions remain historical; current decisions are taken from the accepted combined ledger.

Waveform links resolve to W12 accepted shank0 figures, W9 held-good shank0 figures, W10 shank0 mua screens, and W16A/B/C screens for shanks1–3. Multi-cluster screen links identify the row containing the cluster. Boundary-only or sparse clusters remain linked to the evidence that explains missing complete raw context. The historical control cluster remains outside the 186 selected-run rows. No new review or unit decisions were made.

## Corrected unit table

The original W17 unit CSV unioned two source schemas, retaining duplicate names and leaving avoidable blanks. This was a presentation/export defect. The new `units.csv` uses 32 consistent fields for all 41 units; `units.xlsx` provides the same values with typed numeric cells, filtering, frozen identifiers/header and a Definitions worksheet.

Original good/mua labels are recovered from each selected sorter's `cluster_KSLabel.tsv` rather than guessed from acceptance. All 41 happen to be good. Common quality counts are recomputed from retained event annotations, including the previously absent shank0 guard/availability counts. Duplicate legacy count aliases are removed from this corrected table; all original fields remain preserved in frozen W17. Boundary omissions are distinguished from shared-policy omissions. All analysis counts, rates, exposures, unit identities and amplitude medians are retained.

Generic shared assessment is explicitly `not_assessed` for every shank. The separate W15C core/shoulder assessment is `available` only for shank3 and `not_assessed` elsewhere. A zero shared-policy omission count on another shank means no such exclusion was applied, not that the signal was assessed clean. Column definitions state that quality counts concern retained analysis events and can overlap. No blank was converted to zero merely to make the sheet look complete.

## Verification and provenance

`scripts/revise_w17_report.py` verifies frozen release pins, joins decisions by shank/run/cluster, obtains event counts directly from original cluster arrays, checks waveform targets and hashes them, reconciles the corrected unit counts against retained events and checks both rate conventions. It writes a fresh report directory. `scripts/export_w17_units.mjs` uses the bundled Artifact Tool to export the corrected numeric records; no existing workbook or source result is overwritten. Local workbook staging is under ignored `outputs/w17-report-review` and uses a junction to bundled dependencies.

Checks passed for **186 cluster rows, 12 decision-summary rows, 41 units, 62,048 retained events, 48 distinct evidence images and 202 local links**. Direct inspection of the exported XLSX XML verified all **1,312 data cells and 32 headers** against the corrected JSON/CSV records. Workbook checks found no formula errors; the numeric table is a static accepted-results export. Unit-sheet and definition-sheet previews were inspected. The original W17 manifest still verifies unchanged. No browser-native Excel interaction or filter UI test was performed.

The [presentation metadata](../../../configs/extra4_report_revision02.json) pins code, workbook/report outputs, checks and this record separately from `extra4_release.v1.json`. This changes presentation and the unit-export schema only; it does not revise scientific acceptance, source data, 41 accepted units, 62,048 events, policies or deferred holds. Continue the user's report review from the revised entry point. Generated files still need preservation outside Git.
