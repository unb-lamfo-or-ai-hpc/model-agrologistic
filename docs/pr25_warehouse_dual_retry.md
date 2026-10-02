# PR #25: bounded dual-simplex/four-thread retry

## Observed failure and methodological decision

NPAD job 2089838 stopped at Gurobi's 128 decimal GB soft-memory limit after
12650.56 optimization seconds, despite a 192 GiB Slurm allocation. It explored
16 nodes; the final economic incumbent was 764469455725.4, lower bound
410003580551.1 and gap 46.3676%. The preceding 56 GB attempt explored one node
and ended with the same displayed incumbent and a 46.3716% gap. Increasing the
memory ceiling alone did not resolve the incomplete hierarchy.

The final report `report-memory128-20260913T171425Z` accepts levels 1–3 and nine
references. Only `three_completed_passes` fails in the remaining run. Service,
independent residuals and costs, selected network/penalties, runtime identity
and provenance pass. This is a computational completion failure, not evidence
of infeasibility or a reason to alter the model or loosen acceptance.

## Numerical profile, not a mathematical revision

| Setting | Memory-only attempt | New attempt |
|---|---|---|
| Root relaxation method | Automatic | Dual simplex (`Method=1`) |
| Solver threads / requested CPUs | 16 | 4 |
| SoftMemLimit (decimal GB) | 128 | 128 |
| Slurm memory (GiB) | 192 | 192 |
| Solver time limit (seconds) | 14400 | 14400 |
| Slurm wall time | 6 hours | 6 hours |
| Target MIP gap | 1% | 1% |

Gurobi's [parameter guidelines](https://docs.gurobi.com/projects/optimizer/en/current/concepts/parameters/guidelines.html)
recommend fewer threads when parallel MIP model copies consume memory. The
[Method reference](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter:Method)
describes dual simplex as a lower-memory alternative to concurrent LP solves.
The logs show an expensive root relaxation/crossover and prolonged waiting
for other threads. They motivate testing an explicit root algorithm; they do
not prove which internal structure exhausted memory.

These are two jointly declared computational changes. This is not a controlled
estimate of their individual speedups and not a guarantee of reduced runtime.
`MultiObjMethod` is not set: it concerns continuous multi-objective models,
whereas this problem is a MILP. Node-file spilling is not introduced in this
bounded attempt: it addresses stored search nodes, not all root-relaxation or
per-thread allocations, and the observed tree was small. No scratch files or
additional storage quota are required by this retry policy.

The workbook, scenarios, routes, slacks, hierarchy, tolerances, seed and gap
target remain unchanged. Solver parameters are captured in the normal run
identity. No optimization implementation, independent validator or dependency
changes, so the approved runtime receipt remains applicable while its hash
matches. Different numerical paths can select different equivalent investments;
unchanged mathematical settings do not imply identical incumbent decisions.

## Evidence preservation

New manifest: `experiments/v020_policy_warehouse_dual_retry.yaml`, index 0 only.
New run: `policy_sto9_p20_warehouse_t14400_dual4`, under
`data/results/validation/pr25-final/policy-nine-dual4`.
This is a fresh solve, not resumption of an in-memory search. Both earlier
partial attempts remain untouched. Existing rejected output in the new
directory also blocks resubmission for review.

The default validation plan retains all nine accepted specifications and paths;
the preceding plan is archived as `v020_validation_reference_memory128.yaml`.
The final four-level report must be accepted before merge. If this bounded
attempt still fails, inspect its stages and resource log before another run.
Do not raise limits indefinitely or silently remove a required reference.
Any reduction of the demonstrator scope requires an explicit maintainer decision.
PRs #26–27 remain frozen.

## NPAD commands

Paste only the contents of the block. The subshell prevents `set -e` failures
from closing the interactive terminal. Do not reinstall the approved environment.

```bash
(
  set -e
  cd /home/vrrcelestino/model-agrologistic
  git fetch origin
  git switch feature/v0.2-mathematical-reformulation
  git pull --ff-only origin feature/v0.2-mathematical-reformulation
  export PYTHONNOUSERSITE=1
  export PYTHONDONTWRITEBYTECODE=1
  export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic
  PR25_PYTHON=/home/vrrcelestino/venv313/bin/python
  "$PR25_PYTHON" -m ruff check .
  "$PR25_PYTHON" -m pytest tests/test_pr25_nine_scenario_retry.py
  "$PR25_PYTHON" scripts/run_pr25_nine_scenario_retry.py \
    --dual-retry --index 0 --check-only
  sbatch scripts/run_pr25_warehouse_dual_retry.slurm
)
```

The check-only stage verifies runtime, input existence and output safety. It
does not reserve resources or revalidate the workbook. The single compute job
requires 192 GiB and at least four CPUs. `intel-256` is the default partition;
present availability must be checked on NPAD. The batch launcher also limits
OpenMP/OpenBLAS/MKL threads to four. Do not repeat the previous arrays.

After the job terminates, generate a fresh report:

```bash
(
  set -e
  cd /home/vrrcelestino/model-agrologistic
  export PYTHONNOUSERSITE=1
  export PYTHONDONTWRITEBYTECODE=1
  PR25_REPORT_DIR="data/results/validation/pr25-final/report-dual4-$(date -u +%Y%m%dT%H%M%SZ)"
  /home/vrrcelestino/venv313/bin/python scripts/validate_v020_evidence.py \
    --quality-report data/results/validation/pr25-final/quality/quality_report.json \
    --output-dir "$PR25_REPORT_DIR"
  cat "$PR25_REPORT_DIR/v020_validation_report.json"
)
```

Return the new report and Slurm accounting. If incomplete, include the new
job-log tail and the new run's `lexicographic_stages.csv`. A feasible incumbent
or Slurm completion alone is not acceptance. Exact historical numerical
replication and a complete scalability frontier remain outside this claim.
