# Proposed article structure and prose

These are editorial working passages for S6-B/coauthor review. They do not
replace the reviewed PDF or `manuscript/index.qmd`. The numerical baseline is
the accepted scalar h215 record; the running h300 block supplies no results yet.

## Title options and contribution statement

| Candidate title | Rationale and limitation |
| --- | --- |
| Computational limits and planning outcomes of deterministic and two-stage stochastic grain-storage network models | Balances the computational contribution with the requested interpretation of decisions; limits remain specific to tested profiles |
| Constructing and validating large grain-storage network MILPs: computational evidence from deterministic and stochastic planning | Emphasizes the implemented workflow and validation; requires clear evidence of its developed methods rather than routine solver use |
| Computational scalability of grain-storage network design under deterministic and scenario-based uncertainty | Names the experimental subject concisely; scalability conclusions remain conditional until the audited size comparisons are available |

No final title is selected. Suggested contribution statement:

> Building on the grain-allocation and storage-planning formulation of Rosa
> (2026), this study implements and evaluates a computational workflow for
> deterministic and two-stage stochastic grain-storage network models. The
> workflow binds road data and selected network arcs to each experiment,
> constructs the sparse extensive form, measures its computational phases and
> independently checks exported decisions and objective components. The
> experiments characterize attainable solution quality and resource requirements
> for the declared inputs, and interpret the infrastructure and operating
> decisions returned by validated scalar solutions.

The last clause is a proposed article objective. Its results require the vector
analysis in the [results inventory](results_inventory.md). Do not turn it into
a completed finding before that analysis is accepted.

## Revised outline with section purposes

| Section | Proposed subsections | Reader's question and evidence |
| --- | --- | --- |
|1 Introduction | Agricultural context; computational challenge; research questions and contribution | Why is network investment difficult to compute and interpret? Attribute the foundation once and identify the developed computational work |
|2 Related work | Agricultural network decisions; uncertainty/information; computational methods; gap | Which assumptions and developed methods differ? Retain the complete systematic-review supplement and resolve its factual inconsistencies |
|3 Problem definition and formulation | Assumptions; notation tables; complete DET; STO; slack/units interpretation | What exactly is optimized, constrained and known at each stage? Use the complete proposed scalar block |
|4 Data and computational framework | Warehouse populations; scenarios; OSRM; sparse arcs; construction; validation | How are model inputs created, selected, frozen and checked? Include actual membership and geographic/economic provenance |
|5 Experimental methodology | Cohorts; h215 pair; h300 threads; later size/SCIP gates; hardware/budgets; metrics | What varies and what remains comparable? Distinguish allocated CPUs, solver threads, affinity and phase clocks |
|6 Computational results | Scalar qualification; DET/STO baseline; h300 contrast; later audited outcomes | What solution quality, construction time and memory were attained? Keep incomplete, censored and missing results visible |
|7 Agricultural planning outcomes | Investment; cost composition; operating patterns; regional/temporal slack | What does the validated model decide? First-stage maps and independently checked scenario-dependent diagnostics |
|8 Discussion and limitations | Computational mechanisms; agricultural meaning; numerical/physical/economic limitations | What follows from measured evidence, and what depends on data, penalties or untested conditions? |
|9 Conclusions | Answer the computational and planning questions; supported contribution; remaining limits | No generic solver winner, universal frontier or completed pending experiment |
|10 Reproducibility and data availability | Code/input/runtime identities; access rights; original evidence; supplements | What can another researcher inspect or reproduce, and what remains restricted? |

Recommended research questions:

1. How do the declared warehouse population, scenario replication and retained
   arc structure affect construction, resource demand and attainable global
   solution quality for DET and STO?
2. What strategic investments and operating patterns do validated solutions
   produce, and where do their permitted shortages and capacity exceedances
   concentrate under the chosen inputs and fixed coefficients?

These organize existing approved work. They do not add a factorial study,
scenario-calibration exercise or causal policy comparison.

## Provisional scalar abstract, using accepted h215 evidence only

> Grain-storage network planning couples infrastructure investments to grain
> movements and inventories over time. Scenario replication and directed
> interwarehouse connections can make these models expensive to construct,
> store and solve. Building on Rosa (2026), this study evaluates deterministic
> and two-stage stochastic mixed-integer models with one objective containing
> investment, operating costs and three separate feasibility penalties. The
> computational workflow combines versioned road distances, explicit sparse
> network selection, resource measurements and independent checks of exported
> solutions. In the accepted 215-warehouse baseline, the deterministic model
> uses its original data and the stochastic model uses nine equiprobable
> Cartesian supply/demand scenarios. With a four-hour limit and a1% global
> relative-gap target per model, both returned solutions accepted by the
> original independent validator. Native optimizer runtimes were approximately
>123s and2446s, with gaps of0.000812% and0.740159%, respectively. The substantial
> contribution of artificial penalties requires economic costs and physical
> shortages or capacity exceedances to be reported separately. This baseline
> establishes accepted scalar evidence for the tested inputs. Broader
> computational limits and agricultural planning patterns require the remaining
> audited experiments and analysis of their investment and operating decisions.

This is a factual working abstract for review, not the final submission abstract.
After h300/later gates and agricultural post-processing, rewrite its results
sentence to reflect the complete accepted evidence and remove planning language.
Do not combine the earlier13-attempt hierarchy with this scalar cohort.

## Ready-to-use problem and methods prose

> The model describes strategic investment and subsequent operation in a
> multi-product grain-storage network. Candidate facilities require an opening
> decision, while eligible existing facilities can receive expansion or
> bulk-handling investment. Investment variables are common across scenarios
> and their costs are charged once. Operational variables allocate each
> product through the selected directed network and carry inventory between
> planning periods. The deterministic model uses the original deterministic
> supply and demand arrays. The stochastic model uses a finite scenario set
> whose complete operating trajectory becomes available after the first-stage
> investment decision. Multiple planning periods therefore do not imply a
> multistage information structure.

> For the evaluated scalar configuration, nine scenarios combine the three
> supply and three demand multiplier levels, with weight1/9 per combination.
> These are controlled experimental weights rather than estimated frequencies.
> Physical quantities and cost coefficients retain their declared input units.
> The optimization objective is the undiscounted horizon total of investment,
> transport and handling, inventory holding and three artificial penalties.
> Its monetary unit follows the input dataset; a price year is reported only
> if the source records establish one. No annualization, inflation correction
> or discount rate is introduced by the formulation.

> Native optimization time measures the optimizer call. Data preparation,
> model construction, extraction, independent validation and artifact export
> have separate clocks. Scheduler elapsed time covers the allocation and
> orchestration. Reported memory identifies its scope, such as process RSS,
> solver-managed memory or Slurm step accounting. Solver threads, allocated
> logical CPUs and the worker's observed affinity are separate quantities.
> All current agricultural optimizations use one allocated node; scheduling
> several experiments does not constitute a distributed MILP algorithm.

> For a finite incumbent z and lower bound b in a minimization problem, the
> common relative gap is (z-b)/|z| for a nonzero incumbent and b<=z. When both
> are zero the gap is zero. The current common record stores null for a zero
> incumbent with a nonzero bound, a bound above the incumbent, or missing/nonfinite
> values. Report the solver's native
> convention separately when it differs. The configured target, attained gap,
> termination status and independent feasibility assessment accompany each
> result. A time-limited run describes attained quality at the cutoff and
> cannot supply a completed-work speedup against a finished run.

The common definition follows `src/logic/optimization.py: scalar_mip_gap`.
Gurobi's native convention, including its infinite-gap special cases, follows the
[Gurobi parameter reference](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter-MIPGap).
Rounding belongs only to display. Keep exact values and threshold classification
in the evidence data. Absolute objective uncertainty z-b can supplement the
global gap, without being represented as a bound on an individual cost component.

## Planning interpretation and penalty discussion

> A candidate included in the input is an available option, not necessarily
> an investment selected in the solution. We report its activation together
> with installed quantity and use, since a zero-cost activation can equal one
> even when the associated investment quantity is zero. Expansion and
> bulk-handling conversion are also reported separately because the latter
> increases handling capability in the daily-factor configuration rather than
> static storage. Their geography describes the model's chosen plan under
> the supplied options and coefficients.

> Shortage, stock-capacity exceedance and reception overflow relax specified
> constraints. They neither create physical capacity nor guarantee complete
> recourse when shipping, activation or connectivity remains restrictive.
> The accepted experiments retain coefficients90000,45000 and45000 on the
> corresponding units. The weights influence investment and logistics
> trade-offs and may change the search behaviour, but their effects on runtime
> need not be monotonic. We report the economic subtotal, each artificial
> penalty and physical slack quantities separately. The global gap certifies
> the penalized total and does not by itself certify full demand service,
> nominal capacity adequacy or an equally precise economic subtotal.

> Warehouse-level and period-level diagnostics identify concentrations of
> modelled pressure. Static exceedance summed across periods is expressed in
> tonne-periods. Reception overflow is a period quantity in tonnes; dividing
> by operating days gives a daily equivalent. A region's summed stock
> exceedance must not be interpreted as tonnes of additional warehouse
> infrastructure. Investment implementation still requires land, engineering,
> finance and stakeholder agreements outside the encoded model.

## Literature restructuring and terminology

Use a paragraph's scientific comparison as its organizing unit: state the
decision, uncertainty/information structure and computational method, then the
relevant distinction. The existing citations support the following proposed
clusters, subject to checking their original texts before the final rewrite:

| Cluster | Existing bibliography examples | Distinction to make explicit |
| --- | --- | --- |
| Storage location/network | Foulds2005;Mascarenhas2014;DeMorais2023;Milanez2026 | Static stock versus throughput, modal representation and capacity decisions |
| Uncertainty and recourse | Gholamian2017;Pourmohammadi2020;HosseiniMotlagh2020;Reis2023 | Strategic versus tactical first stage; scenarios versus simulation/disruption options |
| Agricultural computational methods | Shastri2011;Zhao2012;Knapen2025 | Developed solution/data methods and differences between simulation parallelism and a shared-investment MILP |
| Shared-memory methods | Silva2025;HuangfuHall2018 | Measured regions/thread configurations and the limits of inferring proprietary solver algorithms |
| Governance and broader effects | Essien2018;Filippi2022;Wang2024 | Conditions for implementation and impacts not quantified here |

This PR does not claim to have rerun a systematic literature search or verified
all literature interpretations independently. Existing detailed review and
screening anomalies remain in the supplement and decision register.

| Term | Meaning to use consistently |
| --- | --- |
| Warehouse population | Facilities included in a specified instance |
| Candidate | Available investment option, before observing an opening decision |
| Opened/activated candidate | Candidate binary selected in the solution; report quantity/use alongside it |
| Static capacity; inventory | Stock limit and the stored state, respectively, in tonnes |
| Reception/shipping capacity | Handling rates in tonnes/day, converted to period tonnes |
| Bulk-handling conversion | Handling investment with declared conversion factors |
| First/second stage | Shared strategic investment and scenario-dependent operation |
| Feasible incumbent | Returned solution accepted against the encoded constraints/tolerances |
| Best bound; global MIP gap | Solver bound and scalar objective uncertainty under a named convention |
| Slack | Permitted mathematical relaxation of a particular constraint |
| Computational scalability | Observed resource/quality changes across declared instances |
| Baseline | A named input/configuration/experiment, never an unspecified historical value |
| Historical MVP1; archived hierarchical MVP2; scalar MVP2 | Separate experimental cohorts with different contracts |

The captions can be short: Model notation; Computational design; Scalar
solution quality and resources; Investment decisions; Geographic and seasonal
capacity pressure. Put method qualifications in surrounding prose and preserve
units, sources and uncertainty labels in the corresponding visual.
