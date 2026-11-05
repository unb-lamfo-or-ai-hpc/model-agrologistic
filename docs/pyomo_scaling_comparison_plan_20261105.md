# Analysis plan for the completed common-Pyomo campaign

This plan records the agreed analysis for PR #148. It applies to the existing
Gurobi and HiGHS W STO runs for h300, h400 and h500, at thread ceilings of
1, 2, 4, 8 and 16, with three temporal repetitions at seed 42. The nominal
native allowance is eight hours and the common relative-gap target is 1%.
The planned comparison uses all 90 scientific cell identities, with outcome
and evidence coverage reported separately. Historical native runs and h215
remain in their own cohorts. [Campaign schedule](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/334827d5e3669b4fcdf2801fd4cea466e5a71d06/experiments/pyomo_scaling_serial_schedule_v1.json)

## Assemble the evidence

1. Begin with the existing `control:final-tables` outputs under
   `jobs/control__final-tables/`. Verify the SHA-256 entries in
   `final_result.json` against `tables/configurations.csv` and
   `tables/results.csv`. Join one-to-one by cell ID and reconcile the
   90 planned cells and 30 solver–population–thread combinations with the
   schedule. The 93 new scheduler jobs include control jobs. The four reused
   h300 pilots each count once in the scientific grid.
2. Reconcile each available scientific row with its original collection
   receipt, archive hash and validation record. Retain the input, matrix,
   bounds, hardware class, worker affinity, effective options and runtime
   identities needed for each comparison. Use the official records in place
   of preliminary readback values while preserving the dated preview as
   evidence of what was available at that point. Review discrepancies before
   using the affected row.
3. If final consolidation is incomplete, reconcile the existing stage and
   cell receipts against the same grid and report the coverage explicitly.
   Keep unexecuted, uncollected and unresolved cells visible. Carry forward
   the controller's original statuses and missing fields.

Record scheduler state, native termination, availability of a validated
incumbent and target attainment as separate fields. A reported success at
the common target requires the accepted original validation, a finite
incumbent and bound, and a common gap at or below 0.01. A time limit may
return a validated incumbent above the target or no usable incumbent.
A time-limited observation without an attained target is right-censored
at its recorded observation time. Operational failures and never-started
cells have distinct statuses. Retain missing objective, gap and timing
fields as missing. Report the nominal allowance and measured runtime
separately. [Consolidation logic and output fields](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/334827d5e3669b4fcdf2801fd4cea466e5a71d06/scripts/pyomo_serial_queue.py)

## Comparison rules

| Question | What stays fixed | What is reported |
| --- | --- | --- |
| Problem-size scale-up | Solver, thread ceiling, protocol and comparable hardware class | Across h300, h400 and h500, report admissible arcs and model dimensions alongside construction, native and application times, memory and achieved quality. The selected graph changes with population. Interpret differences across the studied instances. |
| Strong scaling | Population, effective instance, solver, execution profile and quality criterion | Compare the response to the thread ceiling on the fixed model. Check worker affinity and SMT scope separately from the root allocation. Changes in internal solver work may contribute to observed time differences. |
| Speedup and efficiency | The same strong-scaling comparison, with a one-thread baseline and one timing definition | Use `S(p) = median(T(1)) / median(T(p))` and `E(p) = S(p) / p`. Here `p` is the configured thread ceiling, so `E(p)` is normalized by that setting. Report native and end-to-end ratios separately. |
| Gurobi versus HiGHS | Population, matched effective algebra, thread ceiling, hardware scope and quality criterion | Compare validated target attainment first, then attained gaps and measured times for comparable outcomes. A between-solver ratio describes relative time under the stated protocol. |
| Weak scaling | Approximately constant work per computational resource as both problem and resources increase | The present grid supports a problem-size × thread comparison. Admissible arcs or matrix nonzeros per thread are structural descriptors. Use the term “problem-size and resource scaling” for these results. |

The worker has an affinity pool of 16 logical CPUs, and the scientific jobs
request an exclusive node. Report the observed Slurm allocation and affinity
from the receipts. A thread ceiling describes a solver setting. Utilization
of physical cores would require measurements of active CPU time and mapping
of logical CPUs to cores and SMT siblings. Sampled worker-tree peak RSS and
Slurm step MaxRSS are distinct measures. Record their scopes and use matching
measures when comparing memory.

## Timing and censored outcomes

- Inspect the retained logs for a time-stamped incumbent and bound supporting
  a consistent first crossing of the common gap target. If available for both
  sides, report the **logged time to the target** and the independently
  validated final outcome separately. The original validation applies to
  the returned plan.
- Otherwise use **time to termination under the common policy**, with native
  termination, final gap and validation stated beside it. Time-limited runs
  stay in the outcome table and supply censoring information for time to
  target. Native and application clocks answer different questions. Preserve
  available construction, transfer, optimization and export timings from
  the original receipts without inferring a phase from overlapping clocks.
- Present individual repetition values, the eligible sample size, median
  and range. The headline time ratios require three comparable successful
  observations on each side with equivalent timing and stopping criteria.
  Where coverage is incomplete or censoring is present, report the
  individual times, counts and outcome distribution. This is a reporting
  rule for the ratios. Valid recorded outcomes stay in the evidence table.
  Fixed-seed temporal repetitions describe the tested protocol's
  variability. Avoid treating them as independent problem instances.

## Final tables and manuscript placement

| Output | Rows and fields | Destination |
| --- | --- | --- |
| Cell ledger | 90 planned IDs with settings, provenance, scheduler and solver state, validation, objective, bound, gap, clocks and memory | Repository evidence |
| Outcome coverage | 30 settings with planned, collected, validated at target, validated above target, censored without incumbent, operational failure and unavailable counts. Use separate termination and validation columns in the ledger for overlapping states. | Appendix C |
| Size and resource comparison | Fixed solver/thread groups across the three populations, with variables, constraints, nonzeros, native and end-to-end time, measured peak scope and attainment | Results and Appendix C |
| Strong-scaling and solver comparison | Individual outcomes by repetition, eligible sample counts, native and application median/range, speedup and efficiency where supported, and same-setting solver contrasts | Results and Appendix C |

The article can then interpret solution attainability, the resource cost of
larger screened instances and the observed effect of thread settings. Report
any incomplete population coverage where it limits the comparison. Replace
the preliminary table only after reconciling the final evidence, retaining
its dated source in the repository. The approved campaign is the scope of
this plan. A classical weak-scaling design or physical-core utilization study
would be a separate scientific question.
