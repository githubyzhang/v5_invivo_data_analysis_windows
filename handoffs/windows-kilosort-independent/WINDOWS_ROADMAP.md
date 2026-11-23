# Windows Kilosort4 roadmap

Updated: 2026-11-22. Bootstrap template: copy into `docs/development/roadmap.md` in the independent Windows checkout. That destination becomes the single current tracker; retain this file only as dated handoff context.

## Adopted direction

Windows independently develops a Kilosort4-centered sorting and neural-activity workflow. Mac continues its custom detector and electrode-level analysis. Shared checkpoint: `92da0b2c30c70132a8cd4f44a6bb545e59fc463f`; Windows repository: independent clone, initially on `master`, with no remote. See `handoffs/windows-kilosort-independent/START_HERE.md` for contract and bootstrap.

## Current evidence

extra_4/shank0 baseline completed: 39,620 events / 59 clusters, 24 automated good and 35 mua. Transfer integrity checked on Mac. Diagnostic review is complete; human curation and scientific acceptance remain pending. Full report, original outputs, environment locks and manifest are retained in the existing worker package. No extra_5 or other-shank sorting is established by this pilot.

## Next

1. Establish the independent checkout, ignore local evidence/environment directories, import useful worker scripts with provenance, and record actual data/output paths and environment setup.
2. Review promising and questionable clusters, disturbance windows and split candidates described in RUN_REPORT. Preserve original labels, make curation changes traceable and assess exposure/short-interval limitations.
3. Establish a reusable unit-quality report and decide whether separately named sorter sensitivity runs are necessary.
4. Expand to other shanks/extra_5 once pilot review supports it and required data are available; retain independent per-recording identities.
5. Build downstream unit activity summaries with clear uncertainty and curated versus uncurated distinctions.

## Deferred / boundaries

No confirmed cross-recording neuron matching, universal artifact removal or complete neuron recovery. extra_6 and stimulation-period artifact handling remain separate future research. Shared artifact references cover only part of each recording. Preserve all source data and baseline outputs. Coordinate selected fixes/results with Mac without making either workflow depend on the other's milestones.
