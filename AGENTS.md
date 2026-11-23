# Project working conventions

Read README.md, docs/development/roadmap.md and the latest linked round before work. This folder is the independent Windows project root. The Mac detector sources are retained as history; do not silently adopt their scientific defaults for Kilosort.

Use docs/documentation-workflow.md pragmatically: one current tracker, authoritative methods/output references, and one dated record per substantive round. Distinguish proposals, implementation, validation and scientific adoption. Commit/push only under the user's normal authorization workflow.

Original data, frozen outputs/labels, manifests and archives must remain unchanged. The complete former worker under worker_returns/worker-snapshot is historical evidence, not a second active checkout. Use root .venv, .venv-gui and .venv-phy, root data, and new result paths. Do not run the archived worker's old environment or modify its history to make old paths current.

User preference inherited from the Windows worker (2026-11-21): release computer-use connections when finished without closing user applications. Use the documented release/reset operation for the tool in use. Do not claim capture shutdown without evidence, and do not take another screenshot solely to test cleanup if it would reopen capture.
