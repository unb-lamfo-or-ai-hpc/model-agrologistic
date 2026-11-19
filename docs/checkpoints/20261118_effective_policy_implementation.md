# Approved optional policy implementation checkpoint — 18 November 2026

The researcher approved beta/alpha scopes and levels and requested their
implementation in PR158, repeat tests and solver-free CI. Both PR156 and PR158
remain Draft. No new HPC job, solver execution, merge or manuscript change is allowed.

The first deliverable was a hash-checked national product/scenario table from
accepted native DET/STO and Pyomo STO h215 W vectors: 38 rows, separate cohorts.
It exposes full maize service and soybean STO service of 73.28186%–90.13119%,
with soybean export shares of 66.69067%–72.60320%. These are historical incumbent
outcomes, not new constrained experiments or exact optima.

Optional rows are added only through the effective pipeline's construction entry
point, reusing the unchanged core Pyomo builder. No new variables/objective terms
or changes to legacy/native builders are introduced. Null defaults retain the
old matrix. The effective validator composes original physical/cost checks with
independent unweighted policy sums and conservative sparse-export precision checks.

Read [implementation](../effective_policy_implementation.md),
[historical table](../effective_h215_policy_reference.md) and
[readiness](../effective_ci_and_merge_readiness.md). The earlier proposal/CI and
h215 qualification receipts remain historical evidence. New test/CI results are
recorded separately; tiny manual-vector checks are not large-instance numerical
qualification. Initial software-test failures are preserved locally and corrected
without changing original evidence.

Final local repetitions passed 110 tests each, with zero errors/failures/skips,
optimizer calls or forbidden execution attempts, and identical source inventories.
Ruff, Node syntax and offline wheel packaging passed; all 50 packaged source
modules match. The [implementation receipt](../evidence/effective_policy_implementation_20261118.json)
binds these checks, original table hashes and preserved scientific/CI sources.
Actual final-head cloud CI is reviewed separately in PR158, never inferred from
local tests. The original pandas warning and packaging deprecation remain disclosed.

The future execution package must use effective construction and effective
validation together; generic/native historical solve routes do not implement
these optional policies. No controller or current array2252608 is modified.
After review, integration and future h215 execution still require their own
researcher authorization. No h300+ extension is admitted by this checkpoint.
