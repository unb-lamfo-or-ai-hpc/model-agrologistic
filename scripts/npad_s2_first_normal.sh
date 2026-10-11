#!/usr/bin/env bash
# First NORMAL stdlib synthetic attempt only. Human CLI after qualified merge.
set -euo pipefail
umask 077
if [[ $# != 2 || ! $2 =~ ^[0-9a-f]{40}$ || ! $1 =~ ^(start|collect)$ ]]; then
  printf 'Usage: bash npad_s2_first_normal.sh {start|collect} FULL_REVIEWED_SOURCE_SHA\n' >&2
  exit 64
fi
ACTION=$1
SOURCE_SHA=$2
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
CLAIM="$BASE/.mvp2-s2-first-normal-v1"
RUN=
PHASE=prerequisites
finish() {
  local rc=$?
  trap - EXIT
  printf 'DRIVER_EXIT=%s\nBOOTSTRAP_PHASE=%s\nPRESERVE_BOOTSTRAP=%s\nPRESERVE_CLAIM=%s\n' \
    "$rc" "$PHASE" "${RUN:-existing-claim-or-not-created}" "$CLAIM"
  printf 'NO_ADVERSE_NATIVE_MINIATURE_H300_OR_REPEAT_ADMITTED\n'
  exit "$rc"
}
trap finish EXIT
test -d "$BASE"
test -x "$PY"
test "$(id -un)" = vrrcelestino
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
"$PY" -B -c 'import sys; assert sys.platform == "linux" and sys.version_info[:2] == (3, 13)'
if [[ -e $CLAIM ]]; then
  PHASE=existing_claim_collect_only
  # An incomplete/unknown claim is a stop, not permission to create another run.
  SRC=$("$PY" -B -I - "$CLAIM" "$SOURCE_SHA" <<'PY'
import json
import pathlib
import sys
claim = pathlib.Path(sys.argv[1])
for path in (claim, *claim.parents):
    assert not path.is_symlink(), 'Linked campaign claim; preserve and stop.'
intent = json.loads((claim / 'intent.json').read_bytes())
assert intent['source_commit'] == sys.argv[2], 'Use original frozen source; do not retry.'
envelope = json.loads((claim / 'private-envelope.json').read_bytes())
source = pathlib.Path(envelope['checkout'])
base = pathlib.Path('/home/vrrcelestino/model-agrologistic-hygiene-audit')
assert source.name == 'source' and source.parent.parent == base
assert source.parent.name.startswith('s2-normal-driver-')
for path in (source, *source.parents):
    assert not path.is_symlink(), 'Linked source; preserve and stop.'
print(source)
PY
)
  RUN=$(dirname "$SRC")
  exec "$PY" -B -I "$SRC/scripts/mvp2_s2_first_normal.py" collect --source-sha "$SOURCE_SHA"
fi
if [[ $ACTION != start ]]; then
  printf 'No original campaign claim. Collection cannot submit a job.\n' >&2
  exit 2
fi
RUN=$(mktemp -d "$BASE/s2-normal-driver-XXXXXXXX")
printf 'PRESERVE_BOOTSTRAP=%s\nSOURCE_SHA=%s\n' "$RUN" "$SOURCE_SHA"
PHASE=checkout
git -c core.autocrlf=false clone --no-checkout \
  https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$RUN/source"
SRC="$RUN/source"
printf '%s\n' \
  '/manuscript/comparison_provenance.json -text' \
  '/manuscript/figures/runtime_memory_comparison.pdf -text' \
  > "$SRC/.git/info/attributes"
git -C "$SRC" config core.autocrlf false
git -C "$SRC" merge-base --is-ancestor "$SOURCE_SHA" origin/develop
git -C "$SRC" checkout --detach "$SOURCE_SHA"
test "$(git -C "$SRC" rev-parse HEAD)" = "$SOURCE_SHA"
test -z "$(git -C "$SRC" status --porcelain --untracked-files=all)"
cd "$SRC"
PHASE=regression
"$PY" -B -m ruff check --no-cache scripts/mvp2_s2_first_normal.py \
  scripts/mvp2_s2_batch_adapter.py scripts/mvp2_s2_operational.py \
  tests/test_mvp2_s2_first_normal.py tests/test_mvp2_s2_batch_adapter.py \
  tests/test_mvp2_s2_operational.py
"$PY" -B -m pytest -p no:cacheprovider \
  tests/test_mvp2_s2_first_normal.py tests/test_mvp2_s2_batch_adapter.py \
  tests/test_mvp2_s2_operational.py -q --basetemp="$RUN/tests" \
  --junitxml="$RUN/regression.xml"
"$PY" -B - "$RUN/regression.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET
cases = ET.parse(sys.argv[1]).getroot().findall('.//testcase')
assert len(cases) == 243, 'Pinned regression count changed; preserve, do not bypass.'
assert not any(x.find('failure') is not None or x.find('error') is not None for x in cases)
skips = [x for x in cases if x.find('skipped') is not None]
assert len(skips) == 2 and {x.get('name') for x in skips} == {
    'test_probe_cli_platform_failure_still_packages_negative_evidence',
    'test_real_non_linux_start_has_no_effect',
}, 'Unexpected skip; no submission admitted.'
print('NPAD_FIRST_NORMAL_REGRESSION=241 passed; two intentional non-Linux-only negative CLI skips')
PY
test -z "$(git -C "$SRC" status --porcelain --untracked-files=all)"
PHASE=first_normal_only
"$PY" -B -I "$SRC/scripts/mvp2_s2_first_normal.py" start --source-sha "$SOURCE_SHA"
PHASE=known_job_collect_next
printf 'Next: bash npad_s2_first_normal.sh collect %s\n' "$SOURCE_SHA"
# Transfer only the subsequently printed DOWNLOAD and TRANSFER_CHECKSUM.
# Preserve bootstrap/source/run/claim even on failure; no automatic retry.
