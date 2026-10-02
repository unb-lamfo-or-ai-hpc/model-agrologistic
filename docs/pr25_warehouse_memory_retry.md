# PR #25: isolated warehouse-only memory retry

> Historical resource-only attempt: job 2089838 also reached the soft-memory
> limit. Preserve its outputs and use the [dual/four-thread retry](pr25_warehouse_dual_retry.md).
> Its reference plan is archived as `v020_validation_reference_memory128.yaml`.

## Diagnosis and evidence boundary

The supplied log for NPAD job `2088823_0` confirms `Memory limit reached`.
Optimization stopped after 11393.77 seconds, before the 14400-second limit,
with economic incumbent 764469455725.4, bound 409973108225.9 and gap 46.3716%.
The independent checker accepts service and residuals, but
`three_completed_passes` is false. This is useful partial evidence, not a
completed lexicographic solution. The accepted direct-arc case is not repeated.

Gurobi's [SoftMemLimit](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter:SoftMemLimit)
uses decimal GB and allows a graceful stop with solution retrieval. It differs
from the Slurm allocation and can be overshot between safe checks. Process
MaxRSS is not exactly the same as Gurobi's internal memory accounting.

## Controlled resource change

| Setting | Previous warehouse retry | New warehouse retry |
|---|---|---|
| SoftMemLimit (decimal GB) | 56 | 128 |
| Slurm allocation (GiB) | 96 | 192 |
| Solver threads | 16 | 16 |
| Solver time limit (seconds) | 14400 | 14400 |
| Slurm wall time | 6 hours | 6 hours |
| Target MIP gap | 1% | 1% |

The allocation leaves approximately 73 GiB beyond the soft limit for Python,
other native memory and transient overshoot; it is a margin, not a guarantee.
No solver method, node-file policy, objective tolerance, route set, penalty,
scenario, workbook, model or validation rule changes. The long root relaxation
and crossover remain runtime risks. Method/thread tuning is deferred until
this isolated resource change has evidence.

This is a fresh solve, not continuation of an in-memory search. The new name
is `policy_sto9_p20_warehouse_t14400_mem128`, under
`data/results/validation/pr25-final/policy-nine-memory128`.
Old partial results are never overwritten. Existing rejected new outputs also
stop resubmission for review. The final plan preserves the nine accepted
references exactly. The preceding plan is retained as
`experiments/v020_validation_reference_t14400.yaml`.

The launcher requires at least 192 GiB and 16 CPUs before starting Gurobi.
Submit one job, not an array. Partition availability is determined on NPAD;
`intel-256` is the requested default, not a claim about current availability.
Keep the approved isolated runtime and all accepted receipts unchanged.

## NPAD execution

Paste only the block contents. The subshell isolates `set -e` so a failure does
not close the VS Code terminal. No reinstall or complete rerun is necessary.

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
    --memory-retry --index 0 --check-only
  sbatch scripts/run_pr25_warehouse_memory_retry.slurm
)
```

The light check verifies runtime, input existence, manifest structure and
output safety; it neither reserves resources nor certifies workbook contents.
The compute task uses the normal pipeline and full run assessor. A nonzero
exit requires review even when a feasible solution has been exported.

After termination, generate the final report in a fresh directory:

```bash
(
  set -e
  cd /home/vrrcelestino/model-agrologistic
  export PYTHONNOUSERSITE=1
  export PYTHONDONTWRITEBYTECODE=1
  PR25_REPORT_DIR="data/results/validation/pr25-final/report-memory128-$(date -u +%Y%m%dT%H%M%SZ)"
  /home/vrrcelestino/venv313/bin/python scripts/validate_v020_evidence.py \
    --quality-report data/results/validation/pr25-final/quality/quality_report.json \
    --output-dir "$PR25_REPORT_DIR"
  cat "$PR25_REPORT_DIR/v020_validation_report.json"
)
```

Return the report and job accounting. If not accepted, also return the new
job log tail and `lexicographic_stages.csv` from the new run directory.
Do not relax the gate or repeat accepted cases to force completion. PRs #26
and #27 remain frozen until explicitly resumed. No merge/tag is part of this
retry; exact historical numerical replication remains unproven.
