# Agrologistic MVP3.0 methodological plan - English EN, Rev4

Scientific design approved on 24 November 2026; Rev4 editorial review prepared
on the same date for researcher approval. PRs #164 and #166 remain Draft.

The GitHub source is `plan.tex`; the delivered editable package uses `main.tex`.
Use `python audit_display_context.py plan.tex` to repeat the source-context audit
in this directory. Earlier editions and their QA remain historical evidence.

## Experimental order

1. Table 6: Stage A, h215 only, K={1,1.25,1.5,2}, beta/alpha disabled,
   DET and STO: 8 cases.
2. Table 7: Stage B, h215 only, K=1, profiles P1-P8, DET and STO: 16 additional
   cases. P0/K=1 is reused from A, giving 24 distinct initial observations.
3. Table 8: conditional h300, h400 and h500 cases, selected from validated
   nondominated h215 configurations separately for DET/STO. Counts and
   repetitions remain conditional; no new factorial crossing is prescribed.

Every table and figure has an adjacent paragraph introducing its contents and
one or more paragraphs interpreting it. The 24-display audit is in `review/`.
The initial resource ceiling remains 192 native hours and 288 allocation hours
at 192 GiB, excluding queue and qualification. The 72-observation example is only
an optional repetition budget. Native Gurobi 14 automatic settings, W topology,
the scalar objective and beta/alpha/K semantics are retained. No Benders,
GPU or thread-speedup experiment is introduced.

## Editable project and verification

`main.tex` is the complete editable source, including native LaTeX figures and
the embedded bibliography. `appendices/` contains the two unchanged v2 workbooks.
`workbook-versions.json` distinguishes workbook edition 2 from the compatible v1
computational schema. The registry is an inspection/reconciliation reference,
not a second implicit source of parameter overrides. Full source/SQLite custody
acceptance remains a separate gate in Draft PR #164.

The revised PDF is at the package root. `review/` contains current QA/context
audits and earlier editions/reviews for provenance. Earlier QA files refer to
their own versions. `SHA256SUMS` covers every other archive member.

Using an existing TeX installation, compile `main.tex` three times with:

```text
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
```

Alternatively use `python build.py --pdflatex <existing-executable>`.
The standard-library-only `review/audit_display_context.py main.tex` checks
display references and adjacent prose. Human review remains necessary to assess
the quality of the explanations. The PDF and workbooks are local review
deliverables, not a newly published dataset. No solver, job, installation,
shared-environment change or merge is part of this revision.
