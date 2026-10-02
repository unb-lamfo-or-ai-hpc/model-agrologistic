#!/bin/bash
# Run with bash, never source: failures must not close the interactive terminal.
# Submit one reviewed case; no automatic escalation or dependency chain.
set -euo pipefail
PROJECT_ROOT="${PROJECT_ROOT:-/home/vrrcelestino/model-agrologistic}"
PYTHON="${PYTHON:-/home/vrrcelestino/venv313/bin/python}"
: "${SPRINT_A_EXPECTED_COMMIT:?Set the reviewed full Git commit SHA}"
CASE="${1:-h400-direct}"
case "$CASE" in
  h400-direct|h400-warehouse)
    BASELINE=nine-connectivity-h400-20260916T123635Z ;;
  h300-warehouse)
    BASELINE=nine-connectivity-h300-20260915T150139Z ;;
  *) printf 'Unsupported Sprint A case: %s\n' "$CASE" >&2; exit 2 ;;
esac
cd "$PROJECT_ROOT"
test "$(git branch --show-current)" = research/stagewise-root-diagnostics
test "$(git rev-parse HEAD)" = "$SPRINT_A_EXPECTED_COMMIT"
test -z "$(git status --porcelain)"
test -x "$PYTHON"
export PYTHON PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE="$PROJECT_ROOT/secrets/gurobi.lic"
export STAGEWISE_SOURCE_COMMIT="$SPRINT_A_EXPECTED_COMMIT"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
QUALITY_DIR="$PROJECT_ROOT/data/results/validation/sprint-a-all-barrier-$STAMP"
CAMPAIGN_ROOT="$PROJECT_ROOT/data/results/hpc/sprint-a-$CASE-all-barrier-$STAMP"
mkdir -p "$(dirname "$QUALITY_DIR")"
mkdir "$QUALITY_DIR"
"$PYTHON" -m ruff check . | tee "$QUALITY_DIR/ruff.log"
"$PYTHON" -m pytest tests/test_stagewise_root.py tests/test_nine_audit.py \
  tests/test_experiment_runner.py --junitxml "$QUALITY_DIR/pytest.xml" \
  | tee "$QUALITY_DIR/pytest.log"
"$PYTHON" scripts/prepare_stagewise_campaign.py \
  --check-licensed-junit "$QUALITY_DIR/pytest.xml"
"$PYTHON" scripts/prepare_stagewise_campaign.py \
  --baseline-manifest "$PROJECT_ROOT/data/results/hpc/$BASELINE/campaign.yaml" \
  --campaign-root "$CAMPAIGN_ROOT" --case "$CASE" --profile all-barrier
export STAGEWISE_MANIFEST="$CAMPAIGN_ROOT/campaign.yaml"
"$PYTHON" scripts/prepare_stagewise_campaign.py \
  --check-manifest "$STAGEWISE_MANIFEST" --require-profile all-barrier
test "$(git rev-parse HEAD)" = "$SPRINT_A_EXPECTED_COMMIT"
test -z "$(git status --porcelain)"
sbatch --test-only --account=sxdsouza --export=ALL scripts/run_stagewise_root.slurm
JOB_ID="$(sbatch --parsable --account=sxdsouza --export=ALL scripts/run_stagewise_root.slurm)"
printf 'Job: %s\nCampaign: %s\nQuality: %s\nSource: %s\n' \
  "$JOB_ID" "$CAMPAIGN_ROOT" "$QUALITY_DIR" "$STAGEWISE_SOURCE_COMMIT" \
  | tee "$CAMPAIGN_ROOT/submission.txt"
