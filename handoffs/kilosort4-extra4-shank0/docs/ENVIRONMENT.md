# Windows environment

Use a new project-local `.venv` or dedicated conda environment, Python 3.11 or 3.12, on the Windows SSD. The Mac environment is not transferable and is not included.

`requirements.in` declares dependency scope, **not a reproducibility lock**. Select a released Kilosort 4.x version, inspect its official instructions and pin the exact resolved environment before the pilot. Install an appropriate CUDA PyTorch build for the actual GPU/driver first; the newest desktop GPU may need a newer CUDA build than older Kilosort installation examples. Do not guess the GPU model from 'Area-51'. Run a small CUDA tensor computation, not only `torch.cuda.is_available()`. Record GPU name, VRAM, driver, PyTorch and CUDA versions, Python version, OS and Kilosort version.

PowerShell outline (adapt the GPU PyTorch installation command using official guidance):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
# Install the appropriate GPU PyTorch build from https://pytorch.org/get-started/locally/
python -m pip install -r requirements.in
python -m pip freeze > environment-lock.txt
python scripts/verify_package.py
python scripts/run_pilot.py --run-name pilot01
```

If activation is disallowed, call `.venv\Scripts\python.exe` directly; changing system execution policy is not required. Keep Phy in a separate environment if dependency conflicts arise. Kilosort weights may require an initial network download; record failures rather than replacing the algorithm.

Official references checked during preparation:
- https://kilosort.readthedocs.io/en/latest/README.html
- https://kilosort.readthedocs.io/en/latest/tutorials/basic_example.html
- https://kilosort.readthedocs.io/en/latest/tutorials/make_probe.html
- https://kilosort.readthedocs.io/en/latest/export_files.html
- https://github.com/MouseLand/Kilosort/blob/main/kilosort/parameters.py

This package's launcher follows the documented API but remains untested on Windows/GPU. Verify installed-version signatures; save any compatibility changes and their reasons with the returned output.
