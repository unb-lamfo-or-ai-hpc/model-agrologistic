#!/bin/bash
# New worktree and outputs only; never mutate or cancel baseline jobs.
set -euo pipefail
: "${SCIP_MEMORY_CHECKOUT:?Set the new detached checkout}"
: "${SCIP_MEMORY_ROOT:?Set the new campaign root}"
: "${SCIP_MEMORY_SOURCE:?Set its exact commit}"
: "${SCIP_PYTHON:?Set the read-only qualified Python}"
: "${SLURM_ARRAY_TASK_ID:?Submit the reviewed two-case 300-hub array}"
case "$SLURM_ARRAY_TASK_ID" in 0|1) ;; *) false ;; esac
test "${SLURM_JOB_NUM_NODES:-0}" -eq 1
test "${SLURM_CPUS_PER_TASK:-0}" -ge 4
cd "$SCIP_MEMORY_CHECKOUT"
test "$(git rev-parse HEAD)" = "$SCIP_MEMORY_SOURCE"
test -z "$(git status --porcelain --untracked-files=no)"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export AGROLOGISTIC_SOURCE_COMMIT="$SCIP_MEMORY_SOURCE"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
CASE_DIR="$SCIP_MEMORY_ROOT/case-$SLURM_ARRAY_TASK_ID"
PLAN="$SCIP_MEMORY_ROOT/memory_plan.json"
MANIFEST="$CASE_DIR/campaign.yaml"
"$SCIP_PYTHON" scripts/prepare_scip_memory_campaign.py --plan "$PLAN" --index "$SLURM_ARRAY_TASK_ID"
mkdir "$CASE_DIR/.execution-claimed"
scontrol show job "$SLURM_JOB_ID" > "$CASE_DIR/scheduler_job.txt"
scontrol show node "${SLURMD_NODENAME:?Missing compute node name}" -o > "$CASE_DIR/scheduler_node.txt"
"$SCIP_PYTHON" - "$CASE_DIR/scheduler_node.txt" <<'PY'
import os
import sys
from pathlib import Path
from scripts.prepare_scip_memory_campaign import validate_resources
validate_resources(Path(sys.argv[1]).read_text(), os.environ['SLURM_JOB_PARTITION'],
                   int(os.environ['SLURM_MEM_PER_NODE']))
print('SCIP FULL-NODE RESOURCE CONTRACT: ACCEPTED')
PY
printf 'job=%s index=%s source=%s host=%s requested_cpus=%s memory_mib=%s scip_limit_mb=393216\n' \
  "$SLURM_JOB_ID" "$SLURM_ARRAY_TASK_ID" "$SCIP_MEMORY_SOURCE" \
  "$(hostname)" "$SLURM_CPUS_PER_TASK" "$SLURM_MEM_PER_NODE"
"$SCIP_PYTHON" scripts/run_batch_hpc.py "$MANIFEST" --index 0 --dry-run
"$SCIP_PYTHON" scripts/prepare_scip_memory_campaign.py \
  --plan "$PLAN" --index "$SLURM_ARRAY_TASK_ID" --preflight
solve_rc=0
"$SCIP_PYTHON" scripts/run_batch_hpc.py "$MANIFEST" --index 0 || solve_rc=$?
audit_rc=0
"$SCIP_PYTHON" scripts/audit_nine_campaign.py "$MANIFEST" \
  --indices 0 --output-dir "$CASE_DIR/audit" || audit_rc=$?
printf 'solve_exit_code=%s audit_exit_code=%s\n' "$solve_rc" "$audit_rc"
test "$solve_rc" -eq 0
test "$audit_rc" -eq 0
