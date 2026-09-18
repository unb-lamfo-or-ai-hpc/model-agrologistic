# SCIP qualification and bounded frontier comparison

## Revised sequence and scope

The development sequence is **A, C, D, initial E**, followed by a decision on
resuming B. Expansion beyond 400 hubs and Benders decomposition are deferred,
not cancelled. This ordering supports an initial reproducible package for
research collaborators without requiring a definitive scalability frontier.

| Sprint | Deliverable | Admission requirement |
|---|---|---|
| A | Gurobi all-barrier evidence for unresolved 300/400-hub instances | Existing frozen data and numerical contract |
| C | Native SCIP formulation, staged optimizer, independent validation and 215-hub pilot | Analytical, backend-parity and export tests |
| D | Paired comparison through 400 hubs | Qualified SCIP backend and resource-reviewed instances |
| E, first release | English scientific report, figures, manuscript and curated data inventory | Provenance and explicit qualification of all outcomes |
| B, deferred | Larger populations and additional solution strategies | Review of the initial comparative evidence |

The running Sprint A job must continue on the frozen source
`899857954f65d3bb48268ed58ece26313379bea4`. Development of SCIP takes place on
a separate branch and checkout. Do not update the active NPAD checkout or its
Python environment while any of these Gurobi jobs are queued or running.

## Immediate remaining Sprint A submissions

The all-barrier 400-hub direct-enabled job is **2105903**, with supplied status
RUNNING at 06:45:39. Jobs **2106399** (400-warehouse) and **2106401**
(300-warehouse) were also reported RUNNING. Their preceding test-only estimates
2106398 and 2106400 are not additional submitted jobs. Both new submissions
passed 87 licensed/focused tests and the input contract gate. No final
optimization outcome has been reported. These experiments are independent.
The scheduler controls concurrent resource allocation; each requests four CPUs
and 192 GiB, with the existing 12-hour scheduler limit and 28,800-second global
optimization budget. Do not submit another `h400-direct` job.

Use the existing `submit_sprint_a_barrier.sh` at the frozen commit, not a newer
checkout. Run each helper once, preserve its submission receipt, and inspect
existing receipts before retrying after an interrupted shell. No successful
result from the running job is assumed by submitting the remaining cases.

## Status of SCIP implementation

The native `pyscipopt` dispatch now builds the stochastic extensive form and
supports scalar penalties and sequential lexicographic objectives. Deterministic
SCIP dispatch, EVPI/VSS, IIS export and Gurobi-specific options remain explicitly
unsupported. Native implementation does not by itself qualify a 215-hub run.
The runtime probe remains read-only and cannot certify mathematical parity.

Local qualification uses Python 3.13.15, PySCIPOpt 6.2.1, SCIP 10.0.2 and a
native banner identifying SoPlex 8.0.2 on Windows. This does not establish the
LP build on NPAD. The local Gurobi license is expired; licensed parity must be
qualified separately on NPAD. Linux CI executes native SCIP analytical tests
and archives the native build banner without treating that scope as parity.

### Implemented equivalence ledger

| Family | SCIP realization | Qualification |
|---|---|---|
| Shared investments | One set of candidate/expansion/bulkification variables | Probability-weighted analytical optimum; nine-scenario fixture |
| Activation and exclusion | Shared algebraic constraints; native binary variables | Fixed/scalable candidates and bulkification tests |
| Supply, inventory, demand, exports | Native linear rows on the frozen graph | Independent residual reconstruction, carry-over and export tests |
| Direct and multi-hop routing | Selected OD/DC/DD/OC adjacency | Disabled/enabled direct-route regression |
| Stock and reception slacks | Separate nonnegative recourse variables | 28/30/31-day dimensional tests |
| Closed-candidate slacks | Native indicators: closed implies nonnegative slack <= 0 | Closed/open candidate tests; no artificial capacity Big-M |
| Objective costs | Shared algebraic coefficient helpers, native SCIP expressions | Analytical components and independent cost reconstruction |
| Priorities | Sequential solves with explicit inherited bounds | Global-budget/resource-stop tests and final-limit reconstruction |
| Artifacts | Common experiment runner and completion receipt | Actual SCIP solve, export, independent validation and hash verification |

No Gurobi model or environment is instantiated by the SCIP backend. Algebraic
helpers remain in historically named modules; the independent validator does
not reuse those helpers. This distinction avoids conflating shared mathematics
with solver-backed execution.

### Numerical and lifecycle contract

For a minimization pass with incumbent U and lower bound L, the next objective
inherits `max(U, L + abs(U)*target_gap, L + 1e-10) + priority_absolute_tolerance`.
This reproduces the existing MIP priority-budget convention, not exact zero-drift
lexicography. Bounds achieved by different solvers can produce different budgets.
SCIP's native gap is retained alongside the common incumbent-denominator gap.
Near-zero service uses an absolute certificate. An uncertified pass stops the
sequence; economic optimization cannot be reported as completed merely because
an incumbent exists. One wall-time budget covers all passes and transitions.

The internal SCIP feasibility tolerance is `min(1e-9, priority_tolerance/100)`;
the independent validator retains its existing tolerances. A direct-route
analytical regression exposed an incorrect economic optimum with the default
SCIP tolerance and near-zero priority rows. The stricter setting recovered the
known optimum and is explicitly recorded, not presented as identical to Gurobi's
internal tolerance. Numerical settings must accompany benchmark comparisons.
`optimize()` remains the sequential SCIP driver; thread settings are ceilings,
not proof of parallel search or a multithreaded LP implementation. Terminal
transformed sizes and SCIP-owned memory are not peak RSS or a presolved root
matrix. Those telemetry scopes must not be conflated.

## NPAD: isolated analytical and licensed qualification

Do not switch, pull or install packages in the active Sprint A checkout or venv.
Use a fresh detached worktree and a separate venv. Run the following in a
subshell; failure does not close the interactive terminal. `PR31_SHA` must be
the full reviewed PR31 commit supplied with the handoff, not an estimate.

```bash
(
  set -euo pipefail
  cd /home/vrrcelestino/model-agrologistic
  : "${PR31_SHA:?Set the full PR31 commit from the handoff}"
  git fetch origin research/scip-qualification
  test "$(git rev-parse origin/research/scip-qualification)" = "$PR31_SHA"
  SCIP_ROOT="$(mktemp -d /home/vrrcelestino/agrologistic-scip-pr31-XXXXXX)"
  export SCIP_CHECKOUT="$SCIP_ROOT/source"
  git worktree add --detach "$SCIP_CHECKOUT" "$PR31_SHA"
  /home/vrrcelestino/venv313/bin/python -m venv "$SCIP_ROOT/venv"
  export SCIP_PYTHON="$SCIP_ROOT/venv/bin/python"
  export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
  GUROBI_VERSION="$(/home/vrrcelestino/venv313/bin/python -c 'import importlib.metadata; print(importlib.metadata.version("gurobipy"))')"
  "$SCIP_PYTHON" -m pip install -e "$SCIP_CHECKOUT[dev,scip]" \
    "pyscipopt==6.2.1" "gurobipy==$GUROBI_VERSION"
  export SCIP_SOURCE_COMMIT="$PR31_SHA"
  export SCIP_REPORT_DIR="$SCIP_ROOT/qualification"
  export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic
  test -r "$GRB_LICENSE_FILE"
  test "$(git -C "$SCIP_CHECKOUT" rev-parse HEAD)" = "$PR31_SHA"
  test -z "$(git -C "$SCIP_CHECKOUT" status --porcelain --untracked-files=no)"
  SCIP_JOB="$(sbatch --parsable --account=sxdsouza --export=ALL \
    --chdir="$SCIP_CHECKOUT" --output="$SCIP_ROOT/qualification-%j.out" \
    "$SCIP_CHECKOUT/scripts/run_scip_qualification.slurm")"
  printf 'SCIP qualification job: %s\nRoot: %s\nReport: %s\n' \
    "$SCIP_JOB" "$SCIP_ROOT" "$SCIP_REPORT_DIR/qualification_report.json"
)
```

Return `qualification_report.json`, `native_build.log` and the pytest summary.
Acceptance requires zero skipped tests, including the licensed parity check.
The job requests only 8 GiB/20 minutes and never loads population workbooks or
submits another job. A failed qualification must be diagnosed before any
215-hub pilot. Keep the isolated worktree and environment for provenance.

Do not install or upgrade PySCIPOpt in the active Gurobi environment. Use an
isolated SCIP environment after dependency and LP-library identification, with
pinned Python, PySCIPOpt, SCIP, LP solver and build provenance. Prefer an
independent SCIP/SoPlex stack; any Gurobi-linked LP implementation must be
identified as a separate hybrid comparison. Record actual parallelism, not
just the scheduler CPU allocation.

## Implementation sequence

1. **Formulation mapping.** Implement the nine-scenario policy extensive form
   with identical variable domains, first-stage nonanticipativity, investment
   activation, scalable candidate capacity, expansion/bulkification, inventory
   balances, direct/transshipment routing, domestic/export service and separate
   emergency quantities. Use the same units and probability weights. Build a
   constraint-family equivalence ledger; fail explicitly on unsupported options.
2. **Lexicographic controller.** Execute service, capacity and economic cost
   sequentially with an explicit global optimization budget. Carry forward the
   documented higher-priority limits, rather than replacing the hierarchy with
   weighted penalties. Preserve valid incumbents and bounds before releasing
   transformed data or changing objectives. Record time consumed in every solve
   and controller transition; do not grant each pass a fresh eight hours.
3. **Result and audit parity.** Return the common result schema, all stage records,
   component costs, sparse flows/inventories, investment decisions and separate
   slacks. Run the existing independent validator; preserve completion receipts,
   checksums and read/build/optimize/extract/validate/export timings. Unknown
   bounds and unavailable telemetry must remain missing, not zero.
4. **Miniature qualification.** Test analytical optima, candidate-open coupling,
   expansion/bulkification, inventory carry-over, direct arcs, multi-hop flow,
   scenarios/probabilities, no-route cases, infeasibility and resource termination.
   Compare objective values and reconstructed feasibility against Gurobi, not
   exact variable vectors when alternative optimal solutions exist. Test all
   three passes, near-zero service objectives and preservation of prior limits.
5. **215-hub pilot.** Only after qualification, prepare warehouse-only and
   direct-enabled cases using the already materialized and hashed 215-hub input,
   nine scenarios and the same filtering/repair contract. Do not rerun OSRM or
   change nearest-20% selection. Execute one resource-reviewed case first and
   assess its memory, bounds and controller semantics before the second.

Sequential re-solves need careful transformed-model lifecycle handling. The
[PySCIPOpt Model API](https://pyscipopt.readthedocs.io/en/latest/api/model.html)
documents version/parameter inspection and `freeTransform`; merely calling
these APIs is not a proof that the new lexicographic controller matches Gurobi.
Dedicated tests must establish that equivalence.

## Acceptance and comparability

Retain 10% as the common quality target. Report each solver's native gap and
an independently reconstructed common gap for positive minimization objectives,
`(incumbent - bound) / abs(incumbent)`, with explicit numerical handling of tiny
bound inversions. Near-zero service uses its absolute certificate. A native
SCIP gap parameter and a Gurobi gap parameter need not have identical conventions.

Gurobi's bound-dependent inherited priority budgets must be reproduced or any
controlled difference explicitly versioned and disclosed. Two runs may have
different permissible capacity budgets even when both use a nominal 10% gap.
Do not interpret differences in economic cost as solver superiority over the
same feasible region unless the effective higher-priority limits are comparable.

Keep the same inputs, scenario design, seed policy, global time budget, resource
reservation and independent feasibility tolerances. SCIP uses its supported LP
algorithm and build; the Gurobi all-barrier setting is not blindly transferred
to SCIP. Record LP backend, thread behaviour and distinct memory accounting.
No solver is assumed to have a smaller frontier in advance.

## Sprint D: evidence through 400 hubs

Compare 215, 300 and 400 hubs for warehouse-only and direct-enabled networks.
Historical Gurobi 215-hub results remain labelled with their historical method;
they are not all-barrier observations. A new 215-hub Gurobi control is not part
of the current submission batch. If algorithm-matched controls are required
later, define them as a separate comparison rather than silently relabelling
or rerunning the accepted historical experiment.

Attempt 300/400-hub SCIP instances only after the 215-hub pilot and resource
admission. Retain failed builds, no-incumbent terminations, valid high-gap
incumbents, incomplete hierarchies and successful certificates. Scheduler
COMPLETED is not numerical acceptance. An OOM/time limit does not prove model
infeasibility or impossibility at every larger population.

Report both the largest tested **quality-certified** population and the largest
tested population yielding an independently valid incumbent. These are empirical
frontiers conditional on the configuration and budget. Four hundred hubs is
currently a stressed test point, not an established universal maximum. Do not
assume monotonic complexity or infer untested populations from one failure.

## Sprint E: first collaborator package

Deliver an English manuscript/report, input and source fingerprints, environment
manifest, selected population lists, route/connectivity audits, per-stage status
and gap tables, timing/memory figures and all negative outcomes. Separate
resource-censored incumbents from economic comparisons supported by completed
hierarchies. Include instructions and an output inventory; keep credentials,
licensed binaries and uncurated temporary files out of the shared package.

Maintain the Zenodo draft as a curation target, not an automatically published
record. Freeze and verify the shareable artifacts before publication. The first
package does not claim the 500--1000-hub frontier or completion of a Benders
implementation. After collaborator review, decide whether to resume Sprint B
with larger populations, additional algorithms or a dedicated Benders protocol.
