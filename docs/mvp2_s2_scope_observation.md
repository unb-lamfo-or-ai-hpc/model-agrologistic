# S2: bounded controller-scope observation after job 2209138

## Completed observation: job 2209770

The [independent review](evidence/s2_scope_2209770_review.json) binds the exact
source, plan and archive hashes. Checksum/schema/identity replay passed with
`observed_not_qualified`, not normal or containment acceptance. Root, batch,
extern and numeric step all completed 0:0. Root/batch elapsed 3 seconds; the
step's 0-second accounting value is not a claim of zero CPU work.

Memory, freezer and cpuset scopes were disjoint. Only cpuacct was equal. The
numeric-step PID matched the worker identity. Observed hierarchical memory
ceilings were 256 MiB (worker) and 2 GiB (supervisor); direct leaf limits were
9223372036854771712 bytes for both. The hierarchical limit, not the large leaf
value alone, matters for interpreting available memory. No stress/OOM test was run.

Both cpusets contained two CPUs; Slurm reported one CPU for the numeric step.
On 13 October the maintainer returned the hash-asserting read of the preserved
`Cpus_allowed_list` fields: supervisor `0,32`, worker `0`. The exact status hashes
and attribution are in the review metadata. Raw records remain on NPAD; these
fields were reported by the maintainer, not independently rehashed locally or
inserted into the original archive. No new job was needed for this read.

The worker's observed CPU affinity was narrower than its two-CPU cpuset. A task's
affinity can be changed subject to its cpuset restriction; this observation does
not establish a hard one-CPU boundary. See the [Linux cpuset/affinity semantics](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v1/cpusets.html).
Do not infer SMT siblings or physical-core count merely from CPU IDs `0,32`.
Distinct non-nested cgroup paths also do not prove disjoint CPU sets or exclusive
CPU placement. The worker and supervisor affinity masks overlap at CPU `0`.
The existing normal validators still require a one-CPU cpuset, so a cpuacct-only
relaxation would leave an independently observed blocker.

### Bounded repair acceptance criteria (design only)

1. Preserve original evidence and strict legacy replay. Separate controller-path
   relations from CPU-set overlap, task affinity and resource accounting provenance.
2. Retain disjoint memory/freezer/cpuset scope checks; classify shared cpuacct
   explicitly instead of claiming its counter measures worker-only CPU time.
3. Reconcile both normal validators and exporters with the explicit CPU contract.
   Do not replace a hard cpuset ceiling with a startup affinity observation or
   automatically accept two CPUs. If the resource contract needs to change, obtain
   maintainer approval before admission; otherwise qualify a way to satisfy it.
4. Cover shared/nested enforcement scopes, shared accounting, overlapping CPU
   masks, affinity/cpuset mismatch and missing observations with regression tests.
   No guessed zero resource measurements or stronger cleanup claims are allowed.
5. Only after software qualification and an explicit successor release, provide
   a new one-shot normal CLI. Preserve consumed claims; no retry or long-job
   command is admitted by this design or by the observation's successful exit.

The next design must distinguish enforcement/tracking from resource accounting,
retain safe disjoint memory/freezer/cpuset validation, and avoid attributing a
shared cpuacct counter to the worker. Official [Slurm controller roles](https://slurm.schedmd.com/cgroups.html)
and [Linux hierarchical memory semantics](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v1/memory.html)
provide interpretation, not proof of NPAD configuration. The previously reported
jobacct_gather/linux setting is consistent with this observation; causality or
a configuration defect is not established. Old normal and observation claims
remain consumed; every execution/cleanup admission stays false.

### CPU-contract decision before operational integration

The current strict one-logical-CPU cpuset contract remains in force. The available
evidence cannot establish a Slurm invocation that narrows the kernel cpuset, and
changing startup affinity alone would not satisfy that contract. There are two
explicit routes, neither admitted by this PR:

- Retain the one-logical-CPU hard ceiling: obtain an NPAD-supported configuration
  and qualify the actual kernel boundary before the next normal release. Do not
  guess that an SMT hint or binding option changes cgroup enforcement.
- Subject to maintainer approval, define a synthetic-only hard envelope of at
  most two logical CPUs, within the unchanged two-CPU allocation, with one CPU
  requested for the numeric step and observed initial worker affinity of one CPU.
  Record the potential two-CPU envelope honestly; do not call it hard one-CPU
  containment or exclusive CPU placement. Memory (256 MiB worker / 2 GiB job),
  walltime and one-shot limits remain unchanged. This is not approval to alter
  the later h300 scientific thread contrast or its resource admission.

The second route is the proposed practical option, not an applied relaxation.
Its successor must check CPU-set membership in the allocation (not only counts),
bound the effective envelope, preserve process ownership and memory/freezer
separation, and explicitly mark shared cpuacct measurements as non-attributable.
If worker-specific CPU accounting cannot be established, report it unavailable
rather than subtracting supervisor usage or silently falling back to zero.
Legacy schemas/receipts remain strict and immutable. Runtime integration, Linux
regression, new release identity and independent normal/adverse audits remain
necessary; CPU-contract approval alone cannot authorize a job.

The historical protocol below records the one completed diagnostic, not a repeat.

## Evidence and question

PR #80 merged at `5bf509a6db90b09eef8e1e13529f5039d934a9e1`. The maintainer ran
the pinned normal source `9c008eecb93aa4b4a221fced2fafead467d89021`.
Job 2209138 root/batch completed 0:0 in 8 seconds; numeric step 2209138.0 failed
2:0 in 4 seconds. Transferred archive SHA-256:
`4f0f4bc20337d5bc7b42283afd5de620d0500509d6a7010938b18425214a14a1`.
Independent replay exactly reproduced the supplied negative review. The
[audit record](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/80#issuecomment-6148550118)
binds the evidence to its frozen source. Batch and worker source/runtime checks
passed. The supervisor diagnostic identifies `separated_scopes` line 239,
`Shared/nested supervisor scope.` The controller and direction are absent.
There is no contract, phase sample, normal acceptance or cleanup proof.

Question: which of memory, cpuacct, freezer and cpuset are equal, nested or
disjoint for an actual batch supervisor and idle numeric step on NPAD? Request
sizes, declared Slurm plugins and terminal accounting cannot answer this.
This is not a solver experiment and does not change any separation predicate.

## Fixed observation envelope

| Component | Fixed scope |
| --- | --- |
| Allocation | One node, 2 CPUs, 2048 MiB, 5 minutes; account sxdsouza, intel-256, no requeue |
| Numeric step | One task, 1 CPU, 256 MiB, exact allocation, threads binding, 2-minute ceiling |
| Observer | Standard-library Python identity handshake and idle wait; no model, solver, child tree or license |
| Communication | Short private Unix seqpacket socket, kernel peer credentials, 30-second accept and 45-second leaf receive deadlines |
| Queries | Three bounded reads: exact job, exact numeric step, listpids of that step |
| End | Release the idle observer, reap owned local srun; never assert remote cleanup |

The leaf's requested memory/CPU limits are not assumed to be effective kernel
limits. Record actual memory and hierarchical-memory limits and cpuset size
when available. Unsupported mappings/read failures remain explicit missing
observations. The observer is not an adversarial process and forks no descendants.
No scancel is issued. If the local client exceeds its wait, only that owned
client is killed; the remote leaf has its own finite wait and scheduler ceiling.
These are bounded requests, not a hard real-time guarantee under kernel/Slurm failure.

The raw proc identity, membership and mount records are saved **before** mapping
or relation checks. All four relationships are reported even when one is shared.
Raw proc/query/client-output records stay in the private NPAD run. The portable
archive has exactly anchor.json, observation.json and accounting.json; its nested
schema permits only identities, hashes, controller relations, numeric counters,
allowlisted Slurm fields and bounded numeric PID rows. No environment, license,
arbitrary stderr, raw cgroup paths or working directories are exported.
Keep private originals: hashes alone cannot reconstruct them.

## One-shot lifecycle and qualification

`npad_s2_scope_diagnostic.sh start REVIEWED_SHA` checks the frozen source,
47 focused regressions with no failures/errors/skips, then raw physical source
closure. The immutable head must descend from the merged PR #80 baseline.
As in the earlier observation-only diagnostic, a separately reviewed and CI-green
PR head may be used before merge; this does **not** authorize its merge or a
normal/solver execution. The handoff must pin both full commit and driver SHA-256.
No moving branch name is an execution pin. Linux CI checks Bash syntax, focused
regressions and post-test physical source closure; local tests do not prove NPAD behavior.

The independent claim `.mvp2-s2-scope-observation-v1` is reserved before sbatch.
Exactly one submission is possible. Unknown acknowledgement consumes the claim
and requires read-only investigation; do not remove it. Existing claims route to
original-source collection only. Start/collect never alter old normal claims,
recovery carriers, certificates, models, runtime packages or manuscript files.

`collect REVIEWED_SHA` reads terminal sacct with State%80 and numeric steps;
nonterminal accounting returns without submission. It packages complete,
incomplete or missing observation, validates a replay, prints DOWNLOAD and
TRANSFER_CHECKSUM, and caches the archive. Repeating collection returns the
same verified bytes without a new scheduler query or job. Transfer only those
two paths through MobaXterm. Preserve the bootstrap, claim and private run.

## Interpretation and next decision

`observed_not_qualified` means data were collected, not containment accepted.
`incomplete` or `missing_observation` remains useful negative evidence.
Every normal/adverse/native/production/repeat/isolation/cleanup admission flag
remains false, including on successful observation and replay.

The independent audit must compare all controller relations, actual limits,
process identities, numeric-step membership and terminal accounting. Then decide
whether a role-specific accounting/enforcement distinction is justified, whether
resource or mapping configuration needs correction, or whether NPAD support is
needed. Do not relax the predicate merely to make a test pass. A normal successor
needs a qualified explicit release; no long jobs follow automatically. S2's full
experimental scope is preserved and branch synchronization remains after article review.
