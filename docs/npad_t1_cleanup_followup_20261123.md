# T1 cleanup follow-up: diagnose retention before reuse — 23 November 2026

## What the operator output establishes

| Reported outcome | Count |
| --- | ---: |
| Cache files removed | 0 |
| Disposable duplicate files removed | 0 |
| Candidates retained | 8449 |
| Logical bytes removed | 0 |

The run reached its final receipt after archive creation and member verification.
This is a reported backup-only outcome, not successful cleanup. The terminal log
does not contain per-file retention reasons. The report tar.gz and its sidecar
are already available on NPAD; transfer these derived reports, not another large
copy of the historical backup.

The quota print of 50495M preceded backup construction. It is neither the final
quota observation nor the compressed archive size. Measure those separately;
do not infer a storage reduction from the word finished.

## Defect reproduced in the exact executed helper

Process references are stored without their type/PID origin and normalized with
rstrip("/"). Therefore a process cwd/descriptor pointing to "/" can become "".

The subsequent predicate is:

    target == reference or target.startswith(reference + "/")

For an empty reference, every absolute target satisfies the prefix condition.
A local temporary-free call of the original predicate confirms this for both a
cache target and a disposable-copy target. No NPAD operation was performed.

This confirms a code defect, not the actual reason for this particular run.
The action journal may instead or additionally show specific process references,
changed identity/hash, restricted process visibility or control omissions.
Do not label all 8449 files as genuinely in use without examining those records.

## Verification sequence

1. Verify the already-created cleanup-reports.tar.gz against the reported SHA-256.
   Verify the original REPORT_SHA256SUMS. Retain the original ledgers unchanged.
2. Reconcile cleanup-result.json against all action statuses. Count unlink intents,
   successful removals and retention reasons. The sum must match the 8449 targets.
3. Read verified-backup.json for exact member count, compressed bytes, source
   bytes and backup SHA-256. The planned member count is 110705. Do not hash the
   large backup again merely to obtain a summary already preserved in its receipt.
4. For each prune snapshot, count empty, filesystem-root, home-directory and
   exact/specific references; retain PID/type provenance where it is available.
   The old report lost origins, so fresh targeted observation may be necessary
   if the original snapshot cannot identify a specific dependency.
5. Classify the original control/process omissions by actual reason and path.
   A test-fixture path alone does not justify suppressing an unreadable real
   dependency. Document any exception specifically.
6. Only after identifying the actual causes, prepare a correction with canonical,
   typed process references (cwd, regular-file fd, directory fd, exe), explicit
   root/broad-directory treatment and protection of specific file references.
   Empty/noncanonical strings must never enter prefix matching.
7. Add Linux controls for "/", "", home/audit-root cwd, directory descriptors,
   a genuinely open target, unknown/unreadable process state, corrupt backup,
   changed targets and keepers. An observed true dependency must remain retained.
8. Qualify a read-only dry run against the 8449 original targets and the existing
   verified backup manifest. Report eligible/retained counts and reasons. No
   automatic prune or backup recreation follows this diagnostic.
9. A later pinned cleanup, within the existing researcher-authorized scope, must
   reuse and revalidate the backup custody and final source identities. Preserve
   source/receipt history; no claim, scientific vector or environment is pruned.

## Required operational correction

A successful process exit can mean every proposed removal was withheld. Add an
explicit outcome such as backup_verified_cleanup_withheld, with actual counts,
and meaningful non-completion reporting when zero planned actions are eligible.
Do not weaken the checks simply to obtain a nonzero deletion count.

The current large backup and original historical files remain in custody.
New work is limited to verification/planning. PR #159/#163 remain Draft, with
no new HPC jobs, environment mutation or merge.
