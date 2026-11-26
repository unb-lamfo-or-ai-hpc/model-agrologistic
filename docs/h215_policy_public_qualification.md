# Public h215-policy qualification package — not executed

The [controller](../scripts/effective_h215_public.py) prepares source-pinned
public tests and a batch file. It has `prepare` and compute-only `execute`
commands; no submission, release, retry or private input/solve command exists.
Neither command has been run on NPAD in this preparation.

## Inventory and acceptance

1. Run the explicit data/algebra suite in a child process with native imports,
   optimizer entry points and subprocess execution blocked during its tests.
   Bind the complete test inventory to the prepared source/plan. Require zero
   skips, failures, errors and forbidden execution attempts.
2. Reuse the original default-environment 2001-row/variable public license
   capacity probe. Check metadata/capability without exporting license content
   or native startup/exception messages. A public license receipt is not a
   private h215 execution authorization.
3. Run 48 tiny analytical controls: DET/STO × thread ceilings1/4 × 12 controls.
   Each set contains the nine policy configurations, beta1/alpha0 endpoint,
   scalable-candidate investment and a deliberately infeasible hard-shipping
   control. Each native solve has a 30s limit and gap0. Exact optimal positive
   returns and independently accepted original-unit/policy certificates are
   required; the negative control must return proven infeasible with no incumbent.

These are synthetic public software examples, not additional agricultural
observations or performance benchmarks. They reuse the existing test fixture
and original mathematical builder. The positive example has 10 offered and
demanded tonnes. If X tonnes are exported, its objective is
`20090 - 992 X`, with
`X=min(10, 10(1-beta), 10 alpha)` for enabled controls. Domestic shipping costs
2000/t; export shipping plus shortage costs1008/t; stock plus stock excess and
shortage costs3002/t. Origin receipt costs90 in total. Thus maximizing admissible
X gives the analytical minimum. Examples:

| Control | Export tonnes | Objective |
|---|---:|---:|
| Neutral | 10 | 10170 |
| beta0.90 | 1 | 19098 |
| beta0.95 | 0.5 | 19594 |
| alpha0.60 | 6 | 14138 |
| alpha0.50 | 5 | 15130 |
| beta1/alpha0 | 0 | 20090 |

In combinations beta dominates the chosen export ceilings in this example;
isolated alpha controls test its active effect. The candidate variant requires
capacity10/6 with unit proportional cost, added once to objective10170 even
with STO weights0.25/0.75. The negative example has zero hard shipping while
beta0.9 requires nine domestic tonnes. This algebraic contradiction is distinct
from failure to obtain an incumbent in an agricultural instance.

The [shared execution adapter](../src/logic/effective_gurobi_execution.py)
constructs through `build_effective_model`, transfers via APPSI, records actual
native parameters/matrix/bound/counters, exports through retained extraction
with dense critical zeros, independently validates, disposes native resources
and clears the model. No new formulation is introduced. Future private workers
must use this qualified path and add their own admission, monitoring and receipts.

## Preparation and compute boundaries

- Source archive SHA-256 and full source commit are required. Use the public
  GitHub source archive; compute execution has no Git dependency.
- All new files, source extraction, claim, tmp and cache directories are under
  `/home/vrrcelestino/model-agrologistic-hygiene-audit/`. Nothing is written
  directly to `/home/vrrcelestino/`. The existing interpreter and designated
  license are referenced read-only; license bytes are not inspected or hashed.
- An immutable new claim `.mvp2-h215-effective-policy-public-v1` contains the
  full source inventory, package code fingerprints and Python identity,
  `plan.json` and generated `qualification.sh`. Existing claims are refused.
- The batch requests intel-256, exclusive single node,192GiB,16 physical cores,
  one logical CPU per core,1h wall time. Execution verifies numeric Slurm job
  and step, allocation, actual physical affinity, inherited cgroup192GiB limit
  and clear OOM counters before importing a native engine. Repeat checks and
  source verification after all controls.
- A one-shot `started.json` prevents repeating a consumed execution. Every
  control has its own JSON; the final result reports qualification or rejection.
  No automatic retry or private follow-on is admitted. Keep failed/partial claims.
- Sanitized errors record the exception type. Native output is captured, not
  copied into public logs. Never print a license or unfiltered native exception.

## Operator sequence for later authorization

This is the order for preparing a future operator handoff, not a launch recipe:

1. Pin the reviewed source commit and SHA-256 of its public tarball; download
   it below the audit project and independently verify the digest.
2. Invoke `effective_h215_public.py prepare --claim PATH --archive PATH
   --source-sha COMMIT --archive-sha256 DIGEST` using the existing interpreter.
   Expect `prepared_no_job`; preserve the returned plan hash. Preparation
   reads package metadata/files, extracts only pinned public sources and writes
   the batch file, without loading a solver or historical/private inputs.
3. Review the plan and batch. Actual scheduler submission remains outside this
   task and requires a later researcher instruction. No job is submitted now.
4. After an authorized public run, collect the original result, tests XML,
   capability/allocation/control receipts, source/plan identities and Slurm
   accounting, with file hashes. Scheduler success alone is insufficient.
5. Only then prepare/review the private operational package and finite queue.

## Readiness

- [x] PR158 merged with explicit authorization; baseline receipts preserved.
- [x] Finite18-case scientific protocol and48-control public inventory prepared.
- [x] Solver-free witnesses cover construction, objective and exact export path.
- [x] CI routes these additions to guarded data tests; old solver jobs retained.
- [ ] Native public execution/48 numerical controls and default license probe.
- [ ] Original public scheduler/runtime/receipt collection and acceptance.
- [ ] Private bundle admission, worker/queue qualification and execution approval.

PR156 stays Draft. No manuscript, dataset, Zenodo publication or new HPC job is
part of this preparation. The new preparation PR also stays Draft.
