# S2 independent environment verifier and closed operational adapter

Current continuation after PR #93 merge: the separately authorized
[complete closed normal lifecycle package](mvp2_s2_lifecycle_release.md) integrates
worker, controlled release/stop, exclusive claim, wrapper and terminal/forensic
collection. This historical software description and all original evidence remain
preserved; no installed environment proof or execution admission follows.

## Authority, base and deliverable

14 October 2026; verified develop base
`9cc579d23f544c3ec6cdd7bbd71d85e6294ba01a` (PR #92 merged).
The maintainer authorized software integration/qualification only, preserving
claims/evidence and blocking executions. This package implements the missing
independent observational verifier and closed adapter for the
[prospective lifecycle protocol](mvp2_s2_lifecycle_protocol.md). It does not adopt
an installed cleanup criterion, admit normal A, reserve a claim or supply a CLI.
The [checkpoint](../PROJECT_STATE.md) remains authoritative.

| Component | Independent inputs | Result and boundary |
| --- | --- | --- |
| Environment verifier | Kernel process/namespace/mount/FD records, actual filesystem type and recursive controller reads; exact Slurm ownership/membership | Derives conditional assurance digests; unsupported or missing evidence blocks |
| Operational adapter | Current sealed source/runtime; socket peer credentials; source/job/step/nonce handshake; two independently captured environments | Software barrier only: no IPC release, fork, signal, claim or scheduler submission |
| Continuation and forensics | Fresh parent anchors/policy/inventory; actual step status; identity absence, exact accounting and explicit product/write readers | Bounded semantic replay, negative/partial preservation and redacted review; never installed cleanup acceptance |

Executable public entries deny before imports/effects. Dependencies are explicit;
there is no default live transport/kernel selection, discovery or effects factory.
Old workers, launchers, controllers, parsers and evidence are not modified.

## Conservative sufficient environment profile

The independent reader checks Linux x86_64, actual cgroup-v1 filesystem magic via
`fstatfs` on opened descriptors, unique full-root controller mounts and stable
mount/device/inode/process identities. It compares user/mount/PID/cgroup namespace
identities with the visible host PID1, requires the initial full UID map and
requires the observed user-namespace creation limit to be zero. Namespace-relative
paths cannot by themselves establish host coverage; see
[cgroup namespace semantics](https://man7.org/linux/man-pages/man7/cgroup_namespaces.7.html).

It traverses the **whole visible hierarchy** for each relevant controller, not
only a writable worker subtree. Directories and migration files must be root-owned,
not group/other writable and have no extended access ACL. A bounded inherited FD
inventory rejects writable cgroup descriptors. This deliberately conservative
sufficient profile avoids assuming the cgroup-v2 common-ancestor migration rule
applies to v1; see [Linux cgroups](https://man7.org/linux/man-pages/man7/cgroups.7.html).
Root-owned mode bits alone are not the complete no-escape argument: namespace,
capability, descriptor, source identity and recursive coverage checks are mandatory.

The worker must be non-root, have matching real/effective/saved/filesystem IDs,
zero effective/permitted/inheritable/ambient capabilities, NoNewPrivs=1 and one
initial synthetic thread. The fixed SET/GET hardening component accepts an explicit
injected primitive only; no actual prctl mutation or host setting change occurs
in this qualification. [NoNewPrivs](https://docs.kernel.org/userspace-api/no_new_privs.html)
is inherited and irreversible, but is **not sufficient by itself** to prevent
every privilege transfer. This package additionally depends on the current sealed
stdlib normal worker and trusted host administration; it does not secure arbitrary
hostile code or administrators. See also the
[kernel process status fields](https://man7.org/linux/man-pages/man5/proc_pid_status.5.html).

The actual observer PID must be the bound live non-zombie supervisor beneath all
three controller parents. Under trusted administration, the kernel v1 rule that
a populated group/ancestor cannot be removed conditions parent persistence;
see [kernel v1 cgroup removal](https://docs.kernel.org/admin-guide/cgroup-v1/cgroups.html).
Each observation rechecks supervisor identity/membership, host profile, mount and
parent identities, full permission coverage and recursive inventory. An open FD
alone, unchanged filename or equal snapshots is not a persistence capability.
Any replacement, migration, unknown process, unreadable inventory or changed host
profile blocks. This is sampled conditional evidence, not continuous attestation.

**NPAD compatibility is unknown.** No positive installed test has occurred. In
particular, user-namespace policy, delegation, mount visibility, process access
or scan latency may make this sufficient profile unavailable. A failure does not
prove no other rigorous profile is possible. Preserve the exact negative site;
do not automatically disable namespaces, change permissions, weaken admission,
extend budgets or submit another normal job. Infrastructure support or a separately
reviewed profile would require a subsequent decision.

## Current identity and lifecycle integration

The sealed manifest binds the complete tracked source, including the new verifier
and adapter, against an externally provided manifest digest. Batch checks require
compute-role tools only; Git/sbatch remain login-only. Worker-role checks use the
same source and Python identity without assuming login tools exist on compute.
AF_UNIX/SOCK_SEQPACKET peer PID/UID/GID are read from the accepted kernel connection;
the worker's executable/argv, runtime, nonce, source, manifest, contract and exact
job/step are checked independently. A handshake cannot supply its own environment
assurance. The local srun client is an explicit bound child of the supervisor,
with checked process/executable identity; no broad same-UID/group exemption exists.

Fixed scheduler reads are allocation, exact numeric worker step/membership,
reserved numeric batch-membership query and wide accounting. RPC helpers have
one-second timeouts and64KiB output bounds; queries complete before membership
capture. No submit, launch or signal method is exposed. Startup needs two separate
environment/resource captures. Initial affinity, inherited finite memory ceilings
and the up-to-two-logical-CPU envelope reuse the existing ResourceGate unchanged.

After actual leader absence or terminal step classification, the verifier keeps
observing the persistent parent and known identities without recreating the gone
worker leaf. Step directories are queried independently and retain
available/missing/unavailable distinctions. Post-exit worker resources are `None`,
never a stale live sample. Shared cpuacct is not attributed worker CPU. Accounting
lag yields a partial observation, not quiet progress. Original390s cleanup,
5s quiet/minimum3samples,5s maximum sampling gap and all startup/exercise/global
deadlines remain unchanged. No linger, afterok chain, terminal-only fallback or
additional synthetic slot is introduced.

Every raw read/result is captured in bounded private software frames: at most512
kernel calls per frame,16MiB per frame and32MiB cumulative adapter evidence. Whole
hierarchy traversal is bounded to2048groups/depth32. These are rejection bounds,
not proof the full scan fits NPAD's unchanged five-second cadence. Frame exhaustion
or slow observation blocks; it never silently drops history or extends time.
Independent replay checks requests, raw facts, results, packet/journal agreement
and final accounting. Invalid nested journal replay cannot be reported as a valid
top-level replay. Before-barrier failures preserve controlled diagnostic sites
and negative/partial metadata. Public reviews contain digests/fixed diagnostics,
not private paths, PIDs, raw hierarchy inventories or credentials.

## Qualification and remaining release work

Local Python3.13/Windows qualification:215 focused cases passed,3 Linux-only
skips; expanded S2:1996 passed,12 disclosed platform skips, zero failures/errors.
Ruff, whitespace, YAML and159 relative documentation links passed. Exact-head
Linux CI must pass before Ready; local skips do not satisfy Linux qualification.
No Gurobi license or scientific optimization was exercised.

Tests use explicit fixture kernel/RPC/clock/launcher objects. The integration suite
covers valid normal fast exit, live-to-post-exit transition, actual missing-step
semantics, short accounting lag, security/namespace/FD/permission failures,
source/runtime/peer/nonce drift, foreign/migrated/replaced/unreadable processes
and scopes, cadence/evidence limits, replay corruption and closed public verbs.
Linux CI separately exercises real read-only fstatfs/socket peer primitives;
it does **not** exercise a real Slurm or complete cgroup-v1 environment. Clean
export regression verifies physical source closure before/after testing. No
solver, license, worker process, adverse tree or NPAD action is exercised.

All admission/containment/cleanup flags stay false, even after a valid software
candidate or terminal replay. PR #92's historical readiness remains unchanged;
this new closed adapter is the current software integration, not a retroactive
rewrite of that receipt. Original job2210952/job2210506 and earlier evidence stays
byte-identical. Models, h300 science, manuscript and resource parameters are intact.

Next complete gate: qualify the future real worker entry/security preparation,
bounded IPC release and stop/controller wiring, fresh exclusive claim, wrapper,
source closure, terminal/forensic transfer and pinned human instructions together.
No existing launcher selects this adapter and its proposed worker argv currently
points to a deliberately denied entry. The adapter therefore is **not runnable**
and cannot establish installed persistent-parent/no-escape acceptance. Finish
Ready/merge review of this closed package first; only a later separately reviewed
release can propose live admission. No NPAD CLI now. Full S2 A/P2-P5 and subsequent
scientific scope remain open, with final synchronization only after article review.
