#!/bin/bash
# All baseline jobs must terminate before any repeated instance starts.
set -euo pipefail
: "${SCIP_MEMORY_CHECKOUT:?Set the new detached checkout}"
: "${SCIP_MEMORY_ROOT:?Set the new campaign root}"
: "${SCIP_MEMORY_SOURCE:?Set its exact commit}"
: "${SCIP_PYTHON:?Set the read-only qualified Python}"
cd "$SCIP_MEMORY_CHECKOUT"
test "$(git rev-parse HEAD)" = "$SCIP_MEMORY_SOURCE"
test -z "$(git status --porcelain --untracked-files=no)"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
for index in 0 1 2 3; do
  "$SCIP_PYTHON" scripts/prepare_scip_memory_campaign.py \
    --plan "$SCIP_MEMORY_ROOT/memory_plan.json" --index "$index"
done
# IDs are fixed to the reviewed baseline campaigns. A completed baseline need
# not remain in the controller; accounting must confirm its terminal status.
dependencies=()
mkdir "$SCIP_MEMORY_ROOT/.submission-check-claimed"
for baseline_job in 2107034 2107114; do
  states="$(sacct -X -n -P -j "$baseline_job" --format=State%40)"
  test -n "$states"
  printf '%s\n' "$states" > "$SCIP_MEMORY_ROOT/baseline-${baseline_job}-states.txt"
  if printf '%s\n' "$states" | grep -Eq 'PENDING|RUNNING|CONFIGURING|COMPLETING|SUSPENDED|REQUEUED|RESIZING|SIGNALING|STAGE_OUT'; then
    dependencies+=("$baseline_job")
  elif printf '%s\n' "$states" | grep -Evq '^[[:space:]]*(COMPLETED|FAILED|CANCELLED[^|]*|TIMEOUT|OUT_OF_MEMORY|NODE_FAIL|PREEMPTED|BOOT_FAIL|DEADLINE|REVOKED)\|?[[:space:]]*$'; then
    printf 'Unrecognized baseline state; no submission: %s\n' "$states" >&2
    exit 1
  fi
done
options=(--account=sxdsouza --partition=intel-512 --nodes=1 --ntasks=1
  --cpus-per-task=4 --exclusive --mem=0 --time=12:00:00 --array=0-3%2
  --job-name=scip-memory --export=ALL --chdir="$SCIP_MEMORY_CHECKOUT"
  --output="$SCIP_MEMORY_ROOT/slurm-%A_%a.out")
if [ "${#dependencies[@]}" -gt 0 ]; then
  dependency_text="$(IFS=:; printf '%s' "${dependencies[*]}")"
  options+=("--dependency=afterany:$dependency_text" --kill-on-invalid-dep=yes)
fi
unset SBATCH_QOS
WORKER="$SCIP_MEMORY_CHECKOUT/scripts/run_scip_memory_campaign.slurm"
sbatch --test-only "${options[@]}" "$WORKER"
mkdir "$SCIP_MEMORY_ROOT/.submission-claimed"
job="$(sbatch --parsable "${options[@]}" "$WORKER")"
printf 'MEMORY_JOB=%s\n' "$job" | tee "$SCIP_MEMORY_ROOT/submission.txt"
printf 'Campaign: %s\n' "$SCIP_MEMORY_ROOT"
