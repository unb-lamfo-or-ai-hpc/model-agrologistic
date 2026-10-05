#!/usr/bin/env bash
# One explicitly reviewed h300 control, never a pair or an array.
set -euo pipefail
: "${H300_CHECKOUT:?Set immutable detached checkout}"
: "${H300_PLAN:?Set new baseline_plan.json}"
H300_PYTHON=${H300_PYTHON:-/home/vrrcelestino/venv313/bin/python}
cd "$H300_CHECKOUT"
tracked=$(git status --porcelain --untracked-files=no)
test -z "$tracked"
test -z "$(git symbolic-ref -q HEAD || true)"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic
unset SCIPOPTDIR SBATCH_QOS SLURM_ARRAY_TASK_ID SLURM_ARRAY_JOB_ID
"$H300_PYTHON" scripts/probe_npad_gurobi_license.py --check-file
"$H300_PYTHON" scripts/mvp2_h300_baseline.py --plan "$H300_PLAN" --check
H300_SOURCE=$(git rev-parse HEAD)
H300_TOOLS=$("$H300_PYTHON" scripts/mvp2_h300_baseline.py --plan "$H300_PLAN" --tool-identity)
export H300_CHECKOUT H300_PLAN H300_PYTHON H300_SOURCE H300_TOOLS
H300_EXECUTION=$(dirname "$H300_PLAN")
bash -n scripts/run_mvp2_h300_baseline.slurm
options=(--account=sxdsouza --partition=intel-256 --nodes=1 --ntasks=1
  --cpus-per-task=4 --mem=192G --time=12:00:00 --job-name=mvp2-h300-baseline
  --export=ALL --chdir="$H300_CHECKOUT" --output="$H300_EXECUTION/slurm-%j.out")
sbatch --test-only "${options[@]}" scripts/run_mvp2_h300_baseline.slurm
mkdir "$H300_EXECUTION/.submission-claimed"
printf '%s\n' "$H300_SOURCE" > "$H300_EXECUTION/source_commit.txt"
printf '%s\n' "$H300_TOOLS" > "$H300_EXECUTION/tool_hashes.json"
job=$(sbatch --parsable "${options[@]}" scripts/run_mvp2_h300_baseline.slurm)
[[ "$job" =~ ^[0-9]+$ ]] || { printf 'STOP: ambiguous submission; preserve claim and inspect Slurm.\n' >&2; exit 1; }
printf 'MVP2_H300_BASELINE_JOB=%s\n' "$job" | tee "$H300_EXECUTION/submission.txt"
printf 'Execution directory: %s\n' "$H300_EXECUTION"
