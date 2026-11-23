# W3 — FAISS DLL repair with Windows protections retained

Date: 2026-11-22. State: active runtime repair validated; no new sorting or scientific adoption.

## Cause and repair

Reproduced the FAISS 1.16.0 `_swigfaiss.pyd` Application Control import failure. The installed extension exactly matches the 1.16.0 wheel obtained from PyPI; this was not migration corruption. The file is unsigned and has no Zone.Identifier stream. Previous Code Integrity events identified the signing/policy block. Microsoft documents that Smart App Control uses reputation/signature checks; the precise cloud reputation decision is not observable here. [Microsoft guidance](https://support.microsoft.com/en-gb/windows/security/threat-malware-protection/smart-app-control-frequently-asked-questions).

Tested the compatible [FAISS 1.13.2 PyPI release](https://pypi.org/project/faiss-cpu/1.13.2/) in an isolated target directory before replacing the active dependency. It loaded normally and passed NumPy nearest-neighbor, Kilosort neighbor-graph and CUDA checks. Installed that exact wheel into root `.venv` using `--no-index --no-deps`; `.venv-gui` uses the same package through its existing .pth. FAISS 1.16.0 → 1.13.2 is the only package-list difference. Kilosort remains 4.1.7, Torch 2.11.0+cu128, Python 3.12.10. Phy was not changed.

Smart App Control remains enabled (`VerifiedAndReputablePolicyState = 1`). No exclusions, certificate changes, policy changes, DLL rewriting, unblocking, or upstream library patches were used. This is a different compatible package release accepted by the existing Windows policy, not an exception for the blocked DLL.

Wheel identities (both retained in ignored `results/dll-repair-2026-11-22/wheels/`):

| Wheel | SHA-256 |
|---|---|
| faiss_cpu-1.16.0-cp312-cp312-win_amd64.whl | `6b9076b0015f95c9de632bbe291995a45541573b2aca7ae7a038c7a3732948e4` |
| faiss_cpu-1.13.2-cp312-cp312-win_amd64.whl | `b82c01d30430dd7b1fa442001b9099735d1a82f6bb72033acdc9206d5ac66a64` |

Original blocked extension SHA-256: `e4a5098906657a373832ad404a898cf3a26a7cea5ccb63557f3299228857162c`.

## GUI configuration correction

Startup testing uncovered a separate launcher issue: Qt's two-string organization/application QSettings constructor always selects NativeFormat, regardless of setDefaultFormat. On Windows the old launcher therefore attempted registry storage rather than its advertised local INI path. In sandboxed tests that left results_dir unavailable, exposing an upstream Path/list error during GUI construction. [Qt constructor documentation](https://doc.qt.io/qt-6/qsettings.html#QSettings-3).

`scripts/launch_kilosort.py` now scopes that one constructor signature to an explicit `viewing/qt-config-local/Kilosort4.ini` file. The adapter is restored on exit, leaves other signatures alone, and does not modify installed Qt/Kilosort sources. The project configuration supplies the probe, raw data, numerical scale and fresh exploration result path. No scientific settings changed.

An initial direct GUI harness omitted results_dir; a later harness set the download-cache environment too late, after Kilosort import. Both harness errors were corrected. The final reusable `scripts/check_sorting_runtime.py --gui` sets its cache before import, uses isolated INI settings, and validates the same configuration helper as the root launcher.

## Validation

Isolated candidate and final active environments pass exact nearest-neighbor indices against NumPy on deterministic non-tied data, distance tolerances, Kilosort's actual `neigh_mat` path and sparse-graph diagonal checks, and a CUDA matrix check on RTX 5090. Both active environments pass pip check. The configured GUI constructs/closes offscreen, points to the intended local INI and fresh output path, and restores the Qt settings constructor afterward. This is startup validation, not a new visual rendering assessment.

Evidence: `results/dll-repair-2026-11-22/initial-identity.json`, `candidate-validation.json`, `active-validation.json`, `final-gui-validation.json`, and before/after dependency locks. All 169 frozen-return payloads remain unchanged. The complete historical worker and its 1.16.0 environment/locks remain untouched. New active locks are `requirements-windows-lock.txt` and `requirements-windows-gui-lock.txt`.

Raw pip freeze output records FAISS as a local-wheel URL. Raw after-freeze files are retained with the repair evidence; versioned locks normalize that one entry to `faiss-cpu==1.13.2` for portability. The exact installed version and wheel hash are independently recorded above. All other dependency entries are unchanged.

No full sorter run was performed, and this does not establish identical clusters across FAISS releases. Original pilot results remain attributed to their original environment. Future runs must save their actual versions; source identity, geometry, settings and curation requirements remain unchanged. Resume the [roadmap](../roadmap.md)'s targeted pilot review; full execution is not needed simply to recover the GUI or inspect the completed pilot.
