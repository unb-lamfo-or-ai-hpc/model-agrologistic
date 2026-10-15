# S2 prerequisite job2211568: negative evidence and closed diagnostic correction

## Identity, integrity and preserved meaning

15 October 2026. PR #95 merged into develop at
`cdc14591acd6b4743aa925e446070afd5524107d`. The observation ran source
`0b98e01cfb7b5cc27e6500c5c223ff39b17800bd`, not the later merge identity.
The researcher supplied the original archive/sidecar and terminal accounting.
SHA256 matches both the sidecar and the reported checksum:
`61d9ecf4504619d48238a16f0a6d96a91157704b530d3eea106c6242a204b4ab`.

The original bounded auditor independently replays `blocked_environment`; the
five-member allowlist, raw record checksums, negative review and terminal root/
batch/extern accounting agree. These rows report COMPLETED/0:0/4seconds. Allocation
and batch-membership checks pass. No numeric worker step or optimization ran.
Scheduler success is successful preservation of the observation, not qualification
of the environment or scientific success. No performance conclusion follows.

All599 archived source-manifest SHA256 entries were separately compared with raw
Git blobs at the executed commit: all match. The plan digest is
`140259faf649cf1559df73ee5ecdf4c7d23db32f9263ed4939483dd441cf9b7a`.
It was read from the bundle and recomputed, not independently supplied as a new
NPAD attestation. Source/job/archive anchors are provided by the researcher and
checked separately; this provenance distinction remains explicit in the
[redacted derived review](evidence/s2_profile_2211568_review.json).
No raw archive, UID, PID, absolute scope, namespace inode or credential is committed.

## What the negative result actually establishes

| Observation | Supported conclusion | Unsupported inference |
| --- | --- | --- |
| Current allocation and batch membership passed | Expected allocation/ownership was observed | Normal worker containment or cleanup passed |
| Combined host channel unavailable | At least one host read failed; primitive/errno was not retained | max_user_namespaces is nonzero, namespaces differ, or NPAD is unsafe |
| Memory membership ends in step_batch/task_0 | The observer's direct-step-only assumption rejects this layout before controller I/O | The memory hierarchy was actually inspected and found writable |
| Freezer/cpuset membership ends in step_batch | Their pathname preconditions pass, but a later read/validation failed | Which primitive failed, its errno, or root cause is known |
| Capture elapsed0.039763497188687325s; no budget_exhausted channel | Capture was inside the90s cooperative budget | bounded_capture=false proves timeout |

The historical `bounded_capture` predicate is the conjunction of elapsed<90 and
all channels having no error. It is false here because evidence is incomplete,
not because capture exceeded the budget. Preserve its original false value; the
derived audit separates `capture_within_budget=true` from
`channel_evidence_complete=false`. Four channels failed:host/memory/freezer/cpuset.
Do not count six aggregate blockers as six independent established site defects.
The namespace/identity blocker depends on the unavailable host channel.

`KernelReader.host()` reads all PID1 namespace identities before the namespace
limit. If any early read fails, the channel loses its later independent value.
The packet contains no errno or failing primitive. Permission denial is plausible,
not demonstrated: Linux gates dereferencing namespace links through a ptrace
access check ([Linux namespaces manual](https://man7.org/linux/man-pages/man7/namespaces.7.html)).
Do not set the limit to zero, use sudo or weaken permissions on that hypothesis.

Controller paths may have different depths: cgroup-v1 supports independent
hierarchies and controller-specific task grouping, not a uniform role depth
([kernel cgroup-v1 guide](https://docs.kernel.org/admin-guide/cgroup-v1/cgroups.html)).
Here the additional memory task_0 leaf is directly recorded evidence. Recognizing
that syntax does not prove ownership, filesystem type, resource ceilings,
non-delegation, complete hierarchy coverage or persistence through cleanup.

## Complete closed software correction package

The [new diagnostic module](../scripts/mvp2_s2_profile_diagnostics.py) and
[regression](../tests/test_mvp2_s2_profile_diagnostics.py) qualify:

- Exact UID/job/step ancestry: direct batch leaves for memory/freezer/cpuset and
  the observed memory-only step_batch/task_0 layout. Other tasks, numeric worker
  steps, arbitrary descendants, path aliases, wrong jobs/UIDs/mounts are rejected.
- Independent injected host reads, so an unreadable namespace cannot erase a
  readable limit, nor an unreadable limit erase readable namespace facts.
- Fixed primitive-stage/errno diagnostics without exception text or private paths;
  no hidden fallback, retry, default reader or effect factory.
- Deadline and evidence-completeness separation; late success cannot become valid
  evidence, and expired reads are not invoked. Blocking syscalls remain unbounded
  by Python alone; no hard wall-clock guarantee is invented.
- Offline fixed-archive replay/redaction, source/job/checksum anchors and explicit
  plan-anchor provenance, without extraction or replacing historical receipts.

These are **closed components**, not an integrated operational observer. All direct
Python entries and execute verbs deny before I/O. No existing observer, launcher,
auditor, parser, worker, claim, wrapper, certificate or scientific setting is
modified. The zero-limit/namespace/hierarchy/quiet-cleanup requirements remain
unchanged. The observed failed result cannot be upgraded by the new path parser.
No new source/claim/execution slot or runnable NPAD command is supplied here.

Local focused qualification:159passed/one disclosed Linux-only skip. Actual archive
replay and599 original manifest/blob comparisons were performed outside the test
fixtures. Tests emulate redacted archive facts and injected reads; no Slurm,
kernel security change, worker, solver or license is exercised. Linux CI qualifies
the160-case diagnostic/profile cohort with zero failures/errors/skips and physical
source closure before/after. Expanded S2 and exact-head CI are recorded on the PR.

## Next gate and decisions

1. Finish this audit/closed correction PR, exact-head qualification and Ready review;
   obtain separate maintainer merge authorization. **No NPAD CLI now.**
2. Integrate the qualified diagnostics and exact memory layout into one complete
   prospective observational package, preserving old executables/claims/archives.
   Qualify its wrapper, stage-specific capture, independent replay and collection
   together before any proposed human execution. Do not repeat the PR95 job/source
   or assume these components opened a normal slot.
3. A later justified observation must distinguish unreadable prerequisites from
   observed unsupported values and identify the actual failing primitives. If the
   conservative profile is demonstrably unsupported or unobservable, seek NPAD
   support or an explicit reviewed protocol decision. No automatic sudo, sysctl,
   chmod, namespace change, security weakening or repeated-normal loop.

This observation does not justify reducing S2, admitting production, discarding
negative evidence or changing models/scientific tolerances. Full S2 A/P2-P5 and
later h400/SCIP-h215/conditional h500/S6 remain; S3/S4 cancelled, EVPI/VSS excluded,
main/develop synchronization only after article review. Original observation
claim, bootstrap, archive and sidecar must remain preserved.
