# Computers and Electronics in Agriculture: editorial compliance

Assessed against the current [Guide for Authors](https://www.sciencedirect.com/journal/computers-and-electronics-in-agriculture/publish/guide-for-authors)
on 2 October 2026. A document build is not scientific acceptance or permission
to submit.

## Scope and contribution

CEA covers post-harvest storage and logistics, but emphasizes innovation in
agricultural computing. Application of an off-the-shelf solver alone is not an
adequate novelty claim. The article identifies its investigator-developed
formulation, connectivity-aware road-data workflow, objective-pass instrumentation
and independent validation. Its research question concerns construction and
quality certification under an explicit resource budget. Novelty is not claimed
solely from problem size, NPAD use or adoption of Gurobi/SCIP.

Knapen et al. (2025) motivates scalable agricultural computing; Essien et al.
(2018) motivates stakeholder-sensitive grain-storage decision support; Hosseini-
Motlagh et al. (2020) motivates uncertainty-aware network design. These studies
are contextual precedents, not quantitative validation of this implementation.

## Template and submission files

Elsevier accepts editable LaTeX sources. Its [LaTeX instructions](https://www.elsevier.com/en-gb/researcher/author/policies-and-guidelines/latex-instructions)
identify `elsarticle` as a publisher class; CAS is another available family,
while camera-ready CRC templates are editor-directed. This project adopts
single-column `elsarticle` preprint formatting, author-year citations,
11-point type and A4 paper through a pinned community Quarto integration.
Historical SBC assets are retained for reproducibility, not as the active
submission template.

The current guide does not establish a universal 20-page research-article
maximum. That target is a project preference, not a verified journal restriction.
Editable source is required; PDF alone is insufficient. The package generator
places assets at one level for Editorial Manager. Main and Appendix A remain
separate editable documents.

| Requirement | Revision status |
|:--|:--|
| Abstract, at most 250 words | Checked automatically |
| One to seven English keywords | Five supplied |
| Separate highlights, three to five bullets, each at most 85 characters | Five supplied and checked |
| Authors, affiliations and corresponding contact | Seven authors/ORCIDs retained; full postal addresses need confirmation |
| Editable equations and tables | Native LaTeX, not screenshots |
| In-text references to figures/tables | Added before relevant items |
| Vector line-art figures, with embedded fonts | PDFs accompany browser-compatible PNG previews |
| Descriptive supplementary material | Appendix A has Quarto/TeX, HTML and PDF |
| Author-year citations and reference list | Rendered bibliography checked; source metadata retained |
| AI-assistance declaration before References | Retained with human responsibility statement |
| CRediT contributions | Requires agreement; roles not inferred |
| Funding and sponsor involvement | Requires factual author confirmation |
| Competing-interest declaration | Requires confirmation; absence not assumed |
| Data availability and repository links | Draft status stated; licensed release and DOI citation pending |
| All-author approval | Pending; no submission authorized by this checklist |

A graphical abstract is encouraged, not mandatory. If supplied, it must satisfy
readability and size requirements (at least 531 by 1328 pixels, height by width,
or equivalent proportions). The pipeline figure is not automatically a compliant
graphical abstract. No generated image substitutes for primary experimental data.

## Data deposition and Zenodo release

The journal's Option C policy and Elsevier's [research-data guidance](https://www.elsevier.com/researcher/author/tools-and-resources/research-data/data-guidelines)
require deposition and citation/linking of relevant data, or an explanation
when sharing is not possible. They do not prescribe Zenodo exclusively.
Zenodo is the chosen repository; record 22751909 is an unpublished draft.
Its upload URL is not a released dataset citation.

Before release: reconcile source-workbook rights; prepare canonical inputs and
population manifests; include principal case/stage summaries, independent
validation records, routing audits and README/data dictionary; retain unsuccessful
attempts with explicit outcomes; add checksums and code version; exclude
credentials, environments, caches, duplicates and private library files.
ODbL-derived road data and source workbooks need appropriate license separation,
not a blanket MIT assignment. Publish an immutable version, verify public access,
then insert its DOI citation and persistent link in the article. Version subsequent
corrections. Do not fabricate missing solution vectors or alter historical evidence.

## Preprint recommendation

For arXiv, the proposed primary category is **cs.CE (Computational Engineering,
Finance, and Science)**, with **math.OC (Optimization and Control)** as a possible
cross-list. The [arXiv taxonomy](https://arxiv.org/category_taxonomy) supports this
computational application and optimization focus. cs.DC is less appropriate
without an evaluated distributed algorithm; cluster use alone does not establish
distributed-computing novelty. Classification is subject to arXiv moderation.

Elsevier permits preprints under its sharing policies, but this does not authorize
upload on the authors' behalf. Obtain coauthor approval, reconcile Appendix A,
finalize data availability and remove unresolved editorial statements before
posting. Link the dataset DOI and code version. Preprint availability does not
replace peer review or journal acceptance.
