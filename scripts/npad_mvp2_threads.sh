#!/usr/bin/env bash
# Durable one-shot qualification. Repeating start only collects an existing job.
set -euo pipefail
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
S2_PYTHON=/home/vrrcelestino/venv313/bin/python
CLAIM="$BASE/.mvp2-threads-qualification-s2"
stop() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
[[ ${1:-} =~ ^(start|recover-login)$ && ${2:-} =~ ^[0-9a-f]{40}$ && $# == 2 ]] || \
  stop 'Usage: bash npad_mvp2_threads.sh {start|recover-login} FULL_REVIEWED_SHA'
SOURCE_SHA=$2
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic
unset SCIPOPTDIR SBATCH_QOS
RECOVERY_RECEIPT=''
if [[ $1 == recover-login ]]; then
  ORIGINAL_SHA=0360c25c2486daf99c223ca18f6bf80cb2af8238
  [[ "$SOURCE_SHA" != "$ORIGINAL_SHA" ]] || stop 'Recovery requires the reviewed fixed source'
  CLAIM="$BASE/.mvp2-threads-qualification-s2-login-recovery"
  if [[ ! -e "$CLAIM" ]]; then
    RECOVERY_RECEIPT=$("$S2_PYTHON" - "$BASE" "$ORIGINAL_SHA" <<'PY_RECOVERY'
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def recovery_gate(base, original_sha, command=subprocess.check_output):
    claim = base / ".mvp2-threads-qualification-s2"
    original = base / "mvp2-threads-s2-GXnpz4Ln"
    def stop(message):
        raise ValueError(message)
    if (claim.is_symlink() or original.is_symlink() or
            any((claim / name).is_symlink() for name in ("run.txt", "source.txt"))):
        stop("Symlinked original claim/run")
    if {p.name for p in claim.iterdir()} != {"run.txt", "source.txt"}:
        stop("Unexpected original claim products")
    if Path((claim / "run.txt").read_text().strip()).resolve() != original.resolve():
        stop("Original run identity differs")
    if (claim / "source.txt").read_text().strip() != original_sha:
        stop("Original source identity differs")
    if {p.name for p in original.iterdir()} != {"source", "qualification", "focused-tests.xml"}:
        stop("Unexpected original bootstrap/submission products")
    output = original / "qualification"
    if output.is_symlink() or {p.name for p in output.iterdir()} != {"plan.json"}:
        stop("Submission/execution or ambiguous qualification products exist")
    source = original / "source"
    if source.is_symlink() or (output / "plan.json").is_symlink() or (
            original / "focused-tests.xml").is_symlink():
        stop("Linked original evidence")
    def git(*args):
        return command(["git", "-C", str(source), *args]).strip()
    if git("rev-parse", "HEAD").decode() != original_sha or git(
            "status", "--porcelain", "--untracked-files=no"):
        stop("Original checkout identity/status differs")
    for record in filter(None, git("ls-files", "-s", "-z").split(b"\0")):
        metadata, name = record.split(b"\t", 1)
        mode, expected, stage = metadata.split()
        path = source / name.decode()
        if stage != b"0" or mode not in (b"100644", b"100755") or path.is_symlink():
            stop("Unsupported original tracked entry")
        observed = command(["git", "hash-object", "--no-filters", "--stdin"],
                           input=path.read_bytes()).strip()
        if observed != expected:
            stop("Original raw HEAD bytes differ")
    suites = list(ET.parse(original / "focused-tests.xml").getroot().iter("testsuite"))
    counts = {k: sum(int(s.get(k, "0")) for s in suites)
              for k in ("tests", "failures", "errors", "skipped")}
    if counts != {"tests": 56, "failures": 0, "errors": 0, "skipped": 0}:
        stop("Original regression receipt differs")
    processes = command(["ps", "-eo", "pid=,ppid=,args="]).decode().splitlines()
    rows = [row.strip().split(None, 2) for row in processes if row.strip()]
    ancestors = {os.getpid()}
    while True:
        parents = {int(row[1]) for row in rows if len(row) == 3 and int(row[0]) in ancestors}
        if parents <= ancestors:
            break
        ancestors |= parents
    for row in rows:
        if len(row) != 3:
            stop("Ambiguous process observation")
        if int(row[0]) not in ancestors and (str(original) in row[2] or
                                           "npad_mvp2_threads.sh start" in row[2]):
            stop("Original bootstrap/process is still active")
    queue = command(["squeue", "--me", "--noheader", "--format=%i|%j|%T|%Z"]).decode()
    for row in queue.splitlines():
        fields = row.split("|")
        if len(fields) != 4 or "mvp2-threads" in fields[1] or str(original) in fields[3]:
            stop("Active or ambiguous S2 scheduler observation")
    # Import only after every tracked byte in the immutable old source was checked.
    sys.path.insert(0, str(source))
    from scripts import mvp2_threads as previous
    plan = previous.check(output)
    if plan["source_commit"] != original_sha:
        stop("Original plan source differs")
    return {"schema_version": "s2-login-recovery-v1", "status": "pre_submission_only",
            "original_run": str(original), "original_source": original_sha,
            "original_tests": counts, "active_original_processes": False,
            "active_s2_jobs": False, "original_submission_products": False,
            "original_plan_sha256": hashlib.sha256((output / "plan.json").read_bytes()).hexdigest(),
            "original_tests_sha256": hashlib.sha256(
                (original / "focused-tests.xml").read_bytes()).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(recovery_gate(Path(sys.argv[1]), sys.argv[2]), sort_keys=True))
PY_RECOVERY
    )
  fi
fi
if mkdir "$CLAIM" 2>/dev/null; then
  RUN=$(mktemp -d "$BASE/mvp2-threads-s2-XXXXXXXX")
  printf '%s\n' "$RUN" > "$CLAIM/run.txt"
  printf '%s\n' "$SOURCE_SHA" > "$CLAIM/source.txt"
  if [[ -n "$RECOVERY_RECEIPT" ]]; then
    printf '%s\n' "$RECOVERY_RECEIPT" > "$RUN/login-recovery.json"
    printf 'Original attempt preserved; verified pre-submission recovery only.\n'
  fi
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
