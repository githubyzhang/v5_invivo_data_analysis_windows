# Local Windows viewers

Run `Open Sorted Results in Phy.cmd` or `Open Kilosort GUI.cmd` at the project root.
The three environments and Python runtime are local to this project; no sibling worker is required.

Current blocker (2026-11-22): Windows Smart App Control blocks FAISS in both the old and migrated environment. Phy loading works; the Kilosort launcher is relocated but cannot run until that policy/trusted-package issue is resolved. No security bypass or package-version change was applied.

Phy opens `viewing/pilot01-playground`, copied from the worker's later viewer workspace, including its existing UI/cache state. Only its copied params.py data path was changed. Raw data come from `data/extra4_shank0_float32.bin`. Saved curation affects this working copy, never the frozen pilot. Start with clusters 34/35, then sparse 26/29, boundary-only 37/58 and similar pairs 31/33 and 45/48. Preserve explicit revision records before scientific adoption; automated good is not a confirmed neuron.

Kilosort uses `scripts/launch_kilosort.py`, adapted from the worker's launcher, and the byte-preserved config/geometry under `configs/pilot01/`. It stores settings in a fresh `viewing/qt-config-local` directory and chooses a distinct exploration output per launch. LOAD displays raw/whitened signals; RUN starts sorting. No new sorting is needed to view the completed pilot. Recheck exclusions and settings before any intentional new run. The config's relative data path is interpreted from this project root.

`.venv-gui` has Qt6 and uses a local .pth reference to `.venv` for pilot dependencies. `.venv-phy` keeps independent Qt5 dependencies. Both package sets match the old environments; launchers were regenerated for the new location. Qt6 imports and Phy model/raw-data checks pass; Kilosort imports are blocked as above. GUI rendering was not rechecked visually this round. Prior visual verification is documented in the preserved worker's viewer round.

Templates are whitened and raw numerical scaling is not voltage calibration. Phy's optional TemplateFeatureView is unavailable for this export; the PC FeatureView is supported. The original five-minute viewer tour is preserved in the worker snapshot's `viewing/README.txt` and copied locally, with its migration notice.
