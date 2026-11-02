# Scientific revision blueprint — 30 October 2026

This is an **author-facing decision record**, not publication prose.
Baseline: [develop c80dca69](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/commit/c80dca69c247753d49f06925ec712fcd43bb5a56).
The two annotated PDFs are historical previews from 5966c08e, not the current
develop manuscript. Their 69 pages, equations, tables, figures and references
were read; all pages were visually inspected in twelve contact sheets.
Eleven article annotations and thirteen supplement annotations were extracted.
Blank comment-author metadata does not identify a particular coauthor.
The [structured response matrix](evidence/editorial_annotations_20261030.json)
retains all 24 comments, PDF hashes and page anchors; temporary PDFs, page
images and full text extracts remain local.

The approved title and literal research question, SO1–SO4, attribution to Rosa
(2026), mathematical formulation, effective inputs and accepted experimental
records are preserved. This blueprint precedes extensive editing. Proposed
changes below are not a declaration that the scientific revision is complete.
PR #143 has been merged with explicit approval at c80dca69c247753d49f06925ec712fcd43bb5a56; its public license
qualification does not authorize or qualify another private experiment.

The [first-pass progress record](editorial_revision_progress_20261030.md) and
structured matrix record subsequent implementation; the table below preserves
the pre-edit disposition required by the mandate.

## A. Annotation-response matrix

“Resolved in baseline” means the commented wording is already absent in develop.
“Planned” means the correction is authorized editorial work but remains subject
to source review. Author-decision items are held at the point of scientific
choice, while independent editing continues. Each original Portuguese comment
is retained verbatim in the structured matrix; the table summarizes its concern.

| PDF | Page | Annotation / scientific concern | Proposed correction | Source evidence | Acceptance status |
| --- | ---: | --- | --- | --- | --- |
| Article | 1 | ART-01: Remove development announcement | Keep reader-only front matter; the announcement is already absent from develop. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/index.qmd) | resolved in baseline |
| Article | 1 | ART-02: Explain the problem before technical bookkeeping | Rewrite the abstract around location/capacity decisions, uncertainty, computational assessment and agricultural findings. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/index.qmd) | planned |
| Article | 1 | ART-03: Begin scale comparison at h215 | Describe the stochastic matrix from 14.1 million variables at h215 to 63.4 million at h500. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/scalar_results.qmd) | planned |
| Article | 1 | ART-04: Reduce abstract detail and explain relevance | Move thread lists and phase/resource detail to Results; retain a small number of interpretable headline findings. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/scalar_results.qmd) | planned |
| Article | 1 | ART-05: Keep detailed cost/service trade-offs in Results | Explain W/D under the single scalar objective in Results; omit the W/D comparison from the abstract. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/wd_results.qmd) | planned |
| Article | 1 | ART-06: Separate operational incidents from scientific outcomes | Remove incident narratives from the abstract. Retain relevant adverse numerical outcomes in any solver comparison, with concise limitations; author confirmation is needed on the tension with blanket exclusion. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/index.qmd) | author decision required |
| Article | 1 | ART-07: State the agricultural meaning of the computational assessment | Explain how attainable scale supports capacity-sizing analysis and why returned plans require service/stock/throughput interpretation. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/scalar_results.qmd) | planned |
| Article | 1 | ART-08: Concentrate Human–AI exposition in Methods and Appendix B | Remove AI discussion from the abstract; preserve approved SO4/C3 and the required AI declaration pending an explicit author decision on their placement. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/index.qmd) | author decision required |
| Article | 1 | ART-09: Index the actual mathematical/planning problem | Add network design and mixed-integer linear programming to the keywords. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/index.qmd) | planned |
| Article | 1 | ART-10: Use the approved hub-location terminology | Replace the facility-location keyword with hub location. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/index.qmd) | planned |
| Article | 1 | ART-11: Do not present reproducibility as a novelty keyword | Remove reproducibility from the keywords while retaining reproducibility obligations in Methods/data availability. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/index.qmd) | planned |
| Supplement | 1 | SUP-01: Make each appendix independently readable | Remove the general supplementary guide; introduce necessary concepts within each appendix. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/supplement/index.qmd) | planned |
| Supplement | 1 | SUP-02: Preserve the systematic review without administrative commentary | Use the full systematic-review title and preserve the original 19-page PDF. Keep checksum/count/date issues in the author decision record only. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/supplement/appendix_a_original.pdf) | planned |
| Supplement | 21 | SUP-03: Use scientific rather than development branding | Use this work in scientific prose. The development name is absent from current Appendix B but remains in the Methods include and will be removed there. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/human_ai_methodology.qmd) | partially resolved in baseline |
| Supplement | 21 | SUP-04: Describe what the researchers actually did | Replace defensive introductory clauses with constructive descriptions of assistants, human review and verification. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/supplement/index.qmd) | planned |
| Supplement | 21 | SUP-05: Avoid repeated attribution in the AI account | Retain Rosa attribution in the model/Introduction; remove its redundant explanatory paragraph from Appendix B. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/supplement/index.qmd) | planned |
| Supplement | 21 | SUP-06: Remove defensive independent-origin assertions | Describe adoption and verification of proposals constructively; keep historical attribution decisions in GitHub. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/supplement/index.qmd) | planned |
| Supplement | 21 | SUP-07: Keep meeting milestones outside publication prose | The meeting-date reference is already absent from current Appendix B; preserve that reader-facing separation. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/supplement/index.qmd) | resolved in baseline |
| Supplement | 21 | SUP-08: Centralize useful, stable software links | Replace historical meeting/PR links with one compact implementation/data index and self-contained explanation. Freeze final main/release links only after authorized integration. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/supplement/appendix_c.qmd) | planned |
| Supplement | 21 | SUP-09: Show the verification method concretely | Introduce P1–P6 and V1–V4 using investment/probability/residual examples; avoid making development failures the organizing narrative. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/supplement/index.qmd) | planned |
| Supplement | 21 | SUP-10: State Gurobot's role directly | The retrospective-account wording is already absent; retain a direct description of Gurobot's role while improving the surrounding prose. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/supplement/index.qmd) | resolved in baseline |
| Supplement | 23 | SUP-11: Make the workflow figure readable and properly introduced | Remove development text inside the graphic; shorten title/caption, cite before and interpret after in Methods and B. Check floating placement in final rendering. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/human_ai_methodology.qmd) | planned |
| Supplement | 25 | SUP-12: Explain the model-to-code connection without link overload | Reorganize C around equations, a compact linked implementation tree and a worked example; state the uncompiled/unvalidated GAMS limitation once. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/supplement/appendix_c.qmd) | planned |
| Supplement | 29 | SUP-13: Expose the actual numerical inputs and access limits | Present effective values, 14-sheet gold coverage and registry/processed-input provenance. Prepare a numerical coverage ledger; full-data publication needs access/rights/format decisions. Obsolete penalty values remain outside publication prose. | [Source](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/c80dca69c247753d49f06925ec712fcd43bb5a56/manuscript/supplement/appendix_d.qmd) | data and author decision required |

The original Appendix A has 19 pages. Its tracked SHA-256 is
`859dc52b64b6bcf471f7616182d8cadf2b693dbfd19ad4b9248637b5c231b3ed`.
Each original decoded page stream matches its embedded Form XObject on
supplement pages 2–20; normalized page text also matches. This establishes
preservation of included page content, not byte equality of the outer merged
PDF or its rounded page boxes. No original PDF is edited.

## B. B3 literature-gap and contribution verification

### Working argument and evidence boundary

Agricultural facility location, integrated grain-network planning, uncertainty
and computational solution methods all have established precedents. Our
working contribution is the empirical connection between extensive-form
dimensions, phase-specific resource requirements, certified solution quality
and the resulting location/capacity/flow decisions. It is not a new MILP
algorithm, a universal scale frontier or a controlled parallel-speedup study.

The retained inventory is **36 main bibliography records (33 cited) plus two
review-method records**. Retention, citation and full-text verification are
different statuses. The [incremental primary-source ledger](evidence/literature_gap_verification_20261030.json)
supplements, rather than overwrites, the earlier
[claim reconciliation](literature_claims_reconciliation_20261028.md) and
[38-record disposition](literature_disposition_20261028.json).
It explicitly records new reading, earlier partial access and pending work.

Two primary-source readings sharpen the gap:

- **Essien et al. (2018)** integrate location, transport, forecasting and
  goal programming for grain-storage decision support. Their location and
  integrated-network contributions must be acknowledged directly.
  See Sections 2.1.1–2.2 and Tables 1–4 of the
  [institutional full text](https://ugspace.ug.edu.gh/server/api/core/bitstreams/ba3cff00-501e-4c12-aba8-011fe3e7ccb0/content).
- **Reis et al. (2023)** report a two-stage stochastic tactical soybean LP with
  243 scenarios, 1,987,225 variables and 2,288,220 constraints, including an
  algorithm/runtime comparison. This rules out treating large stochastic
  agricultural models or solver-algorithm comparisons as absent from the
  literature. Their contractual first-stage decisions differ from our
  warehouse location/capacity MILP. No cross-paper runtime ratio is meaningful.
  See [Sections 3.1–3.2, 4.2, 6.1 and 7](https://www.mdpi.com/2305-6290/7/3/49).

**Priority order:** (1) full-text comparison with Gholamian, Hosseini-Motlagh,
Shastri and the complete Rosa thesis; (2) resolve the remaining close storage,
network-design and uncertainty precedents in the retained inventory; (3) check
computational-method and measurement sources; (4) verify metadata and connect
every retained claim to an exact section/table/page. Preview-only access can
support a positively stated abstract claim, never an assertion that the full
paper lacks a method, quality metric or resource measurement.

Nourbakhsh et al. (2016), DOI
[10.1016/j.biosystemseng.2016.08.011](https://www.sciencedirect.com/science/article/pii/S1537511016304767),
is a new **review candidate**, identified in Essien's references and confirmed
in publisher/institutional metadata. It addresses grain-network infrastructure
and logistics investment. Full text is pending; it is not silently added to
the 38 retained records or the manuscript bibliography.

### Contribution and highlights acceptance

| Component | Defensible content | Evidence required before final wording |
| --- | --- | --- |
| C1 / SO2 | Observed dimensions, construction/optimization phases, measured memory and certified quality across the retained cohort | Original cohort records, clearly separated timing/resource scopes, no causal thread or solver ranking |
| C2 / SO1 and SO3 | Location/capacity and flow consequences of the implemented scalar model | Decisions and residuals, economic/penalty separation, service and stock/throughput indicators, W/D limitations |
| C3 / SO4 | Complementary human-supervised implementation and verification procedure | Documented tool roles and P1–P6/V1–V4 examples; no inferred productivity or algorithmic novelty |

Final highlights must reflect these accepted empirical findings rather than
record counts or infrastructure announcements. Novelty remains conditional on
full-text reconciliation and a clear account of additions to Rosa (2026).

The [official CEA guide](https://www.sciencedirect.com/journal/computers-and-electronics-in-agriculture/publish/guide-for-authors)
was rechecked in a Codex tab. Current requirements include an abstract of at
most 250 words; one to seven English keywords; a separate editable file with
three to five highlights of at most 85 characters each; editable Word/LaTeX
sources; editable, cited tables; captioned supplements; data availability;
author declarations and approval. Existing-software application alone is a
scope risk. A shorter application-note limit is not a research-article limit.
The submission checklist must be rechecked near submission.

## C. D2 appendix and numerical-data plan

### A — Preserve the original review

Use **Appendix A — Systematic Literature Review of Grain Facility-Location
Models**, followed by the unchanged 19-page original. Remove publication-facing
checksum, review-history and PRISMA discrepancy commentary. Preserve the
count/date questions here for author resolution; do not reconstruct a search
or silently repair the original review.

### B — Explain the research method constructively

Organize the account around what Gurobot, Gemini/GPT, ChatGPT Classic and Codex
supported, what humans decided and how adoption was checked. Present:

- P1 Human Scientific Intent; P2 AI-Assisted Implementation; P3 Technical
  Verification; P4 Scientific Validation; P5 Human Scientific Decision;
  P6 Provenance/Reporting.
- V1 software functionality; V2 mathematical consistency; V3 protocol
  conformity; V4 empirical scientific support.

Use concrete examples: shared investment charged once, probability weighting,
capacity units, original-unit residuals and interpretation of the returned
plan. Keep exploratory objectives/decomposition in historical records rather
than presenting them as active methods. Use a compact Methods account with
the same workflow figure repeated in B; cite each figure before it appears
and follow it with an interpretive paragraph. Remove development instructions
inside the graphic. Preserve necessary limitations once, without organizing
the narrative around disclaimers.

### C — Explain equations, implementations and validation

Begin with the deterministic model and shared first-stage/stochastic recourse
structure. State the full scalar objective once, define all units and explain
feasibility slacks. Use scientific OW/WD/WW/direct-OD notation, with a concise
legacy OD/DC/DD/OC crosswalk. Follow with one linked implementation tree/table
for native Gurobi, native SCIP, common Pyomo and GAMS, plus a small worked
example linking an equation to investment, flows and residual reconstruction.
State the uncompiled/not numerically validated GAMS limitation once. Do not
claim numerical parity from textual or structural correspondence.

### D — Present values, coverage and reconstruction

The following data layers must remain distinct:

| Layer | Required presentation | Present access/verification boundary |
| --- | --- | --- |
| Public revised gold workbook | All 14 sheet names, numerical tables, units, source cells and a machine-readable numerical companion where suitable | Public source SHA `de3bdc51b2c338194a5013165bec2884b68784fb207ae8c762984a1b44856082`; source-cell audit exists |
| Full warehouse registry | Explain 18,086 rows / 13 columns, role/eligibility rules and selection; expose all authorized numerical records in an appropriate companion | Registered source SHA `0d19865ac72eca0706960d10b6dbd1647a4951378a831715e39af8029ecb77f2`; external bytes/access rights are not established by this editorial pass |
| Effective processed instances | Exact warehouse IDs/roles/order, frozen OSRM arcs/distances, derived parameters and hashes for each retained size | A source dictionary alone cannot recreate missing processed workbooks or road-graph data |
| Effective model settings | Explicit units, 60 periods/two products, nine Cartesian scenarios, probability weights, initial-stock convention, costs/capacities and penalties | Use only executed 90,000 / 45,000 / 45,000 penalty rates, with their distinct physical units |
| Derived inputs/results | Explain deterministic transformations and distinguish input candidates from optimized facilities | No regeneration or new solve is part of this revision |

The first [14-sheet numerical coverage ledger](evidence/appendix_d_numerical_coverage_20261030.json)
now records dimensions and counts of numerical, formula and nonempty cells from
the hash-verified public gold source. It is a coverage inventory, not a complete
effective-values export. Continue the sheet/column/row reconciliation rather than
substituting another dictionary. Separate values already public, values derivable from public
sources and restricted/missing values. Present freight, holding, investment,
handling and scalable-capacity numbers in human-readable tables. Explain
146 existing facilities and 69/154/254/354 candidates for totals
215/300/400/500, and the nonnested OSRM graphs after screening.
Zero initial stock is an explicit convention when no initial-stock sheet is
present. Do not expose obsolete penalty cells in publication prose.

Literal inclusion of the entire registry and all processed networks in the
PDF would overwhelm it; the proposed solution is explanatory tables plus
complete authorized numerical companions. This format and the rights/access
of external/private records need author confirmation. Until those are
resolved, state the actual reproduction boundary rather than promising full
independent reconstruction. No restricted workbook, raw archive or dataset
deposit is authorized by this plan.

## D. A2 manuscript restructuring

Preserve the approved title and literal research question. Build a continuous
argument: agricultural storage/handling needs → location/capacity/flow
decisions → uncertainty → extensive-form computational burden → verified
literature distinction → question/objectives → C1/C2/C3.

1. **Abstract:** rewrite for agricultural and OR readers, beginning at h215.
   State the model class, empirical design, principal scale/quality finding and
   agricultural meaning. Remove job/startup narratives, version/thread lists,
   W/D detail and Human–AI exposition. Keep the detailed interpretation in Results.
2. **Introduction/related work:** make each novelty statement source-bound;
   compare decision structure and computational scope rather than paper size.
   Preserve Rosa attribution and distinguish the article's contribution.
3. **Methods:** complete readable equations, units and stage timing; explain
   input/network construction and quality/resource definitions. Keep the
   Human–AI subsection concise and place its figure in Methods.
4. **Results:** R1 matrix dimensions; R2 phase-specific time/memory; R3
   objective/bound/gap and feasibility; R4 agricultural location/capacity/flow
   interpretation; R5 W/D; R6 audited solver observations, where relevant.
5. **Discussion/conclusions:** answer the question with the scope of the
   observations, not a universal solver/complexity claim. Explain why all
   candidates receiving positive capacity is principally a distributed-sizing
   outcome rather than evidence of sparse hub selection. Distinguish modeled
   stock/throughput exceedances, unmet demand and economic expenditures.
6. **Figures/tables:** introduce and interpret every visual. An h500 optimized
   map requires original decision vectors and coordinates; an input-population
   map cannot be relabeled an optimized network. Road polylines require actual
   route geometry. Keep hashes/job/diagnostic receipts outside graphics.
7. **End matter:** preserve the numbered AI declaration, NPAD acknowledgment,
   required declarations and reconciled references.

An input-only h500 map and incomplete numeric data disclosure remain explicit
open items. The first source edits may improve abstract/keywords and standalone
appendix framing, but do not complete B3, D2 or the final numerical synthesis.

## E. X3 dependencies and revised Sprint sequence

| Workstream / package | Next deliverable | Can proceed now | Completion gate |
| --- | --- | --- | --- |
| X3 / PR #142 | Preserve original Gurobi failure and terminal SCIP evidence; configuration and outcome tables with cohort/source identity | Existing evidence audit and tables | Original terminal package review; no invented outcome |
| Separate operational follow-up | Qualify a new Gurobi package/claim after the merged license repair | Preparation under the earlier operational authorization | Its own qualification, merge approval and manual NPAD execution; not released by this editorial PR |
| B3 / coherent editorial PR | Primary claim/source matrix, verified gap, contribution/highlights reconciliation | Yes, independent of jobs | Close-precedent full texts and Rosa overlap reviewed |
| D2 / same editorial package | Standalone B/C/D, unchanged A, source-bound numerical coverage | Yes | Data access/rights/format resolved; equations/code/example and links checked |
| A2 / same editorial package | Coherent abstract, Introduction, Methods, agricultural discussion and final manuscript | Structure/prose now | Numerical claims reconciled with X3; scientific decisions resolved |
| S6-B1 | Author facts, permissions, complete editable sources, data statement and journal checklist | Inventory now | Coauthor scientific review and final package qualification |
| S6-B2 | Reviewed develop/main integration and final Quarto/Pages PDFs | Planning only | Explicit integration/publication approval, final rendering and visual inspection |

The latest supplied SCIP job #2228192 snapshot is **RUNNING at 01:31:59**,
not a terminal result or a live scheduler observation by this agent. Gurobi
#2228189 failed before a numerical search result because of the license; it
must not appear as evidence of optimization difficulty. The public license
probe #2228385 passed, but it is not h215 evidence. No starts, resubmissions,
solver-setting changes or new experiments are authorized by the editorial
mandate. CBC capability/cancellation stays only in GitHub technical records.

Use T1 focused document/source/figure checks for bounded edits; T2 related
regressions after structural changes; T3 final required checks and full
render/visual inspection before Ready. Existing PDFs were inspected, but no
new final PDFs have been rendered. Final PDFs remain a Quarto/Pages action
after separately authorized main integration. December is a planning target,
not a substitute for scientific acceptance.

## F. Scientific decisions for the authors

These are specific pending decisions, not repeated permission requests for
routine editing. Independent work continues while they are resolved.

| Decision | Proposed handling | Why author confirmation is required |
| --- | --- | --- |
| Literal research question | Keep approved wording; optionally refine “optimal resolution” to solution to a prescribed tolerance | Changing the accepted scientific question exceeds copyediting |
| ART-08 versus SO4/C3 | Put substantive AI discussion in Methods/B, retain minimal approved objective/contribution and mandatory declaration | The annotation's absolute exclusion conflicts with approved SO4/C3/end matter |
| ART-06 adverse outcomes | Remove operational incident detail from publication; retain relevant adverse numerical observations in a concise cohort/limitations account | Selectively excluding unsuccessful numerical arms can bias the comparison |
| Original review count/date | Preserve original Appendix A; resolve 20−2 versus 19 and date/2025–2026 chronology in a documented author decision | A systematic search cannot be reconstructed editorially |
| Complete numerical data | Tables plus authorized full machine-readable companions and precise access statement | Registry/processed-input rights, access and publication format are unresolved |
| Rosa thesis relationship | Author-verified model/result overlap and incremental contribution statement | The full thesis has not been compared; an abstract is insufficient |
| Economic interpretation | Confirm price/base-year and any intended policy interpretation; otherwise state modeled monetary units and artificial penalties | Objective magnitude and penalty dominance do not establish real expenditure |
| Final main/release links | Pin the integrated reviewed version at the final publication gate | Main currently differs; premature main links could point to another model |

No scientific decision, coauthor acceptance, journal submission or data release
is inferred from drafting this blueprint.
