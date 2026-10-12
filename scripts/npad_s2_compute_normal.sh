#!/usr/bin/env bash
# Human login-node entry after reviewed merge; at most one normal synthetic job.
set -euo pipefail
umask 077
if [[ $# != 2 || ! $2 =~ ^[0-9a-f]{40}$ || ! $1 =~ ^(start|collect)$ ]]; then
  printf 'Usage: bash npad_s2_compute_normal.sh {start|collect} FULL_REVIEWED_SOURCE_SHA\n' >&2
  exit 64
fi
ACTION=$1
SOURCE_SHA=$2
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
CLAIM="$BASE/.mvp2-s2-compute-integration-v1"
RUN=
PHASE=prerequisites
finish() {
  local rc=$?
  trap - EXIT
  printf 'DRIVER_EXIT=%s\nBOOTSTRAP_PHASE=%s\nPRESERVE_BOOTSTRAP=%s\nPRESERVE_CLAIM=%s\n' \
    "$rc" "$PHASE" "${RUN:-not-created}" "$CLAIM"
  printf 'NO_ADVERSE_NATIVE_MINIATURE_H300_OR_REPEAT_ADMITTED\n'
  exit "$rc"
}
trap finish EXIT
test -d "$BASE"
test -x "$PY"
test "$(id -un)" = vrrcelestino
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
"$PY" -B -c 'import sys; assert sys.platform == "linux" and sys.version_info[:2] == (3, 13)'
if [[ -e $CLAIM || -L $CLAIM ]]; then
  PHASE=existing_claim_collect_only
  SRC=$("$PY" -B -I - "$CLAIM" "$SOURCE_SHA" <<'PY'
import json
import pathlib
import sys
claim = pathlib.Path(sys.argv[1])
for path in (claim, *claim.parents):
    assert not path.is_symlink(), 'Linked claim; preserve and stop.'
intent = json.loads((claim / 'intent.json').read_bytes())
assert intent['source_commit'] == sys.argv[2], 'Use frozen source, never resubmit.'
proposal = json.loads((claim / 'proposal.json').read_bytes())
source = pathlib.Path(proposal['envelope']['checkout'])
assert source.name == 'source' and source.parent.parent == claim.parent
assert source.parent.name.startswith('s2-compute-driver-')
for path in (source, *source.parents):
    assert not path.is_symlink(), 'Linked source; preserve and stop.'
print(source)
PY
)
  RUN=$(dirname "$SRC")
else
  test "$ACTION" = start
  test -d "$BASE/.mvp2-s2-first-normal-v1"
  test -d "$BASE/.mvp2-s2-normal-recovery-pr67-v1"
  RUN=$(mktemp -d "$BASE/s2-compute-driver-XXXXXXXX")
  printf 'PRESERVE_BOOTSTRAP=%s\nSOURCE_SHA=%s\n' "$RUN" "$SOURCE_SHA"
  PHASE=checkout
  git -c core.autocrlf=false clone --no-checkout \
    https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$RUN/source"
  SRC="$RUN/source"
  printf '%s\n' '/manuscript/comparison_provenance.json -text' \
    '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
  git -C "$SRC" config core.autocrlf false
  git -C "$SRC" merge-base --is-ancestor "$SOURCE_SHA" origin/develop
  git -C "$SRC" checkout --detach "$SOURCE_SHA"
fi
PHASE=login_raw_head
# Byte verification also precedes execution from an existing consumed claim.
"$PY" -B -I - "$SRC" "$SOURCE_SHA" <<'PY'
import hashlib
import pathlib
import subprocess
import sys
root = pathlib.Path(sys.argv[1])
prefix = ['git', '--no-optional-locks', '-C', str(root)]
def git(*args):
    return subprocess.check_output(prefix + list(args), timeout=30)
assert git('rev-parse', 'HEAD').decode().strip() == sys.argv[2]
assert not git('status', '--porcelain', '--untracked-files=all', '--ignored'), 'Unexpected source content, including ignored files; preserve checkout.'
count = 0
files = {}
for record in git('ls-files', '--stage', '-z').split(b'\0'):
    if not record:
        continue
    meta, name = record.split(b'\t', 1)
    mode, oid, stage = meta.split()
    assert mode in (b'100644', b'100755') and stage == b'0'
    relative = pathlib.PurePosixPath(name.decode())
    assert not relative.is_absolute() and '..' not in relative.parts
    path = root.joinpath(*relative.parts)
    assert not any(p.is_symlink() for p in (path, *path.parents))
    assert path.read_bytes() == git('cat-file', 'blob', oid.decode())
    files[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    count += 1
sys.path.insert(0, str(root))
from scripts import mvp2_s2_compute_identity as identity
identity.inspect_tree(root, files)
print(f'RAW_HEAD_BYTES={count} tracked files identical')
PY
if [[ -e $CLAIM ]]; then
  PHASE=collection_no_resubmission
  "$PY" -B -I "$SRC/scripts/mvp2_s2_compute_normal.py" collect --source-sha "$SOURCE_SHA"
  exit 0
fi
cd "$SRC"
PHASE=regression
"$PY" -B -m ruff check --no-cache scripts/mvp2_s2_compute_normal.py \
  scripts/mvp2_s2_compute_integration.py scripts/mvp2_s2_compute_identity.py \
  tests/test_mvp2_s2_compute_normal.py tests/test_mvp2_s2_compute_identity.py
"$PY" -B -m pytest -p no:cacheprovider \
  tests/test_mvp2_s2_first_normal.py tests/test_mvp2_s2_normal_diagnostics.py \
  tests/test_mvp2_s2_normal_recovery.py tests/test_mvp2_s2_batch_adapter.py \
  tests/test_mvp2_s2_operational.py tests/test_mvp2_s2_compute_identity.py \
  tests/test_mvp2_s2_compute_integration.py tests/test_mvp2_s2_compute_normal.py \
  tests/test_mvp2_s2_listpids_compatibility.py \
  -q --basetemp="$RUN/tests" --junitxml="$RUN/regression.xml"
"$PY" -B - "$RUN/regression.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET
cases = ET.parse(sys.argv[1]).getroot().findall('.//testcase')
assert len(cases) == 524, 'Pinned regression count changed; preserve, do not bypass.'
assert not any(x.find(k) is not None for x in cases for k in ('failure', 'error'))
skips = [x for x in cases if x.find('skipped') is not None]
assert len(skips) == 2 and {x.get('name') for x in skips} == {
    'test_probe_cli_platform_failure_still_packages_negative_evidence',
    'test_real_non_linux_start_has_no_effect',
}, 'Unexpected skip; no submission.'
print(f'NPAD_COMPUTE_NORMAL_REGRESSION={len(cases) - 2} passed; two intentional platform skips')
PY
test -z "$(git -C "$SRC" status --porcelain --untracked-files=all --ignored)"
PHASE=post_regression_source_inventory
"$PY" -B -I - "$SRC" <<'PY'
import pathlib
import subprocess
import sys
root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root))
from scripts import mvp2_s2_compute_identity as identity
from scripts import mvp2_s2_batch_adapter as adapter
names = subprocess.check_output(
    ['git', '--no-optional-locks', '-C', str(root), 'ls-files', '-z'], timeout=30
).decode().rstrip('\0').split('\0')
files = {name: adapter.sha_file(root / name, identity.FILE_LIMIT) for name in names}
identity.inspect_tree(root, files)
print('POST_REGRESSION_SOURCE_INVENTORY=VERIFIED; NO_SUBMISSION_YET')
PY
PHASE=one_normal_only
"$PY" -B -I "$SRC/scripts/mvp2_s2_compute_normal.py" start --source-sha "$SOURCE_SHA"
PHASE=known_job_collect_next
printf 'Next: bash npad_s2_compute_normal.sh collect %s\n' "$SOURCE_SHA"
