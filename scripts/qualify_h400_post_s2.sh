#!/usr/bin/env bash
# Local software/proposal wrapper only. No NPAD submission, claim or solver.
set -euo pipefail
case "${1:-}" in
  describe|prepare|check|pack|audit) ;;
  *) printf '%s\n' 'CLOSED: only describe/prepare/check/pack/audit; no job or repeat.' >&2; exit 2 ;;
esac
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
PY=${H400_QUALIFICATION_PYTHON:-python}
exec "$PY" -B -I -c 'import runpy,sys;sys.dont_write_bytecode=True;r=sys.argv.pop(1);sys.path.insert(0,r);runpy.run_module("scripts.mvp2_h400_post_s2",run_name="__main__",alter_sys=True)' "$ROOT" "$@"
