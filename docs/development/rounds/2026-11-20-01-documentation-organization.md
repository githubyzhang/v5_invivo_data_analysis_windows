# Documentation organization

Date: 2026-11-20. State: implemented; documentation consistency checked.

## Purpose and changes

Adapt the user's FMAE workflow guide so a collaborator can find current status, governing references, evidence and the next action without reconstructing the chat.

Added the [documentation map](../../README.md), a single [roadmap](../roadmap.md) and [setup guide](../setup.md). Shortened the root README to purpose, boundaries and navigation. Retained stable methods, decisions, output schema and viewer-handoff paths. Reframed `PROGRESS.md` as an explicitly historical investigation ledger, preserving prior findings and result links. The supplied workflow guide remains unchanged.

The roadmap separates completed detection/activity work from proposed sorting. Geometry, compute environment and sorting-specific input/artifact decisions remain unresolved; no sorter has been adopted. Earlier work is linked to verified commit checkpoints rather than assigned retrospective dates.

## Validation and limits

Checked relative Markdown targets across the project README and docs, and checked the diff for whitespace errors. Compared the supplied guide and review-label/provenance files before and after the edit to confirm they were unchanged. Source code, detector outputs, calibrations and the saved presentation were not modified. No detection, waveform analysis or implementation tests were rerun for this documentation-only round. Historical test counts retain their original scope.

Generated evidence is local and Git-ignored, so its links require the existing results. Report regeneration does not automatically rebuild the presentation; that distinction is documented in setup.

## Next

Use the roadmap to resume sorting preparation after the user resolves geometry and compute availability. Continue the adopted documentation loop for substantive future rounds. Commit/push remains a separate user action.
