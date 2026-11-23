# Windows custom detector integration

The latest Mac detector runs alongside the independent Kilosort workflow. It produces electrode-level candidate eAPs and quality annotations, not sorted units. Neither candidate counts nor warning counts measure neuron yield or biological accuracy. The single [roadmap](development/roadmap.md) tracks status; [W6](development/rounds/2026-11-23-03-custom-pipeline-integration.md) records native acceptance.

## Source and environment

The 2026-11-23 handoff has 106 payloads pinned by `PACKAGE_MANIFEST.json`, SHA-256 `7b6ae7b17c22f3a00d67ccf4e1c0ea5eb6526188ebccd0f3cf684cc96d1911f8`. Generating Mac HEAD is `fbe30269513ed21318efd901afebee3086e755d9`, with uncommitted working-tree content included; the manifest, not HEAD alone, identifies the exact package. The complete verified package lives under `worker_returns/mac-current-pipeline-2026-11-23/received/`. It contains no raw recordings or Git checkout.

`custom_pipeline/mac_2026_11_23/` contains 45 unchanged upstream source/test/document files with per-file hashes. Existing root `analysis/`, historical guard helpers and all frozen Kilosort outputs are preserved. `scripts/run_custom_pipeline.py` verifies this subset before execution and invokes it in a subprocess with a distinct import root.

Use `.venv-detector`, created from the root Python 3.12.10 runtime. The Mac package's four requested versions installed unchanged on Windows: NumPy 2.4.6, SciPy 1.17.1, h5py 3.16.0 and Matplotlib 3.11.2. Mac used Python 3.11; native numerical equivalence is tested rather than assumed. [The Windows detector lock](../requirements-windows-detector-lock.txt) pins transitive dependencies. Do not install it into `.venv`, `.venv-gui` or `.venv-phy`.

For a new environment only:

```powershell
& ./.python/python.exe -m venv .venv-detector
& ./.venv-detector/Scripts/python.exe -m pip install -r requirements-windows-detector-lock.txt
& ./.venv-detector/Scripts/python.exe -m pip check
```

## Supported execution

From the project root, use a new output name within `results/custom_detector/`:

```powershell
& ./.venv-detector/Scripts/python.exe -B scripts/run_custom_pipeline.py detect --input C:/DATA/cnea_data/invivo/26-11-06/0192/extra_4_signals.h5 --output results/custom_detector/extra4_NEW
& ./.venv-detector/Scripts/python.exe -B scripts/run_custom_pipeline.py annotate --input worker_returns/mac-current-pipeline-2026-11-23/received/reference_outputs/extra4/spikes.h5 --output results/custom_detector/reference_extra4_NEW
```

The detector uses generic `--input`, adaptive MA50 and no import of old source-bound signal masks. The launcher hashes the input before/after, validates upstream bytes, captures a log and writes a sibling `NAME.launch.json` containing command, source/environment/adapter identities and completion. The upstream `pipeline_progress.json` separately tracks detection and coincidence completion. Preserve failed/partial runs; choose a fresh name to restart. Annotation failure leaves completed spikes intact, so standalone annotation can recover without redetection. No implicit overwrite or resume exists.

`--profile broad` is the default; `tight` selects the other display alias while saving both. `--min-channels` is explicitly recorded; it is never silently lowered from 1024. Inputs are converted floating HDF5 `signals`, ordered `(channels,samples)`, with original zero-based channel IDs and nominal 10,000 Hz / physical 10,080 Hz. No raw uint16 conversion, retiming or arbitrary-rate support is added.

## Method boundaries

The inherited [methods](../custom_pipeline/mac_2026_11_23/docs/METHODS.md) and [output contract](../custom_pipeline/mac_2026_11_23/docs/OUTPUTS.md) define detector behavior. MA50 subtracts a 25-before/current/24-after baseline. Exact-flat runs ≥10 samples receive ±500-sample guards; these exclude channel-time from noise estimation and candidate selection. Noise uses per-second centered MAD/0.67448975, requiring at least half the window and 250 usable samples. Threshold is five times the maximum of channel noise and the across-valid-channel median floor. Negative peaks receive amplitude-priority 50-sample spacing across the whole channel. This is not a neuronal refractory-period definition.

Keep three warning sources distinct:

| Source | Support | Meaning in this integration |
| --- | --- | --- |
| Per-channel flat guard | Individual electrode intervals | Excluded by the custom detector; diagnostic overlap only for Kilosort |
| Baseline/broadband signal warnings | Historical research covers 35/300 seconds | Preserved in reference fixtures; generic native runs mark them unavailable rather than silently importing them |
| Candidate coincidence | Every full supported window across the recording | New annotation-only tight (10 samples / 5%) and broad (50 samples / 5%) profiles; no candidates removed |

Coincidence counts distinct active channels divided by channels observable throughout each whole sliding window, requiring ≥1024 eligible channels. Every integer window start is evaluated; qualifying full half-open windows are unioned without extra padding. All candidates inside those intervals are flagged, including noncontributing channels. Availability remains explicit. This feature does not complete full-recording signal-based assessment, recover threshold-suppressed candidates or prove artifact origin. Named broad/tight settings are the current Mac defaults; the older research 5 ms / 50% setting is not substituted for them.

## Kilosort annotation adapter

```powershell
& ./.venv-detector/Scripts/python.exe -B scripts/annotate_kilosort_from_custom.py --detector results/custom_detector/extra4_windows01 --evidence worker_returns/extra4_shank0/pilot01/received --binary data/extra4_shank0_float32.bin --output results/custom_detector/kilosort_pilot01_quality_NEW
```

This adapter is deliberately pilot-specific. It requires a completed native detection launch with full raw HDF5 hash verification. It verifies every mapped source value against the unchanged 512-channel pilot binary, checks frozen-return hashes and binds candidate/annotation files by SHA-256. It transfers global warning/availability **intervals by original sample index**, never candidate event-row masks. It does not recalculate coincidence from 59 sorter clusters or lower the quorum for a single shank. Its global population is the 2048-channel detector; the annotated sorter population is shank0.

`external_quality.h5`, schema `kilosort-external-detector-quality-v1`, retains final-array event indices, sample indices, cluster IDs and template-peak global electrodes. `/annotations/` stores separate broad/tight warning and availability, historical signal warning/availability, peak-channel flat-guard overlap and peak-channel detector observability. `/intervals/` retains the global supports. Original candidate and sorter files are untouched. `cluster_overlap.csv` summarizes counts; `summary.json` pins provenance and verification; a manifest hashes outputs.

Peak-channel observability combines that electrode's valid noise windows, reference eligibility, guards and physical MA50 edges. It is an external detector diagnostic, **not a validated sorted-unit observation mask or rate denominator**. No warning is adopted as a unit label, spike exclusion, whole-shank mask, interpolation or Kilosort input change. A global coincidence warning can represent real shared neural activity. Unavailable is not equivalent to assessed-unflagged.

## Acceptance and reproduction

```powershell
& ./.venv-detector/Scripts/python.exe -B scripts/validate_custom_pipeline.py --native-extra4 results/custom_detector/extra4_windows01 --output results/custom_detector/acceptance_NEW
```

The acceptance script requires separately regenerated reference sidecars in `reference_extra4_annotation_windows01` and `reference_extra5_annotation_windows01`. It checks package/imported hashes, captures all 42 upstream tests and three adapter tests, validates both frozen fixtures, compares all reference annotation datasets, and compares native extra_4 candidates/noise/quality arrays with Mac. The six old signal-warning datasets intentionally differ because generic input has no imported signal-based assessment. Named coincidence masks and availability are compared independently. HDF5 file bytes may differ due to paths/provenance; array identity is the relevant numerical criterion.

Fixed calibration, native full extra_5 redetection, extra_6/stimulation handling and full-recording signal-warning assessment remain outside this acceptance. Detector success does not constitute a new Kilosort sort or acceptance of any neuron identities.
