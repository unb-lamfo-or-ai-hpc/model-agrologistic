# Artur controlled stochastic extension

> Historical development record. Results and commands below refer to their named
> earlier campaigns, not automatic v0.2 acceptance. Use the
> [current mathematical contract](v020_mathematical_contract.md),
> [validation report](v020_validation_report.md) and
> [results interpretation](results_interpretation.md) for current claims.
> In particular, old objective ordering, slack-unit labels and complete-recourse
> language must not be transferred to new evidence without checking the contract.

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

## MVP policy for service, supply, and emergency capacity

The MVP preserves complete recourse instead of forcing every stress scenario
to fit the nominal infrastructure. Unmet domestic demand and emergency static
or reception capacity keep the model solvable when the admissible investment
set is insufficient. They are last-resort diagnostic variables, not ordinary
operating resources.

The policy is therefore:

- satisfy domestic demand in every scenario whenever physically attainable;
- retain unmet demand as an explicit last-resort service shortfall;
- allocate all origin supply to domestic demand, export flow, or terminal
  inventory;
- retain emergency capacity as a quantified infrastructure gap;
- keep investment, operation, and Big-M penalty components separate;
- interpret physical slack quantities as planning evidence while treating their
  Big-M monetary contribution as penalty-dependent, not as an observed cost.

A positive emergency-capacity value does not invalidate an otherwise usable
solution. The audit classifies it as `emergency_capacity_required`. A material
balance residual remains a formulation or extraction failure, while material
unmet demand is classified separately as `domestic_service_shortfall`.

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

After either run, the structured exports include:

- `material_balance_by_scenario.csv`, reconciling supply and initial inventory
  with domestic flow, export flow, and terminal inventory;
- `capacity_gap_by_scenario.csv`, separating static and reception gaps and
  reporting the peak reception gap in tonnes per day;
- `emergency_capacity_daily.csv`, preserving facility, period, scenario, and
  daily-equivalent detail;
- `investment_saturation.csv`, comparing first-stage decisions with configured
  upper bounds;
- `evpi_vss_decomposition.csv`, separating investment, operation, and penalty
  contributions when index 1 is executed.

## Acceptance criteria

The three-scenario gate passes when:

- the workbook audit reports exactly the three declared scenario identifiers,
  probabilities, and multipliers;
- RP returns a usable optimal solution and all scenario probabilities sum to 1;
- material balance and the domestic-demand equality hold in every scenario;
- unmet demand and emergency capacity are reported explicitly and are not
  silently removed from the result;
- positive emergency capacity is classified as an infrastructure finding and
  does not by itself reject the gate;
- RP, WS, EV, and EEV are finite under the scalar penalty objective;
- EVPI and VSS are non-negative within the configured numerical tolerance;
- checkpoints and structured artifacts permit an interrupted EVPI/VSS run to
  resume without reusing a different experiment identity.

The lexicographic service policy is intentionally excluded from monetary
EVPI/VSS. A nine-scenario Cartesian extension is deferred until this gate is
accepted, which limits computational cost and isolates scenario-design errors.

## Gate 2C RP evidence

The first three-scenario RP run reached an optimal solution with 100% domestic
service and zero unmet demand in every scenario. The low-supply and central
scenarios required no emergency capacity. The high-supply, low-demand scenario
required 1,939,937.68 tonnes of reception throughput over the modeled periods,
or 646,645.89 probability-weighted tonnes. No static-capacity slack was used.

All eligible candidate, expansion, and bulkification capacities reached their
configured upper bounds. The residual reception gap is therefore outside the
current decision set. It is concentrated in April harvest peaks and must be
reported as a strategic infrastructure requirement rather than removed by
reducing the 1.15 supply multiplier.

The economic objective was 57.16 billion monetary units, while the Big-M
reception penalty represented approximately 91.88% of the penalized objective.
Consequently, scalar EVPI and VSS remain mathematically valid under the common
objective, but their total monetary magnitudes must be accompanied by component
and physical-slack decomposition.
