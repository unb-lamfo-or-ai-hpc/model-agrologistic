# Model Agrologistic

Research software for strategic agricultural logistics planning through
deterministic and two-stage stochastic mixed-integer linear programming (MILP).
The model evaluates warehouse opening, capacity expansion and bulkification
under supply and demand uncertainty. Its intended use is reproducible research
and public-investment analysis, not operational dispatch or a production service.

## Research status and scope

The completed nine-scenario comparison contains **13 optimization attempts**:
seven Gurobi and six native SCIP/SoPlex attempts. Gurobi produced four
quality-certified attempts at a 10% per-stage gap target and a nominal
28,800-second optimization budget: both 215-warehouse variants, the historical
direct-enabled 300-warehouse variant, and the all-barrier warehouse-only
300-warehouse repeat. Both all-barrier 400-warehouse runs retain independently
valid incumbents but do not meet the complete hierarchical quality criterion.
SCIP produced no incumbent in the tested 215/300-warehouse attempts: four
time limits and two earlier memory limits. These are configuration-specific
outcomes, not proofs of infeasibility or universal solver-size limits.

See the [comparison report](docs/evidence/sprint_c_final_20260920/comparison_summary.md),
[paired-input reconciliation](docs/evidence/sprint_c_final_20260920/paired_input_reconciliation.json)
and [documentation roadmap](docs/sprint_d_documentation.md). Original failures,
resource amendments and historical method variants remain separate observations.
SCIP 400-warehouse cases were preflight-only; no 500-warehouse solve is claimed.
Reported input identities match in eight cross-solver pairings, but hardware,
memory, runtime versions and algorithms are not all controlled. This is not a
speedup experiment or a full revalidation of absent raw solution files.

### Historical bounded thesis-method demonstration

The package is **0.2.0.dev0**. It distinguishes a bounded reconstruction of
Artur's thesis methodology from an expanded policy-oriented network. Neither
track establishes exact numerical replication of the published thesis tables:
the historical road-network snapshot and forecasting path have not been
reconstructed, and separate feasibility slacks change the historical objective.

The bounded demonstration concluded with nine of ten selected references
accepted. Mathematical/data contracts, licensed software tests and independent
solution checks passed. The warehouse-only nine-scenario trial reached its
14,400-second optimization budget in the capacity pass, with a 100% relative
gap; the economic pass was not executed. Its domestic-service target and
independent feasibility checks passed. This is a documented computational limit,
not evidence of model infeasibility.

The original four-level certificate remains rejected, with level 4 incomplete.
Development closure does not change that outcome or the configured 1% gap
target. See the [validation report](docs/v020_validation_report.md) and
[final evidence](docs/evidence/pr25-final/README.md) for identities and stage
observations. Successful CI is not a substitute for scientific acceptance.

The archived v0.1.0 package records a maintainer-accepted computational
demonstration in the relevant NPAD environment under the project's TRL 6
protocol. It is historical development evidence, not independent accreditation
or certification of v0.2. See the [historical protocol](docs/trl6_reproducibility_protocol.md).

## Scientific questions

The [scientific manuscript](manuscript/README.md) presents the formulation,
computational protocol, observed outcomes and limitations. Its Quarto HTML/PDF
build uses committed observations and does not execute the solver. Journal
submission and public document deployment are separate from branch integration.

1. How do uncertainty and direct origin-to-customer routes affect first-stage
   investments, domestic service and logistics costs?
2. Where do nominal storage or reception capacities fail to support the
   optimized allocation, and how sensitive are these findings to model policy?
3. What computational effort is required for explicitly defined network and
   scenario sizes under controlled solver settings and hardware?

The completed comparison covers nine-scenario optimization attempts at
215, 300 and 400 warehouses. Road-distance materialization also reached 500
warehouses; this is not a certified 500-warehouse optimization. Native SCIP
analytical and licensed miniature parity qualification passed on NPAD, while
large SCIP instances did not yield incumbents within the tested budgets.
Larger populations, a definitive scalability frontier and the complete
15/20/25% sensitivity campaign remain future work.

## Mathematical interpretation

- All supply must reach domestic deliveries, exports or warehouse inventory.
  There is no free disposal or unused-supply decision.
- Domestic deliveries plus unmet-demand slack equal domestic demand. Export
  deliveries are bounded above; terminal inventory is free within the balance
  and capacity constraints.
- First-stage investment decisions are shared across stochastic scenarios;
  transport, inventory and feasibility slacks are scenario-dependent recourse.
- The thesis-method track minimizes scalar cost with dynamic penalties. The
  policy track prioritizes domestic service, then an emergency-violation score,
  then economic cost, subject to declared solver tolerances.
- Emergency variables diagnose relaxed constraints; they are not installed
  infrastructure or procurement recommendations. They do not guarantee
  unconditional complete recourse: shipping, connectivity and activation remain
  hard constraints.
- Reception overflow is already **tonnes within a period**, after nominal daily
  throughput has been multiplied by operating days. Do not multiply the slack
  by 30 again. Static exceedance is a warehouse-period stock quantity; summing
  it over periods does not yield an installed capacity requirement.

Read the [mathematical contract](docs/v020_mathematical_contract.md) and the
[results interpretation guide](docs/results_interpretation.md) before comparing
costs, service, capacity, timing or EVPI/VSS.

## Reproducible workflow

```text
Pinned sources and workbook contracts
  -> normalized instance and OSRM distance materialization
  -> route selection, connectivity audit and size preflight
  -> frozen network/penalties and selected native solver
  -> independent solution validation and structured artifacts
  -> reference acceptance, scientific tables and figures
```

OSRM supplies distance along the fastest route for its configured driving
profile. The 20% rule retains a grouped fraction of the shortest materialized
edges; it is not a Pareto-optimal network or a cumulative-cost 80/20 rule. Policy
connectivity repairs use existing eligible routes and are reported separately.
Audited Haversine fallbacks are restricted to declared routing/snap conditions;
HTTP failures or timeouts must not silently change the distance method.

### Installation for a new research environment

Use Python 3.13. Gurobi optimization and licensed cross-backend parity tests
require a valid Gurobi license; native SCIP uses its separately qualified runtime.
Dependency ranges
are in [pyproject.toml](pyproject.toml); replay additionally requires the exact
package versions recorded in the environment receipt.

Run from the repository root. On Linux, for a **new virtual environment**:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
export PYTHONNOUSERSITE=1
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

On Windows, activate `.venv\Scripts\Activate.ps1` and set
`$env:PYTHONNOUSERSITE = '1'`. The `visualization` extra installs Matplotlib and
Seaborn without the remaining development tools. The `all` extra includes
optional forecasting packages and is not required for the reference pipeline.
Native Gurobi and stochastic PySCIPOpt backends are implemented. The `scip`
extra supplies the optional dependency; installation alone does not qualify a
runtime or certify a large solve. See the
[SCIP qualification protocol](docs/scip_qualification_protocol.md) and
[completed comparison](docs/evidence/sprint_c_final_20260920/comparison_summary.md).
Deterministic SCIP, SCIP EVPI/VSS and SCIP IIS are not supported by this backend.
CBC is not a project target. Do not install or upgrade packages in an environment
used by an active or archived campaign merely to read the comparison.

On NPAD, the existing `venv313` prefix is a **Conda environment**, despite its
name. Use `conda activate /home/vrrcelestino/venv313`, not a nonexistent
`bin/activate`. Set `PYTHONNOUSERSITE=1` before starting Python. User-site
packages can otherwise shadow the approved solver version. Do not reinstall
packages or switch branches while reference jobs use that checkout.

Keep license files outside version control. Set `GRB_LICENSE_FILE` to the
existing authorized license; never publish its contents. This repository does
not distribute a Gurobi license.

### Verification and execution

For a local development checkout:

```bash
python -m ruff check .
python -m pytest -p no:cacheprovider
python -m build
```

Missing or expired licenses can cause analytical solver tests to be skipped.
That is useful software feedback but cannot satisfy the licensed final quality
gate. [tests/README.md](tests/README.md) explains the distinction.

After the specified generated OSRM workbook exists, a solver-free preflight is:

```bash
python scripts/run_batch_hpc.py experiments/v020_thesis_compatible.yaml --index 0 --dry-run
```

This loads data and estimates size; it neither builds nor optimizes the MILP.
It still writes preflight artifacts: use a separate output directory to protect
existing campaigns. Do not omit `--index` in a large campaign: outside a Slurm
array, omission selects all experiments.

The [experiment catalogue](experiments/README.md) identifies the reference plan.
The [script guide](scripts/README.md) separates preprocessing, solving, auditing
and reporting. The [retry runbook](docs/pr25_nine_scenario_retry.md) records the
completed experimental procedure. Replaying a reference requires its original
implementation and environment; documentation-only source changes do not
authorize rewriting the fingerprints of archived results.

## Repository guide

| Directory | Purpose |
|---|---|
| [docs](docs/README.md) | Current contracts, interpretation and historical protocols |
| [data](data/README.md) | Source lineage, templates and generated-artifact boundaries |
| [benchmark](benchmark/README.md) | Historical assets, not a certified generated instance |
| [experiments](experiments/README.md) | Versioned definitions and reference selection |
| [scripts](scripts/README.md) | Preprocessing, execution and reporting entry points |
| [src](src/README.md) | Data, model, solver and independent-validation architecture |
| [tests](tests/README.md) | Analytical, integration and integrity checks |

Code comments and research documentation are written in English. Portuguese
workbook columns, geographic identifiers and legacy localization keys remain
stable data/API contracts; they are not translated opportunistically.

## Sharing and citation

Follow [CONTRIBUTING.md](CONTRIBUTING.md) for review and provenance requirements.
Use [CITATION.cff](CITATION.cff) and report the exact commit, input identities,
solver/runtime versions and experiment configuration. The code is licensed under
[MIT](LICENSE) for original project contributions; third-party data and software retain their own licensing
and attribution requirements.
See [licensing and data redistribution boundaries](LICENSING.md) before
redistributing source datasets, upstream benchmark assets or derived databases.

A Quarto Manuscript based on `cvictorr2508/quarto-sbc` is planned after the
reference evidence and documentation review. It must distinguish thesis-method
comparison, historical v0.1 evidence and policy extensions. This branch neither
publishes the article nor changes repository visibility.
