# Documentation map and working convention

This project adapts the [FMAE documentation workflow reference](documentation-workflow.md). The reference is preserved as supplied; this page describes the conventions actually used here.

## Where information belongs

| Document | Owns |
|---|---|
| [Project README](../README.md) | Purpose, boundaries and navigation |
| [Roadmap](development/roadmap.md) | The single current tracker: status, next action, open decisions and blockers |
| [Setup](development/setup.md) | Environment, run commands, interruption handling and reproduction |
| [Methods](METHODS.md) | Detection definitions and quality handling |
| [Decisions](DECISIONS.md) | Adopted detector choices, rationale and limits |
| [Output schema](OUTPUTS.md) | Authoritative saved-file contract and validation semantics |
| [Viewer handoff](VIEWER_HANDOFF.md) | Consumer-specific integration guidance; links to the schema |
| [Investigation history](PROGRESS.md) | Historical evidence through the initial activity report |
| [Dated rounds](development/rounds/) | Substantive changes, validation and remaining uncertainty after this reorganization |
| [User labels](reviews/ma50_user_review.json) and [provenance](reviews/provenance.json) | Preserved expert review evidence |

Existing reference filenames stay in place to avoid breaking handoffs. We do not need separate architecture/research/client directory trees yet. Historical experiments are retained in the investigation ledger and their original generated reports; we do not invent retrospective round dates or rewrite frozen experiments as current specifications.

## Update loop

1. Read the root README and roadmap, then the references relevant to the task.
2. Do the bounded work and record what actually passed, failed or remains unknown.
3. Update the owning reference only if its meaning changed.
4. Add one dated round for a substantive implementation, experiment, review or handoff.
5. Update the roadmap and essential navigation. Do not add competing current-status sections elsewhere.

Round filenames use `YYYY-MM-DD-NN-short-title.md`; related small fixes can share one record. Descriptive names are sufficient until milestone IDs solve a real coordination problem. State **proposed**, **implemented**, **validated for a stated scope**, or **adopted** explicitly. Include purpose, changes, validation/evidence, limitations and next action; omit empty sections. A documentation update does not authorize a commit or push.

## Scientific evidence and history

Engineering tests and source-file checks do not establish eAP accuracy or neuronal identity. Keep recording conditions separate; preserve extra_5/6's post-stimulation history. Selected waveform labels are not a random accuracy sample. A proposed sorter or artifact rule does not become an adopted default merely by appearing in the roadmap.

Keep frozen results, labels and provenance intact. Add dated corrections or supersession links when needed, rather than silently rewriting the evidence. Old test counts and statements of incomplete work remain historical; the roadmap owns today's status. Local result links may be unavailable in a fresh clone because generated results are not versioned; the setup guide owns their storage and reproduction instructions.

For documentation-only changes, check relative links, preserved evidence and the diff. Do not rerun expensive recording analysis just to reorganize prose.
