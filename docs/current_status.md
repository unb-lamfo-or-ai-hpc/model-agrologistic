# Dated research status: 12 October 2026

This is a derived handoff snapshot, not a new certificate. Reviewed integration
base: develop `478d5ee513994a20e8788f1f504b195a7f67f346` (PR #73 merged).
Read [PROJECT_STATE.md](../PROJECT_STATE.md), the [roadmap](mvp2_hpc_roadmap.md)
and linked evidence for full history. Refresh live PR state before continuing;
open PR content is not integrated code. The [portable memory](research_context.md)
was integrated with explicit authorization; it is not an execution gate.

## What is established

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
| Main synchronization | Deferred to S2 closure; inspect both ancestry directions and effective protection/checks |
| Portable-memory integration | PR64 merged with authorization; its files belong to develop and a later reviewed promotion unless explicitly scoped otherwise |

EVPI/VSS and section 3.8 are to be excluded at S6; these calculations are no
longer remaining experiment work. The article and presentation are unchanged now.
The exact manuscript version last emailed to coauthors remains to be identified
before editorial integration. No release, deposit, submission or deadline is
authorized by this status snapshot.
