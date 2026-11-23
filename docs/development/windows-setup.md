# Windows setup and evidence recovery

Updated: 2026-11-23. The only active project/repository root is `C:\Projects\invivo_extracellular_data_analysis`. The temporary nested `windows-kilosort` checkout has been flattened without changing Git history. Shared checkpoint: `92da0b2c30c70132a8cd4f44a6bb545e59fc463f`; branch master, no remote. Later local commits retain that ancestry. The current Mac detector now has its own `.venv-detector`, source subset and root launcher; [its integration guide](../CUSTOM_PIPELINE_WINDOWS.md) owns setup and commands. It does not change the Kilosort environments.

## Local runtime

`.python` contains Python 3.12.10. `.venv` contains the pilot package set with FAISS changed from 1.16.0 to 1.13.2 to resolve the Windows DLL block. `.venv-gui` adds Qt6 and references those local pilot packages; `.venv-phy` is unchanged. Active sorting and GUI locks are [requirements-windows-lock.txt](../../requirements-windows-lock.txt) and [requirements-windows-gui-lock.txt](../../requirements-windows-gui-lock.txt). Original locks remain frozen in the evidence; do not overwrite them. Both active environments pass pip check. No Mac environment is used.

**Resolved:** Smart App Control rejects the published FAISS 1.16.0 DLL on this machine but accepts the compatible 1.13.2 release. FAISS is the only changed dependency; Kilosort remains 4.1.7 and Torch remains 2.11.0+cu128. Nearest-neighbor results match NumPy, Kilosort's graph calculation and CUDA pass, and the GUI constructs/closes offscreen with explicit local INI settings. Smart App Control remains enabled; no security policy or installed upstream code was patched. This is runtime validation, not proof that future sorting is bitwise equivalent to the original pilot.

To apply the repair after restoring the historical environment:

```powershell
& ./.venv/Scripts/python.exe -B -m pip install --no-deps faiss-cpu==1.13.2
& ./.venv/Scripts/python.exe -B -m pip check
& ./.venv-gui/Scripts/python.exe -B scripts/check_sorting_runtime.py --gui --output results/NEW-RUNTIME-CHECK.json
```

For offline repair, use the retained wheel under `results/dll-repair-2026-11-22/wheels/` with `--no-index --no-deps`. Its SHA-256 is recorded in the repair round. A full recreation needs the matching CUDA PyTorch distribution from its cu128 index as well as the active lock. Avoid an unpinned FAISS upgrade; preserve changed versions in every future run's environment metadata.

PowerShell from the project root:

```powershell
$py = '.\.venv\Scripts\python.exe'
& $py -B -m pip check
& $py -B scripts/review_units.py --evidence worker_returns/extra4_shank0/pilot01/received --output results/extra4_shank0/NEW-REVIEW-NAME
# Optional inherited detector tests, with a Windows-local plotting cache:
$env:MPLCONFIGDIR = Join-Path $PWD 'results/matplotlib-cache'
& $py -B -m unittest discover -s tests
```

Use a new report output path every time. `report-manifest.json` is written last and marks completion. `pilot01-review01` is preserved as initial bootstrap evidence; `pilot01-review02-local` validates the consolidated environment. See [viewer instructions](viewers.md) for the root launch buttons.

## Storage and preservation

- `data/extra4_shank0_float32.bin`: current local raw binary; 6,144,000,000 bytes, SHA-256 `11cd033eb0bda858f7598123a795f198078cc227d98d92543e8ea88f9e12eff0`. Never modify it.
- `configs/pilot01/`: byte-preserved config and original global/binary-channel geometry. Relative data paths are interpreted from the project root.
- `worker_returns/extra4_shank0/pilot01/`: frozen return ZIP, verified extraction, and original recovery record. Historical absolute paths in that recovery record describe the original operation and are not current dependencies.
- `worker_returns/worker-snapshot/`: entire former worker, including Git history, original environments, source data/results, viewer playground, later documentation and locks. This is ignored historical evidence, not an active project or environment. Its old absolute paths must remain unchanged.
- `viewing/pilot01-playground/`: migrated mutable viewer copy. Only copied params.py points to the root data; original output/labels remain preserved. New GUI runs stay under viewing/gui_runs.
- `results/migration-2026-11-22/`: complete before/after preservation manifest and migration checks. `get_started/`: original delivery package, ignored.

The old sibling worker path is no longer needed. Originals have been preserved in the snapshot rather than discarded. Source data, evidence, outputs, viewer caches and all environments are ignored; source/configuration/docs and small locks are versioned. Do not use old environment executables inside the snapshot. To recover another copy of the frozen pilot, `scripts/recover_pilot.py --worker worker_returns/worker-snapshot --destination worker_returns/NEW-RECOVERY` can be run using root `.venv`.

For future offline environment recreation, `scripts/create_local_environments.py --worker worker_returns/worker-snapshot` requires new destination runtime/environment directories and refuses existing ones. It restores the historical package versions including FAISS 1.16.0, regenerates paths/launchers, and checks archived locks without executing old environments. Apply the FAISS repair above afterward; active and historical locks intentionally differ.

No original launcher was rerun. It assumes a complete original worker layout/transfer manifest; do not run it against the frozen return extraction. Any new sorting requires a distinct run name, resolved settings, source hashes and a recorded hypothesis.

## Source recordings located on Windows

User-supplied source directory (2026-11-22): `C:\DATA\cnea_data\invivo\26-11-06\0192`. Treat its contents as read-only. Read-only HDF5 header inspection confirms `extra_4_signals.h5`, `extra_5_signals.h5` and `extra_6_signals.h5` each contain float16 `signals` shaped `(2048, 3000000)`. The directory also contains earlier recordings/reference files and injection recordings. Injection-pattern signals have shapes `(2048, 24000000)` and `(2048, 9000000)` and remain separate scope.

These sources make other-shank/extra_5 export possible after pilot review. W6 established the full extra_4 HDF5 SHA-256 (`3bedaa51bca65205dcc81e25ef48f249c9f1ea34346f4cfd7327e26269bd9755`) and exact agreement of every mapped shank0 value with the verified pilot binary; native custom-detector arrays also match the Mac fixture. extra_5/6 header inspection alone is not full content/hash verification; establish their source hashes and mapping/export checks before new runs. The shank0 binary remains the pilot's authoritative sorting input. extra_6 and stimulation-period work remain deferred.

## Reproduce targeted Round 1 evidence

Use root `.venv`; choose a new output name. This reads the verified local binary and frozen results without running Kilosort or changing labels:

```powershell
& ./.venv/Scripts/python.exe -B scripts/review_pilot_round1.py --evidence worker_returns/extra4_shank0/pilot01/received --binary data/extra4_shank0_float32.bin --output results/extra4_shank0/NEW-ROUND1-REVIEW
& ./.venv/Scripts/python.exe -B scripts/validate_round1_review.py --report results/extra4_shank0/NEW-ROUND1-REVIEW --evidence worker_returns/extra4_shank0/pilot01/received --binary data/extra4_shank0_float32.bin
& ./.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_round1_review.py
```

The mechanical generator does not make curation decisions. Complete visual review, add findings/proposals and refresh the report manifest before handing off a finished packet. The finalized 2026-11-23 packet is `results/extra4_shank0/pilot01-round1/`; its methodology and file schemas are in [the quality contract](../WINDOWS_QUALITY.md#targeted-round-1-raw-review).
## Reproduce Round 2 evidence

Use a fresh output path for every execution. The completed reviewed packet is `results/extra4_shank0/pilot01-round2-reviewed`; `pilot01-round2` is an intermediate rendering. From the project root:

```powershell
$env:MPLCONFIGDIR = Join-Path $PWD 'results/matplotlib-cache'
& ./.venv/Scripts/python.exe -B scripts/review_pilot_round2.py --evidence worker_returns/extra4_shank0/pilot01/received --binary data/extra4_shank0_float32.bin --output results/extra4_shank0/pilot01-round2-new --source-h5 C:/DATA/cnea_data/invivo/26-11-06/0192/extra_4_signals.h5
& ./.venv/Scripts/python.exe -B scripts/validate_round2_review.py --report results/extra4_shank0/pilot01-round2-new --evidence worker_returns/extra4_shank0/pilot01/received --binary data/extra4_shank0_float32.bin
& ./.venv/Scripts/python.exe -B scripts/review_pilot_clipping_guard.py --evidence worker_returns/extra4_shank0/pilot01/received --binary data/extra4_shank0_float32.bin --output results/extra4_shank0/pilot01-round2-new/clipping-guard
& ./.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_round2_review.py
```

Run the independent audit before adding the guard supplement or reviewed prose. Each refuses overwriting its existing destination. The HDF5 option performs a bounded read-only source comparison, not full-source hashing. Guard replay imports the inherited flat-mask helpers; it does not run the Mac detector or change Kilosort settings. After visual review, add findings and pending proposals separately, then refresh the root SHA-256 manifest recursively to include every file except the root manifest itself. The [quality contract](../WINDOWS_QUALITY.md#round-2-pair-disturbance-and-guard-review) defines the evidence and its limits.
