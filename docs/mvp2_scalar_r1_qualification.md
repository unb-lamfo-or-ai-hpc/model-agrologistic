# R1 scalar software qualification — 19 October 2026

Scope: consolidated [PR112](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/112)
replaces closed, unmerged PR111. This is small software/mathematical qualification,
not NPAD execution, scalability evidence or approval of future resource budgets.

## Immutable references

- Pre-refactor develop/archive: `5f9daa55b3afb5bbcb3449bc83c970cf10a28ca6`,
  `archive/mvp2-multiobjective-20261019`, created before implementation.
- Preserved PR111 head: `dffc8b79e8c6c8033be0fb5fbff6d7b6ca1d8f7c`.
- Qualified implementation candidate: `c72afc65fd4c200e630753bf911e87f29092936e`.
- Git source subtree `src`: `666029ace80bd60417d91c43d4460a33326acf64`.
- Git retained-test subtree: `641fb17aab389e9e2ebd3f281f9764c07c21e165`.

The final checkpoint-only commit must retain these source/test trees and pass
the exact-head workflow again before Ready. See the PR checks for that final
revision; this document does not claim to contain its own future commit hash.

## Qualification results

| Gate | Observed result | Reference / limitation |
| --- | --- | --- |
| T1/T2 | Focused/related scalar, facade, SCIP, resource and integrity regressions passed while editing | Local Gurobi license skips were disclosed, not accepted as native qualification |
| T3 exact-head Linux | **497 passed; zero failures, errors or skips** | [Scalar R1 CI](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/actions/runs/39323120878); Python3.13.16, Gurobi13.0.3 restricted small-model license, PySCIPOpt6.2.1 |
| Native/lifecycle related CI | Passed | [SCIP](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/actions/runs/39323120962), [resources](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/actions/runs/39323120950) |
| General quality / distribution | Ruff, retained tests and distribution build passed | [Quality](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/actions/runs/39323120990) |
| Full local Windows | 441 passed, 56 skipped, zero failures/errors | All56 skips: expired local Gurobi license; native SCIP ran. Not a diagnosis of NPAD WLS |
| Source/scope | One native objective and optimizer call per backend; physical/tracked source closure passed | Original manuscript, data and `docs/evidence` unchanged against archive; changed Markdown links have no missing local targets |

Downloaded Linux JUnit: 497 tests, zero failures/errors/skips, SHA256
`d364fd7d6000dbac6a9477371fcb156a510d917328609feda13c8abb40d5084e`.
The raw CI artifact remains attached to the workflow, not committed as HPC evidence.
One pre-existing pandas concatenation FutureWarning remains; it is not hidden.

The earlier513-case full gate also passed on `b686143f79f9834dbb73bac05818662f713dd92d`.
The difference is16 retired historical campaign-generator cases, not removal of
failing mathematical tests. Their exact code remains in the archive; read-only
historical-record and sensitive-file inventory checks remain active.

## What was checked and corrected

Analytical costs, DET/one-scenario STO equivalence, unequal probabilities,
investment once under duplicate-scenario splitting, the three distinct slacks,
physical routes/capacity coupling, corrupted costs/residuals, finite incumbent/
missing-bound handling, disposal/telemetry and real Excel -> ExperimentSpec ->
independent validation -> closed artifacts are exercised. No new large instance
or performance comparison was run.

Initial CI failures are retained in the PR history. Repairs restored DET physical
summary keys; distinguished legitimate first/second-stage recourse metadata from
objective priorities; replaced a retired hierarchy test with the scalar cost
trade-off; removed orphaned archived fixtures; and isolated mocked license paths
so dummy selection tests cannot contaminate later native tests. CI attributes
preserve two original historical manuscript blobs without normalization; their
tracked bytes were not edited. No penalty coefficient, physical unit or residual
tolerance was relaxed to obtain a pass.

## Boundary and next owner

No NPAD job/probe, claim reset, retry, manuscript edit, merge or branch promotion.
Existing designated NPAD WLS/path is confirmed unchanged, not freshly tested here.
R1 denies Slurm optimization. Ready requires the final exact-head checks; merge
requires the researcher's explicit authorization. R2 must separately qualify
small native/operational evidence and reviewed resources before any human CLI.
Historical hierarchy/thread results are not scalar performance certificates.
