# Pipeline entry points

Run commands from the repository root, not from quarantine or a result folder.
Use the same isolated Python environment as the selected evidence. Each command
supports `--help`; inspect its input and output defaults before execution.

| Stage | Entry points | Effects |
|---|---|---|
| Source lineage | `reconcile_artur_benchmark.py`, `build_artur_instance.py` | Verify/acquire pinned assets and persist a bounded instance |
| Normalization | `normalize_artur_instance.py`, `build_artur_solver_workbook.py` | Produce audited derived inputs; never silently alter raw evidence |
| Population | `audit_warehouse_registry.py`, `build_policy_population_workbooks.py` | Select nested real facilities and translate candidate capacities/costs |
| Road distances | `materialize_policy_osrm_workbook.py`, `materialize_policy_osrm_population.slurm` | Query OSRM/cache and persist distances with provenance; no MILP solve |
| Topology | `audit_route_coverage.py` | Report selected routes, gaps and eligible repairs |
| Preflight/solve | `run_batch_hpc.py` | `--dry-run` loads/estimates; normal mode builds, solves and exports |
| Existing-run audit | `audit_existing_run.py` | Rebuild model audit after identity checks; does not optimize |
| Quality receipt | `run_validation_suite.py` | Run Ruff, pytest and build; record environment-bound receipt |
| Final acceptance | `validate_v020_evidence.py` | Assess required references and quality evidence; does not solve |
| Manuscript comparison | `build_manuscript_comparison.py`, `check_manuscript.py` | Generate/check frozen tables and figures; no solver execution |
| Bounded retries | `run_pr25_nine_scenario_retry.py`, matching `.slurm` | Guard approved identity and isolated outputs for two reference retries |
| Presentation | `build_mvp_scientific_evidence.py`, `generate_scientific_plots.py`, `generate_scientific_results.py` | Build tables/figures from existing outputs, with historical defaults |
| Original-evidence comparison | `finalize_solver_comparison.py` | Verify the frozen Sprint C archive, reconcile exported input identities and generate the 13-attempt report; no solver execution |
| Preliminary comparison | `build_solver_comparison.py` | Reproduce the historical nine-attempt subset from the two earlier archives; not the final Sprint C cohort |
| Storage hygiene | `audit_repository_hygiene.py`, `quarantine_repository_artifacts.py` | Audit first; move/compress only explicitly reviewed candidates |

`run_batch_hpc.py --aggregate-only` rebuilds summary tables; it cannot create
missing optimization evidence. `audit_existing_run.py` is also not a substitute
for solving or the independent final acceptance checks.

## Current versus historical execution

Use [the comparison report](../docs/evidence/sprint_c_final_20260920/comparison_summary.md)
for the completed nine-scenario Gurobi/SCIP campaign. Its original-evidence
archive can be processed with `finalize_solver_comparison.py --original-archive`
and `--output-dir`, supplying the existing archive path and a new output directory.
The report is bound to the documented archive SHA256; a different cohort requires
an explicit reporting revision. It does not import a solver, rebuild a model,
or overwrite original audits. Matplotlib is required for figures.

The [reference catalogue](../experiments/README.md) and
[PR #25 retry runbook](../docs/pr25_nine_scenario_retry.md) preserve the earlier
bounded validation, not a request to resubmit completed jobs.
`run_trl6_protocol.py` and its historical document preserve the earlier v0.1
demonstration; they are not the v0.2 four-level validator.

The presentation scripts retain historical campaign defaults. Inspect explicit
directory arguments and scientific comparability before preparing a v0.2
manuscript. Creating a plot manifest does not accept the underlying solves.

`benchmark_model.py` and `inspect_excel_instance.py` are exploratory utilities,
not the current reference launcher. Their optional dependencies and historical
assumptions must not be inferred from the native validated pipeline.

## HPC execution discipline

- Activate the existing Conda prefix and export `PYTHONNOUSERSITE=1` before Python.
- Keep credentials outside Git and reuse the authorized license configuration.
- Use an explicit run index, bounded resource request and separate output root.
- Keep intermediate reports and submission receipts within project-owned
  directories, not loose in the home directory. Existing virtual environments
  remain in place; housekeeping is a separate reviewed operation.
- Do not switch branches or install packages while jobs use a shared checkout.
- Inspect the real job ID returned by `sbatch`; angle-bracket placeholders are
  not valid shell arguments to copy literally.
- A successful Slurm exit is necessary but not sufficient for scientific
  acceptance. Inspect completion, independent validation and stage statuses.

Do not paste `exit 1` into an interactive terminal to implement a guard. Prefer
the versioned scripts, whose nonzero process exit returns control to the shell.
