# Implementation architecture

The import namespace is `src.logic`. The scientific pipeline is intentionally
separated into input translation, mathematical policy, solver construction and
independent output validation.

| Responsibility | Principal modules in `logic/` |
|---|---|
| Canonical data and configuration | `model_data`, `model_config`, `excel_loader`, `model_validation` |
| Historical input lineage | `artur_benchmark`, `artur_instance`, `artur_normalization`, `artur_adapter` |
| Real population extension | `warehouse_population`, `warehouse_workbook` |
| Road-distance authority | `osrm`, `policy_osrm` |
| Selected graph | `route_filtering`, `route_coverage`, `route_connectivity` |
| Frozen mathematical semantics | `mathematical_contract`, `capacity_bounds` |
| Solver facade and native models | `optimization`, `optimization_gurobipy`, `optimization_gurobipy_stochastic` |
| Value-of-information analysis | `stochastic_analysis_gurobipy` |
| Independent checks and identities | `solution_validation`, `run_integrity`, `v020_validation` |
| Execution and diagnostics | `experiment_runner`, `model_audit`, `objective_diagnostics` |
| Metrics and presentation | `metrics`, `scientific_evidence`, `scientific_plots`, `scientific_results` |

First-stage investments are common to scenarios in the extensive form. Flow,
inventory and slack decisions are scenario-indexed. Freeze selected routes and
penalties before RP/WS/EV/EEV projections so these calculations represent one
scientific contract rather than separately reconfigured networks.

The independent solution validator must not import solver expressions or reuse
their capacity/cost construction helpers. Its ability to detect implementation
errors depends on reconstructing the constraints from input and output records.

`run_integrity` hashes normalized Python source in `logic/` and numerical package
versions. **Comments and docstrings in these files affect the identity**, even
when executable semantics are unchanged. Preserve old receipts and run them
against their original checkout/runtime; never rewrite a hash to admit evidence.

## Legacy and optional modules

`optimization_pyomo` is not a parity-certified alternative to the native model.
The native SCIP facade is a reserved, explicitly unimplemented path. `prediction`
retains exploratory forecasting code outside the reference campaign; importing
it can invoke historical environment-repair logic, so it is not an import-only
documentation probe. No forecasting reconstruction is claimed for the thesis.

`i18n`, `utils` and [locales](locales/README.md) preserve earlier interface
contracts. English documentation does not justify changing Portuguese runtime
keys, geographic names or workbook schemas. The reference workflow is CLI-based,
not a certified graphical user interface.
