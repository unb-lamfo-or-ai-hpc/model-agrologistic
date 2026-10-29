# Pyomo h215 W three-solver continuation — researcher mandate, 29 October 2026

## Required order and experiment scope

The researcher requests completion of PR139 and preservation of the original
evidence first, followed by a separate PR implementing Pyomo adapters for Gurobi
and SCIP and preparing new h215 STO/W observations with Gurobi, SCIP and CBC.
This replaces the earlier optional-benchmark planning position. It does not
authorize an agent HPC connection, repeat of an old start or merge without the
researcher's approval.

PR139 closes the current journal-reader/evidence consolidation after its pending
local document checks. Original certificates/packages and the historical
Gurobi/SCIP/HiGHS outcomes remain unchanged. Full bibliographic and original
Appendix A reconciliation remains a distinct editorial workstream, not a claim
of completed full-text review.

The next PR will build every new arm from the same existing bounded Pyomo
extensive form, without changing physical inputs, selected OSRM routes, scenarios,
penalties, units or the original independent validator. Native reference backends
remain intact. Existing HiGHS evidence is preserved as a reference; the new
requested experimental set is Gurobi, SCIP and CBC, not a HiGHS restart.

## Solver strategy and adapter behavior

Pyomo is the modeling layer; the solver still executes presolve, relaxations,
cuts, branching and heuristics. APPSI's Gurobi adapter uses gurobipy, applies
requested options and calls the native optimize method. Unless explicitly
overridden, the solver retains its own defaults and automatic strategy.
This does not promise identical search versus our native indicator model:
the bounded Pyomo representation, row/column order and coefficient translation
may differ.

Use APPSI Gurobi with an explicitly owned lifecycle. For SCIP, evaluate a
persistent adapter translating Pyomo's standard linear representation through
the already installed PySCIPOpt API, avoiding an assumed available SCIP/AMPL
executable. Reuse the same Pyomo model builder, not the native scientific builder.
Reject nonlinear/SOS/unsupported components rather than silently drop them.
CBC retains its explicit executable interface; availability, build capabilities,
LP-file cost and terminal parsing require qualification.

Do not force presolve, barrier, dual simplex, heuristics or cuts in the initial
comparison. Record installed defaults, all requested/effective overrides and
observed algorithmic behavior. Algorithm tuning, warm starts and repetitions
are separate contrasts, not implicit retries.

## Seed semantics

A pseudorandom seed is not a MIP start, initial feasible solution, LP basis or
shared random trajectory. The number42 is a documented convention, not a
mathematical requirement. Existing Gurobi/SCIP/HiGHS studies used it, so request
and record42 consistently in the new campaign, with solver-specific semantics.

- Gurobi: Seed=42; its default is already a fixed seed0. Pyomo alone does not
  require a different seed. Same model, order, version, hardware and parameters
  matter; wall-clock stopping and nondeterministic concurrent choices can still
  affect reproducibility.
- SCIP: randomization/randomseedshift=42, recording permutation/lp seeds and
  other effective defaults too. A global shift is not a promise of the same
  initial point as another solver.
- HiGHS reference: random_seed=42. Its native parameters/log remain unchanged.
- CBC: randomCbcSeed=42 and, where confirmed by the installed CLP interface,
  randomSeed=42. CBC/CLP have distinct randomness controls. Zero can select
  clock-based initialization in CBC, so never equate zero across solvers.
  Verify the installed executable's option semantics and thread support.

The adapter must expose requested and effective parameters, not only the shared
SolverConfig. Setting Python/NumPy seeds does not replace native solver seeds.
Sort variable/constraint/route construction and record matrix identities;
PYTHONHASHSEED is not a substitute for deterministic construction. Cold starts
will provide no initial incumbent, basis or history. No exact-vector or
bitwise-repeatability guarantee is made for an eight-hour wall-clock solve.
One seed/run per solver supports a case comparison, not a robustness study over
seeds or a general solver ranking.

Primary sources:
- https://pyomo.readthedocs.io/en/stable/_modules/pyomo/contrib/appsi/solvers/gurobi.html
- https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html
- https://support.gurobi.com/hc/en-us/articles/360031636051-Is-Gurobi-deterministic
- https://scipopt.org/doc/html/PARAMETERS.php
- https://ergo-code.github.io/HiGHS/dev/options/definitions/
- https://github.com/coin-or/Cbc/blob/master/src/CbcParameters.cpp

Current upstream documentation is conceptual support, not evidence of installed
NPAD versions/defaults. Obtain the actual runtime inventory manually.

## Qualification and prospective operational design

1. Implement/qualify the new adapters in their own PR after PR139 completion.
   Analytical DET/STO tests, original residual and cost parity, all slack units,
   scenario probabilities/investment once, infeasible/unbounded/time-limit/
   no-incumbent states, parameter validation and cleanup are required.
2. Bind each build to the same workbook, membership, frozen route contract,
   scenario probabilities and bounded-slack proof. Compute a streaming
   canonical ordered linear-matrix identity including domains, bounds, objective
   constant and row bounds; test lossless transfer, avoiding a giant duplicate
   Python representation or undocumented coefficient rounding.
3. Qualify construction, serialization/native transfer, memory and solver
   disposal at public small/medium sizes. Missing native executable/license/
   package support must stop preparation with an actionable inventory request,
   not trigger automatic installation or fallback.
4. Plan one cold h215 STO/W arm for each of Gurobi, SCIP and CBC. Proposed common
   native allowance8h, gap target1%, solver-thread ceiling4, same original
   residual tolerances, seed42 and192GiB reservation. These are prospective:
   confirm CBC serialization/memory/build and native timeout handling before
   releasing an operational package. Slurm12h per independent arm is the initial
   envelope, not extra native solve time. Do not put three8h solves in one
   twelve-hour allocation.
5. Record first incumbent and common-gap threshold times when supported,
   primal/dual traces, final native/common gap, native status, LP/node counters
   and phase timings. Distinguish external worker RSS, Slurm MaxRSS and native
   memory. Record algorithm choice, thread effectiveness and node-sharing data.
   Do not force premature live native-API polling from an observer thread.
6. Create new predecessor-bound claims, sources and plan hashes for all three.
   Preserve success, no-incumbent, errors and censored attempts equally.
   No reuse of consumed claims or automatic retry/follow-on. Qualify startup,
   phase ledger, late return, cancellation, collection and offline audit before
   the researcher-approved merge.
7. Only after qualification/merge provide pinned commands for the researcher's
   manual NPAD CLI. All remote files remain below model-agrologistic-prefixed
   directories; transfers are by MobaXterm. Prefer sequential observations or
   controlled distinct resources when attributing runtime differences. No SSH,
   scp, scheduler or solve is invoked by Codex.

No new HPC command is released by this plan.
