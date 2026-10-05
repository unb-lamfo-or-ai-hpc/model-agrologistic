#!/usr/bin/env bash
# One input-only retry per pinned commit; repeated starts only resume collection.
set -euo pipefail
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
REF=/home/vrrcelestino/model-agrologistic/data/results/hpc/nine-connectivity-corrected-20260914T180739Z/campaign.yaml
QUAL=$BASE/mvp2-objbound-retry-V64C2OGW/report/qualification/qualification_report.json
PY=/home/vrrcelestino/venv313/bin/python
stop() { printf 'STOP: %s\n' "$*" >&2; exit 1; }

collect_existing() {
  local run=$1 job state collection source
  run=$(realpath -e "$run")
  case "$run" in "$BASE"/mvp2-h300-input-retry-*) ;; *) stop "Unexpected run path";; esac
  test -f "$run/audit/submission.txt" || stop "No submission receipt; preserve $run"
  source=$(cat "$run/audit/source_commit.txt")
  test "$(git -C "$run/source" rev-parse HEAD)" = "$source" || stop "Checkout changed"
  job=$(sed -n 's/^MVP2_PAIR_PREFLIGHT_JOB=//p' "$run/audit/submission.txt")
  case "$job" in *[!0-9]*|'') stop "Invalid standalone job ID";; esac
  printf 'PRESERVE_RUN=%s\nJOB=%s\n' "$run" "$job"
  printf 'Waiting for terminal accounting; Ctrl-C is safe. Resume with: bash %s collect %s\n' "$0" "$run"
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
    "$run/source/scripts/collect_mvp2_pair_preflight.py" \
    --run-dir "$run" --output-dir "$collection/evidence" --job-id "$job"
}

case "${1:-}" in
  collect)
    test "$#" = 2 || stop "Usage: $0 collect /absolute/preserved/run"
    collect_existing "$2"
    exit 0;;
  start)
    test "$#" = 2 || stop "Usage: $0 start FULL_REVIEWED_SOURCE_SHA"
    SOURCE_SHA=$2
    [[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || stop "Require a full pinned commit"
    ;;
  *) stop "Usage: $0 {start FULL_SHA | collect /absolute/preserved/run}";;
esac

test -d "$BASE" && test -x "$PY" || stop "Missing NPAD base or qualified Python"
test "$(sha256sum "$REF" | cut -d ' ' -f 1)" = 348c4c08c2c9e906cbd3a28df7753577ebed3cac30702aae30dfb8ce2ad25694
test "$(sha256sum "$QUAL" | cut -d ' ' -f 1)" = b9e4b2a5bb7ecf66b0c54432986c3033bf381bdea223fc914ddefa7dcc24bde7
CLAIM=$BASE/.pr47-h300-input-retry-$SOURCE_SHA
if ! mkdir "$CLAIM" 2>/dev/null; then
  test -f "$CLAIM/run.txt" || stop "Existing claim without a run pointer; do not remove it"
  RUN=$(cat "$CLAIM/run.txt")
  printf 'Existing retry claim: no job will be submitted again.\n'
  collect_existing "$RUN"
  exit 0
fi
RUN=$(mktemp -d "$BASE/mvp2-h300-input-retry-XXXXXXXX")
printf '%s\n' "$RUN" > "$CLAIM/run.txt"
printf 'PRESERVE_RUN=%s\n' "$RUN"
git clone --no-checkout https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$RUN/source"
SRC=$RUN/source
printf '%s\n' '/manuscript/comparison_provenance.json -text' \
  '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$SRC/.git/info/attributes"
git -C "$SRC" checkout --detach "$SOURCE_SHA"
test "$(git -C "$SRC" rev-parse HEAD)" = "$SOURCE_SHA"
test -z "$(git -C "$SRC" status --porcelain --untracked-files=no)"
cd "$SRC"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
"$PY" - "$REF" <<'PY'
import hashlib
import subprocess
import sys
from pathlib import Path

from src.logic.experiment_runner import load_experiment_manifest

entries = subprocess.check_output(["git", "ls-tree", "-rz", "--full-tree", "HEAD"])
count = 0
for entry in entries.split(b"\0"):
    if not entry:
        continue
    metadata, name = entry.split(b"\t", 1)
    mode, kind, expected = metadata.split()
    if kind != b"blob" or mode not in (b"100644", b"100755"):
        raise SystemExit("STOP: unsupported tracked entry")
    data = Path(name.decode()).read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if actual != expected.decode():
        raise SystemExit(f"STOP: raw checkout byte mismatch: {name.decode()}")
    count += 1
print(f"Raw HEAD-byte gate: {count} tracked files identical.")
manifest = load_experiment_manifest(sys.argv[1])
candidates = [i for i, spec in enumerate(manifest.experiments)
              if spec.metadata.get("warehouse_population") == 300
              and spec.model.mode == "sto" and spec.model.objective_policy == "lexicographic"
              and spec.model.use_direct_origin_customer is False]
if candidates != [2]:
    raise SystemExit(f"STOP: reviewed h300 index must be [2], got {candidates}")
print("REVIEWED_H300_INDEX=2")
PY
"$PY" scripts/prepare_mvp2_resource_contrasts.py \
  --reference-manifest "$REF" \
  --reference-sha256 348c4c08c2c9e906cbd3a28df7753577ebed3cac30702aae30dfb8ce2ad25694 \
  --index 2 --qualification-report "$QUAL" --output-dir "$RUN/prepared" --case h300-warehouse
mkdir "$RUN/audit"
MVP2_PAIR_CHECKOUT="$SRC" MVP2_PAIR_PLAN="$RUN/prepared/resource_contrast_plan.json" \
  MVP2_PAIR_AUDIT="$RUN/audit" MVP2_PAIR_PYTHON="$PY" \
  bash scripts/submit_mvp2_pair_preflight.sh
collect_existing "$RUN"
