# S2: one node-corrected normal synthetic observation

## Purpose and boundary

Base: PR #74 merged into develop at
`4b10f6bb623b7e2a77eaa85979a22d0dbdaa79d1`. Its
[audited diagnostic](mvp2_s2_node_identity_evidence.md) observed the NPAD
rack FQDN / scheduler short-name mismatch. This gate qualifies the complete
operational route for exactly one fresh normal synthetic observation with that
correction, not another diagnostic repeat or a scientific optimization.

The fixed allocation remains one node, two CPUs, 2048 MiB, twelve minutes,
no requeue. Solver licenses, model/data, parameters and source scientific
validation are unchanged. Adverse/native miniature/h300/repeats stay closed.
CI and merge do not prove installed Slurm containment. Do not execute this
gate until its exact-head qualification, Ready, authorized merge and pinned
CLI handoff. Only the maintainer executes NPAD commands.

## Complete lifecycle and immutable identities

- Entry: `scripts/mvp2_s2_node_normal.py`; bootstrap:
  `scripts/npad_s2_node_normal.sh`. Claim basename:
  `.mvp2-s2-node-normal-v1`; fresh bootstrap prefix `s2-node-driver-`.
- The login bootstrap requires a source ancestor of origin/develop, raw HEAD
  byte equality, physical source closure including ignored files, and the exact
  selected regression gate. It runs Python with `-B`, including isolated child
  processes. Test products remain outside source; closure is rechecked afterwards.
- Release schema `s2-node-normal-release-v1` adds the fixed immediate predecessor
  and diagnostic reference to the existing qualified release. No old reader,
  claim, archive or source is rewritten. No monkeypatching of production module
  globals or caller-selected claim is used.
- Before reservation, the login sealer audits original predecessor receipts,
  archive and tracked-byte inventory. Existing older historical checks remain.
  Compute verification reads sealed bytes without historical Git/submission
  executables and without importing historical checkouts. Existing historical
  ignored caches are preserved; current source must remain physically closed.
- An exclusive claim precedes the only `sbatch`; proposal and intent are durable
  first. Only the acknowledged job ID changes in the final release. Ambiguous
  acknowledgement consumes the claim: preserve and investigate, never resubmit.
- Batch/worker entries bind proposal/release/specification digests and use shared
  numeric-step containment, membership, kernel-peer handshake, stop handling and
  teardown. Node comparison inherits PR #74's bounded mapping; no new alias,
  DNS, environment fallback or resource relaxation is introduced.
- Existing claim means collect only. Terminal accounting, partial/negative
  outcomes and early structured diagnostics are retained. The portable archive
  contains only anchor, collection and independent review. Cached collection
  rechecks archive, review and exact checksum sidecar; it never resubmits.

### Frozen references

| Reference | Source | Evidence SHA-256 |
| --- | --- | --- |
| Negative normal 2208339 | `f96d9729f2a3bf7a8310094aa8a675b224b203d1` | `b10d4e4c2930a4dce0ea685b8aa0af4a1effff815da878e652c50712e4f3cc95` |
| Diagnostic 2208438 | `1c33692f9affdf3ec5dece387a9425cf5b2fd671` | `7042a46430a2bac242080306e86a5a81f6c165949ca537abba4c5d329980157e` |

Normal release digest:
`baeed8c999179e36f824b9faf9fa2f5caac3885b1099c385c59b3db302f40e46`.
Diagnostic plan digest:
`5cc0032835331416b588351af404973c131c9fa702d28876c12a09f57cb14d90`.
The original diagnostic still replays `observed_mismatch_or_query_failure`;
the original normal still replays `no_attempt_receipt`. Neither is promoted.
The diagnostic archive is a fixed read-only reference, not an executable source
or a newly scheduled query. Private paths/UID/raw archives are not published.

## Qualification and acceptance

The new suites exercise proposal/release binding, durable one-shot submission,
acknowledgement ambiguity, stops, batch/worker dispatch, old-claim denial,
terminal/cached/negative collection, portable checksum replay, immutable
predecessor bytes and the original diagnostic reader. Existing suites retain
allocation-to-step node continuity and physical source-closure regressions.
All test scheduler effects are injected; the test command never executes an
installed Slurm command or licensed solver. Exact-head CI results belong in
the PR review record, not in a fabricated NPAD receipt.

NPAD bootstrap policy: 784 cases, 782 passes and exactly the two existing
non-Linux-only negative CLI skips, no failures/errors. No unreviewed skip or
test-count change is accepted. Windows local capability skips are reported
separately; they cannot satisfy this Linux gate.

After merge, the handoff pins source SHA and bootstrap SHA-256 and supplies
download/start, job-status and collection commands, including fresh-login
recovery from the immutable proposal. Transfer the printed `DOWNLOAD` and
`TRANSFER_CHECKSUM` using MobaXterm. No manual cleanup or old claim reset.

Review must distinguish scheduler exit, portable integrity, actual normal
worker completion and containment. `integrity_replayed_not_live_qualified`
is not a live qualification decision by itself; `no_attempt_receipt` remains
a negative result. Missing evidence blocks acceptance. Even a successful normal
observation does not admit adverse cases, native miniatures or the h300 contrast.
Use the actual carrier to decide the next bounded gate. S2 remains open.
