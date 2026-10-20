#!/bin/bash
# Software/proposal wrapper ONLY. Does not submit or run a model on NPAD.
set -euo pipefail
ACTION=${1:?Use prepare/status/collect/budget/audit; execution is closed}
SOURCE_SHA=${2:?Require the complete reviewed source SHA}
case "$ACTION" in
  start|batch|worker|h300) printf 'R3A_EXECUTION_CLOSED; NO_JOB_SUBMITTED\n' >&2; exit 2;;
  prepare|status|collect|budget|audit) ;;
  *) printf 'Unsupported action\n' >&2; exit 2;;
esac
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo 'Full SHA required' >&2; exit 2; }
BASE=${MVP2_R3A_BASE:?Select existing audit parent}
PY=${MVP2_R3A_PYTHON:?Select existing Python3.13}
[[ "$BASE" = /* && -d "$BASE" && -x "$PY" ]] || { echo 'Invalid base/Python' >&2; exit 2; }
[[ -z ${SLURM_JOB_ID:-} ]] || { echo 'Proposal wrapper is login-only, not a compute worker' >&2; exit 2; }
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
CLAIM="$BASE/.mvp2-scalar-r3a-proposal-v1"
trap 'code=$?; printf "DRIVER_EXIT=%s\nPRESERVE_PROPOSAL=%s\nNO_JOB_NATIVE_H300_OR_REPEAT_ADMITTED\n" "$code" "$CLAIM"' EXIT
if [[ -d "$CLAIM" ]]; then
  SRC=$("$PY" -B -I -c 'import hashlib,json,pathlib,sys; c=pathlib.Path(sys.argv[1]); p=json.loads((c/"plan.json").read_bytes()); raw=(c/"source.json").read_bytes(); i=json.loads(raw); assert hashlib.sha256(raw).hexdigest()==p["source_inventory_sha256"] and p["source_commit"]==sys.argv[2]==i["source_commit"]; r=pathlib.Path(p["source_root"]); assert r.is_relative_to(c.parent) and r.name=="source"; assert all(not (r/n).is_symlink() and hashlib.sha256((r/n).read_bytes()).hexdigest()==v for n,v in i["files"].items()); print(r)' "$CLAIM" "$SOURCE_SHA")
  if [[ "$ACTION" = prepare ]]; then ACTION=status; fi
else
  case "$ACTION" in status|collect) echo 'Proposal absent; no job or collection exists' >&2; exit 2;; esac
  DRIVER=$(mktemp -d "$BASE/scalar-r3a-proposal-XXXXXXXX")
  SRC="$DRIVER/source"
  printf 'PRESERVE_BOOTSTRAP=%s\n' "$DRIVER"
  git -c core.autocrlf=false clone --no-checkout https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$SRC"
  printf '%s\n' '/manuscript/comparison_provenance.json -text' '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
  git -C "$SRC" -c core.autocrlf=false checkout --detach "$SOURCE_SHA"
fi
cd "$SRC"
"$PY" -B -I -c 'import sys; assert sys.version_info[:2]==(3,13); sys.path.insert(0,sys.argv[1]); from scripts.mvp2_scalar_r2 import source_inventory,verify_source; i=source_inventory(); assert i["source_commit"]==sys.argv[2]; verify_source(i); print("RAW_HEAD_BYTES=VERIFIED; PROPOSAL_ONLY")' "$SRC" "$SOURCE_SHA"
ARGS=("$ACTION" --claim "$CLAIM" --source-sha "$SOURCE_SHA")
if [[ "$ACTION" = prepare ]]; then
  ARGS+=(--workbook "${MVP2_R3A_WORKBOOK:?Select existing h215 input}" --workbook-sha256 "${MVP2_R3A_WORKBOOK_SHA256:?Pin input checksum}" --r2-archive "${MVP2_R3A_R2_ARCHIVE:?Select preserved accepted R2 archive}" --r2-sha256 57b8e4d37ee21be04dd651088d9c525b812cf82514f3d55b23e3759651da2ed6)
  ARGS+=(--population-manifest "${MVP2_R3A_POPULATION_MANIFEST:?Select preserved population protocol}" --population-order "${MVP2_R3A_POPULATION_ORDER:?Select preserved population order CSV}" --population-manifest-sha256 "${MVP2_R3A_POPULATION_MANIFEST_SHA256:?Pin protocol hash}" --population-order-sha256 "${MVP2_R3A_POPULATION_ORDER_SHA256:?Pin population-order hash}")
elif [[ "$ACTION" = audit ]]; then
  ARGS+=(--archive "${MVP2_R3A_ARCHIVE:?Select evidence}" --sha256 "${MVP2_R3A_ARCHIVE_SHA256:?Select expected checksum}")
fi
"$PY" -B -I -c 'import runpy,sys; sys.dont_write_bytecode=True; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("scripts.mvp2_scalar_r3a",run_name="__main__",alter_sys=True)' "$SRC" "${ARGS[@]}"
