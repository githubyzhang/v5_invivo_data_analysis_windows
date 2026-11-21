# Kilosort4 Windows worker package

Date: 2026-11-21. State: package prepared and export verified; Windows sorting not yet run.

The user selected Kilosort4 and a split workflow: Mac remains the research home; the Windows Area-51 desktop is the compute worker. The user confirmed the legacy four-shank arrangement and 30 µm vertical/horizontal electrode center spacing. The first assignment is extra_4, physical shank 1 (zero-based shank0), 512 channels across all 3,000,000 original samples. extra_5 and additional shanks await pilot review.

The portable assignment is built from [handoff sources](../../../handoffs/kilosort4-extra4-shank0/START_HERE.md) by `analysis/prepare_kilosort_worker.py`. Destination: `/Volumes/YZ/kilosort4-extra4-shank0-worker-2026-11-21/`. It includes continuous float32 binary data, row/column geometry and original channel mapping, previous detections/quality metadata, worker instructions, documentation-workflow guide, baseline launcher, verification script and return checklist. Nominal 10,000 Hz / physical 10,080 Hz conventions and original sample coordinates are retained.

The binary is a lossless float16-to-float32 cast with no preprocessing. The diagnostic baseline delegates preprocessing to Kilosort4; configuration choices are starting settings, not validated optimal settings. The Windows worker must verify GPU/CUDA, resolve and freeze exact dependency versions, inspect geometry/data, and review output quality. The dependency input is explicitly not a lockfile. No Kilosort/GPU execution is claimed on Mac.

## Interruption recovery

The client reported `Bad Request` interruptions. The message alone does not identify the failing service or prove a client-version cause. After a restart, the export process was absent and 200,000 samples remained in the partial binary. Resume support verifies the entire existing prefix against the source before appending. Final publication requires a full binary hash readback, source sample checks and manifest creation. Never run two writers against the same package; an existing completed manifest prevents resume.

The resumed export completed. The package totals 6,149,074,388 payload bytes, including the 6,144,000,000-byte binary. A full binary SHA-256 readback matched the export stream; eight sample positions across all 512 channels matched the source exactly. The mapping bijection and synthetic binary-layout fixture passed. All small payload hashes, guide-copy identity, and the 512 unique electrode coordinates were checked. The manifest is copied locally to `results/kilosort_worker_package/manifest.json`. No source recording or existing detection output was modified.

Binary SHA-256: `11cd033eb0bda858f7598123a795f198078cc227d98d92543e8ea88f9e12eff0`.

## Next

Transfer the completed folder to Windows SSD, open it as a project and start at START_HERE.md. Return the complete sorter output, executed configuration/scripts, environment lock, report and hashes to the Mac project. Neuron labels remain provisional pending review.
