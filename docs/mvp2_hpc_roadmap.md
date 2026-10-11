# MVP 2.0: evidence-led computational roadmap

## Authority and scope

Reconciled 9 October 2026 after PR #56 integration and the maintainer's revised
scope. S1-C followed PRs #44, #47, #48, #49, #50 and #51. This plan supersedes the earlier roadmap's
mandatory solver campaign, decomposition implementation and calendar estimates.
It does not rewrite archived results. The [S1 closure](mvp2_sprint1_closure.md)
defines original receipts, adopted exit criteria and explicit limitations.

The research question is which instance and computational profile can complete
the service/capacity/economic hierarchy for agricultural storage and transport
networks under uncertainty, with original-unit independent feasibility and
declared resource/time limits. Principal decisions are strategic facility
opening, capacity and network planning; transport/storage operations provide
tactical context. This is not evidence of operational deployment.

Computers and Electronics in Agriculture is the intended journal, subject to
coauthor approval and demonstrated contribution. The contribution is computational
evidence relevant to agricultural decision support, not merely cluster use or a
solver-brand ranking. No acceleration is assumed. The frozen `v0.2.0-mvp1`
release, model, data and historical results remain unchanged.

Coauthor agreements were supplied on 7 October 2026; the meeting date was not
provided. Their scope changes are recorded here, not applied to the article.
No Benders or other decomposition implementation belongs to this study.
The former S3 new-solver scope and S4 decomposition scope are cancelled. Revisit
the existing SCIP backend at h215 after S2; then assess one h500 Gurobi frontier.
This is not an admission for any execution. Do not seek adverse results: success,
partial progress and failure are all informative only with adequate evidence.
Sprint numbering is retained to keep historical references intelligible.

## Evidence baseline and experimental invariants

The [MVP1 thirteen-attempt comparison](evidence/sprint_c_final_20260920/comparison_summary.md)
remains a historical cohort, including unsuccessful configurations. Historical
h300 automatic/all-barrier and h400 memory/time stops remain distinct profiles.
The new accepted h400 control is neither a correction of historical failures
nor proof of causal improvement. SCIP no-incumbent outcomes do not establish
infeasibility or a universal backend ranking. S1 adds six accepted h215 arms,
one separately reviewed h300 baseline, one descriptive h300 pair and one h400
control. Input-only acceptance does not certify optimization.

- Preserve canonical workbook identities, nested populations, nine scenarios,
  probabilities, sixty periods, two products, units, terminal inventory and
  audited grouped route selection/repair. Aggregated federative-unit flows are
  not a full municipal network. Verify filter/cache claims and actual retained
  routes from implementation before publication. Potential multi-hop reachability
  is not active-network throughput feasibility.
- Preserve native service-first hierarchy and original independent validation.
  Pass certificates, feasibility, final degradation and scheduler termination
  are separate decisions. A feasible incumbent or COMPLETED/0:0 is not complete
  acceptance; OPTIMAL with tolerances does not mean exact zero-gap optimality.
- Keep inherited Gurobi MIPGap=0.1 and native hierarchical allowances. Report
  pass incumbent/bound/gap separately from final capacity and its difference
  to the retained bound. Near-zero service uses its declared absolute tolerance,
  not the relative-gap sentinel. The meeting's "below 10%" shorthand does not
  replace the audited contract.
- Keep seed 42 for common comparisons; it alone does not imply determinism.
  Hold model, runtime/source, LP method, cold start and resources fixed for
  thread contrasts. Memory/methodology changes require separate comparisons.
- Distinguish optimization, build, extraction, validation, application and
  scheduler clocks. Eight hours is the current optimization budget; Slurm
  headroom is separate. A possible 24-hour budget is not admitted.
- Separate SoftMemLimit decimal GB, allocation/RSS units, finite cgroup limit,
  requested/allocated CPUs, solver threads and measured CPU usage. Do not infer
  available resources from node labels or reduced allocation from sampled peaks.
- Preserve source/environment receipts, durable claims, adverse outcomes and
  new-directory protocols. Missing telemetry and censoring stay visible. Portable
  replay is not new residual validation or a fresh private-workbook reload.
- Production-scale sparse coefficient/objective fingerprints remain a desirable
  gate for future formulation changes; miniature fingerprints and matching
  aggregates/exports do not prove large-model formal equivalence.

## S0 — instrumentation and miniature qualification: evidence complete

Corrected licensed NPAD job 2143922 passed 138 tests without skips and twelve
miniature Gurobi/SCIP observations. Initial ObjBound conversion failures remain
archived. Instrumentation and native ownership are implemented. Large-run causal
sampler overhead and continuous five-second coverage are not established; those
limitations are explicit, not silently marked satisfied.

## S1 — lifecycle and bounded memory study: integrated bounded closure

S1-A: accepted h300 warehouse-only input, baseline and descriptive compact-first
pair. S1-B: accepted h400 direct input and one instrumented control. S1-C:
consolidate those with three h215 pairs, record exit decisions and reconcile
this roadmap. Documentary PR #52 merged at
`9d302406e2aae0958ff61084f750fa4cf1730eac`, closing the adopted bounded scope.

Compaction stays optional/default-off. Paired application RSS was lower, runtime
effects varied and native solver memory was essentially unchanged. No causal
gain, significance, reduced construction peak or smaller allocation is demonstrated.
Production retains the native hierarchy. Explicit reuse/rebuild equivalence is
qualified only on restricted miniature original MIPs. Large rebuild, generalized
copy elimination, crossover changes and scalable fingerprints are deferred.
No extra pair or h400 compact arm is automatically admitted.

## S2 — next: separately qualified Gurobi thread screening

First PR: [qualify thread parameters and one-shot collection](mvp2_thread_qualification.md)
on five licensed analytical miniatures, 1/2/4/8/16 threads, seed 42 and all-barrier.
Accepted [job 2202239 and portable residual/integrity audit](mvp2_thread_qualification_evidence.md)
close this first gate only. CI software checks remain distinct from original
NPAD scientific evidence. Production remains closed. Select
h300 warehouse-only uncompacted control as the proposed production reference,
with a common 1800-second diagnostic optimization window, original memory and
method, fixed node class and at least 16 CPUs/task. The miniature envelope is
separate from production and provides no production speedup or utilization claim.

After PR #53 integration, the [h300 design gate](mvp2_h300_thread_design.md)
qualifies homogeneous environment, diagnostic/watchdog arithmetic, partial
observations and resource metrics without admitting execution or repeats.
Split live implementation/admission and resulting evidence/decision from that
solver-free gate. Only a subsequent qualified, separately admitted bounded block
can inform any selected full-budget or replicated block. This split replaces the
earlier combined "second PR" boundary; it is not an extra experimental campaign.
After PR #54 integration at `31c6dd8b0462af14d74997773e30bdda099e4b22`,
the [runtime component gate](mvp2_h300_runtime_controls.md) implements parent
watchdogs, immutable claims, post-cleanup parent closure and portable partial
review. It does not qualify a native production worker, live allocation/cgroup
containment, fresh license/homogeneity, production telemetry or source/cohort
admission. Those remain a closed integration/qualification step before any
separately authorized diagnostic block. No optimization or repeat is admitted;
component completion does not close S2 or establish thread performance.
After PR #55 integration at `af7271962d314d5c1e26f1c7745147ea071c4c7f`,
the [closed native-worker gate](mvp2_h300_native_worker.md) connects strict
native-call seams, effective global limits and native count snapshots to partial
export. Fake native APIs qualify software paths, not licensed parity or h300
resource sufficiency. Its changed implementation must receive a new source/cohort
qualification; historical design hashes and accepted archives are not rewritten.
Full worker-evidence transfer, live sampling and allocation-wide closure remain
closed qualification steps before a separately authorized miniature protocol.
No job, optimization block or repeat is admitted by this integration.
PR #56 was integrated at `0443b1c23fc98b147f73618a5db50131dc2de70e`.
The next [worker evidence/resource gate](mvp2_h300_worker_evidence.md) implements
a separate whole-worker envelope, actual byte/runtime binding and read-only
Linux resource/containment observations. The public entries remain denied.
Existing process-group controls are not allocation containment; delegated cgroup
setup, race-free worker placement, enforced teardown and licensed integration
still need a separately qualified miniature protocol before h300 admission.
Compare equal completed work, stage latency, time-to-bound,
time-to-incumbent, effective CPU use, core-hours and memory. Speedup T1/Tp and
efficiency (T1/Tp)/p require comparable completed work; censored runs are not
ordinary complete timings. Disclose shared-node/order effects. Balanced repeats
are necessary before stronger performance claims; allocated CPUs are not active
solver threads.

Memory response is a separate conditional PR with fixed threads and measured
headroom. Higher caps, 512-class nodes or lower allocations are not automatic
deliverables. Seed sensitivity, warm starts and LP changes likewise need separate
rationale/qualification. Node files are not assumed to fix root-LP factorization.
Exit: audited response including no-benefit/failure profiles, explicit comparison
limits and justified next-profile decision. Speedup is not required for success.

## S3 — new alternative solvers: cancelled

Maintainer decision of 9 October: no HiGHS, CPLEX or additional solver campaign.
Preserve historical numbering and evidence; cancellation is not completion of
an experiment. The existing SCIP backend has the separate bounded scope below.

## S4 — decomposition: cancelled

The earlier Benders/multi-worker prototype plan is superseded. Do not implement
decomposition to finish MVP2. Mention it only briefly as future research in the
conclusions at S6, not a dedicated subsection implying an unfulfilled requirement.
A later method would need new mathematics, valid global bounds, miniature
validation and smaller instances under that same method before comparisons.

## Existing SCIP h215 requalification — bounded, after S2

Audit the original LP-root bottleneck before parameter screening: both historical
h215 variants timed out without an incumbent during the first root LP, with
about 12.5 million transformed continuous variables. This is not mathematical
infeasibility or a universal SCIP inability. Preserve SCIP/SoPlex build, LP method,
numerics, presolve, resource and stage-clock provenance. First investigate the
existing pinned stack, not a silent dependency upgrade or new commercial LP.

Form a small evidence-led set of supported LP/presolve hypotheses; qualify on
analytical fixtures and a smaller positive control before a bounded h215
warehouse-only screen. At most one justified candidate receives a separately
admitted full-budget attempt; no parameter sweep or automatic retry. Do not
loosen numerical/priority tolerances to obtain apparent success, substitute a
weighted objective, seed with a Gurobi solution without a separate warm-start
experiment, or claim parameter availability proves LP/thread capability.

Record construction, root LP completion, independently valid incumbent and full
hierarchy acceptance separately. A smaller solved control does not meet h215.
Negative closure describes tested profiles and resources, not "nothing else can
work". Planning estimate: two or three scoped PRs, not a solver campaign quota.

## S5 — h500 empirical frontier, after S2/SCIP review

Prioritize h500 with direct arcs to preserve the accepted S1-B h400 policy;
verify nested population and all other input/model identities. Separate input-only
and construction/resource qualification from one admitted bounded baseline and
evidence review. Initially retain the h400 four-thread profile and eight-hour
optimization budget if resource-admissible; h300 thread screening does not
automatically transfer its best setting to h500. Do not change time, memory and
threads together or globally relax size guards. No h600--h1000 commitment.
Difficulty need not increase monotonically with population. Planning estimate:
two or three scoped PRs; original negative outcomes remain preserved.

Distinguish construction-admitted, independently feasible-incumbent and complete
hierarchy-certified frontiers per method/resource/time profile. The largest
accepted instance is not a universal solver/model limit. Retain timeout, partial
hierarchy, OOM and no-incumbent outcomes without imputing costs/service. A
documented sufficiency decision may close S5 without every candidate size.

## S6 — editorial synthesis and reproducibility package

Current article/presentation stay unchanged until the editorial gate. Deepen the
computational/HPC discussion around dimensions/nonzeros, phase-specific LP/MIP
bottlenecks, effective parallelism versus allocated CPUs, scope-specific memory,
quality versus runtime/core-hour cost, adverse outcomes and reproducibility.
Keep agricultural strategic decision support central. Empirical difficulty is
not an asymptotic complexity proof or universal solver ranking. Identify
the exact manuscript linked in the last email to coauthors: URL/version not yet
provided; Pages/local copies are not assumed authoritative. Respect the review
freeze and check applicability of older comments before integration.

An editorial PR reconciles audited results, strategic framing, accessible
definitions/units and coauthor comments. Preserve the full approximately 21-page
systematic review by Artur and collaborators as appendix/supplement, confirming
the authoritative file; no unverified AI condensation. Explain mathematical
indices/variables/results for non-HPC readers. Gabriela/Rodolfo emphasize coherence
and comprehension; Luis emphasizes homogeneous comparisons. AI assists drafting
and verification, not scientific authority. Victor manually incorporates final
LaTeX changes after human review.

Exclude section 3.8, "Value of information and stochasticity", and EVPI/VSS only
at S6; those calculations are not remaining MVP2 work. Emergency-capacity reliance
and penalty shares are not actual financial performance.

A separate packaging PR reconciles Appendix A, figure/source provenance,
complete/adverse evidence, cached-route identities and release manifest. Plan a
new version linked to exact code and final Zenodo deposit; preserve MVP1 archives.
Release, deposit, preprint and submission require their own later decisions.

## PR and execution boundaries

Counts are scope boundaries, not quotas/dates: after #56, S2 has an estimated
four gates (closed integration, licensed miniatures, h300 admission, evidence/
decision), with narrower splits only when justified. S3/S4 are cancelled; bounded
existing-SCIP requalification precedes h500; S6 editorial synthesis stays separate
from packaging. Do not launch follow-on fronts inside the closed integration PR.
Do not schedule speculative campaigns to fill sprint numbers.

After #57, closed integration evidence/resource replay is software-qualified.
The licensed miniature integration has one justified prerequisite split:
[compute-node containment capabilities](mvp2_s2_containment_gate.md). A read-only,
solver-free input allocation establishes facts before implementing effective
worker containment. This does not complete miniature qualification, admit h300
or add a research campaign; missing delegation cannot be silently bypassed.

After #58, job 2202795 input evidence replay is accepted but its capability
outcome is blocked_environment (cgroup v1, existing path requires v2). The
subsequent read-only site inventory supports investigating Slurm-owned numeric
worker steps, not claiming effective containment. The justified next split is a
[closed step contract and read-only v1 observer](mvp2_s2_slurm_step_gate.md), with
no launcher or job admission. The proposed 390-second cleanup observation budget
accounts for declared KillWait 300 s and UnkillableStepTimeout 60 s plus margin;
it is not a guarantee of termination. A separate bounded synthetic integration
and live audit must precede licensed miniatures. This does not require upgrading
the cluster or change the research scope, tolerances or blocked h300 campaign.

After #59 merged at `a4ce020d01298a292ab10819d21355775a562b85`, the v1
observer/step contract is software-qualified. The next gate implements
[closed synthetic launcher/controller and partial-evidence components](mvp2_s2_synthetic_controller.md)
using injected transports, not a live job driver. Actual step ownership, finite
enforcement, complete descendant cleanup/reaping and no late writes remain live
qualification obligations. No synthetic, licensed miniature, h300 or repeat is
admitted by component regression or merge. Finish the actual bounded batch
adapter and its explicit synthetic-only protocol before requesting NPAD CLI.

PR #60 merged at `4472c8429a2aa99d10a716d827f1f6bfa0ec022a`.
The [closed real batch adapter](mvp2_s2_batch_adapter.md) integrates POSIX pipes,
kernel-peer IPC, raw source/runtime/allocation checks, actual numeric-step binding,
controller events/resources and terminal partial/adverse collection. Its public
CLIs stay denied; offline regression cannot promote any admission flag. Next is
the separately frozen installed runtime/tool envelope and synthetic-only
admission/terminal protocol, including interruption, unknown client/remote
cleanup and strict installed command grammar. No NPAD command is admitted yet.

PR #61 merged at `dd68588a5bdfe1f6536e357dab049509678659e4`.
The [operational protocol gate](mvp2_s2_operational_protocol.md) now qualifies
the closed first-normal one-attempt proposal, interruption/unknown-effect
dispositions and externally checksum-bound partial collection sidecar. Only
the installed-envelope read-only probe becomes executable after merge: no
allocation, step, synthetic exercise, solver/license or repeat. Actual installed
binary identities/configuration are a concrete missing input; do not fabricate
them or equate declaration with live containment. Independently audit the probe
before separately qualifying the first-normal live wrapper/installed grammar.
Then audit that one normal attempt before any adverse synthetic case, licensed
miniature or fresh h300 admission. This is not S2 closure or a performance result.

PR #62 merged at `01016fbbbdfdc6dd7cf005488105b4d3181f671d`.
The first read-only bootstrap stopped before the probe: the Linux kernel-peer
test inherited a pytest path exceeding the unchanged 100-byte IPC guard.
The maintainer reported 166 passed, one failure, one intentional skip and no
job submission. This is a fixture portability defect, not an observed Slurm,
license, native-worker or containment failure. The reported directory existed
during the traceback; its present location is unverified, not recreated.
The [scoped recovery correction](mvp2_s2_envelope_recovery.md) preserves that
attempt, fixes only the disposable test endpoint and versions the read-only
driver with phase/location receipts. It does not add a research campaign or
admit synthetic/native/h300 execution. S2 remains open; the next scientific
decision still requires independently audited installed-envelope evidence.

## S2 closure — deferred protected-main reconciliation

Maintainer decision on 9 October: synchronize only at the end of the current S2,
not inside intermediate containment or diagnostic PRs. GitHub's develop view at
`a4ce020` reports 111 commits ahead of main and 1 behind; this dated UI observation
must be recomputed at closure. It is not a conflict assessment or authorization
to overwrite main-only work. The attached PDF and read-only live settings review
on 9 October now document the ruleset below; prior unaudited-rule wording is
superseded for this dated snapshot, not for later effective-rule changes.

Ruleset `model-agrologistic-main-protect`, ID 24804465, is Active and targets
`refs/heads/main` only. Restrict creations, updates and deletions are selected;
required status check is `check-branch`, Any source. Organization admin has an
Always allow bypass. Require-PR, linear history, up-to-date-before-merge and
block-force-push are not selected. PDF SHA-256:
`b2860c7cfc51bca4387a03e8dd92fc1a4232caf633fea435543080b9c3d25866`.
These settings restrict ordinary writers but do not make main immutable against
an exempt admin. They do not establish this assistant/account's bypass role.
No rule, actor, permission or workflow is changed here. At closure recheck the
effective rule set and the implementation/provenance of `check-branch`; a missing
or failing required check is a blocker, not authorization to bypass it. Review
PRs remain our workflow even though this ruleset does not itself require them.

At closure, inspect exact main/develop heads, both ancestry directions, exclusive
commits and affected files. If main has exclusive history, first prepare a scoped
main-to-develop reconciliation PR, resolve conflicts explicitly without dropping
either side, qualify exact-head CI and request approval only when Ready. Then
prepare the develop-to-main promotion PR for the integrated S2 snapshot, with
evidence ledger, scope/diff and checks. No force-push, history reset, protection
bypass or rule weakening. A blocked protected-main merge is handed to the
maintainer through normal review/merge controls.

Prefer an allowed ancestry-preserving integration strategy. If promotion creates
a new merge commit on main, develop can become one commit behind despite equal
code trees: finish with a reviewed main-to-develop back-merge, if necessary, and
verify main is an ancestor of develop and the integrated code trees match at
handoff. If the rules require squash/rebase, inspect the resulting graph rather
than assuming synchronization from equal files. One PR may not satisfy both
directions; the sequence depends on the actual protected-branch rules and graph.

Protection governs permitted mutations; it does not make history universally
immutable against actors allowed by those rules. Release/tag/deposit and public
manuscript deployment remain separate decisions. No promotion, reconciliation,
rule change or merge authorization is exercised by the current software PR.

GitHub main stays stable, develop integrates scoped PRs. Qualify exact-head CI
and mark Ready before requesting merge. The assistant prepares scoped code/docs;
NPAD CLI is executed by the user and merge needs separate authorization. This
S1-C performs no job, release, deposit or article edit.
