# Isolated SCIP expansion through 400-hub preflight

## Scope and evidence boundary

The native SCIP implementation is unchanged from the qualified numerical source
used by job 2107034. This protocol adds experimental orchestration, not equations,
solver options or numerical tolerances. It does not update the running checkout,
install packages or repeat the active 215-hub warehouse-only experiment.

The existing small-instance qualification passed 42 tests without skips, including
licensed Gurobi parity. The reviewed NPAD build is SCIP 10.0.2 with SoPlex 8.0.2
and 8-byte precision. Large-instance construction and convergence remain empirical
questions. Gurobi memory observations are not bounds for PySCIPOpt/SoPlex.

The incremental resource experiment is bounded as follows:

| Array index | Warehouses | Direct arcs | Preflight | Solve admission |
|---|---:|---|---|---|
| 0 | 215 | Enabled | Yes | Bounded experimental trial |
| 1 | 300 | Disabled | Yes | Bounded experimental trial |
| 2 | 300 | Enabled | Yes | Bounded experimental trial |
| 3 | 400 | Disabled | Yes | Deferred pending SCIP resource evidence |
| 4 | 400 | Enabled | Yes | Deferred pending SCIP resource evidence |

Preparing a 400-hub manifest is not permission to execute its solve. The worker
rejects solve indices 3 and 4 even if someone manually extends the Slurm array.
The first 215-hub warehouse-only experiment is not included in any new array.
The larger-instance risk is explicit for 300 hubs: memory exhaustion, failed
construction and incomplete optimization remain reportable experimental outcomes,
not grounds for silently changing the mathematical contract or replacing evidence.

## Isolation and frozen inputs

Create a new detached worktree at the exact handoff commit. Reuse the already
qualified Python environment **read-only**: do not run pip, upgrade dependencies
or alter its editable installation. Entry-point scripts place the new repository
root first on the Python import path; the unchanged source/package identity is
checked against the original qualification before each task. The active worktree
at `/home/vrrcelestino/agrologistic-scip-pr31-4N2wGy/source` remains at its original
commit. Git fetch/worktree registration changes shared Git metadata, not files in
that active checkout.

The reference pilot manifest and admission receipt are read-only provenance.
Only their input/qualification contracts are checked; the running solution,
logs, execution claim and output directories are not modified. The 215-hub input
must match its frozen hash. The previously accepted OSRM hashes are fixed for:

- 300 hubs: `7761cce77cf93dcba2f617714f0117c1f2ead4de0c3f27149daceba447e0c7d1`.
- 400 hubs: `c3085456997714ef5a8bdbf61e2c9a5e578c2636003947427cf58933d21ceb13`.

Nearest-20% selection, explicitly audited strong interhub connectivity repair,
nine scenarios, 60 periods and the existing candidate/investment/slack contracts
are preserved. No OSRM query or workbook regeneration is required. Shared-variable
preflight limits are 16, 26 and 43 million for 215, 300 and 400 hubs respectively;
these estimates exclude SCIP-internal transformation and indicator overhead.

## Resources and dependency semantics

Preflight tasks request four CPUs, 16 GiB and two hours; at most two run at once.
Solve tasks request four CPUs, 192 GiB and 12 hours, with a global 28,800-second
optimization budget and common gap target 10%. At most **two new solves** run
simultaneously. The already running job 2107034 is outside this array limit, so
up to three large solves could overlap. Scheduler availability and account limits
still determine actual starts. No live availability has been asserted.

The native `limits/memory=131072` MB remains unchanged. It is SCIP-owned accounting,
not a ceiling on Python process RSS; a Slurm OOM remains possible. Thread settings
are ceilings, not proof of multicore LP/search execution. The driver remains
sequential `optimize()` with native SoPlex defaults, not concurrent SCIP or a
translation of Gurobi barrier parameters. EVPI/VSS and IIS are disabled.

Both arrays use `intel-256`, account `sxdsouza`, and the account-default QoS. The
submission helper clears `SBATCH_QOS`; it never specifies a QoS name. The solve
array uses `aftercorr` dependencies, so each solve waits for its own corresponding
successful preflight, not all five. A failure in a deferred 400-hub preflight does
not block the admitted 215/300 cases. See the official
[Slurm array dependency documentation](https://slurm.schedmd.com/job_array.html).
The worker independently checks the recorded preflight hash; the scheduler
dependency alone is not admission.

## NPAD preparation and submission

Set `SCIP_EXPANSION_SOURCE` to the exact handoff commit before this block. This
creates a new worktree; it never switches or pulls the active pilot checkout.

```bash
(
  set -euo pipefail
  : "${SCIP_EXPANSION_SOURCE:?Set the exact handoff commit}"
  export SCIP_EXPANSION_SOURCE
  REPO=/home/vrrcelestino/model-agrologistic
  git -C "$REPO" fetch origin research/scip-qualification
  EXPANSION_WORK="$(mktemp -d /home/vrrcelestino/agrologistic-scip-expansion-XXXXXX)"
  export SCIP_EXPANSION_CHECKOUT="$EXPANSION_WORK/source"
  git -C "$REPO" worktree add --detach "$SCIP_EXPANSION_CHECKOUT" "$SCIP_EXPANSION_SOURCE"
  export SCIP_PYTHON=/home/vrrcelestino/agrologistic-scip-pr31-4N2wGy/venv/bin/python
  export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
  cd "$SCIP_EXPANSION_CHECKOUT"
  "$SCIP_PYTHON" -m pytest tests/test_scip_expansion.py tests/test_scip_pilot.py -q
  export SCIP_EXPANSION_ROOT="$REPO/data/results/hpc/scip-expansion-$(date -u +%Y%m%dT%H%M%SZ)"
  "$SCIP_PYTHON" scripts/prepare_scip_expansion.py \
    --campaign-root "$SCIP_EXPANSION_ROOT" \
    --data-root "$REPO/data/processed" \
    --reference-manifest "$REPO/data/results/hpc/scip-h215-warehouse-20260919T131233Z/campaign.yaml"
  bash scripts/submit_scip_expansion.sh
)
```

The helper prints and saves `PREFLIGHT_JOB` and `SOLVE_JOB` in `submission.txt`.
Do not re-execute the whole block after a partial failure: inspect that receipt
first. An atomic submission claim prevents the same campaign from being submitted
twice. Each case also has separate preflight/solve claims; preserve them after
failure and request a reviewed retry rather than removing markers or overwriting
results. If preflight submission succeeds but solve submission fails, its ID is
retained and the preflight array must not be resubmitted.

## Artifact handoff and next decisions

The root contains `expansion_plan.json`, `submission.txt`, `preflight-ARRAY_INDEX.out`
and `solve-ARRAY_INDEX.out`. Each `case-N` contains its own `campaign.yaml`,
immutable `preflight_snapshot.json` and `preflight_gate.json`. The solve can
regenerate its own `runs/NAME/preflight.json` without overwriting the admission
snapshot. Solved cases also write `scip.log`, common run artifacts and:

- `case-N/audit/nine_audit_manifest.json`;
- `case-N/audit/nine_results.json`;
- `case-N/audit/nine_stage_gaps.json`.

Send the plan, both job IDs, accounting and each completed case's three audit
JSONs without waiting for the last case. On failure, provide its worker log and
native SCIP log if present. Process success is not acceptance; review service,
independent feasibility, native/common gaps, inherited priority budgets and all
stage statuses. Preserve failed builds and resource-censored incumbents.

The 400-hub solve decision follows actual SCIP construction/RSS/native-memory and
stage-progress evidence from the active pilot and 300-hub trials. No automated
extrapolation or hidden memory increase is authorized. The approved project
sequence remains Sprint A (Gurobi), Sprint C (SCIP), Sprint D (paired evidence
through 400), then initial Sprint E; larger-network/Benders work remains deferred.
