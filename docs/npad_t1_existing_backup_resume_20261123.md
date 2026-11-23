# T1 cleanup resume from the existing archive — 23 November 2026

The targeted diagnosis archive matches its reported SHA-256
7be1b4a77bdc13a1dedc3080f9d2e5aff6af1fe68b8a2371afb34add8e9a71b5.
Both manifest members and pinned inspector/helper identities verify.

## Findings from the returned metadata

Of the ten previously inaccessible PIDs, three were no longer visible.
The remaining observations comprise three user sshd processes, three
sftp-server processes and one user PAM helper. Their UID fields are consistent
with the researcher. This is metadata classification, not proof of file-use
absence. In particular, an SFTP server is a potential file consumer and is never
excluded from the cleanup gate on the basis of its name.

All eight non-test omitted controls are confirmed zero bytes with the canonical
empty-file SHA. The six malformed test controls retain their original exact
hashes, five six-byte members and one seven-byte member. None is rewritten.

## Authorized bounded operational policy

The authorization remains the 338 regenerable caches and 8111 disposable
source/download duplicates selected in the original pinned plan. No expansion
to original claims, vectors, inputs, OSRM, current project or shared environments.

1. Disconnect file-transfer/SFTP clients while keeping an independent SSH
   terminal. The resume checks for same-user sftp-server processes before reading
   the large backup and again at gate checkpoints. It never kills a session.
2. Require an empty user queue; no job is cancelled or submitted.
3. Verify the original package manifest, original cleanup report and targeted
   diagnosis against their existing SHA pins. Preserve all prior source files.
4. Rehash the existing 2088818486-byte archive once against its accepted SHA and
   receipt. No new historical archive is created and no 16.36 GB source traversal
   is repeated. Compare backup identity/ctime at pruning checkpoints.
5. Obtain fresh known-control, symlink and visible same-user process references.
   Empty historical controls and malformed test fixtures are accepted only as
   unchanged, individually hash-bound observations from the verified diagnosis;
   they remain preserved. A new or changed omission is not silently ignored.
6. Treat unreadable SSH/PAM session helpers as explicitly bounded infrastructure
   exceptions only after verifying all four user UID values, proc-directory UID,
   PID/PPid linkage and parent role/ownership. SSH requires a root-owned sshd
   parent; PAM requires a same-user systemd parent. Unknown/unreadable workloads,
   wrong ownership/lineage, and every SFTP process remain blockers.
7. For each candidate, retain specific process/control/symlink references and
   verify the current hash/identity. Verify the retained matching keeper for
   every duplicate. Unlink only the individually admitted regular file and
   flush intent/result receipts.
8. Preserve the existing backup and return a small new operation-report archive.
   Actual counts may be lower than planned when files changed or remain in use.

The session exceptions are operational judgments within the researcher's
authorized low-impact cache/disposable-copy scope, not global dependency
certification. Other users, hidden processes and future references cannot be
universally observed. No exemption is applied merely from a process name or UID,
and no permissions, authentication services or credentials are changed.

If SFTP is active, the program stops before backup hashing or any removal and
prints the action required. Do not use sudo, chmod, kill or another account to
bypass the gate. An interrupted/partial operation has explicit counts and
preserves every original/new receipt. Missing or changed targets are retained,
never guessed to have been removed by this invocation.

## Storage and MVP3 continuity

The existing ordinary archive already compresses 16362411113 logical bytes into
2088818486 bytes. Original scientific files remain; this limited cleanup is
at most about 86.69 MiB of logical unlink candidates, not 3.14 GiB or a guarantee
of net free-space recovery. The full original archive is deliberately preserved.

This closes the disposable-file portion of T1 when actual receipts return.
Final XLSX/SQLite reconciliation remains the separate T2 activity; neither data
contract nor development environment is changed by storage preparation.

## Qualification and handoff

A dedicated Linux workflow runs the previous 24 custody/probe controls and
11 new resume controls. New cases cover real temporary-file backup reuse with no
recompression, corrupt-backup source retention, SFTP refusal before hashing/
unlinking, strict SSH/PAM lineage, unknown processes and changed control hashes.
Local Ruff passes. Consult exact-source Actions results before the pinned
human-only handoff. PR #159 and PR #163 remain Draft, without a merge.

The new wrapper is the only prospective apply command. Never rerun the original
archive-building bootstrap. No NPAD execution is performed by Codex.
