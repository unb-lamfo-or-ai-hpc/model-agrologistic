# Agrologistic MVP3.0 methodological plan - English EN, Rev3

Scientific reference: 23 November 2026. Approved staged-design revision:
24 November 2026. Prepared in Draft PR #166; no merge or HPC execution is authorised.

The GitHub source is `plan.tex` in this directory; the editable package uses
`main.tex`. Rev3 replaces the earlier experimental-design edition within
Draft PR #166. The earlier edition remains in Git history.

## Approved research design

Stage A evaluates P0 with beta/alpha disabled at K={1,1.25,1.5,2} in DET and STO:
8 cases. Stage B adds P1-P8 at K=1 in both modes: 16 cases. P0/K=1 is reused,
giving 24 distinct initial observations. Repetitions and larger-population cases
are selected after the initial h215 analysis. The balanced 72-observation example
is an optional budget calculation only. The fixed initial ceiling is 192 native
hours and 288 allocation hours at 192 GiB, excluding queue and qualification.

Native Gurobi 14, Method=-1, Threads=0, W topology, the scalar objective and the
approved beta/alpha/K controls are retained. The plan examines validated empirical
economic-cost/domestic-service frontiers separately for DET/STO. It contains no
Benders or thread-speedup study. The abstract, research question/objectives,
original displayed model expressions and bibliography remain unchanged.

## Contents and reproduction

- `main.tex`: complete editable LaTeX source. Figures use native LaTeX drawing;
  the bibliography is embedded in the source, so no external graphics/BibTeX
  file is required.
- The revised PDF is included at the package root.
- `appendices/`: the two unchanged v2 XLSX inspection workbooks.
- `workbook-versions.json`: workbook identities and edition/schema distinction.
- `review/`: current QA, approved design, solver-free tests and retained historical
  reviews. Earlier QA files describe their own editions, not Rev3 acceptance.
- `SHA256SUMS`: SHA-256 of every other package member.
- `build.py`: optional standard-library helper for document compilation only.

Using an existing TeX distribution with the packages declared in the preamble,
compile `main.tex` three times:

```text
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
```

Alternatively: `python build.py --pdflatex <path-to-existing-pdflatex>`.
No package installation, environment modification, solver or HPC job is involved.

## Data identity and limits

The active files are `agrologistic_effective_baseline_v2.xlsx` and
`agrologistic_warehouse_registry_v2.xlsx`. Their exact hashes are in
`workbook-versions.json` and `SHA256SUMS`. Workbook edition 2 retains the compatible
computational schema `agrologistic-effective-baseline-v1`. The effective workbook
supplies the normalised ModelData bundle; the registry is an inspection and
reconciliation reference rather than a second implicit override source.

These local review attachments are not a newly published dataset. Full source
and SQLite custody acceptance remains a separate gate in Draft PR #164.
The source, protocols and checks are documented in GitHub; PDF/XLSX/ZIP review
attachments are delivered locally. Original workbooks, PDFs and scientific
results are preserved. Neither PR #164 nor PR #166 is merged by this revision.
