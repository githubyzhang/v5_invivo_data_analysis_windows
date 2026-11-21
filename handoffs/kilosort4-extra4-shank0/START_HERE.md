# Windows Kilosort4 worker: extra_4, first shank

You are the Windows compute worker. The Mac project remains the research home. Read this file, `docs/WORK_ORDER.md`, and `docs/roadmap.md` before work. You do not need the originating chat or full repository.

## Assignment

Run and review a bounded Kilosort4 pilot on **extra_4, physical shank 1 (zero-based shank 0), all 3,000,000 samples**. This is 512 electrodes over 300 nominal seconds. The user confirmed the legacy mapping and **30 µm horizontal and vertical center spacing**. The package contains continuous converted signals, not just thresholded event snippets. Do not expand to other shanks or extra_5 in this assignment.

Copy this entire folder onto the Windows SSD. Open that copy as the new project. Keep input files unchanged. Allow at least 30 GB free for data, environment and working outputs; actual requirements depend on software and preprocessing copies.

1. Read `docs/WORK_ORDER.md` and `docs/ENVIRONMENT.md`.
2. Create a local Python environment and install the dependencies. Verify the actual NVIDIA GPU, driver, CUDA-compatible PyTorch build and GPU computation; do not silently fall back to CPU.
3. Run `python scripts/verify_package.py`. Inspect geometry and raw signal examples before sorting.
4. Read `config.json`. Run `python scripts/run_pilot.py --run-name pilot01` after preflight. This is a diagnostic baseline, not a validated sorting configuration. The Windows worker may make necessary compatibility fixes with a documented diff and exact environment record.
5. Review outputs and complete `docs/RETURN_CHECKLIST.md`. Return the entire `outputs/` directory, executed scripts/configuration, environment lock, run report and hash manifest. Original input binary need not be copied back to the Mac.

The package was prepared on macOS; Kilosort and GPU execution have **not** been tested here. An installation success or completed sorter run does not establish isolated neurons. Do not inherit the old detector's 5 ms spacing or treat its absence of short intervals as sorting quality.
