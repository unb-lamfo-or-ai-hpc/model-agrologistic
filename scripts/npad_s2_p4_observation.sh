#!/usr/bin/env bash
# Human prerequisite observation only; one global claim, never h300 or repeats.
set -euo pipefail
umask 077
if [[ $# -lt 2 || ! $1 =~ ^(start|status|wait|collect)$ || ! $2 =~ ^[0-9a-f]{40}$ ]]; then
  printf 'Usage: npad_s2_p4_observation.sh ACTION FULL_SHA [--one-reviewed-observation-only]\n' >&2
  exit 64
fi
ACTION=$1
SOURCE_SHA=$2
shift 2
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
CLAIM="$BASE/.mvp2-s2-p4-observation-v1"
if [[ $ACTION != start && ! -e $CLAIM && ! -L $CLAIM ]]; then
  printf 'OBSERVATION_STATUS=not_submitted; no observation claim exists\nNO_JOB_OR_TERMINAL_COLLECTION_AVAILABLE; preserve the failed bootstrap\nNO_H300_REPEAT_OR_AUTOMATIC_FOLLOW_ON_ADMITTED\n' >&2
  exit 2
fi
test -d "$BASE" && test -x "$PY"
test "$(id -un)" = vrrcelestino
export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
SELF=$(realpath -e -- "$0")
if [[ -e $CLAIM || -L $CLAIM ]]; then
  SRC=$("$PY" -B -I -c 'import json,pathlib,sys; c=pathlib.Path(sys.argv[1]); assert not any(p.is_symlink() for p in (c,*c.parents)); assert json.loads((c/"plan.json").read_bytes())["source_commit"]==sys.argv[2]; r=pathlib.Path(json.loads((c/"origin.json").read_bytes())["root"]); assert r.name=="source" and r.parent.parent==c.parent and r.parent.name.startswith("s2-p4-observation-driver-"); assert not any(p.is_symlink() for p in (r,*r.parents)); print(r)' "$CLAIM" "$SOURCE_SHA")
  if [[ $ACTION == start ]]; then ACTION=collect; fi
else
  test "$ACTION" = start
  test "${1:-}" = --one-reviewed-observation-only
  test ! -e "$BASE/.mvp2-s2-p4-admission-v1"
  BOOTSTRAP=$(mktemp -d "$BASE/s2-p4-observation-driver-XXXXXXXX")
  SRC="$BOOTSTRAP/source"
  printf 'PRESERVE_BOOTSTRAP=%s\n' "$BOOTSTRAP"
  git -c core.autocrlf=false clone --no-checkout https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$SRC"
  printf '%s\n' '/manuscript/comparison_provenance.json -text' '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
  git -C "$SRC" merge-base --is-ancestor 279a081a8d100c787b65ca620d2b69ef36e88342 "$SOURCE_SHA"
  git -C "$SRC" merge-base --is-ancestor "$SOURCE_SHA" origin/develop
  git -C "$SRC" checkout --detach "$SOURCE_SHA"
fi
verify() {
  "$PY" -B -I -c 'import pathlib,sys; r=pathlib.Path(sys.argv[1]); sys.path.insert(0,str(r)); from scripts import mvp2_s2_allocation_diagnostic as s; f=s.source_files(r,sys.argv[2]); assert pathlib.Path(sys.argv[3]).read_bytes()==(r/"scripts/npad_s2_p4_observation.sh").read_bytes(); print("RAW_HEAD_BYTES="+str(len(f))+" identical; OBSERVATION_ONLY")' "$SRC" "$SOURCE_SHA" "$SELF"
}
verify
if [[ ! -e $CLAIM ]]; then
  cd "$SRC"
  "$PY" -B -m ruff check --no-cache scripts/mvp2_s2_p4_observation.py scripts/mvp2_s2_h300_runtime.py tests/test_mvp2_s2_p4_observation.py tests/test_mvp2_s2_p4_input_contract.py
  "$PY" -B -m pytest -p no:cacheprovider tests/test_mvp2_s2_p4_observation.py tests/test_mvp2_s2_p4_admission.py tests/test_mvp2_s2_p4_input_contract.py -q --basetemp="$BOOTSTRAP/tests" --junitxml="$BOOTSTRAP/regression.xml"
  "$PY" -B -I -c 'import sys,xml.etree.ElementTree as E; c=E.parse(sys.argv[1]).getroot().findall(".//testcase"); assert len(c)==107 and not any(x.find(k) is not None for x in c for k in ("failure","error","skipped")); print("P4_OBSERVATION_REGRESSION="+str(len(c))+" passed; zero failures/errors/skips")' "$BOOTSTRAP/regression.xml"
  verify
fi
exec "$PY" -B -I -c 'import runpy,sys; sys.dont_write_bytecode=True; r=sys.argv.pop(1); sys.path.insert(0,r); runpy.run_module("scripts.mvp2_s2_p4_observation",run_name="__main__",alter_sys=True)' "$SRC" "$ACTION" "$SOURCE_SHA" "$@"
