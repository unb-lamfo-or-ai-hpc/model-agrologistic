# Authorized T1 cleanup handoff — 23 November 2026

The researcher explicitly requests commands for removal of the 338 cache
candidates and matching redundant copies, plus compression of material not
essential to continued development. This supersedes the prior no-cleanup
authorization for the bounded actions described here. It does not authorize
a merge, new HPC jobs, solver calls or environment changes.

## Concrete scope

| Planned role | Files | Logical bytes |
| --- | ---: | ---: |
| Regenerable cache candidates | 338 | 1849971 |
| Disposable duplicate code/download candidates | 8111 | 89051300 |
| Archive only; preserve original paths | 102256 | 16271509842 |
| Retained comparison/keeper records | 2597 | 68393029 |

The two database-filename guards are excluded. All original claims, controls,
scientific solution vectors, active inputs, the current checkout, OSRM and both
shared environments are excluded from pruning. The 4087 content-match groups
are not an instruction to erase all but one scientific observation.

Disposable duplicates are restricted to historical audit bootstrap/source
directories with explicit naming and file-type allowlists. Each has a distinct,
retained matching-content keeper. Paths with specific references in the prior
readback were not admitted. This yields 8111 conditional removals (about
84.93 MiB), not the full 3.1445 GiB content-match excess.

## Operator procedure

A private package contains the 113302 stable records and 11834 known control/
symlink metadata rows, plus the standalone standard-library helper. It contains
no original scientific file contents, license contents or environment snapshot.
Its manifest and outer checksum pin the exact selection and helper bytes.

1. On the login shell, require an empty user queue. Never cancel or submit jobs.
2. Create a fresh output directory under model-agrologistic-hygiene-audit.
3. Read the listed known controls, symlinks and visible same-user processes again.
   Omission paths/reason classes are recorded, without credential values.
4. Create an ordinary tar.gz with 110705 listed historical/cache regular files.
   Check inventory device/inode/size/mtime, refuse symlink traversal and check for
   mutation. A change aborts before any unlink.
5. Independently decompress and hash every member against its accepted source
   SHA-256. Only a completely matching backup permits pruning.
6. Recheck queue, dependency observations, source hash and final identity. For
   each duplicate, recheck the retained keeper, which is never a removal target.
7. Remove each permitted cache/disposable duplicate with a single dirfd-relative
   unlink. Keep directories, claims and all original scientific vectors.
   Flush intent/result receipts. Retain changed, busy or uncertain targets.
8. Deliver cleanup-reports.tar.gz and its sidecar, retaining the full backup.

The helper never executes rm -rf, follows a source symlink, installs a package,
invokes an optimizer, changes scheduler state, compresses a production SQLite
snapshot or touches the shared environments. It runs with Python -B -I -S.

## Dependency limits and retention

A shell cwd at an inventory root is not treated as use of every descendant.
Specific process/control/symlink references remain relevant. Duplicate pruning
is withheld for incomplete process visibility or unresolved non-test control
omissions. Cache pruning is confined to the explicitly authorized regenerable
cache files; observed process dependencies and changed hashes still retain them.

The observations are not a global filesystem freeze. Other users, remote
nodes and future dependencies remain beyond full visibility. The source-specific
allowlist and verified independent backup bound the action in this context.
No currently referenced code tree or scientific claim is intentionally pruned.

The archive is a backup of listed regular files, not a complete directory image:
opaque directories, symlink targets and SQLite/WAL consistency are not covered.
Backup is created at compression level 1 and verified before removal. It initially
requires additional quota. Keeping the historical originals plus the local backup
can increase total usage; no net storage gain is promised. A later off-host custody
decision is distinct from this limited removal. Do not remove the backup.

A recovery restores ordinary independent files from their original relative
tar member paths into a fresh isolated restoration directory. Never extract over
the active project. Temporary-file controls verify payload recovery and corruption
rejection; the NPAD run revalidates every real member.

## Qualification and governance

The helper and tests are separate from the qualified read-only inspector at
d3a0c654. An additional Linux CI workflow tests file-level custody with temporary
fixtures, not NPAD data or solver runs. Private path tables remain outside GitHub.
PR #159 and PR #163 remain Draft; NPAD execution is human-only.

The handoff supplies an executable plan, not evidence that cleanup has occurred.
Only the returned operation ledger establishes actual removals and retained items.
