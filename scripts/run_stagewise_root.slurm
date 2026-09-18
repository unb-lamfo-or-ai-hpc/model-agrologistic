#!/bin/bash
#SBATCH --job-name=stagewise-root
#SBATCH --partition=intel-256
#SBATCH --qos=preempt
#SBATCH --cpus-per-task=4
#SBATCH --mem=192G
#SBATCH --time=12:00:00
#SBATCH --output=slurm-stagewise-root-%j.out

# Sprint A: one all-barrier case only; process completion is not acceptance.
set -euo pipefail
PROJECT_ROOT="${PROJECT_ROOT:-/home/vrrcelestino/model-agrologistic}"
PYTHON="${PYTHON:-/home/vrrcelestino/venv313/bin/python}"
: "${STAGEWISE_MANIFEST:?Set the absolute freshly prepared campaign manifest}"
: "${STAGEWISE_SOURCE_COMMIT:?Set the tested source commit before submission}"
cd "$PROJECT_ROOT"
# The Python contract checks source hashes; Git may be absent on compute nodes.
test "$SLURM_CPUS_PER_TASK" = 4
test "${SLURM_MEM_PER_NODE:-0}" -ge 196608
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE="$PROJECT_ROOT/secrets/gurobi.lic"
printf 'job=%s partition=%s cpus=%s memory_mib=%s\n' \
  "$SLURM_JOB_ID" "$SLURM_JOB_PARTITION" "$SLURM_CPUS_PER_TASK" "${SLURM_MEM_PER_NODE:-unknown}"
printf 'source_commit=%s\n' "$STAGEWISE_SOURCE_COMMIT"
"$PYTHON" scripts/prepare_stagewise_campaign.py --check-manifest "$STAGEWISE_MANIFEST" \
  --require-profile all-barrier
"$PYTHON" scripts/run_batch_hpc.py "$STAGEWISE_MANIFEST" --index 0 --dry-run
"$PYTHON" scripts/run_batch_hpc.py "$STAGEWISE_MANIFEST" --index 0
"$PYTHON" scripts/audit_nine_campaign.py "$STAGEWISE_MANIFEST" \
  --indices 0 --output-dir "$(dirname "$STAGEWISE_MANIFEST")/audit"
