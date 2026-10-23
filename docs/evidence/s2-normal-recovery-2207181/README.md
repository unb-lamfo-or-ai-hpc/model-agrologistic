# Normal recovery 2207181: negative operational evidence

Reviewed 11 October 2026. PR #67 merged into develop at
`fe56d465720d396ebfb2c7f202fb0482db0d91ad`. Executed source remains
`c74f316e30a1b034368ce15b4877d03f31c5d09b`, not the merge commit.

The externally supplied archive SHA-256 was independently verified:
`264037fafd7ef52a74e3854b35213228a257d2f3f98f8f55e5ec29fc4eab8b8f`.
Bounded replay without extraction/execution reproduced
`integrity_replayed_not_live_qualified`. [Semantic records](records.json) retain
the original lineage, review and four inner records; no certificate is rewritten.

- Root and batch: FAILED, 1:0, two seconds. Extern: COMPLETED, 0:0.
- Missing terminal batch receipt; controller not_replayed, worker outcome unknown,
  null worker contract and no worker evidence bundle. No live qualification.
- Reported regression: 343 passed, two intentional non-Linux negative CLI skips.
  The regression XML was not transferred; do not call it independently audited.
- The additionally transferred `s2-first-normal-evidence.tar.gz` is byte-identical
  to this recovery's inner archive, SHA-256
  `0f5da97c69a742d4392911dc7238d127e12ca7be4e746d456ac417f6efb6a1ed`.
  It is NOT the original job 2207167 archive (`03ee4d87...`). A reused filename
  is not provenance. Preserve the original predecessor reference and archive.

## Cause: supplemental maintainer-reported stderr

After replay, the maintainer read the existing job's stderr and supplied its
traceback in chat. This supplemental observation is not a member of the audited
archive and has no independently transferred raw-file checksum. The final error
was `FileNotFoundError` for `/usr/bin/git`. Reviewed source locations:

1. recovery `batch`, line 318: `load_claim` before shared diagnostic capture;
2. recovery `load_claim`, line 160: `verify_predecessor`;
3. recovery `verify_predecessor`, line 132: `n.recheck(envelope)`;
4. first-normal `recheck`, line 284: hash every login-envelope tool;
5. batch-adapter `_file`, line 62: open the absent executable.

The immediate failure is a login-versus-compute tool dependency mismatch. The
predecessor recheck required login Git on the batch host. This does not establish
that all compute nodes lack Git, that other tools are present, or that the older
2207167 failure had the same cause. It is not a Gurobi/license/MILP failure.

The exception escaped before shared batch diagnostics and before this path's
worker launch. Collection therefore correctly retained a missing receipt rather
than fabricating completion. Earlier component tests did not qualify this
installed host difference. More test passes are not evidence of node parity.

## Correction and remaining boundary

The [compute identity correction](../../mvp2_s2_compute_identity.md) adds early
redacted stderr coverage and closed role-specific identity components. No new
attempt is admitted. Original claims, failed checkout, receipts and archives
remain untouched. Do not install/copy Git, alter PATH, replace runtime hashes,
remove integrity guards or retry either consumed claim to pass this gate.
