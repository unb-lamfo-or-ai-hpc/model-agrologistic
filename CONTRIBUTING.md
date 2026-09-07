# Contributing

This repository is a research demonstrator. Contributions should preserve its
scientific traceability and explicit distinction between reproduction,
controlled extension, and exploratory work.

## Development setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest
```

## Contribution rules

- Create a focused branch from `develop`.
- Keep optimization backends independent from Excel ingestion.
- Add or update tests for every behavior change.
- Document mathematical and data-contract changes before merging them.
- Keep code comments, docstrings, commit-facing documentation, and README files
  in English.
- Preserve Portuguese workbook identifiers when they belong to the stable data
  contract.
- Do not commit solver licenses, WLS credentials, raw private data, generated
  HPC outputs, or local environment paths.
- Do not present controlled stochastic scenarios as reconstructed forecasts.
- Report Big-M feasibility penalties separately from observed economic costs.

Gurobi is the validated backend for version 0.1.0. Native PySCIPOpt may be
evaluated after the TRL 6 freeze. CBC is not a target backend.

## Pull requests

A pull request should state:

- its scientific or technical objective;
- affected model assumptions and data contracts;
- tests executed and their environment;
- whether a valid Gurobi license was available;
- any change to reproducibility manifests or expected evidence;
- remaining limitations.

Large experimental outputs should be archived outside Git and referenced by a
small manifest with checksums.
