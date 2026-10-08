# S2 h300 thread screen: design qualification, execution closed

## Scope and immutable references

PR #53 was merged into develop at `1181eb1d03de1990f5e02d99bda0ef0a93563a47`.
Its [licensed miniatures](mvp2_thread_qualification_evidence.md) close the first
S2 gate. This next PR qualifies a **design**, not a production allocation,
license, scheduler admission, partial-solution collector or new experimental result.
No executor, Slurm script, submission command, admission token or repeat is added.
Both execution/repeat flags in [the policy](mvp2_h300_thread_policy.json) remain false.

The [solver-free contract](../scripts/mvp2_h300_thread_contract.py) validates
fixed policy/budget arithmetic, normalized hypothetical environment records,
adverse-result classification and measurement units. Its inputs are not signed
or hash-authenticated receipts. A caller-provided `accepted=true` is not evidence;
these helpers cannot validate an arbitrary archive or authorize execution.
Synthetic [regressions](../tests/test_mvp2_h300_thread_contract.py) require no license.

Reference: h300 warehouse-only **uncompacted control**, 300 hubs, nine scenarios,
sixty periods, two products, no direct origin/customer arcs, 25,107,544 variables.
Retain original workbook, routes, connectivity, model, native priority semantics
and their narrowly qualified size exception. No global guard relaxation.

| Prior evidence | Original source | Archive SHA256 / role |
| --- | --- | --- |
| Input job 2198085 | `3957f84ff49ac500eecf25b85e6b710b4b3b1010` | `97395d29b802e558d3ac88db8c8e74cf3447d165782530a9c8d7cafd59f106fb`; exact workbook/input identity |
| Descriptive pair 2199525 | `0e663c8bd8d9c5c4b27dbb09db3f1375ad52257d` | `5e52e56887dcb57b9c6209fb884129bf85cc322779fc17c2279c589519d4c1d9`; original control profile/headroom |
| Miniature job 2202239 | `04e8c0f8bd1255215f63f7592b027eac7a346b76` | `985002c13784ba071054e4c0db412cb41eefa60366f777866ce3eb3d52b586b2`; settings/lifecycle only |

Workbook SHA256 is `7761cce77cf93dcba2f617714f0117c1f2ead4de0c3f27149daceba447e0c7d1`.
Core identity is `b4de41ade0b3c55f8f20a66480cffa275421f8157444b1db3000a9eb50f2d351`.
Later review/merge commits do not replace these execution identities. Historical
acceptance does not establish current file/runtime/route/license/allocation admission.
Private archives/workbooks, original receipts and license contents are not committed.

## Homogeneous block and scientific invariants

Proposed grid: 1/2/4/8/16; initial order: 4/1/8/2/16. Five cold sequential Python
processes in **one allocation on one physical node**. No concurrent arms, warm
starts, environment mutation, package installation, formulation/seed/memory changes.
Only configured Gurobi Threads varies across arm profiles. A single fixed-order
block is descriptive, not randomized/balanced evidence of causal acceleration.

Preserve Python 3.13.15/Gurobi 13.0.3, complete dependency/runtime fingerprint,
seed 42, native service/capacity/economic hierarchy, all-pass Method=2,
NumericFocus=1, MIPGap=0.1, inherited absolute/objective tolerances, SoftMemLimit=128
**decimal GB**, compaction off and existing telemetry settings. No EVPI/VSS work.
Do not manufacture an equivalent single-objective or explicit-rebuild experiment.

Request intel-256, one node/task, 16 CPUs/task, 196608 MiB (192 GiB), six hours.
Capture job/node/partition/QoS, actual allocated logical CPUs, exact affinity IDs,
CPU model/architecture/socket/core/SMT topology, node memory, actual finite
192-GiB cgroup and native-library thread environment (OMP/MKL/OpenBLAS).
All five captures must match; record extra memory-induced allocated CPUs as cost.
Affinity ordering alone is irrelevant. No exclusive-node or load-isolation claim.
Shared-node contention remains an uncontrolled factor even on identical hardware.
Normalized design checks do not authenticate scheduler text or prove cold/serial execution.

## Diagnostic budget and watchdog design

The 1800-second TimeLimit is **global to the single native multiobjective optimize
call**, not 1800 per priority. Do not override TimeLimit in a per-pass environment.
Global parameters must precede creation of per-pass environments, which inherit
them; this matches the current core's configuration order. See
[Gurobi multiobjective environments](https://docs.gurobi.com/projects/optimizer/en/current/features/multiobjective.html#multi-objective-environments).
The solver can exceed TimeLimit during termination/attribute computations; see
[TimeLimit](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter:TimeLimit).
A separate parent watchdog and cleanup grace must handle that possibility.

| Proposed envelope | Seconds | Interpretation |
| --- | ---: | --- |
| Input/model construction | 900 | Design cap; S1 control build was 445.65 s, not a guarantee |
| Native optimization, all priorities together | 1800 | Same diagnostic window for every arm, not S1's 28800 s |
| Extraction/export/independent validation | 900 | Design cap, including disposal/validation ordering |
| Cleanup/termination grace | 300 | Capture failure/partial products; do not repair receipts |
| Child hard watchdog | 3900 | Sum of the four envelopes; a whole-child cap alone cannot enforce each phase |
| Fresh admission | 600 | Proposed block cap, not a license already granted |
| Block audit | 900 | Separate from scientific optimization clocks |
| Terminal reserve | 600 | Allow closure/collection metadata; queue delay is outside allocation elapsed |
| Slurm allocation cap | 21600 | 5 x 3900 + 600 + 900 + 600 = six hours |

Arithmetic fits the proposed cap; it does not prove live sufficiency. A future
worker must implement phase-aware deadlines and remaining-block headroom before
each cold child. Do not silently extend a deadline or relaunch a censored arm.
After a normally closed native time/memory-censored arm, retain the observation;
continuing to the next planned distinct arm requires intact allocation, no live
child, valid remaining headroom and qualified collection. This is not a repeat.
OOM, preemption, signal/watchdog kill, resource drift or corrupt evidence stops
the remaining block. Never substitute a new node or a different source mid-block.
Unrun arms remain explicitly not executed, not synthetic failed/zero observations.

## Partial observations: three separate axes

Retain evidence integrity/closure, independent incumbent feasibility, contiguous
accepted priority prefix and stopping reason separately. The pure classifier
does not recompute residuals, certify bounds or authenticate any of these fields.

| Disposition | Required interpretation |
| --- | --- |
| Complete accepted hierarchy | Closed original products, successful terminal accounting, validated incumbent, all three OPTIMAL priority certificates and accepted final degradation |
| Feasible partial hierarchy | Independently validated incumbent but incomplete/unaccepted hierarchy or closure; never promote to full lexicographic acceptance |
| Unvalidated incumbent | Solver reports a solution, but residual certificate is absent/rejected; no feasibility claim |
| No incumbent | No usable incumbent; leave service/capacity/cost fields absent, not zero |
| Execution failed | Failed process/node/accounting; preserve any separately validated incumbent without claiming execution success |
| Evidence rejected | Integrity inconsistent; no scientific acceptance even if summary flags say accepted |

Orthogonal censor reasons: native time/memory, scheduler time/memory, preemption
and cancellation. Cancellation is an administrative interruption, not natural
solver censoring. Product closure is separately reported. An absent stage is not
OPTIMAL; only a contiguous ordered certified prefix is meaningful. Partial-stage
incumbents/bounds belong to their observed stage, not a fabricated final-economic
or final-capacity certificate. OPTIMAL here means the inherited tolerances, not
an exact mathematical optimum. Near-zero service uses absolute tolerances.

The existing miniature/full-hierarchy collectors must NOT be reused as acceptance
for partial production. The core may stop/raise without full solution exports:
that is an observed limitation to preserve, not permission to invent a vector.
A future collector must distinguish historical full certificates from this
diagnostic cohort and qualify no-incumbent/partial-export behavior before admission.

## Measurement and comparison rules

Keep construction, optimize, export/validation, application and Slurm clocks
distinct. Collect per-priority latency, first observed incumbent/bound, iterations,
nodes/work and effective settings. No event means missing, not zero; time to first
callback observation is not necessarily exact time to the first solver solution.

Reserved core-hours = allocated logical CPUs x allocation elapsed / 3600.
Configured thread-hours = Threads x its declared observation interval / 3600;
it is not measured CPU use. Measured process-tree CPU-hours = valid cumulative
CPU seconds / 3600, with counter identity/reset checks and no parent/child
double counting. CPU seconds / elapsed describes average observed CPU cores,
not solver-only utilization. Do not attribute the whole batch cost to every arm.

Report application lifetime high-water RSS, sampled process-tree RSS, finite
cgroup charged memory, observed native solver decimal GB and Slurm batch MaxRSS
separately. GiB = bytes/2^30; native GB = bytes/10^9. No substitution of scopes.
Record cadence/max gap, dropped rows/errors and phase coverage. Sparse samples
do not establish continuous phase peaks or causal telemetry overhead.

Speedup T1/Tp and efficiency (T1/Tp)/p are permitted only as **descriptive**
ratios for comparable completed, accepted work with identical work-scope and
environment identities. Work scope excludes Threads/run paths but includes
input/model/quality targets and common budget; it is not equality of algorithmic
iterations or a demand for identical decision vectors. Partial/censored or
unvalidated timings have no ordinary speedup ratio. Compare their observed stage,
bound/incumbent quality and resource cost at the common window instead. Do not
divide two capped 1800-second observations and report speedup=1.

## Exit criteria and next authority boundary

This design PR exits after fixed-policy/unit/adverse-record regressions, exact-head
CI, reviewed GitHub diff, Ready status and separately authorized merge. No NPAD
CLI is needed. It does not complete S2 or satisfy live production admission.

Next, a separate implementation/admission PR must bind and reverify original
input/S1/miniature archives, workbook, manifest/spec/routes/size review, raw source,
runtime/tool identities, fresh on-node license and scheduler/cgroup observations.
It must implement one-shot immutable claims, cold serial execution, phase/block
watchdogs, no-incumbent/partial handling and portable allowlisted collection with
per-product hashes; qualify the lifecycle using synthetic failures and licensed
small controls before requesting one bounded h300 block. A future runbook will
include start/resume/terminal collection/transfer together. No current start command.

After that block's audit, choose closure/no-benefit/no-extension or separately
justify a full-budget control/balanced repeats. Acceleration is not an exit
requirement. Alternative solvers/frontier expansion remain conditional; Benders
is future work, not implementation. Article/presentation and EVPI/VSS exclusion
remain S6. Original runs/claims/receipts stay preserved.
