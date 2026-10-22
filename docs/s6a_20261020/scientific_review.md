# Scientific review of the coauthor annotations

## Assessment and authority

The source is the supplied33-page annotated PDF, SHA256
`fbcd5a083775ca25f117adbab1f805c0a08545cd946b0c1bf0045e3258727179`.
It contains123 highlights,13 strikeouts and10 notes, with17 empty comments.
All page numbers below refer to that PDF. The accompanying pasted assessment
is a useful agenda; it is not evidence that an annotation was implemented or an
experiment executed. The researcher authorizes this PR and omits authorship
identification, superseding the attachment's requests to recover author names
or ask again before opening the PR.

Decisions follow the explicit researcher mandate, [scalar contract](../mvp2_scalar_contract.md),
accepted evidence and then review recommendations. Scientific changes are not
inferred from editorial requests. The mathematical model remains unchanged.

The most important recommendation, A142 on p24, is accepted: describe the
optimized agricultural plan. The article needs a reader to understand which
candidate facilities are activated, where positive investment occurs, how grain
moves and where capacity pressure remains. This is descriptive interpretation of
the encoded planning problem. It does not require proving economic, social or
environmental gains from implementation in the real system.

## Source reconciliation before editing

The reviewed file has a different hash from the annotated PDF recorded in
[the earlier coauthor revision](../cea_coauthor_revision.md),9fddd98a.... Preserve
both identities. Its title, SBC layout, abstract and thirteen-attempt comparison
match the manuscript family before the2 October rewrite: the text at
`9e648a4cd72f0eda04287736fbd7329185aadba7` and parent of
`e80693ae5d44e7ca117dfa4b2f1d84bba40210cf` is a matching source candidate.
Title/paragraph matches do not establish the exact generating commit, compiler
or package. That build identity is unresolved. Treat the PDF hash and page/object
locators as the authoritative review target until the authors identify the build.

Current `manuscript/index.qmd` has a different title and an Elsevier renderer.
It already expands transport costs, uses explicit quantifiers, shortens several
captions and includes notation/table references. Its historical hierarchy,
EVPI/VSS and results still require a coherent scalar revision. An annotation can
therefore be addressed in the later historical source while still needing review
in the new scalar article. No content is declared implemented solely from the
old `cea_coauthor_revision.md` checklist. The matrix records these distinctions.

## Action register

Each action defines a concrete acceptance test and its evidence dependency.
`Implementation pending S6-B` applies unless the matrix explicitly identifies
an item already present in repository sources. The full mapping is in
[annotation_responses.csv](annotation_responses.csv).

| Action | PDF pages / principal IDs | Assessment and required revision | Evidence / objective acceptance criterion |
| --- | --- | --- | --- |
| C01 Front matter |1;A001 | Accept Litoral spelling; retain existing author list and institutions | Current authors.json and rendered affiliation agree; no author/order change |
| C02 Questions and contribution |1–2,7,29;A002,A009,A016,A058–60,A146 | Credit Rosa (2026), define implemented contribution, offer computational-limits titles and include planning interpretation | Each contribution maps to code/evidence; final title/novelty claim receives coauthor approval |
| C03 Language and terminology |1–10,21;multiple targeted edits | Accept precise terminology and grammar; distinguish planning period, inventory stock, storage capacity, facility and model construction | Consistent dictionary in outline/prose/equations/captions; preserve actual monthly convention and original values |
| C04 Related work and application boundaries |2–6;A018–43,A050 | Group studies by decisions, network, uncertainty and computational method; explain governance and environmental exclusions | Comparison identifies the actual assumption being compared; no numerical benefit or uniqueness claim from unrelated papers |
| C05 Uncertainty synthesis |5;A044–46 | Accept restructuring and specialist coauthor review; separate strategic investment from tactical decisions and different information structures | Scenario construction and two-stage assumptions explicit; finite weights not described as estimated probabilities |
| C06 Complete mathematical presentation |7–15;A065–101 | Accept conventional objective-first DET and complete STO presentation with definitions, indices/domains, then explanation | Every family crosswalks to current builder; all four transport terms, three penalties and investment once are explicit |
| C07 Physical units and slack interpretation |3,5,9,23;A022,A047–48,A074–75,A131 | Clarify stock, daily handling and period overflow; discuss fixed coefficients and financial meaning | Reception overflow added after daily conversion; storage summed over time labelled tonne-periods; penalties separate from expenditure |
| C08 Closed-candidate activation |13;A093 | Partially accept the need for clear activation, retain native indicators | The implication y=0 implies both capacity slacks zero is explicit; any future finite bound needs a separate equivalence argument/approval |
| C09 Local conservation |14;A099 | Accept removing the redundant aggregate equation from the main formulation | Original indexed origin/warehouse/product/period/scenario residuals stay the validation basis; aggregate only supplementary diagnostic |
| C10 Data, populations and scenarios |9,16–19,21;A072–73,A104–08,A114–15,A119,A124 | Explain reference workbook, preprocessing, original ranking and actual execution status; supply input table | Full input hash and population membership bind the run; 146 existing plus69/154/254/354 candidates at215/300/400/500; status and scalar/historical cohort explicit |
| C11 Scenario and input supplement |18–19;A119 | Give low/base/high multipliers, Cartesian construction and approved weights together with physical/economic inputs | Nine1/9 weights sum to one; original DET arrays stay distinct; unknown currency/price year stays explicitly unknown |
| C12 Deterministic evidence |17,29;A111–12,A146 | Accept: use already accepted scalar h215 DET/STO results and declared input differences | Dimensions, phases, objective/bound/gap, resources and original validation identified per mode; no EVPI/VSS or economic-superiority inference |
| C13 Numerical reconciliation |17,21,23–24;A110,A121,A132 | Separate target/achieved gap, global/stage gap and cross-cohort values; retain precision near thresholds | Values trace to unrounded records; the1% slide refers to its own cohort; no unsupported monotonicity claim |
| C14 Agricultural planning outputs |24;A142 | Accept as scientific priority: interpret actual scalar investment and recourse decisions | Use accepted solution vectors, coefficients and geographic join; report counts/quantities/costs/flows/units plus separate slack peaks and totals |
| C15 Evidence communication |7,25;A057,A062,A143 | Accept a readable validation paragraph in the main text | Distinguish original residual certification, portable receipt replay and new revalidation; move hash/detail inventories into supplement |
| C16 Computational/HPC interpretation |6,27;A053,A144 | Accept clearer phase/thread/scenario/memory reasoning; qualify any LP assertion | Zero fixed costs do not alone remove integrality; empirical presolve claims name the run/objective/log; no scalar claim from archived service pass |
| C17 Unimplemented decomposition |28;A145 | Resolved by existing S4 cancellation: remove detailed Benders derivation from active article | No implemented decomposition claim or future-work dependency; at most a brief optional research direction |
| C18 Value of information |19;A118 | Resolved by existing exclusion: remove EVPI/VSS and associated auxiliary-solve passages | No active calculation, metric or experiment added; historical files preserved |
| C19 Figures, tables and captions |4,6,8–10,16–24;many IDs | Accept short captions, explicit references and readable visual encodings; adapt slide18 to scalar phase metrics | Every visual is cited/discussed, has units/source and comparable denominator; historical priority stack is not reused as scalar timing |
| C20 Cost horizon and accounting |4–5,23;A034,A041,A129 | Accept explicit input-currency horizon totals, investment once, operation by period | Currency/year status and undiscounted basis are documented; no annualization or observed-loss interpretation invented |
| C21 Claims and supplements |7,21,29;A064,A125,A146 | Accept bounded statements and full historical/systematic-review supplement preservation | Main narrative foregrounds scalar evidence; missing/censored outcomes stay visible; redistribution needs factual rights confirmation |
| C22 Unexplained marks |3,7–9,13,15,17–18,21,24;17 IDs | Clarify: retain every mark with its location and no invented intention | The matrix's empty-comment inventory matches all17 original marks; independent editorial corrections are labelled separately |

## Quantitative issues that can already be resolved

### Deterministic results and fixed penalties

The [accepted h215 record](../evidence/scalar_h215_2217990_review.json) supplies
real scalar results for job2217990, beyond the historical PDF's DET promise.
DET native runtime122.514958s and native gap0.0008121363%; STO2445.517971s and
0.7401594783%. Both meet the configured1% global scalar target and have accepted
original residual certificates. Portable review replays those certificates; it
does not newly solve or recompute private-input residuals.

Domestic service is91.8611844%/92.2673837%; penalty shares96.5917779%/96.9865311%.
These figures motivate physical and accounting interpretation, while preserving
the researcher's acceptance of the result and coefficients. A small global gap
does not independently bound the economic subtotal. No new service floor,
zero-slack condition or penalty calibration is introduced.

### The1% versus10% discrepancy (A121)

Three located copies of the25-slide presentation have matching slide15 content.
The download-labelled5 October copy, SHA25628488050..., describes the ten-reference
cohort with4h and1%, including the incomplete nine-scenario warehouse-only case.
The reviewed PDF describes the later thirteen-attempt comparison with8h and10%
per nonzero hierarchy pass. These are different cohorts, so the percentage alone
is not a contradiction. The current scalar h215 and planned h300 block use4h and
1% globally per arm. State all three experimental contracts explicitly.

The file's internal footer says4 October; its download name says5 October.
Matching local copies establish what the inspected slides say, not which exact
attachment reached each coauthor. The evidence record includes each file hash.
Slide18 is a stack of historical priority runtimes. A current scalar figure can
retain that readability while stacking data/build/optimization/extraction/
validation phases only when their clocks do not overlap.

### Why353.989 need not exceed354.889 in the expected direction (A132)

The values are historical economic components for215/D/A and300/D/A, not current
scalar objective optima. The larger nested *feasible set*, if established under
identical objective/data and embedded smaller plans, implies a nonincreasing
optimal total for minimization. It does not constrain each arbitrary incumbent,
nor one cost component under a hierarchy with inherited limits. Audit costs,
arcs, scenarios, embedding and quality before interpreting the difference.
The existing [comparison ledger](../evidence/sprint_c_final_20260920/comparison_summary.md)
explicitly qualifies the inherited capacity/economic comparisons. No value is
changed and no new corrective optimization is prescribed here.

### Zero-cost activation and presolve (A144)

With zero fixed charges and no positive minimum investment, activation binaries
can be degenerate: y=1 need not imply positive candidate capacity. That explains
why agricultural counts must accompany quantities. It does not establish that
all integer variables are removable or the full problem is an LP. The PDF's
observed continuous presolved SCIP problem refers to a historical service pass.
The current scalar objective and its root/presolve logs require their own
evidence. Write only the conditional mechanism until those logs are audited.

## Journal relevance and limits

The [publisher's scope](https://shop.elsevier.com/journals/computers-and-electronics-in-agriculture/0168-1699)
includes agricultural storage/logistics and emphasizes computing innovation
beyond routine application of existing tools. This suggests a plausible fit if
the paper demonstrates a developed computational method, reliable measured
evidence and meaningful agricultural outputs. It does not establish acceptance.
The current distinctive claim should rest on the inspectable construction,
network/data contracts and independent validation, with measured computational
limits. A cluster allocation or a solver comparison alone is insufficient.

The framing should join two questions: what solution quality/resource demand is
attained for the declared DET/STO instances, and what those validated solutions
mean for the modelled storage system. Keep policy implementation, external
forecast accuracy and environmental impacts outside the demonstrated claims.
Additional causal performance claims would need a separate matched design;
they are not silently added as required campaigns.

## Outstanding evidence and author decisions

Actual scalar agricultural vectors/geographic inputs, final h300 terminal review,
currency/price-year facts, review-search chronology and final coauthor approval
remain dependencies. Source build identity, title and supplementary disclosure
are factual/editorial decisions. Big-M replacement, penalty calibration, new
solvers and reopening S3/S4 are not necessary to implement the compatible
recommendations. See [roadmap_and_decisions.md](roadmap_and_decisions.md).
