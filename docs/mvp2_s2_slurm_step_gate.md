# S2: closed Slurm-step contract and cgroup-v1 observer

## Evidence and decision

PR #58 merged at `9bf4160b20b6909a594e931f4da14d576f840776`.
Its input-only job 2202795 completed with exit 0:0. The archive
`s2-containment-evidence-2202795.tar.gz` has independently verified SHA-256
`68604864018944b1afe7d546207a1a8881a5a473fed5a49896f389d0fcef325e`.
Replay accepted the evidence and its original source/job/nonce binding;
the probe outcome remains **blocked_environment**, because the existing
containment path requires cgroup v2 while the observed environment is v1.
Accepted collection is not accepted containment. No native process ran.
See the [terminal audit](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/58#issuecomment-6083507326).

The maintainer subsequently supplied a successful read-only configuration
inventory, preserved in [site inventory](mvp2_s2_slurm_site_inventory.json).
It declares `proctrack/cgroup`, `task/affinity,task/cgroup`,
`select/cons_tres`, `CR_CPU_MEMORY`, `TaskPluginParam=threads` and
`jobacct_gather/linux`. Both observed **client** versions are 22.05.11;
this does not establish controller/daemon/plugin/kernel versions or effective
limits. KillWait is 300 seconds; UnkillableStepTimeout is 60 seconds.
These are user-supplied declarations, not signed remote attestation.

Decision: investigate a Slurm-owned numeric worker step, with the batch
supervisor outside it, without requiring a cluster upgrade, writable delegation
or a new solver. This PR implements only closed software interfaces and an
observer. **There is no launcher, submission command or execution admission.**
All isolation/native/production/repeat flags remain false. S2 stays open.

## Implemented software boundary

`scripts/mvp2_s2_slurm_step.py` has no scheduler invocation, subprocess launch,
cgroup write or native-solver import. Its exact-schema inventory reviewer rejects
version/configuration drift rather than silently treating it as an improvement.
Its binding accepts a canonical positive job ID and a numeric worker step only;
arrays, heterogeneous IDs, batch/extern worker targets and allocation-wide signal
targets are rejected. Nonce and source-commit fields bind the proposed record,
but do not prove that Slurm created or owns the scope.

Signal descriptors are inert argument lists addressed to `job.step`, never to
the allocation. The [official scancel documentation](https://slurm.schedmd.com/scancel.html)
supports distinguishing step and allocation targets; these current docs are
not proof of installed 22.05.11 behaviour. A later live gate must qualify exact
signal routing, acknowledgement and cleanup on the actual stack. Successful
signal submission must never mean successful termination.

Actual `/proc/<pid>/cgroup` and mountinfo data map v1 controller scopes. Slurm
directory names are not guessed. Missing, duplicate, mixed-v2, root-shared or
namespaced-root mappings fail closed. The separation check requires distinct,
non-nested worker and supervisor scopes in all four controllers. It explicitly
does **not** establish job ownership or prevent a later migration.

The observer uses read-only, no-follow descriptor access inherited from the
resource collector. Live mode requires Linux and observed v1 mounts. It bounds
freezer traversal to 128 groups, depth 16 and 4096 unique processes, checks
root/subgroup identities, rereads membership/children and checks memory-ceiling
drift. Failures/disappearance return blocked observations, never cleanup success.
Schema/path precondition errors raise ValueError. Fixture mode is marked
synthetic and cannot produce an admission. No raw PID, scope path, hostname,
environment or exception message is exported; scope identities use SHA-256 of
the JSON-encoded path string, not the older v2 raw-path encoding.

These checks are bounded observations, not an atomic kernel snapshot. They do
not yet prove PID start times, Slurm ownership, external-writer identity,
containment of all lifetimes, reaping, absence of future descendants or closure.
The module is not connected to the existing worker or any execution CLI.

## Resource interpretation

| Field | Unit and interpretation | Not established |
| --- | --- | --- |
| memory_usage_bytes / memory_max_usage_bytes | v1 charged usage / high-water counter | Process RSS, exact resident footprint or a full run peak from one sample |
| effective_reported_memory_limit_bytes | Minimum of own limit and reported hierarchical ceiling; finite ceiling and hierarchy required | Effective enforcement or a successful OOM cleanup |
| memory_failcnt | Memory-limit charge failures | OOM-kill count |
| cpu_usage_ns | Hierarchical cpuacct usage in nanoseconds | Allocated core-hours, speedup or CPU utilisation without elapsed deltas |
| cpuset_cpu_count | Count of CPUs listed in observed cpuset | Dedicated physical cores, quota or actual parallelism |
| freezer_unique_process_count | Bounded recursively observed membership | Reaping or lifetime closure, even when zero |

The kernel documents [cpuacct units](https://docs.kernel.org/admin-guide/cgroup-v1/cpuacct.html)
and [v1 memory counters](https://docs.kernel.org/admin-guide/cgroup-v1/memory.html).
The memory document warns that it is outdated; actual kernel behaviour still
requires live qualification. `jobacct_gather/linux` and sacct MaxRSS are separate
observations, not interchangeable with these counters. Memory snapshots may be
approximate and include charged cache. Do not sum hierarchical and child counters.

## Proposed synthetic profile — NOT executable or admitted

The pure `qualification_plan` function freezes a proposal: one node, 2 allocated
CPUs, 2048 MiB allocation, worker 1 CPU / 256 MiB, startup 30 s, exercise 60 s,
TERM grace 5 s, cleanup-observation budget 390 s and allocation wall 720 s.
The cleanup budget is **300 + 60 + 30 seconds**, a conservative design choice
informed by declarations, not a documented upper bound on process death.
Uninterruptible processes may outlive it. Any unresolved cleanup must remain
blocked and preserved; the controller must not continue to another case.

No memory-pressure case is admitted by this proposal. A future launcher must
prove finite effective enforcement and safe external supervision before a
separately bounded adversarial resource case. It must not exercise host-wide
OOM, alter cgroup ownership or use an allocation-wide kill as a fallback.

## Remaining gates and exit criteria

1. Qualify and merge this closed interface/observer PR at its exact published
   head, with source parity, negative fixtures, existing S2 regression and CI.
   No NPAD CLI is needed for this software-only gate.
2. Integrate a separately reviewed bounded synthetic launcher/controller:
   establish actual Slurm job/numeric-step/cgroup ownership, supervisor and
   partial-output writer outside the worker scope, barrier before native import,
   immutable source/profile/nonce binding, one-shot claim, exact-target TERM/KILL,
   deadlines and external observation. Freeze case matrix and collector before
   requesting the user to run anything. No implicit retry on unsupported layout.
3. Qualify the live synthetic path, including nested and session-detached
   descendants, TERM-ignoring timeout, forced cleanup, no late writes, empty
   dedicated scope **and** process reaping, failures during build/optimisation/
   export/disposal, missing/stale/removed scopes and bounded partial evidence.
   Preserve adverse outcomes. Accounting alone cannot satisfy this gate.
4. Only after that audit, qualify separately admitted licensed analytical
   miniatures through the integrated path; PR #53 is not a substitute.
5. Then review fresh homogeneous h300 admission, one bounded diagnostic thread
   block and final evidence/decision. Censored timings are not full-budget speedup.

Merging this PR admits none of steps 2--5. S3/S4 remain cancelled; bounded
existing SCIP h215 requalification, h500 assessment and S6 HPC/editorial synthesis
remain in the [roadmap](mvp2_hpc_roadmap.md). No manuscript, model, dependency,
solver tolerance, thread campaign, release or deposit is changed here.

## Offline qualification

Python 3.13: 86 new tests pass on Windows; the new Linux no-follow symlink
fixture skips there. The combined eight S2 contract/control/partial/native/
evidence/resource/containment/step suites pass 535 tests, with seven explicit
platform skips (Bash syntax, POSIX groups, symlinks and Linux proc inspection).
Ruff passes across src/scripts/tests and the new Python files are formatted.
None of these tests is live NPAD containment evidence. Linux CI, changed-file
parity and exact-head review are checked before marking the PR Ready.
