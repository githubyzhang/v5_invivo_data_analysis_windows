# Windows Monday: independent Kilosort4 workflow

Date: 2026-11-22. User-adopted direction: Windows develops independently with Kilosort4 as its main workflow; Mac continues its custom detector and electrode-level analysis. You are now an independent research track, not just a bounded GPU execution worker. Preserve evidence and distinguish proposals, validation and adopted policy.

## Bootstrap without losing your completed work

The portable delivery ZIP contains this note, `WINDOWS_ROADMAP.md`, the documentation-workflow guide and `windows-kilosort.bundle`. It does not contain data, outputs, environments or the Mac's uncommitted documentation edits. The repository snapshot starts at committed worker-package checkpoint `92da0b2c30c70132a8cd4f44a6bb545e59fc463f`; this note supersedes its old worker-only/current-roadmap instructions. No new commit or push was made on Mac.

Keep your existing worker folder and completed pilot untouched. Extract the ZIP to a transfer folder. In PowerShell, from that folder, create a NEW sibling checkout (destination must not exist):

```powershell
git clone --branch master ./windows-kilosort.bundle ../invivo-kilosort-windows
git -C ../invivo-kilosort-windows remote remove origin
git -C ../invivo-kilosort-windows rev-parse HEAD
git -C ../invivo-kilosort-windows branch --show-current
```

Expected HEAD is the full hash above; expected branch is `master` in the NEW repository. The second command removes the bundle-path origin so the repository has no misleading remote. This does not affect the Mac repository. A GitHub fork relationship is not created by these offline commands.

Your first documentation change in the new checkout: copy this note and `WINDOWS_ROADMAP.md` into `handoffs/windows-kilosort-independent/`, use `WINDOWS_ROADMAP.md` as the content of `docs/development/roadmap.md`, and update root README to state Windows/Kilosort ownership. The guide already exists at `docs/documentation-workflow.md`; an identical standalone copy is supplied for convenience. Keep one current tracker, dated round records, and authoritative methods/output specifications. Record this bootstrap as a new round. Commit according to the user's normal review/commit workflow.

Keep original worker package and pilot as evidence outside the new source checkout, or copy them into ignored storage. Before importing any outputs, add `/worker_returns/`, `/.python/` and any new environment/output directories to `.gitignore`; `/data/`, `/results/` and `.venv/` are already ignored. Never copy the Mac environment. Reuse your verified Windows environment in place initially or recreate a project-local environment from your returned locks; document which was used. Port useful worker scripts into versioned source with their provenance, rather than treating ignored evidence as the only implementation.

## Existing assets: do not repeat the completed export/sort by default

You already have the Windows worker and full pilot. The original portable worker folder is named `kilosort4-extra4-shank0-worker-2026-11-21`; its input `data/extra4_shank0_float32.bin` is 6,144,000,000 bytes, SHA-256 `11cd033eb0bda858f7598123a795f198078cc227d98d92543e8ea88f9e12eff0`. It contains only extra_4/shank0, not other shanks or extra_5.

The received ZIP identity on Mac is `extra4_shank0_pilot01_return.zip`, SHA-256 `087ba85cb9c195a9e1b401b8dc0f46d1969537e0f728addde33a72cc0f4df73d`. Mac keeps it under `worker_returns/kilosort4/extra4_shank0/pilot01/`, with extracted `received/`. All 169 manifest-listed payload files were verified. Start scientific work from your `RUN_REPORT.md`; retain `return-manifest.json`, environment locks, configs and original outputs unchanged. Original transfer manifest and return manifest cover different states.

Pilot: 39,620 final events, 59 clusters (24 automated good, 35 mua), no human curation. RTX 5090 / Kilosort 4.1.7; unchanged baseline, full 300 nominal seconds and 512 channels. No MA50/custom clipping mask or shared-warning exclusion was applied. Existing labels are not confirmed neurons. Review priorities: promising clusters 34/35 and 5/12; good cluster 2's contamination; sparse good 26/29; boundary-only 37/58; similar pairs 31/33 and 45/48; channel 248/global1921 and report disturbance windows. `kept_spikes.npy` indexes the pre-deduplication list: do not apply it again to the final arrays.

## Shared data contract

- Original integer sample indices are authoritative. Nominal fs=10,000 Hz; physical fs=10,080 Hz. Preserve both conventions and label reported durations/rates. No silent resampling or timeline concatenation.
- Original converted HDF5: dataset `signals`, `(2048, 3000000)`, float16, trusted conversion. Worker binary: little-endian float32 `(3000000,512)`, sample-major, lossless cast, no pre-export filtering. Record numeric scaling separately from voltage calibration; whitened/template amplitudes are not raw voltages.
- Four shanks, each 128 rows × 4 columns, 30 µm horizontal and vertical pitch. Pilot zero-based shank0 is physical shank1. Preserve the original global-channel mapping and local binary indices; use the provided mapping files, not inferred consecutive global IDs.
- extra_4/5/6 are purely extracellular recordings; extra_5/6 follow stimulation experiments. Differences do not establish a causal stimulation effect. extra_6 remains outside the initial program because of disturbed/fast-noise signals. Stimulation-period recordings are separate scope.
- Source recordings and baseline evidence are read-only. Save new runs under distinct names with source hashes, resolved config, exact versions and geometry. No automatic adoption of artifact removal or default changes from one track into the other.
- Mac's MA50/adaptive events use 5 ms per-electrode spacing and are not unit identities. Kilosort counts and Mac candidate counts measure different things. Full-recording shared-warning coverage is incomplete (35/300 seconds in prior reference); unavailable means unassessed. Existing per-channel flat guards are proxies, not calibrated clipping rails.

## Independent continuation and result exchange

First review/curate the pilot and establish a reusable quality report. Preserve original automated labels and explicit curation revisions with rationale. Decide whether sensitivity runs are needed before expanding to other shanks and extra_5. Any expansion needs those source data; use explicit Windows paths rather than Mac `/Volumes/YZ` paths. Do not assume matching cluster IDs identify the same neuron across recordings.

Build firing-rate, burst, spatial and timing analyses from sorted outputs as separate downstream analyses. Kilosort is the main sorting tool, not automatic biological interpretation. Mac does not need to approve every Windows development step; user authorization and scientific acceptance decisions still govern that project.

For optional exchanges, send a concise RUN_REPORT, source/config identity, geometry, units/timing convention, quality/curation state, metrics, plots, output schema and a hash manifest. Include aligned event sample indices and cluster IDs, and distinguish original labels from curation. Transfer data separately from Git. Mac can compare selected results without merging the Windows implementation.

## Transfer choices

Recommended now: this offline Git bundle plus the assets already on Windows. A bundle preserves repository history; an ordinary source-folder copy does not. The separate guide and handoff supply the post-checkpoint context.

Later, create a separate GitHub repository for Windows, or a GitHub fork of the Mac repository if one is available. Configure the Windows repository as origin; optionally add the Mac repository as upstream for selective fixes. Publish only reviewed code/docs, not recordings or ignored results. Do not routinely merge divergent scientific defaults. No Git remote is configured in the Mac checkout and nothing has been published by this handoff. This package implements an offline fork with common history, not a hosted GitHub fork.
