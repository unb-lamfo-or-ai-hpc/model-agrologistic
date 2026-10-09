# S2 - closed real batch adapter qualification

## Scope and admission

PR #60 merged into develop at `4472c8429a2aa99d10a716d827f1f6bfa0ec022a`.
Its injected components now have a real POSIX transport, local IPC bridge,
batch integration and terminal collector. This is a **software gate before the
synthetic NPAD test**, not approval to run it. Public batch and worker entry
points still deny before reading arguments, files or environment. There is no
`sbatch`, submission driver, environment override or admitted executable runbook.
Calling internal Python components manually is not authorization and is not a
security capability. Merge admits no allocation, step, native miniature, solver,
h300 diagnostic or repeat. All admission/live-containment flags remain false.

## Integration and order of effects

1. Freeze a pre-binding specification: source commit, nonce, job, synthetic case,
   canonical paths, inventory and independently retained Python/tool hashes.
   There is deliberately no guessed numeric worker step. Source and run are
   separate. Resolve legitimate executable symlinks before freezing the plan;
   linked source, product and binary paths are rejected.
2. Verify binaries before invoking Git. Check every regular tracked file against
   its raw HEAD blob, including binary files; reject dirty/untracked source,
   symlink/submodule/conflicted entries and LF/CRLF drift. Bound to 1024 files,
   8 MiB per file and 32 MiB total. Source blob queries have their own bounded
   counter, separate from the live scheduler RPC budget.
3. Check actual supervisor entry/runtime, Python 3.13 and installed Slurm client
   versions against the observed 22.05.11 declaration. Independently query the
   allocation: owner UID, RUNNING, one exact local node/batch host, two CPUs,
   2048 MiB node memory and twelve-minute wall. Require the supervisor PID in
   local `listpids job.batch`; environment identifiers alone do not establish it.
4. Claim a new run directory exclusively; persist claim, worker plan and launch
   intent before launching. Existing directories are preserved without even an
   attempt receipt being written into them. Unknown launch acknowledgement is
   not retried. The fixed `srun` descriptor uses the existing job, one CPU,
   256 MiB, exact resources, thread binding, ten-second immediate request,
   nine-minute step and no inherited user environment. Its worker CLI remains
   closed in this revision, so the descriptor is not a runnable admission recipe.
5. Connect through local `AF_UNIX/SOCK_SEQPACKET`, mode 0600. Kernel peer PID/UID,
   independently read `/proc` identities/scopes and actual executable establish
   the candidate worker. The worker supplies only bounded nonce/job/step and
   measured source/runtime digests. Cross-check the actual numeric step with
   `scontrol show step` and `listpids`, never launch order or cgroup basenames.
   Two strict resource/member barriers must agree while the worker waits.
6. Persist contract, binding and the controller release event outside the
   worker scope before the IPC release. The worker verifies supervisor peer,
   source/runtime, release identity and its own startup deadline before any
   synthetic phase or nested process. Only fixed build/optimization/export/
   disposal callbacks exist; these are not model construction or optimization.
7. Pump both srun pipes; read member identities, resources, fixed phase products,
   heartbeat/fingerprint and step accounting. Persist each sample/controller
   event before an exact-step signal intent and signal effect. TERM/KILL are each
   one-shot. A timeout consumes the intent; acknowledgements never prove death.
8. Preserve original claims, IPC path and partial/adverse products. The terminal
   collector does not query Slurm, signal, submit or rerun. Its caller supplies
   terminal accounting, an independently retained specification and, if bound,
   contract. An unbound attempt has a distinct blocked record, not invented
   successful phases or a guessed signal target.

## Bounds and evidence interpretation

The PR60 profile remains frozen: startup 30 s, exercise 60 s, TERM grace 5 s,
cleanup observation 390 s, nominal allocation 720 s and a parent collection
reserve starting at elapsed 660 s. The 390 s design budget is **not** a guaranteed
scheduler kill deadline. Each query drains stdout and stderr together with a
combined byte cap and a ten-second communication deadline; cleanup kills only
the locally owned query process and waits at most one more second. No group or
allocation cancellation fallback exists. A bound query failure is explicit;
unknown remote ownership is preserved, not guessed away.

Python process creation and blocked kernel/filesystem operations cannot be
interrupted reliably by these user-space deadlines. The nominal reserve does
not prove an unstallable parent. Closing pipes or observing a reaped srun client
does not prove remote cleanup; an unbound/live client may remain when an attempt
is preserved. The later live admission must explicitly qualify interruption,
client lifetime and allocation-wall behaviour. No synthetic or licensed run is
allowed to rely on an assumed hard timeout.

Sampling is nominally every two seconds, at most 256 observations and 512 live
RPCs. Observed gaps over five seconds become adverse; a finite bound reached
early preserves the attempt rather than extending it. Known PID/starttime
identities are bounded to 64 for the entire attempt. Counter rollback, changed
limits, replaced scopes, missing observations, mismatched memberships and moved
supervisors invalidate a clean sample. Empty/missing scopes are not cleanup.
Short-lived descendants between samples are not comprehensively discovered.

The nested stdlib exercise is still limited to child plus TERM-ignoring,
session-detached grandchild with a cooperative 120-second self-exit bound. A
fixed heartbeat challenge updates at most once per second; the parent includes
both completed and pending heartbeat products in the fingerprint. Observed late
writes restart the quiet period (three clean observations spanning five seconds).
This tests an observation mechanism, not absence of every possible filesystem
write, an atomic kernel snapshot, a subreaper or hostile-same-UID isolation.
No real synthetic fork tree is exercised by this PR's tests or CI.

The exclusive portable archive contains exactly six regular JSON members:
contract, events, worker, adapter, accounting and recomputed review. It excludes
raw PIDs, hostnames, executable/scope/run paths, raw pipe output, environment,
arbitrary logs, workbooks and license contents. The original run retains its
private operational files. SHA-256, external specification/runtime/job binding,
optional externally retained contract, replayed events/resources and terminal
job/batch/bound-step records are checked. Duplicate/link/traversal/extra members,
nonfinite/duplicate JSON keys, trailing nonzero tar data and expansion beyond
2 MiB fail replay; no extraction or overwrite occurs. Nonzero terminal exits
are preserved as adverse outcomes, not filtered into apparent successes.

`candidate_closed` remains a controller claim, not live containment acceptance.
Worker `synthetic_complete_not_cleanup` and `partial` remain distinct; cleanup
can be observed without completed worker phases. Charged memory bytes are not
RSS; `cpuacct` nanoseconds are not allocated core-hours; failcnt is not an OOM
kill count; one cpuset entry does not establish exclusive physical cores.

## Qualification and next explicit gate

Offline tests cover real adapter plumbing with injected scheduler/process
observations, worker IPC release/failure matrix, partial products, immutable
claims, exact-target signals, source byte drift, changed resources, quiet-period
restart and bounded terminal archive replay. Linux CI additionally tests real
nonblocking pipes using tiny local Python children and kernel peer credentials
with a local socket/thread. These are not Slurm jobs, synthetic fork trees or
licensed miniatures. Windows skips these two Linux-specific transport tests.
Published-source parity, focused regression, lint/build and PR-head integration
checks must pass before Ready; the final audit reports their observed counts.

The [official srun](https://slurm.schedmd.com/srun.html),
[scontrol](https://slurm.schedmd.com/scontrol.html),
[scancel](https://slurm.schedmd.com/scancel.html) and
[Python subprocess](https://docs.python.org/3.13/library/subprocess.html)
documentation support the design, not installed NPAD output grammar or plugin
enforcement. Strict one-line job/step and parsable accounting formats are
unqualified site prerequisites: any mismatch blocks, without permissive fallback.
No RPC/config output beyond allowlisted fields belongs in portable receipts.

Next, separately freeze the actual installed runtime/tool envelope, the bounded
synthetic-only admission wrappers and terminal command protocol. Qualify the
closed worker-to-session dispatch, interruptions, failure packaging, short IPC
path (at most 100 encoded bytes), local node naming/step grammar and total
campaign budget before asking the maintainer to execute a first normal synthetic
case. Do not silently chain the six cases or retry an unresolved one. Further
adverse cases require the same explicit bounded protocol and audited predecessor.
Live containment audit precedes licensed miniature integration and fresh h300
diagnostic admission. S2 stays open. S3/S4 remain cancelled; SCIP h215, h500/S5
and HPC-focused S6 plans are unchanged. No article/slides or main synchronization.
