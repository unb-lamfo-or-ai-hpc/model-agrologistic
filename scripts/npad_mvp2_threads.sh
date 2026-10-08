#!/usr/bin/env bash
# Durable one-shot qualification. Repeating start only collects an existing job.
set -euo pipefail
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
S2_PYTHON=/home/vrrcelestino/venv313/bin/python
CLAIM="$BASE/.mvp2-threads-qualification-s2"
stop() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
[[ ${1:-} == start && ${2:-} =~ ^[0-9a-f]{40}$ && $# == 2 ]] || \
  stop 'Usage: bash npad_mvp2_threads.sh start FULL_REVIEWED_SHA'
SOURCE_SHA=$2
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
unset SCIPOPTDIR SBATCH_QOS
if mkdir "$CLAIM" 2>/dev/null; then
  RUN=$(mktemp -d "$BASE/mvp2-threads-s2-XXXXXXXX")
  printf '%s\n' "$RUN" > "$CLAIM/run.txt"
  printf '%s\n' "$SOURCE_SHA" > "$CLAIM/source.txt"
  printf 'PRESERVE_RUN=%s\n' "$RUN"
  git clone --no-checkout https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$RUN/source"
  git -C "$RUN/source" config core.autocrlf false
  printf '%s\n' '/manuscript/comparison_provenance.json -text' \
    '/manuscript/figures/runtime_memory_comparison.pdf -text' > "$RUN/source/.git/info/attributes"
  git -C "$RUN/source" checkout --detach "$SOURCE_SHA"
  S2_CHECKOUT="$RUN/source"
  cd "$S2_CHECKOUT"
  test "$(git rev-parse HEAD)" = "$SOURCE_SHA"
  test -z "$(git status --porcelain --untracked-files=no)"
  "$S2_PYTHON" - <<'PY'
import subprocess
from pathlib import Path
records = subprocess.check_output(["git", "ls-files", "-s", "-z"]).split(b"\0")
count = 0
for record in filter(None, records):
    metadata, name = record.split(b"\t", 1)
    mode, expected, stage = metadata.split()
    if stage != b"0" or mode not in (b"100644", b"100755"):
        raise SystemExit("STOP: unsupported tracked entry")
    observed = subprocess.check_output(["git", "hash-object", "--no-filters", "--stdin"],
                                       input=Path(name.decode()).read_bytes()).strip()
    if observed != expected:
        raise SystemExit(f"STOP: raw HEAD bytes differ: {name.decode()}")
    count += 1
print(f"Raw HEAD-byte gate: {count} tracked files identical.")
PY
  "$S2_PYTHON" -m ruff check .
  "$S2_PYTHON" -m pytest -q tests/test_mvp2_threads.py --junitxml "$RUN/focused-tests.xml"
  "$S2_PYTHON" - "$RUN/focused-tests.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET
suites = list(ET.parse(sys.argv[1]).getroot().iter("testsuite"))
counts = {key: sum(int(s.get(key, "0")) for s in suites)
          for key in ("tests", "failures", "errors", "skipped")}
if counts["tests"] < 20 or any(counts[k] for k in ("failures", "errors", "skipped")):
    raise SystemExit(f"STOP: failed or skipped focused qualification: {counts}")
print(f"NPAD S2 regression gate: {counts}")
PY
  S2_OUTPUT="$RUN/qualification"
  "$S2_PYTHON" scripts/mvp2_threads.py prepare --output "$S2_OUTPUT" --source "$SOURCE_SHA"
  "$S2_PYTHON" scripts/probe_npad_gurobi_license.py --check-file
  bash -n scripts/run_mvp2_threads.slurm
  export S2_CHECKOUT S2_OUTPUT S2_PYTHON
  options=(--account=sxdsouza --partition=intel-256 --nodes=1 --ntasks=1
    --cpus-per-task=16 --mem=16G --time=00:30:00 --job-name=mvp2-threads-mini
    --export=ALL --chdir="$S2_CHECKOUT" --output="$RUN/slurm-%j.out")
  sbatch --test-only "${options[@]}" scripts/run_mvp2_threads.slurm
  mkdir "$S2_OUTPUT/.submission-claimed"
  submitted=$(sbatch --parsable "${options[@]}" scripts/run_mvp2_threads.slurm)
  job_pattern='^[0-9]+(;[A-Za-z0-9._-]+)?$'
  [[ "$submitted" =~ $job_pattern ]] || stop 'Ambiguous sbatch; preserve claim, do not resubmit'
  JOB=${submitted%%;*}
  "$S2_PYTHON" - "$S2_OUTPUT" "$JOB" "$SOURCE_SHA" <<'PY'
import json
import sys
from pathlib import Path
with (Path(sys.argv[1]) / "submission.json").open("x", encoding="utf-8") as stream:
    json.dump({"job_id": sys.argv[2], "source_commit": sys.argv[3]}, stream)
PY
else
  test -f "$CLAIM/run.txt" && test -f "$CLAIM/source.txt" || stop 'Incomplete claim; preserve it for diagnosis'
  test "$(< "$CLAIM/source.txt")" = "$SOURCE_SHA" || stop 'Existing claim uses another source; no resubmission'
  RUN=$(< "$CLAIM/run.txt")
fi
RUN=$(realpath "$RUN")
[[ "$RUN" == "$BASE"/mvp2-threads-s2-* ]] || stop 'Run escaped its isolated root'
S2_CHECKOUT="$RUN/source"
S2_OUTPUT="$RUN/qualification"
test "$(git -C "$S2_CHECKOUT" rev-parse HEAD)" = "$SOURCE_SHA"
test -z "$(git -C "$S2_CHECKOUT" status --porcelain --untracked-files=no)"
cd "$S2_CHECKOUT"
test -f "$S2_OUTPUT/submission.json" || stop 'No submission receipt; preserve ambiguous claim, do not resubmit'
JOB=$("$S2_PYTHON" - "$S2_OUTPUT/submission.json" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["job_id"])
PY
)
[[ "$JOB" =~ ^[0-9]+$ ]] || stop 'Invalid job identity'
printf 'PRESERVE_RUN=%s\nJOB=%s\nRepeat this same start command to collect, never resubmit.\n' "$RUN" "$JOB"
while true; do
  accounting=$(sacct -j "$JOB" --noheader --parsable2 --format=JobIDRaw,State,ExitCode,Elapsed,MaxRSS)
  if "$S2_PYTHON" - "$accounting" "$JOB" <<'PY'
import sys
from scripts.collect_mvp2_pair_preflight import terminal_accounting
try:
    terminal_accounting(sys.argv[1], sys.argv[2])
except ValueError:
    raise SystemExit(1)
PY
  then break; fi
  printf '%s job=%s nonterminal/accounting pending; Ctrl-C is safe\n' "$(date -u +%FT%TZ)" "$JOB"
  sleep 20
done
COLLECTION=$(mktemp -d "$RUN/collection-XXXXXXXX")
printf '%s\n' "$accounting" > "$COLLECTION/accounting.txt"
cd "$S2_CHECKOUT"
"$S2_PYTHON" scripts/mvp2_threads.py collect --output "$S2_OUTPUT" \
  --accounting "$COLLECTION/accounting.txt" --destination "$COLLECTION/evidence"
