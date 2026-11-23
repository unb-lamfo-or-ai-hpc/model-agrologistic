# Audited T1 backup-only closeout and correction — 23 November 2026

## Independent report audit

The transferred cleanup-reports.tar.gz matches SHA-256
29d5df4f4c65a1b92219a27e773e04e67790782692d5eabc5abf88eb6ada87a6.
All 17 internal ledger entries pass, with safe/unique regular archive members.
The action journal contains exactly 8449 unique retained records, matching the
338 cache and 8111 disposable-copy targets. There are no unlink intents or
successful removals. Every retention reason is Observed process dependency.

The backup receipt records 110705 members, 16362411113 source logical bytes and
2088818486 compressed bytes (about 1.95 GiB), with member hashing reported passed.
The backup SHA is d093e7defbca502ccc3c7e27a827f6baab13c1bdf14370cc9fca3133c7df1dd0.
This audit verifies the receipt and its report custody; the large backup bytes
remain on NPAD and have not been independently rehashed locally.

[Structured evidence](evidence/npad_t1_cleanup_reports_audited_20261123.json).

## Confirmed cause and remaining blockers

Every prune snapshot contains an empty process reference. The old matcher
treated this as a prefix of every absolute target; that first guard retained
all 8449 files before later checks were reached.

An offline counterfactual removing invalid/root prefixes finds zero specific
observed process-path matches in the saved snapshots for both target classes.
There remain 104 cache files with historical control/directory/symlink prefix
references. These are not necessarily live consumers; no cleanup eligibility
is inferred from this counterfactual.

Two later duplicate guards would still withhold the 8111 duplicate candidates:
30 PermissionError records (cwd, exe and fd-directory access for each of ten
PIDs) and eight non-test control parse failures. These must not be silently
discarded merely because the first bug is fixed.

The eight non-test parse failures correspond to native-ready.json/result.json
placeholders from failed job 2278573 in four retained locations. All eight were
zero bytes in the prior metadata inventory. Four actual members in the locally
preserved original closeout archive are independently confirmed empty, with the
standard empty-file SHA-256. The original archive itself matches its retained SHA.
The six other malformed controls are under test-fixture paths, sized six/seven
bytes in the metadata. Their exact current bytes and all ten PID metadata remain
a targeted read-only follow-up. No original JSON is repaired, filled or deleted.

## Correction implemented, without activating cleanup

- Canonical reference handling preserves "/" as a root value and rejects empty,
  relative, special-descriptor and ambiguous values for path matching.
- Process observations retain PID, origin (cwd/exe/fd), target type and scope.
  Broad filesystem/home/project-root handles remain metadata, not blanket
  evidence that every descendant is consumed.
- Specific inventory paths still protect matching files/subtrees. Process access
  errors remain explicit, and existing conservative duplicate withholding stays.
- A wholly retained operation reports backup_verified_cleanup_withheld.
  Mixed completion and actual completion have separate outcomes.
- Mutation requires an explicit --apply option. No new apply command/package
  is supplied; the old pinned bootstrap must not be repeated.

The correction changes only T1 operational inspection/custody files. Scientific
models, inputs, claims, accepted results, manuscripts and environments are intact.

## Next human-only NPAD step

The new inspect_t1_cleanup_retention.py reads the already-created signed report,
checks its internal ledger, and produces the historical counterfactual. It reads
the status/UID metadata and accessible cwd/exe/fd targets of the ten original
error PIDs, plus sizes/hashes/parse status of the 14 omitted controls. It never
reads command arguments, environment variables, license contents or credentials,
and never elevates permissions or terminates processes.

The probe writes a fresh small derived-report directory under the audit root.
It does not scan all 113304 source records, hash/recompress the large backup,
invoke the cleanup routine, submit/cancel a job, install a package or change the
shared environment. Its result explicitly says pruning_allowed=false.

A process that vanished since the old snapshot is recorded as no_longer_visible,
not retroactively declared irrelevant. Remaining unreadable processes stay an
observability gap; a command name or UID alone will not clear removal.

## Qualification

The dedicated Linux workflow runs 18 custody/reference controls plus six
read-only probe controls, using temporary files and no optimizer. Portable local
checks and Ruff pass; Linux-specific no-follow/inode cases are qualified in the
exact-head Actions run. Private PID/path tables remain local.

PR #159 and PR #163 stay Draft. No NPAD execution, new removal, backup recreation
or merge occurs during this correction. The next decision depends on the returned
probe report; do not interpret a successful diagnostic exit as cleanup permission.
