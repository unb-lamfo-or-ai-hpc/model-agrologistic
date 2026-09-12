# PR #25: bounded nine-scenario completion

## Accepted evidence and remaining failure

The maintainer's 2026-09-12 NPAD report accepts levels 1 (mathematical/data
contract), 2 (software/licensed analytical tests), and 3 (independent solution
validation). Eight of the ten reference executions are accepted. Both remaining
nine-scenario solutions satisfy domestic service and the independent residual
and cost checks, but their lexicographic hierarchy is incomplete at 3600 seconds.

| Nine-scenario case | Service | Capacity | Economic cost | Result |
|---|---|---|---|---|
| Warehouse-only | Optimal | Time limit; gap about 99.765% | Not started | Partial |
| Direct arcs | Optimal | Optimal within 1%; gap about 0.8644% | Time limit; gap about 99.9998% | Partial |

The warehouse-only result is dominated by a poor capacity incumbent; its large
emergency quantities are not an optimized recommendation for physical investment.
The reported process peaks were approximately 43-44 GiB, below the 96 GiB Slurm
request. The logs explicitly identify time limits, not an observed memory failure.
The Slurm failure code comes from the launcher's final acceptance guard after
Gurobi exported a usable but incomplete solution. It is not solver infeasibility.

The warehouse summary declares job 2088491 while the supplied array/log context
references 2088219. Preserve those recorded identifiers; the artifact fingerprints
and checksums, not a rewritten job identifier, determine admission.

## Runtime isolation is mandatory

The interactive Python session imported Gurobi 13.0.2 from
`/home/vrrcelestino/.local/lib/python3.13/site-packages`. With
`PYTHONNOUSERSITE=1`, the same Python executable imports the approved Gurobi
13.0.3 from `/home/vrrcelestino/venv313/lib/python3.13/site-packages`.
All 37 implementation source hashes were identical between the two reports.
Isolation restores the approved runtime fingerprint:

```text
c9cfe18e8c1fe19d4e5659139804b4b8dea7b650d4c5e0c3dcb8b5afde4f3042
```

Do not reinstall either package, rewrite quality receipts, or weaken fingerprint
checks. Set the environment variable before starting Python. The existing NPAD
licensed quality receipt remains usable because this increment changes only
experiment manifests, launch scripts, tests and documentation, not `src/logic`.
Additional orchestration tests are verified separately in CI.

## Controlled change

`experiments/v020_policy_nine_scenario_retry.yaml` copies the effective settings
of policy indices 14/15. The only solver change is **TimeLimit: 3600 -> 14400**.
New experiment names and metadata identify the retry. Workbook, scenario design,
route selection, penalties, slack semantics, objective hierarchy, MIPGap (1%),
SoftMemLimit (56), seed and 16 solver threads remain unchanged. Regression tests
compare all effective configuration fields, not merely selected YAML lines.

This is a fresh solve, not continuation of a saved branch-and-bound search.
14400 seconds is the overall configured optimization budget, not a fresh budget
for each lexicographic pass. The six-hour Slurm wall limit leaves room for data
loading, model construction, independent validation and export. It neither
changes the solver limit nor guarantees completion. No new solver-method tuning,
larger population, additional scenario design or relaxed acceptance criterion is
introduced. A repeated partial result remains unaccepted and visible.

| Retry index | Name | Original policy index |
|---|---|---|
| 0 | `policy_sto9_p20_warehouse_t14400` | 14 |
| 1 | `policy_sto9_p20_direct_t14400` | 15 |

The new output root is
`data/results/validation/pr25-final/policy-nine-t14400`. The old 3600-second
outputs under `.../policy` are not moved or overwritten. The final reference
plan still requires ten cases: eight unchanged references plus these two retries.
`v020_validation_reference_t3600.yaml` preserves the historical selection.
The complete embedded plan is recorded in each generated report.

## NPAD execution

Run from the repository root. No `exit` or global `set -e` is needed in the
interactive terminal. Keep implementation source, input workbooks and the
approved environment unchanged during the jobs.

```bash
cd /home/vrrcelestino/model-agrologistic
conda activate /home/vrrcelestino/venv313
git fetch origin
git switch feature/v0.2-mathematical-reformulation
git pull --ff-only origin feature/v0.2-mathematical-reformulation
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic

/home/vrrcelestino/venv313/bin/python scripts/run_pr25_nine_scenario_retry.py --index 0 --check-only &&
/home/vrrcelestino/venv313/bin/python scripts/run_pr25_nine_scenario_retry.py --index 1 --check-only &&
sbatch scripts/run_pr25_nine_scenario_retry.slurm
```

The light check verifies the runtime receipt, selected manifest, input-file
existence and output safety; it does not invoke Gurobi or certify workbook
contents. Each compute task uses the normal pipeline and runs the complete
reference assessment after export. An already accepted retry is skipped;
existing unaccepted outputs stop the task for review rather than being overwritten.
Submit at most this two-task array; do not resubmit the original ten-task launcher.
Default resources are intel-256, 16 CPUs, 96 GiB, and at most two simultaneous
tasks. Availability is determined by the scheduler; a partition override is
per submission and must retain adequate memory and wall-time limits.

After both tasks finish, regenerate the report in a new directory:

```bash
export PYTHONNOUSERSITE=1
REPORT_DIR="data/results/validation/pr25-final/report-t14400-$(date -u +%Y%m%dT%H%M%SZ)"
/home/vrrcelestino/venv313/bin/python scripts/validate_v020_evidence.py \
  --quality-report data/results/validation/pr25-final/quality/quality_report.json \
  --output-dir "$REPORT_DIR"
cat "$REPORT_DIR/v020_validation_report.json"
```

For historical assessment, use the same command with
`--plan experiments/v020_validation_reference_t3600.yaml` and a different output
directory. Never substitute the archived v0.1 certificate for these references.

Merge readiness requires an accepted final four-level report, not just Slurm
completion. Exact numerical replication of Artur's published tables remains
unestablished even after this bounded reference gate passes. The next scoped
work remains PR #26 (English documentation/comments), then PR #27 (Quarto
Manuscript using quarto-sbc). No new release/tag or repository-publication action
is part of this retry.
