# Artur nine-scenario controlled extension

## Scientific purpose

Gate 2D extends the accepted three-scenario Artur experiment to the complete
Cartesian product of the same three supply levels and three domestic-demand
levels. The purpose is to test whether the shared first-stage investment plan
remains adequate when supply and demand vary independently.

This is a controlled model extension, not an exact reconstruction of the
thesis forecasting process. The historical fitted distributions, random draws,
scenario reduction procedure, and empirical probabilities remain unavailable.

## Experimental contract

The gate uses nine scenarios:

- supply multipliers: `0.85`, `1.00`, and `1.15`;
- domestic-demand multipliers: `0.95`, `1.00`, and `1.05`;
- every supply-demand combination;
- equal experimental probability `1/9` for every scenario;
- the persisted `artur_legacy_i001` solver workbook;
- the Gurobi penalty objective used by the accepted three-scenario campaign;
- full supply allocation, domestic-demand equality, and free terminal inventory;
- shared opening, candidate capacity, expansion, and bulkification decisions;
- scenario-dependent flows, inventory, unmet demand, and emergency capacity.

Emergency capacity preserves complete recourse and remains an infrastructure
gap indicator. Its use is not an automatic gate failure. Big-M penalty values
must be reported separately from observed economic costs, and the penalty
component of VSS must not be interpreted as an observed monetary benefit.

## Execution order

Rebuild the derived workbook after pulling the feature branch:

```bash
python scripts/build_artur_solver_workbook.py \
  --name artur_legacy_i001 \
  --overwrite
```

Inspect the nine-scenario RP before allocating a solver job:

```bash
python scripts/run_batch_hpc.py \
  experiments/artur_stochastic_extension.yaml \
  --index 2 \
  --dry-run
```

Run and audit the RP first:

```bash
python scripts/run_batch_hpc.py \
  experiments/artur_stochastic_extension.yaml \
  --index 2

python scripts/audit_existing_run.py \
  experiments/artur_stochastic_extension.yaml \
  --index 2
```

Only after accepting the RP evidence, inspect and execute the checkpointed
EVPI/VSS calculation:

```bash
python scripts/run_batch_hpc.py \
  experiments/artur_stochastic_extension.yaml \
  --index 3 \
  --dry-run

python scripts/run_batch_hpc.py \
  experiments/artur_stochastic_extension.yaml \
  --index 3
```

Regenerate the campaign summary after each completed run:

```bash
python scripts/run_batch_hpc.py \
  experiments/artur_stochastic_extension.yaml \
  --aggregate-only
```

## Acceptance criteria

Gate 2D is accepted when:

- preflight reports exactly nine unique scenarios and probabilities sum to one;
- RP returns a usable optimal solution within the declared resource contract;
- material balance is within tolerance in every scenario;
- domestic demand is satisfied through ordinary flow or explicit unmet-demand
  slack in every scenario;
- all supply is allocated to domestic demand, export flow, or inventory;
- emergency-capacity use is exported by scenario, warehouse, period, and type;
- investment saturation is exported instead of hidden by aggregate totals;
- RP, WS, EV, and EEV are finite for the scalar penalty objective;
- EVPI and VSS are non-negative within numerical tolerance;
- economic and Big-M penalty components are kept separate in interpretation;
- the run remains labelled as a controlled extension.

The gate does not require zero emergency capacity. Material emergency use is a
strategic finding that the configured investment frontier is insufficient for
at least one stress condition.
