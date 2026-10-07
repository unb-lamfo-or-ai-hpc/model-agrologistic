#!/usr/bin/env bash
# Fresh scheduler/cgroup/license gates before exactly one control process.
set -euo pipefail
: "${H400_CHECKOUT:?}" "${H400_PLAN:?}" "${H400_SOURCE:?}" "${H400_TOOLS:?}"
H400_PYTHON=${H400_PYTHON:-/home/vrrcelestino/venv313/bin/python}
H400_EXECUTION=$(dirname "$H400_PLAN")
phase=initialization
record_exit() {
  local rc=$?
  trap - EXIT
  set +e
  "$H400_PYTHON" - "$H400_EXECUTION" "${SLURM_JOB_ID:-}" "$H400_SOURCE" "$phase" "$rc" <<'PY'
import json
import sys
from pathlib import Path
root, job, source, phase, code = sys.argv[1:]
with (Path(root) / "worker_status.json").open("x", encoding="utf-8") as stream:
    json.dump({"schema_version": "mvp2-h400-control-worker-v1", "job_id": job,
               "source_commit": source, "phase": phase, "exit_code": int(code),
               "status": "completed" if code == "0" else "failed"}, stream, indent=2)
    stream.write("\n")
PY
  local status_rc=$?
  if [ "$rc" -eq 0 ] && [ "$status_rc" -ne 0 ]; then rc=$status_rc; fi
  exit "$rc"
}
trap record_exit EXIT
cd "$H400_CHECKOUT"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic
unset SCIPOPTDIR SLURM_ARRAY_TASK_ID SLURM_ARRAY_JOB_ID
phase=scheduler_capture
mkdir "$H400_EXECUTION/scheduler"
scontrol show job "$SLURM_JOB_ID" -o > "$H400_EXECUTION/scheduler/job.txt"
scontrol show node "${SLURMD_NODENAME:?}" -o > "$H400_EXECUTION/scheduler/node.txt"
phase=allocation_license_and_control
"$H400_PYTHON" scripts/mvp2_h400_control.py --plan "$H400_PLAN" \
  --job-file "$H400_EXECUTION/scheduler/job.txt" --node-file "$H400_EXECUTION/scheduler/node.txt" \
  --job-id "$SLURM_JOB_ID" --node-name "$SLURMD_NODENAME" \
  --tools "$H400_TOOLS" --source-commit "$H400_SOURCE"
phase=complete
