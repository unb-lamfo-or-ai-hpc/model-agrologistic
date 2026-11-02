# Proposed Gurobi–HiGHS campaign and staged publication
Date: 31 October 2026 (America/Fortaleza).
Status: scientific/operational proposal only. No execution code changed, no new claim/start, scheduler action or merge. The researcher requests evaluation before bibliographic reconciliation continues. This document supersedes the prior “no future campaign” planning assumption only as a proposal; it does not upgrade consumed claims.

## 1. Publication scope and h215 coverage

Focusing the article on Gurobi and HiGHS is a defensible scope choice. Remove SCIP performance tables/discussion and current generated-supplement solver-result prose in a subsequent bounded editorial change; retain its complete original successes/failures, source, packages and exclusion rationale in technical GitHub records. Do not delete original Appendix A or rewrite archived evidence. Reader claims must concern the two studied solvers, not commercial/open-source classes generally. The repository can retain the complete campaign history without naming every excluded implementation in the article.

Current accepted h215 coverage, one original observation per displayed implementation/case:
| h215 configuration | Gurobi / native gurobipy | HiGHS / Pyomo APPSI |
| --- | --- | --- |
| W DET | available, 4 threads | not executed in the audited cohort |
| W STO | available, 4 threads | available, 4 threads |
| D DET | available, 4 threads | not executed in the audited cohort |
| D STO | available, 4 threads | not executed in the audited cohort |

There is an additional accepted common-Pyomo Gurobi W/STO observation, separate from the native cohort. Completing the four-cell HiGHS descriptive panel needs THREE new case observations, not a repeat of its consumed W/STO claim. Thus a completely new 90-run larger-population grid plus these three is 93 population solves, before any additional qualification-only attempts. h215 remains descriptive n=1; it cannot supply the new grid's three replications. If requiring the entire h215 panel to use common-Pyomo Gurobi too, three additional Gurobi cases would be needed; do not silently add them.

The proposal does not yet remove reader text; manuscript edits must be reconciled with the final protocol in the next bounded increment.

## 2. Historical larger-population coverage

| Network | Native Gurobi accepted thread settings | Repetitions per existing setting | HiGHS accepted |
| --- | --- | --- | --- |
| h300 W STO | 1, 2, 4, 8, 16 | 1 | none |
| h400 W STO | 1 only | 1 | none |
| h500 W STO | 1 only | 1 | none |

Original input receipts register seed42, relative gap0.01 and native TimeLimit14400s for ALL seven existing h300/h400/h500 observations. Some archive names refer to eight-hour operational packages; those names are not native time-limit evidence. All returned early after satisfying quality, but the new 28800s protocol still needs a distinct cohort. Their identities must never be relabeled as new 8h replications. Keep them as historical references. Do not automatically reduce the new grid from90 to83 by pooling old runs from different dates/protocols.

## 3. Solver versus implementation comparison

Preferred primary grid: the same Pyomo extensive form and bounded_scalar_slacks_v1 for both Gurobi/APPSI and HiGHS/APPSI. Check exact per-network workbook hashes, ordered warehouse IDs, selected directed network, scenarios, coefficient/penalty/units contract, bounded-slack proof and ordered linear matrix identity for both engines. Exact scenario/network equality is required within a population, not across differently screened populations.

Native gurobipy remains a useful supplementary reference. The historical native formulation uses general/indicator constraints whereas the common Pyomo formulation uses proved bounded linear representatives. Mathematical projection/optimal scalar-value equivalence does not make the internal full regions, presolve representation or solver search identical. Comparing these two existing native/Pyomo pipelines is valid as an end-to-end IMPLEMENTATION comparison, not an isolated estimate of solver-engine effects. Equal mathematical optima alone do not remove this confounder.

Alternative if the researcher prefers to retain gurobipy as the primary Gurobi route: explicitly title the estimand implementation/pipeline performance, preserve both representations and report construction, transfer, native optimization, extraction and full elapsed time separately. Another possible future native linear-matrix adapter could remove that formulation difference, but it requires new implementation/qualification; it is not assumed to exist.

## 4. HiGHS threads and exact-version behavior

The v1.15.1 option definition accepts a nonnegative threads setting up to its integer bound;16 is supported as a configured maximum. Existing NPAD binary behavior at16 and physical CPU affinity still require a small public compute qualification. Acceptance of an option is not proof of actual16-core activity.

The exact v1.15.1 parallelism documentation requires parallel="on" for multithreaded MIP tree exploration. The old h215 observation retained four threads but logged parallel search off / one maximum worker. Therefore a meaningful prospective thread study should preregister parallel="on" at ALL five levels (including1), retain one fresh OS process per run, and record effective parallel/thread/LP/worker settings and phase-specific CPU activity. The current adapter does NOT yet expose arbitrary HiGHS options: its allowlist rejects extras. A prospective PR must qualify this explicit option and introspection rather than quietly insert it or reuse old acceptance.

Version1.15 also explicitly disables parallel simplex inside MIP LP relaxations. Additional MIP search workers cannot guarantee acceleration when a large root relaxation dominates. Do not change LP algorithms by population to force speedup. Keep16 as a legitimate sensitivity level, but distinguish a thread ceiling, actual worker activity and achieved speedup. HiGHS documents memory bandwidth as a common limitation and does not promise benefit above8.

Primary native sources:
- [v1.15.1 option definitions](https://github.com/ERGO-Code/HiGHS/blob/v1.15.1/highs/lp_data/HighsOptions.h)
- [v1.15.1 parallelism](https://github.com/ERGO-Code/HiGHS/blob/v1.15.1/docs/src/parallel.md)
- [v1.15.1 release notes, parallel MIP and MIP LP behavior](https://github.com/ERGO-Code/HiGHS/releases/tag/v1.15.1)

## 5. Prospective settings and resource admission

Freeze30cells =2solvers ×3populations ×5thread ceilings, with3fresh process repetitions in each cell. Fixed model seed42; 8h native scalar budget; initial common quality target1%; original independent primal validation/tolerances; fixed versions/input/source; no warm start, predecessor incumbent import, automatic retry, fallback or extension beyond the admitted budget. Keep Gurobi automatic algorithm settings with explicit resource/seed/gap/feasibility overrides. Record actual defaults, not an inaccurate “all defaults” label. HiGHS parallel="on" is an explicit prospective override, not its historical profile.

The current h215 driver admits at most16million Pyomo variables and binds a single h215W/four-thread profile. It cannot be reused by changing only a workbook path. Historical native dimensions are about25.1million variables at h300,42.1million at h400 and63.4million at h500; the common-Pyomo counts need new estimation/identity checks. Historical h500 native sampled application peak is about111.8GiB at ONE thread. This does not qualify HiGHS/Pyomo or16threads in192GiB. Do not extrapolate memory linearly as an admission proof.

Before large rollout:
1. Public tiny-model option/version/license tests, including each HiGHS thread ceiling and parameter readback in fresh processes; no private solve in login.
2. Exact input/route/scenario/penalty estimate and qualified per-instance variable guard.
3. Memory/construction/transfer pilots, starting at h300 and qualifying h400/h500 before bulk release. A pilot may count toward the90 ONLY if its exact final source/protocol/hardware/stopping settings are unchanged; otherwise retain it separately and disclose extra attempts.
4. Choose an adequate node/memory class from observations, potentially512GiB if available/needed. Match both solvers within population and account for hardware changes across populations. Do not silently lower size, routes, scenarios or tolerances to fit.
5. Use the same declared CPU allocation/affinity and memory budget across thread settings, preferably mapped physical cores with SMT/NUMA documented. If only logical CPUs are controlled, label them accordingly. One measured run per node at a time; concurrent campaign lanes use different nodes. Qualify multi-job license capability if concurrent Gurobi solves are proposed; never expose license contents.

Eight native hours exclude Python model construction, matrix fingerprinting, transfer, extraction, validation and export. A provisional12h Slurm envelope provides4h for those phases, subject to pilot measurement. An unsuccessful native solve and an operational/license/OOM/preemption failure have distinct outcomes.

## 6. Repetitions and statistical interpretation

Three runs with seed42 are valid temporal/execution repetitions conditional on a fixed seed. They do not sample the distribution of algorithmic randomness, create three distinct initial solutions or guarantee repeated identical incumbents. Gurobi's default Seed is0;42 is an explicit perturbation setting. Its TimeLimit is not a deterministic-work stopping rule. Keep the requested common elapsed-time budget rather than substituting Gurobi WorkLimit (not a common cross-solver quantity).

Use independently started processes and freeze deterministic input/row/column ordering. Vary neither seeds nor settings between the three runs. Preregister a separate schedule-randomization seed, unrelated to solver seed42, and randomize/balance solver/thread order within population/repetition blocks. Spread repetitions over distinct job/day blocks; do not execute all Gurobi first and all HiGHS later, or place every repetition in one uninterrupted temporal block. Record node, CPU model/affinity, SMT/NUMA, versions, allocation, dates, per-phase CPU/RSS and interruptions.

Primary outcomes: valid solution reaching the common1% criterion, native solve-to-return time under that stopping rule, full application time, attained common gap/objective/bound and validation. If progress telemetry supports it, also report time to first incumbent and first logged common-quality target. Preserve quality overshoot: a solver returning0.0002% has exceeded a1% target, rather than produced the same exact attained precision as0.74%. A common target supports a practical threshold comparison; it does not imply equal attained gaps.

For each cell report all three observations, median, range and variability; intervals must disclose very small n. Use paired/block-aware contrasts and within-solver thread speedup relative to1thread. Do not treat all90 observations as90 independent benchmark instances; there are only THREE population/network instances, with shared data/structure. Inference about arbitrary agricultural MILPs would be unsupported. With seed fixed, distinguish system/execution variability from an unmeasured seed effect. Stronger algorithmic-randomness claims would require a separately agreed multi-seed design.

Native time limits without target are censored observations for time-to-target, not exact8h completions. Do not drop them from averages of successful runs or substitute arbitrary giant runtimes; report success fractions, terminal gaps and appropriately censored/descriptive comparisons. Memory/operational/preemption failures remain separately classified. Never use missing objective/gap as zero.

[Gurobi parameter reference](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#seed) explains the seed perturbation; its [WorkLimit reference](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#worklimit) distinguishes deterministic work from elapsed-time stopping.

## 7. Scheduling and budget

The90-run native budget is at most720aggregate native hours. If ALL90 reach8h, that alone consumes30days in one serial lane; setup/export/queue time then exceeds that horizon. It is a worst-budget scenario, not a prediction or unconditional lower bound: successful early returns can make actual time much shorter.

| Scheduling scenario | Budget if all run envelopes are consumed, excluding queue |
| --- | --- |
| One serial lane, native time only |30days|
| One serial lane,12h total application envelope |45days|
| Two independent lanes,12h total envelope |22.5days|

Thirty calendar days is therefore a target conditional on measured early-return/overhead, concurrency and queue availability, not a guaranteed deadline. Adding the three missing h215 HiGHS observations adds up to24native hours, separately budgeted. Fixed16allocated logical CPUs ×90 ×12h would request up to17280allocated CPU-hours; configured solver thread-hours and actual CPU consumption are different metrics.

Preferred orchestration: one run per job/array task, a provisional12h envelope and a campaign-wide concurrency cap of2, subject to NPAD admission. Each task has independent source/plan/config/repetition/claim/terminal/collection identities and exits after that run. A single array can enforce a cap when resource requests are common; different arrays do not share a global cap automatically. CPU/memory classes must be designed accordingly.

The researcher's48h maximum is a scheduling constraint to confirm for the actual partition/QoS/account, not a reason to pack6×8h solves into48h. That would leave no time for construction or exports. If long serial containers are preferred, use a pilot-qualified whole-run budget and leave an explicit reserve; an illustrative conservative alternative is3runs with up to12h envelopes inside a48h container. A short-job array gives clearer accounting and smaller preemption scope. Separate dependent jobs do not reserve the next node or eliminate queue delays.

Slurm's official [job-array documentation](https://slurm.schedmd.com/job_array.html) supports capped task concurrency. Exact NPAD limits, queue concurrency, preemption/requeue and memory policies still need manual NPAD inventory during operational preparation. No schedule, array or job is submitted by this plan.

## 8. PR and Sprint sequence

- **Current S6-A/X3 and PR142:** reconcile the completed old campaign, preserve originals and keep historical native comparisons separately identified.
- **PR144 reader scope:** implement the approved two-solver focus in a bounded follow-up, retain article/appendix investments and final h215 coverage labels, complete B3/D2 and the corrected maps/AppendixE. Do not claim missing observations exist.
- **New protocol/operational PR (number unassigned):** freeze estimand, matrix/representation choice, parameter/parallel/seed policy,30cells/90runs, block schedule, resources, individual immutable claims and collection/statistics formats. Qualify new variable/resource limits, options and failure paths on public controls and manual NPAD pilots. Its own explicit merge precedes pinned human launches.
- **Rollout:** release only qualified new cells, preserve pilot eligibility criteria and cap concurrent jobs. Complete the three missing h215 HiGHS cases in a separately identified descriptive subcampaign if that panel is retained. No old start is reused.
- **S6-B in parallel after launch:** finish bibliographic reconciliation, reader math/units/data access and outstanding author decisions; generate updated local Quarto article AND appendix PDFs and present both in Codex tabs. Do not wait for all30days of the new campaign to do editorial work.
- **Intermediate develop/main publication PR:** reconcile PR142/144 with newer develop/PR145, qualify actual sources/links/builds, request each merge separately and publish current completed evidence through Quarto/Pages. Date the results cutoff; describe the new campaign only as preregistered/underway, with actual submitted counts/status. Do not fabricate an executed count before scheduler receipts or present pending statistical results. A Pages working manuscript is not journal acceptance/submission.
- **Final campaign consolidation PR:** audit all terminal packages, report completed/censored/operational outcomes under the frozen policy, produce configuration/outcome/statistical tables and update article/appendices/results cutoff, followed by separately approved integration. Intermediate publication is not automatic closure of all MVP2 work.

The protocol and future source/claim admission are still to be qualified. No new run, automatic retry, merge or publication has occurred.
