# Gurobi14 compatibility checkpoint — 20 November 2026

## Original failure audited; recording correction prepared

Job2278573 is FAILED1:0 in78s. Its final archive SHA-256
`a79e0872b4d5bcede1f7094a02096dba8ba917598f13d503cfc0dae8f5f50988`
and sidecar match locally; all37 transfer-manifest entries and15 nested official
entries verify. The original native-ready.json and result.json are empty. Native
optimization-entry/return, validation and worker-ledger receipts are absent.
See the [failure analysis](../gurobi14_h215_2278573_failure_analysis.md).

The identified defect is JSON recording of nonfinite parameter metadata after
opening the receipt file; the failure sequence reproduces with the exact old
controller and documented SoftMemLimit infinite default using API doubles only.
Prospective corrections preserve parameter semantics, serialize before file
creation, protect originals and report invalid/empty collected JSON explicitly.
Tests now cover actual JSON publication of all phase records with infinite defaults.
The old source72fd9f52 and consumed claim are untouched; no rerun is authorized.

The current shared prefix contains106 distributions against the frozen69, with37
additions and no changes to existing versions. This does not establish the job-start
inventory. The exact original environment guard remains active; a new execution
baseline is a separate decision, not an automatic acceptance of the shared changes.
Operational adoption remains unqualified because optimize never began. No new job,
optimizer, WLS session, shared-environment modification, manuscript change or merge
is performed. PR160 remains Draft. Earlier PENDING and qualification-pending
statements below are historical and superseded by this section.

## Operator update: submitted job and partial array accounting

The researcher authorized and submitted exactly one compatibility job, **2278573**,
from source `72fd9f52e1b439b46576d7d33cfaf928a63a51df`. Its last reported
state is PENDING (Resources). The original collector correctly returned
nonterminal_or_accounting_pending. Preparation's prepared_no_job preceded the
single submission; its fresh claim and submission/release are now consumed.
Do not repeat preparation, submission, release or cloning. The reported plan
SHA-256 has 64 hexadecimal characters and is retained verbatim; no independent
NPAD byte/hash inspection is claimed. WLS acceptance and native results remain
unknown. See [submission receipt](../evidence/gurobi14_h215_2278573_submitted_20261120.json).

The subsequent attached sacct snapshot covers the original h300 array2252608:
49 COMPLETED, 7 FAILED (tasks6,17,19,21,24,44,54; exit1:0), task56 RUNNING
04:37:32 and tasks57–59 still pending in the preceding full-range queue record.
The attachment abbreviates the pending range and does not refresh job2278573.
Scheduler completion is separate from scientific acceptance; failure causes
require original logs. Preserve the original array without retries or changes.
Its final collection is not yet ready. The attachment SHA-256 and task counts
are retained in the receipt. No original computational result is modified.

All seven workflows passed at the pinned execution source72fd9f52, including
18 solver-free controls. This evidence-only follow-up does not requalify an
actual WLS/native run. PR160 remains Draft; GO/NO-GO and merge remain pending.

## Earlier preparation context (superseded where updated above)

The researcher resumed after the short pause, supplied a successful original clone
report and requested autonomy, with authorization requested only for CLI execution
or merge. The preserved source environment is13.0.3; the clone loads14.0.0 under
Python3.13.15. Only gurobipy changed according to the qualified clone script's
reported verification. No agent NPAD access or independent raw-file hash review
is claimed; the original environment ledger will be checked before submission.

Read [protocol](../gurobi14_minimal_migration.md), [reported clone receipt](../evidence/gurobi14_environment_clone_reported_20261120.json)
and [single-job preparation](../gurobi14_h215_compatibility_execution.md).
The code preserves the existing native mathematical builder, DET/W loader/network,
penalty vector, original validation and all historical evidence. One explicitly
owned WLS environment, one native model and one optimize attempt are prepared.
Only TimeLimit=300 is assigned; all other optimization defaults are audited.
One exclusive CPU job requests192GiB and one wall hour for construction, solve and
validation. Slurm requeue is disabled. A time-limited return without incumbent
can qualify compatibility; it is not mathematical infeasibility.

Eighteen local standard-library/double controls and Ruff passed. Linux checks,
source archive identity and all final exact-head workflows must be read before
requesting CLI authorization. CI does not establish actual Gurobi14/WLS or real
instance acceptance. The native test, original validation result and operational
GO/NO-GO remain pending. No scheduler call, license session or optimizer execution
has been made by Codex. PR160 remains Draft; no merge is authorized here.

The previous package message from another project is withdrawn and excluded.
The actual NPAD preflight confirms x86_64/glibc2.28, required input dependencies,
three matching input hashes and a readable existing license file. Readability
alone is not WLS acceptance. The explicitly selected clone prefix is the sole
new-environment exception to the audit-project directory rule. Preserve all
original claims and never repeat cloning or a consumed/uncertain submission.

The researcher clarified that current develop/main synchronization uses only
already integrated develop content and does not wait for the open PRs. Those PRs
remain independent for later develop integration. No implicit merge authorization.

The English EN methodological-plan rewrite remains deferred until two further
mandates are supplied and reconciled. Preserve the latest qualified XLSX files
as the MVP3.0 starting data. No new Benders implementation, manuscript/result
changes, data publication or larger-instance campaign occurs in this test.
