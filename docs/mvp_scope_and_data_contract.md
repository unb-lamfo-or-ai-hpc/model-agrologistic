# MVP scope and frozen data contract

## Research objective

The MVP is a research prototype intended to demonstrate TRL 6 evidence in the
NPAD environment. It must load a documented workbook, solve deterministic and
two-stage stochastic MILP cases, export auditable decisions and performance
metrics, and reproduce the experiment from versioned configuration. It is not
a market deployment, graphical decision-support product, or claim of numerical
identity with the thesis before the original generated instance is recovered.

## Included capabilities

The frozen MVP includes:

- Excel-to-`ModelData` ingestion with validation and explicit fallbacks;
- deterministic and two-stage stochastic Gurobi formulations;
- configurable one-, three-, and nine-scenario experiments;
- warehouse opening, expansion, bulkification, transshipment, direct routes,
  inventory, domestic demand, and export upper bounds;
- penalty and lexicographic slack policies, with EVPI/VSS restricted to the
  scalar penalty objective;
- DynCap, Turnover, service, emergency-capacity, cost, runtime, and memory
  outputs;
- YAML campaigns, Slurm execution, preflight size guards, resumable EVPI/VSS,
  and structured JSON/CSV artifacts.

Pyomo/SCIP parity, a graphical interface, automated forecasting, and a trained
GNN are outside this MVP. They may be evaluated after the TRL 6 demonstration.

## Two evidence tracks

The data contract deliberately keeps two tracks separate.

### Artur benchmark reproduction

This track is the bounded reproduction baseline. Its source is the `benchmark`
directory of `cvictorr2508/silodss`, pinned to commit
`9d190ce91bb60c192329c4bbd5638f24909cb1e2`. The individual Git blob hashes and
sizes are recorded in `data/manifests/mvp_data_contract.json`.

This track supports comparison with the thesis assumptions and published case
structure. Numerical identity must not be claimed until every generated input,
random seed, network-construction rule, solver setting, and historical software
dependency used by the thesis has been reconstructed or recovered.

### Gold workbook extension

This track is the canonical MVP instance for extension and robustness testing:

```text
data/templates/model_agrologistic_padrao_ouro.xlsx
SHA-256: de3bdc51b2c338194a5013165bec2884b68784fb207ae8c762984a1b44856082
```

Its frozen structural signature is 37 origins, 215 warehouses (146 existing
and 69 candidates), 27 domestic customers, 10 export customers, 2 products,
and 60 periods. Formula-backed candidate and expansion fields are recovered
from documented workbook parameters when cached Excel values are absent; the
loader reports these derivations instead of silently replacing them with zero.

Results from this track are an extension and robustness test, not a direct
numerical validation of Artur's thesis.

## Reproducibility contract

Every official MVP run must retain:

1. the Git commit of this repository;
2. the experiment YAML and workbook SHA-256;
3. the preflight data signature and model-size estimate;
4. Python executable, environment prefix, package versions, and Slurm IDs;
5. solver options, solution status, runtime, MIP gap, and peak memory;
6. structured result, audit, decision, flow, inventory, service, and metric
   artifacts.

Slurm jobs set `PYTHONNOUSERSITE=1` so packages installed under the user's home
directory cannot override the selected Conda environment. Interactive runs
should use the same setting.

## Sprint 1 acceptance gate

Sprint 1 is complete when all of the following hold on NPAD:

- the canonical workbook hash matches the frozen contract;
- the full test suite passes with `PYTHONNOUSERSITE=1`;
- a dry run writes `preflight.json` with the expected structural signature,
  package versions, and no unexplained zero investment values;
- the Artur benchmark source remains pinned to the recorded immutable commit;
- PR #15 remains limited to data ingestion, data identity, environment
  isolation, and reproducibility documentation.

Warnings from unsupported Excel data-validation extensions are currently
non-blocking because the loader reads values rather than re-saving the official
workbook. They must be revisited if the pipeline starts writing that workbook.
