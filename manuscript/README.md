# Scientific manuscript — integrated scalar revision

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

## Evidence boundary

The active Results section uses eight accepted scalar observations: h215
DET/STO, five h300 thread levels and h400 STO. Original source/job/input hashes,
penalties and residual tolerances remain frozen. `scalar_evidence.json` and its
generated `scalar_results.qmd` retain original certificate identities; later
replay/post-processing is not fresh private-input residual revalidation.
h500 job2220382 is pending in the last supplied snapshot, not a numerical result.
No causal thread speedup, full service, exact zero-gap proof or financial
interpretation of artificial penalties is claimed.

The old thirteen-attempt comparison, ten-reference results, failed capacity-pass
trial, original certificates and their figures remain unchanged historical
cohorts. `comparison_results.qmd`, `historical_reference_results.md`,
`comparison_provenance.json`, `results_snapshot.json` and
`evidence_status.json` must not be pooled with or relabelled as scalar evidence.
SCIP/h215 remains a separate decision; S3/S4 and EVPI/VSS remain excluded.

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
