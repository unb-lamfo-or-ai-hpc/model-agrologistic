# S2: qualify threads before production screening

## Decision and scope

PR #52 merged into develop at `9d302406e2aae0958ff61084f750fa4cf1730eac`.
The [bounded S1 closure](mvp2_sprint1_closure.md) remains the evidence baseline.
This first S2 PR qualifies configuration, fresh admission and resumable transfer
on analytical Gurobi miniatures. It cannot execute any production workbook.
Large screening and automatic repeats remain closed even after acceptance.
The article, presentation, historical receipts and solver implementation are unchanged.

Two gates are intentionally distinct:

1. **This PR:** one NPAD allocation, fresh license capability, five cold-process
   analytical solves with 1/2/4/8/16 thread settings, original-unit independent
   residual validation, existing service/gap/degradation audit, terminal accounting
   and portable products. CI does not substitute for this licensed NPAD evidence.
2. **Next scoped admission/evidence PR:** recheck accepted h300 input and S1
   products, derive a bounded homogeneous production window, qualify censoring
   and resource costs, then issue an immutable production driver. No production
   executor or admission token is delivered by this PR.

This operational qualification is not a production performance experiment.
Gurobi accepting a setting does not establish actual parallel utilization,
large-model fit, determinism, speedup or scientific equality of all future runs.

## Miniature contract

The [machine-readable policy](mvp2_threads_policy.json) fixes grid 1/2/4/8/16,
execution order 4/1/8/2/16, seed 42, native stochastic three-priority hierarchy,
all-barrier per-pass Method=2, NumericFocus=1, MIPGap=0.1 and default-off compaction.
Each child is a fresh Python process with a 60-second optimization budget and
180-second process watchdog. A failure stops the remaining grid; never silently
retry an arm. There is no warm start or production rebuild.

The public analytical fixture has one origin, warehouse, customer and product,
one period and two scenarios. It uses the existing two-scenario fixture with
positive demand of 20/50 units, so service is nontrivial. Its scientific hash,
runtime/source/tool identities and exact specification are bound in the plan.
It is not a miniature reproduction of all h300 features.

SoftMemLimit=1 **decimal GB** is a miniature-only envelope. Slurm requests one
intel-256 node, one task, 16 CPUs/task, 16 **GiB** and 30 minutes. Fresh admission
requires exact standalone running scheduler records, observed memory, at least
16 accessible affinity CPUs and a finite matching-or-larger cgroup cap bounded
by captured node memory. Allocated CPUs may exceed requested CPUs; record both.
The license probe exceeds the bundled 2000-variable/constraint limit without
reading, hashing or exporting license contents. No exclusive node is claimed.

Acceptance requires five current completion markers and products, three closed
stages, accepted independent residuals, the inherited service/gap/degradation
classification and observed effective per-stage Threads/Method/time/memory/gap/
NumericFocus settings. Scheduler COMPLETED/0:0 alone is insufficient. A time
limit is not accepted for these tiny qualification instances. A partial or
failed run is preserved and collected as rejected evidence, not imputed.

One unbalanced, nonrandomized order provides no causal comparison. Different
optimal solutions within hierarchical tolerances need not be numerically
identical; do not reject valid alternatives merely for different costs/decisions.
Effective parameter receipts certify settings, not measured active thread counts.

## Proposed production window: not admitted

Prefer **h300 warehouse-only control**, not h400 direct. Accepted input job
2198085 and descriptive pair job 2199525 provide exact input identities and
successful original-profile certificates. H300 showed more resource/time headroom
than h400 direct, which used nearly its eight-hour optimization budget. This
selection is operational judgment, not a proof that difficulty is monotone.

The proposal preserves nine scenarios, sixty periods, two products, original
data/routes/hierarchy, seed 42, all-barrier, NumericFocus=1, MIPGap=0.1,
SoftMemLimit=128 decimal GB, 192 GiB allocation, compaction off and node class.
Reserve at least 16 CPUs/task for the entire block; the five arm settings alone
vary. Memory-induced allocation can exceed 16 and must be reported as cost,
not called active solver parallelism.

Propose a **common 1800-second optimization window per arm**, separately from
S1's full 28800-second certificate budget. This diagnostic budget change applies
equally to all arms, not selectively to a thread count. Native time semantics,
construction/export/validation watchdog and total Slurm headroom need separate
qualification before submission. No 24-hour budget or full-budget five-arm grid
is admitted. Initial order 4/1/8/2/16 is not balanced or randomized; a single
block would be descriptive only.

Production screening must distinguish complete accepted hierarchy, feasible
partial hierarchy, time/memory-censored observation and no incumbent/failed
execution. The miniature collector must not be reused to falsely accept
production partial results. Compare stage latency, time-to-incumbent/bound,
iterations, nodes/work, CPU seconds, sampled RSS/native memory, core-hours and
telemetry coverage. Missing events remain missing, not zero. Speedup T1/Tp and
efficiency (T1/Tp)/p require equal completed work; censored times are not ordinary
complete timings. Report scheduler cost as allocated CPUs times elapsed hours,
distinct from solver-thread-hours and measured process CPU hours.

Audit the first admitted block before choosing any full-budget positive control
or balanced repeats. No-benefit, failure or a documented no-extension decision
can close the screen; acceleration is not an exit requirement. Additional memory,
method, seed, solver and frontier changes stay separate conditional questions.

## NPAD execution and all follow-up steps

### Login-license bootstrap correction and one bounded recovery

The first attempt at `0360c25c2486daf99c223ca18f6bf80cb2af8238`, run
`mvp2-threads-s2-GXnpz4Ln`, passed raw-byte verification and all 56 Linux
focused tests, then stopped at the login-node license-file selector check.
The driver had not exported `GRB_LICENSE_FILE`; this is a bootstrap defect,
not evidence of an expired NPAD license or a solver failure. The designated
path remains `/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic`.
The fixed driver exports it on login as well as in the worker, overriding an
absent or incorrect inherited selector without reading license contents.

For this exact failed attempt only, use `recover-login FULL_FIXED_SHA`, not
`start`, from the immutable recovery runbook in the PR comment. Before a fresh
isolated bootstrap, the recovery checks the original claim/run/source, every
tracked raw HEAD byte, the original 56-test receipt and bound plan/runtime.
It requires qualification to contain only `plan.json`, no other run-level
products, no active original bootstrap/process and no active S2 queue entry.
An unavailable/ambiguous check stops; it never treats a missing job receipt as
proof that submission did not happen. Any submission marker, scheduler files,
Slurm output or execution evidence blocks recovery. No `sbatch` can be reached
through this path unless all pre-submission checks pass.

The original run and `.mvp2-threads-qualification-s2` claim remain untouched.
A separate `.mvp2-threads-qualification-s2-login-recovery` one-shot claim binds
the fixed source and fresh run. A hashed `login-recovery.json` receipt records
original identities and negative pre-submission checks, is bound into the new
plan and transfers in the allowlisted archive. This is a recovery of a failed
software bootstrap, not a repeat of an optimization. The thread/model/resource
policy is unchanged. Repeating the exact `recover-login` command collects only
its existing job; an incomplete or ambiguous recovery claim stops, never retries.
The correction remains Draft until original licensed miniature evidence is audited.

The PR comment provides the **verified immutable head SHA**, driver SHA256 and
copy-and-paste bootstrap. Do not replace that SHA with develop or a branch name.
Download `scripts/npad_mvp2_threads.sh` from that exact commit, check its SHA256,
then run `bash DRIVER start FULL_SHA` in the existing NPAD environment. Do not
install packages or change a shared checkout.

The driver isolates a new source/run, compares every tracked file against raw
HEAD blobs, runs Ruff and focused tests without failures/errors/skips, checks the
designated license path, and performs sbatch --test-only before submission.
The successful dry-run line may mention another job number; `JOB=` identifies
the real submitted job. The durable `.mvp2-threads-qualification-s2` claim is
created before bootstrap; failures preserve it for diagnosis, never automatic
deletion or resubmission. An ambiguous submission without a receipt is a stop.

Leave it running through collection, or interrupt the waiting collector with
Ctrl-C. To resume, repeat **the same driver start command and same SHA**. It
collects the existing receipt, never submits again. While waiting:

```bash
sacct -j JOB --format=JobID,State,Elapsed,ExitCode,MaxRSS
```

On terminal accounting, collection prints `COLLECTION_STATUS`, `SHA256`,
`DOWNLOAD` and `TRANSFER_CHECKSUM`. A fresh collection directory avoids replacing
any previous package. Transfer both `.tar.gz` and `.tar.gz.sha256` with MobaXterm
and attach them with the printed checksum. Failure still produces a portable
allowlisted package if the plan/source/runtime remains current; otherwise keep
the run and share the diagnostic stop, never repair historical receipts.
Only enumerated fixture JSON/CSV and scheduler/qualification receipts transfer;
no license, raw solver logs, arbitrary extra files or private workbook.

After independent archive audit, record the original NPAD source/job/checksum,
remaining limitations and exit decision on GitHub. Only then finish this PR,
confirm exact-head CI and mark Ready before asking for merge. A production
admission PR follows that gate. No manuscript, release or deposit is authorized.
