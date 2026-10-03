#!/bin/bash
# Small qualification only. Submission captures source and exact allocation.
set -euo pipefail
: "${MVP2_CHECKOUT:?Set immutable checkout}"
: "${MVP2_REPORT:?Set new report directory}"
: "${MVP2_SOURCE:?Set exact source commit}"
: "${MVP2_IDENTITY:?Set implementation SHA256}"
MVP2_PYTHON="${MVP2_PYTHON:-/home/vrrcelestino/venv313/bin/python}"
cd "$MVP2_CHECKOUT"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export AGROLOGISTIC_SOURCE_COMMIT="$MVP2_SOURCE"
unset SCIPOPTDIR
mkdir "$MVP2_REPORT/scheduler"
scontrol show job "$SLURM_JOB_ID" > "$MVP2_REPORT/scheduler/job.txt"
scontrol show node "${SLURMD_NODENAME:?}" -o > "$MVP2_REPORT/scheduler/node.txt"
"$MVP2_PYTHON" -c 'import os; from src.logic.run_integrity import implementation_identity; assert implementation_identity()["sha256"] == os.environ["MVP2_IDENTITY"], "Source/runtime changed after submission"'
# No Git or SLURM_MEM_PER_NODE dependency exists on a compute node.
"$MVP2_PYTHON" scripts/qualify_mvp2_resources.py --output-dir "$MVP2_REPORT/qualification"
