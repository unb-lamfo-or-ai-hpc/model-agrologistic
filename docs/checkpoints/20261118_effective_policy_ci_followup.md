# PR158 policy and solver-free CI follow-up — 18 November 2026

## Researcher authorization

Continue PR158 with grounded beta/alpha scope and sensitivity-level proposals,
repeat tests on final code, organize CI without solvers and present readiness.
Keep PR156/158 Draft. No policy activation, new HPC job or merge is authorized.

## Changes

- Propose per-product/scenario, full-horizon beta floors and alpha export/supply
  ceilings, with explicit alternatives, limits and necessary feasibility checks.
- Propose staged diagnostic levels, kept in a separate non-executable JSON file.
- Add exact-diff CI routing and a guarded explicit data/construction test runner.
  Keep retained native qualification steps; do not claim their skipped jobs passed.
- Add code-review/CI/authorization checklist, distinct from future policy approval.

See [the scientific proposal](../effective_beta_alpha_proposal.md),
[protocol](../effective_parametric_protocol.md) and
[readiness](../effective_ci_and_merge_readiness.md).

## Evidence and technical corrections

The first local guarded test attempt blocked Windows host-information subprocess
use. The runner now caches host metadata before
its test boundary, blocks native imports using a catchable missing-dependency
exception, and treats forbidden optimizer/process execution as a hard failure.
An initial shutdown profiler annotation issue was corrected without changing
the scientific runtime. Original failed local receipts remain in custody.

Both final local repetitions passed 86 tests with no skips/failures/errors,
identical test/runtime source inventories and zero optimizer calls or forbidden
execution attempts. Ruff, Node syntax and offline wheel packaging passed;
all 48 packaged modules match. See
`docs/evidence/effective_policy_ci_20261118.json`. The original pandas warning
remains disclosed. Actual exact-head Actions results are reviewed in PR158;
the local receipt never asserts cloud success. Existing 65-test/private h215
receipts remain historical evidence, with the new inventory distinguished.

## Preservation and handoff

The two effective runtime modules, original neutral template and seven qualified
algebra modules remain unchanged from implementation commit c9fe8bc. Source
workbooks, registry, complete derived data, previous packages and original
qualification receipts are preserved. No article/supplement file is edited.
PR156 stays at its author-reviewed head; array2252608 is not inspected live,
submitted, cancelled, retried or otherwise changed.

Next: review scopes/levels and code/CI evidence. Any integration, activation or
future h215 experiment needs its own corresponding researcher authorization.
