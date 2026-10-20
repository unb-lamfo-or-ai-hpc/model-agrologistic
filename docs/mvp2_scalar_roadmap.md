# Scalar MVP2 roadmap — 19 October 2026

20 October update: R1 merged in PR112. The maintainer approved the prospective
R2 envelope below. The [R2 package](mvp2_scalar_r2.md) is being prepared/qualified;
no NPAD job has been executed/admitted by that software work. Later stages and
their separate scientific/resource decisions remain unchanged.

The [scalar contract](mvp2_scalar_contract.md) supersedes the unexecuted PR111
hierarchical h400 continuation, not the historical S0/S1/S2 certificates.
R1–R5 below do not reopen cancelled S3/S4.

R1 implementation and small native software qualification are consolidated in
[PR112](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/112);
[recorded results](mvp2_scalar_r1_qualification.md) do not admit R2 or NPAD.
PR111 is closed as superseded, with its branch/history preserved. PR112 has merged;
R2 remains subject to final-head checks, Ready and explicit merge authorization.

| Stage | Complete functional package | Acceptance / dependency |
| --- | --- | --- |
| R1 | Scalar code/configuration/validation/tests/documentation | DET/STO equivalence, investment once, three penalties, independent costs, exact-head qualification; no NPAD |
| R2 | Small mathematical/operational qualification, wrapper and collector | R1 merge; actual small native evidence, bounded phases/resources, independent review, new budget proposals; human CLI only |
| R3-A | h215 DET/STO baselines and h300 scalar threads | R2 accepted; audit h215 before h300 admission; fixed factors within each contrast |
| R3-B | h400 scalar package | Choose a candidate from new baselines, not old hierarchical ranking; approve h500 criteria BEFORE h400 execution |
| R4 | Existing SCIP/h215 complementary package | Scalar qualification and explicit root-LP/search hypothesis; may overlap R3 after baseline |
| R5 | Conditional h500 frontier | Scalar h400 success plus new input/build/resource/transfer admission; SCIP success not required |
| S6-A | Scientific synthesis | Audited scalar positive/partial/negative results, controlled comparisons and limits; MVP1 contextual only |
| S6-B | Article and reproducibility | Preserve coauthor revision; revise framing/methods/tables/figures/appendix; exclude EVPI/VSS; human publication approval |

Planning allowance: R1 approximately 1–2 weeks, R2 about one week, scalar
h215/h300/h400 during November; conditional h500 potentially late November/
December. SCIP preparation, evidence inventory and editorial structure can run
in parallel. These are engineering/review windows, not queue/success predictions.
Keep M2 15 November (intermediate methodology), M3 23 December (consolidation)
and M4 31 December (submission target). December is accelerated/high risk;
January2027 remains the provisional base forecast. Re-estimate after R2 and
scalar baselines, preserving approved scope and a real coauthor review window.

Aim for 8–9 functional PRs including conditional h500 and one/two editorial
packages, not a quota or guaranteed count. Related repairs stay in the same PR.
Final protected-main integration needs separate authorized Ready PR(s) after
article review; it is not a prerequisite for experiments.

## Prospective resource ledger — not an admission

Do not automatically inherit 3600s/28800s hierarchy budgets or four-thread
ranking. R1 tests use public tiny analytical models, not scalability campaigns.
Approved R2 ceiling,20 October: one solver thread, at most four allocated logical CPUs,
at most 8GiB, at most 60s optimization per small case and a 20-minute reservation
including build/validation/cleanup/collection. Reservation ceiling: 1.333 allocated
logical-CPU hours, not measured CPU/billing. R2 software qualification, explicitly
authorized merge and human CLI remain required; R1 alone admits no allocation.

Each later h215/h300/h400/SCIP-h215/h500 proposal must specify allocated logical
CPUs, solver threads, observed affinity/SMT, memory request/native ceiling, build,
scalar solve, late-return/export, cleanup, fresh validation and collection windows,
core-hours, expanded transfer cap, acceptance/stop rules and dependencies.
Aggregate compatible serial arms only where justified; no automatic follow-on
across size gates or unapproved repeats.

Historical application RSS roughly56–58GiB for S2 h300 and101GiB for S1 h400 is
a sizing reference only. Different formulations/scopes cannot predict scalar
memory/time. Large scalar budgets/core-hour forecasts are not yet justified:
derive them from admitted baseline measurements. Measure sparse-output volume;
do not truncate evidence to satisfy a transfer cap.

Before h400, approve a numerical global-gap/absolute-gap quality criterion and
resource-headroom rule. h500 needs an independently feasible h400 incumbent
meeting that criterion, reconstructed objective, closed source/input/runtime/
terminal evidence, respected budgets and an admissible h500 estimate. Slurm
COMPLETED alone is insufficient. If the gate fails, preserve the result and
return the scientific decision to the researcher; do not silently cancel h500,
loosen criteria or retry.
