# Local Windows viewers

Run `Open Sorted Results in Phy.cmd` or `Open Kilosort GUI.cmd` at the project root.
The three environments and Python runtime are local to this project; no sibling worker is required.

DLL repair (2026-11-22): active FAISS is pinned to 1.13.2, which loads with Smart App Control enabled. Kilosort imports and offscreen GUI construction pass; original pilot provenance remains unchanged. See the [repair round](rounds/2026-11-22-03-windows-dll-repair.md).

**Launcher target:** Phy opens the historical all-channel pilot copy, not the selected without-248 run or accepted W12 subset. Use the [W12 report](../../results/extra4_shank0/w12-curated-v1/index.html) for accepted derived results; no accepted-subset Phy launcher has been configured.

Phy opens `viewing/pilot01-playground`, copied from the worker's later viewer workspace, including its existing UI/cache state. Only its copied params.py data path was changed. Raw data come from `data/extra4_shank0_float32.bin`. Saved curation affects this working copy, never the frozen pilot. The old viewer tour uses historical clusters 34/35, 26/29, 37/58, 31/33 and 45/48; those IDs must not be interpreted as selected-run cluster IDs. Preserve explicit revision records before scientific adoption; automated good is not a confirmed neuron.

Kilosort uses `scripts/launch_kilosort.py`, adapted from the worker's launcher, and the byte-preserved config/geometry under `configs/pilot01/`. It stores settings in a fresh `viewing/qt-config-local` directory and chooses a distinct exploration output per launch. LOAD displays raw/whitened signals; RUN starts sorting. No new sorting is needed to view the completed pilot. Recheck exclusions and settings before any intentional new run. The config's relative data path is interpreted from this project root.

`.venv-gui` has Qt6 and uses a local .pth reference to `.venv`. FAISS is the only dependency changed since migration. `.venv-phy` keeps unchanged independent Qt5 dependencies. The Kilosort launcher scopes its settings constructor to `viewing/qt-config-local/Kilosort4.ini`; this corrects the old default-format call, which still selected the Windows registry. Installed Kilosort files are unchanged. Offscreen startup/settings persistence were checked; no new visual rendering assessment or sorting was performed. Prior visual verification remains in the preserved worker's viewer round.

Templates are whitened and raw numerical scaling is not voltage calibration. Phy's optional TemplateFeatureView is unavailable for this export; the PC FeatureView is supported. The original five-minute viewer tour is preserved in the worker snapshot's `viewing/README.txt` and copied locally, with its migration notice.

Probe display: Kilosort 4.1.7's **True Aspect Ratio** checkbox defaults to unchecked, so the panel can stretch x and y independently. Enable it in Probe View to compare physical spacing. Verified CSV, probe JSON and original sorted channel positions agree on 30 micrometre pitch in both axes: four columns at x=0/30/60/90 and 128 rows from y=0 through 3810. The 90-by-3810 micrometre span is between electrode centers for this one shank, not the full probe outline. This display option does not alter sorter geometry.
