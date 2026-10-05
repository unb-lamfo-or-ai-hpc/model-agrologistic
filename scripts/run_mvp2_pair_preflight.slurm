#!/bin/bash
# Input inspection only; no Git or memory environment dependency on compute nodes.
set -euo pipefail
: "${MVP2_PAIR_CHECKOUT:?Set the new immutable checkout}"
: "${MVP2_PAIR_PLAN:?Set the preserved prepared plan}"
: "${MVP2_PAIR_AUDIT:?Set the new empty audit parent}"
: "${MVP2_PAIR_SOURCE:?Set source commit on the login node}"
: "${MVP2_PAIR_TOOLS:?Set submitted tool hashes}"
MVP2_PAIR_PYTHON="${MVP2_PAIR_PYTHON:-/home/vrrcelestino/venv313/bin/python}"
phase=worker_setup
write_worker_status() {
  local worker_exit=$?
  trap - EXIT
  set +e
  "$MVP2_PAIR_PYTHON" - "$MVP2_PAIR_AUDIT/worker_status.json" \
    "$worker_exit" "$phase" "${SLURM_JOB_ID:-unknown}" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

path, exit_code, phase, job = sys.argv[1:]
record = {
    "schema_version": "mvp2-input-worker-status-v1",
    "status": "completed" if exit_code == "0" else "failed",
    "exit_code": int(exit_code), "phase": phase, "job_id": job,
    "created_at_utc": datetime.now(UTC).isoformat(),
    "optimization_executed": False,
}
with Path(path).open("x", encoding="utf-8") as stream:
    stream.write(json.dumps(record, indent=2) + "\n")
PY
  local status_exit=$?
  if [ "$worker_exit" -eq 0 ] && [ "$status_exit" -ne 0 ]; then
    worker_exit=$status_exit
  fi
  exit "$worker_exit"
}
trap write_worker_status EXIT
cd "$MVP2_PAIR_CHECKOUT"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export AGROLOGISTIC_SOURCE_COMMIT="$MVP2_PAIR_SOURCE"
unset SCIPOPTDIR
phase=scheduler_capture
mkdir "$MVP2_PAIR_AUDIT/scheduler"
scontrol show job "$SLURM_JOB_ID" -o > "$MVP2_PAIR_AUDIT/scheduler/job.txt"
scontrol show node "${SLURMD_NODENAME:?}" -o > "$MVP2_PAIR_AUDIT/scheduler/node.txt"
phase=python_preflight
"$MVP2_PAIR_PYTHON" scripts/preflight_mvp2_resource_pair.py \
  --plan "$MVP2_PAIR_PLAN" --output-dir "$MVP2_PAIR_AUDIT/preflight" \
  --job-file "$MVP2_PAIR_AUDIT/scheduler/job.txt" \
  --node-file "$MVP2_PAIR_AUDIT/scheduler/node.txt" \
  --job-id "$SLURM_JOB_ID" --node-name "$SLURMD_NODENAME" --tools "$MVP2_PAIR_TOOLS"
phase=complete
