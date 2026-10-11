# S2 correction: distinguish login identity from compute requirements

## Evidence-led objective

[Job 2207181](evidence/s2-normal-recovery-2207181/README.md) failed while hashing
`/usr/bin/git` on its batch node, before the shared diagnostic boundary. This
specific absence was reported from existing stderr; the independently audited
carrier establishes FAILED/missing receipt, not the exception by itself.

The correction is not to disable source validation or install an unqualified
Git runtime. Git provenance belongs to preparation on the login host. The batch
must independently verify the exact files it will use and its actual runtime
tools. Old login receipts must not be relabeled as compute observations.

## Implemented, closed components

`scripts/mvp2_s2_compute_identity.py` has no runnable admission, launcher, scheduler
query, retry or worker interface. Its standalone CLI denies execution.

| Role | Identity obligation |
| --- | --- |
| Login preparation | Verify Git executable hash; existing raw HEAD/clean-index gate compares every tracked file to its Git blob; seal the complete file-hash map and source commit; recheck actual bytes, inventory and HEAD before returning |
| Batch compute | Check externally bound manifest digest/source; reread every file and compare aggregate/worker identity; reject missing, changed, extra/shadow files, unreviewed directories, links and oversize trees; no Git process or executable access |
| Batch runtime | Check exact Python and srun/scontrol/scancel/sacct hashes; report precisely these verified tools under a new role-specific schema, never pretend Git/sbatch were checked on compute |

Limits retain 1024 tracked files, 8 MiB/file, 32 MiB total. Only the checkout's
real `.git` directory is excluded from the compute content walk. Ignored cache
files are not automatically safe: `__pycache__`/shadow files are rejected. The
future pinned checkout must use `-B` and keep tests/products outside it. This
does not change the existing raw-HEAD algorithm or relax source byte comparison.
The external manifest digest must come from the immutable admitted claim, not
be recomputed from the candidate and called trustworthy. Hashes are relative
integrity checks, not protection against a malicious same-UID owner or mutations
after checking. Existing ownership, bounded startup and source admission remain
necessary. No hard kernel/filesystem timeout is promised.

Recovery `batch` now covers require_host/load_claim/exclusive batch claim errors
before entering shared supervision. It emits a bounded message-free JSON line
to stderr and exits 2; it does not write to an unvalidated claim, fabricate a
terminal receipt, launch a worker or continue after failure. Unknown exception
types are reduced to `unexpected_error`; raw exception text/paths are omitted.
Module-import/interpreter failures and abrupt termination can still lack this
record. Preserve scheduler stdout/stderr in the next bounded collection design.
Existing v1/v2 archive replay and the consumed PR67 driver remain unchanged.

## Offline qualification and explicit unfinished integration

Tests include actual isolated-Python missing-file failure, source tampering and
shadow files, runtime absence/drift, no-command compute verification, redaction,
exclusive claim failure, and a Linux disposable real-Git seal followed by
Git-free compute verification. These do not exercise Slurm or prove containment.

The next scoped integration must, before any fresh normal admission:

1. bind both preserved predecessors and the sealed manifest to a new immutable
   claim and source; never run altered code against consumed claims;
2. use the Git-free path at batch AND worker entry, including predecessor
   validation, shared runtime/source checks and adapter preflight; leaving even
   one legacy Git recheck is not a repair;
3. separate actual role-specific runtime receipts in the new evidence schema
   and audit them without changing historical v1/v2 semantics;
4. capture bounded early diagnostics and preserve absence explicitly, qualify
   missing/drifted compute tools and interruption end to end in CI;
5. freeze one normal-only source/driver after review, authorized merge and
   explicit human CLI. No new source/claim/job is admitted by this component PR.

Missing required compute Slurm tools must block; they have not been inventoried
by this failure. Do not infer their availability from login or fall back to
another executable. Resource/cgroup/IPC/exact-step/cleanup checks stay intact.
This correction is necessary but not yet integrated into a successor live
protocol. No normal/adverse/native/h300/repeat execution or main synchronization
is authorized here. Full S2 remains open; scientific parameters are unchanged.
