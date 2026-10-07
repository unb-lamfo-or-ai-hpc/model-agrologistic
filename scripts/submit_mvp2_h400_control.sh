#!/usr/bin/env bash
# One immutable h400 control, never an array or repeated campaign.
set -euo pipefail
: "${H400_CHECKOUT:?}" "${H400_PLAN:?}"
H400_PYTHON=${H400_PYTHON:-/home/vrrcelestino/venv313/bin/python}
cd "$H400_CHECKOUT"
test -z "$(git status --porcelain --untracked-files=no)"
test -z "$(git symbolic-ref -q HEAD || true)"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic
unset SCIPOPTDIR SBATCH_QOS SLURM_ARRAY_TASK_ID SLURM_ARRAY_JOB_ID
H400_SOURCE=$(git rev-parse HEAD)
"$H400_PYTHON" scripts/probe_npad_gurobi_license.py --check-file
"$H400_PYTHON" scripts/mvp2_h400_control.py --plan "$H400_PLAN" --check --source-commit "$H400_SOURCE"
H400_TOOLS=$("$H400_PYTHON" scripts/mvp2_h400_control.py --plan "$H400_PLAN" --tool-identity)
export H400_CHECKOUT H400_PLAN H400_PYTHON H400_SOURCE H400_TOOLS
H400_EXECUTION=$(dirname "$H400_PLAN")
bash -n scripts/run_mvp2_h400_control.slurm
options=(--account=sxdsouza --partition=intel-256 --nodes=1 --ntasks=1
  --cpus-per-task=4 --mem=192G --time=12:00:00 --job-name=mvp2-h400-control
  --export=ALL --chdir="$H400_CHECKOUT" --output="$H400_EXECUTION/slurm-%j.out")
sbatch --test-only "${options[@]}" scripts/run_mvp2_h400_control.slurm
mkdir "$H400_EXECUTION/.submission-claimed"
printf '%s\n' "$H400_SOURCE" > "$H400_EXECUTION/source_commit.txt"
printf '%s\n' "$H400_TOOLS" > "$H400_EXECUTION/tool_hashes.json"
submitted=$(sbatch --parsable "${options[@]}" scripts/run_mvp2_h400_control.slurm)
job_pattern='^[0-9]+(;[A-Za-z0-9._-]+)?$'
[[ "$submitted" =~ $job_pattern ]] || { printf 'STOP: ambiguous submission; preserve claim.\n' >&2; exit 1; }
job=${submitted%%;*}
printf 'MVP2_H400_CONTROL_JOB=%s\n' "$job" | tee "$H400_EXECUTION/submission.txt"
printf 'Execution directory: %s\n' "$H400_EXECUTION"
