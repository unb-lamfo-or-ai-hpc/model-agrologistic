# S2 closed compute integration and collection qualification

## Scope and base

PR #68 merged into develop at `a2501f81cd4c45916b09227a378fe1505e97e190`.
This successor connects its identity components to the normal batch, worker,
adapter and collection paths. It is an **offline integration gate**, not a
new NPAD admission. The new module's CLI refuses execution before imports;
there is no start command, submission wrapper or retry. Its proposed worker
argv remains non-runnable until a separately reviewed driver is integrated.

The two consumed claims and original archives remain unchanged. The observed
failure of job 2207181 is described in the [original evidence ledger](evidence/s2-normal-recovery-2207181/README.md).
Neither integrity replay nor these tests establish live containment.

## Integrated boundaries

| Boundary | Required verification | Failure disposition |
| --- | --- | --- |
| Login seal | Existing strict envelope/runtime checks and raw Git HEAD comparison; original archive replay for both failed attempts; complete source manifests and immutable record hashes | No claim/job is created by sealing |
| Private release | Externally retained release digest; current normal plan; both fixed predecessor source/job/archive identities; separate current checkout/run/job; complete manifest closure | Reject drift, reused identities, omitted records or extra keys |
| Batch entry | Linux/Python host; current and historical source bytes and record/archive hashes without Git; current Python and four required Slurm executable hashes; actual entry/interpreter location; job and immutable claim binding | Exclusive batch claim; message-free early diagnostic; no legacy predecessor dispatch |
| Shared batch and adapter | Fixed Git-free runtime/source hooks; compute transport rejects source commands; original allocation/IPC/numeric-step/controller/cleanup checks remain | No fallback executable or weakened byte identity |
| Worker entry | Same sealed history/source verification; Python identity only, not batch-only Slurm tools; actual entry location and job/spec binding; existing durable run claim | Write-once role receipt, then existing worker-plan and kernel-peer dispatcher |
| Collection | Terminal root/batch accounting; immutable release; original attempt/operation and worker identity when bound; bounded stdout/stderr diagnostics | Missing receipts stay missing; no invented worker outcome or live acceptance |

The release digest is supplied from a future immutable reviewed driver/claim;
computing a candidate's own digest is not an external trust anchor. Hashes prove
relative integrity, not resistance to a malicious same-UID writer. Startup
checks retain the 120-second userspace budget; filesystem operations do not
acquire a hard kernel timeout from that check. The release is capped at 1 MiB;
each full source tree retains the PR68 count/file/total bounds. Tests and caches
must remain outside pinned source trees, with Python bytecode writes disabled.

12 October correction: current executable source still requires complete physical
closure. Both frozen historical entries now use a distinct tracked-source schema
and read-only verifier: login retains original Git/HEAD checks, compute rereads
every sealed tracked file plus bound records/archives without Git. Ignored historical
caches remain untouched and outside the manifest; historical code is not imported
or executed. A historical manifest cannot substitute for current admission.
This is an evidence/execution distinction, not a global cache exemption. See
[bytecode recovery](mvp2_s2_compute_normal.md#bytecode-recovery--12-october-2026).

## Evidence semantics

- `s2-compute-runtime-v1` explicitly distinguishes batch from worker. Batch
  records Python and srun/scontrol/scancel/sacct; worker records Python and an
  empty Slurm-tool map. Git/sbatch remain login-only. Missing or changed
  required executables block, rather than selecting a replacement from PATH.
- New adapter attempts and bundle reviews use v2; operational sidecars use
  `s2-normal-collection-v2`. Existing callers default to v1. Legacy readers
  reject v2; the new reader rejects a v1 attempt or a fabricated Git observation.
- The new closed collector creates an exclusive `s2-compute-evidence.tar.gz`
  and checksum, replays its public `collection.json`/`review.json`, and never
  edits the original claim/run. The external spec/release/source anchors remain
  required by replay; private envelopes and paths are not exported in the carrier.
- Raw scheduler logs remain private. At most 16 KiB per log is inspected; only
  allowlisted, message-free entry diagnostics, byte counts and file hashes are
  exported. Absence and absence of a structured diagnostic are different states.
  Oversize, unsafe or malformed structured logs reject collection, not silently
  truncate it. Abrupt/import/interpreter failure can still leave no diagnostic.
- A missing attempt is `no_attempt_receipt`, not successful containment.
  An incomplete journal cannot be packaged as a complete attempt; preserve it
  for forensic review. All future admission and live-containment flags stay false.

## Qualification and remaining admission work

The dedicated suite qualifies strict release/history binding, role-specific
runtime drift, forbidden compute Git paths, both entry boundaries, fixed
batch/worker composition, duplicate claims, worker identity persistence,
message redaction, missing/oversize diagnostics, negative archive round-trip,
checksum/tamper rejection and v2 controller-bundle replay. Effectful Slurm,
cgroup observations and worker dispatch are faked. Existing real local Linux
IPC/pipe and disposable Git/source tests remain in CI; none launches an NPAD job.

The next gate must freeze one **new** normal-only admission driver and source,
persist the sealed release before publishing its job release, bind the digest
through both executable entries, qualify actual CLI wiring and one-shot unknown
acknowledgement/collection behavior, and provide complete pinned human commands.
It must not reuse either consumed claim or run altered code in an old checkout.
Only after review, authorized merge and explicit human CLI may a fresh normal
observation run. Independent terminal audit precedes adverse/native/h300 gates.

Successor: [one-shot normal operational gate](mvp2_s2_compute_normal.md).
The integration itself remains a closed component. The successor supplies the
separately reviewed public driver; old standalone entry points are not reopened.

No scientific parameter, model, manifest, solver, license or resource request
changes here. S2 remains open, including the h300 1/2/4/8/16-thread contrast.
S3/S4 remain cancelled. h400, existing SCIP/h215, conditional h500 and S6 retain
the [approved roadmap](mvp2_hpc_roadmap.md). Main/develop synchronization stays
at the separately authorized S2 closure.
