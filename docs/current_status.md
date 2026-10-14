# Dated research status: 14 October 2026

This is a derived handoff snapshot, not a new certificate. Reviewed integration
base: develop `8a3f15084400424e07cd3367fa3a76295cc828c8` (PR #85 merged).
Read [PROJECT_STATE.md](../PROJECT_STATE.md), the [roadmap](mvp2_hpc_roadmap.md)
and linked evidence for full history. Refresh live PR state before continuing;
open PR content is not integrated code. The [portable memory](research_context.md)
was integrated with explicit authorization; it is not an execution gate.

## Current handoff

Job `2210506` has [independently replayed intact negative evidence](mvp2_s2_normal_2210506_audit.md).
Archive SHA-256 `0239bbec7edd29cf384e7949d441ec6fb3e8474f77c735799978620fc74aa642`.
Initial barriers and four stdlib worker phases passed, but all 186 samples faulted
and the controller blocked at the cleanup deadline. Completion is not containment
acceptance. The exact installed exception was not recorded; earlier member-read
failure suppressing later lifecycle/accounting reads is reproduced offline.
The resource-normal claim is consumed/collection-only. Next: qualify the read-only
audit and disconnected independent diagnostics, Ready/merge review, then bounded
operational integration before any successor admission. No NPAD command is
required now; no retry, cleanup relaxation or downstream execution is admitted.
Original evidence and all scientific/editorial decisions remain unchanged.

### Prior operational-wrapper handoff

PR #84 is merged with explicit authorization and six successful checks. The
[operational normal wrapper](mvp2_s2_resource_operational.md) connects the
sealed current source/runtime, exclusive claim, fixed synthetic worker,
normal resource adapter and immutable terminal/forensic collection. Existing
start resumes collection, never submission. Qualification is software-only;
no NPAD execution or live containment result is claimed. Next owner: agent
finishes Ready review and requests separate merge authorization; then the
maintainer uses the pinned CLI for one normal synthetic job and transfers
terminal evidence. All downstream execution remains closed. Historical claims
and scientific/editorial decisions are unchanged.

### Prior closed-launcher handoff

PR #83 is merged with explicit authorization. The maintainer resumed work on
14 October and requested the [closed launcher/forensic gate](mvp2_s2_resource_launcher.md).
It binds a fresh sealed release to a distinct one-shot claim and worker entry,
and qualifies terminal collection including absent/truncated final receipts.
Current entry points and production adapter launch remain closed; no NPAD
command or new claim is admitted by qualification or merge. Next owner: agent
finishes software qualification/Ready and requests merge; then prepares the
pinned normal-only admission wrapper. Previous prospective handoffs below are
historical. S2 and all later scientific/editorial decisions remain unchanged.

### Prior resource integration handoff

PR #82 is merged with explicit authorization. The
[normal resource integration](mvp2_s2_resource_normal_integration.md) connects
the approved v2 policy to the inherited handshake/sample/cleanup path and
versioned replay. Exact CPU membership and initial affinity are independently
read; zero post-exit membership is not fabricated into a live observation.
The new adapter launch and CLI remain closed; historical drivers and claims
are unchanged. Next: qualify/Ready this integration, request its merge, then
qualify a fresh normal-only release and complete terminal/forensic collection.
No NPAD command or live admission follows from this software checkpoint.

### Prior contract handoff

The maintainer approved the synthetic two-logical-CPU hard envelope within the
same allocation, initial one-CPU affinity and unchanged memory/time, without
execution authority or h300 changes. The [closed v2 resource gate](mvp2_s2_synthetic_resource_contract.md)
qualifies membership, enforcement/accounting separation and replay; legacy
runtime remains unchanged. Next: qualify/Ready this PR, obtain merge approval,
then integrate the explicit normal successor. No new SMT probe, repeat or job
is admitted. Earlier pending-decision statements below are historical.

### Prior observation handoff

Latest observation: job `2209770`, source `450d10b38d2fcdb8101b38069559103a0098a0a0`,
archive SHA-256 `f1f19fd0b494526af78e59ea979c5d428089e9f0afda4a7e78040d4df53be18f`.
Independent replay is `observed_not_qualified`: memory/freezer/cpuset disjoint,
cpuacct equal, worker hierarchical memory ceiling 256 MiB, worker cpuset two CPUs
versus one scheduler CPU. The maintainer's hash-asserting saved-status read reports
supervisor affinity `0,32` and worker affinity `0`; raw records remain private.
This resolves the saved-affinity question, not hard one-CPU containment, CPU
exclusivity or physical-core topology. Next qualify the role-aware enforcement/
accounting design and reconcile the CPU contract. Both normal and observation
claims are consumed; no repeat or successor is admitted. See the
[review](evidence/s2_scope_2209770_review.json). Earlier observation-start handoff
below is historical, not an instruction to submit another job.

PR #80 is merged at `5bf509a6db90b09eef8e1e13529f5039d934a9e1`.
Job `2209138` has independently replayed negative evidence: batch completed,
numeric step failed, shared/nested controller predicate failed at handshake.
The normal claim is consumed, not retryable. Follow the
[scope observation protocol](mvp2_s2_scope_observation.md): a separately qualified
immutable head, one short observation-only job, then audit of all four controller
relations. Neither this probe nor its successful collection admits normal,
adverse, native, h300 or repeat execution. Prior handoff text below is historical.

### Prior campaign and integration handoff

The [S2 closure campaign](mvp2_s2_closure_campaign.md) consolidates the five blocks
and remaining P2-P5 functional packages. It is a checked plan, not an end-to-end
runnable release. Its six-hour h300 allocation remains behind normal/adverse/
native admission. The native envelope and therefore total campaign budget are
not yet frozen. Preparing this campaign does not create another NPAD prerequisite.

PR #79 is merged. PR #80 reconciles its campaign with the duplicate-carrier
repair: the failed PR #77 start submitted no job. The [step-normal gate](mvp2_s2_step_normal.md)
now pins `9c008eecb93aa4b4a221fced2fafead467d89021`, retaining the same claim
and twelve-minute allocation. After PR #80's qualified authorized merge, the
maintainer uses its [pinned CLI or collects a matching existing claim](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/80#issuecomment-6146287095);
agent audits returned evidence. No live result has been reported for this repair.
Long solver jobs and subsequent admissions remain behind their pending gates.

13 October decision: cancel synchronization at S2 closure; defer it to final
consolidation after article review (S6-A/S6-B), through separately qualified,
authorized PRs. S2 retains its full experiments and can close without main
promotion. Later experimental/editorial work has no synchronization dependency.
Earlier next-action statements below are historical, not current instructions.

## What is established

Latest: job 2208459 has a preserved **negative unbound attempt**, not normal
acceptance. Root/batch completed; step 0 was cancelled 0:9. The collection parser
rejected Slurm's numeric cancellation suffix. See [recovery and limitations](mvp2_s2_accounting_recovery.md).
The recovered carrier is now checksum/inventory audited; worker identity exists,
but no binding/contract/phases or samples. Negative semantic replay is preserved.
The same functional PR corrects source-confirmed Slurm step UID/count/host schema
assumptions, with 31 new offline cases. Exact historical exception remains unknown.
Next: finish qualification/Ready and obtain merge authorization; then qualify a
distinct normal-only successor. Collection is complete, not a request to repeat.
No three-job/four-hour campaign is admitted. The statements below are historical.

Prior continuation: [node-normal operational gate](mvp2_s2_node_normal.md)
prepares one fresh normal-only claim, preserving jobs 2208339/2208438 and all
earlier certificates. Software qualification/merge are not live acceptance.
No new job is submitted; no adverse/native/h300/repeat admission is included.
Current owner: agent finishes qualification/Ready, then maintainer decides merge.

| Cohort/gate | Audited result | Interpretation limit |
| --- | --- | --- |
| Frozen MVP1, `v0.2.0-mvp1` | Thirteen attempts: seven Gurobi, six SCIP/SoPlex; four Gurobi quality-certified attempts | Preserve historical partial/failure outcomes; not a controlled solver speedup experiment |
| MVP2 S0 | Instrumentation and licensed miniature qualification, job 2143922 | Does not establish large-run causal sampler overhead or continuous telemetry coverage |
| S1 h215 | Three pairs/six accepted arms: jobs 2151415, 2184508, 2196511 | Observed numerical behavior preserved; no causal acceleration demonstrated |
| S1 h300, no direct arcs | Accepted baseline 2198528 after distinct evidence review; accepted descriptive pair 2199525 | Original collection rejection remains historical; no silent rerun or replication claim |
| S1 h400, direct arcs | Input 2200298 and accepted control 2200384; complete hierarchy and independent validation | One control, not a pure warehouse-count scaling contrast with h300 |
| S2 first miniature gate | Accepted job 2202239 at 1/2/4/8/16 threads | Analytical miniature qualification only; no production speedup claim |
| S2 containment input | Job 2202795 evidence accepted; capability outcome `blocked_environment` | cgroup v1 does not satisfy the implemented v2 path; not proven live containment |

Sources: [MVP1 comparison](evidence/sprint_c_final_20260920/comparison_summary.md),
[S1 exit ledger](mvp2_sprint1_closure.md),
[h215 consolidation](mvp2_h215_resource_consolidation.md),
[h300 baseline](mvp2_h300_baseline_acceptance.md),
[h300 pair](mvp2_h300_pair_acceptance.md),
[h400 control](mvp2_h400_control_acceptance.md),
[thread miniatures](mvp2_thread_qualification_evidence.md) and
[containment gate](mvp2_s2_containment_gate.md).

Compaction remains optional/default-off. Lower paired application RSS does not
establish lower native memory, smaller allocations or runtime acceleration.
The accepted h400 control reports about 7.76 optimization hours and 101.11 GiB
application RSS peak. Its Slurm batch maximum is a different measurement, not
a replacement. Final capacity quality must be read separately from the earlier
capacity-pass gap; acceptance retains the inherited hierarchical allowances.

## Current open work: S2

Current audited result: [diagnostic 2208438](mvp2_s2_node_identity_evidence.md)
completed 0:0 but retained `observed_mismatch_or_query_failure`. Successful query,
seven matches; NodeList/BatchHost short name differs from local NPAD FQDN.
PR #74 qualifies a restricted rack-FQDN mapping and exact allocation-to-step node
continuity. Source, resource and containment requirements are not relaxed.
The original diagnostic stays negative; no old claim can be reused and no fresh
normal execution is admitted. Next: final CI/Ready and explicit merge decision,
then a separately qualified fresh normal-only claim. S2 remains open.
The following diagnostic-planning and prior observations are historical.

Latest: job 2208339 independently replays `no_attempt_receipt`; allocation
preflight rejected an unknown field comparison at adapter line 485, before
worker launch. Reported accounting matches the requested 2 CPU/2G/one-node/
12-minute envelope; it cannot reconstruct live field representation or hostname
comparison. Preserve this consumed claim and predecessor 2208056. The
[diagnostic-only gate](mvp2_s2_allocation_diagnostic.md) gathers all relevant
fields and comparisons without changing the normal gate. The diagnostic PR stays
draft pending live observation and any evidence-based correction in the same PR.
No worker, adverse, native, h300 or repeat is admitted. The following entries
describe earlier observations, not the current next action.

Latest audited observation: [job 2208056](evidence/s2-compute-normal-2208056/README.md)
failed in supervisor batch-membership preflight. Integrity replay succeeds with
`no_attempt_receipt`; this is not live acceptance. Tagged Slurm 22.05.11 source
explains the unsupported `.batch` query; installed raw output was not retained.
The bounded offline correction retains the PID gate, supports descendant display
markers and prohibits reserved worker/signal IDs. The compute claim is consumed.
PR #72 is merged after explicit authorization and four successful head checks.
The [successor normal gate](mvp2_s2_normal_successor.md) binds three immutable
predecessors and a distinct one-shot claim through complete operational wiring.
Next owner: agent qualifies this successor; maintainer authorizes its merge only
when Ready and separately authorizes/executes the frozen CLI.
No retry, adverse/native/h300 or repeat is admitted. The text below is historical.

Previous observation: the authorized PR70 normal bootstrap passed its reported
481 tests/two intentional skips, then failed in current source sealing before
claim creation/submission. Maintainer read-only follow-up confirms ignored
`scripts/__pycache__` in current and both historical checkouts; CLAIM_ABSENT.
The [bytecode correction](mvp2_s2_compute_normal.md#bytecode-recovery--12-october-2026)
qualifies explicit child `-B`, regression-to-physical-closure composition and
separate historical tracked-byte verification without cleaning evidence.
Earlier next-owner/merge wording below describes the prior handoff, not permission
to rerun it. Next owner: agent qualifies this bounded correction; maintainer
authorizes its merge and a new frozen normal-only execution separately.
No new job, live normal acceptance, containment or adverse/native/h300 admission.

PRs #53–#69 successively qualify thread parameters, diagnostic design, runtime
controls, native-worker/evidence seams, containment observations, numeric Slurm
step contracts, controller, batch adapter and operational protocol. Software
component coverage is not live operational qualification. S2 remains OPEN.

PR #63 is integrated; its read-only envelope was independently audited as
observed_not_admitted. PR #65 and then #64 merged on 11 October with authorization;
both develop push Quality runs passed. Job 2207167 at PR65 source
`12691638cd85d5218725bf704dc6b9452b1ca90c` failed 2:0 after two seconds.
Its [audited semantic records](evidence/s2-first-normal-2207167/records.json)
retain blocked_before_launch, not_replayed controller and unknown worker outcome.
Integrity replay passed, not normal/live containment qualification. Maintainer
log inspection also reports no captured error detail; the root cause is unknown.
PR #66's bounded phase/error/code-location diagnostics are integrated, not a
demonstrated repair or live qualification. The [normal continuation gate](mvp2_s2_normal_recovery.md)
admitted one fresh independently claimed observation, preserving the old attempt.
That recovery, job 2207181, failed 1:0 after two seconds. Its independently
[audited carrier](evidence/s2-normal-recovery-2207181/README.md) retains a missing
batch receipt. Supplemental stderr identifies absent `/usr/bin/git` during the
batch predecessor recheck. The [compute identity correction](mvp2_s2_compute_identity.md)
qualifies login/compute separation and early diagnostics as closed components;
the [successor closed integration](mvp2_s2_compute_integration.md) wires batch,
worker, preserved history, adapter runtime and versioned collection. Its public
CLI remains denied. The [successor operational driver](mvp2_s2_compute_normal.md)
now supplies the separately qualified normal-only route, pending authorized merge
and frozen maintainer execution. No live repair or containment is claimed.

| Next dependency | Owner | Required decision/evidence |
| --- | --- | --- |
| Fresh normal operational driver after merged #69 | Agent qualifies code/CI; maintainer reviews merge, then executes pinned CLI | [One-shot normal-only gate](mvp2_s2_compute_normal.md): immutable proposal/job release, Git-free batch/worker wiring, portable collection; no retry of consumed claims |
| Normal evidence and adverse release | Later scoped PR | Independently audit actual normal outcome first; current failure does not release adverse cases |
| Native miniature and h300 diagnostic block | Later independent gates | Fresh admission and original evidence; not authorized by this table |

The PR67 claim is consumed. The new driver must be qualified, explicitly
authorized and merged before its frozen normal-only maintainer CLI is used.
Adverse cases, native miniature, h300 optimization and repeats remain CLOSED.
Do not rerun or patch either consumed PR65/PR67 attempt. Remaining PR count is
conditional on actual live evidence, not a fixed campaign quota.

## Subsequent scope and pending decisions

| Workstream | Status/exit direction |
| --- | --- |
| S1 | Adopted bounded closure integrated in PR #52; deferred ambitions remain explicit |
| S2 | Finish operational qualification, then separately admitted diagnostic evidence/decision; no-benefit or bounded negative outcomes can be valid |
| Former S3/S4 | Cancelled, not experimentally completed |
| Existing SCIP h215 | After S2: audit root LP, supported bounded hypotheses and a smaller positive control before any admitted large attempt |
| S5 h500 | Conditional input/build/resource gates and bounded empirical frontier; not yet optimized or admitted |
| S6 | Computational/HPC synthesis, coauthor reconciliation and separate reproducibility packaging |
| Main synchronization | Final consolidation after article review, not S2 closure; inspect both ancestry directions, promotion scope and effective protection/checks; separate Ready/merge approvals |
| Portable-memory integration | PR64 merged with authorization; its files belong to develop and a later reviewed promotion unless explicitly scoped otherwise |

EVPI/VSS and section 3.8 are to be excluded at S6; these calculations are no
longer remaining experiment work. The article and presentation are unchanged now.
The exact manuscript version last emailed to coauthors remains to be identified
before editorial integration. No release, deposit, submission or deadline is
authorized by this status snapshot.
