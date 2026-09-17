# Stagewise root-relaxation diagnostics: unresolved 300–400-hub cases

## Scope and experimental rationale

The nine-scenario extensive-form model is retained. This experiment changes
the root LP algorithm of one lexicographic pass, not its objective, constraints,
priorities, degradation tolerances or acceptance criteria. The prepared dual-only
submission is suspended. No 215-hub case or accepted 300-hub direct-enabled case
is repeated. Benders decomposition, SCIP, 500-hub expansion and a cut-parameter
grid are outside this protocol.

| Case identifier | Baseline outcome | Pass receiving the intervention |
|---|---|---|
| `h400-direct` | Capacity pass: `MEM_LIMIT`, bound zero, 100% gap | 2: emergency capacity |
| `h400-warehouse` | Capacity pass: `MEM_LIMIT`, bound zero, 100% gap | 2: emergency capacity |
| `h300-warehouse` | Economic pass: time limit, target gap not attained | 3: economic cost |

The earlier passes must still execute: this is not a restart from a previously
accepted first-stage solution. In particular, the economic-pass experiment at
300 hubs leaves the capacity-pass algorithm unchanged. Timing and bounds are
reported for every pass, including those not receiving the intervention.

The initial profile is `barrier`: `Method=2` in the designated pass only.
Unmodified passes inherit the existing automatic method. Start with
`h400-direct` as a single diagnostic job, inspect the evidence, and then evaluate
the other unresolved cases. This adaptive order is not a randomized benchmark.
At most one follow-up profile per case should be selected after inspecting the
barrier evidence; do not launch a Cartesian parameter grid.

| Follow-up evidence | Conditional profile | Interpretation |
|---|---|---|
| Presolved nonzeros/factorization memory dominate | `barrier-sparse`: `Method=2`, `PreSparsify=2` | Test sparsification of the root relaxation; record whether nonzeros and memory actually decrease. |
| Barrier remains memory-constrained or fails to advance its relaxation | `primal`: `Method=0` | Compare primal simplex with the barrier experiment and frozen automatic baseline. |
| Root completes but bound progression remains weak in the tree | No automatic follow-up | Review formulation and tree statistics before considering a separate cuts study. |

These are hypotheses, not claims that barrier or sparsification is faster or
uses less memory. A conditional profile requires the same case's barrier
`result.json` and an explicit diagnostic rationale. The preparer hashes that
evidence; the rationale records a research decision, not numerical acceptance.

## Fixed controls

- Nine scenarios, 60 periods, the same OSRM workbook, nearest-20% selection and
  audited connectivity repair; identical warehouse population and direct-arc policy.
- Lexicographic priorities: expected unmet demand, emergency capacity, economic cost.
- Global optimization budget: **28,800 seconds across the complete hierarchy**,
  not 28,800 seconds per pass. No per-pass time-limit override is introduced.
- Relative MIP target: **0.10**; existing absolute gap and objective-degradation
  tolerances are unchanged. Zero service objectives retain their absolute-tolerance
  certificate rather than being judged by an undefined relative gap.
- Four solver threads, seed 42, `NumericFocus=1`, `SoftMemLimit=128` decimal GB.
- Slurm allocation: four CPUs, 192 GiB, 12 hours, `intel-256`, account `sxdsouza`,
  QoS `preempt` as used by the preceding campaigns. Scheduler availability remains
  subject to a fresh `sbatch --test-only` check.
- EVPI/VSS remain disabled. No warm start, `NodeMethod`, crossover, cut, heuristic,
  memory-limit or gap change is combined with this intervention.

The source YAML and input workbook are checked against the previously reported
SHA-256 values. Their entire mathematical/data configuration is cloned. New
results use new directories and names. Reusing outputs or nesting a new campaign
inside the frozen baseline is rejected. Source hashes are rechecked at job start
without requiring Git on a compute node. Do not change the checkout while a job
is pending or executing.

Instrumentation changes the implementation identity. Preserve all previous
results and their original checkout/receipts; **do not re-audit old runs under the
new implementation to manufacture matching identities**. Compare their frozen
reports with newly generated reports, disclosing the observational code change.

## Observations and interpretation

The new outputs supplement, rather than replace, existing evidence:

| Artifact | Content |
|---|---|
| `stagewise_contract.json` | Frozen input hashes, source fingerprint, selected case/pass/profile and any conditional diagnostic rationale. |
| `solver_diagnostics.json` | Original matrix dimensions, configured per-pass parameters, observed presolved matrices, sampled memory/progress, root-log extracts, unavailable fields. |
| `solver_presolved_matrix.csv` | Rows, columns and nonzeros reported by Gurobi's MESSAGE stream, with pass attribution and the original log line. |
| `solver_stage_progress.csv` | Available MIP incumbents/bounds/gaps, node/iteration/cut counts, solver memory and runtime; terminal observations for each pass. |
| `lexicographic_stages.csv` | Authoritative terminal pass statuses, bounds, gaps, timings and degradation checks from the existing observer. |
| `run_summary.json`, `result.json` | End-to-end timing regions, process peak RSS, scientific outputs and embedded diagnostics. |
| `independent_validation.json`, `run_completion.json` | Independent primal checks and checksums, including the new diagnostic files. |
| `audit/nine_results.json`, `audit/nine_stage_gaps.json`, `audit/nine_audit_manifest.json` | Existing campaign acceptance results for the selected case. |
| `slurm-stagewise-root-JOBID.out` | Full optimizer log, preflight, source commit declaration, resource allocation and export/audit messages. |

Sampling occurs on available callbacks, at most once per 30 wall seconds plus
pass-termination events; it is not a guarantee that callbacks occur every 30
seconds. At most 10,000 progress samples, 100 matrix observations and 300 root
log extracts are retained. No solution vector is retrieved by the new observer.
No additional `model.presolve()` model copy is created. Matrix dimensions are
observations from solver logs, **not** counts reconstructed from deletion
counters. An absent matrix or callback field is explicitly missing, never zero.

Memory from Gurobi is in decimal GB and may refer to solver-environment
allocation. Existing process RSS is in MiB; Slurm MaxRSS is a separate accounting
measurement. Do not equate these quantities or add stage peak-memory values.
LP iteration objectives are not reported as valid MIP lower bounds. The undefined
relative gap at a zero incumbent is left null in the new telemetry. Callback
diagnostic failures are recorded without interrupting terminal-stage accounting.

A completed Slurm job or a feasible zero-shortfall incumbent does not establish
completion of the objective hierarchy. Acceptance still requires the existing
independent checks, service certificate, all required passes and their applicable
gap/degradation criteria. If telemetry is missing, retain the scientific result
but do not claim a complete diagnostic comparison.

## NPAD: tests and first barrier submission

Run this block from an interactive shell. Parentheses confine `set -e` to a
subshell: a failed command does not close the VS Code terminal. This submits
**one case only**, not a three-case array. No scheduler job has been submitted
by preparing this pull request.

```bash
(
set -e
cd /home/vrrcelestino/model-agrologistic
test -z "$(git status --porcelain)"
git fetch origin
git switch research/stagewise-root-diagnostics
git pull --ff-only origin research/stagewise-root-diagnostics
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE="$PWD/secrets/gurobi.lic"
export PYTHON=/home/vrrcelestino/venv313/bin/python
export STAGEWISE_SOURCE_COMMIT="$(git rev-parse HEAD)"

"$PYTHON" -m ruff check .
QUALITY_DIR="$PWD/data/results/validation/stagewise-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$QUALITY_DIR"
"$PYTHON" -m pytest tests/test_stagewise_root.py \
  tests/test_nine_audit.py tests/test_experiment_runner.py \
  --junitxml "$QUALITY_DIR/pytest.xml"
"$PYTHON" - "$QUALITY_DIR/pytest.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET
cases = list(ET.parse(sys.argv[1]).getroot().iter("testcase"))
licensed = [c for c in cases if c.get("name", "").startswith("test_licensed_stagewise_parity")]
assert len(licensed) == 2, "Both licensed stage-parity tests must be collected"
assert not any(c.find(tag) is not None for c in cases for tag in ("failure", "error", "skipped"))
print("STAGEWISE LICENSED TEST GATE: ACCEPTED")
PY

CAMPAIGN_ROOT="$PWD/data/results/hpc/stagewise-h400-direct-barrier-$(date -u +%Y%m%dT%H%M%SZ)"
"$PYTHON" scripts/prepare_stagewise_campaign.py \
  --baseline-manifest "$PWD/data/results/hpc/nine-connectivity-h400-20260916T123635Z/campaign.yaml" \
  --campaign-root "$CAMPAIGN_ROOT" --case h400-direct --profile barrier
export STAGEWISE_MANIFEST="$CAMPAIGN_ROOT/campaign.yaml"
"$PYTHON" scripts/prepare_stagewise_campaign.py --check-manifest "$STAGEWISE_MANIFEST"
sbatch --test-only --account=sxdsouza --export=ALL scripts/run_stagewise_root.slurm
STAGEWISE_JOB_ID="$(sbatch --parsable --account=sxdsouza --export=ALL scripts/run_stagewise_root.slurm)"
printf 'Job: %s\nCampaign: %s\nQuality: %s\n' "$STAGEWISE_JOB_ID" "$CAMPAIGN_ROOT" "$QUALITY_DIR"
)
```

Retain the printed job ID and campaign path. If the licensed gate fails or skips
a test, stop before submission and return that output. No package upgrade is
requested: retain the existing validated NPAD environment. The scripts check
fresh output directories and source identity again on the compute node.

After completion, share the job's `sacct` output, full Slurm log,
`stagewise_contract.json`, and the selected run's `solver_diagnostics.json`,
`lexicographic_stages.csv`, `run_summary.json`, `independent_validation.json` and
the three audit JSON files listed above. The full flows/inventories need not be
transferred for the first diagnosis. Preserve them with the completion receipt.

## Subsequent unresolved cases

Use the same tested source and launcher, a fresh campaign root, and exactly one
case per submission. Prepare the remaining barrier cases after reviewing the
first diagnostic; do not submit both algorithm variants automatically.

| `--case` | `--baseline-manifest` relative to the repository |
|---|---|
| `h400-warehouse` | `data/results/hpc/nine-connectivity-h400-20260916T123635Z/campaign.yaml` |
| `h300-warehouse` | `data/results/hpc/nine-connectivity-h300-20260915T150139Z/campaign.yaml` |

For an evidence-supported follow-up, keep the same case/baseline and choose
`--profile barrier-sparse` or `--profile primal`, supplying `--prior-result`
with that case's barrier `result.json` and `--diagnostic-note` explaining the
observed memory, presolved matrix or relaxation behaviour. Each profile restarts
the full hierarchy with the same global budget. Record failures, incomplete
passes and time/memory censorship alongside successful outcomes. No increased
budget, changed acceptance threshold or new population follows automatically.

## Technical basis

- [Gurobi multi-objective environments](https://docs.gurobi.com/projects/optimizer/en/current/concepts/environments/multiobjective.html): per-pass environments are created after global parameter settings; the global time budget still applies.
- [Gurobi parameter reference](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html): `Method` and `PreSparsify` control numerical algorithms without redefining the scientific objective hierarchy.
- [Gurobi callback reference](https://docs.gurobi.com/projects/optimizer/en/current/reference/numericcodes/callbacks.html): message observations, memory/progress queries and terminal multi-objective pass statistics.

The licensed miniature tests compare all three objective values between the
unchanged automatic configuration and each isolated barrier intervention.
They must pass on NPAD before a large run; local tests without a usable license
do not constitute numerical parity evidence.
