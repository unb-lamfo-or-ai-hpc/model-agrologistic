# Experiment catalogue

YAML files define scientific configurations, not proof that every listed run has
been executed. Indices are zero-based and local to each manifest. Always check
the experiment name printed by preflight before submitting a job.

## Final PR #25 reference selection

[v020_validation_reference.yaml](v020_validation_reference.yaml) selects ten
executions from four manifests. It is a validation plan, not a solver manifest.

| Manifest | Selected indices | Scientific role |
|---|---|---|
| [v020_thesis_compatible.yaml](v020_thesis_compatible.yaml) | 0, 1, 6, 7 | Bounded alpha 0.8, deterministic/three scenarios, direct off/on |
| [v020_policy_service_feasibility.yaml](v020_policy_service_feasibility.yaml) | 0, 2 | Service-first deterministic references |
| [v020_policy_mvp.yaml](v020_policy_mvp.yaml) | 8, 9 | Service-first three-scenario references at 20% |
| [v020_policy_nine_scenario_retry.yaml](v020_policy_nine_scenario_retry.yaml) | 0, 1 | Nine-scenario references with a 14,400-second solver budget |

The original 3600-second selection remains in
[v020_validation_reference_t3600.yaml](v020_validation_reference_t3600.yaml).
Retries use fresh names and output directories; do not overwrite earlier runs.
The historical selection closed with nine accepted references and one incomplete
warehouse-only nine-scenario hierarchy. The original aggregate certificate remains
rejected. The later comparison below has a different time/gap/network contract
and does not retroactively change that certificate.

## Completed nine-scenario solver comparison

The [frozen comparison](../docs/evidence/sprint_c_final_20260920/comparison_summary.md)
contains seven Gurobi and six SCIP attempts at 215--400 warehouses, including
unsuccessful configurations and identified repeats. Its nominal optimization
budget is 28800 seconds, with a 10% capacity/economic pass-gap target and a
separate absolute service certificate. Four Gurobi attempts at 215/300 are
quality-certified; three have valid but uncertified incumbents. All six SCIP
attempts at 215/300 ended without incumbents. SCIP 400 is preflight-only.

Historical launch protocols document actual configurations and failure handling;
they are not pending submissions. No new NPAD run is required to reproduce the
comparison or manuscript. Use the [artifact dictionary](../docs/artifact_dictionary.md)
to distinguish input readiness, independent feasibility and solution quality.
Raw manifests remain frozen; a new solve requires a new output identity.

Thesis index 6 is stochastic because indices 0–5 contain the six deterministic
configurations. Thesis index 1 is the deterministic direct-arc case, not the
stochastic counterpart. Policy indices follow their own factor ordering.

## Interpretation and deferred configurations

The thesis profile preserves the historical grouped 20% rule without repairs.
Policy uses `connectivity_preserving_pareto`: retain grouped nearest edges, then
add audited existing routes to meet the selected coverage contract. A repair is
not a synthetic distance or a guarantee of capacity feasibility.

The policy manifest also defines 15% and 25% configurations. Their presence is
not authorization to launch the complete factorial or a claim of acceptance.
[v020_policy_time_limit.yaml](v020_policy_time_limit.yaml) is a separate timing
study; [v020_thesis_topology_control.yaml](v020_thesis_topology_control.yaml)
is a separately named connectivity control. Neither substitutes for a required
reference merely because it produces a more attractive result.

Older files without the `v020_` prefix retain v0.1/exploratory campaigns. Their
network, objective, data and stage policies can differ. Never aggregate them
with current runs as though they were replicates of the same experiment.

## Safe use

Run from the repository root with the approved isolated environment. Use an
explicit index and `--dry-run` before an authorized compute-node solve. Omitting
the index outside Slurm can execute the entire manifest. Preflight writes
artifacts but does not call Gurobi. Large solves belong on allocated compute
nodes; a scheduler wall-time limit and Gurobi's solver limit are distinct.

Changing a manifest, input hash or implementation requires a new identified
experiment. Resume and aggregation must reject incompatible evidence rather than
relaxing the integrity contract. See [the retry runbook](../docs/pr25_nine_scenario_retry.md).
