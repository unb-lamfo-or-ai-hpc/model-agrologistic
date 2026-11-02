# PR #148 implementation checkpoint — 1 November 2026

Human receipts identify HiGHS 2231591 and Gurobi 2231593, engine c493be8c,
16 threads, seed 42 and plans 925a1de0/4be92d10. Their last supplied state is
RUNNING; no terminal result is inferred. Both are attached to the finite graph.
It needs 86 further solves, six controls and one final job: 93 new submissions.
Both one-thread original archives remain preserved.

The separate controller prepares engine-compatible plans, submits held jobs,
validates all receipts and releases once. Ambiguous submission, weakened
dependency, source/profile/owner mismatch or incomplete release prevents
execution. Collection retains original and partial evidence, distinguishes
non-execution, and does not reject censoring merely for missing the gap target.
Consolidation accounts for all 90 cells without imputing missing metrics.

All 98 local tests passed without failures, errors or skips. They cover partial
submission, release uncertainty, race conditions, dependency semantics, storage
budget, gates, original-plan compatibility, source binding and streaming.
Ruff passed with the repository configuration. No native optimization or NPAD
command was executed locally. Public qualification remains pending: 209 tests
(111 original plus 98 new) and five tiny Slurm probes. One intentionally failed
probe and its cancelled child are expected. The public native job waits for
the current private Gurobi when necessary.

PR #144 advances literature and practical interpretation of paired results;
18 focused reader checks passed. Nine unique historical additions from PR #142
were preserved using their original Git blobs in PR #144. PR #142 was closed
as superseded, without merge or branch deletion. PRs #144 and #148 remain
independent drafts. No merge, publication, raw-evidence upload or PDF generation
is implied by this checkpoint.
