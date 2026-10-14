# S2 lifecycle-aware protocol: closed software qualification

Current software integration after PR #92 merge: the separately authorized
[independent environment verifier and closed operational adapter](mvp2_s2_lifecycle_integration.md)
implements conditional current read checks for the proof obligations below.
It does not change this original protocol or historical receipt, admit execution
or establish installed NPAD compatibility. All public effects stay closed;
original claims, evidence and budgets are preserved.

14 October 2026. Verified develop base after PR #91 merge:
`c838fd10c911cd2cf2e16c60eb9a46d578cc0269`. Authority: the maintainer authorized
**software qualification only**, preserving claims/evidence and blocking execution.
Read [PROJECT_STATE.md](../PROJECT_STATE.md) first. The
[job2210952 audit](mvp2_s2_fast_exit_2210952_audit.md) remains an unchanged historical
observation, not a certificate under this new prospective protocol.

## What this package implements

| Component | Implemented software responsibility | Explicitly not provided |
| --- | --- | --- |
| [Protocol/reducer](../scripts/mvp2_s2_lifecycle_protocol.py) | Strict versioned contract, role/parent bindings, live resource-gate reuse, descendant registry, post-exit checks, bounded hash-chained replay | IPC release, scheduler cancellation, process creation or live attestation |
| [Observer primitive](../scripts/mvp2_s2_lifecycle_observer.py) | Explicit bounded no-follow two-pass recursive local reads; independent channel capture preserves other evidence after a read failure | Default paths, mount discovery, scheduler query, proof of parent persistence or no escape |
| [Qualification wrapper/collector](../scripts/mvp2_s2_lifecycle_package.py) | Explicit callback seam, terminal identity binding, redacted semantic review, missing/rejected-journal forensics and readiness inventory | Real operational adapter, claim loader/reservation, filesystem writes, archive extraction or runnable normal CLI |
| [Regression](../tests/test_mvp2_s2_lifecycle_protocol.py) | Normal/four phase failures/nested descendant simulations, negative bindings/coverage, real disposable directory primitives and Linux own-process/no-follow checks | NPAD jobs, actual adverse process tree, solver or license exercise |

Every direct entry point, including start/collect/native/h300/retry verbs, denies
before imports or I/O. The exported execute function also denies immediately.
The package does not modify, monkeypatch, dispatch from or relax an older launcher,
worker, controller, release, archive reader or certificate. There is no live
transport factory or implicit environment fallback. S2 is not closed by this PR.

## Why the evidence modality is separate

Job2210952 observed unavailable memory/freezer/cpuset step scopes in five post-exit
samples; terminal accounting and products survived. The previous normal predicate
depended on those step directories remaining observable. Repeating unchanged
normal cannot repair the observed gap. This prospective version instead separates:

1. **Live enforcement:** independently obtained current job/source/nonce/process
   identity, bounded CPU-ID sets/initial affinity, inherited finite memory limits,
   disjoint role scopes and subsequent live samples must still pass. Reuse the
   strict [synthetic resource contract](mvp2_s2_synthetic_resource_contract.md).
2. **Post-exit closure evidence:** original step scopes may remain explicitly
   `missing` or `unavailable`; they are never recorded as observed empty. A distinct
   pre-bound, persistent allocation-level recursive inventory must still be valid.
   Exact-step terminal accounting, full tracked-identity absence, owned local-client
   reaping and quiet writes are separate necessary checks, not substitutes for it.

The new status `software_candidate_closed` means **the supplied qualification
trace satisfies software predicates**. It does not mean remote cleanup, successful
optimization, scientific acceptance or execution admission. Portable hashes bind
inputs; they cannot reconstruct omitted private facts or establish their truth.

## Mandatory external obligations, not self-certifying booleans

Before a future operational release, an independent verifier must establish:

- Current scheduler job ownership and source/runtime/IPC/kernel process binding.
- Actual cgroup-v1 mount/namespace, persistent parent identity and strict ancestry
  for memory, freezer and cpuset. Parent/worker/batch device/inode identities must
  not alias. Parent persistence must cover the cleanup window, not just two reads.
- Complete recursively observable controller coverage, no unrelated jobs/writers,
  and that unprivileged descendants cannot migrate/escape the covered hierarchy.
  A same-UID process, remembered PID, common prefix or shared cpuacct proves none
  of these. Permissions, capabilities, delegation and namespaces must be considered;
  mode bits alone and absence of a recorded escape are not proof of impossibility.

The schema requires externally bound evidence digests for each obligation, with
`checked_not_attested` status. Fixtures simulate those inputs. **This package
does not implement the environment verifier and does not turn an assurance hash
into a capability.** Readiness keeps `installed_persistent_observer_qualified`,
`live_adapter_implemented` and every admission flag false. A future adapter cannot
fill these records with constants, a configuration declaration or hashes copied
from an older run. Missing/unknown obligations must fail before worker release.
If these obligations cannot be established on NPAD, stop and report the limitation;
do not submit a loop of revised normal jobs or weaken coverage automatically.

The [Linux cgroup-v1 reference](https://docs.kernel.org/admin-guide/cgroup-v1/cgroups.html)
describes inherited membership, independent hierarchies and permission-dependent
migration; `cgroup.procs` may contain duplicate or unsorted TGIDs. The new explicit
reader sorts/deduplicates within one file while rejecting cross-group duplicates
as unstable traversal. No legacy parser changes. The
[Slurm cgroup guide](https://slurm.schedmd.com/cgroups.html) supplies general context,
not proof of installed Slurm22.05.11 lifetime, ownership or permissions.

## Identity, coverage and failure rules

Two independently supplied initial inventories must agree, include both bound
roles in their actual role subtrees, and agree across the three enforcement
controllers. The portable resource observation is bound to those role identities
and the separately recorded resource scope digest. Resource counters/limits stay
under the existing ResourceGate; shared cpuacct never becomes worker-attributed CPU.

The recursive reader uses explicit roots and process resolvers, bounded to128
groups, depth16 and64 unique members. It performs two complete reads and detects
missing files, links, device/inode changes, process reuse and membership movement.
Equal passes are **not atomic**, continuous monitoring or proof of persistence.
Those limitations remain independent live-verifier obligations.

Supervisor identity is immutable. At most one batch-shell and one owned local
srun-client identity may be pre-bound with explicit ownership-evidence digests;
they must occupy the supervisor subtree and cannot alias the worker. The local
client must be absent before closure even if a caller reports it reaped. There is
no broad UID, process-group, PID-range or command-name exemption. Short-lived
queries receive no exemption: the future transport must reap them before capture.
An unexpected query/member invalidates observation rather than disappearing from
the denominator. Independent role/ownership evidence is still required in reality.

Descendants are registered before acceptance, with stable PID/UID/starttime and
bound parent/ownership evidence. Parentage alone or a process group is not actual
scheduler ownership. A detached/TERM-ignoring descendant remains tracked even
after its leader exits. Unregistered/reused/migrated identities, missing/replaced
parents, controller disagreement, invalid resources and unreadable inventories
latch the reducer blocked; it cannot restart the quiet interval into acceptance.
Valid observations of a still-present or unobservable known PID do not count as
quiet and cannot be replaced by the leader's absence.

Post-exit resources are explicitly `null`, not fabricated from a cached live
snapshot. The continuing parent inventory is mandatory. Phase products retain
the original nonce/case/order validation. The write inventory includes all fixed
worker product names, heartbeat and pending heartbeat, not just a terminal receipt.
Missing products prevent quiet; changing heartbeat/write fingerprints restart
the full interval. Invalid nonce/phase/write bindings block. The supervisor-owned
files and any unexpected writers must be handled by the independent runtime
verifier, not implicitly excluded by this reducer.

## Budgets and clocks

The proposed version retains allocation2CPUs/2048MiB/720s, worker request1CPU/
256MiB, at-most-two-logical-CPU hard envelope, initial affinity1CPU, startup30s,
exercise60s, TERM grace5s, cleanup390s and quiet5s/minimum3samples. It preserves the
diagnostic adapter's maximum5-second sampling gap. Registry/end events cannot mask
a resource-sampling gap. Times are finite monotonic seconds relative to the same
parent epoch; rollback/nonprogress/gaps cannot satisfy acceptance. Cleanup/global
deadlines precede late positive observations. No signal or timing extension is
executed by the reducer. P3 still has to reconcile390s with h300's300s grace.

## Terminal and forensic handoff

The collector is a pure function over an explicit contract/journal/terminal text,
externally bound source commit, job, contract digest and expected journal digest.
It requires root, batch and the exact numeric step terminal (and extern if present).
Recorded terminal step state/code cannot contradict final accounting. Hash-chain
order, event grammar and each reducer transition are independently replayed.
An incomplete valid prefix remains incomplete, not a completed cleanup.

Missing/corrupt/mismatched journals retain negative metadata; originals are never
edited and no missing event/claim is reconstructed. Returned public reviews have
only digests/counts/states and false admission flags; private journals contain
scope paths/PIDs and must remain private. No raw journal or HPC archive is committed
or uploaded by this PR. It creates no operational claim or future execution slot.

## Qualification and next owner

Focused local qualification:198 passed, one disclosed Linux-specific skip on
Windows/Python3.13; includes the new prospective protocol, unchanged resource gate
and job2210952 auditor. Linux CI qualifies the real local no-follow/own-process
primitive plus clean exported physical source closure. Expanded S2 regression and
all six exact-head repository checks must complete before Ready. No licensed
solver or NPAD workload was exercised. Final results are recorded in the PR.

After Ready, request separate merge authorization. Then integrate/qualify the
independent environment verifier, real source/runtime/IPC/transport binding and
terminal/forensic operational package while keeping execution closed. The live
release must be reviewed separately, use a fresh exclusive claim, preserve old
claims and provide complete pinned human commands together. **No NPAD CLI now.**
Do not mistake this software qualification for adopting the replacement live
criterion or proving NPAD support. Full normal A/P2-P5 and later scientific scope
remain; S3/S4 cancelled, EVPI/VSS excluded, main/develop sync after article review.
