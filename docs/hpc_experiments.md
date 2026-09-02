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
sbatch --array=0-2 run_model_agrologistic.slurm
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
├── model_audit.json
├── run_summary.json
├── warehouse_decisions.csv
├── flows.csv
├── inventories.csv
├── unmet_demand.csv
├── emergency_capacity.csv
├── scenario_performance.csv
├── infeasibility.json          # only when IIS was requested
├── storage_by_warehouse.csv
└── storage_by_scenario.csv
```

`result.json` contains the complete solver-independent result, configurations,
timestamps, metrics, and optional EVPI/VSS values. The raw solver object is not
serialized. JSON and CSV files are written atomically so a completed artifact
is never partially visible to another process.

For stochastic runs, `scenario_performance.csv` reports the probability,
operating cost, domestic demand served and unmet, service level, direct flow,
emergency capacity, DynCap, and Turnover separately for every scenario. These
values are not probability-weighted; the aggregate expected values remain in
`run_summary.json`.

`model_audit.json` is a non-blocking methodological diagnostic. It inventories
parameter scales, zero-cost investment opportunities, capacity totals before
and after `days_per_period`, objective-component shares, activated zero-cost
investments, and expected/scenario service levels. Findings are warnings for
review; they do not silently modify inputs or solver behavior.

To audit an already completed run without solving it again:

```bash
python scripts/audit_existing_run.py \
  experiments/example_hpc.yaml \
  --index 1
```

Use index 2 for the completed EVPI/VSS run. The command verifies the workbook
hash, loader contract, and mathematical model configuration before combining
the current input with the stored structured result.

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

## Stage 5.4 progressive stochastic campaign

The production example deliberately separates the nine-scenario recourse
problem from the complete EVPI/VSS analysis. Validate the extensive form first:

```bash
python scripts/run_batch_hpc.py \
  experiments/example_hpc.yaml \
  --index 1 \
  --dry-run

python scripts/run_batch_hpc.py \
  experiments/example_hpc.yaml \
  --index 1
```

Index 1 solves RP only. Inspect `run_summary.json`, `result.json`, the Gurobi
log, runtime, gap, service level, emergency capacity, and the scheduler's peak
memory before starting index 2.

The complete nine-scenario analysis performs 12 optimizations: RP, EV, EEV,
and one wait-and-see problem per scenario. Start it only after the RP pilot is
computationally acceptable:

```bash
python scripts/run_batch_hpc.py \
  experiments/example_hpc.yaml \
  --index 2 \
  --dry-run

python scripts/run_batch_hpc.py \
  experiments/example_hpc.yaml \
  --index 2
```

Index 2 sets `resume_evpi_vss: true`. Every usable intermediate solution is
stored atomically under:

```text
data/results/hpc/stochastic_nine_scenarios_evpi_vss/
└── evpi_vss_checkpoints/
    ├── manifest.json
    ├── progress.json
    ├── rp.json
    ├── ev.json
    ├── eev.json
    └── ws_000.json ... ws_008.json
```

`progress.json` identifies the active step and the number of completed solves.
If the job is interrupted, submit the same command again. Completed steps are
restored only when the workbook hash and complete experiment configuration
match. A changed workbook, scenario contract, model option, or solver option
receives a different checkpoint identity and is rejected instead of silently
mixing incompatible results.

The RP pilot is a diagnostic baseline, not the final scientific campaign. The
service-level modeling decision described in
`docs/service_level_methodology.md` must be frozen before definitive EVPI/VSS
and sensitivity results are reported.

### NPAD memory profile and Slurm submission

The first nine-scenario RP attempt was executed on `service0` with a 48 GiB
per-process virtual-memory limit. Gurobi exhausted that limit after presolve,
before finding an incumbent. Large stochastic runs must therefore use a Slurm
compute node rather than the service node.

The validated submission profile targets `intel-128` with 16 CPUs and 64 GiB:

```bash
sbatch scripts/run_model_agrologistic.slurm
```

The default `EXPERIMENT_INDEX=1` runs only the nine-scenario RP. Select index 2
explicitly for the checkpointed EVPI/VSS campaign. After a job finishes,
inspect accounting with:

```bash
sacct -j <job-id> \
  --format=JobID,JobName,Partition,State,Elapsed,AllocCPUS,ReqMem,MaxRSS,ExitCode
```

The stochastic entries use a two-hour Gurobi limit, 16 solver threads,
`NumericFocus=1`, and `SoftMemLimit=56` GB. The 8 GiB difference from the Slurm
request is reserved for Python, model construction, and operating-system
overhead. A soft-memory termination returns a diagnostic Gurobi status instead
of an abrupt cgroup allocation failure.

The production RP job `2071952` completed optimally in 14 minutes 52 seconds.
It used 16,623,156 KiB of peak resident memory (about 15.9 GiB), obtained a
zero optimality gap, and produced an expected domestic service level of
78.70%. The scenario service levels ranged from 74.48% to 81.44%. The complete
checkpointed EVPI/VSS campaign subsequently completed on `intel-128` with a
64 GiB request.

For a materially larger scenario set or workbook, use `intel-256` as the first
fallback:

```bash
sbatch \
  --partition=intel-256 \
  --mem=192G \
  scripts/run_model_agrologistic.slurm
```

The first service-node failure was caused by an inherited 48 GiB virtual-memory
limit, not by resident-memory demand. The Slurm script removes inherited
virtual-memory and CPU-time limits and executes the selected virtual
environment's Python directly, without depending on a node-specific Conda
initialization script or `/usr/bin/time`.
