# Gurobi 14 dependency declaration — 24 November 2026

The local DELL5300 environment loads Python 3.13.15 and gurobipy 14.0.0. A silent Gurobi environment initialisation accepted the existing local license, with no optimization. The 203-distribution inventory was unchanged by the review. No credentials were read, copied, hashed or committed. The CFL-GNN upgrade receipt separately reports that only gurobipy changed and that the other 202 distribution versions were preserved.

The editable Agrologistic checkout is clean on main at `7e953f07f829b4ea4521253eca4bb8f1e2b3c994`. Its pyproject SHA-256 is `11e752d2bc0261eda5e7d219e85be7c5b5457f872c4d646ae30cffb8c89fef49`. Develop at `2391137cdbe4f86cdb784f9e4e545944fac2a688` still declares the same four <14 requirements; there is no equivalent open PR.

## Source change

Change only the four existing Gurobi declarations from `gurobipy>=13.0.2,<14` to `gurobipy>=13.0.2,<15`: required dependencies and the gurobi, hpc and all extras. The lower bound and every other dependency declaration remain unchanged. No extra is installed or activated.

A narrow CI routing control recognises exactly those four byte substitutions. A pyproject change by itself remains outside the solver-free route unless the two tracked blobs pass that exact comparison. Any additional edit, lower-bound change, different ceiling or scientific-builder change retains normal qualification routing. Tests cover acceptance and rejection, dependency specifiers and the existing optimizer/process barriers. This is CI routing for the approved metadata change, not a general exemption for dependency edits.

## Local and installation boundaries

The checked source in this chat's authorised worktree contains the same four-line patch. The installed editable checkout outside that worktree is preserved. Its installed requirement metadata still says <14, so the recorded installation conflict remains until the source change is accepted and that checkout is reconciled through the project's workflow.

After acceptance, the bounded installation operation is a metadata-only editable refresh with `--no-deps`, without extras, followed by pip check and before/after distribution comparison. That operation is not performed in this PR because the researcher requires the shared environment to remain unchanged. The Python base and every unrelated package remain outside scope.

## Validation and limitation

Twenty local metadata/routing controls and Ruff passed. They accept Gurobi 14, retain 13.0.2 compatibility in the declaration and reject 15.0.0. The existing license acceptance is a technical environment check, not a full Agrologistic qualification or a new scientific result. No NPAD/DGX call, optimization, training, benchmark, merge or publication is performed.
