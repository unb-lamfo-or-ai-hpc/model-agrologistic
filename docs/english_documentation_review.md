# Scientific documentation and implementation commentary

## Scope

The documentation presents deterministic and two-stage stochastic grain-storage
planning, input provenance, numerical interpretation, independent validation and
HPC execution to an international research audience. Original prose, code comments
and docstrings use English. Original geographic identifiers, data-schema names,
bibliographic titles and localization keys retain their operational meaning.

The bounded NPAD study concluded with nine of ten references accepted. The final
warehouse-only nine-scenario trial reached the time limit in the capacity pass;
the economic pass was not executed. The original certificate remains rejected.
The [validation report](v020_validation_report.md) records this computational
limit rather than treating development closure as complete reference acceptance.

## Documentation coverage

- Root README: research questions, model scope, installation, reproducible use
  and qualified validation outcomes.
- Directory guides: documentation, data sources, templates, benchmarks,
  experiments, scripts, implementation, localization and tests.
- Interpretation: costs, service, separate slack quantities, handling metrics,
  timing, numerical bounds and stochastic value metrics.
- Source commentary: stochastic nonanticipativity, activation, feasibility,
  routing provenance, value metrics and independent residual checking.
- Historical protocols: explicitly distinguished from the current formulation
  and its final bounded experiment.

## Verification and provenance

Python changes in this documentation review are comments and docstrings.
Executable AST equality, after removing docstrings and source-location
attributes, was checked against the implementation baseline. This establishes
the intended scope of the edits, not identical Python text, identical
`__doc__` values or numerical equivalence with a historical thesis.

The recorded local review inspected 107 Python files; 13 changed files retained
equal executable ASTs. It checked 101 relative documentation links without
missing targets. Ruff passed; the local suite reported 296 passed and
49 licensed tests skipped because the local Gurobi license was expired.
Wheel and source distribution builds passed. These local checks are distinct
from the accepted zero-skip licensed NPAD quality receipt.

Source identity includes Python text, including comments and docstrings.
Consequently, archived execution receipts retain their original implementation
and runtime fingerprint; their hashes are not rewritten for this documentation
revision. Re-execution requires its own compatible environment and quality
receipt. Optional forecasting modules were inspected without importing their
environment-repair side effects.

## Research communication

The final resource-limited case is reported as an independently valid incumbent
with incomplete objective optimization. It is neither omitted nor described as
an infeasible mathematical model. The 1% configured relative-gap criterion was
not relaxed retrospectively. Comparative economic and warehouse-level analyses
require matching exported decisions and cannot be reconstructed from acceptance
flags alone.

Further computational research includes scenario decomposition, controlled
algorithm/thread comparisons and larger nested warehouse populations. Original
contributions are distributed under MIT with explicit third-party licensing and
data-provenance boundaries.
