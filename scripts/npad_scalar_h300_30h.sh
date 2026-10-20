#!/bin/bash
# Human-only one-block operational wrapper. No installs, resampling or retries.
set -euo pipefail
WRAPPER=$(readlink -f -- "$0")
ACTION=${1:?Use start/status/wait/collect/budget/audit}
SOURCE_SHA=${2:?Require the full reviewed source SHA}
case "$ACTION" in
  start|status|wait|collect|budget|audit) ;;
  *) echo 'Unsupported action; repeats/larger populations remain closed' >&2; exit 2;;
esac
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo 'Full SHA required' >&2; exit 2; }
BASE=${MVP2_H300_BASE:-/home/vrrcelestino/model-agrologistic-hygiene-audit}
PY=${MVP2_H300_PYTHON:-/home/vrrcelestino/venv313/bin/python}
[[ "$BASE" = /* && -d "$BASE" && -x "$PY" && -z ${SLURM_JOB_ID:-} ]] || {
  echo 'Existing audit base/Python and login context required' >&2; exit 2;
}
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
CLAIM="$BASE/.mvp2-scalar-h300-30h-v1"
DRIVER=''
trap 'code=$?; printf "DRIVER_EXIT=%s\nPRESERVE_CLAIM=%s\nPRESERVE_BOOTSTRAP=%s\nNO_REPEAT_LARGER_INSTANCE_OR_AUTOMATIC_FOLLOW_ON_ADMITTED\n" "$code" "$CLAIM" "$DRIVER"' EXIT
if [[ -d "$CLAIM" ]]; then
  SRC=$("$PY" -B -I -c 'import hashlib,json,pathlib,sys; c=pathlib.Path(sys.argv[1]); p=json.loads((c/"plan.json").read_bytes()); raw=(c/"source.json").read_bytes(); i=json.loads(raw); assert hashlib.sha256(raw).hexdigest()==p["source_inventory_sha256"] and p["source_commit"]==sys.argv[2]==i["source_commit"]; n=pathlib.Path(p["source_root"]); assert n.is_relative_to(c.parent) and n.name=="source" and n.parent.name.startswith("scalar-h300-30h-driver-") and all((n/k).is_file() and not (n/k).is_symlink() and hashlib.sha256((n/k).read_bytes()).hexdigest()==v for k,v in i["files"].items()); print(n)' "$CLAIM" "$SOURCE_SHA")
  if [[ "$ACTION" = start ]]; then
    echo 'Existing consumed claim: collect only; no second submission'
    ACTION=collect
  fi
else
  case "$ACTION" in status|wait|collect) echo 'Claim absent; no job/collection exists' >&2; exit 2;; esac
  DRIVER=$(mktemp -d "$BASE/scalar-h300-30h-driver-XXXXXXXX")
  SRC="$DRIVER/source"
  printf 'PRESERVE_BOOTSTRAP=%s\n' "$DRIVER"
  git -c core.autocrlf=false clone --no-checkout https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$SRC"
  printf '%s\n' '/manuscript/comparison_provenance.json -text' '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
  git -C "$SRC" -c core.autocrlf=false checkout --detach "$SOURCE_SHA"
fi
cd "$SRC"
"$PY" -B -I -c 'import sys; assert sys.version_info[:2]==(3,13); sys.path.insert(0,sys.argv[1]); from scripts.mvp2_scalar_r2 import source_inventory,verify_source; i=source_inventory(); assert i["source_commit"]==sys.argv[2]; verify_source(i); print("RAW_HEAD_BYTES="+str(len(i["files"]))+" identical; ONE_H300_30H_BLOCK_ONLY")' "$SRC" "$SOURCE_SHA"
if [[ "$ACTION" = start ]]; then
  "$PY" -B -I -c 'import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("ruff",run_name="__main__")' "$SRC" check .
  "$PY" -B -I -c 'import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("pytest",run_name="__main__")' "$SRC" -q -p no:cacheprovider tests/test_scalar_h300.py tests/test_scalar_h300_operational.py --basetemp "$DRIVER/tests" --junitxml "$DRIVER/regression.xml"
  "$PY" -B -I -c 'import sys,xml.etree.ElementTree as e; s=list(e.parse(sys.argv[1]).getroot().iter("testsuite")); assert s and sum(int(x.get("tests",0)) for x in s)>0 and all(int(x.get(k,0))==0 for x in s for k in ("failures","errors","skipped")); print("H300_OPERATIONAL_LOGIN_REGRESSION=VERIFIED; NO_SOLVER_OR_JOB_IN_REGRESSION")' "$DRIVER/regression.xml"
  "$PY" -B -I -c 'import sys; sys.path.insert(0,sys.argv[1]); from scripts.mvp2_scalar_r2 import source_inventory,verify_source; i=source_inventory(); assert i["source_commit"]==sys.argv[2]; verify_source(i); print("POST_REGRESSION_RAW_SOURCE=VERIFIED")' "$SRC" "$SOURCE_SHA"
  export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic
fi
ARGS=("$ACTION" --claim "$CLAIM" --source-sha "$SOURCE_SHA")
if [[ "$ACTION" = start ]]; then
  INPUT=/home/vrrcelestino/model-agrologistic/data/processed
  ARGS+=(--one-reviewed-h300-block --workbook "$INPUT/nine_population_osrm_v1/warehouses_300/model_input.xlsx" --materialization-path "$INPUT/nine_population_osrm_v1/warehouses_300/osrm_materialization_audit.json" --population "$INPUT/warehouse_population_v020/warehouse_population_manifest.json" --order "$INPUT/warehouse_population_v020/warehouse_population_order.csv" --predecessor "$BASE/.mvp2-scalar-r3a-h215-4h-v1/scalar-h215-evidence.tar.gz")
elif [[ "$ACTION" = audit ]]; then
  ARGS+=(--archive "${MVP2_H300_ARCHIVE:?Select evidence archive}" --sha256 "${MVP2_H300_SHA256:?Select external checksum}")
fi
"$PY" -B -I -c 'import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("scripts.mvp2_scalar_h300_operational",run_name="__main__")' "$SRC" "${ARGS[@]}"
printf 'STATUS_COMMAND=bash %q status %s\nWAIT_COMMAND=bash %q wait %s\nCOLLECT_COMMAND=bash %q collect %s\n' "$WRAPPER" "$SOURCE_SHA" "$WRAPPER" "$SOURCE_SHA" "$WRAPPER" "$SOURCE_SHA"
if [[ -f "$CLAIM/job.json" ]]; then
  "$PY" -B -I -c 'import json,pathlib,sys; print("JOB_ID="+json.loads((pathlib.Path(sys.argv[1])/"job.json").read_bytes())["job_id"])' "$CLAIM"
fi
