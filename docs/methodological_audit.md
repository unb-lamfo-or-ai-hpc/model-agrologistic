# Stage 5.5–5.6 methodological audit

## Purpose

The completed nine-scenario RP and EVPI/VSS campaign validates the software
pipeline. It does not by itself validate the economic interpretation of the
result. Stage 5.5 creates a reproducible audit gate before any formulation or
workbook value is changed.

The audit is deliberately non-blocking. It reports facts and warnings in
`model_audit.json`; it never invents costs, changes units, increases capacity,
or imposes a service target.

## Current baseline evidence

- expected domestic service: 78.70%;
- scenario range: 74.48% to 81.44%;
- unmet-demand cost: 99.45% of the objective;
- 69 candidate warehouses opened;
- candidate construction was initially loaded with zero model cost even though
  the workbook reported a positive total construction estimate;
- 146 warehouses expanded and 92 bulkified;
- all binary variables eliminated by presolve in the production RP.

Stage 5.6 resolves the candidate-cost inconsistency without creating a fixed
cost split. When both optional model-cost columns are zero, the loader converts
the workbook's reported total construction estimate to a linear cost per ton:
`reported_total_cost / maximum_candidate_capacity`. Expansion and
bulkification already use positive literature-based costs per ton. A zero fixed
component is therefore acceptable whenever the corresponding variable cost is
positive.

## Audit contract

The input section reports:

- model mode, scenario count, periods, objective policy, the 30-day fallback,
  and effective days for every period;
- static, daily reception/shipping, and converted per-period capacities;
- count, zero count, minimum, maximum, and positive scale ratio for key
  capacities, costs, penalties, supply, and demand;
- investment opportunities whose complete applicable cost is zero;
- parameters reaching `1e9`, which may indicate a sentinel or scaling issue.

When a structured solution is available, the solution section adds:

- objective components and their shares;
- investment counts and selected capacities;
- capacity-based investment activations whose complete applicable cost is
  zero;
- expected, minimum, maximum, and per-scenario domestic service levels;
- a warning when one component represents at least 90% of the objective.

## Commands

A dry run produces the input audit without invoking Gurobi:

```bash
python scripts/run_batch_hpc.py \
  experiments/example_hpc.yaml \
  --index 1 \
  --dry-run
```

Audit an existing RP or EVPI/VSS result without solving again:

```bash
python scripts/audit_existing_run.py experiments/example_hpc.yaml --index 1
python scripts/audit_existing_run.py experiments/example_hpc.yaml --index 2
```

The audit command is introduced by PR #12. Confirm that the checkout contains
that revision before invoking it:

```bash
git fetch origin
git rev-parse --short HEAD
git rev-parse --short origin/develop
test -f scripts/audit_existing_run.py
```

If the local and remote revisions differ, synchronize first. A missing script
on an older checkout is not an audit or Python failure.

## Decision gates

1. **Units:** reception and shipping remain daily rates and are multiplied
   exactly once by `days_per_period_by_period[t]`, with 30 days as the fallback.
2. **Investment economics:** use constant returns to scale and the observed
   cost per ton. Do not fabricate a fixed/variable decomposition.
3. **Supply allocation:** keep origin supply balance as an equality. Every ton
   must enter a domestic, export, or warehouse-inventory path; no disposal or
   unused-supply variable is introduced.
4. **Service policy:** keep `penalty` as the reproducible legacy baseline and
   provide `lexicographic` as an explicit alternative. No arbitrary service
   floor is imposed in Stage 5.6.
5. **Freeze and rerun:** version the selected objective policy before new
   scientific comparisons. Scalar EVPI/VSS remains restricted to the penalty
   objective.

The pre-Stage 5.6 EVPI/VSS result remains a technical pipeline baseline because
candidate investment was free in that run. It must not be compared directly
with results produced after the corrected candidate-cost loading contract.
