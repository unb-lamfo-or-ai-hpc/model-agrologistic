# S2 job2210952: observed fast-exit boundary, no cleanup admission

14 October 2026. PR #90 merged at
`e2a40c8f1e6d87d82cbe7edbef370e78145f0024`; execution source remains
`021ba83d99132c5b872873439ae00cc82aec3793`, not the subsequent audit source.
Authority: [checkpoint](../PROJECT_STATE.md) and [operational completion plan](mvp2_s2_operational_completion.md).

## External identity and independently replayed evidence

- Archive SHA256: `e3c01f0b5db22b99b61b3a214eee42a694d1893d0f52c5b9b370d6a486b7561d`.
- Plan SHA256: `bd1b423377bf4aaaacf2fa6e5a03f1c2e6bb0c3cef4d6c044c81e504be720359`.
- Job2210952, exact numeric step0, one consumed fast-exit-observation claim.

Transferred archive bytes, sidecar and external source/job/plan identities agree.
The bounded reader verifies exact archive inventory, structured metadata,
independent channel grammar, exact terminal accounting and false admission flags.
The [read-only outcome interpreter](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/5f9daa55b3afb5bbcb3449bc83c970cf10a28ca6/scripts/mvp2_s2_fast_exit_audit.py) rechecks
the same archive bytes and generates the [redacted public review](evidence/s2_fast_exit_2210952_review.json).
No archive extraction, original writes, scheduler action, license access, source
relabeling or remote attestation is involved. CI tests fake carriers and public
metadata; the private raw archive is not available to CI or committed in Git.

## Observed result

The observer reached `observed_not_admitted` without a recorded exception.
Local srun returned0. Final root/batch/extern accounting is COMPLETED0:0 at14s;
the worker step is COMPLETED0:0 at one reported second. The supplied sacct screen
also reports two allocated CPUs; the portable final accounting schema does not
retain that CPU field. Scheduler clocks are not the exact worker exit clock.

| Channel | All five post-client-reaping observations | Interpretation |
| --- | --- | --- |
| memory/freezer/cpuset directories | Missing, value null | Original step scopes no longer readable by the observer; not observed empty |
| Exact listpids / show-step | Unavailable, value null | No valid live membership/step response; exact underlying RPC reason is not exported |
| Bound step accounting | COMPLETED0:0, elapsed1s | Terminal step evidence, not independent containment/cleanup proof |
| Known leader | Known PID absent | No proof that all descendants are absent |
| Products | Four phase receipts and terminal receipt available; hashes unchanged | Producer-reported validated stdlib products survive other-channel failure; not a native optimization or raw-product revalidation |
| cpuacct | Readable shared scope; five direct members | Not worker-only membership or attributable CPU usage |

Actual observation start offsets are0.0000588009,1.0001037968,3.0001000902,
6.0000996459 and10.0001028832seconds after owned local-client reaping. These are
five samples of one run, not five independent experiments or an exact kernel
exit-time reconstruction. Outer controllers-channel success does not mean every
controller is available; its per-controller missing states remain explicit.

Initially the producer reports disjoint memory/freezer/cpuset role scopes and
shared cpuacct. Both role cpusets contain two logical CPUs. Direct memory limit
values are9223372036854771712bytes (the unlimited sentinel); inherited ceilings
are268435456bytes(worker) and2147483648bytes(supervisor). Effective initial
ceilings are therefore256MiB and2048MiB, not unlimited. Initial affinity was
checked by the producer's gate but is not separately exported in this carrier.
The limits are not full-run peaks or evidence of sustained sampling coverage.
The supplied MaxRSS fields must not be promoted to a complete process-tree peak.

Raw product contents/nonce, private scope paths, pre-exit directory inventory and
exact post-exit RPC diagnostics are not in the portable carrier. The audit can
verify archive integrity and reported observations, not independently reconstruct
those omitted raw facts. The original private run/source/claim remain preserved.

## What this resolves, and what it does not

The limited observation accomplished its question: in this run the relevant
step scopes are unavailable after exit, while products/accounting remain usable.
The unchanged normal controller requires retained, valid membership/resource
scopes plus a five-second quiet proof. These observations cannot satisfy that
predicate. Another identical normal submission is therefore not justified.

This is consistent with scheduler-managed step lifecycle, but does not prove
which actor removed a directory, why each RPC failed, that every future NPAD
node behaves identically, or what exact exception caused job2210506. Its original
[negative audit](mvp2_s2_normal_2210506_audit.md), checksum and claims remain
unchanged. Four stdlib phases are not native MILP phases;14s versus the older
395s is not a speedup comparison. S2 normal A and P2-P5 are still open.

## Protocol decision required before the next normal release

**No criterion change is implemented or approved in this audit.** Its merge is
only evidence/checkpoint integration, not approval of the proposal below.

### A. Recommended: qualify a separate lifecycle-aware protocol (requires authority)

Prepare one complete, versioned software package that separates two questions:

1. During execution, independently establish current job/step/source/PID binding,
   live worker enforcement, finite inherited memory/CPU limits and observable
   resource samples. Unknown/drift continues to block.
2. Before releasing the leaf, bind a genuinely persistent allocation-level scope
   and recursive descendant observer for enforcement/tracking controllers. Prove
   its actual identity, ownership, coverage, exclusion of unrelated jobs, and that
   unprivileged descendants cannot escape/migrate outside the covered hierarchy.
   An inferred pathname, unbound parent, shared cpuacct or known-PID list is not
   sufficient. Persistence and permissions have not been demonstrated by this run.
3. After exit, keep missing step scopes explicitly unobservable. A new closure
   proof would require that independently bound persistent inventory, exact-step
   terminal evidence, stable identities/absence for tracked processes, unchanged
   products and the quiet interval. The supervisor/batch and its own short-lived
   query processes require explicit identity-bound accounting, not a broad PID/UID
   exclusion. Unknown members, replacement, unreadable parent, escaping setsid
   descendants, ambiguous ownership or incomplete coverage must block.
4. Qualify normal and all five adverse paths with fakes/real local primitives,
   versioned receipts, independent replay and negative tests. Keep the existing
   five-second quiet and390-second cleanup budgets unless separately reviewed;
   P3 must still reconcile compatibility with h300's300-second grace.

This is an engineering hypothesis, not an accepted equivalent proof or a promise
that the installed NPAD environment supports it. It changes the evidence modality
and therefore requires an explicit protocol decision. It must not be implemented
as terminal-only acceptance or missing-to-empty substitution. No artificial worker
linger, memory/thread/scientific change, extra solver or automatic repeat is added.

After explicit authority, qualify adapter + wrapper + tests + release/collection
in one functional PR. Only then propose a separately bounded human normal attempt
with a fresh claim and fail-before-release environment gate. No additional live
observation campaign is presumed; if the proposed persistent observer cannot be
qualified, stop with evidence rather than repeatedly submitting corrected jobs.

### B. Retain the existing criterion and seek appropriate NPAD infrastructure

If the researcher does not authorize A, the current criterion remains binding.
Seek NPAD confirmation of an appropriately persistent isolated observable scope
with suitable permissions/lifecycle guarantees. Availability and cost are unknown;
no cgroup administration, package upgrade or new job is authorized here. A worker
linger alone neither meets the original post-exit proof nor proves descendant
cleanup, so it is not recommended as a shortcut.

### Source boundary

The [Linux cgroup-v1 reference](https://docs.kernel.org/admin-guide/cgroup-v1/cgroups.html)
describes inherited task groups, separate controller hierarchies and permission-
dependent migration. The [Slurm cgroup guide](https://slurm.schedmd.com/cgroups.html)
describes scheduler cgroup integration. These primary references inform the
proposal, not proof of the installed Slurm22.05.11 configuration, ownership or
scope persistence. No kernel-deletion theorem is inferred from a missing path.

## Remaining sequence and next owner

Finish this audit PR's software qualification and Ready review; ask separately
for merge and explicit authorization to qualify optionA, or direction to retainB.
No NPAD CLI action is needed now. While preserving the closed eleven-slot P2-P4
inventory, do not add an operational executor that presumes the protocol decision.
After the decision: complete normal A/audit, five adverse P2, licensed integrated
native P3, homogeneous h300 P4(4/1/8/2/16), comparison/exit P5. Native budget and
cleanup compatibility remain pending. Later h400/SCIP-h215/conditional h500/S6,
S3/S4 cancellation, EVPI/VSS exclusion and post-article main synchronization remain.
