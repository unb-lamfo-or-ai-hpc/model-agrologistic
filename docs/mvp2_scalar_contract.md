# Scalar economic MVP2 — R1, 19 October 2026

## Approved scope and history

DET and two-stage STO minimize one scalar economic objective. This replaces
the unexecuted hierarchical h400 qualification in PR111. Before code changes,
the complete develop tree was published on `archive/mvp2-multiobjective-20261019`
at **5f9daa55b3afb5bbcb3449bc83c970cf10a28ca6**. Never change that reference.
PR111 remains preserved at `dffc8b79e8c6c8033be0fb5fbff6d7b6ca1d8f7c`.
[Immutable historical source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/tree/5f9daa55b3afb5bbcb3449bc83c970cf10a28ca6).

S2 remains closed as its bounded historical diagnostic. Its five feasible,
time-censored hierarchical arms neither certify scalar performance nor select
scalar threads. Preserve original evidence/certificates/checksums, external raw
archives, failed attempts and NPAD claims. Do not overwrite or reset them.

## Mathematical contract

Minimize investment plus the probability-weighted sum of transportation,
storage and three feasibility penalties. Opening, candidate capacity, expansion
and bulk-handling investments are scenario-independent, precede the first period
and are charged once. Operations and slacks depend on the scenario. Each model
uses one native scalar objective and one optimizer call.

DET embeds its original deterministic arrays as one scenario of probability one
in the same extensive-form builder. It does not silently select a stochastic
realization or average uncertain demand. Its existing output API retains records
without scenario columns. A matching one-scenario STO must be mathematically
equivalent; multiple optima need not produce identical decision records.

Preserve sparse routes, physical constraints, eligibility, balances, 60-period
interpretation, daily conversions, penalty rules and independent validation
tolerances. Preserve exactly these slack families:

1. Domestic shortage: tonnes in the demand balance.
2. Static exceedance: warehouse-period stock tonnes.
3. Reception overflow: tonnes in the period, added AFTER nominal daily reception
   is converted to that period; never multiply this slack by operating days again.

No fourth slack or separate slack objective. Positive slack means a relaxation
was used, not installed capacity or proof of no-slack infeasibility. Report
investment/operation costs and artificial penalties separately: penalty totals
are not observed financial expenses. Do not recalibrate coefficients or change
other scientific parameters without scientific approval.

## Active pipeline and migration

Data -> scenarios -> sparse network -> scalar MILP -> solver -> independent
feasibility/cost validation -> economic/resource outputs -> scalability -> article.

Reuse loaders, scenario generation, route filtering/repair, sparse construction,
original-unit validator, ownership/disposal, optional default-off compaction,
bounded OS/native telemetry, source/runtime identities and completion integrity.
Gurobi is the reference; native SCIP/SoPlex remains complementary. No new solver.

Remove active priorities, stage-only drivers/instrumentation and EVPI/VSS
calculation/campaigns. Their exact code, launchers, workflows and old tests remain
recoverable from the immutable archive. Historical documentation and manuscript
are records, not current execution instructions. Original evidence JSON stays
unchanged. The coauthor-reviewed manuscript is revised only at S6, without
automatic Pages publication.

Manifest **version 2** is the scalar contract. Version-1 campaigns and removed
analysis/stage fields fail explicitly; never silently convert old campaigns.
The stable `objective_policy="penalty"` key is retained as the only accepted
policy. New runs cannot overwrite old output directories. Source package
boundaries prevent removed modules leaking from another editable installation.
New source identities do not upgrade historical completion certificates.

## Acceptance and tests

T1 focused while editing; T2 related after stabilization; T3 full retained suite,
lint/build and exact-head Linux native tests before Ready. Record initial failures
and platform/license limitations honestly. A licensed-test skip is not acceptance.

Required analytical cases: hand-calculated objective; DET/one-scenario STO parity;
unequal probabilities; identical-scenario splitting with investment charged once;
each separate slack and its units; direct/transshipment/capacity coupling;
corrupted costs/residuals; no incumbent; failed cleanup; bounded telemetry;
completion integrity; and real Excel/slotted ExperimentSpec integration.

Reconstruct every cost component and the scalar total independently. Preserve
raw solver objective, best bound, global gap, native status and incumbent existence
separately from feasibility. SCIP native gap and the common incumbent-denominator
gap have distinct labels. No-incumbent is not infeasibility; censored work is not
completed-work speedup. Do not interpret changes in routes/scenarios as pure
population effects.

## Execution/governance boundary

R1 executes no NPAD job/probe and admits no allocation. The batch CLI denies
optimization inside Slurm pending R2. Resource/time/transfer budgets, claims,
pinned CLI and executions require separate qualification and human approval.
Reuse minimum academic controls, not unavailable production-isolation guarantees.
No retry or automatic follow-on. Ready precedes explicit merge authorization.
S3/S4 stay cancelled; EVPI/VSS remain permanently excluded. Main/develop
reconciliation occurs only after reviewed S6-B, under separate Ready PRs/approval.

Maintainer WLS confirmation: preserve the existing designated NPAD license and
its previously established path; no replacement or path migration was approved.
R2 must explicitly select that existing authorized license and bind a redacted
fresh capability receipt. Never publish WLS values or infer a license failure
from missing solve progress. R1 does not access or change the license/environment;
the expired local Windows license is not a diagnosis of NPAD WLS capability.
