# Independent Windows Kilosort4 analysis

This is the single Windows project root. It develops Kilosort4 sorting and downstream activity analysis independently of the Mac detector, while preserving common Git history and scientific provenance.

Start with the [roadmap](docs/development/roadmap.md), [Windows setup](docs/development/windows-setup.md), [viewers](docs/development/viewers.md), and [quality-report contract](docs/WINDOWS_QUALITY.md). The [migration handoff](handoffs/windows-kilosort-independent/START_HERE.md) owns the shared data contract. [Documentation conventions](docs/README.md) describe project upkeep.

The preserved extra_4/shank0 pilot has 39,620 events, 59 clusters (24 automated good, 35 mua), with no human curation. Open the [local quality report](results/extra4_shank0/pilot01-review02-local/index.html) or the [frozen RUN_REPORT](worker_returns/extra4_shank0/pilot01/received/RUN_REPORT.md). Original data, output arrays and labels remain unchanged. These local artifacts are ignored by Git.

Data, Python environments and viewer launchers are now inside this root; the old sibling worker is preserved under ignored `worker_returns/worker-snapshot`. The original transfer package remains in `get_started`. No remote is configured and no changes were published.

**Runtime status:** CPU reports and Phy raw-waveform loading work, and CUDA checks pass. Windows Smart App Control currently blocks the FAISS DLL needed by Kilosort, including in the old environment. New sorting and the Kilosort GUI await resolution of that system-policy issue; see setup. Security settings have not been changed.

Integer sample indices are authoritative; nominal sampling is 10,000 Hz and physical sampling 10,080 Hz. Automated good labels are not confirmed neurons. No masking, merging, resampling or relabeling has been adopted. Other-shank/extra_5 expansion needs source data and pilot acceptance; extra_6 and stimulation-period handling remain deferred.

Inherited `analysis/`, `legacy/`, `requirements.txt`, detector methods and tests belong to the Mac candidate-detection track. See [its historical progress](docs/PROGRESS.md) and [methods](docs/METHODS.md); those scientific defaults are not Windows sorting defaults.
