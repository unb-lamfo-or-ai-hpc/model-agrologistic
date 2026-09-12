# PR #26: English scientific documentation review

## Scope and dependency

This draft is stacked on PR #25 at commit
`177a469c5a55f292062c625bbcc71f7e93d5cd73`. The maintainer authorized parallel
documentation work while the nine-scenario retries run. It does not modify that
branch, the NPAD checkout, job resources or the reference-selection plan.

The latest supplied accounting lists jobs `2088823_0` and `2088823_1` as running
on intel-256, each with 16 CPUs and 96 GiB, at elapsed 01:33:40. This is a reported
checkpoint, not live monitoring. PR #25 level 4 remains pending until its final
receipts are reviewed. This draft cannot make that gate pass.

## Review changes

- Reorganize the root README around scientific questions, reproducible use and
  qualified evidence rather than the historical release workflow.
- Add directory guides for docs, data, source manifests, templates, benchmark,
  experiments, scripts, implementation, localization and tests.
- Document costs, service, separate slack quantities, handling metrics, timing,
  numerical bounds and publication requirements in a reader-facing guide.
- Correct stale current-contract wording about unconditional complete recourse,
  direct template use, route repairs and the final reference gate.
- Identify older campaign protocols as historical records. Their archived
  observations are not silently rewritten as v0.2 validation.
- Expand English comments/docstrings around stochastic nonanticipativity,
  feasibility interpretation, routing, value metrics and independent checking.
- Preserve Portuguese schema names, geographic identifiers and localization
  keys. They are runtime/data contracts, not untranslated research commentary.

## Verification and limitations

The review inventories Python comments across `src`, `scripts` and `tests` and
checks changed Python ASTs after removing only docstrings and source-location
attributes. Executable AST equality is required; comments and docstrings are
the only intended Python changes. No manifest, solver parameter, dependency,
data file, test expectation or mathematical expression is changed.

AST equality does not assert identical `__doc__` values or byte identities.
It also does not establish numerical equivalence with a historical thesis.
Legacy forecasting modules are inspected as text, not imported: their optional
environment-repair side effects remain outside the reference pipeline.

The root and directory navigation links are checked against existing repository
paths. Historical external links and unavailable generated HPC files are not
presented as locally re-executed evidence. Local Ruff, tests and distribution
build results are recorded in the PR; skipped licensed tests remain explicit.

### Local verification receipt (2026-09-12)

- Python source inventory: 107 files; 13 changed Python files, all with equal
  executable ASTs after docstring removal. The remaining Python files are unchanged.
- Relative documentation links: 101 checked, zero missing targets.
- Ruff: passed. Full suite: 296 passed, 49 skipped, four warnings, 49.19 seconds.
  The skips are licensed Gurobi tests; the local license expired on 2024-03-03.
- Source distribution and wheel: built successfully with `build --no-isolation`
  using the existing local development dependencies.
- Import-path checks confirm the reviewed documentation checkout supplies the
  native solver and identity modules. Its local source/runtime fingerprint is
  `3fc456ed2a411e6a23868ffd672972a25b95942342efb230d194eb318db4d6e2`.

These checks do not replace the zero-skip NPAD receipt for PR #25. No licensed
optimization was performed as part of this documentation review.

## Identity and handoff

`run_integrity.implementation_identity()` hashes all Python text in `src/logic`
after newline normalization. Consequently this comment/docstring review has a
new identity even though the executable AST is unchanged. This is deliberate
provenance, not a reason to weaken the guard or rewrite accepted receipts.

Finish PR #25 validation against its original source/runtime. Preserve that
commit, its workbooks, original receipts and final accepted run selection for
publication. Do not switch NPAD to this branch while the jobs are active or
validate old runs under the new comment-only identity. A new execution under
PR #26 would need its own compatible quality receipt; it is not required merely
to preserve and publish PR #25's correctly identified evidence.

After PR #25 merges, retarget this draft to `develop`, reconcile any intervening
changes and request maintainer authorization before Ready for review. The
existing CI trigger targets `main` and `develop`, so a stacked PR does not
automatically receive that workflow until retargeted. Do not report absent CI
as successful. No CI-policy change is bundled into this documentation PR.

The subsequent Quarto Manuscript uses `cvictorr2508/quarto-sbc`. Before writing
numerical claims, freeze the final evidence package and select compatible
table/figure inputs explicitly. Publication, repository visibility and a release
tag remain separate actions. No new NPAD solve is requested by this draft.
