# Experimental artifacts and measurement semantics

Files are conditional on the selected workflow and on whether a solution exists;
a filename alone is not an acceptance certificate. Historical manifests retain
their original contracts. See the [comparison](evidence/sprint_c_final_20260920/comparison_summary.md).

## Phase outputs

| Phase | Principal outputs | Interpretation |
| --- | --- | --- |
| Source normalization | `supply.csv`, `demand.csv`, `warehouses.csv`, `distances.csv`, `transformation_audit.json` | Historical inputs and conservation/provenance checks |
| Candidate population | `warehouse_population_manifest.json`, `warehouse_population_order.csv`, `warehouse_population_levels.csv`, `population_workbook_manifest.json`, per-population `model_input.xlsx` | Nested site selection; candidates have zero usable base capacity |
| Routing | `osrm_materialization_audit.json`, updated `model_input.xlsx`, persistent pair cache | Directed distance authority and numerical-integrity counts |
| Input/preflight | `preflight.json`, campaign-specific input/admission receipts | Sizes, scenarios, routes and permission to attempt a solve |
| Interhub topology | `interhub_connectivity_audit.json`, `interhub_components.csv`, `interhub_repair_edges.csv`, `interhub_path_summary.csv` | Baseline, repairs, retained fraction and multi-hop paths |
| Native solve | Native log, `result.json`, `run_summary.json`, `lexicographic_stages.csv` | Termination, incumbents, stage objectives/bounds and timings |
| Decision export | `flows.csv`, `inventories.csv`, `warehouse_decisions.csv`, `unmet_demand.csv`, `emergency_capacity.csv` | Sparse decisions; interpret empty files with solve status |
| Independent checks | `independent_validation.json`, `model_audit.json`, completion receipt and hashes | Constraint/cost reconstruction and artifact identity |
| Derived reports | `scenario_performance.csv`, `material_balance_by_scenario.csv`, `capacity_gap_by_scenario.csv`, `investment_saturation.csv`, `emergency_capacity_daily.csv`, `storage_by_warehouse.csv`, `storage_by_scenario.csv` | Scenario service, conservation and capacity diagnostics |
| Optional analyses | `evpi_vss_decomposition.csv`, `value_analysis_timings.csv`, `infeasibility.json` | Only supported/requested analyses; an empty file is not a zero result |
| Campaign aggregation | `batch_summary.csv`; `nine_results.json`, `nine_results.csv`, `nine_stages.json`, campaign audit receipt | Acceptance scoped to selected indices |
| Comparative cohort | `comparison_cases.json`, `comparison_stages.json`, `paired_input_reconciliation.json`, `evidence_inventory.json`, `comparison_artifact_manifest.json`, `comparison_summary.md`, `runtime_memory_comparison.png/.svg` | Thirteen frozen attempts, failures and identity limitations |
| Manuscript | `comparison_results.qmd`, `comparison_provenance.json`, `pipeline.png`, `solver-comparison.png`, HTML/PDF and LaTeX package | Derived presentation, not a new solver validation |

Historical figures remain in `manuscript/figures/`; the earlier ten-reference
experiment is labeled separately. The compact comparison archive does not
contain every solution CSV above. Its inventory lists supplied and missing
members; absent full solutions were not revalidated during manuscript preparation.

## Units and clocks

- Distance: kilometres after OSRM metre conversion. Ordered pairs need not be
  symmetric. Logical route counts differ from coordinate-cache counts.
- Flow and reception overflow: tonnes during a period. Daily nominal handling
  rates are converted once. Do not multiply period overflow by 30 again.
- Static exceedance: stock tonnes at a warehouse-period. Its weighted sum over
  periods is a violation score, not installed storage capacity.
- Economic cost excludes artificial penalties. `penalized_cost` is a diagnostic
  scalar, not the optimized lexicographic objective.
- `optimization_seconds` measures the application optimization region;
  `solver_reported_runtime_seconds` is native solver time. Build, input reading,
  extraction, validation and export have separate scopes. End-to-end and
  solve-sequence intervals overlap; do not add them.
- EVPI/VSS auxiliary solves belong to `postoptimality_seconds`; this comparison
  disables them. Scalar value metrics do not automatically apply to a hierarchy.
- Application RSS is a process-lifetime high-water mark. Exported `peak_rss_mb`
  values are treated as MiB and divided by 1024 for GiB. Slurm MaxRSS is a
  distinct sample. Internal memory settings are not RSS or node allocations.
- Gap fractions become percentages by multiplication by 100. Report attained
  gaps per pass. Zero-service sentinels are not violations; use the absolute
  certificate. Missing incumbents have no certified service, cost or finite gap.

## Four distinct decisions

1. Software qualification: analytical and licensed miniature parity tests pass.
2. Input admission: inputs and allocations permit a named attempt.
3. Independent feasibility: an actual incumbent satisfies the contract within
   recorded residual and sparse-export tolerances.
4. Hierarchy quality: every priority meets the campaign's bounds and inherited
   limits. A feasible incumbent may fail this final test.

The historical gate is not rewritten by later experiments. Failed attempts are
scientific evidence. Document rendering and green CI do not supply missing
optimization evidence or author approval for submission.
