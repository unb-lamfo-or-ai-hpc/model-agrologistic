# Researcher decisions and implementation boundary — 18 November 2026

## Approved

- Preserve historical effective inputs and accepted results.
- Implement original/effective/scenario separation, derived XLSX inspection files,
  normalized CSV ingestion, provenance and neutral parameter controls.
- Reuse ModelData and the existing DET/STO scalar Pyomo formulation.
- Qualify h215 data/construction locally without optimization.
- Version code, documentation and redacted evidence in PRs to develop.
- Keep PR156 Draft and array2252608 unchanged.

## Subsequent approved policy implementation

The researcher approved the full-horizon, per-product/scenario beta/alpha scopes
and proposed levels, explicitly requesting implementation in PR158. This overrides
the earlier separate-PR suggestion. The [policy implementation](../effective_policy_implementation.md)
reuses the existing builder, preserves null defaults and adds independent checks.
No solver/HPC execution, merge or manuscript change is authorized.

## Pending scientific decisions

1. Positive absolute fixed costs and empirical calibration by technology.
2. Future execution package, resource budget and numerical qualification.
3. Any annual/local service policy or alternative export denominator beyond the
   approved horizon scope.

## Preserved restrictions

No solver execution, HPC submission, source-data replacement, distance
recalculation, direct main/develop edit, merge, article/supplement modification,
Zenodo publication or manuscript submission. W only for future experiments;
h215 D remains historical. h300+ expansion follows completion of h215.

## Historical accounting checkpoint supplied by researcher

Array2252608:34COMPLETED,5FAILED(_6,_17,_19,_21,_24),_39RUNNING and
_40–_59PENDING. The final collector is already uploaded within the approved
NPAD project directory. Wait for all60tasks to become terminal; do not repeat
submission or treat scheduler completion as accepted scientific output.

## Technical choices made under this mandate

- Freeze effective penalties and investment maxima before independent scenarios.
- Reject non-neutral beta/alpha and positive fixed-cost overrides pending approval.
- Store full private derived artifacts locally; publish only code/schema/redacted receipts.
- Check STO algebra by all full-horizon scenario blocks to fit local32GiB RAM.
- The first implementation commit suspended optimizer-calling CI with its commit
  message. The subsequent researcher request authorizes scoped solver-free CI,
  repeat tests and policy proposals; native tests/branch protections are retained.

Evidence status is recorded separately from these authorizations in the local
qualification report and redacted GitHub receipt. This document authorizes no
future experiment, calibration conclusion or publication.
