# Scientific manuscript — integrated scalar revision

27 October current revision: S5 closed by authorized PR130 merge
`b031c3d1014df433020a6bb98534b9b9d8de4ffb`. The original h500 job2220382
is now in all numerical tables: nine W scaling observations plus two D h215
observations, eleven scalar observations rather than replications. The stale
pending statements below are dated history. The researcher authorizes this
h500/W-D editorial reconciliation and one prospective SCIP STO h215 W test.
The original SCIP scalar h215 observation is now audited: timelimit and zero
solutions, recorded separately in scip_results.qmd/open_source_comparison_status.json.
A longer SCIP window and multisolver Pyomo/HiGHS qualification are planned;
no new execution follows from this checkpoint. See docs/mvp2_completion_plan_20261028.md.
The h500 geographic snapshot remains input-only. No deployment, new deposit,
journal submission or final author acceptance is implied. The existing Pages
approval receipt belongs to the previous snapshot and is not rewritten here.

23October current authority: PR120 is merged; the researcher explicitly requests
the current S6-A as a public coauthor REVIEW snapshot after normal develop/main
reconciliation. This supersedes the older draft/publication holds below, not
final approval or journal submission. The separate h215 W/D Results section
adds two accepted D observations, keeps the original eight W scaling observations
unchanged and reports lower penalized cost BUT worse service. S5/h500 terminal
evidence, further coauthor rounds and S6-B remain open. Check pages_approval.json
and the actual deployment receipt; CI/merge alone is not publication.

The approved article is **Computational Scalability of Deterministic and
Two-Stage Stochastic MILP Models for Grain-Storage Network Design and Hub
Location**. PR120 implements the researcher's final21October mandate on the
existing editorial branch. It does not authorize merge, deployment or submission.

The22October extension adds Appendix C (actual Python/Gurobi/SCIP crosswalk,
shared reviewable GAMS translation and effective-input exporter) and Appendix D
(source cells, units, transformation rules, source hashes and actual population
nesting/order). GAMS compilation and numerical parity are explicitly unperformed;
the tool is unavailable. The AI declaration, supplied NPAD Acknowledgements and
References are consecutive numbered sections. No scientific code, model, penalty,
certificate or live HPC claim is changed. PR120 remains draft during review.

## Current evidence boundary

The active Results section uses nine accepted W scalar observations: h215
DET/STO, five h300 thread levels, h400 STO and h500 STO, plus the separate D pair. Original source/job/input hashes,
penalties and residual tolerances remain frozen. `scalar_evidence.json` and its
generated `scalar_results.qmd` retain original certificate identities; later
replay/post-processing is not fresh private-input residual revalidation.
Original h500 job2220382 passed the S5 archive/source/certificate audit.
No causal thread speedup, full service, exact zero-gap proof or financial
interpretation of artificial penalties is claimed.

The old thirteen-attempt comparison, ten-reference results, failed capacity-pass
trial, original certificates and their figures remain unchanged historical
cohorts. `comparison_results.qmd`, `historical_reference_results.md`,
`comparison_provenance.json`, `results_snapshot.json` and
`evidence_status.json` must not be pooled with or relabelled as scalar evidence.
The original scalar SCIP/h215 W negative observation is complete. A distinct
longer-window operational PR and separate multisolver implementation/qualification
are requested; their new jobs require qualified merge and pinned human CLI. S3/S4 and EVPI/VSS remain excluded.

## Reproduce the document

Use a clean checkout, Python3.13 with the declared geographic/document
dependencies, Quarto1.10.18, TinyTeX with pdfpages and the existing declared
template packages, and rsvg-convert for the shared workflow SVG:

```bash
python scripts/build_manuscript_comparison.py --check
python -m scripts.build_scalar_manuscript --check
python -m scripts.build_s6a_assets
python scripts/check_manuscript.py
quarto render manuscript
quarto render manuscript/supplement
python scripts/assemble_manuscript_outputs.py
python scripts/check_manuscript.py --rendered
python scripts/package_manuscript.py --output manuscript/_manuscript/coauthor-latex.zip
```

No solver, licence, NPAD connection, map tiles, OSRM request or browser is used
by the build. The existing manuscript CI installs declared dependencies and
renders the article and supplement. Source and generated-asset hashes are
recorded in `figures/s6a_assets.json`; scientific map definitions and full
source identities are in `maps/` and `geographic_sources.json`.
Use fresh outputs when changing render code; scientific map export preserves
prior outputs rather than silently overwriting receipts.

Outputs are `_manuscript/index.html`, `index.pdf`,
`supplementary-review.html`, `supplementary-review.pdf` and the original
`appendix_a_original.pdf`. The flat coauthor ZIP contains editable LaTeX,
bibliographies, figures, notices and checksums. Use a new ZIP filename for each
review; the packager preserves earlier archives.

## Geographic preparation

See [the full local/headless guide](../docs/s6a_20261021/geographic_reproducibility.md).
An explicit preparation step reads original frozen XLSX/accepted archives and
writes a separate geographic SQLite. Dash and headless PNG/PDF/SVG open it
read-only and share scientific figure definitions, styles and filters.
Original coordinates and coincident node roles are retained. The supplied
distance matrices lack road polylines; no straight connections are invented.
h500 shows input availability, never inferred optimized decisions.

## Models, literature and Human–AI account

`formulation.qmd` presents full scalar DET/STO objectives, constraints, domains,
units and interpretation. The code crosswalk and C01–C22 response are in
[the integrated review record](../docs/s6a_20261021/integrated_revision_crosswalk.md).
Rosa's mathematical foundation is credited. The historical Benders audit is
retained as unimplemented historical material, not an active method.

Appendix A incorporates all19 pages of the supplied review byte-for-byte,
SHA256859dc52b64b6bcf471f7616182d8cadf2b693dbfd19ad4b9248637b5c231b3ed.
Original search arithmetic and date issues are documented, not silently
corrected. Appendix B contains ten Human–AI sections; the main article has a
bounded methodological passage, concise activity table and the same editable
workflow figure. Retrospective AI accounts are not independent execution logs.

The retained bibliography/citation-selection provenance is unchanged; only
actually cited records are required in the rendered reference list. Public
bibliographic identifiers, not private library notes, are published. Seven
authors' approved metadata remains in `authors.json`, without new CRediT or
individual-reviewer responsibility assignments.

## Rights, publication and final review

The pinned Elsevier extension0.4.5, vendored files and their checksum/rights
notices are preserved. Original project code is MIT; external data and
OpenStreetMap-derived databases retain their applicable terms. The published
Zenodo0.2.0 receipt does not assert that all later scalar archives are deposited.

The old hash-bound Pages approval must reject this revised source. Merge into
develop does not deploy the draft or authorize journal/arXiv submission. Coauthor
review, declarations, rights and final submission authorization remain necessary.
The original146 annotation locators are unchanged; the17 unexplained marks and
historical source/build reconciliation are administratively closed as directed,
not newly verified or interpreted. Final main/develop integration follows
article review, not this editorial preparation.
