# Bounded 400-hub Gurobi pilot

## Experimental contract

The independently audited 300-hub direct-enabled case met the 10% criterion. The warehouse-only solution was independently feasible but retained a 50.5203% economic gap at the time limit. Preserve both outcomes; the next population is not a retry or a retrospective relaxation.

The 400-hub pair contains an estimated 42,106,944 and 42,426,624 variables. Admit it with a finite 43,000,000-variable preventive threshold and an explicit review note. Keep nine scenarios, nearest-20% interhub selection with audited repair, four threads, 28,800 s total optimization time, 0.10 relative gap, 128 GiB solver soft memory, and 192 GiB Slurm allocation. Run at most one array task. The soft limit is not a process-RSS guarantee; a memory-censored outcome is plausible. Do not alter parameters after submission or automatically retry an incomplete run. Do not submit 500-hub cases from this receipt.

The existing OSRM workbook is reused without rematerialization. The generator and optimizer implementation remain unchanged. Preflight is mandatory but does not predict solving memory or convergence. This pilot includes no SCIP or EVPI/VSS calculation.

## NPAD submission

Run the following block once from an interactive Bash terminal. Its subshell keeps failures from closing that terminal. Start with a clean checkout on the indicated branch; `git pull --ff-only` must succeed. If a command fails after creating a campaign directory, preserve that directory and diagnose it rather than repeating the entire block blindly.

```bash
(
set -e
cd /home/vrrcelestino/model-agrologistic
git switch research/pilot-readiness-curation
git pull --ff-only origin research/pilot-readiness-curation

export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE="$PWD/secrets/gurobi.lic"
PYTHON=/home/vrrcelestino/venv313/bin/python
"$PYTHON" -m pytest tests/test_nine_campaign.py tests/test_nine_audit.py tests/test_release_readiness.py

H400_INPUT="$PWD/data/processed/nine_population_osrm_v1/warehouses_400/model_input.xlsx"
printf '%s  %s\n' \
  c3085456997714ef5a8bdbf61e2c9a5e578c2636003947427cf58933d21ceb13 \
  "$H400_INPUT" | sha256sum -c -

export H400_CAMPAIGN="$PWD/data/results/hpc/nine-connectivity-h400-$(date -u +%Y%m%dT%H%M%SZ)"
"$PYTHON" scripts/prepare_nine_scenario_campaign.py \
  --campaign-root "$H400_CAMPAIGN" \
  --populations 400 \
  --workbook-override "400=$H400_INPUT" \
  --max-estimated-variables 43000000 \
  --resource-review-note "300-hub cases reached approximately 81 GiB RSS; 400-hub scaling may exceed the unchanged 128 GiB solver soft limit. Admit one active task at 192 GiB allocation, retain all censored outcomes, no automatic retry."
export NINE_MANIFEST="$H400_CAMPAIGN/campaign.yaml"

H400_PREFLIGHT_JOB="$(sbatch --parsable \
  --account=sxdsouza --qos=preempt --partition=intel-256 \
  --job-name=nine-h400-pre --cpus-per-task=4 --mem=16G --time=01:00:00 \
  --export=ALL --output="$H400_CAMPAIGN/preflight-%j.log" \
  --wrap='set -eu
    cd /home/vrrcelestino/model-agrologistic
    /home/vrrcelestino/venv313/bin/python scripts/audit_nine_campaign.py \
      "$NINE_MANIFEST" --preflight --indices 0 1 \
      --output-dir "$H400_CAMPAIGN/preflight" --require-accepted')"
printf 'Campaign: %s\nPreflight job: %s\n' "$H400_CAMPAIGN" "$H400_PREFLIGHT_JOB"

H400_SOLVE_JOB="$(sbatch --parsable \
  --account=sxdsouza --qos=preempt --partition=intel-256 \
  --job-name=nine-h400 --cpus-per-task=4 --mem=192G --time=12:00:00 \
  --array=0-1%1 --dependency="afterok:$H400_PREFLIGHT_JOB" \
  --export=ALL --output="$H400_CAMPAIGN/solve-%A_%a.log" \
  scripts/run_nine_connectivity.slurm)"
printf '400-hub solve array: %s\n' "$H400_SOLVE_JOB"

H400_AUDIT_JOB="$(sbatch --parsable \
  --account=sxdsouza --qos=preempt --partition=intel-256 \
  --job-name=nine-h400-audit --cpus-per-task=4 --mem=16G --time=00:30:00 \
  --dependency="afterany:$H400_SOLVE_JOB" --export=ALL \
  --output="$H400_CAMPAIGN/audit-%j.log" \
  --wrap='set -eu
    cd /home/vrrcelestino/model-agrologistic
    /home/vrrcelestino/venv313/bin/python scripts/audit_nine_campaign.py \
      "$NINE_MANIFEST" --indices 0 1 --output-dir "$H400_CAMPAIGN/final-audit"')"
printf 'Audit job: %s\nReport: %s/final-audit\n' "$H400_AUDIT_JOB" "$H400_CAMPAIGN"
)
```

The solve array is queued with `afterok` and cannot start if preflight fails. A failed dependency may leave jobs pending; inspect and cancel only the recorded unstarted dependent jobs if necessary. The final audit runs after all solve tasks terminate, including failures. Omitting `--require-accepted` on this final reporting job allows collection of mixed or censored results without changing their classifications. No report exit code is a substitute for reading the acceptance manifest.

Both cases require up to sixteen optimization job-hours sequentially, plus queueing and pipeline overhead. Keep the code, environment and campaign unchanged until completion. Save the printed path and all three job identifiers because variables in this subshell are not retained in the interactive shell.

## Return evidence and decision gate

Return Slurm accounting and `final-audit/nine_audit_manifest.json`, `nine_results.json`, and `nine_stage_gaps.json` when available. If a run lacks completed artifacts, also return its log tail; missing stage exports must not become a zero gap. Retain the graph audit products generated by preflight, input and campaign hashes, and all failed or interrupted outputs. Compare independent validity, final service, stage gaps, allowed hierarchical degradation, timings and measured memory. Do not compare a time-limited incumbent against a converged economic objective as if the difference were a certified policy effect.

Admission of 500 hubs and any solver-method or memory-budget sensitivity requires review of these results. Increasing a resource limit later constitutes a separate experiment with a new campaign identity. Native SCIP implementation and cross-solver qualification remain separate work.
