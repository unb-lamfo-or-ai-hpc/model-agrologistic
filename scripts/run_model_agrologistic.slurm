#!/bin/bash
#SBATCH --job-name=agrologistic-rp
#SBATCH --partition=intel-256
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=192G
#SBATCH --time=06:00:00
#SBATCH --output=slurm-%x-%j.out

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:?Submit this job from the repository root}"

environment_path="${AGROLOGISTIC_ENV:-/home/vrrcelestino/venv313}"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${environment_path}"

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export OPENBLAS_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK}"

experiment_index="${EXPERIMENT_INDEX:-1}"
log_dir="data/results/hpc/slurm_logs"
mkdir -p "${log_dir}"
run_log="${log_dir}/experiment-${experiment_index}-job-${SLURM_JOB_ID}.log"

echo "job_id=${SLURM_JOB_ID}"
echo "host=$(hostname)"
echo "experiment_index=${experiment_index}"
echo "cpus=${SLURM_CPUS_PER_TASK}"
echo "memory_per_node=${SLURM_MEM_PER_NODE:-unknown}MB"
echo "environment=${environment_path}"

/usr/bin/time -v \
  python scripts/run_batch_hpc.py \
    experiments/example_hpc.yaml \
    --index "${experiment_index}" \
  2>&1 | tee "${run_log}"
