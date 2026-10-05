#!/bin/bash
# Input inspection only; no Git or memory environment dependency on compute nodes.
set -euo pipefail
: "${MVP2_PAIR_CHECKOUT:?Set the new immutable checkout}"
: "${MVP2_PAIR_PLAN:?Set the preserved prepared plan}"
: "${MVP2_PAIR_AUDIT:?Set the new empty audit parent}"
: "${MVP2_PAIR_SOURCE:?Set source commit on the login node}"
: "${MVP2_PAIR_TOOLS:?Set submitted tool hashes}"
MVP2_PAIR_PYTHON="${MVP2_PAIR_PYTHON:-/home/vrrcelestino/venv313/bin/python}"
cd "$MVP2_PAIR_CHECKOUT"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export AGROLOGISTIC_SOURCE_COMMIT="$MVP2_PAIR_SOURCE"
unset SCIPOPTDIR
mkdir "$MVP2_PAIR_AUDIT/scheduler"
scontrol show job "$SLURM_JOB_ID" -o > "$MVP2_PAIR_AUDIT/scheduler/job.txt"
scontrol show node "${SLURMD_NODENAME:?}" -o > "$MVP2_PAIR_AUDIT/scheduler/node.txt"
"$MVP2_PAIR_PYTHON" scripts/preflight_mvp2_resource_pair.py \
  --plan "$MVP2_PAIR_PLAN" --output-dir "$MVP2_PAIR_AUDIT/preflight" \
  --job-file "$MVP2_PAIR_AUDIT/scheduler/job.txt" \
  --node-file "$MVP2_PAIR_AUDIT/scheduler/node.txt" \
  --job-id "$SLURM_JOB_ID" --node-name "$SLURMD_NODENAME" --tools "$MVP2_PAIR_TOOLS"
