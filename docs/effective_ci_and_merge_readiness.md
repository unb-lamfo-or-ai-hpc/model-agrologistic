# Solver-free CI and merge readiness for PR158

## Authorized execution scope

The researcher requests repeat tests on final code, CI without solvers and a
readiness checklist. These are software/data checks; no new numerical baseline,
calibration or sensitivity result is generated. PR156 remains Draft and its
sources are unchanged. PR158 also remains Draft pending review and authorization.

The first implementation commit c9fe8bc used `[skip ci]`. This follow-up supplies
an explicit alternative, preserving each retained native qualification workflow.
It does not change branch protection, merge policy, experimental solver settings
or the historical 2252608 campaign. Do not use `[skip ci]` on the follow-up head.

## Routing design

`effective_ci_scope.py` compares full base/head commit SHAs with rename detection
disabled. Only the enumerated effective-data code/test/config paths, associated
CI routing files and documentary paths select the data route. A mathematical
builder, loader, source workbook, campaign controller, dependency manifest or
unlisted path keeps the native route. Deleted/renamed scientific sources therefore
cannot disappear from the path comparison. Invalid/missing refs fail the routing
job; dependent qualification does not run after routing failure.

The reusable `ci-scope.yml` exposes `data_only`. Existing Quality, Pyomo, Scalar,
SCIP and Resource workflows keep their original qualification steps and job names,
and run them when data_only is false. For this data-only PR they are explicitly
skipped, not passed as solver tests. `effective-data.yml` runs the replacement
data/construction check on the exact PR head, without `[skip ci]`.

The pattern follows the official GitHub documentation for
[reusable workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)
and [job outputs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/pass-job-outputs).
This is reviewed workflow logic, not a security boundary against arbitrary edits
to CI itself. Any modification of routing/allowlisted executable files needs code
review; the classification is not evidence that those changes are scientifically
correct. Confirm the final diff still lies within this mandate before pushing.

## Data route execution

- Install explicit data/Pyomo-construction/test/build dependencies and the project
  with `--no-deps`; do not install Gurobi, HiGHS, SCIP, CBC or native licenses.
- Run Ruff and JavaScript syntax validation; do not render large private workbooks
  in cloud CI or supply private data to Actions.
- Run the explicit inventory in `check_effective_contract.py`. Disable unrelated
  pytest plugin autoload. Reject skips/errors/failures and forbidden execution.
- Import barriers prevent native solver loading. Call barriers reject project/
  Pyomo optimizer entry points. Audit barriers reject child processes during the
  test phase. Cache Windows host metadata before that phase for JUnit reporting.
- Build distributions separately, without dependency installation or optimization.
- Upload only tiny public-fixture test receipts, source hashes and JUnit results.

These barriers support the declared inventory; they are not general sandbox or
host-security certification. Existing tiny fixtures verify algebra without being
new experimental instances. Full private h215 algebra evidence from the original
implementation is preserved; cloud CI does not rebuild that large private matrix.

## Merge-readiness checklist

| Item | Status / evidence |
| --- | --- |
| Original/effective/scenario separation; penalty/ceiling independence | Implemented; existing regression controls |
| h215 DET and all nine STO block equivalence | Accepted existing receipt; no new optimization |
| beta/alpha/fixed-cost activation blocked; neutral template unchanged | Executable interface unchanged; negative activation tests |
| Scientific runtime/campaign/article sources unchanged by follow-up | Inspect final diff against c9fe8bc and original protected sources |
| Final-code test repetition and source identity | 86 tests passed twice; identical source inventories; [receipt](evidence/effective_policy_ci_20261118.json) |
| Ruff, Node syntax, offline packaging | Passed locally; 48 wheel modules match; no dependency installation locally |
| Exact-head cloud solver-free CI | Inspect [current PR158 checks](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/158/checks); actual confirmation belongs to the current PR review |
| Retained native qualification steps/protections | Preserved; data-route skips are not numerical qualification |
| No private data or machine paths in GitHub additions | Inspect staged diff and redacted evidence |
| Researcher/code review and explicit merge authorization | Pending; both PRs remain Draft |

Pending beta/alpha scope or sensitivity-level approval does not require activating
them to integrate this infrastructure. Those decisions gate later activation and
execution, not a new mandatory experiment or an invented submission milestone.
If existing branch protection requires an additional check, report its actual
status; do not waive it or reinterpret it as green. Readiness never grants merge.
