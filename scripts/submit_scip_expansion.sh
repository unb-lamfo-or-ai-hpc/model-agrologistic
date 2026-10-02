#!/bin/bash
# Submit once; preserve partial-submission receipts rather than silently retrying.
set -euo pipefail
: "${SCIP_EXPANSION_CHECKOUT:?Set the new isolated checkout}"
: "${SCIP_PYTHON:?Set the unchanged qualified Python environment}"
: "${SCIP_EXPANSION_ROOT:?Set the freshly prepared expansion root}"
: "${SCIP_EXPANSION_SOURCE:?Set the exact checkout commit}"
cd "$SCIP_EXPANSION_CHECKOUT"
test "$(git rev-parse HEAD)" = "$SCIP_EXPANSION_SOURCE"
test -z "$(git status --porcelain --untracked-files=no)"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
for index in 0 1 2 3 4; do
  "$SCIP_PYTHON" scripts/prepare_scip_expansion.py \
    --plan "$SCIP_EXPANSION_ROOT/expansion_plan.json" --index "$index"
done
mkdir "$SCIP_EXPANSION_ROOT/.submission-claimed"
unset SBATCH_QOS
WORKER="$SCIP_EXPANSION_CHECKOUT/scripts/run_scip_expansion.slurm"
preflight_job="$(sbatch --parsable --account=sxdsouza --partition=intel-256 \
  --job-name=scip-expand-pre --cpus-per-task=4 --mem=16G --time=02:00:00 \
  --array=0-4%2 --export=ALL,SCIP_PHASE=preflight --chdir="$SCIP_EXPANSION_CHECKOUT" \
  --output="$SCIP_EXPANSION_ROOT/preflight-%A_%a.out" "$WORKER")"
printf 'PREFLIGHT_JOB=%s\n' "$preflight_job" | tee "$SCIP_EXPANSION_ROOT/submission.txt"
solve_job="$(sbatch --parsable --account=sxdsouza --partition=intel-256 \
  --job-name=scip-expand --cpus-per-task=4 --mem=192G --time=12:00:00 \
  --array=0-2%2 --dependency="aftercorr:${preflight_job%%;*}" \
  --export=ALL,SCIP_PHASE=solve --chdir="$SCIP_EXPANSION_CHECKOUT" \
  --output="$SCIP_EXPANSION_ROOT/solve-%A_%a.out" "$WORKER")"
printf 'SOLVE_JOB=%s\n' "$solve_job" | tee -a "$SCIP_EXPANSION_ROOT/submission.txt"
printf 'Campaign: %s\n400-hub solves: not submitted (preflight only)\n' "$SCIP_EXPANSION_ROOT"
