#!/bin/bash
# Resources and array indices are supplied by the versioned submission helper.
# No explicit QoS; no writes to the original 215-hub pilot checkout or campaign.
set -euo pipefail
: "${SCIP_EXPANSION_CHECKOUT:?Set the new isolated checkout}"
: "${SCIP_PYTHON:?Set the read-only qualified Python environment}"
: "${SCIP_EXPANSION_ROOT:?Set the fresh campaign root}"
: "${SCIP_EXPANSION_SOURCE:?Set the exact checkout commit}"
: "${SCIP_PHASE:?Select preflight or solve}"
: "${SLURM_ARRAY_TASK_ID:?Submit through the bounded array helper}"
case "$SLURM_ARRAY_TASK_ID" in 0|1|2|3|4) ;; *) false ;; esac
case "$SCIP_PHASE" in preflight|solve) ;; *) false ;; esac
test "$SLURM_CPUS_PER_TASK" = 4
if [ "$SCIP_PHASE" = solve ]; then
  test "${SLURM_MEM_PER_NODE:-0}" -ge 196608
else
  test "${SLURM_MEM_PER_NODE:-0}" -ge 16384
fi
cd "$SCIP_EXPANSION_CHECKOUT"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export AGROLOGISTIC_SOURCE_COMMIT="$SCIP_EXPANSION_SOURCE"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
PLAN="$SCIP_EXPANSION_ROOT/expansion_plan.json"
CASE_DIR="$SCIP_EXPANSION_ROOT/case-$SLURM_ARRAY_TASK_ID"
MANIFEST="$CASE_DIR/campaign.yaml"
printf 'job=%s index=%s phase=%s source=%s host=%s memory_mib=%s\n' \
  "$SLURM_JOB_ID" "$SLURM_ARRAY_TASK_ID" "$SCIP_PHASE" "$SCIP_EXPANSION_SOURCE" \
  "$(hostname)" "$SLURM_MEM_PER_NODE"
"$SCIP_PYTHON" scripts/prepare_scip_expansion.py --plan "$PLAN" \
  --index "$SLURM_ARRAY_TASK_ID" --phase "$SCIP_PHASE"
mkdir "$CASE_DIR/.$SCIP_PHASE-claimed"
if [ "$SCIP_PHASE" = preflight ]; then
  "$SCIP_PYTHON" scripts/run_batch_hpc.py "$MANIFEST" --index 0 --dry-run
  "$SCIP_PYTHON" scripts/prepare_scip_expansion.py --plan "$PLAN" \
    --index "$SLURM_ARRAY_TASK_ID" --record-preflight
else
  "$SCIP_PYTHON" scripts/prepare_scip_expansion.py --plan "$PLAN" \
    --index "$SLURM_ARRAY_TASK_ID" --phase solve --check-preflight
  solve_rc=0
  "$SCIP_PYTHON" scripts/run_batch_hpc.py "$MANIFEST" --index 0 || solve_rc=$?
  audit_rc=0
  "$SCIP_PYTHON" scripts/audit_nine_campaign.py "$MANIFEST" \
    --indices 0 --output-dir "$CASE_DIR/audit" || audit_rc=$?
  printf 'solve_exit_code=%s audit_exit_code=%s\n' "$solve_rc" "$audit_rc"
  test "$solve_rc" -eq 0
  test "$audit_rc" -eq 0
fi
