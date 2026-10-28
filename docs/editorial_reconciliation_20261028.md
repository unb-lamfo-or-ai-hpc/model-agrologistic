> Follow-up: the returned 01.04 opinion and current develop are reconciled in
> [the claim/source matrix and author action sheet](literature_claims_reconciliation_20261028.md).
> This document preserves PR136's earlier reading baseline and exposition work;
> it is not the current pending-job list or a full 38-record review.

# Literature and exposition reconciliation — 28 October 2026

## What was preserved and what was examined

The main/develop reading baselines are b53b87043f898f2af11dba3f79f23f43738ad2df
and c092fa7be2fea69f6e0eb8ab707e38aa68e1b85b, respectively.
Their retained references.bib contents are identical:36 records,33 cited in the
expanded main article. dubke2011, steiner2017 and kaltis2026 remain retained but
uncited there. Two additional review-method records are in review-methods.bib.
These counts distinguish bibliography inventory from a completed full-text review
or a new systematic search. The original Appendix A, author metadata, title,
question, objectives and mathematical model remain preserved.

The public Pages article was inspected in the Codex browser: it identifies the
23 October review snapshot and still describes h500 as pending. Its source is a
historical public baseline; develop already contains later accepted h500 and
original negative scalar SCIP evidence. This revision does not publish a new
Pages snapshot or restore outdated statements over accepted results.

The six retained Computers and Electronics in Agriculture (CEA) references
fall into two groups: agricultural network/decision support and computational
methods at optimization, simulation and data-preparation levels. They are
relevant precedents, but not exchangeable runtime baselines.

## CEA precedents and their role in this revision

| Citation / source access | Scientific distinction | Editorial consequence |
| --- | --- | --- |
| essien2018, DOI 10.1016/j.compag.2018.02.019; full five-page article available from the University of Ghana repository | Grain-storage decision support combines stakeholder-specific location/transport models, forecasting and goal programming. Its staged decision-support procedure is not automatically two-stage stochastic recourse. | State the decision-maker, objective and uncertainty interpretation before comparing models. Explain a stakeholder trade-off through the corresponding cost comparison. |
| gholamian2017, DOI 10.1016/j.compag.2017.05.038; publisher preview/abstract | An integrated wheat-chain case includes network decisions beyond warehouse count. Its model and case differ from the present Brazilian grain network. | Compare decisions, echelons and constraints rather than presenting generic grain-network optimization as an unoccupied topic. Full-text method/result claims still need verification. |
| hosseini2020, DOI 10.1016/j.compag.2019.105095; publisher preview/section excerpts | Sustainability, resilience and uncertainty motivate a multi-objective wheat-network design/redesign problem. | Do not equate emergency algebraic slack with implemented resilience, or assign sustainability outcomes absent from our model. |
| shastri2011, DOI 10.1016/j.compag.2011.01.006; Illinois institutional record and publisher abstract/preview | BioFeed already connects agricultural MILP solution strategy with decomposition/distributed computation. | A computational contribution needs comparison with existing methods and evidence. Current extensive-form computation is not a new decomposition algorithm. |
| knapen2025, DOI 10.1016/j.compag.2025.110392; Wageningen institutional abstract/metadata | Distributed WISS-WOFOST simulation and aggregation have different parallel work units from a MILP with shared first-stage integer decisions. | Identify the computational workload and measured region. Published simulation scaling cannot validate solver-thread speedup here. Full PDF access was attempted, not obtained in this session. |
| zhao2012, DOI 10.1016/j.compag.2012.08.007; publisher abstract/preview | Spatial input-data assembly is a distinct computational stage. | Separate preparation, construction, optimization and post-processing. Do not attribute all wall time to native solution work. |

Sources inspected:
- [Essien et al., institutional full text](https://ugspace.ug.edu.gh/server/api/core/bitstreams/ba3cff00-501e-4c12-aba8-011fe3e7ccb0/content)
- [Gholamian and Taghanzadeh, publisher](https://www.sciencedirect.com/science/article/pii/S016816991630919X)
- [Hosseini-Motlagh et al., publisher](https://www.sciencedirect.com/science/article/pii/S0168169919315479)
- [Shastri et al., Illinois record](https://experts.illinois.edu/en/publications/a-novel-decomposition-and-distributed-computing-approach-for-the-/)
- [Knapen et al., Wageningen record](https://research.wur.nl/en/publications/efficient-and-scalable-crop-growth-simulations-using-standard-big/)
- [Zhao et al., publisher](https://www.sciencedirect.com/science/article/abs/pii/S0168169912002086)

Direct HTTP retrieval of several ScienceDirect pages returned 403; indexed
publisher previews were available. Access level is explicitly recorded rather
than treating a title, abstract or institutional metadata page as a full-text
assessment. The broader source-by-source literature-gap investigation is the
chat 01.04 handoff, not a completed result of this focused reconciliation.

## Lessons from the supplied Porporatto–Fumero–Corsano article

The supplied PDF is the 18-page article *Efficient matheuristic and flow-based
formulation for the multi-product Production Routing Problem with heterogeneous
fleet*, DOI 10.1016/j.compchemeng.2026.109898. It is in Computers and Chemical
Engineering, volume 216 (2027), 109898, available online 18 September 2026.
Record the issue year separately from online availability; do not silently
invent a 2026 issue year from the DOI. Its SHA256 is
2cae4e1d369ad5e9b832f62e9b3e76a1ed464222473e160640fc23799cafcfd2.
The PDF was text-inspected and its model/results pages rendered and visually
examined. It is not redistributed in this repository.

The observations concern a coauthored article; the individual writing
contribution of Gabriela Corsano cannot be isolated from the PDF. Its exposition
is useful in six specific respects:

1. Section 2 defines the system, horizon and decisions before presenting the model.
   It explains each constraint family by its function, following the equations.
2. The literature comparison uses problem features and the nearest competing
   formulation to motivate contributions, rather than listing citations.
3. Section 4.1 uses a small case to connect costs and actual operating choices.
   The reader learns why a particular trade-off occurs before seeing aggregate
   benchmark performance.
4. Section 4.3 separates primal feasibility, upper bounds, lower bounds and gaps.
   It states differences in hardware, software and budgets at the comparison.
5. Sections 4.5–4.6 distinguish a default configuration from best-of-many selection,
   define denominators, examine exceptions and retain instance-level detail.
6. Section 5 states limitations that affect inference, including missing endogenous
   bounds and a comparison that is not like-for-like.

The present revision applies these organizational principles to B/C/D: purpose
and decisions first; definitions and units before transformations; formal
equivalence with its assumptions; interpretation before technical identifiers;
and limitations adjacent to the claim they qualify. It does not copy wording,
numerical results, a PRP benchmark or an algorithm into the grain-network study.
A performance-profile figure would need an appropriate matched instance set;
our single-observation thread block does not supply one.

## Current journal-preparation facts

The [official CEA Guide for Authors](https://www.sciencedirect.com/journal/computers-and-electronics-in-agriculture/publish/guide-for-authors)
was read in the Codex browser on 28 October 2026 after direct web retrieval failed.
Its scope includes post-harvest storage/logistics but emphasizes a demonstrated
computational innovation. Original research, rather than an application note,
is the present intended category. Fit remains a scientific assessment.

Current preparation checklist: abstract at most 250 words; 1–7 keywords; separate
editable highlights with 3–5 points of at most 85 characters each; editable manuscript
sources; editable tables; individually supplied figures and captions; graphical
abstract encouraged, not stated as mandatory; numbered appendices; AI disclosure,
funding/conflict statements, CRediT and all-author approval; research-data deposit/
citation or explanation of restrictions, plus an availability statement.
No journal-wide page cap, compulsory graphical abstract or compulsory CAS class
is inferred from generic templates.

The [publisher's LaTeX instructions](https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions)
provide elsarticle and alternative templates and require checking journal-specific
rules. Source files for Editorial Manager must be flat. The existing pinned
community Quarto extension wraps elsarticle; it is not journal endorsement.
Its class/styles/notices are unchanged. Final file packaging, citation style,
figure resolution/permissions and declarations still require a submission pass.
No editor contact, submission, public update or rights clearance is performed.
