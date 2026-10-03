#!/bin/bash
# Standalone preflight only. Preserve the prepared pair and qualified runtime.
set -euo pipefail
: "${MVP2_PAIR_CHECKOUT:?Set the new detached checkout}"
: "${MVP2_PAIR_PLAN:?Set the original resource_contrast_plan.json}"
: "${MVP2_PAIR_AUDIT:?Set an existing empty audit parent}"
MVP2_PAIR_PYTHON="${MVP2_PAIR_PYTHON:-/home/vrrcelestino/venv313/bin/python}"
cd "$MVP2_PAIR_CHECKOUT"
stop() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
test -d "$MVP2_PAIR_AUDIT" || stop "Audit parent does not exist: $MVP2_PAIR_AUDIT"
test -z "$(ls -A "$MVP2_PAIR_AUDIT")" || stop "Audit parent is not empty: $MVP2_PAIR_AUDIT"
if ! tracked_status="$(git status --porcelain --untracked-files=no)"; then
  stop "Cannot inspect tracked checkout status; no job was submitted."
fi
if [ -n "$tracked_status" ]; then
  printf '%s\n' "$tracked_status" >&2
  stop "Tracked checkout differs from its pinned commit; no job was submitted. Preserve changes; do not bypass this gate."
fi
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
unset SCIPOPTDIR SBATCH_QOS
export MVP2_PAIR_CHECKOUT MVP2_PAIR_PLAN MVP2_PAIR_AUDIT MVP2_PAIR_PYTHON
MVP2_PAIR_SOURCE="$(git rev-parse HEAD)"
export MVP2_PAIR_SOURCE
"$MVP2_PAIR_PYTHON" scripts/preflight_mvp2_resource_pair.py --plan "$MVP2_PAIR_PLAN" --check
MVP2_PAIR_TOOLS="$("$MVP2_PAIR_PYTHON" scripts/preflight_mvp2_resource_pair.py \
  --plan "$MVP2_PAIR_PLAN" --tool-identity)"
export MVP2_PAIR_TOOLS
bash -n scripts/run_mvp2_pair_preflight.slurm
options=(--account=sxdsouza --partition=intel-256 --nodes=1 --ntasks=1
  --cpus-per-task=4 --mem=16G --time=00:30:00 --job-name=mvp2-pair-input
  --export=ALL --chdir="$MVP2_PAIR_CHECKOUT" --output="$MVP2_PAIR_AUDIT/slurm-%j.out")
sbatch --test-only "${options[@]}" scripts/run_mvp2_pair_preflight.slurm
mkdir "$MVP2_PAIR_AUDIT/.submission-claimed"
printf '%s\n' "$MVP2_PAIR_SOURCE" > "$MVP2_PAIR_AUDIT/source_commit.txt"
printf '%s\n' "$MVP2_PAIR_TOOLS" > "$MVP2_PAIR_AUDIT/tool_hashes.json"
job="$(sbatch --parsable "${options[@]}" scripts/run_mvp2_pair_preflight.slurm)"
printf 'MVP2_PAIR_PREFLIGHT_JOB=%s\n' "$job" | tee "$MVP2_PAIR_AUDIT/submission.txt"
printf 'Report: %s/preflight/pair_preflight.json\n' "$MVP2_PAIR_AUDIT"
