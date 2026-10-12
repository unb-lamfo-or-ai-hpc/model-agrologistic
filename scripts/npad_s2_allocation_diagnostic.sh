#!/usr/bin/env bash
# Diagnostic-only source may be a qualified immutable PR commit before merge.
set -euo pipefail
umask 077
if [[ $# != 2 || ! $1 =~ ^(start|collect)$ || ! $2 =~ ^[0-9a-f]{40}$ ]]; then
  printf 'Usage: bash npad_s2_allocation_diagnostic.sh {start|collect} REVIEWED_SHA\n' >&2
  exit 64
fi
ACTION=$1
SOURCE_SHA=$2
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
CLAIM="$BASE/.mvp2-s2-allocation-diagnostic-v1"
test -d "$BASE"
test -x "$PY"
test "$(id -un)" = vrrcelestino
test ! -L "$CLAIM"
if [[ -e $CLAIM ]]; then
  SRC=$("$PY" -B -I - "$CLAIM/plan.json" "$SOURCE_SHA" "$BASE" <<'PY'
import json
import pathlib
import sys
plan = json.loads(pathlib.Path(sys.argv[1]).read_bytes())
assert plan['source_commit'] == sys.argv[2], 'Use original source; never resubmit.'
source = pathlib.Path(plan['checkout'])
assert source.name == 'source' and source.parent.name.startswith('s2-allocation-driver-')
assert source.parent.parent == pathlib.Path(sys.argv[3])
assert not any(p.is_symlink() for p in (source, *source.parents))
print(source)
PY
)
  ACTION=collect
else
  test "$ACTION" = start
  RUN=$(mktemp -d "$BASE/s2-allocation-driver-XXXXXXXX")
  printf 'PRESERVE_BOOTSTRAP=%s\n' "$RUN"
  git -c core.autocrlf=false clone --no-checkout \
    https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$RUN/source"
  SRC="$RUN/source"
  printf '%s\n' '/manuscript/comparison_provenance.json -text' \
    '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
  git -C "$SRC" config core.autocrlf false
  git -C "$SRC" checkout --detach "$SOURCE_SHA"
  # Reviewed integration base must be preserved; no moving-branch execution.
  git -C "$SRC" merge-base --is-ancestor 478d5ee513994a20e8788f1f504b195a7f67f346 "$SOURCE_SHA"
fi
test "$(git -C "$SRC" rev-parse HEAD)" = "$SOURCE_SHA"
test -z "$(git -C "$SRC" status --porcelain --untracked-files=all --ignored)"
cd "$SRC"
if [[ $ACTION == start ]]; then
  "$PY" -B -m ruff check --no-cache scripts/mvp2_s2_allocation_diagnostic.py tests/test_mvp2_s2_allocation_diagnostic.py
  "$PY" -B -m pytest -p no:cacheprovider tests/test_mvp2_s2_allocation_diagnostic.py \
    -q --basetemp="$(dirname "$SRC")/tests" --junitxml="$(dirname "$SRC")/regression.xml"
  "$PY" -B -I - "$(dirname "$SRC")/regression.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET
cases = ET.parse(sys.argv[1]).getroot().findall('.//testcase')
assert len(cases) == 56 and not any(c.find(k) is not None for c in cases for k in ('failure', 'error', 'skipped'))
print(f'NPAD_ALLOCATION_REGRESSION={len(cases)} passed; zero failures/errors/skips')
PY
fi
# Source byte verification before start AND collect, without creating bytecode.
"$PY" -B -I - "$SRC" "$SOURCE_SHA" <<'PY'
import pathlib
import subprocess
import sys
root = pathlib.Path(sys.argv[1])
prefix = ['git', '--no-optional-locks', '-C', str(root)]
assert subprocess.check_output(prefix + ['rev-parse', 'HEAD']).decode().strip() == sys.argv[2]
assert not subprocess.check_output(prefix + ['status', '--porcelain', '--untracked-files=all', '--ignored'])
for name in subprocess.check_output(prefix + ['ls-files', '-z']).decode().rstrip('\0').split('\0'):
    path = root / name
    assert not any(p.is_symlink() for p in (path, *path.parents))
    assert path.read_bytes() == subprocess.check_output(prefix + ['cat-file', 'blob', 'HEAD:' + name])
print('RAW_HEAD_BYTES=VERIFIED; OBSERVATION_ONLY')
PY
"$PY" -B -I scripts/mvp2_s2_allocation_diagnostic.py "$ACTION" --source-sha "$SOURCE_SHA"
printf 'RESUME_COMMAND=bash %s/scripts/npad_s2_allocation_diagnostic.sh collect %s\n' "$SRC" "$SOURCE_SHA"
printf 'NO_NORMAL_ADVERSE_NATIVE_H300_OR_REPEAT_ADMITTED\n'
