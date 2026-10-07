#!/usr/bin/env bash
# One descriptive serial pair; immutable checkout and durable submission claim.
set -euo pipefail
: "${H300_PAIR_CHECKOUT:?Set immutable detached checkout}"
: "${H300_PAIR_PLAN:?Set new pair_plan.json}"
H300_PAIR_PYTHON=${H300_PAIR_PYTHON:-/home/vrrcelestino/venv313/bin/python}
cd "$H300_PAIR_CHECKOUT"
tracked=$(git status --porcelain --untracked-files=no)
test -z "$tracked"
test -z "$(git symbolic-ref -q HEAD || true)"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic
unset SCIPOPTDIR SBATCH_QOS SLURM_ARRAY_TASK_ID SLURM_ARRAY_JOB_ID
"$H300_PAIR_PYTHON" scripts/probe_npad_gurobi_license.py --check-file
"$H300_PAIR_PYTHON" scripts/mvp2_h300_pair.py --plan "$H300_PAIR_PLAN" --check
H300_PAIR_SOURCE=$(git rev-parse HEAD)
H300_PAIR_TOOLS=$("$H300_PAIR_PYTHON" scripts/mvp2_h300_pair.py --plan "$H300_PAIR_PLAN" --tool-identity)
export H300_PAIR_CHECKOUT H300_PAIR_PLAN H300_PAIR_PYTHON H300_PAIR_SOURCE H300_PAIR_TOOLS
H300_PAIR_EXECUTION=$(dirname "$H300_PAIR_PLAN")
bash -n scripts/run_mvp2_h300_pair.slurm
options=(--account=sxdsouza --partition=intel-256 --nodes=1 --ntasks=1
  --cpus-per-task=4 --mem=192G --time=18:00:00 --job-name=mvp2-h300-s1a-pair
  --export=ALL --chdir="$H300_PAIR_CHECKOUT" --output="$H300_PAIR_EXECUTION/slurm-%j.out")
sbatch --test-only "${options[@]}" scripts/run_mvp2_h300_pair.slurm
mkdir "$H300_PAIR_EXECUTION/.submission-claimed"
printf '%s\n' "$H300_PAIR_SOURCE" > "$H300_PAIR_EXECUTION/source_commit.txt"
printf '%s\n' "$H300_PAIR_TOOLS" > "$H300_PAIR_EXECUTION/tool_hashes.json"
job=$(sbatch --parsable "${options[@]}" scripts/run_mvp2_h300_pair.slurm)
[[ "$job" =~ ^[0-9]+$ ]] || { printf 'STOP: ambiguous submission; preserve claim and inspect Slurm.\n' >&2; exit 1; }
printf 'MVP2_H300_PAIR_JOB=%s\n' "$job" | tee "$H300_PAIR_EXECUTION/submission.txt"
printf 'Execution directory: %s\n' "$H300_PAIR_EXECUTION"
