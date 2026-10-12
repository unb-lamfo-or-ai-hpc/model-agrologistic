#!/usr/bin/env bash
# Collection only. Never source or modify the original execution checkout.
set -euo pipefail
umask 077
if [[ $# != 1 || ! $1 =~ ^[0-9a-f]{40}$ ]]; then
  printf 'Usage: bash npad_s2_accounting_recovery.sh FULL_REVIEWED_ANALYSIS_SHA\n' >&2
  exit 64
fi
ANALYSIS_SHA=$1
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
test -d "$BASE/.mvp2-s2-node-normal-v1"
test -x "$PY"
test "$(id -un)" = vrrcelestino
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
READER=$(mktemp -d "$BASE/s2-accounting-reader-XXXXXXXX")
printf 'PRESERVE_READER=%s\nANALYSIS_SOURCE=%s\n' "$READER" "$ANALYSIS_SHA"
trap 'printf "READER_EXIT=%s; NO_JOB_SUBMITTED_OR_REPEATED\n" "$?"' EXIT
git -c core.autocrlf=false clone --no-checkout \
  https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$READER/source"
SRC="$READER/source"
printf '%s\n' '/manuscript/comparison_provenance.json -text' \
  '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
git -C "$SRC" -c core.autocrlf=false checkout --detach "$ANALYSIS_SHA"
test "$(git -C "$SRC" rev-parse HEAD)" = "$ANALYSIS_SHA"
test -z "$(git -C "$SRC" status --porcelain --untracked-files=all --ignored)"
cd "$SRC"
"$PY" -B -m ruff check --no-cache scripts/mvp2_s2_accounting_recovery.py \
  scripts/mvp2_s2_batch_adapter.py scripts/mvp2_s2_operational.py \
  tests/test_mvp2_s2_accounting_recovery.py
"$PY" -B -m pytest -p no:cacheprovider tests/test_mvp2_s2_accounting_recovery.py \
  -q --basetemp="$READER/tests" --junitxml="$READER/regression.xml"
"$PY" -B -I - "$READER/regression.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET
cases = ET.parse(sys.argv[1]).getroot().findall('.//testcase')
assert len(cases) == 63
assert not any(c.find(k) is not None for c in cases for k in ('failure', 'error', 'skipped'))
print('ACCOUNTING_RECOVERY_REGRESSION=63 passed; no failures/errors/skips; NO_SUBMISSION')
PY
"$PY" -B -I "$SRC/scripts/mvp2_s2_accounting_recovery.py" --analysis-sha "$ANALYSIS_SHA"
