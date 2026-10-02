#!/bin/bash
#SBATCH --job-name=pr25-memory-retry
#SBATCH --partition=intel-256
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=192G
#SBATCH --time=06:00:00
#SBATCH --output=slurm-pr25-memory-retry-%j.out

# Batch-only launcher: never source this file into an interactive terminal.
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Submit from the model-agrologistic repository root}"
ulimit -v unlimited
ulimit -t unlimited
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE="${GRB_LICENSE_FILE:-$PWD/secrets/gurobi.lic}"
export OMP_NUM_THREADS=16
export OPENBLAS_NUM_THREADS=16
export MKL_NUM_THREADS=16
pr25_python="${AGROLOGISTIC_PYTHON:-/home/vrrcelestino/venv313/bin/python}"
test -x "$pr25_python"
test -r "$GRB_LICENSE_FILE"
printf 'job_id=%s partition=%s host=%s memory_mib=%s cpus=%s\n' \
  "$SLURM_JOB_ID" "$SLURM_JOB_PARTITION" "$(hostname)" \
  "${SLURM_MEM_PER_NODE:-unset}" "${SLURM_CPUS_PER_TASK:-unset}"
exec "$pr25_python" scripts/run_pr25_nine_scenario_retry.py --memory-retry --index 0
