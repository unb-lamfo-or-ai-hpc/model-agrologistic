# Computational positioning and thesis attribution

Review date: 13 September 2026. This is an editorial provenance record, not
an experimental result or a claim of journal acceptance.

## Research position

The intended audience is agricultural computing, with *Computers and
Electronics in Agriculture* as a candidate venue. The maintainer-supplied
aims-and-scope text emphasizes investigator-developed computing contributions;
the publisher scope page was not retrievable during this review (HTTP 403).
Scope guidance is not cited as scientific evidence in the manuscript.

The manuscript now prioritizes computational model growth, auditable network
preparation, dimensional contracts, independent validation, stage-level solution
quality and resource reporting. Agricultural investment remains the application,
not a substitute for a computing contribution. Gurobi and OSRM remain credited
external components. No new distributed MILP algorithm, measured parallel speedup,
PaScal integration or completed scalability frontier is claimed.

Nine of ten selected reference executions were accepted at the evidence cutoff.
The final warehouse-only nine-scenario retry remains unresolved. Road matrices
for 500 warehouses do not establish optimization performance at that size.
Matched component ablations and repeated thread-scaling experiments are still
needed to isolate performance benefits. Repositioning the text does not supply
those missing results or guarantee suitability for the intended journal.

## Intellectual provenance

The grain-storage mathematical and decision-support foundation is attributed to
Artur Guerra Rosa's doctoral thesis. It is distinct from the published 2025
literature review. The manuscript cites both and explicitly identifies changed
road data, separate slacks and service-first objectives as qualifications of the
present extension.

APA-form thesis reference:

Rosa, A. G. (2026). *Modelagem matemática e sistemas de apoio à decisão para a
logística de alocação e armazenagem de grãos no Brasil* [Tese de doutorado,
Universidade de Brasília].

Program: Programa de Pós-graduação em Agronegócios, Faculdade de Agronomia e
Medicina Veterinária (FAV), Universidade de Brasília. The original Portuguese
title and institutional names are preserved as bibliographic metadata.

The author team supplied the thesis description. The [official doctoral defence
announcement](https://sigaa.unb.br/sigaa/public/programa/noticias_desc.jsf?id=853&lc=pt_BR&noticia=23891799)
corroborates author, title and year. This URL is a metadata provenance source,
not a deposited thesis download; no DOI or repository handle was invented.
The SBC template controls the rendered author-year bibliography style; this
audit gives the requested APA-form reference independently of that house style.

## Focused reference review

This is a targeted literature update, not a newly executed systematic review.
Claims drawn from abstracts remain limited to their stated scope; no unavailable
algorithm details or numerical speedups were inferred.

| Citation key | Primary verification | Use and boundary |
|:--|:--|:--|
| `shastri2011` | [Publisher](https://doi.org/10.1016/j.compag.2011.01.006); [Illinois](https://experts.illinois.edu/en/publications/a-novel-decomposition-and-distributed-computing-approach-for-the-/) | Agricultural optimization decomposition precedent, not an implemented baseline |
| `knapen2025` | [Publisher](https://doi.org/10.1016/j.compag.2025.110392); [Wageningen](https://research.wur.nl/en/publications/efficient-and-scalable-crop-growth-simulations-using-standard-big/) | Distributed crop simulation distinguished from coupled stochastic MILP |
| `zhao2012` | [Publisher](https://doi.org/10.1016/j.compag.2012.08.007) | Spatial data assembly separated from optimization |
| `silva2025pascal` | [DOI](https://doi.org/10.1109/ACCESS.2025.3639388); [UFRN author page](https://www.dca.ufrn.br/~samuel/index.php) | Profiling motivation; PaScal is not integrated |
| `huangfu2018` | [Publisher](https://doi.org/10.1007/s12532-017-0130-5) | Parallel LP context; no inference about Gurobi internals |

## Zotero reconciliation

Collection: **Model Agrologistic — Manuscript v0.2**, key `Q9G99YM3`.
All 35 cited records were read back through the local API. Four existing items
were added without replacing metadata or other memberships. The thesis
(`YKWSRZB7`) and Zhao article (`F98ZMAA6`) were created only after exact
title/DOI searches. `citation_selection.json` maps every manuscript key to the
verified item. Private attachments and library notes are not exported.
