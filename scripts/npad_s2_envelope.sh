#!/usr/bin/env bash
# Read-only envelope observation after this source is merged; NEVER submits jobs.
set -euo pipefail
umask 077
if [[ $# != 1 || ! $1 =~ ^[0-9a-f]{40}$ ]]; then
  printf 'Usage: bash npad_s2_envelope.sh FULL_MERGED_SOURCE_SHA\n' >&2
  exit 64
fi
SOURCE_SHA=$1
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
RUN=
PHASE=prerequisites
finish() {
  local rc=$?
  trap - EXIT
  printf 'DRIVER_EXIT=%s\nBOOTSTRAP_PHASE=%s\nPRESERVE_RUN=%s\n' \
    "$rc" "$PHASE" "${RUN:-not-created}"
  if [[ -n $RUN && -d $RUN ]]; then
    printf 'RUN_PATH_PRESENT_ON_EXIT=true\nREGRESSION_XML=%s/regression.xml\n' "$RUN"
  else
    printf 'RUN_PATH_PRESENT_ON_EXIT=false\n'
  fi
  printf 'NO_JOB_SUBMITTED_BY_THIS_DRIVER\n'
  exit "$rc"
}
trap finish EXIT
phase() {
  PHASE=$1
  printf '%s\n' "$PHASE" >> "$RUN/bootstrap-phases.txt"
  printf 'BOOTSTRAP_PHASE=%s\n' "$PHASE"
}
test -d "$BASE"
test -x "$PY"
test "$(id -un)" = vrrcelestino
RUN=$(mktemp -d "$BASE/s2-envelope-repair-XXXXXXXX")
printf 'PRESERVE_RUN=%s\nSOURCE_SHA=%s\n' "$RUN" "$SOURCE_SHA"
printf 'host=%s\nuser=%s\nrun=%s\nsource=%s\n' \
  "$(hostname -s)" "$(id -un)" "$RUN" "$SOURCE_SHA" > "$RUN/run-location.txt"
printf 'LOCAL_LOCATION_RECEIPT=%s/run-location.txt\n' "$RUN"
phase checkout
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
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
cd "$SRC"
"$PY" -B -c 'import sys; assert sys.platform == "linux" and sys.version_info[:2] == (3, 13)'
phase lint
"$PY" -B -m ruff check --no-cache \
  scripts/mvp2_s2_operational.py scripts/mvp2_s2_batch_adapter.py \
  tests/test_mvp2_s2_operational.py tests/test_mvp2_s2_batch_adapter.py
phase regression
"$PY" -B -m pytest -p no:cacheprovider \
  tests/test_mvp2_s2_operational.py tests/test_mvp2_s2_batch_adapter.py \
  -q --basetemp="$RUN/tests" --junitxml="$RUN/regression.xml"
"$PY" -B - "$RUN/regression.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET
cases = ET.parse(sys.argv[1]).getroot().findall('.//testcase')
skips = [x for x in cases if x.find('skipped') is not None]
assert len(cases) == 170, 'Unexpected pinned test count; stop, do not bypass.'
assert not any(x.find('failure') is not None or x.find('error') is not None for x in cases)
assert len(skips) == 1 and skips[0].get('name') == 'test_probe_cli_platform_failure_still_packages_negative_evidence', 'Unexpected skip; stop.'
print('NPAD_ENVELOPE_REGRESSION=169 passed; one intentional non-Linux-only negative CLI skip; zero failures/errors')
PY
test -z "$(git -C "$SRC" status --porcelain --untracked-files=all)"
phase read_only_probe
"$PY" -B -I "$SRC/scripts/mvp2_s2_operational.py" probe-envelope \
  --source-sha "$SOURCE_SHA" --output "$RUN/envelope"
phase complete_not_admitted
# Transfer only printed DOWNLOAD/TRANSFER_CHECKSUM; keep location/private envelope locally.
# A handled blocked_envelope exits 2 AFTER packaging. No synthetic repeat is admitted.
