# Agrologistic MVP3.0 methodological plan — English EN

This is the 23 November 2026 editorial revision of the author-annotated plan. The source is `plan.tex` in GitHub and `main.tex` in the downloadable editable package.

The plan explains the native Gurobi 14 DET/STO W models, beta (domestic service), alpha (export ceiling), and K (a common multiplier of candidate and expansion capacity ceilings). It includes the proposed policy/capacity matrix, budgets, A1–A5 analysis, empirical economic–service frontier, S0–S5 schedule and six appendices. The 80/20 distance-based edge filter is explicitly distinguished from economic–service Pareto dominance.

## Editorial review and recovered network method

All 89 PDF review annotations have individual dispositions in [annotation-disposition.md](annotation-disposition.md). Subsequent author clarifications govern K and the alpha/beta notation. [network-recovery.md](network-recovery.md) documents the exact selection/repair procedure and the independent traversal of the frozen effective graphs. Aggregate replay results are in [network-audit.json](network-audit.json).

The grid and computational follow-ups are methodological proposals for review. This documentation update does not activate K or new experiments, change the model objective, alter the retained scientific implementation, or qualify a new campaign. The existing operational preparation in PR159 remains held under its own source and admission requirements.

## Build and review

Build with a TeX distribution containing the standard packages declared in the preamble:

```text
pdflatex -interaction=nonstopmode -halt-on-error plan.tex
pdflatex -interaction=nonstopmode -halt-on-error plan.tex
```

For the editable package, use `main.tex` instead. Figures use native LaTeX drawing primitives. The bibliography is embedded in the source, so no separate bibliography processor is required. The PDFs and private workbook attachments are distributed as local review artifacts, not published datasets.

The rendering record, source/PDF identities, annotation coverage and static checks are in [editorial-qa.json](editorial-qa.json). The source compiles without unresolved references, missing citations or overfull boxes. All final pages were rendered and visually inspected, including full-page checks of the K equations, the 80/20 rule and network tables.

## Attached reference workbooks

The private editable package retains the reviewed files unchanged:

| File | SHA-256 |
|---|---|
| agrologistic_effective_baseline_v1.xlsx | d5babec48bb40a61843ccb4e7c9c059429b4d8ac32cefec945fda4e4fb84c917 |
| agrologistic_warehouse_registry_v1.xlsx | f39c2f29862aecb9a64fd0d37548eb788e402c805a5db6def6c5ec8a351d25bc |

Appendices A and B describe their contents, parameter locators and interpretation. These are effective-reference workbooks under continuing scientific review. Future revisions retain provenance and explicit differences. Raw registry, flow and SQLite contents are not included in this GitHub documentation directory.

## Replaying the structural audit

```text
python audit_frozen_graph.py --support IDENTIFIED_PRIVATE_SUPPORT_DIRECTORY --output NEW_AUDIT_JSON
```

The standard-library script verifies the manifest and recomputes aggregate directed reachability. It refuses to overwrite the output, performs no optimization or database call, and makes no throughput or time-feasibility claim.
