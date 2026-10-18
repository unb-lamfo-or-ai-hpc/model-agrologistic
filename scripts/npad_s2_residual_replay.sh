#!/usr/bin/env bash
# One read-only replay allocation; original claims and vectors remain immutable.
set -euo pipefail
umask 077
if [[ $# != 2 || ! $1 =~ ^(start|status|wait|collect)$ || ! $2 =~ ^[0-9a-f]{40}$ ]]; then
  printf 'Usage: npad_s2_residual_replay.sh ACTION FULL_SHA\n' >&2
  exit 64
fi
ACTION=$1
SOURCE_SHA=$2
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
CLAIM="$BASE/.mvp2-s2-residual-replay-v1"
if [[ $ACTION != start && ! -e $CLAIM && ! -L $CLAIM ]]; then
  printf 'REPLAY_STATUS=not_submitted; preserve bootstrap; NO_JOB\n' >&2
  exit 2
fi
test -d "$BASE" && test -x "$PY"
test "$(id -un)" = vrrcelestino
export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
SELF=$(realpath -e -- "$0")
if [[ -e $CLAIM || -L $CLAIM ]]; then
  SRC=$("$PY" -B -I -c 'import json,pathlib,sys; c=pathlib.Path(sys.argv[1]); assert not any(p.is_symlink() for p in (c,*c.parents)); assert json.loads((c/"plan.json").read_bytes())["source_commit"]==sys.argv[2]; r=pathlib.Path(json.loads((c/"replay-origin.json").read_bytes())["root"]); assert r.name=="source" and r.parent.parent==c.parent and r.parent.name.startswith("s2-residual-driver-"); assert not any(p.is_symlink() for p in (r,*r.parents)); print(r)' "$CLAIM" "$SOURCE_SHA")
  if [[ $ACTION == start ]]; then ACTION=collect; fi
else
  test "$ACTION" = start
  BOOTSTRAP=$(mktemp -d "$BASE/s2-residual-driver-XXXXXXXX")
  SRC="$BOOTSTRAP/source"
  printf 'PRESERVE_BOOTSTRAP=%s\n' "$BOOTSTRAP"
  git -c core.autocrlf=false clone --no-checkout https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$SRC"
  printf '%s\n' '/manuscript/comparison_provenance.json -text' '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
  git -C "$SRC" merge-base --is-ancestor 233abebe97b111fea5f5bbe4cdd4c9f527988e72 "$SOURCE_SHA"
  git -C "$SRC" merge-base --is-ancestor "$SOURCE_SHA" origin/develop
  git -C "$SRC" checkout --detach "$SOURCE_SHA"
fi
verify() {
  "$PY" -B -I -c 'import pathlib,sys; r=pathlib.Path(sys.argv[1]); sys.path.insert(0,str(r)); from scripts import mvp2_s2_allocation_diagnostic as s; f=s.source_files(r,sys.argv[2]); assert pathlib.Path(sys.argv[3]).read_bytes()==(r/"scripts/npad_s2_residual_replay.sh").read_bytes(); print("RAW_HEAD_BYTES="+str(len(f))+" identical; EXISTING_VECTOR_ONLY")' "$SRC" "$SOURCE_SHA" "$SELF"
}
verify
if [[ ! -e $CLAIM ]]; then
  cd "$SRC"
  "$PY" -B -m ruff check --no-cache scripts/mvp2_s2_residual_replay.py tests/test_mvp2_s2_residual_replay.py tests/s2_residual_fixture.py
  "$PY" -B -m pytest -p no:cacheprovider tests/test_mvp2_s2_residual_replay.py -q --basetemp="$BOOTSTRAP/tests" --junitxml="$BOOTSTRAP/regression.xml"
  "$PY" -B -I -c 'import sys,xml.etree.ElementTree as E; c=E.parse(sys.argv[1]).getroot().findall(".//testcase"); assert len(c)==56 and not any(x.find(k) is not None for x in c for k in ("failure","error","skipped")); print("RESIDUAL_REPLAY_REGRESSION="+str(len(c))+" passed; zero failures/errors/skips")' "$BOOTSTRAP/regression.xml"
  verify
fi
exec "$PY" -B -I -c 'import runpy,sys;sys.dont_write_bytecode=True;r=sys.argv.pop(1);sys.path.insert(0,r);runpy.run_module("scripts.mvp2_s2_residual_replay",run_name="__main__",alter_sys=True)' "$SRC" "$ACTION" "$SOURCE_SHA"
