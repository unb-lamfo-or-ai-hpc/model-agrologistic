# Bounded solver-agnostic scalar implementation plan — 28 October 2026

## Implementation progress after authorized PR133 integration

PR133 merged at4608250d…; the native8h/Slurm12h package and its frozen
82cb58ff… human handoff are complete, awaiting manual NPAD execution/evidence.
PR134 implements the scalar Pyomo HiGHS/CBC version with public miniature
qualification and the explicitly proved bounded-slack representation.
See [the implementation/qualification boundary](pyomo_multisolver.md).
Its own merge remains a human gate. The older implementation-stub descriptions
below are the retained design-stage snapshot, not the current software state.
M1 is implemented; M2 still needs installed-runtime, small/medium build/resource
evidence and a complete separate large-instance operational package.
CBC is implemented/tested on public controls, without a population experiment.
No moving develop pin, automatic solver fallback, additional SCIP attempt,
h215 HiGHS/CBC job or new scientific observation is admitted by this update.


The researcher requests planning a longer SCIP test and other free solvers,
including HiGHS and a multisolver implementation. This document is design and
qualification scope, not implemented Pyomo/HiGHS/CBC capability or admission of
a solver sweep. See [the sprint/PR plan](mvp2_completion_plan_20261028.md).

## What the repository actually implements

| Layer | Current implementation |
| --- | --- |
| Canonical data | ModelData, input validation, shared scenario/route/math preparation |
| Public dispatch/results | optimization.solve_model; SolverConfig; OptimizationResult |
| Gurobi | Native gurobipy scalar DET/STO extensive forms |
| SCIP | Native PySCIPOpt; not Pyomo; solve_model_scip builds, optimizes and extracts the extensive form |
| Indicator implications | Native SCIP addConsIndicator for closed-facility operation; native Gurobi counterpart |
| Common independent validation | solution_validation reconstructs mathematical feasibility and costs from returned decisions |
| Pyomo | optimization_pyomo.solve_model_pyomo currently raises OptimizationBackendNotImplementedError for DET and STO |
| HiGHS / CBC through a complete scalar model | Not implemented or qualified; installed availability on NPAD unknown |

The SCIP module reuses algebraic investment/capacity/cost helpers imported from
Gurobi-named modules, but those helper calls do not instantiate a Gurobi model,
environment or license. Native variables, recourse rows, indicators, optimization,
extraction and disposal use PySCIPOpt. The computation used sequential
`optimize()`, not `solveConcurrent()`; four configured thread ceilings do not
establish concurrent branch-and-bound or four effective LP threads.
SoPlex is SCIP's LP engine here, not a standalone replacement MILP solver.

Read source at PR131's executed commit:
[SCIP implementation](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/cbd64d86914dd416ed16b6a58ffe1069401e3aad/src/logic/optimization_scip.py),
[common facade](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/cbd64d86914dd416ed16b6a58ffe1069401e3aad/src/logic/optimization.py),
[Pyomo stub](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/cbd64d86914dd416ed16b6a58ffe1069401e3aad/src/logic/optimization_pyomo.py).

## Proposed architecture

Keep the existing native Gurobi/SCIP paths as qualified references and preserve
their original experiments. Implement the currently missing solver-neutral
Pyomo DET/STO formulation as a separately selectable backend, with a common
compiler/capability policy rather than copying the mathematics for every solver.

Canonical frozen inputs -> shared mathematical preparation -> sparse indexed
formulation -> explicit solver-capability/constraint translation -> chosen
adapter -> normalized OptimizationResult -> independent residual/cost validator
-> bounded output/provenance/resource evidence.

First qualify HiGHS through its Python-backed Pyomo interface. CBC is the next
candidate through its separately pinned Pyomo interface. A direct sparse
`highspy` adapter is a possible measured alternative if Pyomo construction,
transfer or resident memory is too expensive at 14 million variables; it is not
assumed faster or silently mixed into the same benchmark. Preserve the common
data/result/validator contract whichever adapter is chosen.

Pyomo is a modeling layer, not a solver or proof that all solver capabilities
are interchangeable. Its APPSI documentation includes HiGHS and CBC; HiGHS also
documents direct highspy model construction and sparse model transfer:
[Pyomo APPSI](https://pyomo.readthedocs.io/en/stable/reference/topical/appsi/appsi.html),
[HiGHS Python interface](https://ergo-code.github.io/HiGHS/stable/interfaces/python/example-py/),
[CBC project](https://github.com/coin-or/Cbc).

## Mathematical and capability gate before scale

1. Map every scalar DET/STO equation, first-stage investment counted once,
   original DET arrays, scenario probabilities, network/units and three separate
   penalties. Preserve fixed coefficients and tolerances; do not pool the old
   hierarchy objective into this implementation.
2. Inventory each pinned interface: native indicator support, finite/infinite
   bounds, mutable-model transfer, limits, native/common gap, bound/status
   semantics, callback safety, lifecycle and negative-result extraction.
3. For an unsupported indicator, prove an equivalent linear representation
   before enabling that backend. No arbitrary Big-M, dropped implication or
   bounds taken from observed incumbents. Emergency slacks relax physical
   capacities and transshipment can create circulations: nominal capacity or
   total supply is not automatically a valid upper bound on every flow.
4. State exactly whether a transformation preserves the entire feasible region
   or only optimal values under additional proved assumptions. The latter is
   not silently accepted as the original model contract. If finite valid bounds
   cannot be established for the required representation, keep the backend
   blocked and report that formulation limitation.
5. If using GDP transformations, record transformation version, all bound
   derivations and generated coefficients. Pyomo's own documentation explains
   Big-M/hull reformulations and their bound requirements; installing Pyomo does
   not discharge that proof:
   [Pyomo GDP reformulations](https://pyomo.readthedocs.io/en/stable/explanation/modeling/gdp/solving.html).
6. Test the same compiled MILP with at least two qualified solvers on public
   miniatures, as well as against native references. Feasible sets/objective,
   residuals and valid bounds matter; alternate optima need not have identical
   decision vectors. Separately label changes in formulation/interface so a
   timing difference is not attributed entirely to solver software.

## Complete qualification and execution gates

Public controls: hand-calculated DET and one-scenario STO equality; unequal
probabilities; scenario splitting/investment once; each slack's units/penalty;
closed/open facilities and indicator boundary cases; infeasible/unbounded and
no-incumbent cases; finite bounds and numerical scaling; export/reload,
independent residual rejection, timeout/cancellation, disposal and partial
forensic collection. Add medium public sparse construction/memory controls and
a clear threshold for the h215 build before requesting a large observation.

Keep mathematical equivalence controls separate from performance experiments.
Measure build, native optimization, extraction, export, validation and end-to-end
time separately; native gap definitions differ. Normalize a common
incumbent-denominator gap only with finite valid incumbent/bound; retain missing
values as null. Keep allocation, sampled process memory, native memory and Slurm
MaxRSS scopes distinct. Preserve positive and negative observations equally.

Cloud CI may use declared dependencies; no new local environment or package
installation is authorized. Inspect existing NPAD runtime metadata manually
before any required human installation decision. A complete HiGHS h215
operational PR must specify one arm, source/input/representation hashes, budget,
fresh claim, exact-step/phase ownership, independent external observation where
qualified, immutable collection and audit. It needs its own qualified merge and
pinned human CLI. No automatic solver fallback, repeated search until failure,
new population, resource escalation or promise of an open-source limitation.

The next longer SCIP run preserves its existing native formulation to isolate
the planned time-window extension as far as the one-observation design permits.
It does not wait for a Pyomo rewrite. Multisolver implementation can progress
alongside the human run and coauthor review, but new measured results enter the
manuscript only after independent original-evidence review.
