# Primary-source comparison and gap tests — 30 October 2026

Author-facing B3 increment for PR144. This record narrows scientific claims;
it does not certify a complete systematic search or full-text access to all38
retained records. Original bibliography records, Appendix A and thesis
attribution remain unchanged. See the [access ledger](evidence/literature_gap_verification_20261030.json).

## Verified distinctions and unresolved fields

| Source / access | Positively established content | Consequence for this paper | Still required |
| --- | --- | --- | --- |
| Essien2018; institutional full text, Sections2.1.1–2.2 and Tables1–4 | Grain-storage location, transport, forecasting and weighted goal programming; integrated decision support | Storage location and integration are established precedents | Complete extraction of exact computational-quality/resource fields for the comparison table |
| Reis2023; publisher full text, targeted Sections3.1–3.2,4.2,6.1,7 | Tactical stochastic LP, contractual first-stage decisions, operational recourse; documented matrix size and algorithm comparison | Distinguish decision domains/investment and measurement scope; numerical size alone is insufficient for novelty | Remaining formulation/table extraction before calling this a complete full-paper reconciliation |
| Gholamian2017; publisher preview | Integrated wheat planning with new silos, distribution, imports/exports, blending and transport | Infrastructure/operation integration precedes this study | Full equations, uncertainty, matrix, bounds/gaps, resources and stopping definitions |
| Hosseini2020; earlier publisher preview | Wheat-network design with uncertainty, sustainability and resilience | Do not present uncertainty or resilience as generic new features here | Full text and exact decision/solution/computation comparison |
| Shastri2011; institutional abstract | Agricultural MILP decomposition and distributed solution | No first agricultural-HPC/decomposition/scalability claim | Full method, decomposition assumptions, quality certificates, timings and resource scopes |
| Rosa2026thesis; prior abstract-level access and acknowledged model foundation | The article's mathematical provenance is explicitly attributed | Delimit incremental empirical/methodological content | Author-verified complete thesis/model/result overlap |
| Rosa2025; original review retained, prior open-text identification | Systematic grain-facility-location background | Preserve the original19-page review, not an AI replacement | Search-date/count chronology author decision |
| Nourbakhsh2016; publisher/institutional metadata and preview | Grain-network design with infrastructure investment and post-harvest-loss mechanisms | Additional close precedent to review | Full text; remains a candidate outside the retained38 and bibliography |

Sources:
[Essien institutional text](https://ugspace.ug.edu.gh/server/api/core/bitstreams/ba3cff00-501e-4c12-aba8-011fe3e7ccb0/content);
[Reis publisher text](https://www.mdpi.com/2305-6290/7/3/49);
[Gholamian publisher preview](https://www.sciencedirect.com/science/article/pii/S016816991630919X);
[Hosseini publisher preview](https://www.sciencedirect.com/science/article/pii/S0168169919315479);
[Shastri institutional record](https://experts.illinois.edu/en/publications/a-novel-decomposition-and-distributed-computing-approach-for-the-/);
[Nourbakhsh publisher record](https://www.sciencedirect.com/science/article/pii/S1537511016304767).

Access to a preview does not establish that the full paper omits a quality,
memory or timing metric. The current pass did not obtain new full texts for
the access-limited studies, and does not promote their access statuses.

## Gap/contribution tests

| Proposed claim | Test against the literature/evidence | Disposition |
| --- | --- | --- |
| New grain-storage location or stochastic network model in general | Established location/uncertainty precedents and Rosa foundation | Exclude this claim |
| First large stochastic agricultural optimization | Existing large tactical LP and computational-method studies | Exclude this claim |
| New optimization algorithm or controlled parallel speedup | No new algorithm; one observation per thread configuration | Exclude this claim |
| Empirical extensive-form assessment linking phases, attained quality and planning decisions | Compare matched decision structures and measurement scopes in close full texts; retain exact original cohort certificates | Working C1/C2 position, conditional on B3 completion |
| General inability of open-source solvers at h215 | Original accepted HiGHS result, distinct SCIP outcomes and unfinished common-form campaign | Exclude solver-class impossibility; report observed, qualified outcomes |
| Distributed capacity-sizing pattern in returned plans | Original positive-candidate investment counts and physical summaries | Retain bounded interpretation; do not infer sparse hub selection or policy-optimal infrastructure |
| AI productivity or scientific authority | No controlled productivity experiment; humans review/adopt proposals | Keep C3 complementary, with approved SO4 and Methods/B explanation |

The article's single approved question is preserved. It asks about attainable
resolution quality and computational requirements for the defined planning
models, not a universal asymptotic law. Final wording must connect C1 to
measurements and C2 to the physical decisions, not treat a solver's success
status or variable count as the scientific contribution.

## Next B3 actions

Prioritize lawful full-text access to the closest network/uncertainty and
distributed-MILP sources and the complete Rosa thesis. Extract decision domains,
uncertainty, objective/physical scope, algorithm, dimensions, quality and
phase/resource definitions with exact page/table locators. Reconcile the
remaining retained records using that same schema; verify identifiers/authors/
years without silently adding or deleting references. Keep inaccessible or
unverified fields explicit. Final gap/highlights and claims of incremental
contribution remain subject to this source-specific comparison.

## B3 increment — 1 November 2026

Reis et al. Table 8 (p.18) was checked against the original 26-page PDF,
including a rendered page, rather than a search snippet. For the same
243-scenario LP, the three algorithm columns report:

| Algorithm | Solution time, s | Peak Memory, Mb as printed |
| --- | ---: | ---: |
| Barrier | 84.61 | 2720 |
| Dual simplex | 246.9 | 2131 |
| Primal simplex | 328.91 | 1902 |

The accompanying text identifies AIMMS 4.82, CPLEX 20.1, an i7-7500 at
2.70 GHz and 8 GB RAM. Section 3.2 and Tables 3-5 distinguish first-stage
grain/transport contracts from second-stage spot purchases, processing,
sales, inventories and flows. Their profit objective and fixed-recourse LP
are not the present penalized infrastructure-investment MILP.

This positively establishes prior measurement of memory as well as runtime
and algorithm choice. The gap cannot be framed as the first resource-aware
agricultural optimization study. The manuscript now acknowledges these
measurements explicitly, preserving the printed memory unit without an
unsupported MB/MiB conversion. No cross-paper speed or memory ratio is formed.
Published iteration counts are not used to rank algorithms or validate the
paper's results. Other access-limited sources retain their prior status;
this increment does not close the full-text or Rosa-thesis comparison.

## Contribution baseline and Essien extraction — 1 November 2026

The comparison baseline is the whole Related Work corpus, including Rosa's
thesis. Thesis overlap is one necessary provenance comparison, not the sole
boundary of the article's contribution. C1/C2 require evidence against location,
investment, uncertainty and computational-method precedents together.

Essien et al., Sections 2.1-2.2, Eqs.(1)/(22), pp.127-129: prescribe site count
and minimize normalized stakeholder transport deviations. Ghana application,
four stakeholder groups; Matlab R2016b, GAMS 24.8.3 and ArcGIS; Google Distance
Matrix inputs. This is a positive decision-structure comparison, not a claim
that an unextracted runtime or memory field is absent. The article now
distinguishes this scope from continuous capacity sizing with shared investment.
Primary institutional text:
https://ugspace.ug.edu.gh/server/api/core/bitstreams/ba3cff00-501e-4c12-aba8-011fe3e7ccb0/content

| Contribution test | Literature baseline | Additional evidence needed here |
| --- | --- | --- |
| Computational characterization | Agricultural MILP methods, large tactical LP and published resource measurements | Common formulation, per-phase clocks, quality/bounds, hardware and resource scopes; retain unequal-gap limitations |
| Agricultural interpretation | Location, stakeholder trade-offs, network investment and uncertainty precedents, including Rosa | Source-bound installed capacities, separate stock/throughput/slack units, service and flow-distance summaries |
| Comparison of implementations | Native solver algorithms and modeling interfaces | Separate historical/native and common-Pyomo cohorts; paired matrix/input bindings and repeated controlled profiles |
| Complementary research method | Human-directed scientific modeling and verification | Inspectable proposal/adoption/check chain; no causal AI-productivity claim |

The active h300 jobs provide no new outcome yet. The 90 planned calculations
do not become statistical evidence merely through submission. Full-text access
limits, complete Rosa comparison and unresolved author decisions remain open.


## B3 source-specific increment — 1 November 2026

Milanez2026: original journal PDF, pp.12-13, BSEC-SLACK Eqs.(12)-(15)
and Table2: penalized seaport overflow, CPLEX12.6 CPU time and gap.
These are direct precedents; do not claim novelty for either mechanism or
reporting field. Port throughput slack differs from our stock/reception/
shortage families. No cross-paper performance ratio is justified.
[Primary text](https://www.scielo.br/j/bbr/a/BB8SXxvqdLYrmLc9LNHHxNv/?format=pdf&lang=en).

The metadata ledger retains all38 bibliography records. Crossref provides
32 DOI identities with matching normalized titles and retained publication
years. Two additional article identities were verified from their journals;
the dataset is verified through Zenodo rather than Crossref. No bibliography
record was added or removed. Registry identity is not full-text scientific
reconciliation, and complete author-order verification remains open. The
thesis overlap and other access-limited close precedents retain their open
statuses. See [the source-specific ledger](evidence/reference_registry_reconciliation_20261101.json).
