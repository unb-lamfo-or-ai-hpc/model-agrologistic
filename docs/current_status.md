# Dated research status: 9 October 2026

This is a derived handoff snapshot, not a new certificate. Reviewed integration
base: develop `01016fbbbdfdc6dd7cf005488105b4d3181f671d` (PR #62).
Read [PROJECT_STATE.md](../PROJECT_STATE.md), the [roadmap](mvp2_hpc_roadmap.md)
and linked evidence for full history. Refresh live PR state before continuing;
open PR content is not integrated code. This document's branch is a separate
[portable-memory proposal](research_context.md), not an execution gate.

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

PRs #53–#62 successively qualify thread parameters, diagnostic design, runtime
controls, native-worker/evidence seams, containment observations, numeric Slurm
step contracts, controller, batch adapter and operational protocol. Software
component coverage is not live operational qualification. S2 remains OPEN.

[PR #63](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/63)
is open/Ready at `7532beea7ffa429ba9f34bfd091bd60069efc4f8` as inspected on
9 October. It repairs a long-path IPC test fixture and versions a read-only
envelope-recovery driver; the production adapter is unchanged. Its audit retains
an initial timing-sensitive legacy-control CI failure and a successful same-head
rerun. Neither is evidence of NPAD containment. The maintainer reports that the
PR63 command has not been executed. Do not infer a merge or an envelope result.

| Next dependency | Owner | Required decision/evidence |
| --- | --- | --- |
| PR63 integration | Maintainer | Separate merge authorization after review; verify live state |
| Read-only installed-envelope observation | Maintainer executes CLI | Only the exact merged-source-pinned PR63 handoff; preserve failure/location receipts |
| Envelope evidence review | Agent prepares audit; maintainer decides | Actual portable receipt and checksum, including any blocked outcome |
| Limited first-normal synthetic qualification | Later scoped PR | Installed grammar, exact-step ownership/cleanup and live containment must be qualified before release |
| Native miniature and h300 diagnostic block | Later independent gates | Fresh admission and original evidence; not authorized by this table |

No new CLI is introduced by the memory package. Synthetic jobs, native miniature,
h300 optimization and repeats remain CLOSED. Do not rerun the PR62 bootstrap or
skip regressions because PR63 has not yet been executed. Remaining PR count is
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
| Portable-memory integration | Keep separate branch/PR until destination decided; merging to develop normally includes these files in a later main promotion |

EVPI/VSS and section 3.8 are to be excluded at S6; these calculations are no
longer remaining experiment work. The article and presentation are unchanged now.
The exact manuscript version last emailed to coauthors remains to be identified
before editorial integration. No release, deposit, submission or deadline is
authorized by this status snapshot.
