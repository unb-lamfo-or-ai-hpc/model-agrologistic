# Common Pyomo formulation with Gurobi and SCIP

Target update29October: public v2/job2227458 passed all168tests with zero
failures/errors/skips and verified source integrity after testing. It verifies
the untouched v1 predecessor. Public four-adapter qualification is complete;
private h215 resource/admission qualification remains separate. Original
job2227457 stays rejected:166passed/one login-context test failure, repaired
only in the test fixture with an additional compute-refusal control.
See [accepted v2](evidence/pyomo_qualification_2227458.json) and
[original diagnosis](pyomo_qualification_2227457_diagnosis.md).

PR139 consolidated the journal-reader revision and original solver evidence and
was merged into develop at8740dc5771ae87b95e49c649abad0a8deb4631da with explicit
researcher authorization. This separate implementation adds Gurobi and SCIP
adapters to the same bounded scalar Pyomo formulation used by HiGHS and CBC.
It does not replace native reference implementations or any executed source.

## Interfaces and common mathematical representation

Use backend=pyomo with solver_name=gurobi, scip, highs or cbc. Gurobi uses Pyomo's
APPSI Gurobi interface and gurobipy. SCIP uses a local adapter that translates
Pyomo's standard linear expressions into PySCIPOpt variables and rows; it does
not call our native SCIP scientific model builder or require a SCIP/AMPL binary.
HiGHS retains APPSI; CBC retains Pyomo's explicit executable interface.

All choices construct the same extensive form using build_model. The explicit
indicator_reformulation=bounded_scalar_slacks_v1 policy remains mandatory,
and its existing proof and limits remain unchanged. Objective constants,
negative variable bounds, variable domains, equality and ranged rows are
preserved in the SCIP transfer. Nonlinear expressions are rejected. Native
SCIP may represent a ranged row as two constraints, so native row counts need
not equal the common Pyomo count.

The ordered-pyomo-linear-matrix-v1 identity hashes variables/domains/bounds,
fixed values, objective constant and coefficients, and every active row with
its constant and bounds. Finite binary64 values are encoded with float.hex;
there is no decimal-rounding export. Row coefficients are processed one row
at a time rather than retaining a second complete matrix. The variable-index
mapping still consumes memory and belongs in future h215 resource qualification.
The identity concerns the common ordered algebra, not presolved matrices or
a proof that every native solver internally uses an identical representation.
Returned solutions continue through the ORIGINAL independent validator.

## Strategy, seed and result semantics

The adapters set time/gap limits, thread ceilings, seed and feasibility settings.
They do not force presolve, the root LP algorithm, cuts or heuristics. Gurobi's
effective Presolve, Method, NodeMethod, Heuristics, Cuts and ConcurrentMIP settings
are retained with the other parameters. SCIP records effective parameters,
including its global seed shift and LP/permutation seed defaults. CBC's retained
options are labeled requested, not falsely advertised as native introspection.
Algorithmic defaults and actual thread use remain solver-specific.

Seed42 remains a reproducibility convention for the prospective experiment,
not a common incumbent, basis, random sequence or guarantee of bitwise results
under a wall-clock cutoff. Gurobi Seed, SCIP randomseedshift, HiGHS random_seed
and CBC/CLP seed controls have distinct meanings. The process supplies no MIP
start. Both native and incumbent-normalized common gaps are retained where
available. A no-incumbent/error/infeasible/unbounded result exports no invented
objective, decisions, costs or service indicators.

Each adapter owns its native model and disposes it after extraction, negative
termination and exceptions. The code does not globally dispose unrelated Gurobi
environments. Disposal is not a guarantee that the OS recovers all allocator RSS.

## Local qualification and remaining target-platform gate

The existing Windows venv313 interpreter was used without installation or a
new environment. PySCIPOpt6.2.1 and highspy1.15.1 wheels were unpacked only into
the approved .codex temporary test directory and selected through a process-local
PYTHONPATH. Official CBC2.10.13 MSVC binaries were unpacked there and hash-checked.
The MinGW build did not start on this Windows because a DLL dependency was missing;
that failure is an execution/build observation, not a CBC numerical failure.

An inherited GRB_LICENSE_FILE pointed to an expired license. It was unset only
inside the child test process, allowing the legitimate size-limited license
included in gurobipy13.0.3 to run PUBLIC SMALL controls. No license file or
permanent setting was changed. This license does not admit h215 execution.

The focused real-solver suite passed66tests with zero skips; two additional
exception-cleanup tests also passed. Controls cover DET/STO hand calculations,
three separate slack costs/units, probabilities/investment once, exports and
independent certificates, immutable completion, infeasible/unbounded outcomes,
common matrix equality across all four engines, parameter recording, transfer
constants/ranged rows/negative bounds, and no-incumbent/time-limit behavior.

Linux-specific tests importing resource cannot run on Windows and remain target
qualification, not silently skipped acceptance. Historical startup tests also
need Windows extended-length temporary paths; their first failure under an
overlong ordinary path is retained separately. No Linux/NPAD large-input
qualification, performance result or additional experiment is claimed here.

## Next h215 W campaign

The researcher requests one NEW common-form h215 STO/W observation each for
Gurobi, SCIP and CBC, initially planning8native hours/12Slurm hours per arm,
four solver threads,192GiB, seed42 and the original1% gap/residual criteria.
Three8hour solves do not fit in one12hour allocation. Preserve the original
HiGHS result and every consumed claim; do not repeat an old start.

The latest human read-only NPAD inventory confirms Python3.13.15, Pyomo6.10.1,
gurobipy13.0.3, PySCIPOpt6.2.1 and highspy1.15.1. CBC is NOT on PATH. Package
metadata does not establish an available Gurobi license or compatible CBC binary.
The recorded compute platform is glibc2.28: do not assume a newer Ubuntu-built
binary is compatible. Obtain or build a private CBC executable below the approved
model-agrologistic directory, then qualify it on a compute node before release.

The operational package must qualify startup/phase/late-return controls, the
matrix identity receipt, resources, terminal positive/negative/censored results,
safe immutable collection and offline audit. Pinned source/plan/new claims and
an explicitly authorized merge precede the researcher's manual NPAD commands.
No scheduler call, installation or solver job on NPAD occurs from Codex.

See mvp2_pyomo_three_solver_execution_plan_20261029.md for the ordered protocol.
