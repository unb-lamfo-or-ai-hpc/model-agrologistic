#!/usr/bin/env bash
# Qualified immutable observation source; no normal/solver/repeat admission.
set -euo pipefail
umask 077
if [[ $# != 2 || ! $1 =~ ^(start|collect)$ || ! $2 =~ ^[0-9a-f]{40}$ ]]; then
  printf 'Usage: bash npad_s2_scope_diagnostic.sh {start|collect} REVIEWED_SHA\n' >&2
  exit 64
fi
ACTION=$1
SOURCE_SHA=$2
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
CLAIM="$BASE/.mvp2-s2-scope-observation-v1"
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
assert source.name == 'source' and source.parent.name.startswith('s2-scope-driver-')
assert source.parent.parent == pathlib.Path(sys.argv[3])
assert not any(p.is_symlink() for p in (source, *source.parents))
print(source)
PY
)
  ACTION=collect
else
  test "$ACTION" = start
  RUN=$(mktemp -d "$BASE/s2-scope-driver-XXXXXXXX")
  printf 'PRESERVE_BOOTSTRAP=%s\n' "$RUN"
  git -c core.autocrlf=false clone --no-checkout \
    https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$RUN/source"
  SRC="$RUN/source"
  printf '%s\n' '/manuscript/comparison_provenance.json -text' \
    '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
  git -C "$SRC" config core.autocrlf false
  git -C "$SRC" checkout --detach "$SOURCE_SHA"
  git -C "$SRC" merge-base --is-ancestor 5bf509a6db90b09eef8e1e13529f5039d934a9e1 "$SOURCE_SHA"
fi
test "$(git -C "$SRC" rev-parse HEAD)" = "$SOURCE_SHA"
cd "$SRC"
if [[ $ACTION == start ]]; then
  "$PY" -B -m ruff check --no-cache scripts/mvp2_s2_scope_diagnostic.py tests/test_mvp2_s2_scope_diagnostic.py
  "$PY" -B -m pytest -p no:cacheprovider tests/test_mvp2_s2_scope_diagnostic.py \
    -q --basetemp="$(dirname "$SRC")/tests" --junitxml="$(dirname "$SRC")/regression.xml"
  "$PY" -B -I - "$(dirname "$SRC")/regression.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET
cases = ET.parse(sys.argv[1]).getroot().findall('.//testcase')
assert len(cases) == 47 and not any(c.find(k) is not None for c in cases for k in ('failure', 'error', 'skipped'))
print(f'NPAD_SCOPE_REGRESSION={len(cases)} passed; zero failures/errors/skips')
PY
fi
"$PY" -B -I - "$SRC" "$SOURCE_SHA" <<'PY'
import pathlib
import sys
sys.path.insert(0, sys.argv[1])
from scripts import mvp2_s2_allocation_diagnostic as d
d.source_files(pathlib.Path(sys.argv[1]), sys.argv[2])
print('RAW_HEAD_BYTES=VERIFIED; OBSERVATION_ONLY')
PY
"$PY" -B -I scripts/mvp2_s2_scope_diagnostic.py "$ACTION" --source-sha "$SOURCE_SHA"
printf 'RESUME_COMMAND=bash %s/scripts/npad_s2_scope_diagnostic.sh collect %s\n' "$SRC" "$SOURCE_SHA"
printf 'NO_NORMAL_ADVERSE_NATIVE_H300_OR_REPEAT_ADMITTED\n'
