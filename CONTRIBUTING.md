# Contributing

## Scientific review and evidence isolation

Use English for research prose, code comments and docstrings. Preserve workbook
column names, geographic identifiers and localization keys as stable contracts.
Explain the mechanism and scientific qualification, not just what an assignment
does. Do not add speculative claims of exact thesis replication or unconditional
complete recourse.

Never change a shared NPAD checkout or its packages while jobs use it. PR #26 is
stacked on PR #25 to isolate documentation from ongoing validation. After PR #25
merges, retarget and reconcile the documentation branch before requesting review.
Keep it draft until the maintainer authorizes Ready for review.

Comments and docstrings in `src/logic` change the implementation fingerprint.
Documentation outside those files does not. Preserve accepted receipts with the
original commit/runtime; AST equivalence is useful review evidence but does not
permit rewriting hashes or relabeling an old run as a new execution. Document a
new source identity explicitly, even for behavior-preserving comment changes.

For a documentation-only PR, inspect executable AST differences, relative links,
command defaults, Ruff, tests and distribution build. Keep dependency ranges,
solver parameters, manifests, tolerances and data unchanged. Qualify local
licensed-test skips separately from NPAD acceptance.

This repository is a research demonstrator. Contributions should preserve its
scientific traceability and explicit distinction between reproduction,
controlled extension, and exploratory work.

## Development setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
export PYTHONNOUSERSITE=1
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest
```

## Contribution rules

- Create a focused branch from `develop`, or an explicitly approved stacked base.
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

Gurobi is the native reference backend for the archived v0.1 demonstration and
current v0.2 validation. Native PySCIPOpt parity remains deferred. CBC is not a
target backend.

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
