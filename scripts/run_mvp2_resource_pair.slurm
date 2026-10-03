#!/bin/bash
# One serial pair, fresh process per arm. Git is not needed on compute nodes.
set -euo pipefail
: "${MVP2_SOLVE_CHECKOUT:?Set the immutable checkout}"
: "${MVP2_SOLVE_PLAN:?Set the new solve plan}"
: "${MVP2_SOLVE_SOURCE:?Set the pinned login-node source}"
: "${MVP2_SOLVE_TOOLS:?Set submitted tool hashes}"
MVP2_SOLVE_PYTHON="${MVP2_SOLVE_PYTHON:-/home/vrrcelestino/venv313/bin/python}"
cd "$MVP2_SOLVE_CHECKOUT"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic
unset SCIPOPTDIR
MVP2_SOLVE_DIRECTORY="$(dirname "$MVP2_SOLVE_PLAN")"
mkdir "$MVP2_SOLVE_DIRECTORY/scheduler"
scontrol show job "$SLURM_JOB_ID" -o > "$MVP2_SOLVE_DIRECTORY/scheduler/job.txt"
scontrol show node "${SLURMD_NODENAME:?}" -o > "$MVP2_SOLVE_DIRECTORY/scheduler/node.txt"
"$MVP2_SOLVE_PYTHON" scripts/admit_mvp2_resource_pair.py \
  --solve-plan "$MVP2_SOLVE_PLAN" \
  --job-file "$MVP2_SOLVE_DIRECTORY/scheduler/job.txt" \
  --node-file "$MVP2_SOLVE_DIRECTORY/scheduler/node.txt" \
  --job-id "$SLURM_JOB_ID" --node-name "$SLURMD_NODENAME" \
  --tools "$MVP2_SOLVE_TOOLS" --source-commit "$MVP2_SOLVE_SOURCE"
