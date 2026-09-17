# Controlled dual-simplex sensitivity at 400 hubs

## Rationale and scope

The original 400-hub cases have independently valid zero-shortfall incumbents but stop in the capacity-stage root relaxation with `MEM_LIMIT`, a zero bound and 100% gap. The logs explicitly identify deterministic concurrent LP optimization. The supplied manifest does not explicitly set `Method`; the observed algorithm must not be confused with a user-configured Method=4.

Test **Method=1 (dual simplex)** as the sole solver-parameter intervention. Gurobi documents lower memory use for dual simplex than concurrent continuous optimization. This motivates a hypothesis, not a guarantee of lower runtime, reduced peak memory, or convergence. Retain four allocated CPUs/solver threads, seed42, NumericFocus1, SoftMemLimit128 decimalGB, a 28,800-second total optimization budget, 10% relative gap, the objective hierarchy and every data/model option. Do not set MultiObjMethod, NodeMethod, NodefileStart or an increased memory limit in the same comparison. All optimizer implementation files remain unchanged.

Start with the direct-enabled case only (index1), which is the larger-population extension of the accepted 300-hub direct case. Index0 (warehouse-only) remains explicitly unsubmitted pending this diagnostic. This selection is adaptive, not a randomized performance comparison. Preserve the original automatic-method cases, including their memory-censored outcomes. Do not proceed to500hubs from this protocol.

The preparer clones the original on-disk YAML rather than reconstructing it from the current template or the indentation-distorted chat copy. It checks the original manifest and workbook hashes, refuses output reuse or nesting inside the baseline, and writes a sensitivity receipt. Semantic differences are limited to Method, names suffixed `_dual`, and the new output directory. A method change alters experiment identity while the mathematical and implementation contracts remain fixed.

## NPAD commands

Run once. A failed command stops the subshell, not the interactive terminal. Keep the printed paths and jobIDs; do not blindly repeat a partially successful submission.

```bash
(
set -e
cd /home/vrrcelestino/model-agrologistic
test -z "$(git status --porcelain)"
git switch research/pilot-readiness-curation
git pull --ff-only origin research/pilot-readiness-curation
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE="$PWD/secrets/gurobi.lic"
PYTHON=/home/vrrcelestino/venv313/bin/python
"$PYTHON" -m pytest tests/test_h400_dual_sensitivity.py tests/test_nine_campaign.py tests/test_nine_audit.py tests/test_release_readiness.py

BASELINE="$PWD/data/results/hpc/nine-connectivity-h400-20260916T123635Z/campaign.yaml"
export H400_DUAL="$PWD/data/results/hpc/nine-connectivity-h400-dual-$(date -u +%Y%m%dT%H%M%SZ)"
"$PYTHON" scripts/prepare_h400_dual_sensitivity.py \
  --baseline-manifest "$BASELINE" \
  --campaign-root "$H400_DUAL" \
  --expected-manifest-sha256 cd12b2caf6e013ebcb6c0008a1d222c8f95951c13c7ccf56bc25df3d0aa45092 \
  --expected-workbook-sha256 c3085456997714ef5a8bdbf61e2c9a5e578c2636003947427cf58933d21ceb13
export NINE_MANIFEST="$H400_DUAL/campaign.yaml"

# The existing array wrapper performs mandatory preflight before optimization.
DUAL_JOB="$(sbatch --parsable \
  --account=sxdsouza --qos=preempt --partition=intel-256 \
  --job-name=h400-dual --cpus-per-task=4 --mem=192G --time=12:00:00 \
  --array=1 --export=ALL --output="$H400_DUAL/solve-%A_%a.log" \
  scripts/run_nine_connectivity.slurm)"
printf 'Campaign: %s\nDirect-enabled dual job: %s\n' "$H400_DUAL" "$DUAL_JOB"

DUAL_AUDIT="$(sbatch --parsable \
  --account=sxdsouza --qos=preempt --partition=intel-256 \
  --job-name=h400-dual-audit --cpus-per-task=4 --mem=16G --time=00:30:00 \
  --dependency="afterany:$DUAL_JOB" --export=ALL \
  --output="$H400_DUAL/audit-%j.log" \
  --wrap='set -eu
    cd /home/vrrcelestino/model-agrologistic
    /home/vrrcelestino/venv313/bin/python scripts/audit_nine_campaign.py \
      "$NINE_MANIFEST" --indices 1 --output-dir "$H400_DUAL/direct-audit"')"
printf 'Audit job: %s\nReport: %s/direct-audit\n' "$DUAL_AUDIT" "$H400_DUAL"
)
```

Do not update the checkout or dependencies while the case runs. The final audit reports only index1 and explicitly leaves index0 unassessed. It runs after either a successful or failed solve; reporting exit0 is not acceptance. No automatic resume, extra optimization budget or incumbent reuse is introduced.

## Evidence required before further submissions

Return accounting, the solver log, `direct-audit/nine_audit_manifest.json`, `nine_results.json` and `nine_stage_gaps.json` when available. Confirm that the log records Method1 and does not retain concurrent root optimization. Compare stage completion, stage and final objective bounds, independent residuals, service, construction/optimization/end-to-end times and both process/Slurm memory measurements against the original direct case. Any speed or memory benefit remains a single-instance observation. A feasible solution without the full accepted hierarchy is retained but not certified as an investment recommendation.

## Sources

- [Gurobi Method parameter and memory guidance](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter.Method).
- [Gurobi soft memory limit, measured in decimal GB](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter.SoftMemLimit).
