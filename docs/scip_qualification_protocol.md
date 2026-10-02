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

## Sprint A terminal execution status

Operator-supplied accounting on 19 September 2026 reports the following frozen
all-barrier executions. All three processes completed with exit code `0:0`;
their numerical acceptance remains subject to the campaign audits.

| Job | Configuration | Scheduler elapsed | Batch MaxRSS (K) |
|---|---|---|---|
| 2105903 | 400 hubs, direct enabled | 08:22:32 | 100906084 |
| 2106399 | 400 hubs, warehouse only | 08:21:35 | 113176020 |
| 2106401 | 300 hubs, warehouse only | 05:52:02 | 60936308 |

Each requested four CPUs and 192 GiB, with a 12-hour scheduler limit and a
28,800-second global optimization budget. Scheduler elapsed includes work
outside optimization and is not the solve time. Do not resubmit these cases.
For each campaign, review `audit/nine_audit_manifest.json`,
`audit/nine_results.json` and `audit/nine_stage_gaps.json`. Preserve the per-run
`solver_diagnostics.json`, `independent_validation.json` and
`run_completion.json` for diagnostic and provenance checks. A completed process
does not certify the three-stage hierarchy or the 10% gap target.

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
  unset SBATCH_QOS
  SCIP_JOB="$(sbatch --parsable --account=sxdsouza --export=ALL \
    --chdir="$SCIP_CHECKOUT" --output="$SCIP_ROOT/qualification-%j.out" \
    "$SCIP_CHECKOUT/scripts/run_scip_qualification.slurm")"
  printf 'SCIP qualification job: %s\nRoot: %s\nReport: %s\n' \
    "$SCIP_JOB" "$SCIP_ROOT" "$SCIP_REPORT_DIR/qualification_report.json"
)
```

The qualification worker deliberately contains no QoS directive. The explicit
`qos1` submission was rejected by NPAD before a job was created; a QoS appearing
in the cluster-wide inventory does not establish access for this association.
Use the account's default QoS and clear inherited `SBATCH_QOS` in the submission
subshell. This does not change the account or cluster configuration. The frozen
Sprint A scripts and their historical scheduling settings remain unchanged.

After this specific submission rejection, reuse the existing isolated source
and venv rather than reinstalling packages. Fetch the corrected PR31 commit,
verify tracked cleanliness in the isolated source, switch that detached source
to the exact handoff SHA, re-export the worker variables and submit once with a
new report directory. If multiple isolated checkouts exist, select the intended
one explicitly; never silently select the most recent directory. Preserve the
original Gurobi checkout and evidence. Save the returned job ID before retrying
any subsequent failure.

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

## Reviewed NPAD qualification and first population pilot

NPAD job 2106964 completed on 19 September 2026 at source
`42200df78c36e2fc2dd216ef46a4f7f84139c156`. The supplied qualification report
records 42 tests, zero skips, accepted analytical and licensed parity, and an
unchanged implementation identity. The native banner identifies SCIP 10.0.2,
8-byte floating-point precision and **SoPlex 8.0.2** as the LP solver on Linux
x86_64 with Python 3.13.15 and PySCIPOpt 6.2.1. This is not a Gurobi-backed LP
comparison. The banner does not establish effective multicore LP execution.

The runtime probe intentionally predates this review: its null LP-backend field
and pending qualification text are not solver failures. Preserve both historical
reports unchanged. The new `pilot_admission.json` is a separate, narrowly scoped
decision after verification of all six hashed qualification artifacts and the
current implementation/environment identity. Changes to the mathematical sources
or dependencies invalidate reuse of that qualification.

Only **one warehouse-only 215-hub, nine-scenario pilot** is admitted. The direct
variant and larger populations await review of its output. This is conditional
experimental admission, not advance certification of a large-instance result.

| Resource or contract | Pilot setting |
|---|---|
| Input | Existing OSRM-authoritative 215-hub workbook; hash frozen at preparation |
| Routing | Unchanged nearest-20% baseline plus audited strong interhub repair |
| Optimization | Sequential service, capacity and economic passes; global 28,800 s |
| Quality | Common incumbent-denominator gap <=10%; absolute service certificate |
| Scheduler | intel-256, account sxdsouza, four CPUs, 192 GiB, 12 h; default QoS |
| Native memory | `limits/memory=131072` MB of SCIP accounting, not process RSS |
| Thread settings | Four-thread ceilings; sequential `optimize()`, not concurrent SCIP |
| LP method | Native SoPlex defaults; no translation of Gurobi barrier parameters |
| Preventive size | At most 16 million shared-formulation estimated variables |
| Excluded analyses | EVPI/VSS and IIS; no automatic additional instances |

SCIP warns that its reported memory can be lower than actual memory usage;
the parameter is not a guarantee against Python or solver process OOM. Native
indicator/transformation variables are not included in the shared-formulation
estimate. Preserve scheduler RSS, pipeline RSS and terminal SCIP-owned memory
as distinct measurements. See the official
[SCIP parameter reference](https://scipopt.org/scip/doc/html/PARAMETERS.php) and
[concurrent-solving documentation](https://www.scipopt.org/doc/html/CONCSCIP.php).
Listing TinyCThread or setting `parallel/maxnthreads` does not mean that this
sequential driver invokes concurrent optimization.

After fetching the exact handoff commit and switching only the clean isolated
checkout, run the following with its existing qualified Python. No dependency
installation or OSRM materialization is required. Set `SCIP_SOURCE_COMMIT` to
that exact commit, not the historical qualification commit.

```bash
(
  set -euo pipefail
  : "${SCIP_SOURCE_COMMIT:?Set the exact current PR31 handoff SHA}"
  export SCIP_CHECKOUT=/home/vrrcelestino/agrologistic-scip-pr31-4N2wGy/source
  export SCIP_PYTHON=/home/vrrcelestino/agrologistic-scip-pr31-4N2wGy/venv/bin/python
  export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
  cd "$SCIP_CHECKOUT"
  test "$(git rev-parse HEAD)" = "$SCIP_SOURCE_COMMIT"
  test -z "$(git status --porcelain --untracked-files=no)"
  "$SCIP_PYTHON" -m pytest tests/test_scip_pilot.py -q
  PILOT_ROOT="/home/vrrcelestino/model-agrologistic/data/results/hpc/scip-h215-warehouse-$(date -u +%Y%m%dT%H%M%SZ)"
  "$SCIP_PYTHON" scripts/prepare_scip_pilot.py \
    --campaign-root "$PILOT_ROOT" \
    --qualification-dir /home/vrrcelestino/agrologistic-scip-pr31-4N2wGy/qualification-20260919T121956Z \
    --workbook /home/vrrcelestino/model-agrologistic/data/processed/policy_population_v020_osrm/warehouses_215/model_input.xlsx
  export SCIP_MANIFEST="$PILOT_ROOT/campaign.yaml"
  unset SBATCH_QOS
  PILOT_JOB="$(sbatch --parsable --account=sxdsouza --export=ALL \
    --chdir="$SCIP_CHECKOUT" --output="$PILOT_ROOT/slurm-%j.out" \
    "$SCIP_CHECKOUT/scripts/run_scip_pilot.slurm")"
  printf '%s\n' "$PILOT_JOB" > "$PILOT_ROOT/submission.txt"
  printf 'SCIP pilot job: %s\nCampaign: %s\n' "$PILOT_JOB" "$PILOT_ROOT"
)
```

The worker verifies qualification/input/source hashes, claims the new campaign
directory atomically and performs preflight on the compute node before building
the model. A claim is retained after failure: diagnose it and use a separately
reviewed new campaign instead of deleting the marker or overwriting evidence.
The mathematical size/population gate is enforced again after preflight. Ordinary
solver exceptions are followed by an audit attempt; an external kill/OOM may
prevent that final audit. Missing audit files therefore require the Slurm log.

Return `pilot_admission.json`, `audit/nine_audit_manifest.json`,
`audit/nine_results.json`, `audit/nine_stage_gaps.json` when available, and the
scheduler status. Keep `scip.log` and the per-run `preflight.json`,
`independent_validation.json`, `run_summary.json`, `lexicographic_stages.csv`
and completion receipt for follow-up. A completed scheduler job does not certify
the full hierarchy; early-stage feasible incumbents remain reportable negative
outcomes. Do not submit 300/400 hubs or the second 215-hub variant automatically.

### Subsequent bounded expansion

The separately authorized [isolated expansion protocol](scip_expansion_protocol.md)
prepares the direct-enabled215-hub case and both300/400-hub variants in a new
worktree. It admits only the first three solves, with two new solves at most in
parallel;400-hub cases remain preflight-only. The running pilot and this original
single-case admission remain unchanged. This explicit resource experiment does
not imply that the original pilot has completed or certified population-scale
performance.

### Resource-amended repeat after the first memory stop

The [SCIP memory-sensitivity repeat](scip_memory_repeat.md) supersedes the plan to
close the SCIP campaign immediately after the original jobs terminate. It admits
two new 300-hub cases on full-memory `intel-512` allocations, with an internal
SCIP limit of393216 MB and unchanged mathematical/time/gap settings. The original
131072 MB threshold is a campaign parameter, not an intrinsic SCIP maximum.
Baseline jobs remain untouched; the new array checks only the termination of the
two earlier300-hub attempts and uses at most two simultaneous nodes. Original
215-hub jobs are neither repeated nor awaited; accepted results at their smaller
budget remain valid. The400-hub cases remain unsubmitted. The revised two-case
protocol supersedes the four-case preparation at `e5a2334`.
