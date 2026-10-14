# S2 normal job 2210506: intact negative evidence, not containment acceptance

## Identity and independently replayed result

14 October 2026. PR #85 merged into develop at
`8a3f15084400424e07cd3367fa3a76295cc828c8`. Execution source remains
`45b4731f40b7be43880dfd04e49899a6a301f70a`; the merge tree is identical.
The transferred archive and sidecar both match SHA-256
`0239bbec7edd29cf384e7949d441ec6fb3e8474f77c735799978620fc74aa642`.
Release digest:
`69bcc4ec244dfbb2225bfd27267328cb270e430cda2dc3e3433c6b995e3b418e`.
Raw archives remain outside Git; the generated
[public review](evidence/s2_resource_normal_2210506_review.json) contains only
bounded redacted semantics and provenance, not a replacement certificate.

Independent portable replay agrees with the collected result:
`terminal_integrity_replayed_not_live_qualified`, `complete_replayed`, controller
`blocked`, all admission/cleanup flags false. Collection and repeat collection
returned the same archive checksum. The one-shot resource-normal claim is now
consumed and collection-only. Never reset it or reuse a historical claim.

## What advanced and what did not

Both kernel/resource barriers were recorded before IPC release. The observed
worker and allocation CPU IDs are `[0,32]`, initial worker affinity `[0]`, worker
memory ceiling 256 MiB and supervisor ceiling 2048 MiB. Enforcement/tracking
paths are disjoint under the approved role-aware contract; cpuacct is shared.
These are initial observations, not sustained containment or CPU exclusivity.
Worker-only CPU usage remains unavailable, not zero. The initial memory peak
counter is 49,479,680 bytes; it is not a measured full-run peak.

The worker recorded build, optimization, export and disposal in order, followed
by `synthetic_complete`. These are **stdlib synthetic phases**, not native MILP
construction, optimization or licensed scientific results. Terminal accounting
records root/batch/extern `COMPLETED 0:0` at 395 seconds and numeric step `.0`
`COMPLETED 0:0` at one rounded second. Scheduler clocks and the supervisor's
monotonic observation clock have different scopes; do not equate them.

| Supervisor-relative time | Preserved event | Interpretation |
| --- | --- | --- |
| 0.8068 s | Two barriers released IPC | Initial binding/resource gate passed |
| 0.8493 s | First observation faults; TERM exact-step intent | Launcher reaped and known PIDs absent, but membership/scope/writes unknown |
| 7.2549 s | KILL exact-step intent | Quiet cleanup could not be established |
| 391.5968 s | `preserve_blocked_attempt` | Existing 390-second cleanup deadline exhausted |

All 186 samples faulted; none contains a usable resource snapshot, accounting
observation or stable-write fingerprint. There are zero post-barrier resource
samples. `step_terminal=false` and `worker_done=false` in those samples mean
that the coupled read did not establish these facts, not that the ultimately
completed worker was necessarily still running. TERM/KILL are journaled
controller intents; they do not demonstrate forced termination of a live process.
The worker's exit alone and the absence of known PIDs do not prove descendant
scope emptiness or the required quiet period. Normal containment is not accepted.

## Cause: demonstrated coupling versus unrecorded installed exception

At the execution source, `BatchAdapter.tick()` has a single try block in this
order: launcher pump/reaping, `_members()`, resource snapshot/validation,
supervisor validation, products/write fingerprint, then accounting. An earlier
exception suppresses all later reads and marks the sample faulty. The archive
does not contain the thrown exception class, exact read stage or raw scheduler
response for those faults. No traceback/operation diagnostic identifies it.

A fake-transport regression now reproduces the first-sample signature by making
`_members()` unavailable after a fast normal exit: launcher/PID exit observations
remain positive, while membership/snapshot/accounting/products remain unknown,
TERM is requested and the controller eventually blocks. This establishes a
software observability defect and a plausible failure mechanism, **not the exact
exception in job 2210506**. Step disappearance, PID-read races or an unexpected
listpids response remain hypotheses. Cgroup deletion is not independently
demonstrated and must not be reported as the confirmed cause.

## Bounded next software gate; no retry or policy relaxation

`mvp2_s2_normal_audit.py audit` independently replays a transferred archive with
external checksum/source/job/release bindings and prints the conservative
outcome. It never connects to NPAD, submits, signals, repairs or writes evidence.
The public JSON is generated from this function; original bytes stay unchanged.

Its disconnected `observe_channels()` seam qualifies independent launcher,
membership, resource, products, accounting and PID-absence diagnostic channels.
An unavailable member channel cannot erase separately obtained accounting or
product diagnostics. Outputs contain only canonical hashes and allowlisted
error classes, never exception messages, paths or raw values. The seam itself
does not validate live inputs; future adapters must independently bound/validate
each observation. Even a successful callback is `observed_not_qualified`.
It is not imported or used by any driver, adapter or controller. Interruptions
propagate without retry. Existing sample/event/replay schemas, cleanup predicates,
worker timing, resources, commands, scientific code and historical drivers are
unchanged. Missing membership never becomes zero; a missing scope never becomes
an empty one. No positive live acceptance is retroactively manufactured.

Next owner: agent completes offline qualification/Ready review and requests
separate merge authorization for this audit/diagnostic PR. Then qualify a
bounded operational integration of the independent diagnostics and a reviewed
fast-exit observation protocol **before** proposing another normal admission.
That integration must distinguish terminal evidence from live resource/membership
evidence and preserve the strict cleanup requirement. Any necessary change to
acceptance predicates or timing requires explicit maintainer review, not a
fallback hidden in code. A future attempt requires a distinct reviewed claim,
not reuse of job 2210506. No new NPAD command is needed for this offline gate.

All adverse, native miniature, h300 and repeat execution remains blocked.
The [closure campaign](mvp2_s2_closure_campaign.md) retains its scientific scope;
normal block A has advanced through binding/worker execution but not its exit
criterion. S2 stays open. S3/S4 remain cancelled, EVPI/VSS excluded, manuscript
freeze preserved and main/develop synchronization deferred until article review.
