#!/usr/bin/env bash
# Input inspection only: no native model construction, license probe or optimization.
set -euo pipefail
: "${H400_INPUT_CHECKOUT:?}" "${H400_INPUT_PLAN:?}" "${H400_INPUT_AUDIT:?}" "${H400_INPUT_SOURCE:?}"
H400_INPUT_PYTHON=${H400_INPUT_PYTHON:-/home/vrrcelestino/venv313/bin/python}
phase=worker_setup
write_status() {
  local worker_exit=$?
  trap - EXIT
  set +e
  "$H400_INPUT_PYTHON" - "$H400_INPUT_AUDIT/worker_status.json" "$worker_exit" \
    "$phase" "${SLURM_JOB_ID:-unknown}" "$H400_INPUT_SOURCE" <<'PY'
import json
import sys
from pathlib import Path
path, code, phase, job, source = sys.argv[1:]
record = {"schema_version": "mvp2-h400-input-worker-v1", "job_id": job,
          "source_commit": source, "status": "completed" if code == "0" else "failed",
          "exit_code": int(code), "phase": phase, "optimization_executed": False}
with Path(path).open("x") as stream:
    stream.write(json.dumps(record, indent=2) + "\n")
PY
  local status_exit=$?
  if [ "$worker_exit" -eq 0 ] && [ "$status_exit" -ne 0 ]; then worker_exit=$status_exit; fi
  exit "$worker_exit"
}
trap write_status EXIT
cd "$H400_INPUT_CHECKOUT"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export AGROLOGISTIC_SOURCE_COMMIT="$H400_INPUT_SOURCE"
unset SCIPOPTDIR
phase=scheduler_capture
mkdir "$H400_INPUT_AUDIT/scheduler"
scontrol show job "$SLURM_JOB_ID" -o > "$H400_INPUT_AUDIT/scheduler/job.txt"
scontrol show node "${SLURMD_NODENAME:?}" -o > "$H400_INPUT_AUDIT/scheduler/node.txt"
phase=python_preflight
"$H400_INPUT_PYTHON" scripts/mvp2_h400_input.py inspect --plan "$H400_INPUT_PLAN" \
  --output-dir "$H400_INPUT_AUDIT/preflight" --source "$H400_INPUT_SOURCE" \
  --job-file "$H400_INPUT_AUDIT/scheduler/job.txt" --node-file "$H400_INPUT_AUDIT/scheduler/node.txt" \
  --job-id "$SLURM_JOB_ID" --node-name "$SLURMD_NODENAME"
phase=complete
