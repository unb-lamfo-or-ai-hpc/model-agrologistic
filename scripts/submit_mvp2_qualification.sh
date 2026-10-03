#!/bin/bash
# Run on the login node, from a new checkout; never mutate a running campaign.
set -euo pipefail
: "${MVP2_CHECKOUT:?Set the new source checkout}"
: "${MVP2_REPORT:?Set an existing, empty qualification parent directory}"
MVP2_PYTHON="${MVP2_PYTHON:-/home/vrrcelestino/venv313/bin/python}"
cd "$MVP2_CHECKOUT"
test -d "$MVP2_REPORT"
test ! -e "$MVP2_REPORT/.submission-claimed"
test -z "$(git status --porcelain --untracked-files=no)"
export MVP2_CHECKOUT MVP2_REPORT MVP2_PYTHON
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
unset SCIPOPTDIR SBATCH_QOS
MVP2_SOURCE="$(git rev-parse HEAD)"
MVP2_IDENTITY="$("$MVP2_PYTHON" -c 'from src.logic.run_integrity import implementation_identity; print(implementation_identity()["sha256"])')"
export MVP2_SOURCE MVP2_IDENTITY
printf '%s\n' "$MVP2_SOURCE" > "$MVP2_REPORT/source_commit.txt"
printf '%s\n' "$MVP2_IDENTITY" > "$MVP2_REPORT/implementation_sha256.txt"
bash -n scripts/run_mvp2_qualification.slurm
options=(--account=sxdsouza --partition=intel-256 --nodes=1 --ntasks=1
  --cpus-per-task=2 --mem=16G --time=00:30:00 --job-name=mvp2-qual
  --export=ALL --chdir="$MVP2_CHECKOUT" --output="$MVP2_REPORT/slurm-%j.out")
sbatch --test-only "${options[@]}" scripts/run_mvp2_qualification.slurm
mkdir "$MVP2_REPORT/.submission-claimed"
job="$(sbatch --parsable "${options[@]}" scripts/run_mvp2_qualification.slurm)"
printf 'MVP2_QUALIFICATION_JOB=%s\n' "$job" | tee "$MVP2_REPORT/submission.txt"
printf 'Report: %s/qualification/qualification_report.json\n' "$MVP2_REPORT"
