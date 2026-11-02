# Literature, claims and article reconciliation — 28 October 2026

## Decision and scope

This revision narrows the article's empirical contribution and improves its
argument while the two separately claimed solver attempts await original
terminal evidence. It adopts the useful recommendations of
HAI-LIT-AGRO-2026-01; that opinion is a research input, not independent execution
evidence or coauthor approval.

The received UTF-8 opinion has SHA-256
`2868e84f05b253521dd717b1d20141bba1bbc9e8c86003e3ae14dfca520a6b7c`.
Its reading baseline was c092fa7b, before PR136's appendix revision and PR137's
startup repair. The implementation baseline here is merged develop
fbbcee3dc9a4dfd6ade5d0d7b1a1d253744207c6. Recommendations have therefore
been reconciled against the current files rather than applied as replacement
instructions. The approved title, research question, SO1–SO4, author metadata,
model, original Appendix A and original evidence remain preserved.

## What changed in the argument

The abstract now starts with the computational and planning question.
The introduction acknowledges existing grain-network and stochastic planning
models before stating the narrower empirical question. A closest-precedent
table compares relevant decisions and methods without treating an inaccessible
full text as proof that a feature is absent.

C1 concerns observed dimensions, phase times, sampled memory and certified
quality. C2 concerns the returned agricultural decisions and the difference
between financial costs and artificial penalties. C3 remains a complementary,
human-supervised research account requested by the coauthors. It is not a new
optimization algorithm or a controlled productivity claim. The approved title's
word *scalability* is interpreted as observed behavior on the retained cases;
there is no fitted scaling law or universal computational frontier.

Results distinguish eleven accepted Gurobi observations, the original negative
SCIP four-hour observation, the original HiGHS startup failure and the two
pending eight-hour attempts. A dated status table makes those categories
explicit. More direct delivery can lower the scalar total while worsening
domestic service: the approved weighted objective permits that trade-off.
Artificial emergency slacks are not evidence of installed resilience.

The separate editable highlights now identify eleven observations and correctly
distinguish the declared 1% criterion from the attained h500 gap of 0.2074%.
The bibliography remains 36 retained records, 33 cited in the expanded main
article, plus two supplementary review-method records. No DOI, citation key,
historical Zotero membership receipt or raw certificate has been silently changed.

## Primary-source reconciliation

Access levels describe this reading, not the opinion author's access.
The [38-record disposition ledger](literature_disposition_20261028.json) preserves
the whole starting inventory. The matrix below records the claims actually
adopted. Records marked retained/not reread have not undergone a new full-text
audit in this pass.

| Claim or editorial decision | Evidence and locator | Access / consequence |
| --- | --- | --- |
| Grain-storage network optimization is established work | Essien et al. (2018), model framework and case; Gholamian and Taghanzadeh (2017), abstract/highlights | Essien institutional full text; Gholamian publisher preview. Cite specific decision settings; do not claim a first grain-location MILP. |
| Resilience and sustainability are existing research concerns | Hosseini-Motlagh et al. (2020), abstract and publisher section previews | Preview only. Do not describe our algebraic emergency capacities as a resilience policy or an environmental outcome. |
| Stochastic agricultural planning predates this implementation | Reis et al. (2023), Sections 3.1–3.2 and conclusions | Publisher full-text sections inspected. Distinguish tactical fixed-recourse LP from investment MILP; do not import its information-value calculations. |
| Agricultural optimization already has decomposition/distributed solution research | Shastri et al. (2011), institutional abstract and publisher record | Abstract/metadata. Our extensive-form observations are not a new decomposition method or a cross-paper speedup comparison. |
| Distributed simulation and data assembly are different workloads | Knapen et al. (2025), institutional abstract; Zhao et al. (2012), publisher abstract | Abstract/metadata only. Their work cannot establish our native solver-thread performance. |
| Rosa is a prior mathematical foundation, including SiloDSS investment decisions | Rosa (2026), public UnB defence abstract; existing attribution | Official abstract, not the complete 206-page document. Opening, expansion, bulk conversion and stochastic planning cannot be claimed as newly introduced here. Numerical overlap requires chapter/table comparison by the authors. |
| The current gap is a bounded empirical assessment | Closest-precedent table plus the retained-source limits above | This supports the chosen question, not proof of global novelty. Further search can narrow or revise it. |
| h500 attained the declared scalar quality target | manuscript/scalar_evidence.json, h500 record and docs/evidence/scalar_h500_2220382_review.json, arms[0] | Original package audit/certificate replay, not a fresh solve. Report 0.207432% attained gap versus 1% criterion. |
| Model scale and resource quantities have distinct meanings | Same h500 review, matrix, timings and resource_observations | Separate native runtime, construction, end-to-end time and sampled application RSS. Do not substitute reserved memory, native sampling or Slurm batch RSS. |
| Artificial penalties dominate the h500 total | Same h500 record, reconstructed_costs and physical_diagnostics | Report the 94.074% share and incomplete service. Do not interpret the penalized objective as a calibrated financial loss. |
| D plans have lower penalized cost and worse service | manuscript/wd_results.qmd and its original evidence bindings | Retain objective/bound certificates and the observed mechanism. Single observations do not establish statistical superiority. |
| A lowest observed thread runtime is not causal speedup | manuscript/scalar_results.qmd, h300 thread block | Unreplicated observations; no universal thread recommendation or production-isolation certificate. |
| Original SCIP reached its four-hour limit without an incumbent | docs/evidence/scalar_scip_h215_w_2225638_review.json | Audited negative observation. No objective, gap, service or impossibility inference is invented. |
| Original HiGHS failed operationally, while the two extensions are pending | Original startup audit; evidence/parallel_solvers_20261028_running_v2.json | Preserve job2226407/archive2816e35c separately from running jobs2226388/2226536. Scheduler RUNNING is not native optimization evidence. |
| Human–AI provenance is complementary | Main methodology account, Appendix B and retained decisions | Observable artifacts support accountability; hidden reasoning, reviewer independence and productivity gains are not measured. |
| CEA fit depends on a defensible contribution | Official Guide, introduction/article types | Topic fit is plausible; use of a commercial solver, Pyomo or HPC alone does not establish the journal's required innovation. No acceptance prediction. |

Primary source links:

- [Essien institutional full text](https://ugspace.ug.edu.gh/server/api/core/bitstreams/ba3cff00-501e-4c12-aba8-011fe3e7ccb0/content)
- [Gholamian publisher record](https://www.sciencedirect.com/science/article/pii/S016816991630919X)
- [Hosseini-Motlagh publisher record](https://www.sciencedirect.com/science/article/pii/S0168169919315479)
- [Reis publisher full text](https://www.mdpi.com/2305-6290/7/3/49)
- [Shastri institutional record](https://experts.illinois.edu/en/publications/a-novel-decomposition-and-distributed-computing-approach-for-the-/)
- [Knapen institutional record](https://research.wur.nl/en/publications/efficient-and-scalable-crop-growth-simulations-using-standard-big/)
- [Zhao publisher record](https://www.sciencedirect.com/science/article/abs/pii/S0168169912002086)
- [Rosa review, publisher](https://www.scielo.br/j/gp/a/nMTHjGgtDSpBjRX8Jf7bzjC/)
- [Rosa public defence abstract, UnB](https://sigaa.unb.br/sigaa/public/programa/noticias_desc.jsf?id=853&lc=pt_BR&noticia=23891799)

The SIGAA page was consulted solely as the already cited public institutional
source for Rosa's title and abstract. No authentication or restricted academic
records were involved. Its abstract does not resolve manuscript/table overlap.

## New candidate and unresolved comparisons

Gao et al., *Distributionally robust agricultural product origin warehouses
location-allocation problem under decision-dependent demand uncertainty*,
Journal of Cleaner Production 544 (2026), 147664,
[DOI 10.1016/j.jclepro.2026.147664](https://doi.org/10.1016/j.jclepro.2026.147664),
is a relevant candidate identified by the opinion and confirmed through publisher
metadata/highlights. Those describe a distributionally robust decision-dependent
uncertainty setting and a MILP reformulation. Full-text examination is still
needed to compare decisions, assumptions, computational design and results.
It is recorded separately from the 38 retained records and is not automatically
inserted into references.bib or the historical selection ledger.

The authors should compare Rosa's Chapter 5 with the current formulation and
each reused or newly computed table. Separate mathematical inheritance, historical
data, implementation changes and genuinely new experiments. A publication year
or a defence abstract cannot establish incremental novelty. The 2025 review's
publication/search chronology also needs reconciliation before reproducing its
search dates; the immutable supplied Appendix A is not retrospectively rewritten.

## Current journal requirements

The official [CEA Guide for Authors](https://www.sciencedirect.com/journal/computers-and-electronics-in-agriculture/publish/guide-for-authors)
was read in the Codex browser on 28 October 2026. Its accessible contents
supersede the opinion's unsuccessful HTTP retrieval, without implying that the
opinion verified those requirements.

The Guide requires an abstract of at most 250 words, 1–7 keywords, and a separate
editable highlights file with 3–5 points of at most 85 characters each. It
requests editable source, author declarations, CRediT contributions, funding and
conflict information, and data availability. A graphical abstract is encouraged.
Tables must remain editable. The AI-use declaration and Acknowledgements precede
References. The stated application-note page limit is not a research-article
limit; no general research-article page cap or mandatory CAS class was identified
in the read Guide. The community Quarto Elsevier extension is not publisher
endorsement. Final compliance, reuse rights and all-author approval remain open.

## Coauthor action sheet and completion boundary

| Priority | Action | Exit evidence |
| --- | --- | --- |
| 1 | Confirm the bounded C1/C2 positioning and complementary C3 | Coauthor decision on claims and target-journal fit; preserve approved title/RQ/objectives unless explicitly revised |
| 1 | Resolve Rosa/SiloDSS numerical and methodological overlap | Full chapter/table crosswalk with source locators; explicit incremental contribution |
| 1 | Receive and audit both terminal solver packages | Original archives/checksums/source/plan and residual or negative/partial outcomes; preserve all claims and the original failed HiGHS package |
| 2 | Read inaccessible closest precedents and Gao candidate in full | Page/section-supported comparison; justified citation additions or restrictions, not absence-by-abstract |
| 2 | Reconcile the review chronology and retained uncited records | Document keep/cite/remove decisions; do not relabel a focused update as a new systematic review |
| 2 | Review the revised article and remaining repetition | Coherent agricultural interpretation and consistent figures/captions/units; no operational receipt prose in the main argument |
| 3 | Complete the author and submission package | Human CRediT/funding/conflict/rights/AI statements, editable sources, all-author approval and separate final integration/publication decisions |

This PR is a reviewable reconciliation, not completion of all 38 full-text
assessments, a new systematic search, S6-B closure, Pages deployment or journal
submission. Original terminal evidence can add a numerical result or a bounded
negative/operational outcome; it need not be successful to support honest reporting.
