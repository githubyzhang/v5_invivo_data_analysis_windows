# Return package

Return `outputs/` plus the exact executed `scripts/`, `config.json`, geometry, original package manifest, environment lock and a concise `RUN_REPORT.md`. Hash every returned file with SHA-256 into a return manifest (excluding that manifest itself). Do not return `.venv`, pip caches or the 6.144 GB input binary unless needed for a changed-data investigation.

Keep the complete Kilosort output directory rather than selecting only spike times. It should include the installed version's spike times, spike clusters, amplitudes, templates, template/channel mappings, channel positions, `ops.npy`, `params.py`, cluster TSVs, logs, drift/diagnostic plots and any additional files needed by Phy. Some versions save pre-duplicate-removal arrays: do not mix them with final arrays. Document which arrays and masks were used. Preserve optional preprocessing copies if Phy references them, or explicitly explain how to regenerate them from the package binary.

`RUN_REPORT.md` must state:
- Exact input hash, recording, shank, dimensions, dtype and sampling convention.
- Hardware/software versions and the CUDA computation check.
- Fully resolved settings, preprocessing, numerical scaling, drift choices, exclusions and changes from baseline.
- Completion/failure, runtime and peak memory if available.
- Event and cluster counts; candidate automated 'good'/multiunit/noise labels versus manual judgments.
- Review evidence: waveform/footprint examples, amplitude stability, correlograms, drift and duplicate/artifact concerns.
- Full versus usable exposure for any rates or quality metrics; no short-interval quality claims inherited from the old 5 ms detector.
- Source-aligned integer sample indexing, output-bound checks and round-trip channel mapping.
- Limitations and recommendation: accept for Mac-side review, sensitivity run, or blocked.

Do not relabel clusters as confirmed neurons or delete original clusters. Unit IDs are local to this run. Windows absolute paths in Phy metadata will need relocation on Mac; retain the file contract and original relative binary path. The Mac project will analyze and decide adoption after review.
