#!/usr/bin/env bash
# Pinned human login-node entry: one normal-only job, then read-only status/collection.
set -euo pipefail
umask 077
if [[ $# != 2 || ! $1 =~ ^(start|status|collect|wait)$ || ! $2 =~ ^[0-9a-f]{40}$ ]]; then
  printf 'Usage: bash npad_s2_resource_normal.sh {start|status|collect|wait} FULL_REVIEWED_SOURCE_SHA\n' >&2
  exit 64
fi
ACTION=$1
SOURCE_SHA=$2
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
CLAIM="$BASE/.mvp2-s2-resource-normal-v1"
BOOTSTRAP=
PHASE=prerequisites
finish() {
  local rc=$?
  trap - EXIT
  printf 'DRIVER_EXIT=%s\nBOOTSTRAP_PHASE=%s\nPRESERVE_BOOTSTRAP=%s\nPRESERVE_CLAIM=%s\n' \
    "$rc" "$PHASE" "${BOOTSTRAP:-not-created}" "$CLAIM"
  printf 'NO_ADVERSE_NATIVE_MINIATURE_H300_OR_REPEAT_ADMITTED\n'
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
import json
import pathlib
import sys
def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result, 'Duplicate proposal key; preserve and stop.'
        result[key] = value
    return result
claim = pathlib.Path(sys.argv[1])
for path in (claim, *claim.parents):
    assert not path.is_symlink(), 'Linked claim; preserve and stop.'
with (claim / 'proposal.json').open('rb') as stream:
    raw = stream.read(1024 * 1024 + 1)
assert len(raw) <= 1024 * 1024
proposal = json.loads(raw, object_pairs_hook=pairs)
assert proposal['envelope']['source_commit'] == sys.argv[2], 'Use original source; never reset a claim.'
source = pathlib.Path(proposal['envelope']['checkout'])
assert source.name == 'source' and source.parent.parent == claim.parent
assert source.parent.name.startswith('s2-resource-driver-')
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
  BOOTSTRAP=$(mktemp -d "$BASE/s2-resource-driver-XXXXXXXX")
  SRC="$BOOTSTRAP/source"
  printf 'PRESERVE_BOOTSTRAP=%s\nSOURCE_SHA=%s\n' "$BOOTSTRAP" "$SOURCE_SHA"
  PHASE=checkout
  git -c core.autocrlf=false clone --no-checkout \
    https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$SRC"
  printf '%s\n' '/manuscript/comparison_provenance.json -text' \
    '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
  git -C "$SRC" config core.autocrlf false
  git -C "$SRC" merge-base --is-ancestor f1ab13568cd961d1bf0a61638caa2d3874b9fa8c "$SOURCE_SHA"
  git -C "$SRC" merge-base --is-ancestor "$SOURCE_SHA" origin/develop
  git -C "$SRC" checkout --detach "$SOURCE_SHA"
fi
verify_source() {
  "$PY" -B -I - "$SRC" "$SOURCE_SHA" "$SELF" <<'PY'
import hashlib
import pathlib
import subprocess
import sys
root = pathlib.Path(sys.argv[1])
prefix = ['git', '--no-optional-locks', '-C', str(root)]
def git(*args):
    return subprocess.check_output(prefix + list(args), timeout=30)
assert git('rev-parse', 'HEAD').decode().strip() == sys.argv[2]
assert not git('status', '--porcelain', '--untracked-files=all', '--ignored'), 'Unexpected source content; preserve checkout.'
files = {}
for item in git('ls-files', '--stage', '-z').split(b'\0'):
    if not item:
        continue
    meta, name = item.split(b'\t', 1)
    mode, oid, stage = meta.split()
    assert mode in (b'100644', b'100755') and stage == b'0'
    relative = pathlib.PurePosixPath(name.decode())
    assert not relative.is_absolute() and '..' not in relative.parts
    path = root.joinpath(*relative.parts)
    assert not any(p.is_symlink() for p in (path, *path.parents))
    data = path.read_bytes()
    assert data == git('cat-file', 'blob', oid.decode())
    files[relative.as_posix()] = hashlib.sha256(data).hexdigest()
assert pathlib.Path(sys.argv[3]).read_bytes() == (root / 'scripts/npad_s2_resource_normal.sh').read_bytes(), 'Running driver differs from pinned HEAD.'
sys.path.insert(0, str(root))
from scripts import mvp2_s2_compute_identity as identity
identity.inspect_tree(root, files)
print(f'RAW_HEAD_BYTES={len(files)} tracked files identical')
PY
}
PHASE=login_raw_head
verify_source
if [[ ! -e $CLAIM ]]; then
  PHASE=regression
  cd "$SRC"
  "$PY" -B -m ruff check --no-cache scripts tests
  "$PY" -B -m pytest -p no:cacheprovider \
    tests/test_mvp2_s2_resource_operational.py tests/test_mvp2_s2_resource_launcher.py \
    tests/test_mvp2_s2_resource_normal.py tests/test_mvp2_s2_synthetic_resources.py \
    tests/test_mvp2_s2_compute_identity.py tests/test_mvp2_s2_slurm_step.py \
    -q --basetemp="$BOOTSTRAP/tests" --junitxml="$BOOTSTRAP/regression.xml"
  "$PY" -B -I - "$BOOTSTRAP/regression.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET
cases = ET.parse(sys.argv[1]).getroot().findall('.//testcase')
assert len(cases) == 349, 'Pinned test count changed; preserve, never bypass.'
assert not any(case.find(key) is not None for case in cases for key in ('failure', 'error', 'skipped'))
print(f'NPAD_RESOURCE_NORMAL_REGRESSION={len(cases)} passed; zero failures/errors/skips')
PY
  PHASE=post_regression_source_inventory
  verify_source
  printf 'POST_REGRESSION_SOURCE_INVENTORY=VERIFIED; NO_SUBMISSION_YET\n'
fi
PHASE="$ACTION"_normal_only
"$PY" -B -I "$SRC/scripts/mvp2_s2_resource_operational.py" "$ACTION" --source-sha "$SOURCE_SHA"
printf 'STATUS_COMMAND=bash %s status %s\n' "$SELF" "$SOURCE_SHA"
printf 'COLLECT_COMMAND=bash %s collect %s\n' "$SELF" "$SOURCE_SHA"
printf 'WAIT_COMMAND=bash %s wait %s\n' "$SELF" "$SOURCE_SHA"
printf 'Ctrl-C during wait is safe: repeat wait or collect, never reset a claim.\n'
