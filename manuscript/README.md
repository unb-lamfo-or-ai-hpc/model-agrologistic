# Reading and reproducing the scientific manuscript

The article is **Computational Scalability of Deterministic and Two-Stage
Stochastic MILP Models for Grain-Storage Network Design and Hub Location**.
Its authoritative sources are [the article](index.qmd) and
[the supplementary material](supplement/index.qmd). The source currently under
review must be distinguished from the version published on GitHub Pages.

## Reading route

The article introduces the planning decisions, literature context, formulation,
experimental method and results. The appendices provide complementary detail:

| Appendix | Purpose | Source |
| --- | --- | --- |
| A | Original systematic literature review | [Preserved PDF](supplement/appendix_a_original.pdf) |
| B | Human-supervised AI assistance and verification | [Supplement, B1–B7](supplement/index.qmd) |
| C | Implementations, solver interfaces, parallelism and independent validation | [Appendix C](supplement/appendix_c.qmd) |
| D | Input sources, actual coefficients, units, facility selection and OSRM preparation | [Appendix D](supplement/appendix_d.qmd) |
| E | Individual investment maps, facility lists and flow-distance matrices | [Appendix E](supplement/appendix_e.qmd) |

Appendix A is the preserved researcher-supplied original. The
[source-reading ledger](../docs/literature_full_text_update_20261101.md)
distinguishes full-text passages, previews and metadata; unavailable text is
not evidence that a feature or prior contribution is absent.

## Data and reproducibility

Start with the [input reproduction guide](../docs/evidence/appendix_input_reproduction_20261028.json)
and [data distribution catalog](../data/manifests/research_data_distribution_v1.json).
The gold workbook provides the reference schema and values. The candidate
registry, exact runtime workbook, facility order, materialized road distances,
selected product-specific graph and scenario design have separate identities.
An equal filename or facility count does not establish the same experiment.

Use the [existing v0.2.0 dataset](https://doi.org/10.5281/zenodo.22751909)
and the catalog's exact archive members and hashes. New flow-distance companions
and selected-graph exports are identified in the
[next-release inventory](../data/manifests/zenodo_next_release_inventory_20261101.json).
Prepared local files are not additional public downloads. The
[release-readiness register](../data/manifests/zenodo_release_readiness_20261102.json)
keeps file identity, source attribution, access review and publication state
separate. Complete distance matrices, admissible arcs and positive solution
flows serve different purposes and cannot substitute for one another.

Appendix D explains tonnes per period, daily handling rates, operating days,
tonne-period stock exposure, currency coefficients and scenario aggregation.
Appendix E retains directed endpoint IDs and exact OSRM kilometres. Summing
flows over transport legs does not measure unique delivered tonnes.

## Computational evidence

The native Gurobi cohort and the common-Pyomo campaign are separate observations.
The current article includes the independently inspected first h300 one-thread
Gurobi/HiGHS pair. Later collection receipts are tracked separately until their
package inspection is complete. Every result binds inputs, settings, original
validation, attained gap, timing scopes and resource observations; a small MIP
gap alone does not establish full service or a unique investment plan.

The common formulation uses APPSI interfaces to Gurobi and HiGHS. Appendix C
distinguishes configured thread ceilings from measured resource use and explains
why equal seed values do not create equal solver trajectories. The ongoing
90-cell design has its own progressive qualification and immutable receipts.

## Document build and publication

Document rendering is separate from optimization: Quarto execution is disabled
and document assets are prepared offline from tracked definitions. See
[the article configuration](_quarto.yml),
[the supplement configuration](supplement/_quarto.yml) and
[asset preparation](../scripts/prepare_document_assets.py).
Rendering a document does not start a solver or an HPC job.

For the current development cycle, full-document PDFs and editable-package
regeneration are deferred. Technical checks and publication preparation can
proceed without claiming new rendered documents. Promotion to develop and the
separate main/Pages publication remain distinct reviewed steps. Final Pages
delivery includes article/supplement PDFs and editable TeX downloads after the
authorized publication build.

The [current documentation exit matrix](../docs/checkpoints/20261102_documentation_exit_matrix.md)
records completed checks and remaining source/data/publication work. Historical
editorial and execution notes remain in Git history and the repository's dated
checkpoints, outside this reader guide.
