# S2 — closed operational protocol and read-only installed envelope

## Decision and boundary

PR #61 merged into develop at `dd68588a5bdfe1f6536e357dab049509678659e4`.
The real adapter is integrated, not an installed containment certificate.
This gate qualifies an operational **proposal** for the first normal synthetic
case, interruption handling and partial collection. It opens only the executable
`probe-envelope` read-only entry. Submission, batch and worker entries remain
closed; calling internal components is neither authorization nor a security
capability. No job, step, synthetic tree, license, native miniature, h300 or repeat
is admitted. S2 remains open. No article, dependency, protection or main change.

The dependency is concrete: the installed Python/tool byte identities and current
selected Slurm configuration have not yet been frozen. Do not fabricate hashes
or infer installed output grammar from current upstream manuals. First obtain
that evidence without an allocation; independently audit it before a live release.

## Read-only envelope: executable next step

After this PR merges, the maintainer runs the pinned `scripts/mvp2_s2_operational.py`
with Python 3.13 and `-I`, `probe-envelope --source-sha FULL_HEAD --output NEW_DIR`.
Use a clean detached clone outside the output directory; preserve source and output.
The final PR audit supplies the exact HEAD and a complete copy/paste driver.
No `GRB_LICENSE_FILE` or license access is necessary. Do not run on an unreviewed
revision or manually call the closed execution components.

Order of observation:

1. Require Linux/Python 3.13. Resolve legitimate executable symlinks and hash
   Python plus Git, srun, scontrol, scancel, sacct and sbatch **before invoking Git**.
2. Reuse the adapter's bounded raw-HEAD verifier: exact commit, clean index/tree,
   all tracked regular bytes including binaries, no untracked source or links.
   Disable Git line-ending conversion for the two historical manuscript artifacts
   before checkout. Do not regenerate manuscript products to make the tree clean.
3. Query only raw Git source, five Slurm client `--version` commands and
   `scontrol show config`. `sbatch --version` does not submit. No job ID, allocation,
   PID, daemon log, worker or live accounting is queried by this probe.
4. Retain only the eight already reviewed configuration fields, reject missing,
   duplicate or drifted fields and require observed client version 22.05.11.
   Rehash every executable after observation; mismatch blocks.
5. Keep the full path-bearing envelope locally in `private-envelope.json`.
   Export only `receipt.json` and recomputed `review.json` in
   `s2-envelope-evidence.tar.gz` plus its SHA-256 companion. Send these two files,
   not the private envelope, arbitrary logs, configuration dump or license.

Commands have bounded combined stdout/stderr and nominal ten-second deadlines;
the probe adds a nominal 120-second total query budget. Raw-source limits remain
1024 files, 8 MiB/file and 32 MiB total. These are user-space bounds, not guarantees
against blocked kernel/filesystem operations. Binary hashes are identities,
not attestations of Git, shared libraries, Slurm daemons or hostile-user isolation.
Paths and hashes are not secret capabilities. Configuration does not prove live
enforcement or command grammar.

Outcomes are `observed_not_admitted` or `blocked_envelope`. The latter exits 2
but still packages bounded negative evidence after a handled observation failure.
No raw exception/configuration text is exported. A killed/interrupted probe can
leave only the immutable intent/partial files: preserve them, do not overwrite.
A fresh read-only observation requires a fresh directory, not a submission retry.
Every outcome keeps all execution/admission flags false. Audit the externally
retained checksum and source commit, exact member set, schemas and recomputed
review. Reject links, extra/duplicate/traversal members, nonzero trailers,
oversized records and gzip expansion beyond 128 KiB without extraction.

## First normal case: frozen proposed envelope, not release

The closed `normal_plan` is bound to the independently retained private-envelope
digest, exact source/runtime and future externally known job ID. It is not a
signed authorization token. The future live driver must revalidate all source,
runtime and allocation conditions before effects. No guessed worker step exists.

| Constraint | First-normal proposal |
| --- | --- |
| Campaign | One attempt, one job, one worker step; no retry/requeue |
| Allocation | Account `sxdsouza`, partition `intel-256`, one node, 2 CPUs, 2048 MiB, 720 s |
| Cost ceiling | 1440 allocated CPU-seconds (0.4 allocated core-hours), not measured consumption |
| Parent reserve | Stop/collection boundary at 660 s; not an unstallable hard deadline |
| Worker | Existing fixed normal stdlib phase exercise, one CPU/256 MiB; no solver/model |
| Worker timing | Startup 30 s, exercise 60 s, TERM grace 5 s, cleanup observation 390 s |
| Run | Direct short `s2n-...` child of the designated base; socket path at most 100 bytes |
| Claim | Campaign-wide `.mvp2-s2-first-normal-v1`, exclusive and immutable across commits |

An incomplete claim consumes the attempt; an unknown acknowledgement is not a
reason to repeat. Internal claim qualification has no submission callback.
No adverse case is chained automatically. Additional synthetic cases require
audited predecessor evidence and a new explicit bounded decision; normal alone
does not qualify TERM-ignoring/session-detached descendants.

## Interruptions and unknown effects

The signal handlers for SIGINT/SIGTERM only latch the first reason. They do no
I/O, raise no exception and invoke no scheduler command; prior handlers are
restored. Before launch, stop without a worker. After launch but before binding,
never guess a numeric target. After independently verified binding, the latched
stop feeds the existing replayed controller through `tick(force_fault=True)`;
durable exact-step TERM/KILL intents remain one-shot.

Unknown launch/handshake/tick effects or abrupt Python interruption preserve a
fixed adverse reason; no second launch/handshake or compensating remote signal.
Local cleanup targets only the adapter-owned Popen after an immutable local stop
intent, with one kill and at most a one-second reap wait. Existing intent or
unknown reap stops the campaign. Never scan PIDs, kill a process group or cancel
the allocation as fallback. Reaping/killing local srun can affect Slurm indirectly
and **does not prove remote cleanup**. Remote cleanup remains false in operational
records even when the replayed controller reports `candidate_closed`.

The worker-dispatch seam checks exact normal specification digest, fixed plan
path, nonce/job/runtime and the existing kernel-peer/source/runtime release
session. It does not make the currently denied worker CLI executable.

## Terminal and partial collection

Collection is a separate read-only action after independently supplied terminal
job/batch/actual-bound-step accounting. Preserve original claims, run and partial
products. The existing six-member batch archive/replay remains unchanged. An
additional bounded `operation.json` sidecar records the operational disposition
and binds it to the archive SHA-256. Independent audit requires **both externally
retained checksums**, expected specification, optional bound contract and job ID.
An altered sidecar cannot be laundered through a valid batch checksum.

Prelaunch interruption has no batch archive to invent: preserve its claim/stop
record. Missing terminal accounting, operation, scope membership or cleanup
proof remains unknown/adverse. `COMPLETED/0:0`, accepted archive integrity, phase
completion and live containment are distinct facts. No collection admits retries.

## Qualification and next exit decisions

Offline qualification uses fake scheduler/process effects and real portable
archive replay. It covers read-only allowlists, hash-before-query/recheck order,
version/config drift, campaign expansion, poisoned claims, closed CLIs, kernel
dispatch guards, signal restoration, interrupted/unknown effects, owned-client
cleanup and externally bound partial sidecars. Linux transport checks use only
tiny local pipe/socket fixtures, not Slurm or the synthetic fork tree. Final
counts and exact published-head CI are recorded in the PR audit, not assumed here.

Next actions, without broadening the experiment:

1. Merge the qualified software gate; maintainer executes only the read-only probe.
2. Independently audit the transferred envelope receipt. If blocked, resolve the
   actual cause without submitting a job. If observed, prepare the separately
   qualified first-normal live wrapper and strict installed grammar checks.
3. Only after that release, ask for one bounded normal NPAD test and collect it
   without resubmission. Independently audit it before any adverse synthetic case.
4. Effective containment audit precedes licensed miniature integration, fresh h300
   admission, one diagnostic thread block and S2 evidence/decision closure.

The [official sbatch](https://slurm.schedmd.com/sbatch.html),
[srun](https://slurm.schedmd.com/srun.html) and
[Python signal](https://docs.python.org/3.13/library/signal.html) manuals support
design choices, not installed 22.05.11 behavior. No performance, effective live
containment or S2 completion claim is made. S3/S4 stay cancelled; bounded existing
SCIP h215, h500/S5 and HPC-focused S6 remain the subsequent roadmap. Main/develop
reconciliation waits until S2 closure; EVPI/VSS removal waits until S6.
