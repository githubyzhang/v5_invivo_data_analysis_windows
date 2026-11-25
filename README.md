# Independent Windows Kilosort4 analysis

This is the single Windows project root for Kilosort4 sorting and downstream activity analysis. The Mac custom detector runs alongside it as a separate candidate-detection and quality-annotation pipeline; its defaults are not Kilosort defaults.

Start with the [roadmap](docs/development/roadmap.md) for current status, pending decisions and the agreed next rounds. The [documentation map](docs/README.md) distinguishes active references from preserved history.

| Need | Reference |
| --- | --- |
| Windows environments and storage | [Windows setup](docs/development/windows-setup.md) |
| Reviewed four-shank extra_4 release v1 | [W17 report, revised](results/extra4/w17-report-revision02/index.html), [all 186 cluster decisions](docs/reviews/2026-11-24-w17-four-shank-ledger.csv), [release metadata](configs/extra4_release.v1.json) |
| Review methods and output contracts | [Windows quality reference](docs/WINDOWS_QUALITY.md) |
| Accepted shank0 result | [W12 report](results/extra4_shank0/w12-curated-v1/index.html), [decision ledger](docs/reviews/2026-11-24-w12-curation-ledger.csv), [W13 release](configs/extra4_shank0_release.v1.json) |
| Accepted shanks1–3 results | [W16D report](results/extra4/w16d-curated-v1/index.html), [decision ledger](docs/reviews/2026-11-24-w16d-accepted-curation-ledger.csv), [accepted subsets and policies](configs/extra4_shanks123_curated_v1.json) |
| Remaining-shank inputs and proposals | [W14 findings](docs/reviews/2026-11-24-w14-input-channel-review.md), [input/proposal metadata](configs/extra4_remaining_shanks_w14.proposed.json) |
| GUI/Phy viewing | [Viewer guide](docs/development/viewers.md); the Phy launcher opens a historical pilot copy |
| Current imported Mac detector | [Windows detector guide](docs/CUSTOM_PIPELINE_WINDOWS.md) |

Shank numbers are zero-based: shank0 is the first shank. Original integer sample indices are authoritative; nominal and physical sampling rates are distinct. Automated `good` labels and accepted *putative units* are not definitive neuron identities. Use one selected run per shank; do not mix alternative sorts of the same shank.

Preserve original data, outputs, labels, manifests and archives. `worker_returns/worker-snapshot` is historical evidence, not an active checkout. Use the root environments and fresh result paths. Data, environments and generated results are ignored by Git; committing their metadata does not back up those artifacts. See the [storage contract](docs/development/windows-setup.md#storage-and-preservation).

Root `analysis/`, `legacy/`, `requirements.txt` and the older detector documentation retain Mac history. Do not use their setup commands for the active Windows sorting environment. The [migration handoff](handoffs/windows-kilosort-independent/START_HERE.md) preserves the original transfer contract.
