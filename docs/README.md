# Documentation catalogue

Read the current mathematical contract before interpreting historical plots or
executing an older campaign. Dates and experiment names matter: a chronological
development record is not a single invariant specification.

## Current v0.2 reference

| Document | Use |
|---|---|
| [Mathematical contract](v020_mathematical_contract.md) | Units, constraints, objectives and evidence boundaries |
| [Four-level validation report](v020_validation_report.md) | Accepted checks and remaining executions |
| [Nine-scenario retry runbook](pr25_nine_scenario_retry.md) | Bounded completion without overwriting evidence |
| [Results interpretation](results_interpretation.md) | Costs, service, capacity, timing and EVPI/VSS |
| [Policy design](v020_policy_experiment_design.md) | Reference factors and deferred experiments |
| [Connectivity audit](v020_route_connectivity_audit.md) | Grouped edge selection and identified repairs |
| [Warehouse population protocol](v020_warehouse_scalability_protocol.md) | Nested real facilities and materialization limits |
| [Data lineage](mvp_scope_and_data_contract.md) | Historical source pin and canonical workbook identity |
| [Repository hygiene](repository_hygiene.md) | Conservative, reversible artifact handling |
| [English documentation review](english_documentation_review.md) | PR #26 scope and evidence isolation |

## Historical development and reporting tools

The following documents retain earlier experiments and decisions. Observations
belong to their original configurations, not automatically to v0.2. The earlier
emergency-first hierarchy differs from the current service-first policy.

- [Artur reconstruction](artur_reproduction_protocol.md),
  [three-scenario extension](artur_stochastic_extension.md) and
  [nine-scenario gate](artur_nine_scenario_gate.md).
- [Service-policy history](service_level_methodology.md) and
  [methodological audit](methodological_audit.md).
- [HPC runner guide](hpc_experiments.md), including historical examples.
- [Scientific evidence package](mvp_scientific_evidence.md),
  [visualization](scientific_visualization.md) and
  [results presentation](scientific_results_presentation.md).
- [v0.1 TRL demonstration protocol](trl6_reproducibility_protocol.md).

Generating a figure does not establish acceptance. For a manuscript, select
validated, comparable executions explicitly; check historical default directories
and retain plot manifests and tidy source data.
