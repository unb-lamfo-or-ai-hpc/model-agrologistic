#!/bin/bash
# Small analytical/parity tests only; no population campaign is submitted.
#SBATCH --job-name=scip-pr31-check
#SBATCH --partition=intel-256
#SBATCH --qos=qos1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:20:00
set -euo pipefail
: "${SCIP_CHECKOUT:?Set the isolated PR31 checkout}"
: "${SCIP_PYTHON:?Set the isolated SCIP Python executable}"
: "${SCIP_REPORT_DIR:?Set a new output directory}"
: "${SCIP_SOURCE_COMMIT:?Set the verified checkout SHA before submission}"
cd "$SCIP_CHECKOUT"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
printf 'job=%s host=%s source=%s\n' "$SLURM_JOB_ID" "$(hostname)" "$SCIP_SOURCE_COMMIT"
"$SCIP_PYTHON" scripts/qualify_scip_backend.py --output-dir "$SCIP_REPORT_DIR"
