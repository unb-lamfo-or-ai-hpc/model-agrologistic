# S2-P1 continuation — separately qualified normal observation

## Why this gate exists

PR #66 merged into develop at `f51688b9692058e2d0a639125b65fb5f1ff805ac`.
It added bounded diagnostics, not a demonstrated repair of the NPAD failure.
Job 2207167 at source `12691638cd85d5218725bf704dc6b9452b1ca90c` failed
before worker launch. Its [original semantic records](evidence/s2-first-normal-2207167/records.json)
remain unchanged; archive SHA-256 is
`03ee4d87bf69994fc4f0401e206a67109539ad2dfe0770cd3246b7415e952007`.
The original v1 receipt cannot identify the failing guard. Root cause remains
unknown. Do not describe this gate as a successful fix, retry loop or containment
qualification. Its hypothesis is operational: a separately observed attempt at
the diagnostic implementation will either expose the failing phase/category/
reviewed code location or produce the original normal-case evidence for audit.
No scientific parameter, model or solver is changed.

## Admission boundary and preserved predecessor

Only `scripts/mvp2_s2_normal_recovery.py` opens this new fixed normal-only
boundary after exact-head qualification, authorized merge and human CLI.
Generic operational/batch/worker CLIs stay closed. No adverse case, native
miniature, h300, repeated block or solver execution is admitted. S2 remains open.

The consumed `.mvp2-s2-first-normal-v1` is never edited, deleted, reset or run
again. Before creating a new claim, the wrapper reads its eight bounded immutable
records, binds its original source/job/archive to committed public semantic
records, independently replays the old archive, and checks the old checkout's
raw HEAD bytes, rechecking executable hashes before invoking that Git reader.
It hashes the eight records before/after observation. Missing
files, source/runtime-baseline drift or inconsistent lineage stop advancement.
The old entry is never executed; no old job is queried or cancelled. An absent
old worker directory is not repaired: that failure occurred before its creation.

The new exclusive claim is `.mvp2-s2-normal-recovery-pr67-v1`, with a fresh short
`s2n-...` worker path and nonce, new source/runtime envelope and separate batch
and submission receipts. Its scope is `normal_recovery_only`. Predecessor
snapshot must remain identical at preparation, immediately before the single
submission effect, and on batch/worker/collection entry. An incomplete claim or
uncertain scheduler acknowledgement consumes the attempt. Repeating start on
an existing claim routes only to collection; collection cannot submit. There is
no cleanup/delete/retry command or fallback source. Hashes establish relative
integrity, not a security boundary against the same operating-system user.

## Limits and software qualification

Reuse the [first-normal protocol](mvp2_s2_first_normal.md) and
[operational contract](mvp2_s2_operational_protocol.md) unchanged: account sxdsouza,
partition intel-256, one node, one task/two CPUs, 2048 MiB, twelve minutes,
export NONE, no requeue, one normal worker step. Allocation ceiling is 0.4
core-hours, not measured consumption. Worker: one CPU/256 MiB, startup 30 s,
exercise 60 s, TERM grace 5 s, cleanup observation 390 s, quiet interval 5 s.
Batch preflight is bounded from entry at 120 s; parent reserve at 660 s.
User-space timeouts do not guarantee interruption of kernel/filesystem stalls.

The fresh observation must match PR63's audited Python/tool hashes, client
versions and selected declared settings. It must verify the new checkout/raw
HEAD, actual allocation, numeric step ownership, kernel-peer handshake, v1
cgroup membership/finite limits and durable exact-step stop/cleanup evidence.
No parser, path, resource or socket-length guard is relaxed to pass.

The shared supervision/collection implementation now has fixed internal seams
for the recovery entry, descriptor, transport and evidence carrier; defaults
retain the original first-normal behavior. These are not CLI options. Offline
qualification covers one effect, unknown acknowledgement, original-byte
preservation, lineage/release drift, old-run reuse prevention, worker identity,
scope denial, bounded diagnostics and malformed nested archives. Linux CI also
qualifies real local pipe/peer-credential paths, not Slurm containment. The driver
requires exactly 345 focused cases: 343 passed and two intentional non-Linux-only
negative CLI skips on Linux. Other counts/skips/failures block submission.

## Maintainer sequence — only after this gate is qualified and merged

The final PR audit supplies the full reviewed source SHA and driver SHA-256.
Transfer the committed `scripts/npad_s2_normal_recovery.sh` without editing it;
verify the supplied checksum. Do not substitute the old first-normal driver.
The new driver preserves its bootstrap, checks the merged-source ancestry and
clean checkout, runs lint/regression outside the checkout, then observes the
fresh raw-byte/runtime envelope. No package installation or license access is
needed. All NPAD commands are executed by the maintainer, not the agent.

```bash
bash npad_s2_normal_recovery.sh start FULL_REVIEWED_MERGED_SOURCE_SHA
```

If acknowledged, retain `JOB_ID`, `PRESERVE_CLAIM`, `PRESERVE_RUN` and the
bootstrap directory. The driver returns; it does not poll or chain another case.
An error or uncertain acknowledgement is not permission to delete/restart.
Observe only the printed job:

```bash
sacct -j THE_PRINTED_JOB_ID --format=JobID,State,Elapsed,ExitCode,MaxRSS
bash npad_s2_normal_recovery.sh collect FULL_REVIEWED_MERGED_SOURCE_SHA
```

If nonterminal/accounting-pending, repeat collect at the same source. If blocked,
preserve every original file and return the output for review; do not modify
claims, change source or submit another job. After terminal collection, transfer
only printed `DOWNLOAD` and `TRANSFER_CHECKSUM` with MobaXterm, reporting the
external SHA-256 and job ID. Terminal FAILED evidence must also be retained.

## Evidence and advancement criteria

The new `s2-normal-recovery-evidence.tar.gz` has exactly three bounded members:
`lineage.json`, `normal-evidence.tar.gz`, `review.json`. The lineage identifies
the original source/job/archive, the new source/job and the inner archive hash.
The inner carrier reuses the strict original accounting/anchor/operation/batch
review format, with v2 message-free diagnostics (or explicit missing receipt).
It does not rewrite or relabel the original archive. All future admission flags
remain false. Public carriers omit raw host paths, PID/node inventories, private
envelopes, exception text and licenses; those originals remain preserved on NPAD.
Bounded nested readers reject duplicate/extra/traversal/link members, oversize
expansion, nonzero trailers and scope/source/job/hash/sidecar drift.

Independent local audit, without extraction, execution or NPAD access:

```text
python -B -I scripts/mvp2_s2_normal_recovery.py audit --source-sha FULL_SOURCE_SHA --job JOB_ID --archive ARCHIVE --sha256 EXTERNALLY_RETAINED_SHA256
```

`integrity_replayed_not_live_qualified` means carrier consistency only. A normal
live decision additionally needs complete matching source/runtime/allocation/
step receipts, actual four-phase normal completion, replayed controller and
observed clean terminal membership/quiet interval. Scheduler COMPLETED alone,
unknown worker outcome, blocked_before_launch, missing evidence or a diagnostic
location does not qualify it. A negative result triggers a focused evidence-led
correction, never an automatic retry. Failures before a validated claim reaches
the shared batch diagnostic boundary may still lack a phase receipt; preserve
logs rather than claiming complete failure telemetry.

Even an accepted normal case does not qualify TERM-ignoring or session-detached
descendants. The next separate gate must audit this observation before admitting
bounded adverse qualification; only subsequent gates may reach the native
miniature and the full contracted h300 1/2/4/8/16-thread contrast. No S2 closure,
main/develop synchronization or later h400/SCIP/h500 admission occurs here.
