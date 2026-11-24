# Agrologistic MVP3.0 methodological plan — English EN

Scientific reference: 23 November 2026. Authorized documentary revision:
24 November 2026. Workbook references and inventories are updated. The research
question, hypotheses, equations, policy/capacity design, bibliography and
analysis plan are preserved.

The source is `plan.tex` in GitHub and `main.tex` in the editable package.
The plan uses native Gurobi 14 DET/STO W models and approved beta, alpha and K
controls. It contains no Benders or thread-speedup study. It remains under
author review in Draft PR159.

## Active v2 workbook references

| File | SHA-256 |
|---|---|
| agrologistic_effective_baseline_v2.xlsx | 92698e05b869d67292cf7b080f56b43f7ccc93a27470b2eee559eadbeebd4a3d |
| agrologistic_warehouse_registry_v2.xlsx | 68b9933cc171541b151b7ea60c5d0501d5cecc01675819777af1ffefc11cbe7b |

Both declare `workbook_version=2`. Their presentation identifiers are
`agrologistic-workbook-view-v2` and `agrologistic-warehouse-view-v2`.
The computational identifier `agrologistic-effective-baseline-v1` is the
compatible CSV/ModelData schema, not an obsolete XLSX edition. Do not rename
this schema merely to match the workbook filename.

The qualified export used the effective-baseline v2 XLSX, identified by its
exact hash in the normalized bundle. The registry v2 supports inspection and
reconciliation; it is not a separate direct ModelData-loader input. The exporter
combines effective values with hash-identified frozen network support. This
documentary revision does not establish a global change of NPAD runtime defaults.

Appendix A now documents 20 baseline sheets, including Controls (9 rows),
InvestmentLimits (592), Identification (15), Dictionary (39) and Transformations
(8). Optional travel-duration fields are seconds and unused for freight.
Appendix B documents three registry sheets, 32 field definitions and 18,086
accepted facility rows. The worked parameter locators remain valid.

Workbook identities and unchanged production coefficients are recorded in
[the PR164 qualification](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/cfb99965c613105dfb3bdc9745e7599fe74ed183/docs/evidence/workbook_v2_qualification_20261124.json).
No data/calibration, scientific runtime implementation or experiment was changed.

## Historical provenance

Original v1 workbooks remain preserved, rather than renamed or overwritten:

| Historical file | SHA-256 |
|---|---|
| agrologistic_effective_baseline_v1.xlsx | d5babec48bb40a61843ccb4e7c9c059429b4d8ac32cefec945fda4e4fb84c917 |
| agrologistic_warehouse_registry_v1.xlsx | f39c2f29862aecb9a64fd0d37548eb788e402c805a5db6def6c5ec8a351d25bc |

The earlier PDF/package retain their identities in
[the 23 November checkpoint](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/2ff8ac46522518c2e804e24bc83e7fdb0152818d/docs/checkpoints/20261123_mvp3_methodological_revision.md).
The new package attaches only the active v2 workbooks. Their internal source
hashes identify upstream files. The package SHA256SUMS identifies delivered files.

## Build and review

Use an existing TeX distribution with the packages declared in the preamble:

```text
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error plan.tex
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error plan.tex
```

In the editable package use `main.tex`. Figures use native LaTeX drawing
primitives. The bibliography is embedded in the source. The package contains
the revised PDF/source, unchanged v2 XLSX attachments, a version manifest and
checksums. PDF/workbook attachments remain local review artifacts, not published
datasets.

The current render/identity record is `editorial-qa-v2.json`. The original
`editorial-qa.json` and 89 annotation dispositions remain the record of the
earlier review. Earlier dispositions and the recovered 80/20 graph method are
preserved. The new PDF is checked for references/citations, overfull boxes,
page-boundary problems and excluded study scope, then visually reviewed in full.

No new HPC job, optimizer invocation, shared-environment change or merge is
part of this revision. PR159 and PR164 remain Draft.
