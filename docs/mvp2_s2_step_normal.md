# S2: step-format-corrected normal attempt, ready to leave unattended

## Recovery carrier selection repair — 13 October 2026

The PR #77 bootstrap at `0f627f0779864ec5220d1e94b57e4bb6a6514433`
passed 948 tests/two intentional platform skips and source inventory, then
stopped in `discover_reference`, before claim reservation or scheduler effect.
The maintainer's subsequent read-only inventory reports **two carriers with
the same expected SHA-256**: `64617380256e8cf3c5031ef87fb3d71d9526d923e69e100c5140879a60ad34e3`.
This establishes path ambiguity, not archive corruption, a solver failure or
live normal acceptance. The old error conflated zero and multiple matches.
Printing `PRESERVE_CLAIM` alone does not establish claim existence.

This focused repair retains unique automatic discovery but adds explicit
`--recovery-archive` selection for login `reference`/fresh `start` only. Every
selected carrier still passes the same bounded location/link, exact archive and
replay hashes, member inventory and original-byte checks. There is no first/newest
match heuristic, hash replacement, missing-path fallback or deletion of duplicates.
Use the earlier audited collection's exact path in the pinned human handoff.

The bootstrap's optional third argument is the exact archive path. A read-only
reference check runs **before regression**, then fresh start checks/seals that
selection again before reservation. `reference` creates only a fresh bootstrap
checkout; it creates no submission claim and calls no scheduler or solver.
It verifies negative predecessor integrity, not live containment qualification.
An existing claim cannot accept a different selection: omit the third argument
and collect using its frozen source/reference. No new claim/versioned executor
is needed for this pre-reservation failure; no existing claim may be removed.

After exact-head qualification and authorized merge, publish pinned download,
explicit-path start, status and collect together. Preserve the failed bootstrap
and both carriers. The campaign PR #79 remains independent and unmerged pending
this operational correction; its old execution pin must be reconciled later.
There is still no adverse/native/h300/repeat admission or resource-policy change.

## Scope and execution decision

Base: PR #76 integrated at `0602edf3743cd3253b8253492d4098b65c4a0c9e`.
The maintainer requests preparation before a pause, preferably long jobs. No
long optimization is admitted here: job 2208459 remains a negative unbound
attempt, and the mandatory normal/adverse/native gates have not passed live.
Extending a synthetic test just to occupy four hours would not qualify h300.
The existing h300 optimization window remains 1800 seconds, not four hours.

This functional gate prepares **one normal synthetic job**, one node, two CPUs,
2048 MiB, twelve-minute allocation, no requeue, no solver or license operation.
The previous operational limits, strict peer/cgroup checks and scientific
parameters are unchanged. After exact-head qualification, Ready and authorized
merge, provide the pinned bootstrap to the maintainer. Only the maintainer runs
NPAD commands. No adverse/native/h300 job or automatic chained job follows.

The job executes independently of the login session after the scheduler returns
an acknowledged job ID. Evidence is written durably. The maintainer can leave
and collect after the pause; a twelve-minute allocation is a maximum, not a
promise of twelve minutes of work. Disconnecting before acknowledgement can
leave an unknown-effect claim: preserve it and inspect, never reset or resubmit.

## Immutable predecessor and complete lifecycle

- Bootstrap `scripts/npad_s2_step_normal.sh`; entry
  `scripts/mvp2_s2_step_normal.py`; distinct claim `.mvp2-s2-step-normal-v1`.
- Fresh source prefix `s2-step-driver-`; raw HEAD and complete physical source
  closure before/after regression. No runtime upgrade or old source mutation.
- Without explicit selection, the reader requires exactly one `s2-node-recovery-2208459-*` carrier beneath
  the fixed experiment base. Its checksum must equal
  `64617380256e8cf3c5031ef87fb3d71d9526d923e69e100c5140879a60ad34e3`.
  Absence or ambiguity reports the count and blocks before submission; do not
  guess/delete candidates. Explicit selection does not relax checksum validation.
- The carrier's inventory, nested replay, empty stderr and original live files
  are checked read-only. Original proposal/release/source binding is retained.
  The release seals this reference alongside the existing four earlier attempts
  and allocation diagnostic. Compute rechecks bytes without historical Git or
  importing an old checkout. New source/run/job must differ from job 2208459.
- Exclusive claim and durable intent precede the single `sbatch`. Unknown
  acknowledgement consumes the claim. Existing claim routes only to collection.
- Batch/worker reuse the shared corrected adapter, numeric step UID, node count
  plus exact host, cancellation grammar, membership and containment controls.
- Portable collection retains a bounded message-free operation diagnostic
  (stage/category/module/line), if present. Arbitrary messages/paths are rejected.
  Partial/negative results and unknown cleanup are not promoted to success.
- A new versioned wrapper avoids monkeypatching shared globals or rewriting
  the old entry and receipts. Core containment, source/runtime checks and
  independent review remain shared. No general architecture migration is made.

## Qualification and human handoff

NPAD pre-submission gate after this repair: **964 cases; 962 passes and exactly two existing
non-Linux-only negative CLI skips**, zero failures/errors. It includes PR #76's
63 recovery cases and 31 upstream-format cases, plus 86 successor cases
(72 existing and 14 carrier-selection regressions).
Linux CI validates exact counts, source closure and Bash syntax; tests inject
scheduler effects and do not establish installed NPAD success.

After merge, publish source SHA and bootstrap SHA-256 together with complete
download/start, status and collect commands. Commands must be copy-safe single
lines or a downloadable script; avoid requiring the maintainer to paste heredocs.
`start` on an existing claim collects only; `collect` never reserves or submits.
Use the frozen source printed by the bootstrap after reconnecting. A terminal
job can be collected later without leaving an SSH polling loop running.

Transfer `DOWNLOAD` and `TRANSFER_CHECKSUM`. Acceptance requires actual normal
binding/contract, phase and terminal evidence plus independent containment
review; scheduler COMPLETED, archive integrity and CI are insufficient alone.
Even normal acceptance does not automatically admit adverse or native jobs.

## Next useful long-running work

After live normal audit, qualify adverse containment and the licensed miniature,
then admit the homogeneous h300 thread contrast. Longer scientific allocations
require a reviewed profile and resource budget derived from that evidence.
There is no sleep loop, repeated dummy workload, unreviewed solver run or
automatic follow-on submission merely to fill the pause. Full S2 remains open;
S3/S4 stay cancelled, with approved h400/SCIP/h500/S6 scope unchanged.
