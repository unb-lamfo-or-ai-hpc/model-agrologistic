# S2 normal resource integration — closed operational qualification

## Authority and base

PR #82 was explicitly authorized and merged into develop at
`656537428c5edd8702aff1ed1b865a604b117792` on 13 October 2026, after all six
checks passed. The maintainer requested integration and qualification in the
normal launcher while keeping execution blocked and all prior claims/evidence
unchanged. This document is not an execution authorization or a new certificate.

The [approved resource contract](mvp2_s2_synthetic_resource_contract.md) remains
exact: allocation 2 logical CPUs / 2048 MiB / 720 seconds; worker scheduler
request 1 CPU / 256 MiB; hard worker cpuset at most 2 logical CPUs, all inside
the same allocation; initial affinity exactly 1 CPU. Startup, exercise, grace,
cleanup and quiet budgets remain 30/60/5/390/5 seconds. No SMT configuration
experiment, scientific h300 adjustment, native worker or solver change is added.

## Integrated path

`mvp2_s2_resource_normal.ResourceNormalAdapter` extends the existing normal
compute adapter rather than reproducing its scheduler protocol. Five narrowly
scoped virtual seams in `BatchAdapter` retain strict legacy defaults: barrier,
controller, release digest, event verification and snapshot validation. Old
drivers select none of the new implementation; their receipt semantics stay
unchanged. No global monkeypatch or permissive legacy archive dispatch exists.

The integrated sequence is:

1. Inherited source/runtime and allocation checks, numeric-step binding, Unix
   peer credentials, executable hashes and member identity checks stay in place.
2. Read exact cpuset CPU IDs using no-follow bounded descriptor reads. Resolve
   the exact `job_<job_id>` ancestor of both worker and supervisor, verify
   ancestry, pin all intervening directory identities and reread memberships.
   Unexpected topology blocks rather than guesses an allocation from affinity.
3. Read initial worker affinity between independent process birth/membership
   checks. Require one CPU inside the worker cpuset. Pair it with separately
   read supervisor and worker cgroup snapshots. Validate disjoint enforcement
   scopes, finite inherited memory limits and shared/disjoint accounting.
4. Bind two independent observations to the v2 resource contract before the
   inherited IPC release. Its digest now explicitly identifies the v2 contract.
   The old `contract.json` remains only the unchanged workload/phase descriptor;
   `resource-contract.json`, new barrier receipts and controller events describe
   containment. New attempt schemas cannot be read as legacy successful attempts.
5. Recheck CPU memberships/inodes, memory ceilings, supervisor scopes and
   monotonic counters at every sample. Preserve initial affinity as an initial
   fact, not a lifetime one-CPU claim. After exit, zero members are allowed only
   at sampling: no synthetic live leader or one-member snapshot is fabricated.
6. Reuse the unchanged parent-clock cleanup automaton and exact numeric-step
   TERM/KILL protocol. Resource faults drive a bounded stop. Missing scopes are
   unknown/fault, not empty scopes or proof of cleanup. Candidate closure still
   needs terminal step, absent known PIDs, reaped local client and quiet samples.
7. Preserve separate versioned resource events and attempt evidence. Independent
   replay recomputes resource bindings, event chain and cleanup state. It checks
   positive lifecycle samples against resource samples, runtime/source identity,
   unchanged profile and all non-admission flags. Collection verifies immutable
   journal records and writes only an exclusive derived destination.

CPU time is exported as `cpuacct_scope_usage_ns`; worker-only CPU usage is
`null`, never zero or supervisor-subtracted. Raw resource paths/process status
are not exported. Redacted hashes permit integrity replay, not kernel attestation.

## Negative/partial evidence and remaining release boundary

Unbound, one-observation, faulted and cleanup-timeout attempts are representable
and remain negative. A process interruption before the final carrier is written
cannot be reconstructed as complete evidence: collection fails without changing
any original file. A future operational collector must provide a bounded
forensic carrier for that missing/truncated-final-carrier case and bind terminal
scheduler accounting. This software carrier deliberately does not assert that
accounting was queried or a live job was independently accepted.

Both the module entry point and `ResourceNormalAdapter.launch()` deny before
effects. No new shell driver, claim reservation, sbatch route or CLI admission
is provided. Tests explicitly invoke inherited components with fake transports
to qualify the full handshake/sample/stop/replay path. Such fixture success is
not live containment qualification. Linux CI additionally exercises no-follow
filesystem reads; it does not launch Slurm, a synthetic process tree or a solver.

The next bounded release gate must connect this qualified adapter to a fresh,
immutable normal-only source/runtime release and a new one-shot claim; bind the
worker entry and final accounting/forensic collection; retain preserved negative
predecessors; then qualify the pinned driver before a separate execution decision.
Do not reuse or rerun any historical claim. Merge of this integration alone
does not admit that future release. No NPAD command is required for this PR.

## Qualification record

Tests cover normal handshake through candidate closure, CPU/memory/inode drift,
bad affinity, missing observations, shared accounting, partial barriers, exact
TERM/KILL and cleanup deadline, closed CLI, immutable collection, journal
tampering and strict legacy rejection. Final local counts and Linux CI results
are recorded in the PR against the exact published head. An initial local pytest
invocation failed to create its sandbox-default temporary directory; the suite
was rerun with an explicit isolated workspace basetemp. This was a test harness
filesystem issue, not an NPAD run or an accepted qualification result.

Original archives, claims, consumed attempts, manuscript and scientific
parameters are unchanged. S2 stays open with its full experimental scope;
S3/S4 remain cancelled, EVPI/VSS excluded and branch synchronization deferred
until after article review.
