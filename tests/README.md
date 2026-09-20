# Verification strategy

Tests address software and mathematical implementation, not automatic empirical
validation or agreement with a published numerical result.

| Family | Evidence |
|---|---|
| Input contracts | Workbook schema, duplicate normalization, source lineage and candidate activation |
| Routing | OSRM failure/fallback/cache rules, numerical integrity, selected edges and connectivity |
| Analytical MILPs | Small licensed Gurobi cases for costs, balances, capacities and scenarios |
| Native SCIP | Stochastic analytical cases and separately licensed miniature cross-backend parity |
| Independent validation | Deliberately invalid sparse outputs, local residuals and cost reconstruction |
| Value analysis | Frozen RP/WS/EV/EEV contracts, first-stage fixing and bound-based certification |
| Execution integrity | Receipts, completion markers, stale-output rejection and safe retries |
| Presentation | Reader-facing units, tables, plots and source provenance |

Run from the repository root in the selected environment:

```bash
python -m ruff check .
python -m pytest -p no:cacheprovider
python -m build
```

CI and local development can skip licensed tests when a usable Gurobi license
is unavailable. Report the pass and skip counts separately. The final NPAD
quality gate requires zero skipped tests and compatible source/runtime identity.
Use `scripts/run_validation_suite.py --output-dir <new-directory>` for its receipt;
replace the placeholder before execution. Do not rerun it in an active campaign
directory or install a new environment while jobs are still using that checkout.

A successful quality receipt is level 2, not completion of all four levels.
Reference executions require independently validated artifacts and complete
lexicographic stages as specified by the final validation plan. Time limits,
incomplete hierarchies and skipped tests remain visible rather than being
reclassified to obtain a green report.

The original four-level reference gate and the later nine-scenario campaign are
separate protocols. In the latter, input admission only permits an attempt;
independent feasibility validates an incumbent; quality acceptance additionally
requires all three priorities and their declared bounds. A no-incumbent run
cannot establish service success through default-valued reporting fields.

Solver-free manuscript checks verify bibliography, author metadata, generated
table/source hashes, figure integrity and rendered outputs. They neither rerun
an optimizer nor promote an unsuccessful experiment. See
[the manuscript build](../manuscript/README.md) and
[the measurement dictionary](../docs/artifact_dictionary.md).
