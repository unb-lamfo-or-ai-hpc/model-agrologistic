# S2: recover normal job 2208459 without resubmission

## Observed failure, not live acceptance

PR #75 merged into develop at `c5cc384c732f511525fcfdea6b020c29538afb0d`.
The maintainer reports 782 NPAD passes/two intentional platform skips at execution
source `9911bd68db480fccea2fd774ac0a969238300ece`. Job 2208459 root/batch
completed 0:0 in 20 seconds; numeric step 0 ended 0:9 after four seconds.
The full accounting state is `CANCELLED by <numeric UID>`, not COMPLETED.
The default human display truncates this to `CANCELLED+`.

Two distinct problems must not be conflated:

1. **Confirmed collection defect:** the parser accepted only bare states and
   rejected Slurm's cancellation attribution. Slurm 22.05.11's
   [PRINT_STATE implementation](https://github.com/SchedMD/slurm/blob/slurm-22-05-11-1/src/sacct/print.c)
   formats cancellation with the cancelling numeric UID. The
   [sacct manual](https://slurm.schedmd.com/sacct.html) documents field truncation.
   The correction accepts exactly this bounded unsigned decimal form and maps
   it to CANCELLED. It does not accept arbitrary suffixes, '+' or unknown states.
2. **Prior operational failure, cause not yet established:** the supplied original
   attempt says `blocked_unbound`, `adapter_failure_preserved`, zero samples.
   Operation reason is `adapter_failure_unknown_effect`, local client reaped,
   remote cleanup not proven. The wrapper's `attempt_preserved`/complete means
   preservation finished, not successful handshake, worker completion or containment.
   Attribution to a UID does not identify the triggering software fault or prove
   intentional human cancellation. No OOM/time exhaustion is established.

The initial diagnosis used maintainer-supplied excerpts. The carrier is now
independently audited as recorded below. No location-specific historical cause
should be invented from the missing exception.

## Audited recovery checkpoint, 12 October 2026

The collection-only reader at `17717b7775a4dce44bf9896e372da5a3ac8c9d7d`
passed 63 NPAD tests without skips and submitted no job. Independently checked:

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `s2-node-accounting-recovery-2208459.tar.gz` | `64617380256e8cf3c5031ef87fb3d71d9526d923e69e100c5140879a60ad34e3` | 19 unique regular members; all 18 manifest member sizes and hashes match |
| `s2-node-normal-evidence.tar.gz` | `67fd0db5c0087a4aba8693166412946d9b2966d05c9d7c17ea176a03f5bcc0f5` | Byte-identical to nested replay; independent existing audit returns `integrity_replayed_not_live_qualified` |

Execution proposal/release canonical digests match the frozen anchors below.
The worker identity receipt matches the attempt's source manifest (519 files),
worker and runtime identities. This proves startup identity verification, not
successful IPC release or scientific execution. No binding, contract, phase
completion, terminal worker receipt or telemetry sample was recorded. The local
client stop intent and negative operation are preserved. Remote cleanup remains
unproven. Neither carrier contains the original exception or raw step query.

### Source-backed step schema defect and bounded correction

The [Slurm 22.05.11 step formatter](https://github.com/SchedMD/slurm/blob/slurm-22-05-11-1/src/api/job_step_info.c)
(`slurm_sprint_job_step_info`) emits a numeric `UserId`, `Nodes` as a count,
and `NodeList` as the host list. The previous reader instead required
`name(uid)` and compared `Nodes` to the host name; its fixture reproduced those
incorrect assumptions. This independently establishes a compatibility defect
on the handshake path. It is not proof of the exact historical failing line:
the job's missing raw response/exception prevents that attribution.

The reader now requires a bounded numeric step UID matching the owner,
`Nodes=1`, and exact `NodeList` matching the accepted scheduler node. The
allocation UID grammar, CPU/task/time limits, peer credentials and cgroup
checks remain strict. The new step fingerprint includes both count and host;
old releases and receipts are not rewritten or recertified. Thirty-one new
offline cases cover the official-format fixture and missing, duplicated,
mismatched or malformed fields; existing handshake fixtures are corrected.
This is software qualification only, not an additional live admission.

## Functional correction and provenance

- Shared live accounting and current node-normal collection request `State%80`.
  The transport still accepts the exact legacy query for existing callers.
  Canonical outputs and old receipt schemas are unchanged; raw cancellation
  metadata is retained in the new recovery carrier.
- Future supervisor exceptions additionally preserve a bounded, message-free
  stage/category/code-location sidecar after owned-client cleanup. This does not
  rewrite historical records, relax a handshake or infer missing old diagnostics.
- `scripts/npad_s2_accounting_recovery.sh` checks out a separate pinned analysis
  source and runs the focused regression. It has no submission/retry route.
  `scripts/mvp2_s2_accounting_recovery.py` verifies the fixed original proposal,
  release, acknowledgement and sealed source bytes before collecting existing
  data. No code is imported from the old checkout. The only scheduler command is
  one bounded read-only `sacct` query for 2208459.
- The fixed execution proposal digest is
  `ef93f3ebc9327902d65496940a65346b60090b93ce27c89f974c3669b3bc1c06`;
  release digest is
  `3bc4a50afa926fdd811e7e4f09cb5a76fbb6d16f1e333e4d20a7bc6500ced4e8`.
  The analysis source identity is separate from that frozen execution identity.
- Only allowlisted claim/run/worker products, bounded sample/event records and
  raw accounting are captured. There is no recursive archive of the source,
  home directory, license or environment. Originals are read again to detect
  changes. All output goes to a new sibling recovery directory, not the claim.
- Semantic replay uses existing validators. If it rejects the partial evidence,
  the raw forensic carrier is still exported with the rejection category and
  no successful review. SHA-256/inventory checks prove byte integrity, not live
  acceptance. Transfer this private carrier only for the agreed audit; do not
  commit its paths, UID or raw contents to Git.

## Handoff and next decision

After exact-head software qualification, provide the checksum-pinned download
of the collection-only shell file and invoke it with the full analysis commit.
Unlike a new experimental gate, this read-only recovery does not require an
additional job or reset of any claim. The pinned reviewed branch can be used for
collection before merge. The maintainer executes the CLI and transfers DOWNLOAD
and TRANSFER_CHECKSUM. Archive status is `captured_not_live_qualified`; preserve
negative semantic replay as well. Repeating collection can create a new analysis
directory, but cannot submit or repeat an experiment.

Carrier review is complete and preserves its negative outcome. Complete the
same PR's step-format qualification and Ready/merge review next. A subsequent
normal-only gate must pin the corrected source, retain this negative predecessor,
use a distinct claim, include the new format regression, and qualify its complete
start/batch/worker/collect/audit route before issuing a new CLI handoff. Do not
reuse the prior normal driver with a substituted source hash: it is not a new
admission. Require live binding/contract, completed normal phases, containment
and terminal evidence before considering adverse or native gates.

Keep investigation in this functional PR where practical; request merge only
after qualification and Ready. No new normal/adverse/native/h300 job is admitted
by this PR. A suggestion to run three or more four-hour jobs during the pause
is not a replacement for normal acceptance, adverse containment, native license
qualification or a defined homogeneous h300 cohort. The existing h300 design
uses a common 1800-second diagnostic optimization window; changing that to four
hours is a separately reviewed scientific/budget decision, not a parser repair.

S2 remains open and fully planned. S3/S4 stay cancelled. h400, SCIP/h215, conditional
h500 and S6 remain on the roadmap; main/develop reconciliation stays at S2 closure.
