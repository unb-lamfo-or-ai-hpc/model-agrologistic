# HPC experiments and structured outputs

Stage 5.2 introduces versioned YAML manifests for reproducible local and HPC
experiments. Each manifest records the input workbook, loader choices,
mathematical formulation, solver parameters, and researcher metadata.

## Run a complete manifest

```bash
python scripts/run_batch_hpc.py experiments/example_hpc.yaml
```

The command runs every entry sequentially and creates `batch_summary.csv` after
the individual outputs finish.

## Run one experiment

Indices are zero-based:

```bash
python scripts/run_batch_hpc.py experiments/example_hpc.yaml --index 0
```

Before solving, inspect the selected routes and estimated variable count:

```bash
python scripts/run_batch_hpc.py \
  experiments/example_hpc.yaml \
  --index 0 \
  --dry-run
```

Every run writes `preflight.json`. By default, the runner refuses an estimate
above two million variables. Configure `route_filter_strategy: top_k` with
`route_top_k`, use `pareto`, or explicitly set
`max_estimated_variables: null` when a larger run is intentional.

The command also reads `SLURM_ARRAY_TASK_ID` when `--index` is omitted. A Slurm
submission can therefore use:

```bash
sbatch --array=0-1 run_model_agrologistic.slurm
```

with the job step:

```bash
python scripts/run_batch_hpc.py experiments/example_hpc.yaml
```

Array tasks do not write a shared file, avoiding concurrent writes. After the
array completes, aggregate the isolated summaries with:

```bash
python scripts/run_batch_hpc.py \
  experiments/example_hpc.yaml \
  --aggregate-only
```

## Per-run output contract

Each experiment owns a directory named after its validated run name:

```text
<output_dir>/<experiment_name>/
├── result.json
├── preflight.json
├── run_summary.json
├── warehouse_decisions.csv
├── flows.csv
├── inventories.csv
├── unmet_demand.csv
├── emergency_capacity.csv
├── infeasibility.json          # only when IIS was requested
├── storage_by_warehouse.csv
└── storage_by_scenario.csv
```

`result.json` contains the complete solver-independent result, configurations,
timestamps, metrics, and optional EVPI/VSS values. The raw solver object is not
serialized. JSON and CSV files are written atomically so a completed artifact
is never partially visible to another process.

Failed jobs create `run_summary.json` with `status=error`, exception type, and
message. Set `continue_on_error: true` to let a local sequential batch continue
after an individual failure.

Set `solver.compute_iis: true` to diagnose an infeasible Gurobi model. The
runner exports the bounded list of IIS constraints and variable bounds to
`infeasibility.json`; `iis_max_items` controls the maximum exported items.

## Stage 5.3 route-filter calibration

Run the versioned sensitivity campaign before selecting a filtered network for
the nine-scenario stochastic experiment:

```bash
python scripts/run_batch_hpc.py \
  experiments/route_filter_sensitivity.yaml \
  --dry-run

python scripts/run_batch_hpc.py \
  experiments/route_filter_sensitivity.yaml
```

The campaign compares `top_k` values 3, 5, and 10 with a 5% Pareto filter.
Filtered OD warehouses keep outbound customer coverage and an export exit when
one exists. The cumulative inventory Big-M is computed from only the origins
and upstream warehouses that can reach each facility through selected OD/DD
routes.

`run_summary.json` and the aggregated `batch_summary.csv` include total unmet
demand and static, reception, and combined emergency-capacity use. Select the
smallest network whose objective and emergency-capacity indicators remain
stable before running EVPI/VSS.

The first NPAD campaign completed with 144 passing tests and four optimal
solutions. Pareto 5% reduced the objective by 0.82%, runtime by 8.41%, and
combined emergency capacity by 0.88% relative to `top_k=10`, but increased
unmet domestic demand by 4.59%. Its domestic service level was 35.13%, versus
37.98% for `top_k=10`, so the filtered network must not be selected from the
objective alone.

The golden workbook declares `days_per_period=30`, while the first campaign
used the model default of 22. It also left optional direct origin-customer and
origin-export routes disabled, forcing all supply through warehouse shipping
capacity. Run the follow-up campaign at 30 days to separate the route-filter
effect from the network-policy effect:

```bash
python scripts/run_batch_hpc.py \
  experiments/network_policy_sensitivity.yaml \
  --dry-run

python scripts/run_batch_hpc.py \
  experiments/network_policy_sensitivity.yaml
```

This campaign compares Pareto 5% with `top_k=10`, both with and without direct
routes. Summaries additionally report total and served domestic demand,
domestic service level, and total direct flow. Update `example_hpc.yaml` only
after this comparison identifies the final policy for the nine-scenario run.

The first direct-route comparison raised domestic service from 38.47% to
79.34% for `top_k=10` and reduced combined emergency capacity from 39.18
billion to 471.7 thousand ton-periods. Pareto 5% reached only 48.43% service
because customer-group filtering did not guarantee a direct exit for every
origin/product. Direct route selection now augments the filtered set with the
nearest domestic and export exit for every origin/product. Rerun only the two
direct cases after this coverage change:

```bash
python scripts/run_batch_hpc.py \
  experiments/network_policy_sensitivity.yaml \
  --index 2 \
  --dry-run
python scripts/run_batch_hpc.py \
  experiments/network_policy_sensitivity.yaml \
  --index 3 \
  --dry-run

python scripts/run_batch_hpc.py \
  experiments/network_policy_sensitivity.yaml \
  --index 2
python scripts/run_batch_hpc.py \
  experiments/network_policy_sensitivity.yaml \
  --index 3

python scripts/run_batch_hpc.py \
  experiments/network_policy_sensitivity.yaml \
  --aggregate-only
```

The augmented direct-route rerun confirmed `top_k=10` as the calibrated
policy: 79.34% domestic service, 140.03 million tonnes unmet, and only 470.3
thousand ton-periods of combined emergency capacity. Pareto 5% reached 45.89%
service and is too sparse for the production experiment.

A complete direct network can serve at most 80.37% of domestic demand without
carrying supply between periods at origins. The remaining gap therefore comes
primarily from seasonal timing and warehouse shipping capacity, not from the
`top_k=10` filter. `example_hpc.yaml` now uses direct routes, `top_k=10`, and
30 days per period. The nine-scenario extensive form explicitly raises the
preflight limit to six million variables. Calibrating shipping-capacity units
or adding origin inventory is a separate follow-up modeling decision.

