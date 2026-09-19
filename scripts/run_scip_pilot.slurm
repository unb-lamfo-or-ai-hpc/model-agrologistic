#!/bin/bash
# One admitted pilot only. Account-default QoS; no automatic population expansion.
#SBATCH --job-name=scip-h215-pilot
#SBATCH --partition=intel-256
#SBATCH --cpus-per-task=4
#SBATCH --mem=192G
#SBATCH --time=12:00:00
set -euo pipefail
: "${SCIP_CHECKOUT:?Set the isolated checkout}"
: "${SCIP_PYTHON:?Set the isolated Python}"
: "${SCIP_MANIFEST:?Set the newly admitted campaign manifest}"
: "${SCIP_SOURCE_COMMIT:?Set the exact source commit}"
test "$SLURM_CPUS_PER_TASK" = 4
test "${SLURM_MEM_PER_NODE:-0}" -ge 196608
cd "$SCIP_CHECKOUT"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
printf 'job=%s host=%s source=%s cpus=%s memory_mib=%s\n' \
  "$SLURM_JOB_ID" "$(hostname)" "$SCIP_SOURCE_COMMIT" \
  "$SLURM_CPUS_PER_TASK" "$SLURM_MEM_PER_NODE"
"$SCIP_PYTHON" scripts/prepare_scip_pilot.py --check-manifest "$SCIP_MANIFEST"
# Atomic claim prevents duplicate jobs from overwriting this pilot's evidence.
mkdir "$(dirname "$SCIP_MANIFEST")/.execution-claimed"
"$SCIP_PYTHON" scripts/run_batch_hpc.py "$SCIP_MANIFEST" --index 0 --dry-run
"$SCIP_PYTHON" scripts/prepare_scip_pilot.py --check-manifest "$SCIP_MANIFEST" --check-preflight
solve_rc=0
"$SCIP_PYTHON" scripts/run_batch_hpc.py "$SCIP_MANIFEST" --index 0 || solve_rc=$?
audit_rc=0
"$SCIP_PYTHON" scripts/audit_nine_campaign.py "$SCIP_MANIFEST" \
  --indices 0 --output-dir "$(dirname "$SCIP_MANIFEST")/audit" || audit_rc=$?
printf 'solve_exit_code=%s audit_exit_code=%s\n' "$solve_rc" "$audit_rc"
test "$solve_rc" -eq 0
test "$audit_rc" -eq 0
