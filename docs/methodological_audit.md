# Stage 5.5 methodological audit

## Purpose

The completed nine-scenario RP and EVPI/VSS campaign validates the software
pipeline. It does not by itself validate the economic interpretation of the
result. Stage 5.5 creates a reproducible audit gate before any formulation or
workbook value is changed.

The audit is deliberately non-blocking. It reports facts and warnings in
`model_audit.json`; it never substitutes costs, changes units, increases
capacity, or imposes a service target.

## Current baseline evidence

- expected domestic service: 78.70%;
- scenario range: 74.48% to 81.44%;
- unmet-demand cost: 99.45% of the objective;
- 69 candidate warehouses opened;
- reported opening and candidate-capacity costs: zero;
- 146 warehouses expanded and 92 bulkified;
- all binary variables eliminated by presolve in the production RP.

The zero costs may be intentional placeholders, but they remove an important
network-design trade-off. The technical EVPI/VSS result must therefore remain
classified as a pipeline baseline until the data owners confirm these values.

## Audit contract

The input section reports:

- model mode, scenario count, periods, and `days_per_period`;
- static, daily reception/shipping, and converted per-period capacities;
- count, zero count, minimum, maximum, and positive scale ratio for key
  capacities, costs, penalties, supply, and demand;
- investment opportunities whose configured fixed or variable cost is zero;
- parameters reaching `1e9`, which may indicate a sentinel or scaling issue.

When a structured solution is available, the solution section adds:

- objective components and their shares;
- investment counts and selected capacities;
- activated investments whose associated configured cost is zero;
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

1. **Units:** confirm whether reception and shipping capacities are daily and
   whether the 30-day conversion is applied exactly once.
2. **Investment economics:** confirm or replace zero opening, candidate,
   expansion-fixed, and bulkification-fixed costs using traceable sources.
3. **Penalty scale:** decide whether the 99.45% unmet-demand share expresses an
   intentional lexicographic-like service priority or a unit mismatch.
4. **Service policy:** select the unconstrained baseline, an explicit minimum
   service target, scenario targets, or a separate structural alternative.
5. **Freeze and rerun:** version the chosen workbook/formulation and rerun RP,
   EVPI/VSS, and sensitivities. Results from different contracts must not be
   compared as if they belonged to the same model.

Until all gates are closed, retain the present formulation under the name
`baseline_no_origin_inventory` and label its EVPI/VSS result as technical or
exploratory.
