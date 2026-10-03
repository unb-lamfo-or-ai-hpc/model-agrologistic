#!/bin/bash
# Submit one positive-control pair only after review of original NPAD evidence.
set -euo pipefail
: "${MVP2_SOLVE_CHECKOUT:?Set the new detached checkout}"
: "${MVP2_SOLVE_PLAN:?Set the new solve_plan.json}"
MVP2_SOLVE_PYTHON="${MVP2_SOLVE_PYTHON:-/home/vrrcelestino/venv313/bin/python}"
stop() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
cd "$MVP2_SOLVE_CHECKOUT"
if ! tracked_status="$(git status --porcelain --untracked-files=no)"; then
  stop "Cannot inspect source; no job submitted."
fi
if [ -n "$tracked_status" ]; then
  printf '%s\n' "$tracked_status" >&2
  stop "Tracked source changed; preserve changes and do not bypass admission."
fi
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
unset SCIPOPTDIR SBATCH_QOS
export MVP2_SOLVE_CHECKOUT MVP2_SOLVE_PLAN MVP2_SOLVE_PYTHON
MVP2_SOLVE_SOURCE="$(git rev-parse HEAD)"
export MVP2_SOLVE_SOURCE
"$MVP2_SOLVE_PYTHON" scripts/admit_mvp2_resource_pair.py --solve-plan "$MVP2_SOLVE_PLAN" --check
MVP2_SOLVE_TOOLS="$("$MVP2_SOLVE_PYTHON" scripts/admit_mvp2_resource_pair.py \
  --solve-plan "$MVP2_SOLVE_PLAN" --tool-identity)"
export MVP2_SOLVE_TOOLS
MVP2_SOLVE_DIRECTORY="$(dirname "$MVP2_SOLVE_PLAN")"
test ! -e "$MVP2_SOLVE_DIRECTORY/.submission-claimed" || stop "Pair already claimed; no duplicate job."
bash -n scripts/run_mvp2_resource_pair.slurm
options=(--account=sxdsouza --partition=intel-256 --nodes=1 --ntasks=1
  --cpus-per-task=4 --mem=192G --time=18:00:00 --job-name=mvp2-h215-pair
  --export=ALL --chdir="$MVP2_SOLVE_CHECKOUT" --output="$MVP2_SOLVE_DIRECTORY/slurm-%j.out")
sbatch --test-only "${options[@]}" scripts/run_mvp2_resource_pair.slurm
mkdir "$MVP2_SOLVE_DIRECTORY/.submission-claimed"
printf '%s\n' "$MVP2_SOLVE_SOURCE" > "$MVP2_SOLVE_DIRECTORY/source_commit.txt"
printf '%s\n' "$MVP2_SOLVE_TOOLS" > "$MVP2_SOLVE_DIRECTORY/tool_hashes.json"
job="$(sbatch --parsable "${options[@]}" scripts/run_mvp2_resource_pair.slurm)"
printf 'MVP2_PAIR_SOLVE_JOB=%s\n' "$job" | tee "$MVP2_SOLVE_DIRECTORY/submission.txt"
printf 'Execution directory: %s\n' "$MVP2_SOLVE_DIRECTORY"
