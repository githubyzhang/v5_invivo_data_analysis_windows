# In vivo extracellular spike detection

Analysis of simultaneous 2,048-channel extracellular recordings. The practical v1 pipeline uses MA50 baseline subtraction and adaptive MAD thresholds with an across-channel median floor; fixed quiet-reference thresholds remain available.

The delivered recording scope is extra_4 and extra_5. Detected events are candidate eAPs, not sorted neurons or validated spike identities. extra_5 followed current-injection experiments; compare recordings separately. extra_6 remains outside this delivery because of its unusually disturbed signals.

## Start here

- [Current status, next action and open decisions](docs/development/roadmap.md)
- [Setup, detection commands and report reproduction](docs/development/setup.md)
- [Documentation map and update convention](docs/README.md)
- [Detection methods](docs/METHODS.md) and [adopted decisions](docs/DECISIONS.md)
- [Output schema](docs/OUTPUTS.md) and [viewer handoff](docs/VIEWER_HANDOFF.md)
- [Historical investigations and evidence](docs/PROGRESS.md)

Source data are converted floating-point HDF5 recordings stored outside the repository. Input filenames are explicit and unrestricted; see the setup guide for `--input` usage and the required `signals` layout. Analysis uses nominal 10,000 Hz by project convention (physical sampling: 10,080 Hz).

Generated results and the local environment are Git-ignored. Source recordings are read-only. The original `legacy/` code remains a reference. The pipeline does not yet provide spike sorting, spatial deduplication, stimulation-artifact removal or validated fast-noise correction. Shared-disturbance assessment has partial coverage; unassessed intervals must not be interpreted as artifact-free.
