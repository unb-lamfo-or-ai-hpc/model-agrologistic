#!/usr/bin/env bash
# One global S1-A pair claim; rerunning start resumes collection, never submission.
set -euo pipefail
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
INPUT_RUN=$BASE/mvp2-h300-input-retry-ppbN3rwH
PY=/home/vrrcelestino/venv313/bin/python
stop() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
H300_PAIR_DRIVER_PHASE=initialization
trap 'rc=$?; printf "STOP: phase=%s line=%s exit=%s preserve_run=%s; preserve the claim.\n" "$H300_PAIR_DRIVER_PHASE" "$LINENO" "$rc" "${RUN:-not_created}" >&2; exit "$rc"' ERR

collect_existing() {
  local run=$1 execution job state collection source tracked
  run=$(realpath -e "$run")
  case "$run" in "$BASE"/mvp2-h300-s1a-*) ;; *) stop "Unexpected S1-A run path";; esac
  execution=$run/execution
  test -f "$execution/submission.txt" || stop "No submission receipt; preserve $run and claim"
  source=$(cat "$execution/source_commit.txt")
  test "$(git -C "$run/source" rev-parse HEAD)" = "$source" || stop "Checkout identity changed"
  tracked=$(git -C "$run/source" status --porcelain --untracked-files=no)
  test -z "$tracked" || stop "Tracked source changed; preserve checkout"
  job=$(sed -n 's/^MVP2_H300_PAIR_JOB=//p' "$execution/submission.txt")
  [[ "$job" =~ ^[0-9]+$ ]] || stop "Invalid standalone pair job"
  printf 'PRESERVE_RUN=%s\nJOB=%s\n' "$run" "$job"
  printf 'Waiting for terminal accounting. Ctrl-C is safe; repeat the same start command to collect.\n'
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
    "$run/source/scripts/collect_mvp2_h300_pair.py" \
    --execution "$execution" --output-dir "$collection/evidence" --job-id "$job"
  local archive checksum status
  archive=$collection/evidence/h300-pair-evidence-$job.tar.gz
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
      "$run/source/scripts/collect_mvp2_h300_pair.py" --archive "$archive" \
      --sha256 "$checksum" --review-output "$collection/pair_review.json"
  fi
  printf 'TRANSFER_ARCHIVE=%s\nTRANSFER_CHECKSUM=%s.sha256\n' "$archive" "$archive"
  printf 'Preserve the original run and claim; no repeat is admitted by collection.\n'
}

case "${1:-}" in
  collect)
    test "$#" = 2 || stop "Usage: $0 collect /absolute/S1-A/run"
    collect_existing "$2"
    exit 0;;
  start)
    test "$#" = 2 || stop "Usage: $0 start FULL_CI_PASSED_SOURCE_SHA"
    SOURCE_SHA=$2
    [[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || stop "Require full pinned commit";;
  *) stop "Usage: $0 {start FULL_SHA | collect /absolute/S1-A/run}";;
esac
test -d "$BASE" && test -x "$PY" || stop "Missing base or qualified Python"
CLAIM=$BASE/.mvp2-h300-single-pair-s1a
if ! mkdir "$CLAIM" 2>/dev/null; then
  test -f "$CLAIM/run.txt" && test -f "$CLAIM/source.txt" || stop "Incomplete claim; preserve it"
  test "$(cat "$CLAIM/source.txt")" = "$SOURCE_SHA" || stop "Another source claimed this S1-A pair"
  printf 'Existing S1-A pair claim: no job will be submitted again.\n'
  collect_existing "$(cat "$CLAIM/run.txt")"
  exit 0
fi
printf '%s\n' "$SOURCE_SHA" > "$CLAIM/source.txt"
RUN=$(mktemp -d "$BASE/mvp2-h300-s1a-XXXXXXXX")
printf '%s\n' "$RUN" > "$CLAIM/run.txt"
printf 'PRESERVE_RUN=%s\n' "$RUN"
H300_PAIR_DRIVER_PHASE=clone
git clone --no-checkout https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$RUN/source"
SRC=$RUN/source
git -C "$SRC" config core.autocrlf false
printf '%s\n' '/manuscript/comparison_provenance.json -text' \
  '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
H300_PAIR_DRIVER_PHASE=checkout
git -C "$SRC" checkout --detach "$SOURCE_SHA"
test "$(git -C "$SRC" rev-parse HEAD)" = "$SOURCE_SHA"
tracked=$(git -C "$SRC" status --porcelain --untracked-files=no)
test -z "$tracked"
cd "$SRC"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
"$PY" - <<'PY'
import hashlib
import subprocess
from pathlib import Path
entries = subprocess.check_output(["git", "ls-tree", "-rz", "--full-tree", "HEAD"])
count = 0
for entry in entries.split(b"\0"):
    if not entry:
        continue
    metadata, name = entry.split(b"\t", 1)
    mode, kind, expected = metadata.split()
    if kind != b"blob" or mode not in (b"100644", b"100755"):
        raise SystemExit("STOP: unsupported tracked entry")
    path = Path(name.decode())
    if path.is_symlink():
        raise SystemExit("STOP: tracked symlink")
    data = path.read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if actual != expected.decode():
        raise SystemExit(f"STOP: raw HEAD-byte mismatch: {path}")
    count += 1
print(f"Raw HEAD-byte gate: {count} tracked files identical.")
PY
H300_PAIR_DRIVER_PHASE=focused_regressions
"$PY" -m ruff check .
"$PY" -m pytest -q tests/test_mvp2_resource_contrasts.py tests/test_mvp2_pair_preflight.py \
  tests/test_mvp2_pair_solve.py tests/test_mvp2_preflight_collection.py \
  tests/test_mvp2_h300_retry_driver.py tests/test_mvp2_h300_baseline.py \
  tests/test_mvp2_h300_pair.py --junitxml="$RUN/focused-tests.xml"
"$PY" - "$RUN/focused-tests.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET
cases = list(ET.parse(sys.argv[1]).getroot().iter("testcase"))
if len(cases) < 300 or any(c.find(tag) is not None for c in cases for tag in ("skipped", "failure", "error")):
    raise SystemExit("STOP: incomplete focused regression gate")
print(f"NPAD focused regression gate: {len(cases)} tests, zero failures/errors/skips.")
PY
H300_PAIR_DRIVER_PHASE=prepare_pair
sacct -n -P -j 2198085 --format=JobIDRaw,State,ExitCode,Elapsed,MaxRSS,NodeList > "$RUN/input-accounting.txt"
"$PY" scripts/mvp2_h300_pair.py --input-run "$INPUT_RUN" \
  --input-accounting "$RUN/input-accounting.txt" --output-dir "$RUN/execution"
H300_PAIR_DRIVER_PHASE=submit_pair
H300_PAIR_CHECKOUT="$SRC" H300_PAIR_PLAN="$RUN/execution/pair_plan.json" H300_PAIR_PYTHON="$PY" \
  bash scripts/submit_mvp2_h300_pair.sh
H300_PAIR_DRIVER_PHASE=terminal_collection
collect_existing "$RUN"
