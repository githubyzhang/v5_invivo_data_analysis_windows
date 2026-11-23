# Windows setup and evidence recovery

Updated: 2026-11-22. The only active project/repository root is `C:\Projects\invivo_extracellular_data_analysis`. The temporary nested `windows-kilosort` checkout has been flattened without changing Git history or uncommitted work. HEAD is `92da0b2c30c70132a8cd4f44a6bb545e59fc463f`, branch master, no remote.

## Local runtime

`.python` contains Python 3.12.10. `.venv` contains the unchanged pilot package set, `.venv-gui` adds Qt6 while referencing the local pilot packages, and `.venv-phy` contains independent Phy/Qt5 dependencies. Virtual environments were recreated locally, installed distributions copied without dependency resolution, and console launchers regenerated. All three package lists match the former worker and pass pip check. Their frozen lockfiles remain in the preserved evidence. No Mac environment is used.

**Current limitation:** Windows Smart App Control blocks FAISS `_swigfaiss.pyd` in both the original and relocated pilot environments (Code Integrity events 3033/3077). This prevents Kilosort imports and its GUI. CUDA calculations, Qt6 imports, Phy model/raw-waveform loading and CPU quality reports pass. Security policy was not changed, and no sorter run was repeated. Resolve the Windows policy/trusted-package issue before new sorting; do not mistake a passing pip check for a working Kilosort import.

PowerShell from the project root:

```powershell
$py = '.\.venv\Scripts\python.exe'
& $py -B -m pip check
& $py -B scripts/review_units.py --evidence worker_returns/extra4_shank0/pilot01/received --output results/extra4_shank0/NEW-REVIEW-NAME
# Optional inherited detector tests, with a Windows-local plotting cache:
$env:MPLCONFIGDIR = Join-Path $PWD 'results/matplotlib-cache'
& $py -B -m unittest discover -s tests
```

Use a new report output path every time. `report-manifest.json` is written last and marks completion. `pilot01-review01` is preserved as initial bootstrap evidence; `pilot01-review02-local` validates the consolidated environment. See [viewer instructions](viewers.md) for the root launch buttons and pending Kilosort limitation.

## Storage and preservation

- `data/extra4_shank0_float32.bin`: current local raw binary; 6,144,000,000 bytes, SHA-256 `11cd033eb0bda858f7598123a795f198078cc227d98d92543e8ea88f9e12eff0`. Never modify it.
- `configs/pilot01/`: byte-preserved config and original global/binary-channel geometry. Relative data paths are interpreted from the project root.
- `worker_returns/extra4_shank0/pilot01/`: frozen return ZIP, verified extraction, and original recovery record. Historical absolute paths in that recovery record describe the original operation and are not current dependencies.
- `worker_returns/worker-snapshot/`: entire former worker, including Git history, original environments, source data/results, viewer playground, later documentation and locks. This is ignored historical evidence, not an active project or environment. Its old absolute paths must remain unchanged.
- `viewing/pilot01-playground/`: migrated mutable viewer copy. Only copied params.py points to the root data; original output/labels remain preserved. New GUI runs stay under viewing/gui_runs.
- `results/migration-2026-11-22/`: complete before/after preservation manifest and migration checks. `get_started/`: original delivery package, ignored.

The old sibling worker path is no longer needed. Originals have been preserved in the snapshot rather than discarded. Source data, evidence, outputs, viewer caches and all environments are ignored; source/configuration/docs and small locks are versioned. Do not use old environment executables inside the snapshot. To recover another copy of the frozen pilot, `scripts/recover_pilot.py --worker worker_returns/worker-snapshot --destination worker_returns/NEW-RECOVERY` can be run using root `.venv`.

For future offline environment recreation, `scripts/create_local_environments.py --worker worker_returns/worker-snapshot` requires new destination runtime/environment directories and refuses existing ones. It copies distributions from the intact snapshot, regenerates paths/launchers, and compares against archived locks without executing the old source environments. This preserves versions but cannot resolve an OS policy block. Reinstallation from returned locks into new environments is another recovery option.

No original launcher was rerun. It assumes a complete original worker layout/transfer manifest; do not run it against the frozen return extraction. Any new sorting requires a distinct run name, resolved settings, source hashes and a recorded hypothesis. Other shanks and extra_5 sources are not in this Windows delivery.
