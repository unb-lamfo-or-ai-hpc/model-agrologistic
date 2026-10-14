#!/usr/bin/env bash
# One pinned human observation-only job. Existing/uncertain claims never resubmit.
set -euo pipefail
umask 077
if [[ $# != 2 || ! $1 =~ ^(start|status|collect|wait)$ || ! $2 =~ ^[0-9a-f]{40}$ ]]; then
  printf 'Usage: bash npad_s2_fast_exit_observation.sh {start|status|collect|wait} FULL_REVIEWED_SOURCE_SHA\n' >&2
  exit 64
fi
ACTION=$1
SOURCE_SHA=$2
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
CLAIM="$BASE/.mvp2-s2-fast-exit-observation-v1"
BOOTSTRAP=
PHASE=prerequisites
finish() {
  local rc=$?
  trap - EXIT
  printf 'DRIVER_EXIT=%s\nBOOTSTRAP_PHASE=%s\nPRESERVE_BOOTSTRAP=%s\nPRESERVE_CLAIM=%s\n' \
    "$rc" "$PHASE" "${BOOTSTRAP:-not-created}" "$CLAIM"
  printf 'NO_NORMAL_ADVERSE_NATIVE_MINIATURE_H300_OR_REPEAT_ADMITTED\n'
  exit "$rc"
}
trap finish EXIT
test -d "$BASE"
test -x "$PY"
test "$(id -un)" = vrrcelestino
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
"$PY" -B -I -c 'import sys; assert sys.platform == "linux" and sys.version_info[:2] == (3, 13)'
SELF=$("$PY" -B -I -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$0")
if [[ -e $CLAIM || -L $CLAIM ]]; then
  PHASE=existing_claim_collect_only
  SRC=$("$PY" -B -I - "$CLAIM" "$SOURCE_SHA" <<'PY'
import json, pathlib, sys
def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result, 'Duplicate plan key; preserve and stop.'
        result[key] = value
    return result
claim = pathlib.Path(sys.argv[1])
for path in (claim, *claim.parents):
    assert not path.is_symlink(), 'Linked claim; preserve and stop.'
with (claim / 'plan.json').open('rb') as stream:
    raw = stream.read(1024 * 1024 + 1)
assert len(raw) <= 1024 * 1024
plan = json.loads(raw, object_pairs_hook=pairs)
assert plan['source_commit'] == sys.argv[2], 'Use original source, never reset.'
source = pathlib.Path(plan['checkout'])
assert source.name == 'source' and source.parent.parent == claim.parent
assert source.parent.name.startswith('s2-fast-exit-driver-')
for path in (source, *source.parents):
    assert not path.is_symlink(), 'Linked source; preserve and stop.'
print(source)
PY
)
  BOOTSTRAP=$(dirname "$SRC")
  if [[ $ACTION == start ]]; then
    ACTION=collect
    printf 'Existing claim: collection only; no job will be submitted again.\n'
  fi
else
  test "$ACTION" = start
  BOOTSTRAP=$(mktemp -d "$BASE/s2-fast-exit-driver-XXXXXXXX")
  SRC="$BOOTSTRAP/source"
  printf 'PRESERVE_BOOTSTRAP=%s\nSOURCE_SHA=%s\n' "$BOOTSTRAP" "$SOURCE_SHA"
  PHASE=checkout
  git -c core.autocrlf=false clone --no-checkout \
    https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$SRC"
  printf '%s\n' '/manuscript/comparison_provenance.json -text' \
    '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
  git -C "$SRC" config core.autocrlf false
  git -C "$SRC" merge-base --is-ancestor 40a55f5270c6921f28349024de0dcce69befcab1 "$SOURCE_SHA"
  git -C "$SRC" merge-base --is-ancestor "$SOURCE_SHA" origin/develop
  git -C "$SRC" checkout --detach "$SOURCE_SHA"
fi
verify_source() {
  "$PY" -B -I - "$SRC" "$SOURCE_SHA" "$SELF" <<'PY'
import pathlib, subprocess, sys
root = pathlib.Path(sys.argv[1])
entry = 'scripts/mvp2_s2_allocation_diagnostic.py'
prefix = ['git', '--no-optional-locks', '-C', str(root)]
def git(*args):
    return subprocess.check_output(prefix + list(args), timeout=30)
assert git('rev-parse', 'HEAD').decode().strip() == sys.argv[2]
assert (root / entry).read_bytes() == git('cat-file', 'blob', 'HEAD:' + entry)
sys.path.insert(0, str(root))
from scripts import mvp2_s2_allocation_diagnostic as d
files = d.source_files(root, sys.argv[2])
assert pathlib.Path(sys.argv[3]).read_bytes() == (root / 'scripts/npad_s2_fast_exit_observation.sh').read_bytes()
print(f'RAW_HEAD_BYTES={len(files)} tracked files identical; OBSERVATION_ONLY')
PY
}
PHASE=login_raw_head
verify_source
if [[ ! -e $CLAIM ]]; then
  PHASE=regression
  cd "$SRC"
  "$PY" -B -m ruff check --no-cache scripts tests
  "$PY" -B -m pytest -p no:cacheprovider tests/test_mvp2_s2_fast_exit.py \
    tests/test_mvp2_s2_scope_diagnostic.py -q --basetemp="$BOOTSTRAP/tests" \
    --junitxml="$BOOTSTRAP/regression.xml"
  "$PY" -B -I - "$BOOTSTRAP/regression.xml" <<'PY'
import sys, xml.etree.ElementTree as ET
cases = ET.parse(sys.argv[1]).getroot().findall('.//testcase')
assert len(cases) == 153, 'Pinned regression count changed; preserve, never bypass.'
assert not any(case.find(key) is not None for case in cases for key in ('failure', 'error', 'skipped'))
print(f'NPAD_FAST_EXIT_REGRESSION={len(cases)} passed; zero failures/errors/skips')
PY
  PHASE=post_regression_source_inventory
  verify_source
  printf 'POST_REGRESSION_SOURCE_INVENTORY=VERIFIED; NO_SUBMISSION_YET\n'
fi
PHASE="$ACTION"_observation_only
"$PY" -B -I "$SRC/scripts/mvp2_s2_fast_exit_observation.py" "$ACTION" --source-sha "$SOURCE_SHA"
printf 'STATUS_COMMAND=bash %s status %s\n' "$SELF" "$SOURCE_SHA"
printf 'COLLECT_COMMAND=bash %s collect %s\n' "$SELF" "$SOURCE_SHA"
printf 'WAIT_COMMAND=bash %s wait %s\n' "$SELF" "$SOURCE_SHA"
printf 'Ctrl-C during wait is safe. Preserve claims, run and source; never reset or resubmit.\n'
