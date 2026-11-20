# Single h215 DET/W compatibility test: Gurobi 14

Status on 20 November 2026: execution prepared, not submitted. PR160 remains Draft.
The environment clone is reported verified; license acceptance and the real
optimization are not yet tested. The researcher requires CLI authorization.

## Purpose and fixed scope

Use the qualified historical h215 DET/W workbook as compatibility input only.
Do not change data, coefficients, network, mathematical formulation or validation.
The existing native gurobipy builder is reused. DET is embedded as one deterministic
trajectory in the shared native constructor and projected back to DET; this does
not execute the nine-scenario STO experiment.

The only explicit optimization-parameter assignment is TimeLimit=300 seconds.
Method, Threads, MIPGap, Seed, ConcurrentMIP, heuristics and numerical tolerances
remain Gurobi14 defaults. No SoftMemLimit is set. Every exposed nonconnection
parameter is compared with its native default before optimization and after return.
Any additional nondefault parameter stops the test. The queried default MIPGap
is copied into the result configuration for accurate description, not assigned
as a native option. There is no tuning or performance comparison with Gurobi13.

## Reuse and ownership

scripts/gurobi14_h215_compat.py scopes three existing native seams: model environment,
parameter application and observational phase hooks. It does not replace any
objective, variable, constraint, route selection, result extraction or validator.
The existing model lifecycle disposes the sole native model; its explicitly owned
Gurobi environment is then disposed to release the license session. Scoped seams
are restored on failure as well as success.

Only one native model and one optimize attempt are admitted. There is one WLS
environment, with no separate license-capacity optimization or session-concurrency
test. The designated license identity is checked in memory. Credentials and
unrestricted native exception text are not exported. Native stdout/stderr are
discarded at the file-descriptor level without changing OutputFlag or LogFile.
The structured receipt retains safe error kind/code, phase and available statistics.

The code is loaded from the pinned public source snapshot, not the installed
editable checkout. Package installation and historical project metadata are not
modified. The new interpreter is the researcher-selected venv313_g14 clone.

## Operator stages after authorization

1. Fetch the reviewed launcher and pinned source archive below the dedicated audit
   project, with exact SHA-256 checks; no Git is required on NPAD.
2. Preparation checks the original clone ledger, preserves it, copies the three
   byte-identical historical input files into a fresh compatibility claim, and
   writes a source inventory, immutable plan and batch file. It does not load a
   model or open the license on the login node.
3. Record submission intent before the single sbatch call. Submit held, retain the
   response and job ID, then release that job once. An uncertain submission/release
   preserves the claim for investigation; do not repeat the launcher.
4. The worker verifies ownership, source/input/environment receipts, selected
   interpreter and allocation. It reuses the original loader, population audit,
   DET preparation, selected network and penalty-vector checks before construction.
5. Start the designated WLS, construct the real native model and perform the single
   300-second optimization. Validate a usable incumbent with the original independent
   validator. No other optimization, IIS or automatic follow-on occurs.
6. After terminal accounting, collect original receipts with the printed collect
   command. Collection queries sacct and copies existing evidence; it neither starts
   nor repeats optimization. Preserve a terminal failure or incomplete receipt.

The launcher's three arguments are the reviewed source commit, archive SHA-256
and the operator-designated numeric license identity. Never pass WLS secrets as
arguments. The final operator handoff fixes these values after exact-head review.
Do not execute an unpinned example or an old campaign/public-qualification launcher.

## Resources and clocks

Request one exclusive CPU node in intel-256, 32 CPUs per task with the physical-core
hint and a 192GiB Slurm memory request. GPU is not requested or enabled. Solver
Threads remains automatic; allocation and actual affinity are recorded separately.
This test cannot establish thread scalability or license thread capacity.

The Slurm wall limit is one hour: a preparation/build allowance up to 30 minutes,
five native minutes, up to 15 minutes for extraction/validation and remaining setup
reserve. This is a conservative envelope based on retained h215 preparation
budgets, not a claim that construction was measured again. Native TimeLimit remains
300 seconds and does not include Python construction. Native return can modestly
exceed that limit because of solver stopping work; report actual Runtime.

Automatic Slurm requeue is disabled. Hard memory or wall interruption may leave
partial evidence and is preserved without an automatic retry. It is not converted
into a successful compatibility certificate or mathematical infeasibility.

## Evidence and interpretation

The receipt contains environment/interpreter/source/instance/command identities,
designated-WLS acceptance or rejection, native status, incumbent/bound/gap where
available, Runtime, Work, nodes, Gurobi memory attributes in decimalGB and peak Linux
worker RSS in bytes. Worker RSS includes construction/extraction/validation and
is distinct from Gurobi's memory accounting. Slurm accounting retains its own scope.
Missing or infinite/sentinel values remain null.

A time-limit return without an incumbent supports GO for this minimal compatibility
criterion if construction and optimization returned correctly with the designated
license and default-parameter audit. An incumbent additionally requires independent
validation. An unexpected infeasibility of the qualified real instance, rejected
validation, license/API error or unauthorized parameter override requires diagnosis
and is not a GO. Missing/interrupted evidence can remain inconclusive. No optimality
or one-percent gap is required, and this does not qualify the complete MVP3.0 model,
future Benders implementation, larger instances or a performance claim.

Keep full local receipts in custody. They may include installation paths, instance
validation details and the designated license identity. GitHub receives a redacted
summary and hashes after review, not private inputs, solution vectors, credentials
or unrestricted logs. The clone itself is never recreated by this launcher.

## Verification before the CLI handoff

Controls use only the standard library and explicit model/API doubles; they do not
import real Gurobi, access WLS or solve synthetic agricultural instances. They check
the single TimeLimit assignment, default rejection, secret exclusion, one-model
ownership, cleanup/restoration, compute-only guard, censored-case interpretation,
source archive integrity and the generated single-job envelope.

The Linux workflow additionally checks operator/generated shell syntax, compares
retained native/mathematical/validation files with the base commit and records the
SHA-256 of the exact public source tarball for the operator handoff. These checks
qualify execution controls, not the as-yet-unexecuted native compatibility test.
