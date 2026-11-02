# Scalar Pyomo multisolver implementation and qualification

The researcher explicitly requests a separate implementation PR, parallel to the
longer native SCIP operational PR. The native Gurobi/SCIP implementations,
historical scenarios/input/penalties/claims/certificates and their output
semantics remain unchanged. This PR implements solver-neutral scalar DET/STO
construction and HiGHS/CBC adapters. The later Gurobi/SCIP extension is described in [native adapters](pyomo_native_adapters.md); it submits no HPC job and provides no new h215
performance result. Public miniature correctness is not large-input admission.

## Actual interfaces and explicit scope

Use the existing optimization.solve_model facade with backend=pyomo and
solver_name=highs (alias appsi_highs), cbc, gurobi or scip. The shared ModelData,
ModelConfig, mathematical preparation, sparse route selection,
OptimizationResult and independent solution validator are reused. The
implementation uses Pyomo6.10.1, highspy1.15.1 and the installed CBC executable
whose version is recorded. Native solver APIs retain their original paths.
Gurobi uses APPSI; SCIP translates the same Pyomo linear algebra through PySCIPOpt. An unsupported Pyomo solver raises not-implemented rather than silently switching
backends. SoPlex alone is not a MILP adapter.

A solver-neutral extensive form preserves first-stage investment once, original
DET arrays projected as one scenario, original STO probabilities, capacity
coupling/units and all three penalties. Shared imported Gurobi-named helpers
perform algebra only; the Pyomo paths instantiate no Gurobi environment/license.
Do not infer availability from package metadata or qualified large-scale
execution from these miniature controls.

Candidate emergency-slack indicators require the explicit option
indicator_reformulation=bounded_scalar_slacks_v1. This is a disclosed
representative formulation with a proof below. It is not advertised as preserving
every redundant unbounded slack assignment of the native model.

## Proof and limits of the bounded slack representation

Let I0 be total nonnegative initial stock, S(s,t) total nonnegative exogenous
supply at period t, and Hmax(w,t) a finite upper bound on each warehouse's hard
shipping capacity. Hmax is evaluated from the original capacity expression
using the finite candidate/expansion/bulk maxima; ignoring mutual exclusion
only makes that upper bound larger. Require nonnegative base capacities,
investment bounds, relevant capacity factors and candidate slack coefficients.
NaN/infinity/negative values reject the proof before model allocation.

Summing all warehouse material balances cancels DD transshipment, including
circulation. All inventory and external withdrawals are nonnegative. Thus total
inventory at t is at most I0 plus cumulative exogenous supply through t. Any
individual warehouse's aggregate stock is at most that total. Since effective
static capacity is nonnegative, the minimum required static slack is at most
that same cumulative bound.

Per-period OD arrivals are at most S(s,t). Every DD arrival is an outbound flow
from some warehouse, and the original shipping constraints are HARD. Consequently
all incoming DD flow to one warehouse, even with circulation, is bounded by the
sum of Hmax over all warehouses. Its minimum required reception slack is at most
S(s,t) plus that shipping sum. Supply alone is not a valid throughput bound:
circulation can exceed newly produced grain. Emergency reception relaxes
reception capacity, not shipping capacity.

Use these derived bounds Mstatic(s,t), Mreception(s,t), with candidate rows
0 <= e(kind,s,w,t) <= M(kind,s,t)*open(w). For a closed candidate, this enforces
the same zero slack as its native indicator. For an open candidate, take any
native feasible physical/investment decisions and replace each candidate slack
by its minimum required nonnegative excess. The bounds proved above contain
that representative. Conversely, every bounded-form feasible solution satisfies
the native indicator and all unchanged physical rows.

Therefore the projection onto physical/investment decisions is identical.
With nonnegative scenario probabilities and candidate slack coefficients,
trimming redundant slack cannot increase cost. Since the bounded formulation
is a subset of the native feasible set and every native point has a no-more-
expensive bounded representative, their optimal scalar values are equal.
Zero coefficients/probabilities are allowed; negative candidate slack
coefficients are rejected because the original unbounded-slack objective could
be unbounded below. This is NOT equality of the full redundant-slack feasible
region or a claim of identical relaxations/search behavior.

No bound uses a historical incumbent, penalty magnitude, arbitrary global
constant or a solver-dependent guess. The result records the policy, bound
digest, bound count, maximum and this equivalence scope. Returned decisions
are still checked by the independent ORIGINAL residual/cost validator.
Formulation/translation and native solver effects must be distinguished in
future performance comparisons.

## Run a public/small instance

```python
from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.optimization import solve_model

result = solve_model(
    data, ModelConfig(mode="sto"),
    SolverConfig(
        backend="pyomo", solver_name="highs", time_limit=30, threads=1, seed=42,
        mip_gap=0.01,
        solver_options={"indicator_reformulation": "bounded_scalar_slacks_v1"},
    ),
)
```

This example is not an NPAD execution handoff. Use the separate CBC choice to
solve the SAME constructed formulation. Time, gap, thread and seed options are
mapped per adapter; unqualified options/IIS/resource-telemetry requests reject
rather than reinterpret native Gurobi settings. No automatic fallback or warm
start. Native and common gaps remain distinct; missing values remain null.

HiGHS uses APPSI's persistent Python interface. Set-instance time is included in
construction and separately recorded; native runtime is kept separate from
adapter wall time. CBC uses Pyomo's LP-file shell interface; its solve wall time
includes serialization/process overhead and the retained API does not expose
a native gap, so that field stays null. Bounds and usable incumbents are checked
before loading/exporting a solution. No-incumbent/infeasible/error states export
no invented costs or decisions.

Model/adapter cleanup runs after extraction, no-incumbent and exception paths.
Native HiGHS handles and Pyomo model components are cleared; returned results
retain values, not solver/model/solution-loader handles. Disposal does not prove
that allocators return memory to the operating system.

## Scale, dependencies and next gate

The default guard rejects more than 200000 variables BEFORE model allocation.
It can be explicitly selected by pyomo_max_variables, but changing that option
does not certify a safe h215 build or admit an HPC experiment. First measure
construction, transfer, native, extraction/export/validation and memory at public
small/medium scale. Additional resource/export/lifecycle/terminal controls and
the installed NPAD inventory precede a separate complete HiGHS h215 operational
PR and pinned human CLI. The longer native SCIP test is independent.

The optional multisolver dependency extra pins Pyomo/highspy; CBC is an external
executable. Cloud CI installs them only on disposable runners and tests real
HiGHS and CBC with no skips in the required profile, alongside native references.
No local package installation, clone or environment is created. Missing existing
NPAD packages require human intervention; no install or HPC query occurs here.

Primary interface documentation:
- [Pyomo APPSI](https://pyomo.readthedocs.io/en/stable/reference/topical/appsi/appsi.html)
- [HiGHS interface source](https://pyomo.readthedocs.io/en/stable/_modules/pyomo/contrib/appsi/solvers/highs.html)
- [CBC interface source](https://pyomo.readthedocs.io/en/stable/_modules/pyomo/solvers/plugins/solvers/CBCplugin.html)

Public qualification covers hand-calculated DET/STO equality, separate slack
units/costs, unequal probabilities, scenario splitting and investment once,
native-reference parity, actual infeasible/unbounded and no-incumbent/status
normalization, derived
cumulative/circulation bounds, explicit-policy/option rejection, early variable
guard and disposal. The coauthor working draft records this as software qualification only, keeping
all original scalar population observations unchanged. Full native regression
still requires zero skips. A
different optimum vector is allowed when objective/residual parity holds.
No causal speedup, general open-source inability or private-input performance
result is implied.
