# Model Agrologistic

**Headless optimization core for deterministic and two-stage stochastic agricultural logistics models.**

---

## Overview

`model-agrologistic` is a research-oriented Python project for modeling and solving agricultural logistics network optimization problems.

The project originated from the SiloDSS codebase, which was initially designed as a web-based decision support system. This repository is now being refactored into a **headless computational core** focused on:

- deterministic mixed-integer linear programming models;
- two-stage stochastic mixed-integer linear programming models;
- structured Excel-based model input;
- canonical, solver-agnostic model data structures;
- native Gurobi execution through `gurobipy`;
- solver-neutral execution through `Pyomo`, especially for SCIP;
- precomputed distance matrices using Haversine or OSRM;
- reproducible execution in local and HPC environments.

The central objective is to implement, validate, and extend the mathematical models from Artur's thesis while keeping the code modular, testable, and independent from any graphical interface.

---

## Current Refactoring Goal

The current goal is to transform the former SiloDSS application into a modular optimization pipeline:

```text
Excel input data
  -> Excel loader
  -> canonical ModelData
  -> model validation
  -> distance matrix generation or loading
  -> MILP backend
  -> solution extraction
  -> metrics
  -> experiment outputs
```

The optimization backends must not read Excel files directly. They receive only canonical data objects.

The current canonical workflow is:

```text
.xlsx workbook
   ↓
src/logic/excel_loader.py
   ↓
src/logic/model_data.py
   ↓
src/logic/model_validation.py
   ↓
src/logic/optimization.py
   ↓
src/logic/optimization_gurobipy.py
   or
src/logic/optimization_pyomo.py
   ↓
OptimizationResult
```

---

## Golden Excel Template

The project uses a golden Excel template as the standard model input schema:

```text
data/templates/model_agrologistic_padrao_ouro.xlsx
```

This workbook is intended to be filled and reviewed by humans, but read automatically by the Python loader.

The template includes:

- documented input sheets;
- model parameters;
- deterministic supply and demand;
- warehouse parameters;
- cost parameters;
- scenario structure for future stochastic models;
- a data dictionary;
- a model-change log.

The loader should read sheets by name, not by sheet position.

### Required deterministic sheets

The minimum deterministic loader depends on:

```text
Oferta
Demanda
Warehouses
Frete
Tarifa_Armz
Custo_Invest
Parametros_Modelo
```

### Governance and documentation sheets

The following sheets should be kept in the template for documentation and reproducibility:

```text
00_README
Dicionario_Dados
Alteracoes_Modelo
Listas
```

### Future stochastic sheets

The following sheets are reserved for the two-stage stochastic model:

```text
Cenarios
Oferta_Cenarios
Demanda_Cenarios
```

---

## Demand Representation

The Excel template should not use `∞` as a numeric demand value.

Instead, export-market rows should be represented explicitly using:

```text
Tipo_Demanda = EXPORTACAO
Regra_Limite = AUTO_OFERTA_TOTAL_PRODUTO_PERIODO
```

For deterministic models, the loader interprets this rule as:

```text
export_upper_bound[p, t] =
    sum of supply over all origins for product p and period t
```

For stochastic models, the corresponding rule will be scenario-dependent:

```text
export_upper_bound[p, t, s] =
    sum of supply over all origins for product p, period t, and scenario s
```

This preserves the thesis assumption of a non-binding export market while keeping the Excel file machine-readable.

---

## Model Improvements and Excel Schema Changes

The project may improve the original thesis model when doing so increases mathematical consistency, computational robustness, or experimental reproducibility.

Every model improvement must be classified as one of the following:

```text
1. No Excel schema change required
2. Optional Excel schema change recommended
3. Required Excel schema change
```

When a new model parameter is introduced, the Excel template must indicate whether the value is:

```text
Informado
Estimado
Sintético
Derivado_da_Oferta
Derivado_de_Custo_Invest
Derivado_de_Warehouses
```

This rule ensures that synthetic parameters remain transparent and traceable.

---

## Planned Architecture

```text
model-agrologistic/
├── data/
│   ├── templates/
│   │   └── model_agrologistic_padrao_ouro.xlsx
│   ├── examples/
│   ├── raw/
│   ├── processed/
│   ├── distances/
│   └── results/
│
├── scripts/
│   ├── build_distance_matrix.py
│   ├── run_single_instance.py
│   └── run_batch_hpc.py
│
├── src/
│   └── logic/
│       ├── model_data.py
│       ├── model_config.py
│       ├── model_validation.py
│       ├── excel_loader.py
│       ├── distance_matrix.py
│       ├── osrm.py
│       ├── optimization.py
│       ├── optimization_gurobipy.py
│       ├── optimization_pyomo.py
│       └── metrics.py
│
├── tests/
│   ├── test_model_data.py
│   ├── test_model_config.py
│   ├── test_model_validation.py
│   ├── test_excel_loader.py
│   ├── test_gurobipy_deterministic.py
│   ├── test_pyomo_deterministic.py
│   ├── test_backend_equivalence.py
│   └── test_stochastic_model.py
│
├── pyproject.toml
└── README.md
```

The `data/templates/` directory is versioned because it contains the canonical input schema.

The following directories should normally remain outside version control:

```text
data/raw/
data/processed/
data/results/
```

---

## Optimization Backends

The project is being designed to support two complementary optimization backends.

### 1. Native Gurobi backend

The primary backend uses `gurobipy` directly.

This backend is intended for:

- large-scale MILP experiments;
- high-performance execution;
- tighter control over Gurobi parameters;
- HPC batch runs;
- production-quality computational experiments.

### 2. Pyomo backend

The Pyomo backend is retained as a solver-neutral alternative.

This backend is intended for:

- SCIP execution;
- comparison with the native Gurobi implementation;
- open-source solver experiments;
- mathematical equivalence testing.

The objective is to keep both backends mathematically equivalent for supported model variants.

---

## Mathematical Scope

The model family includes agricultural logistics network optimization with:

- origins, warehouses, candidate facilities, and demand nodes;
- multiple products;
- multiple time periods;
- deterministic and two-stage stochastic formulations;
- origin-to-warehouse flows;
- warehouse-to-customer flows;
- warehouse-to-warehouse transshipment;
- optional direct origin-to-customer flows;
- warehouse opening decisions;
- capacity expansion decisions;
- bulkification decisions;
- storage, freight, and transshipment costs;
- unmet demand penalties;
- emergency capacity penalties;
- dynamic capacity and turnover metrics;
- EVPI and VSS for stochastic experiments.

During the refactoring, particular attention is given to:

- enforcing zero-supply and zero-demand balance constraints;
- preventing emergency capacity at closed candidate facilities;
- distinguishing static capacity slack from reception capacity slack;
- making candidate capacity decisions economically consistent;
- separating Excel ingestion from optimization backends;
- making deterministic and stochastic inputs extensible;
- preserving traceability for synthetic or derived parameters.

---

## Distance Matrices

Distance matrices should be generated or loaded before optimization.

The optimization backends should not query OSRM during model construction or solution.

The intended workflow is:

```text
geographic nodes
  -> Haversine or OSRM preprocessing
  -> distance matrices
  -> ModelData
  -> optimization backend
```

For unit tests and small examples, Haversine distances may be computed directly from coordinates.

For larger experiments, OSRM should be used as a preprocessing step and cached to disk.

---

## HPC Execution

The repository is being prepared for execution in HPC environments, including Slurm-based clusters.

The intended workflow is:

```text
prepare Excel input
  -> load and validate ModelData
  -> generate or load distance matrices
  -> submit batch jobs
  -> solve MILP instances with Gurobi or SCIP
  -> export solution and metrics
```

Docker is not required for the HPC workflow.

---

## Installation

Clone the repository:

```bash
git clone https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git
cd model-agrologistic
```

Create and activate a Python 3.13 virtual environment:

```bash
python3.13 -m venv venv313
source venv313/bin/activate
```

On NPAD, the existing `/home/vrrcelestino/venv313` installation is a Conda
prefix environment despite its directory name. Activate it interactively with:

```bash
conda activate /home/vrrcelestino/venv313
```

The `source /home/vrrcelestino/venv313/bin/activate` command only applies to a
standard Python `venv` and is not available for this Conda environment. Slurm
jobs do not require activation because the provided script invokes the
environment's Python executable directly.

Upgrade `pip`:

```bash
python -m pip install --upgrade pip
```

Install the project in editable mode with development dependencies:

```bash
pip install -e ".[dev]"
```

Install all optional dependencies when needed:

```bash
pip install -e ".[all]"
```

---

## Gurobi License

The native Gurobi backend requires a valid Gurobi license.

For WLS or HPC environments, the license file can be configured using:

```bash
export GRB_LICENSE_FILE=/secrets/gurobi.lic
```

or by passing a license path through `SolverConfig.solver_options`.

The code is prepared to use `/secrets/gurobi.lic` as the default license path when available.

---

## Running Tests

Run all tests:

```bash
python -m pytest
```

Run only the core structural tests:

```bash
python -m pytest \
  tests/test_model_data.py \
  tests/test_model_config.py \
  tests/test_model_validation.py \
  tests/test_optimization_facade.py
```

Run Gurobi deterministic tests:

```bash
python -m pytest tests/test_gurobipy_deterministic.py
```

If `gurobipy` is installed but no valid license is available, Gurobi-specific tests may be skipped.

---

## Development Status

Completed:

- headless optimization core and canonical `ModelData`;
- golden Excel loader and validation layer;
- deterministic native Gurobi formulation;
- warehouse transshipment and direct origin-customer routes;
- capacity expansion and bulkification;
- two-stage stochastic extensive form with 1 to 9 configurable scenarios;
- RP, WS, EV, EEV, EVPI, and VSS calculations;
- DynCap and Turnover metrics aligned with Artur's thesis;
- reproducible local and Slurm experiment manifests;
- structured JSON/CSV exports, preflight model-size guards, and IIS diagnostics;
- calibrated route policy using `top_k=10`, direct routes, and 30 days per period;
- successful nine-scenario RP and checkpointed EVPI/VSS campaigns on NPAD;
- solver-independent methodological audit of inputs and structured solutions;
- pragmatic Stage 5.6 policy contract: candidate construction cost per ton,
  period-specific operating days, and an optional lexicographic slack policy.

Current:

- Stage 5.8 MVP and data freeze, with separate Artur benchmark reproduction
  and gold-workbook extension tracks.

The model keeps full origin-supply allocation, treats reception and shipping
as daily rates converted with a 30-day fallback, and does not impose an
arbitrary service floor. Scalar EVPI/VSS remains available only for the penalty
objective. See
[`docs/service_level_methodology.md`](docs/service_level_methodology.md) and
[`docs/methodological_audit.md`](docs/methodological_audit.md). The MVP boundary
and frozen data identities are documented in
[`docs/mvp_scope_and_data_contract.md`](docs/mvp_scope_and_data_contract.md).

Planned:

- attainable service-cost frontier before any scenario service constraint;
- scientific result tables and plots;
- Pyomo/SCIP parity and backend equivalence, if retained as a project
  requirement.

---

## License

See `LICENSE`.
