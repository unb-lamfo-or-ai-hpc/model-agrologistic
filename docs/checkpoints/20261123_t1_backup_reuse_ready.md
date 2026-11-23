# T1 targeted metadata verified; backup-reuse cleanup prepared — 23 November 2026

Targeted archive SHA-256 7be1b4a77bdc13a1dedc3080f9d2e5aff6af1fe68b8a2371afb34add8e9a71b5
and both ledger members verify. Eight empty historical controls remain unchanged.
Five malformed test fixtures have one known six-byte hash; the sixth has its
known seven-byte hash. Keep every original byte.

Three of ten old PIDs disappeared. Seven still visible are three sshd, three
sftp-server and one PAM helper. Active SFTP remains a blocker. Explicit SSH/PAM
exceptions require UID/ownership and verified parent linkage/role, not names alone.

A separate resume wrapper verifies and reuses the existing 1.95 GiB archive,
then conditionally prunes only original 338 cache/8111 disposable duplicate
targets. No new backup, source campaign, job, environment change or scientific
original removal. Exact backup SHA, source hashes and per-file receipts remain
mandatory. Actual removals are unknown until the human returns the new report.

Read [the protocol](../npad_t1_existing_backup_resume_20261123.md).
PR #159/#163 remain Draft; no merge. Never repeat the old archive-building CLI.
