#!/usr/bin/env bash
# No Git/network on compute; only licensed analytical miniatures are executable.
set -euo pipefail
: "${S2_CHECKOUT:?}" "${S2_OUTPUT:?}" "${S2_PYTHON:?}"
cd "$S2_CHECKOUT"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic
unset SCIPOPTDIR SLURM_ARRAY_TASK_ID SLURM_ARRAY_JOB_ID
mkdir "$S2_OUTPUT/scheduler"
scontrol show job "$SLURM_JOB_ID" -o > "$S2_OUTPUT/scheduler/job.txt"
scontrol show node "${SLURMD_NODENAME:?}" -o > "$S2_OUTPUT/scheduler/node.txt"
"$S2_PYTHON" scripts/mvp2_threads.py execute --output "$S2_OUTPUT" \
  --job "$SLURM_JOB_ID" --node "$SLURMD_NODENAME"
