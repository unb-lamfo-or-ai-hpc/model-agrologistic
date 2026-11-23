# T1 backup completed; cleanup withheld — 23 November 2026

The operator supplied the terminal output of the first authorized cleanup
attempt. It reports **zero cache removals, zero duplicate removals, all 8449
candidates retained, zero logical bytes unlinked**. Backup creation and member
verification returned before the final receipt. No failed backup is reported.

The report archive SHA-256 is reported as
29d5df4f4c65a1b92219a27e773e04e67790782692d5eabc5abf88eb6ada87a6.
Its contents and original action/backup ledgers have not yet been inspected
locally. Do not describe the operator log alone as an independent archive audit.

The earlier code normalizes process targets with rstrip("/"), so a filesystem
root reference becomes an empty string. The prefix predicate then matches every
absolute target. This defect was reproduced locally using the exact qualified
helper, without invoking cleanup or reading NPAD. Whether it explains this
specific run remains pending the action reasons and snapshots.

Read [the follow-up plan](../npad_t1_cleanup_followup_20261123.md) and
[evidence](../evidence/npad_t1_cleanup_operator_return_20261123.json).

Do not rerun the cleanup bootstrap, recreate the large backup, remove the
backup/claims or repeat the 113304-record hash pass. First inspect and verify
the existing cleanup reports. Preserve the original helper and all receipts;
a correction must retain typed reference origins and receive regression tests.
The current generic bounded_cleanup_finished status must not be presented as
successful space reclamation when all planned removals were retained.

PR #159 and PR #163 remain Draft. No new NPAD call, job, solver, shared-environment
change, source deletion, manuscript edit or merge was performed in this review.
