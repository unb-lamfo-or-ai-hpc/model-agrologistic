# MVP2 closeout: develop, main and Pages

## Approved integration

On 20 November 2026 the researcher approved the PR157 working PDFs and explicitly
authorized its develop merge. All six workflows passed at head
`3081a81f5b74d33747aecacb7c12dab40d282b98`. The verified merge is
`32cfa1846ebde278ba4ebbb4eea990a14b461770`; its tree equals that approved head.
The article has 36 pages and the complete supplements have 81 pages.

The final h300 block contains 33 accepted solutions, nine time-limited returns,
seven native soft-memory limits, seven external memory-guard stops and four
researcher cancellations. The final evidence and historical records remain
unchanged. No further MVP2 optimization is planned by this publication work.

## Why publication preparation has its own PR

The previous Pages pipeline rendered Quarto, whereas the researcher reviewed
the LaTeX in `manuscript/author-review`. The publication preparation therefore
selects those exact editorial sources and their reviewed artwork. It does not
rewrite the article or silently substitute an older text. Quarto sources remain
available as a separate editorial representation in GitHub.

The asset archive contains 42 flat, frozen dependencies from the approved
editable project. Together with main.tex, supplement.tex and references.bib,
45 individual file hashes are checked before compilation. Template notices,
the original Appendix A and documentary GAMS files accompany the assets.
There are no workbooks, numerical flow vectors, credentials or execution logs.

The protected-main ancestry check requires the promotion head to be develop.
Current main `3df439d29224b3501c6896605de4402813208052` is one merge commit ahead
of the common ancestor `965ca52777a5899163af72c9630e591b82c61de8`. Their Git trees
are identical (`fac07535624a3273de837635ffb8974e4be34c40`). The preparation branch
retains main as an additional parent, preserving its ancestry without restoring
superseded manuscript or scientific code.

## Review and release sequence

| Step | Evidence / action | Authorization state |
| --- | --- | --- |
| PR157 to develop | Six passing workflows; reviewed PDFs; verified merge 32cfa184 | Completed with explicit authorization |
| Publication preparation to develop | Frozen editorial inputs, local rebuild, source/ZIP/PDF checks and exact-head CI | Separate PR; merge pending |
| Develop to main | Draft promotion PR, including preparation after its approved integration; ancestry and final CI rechecked | Merge pending; explicitly excluded from the present authorization |
| Pages | Manual run on the reviewed main SHA, enabled repository variable and checked acknowledgement | Not dispatched; requires subsequent authorization |
| Public download audit | Anonymous retrieval of HTML/PDF/TeX/ZIP/manifest, identity and link checks | Only after authorized deployment |

The promotion PR stays Draft until the preparation PR is merged with approval.
Its head must be develop, never an alternative branch or a fabricated ancestry
status. The unrelated h215 policy and Gurobi14 PRs stay independent; their merge
is not a prerequisite to this MVP2 promotion.

## Build and output verification

`python -B scripts/build_author_review.py --check-assets` verifies all editorial
and dependency bytes without TeX, a solver or network access. The normal command
compiles the article and supplements in a temporary build directory, with shell
escape disabled. It requires the reviewed page counts, settled references and
the full original Appendix A page sequence. A fresh output directory is required;
existing publication artifacts are preserved.

The HTML pages embed the complete approved-edition PDFs and offer direct
downloads. This avoids presenting a different HTML manuscript. The portable ZIP
includes the same PDF bytes, the exact editorial TeX, bibliography, dependencies
and a complete member inventory. TeX and ZIP URL aliases remain compatible.
Local and Linux PDF file hashes may differ with the TeX engine environment;
editorial source and asset identities remain fixed and every rendered output
receives its own hash. The rebuilt pages still need final visual verification
before publication is reported as complete.

The existing pending `pages_approval.json` remains approved=false. A later
authorized manual run checks the exact main SHA, repository, workflow SHA,
actor and acknowledgement, and activates a run-scoped record. Merely merging a
PR does not deploy. The workflow has no push trigger. It retains contents-read
permissions for building and confines Pages write permission to deployment.

After approval of the main merge and publication, select **Publish reviewed
manuscript** in Actions, choose branch **main**, verify the exact main commit,
and acknowledge **publish_reviewed_snapshot**. The repository variable
`MANUSCRIPT_PAGES_ENABLED` must be `true`. Do not invoke the legacy draft-render
workflow for this edition. Record the actual run URL and output manifest.

The deployed files must include index.html/pdf/tex, supplementary-review.html/
pdf/tex, both editable ZIP aliases, the original Appendix A, run-scoped approval
and publication manifest. Check their anonymous downloaded hashes, all links,
the 19-page original appendix sequence, maps, tables and references. Publication
is not complete until those checks succeed.

No data deposit, Zenodo update, journal submission, HPC action, automatic retry
or new optimizer run is authorized or performed by these PRs.
