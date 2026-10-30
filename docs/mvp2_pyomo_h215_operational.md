# Common-form Pyomo h215 W operational protocol

## Current qualification and eligible experiment scope — 30 October 2026

Public qualification job2227480/source57204e0b/planceeb6d10 is accepted:
282tests,0failures/errors/skips, sources verified after; Slurm COMPLETED0:0.
The actual NPAD CBC2.10.13 static binary rejects threads. Its h215 arm is
CANCELLED under the researcher's policy; Gurobi and SCIP remain proposed.
The generic CBC implementation/tests below remain historical/public controls,
not permission to run its cancelled large arm. No replacement/fallback/retry.
See [accepted qualification](pyomo_qualification_2227480.md) and
[redacted original evidence](evidence/pyomo_qualification_2227480.json).
The operational PR still needs its own merge authorization; no private h215
job is submitted by this qualification. All execution code remains unchanged.


PR140 was explicitly authorized and merged into develop at
`40f33d7cc13d516cd6b130f00398590840131904`. Its accepted public qualification
is job2227458/sourcef166f60c/plan dc41c8b7: 168 tests, no failures, errors or
skips, with source and predecessor checked after execution. Original rejected
job2227457 and every historical experiment remain unchanged.

This separate package prepares one new STO/W observation for Gurobi and SCIP,
and conditionally CBC. The researcher authorizes cancelling the CBC h215 arm
if the installed official binary does not accept the threads option. Such a
cancellation is a binary-capability decision, never a numerical solver failure.
There is no HiGHS restart, warm start, solver sweep or automatic fallback.

## Scientific identity

The scientific code is byte-identical to the qualified adapter implementation.
The operational scripts do not modify the model, data, validator or solver
adapters. Preparation and compute verification bind the same original W:

- Workbook SHA-256 `40edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e`;
  population SHA-256 `4134147f45188d2e8722476dd325b40e584c3746affe99889e045a547d283505`;
  order SHA-256 `7a524b2ed69b41481264d8049842b37e27cd3b96cc20d4e96d98eaf2a39e7903`.
- 215 warehouses: 146 existing and 69 candidates; two products, 60 periods,
  nine equiprobable scenarios. These are the same selected warehouses and
  frozen OSRM distances as the historical Gurobi STO/W cell.
- The complete warehouse-selection receipt, mathematical contract (including
  selected-network hash) and scenario probabilities must match the original W.
  Selected route/product records: OD3182, DC3440, DD18490, OC0. Products are
  already represented in those records; do not multiply them again.
- Effective unmet/static/reception penalties remain 90000/45000/45000, with
  the original units and independent residual tolerances: absolute1e-5,
  relative1e-8. No legacy workbook value is substituted.
- All new arms use the same bounded-slack Pyomo extensive form. The proof
  preserves physical investment projection and optimal scalar value under
  nonnegative candidate-slack penalties; it does not preserve the entire
  redundant auxiliary-slack region of the native indicator formulation.

A normally returned result must retain its ordered common-matrix SHA-256,
14,054,654 variables, 307 binaries and 735,577 linear constraints. Compare the
hash across returned arms before treating them as a common-form comparison.
This hash describes Pyomo algebra before native transformations, not a native
or presolved matrix. If a worker is killed before returning results, a matrix
certificate may be absent; input/source identity does not manufacture one.

## Independent claims and budgets

| Arm | New exclusive claim | Native interface |
|---|---|---|
| Gurobi | `.mvp2-pyomo-gurobi-h215-w-native8h-v1` | APPSI/gurobipy |
| SCIP | `.mvp2-pyomo-scip-h215-w-native8h-v1` | Common Pyomo linear representation through PySCIPOpt |
| CBC, conditional | `.mvp2-pyomo-cbc-h215-w-native8h-v1` | Pyomo CBC executable interface |

Each arm has its own immutable plan, job receipt and evidence archive. A
consumed claim cannot be restarted, even after a failed submission or run.
Every NPAD command is executed manually by the researcher, below the existing
model-agrologistic audit directory. No agent SSH/scp, package installation or
environment change is involved.

Each reservation is 12h Slurm, 192GiB, 24 logical CPUs, one worker step with
16 logical CPUs, and a four-thread solver ceiling. Native allowance is 28800s,
gap target1%, seed42. The ledger reserves 3600s for input/build/transfer and
startup, 28800s optimization, 900s late return/export and 1800s validation;
whole worker35100s, setup/cleanup1800s, planned36900s and unallocated6300s.
Headroom never grants extra optimization. The reservation product288 logical
CPU-hours per arm is not measured utilization or a parallel-efficiency claim.

Native defaults retain algorithm selection. Gurobi still chooses presolve,
LP methods, cuts and heuristics; requested safety/seed/thread/gap/time settings
are checked using native introspection. SCIP's corresponding parameters and
seed shift are also read back. CBC requests are separately checked against
retained command-line acknowledgements; they are not labelled in-process
introspection. The seed is not a common initial incumbent or shared trajectory.

The cold `-B -I -S` bootstrap publishes minimal process/step identity before
site initialization or application imports. The supervisor releases only the
owned step. Twelve timed startup stages, existing phase deadlines, exact-step
termination, terminal accounting, resource sampling and independent validation
remain mandatory. Public controls run only on compute before private build.

## Qualification and release sequence

1. The new public qualification uses
   `scripts/qualify_pyomo_h215_operational.py`, exclusive claim
   `.mvp2-pyomo-h215-operational-qualification-v1`, and 282 tests. It checks
   original v1/v2 receipts, exact source bytes, installed versions and the
   pinned official static CBC archive/binary before and after tests. It never
   reads the private h215 inputs and does not submit a scheduler job itself.
2. On compute, probe `cbc -threads 4 -quit` without a model. Unsupported
   threads records `cbc_arm_cancelled=true`; Gurobi/SCIP qualification can
   still pass. CBC preparation subsequently refuses to create an h215 job.
   Unknown probe errors remain failures, not assumed capability decisions.
3. Required result: 282 tests, zero failures/errors/skips, source verified
   after, explicit CBC decision and `private_h215_execution_admitted=false`.
   A rejected qualification is preserved; there is no automatic retry.
4. Save the actual human NPAD result, review the qualified head, mark the
   operational PR Ready and request its own merge authorization. Do not infer
   that PR140's merge authorizes this separate PR.
5. After authorized merge, provide the pinned launcher commands. The wrapper
   verifies the source is in develop, raw Git bytes, nonnative login controls,
   and the accepted operational/scientific receipts. Each human `start` admits
   only the selected new arm. Prefer sequential observations for timing
   interpretation; any concurrent/shared-node conditions remain disclosed.

## Evidence and interpretation

Collection is terminal-only, immutable and idempotent. Preserve completed,
no-incumbent, rejected-incumbent and censored observations equally. Normal
closure checks product hashes, original residual certificate, native settings,
common matrix, startup/phase/owned-step receipts and accounting. Recompute the
common objective/bound gap; report native gap separately when available.

Generated native scratch files (including potentially large CBC LP files) stay
preserved at NPAD. The archive contains their sizes and streaming SHA-256s in
`native_temporary_inventory.json`, not those temporary bytes. This scope is
explicit; it is not a complete transport of interrupted native scratch. Other
evidence is capped at1GiB without truncating products. Original HPC archives
and private inputs are never committed to GitHub.

Compare objective, dual bound, attained common gap, original residuals, native
status, counters, native runtime, transfer/build/validation/export time and
observed memory. A solver can stop before8h when the target is met; different
attained gaps are not equal-quality timing observations. Single runs support
this instance comparison, not a general solver ranking or an impossibility
claim. Sparse logs do not establish a stalled root relaxation. A controller
termination is censoring, not a clean native time-limit result. Previously
accepted HiGHS and native Gurobi results remain historical references with
their own formulations and measurement scopes.
