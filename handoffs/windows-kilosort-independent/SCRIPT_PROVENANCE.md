# Imported script provenance

`scripts/review_units.py` derives from frozen worker `scripts/review_pilot.py`, dated 2026-11-21, SHA-256 `56cadc7b3aec252b91e30bcd0237ba24fe221fdf29a0758fcf281a1e2e456d1b`.

Return archive SHA-256: `087ba85cb9c195a9e1b401b8dc0f46d1969537e0f728addde33a72cc0f4df73d`. The original script remains in recovered evidence; all 169 payloads were verified. Changes add explicit paths, overwrite protection, all-cluster plots, recomputed boundary/disturbance screens, a pending curation queue, HTML and hashed provenance. Pickled ops loading and recreated ops inventory/drift plots were removed; original evidence remains preserved.

Core metrics and prior-detector comparison are unchanged and compared against the archived CSV. This implementation is pilot-scoped. `recover_pilot.py` is new recovery code. The returned environment lock is byte-preserved.

2026-11-22 consolidation: root `scripts/launch_kilosort.py` adapts the later worker `viewing/launch_kilosort.py`, preserved byte-for-byte under `worker_returns/worker-snapshot/` and inventoried in `results/migration-2026-11-22/worker-before.json`. It reads root configs/data, uses a fresh local Qt settings directory and chooses distinct exploration paths. Root CMD launchers use rebuilt local environments. `create_local_environments.py` and `verify_tree.py` document the offline environment and preservation procedures. These additions do not alter archived pilot scripts or defaults.
