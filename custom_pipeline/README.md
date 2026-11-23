# Custom detector alongside Windows Kilosort

`mac_2026_11_23/` is the unchanged, manifest-bound source/test/reference-document subset of the 2026-11-23 Mac handoff. It is an independent electrode-candidate pipeline, not Kilosort preprocessing. Its package root is isolated in a subprocess to prevent collisions with the older root `analysis/` module. Do not import the two analysis trees into the same Python process.

Use the root [Windows launcher](../scripts/run_custom_pipeline.py) and dedicated `.venv-detector`. The [integration guide](../docs/CUSTOM_PIPELINE_WINDOWS.md) owns supported commands and contracts. `UPSTREAM_FILES.json` pins each imported file to its package hash; `.gitattributes` preserves exact bytes across checkout. Put adaptations in root `scripts/` rather than editing these upstream files.

The complete 106-file handoff, original manifest, START_HERE, Mac reports and saved fixtures are preserved under ignored `worker_returns/mac-current-pipeline-2026-11-23/received/`. It is a snapshot without Git metadata or an environment, not a second active checkout. The bundled standalone reference verifier expects the full package layout and should be run from that preserved package using `.venv-detector`; active production commands use this source subset.

Upstream research tools and documents are retained for context. Their historical Mac paths, missing historical report links and optional calibrations are not configured Windows entry points. The supported Windows launcher provides adaptive MA50 detection and standalone named-profile annotation. Fixed mode needs deliberate calibration/provenance migration and has not been enabled by this integration.
