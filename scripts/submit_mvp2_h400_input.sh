#!/usr/bin/env bash
# One input-only job. This is not an h400 solve submitter.
set -euo pipefail
: "${H400_INPUT_CHECKOUT:?Set the pinned checkout}"
: "${H400_INPUT_PLAN:?Set the input-only plan}"
: "${H400_INPUT_AUDIT:?Set a new empty audit parent}"
H400_INPUT_PYTHON=${H400_INPUT_PYTHON:-/home/vrrcelestino/venv313/bin/python}
stop() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
cd "$H400_INPUT_CHECKOUT"
test -d "$H400_INPUT_AUDIT" && test -z "$(ls -A "$H400_INPUT_AUDIT")" || stop "Audit must be empty"
tracked=$(git status --porcelain --untracked-files=no)
test -z "$tracked" || stop "Tracked checkout changed; preserve changes"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
unset SCIPOPTDIR SBATCH_QOS
H400_INPUT_SOURCE=$(git rev-parse HEAD)
export H400_INPUT_CHECKOUT H400_INPUT_PLAN H400_INPUT_AUDIT H400_INPUT_PYTHON H400_INPUT_SOURCE
"$H400_INPUT_PYTHON" scripts/mvp2_h400_input.py check --plan "$H400_INPUT_PLAN"
"$H400_INPUT_PYTHON" - "$H400_INPUT_PLAN" "$H400_INPUT_SOURCE" <<'PY'
import json
import sys
from pathlib import Path
if json.loads(Path(sys.argv[1]).read_text())["source_commit"] != sys.argv[2]:
    raise SystemExit("STOP: source commit differs")
PY
bash -n scripts/run_mvp2_h400_input.slurm
options=(--account=sxdsouza --partition=intel-256 --nodes=1 --ntasks=1
  --cpus-per-task=4 --mem=16G --time=00:30:00 --job-name=mvp2-h400-input
  --export=ALL --chdir="$H400_INPUT_CHECKOUT" --output="$H400_INPUT_AUDIT/slurm-%j.out")
sbatch --test-only "${options[@]}" scripts/run_mvp2_h400_input.slurm
mkdir "$H400_INPUT_AUDIT/.submission-claimed"
printf '%s\n' "$H400_INPUT_SOURCE" > "$H400_INPUT_AUDIT/source_commit.txt"
"$H400_INPUT_PYTHON" - "$H400_INPUT_PLAN" "$H400_INPUT_AUDIT/tool_hashes.json" <<'PY'
import json
import sys
from pathlib import Path
with Path(sys.argv[2]).open("x") as stream:
    stream.write(json.dumps(json.loads(Path(sys.argv[1]).read_text())["tools"], indent=2) + "\n")
PY
submitted=$(sbatch --parsable "${options[@]}" scripts/run_mvp2_h400_input.slurm)
job_pattern='^[0-9]+(;[A-Za-z0-9._-]+)?$'
[[ "$submitted" =~ $job_pattern ]] || stop "Ambiguous submission; preserve claim, do not resubmit"
job=${submitted%%;*}
printf 'MVP2_H400_INPUT_JOB=%s\n' "$job" | tee "$H400_INPUT_AUDIT/submission.txt"
printf 'Report: %s/preflight/input_preflight.json\n' "$H400_INPUT_AUDIT"
