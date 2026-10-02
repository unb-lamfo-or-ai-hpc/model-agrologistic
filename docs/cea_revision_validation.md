# Editorial build validation, 2 October 2026

Scope: manuscript presentation, Appendix A, rendering and packaging. No solver
implementation, experiment result or historical certificate was changed.

## Checks completed

- Ruff repository check: passed.
- Six relevant manuscript/comparison test modules: 53 tests passed.
- Main-source, rendered-reference and supplementary-reference checks: passed.
- Frozen comparison/provenance check: passed; no changed files under `docs/evidence/`.
- Quarto 1.10.18 HTML and PDF builds: both projects completed.
- Main PDF: 25 A4 pages, including references; Appendix A: nine A4 pages.
- Visual inspection of all pages, with enlarged inspection of revised figures:
  no clipping, overlapping text or unresolved reference markers observed.
- PDF uses editable equations/tables and three vector illustrations. HTML
  uses PNG previews and links to the assembled supplementary documents.
- Flat coauthor ZIP extracted into a separate directory: main source compiled
  with pdfLaTeX/BibTeX and appendix source compiled with pdfLaTeX, using the
  existing local TeX distribution. No solver or NPAD execution was required.

## Delivered artifact identities

| Artifact | SHA256 |
|:--|:--|
| `Agrologistic_CEA_Revised_20261002.pdf` | `f44c708e2816a39dd66ff1a6cb7aa2f62075e7b2432e74fb21d4e9146c335061` |
| `Supplementary_Systematic_Review_20261002.pdf` | `3e03693dc108d12864b313a7835e144929d5425eb22fafea7551e056df42c71f` |
| `Agrologistic_CEA_LaTeX_20261002.zip` | `5347f62b1fdaec08f36b6be7bc6154a8b06852e0ca9c93b3cd4c9500eb1a81ae` |

These identify this local review export, not a bit-reproducible PDF guarantee:
TeX timestamps can change a future binary while the source remains unchanged.
GitHub Actions regenerates downloadable review artifacts from the branch.

## Release boundary

Editorial build acceptance does not resolve the review search chronology or
screening discrepancy. It does not certify new predictive results, a complete
solver frontier, published dataset, author roles, funding or conflict statements.
Coauthor approval, factual reconciliation and a licensed dataset deposit remain
required before submission. No merge, preprint upload or Pages deployment was
performed as part of this revision.
