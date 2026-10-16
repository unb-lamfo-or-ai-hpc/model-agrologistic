#!/usr/bin/env bash
# Observation preparation/collection only. Never submits a job or starts h300.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
ACTION=${1:-check}
case "$ACTION" in
  start|batch|worker|solve|repeat)
    printf '%s\n' 'H300_AND_REPEATS_BLOCKED; no execution admitted' >&2
    exit 2 ;;
  check|prepare|observe|collect|wait|audit) ;;
  *) printf '%s\n' 'Unknown admission action; no job submitted' >&2; exit 2 ;;
esac
shift || true
ADMISSION_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
ADMISSION_PYTHON=${MVP2_P4_PYTHON:-/home/vrrcelestino/venv313/bin/python}
exec "$ADMISSION_PYTHON" -B -I -c 'import runpy,sys; sys.dont_write_bytecode=True; root=sys.argv.pop(1); sys.path.insert(0,root); runpy.run_module("scripts.mvp2_s2_p4_admission",run_name="__main__",alter_sys=True)' "$ADMISSION_ROOT" "$ACTION" "$@"
