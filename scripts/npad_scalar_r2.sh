#!/bin/bash
# Human-only, pinned R2 wrapper. Never installs packages or touches historical claims.
set -euo pipefail
WRAPPER=$(readlink -f -- "$0")
ACTION=${1:?Use start, status, wait or collect}
SOURCE_SHA=${2:?Require the complete reviewed source SHA}
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo 'Full SHA required' >&2; exit 2; }
case "$ACTION" in start|status|wait|collect) ;; *) echo 'Unsupported action' >&2; exit 2;; esac
BASE=${MVP2_R2_BASE:?Set the existing audit parent directory}
PY=${MVP2_R2_PYTHON:?Select the existing Python3.13 executable}
[[ "$BASE" = /* && -d "$BASE" && -x "$PY" ]] || { echo 'Base/Python invalid' >&2; exit 2; }
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
CLAIM="$BASE/.mvp2-scalar-r2-v1"
DRIVER=''
trap 'code=$?; printf "DRIVER_EXIT=%s\nPRESERVE_CLAIM=%s\nPRESERVE_BOOTSTRAP=%s\nNO_REPEAT_OR_LARGER_INSTANCE_ADMITTED\n" "$code" "$CLAIM" "$DRIVER"' EXIT
if [[ -d "$CLAIM" ]]; then
  # Pure stdlib precheck BEFORE importing preserved checkout code. No Git on compute.
  SRC=$("$PY" -B -I -c 'import hashlib,json,pathlib,sys; c=pathlib.Path(sys.argv[1]); p=json.loads((c/"plan.json").read_bytes()); raw=(c/"source.json").read_bytes(); i=json.loads(raw); assert hashlib.sha256(raw).hexdigest()==p["source_inventory_sha256"] and p["source_commit"]==sys.argv[2]==i["source_commit"]; r=pathlib.Path(p["source_root"]); assert r.is_relative_to(c.parent) and r.name=="source"; assert all(not (r/n).is_symlink() and hashlib.sha256((r/n).read_bytes()).hexdigest()==v for n,v in i["files"].items()); print(r)' "$CLAIM" "$SOURCE_SHA")
elif [[ "$ACTION" = start ]]; then
  DRIVER=$(mktemp -d "$BASE/scalar-r2-driver-XXXXXXXX")
  SRC="$DRIVER/source"
  printf 'PRESERVE_BOOTSTRAP=%s\n' "$DRIVER"
  git -c core.autocrlf=false clone --no-checkout https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$SRC"
  printf '%s\n' '/manuscript/comparison_provenance.json -text' '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
  git -C "$SRC" -c core.autocrlf=false checkout --detach "$SOURCE_SHA"
  [[ $(git -C "$SRC" rev-parse HEAD) = "$SOURCE_SHA" ]]
  "$PY" -B -I -c 'import sys; sys.path.insert(0,sys.argv[1]); from scripts.mvp2_scalar_r2 import source_inventory; i=source_inventory(); print("RAW_HEAD_BYTES="+str(len(i["files"]))+" identical; R2_SMALL_ONLY")' "$SRC"
  cd "$SRC"
  "$PY" -B -I -c 'import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("pytest",run_name="__main__",alter_sys=True)' "$SRC" tests/test_scalar_r2.py -q -p no:cacheprovider --basetemp="$DRIVER/regression-tmp" --junitxml="$DRIVER/regression.xml"
  "$PY" -B -I -c 'import sys,xml.etree.ElementTree as e; r=e.parse(sys.argv[1]).getroot(); s=list(r.iter("testsuite")); assert s and sum(int(x.get("tests",0)) for x in s)>0 and all(int(x.get(k,0))==0 for x in s for k in ("errors","failures","skipped")); print("R2_LOGIN_REGRESSION=VERIFIED; NO_SOLVER_OR_JOB_IN_REGRESSION")' "$DRIVER/regression.xml"
else
  echo 'R2 claim absent: no job to observe/collect; no automatic start.' >&2
  exit 2
fi
cd "$SRC"
ARGS=("$ACTION" --claim "$CLAIM" --source-sha "$SOURCE_SHA")
if [[ "$ACTION" = start ]]; then ARGS+=(--one-reviewed-r2-only); fi
"$PY" -B -I -c 'import runpy,sys; sys.dont_write_bytecode=True; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("scripts.mvp2_scalar_r2",run_name="__main__",alter_sys=True)' "$SRC" "${ARGS[@]}"
printf 'STATUS_COMMAND=MVP2_R2_BASE=%q MVP2_R2_PYTHON=%q bash %q status %s\n' "$BASE" "$PY" "$WRAPPER" "$SOURCE_SHA"
printf 'WAIT_COMMAND=MVP2_R2_BASE=%q MVP2_R2_PYTHON=%q bash %q wait %s\n' "$BASE" "$PY" "$WRAPPER" "$SOURCE_SHA"
printf 'COLLECT_COMMAND=MVP2_R2_BASE=%q MVP2_R2_PYTHON=%q bash %q collect %s\n' "$BASE" "$PY" "$WRAPPER" "$SOURCE_SHA"
