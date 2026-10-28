#!/bin/bash
# Human-only one-arm wrapper; no installs, resampling, automatic retries or a larger instance.
set -euo pipefail
WRAPPER=$(readlink -f -- "$0")
ACTION=${1:?Use start/status/wait/collect/budget/audit}
SOURCE_SHA=${2:?Require the full reviewed source SHA}
case "$ACTION" in start|status|wait|collect|budget|audit) ;; *) echo 'Unsupported action' >&2; exit 2;; esac
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo 'Full reviewed SHA required' >&2; exit 2; }
BASE=${MVP2_HIGHS8_W_BASE:-/home/vrrcelestino/model-agrologistic-hygiene-audit}
PY=${MVP2_HIGHS8_W_PYTHON:-/home/vrrcelestino/venv313/bin/python}
[[ "$BASE" = /* && -d "$BASE" && -x "$PY" && -z ${SLURM_JOB_ID:-} ]] || {
  echo 'Existing audit base/Python and login context required' >&2; exit 2;
}
BASE=$(readlink -f -- "$BASE")
NPAD_HOME=$(readlink -f -- /home/vrrcelestino)
[[ "${BASE%/*}" = "$NPAD_HOME" && "${BASE##*/}" = model-agrologistic* && "${BASE##*/}" != model-agrologistic ]] || {
  echo 'Use an approved model-agrologistic output directory, never the home root or preserved input checkout' >&2; exit 2;
}
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
CLAIM="$BASE/.mvp2-scalar-highs-h215-w-native8h-v1"
DRIVER=''
trap 'code=$?; printf "DRIVER_EXIT=%s\nPRESERVE_CLAIM=%s\nPRESERVE_BOOTSTRAP=%s\nNO_REPEAT_LARGER_INSTANCE_OR_AUTOMATIC_FOLLOW_ON_ADMITTED\n" "$code" "$CLAIM" "$DRIVER"' EXIT
[[ ! -L "$CLAIM" ]] || { echo 'Claim link refused; preserve it' >&2; exit 2; }
if [[ -e "$CLAIM" ]]; then
  [[ -d "$CLAIM" ]] || { echo 'Existing non-directory claim; preserve it' >&2; exit 2; }
  [[ "$ACTION" != start ]] || {
    echo 'Existing HiGHS claim: inspect its original receipts; no submission or automatic collection' >&2; exit 2;
  }
  SRC=$("$PY" -B -I -c 'import hashlib,json,pathlib,sys; c=pathlib.Path(sys.argv[1]); p=json.loads((c/"plan.json").read_bytes()); raw=(c/"source.json").read_bytes(); i=json.loads(raw); assert hashlib.sha256(raw).hexdigest()==p["artifact_sha256"]["source.json"] and p["source_commit"]==sys.argv[2]==i["source_commit"]; n=pathlib.Path(p["source_root"]); assert n.is_relative_to(c.parent) and n.name=="source" and n.parent.name.startswith("scalar-highs-h215-w-native8h-driver-") and all((n/k).is_file() and not (n/k).is_symlink() and hashlib.sha256((n/k).read_bytes()).hexdigest()==v for k,v in i["files"].items()); print(n)' "$CLAIM" "$SOURCE_SHA")
else
  case "$ACTION" in status|wait|collect) echo 'Claim absent; no job or terminal collection exists' >&2; exit 2;; esac
  DRIVER=$(mktemp -d "$BASE/scalar-highs-h215-w-native8h-driver-XXXXXXXX")
  mkdir -p "$DRIVER/tmp" "$DRIVER/cache"
  export TMPDIR="$DRIVER/tmp" XDG_CACHE_HOME="$DRIVER/cache" MPLCONFIGDIR="$DRIVER/cache/matplotlib"
  SRC="$DRIVER/source"
  printf 'PRESERVE_BOOTSTRAP=%s\n' "$DRIVER"
  git -c core.autocrlf=false clone --no-checkout https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$SRC"
  printf '%s\n' '/manuscript/comparison_provenance.json -text' '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
  git -C "$SRC" -c core.autocrlf=false checkout --detach "$SOURCE_SHA"
fi
cd "$SRC"
"$PY" -B -I -c 'import sys; assert sys.version_info[:2]==(3,13); sys.path.insert(0,sys.argv[1]); from scripts.mvp2_scalar_r2 import source_inventory,verify_source; i=source_inventory(); assert i["source_commit"]==sys.argv[2]; verify_source(i); print("RAW_HEAD_BYTES="+str(len(i["files"]))+" identical; ONE_LONGER_HiGHS_H215_W_ONLY")' "$SRC" "$SOURCE_SHA"
if [[ "$ACTION" = start ]]; then
  "$PY" -B -I -c 'import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("ruff",run_name="__main__")' "$SRC" check .
  "$PY" -B -I -c 'import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("pytest",run_name="__main__")' "$SRC" -q -p no:cacheprovider tests/test_scalar_highs_h215_8h.py --basetemp "$DRIVER/tests" --junitxml "$DRIVER/regression.xml"
  "$PY" -B -I -c 'import sys,xml.etree.ElementTree as e; s=list(e.parse(sys.argv[1]).getroot().iter("testsuite")); assert s and sum(int(x.get("tests",0)) for x in s)>0 and all(int(x.get(k,0))==0 for x in s for k in ("failures","errors","skipped")); print("HiGHS_OPERATIONAL_LOGIN_REGRESSION=VERIFIED; NO_SOLVER_OR_JOB")' "$DRIVER/regression.xml"
fi
ARGS=("$ACTION" --claim "$CLAIM" --source-sha "$SOURCE_SHA")
if [[ "$ACTION" = start ]]; then
  INPUT=/home/vrrcelestino/model-agrologistic/data/processed
  W_ARCHIVE=${MVP2_HIGHS8_W_PREDECESSOR:-"$BASE/.mvp2-scalar-r3a-h215-4h-v1/scalar-h215-evidence.tar.gz"}
  ARGS+=(--one-reviewed-highs-w --workbook "$INPUT/policy_population_v020_osrm/warehouses_215/model_input.xlsx" --materialization "$INPUT/policy_population_v020_osrm/warehouses_215/osrm_materialization_audit.json" --population "$INPUT/warehouse_population_v020/warehouse_population_manifest.json" --order "$INPUT/warehouse_population_v020/warehouse_population_order.csv" --w-archive "$W_ARCHIVE")
elif [[ "$ACTION" = audit ]]; then
  ARGS+=(--archive "${MVP2_HIGHS8_W_ARCHIVE:?Select evidence archive}" --sha256 "${MVP2_HIGHS8_W_SHA256:?Select external checksum}")
fi
"$PY" -B -I -c 'import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("scripts.mvp2_scalar_highs_h215_8h",run_name="__main__")' "$SRC" "${ARGS[@]}"
printf 'STATUS_COMMAND=bash %q status %s\nWAIT_COMMAND=bash %q wait %s\nCOLLECT_COMMAND=bash %q collect %s\n' "$WRAPPER" "$SOURCE_SHA" "$WRAPPER" "$SOURCE_SHA" "$WRAPPER" "$SOURCE_SHA"
if [[ -f "$CLAIM/job.json" ]]; then
  "$PY" -B -I -c 'import json,pathlib,sys; print("JOB_ID="+json.loads((pathlib.Path(sys.argv[1])/"job.json").read_bytes())["job_id"])' "$CLAIM"
fi

