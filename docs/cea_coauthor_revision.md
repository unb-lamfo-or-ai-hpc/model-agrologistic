# Coauthor revision and source reconciliation

This revision uses the annotated 33-page manuscript and the 19-page review
supplement. Page references below refer to those sources, not the reorganized
article. Private marked PDFs and annotation exports are not redistributed.

| Comment group / original pages | Editorial response |
|:--|:--|
| Affiliation and front matter, 1 | Corrected Litoral, retained authors/ORCIDs, used Elsevier front matter |
| Thesis foundation versus new work, 1–2 and 7 | Credited Rosa and stated revised formulation, tools and bounded assessment without blanket claims that the model is not new |
| Research question and scale, 1–2 and 7 | Focused on construction, memory, quality and independent validation |
| Agricultural and stakeholder interpretation, 3–6 | Retained related work; clarified numerical slack versus physical resilience, governance and environmental indicators |
| Tables and section structure, 4 and 8–10 | Added preceding mentions; integrated notation/model into Materials and methods |
| Full deterministic formulation, 10–14 | Objective first, explicit investment and four transport costs, handling/storage costs, indexed constraints and domains, then interpretation |
| Bulk handling and dimensions, 9–10 | Distinguished static stock, daily throughput and period-level overflow |
| Closed candidates and Big-M, 13 | Kept native indicators; an equivalent Big-M requires a derived bound, not an invented constant |
| Aggregate balance cancellation, 14 | Removed aggregate equation from principal formulation; retained independently checked indexed balances |
| Two-stage structure, 14 | Common investment, scenario recourse and full-trajectory information assumption made explicit |
| OSRM and data versus optimization, 16 | Explained fastest-route distances; separated materialization at 500 from optimization through 400 |
| Numerical precision, 17 | Two displayed decimal places; exact machine-readable records retained |
| Presolve removes integers, 27 | Qualified as service-pass specific, not proof that the entire hierarchy is an LP |
| Excessive future decomposition algebra, 28 | Replaced unimplemented Benders derivation with concise plan and validity requirements |

Proofreading suggestions were incorporated into the substantive rewrite rather
than accepted mechanically. Ambiguous comments were reconciled with implementation
and evidence. Neither an arbitrary activation Big-M nor a single aggregate
certificate replaces the mathematical contract. Remaining authorship, review
chronology and data-release decisions require factual confirmation.

## Systematic review: factual reconciliation

1. Search date `04-10-2026`: a day-month reading is future-dated on 2 October.
   April 10 is possible under month-day ordering but cannot be assumed. Confirm ISO date.
2. Database counts balance: 478 identified − 59 duplicates = 419 screened;
   404 exclusions leaves 15 sought; one unretrieved leaves 14 assessed;
   eight excluded leaves six included.
3. Alternative-source counts do not balance: 20 identified, two duplicates,
   but 19 sought. Subsequent values are one unretrieved, 18 assessed,
   15 excluded and three included. Item-level records must identify the correction.
4. The source diagram caption mentions preparation in 2025, whereas its search
   date is labeled 2026. Confirm version chronology.
5. Foulds is labeled single-period in the classification, but the published
   title describes dynamic models. The appendix records this discrepancy.

The appendix retains reported counts and identifies the unresolved transition;
it does not invent screening records or draw an inconsistent PRISMA diagram.
All nine studies are retained in structural comparison, with contextual
literature and two methods references. Database exports, item-level screening
and quality-assessment records are unavailable locally. Independent reproduction
of study selection is not claimed. Resolve the records before submission rather
than adjusting counts solely to make a diagram balance.

## Input identities

- Annotated manuscript SHA256:
  `9fddd98a202dc28dd511b83d9e8c85f920d9db721ba608dcc3355bdc0449c774`.
- Review supplement SHA256:
  `bd7be439950f8560c209eb5df36449026c9db71b70cdcc5126bc3fcdb013b8b6`.
- Experimental basis: unchanged `docs/evidence/sprint_c_final_20260920/`,
  thirteen attempts, not new optimization or predictive validation.

Scientific presentation is revised without changing certificates, adding missing
solutions, claiming a released Zenodo dataset or certifying submission readiness.
