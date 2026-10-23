# S2 complete prospective observation package v2 — execution closed

## Authority, scope and preserved evidence

15 October 2026. The maintainer reports PR #96 merged into develop at
`37d4b13b4fffdf9566b18075c3b7ab4f9784691f` and authorizes integration and software
qualification of the next complete observational package. This is **not live
execution authorization**. Read the [checkpoint](../PROJECT_STATE.md) and the
[job2211568 audit](mvp2_s2_profile_2211568_audit.md) before interpreting results.
The original source/claim/archive, its `blocked_environment` result and historical
executables remain byte-identical. No original certificate is upgraded.

This version integrates the qualified diagnostic components, explicit read-only
kernel primitives, observer, independent replay, one-shot orchestration, wrapper,
status/wait, terminal/forensic archive and cached resume in one software package.
No additional normal-only micro-release or blind retry is proposed. Public Python
`start`/`batch` and Bash `start` **deny before host checks, source lookup, claim
reservation or scheduler access**. Component tests use disposable namespaces and
injected readers/commands; they are not commands for the NPAD maintainer to run.
The internal orchestration functions are test seams, not a security sandbox or an
authorization bypass. No live reader or job is selected merely by importing code.

## Integrated obligations

| Component | Qualified responsibility | Preserved failure boundary |
| --- | --- | --- |
| Host primitives | Read each PID1 namespace and the namespace limit independently | An unreadable namespace cannot erase a readable limit; no sudo/sysctl/fallback |
| Controller stages | Exact UID/job/batch placement, mount mapping, actual descriptor, hierarchy and inventory | Only memory may use step_batch/task_0; foreign tasks/descendants are not accepted |
| Independent replay | Recompute mount mapping from retained mountinfo; bind descriptor/inventory/hierarchy inodes and observer membership | A path, producer summary or terminal job cannot establish containment |
| One-shot components | New source/plan, exclusive claim, durable intent/called marker and exact acknowledgement | Unknown effect consumes the slot; no reset, guessed job, discovery or retry |
| Collection | Full-width accounting, bounded complete/partial raw records, allowlisted archive, sidecar, external anchors and replay | Missing/corrupt/truncated observations remain negative; cached corruption blocks without replacement |
| Public wrapper | Validate action/SHA and deny new start; qualify prospective source/test/resume logic | No current observation, normal, adverse, native, h300 or repeat admission |

New reserved **software identity**, not a created NPAD claim:
`.mvp2-s2-profile-observation-v2`. It cannot reuse the consumed PR95 namespace
`.mvp2-s2-lifecycle-profile-v1` or any normal/production claim. Source clone naming,
plan/review schemas and archive identity are versioned separately. The new driver
reuses only historical bounded byte-format helpers (raw records, regular-file
prefix capture, archive packing and portable job/path validation). It never calls
the historical claim loader, dispatcher, collector or profile reviewer. These
format/allowlist equalities are regression assertions, not mutable global patches.

The proposed future observation envelope is unchanged: one node, two logical
CPUs,2048MiB,twelve minutes, account sxdsouza, partition intel-256, export NONE,
no requeue. It would have no srun, synthetic worker, solver, license check, IPC
release, prctl, affinity write, signal, cgroup write or host/security adjustment.
Its request ceiling would be0.4CPU-h/0.4GiB-h, not measured resource consumption
or a cleanup bound. It is not submitted or admitted by this package.

## Non-lossy diagnostics and independent interpretation

Each controller captures placement/mount_mapping/descriptor/hierarchy/inventory
as fixed-stage records with value, controlled error category and numeric errno
when the original operation exposes one. Exception text and private paths are
never diagnostics. Failed dependencies do not trigger fallback reads; independent
controllers and host channels continue. Inventory can still be attempted after
hierarchy failure when its descriptor is valid. Permission-policy failures inside
the historical kernel reader may surface as `invalid_evidence` without an errno;
this package does not invent an exact file or syscall in that case.

The independent screen still requires a measured zero namespace limit, matching
host/observer namespace identities, initial UID mapping, current owned allocation
and batch membership, complete visible root-owned/non-delegated/no-ACL cgroup-v1
hierarchies and matching recursive inventory anchors. Actual descriptor reads
check cgroup-v1 fstatfs. The two descriptor leaf roles intentionally refer to the
same batch observer; no worker/supervisor separation is claimed. Replay requires
the observed process identity to occur at the exact bound leaf, not somewhere
else in a matching parent tree. Whole-hierarchy permission facts are tied back to
the mount/job/leaf and inventory inodes, not accepted as an unrelated hierarchy.

The namespace-limit interpretation is explicit:

- `unavailable`: no valid limit value was captured; not proof of incompatibility.
- `observed_zero`: the unchanged zero-limit obligation was met for this snapshot.
- `observed_unsupported`: a valid positive value was measured; no automatic change.
- `invalid_evidence`: a purported value violates its schema; it cannot pass.

`capture_within_budget` and `channel_evidence_complete` are separate predicates.
The90-second cooperative deadline is checked before/after primitive reads; late
success is discarded and later reads are not invoked. Blocking syscalls remain
uninterruptible by this Python budget alone. Source-role checks and scheduler
queries are separate bounded components; the proposed scheduler envelope remains
twelve minutes. Complete facts may still violate policy and produce blockers.

Even `prerequisites_observed_not_admitted` keeps **every execution/cleanup flag
false**. Software fixtures remain `software_fixture_preserved_not_admitted` in
terminal replay. Worker hardening/peer binding, disjoint resources, parent
persistence/no escape throughout execution, quiet cleanup/cadence and NPAD/NFS
crash durability remain unproven. Fsync success is not a crash-durability certificate.

## Qualification and next owner

The exact integrated Linux cohort is608 cases: new observation/driver/wrapper,
closed PR96 diagnostics, original PR95 profile, release, adapter, protocol and
source identity. CI requires zero failures/errors/skips, actual Bash syntax/start
denial, disposable-directory fsync and physical source closure before/after.
Local Windows qualification reports601passed/seven explicit Linux-only skips;
it does not claim actual Bash/Linux primitives passed locally. Expanded regression,
source/blob/scope/link review and all six exact-head GitHub checks are recorded on
the PR. Tests contain synthetic identities only; no archived source is executed.

Next owner: agent finishes exact-head CI and Ready review, then requests separate
merge authorization. After integration, review one explicit **observation-only
operational admission** and complete pinned CLI handoff before any human run.
No CLI action is required now; this wrapper intentionally refuses new starts.
The admission review must retain the exact source, exclusive claim, full SHA/
wrapper checksum, unchanged envelope, status/wait/collect/transfer instructions
and a no-automatic-follow-on decision. A later negative observation requires
evidence-backed NPAD support or an explicit protocol decision, not another normal
retry loop or weakened scientific/security criteria.

S2 A/P2-P5 remains open. h400, bounded existing-SCIP h215, conditional h500 and
S6-A/S6-B remain planned; S3/S4 cancelled, EVPI/VSS excluded. Main/develop
reconciliation remains deferred until after article review. No model, formulation,
data, tolerance, scientific budget, manuscript or original certificate changes.
