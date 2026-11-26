# Editorial disposition — annotated methodological plan

Date: 23 November 2026. Language of revised plan: English EN.

The annotated input PDF has SHA-256 `fe31d2ca823b097a36309a6d7c6b52bfdd77e9063ad98ddebf9136e6cc3cd99d` and 89 review annotations on 29 pages. This matrix paraphrases the requests in English; the original annotated file and extracted comments remain preserved locally. The author's subsequent instructions govern the beta/alpha notation, the new K multiplier, and the explicit distinction between the historical 80/20 distance filter and the empirical economic–service frontier.

The numerical design is a methodological proposal. This revision does not activate a campaign, alter the objective or model implementation, submit jobs, or alter the shared environment. The separate choice of an economic/lexicographic objective remains explicitly outside the current approved objective.

| ID | Requested revision | Disposition | Location |
|---|---|---|---|
| C001 | Remove operational preamble | Replaced by a reader-facing abstract and research purpose | Abstract; Section 1 |
| C002 | Agricultural policy and economic-service emphasis | Reframed question, objectives and design; beta/alpha follow the author's correction | Sections 1–3, 5 |
| C003 | Humanised, self-contained academic introduction | Explained agricultural mechanisms and MVP2-to-MVP3 progression | Section 1 |
| C004 | Explain native and Pyomo implementations | Defined the modelling layers with footnoted technical references | Section 1.1 |
| C005 | Explain CPU execution | Explained processor allocation, topology and observed activity | Sections 2.5, 3.5, 4.4 |
| C006 | Connect numerical quality to agricultural relevance | Distinguished optimality certificates from service and capacity interpretation | Sections 1.1, 5; Appendix E |
| C007 | Explain automatic methods and threads | Described phase-dependent algorithms and observation of Threads=0 | Sections 2.5, 4.4 |
| C008 | Remove Benders from the principal design | Removed the decomposition comparison from this revised research design | Whole document |
| C009 | Explain workbook-to-policy-to-frontier chain | Connected effective inputs, explicit transformations and validated outcomes | Sections 3–5; Appendices A–C |
| C010 | Expand reformulation and tuning | Added diagnosis-driven equivalent-formulation and tuning investigations | Section 4.5; Appendix D |
| C011 | Use affirmative academic language | Rewrote the research purpose and explanatory scope in reader-facing prose | Whole document |
| C012 | Remove migration-operation narrative | Kept environment/job administration in technical evidence outside the plan | Whole document |
| C013 | English only | Rewrote the plan in English; retained proper names and source titles where appropriate | Whole document |
| C014 | Remove repeated negative declarations | Expressed scope through positive definitions and evidence | Whole document |
| C015 | Remove architecture comparison labels | Defined cases by population, DET/STO, policy, K and repetition | Sections 2–3 |
| C016 | State the research question explicitly | Added a full question relating policy, service, investment and computation | Section 1.2 |
| C017 | Replace decomposition hypothesis | Introduced agricultural and diagnosed-computation hypotheses | Section 1.3 |
| C018 | Interpret automatic threads accurately | Separated automatic soft limit, log-reported limit and busy CPU observations | Sections 2.5, 4.4 |
| C019 | Avoid historical penalty anecdote as the framing | Used general mechanism-based motivation and complete physical accounting | Sections 1, 5 |
| C020 | Explain DET/STO and nine scenarios | Defined shared investments and realisation-dependent operations | Sections 2, 2.2 |
| C021 | Describe cumulative population growth | Defined ordered nested membership, 100-site extensions and registry eligibility | Section 2.1; Appendix B.1 |
| C022 | Use familiar objective terminology | Explained one monetary total and its economic/penalty components | Section 2.2 |
| C023 | Preserve published mathematical notation | Retained rho/eta coupling and distinguished freight alpha from indexed export alpha | Section 2; Appendix C |
| C024 | Give parameter locations and values | Added workbook descriptions, field/cell locators and units | Appendix A |
| C025 | Explain penalty components before policy analysis | Defined shortages, static exposure and reception overflow physically | Sections 2.2, 5.1 |
| C026 | Document public and expert-based sources | Added source classification, Rosa references and calibration limitations | Sections 1, 4.1; Appendix A |
| C027 | Explain activation and coupling | Linked binary eligibility, paid quantities and operating capacities | Section 2.2; Appendix C |
| C028 | Explain beta and alpha didactically | Defined independent demand scaling, service floor and export ceiling | Section 2.3 |
| C029 | Use planning-model terminology | Removed architecture labels and explained native DET/STO construction | Sections 2–3 |
| C030 | Clarify stochastic construction | Explained shared first-stage investment and probability-weighted operation | Section 2 |
| C031 | Remove excluded architecture narrative | Focused models and case families on native Gurobi DET/STO W | Whole document |
| C032 | Discuss relevant Gurobi 14 functionality | Explained automatic LP selection, MIP search and newer feasibility heuristics | Section 2.5; Appendix D |
| C033 | Put technical URLs in footnotes | Used a consistent footnote command for technical and source URLs | Whole document |
| C034 | Revise negative phrasing | Replaced defensive preambles by explicit definitions and study scope | Whole document |
| C035 | Remove extensive-form shorthand | Used native planning-model and DET/STO labels | Whole document |
| C036 | Avoid repetitive forbidden-design wording | Defined an automatic reference and separately identified diagnosed treatments | Sections 2.5, 4.5; Appendix D |
| C037 | Explain MIP gap and default target | Defined the gap in percent and the 0.01% reference target | Sections 2.5, 3.6 |
| C038 | Explain quality milestones and parsing | Added Q labels, event times, callback/log reconciliation and logtools | Sections 3.6, 4.3 |
| C039 | Remove decomposition subsection | Removed the former Benders design material | Whole document |
| C040 | Explain indicator equivalence | Defined logical activation and requirements for valid bounded alternatives | Section 2.6; Appendix D |
| C041 | Remove architecture-specific design | Organised cases by agricultural policies and populations | Section 3 |
| C042 | Remove architecture-specific comparisons | Defined matched computational comparisons for the retained models | Sections 3, 5.4 |
| C043 | Show full case identification and families | Added an example identifier, policy profiles and case-count matrix | Sections 3.1–3.2 |
| C044 | State repetition design affirmatively | Specified individual repeats and descriptive temporal summaries | Sections 3.3, 5.4 |
| C045 | Introduce and explain tables and figures | Added preceding references and following interpretation to every display | Whole document; rendering QA |
| C046 | Remove decomposition state machine | Used one fresh model and a four-stage case pipeline | Section 3.3 |
| C047 | Prevent inherited solver state | Specified fresh construction and explicit state/parameter handling | Section 3.1 |
| C048 | Keep captions concise | Used descriptive captions and moved interpretation to prose | All tables and figures |
| C049 | Use research S stages | Replaced legacy G-stage labels by S0–S5 research stages | Section 6 |
| C050 | Explain order of policy and interaction studies | Specified h215 policy/capacity matrix followed by larger populations | Sections 3.2, 6 |
| C051 | Explain memory resource classes | Described the 192 GiB reference and conditional larger-memory class | Section 3.5 |
| C052 | Remove unsupported promises | Expressed budgets and resource availability as explicit planning assumptions | Sections 3.4–3.5, 6 |
| C053 | Set eight-hour native and twelve-hour wall budgets | Used TimeLimit=28800 and a 12-hour Slurm planning envelope | Section 3.4 |
| C054 | Remove decomposition memory comparison | Focused memory evidence on native construction and optimization lifecycle | Sections 3.5, 4.4 |
| C055 | Remove architecture shorthand | Used DET/STO and identified case labels consistently | Whole document |
| C056 | Explain memory lifecycle | Discussed retained objects, temporary copies and phase peaks | Sections 3.5, 4.4; Appendix D |
| C057 | Preserve the planning horizon | Retained 60 months and the approved model scope | Sections 2.1, 3 |
| C058 | Explain budgets, censoring and repeats | Added workload estimates, terminal evidence and individual repetition reporting | Sections 3.3–3.6, 5.4 |
| C059 | Introduce quality subsection in prose | Explained incumbent and bound before the gap equation | Section 3.6 |
| C060 | Use requested quality labels | Defined Q10, Q05, Q01 and Q001 | Section 3.6 |
| C061 | Handle gap edge cases | Explained zero, infinite and unavailable gaps | Section 3.6 |
| C062 | Remove architecture index from attainment time | Defined T(tau) for the identified case | Section 3.6 |
| C063 | Remove decomposition quality language | Applied the quality record to the retained native models | Sections 3.6, 5.4 |
| C064 | Explain threshold events and censoring | Covered bound-only improvement and unattained milestones | Section 3.6 |
| C065 | Describe the identified XLSX data | Explained contents, record counts, units and sources | Section 4.1; Appendices A–B |
| C066 | Explain OSRM and container deployment | Described routing service in Singularity with footnoted references | Section 4.2 |
| C067 | Clarify SQLite deployment | Confirmed the Python cache client runs outside the routing container | Section 4.2 |
| C068 | Make parameter tracing practical | Added field, cell, unit, scope and transformation explanations | Appendices A–B |
| C069 | Preserve the effective coefficients | Separated the reference from explicit experimental transformations | Sections 4.1; Appendix A |
| C070 | Explain collection of events and decisions | Defined complete vectors and trajectory records | Section 4.3 |
| C071 | Remove architecture-specific collection | Used one common identified-case evidence schema | Section 4 |
| C072 | Remove architecture-specific outputs | Defined model, execution, planning and validation evidence layers | Appendix F |
| C073 | Explain floating-point precision | Separated original effective values, round-trip exports and display rounding | Section 4.3 |
| C074 | Explain validation tolerances affirmatively | Recorded original-unit residual rules and separate native tolerances | Section 4.3; Appendix C |
| C075 | Clarify aggregate memory peaks | Used simultaneous process-tree samples and labelled memory units | Section 4.4 |
| C076 | Explain CPU, clocks and memory measures | Separated allocation, threads, busy CPU, Runtime, Work and total time | Section 4.4 |
| C077 | Use logtools as a standard component | Made offline gurobi-logtools parsing part of the analysis pipeline | Sections 4.3, 5.4 |
| C078 | Expand agricultural and frontier analysis | Added A1–A5, marginal admissibility and empirical dominance analysis | Section 5; Appendix E |
| C079 | Remove chat/mandate activation language | Kept reader-facing methodology separate from governance evidence | Whole document |
| C080 | Complete stages and schedule | Added S0–S5 activities, indicative weeks and acceptance products | Section 6 |
| C081 | Remove developer-specific PR packaging prose | Replaced by perennial research outputs and evidence layers | Appendix F |
| C082 | Rewrite baseline appendix didactically | Added narrative, sheet inventory, parameter examples and dimensions | Appendix A |
| C083 | Rewrite registry appendix didactically | Added identity, population order, network recovery and distance-state explanations | Appendix B |
| C084 | Remove decomposition qualification | Qualified neutral/transformed data and native planning constraints | Appendix C |
| C085 | Introduce qualification tables and algebra | Added conservation, operating capacities and acceptance evidence | Appendix C |
| C086 | Explain course concepts in the appendix | Developed diagnosis, equivalent representation and controlled tuning | Appendix D |
| C087 | Rewrite interpretation appendix | Explained attainable service, objective certificates and frontier scope | Appendix E |
| C088 | Make reproducibility appendix perennial | Organised evidence layers without job/PR/migration history | Appendix F |
| C089 | Include independent references section | Added thesis, review, software, course and infrastructure references | References |

## Subsequent author clarifications

- beta remains the product/scenario domestic-service floor; alpha remains the aggregate export-share ceiling. Demand scaling delta_D is independent.
- K multiplies all frozen candidate and expansion capacity ceilings once. Initial installed capacities, unit/fixed costs, handling coefficients and bulk-conversion limits remain separate.
- The 80/20 rule retains the nearest ceil(0.20 n) eligible routes per source/product group; the economic–service Pareto frontier uses complete planning outcomes and a different dominance criterion.
- The recovered connectivity policy allows warehouse hops. Its default requires each active domestic pair and at least one export sink per active product; actual frozen coverage is reported independently from that requirement.
