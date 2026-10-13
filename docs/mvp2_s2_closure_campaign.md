# S2 closure campaign: finite scope, staged admission

Latest evidence, 13 October: diagnostic job `2209770` is complete and independently
replayed as `observed_not_qualified`. Its claim is consumed. Shared cpuacct and a
two-CPU cpuset with reported one-CPU worker affinity require a combined policy
repair; they do not qualify normal containment. The compiler now records the
observation as an inert reference and recommends review, not another NPAD command.
See the [audit and repair criteria](mvp2_s2_scope_observation.md). The historical
budget is unchanged; a successor is not automatically included or admitted.

Prior evidence, 13 October: PR #80 merged and job `2209138` consumed the normal
slot without live qualification. Its root/batch completed but numeric step failed;
the diagnostic records a shared/nested controller predicate failure. The
[scope observation](mvp2_s2_scope_observation.md) is next: one independent
5-minute, 2-CPU, 2048-MiB observation, not a normal repeat or downstream release.
The historical A/B/D envelope below remains 7 h 12 min / 98.4 requested CPU-hours;
this separate diagnostic adds at most 5 requested allocation minutes / 1/6
requested CPU-hour, not measured usage or a revised whole-campaign budget.
The machine plan marks the normal claim collection-only. A successor normal
release, if justified by the observation, requires explicit scope and budget
reconciliation; it is not silently included in the consumed slot.

## Historical campaign baseline

Planning baseline, 13 October 2026: PR #78 merged into develop at
`b416c11a42981dbfc6a330a35d3d0bcb4f1e4652`. This campaign consolidates the
already contracted work; it does not add a new experimental gate, scheduler,
solver campaign or authorization token. It is **not yet an end-to-end runnable
campaign**. PR #79 has now merged; PR #80 reconciles this plan with the corrected
normal-only handoff. The PR #77 start stopped before submission because two
byte-identical recovery carriers existed. PR #80 retains that same normal slot
and selects the previously audited carrier explicitly, without deleting either.
Corrected terminal evidence is not supplied. All later releases remain closed.

The [machine-readable contract](mvp2_s2_closure_campaign.json) and
[read-only compiler](../scripts/plan_mvp2_s2_closure.py) check the inherited
synthetic cases, h300 policy, order and arithmetic. The compiler prints a plan
or checks it; it cannot submit, resume, signal, inspect a license, accept a receipt
or advance a gate from a supplied boolean. A plan checksum is not live evidence.

## Scientific question and fixed contrast

For the same h300 warehouse-only stochastic problem, how does configured Gurobi
Threads affect observed hierarchy progress, solution quality, time and resources
under the same diagnostic window? More threads may help, do nothing or hurt.
The outcome need not demonstrate acceleration to be scientifically useful.

Preserve [the h300 contract](mvp2_h300_thread_design.md): nine scenarios, sixty
periods, two products, no direct origin/customer arcs, no compaction or warm start,
same input/routes, native hierarchy, tolerances, seed, method, memory and runtime.
The only experimental factor is Threads. The historical core hash in the design
policy is a reference, **not** the changed worker's current identity. Native
qualification must bind the actual new source/cohort; never rewrite old receipts.

## Campaign sequence and passage criteria

| Block | Work and budget | Required entry | Exit evidence / next decision |
| --- | --- | --- | --- |
| A — Normal | Existing PR #77 one-shot claim; 2 CPUs, 2048 MiB, at most 12 min | Merged qualified driver; original predecessor preserved | Actual job/step binding, phases, terminal accounting, immutable products and independently audited cleanup/containment; integrity-only replay is insufficient |
| B — Adverse | Five distinct cases, each proposed at 2 CPUs, 2048 MiB, at most 12 min | Accepted A audit and qualified adverse release | Each expected failure and partial prefix match its case; exact-step control, descendant/quiet-period evidence and cleanup independently accepted; unknown effect stops the sequence |
| C — Native miniature | Small public analytical fixture through the actual integrated worker; envelope must be frozen in its release PR | All five B outcomes audited; fresh source/runtime/license qualification | Analytical/residual and native priority checks, real global limits/phase hooks/disposal, live sampling and portable complete/partial/no-incumbent evidence paths qualified |
| D — h300 | One node/allocation, five cold serial arms, 16 requested CPUs, 196608 MiB, at most 6 h | Accepted C audit plus fresh input/source/runtime/license/allocation/export-volume admission | Original terminal/partial evidence for each attempted arm, explicit unrun-arm list on stop; independent audit before any decision |
| E — Closure | No new jobs | D evidence audit | Complete thread-response table, quality/resource comparison, limitations and justified next-profile or inconclusive decision; S2 exit decision recorded in GitHub |

A is **not a new normal repeat**. Use the existing claim if it has already been
created. Never reinterpret a failed historical normal as one of the five B cases.
B order proposed for its single functional release: build failure, optimization
failure, export failure, disposal failure, then the nested setsid/TERM-ignoring
case. Each has its own immutable attempt/job, fixed expected outcome and terminal
collection. These are the five existing adverse cases, not extra solver runs.
The nested case retains exactly two extra processes and its 120-second cooperative
self-exit bound; that exit alone is not proof of forced scheduler cleanup.

No automatic cross-block chain or retry is authorized. Do not pre-submit a chain
of Slurm `afterok` jobs: root exit zero is not independent scientific/containment
acceptance. Offline qualification and a merged PR are also not live evidence.
The adverse release must define per-case audit/admission before proceeding, not
silently convert this campaign outline into a six-case launcher.

## The useful long allocation: block D

Use the existing order **4, 1, 8, 2, 16**, all on the same physical node and
allocation, one cold process at a time. Five separate concurrent allocations
would change the design and could introduce hardware/contention confounding.
Shared-node effects still remain even within this homogeneous block.

| Per arm | Maximum seconds |
| --- | ---: |
| Input and construction | 900 |
| One global native multiobjective optimization window | 1800 |
| Extraction, disposal and independent validation | 900 |
| Cleanup grace | 300 |
| Child watchdog total | 3900 |

Five arms consume at most 19,500 planned child seconds. Add 600 s for fresh
admission, 900 s for block audit and 600 s terminal reserve: **21,600 s = 6 h**.
Optimization windows alone sum to 9,000 s = 2.5 h, not six hours of optimization
and not 1800 s per objective. Native time limits are not external hard deadlines.
The 300-second h300 cleanup design and the separately qualified 390-second
synthetic observation window must be reconciled by the native integration gate:
do not silently import one into the other or consume terminal reserve twice.
If actual containment/teardown cannot fit the six-hour policy, stop and propose
a justified policy amendment before release; no automatic budget extension.

Before every next arm, verify the same source/runtime/input/node/affinity,
stable finite limits, no live prior child and adequate remaining headroom.
A native time/memory-censored arm may be retained and followed by the next
distinct planned arm only after clean closure and qualified evidence handling.
OOM, preemption, watchdog/signal stop, ownership/cleanup uncertainty, resource
drift, corrupt evidence or insufficient headroom stop the remaining block.
Unrun arms are not failed experiments or zero-valued solutions; no automatic retry.

## Resource forecast and its limits

- A plus all B slots: 6 x 12 min = **72 min**, 2.4 requested CPU-hours.
  This includes the existing PR #77 slot once; if already consumed, it is not
  an additional request. Prior failed diagnostic jobs are excluded.
- D: **6 h**, **96 requested CPU-hours**, 192 GiB requested memory. Actual Slurm
  allocated CPUs can exceed the request; record actual allocated cost separately.
- Known A/B/D envelopes: **7 h 12 min and 98.4 requested CPU-hours**. These are
  sequential allocation envelopes, not measured runtime, billing ceilings,
  elapsed calendar estimates or permission to reserve all slots now.
- C remains explicitly **unbudgeted and blocked**. The old job 2202239's
  30-minute/16-CPU miniature was a different gate, not a new native-worker release.
  Freeze C's fixture matrix, jobs, requested resources, phase budgets, licensed
  checks, failure injection and collection volume in the native integration PR.
- Therefore the **total campaign budget is unknown**, not 7 h 12 min. Queue,
  engineering, transfer, audit and researcher review time are additional.

## Evidence and interpretation deliverables

Every operational release must provide pinned download/start, read-only status,
terminal collect and archive/checksum transfer together, with immutable claims
and unknown-acknowledgement handling. The scheduler owns an acknowledged job;
the SSH session need not remain open. Collection must resume without submission.
Persist bounded diagnostics and partial products; keep originals at the NPAD.
Never export license contents, arbitrary environment dumps or private workbooks.

The final comparison must contain all five configured thread counts and distinguish:

- Executed versus not executed; scheduler state versus source/evidence integrity.
- Native status and positive/zero/unknown SolCount; independently validated
  incumbent versus no transferred/validated vector.
- Contiguous accepted priority prefix, stage-specific bounds/gaps, and final
  earlier-objective degradation with its actual tolerance/denominator.
- Build/optimization/extraction-validation/cleanup/application/Slurm clocks.
- Configured threads, requested/allocated CPUs, affinity/topology; measured CPU
  consumption only where counters and lifetime accounting support it.
- Application/tree RSS, cgroup charged memory, native decimal GB and Slurm MaxRSS
  separately, with GiB conversions, cadence/gaps/errors and missing values.
- Descriptive comparable-completed-work speedup/efficiency only where justified.
  Capped, incomplete or unvalidated runs are compared by quality/progress/cost;
  dividing two 1800-second caps does not demonstrate speedup of one.

For a next h400 candidate, prefer supported hierarchy/feasibility progress and
acceptable memory/closure first, then comparable quality-time-CPU cost. If results
conflict or are inconclusive, state that explicitly; do not invent a weighted score
or default to 16 threads. h300 observations do not prove transfer to direct h400.
Balanced repeats or selected full-budget attempts require separate justification;
they are not automatic requirements or automatic admissions of this first screen.

## Functional PR packages and closure

This campaign contract is preparation in parallel with A, not a new prerequisite
for the already merged PR #77. Preserve the four remaining functional boundaries
from the roadmap; do not open a PR per test fixture or per synthetic case.

| Package | Complete deliverable | Dependency and acceptance |
| --- | --- | --- |
| S2-P2 | A evidence audit plus one complete adverse driver/collector/runbook for all five cases | A accepted before live B release; T1/T2, exact-head Linux CI and Ready; separate merge/execution decision |
| S2-P3 | B audit plus native worker/sampler/partial integration and bounded licensed miniature protocol | All B cases audited; real cgroup-v1 Slurm bridge, source/cohort and cleanup-budget compatibility resolved; no inherited v2-only or process-group closure claim |
| S2-P4 | C audit plus complete h300 block driver/admission/collector | Licensed parity, fresh allocation/license/input identity, bounded export volume and homogeneous serial lifecycle qualified; one six-hour block only |
| S2-P5 | D evidence audit, comparison and S2 exit/configuration decision | All five thread observations accounted for, limitations explicit; complete diagnostic comparison or an explicit researcher decision on any interrupted/incomplete scope |

The existing controller/transport and native/partial components are reused.
Related defects, fixtures and platform corrections stay inside their functional
package. No container/runtime migration, general framework or additional solver.
T1 focused tests precede T2 related regression; run complete exact-head CI at a
stabilized head before Ready. Software qualification is not live gate acceptance.

S2 may close with a fully audited five-arm diagnostic showing no gain or censored
solver outcomes; optimal completion of every arm and positive speedup are not
requirements. A blocked normal/native gate or an unrun portion of the contracted
grid does **not** silently close full S2. Preserve it and escalate a bounded scope
or resource decision without erasing negative evidence or changing tolerances.

S2 closure does not synchronize main/develop. Final branch reconciliation stays
after article review. h400, existing SCIP/h215, conditional S5/h500, S6-A and S6-B
remain planned; S3/S4 stay cancelled and EVPI/VSS stay excluded. Retain milestones
M2 15 November, M3 23 December and submission target 31 December 2026; these are
targets, not promises. Forecast calendar completion after A/B establish installed
viability; do not trade away scientific scope to mask an operational delay.

## Executable next step now

After PR #80 is merged, use only its [pinned start/status/collect instructions](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/80#issuecomment-6146287095).
Execution source is `9c008eecb93aa4b4a221fced2fafead467d89021`, not this
planning reconciliation. Driver SHA-256 is
`3603441668908ecd7132da87b91c75da559e5e63dd68279b647f11417391c0b9`.
The manifest's merge-required label describes a prerequisite, not a live result.
If already started, collect the matching existing claim and transfer
the archive plus SHA-256. Agent audits A before the B release decision. No long
job can be admitted from the information currently supplied.

For software-only checking in a development checkout (not a required NPAD job):

```bash
python -B scripts/plan_mvp2_s2_closure.py --check
python -B scripts/plan_mvp2_s2_closure.py
```

These commands write only to stdout; no `start`, `submit`, `admit` or `repeat`
verb exists. Editing the JSON to claim success is rejected, not trusted.
