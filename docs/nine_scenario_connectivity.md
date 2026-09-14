# Nine-scenario interhub connectivity campaign

## Research contract

This separate campaign preserves the accepted thesis and three-scenario configurations. For each product, retain the existing nearest-20% interhub baseline (with the existing rounding and grouping rules), preserve customer-coverage repairs, and add eligible directed DD arcs to connect the potential warehouse graph strongly. Forward and reverse rooted shortest-path trees prioritize the number of added edges, followed by road distance. This deterministic heuristic is not a globally minimum augmentation. A disconnected eligible physical graph is rejected rather than repaired with fabricated distances or Big-M arcs.

The final graph admits directed paths with multiple intermediate warehouses. This is potential connectivity, not a requirement that every candidate opens, nor a guarantee of throughput feasibility. Closed candidates remain subject to the existing activation constraints. The previous DD filter already retained approximately 20%; additional connectivity cannot be assumed to reduce model size or runtime. Report baseline and final fractions separately.

Every preflight and completed run exports:

- `interhub_connectivity_audit.json`: per-product eligible, baseline, repair and final counts and fractions.
- `interhub_components.csv`: strongly connected component membership before and after repair.
- `interhub_repair_edges.csv`: added directed arcs, distances and repair reasons.
- `interhub_path_summary.csv`: reachable and unreachable hub counts and minimum-hop statistics by source and product.

Completed-run checksums include these four products. Path statistics describe the selected graph, not actual freight itineraries or elapsed travel time.

## Experimental scope and acceptance

The population levels are 215, 300, 400, 500, 600, 700, 800, 900 and 1000, with direct arcs disabled/enabled: 18 Gurobi instances. Preserve the existing deterministic population ordering and canonical anchor. Additional levels require workbook construction and OSRM materialization before an exact preflight count can be reported. Counts are not solver timing predictions.

The new target is a relative MIP gap at most 0.10 with a total optimization budget of 14,400 seconds. It does not retroactively change earlier certificates. Report every lexicographic stage, its bound, incumbent, gap and runtime; service and independent feasibility remain required. Incomplete hierarchies, missing bounds and failed runs are retained, not relabeled as successful. The final solution can differ from a pass incumbent within the documented lexicographic degradation rule. Post-optimality EVPI/VSS calculations are disabled in this scaling campaign.

Gurobi is implemented. SCIP remains unimplemented and must not be submitted yet. Its release gate requires the same first-stage decisions, recourse equations, units, objective hierarchy, global time budget, bounds and independent validation on analytical and small cross-solver fixtures. A command accepting the name SCIP is not backend qualification.

A 25-million-variable safety gate is retained for initial execution. Larger preflights are still reported, but require a memory review rather than automatic submission. A timeout is a bound on this algorithm/configuration under the allocated resources, not a universal complexity frontier. Run the 215-hub pilot first; advance population levels only with measured memory headroom.

## NPAD CLI: initial qualified Gurobi pilot

Run from the repository using the dedicated branch. All commands below use a subshell, so a failure does not close the interactive terminal.

```bash
(
set -e
cd /home/vrrcelestino/model-agrologistic
git fetch origin
git switch research/nine-scenario-connectivity
git pull --ff-only origin research/nine-scenario-connectivity
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE="$PWD/secrets/gurobi.lic"
PYTHON=/home/vrrcelestino/venv313/bin/python
"$PYTHON" -m ruff check .
"$PYTHON" -m pytest tests/test_interhub_connectivity.py tests/test_nine_campaign.py tests/test_mathematical_contract.py tests/test_experiment_runner.py
CAMPAIGN_ROOT="$PWD/data/results/hpc/nine-connectivity-$(date -u +%Y%m%dT%H%M%SZ)"
"$PYTHON" scripts/prepare_nine_scenario_campaign.py --campaign-root "$CAMPAIGN_ROOT"
"$PYTHON" scripts/audit_nine_campaign.py "$CAMPAIGN_ROOT/campaign.yaml" --preflight
export NINE_MANIFEST="$CAMPAIGN_ROOT/campaign.yaml"
printf 'Campaign manifest: %s\n' "$NINE_MANIFEST"
sbatch --partition=intel-256 --array=0-1%1 --export=ALL scripts/run_nine_connectivity.slurm
)
```

Only submit after both 215-hub preflights are ready and licensed tests pass. The inventory lists all 18 indices; missing larger workbooks are explicitly reported. Do not launch the full array blindly. Reuse the printed absolute manifest path for later submissions. After each batch:

```bash
(
set -e
cd /home/vrrcelestino/model-agrologistic
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
: "${NINE_MANIFEST:?Set the absolute manifest path printed when creating the campaign}"
/home/vrrcelestino/venv313/bin/python scripts/audit_nine_campaign.py "$NINE_MANIFEST"
)
```

This writes `nine_results.csv/json` and `nine_stage_gaps.csv/json`, with missing/failed instances retained. Preflight writes `nine_preflight.csv/json`. Compare runs only under their recorded hardware and solver settings.

## Additional populations

`build_nine_population_workbooks.py SOURCE_WORKBOOK --population-order data/processed/warehouse_population_v020/warehouse_population_order.csv --output-dir data/processed/nine_population_inputs` generates 300, 400, 600, 700, 800, 900 and 1000 from the existing rank. Replace SOURCE_WORKBOOK with its verified local path; do not resample the candidates. Existing 215/500 OSRM workbooks remain untouched.

For each new size, submit `scripts/materialize_policy_osrm_population.slurm` with exported `TARGET_POPULATION`, `SOURCE_COMMIT` and an absolute `INPUT_WORKBOOK` pointing into `nine_population_inputs`. The output remains `data/processed/policy_population_v020_osrm/warehouses_SIZE`. Existing outputs are protected. Serialize materialization jobs initially to avoid quota pressure; the versioned SQLite cache is reused. Then rerun the campaign preflight. Full population execution remains gated on these actual counts and resource measurements.

## Zenodo curation

A separate dataset draft exists at https://zenodo.org/uploads/22751909 with reserved DOI `10.5281/zenodo.22751909`. The draft is not published and no files have been uploaded. The reserved DOI must not be represented as an available public dataset.

```bash
(
set -e
cd /home/vrrcelestino/model-agrologistic
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
/home/vrrcelestino/venv313/bin/python scripts/inventory_zenodo_data.py \
  --data-root /home/vrrcelestino/model-agrologistic/data \
  --output-dir "/home/vrrcelestino/zenodo-agrologistic-inventory-$(date -u +%Y%m%dT%H%M%SZ)"
)
```

Review this read-only hash/size inventory before creating partitioned archives: canonical inputs; derived populations and road-distance provenance; experiment definitions and accepted results; incomplete/failed research evidence; publication tables/figures. Exclude credentials, private material and regeneration caches. Rights for third-party registry and OSM-derived content require per-asset attribution and licensing; the code's MIT license is not automatically a dataset license. No data are deleted, moved or uploaded by the inventory script.

## Qualification status

Local focused validation: 66 tests passed; seven licensed Gurobi tests skipped because the local license expired. NPAD licensed execution, exact larger-population counts, empirical runtime limits, native SCIP parity and dataset publication remain outstanding. This draft does not certify those unfinished activities.
