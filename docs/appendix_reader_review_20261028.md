# Appendix reader and input review — 28 October 2026

## Assessment

The b60be06 appendices explained the model and provenance, but were not yet
a sufficiently practical reproduction guide for a non-specialist reader.
Several important file names were plain text, the data-acquisition route was
implicit, and numerical source/default/effective values were not gathered
clearly enough. The original Appendix A remains an immutable supplied source,
not a newly repaired systematic review.

## Corrections in the same PR138

| Reader's difficulty | Revision and evidence |
| --- | --- |
| Where to start | Supplement reading map: D inputs, C implementation/validation, B supervised decisions, A preserved literature background |
| Which code implements an equation | Pinned direct links to formulation, common input contract, native Gurobi/SCIP, Pyomo/bound proof and independent validator |
| How to make a first reproducible check | Public Excel-reader command; linked native/Pyomo qualification requirements; input-only GAMS export and explicit unperformed GAMS numerical parity |
| Which gold file was used | Registered de3bdc51 source and full workbook link distinguished from inspected 2fc994ac copy; equal CDA membership does not establish equal data |
| Which candidate source was used | Registered 0d19865a external source, dimensions and pool counts; GitHub manifest versus deposited workbook access distinguished |
| Which actual numbers enter the model | Source cells/cache states, four investment cost ranges/means, tariffs 45/48/50, all 27 freight coefficients, 30 days, 0.25 fallback fraction and effective 90k/45k/45k penalties |
| How additional candidates become investable options | Preserve215 anchors; zero base capacities, observed static-capacity upper bound, no new-candidate expansion/bulk eligibility; 85/185/285 added at h300/h400/h500 |
| How to identify an experimental input | Full processed-workbook and ordered-membership hashes, original versus intermediate ranking, OSRM versus sparse selected-network distinction |
| Whether an old availability flag is current | Pre-S5 h500 flag retained as history; original accepted h500 review is current. Original failed HiGHS and new running jobs remain separate. |
| Where to obtain review PDFs | Existing read-only cloud renderer plus pinned upload-artifact v7 standalone PDFs; original editable ZIP retained, no Pages deployment |

The new input guide is first recorded at
1b54023f4e0c0c27aba64883b1e9cf25817ad0f8 so the appendix can link to a stable
file that already exists. Its source inventory and original receipts remain
unchanged. The cloud audit reads the public canonical workbook directly,
compares original and cached values against the preserved 254-cell inventory,
checks population roles and 27 actual freight values, and checks that pinned
GitHub file paths exist. It does not read private registry/runtime bytes,
construct a solver model or certify a fresh large experiment.

## Bibliographic continuation

The Gao2026 publisher page was examined in a Codex tab: metadata, highlights,
abstract, introduction and section snippets are accessible, while complete
text requires organizational access or purchase. It describes endogenous
decision-dependent uncertainty and a distributionally robust MILP reformulation,
whereas this article's active design uses fixed Cartesian scenarios.
This sharpens the comparison question but does not establish a complete
mathematical/result comparison. No unmatched runtime claim or bibliographic
insertion is made; the candidate access record is updated.

## Qualification and remaining limits

This revision requires its own exact-head CI, public gold audit, article and
supplement render, editable package/checksums and visual inspection before
Ready. No approval from the previous head is carried forward. Source code
for the scientific model, inputs, penalties, tolerances, original packages
and supplied Appendix A bytes are preserved.

Complete numerical reproduction still requires lawful access to the exact
processed inputs, compatible solver/runtime, resources and fresh original-unit
validation. A source checksum, document build, test run and historical certificate
replay are distinct forms of evidence. Full source/text comparisons,
Rosa/SiloDSS overlap, coauthor decisions and final S6-B approval remain open.

After the researcher authorizes this PR's new head and it is merged, the
document workflow can be run on develop. Its branch/commit-bound standalone
article and appendix PDFs can then be opened in Codex. No pre-merge output is
labelled as develop, and no submission/public deployment is inferred.
