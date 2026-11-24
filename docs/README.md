# Documentation map and working convention

Updated 2026-11-24. Start with the root README and the single current tracker, then read only the references relevant to the task. This project applies the supplied [documentation workflow](documentation-workflow.md) pragmatically.

## Active references

| Document | Owns |
| --- | --- |
| [Project README](../README.md) | Purpose, preservation boundaries and entry points |
| [Roadmap](development/roadmap.md) | Current status, agreed future rounds and open decisions |
| [Windows setup](development/windows-setup.md) | Root environments, storage, recovery and reproduction commands |
| [Windows quality reference](WINDOWS_QUALITY.md) | Kilosort review/output contracts, explicitly scoped by round |
| [Windows viewers](development/viewers.md) | Launcher targets and viewer limitations |
| [Windows custom detector](CUSTOM_PIPELINE_WINDOWS.md) | Separate `.venv-detector` workflow and quality sidecar |
| [Dated rounds](development/rounds/) | What changed, what was validated and what remained unresolved at that date |

## Decisions and preserved evidence

| Reference | Scope and interpretation |
| --- | --- |
| [W12 acceptance ledger](reviews/2026-11-24-w12-curation-ledger.csv) and [revision](../configs/extra4_shank0_curated_v1.json) | Current accepted shank0 subset. Acceptance fields supersede earlier wording retained in reasons. |
| [Adopted shank0 policy](../configs/extra4_shank0_analysis_policy.v1.json) | Accepted boundary/exposure and annotation policy; not automatic acceptance for other shanks |
| [W13 release](../configs/extra4_shank0_release.v1.json) and [expansion procedure](development/extra4-expansion.md) | Hash-pinned checkpoint and procedure as of W13. Statements about future W14 work are historical; use the roadmap and W14 contract for subsequent implementation. Do not edit the pinned procedure. |
| [W14 input/proposal metadata](../configs/extra4_remaining_shanks_w14.proposed.json) and [channel ledger](reviews/2026-11-24-w14-channel-proposals.csv) | Verified inputs and proposed channel decisions; a commit does not adopt exclusions |
| Earlier [review findings/ledgers](reviews/) | Evidence and proposals at their named round, not competing current decisions |
| [Mac setup](development/setup.md), [methods](METHODS.md), [decisions](DECISIONS.md), [outputs](OUTPUTS.md), [viewer handoff](VIEWER_HANDOFF.md), [progress](PROGRESS.md) | Inherited detector history. Do not execute its `.venv` setup instructions in the Windows sorter environment. The current imported detector is governed by the Windows detector guide and its pinned upstream sources. |
| [User labels](reviews/ma50_user_review.json) and [provenance](reviews/provenance.json) | Preserved expert review evidence, not labels for the current Kilosort units |

Keep existing reference paths and frozen bytes intact. If a pinned reference becomes stale, clarify its scope in an active entry point or add a new revision; never repair its checksum by rewriting the original manifest.

## Update loop

1. Read README, roadmap and the latest linked round before work.
2. Complete and verify the bounded task. Distinguish implementation, validation, proposal and adoption.
3. Update the owning reference only when its meaning changes; put current status and future work in the roadmap.
4. Write one dated record per substantive round, using `YYYY-MM-DD-NN-short-title.md`. Link evidence instead of copying it into multiple summaries.
5. Check links, preservation and the diff. Commit/push only under the user's normal authorization workflow.

Scientific acceptance is explicit and versioned. A plan, automated label, passing software test or source hash does not establish neuronal identity. Retain holds and unavailable quality assessments without converting them to noise or clean time.

For documentation-only work, check local links and anchors, protected hashes and the changed-file scope. Do not rerun expensive recording analysis. Local result links may be unavailable in a fresh clone; the Windows setup guide owns storage/recovery instructions. The supplied documentation-workflow reference and historical round records are not extra current trackers.
