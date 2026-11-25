# W17 - Reviewed four-shank extra_4 release v1

Date: 2026-11-24. State: **combined accepted release built and independently audited**. This completes the post-W14 reviewed-four-shank milestone. The user authorized W17 after committing W16D. Existing unit and policy acceptances are reused; no new unit decisions, merges, splits or censoring policies are introduced.

## Release outcome

The [release report](../../../results/extra4/w17-release-v1/index.html) combines the frozen shank0 revision with accepted shanks1–3. The [release metadata](../../../configs/extra4_release.v1.json) pins the assembly, audit and accepted inputs. The [complete selected-run ledger](../../reviews/2026-11-24-w17-four-shank-ledger.csv) contains every cluster's disposition and reason.

| Shank, zero-based | Original clusters | Accepted putative units | Deferred holds | Withheld | Analysis events | Accepted-subset omissions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 58 | 11 | 38 | 9 | 18,252 | 2 |
| 1 | 33 | 5 | 13 | 15 | 9,816 | 0 |
| 2 | 53 | 17 | 19 | 17 | 27,537 | 2 |
| 3 | 42 | 8 | 19 | 15 | 6,443 | 10 |
| Total | 186 | 41 | 89 | 56 | 62,048 | 14 |

Scope is all four shanks of the supplied `extra_4_signals.h5`: **2,048 channels x 3,000,000 samples**, verified directly from the HDF5 dataset. Nominal duration is 300 seconds at 10,000 Hz; physical duration is approximately 297.619048 seconds at 10,080 Hz. No extra_5/extra_6 or other recording is included. These are accepted *putative units*, not proof of 41 distinct biological neurons or complete recovery.

## Integration details and scientific boundaries

The old shank0 ledger contains 58 selected-run rows plus one historical control-run c36 row. The assembly's count check caught this extra row before release. The combined selected-run ledger filters by the actual run identity; the control row is preserved separately in `historical_control_ledger.csv`. It remains review history, not a 187th selected-run cluster. The incomplete first assembly is retained under `results/extra4/w17-build-incomplete01`; it has no release manifest and is not the released output. No frozen input was changed to repair this integration issue.

Combined event records preserve every native quality field from the accepted revisions. Shank0 additionally receives explicit common aliases: `active_guard_any` to `any_active_guard`, `active_guard_ge50` to `half_active_guard`, and `boundary` to `incomplete_context`. Original names remain present. Union-schema blanks mean not supplied by that revision, never false, clean or zero. `schema.json` documents this distinction. Shank0 global peak IDs are resolved through the verified physical-channel map rather than inferred from cluster IDs.

Original sample indices, source event indices, cluster IDs and run-qualified unit IDs remain intact. Four separate sorts remain four separate sorts. Local x/y coordinates are not an inter-shank geometry model; no cross-shank neuron uniqueness or merge is inferred. The 2,048 original channel IDs form a complete nonoverlapping mapping across four 512-channel inputs.

Shanks0–2 retain the accepted interior [100,2999900), or 2,999,800 samples per unit. Shank3 also excludes documented shared-flat core/shoulder intervals, leaving 2,918,240 samples. Exposure is per unit, not an additive recording duration. Rates remain observed-event rates within those domains. Shared-loss gaps cannot establish neuronal silence; remaining exposure is not certified clean. Full-2048-channel coincidence meanings, unknown assessments and residual quality limitations remain unchanged. Deferred holds stay outside this subset; a future review can produce a new version without overwriting v1.

## Outputs and reproducibility

The release supplies combined `spikes.csv` / identity-and-amplitude `spikes.npz`, `units.csv`, `curation_ledger.csv`, `omitted_events.csv`, `rate_bins.csv`, `quarters.csv`, `analysis_intervals.npz`, `channel_map.csv`, schema/provenance records and an overview raster. **Quality flags are in the CSV**; the compact event NPZ is an identity/amplitude representation, not a replacement for annotated CSV. Forty-one copied waveform packets are byte-identical to their accepted source packets, preserving their exact selection and mean semantics. Detailed waveform/amplitude/quality reports remain linked to the original accepted outputs.

```powershell
.venv\Scripts\python.exe scripts/build_w17_release.py --output results/extra4/w17-release-v1
.venv\Scripts\python.exe scripts/validate_w17_release.py --report results/extra4/w17-release-v1 --output results/extra4/w17-validation01
```

Use fresh result paths for reproduction. The builder verifies W13's **payloads** map and W16D's **pinned_files** map separately; their provenance schemas differ. The release's assembly summary records its pre-audit state; the separate audit and tracked release metadata establish successful completion without rewriting the assembled manifest.

The independent validator passed **62,048 event identities, 41 unit summaries, 1,230 bins, 164 quarters, 186 selected-run clusters and 14 omitted identities**. It checks native event-field preservation against accepted CSVs, source sorter event arrays/amplitudes and both time conventions; resolves template peaks and physical channel maps; reconstructs domain membership and bin exposure; and rereads **28,593 raw waveform windows** to reproduce pooled and quarter means. All 41 waveform packet hashes match their sources. The source HDF5 content hash and all four binary hashes match their recorded identities. Original frozen revision hashes remain unchanged. The combined raster was visually inspected; report links were checked. These are reproducibility checks, not additional biological validation.

## Preservation and next work

The release is a local, content-hash-frozen artifact, not an externally published dataset or proof of backup. Git stores code, compact decisions and metadata; ignored source/data/results require separate preservation. Retain the source HDF5, four binaries/maps, selected sorter outputs, W13 and W16D accepted artifacts and their transitive pinned evidence, plus this release and its audit. `artifact_inventory.csv` indexes the frozen provenance roots; each root's manifests identify the underlying payloads. The [storage contract](../windows-setup.md#storage-and-preservation) remains authoritative.

The agreed W17 milestone is complete. There is no automatic next sorting or held-cluster review round. Next work should be a separately scoped scientific analysis or later focused hold review. Any changed unit membership or policy requires a new explicit accepted revision; preserve v1 and its limitations. Do not interpret the deferred 89 clusters or withheld 56 as proof of absent neuronal activity.
