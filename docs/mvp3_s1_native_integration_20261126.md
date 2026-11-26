# MVP3 S1: native effective-data and policy integration

Base: develop `22fd493fd74f99320b9f2757d9c4927ffb7551bc` (PR164 merged).
Scientific reference: approved English EN Rev4, 24 November 2026.

## Result and boundaries

Sealed effective data now use the retained native Gurobi extensive-form builder
with full-horizon beta/alpha rows and the existing candidate/expansion limits.
DET is embedded as one realization with probability one; STO shares its single
investment vector across the operational realizations. The original input seal
is retained for independent validation after DET output projection.

This PR prepares software, construction checks and decision export. It does not
qualify a licensed solve, the full production native matrix, production memory,
or live-source consistency. Native/public qualification and human NPAD execution
remain separate gates. No job, license probe, optimizer call, environment change,
merge or scientific publication is part of the local S1 verification.

The existing user checkout is preserved in place. Development uses a separate
managed worktree at the approved base. Original data, accepted receipts, consumed
claims, historical solver profiles, the complete registry and frozen graphs are
not rewritten. Prior Draft164 statements remain dated evidence; PR164's verified
merge receipt governs its administrative status.

## Native integration

`prepare_effective_native` verifies the effective input and scenario seals before
the native facade selects a license path. The policy rows remain indexed by
product and scenario, with no probability weights in their tonne constraints.
The original destination-period export bounds remain in the native builder.
Disabled policies add no rows; an enabled zero remains an explicit policy.

`populate_native_model` is the construction portion of the existing native
extensive-form implementation. The solve path and local symbolic controls use
this same function. Investment costs, daily-capacity coupling, indicators,
balances, original bounds and the scalar objective retain their construction
helpers. Local symbolic tests do not emulate optimization or establish native
solver numerical equivalence.

K is applied by the existing immutable `apply_scenario` transformation, once to
`max_candidate_capacity` and `max_expand_capacity`. The native builder consumes
those transformed bounds directly. Initial assets, the separate bulk limit,
unit/fixed costs and actual installed-tonne accounting retain their reference
meaning. Native indicators are preserved; no new Big-M substitution is added.

## Reference configuration

`reference_solver_config()` creates a fresh native configuration with
`Method=-1`, `Threads=0`, `TimeLimit=28800`, `mip_gap=None` and `seed=None`.
The two `None` values mean that the native parameter setter leaves MIPGap and
Seed untouched. Existing SolverConfig callers retain their historical defaults
and explicit assignments. Other backends cannot select an unset MIPGap.

The effective native path rejects a historical/tuned profile, extra optimization
options, IIS diagnostics or index compaction before native import. A future
execution checks Gurobi major version 14 and reads back the automatic controls
and selected default parameters. This selected readback is not the complete S2
telemetry/default-audit qualification. No native parameter readback was performed
against an installed optimizer during local S1 tests.

## Complete decisions and independent checks

For sealed effective inputs, native extraction retains every selected OD/DC/DD
flow, inventory, domestic shortage and static/reception exceedance, including
zeros, plus every warehouse's investment decisions. Historical unsealed runs
retain their sparse export behavior.

Before physical/economic validation, `dense_vector_coverage` checks the expected
indices and rejects omissions, duplicates and unexpected records. It tracks
periods with bitmaps per index group rather than allocating another full dense
vector. Record order does not determine acceptance. The retained independent
effective validator then reconstructs balances, original-unit costs and policies
from the original sealed DET or STO data. Its tolerances are unchanged.

No incumbent produces no fabricated objective, gap or planning vector and receives
`no_usable_incumbent`, not a feasibility certificate. A complete but invalid plan
retains its rejected validation report. Passing software checks is not a claim
that any agricultural case was solved.

## Local verification

The guarded data/algebra runner now includes native construction/export controls.
A focused subset also covers SolverConfig compatibility. Both inventories block
native solver imports, optimizer entry points and child-process execution.

```text
python -B scripts/check_effective_contract.py --native-only --output <new-local-directory>
python -B scripts/check_effective_contract.py --output <another-new-local-directory>
python -B scripts/check_mvp3_native_inputs.py --baseline <frozen-baseline-v2.xlsx> --registry <frozen-registry-v2.xlsx> --bundle <frozen-normalized-v2-directory> --output <new-local-report.json>
```

The input check verifies the accepted workbook/bundle identities and all 24
catalogued h215 transformations sequentially. It checks native embedding and
policy-row assembly without allocating a native model or rebuilding road routes.
It rechecks source and file identities after inspection. Private inputs and local
reports remain outside Git; only redacted evidence belongs in the PR.

Local symbolic controls cover neutral native algebra against the retained Pyomo
construction, preservation of native indicators, two-product/two-period DET and
nine-scenario STO indexing, K scaling, shared investment accounting, unchanged
unit prices, parameter assignment/readback doubles, dense output, JSON round-trip
precision, independent validation and missing/duplicate vector rejection.

## Scientific sequence and pending gates

The Rev4 initial catalog remains 8 P0/K cases followed by 16 P1-P8/K=1 cases,
reusing P0/K=1. There are 24 first observations, not a mandatory repeated grid.
The ceilings remain 192 native hours and 288 allocation hours at 192 GiB.
Calendar progression depends on accepted evidence, queue access and entitlement;
the older PT-BR presentation's fixed-week table is not the governing schedule.

After S1 local software preparation, complete instrumentation, resource/default
audits, finite-queue/claim controls and separately authorized native/public
qualification before the S2-A/S2-B scientific cycle. Repetitions, diagnostic
treatments and h300/h400/h500 progression remain conditional on accepted h215
evidence and finite approved budgets. Larger DET inputs need their own
qualification. No Benders, GPU, thread-speedup or K-by-active-policy grid is added.

Keep `source_consistency_certified=false`. Frozen routing lineage and the accepted
T2 closeout remain valid within their documented scope; neither this PR nor local
data checks certify the current live cache or fresh NPAD staging.

Remote CI is intentionally withheld under the researcher's local-checks-only
instruction. The PR remains Draft pending separately admitted qualification and
the applicable review gates. No branch-protection or workflow rule is weakened.
