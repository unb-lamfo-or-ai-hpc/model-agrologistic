# Model Agrologistic

**Headless optimization core for agricultural logistics, HPC experiments, and graph-based learning datasets.**

---

## Overview

`model-agrologistic` is a research-oriented Python project for modeling and solving agricultural logistics network optimization problems.

The project originated from the SiloDSS codebase, which was initially designed as a web-based decision support system. This repository is now being refactored into a **headless computational core** focused on:

- mixed-integer linear programming models for agricultural logistics;
- deterministic and two-stage stochastic optimization;
- native Gurobi execution through `gurobipy`;
- solver-neutral execution through `Pyomo`, especially for SCIP;
- precomputed road-distance matrices using OSRM;
- batch execution in HPC environments;
- generation of structured optimization outputs for Graph Neural Networks.


---

## Current Refactoring Goal

The current goal is to transform the former SiloDSS application into a modular optimization and data-generation pipeline:

```text
raw data
  -> preprocessing
  -> distance matrix generation
  -> canonical model data
  -> MILP backend
  -> solution extraction
  -> metrics
  -> GNN/HPC dataset export
```

The project is under active refactoring. Some files and modules described below may still be under construction.

---

## Planned Architecture

```text
model-agrologistic/
├── data/
│   ├── raw/
│   ├── processed/
│   ├── distances/
│   └── instances/
│
├── scripts/
│   ├── build_distance_matrix.py
│   ├── run_single_instance.py
│   ├── run_batch_hpc.py
│   └── export_gnn_dataset.py
│
├── src/
│   └── logic/
│       ├── model_data.py
│       ├── model_config.py
│       ├── model_validation.py
│       ├── preprocessing.py
│       ├── distance_matrix.py
│       ├── osrm.py
│       ├── optimization.py
│       ├── optimization_pyomo.py
│       ├── optimization_gurobipy.py
│       ├── metrics.py
│       ├── exporters.py
│       └── gnn_dataset.py
│
├── tests/
│   ├── test_model_data.py
│   ├── test_model_validation.py
│   ├── test_gurobipy_deterministic.py
│   ├── test_pyomo_deterministic.py
│   ├── test_backend_equivalence.py
│   ├── test_stochastic_model.py
│   └── test_gnn_export.py
│
├── pyproject.toml
└── README.md
```

---

## Optimization Backends

The project is being designed to support two complementary optimization backends.

### 1. Native Gurobi backend

The primary backend will use `gurobipy` directly.

This backend is intended for:

- large-scale MILP experiments;
- high-performance execution;
- tighter control over Gurobi parameters;
- solution extraction for GNN datasets;
- HPC batch runs.

### 2. Pyomo backend

The Pyomo backend will be retained as a solver-neutral alternative.

This backend is intended for:

- SCIP execution;
- comparison with the native Gurobi implementation;
- model validation;
- open-source solver experiments.

The objective is to keep both backends mathematically equivalent.

---

## Mathematical Scope

The model family includes agricultural logistics network optimization with:

- origins, warehouses, candidate facilities, and demand nodes;
- multiple products and time periods;
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
- deterministic and two-stage stochastic formulations.

During the refactoring, particular attention will be given to:

- enforcing zero-supply and zero-demand balance constraints;
- preventing emergency capacity at closed candidate facilities;
- distinguishing static capacity slack from reception capacity slack;
- making candidate capacity decisions economically consistent;
- computing dynamic capacity and turnover metrics after optimization;
- computing EVPI and VSS for stochastic experiments.

---

## OSRM and Distance Matrices

OSRM is retained as the preferred source for road-distance matrices.

However, OSRM should be used as a preprocessing step, not inside the optimization loop.

The intended workflow is:

```text
geographic nodes
  -> OSRM query/cache
  -> distance matrices
  -> optimization model input
```

The HPC jobs should read precomputed distance matrices from disk.

---

## HPC Execution

The repository is being prepared for execution in HPC environments, including Slurm-based clusters.

The intended workflow is:

```text
prepare instances locally or in preprocessing node
submit batch jobs
solve MILP instances with Gurobi or SCIP
export solution files
build graph datasets for GNN training
```

Docker is not required for the HPC workflow.

---

## GNN Dataset Generation

A future goal of the project is to export optimization instances and optimal solutions as graph datasets.

Expected outputs include:

```text
nodes.csv
edges.csv
flows.csv
warehouse_decisions.csv
warehouse_metrics.csv
scenario_metrics.csv
labels_node.csv
labels_edge.csv
graph.pt
```

These files will support supervised learning and algorithm-selection experiments using graph neural networks.

---

## Installation

Clone the repository:

```bash
git clone https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git
cd model-agrologistic
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Activate it on Linux/macOS:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -e .
```

Dependency organization is still being refactored. The final version will separate core, Gurobi, Pyomo, SCIP, OSRM, and GNN dependencies.

---

## Development Status

This repository is currently in the early stage of refactoring.

Completed:

- removal of web frontend files;
- removal of Docker application entry points.

In progress:

- cleaning obsolete references to Dash, Plotly, Docker, and WSGI;
- defining canonical model data structures;
- separating model configuration from solver implementation;
- preparing the optimization backends.

Planned:

- native `gurobipy` deterministic model;
- Pyomo-compatible deterministic model;
- two-stage stochastic formulation;
- OSRM distance matrix preprocessing;
- HPC batch scripts;
- GNN dataset exporters;
- mathematical consistency tests.

---

## License

See `LICENSE`.