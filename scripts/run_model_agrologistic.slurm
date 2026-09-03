#!/bin/bash
#SBATCH --job-name=agrologistic-rp
#SBATCH --partition=intel-128
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --output=slurm-%x-%j.out

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:?Submit this job from the repository root}"

environment_path="${AGROLOGISTIC_ENV:-/home/vrrcelestino/venv313}"
python_executable="${AGROLOGISTIC_PYTHON:-${environment_path}/bin/python}"

if [[ ! -x "${python_executable}" ]]; then
  echo "Python executable not found: ${python_executable}" >&2
  exit 2
fi

if ! ulimit -v unlimited; then
  echo "Warning: could not remove the inherited virtual-memory limit" >&2
fi
if ! ulimit -t unlimited; then
  echo "Warning: could not remove the inherited CPU-time limit" >&2
fi

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export OPENBLAS_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK}"

experiment_manifest="${EXPERIMENT_MANIFEST:-experiments/example_hpc.yaml}"
experiment_index="${EXPERIMENT_INDEX:-${SLURM_ARRAY_TASK_ID:-1}}"
log_dir="data/results/hpc/slurm_logs"
mkdir -p "${log_dir}"
run_log="${log_dir}/experiment-${experiment_index}-job-${SLURM_JOB_ID}.log"

echo "job_id=${SLURM_JOB_ID}"
echo "host=$(hostname)"
echo "experiment_manifest=${experiment_manifest}"
echo "experiment_index=${experiment_index}"
echo "cpus=${SLURM_CPUS_PER_TASK}"
echo "memory_per_node=${SLURM_MEM_PER_NODE:-unknown}MB"
echo "virtual_memory_limit_kb=$(ulimit -v)"
echo "cpu_time_limit_seconds=$(ulimit -t)"
echo "python=${python_executable}"
"${python_executable}" --version

"${python_executable}" scripts/run_batch_hpc.py \
  "${experiment_manifest}" \
  --index "${experiment_index}" \
  2>&1 | tee "${run_log}"
