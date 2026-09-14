#!/bin/bash
#SBATCH --job-name=nine-connect
#SBATCH --partition=intel-256
#SBATCH --cpus-per-task=4
#SBATCH --mem=192G
#SBATCH --time=05:00:00
#SBATCH --output=slurm-nine-connect-%A_%a.out

# Each array task owns one result directory. Preflight is mandatory before solving.
set -euo pipefail
PROJECT_ROOT="${PROJECT_ROOT:-/home/vrrcelestino/model-agrologistic}"
PYTHON="${PYTHON:-/home/vrrcelestino/venv313/bin/python}"
: "${NINE_MANIFEST:?Set NINE_MANIFEST to the generated absolute campaign.yaml path}"
: "${SLURM_ARRAY_TASK_ID:?Submit an explicitly bounded array}"
cd "$PROJECT_ROOT"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE="$PROJECT_ROOT/secrets/gurobi.lic"
printf 'job=%s index=%s partition=%s cpus=%s memory_mib=%s\n' \
  "$SLURM_JOB_ID" "$SLURM_ARRAY_TASK_ID" "$SLURM_JOB_PARTITION" \
  "$SLURM_CPUS_PER_TASK" "${SLURM_MEM_PER_NODE:-unknown}"
"$PYTHON" scripts/run_batch_hpc.py "$NINE_MANIFEST" \
  --index "$SLURM_ARRAY_TASK_ID" --dry-run
"$PYTHON" scripts/run_batch_hpc.py "$NINE_MANIFEST" \
  --index "$SLURM_ARRAY_TASK_ID"
