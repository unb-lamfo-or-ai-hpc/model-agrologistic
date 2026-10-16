#!/usr/bin/env bash
# Closed P4 wrapper. No download, claim creation, sbatch, solver or retry path.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
ACTION=${1:-check}
case "$ACTION" in
  start|batch|worker)
    printf '%s\n' 'H300_AND_REPEATS_BLOCKED; no execution admitted by this release' >&2
    exit 2
    ;;
  check|status|collect|wait) ;;
  *) printf '%s\n' 'Usage: wrapper check|status|collect|wait; execution remains closed' >&2; exit 2 ;;
esac
shift || true
P4_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
P4_PYTHON=${MVP2_P4_PYTHON:-/home/vrrcelestino/venv313/bin/python}
exec "$P4_PYTHON" -B -I -c 'import runpy,sys; sys.dont_write_bytecode=True; root=sys.argv.pop(1); sys.path.insert(0,root); runpy.run_module("scripts.mvp2_s2_h300_runtime",run_name="__main__",alter_sys=True)' "$P4_ROOT" "$ACTION" "$@"
