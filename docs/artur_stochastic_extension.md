# Artur controlled stochastic extension

## Scientific classification

This experiment applies the current two-stage stochastic MILP to the persisted
and normalized `artur_legacy_i001` instance accepted in deterministic Gate 2B.
It is a controlled extension, not an exact stochastic reproduction of Artur's
thesis. The historical forecasting path, fitted distributions, generated
scenario realizations, and probabilities have not been reconstructed.

The extension keeps the data lineage, frozen Haversine network, economic
parameters, Gurobi backend, capacity semantics, domestic-demand equality,
optional export upper bounds, and slack penalties validated in Gate 2B.

## Three-scenario design

The first Gate 2C campaign uses three joint supply-demand states:

| State | Supply level | Supply multiplier | Domestic-demand level | Demand multiplier | Probability |
|---|---|---:|---|---:|---:|
| Adverse | low | 0.85 | high | 1.05 | 1/3 |
| Central | base | 1.00 | base | 1.00 | 1/3 |
| Favorable | high | 1.15 | low | 0.95 | 1/3 |

Export upper bounds follow the supply multiplier so that an automatic export
market remains non-binding relative to scenario supply. The multipliers are the
synthetic levels already used by the gold workbook. Equal probabilities are an
explicit experimental convention; neither is presented as an empirical
estimate from the thesis data.

The extensive form shares candidate opening and capacity, expansion, and
bulkification decisions across scenarios. Flows, inventory, unmet demand, and
emergency capacity are scenario-dependent recourse decisions.

## Execution gates

Rebuild the derived workbook after pulling the branch:

```bash
python scripts/build_artur_solver_workbook.py \
  --name artur_legacy_i001 \
  --overwrite
```

Inspect both experiments before solving:

```bash
python scripts/run_batch_hpc.py \
  experiments/artur_stochastic_extension.yaml \
  --index 0 \
  --dry-run

python scripts/run_batch_hpc.py \
  experiments/artur_stochastic_extension.yaml \
  --index 1 \
  --dry-run
```

Index 0 is the risk-neutral recourse problem (RP) acceptance run. Execute it
first and audit its structured result:

```bash
python scripts/run_batch_hpc.py \
  experiments/artur_stochastic_extension.yaml \
  --index 0

python scripts/audit_existing_run.py \
  experiments/artur_stochastic_extension.yaml \
  --index 0
```

Index 1 calculates RP, WS, EV, EEV, EVPI, and VSS. It uses identity-scoped,
atomic checkpoints and may safely resume after an interrupted run:

```bash
python scripts/run_batch_hpc.py \
  experiments/artur_stochastic_extension.yaml \
  --index 1
```

## Acceptance criteria

The three-scenario gate passes when:

- the workbook audit reports exactly the three declared scenario identifiers,
  probabilities, and multipliers;
- RP returns a usable optimal solution and all scenario probabilities sum to 1;
- material balance and the domestic-demand equality hold in every scenario;
- unmet demand and emergency capacity are reported explicitly and are not
  silently removed from the result;
- RP, WS, EV, and EEV are finite under the scalar penalty objective;
- EVPI and VSS are non-negative within the configured numerical tolerance;
- checkpoints and structured artifacts permit an interrupted EVPI/VSS run to
  resume without reusing a different experiment identity.

The lexicographic service policy is intentionally excluded from monetary
EVPI/VSS. A nine-scenario Cartesian extension is deferred until this gate is
accepted, which limits computational cost and isolates scenario-design errors.
