#!/usr/bin/env bash
# Record scheduler/cgroup gates before the single control optimization.
set -euo pipefail
: "${H300_CHECKOUT:?}"
: "${H300_PLAN:?}"
: "${H300_SOURCE:?}"
: "${H300_TOOLS:?}"
H300_PYTHON=${H300_PYTHON:-/home/vrrcelestino/venv313/bin/python}
H300_EXECUTION=$(dirname "$H300_PLAN")
H300_PHASE=initialization
record_exit() {
  local rc=$?
  trap - EXIT
  "$H300_PYTHON" - "$H300_EXECUTION" "${SLURM_JOB_ID:-}" "$H300_PHASE" "$rc" <<'PY'
import json
import sys
from pathlib import Path
root, job, phase, rc = sys.argv[1:]
with (Path(root) / "worker_status.json").open("x", encoding="utf-8") as stream:
    json.dump({"schema_version": "mvp2-h300-worker-v1", "job_id": job,
               "phase": phase, "exit_code": int(rc),
               "status": "completed" if int(rc) == 0 else "failed"}, stream, indent=2)
    stream.write("\n")
PY
  exit "$rc"
}
trap record_exit EXIT
cd "$H300_CHECKOUT"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic
unset SCIPOPTDIR SLURM_ARRAY_TASK_ID SLURM_ARRAY_JOB_ID
H300_PHASE=scheduler_capture
mkdir "$H300_EXECUTION/scheduler"
scontrol show job "$SLURM_JOB_ID" -o > "$H300_EXECUTION/scheduler/job.txt"
scontrol show node "${SLURMD_NODENAME:?}" -o > "$H300_EXECUTION/scheduler/node.txt"
H300_PHASE=allocation_license_and_baseline
"$H300_PYTHON" scripts/mvp2_h300_baseline.py --plan "$H300_PLAN" \
  --job-file "$H300_EXECUTION/scheduler/job.txt" --node-file "$H300_EXECUTION/scheduler/node.txt" \
  --job-id "$SLURM_JOB_ID" --node-name "$SLURMD_NODENAME" \
  --tools "$H300_TOOLS" --source-commit "$H300_SOURCE"
H300_PHASE=complete
