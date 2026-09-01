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

