#!/usr/bin/env bash
# One durable S1-B input-only claim; repeat starts resume collection only.
set -euo pipefail
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
REF=/home/vrrcelestino/model-agrologistic/data/results/hpc/nine-connectivity-corrected-20260914T180739Z/campaign.yaml
QUAL=$BASE/mvp2-objbound-retry-V64C2OGW/report/qualification/qualification_report.json
PY=/home/vrrcelestino/venv313/bin/python
stop() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
H400_INPUT_DRIVER_PHASE=initialization
trap 'rc=$?; printf "STOP: phase=%s line=%s exit=%s preserve_run=%s; preserve the claim.\n" "$H400_INPUT_DRIVER_PHASE" "$LINENO" "$rc" "${RUN:-not_created}" >&2; exit "$rc"' ERR

collect_existing() {
  local run=$1 job source state collection archive checksum status
  run=$(realpath -e "$run")
  case "$run" in "$BASE"/mvp2-h400-input-s1b-*) ;; *) stop "Unexpected S1-B run path";; esac
  test -f "$run/audit/submission.txt" || stop "No submission receipt; preserve run and claim"
  source=$(cat "$run/audit/source_commit.txt")
  test "$(git -C "$run/source" rev-parse HEAD)" = "$source" || stop "Checkout identity changed"
  test -z "$(git -C "$run/source" status --porcelain --untracked-files=no)" || stop "Tracked source changed"
  job=$(sed -n 's/^MVP2_H400_INPUT_JOB=//p' "$run/audit/submission.txt")
  [[ "$job" =~ ^[0-9]+$ ]] || stop "Invalid input job"
  printf 'PRESERVE_RUN=%s\nJOB=%s\n' "$run" "$job"
  printf 'Waiting for terminal accounting. Ctrl-C is safe; repeat start to collect, never resubmit.\n'
  while true; do
    state=$(sacct -n -P -j "$job" --format=JobIDRaw,State | awk -F '|' -v job="$job" '$1 == job {print $2}')
    printf '%s job=%s state=%s\n' "$(date -u +%FT%TZ)" "$job" "${state:-ACCOUNTING_PENDING}"
    case "$state" in
      COMPLETED|FAILED|CANCELLED*|TIMEOUT|OUT_OF_MEMORY|NODE_FAIL|PREEMPTED|BOOT_FAIL|DEADLINE|REVOKED) break;;
      *) sleep 20;;
    esac
  done
  collection=$(mktemp -d "$run/collection-XXXXXXXX")
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 "$PY" \
    "$run/source/scripts/collect_mvp2_h400_input.py" --run "$run" \
    --output-dir "$collection/evidence" --job-id "$job"
  archive=$collection/evidence/h400-input-evidence-$job.tar.gz
  checksum=$(sha256sum "$archive" | awk '{print $1}')
  status=$("$PY" - "$collection/evidence/collection.json" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text())["status"])
PY
)
  if [[ "$status" == accepted || "$status" == terminal_failure ]]; then
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 "$PY" \
      "$run/source/scripts/collect_mvp2_h400_input.py" --archive "$archive" \
      --sha256 "$checksum" --review-output "$collection/input_review.json"
  fi
  printf 'TRANSFER_ARCHIVE=%s\nTRANSFER_CHECKSUM=%s.sha256\n' "$archive" "$archive"
  printf 'Preserve original run and claim. No solve or repeat is admitted.\n'
}

case "${1:-}" in
  collect) test "$#" = 2 || stop "Usage: $0 collect /absolute/S1-B/run"; collect_existing "$2"; exit 0;;
  start) test "$#" = 2 || stop "Usage: $0 start FULL_CI_PASSED_SHA"
    SOURCE_SHA=$2; [[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || stop "Require full pinned commit";;
  *) stop "Usage: $0 {start FULL_SHA | collect /absolute/S1-B/run}";;
esac
test -d "$BASE" && test -x "$PY" || stop "Missing base or qualified Python"
CLAIM=$BASE/.mvp2-h400-input-s1b
if ! mkdir "$CLAIM" 2>/dev/null; then
  test -f "$CLAIM/run.txt" && test -f "$CLAIM/source.txt" || stop "Incomplete claim; preserve it"
  test "$(cat "$CLAIM/source.txt")" = "$SOURCE_SHA" || stop "Another source claimed S1-B inputs"
  printf 'Existing input claim: no job will be submitted again.\n'
  collect_existing "$(cat "$CLAIM/run.txt")"
  exit 0
fi
printf '%s\n' "$SOURCE_SHA" > "$CLAIM/source.txt"
RUN=$(mktemp -d "$BASE/mvp2-h400-input-s1b-XXXXXXXX")
printf '%s\n' "$RUN" > "$CLAIM/run.txt"
printf 'PRESERVE_RUN=%s\n' "$RUN"
H400_INPUT_DRIVER_PHASE=clone
git clone --no-checkout https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$RUN/source"
SRC=$RUN/source
git -C "$SRC" config core.autocrlf false
printf '%s\n' '/manuscript/comparison_provenance.json -text' \
  '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
H400_INPUT_DRIVER_PHASE=checkout
git -C "$SRC" checkout --detach "$SOURCE_SHA"
test "$(git -C "$SRC" rev-parse HEAD)" = "$SOURCE_SHA"
test -z "$(git -C "$SRC" status --porcelain --untracked-files=no)"
cd "$SRC"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
"$PY" - <<'PY'
import hashlib
import subprocess
from pathlib import Path
count = 0
for entry in subprocess.check_output(["git", "ls-tree", "-rz", "--full-tree", "HEAD"]).split(b"\0"):
    if not entry:
        continue
    metadata, name = entry.split(b"\t", 1)
    mode, kind, expected = metadata.split()
    path = Path(name.decode())
    if kind != b"blob" or mode not in (b"100644", b"100755") or path.is_symlink():
        raise SystemExit("STOP: unsupported tracked entry")
    data = path.read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if actual != expected.decode():
        raise SystemExit(f"STOP: raw HEAD-byte mismatch: {path}")
    count += 1
print(f"Raw HEAD-byte gate: {count} tracked files identical.")
PY
H400_INPUT_DRIVER_PHASE=focused_regressions
"$PY" -m ruff check .
"$PY" -m pytest -q tests/test_mvp2_resource_contrasts.py tests/test_mvp2_pair_preflight.py \
  tests/test_mvp2_preflight_collection.py tests/test_mvp2_h300_retry_driver.py \
  tests/test_mvp2_h400_input.py --junitxml="$RUN/focused-tests.xml"
"$PY" - "$RUN/focused-tests.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET
cases = list(ET.parse(sys.argv[1]).getroot().iter("testcase"))
if len(cases) < 100 or any(c.find(tag) is not None for c in cases for tag in ("skipped", "failure", "error")):
    raise SystemExit("STOP: incomplete focused regression gate")
print(f"NPAD input regression gate: {len(cases)} tests, zero failures/errors/skips.")
PY
H400_INPUT_DRIVER_PHASE=prepare_input
"$PY" scripts/mvp2_h400_input.py prepare --reference "$REF" --qualification "$QUAL" \
  --output-dir "$RUN/prepared" --source "$SOURCE_SHA"
mkdir "$RUN/audit"
H400_INPUT_DRIVER_PHASE=submit_input
H400_INPUT_CHECKOUT="$SRC" H400_INPUT_PLAN="$RUN/prepared/input_plan.json" \
  H400_INPUT_AUDIT="$RUN/audit" H400_INPUT_PYTHON="$PY" bash scripts/submit_mvp2_h400_input.sh
H400_INPUT_DRIVER_PHASE=terminal_collection
collect_existing "$RUN"
