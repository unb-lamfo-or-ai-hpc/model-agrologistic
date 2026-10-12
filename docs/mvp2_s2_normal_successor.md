# S2: one-shot normal successor after the Slurm client correction

12 October 2026. Integration base: PR #72, merged into develop at
`7005b08e596ac47df3d9a9d6af13c2c563f07d64` after explicit authorization and
four successful exact-head checks. This is a complete operational gate, not an
extra helper-only milestone. It is not evidence of a new live observation.

## Fixed scope and prerequisites

The only proposed execution is one normal standard-library synthetic observation.
Keep batch resources at one node, two CPUs, 2048 MiB and twelve minutes, with
the reviewed account/partition, no requeue and no inherited environment export.
Worker scope remains one exact numeric step, one CPU, 256 MiB and nine minutes.
No solver, license probe, optimization data, adverse case, native miniature,
h300 run or repeat is admitted. No model/scientific parameter changes.

Preserve the claims, checkouts and evidence for jobs 2207167, 2207181 and
[2208056](evidence/s2-compute-normal-2208056/README.md). The last claim is
consumed, not reusable. The fixed new claim is `.mvp2-s2-normal-successor-v1`.
There is no caller-selectable claim name, reset switch or retry route.
Absence, corruption or inconsistent evidence blocks preparation; never repair
historical receipts or delete a claim to make the driver proceed.

## Complete operational chain

1. `npad_s2_normal_successor.sh` clones a fresh pinned source already merged
   into develop. Raw HEAD and all physical current-source bytes are checked.
   The eleven-suite regression writes outside source and runs with explicit
   bytecode prevention; post-regression physical closure is mandatory.
2. Login seals current source and the two existing historical records. The new
   predecessor reader independently replays the original job 2208056 archive
   against its fixed SHA, source, job, release and specification digests. It
   reconciles original proposal, submission intent/script, acknowledgement,
   wrapper and log digests. Its original sealed source inventory becomes
   historical tracked-byte data; caches are neither trusted nor deleted.
3. `s2-normal-successor-release-v1` requires all three histories. It reuses the
   unchanged v1 structural/runtime rules for the current source and first two
   predecessors, then enforces the exact third identity and distinct current
   run, job, checkout and commit. Batch and worker verify all sealed history
   bytes without Git, scheduler re-probing of history or importing old sources.
4. One exclusive claim is persisted before one sbatch effect. Proposal digest
   is embedded in batch command; only the acknowledged job changes in release.
   Release is durable before `job.json`. A fast batch waits at most thirty
   seconds. Interruption, missing/ambiguous acknowledgement or unknown effect
   consumes the claim. An existing claim routes to collection, never resubmission.
5. Normal batch/worker entry points use shared identity, adapter, IPC and exact
   step controller code. The Slurm decimal batch alias and descendant grammar
   corrected in PR #72 apply. Reserved IDs are still prohibited worker/signal
   targets. A schema-bound claim check rejects the old claim for new releases.
6. Terminal collection uses only the acknowledged job. Nonterminal or incomplete
   accounting produces no terminal carrier. Cached collections are replayed;
   malformed or inconsistent partial data stops without inventing a result.

The original `mvp2_s2_compute_normal.py` wrapper/reader is unchanged. The new
versioned wrapper intentionally keeps explicit action wiring and archive names;
shared containment, identity and transport are not forked. No module-global
claim swapping or execution of preserved code is used.

## Evidence and interpretation

New carrier: `s2-normal-successor-evidence.tar.gz` and matching `.sha256`.
Only `anchor.json`, `collection.json` and `review.json` are exported. Anchor and
review schemas are distinct from the old carrier. The public anchor includes
all three fixed predecessor identities, including the old release digest.
Private source inventories, claims, raw logs, credentials and local paths stay
on NPAD. Early diagnostics remain allowlisted and message-free.

`no_attempt_receipt` means the operational attempt did not reach a retained
adapter receipt. `integrity_replayed_not_live_qualified` is an integrity replay,
not live acceptance. COMPLETED/0:0 alone is insufficient. Independent review
must inspect source/runtime identity, actual kernel peer and numeric step,
normal outcome, controller observations, terminal cohort and cleanup. Every
future admission flag remains false even after collection. No automatic adverse
test, native execution, production, repeat or S2 closure follows.

## Qualification and human handoff

The pinned regression is 597 cases: on Linux, 595 passes and the same two named
non-Linux-only negative-path skips. The local Windows run reports 594 passes
and three POSIX/kernel capability skips (597 total); these are not the Linux
skip set. New cases cover predecessor/claim
tampering, three-history compute verification, actual carrier replay, immutable
submission, uncertain effects, stop latches, real CLI denial, versioned packing,
cached collection and actual shared batch claim selection. Fakes replace effects,
not a live NPAD test. Full Linux CI and source closure remain required.

Merge requires explicit authorization after the final head is Ready and all
checks pass. A separate maintainer decision authorizes the one normal CLI.
The final PR comment freezes the source SHA and shell checksum; do not execute
a moving branch-head script or substitute a merge SHA. The complete handoff
must include:

1. Download the tracked driver from its immutable commit URL into an exclusive
   directory; verify its published SHA-256 before execution (MobaXterm optional).
2. Run `bash npad_s2_normal_successor.sh start FULL_REVIEWED_SOURCE_SHA`.
3. Save printed `JOB_ID`, `PROPOSAL_SHA256`, `RELEASE_SHA256`, claim and bootstrap.
   Use `sacct -j JOB_ID --format=JobID,State,Elapsed,ExitCode,MaxRSS` for status.
4. Run the same driver with `collect FULL_REVIEWED_SOURCE_SHA` until terminal
   accounting. Repeating start also collects; neither resumes optimization nor
   submits another job. If an unknown acknowledgement is reported, stop and
   preserve the claim for read-only diagnosis instead.
5. Transfer the exact `DOWNLOAD` and `TRANSFER_CHECKSUM` with MobaXterm, report
   printed hashes and submit them for independent audit using the new reader:

```text
python -B -I scripts/mvp2_s2_normal_successor.py audit
  --source-sha FULL_REVIEWED_SOURCE_SHA --job ACKNOWLEDGED_JOB_ID
  --release-sha ACKNOWLEDGED_RELEASE_SHA256
  --archive DOWNLOADED_ARCHIVE --sha256 DOWNLOADED_ARCHIVE_SHA256
```

The placeholders above describe the protocol, not an authorization or a ready
shell block. No NPAD action is required while this PR is being qualified.
