#!/usr/bin/env bash
# One human-selected academic stage. No automatic sequence, retry or h300 route.
set -euo pipefail
umask 077
if [[ $# -lt 3 || ! $1 =~ ^(start|status|wait|collect)$ || ! $3 =~ ^[0-9a-f]{40}$ ]]; then
  printf 'Usage: npad_s2_academic.sh ACTION STAGE FULL_SOURCE_SHA [--one-reviewed-academic-slot ANCHORS...]\n' >&2
  exit 64
fi
ACTION=$1
STAGE=$2
SOURCE_SHA=$3
shift 3
case "$STAGE" in
  normal|build_failure|optimization_failure|export_failure|disposal_failure|nested_setsid_term_ignore|native_miniature) ;;
  *) exit 64 ;;
esac
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
CLAIM="$BASE/.mvp2-s2-academic-v1-$STAGE"
test -d "$BASE"
test -x "$PY"
test "$(id -un)" = vrrcelestino
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
SELF=$("$PY" -B -I -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$0")
if [[ -e $CLAIM || -L $CLAIM ]]; then
  SRC=$("$PY" -B -I - "$CLAIM" "$SOURCE_SHA" <<'PY'
import json, pathlib, sys
claim = pathlib.Path(sys.argv[1])
assert not any(p.is_symlink() for p in (claim, *claim.parents))
assert json.loads((claim / 'plan.json').read_bytes())['source_commit'] == sys.argv[2]
root = pathlib.Path(json.loads((claim / 'origin.json').read_bytes())['checkout'])
assert root.name == 'source' and root.parent.parent == claim.parent
assert root.parent.name.startswith('s2-academic-driver-')
assert not any(p.is_symlink() for p in (root, *root.parents))
print(root)
PY
)
  if [[ $ACTION == start ]]; then ACTION=collect; fi
else
  test "$ACTION" = start
  test "${1:-}" = --one-reviewed-academic-slot
  BOOTSTRAP=$(mktemp -d "$BASE/s2-academic-driver-XXXXXXXX")
  SRC="$BOOTSTRAP/source"
  printf 'PRESERVE_BOOTSTRAP=%s\n' "$BOOTSTRAP"
  git -c core.autocrlf=false clone --no-checkout \
    https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$SRC"
  printf '%s\n' '/manuscript/comparison_provenance.json -text' \
    '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
  git -C "$SRC" merge-base --is-ancestor 219233e2b116ffcc5eac5c462b4b863059eace14 "$SOURCE_SHA"
  git -C "$SRC" merge-base --is-ancestor "$SOURCE_SHA" origin/develop
  git -C "$SRC" checkout --detach "$SOURCE_SHA"
fi
verify() {
  "$PY" -B -I - "$SRC" "$SOURCE_SHA" "$SELF" <<'PY'
import pathlib, sys
root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root))
from scripts import mvp2_s2_allocation_diagnostic as d
files = d.source_files(root, sys.argv[2])
assert pathlib.Path(sys.argv[3]).read_bytes() == (root / 'scripts/npad_s2_academic.sh').read_bytes()
print(f'RAW_HEAD_BYTES={len(files)} tracked files identical; ACADEMIC_NOT_PRODUCTION')
PY
}
verify
if [[ ! -e $CLAIM ]]; then
  cd "$SRC"
  "$PY" -B -m ruff check --no-cache scripts/mvp2_s2_academic.py \
    scripts/mvp2_s2_academic_runtime.py scripts/mvp2_s2_academic_worker.py \
    tests/test_mvp2_s2_academic.py
  "$PY" -B -m pytest -p no:cacheprovider tests/test_mvp2_s2_academic.py \
    -q --basetemp="$BOOTSTRAP/tests" --junitxml="$BOOTSTRAP/regression.xml"
  "$PY" -B -I - "$BOOTSTRAP/regression.xml" <<'PY'
import sys, xml.etree.ElementTree as ET
cases = ET.parse(sys.argv[1]).getroot().findall('.//testcase')
assert len(cases) >= 40
assert not any(c.find(k) is not None for c in cases for k in ('failure', 'error', 'skipped'))
print(f'ACADEMIC_REGRESSION={len(cases)} passed; zero failures/errors/skips')
PY
  verify
fi
ENTRY="$SRC/scripts/mvp2_s2_academic_runtime.py"
if [[ $ACTION == start ]]; then
  "$PY" -B -I "$ENTRY" start "$STAGE" "$SOURCE_SHA" "$@"
elif [[ $ACTION == collect ]]; then
  "$PY" -B -I "$ENTRY" collect "$STAGE"
else
  while true; do
    "$PY" -B -I "$ENTRY" status "$STAGE"
    if [[ $ACTION == status ]]; then break; fi
    if "$PY" -B -I "$ENTRY" collect "$STAGE"; then
      break
    else
      rc=$?
      if [[ $rc != 2 ]]; then exit "$rc"; fi
    fi
    printf 'Accounting pending; preserve claim. Ctrl-C is safe.\n'
    sleep 20
  done
fi
printf 'PRESERVE_CLAIM=%s\nNO_AUTOMATIC_FOLLOW_ON_H300_OR_REPEAT\n' "$CLAIM"
