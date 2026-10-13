# S2: bounded controller-scope observation after job 2209138

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
