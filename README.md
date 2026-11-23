# Independent Windows Kilosort4 analysis

This is the single Windows project root. It develops Kilosort4 sorting and downstream activity analysis independently of the Mac detector, while preserving common Git history and scientific provenance.

Start with the [roadmap](docs/development/roadmap.md), [Windows setup](docs/development/windows-setup.md), [viewers](docs/development/viewers.md), and [quality-report contract](docs/WINDOWS_QUALITY.md). The [migration handoff](handoffs/windows-kilosort-independent/START_HERE.md) owns the shared data contract. [Documentation conventions](docs/README.md) describe project upkeep.

The preserved extra_4/shank0 pilot has 39,620 events, 59 clusters (24 automated good, 35 mua), with no human curation. Open the [local quality report](results/extra4_shank0/pilot01-review02-local/index.html) or the [frozen RUN_REPORT](worker_returns/extra4_shank0/pilot01/received/RUN_REPORT.md). Original data, output arrays and labels remain unchanged. These local artifacts are ignored by Git.

Data, Python environments and viewer launchers are now inside this root; the old sibling worker is preserved under ignored `worker_returns/worker-snapshot`. The original transfer package remains in `get_started`. No remote is configured and no changes were published.

**Runtime status:** The Windows DLL issue is resolved in the active environments with FAISS 1.13.2. Kilosort 4.1.7 imports, nearest-neighbor calculations, CUDA and offscreen GUI startup pass. Smart App Control remains enabled. The historical pilot retains FAISS 1.16.0 provenance; no sorting was repeated. See [the repair round](docs/development/rounds/2026-11-22-03-windows-dll-repair.md).

Integer sample indices are authoritative; nominal sampling is 10,000 Hz and physical sampling 10,080 Hz. Automated good labels are not confirmed neurons. No masking, merging, resampling or relabeling has been adopted. Other-shank/extra_5 expansion needs source data and pilot acceptance; extra_6 and stimulation-period handling remain deferred.

Inherited `analysis/`, `legacy/`, `requirements.txt`, detector methods and tests remain historical Mac candidate-detection sources. The verified current Mac pipeline now runs separately under `custom_pipeline/` with `.venv-detector`; see the [Windows custom-pipeline guide](docs/CUSTOM_PIPELINE_WINDOWS.md). Native extra_4 detection reproduces the Mac candidate arrays exactly. Its new quality sidecar annotates the frozen Kilosort pilot without changing sorting, labels or events. Detector defaults are not Windows sorting defaults.
