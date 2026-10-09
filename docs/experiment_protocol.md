# Experimental protocol: portable summary

Snapshot: 9 October 2026. This document summarizes the
[mathematical contract](v020_mathematical_contract.md),
[S1 ledger](mvp2_sprint1_closure.md), [S2 design](mvp2_h300_thread_design.md)
and [operational protocol](mvp2_s2_operational_protocol.md). The exact approved
manifest, source/runtime identities and per-gate receipt govern each execution.
It is not a runnable campaign or permission to submit/repeat a job.

## Accepted S1 reference and invariants

- Deterministic/stochastic formulations have distinct purposes. The large S1
  study uses the stochastic native hierarchy, nine scenarios, sixty periods,
  two products and preserved scenario probabilities/input identities.
- Hold workbook hashes, nested warehouse populations, route grouping/repairs,
  units, balance/activation constraints, terminal inventory and validation fixed.
  h300 warehouse-only and h400 direct-enabled are different network policies;
  their difference is not attributable solely to population.
- The accepted S1 stack records Python 3.13.15 and Gurobi 13.0.3, `Threads=4`,
  `Seed=42`, `Method=2`, `NumericFocus=1`, `MIPGap=0.1`, `SoftMemLimit=128`
  decimal GB and a 28,800-second optimization budget. These are receipts, not
  permission to replace older runtimes or silently apply them to every experiment.
- Priorities are service, emergency-capacity violation score, economic cost.
  Preserve objective tolerances and native multiobjective behavior. Inherited
  MIP-gap allowance can degrade an earlier objective in the final solution even
  with zero objective relative tolerance. A tiny intermediate gap is not the
  final-capacity gap. Near-zero service requires its absolute-tolerance rule.
- Keep original-unit independent feasibility checks and complete hierarchy
  certificates separate. Emergency slacks are not installed capacity; aggregate
  violation scores and penalty shares are not actual financial performance.
- Preserve source/environment, requested/allocated resources, cold-start policy,
  method and order. A common seed alone does not establish determinism. Do not
  mix compaction, thread, memory, LP-method or formulation changes in one contrast.

## S2 proposal remains conditional

The proposed production reference is h300 warehouse-only, uncompacted control,
with a common 1,800-second diagnostic optimization window and 1/2/4/8/16 threads.
The fixed environment requires a homogeneous node/runtime profile and at least
16 CPUs/task, checked against actual allocation. Stage/global watchdog budgets,
partial export and cleanup remain explicit. Historical four-thread S1 allocation
receipts cannot substitute for fresh S2 resource/containment proof.

Accepted five miniature observations qualify their own gate only. The current
numeric-Slurm-step approach must demonstrate installed command grammar,
race-safe binding, exact ownership, enforced finite limits, teardown/reaping and
no late writes on the actual environment. Declared Slurm configuration, injected
transports, process groups or successful CI alone cannot prove this. See the
[step gate](mvp2_s2_slurm_step_gate.md),
[adapter](mvp2_s2_batch_adapter.md) and operational protocol above.

Read-only envelope observation is distinct from a synthetic exercise and requires
no new solver/license use. Licensed miniatures and any large block subsequently
require their own fresh license and allocation admission. All synthetic/native
miniature/h300/repeat execution remains closed pending its separately reviewed gate.

## Admission, collection and acceptance

1. Define one scoped hypothesis, exact input/model/reference and success/partial/
   failure criteria. Qualify the proposed source and software regressions first.
2. Bind source bytes/SHA, manifest and runtime receipts. Verify fresh resources,
   containment and license where relevant, without publishing private credentials.
3. Use the reviewed one-shot claim and explicit human-executed CLI only after
   admission. No duplicate submission, opportunistic retry or old-claim reuse.
4. Preserve terminal accounting plus partial/adverse artifacts. Scheduler
   `COMPLETED/0:0` means the batch ended successfully, not scientific acceptance.
5. Transfer only the bounded safe archive and checksum. Verify SHA-256, member
   safety/completeness, source/runtime binding and original scientific decisions.
   Portable replay is not a fresh private-workbook reload or fresh residual audit.
6. Record accepted, rejected, partial or blocked outcomes and missing evidence.
   Decide the next gate separately; collection never admits a repeat.

Recover from interrupted collection by the same documented collector, not by
resubmission. A pre-probe regression failure may have no scientific archive;
retain test/location/phase receipts rather than fabricating one. Preserve
original rejected archives even if a later bounded evidence review is accepted.

## How to read the measurements

| Metric | Meaning and interpretation |
| --- | --- |
| Incumbent | Best feasible solution known at that stage; independently validate original-unit residuals |
| Bound and MIP gap | Solver's stage-specific quality information; use recorded objective sense and denominator, and report absolute treatment near zero |
| Final earlier-objective quality | Report final value, retained bound and allowed degradation separately from the pass certificate; state the denominator for relative differences |
| Construction/optimization/extraction/validation | Separate phase clocks; application wall time and scheduler elapsed time include different work/headroom |
| RSS | Resident application/process memory; report process scope, peak cadence and GiB units, including missed samples |
| Native solver memory | Solver-reported memory, distinct from Python/application RSS and construction peak |
| Slurm/cgroup memory | Accounting/enforcement with their own scopes/units; missing MaxRSS is not zero consumption |
| CPUs and threads | Requested CPUs, allocated CPUs, solver threads and measured active CPU use are separate quantities |
| Speedup/efficiency | For comparable completed work, `T1/Tp` and `(T1/Tp)/p`; censored diagnostic timings are not ordinary speedups |
| Core-hours | State whether allocated CPU-hours or measured CPU consumption is used; neither alone proves useful parallel work |

SoftMemLimit uses decimal GB; allocation and reported RSS may use binary GiB or
Slurm K units. State conversions. Do not turn a lower sampled peak into a smaller
safe allocation claim. Shared-node/order effects and sparse telemetry constrain
causal interpretation. With partial runs, compare stage progress, time-to-bound/
incumbent and resources without imputing missing final service, cost or capacity.

Bounded SCIP h215 and S5/h500 require later reviewed protocols; no automatic
parameter sweep, larger budget, new solver or globally relaxed size guard.
EVPI/VSS are not part of the remaining experiment plan. See the
[roadmap](mvp2_hpc_roadmap.md) and [measurement dictionary](artifact_dictionary.md).
