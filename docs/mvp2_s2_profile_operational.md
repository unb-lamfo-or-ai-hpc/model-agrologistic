# S2 observation-only operational gate and complete NPAD handoff

## Authority and immutable boundary

15 October 2026. PR #97 merged into develop at
`adbb835b591558ffc39dd6127b22b86cc92fbf15`. The maintainer authorizes preparing
and qualifying this operational observational gate and complete human CLI,
with a remaining-PR forecast. The agent does not access NPAD or submit jobs.
Read the [checkpoint](../PROJECT_STATE.md), [closed package](mvp2_s2_profile_observation_v2.md)
and [original job2211568 audit](mvp2_s2_profile_2211568_audit.md).

The new [driver](../scripts/mvp2_s2_profile_operational.py) and
[wrapper](../scripts/npad_s2_profile_operational.sh) select only the already
qualified read-only observer. They do not open or edit the PR95/PR97 entries,
normal launchers, native worker, h300 controller or scientific settings.
The namespace `.mvp2-s2-profile-operational-v1` is distinct from every consumed
claim and the unused closed `.mvp2-s2-profile-observation-v2`. No claim is created
by software qualification or PR merge. An immutable operational-scope record is
included in the plan digest: one read-only slot, no worker or automatic follow-on.

After this PR is Ready and separately authorized/merged, only the maintainer may
invoke its fully pinned human observation CLI. The wrapper verifies reviewed
source ancestry in merged develop before any new reservation/submission.
No shortened SHA, moving branch URL, edited script, old source or receipt may
stand in for that reviewed pin. There is no license lookup or environment upgrade.

## One complete operational delivery

| Stage | Qualified behavior | Failure handling |
| --- | --- | --- |
| Login wrapper | Exact SHA/wrapper bytes; isolated raw-HEAD checkout; tests outside source; physical inventory before/after | Preserve failed bootstrap; no cache deletion, package upgrade or shared-checkout edit |
| Submission | Exclusive claim, fsync, source/runtime/tools, sealed intent/called marker before one sbatch | Interrupted/unknown acknowledgement consumes slot; never guess a job, reset or repeat |
| Compute batch | Acknowledged job/UID/plan, raw source/Python and scontrol identity; fixed reaped queries; independent read-only channels | No Git/sbatch on compute, worker, srun, IPC release, signal or security mutation |
| Status/wait | Full-width accounting; root/batch/extern only; terminal state distinguished from acceptance | Delayed accounting stays pending; Ctrl-C is safe; no new submission |
| Collection | Same canonical bounded archive/forensic formats, exact source/job/plan/checksum anchors and independent replay | Missing/corrupt/truncated evidence stays negative; original bytes are preserved |
| Resume | Same cached archive/sidecar re-audited against original job/source | No new query or replacement after cache; corrupt cache blocks |

Only one observation allocation is proposed: one node, two logical CPUs,2048MiB,
twelve minutes, account sxdsouza, partition intel-256, export NONE/no requeue.
Maximum requested reservation is0.4CPU-h and0.4GiB-h, not consumption or billing.
Capture has the unchanged90-second cooperative deadline; fixed queries are
bounded/reaped independently. Blocking kernel/filesystem calls are not hard-bound
by Python. Successful file/directory fsync is not NPAD/NFS crash-durability proof.
This is a short prerequisite observation, not a long solver campaign or a normal
retry. It creates no numeric worker step. Host settings and security stay unchanged.

## Interpretation and stop rules

The independent screen preserves all PR97 obligations: namespace limit and each
PID1 namespace separately; exact UID/job/batch or memory-only task_0 placement;
actual cgroup-v1 descriptors; whole-hierarchy non-delegation/permission policy;
mountinfo/inode/inventory/member binding; separate deadline/completeness checks.
Failures retain fixed-stage/errno diagnostics when available, never exception text.
All normal/adverse/native/production/repeat/cleanup flags remain false.

- `submitted_observation_only`: a job was acknowledged, not accepted scientifically.
- `prerequisites_observed_not_admitted`: this snapshot passes implemented screens;
  it still cannot admit normal, prove persistent isolation/quiet cleanup or close S2.
- `blocked_environment`: missing or unsupported facts; inspect the independent
  host-limit status, blockers and private bounded archive. Unreadable is not nonzero.
- `missing_observation_preserved`, `rejected_observation_preserved` or
  `partial_observation_preserved`: terminal accounting/forensics are retained,
  without promoting a complete/failed job into environmental acceptance.
- Unknown submission: preserve claim/bootstrap, stop, report output. No automatic
  reset, job discovery, alternative claim or retry is admitted.

Transfer every resulting archive and sidecar, including negative outcomes.
No normal/adverse/native/h300/afterok chain follows automatically. If the sufficient
profile is demonstrably unsupported/unobservable, seek NPAD support or an explicit
protocol decision. Do not sudo/sysctl/chmod or weaken criteria to obtain a pass.
The original job2211568 archive/certificate remains blocked and unchanged.

## Complete pinned CLI and transfer

The final PR comment and downloadable handoff supply the full reviewed40-character
source SHA, wrapper SHA256 and complete copyable commands. They cover:

1. Download the exact wrapper directly with curl and verify SHA256, avoiding a
   missing MobaXterm-uploaded script; run start only after the authorized merge.
2. Run the fixed status command to inspect the acknowledged job, without typing
   a guessed job ID or parsing private JSON by hand.
3. Run wait; after JOB_ID is acknowledged, SSH may disconnect. Ctrl-C during wait
   is safe. Resume with the same wait/collect command, never a new bootstrap.
4. Run collect for the same claim. Existing start is collection-only, not a repeat.
   Cached collection prints the same archive/checksum and rechecks integrity.
5. Transfer exactly DOWNLOAD and TRANSFER_CHECKSUM with MobaXterm and report SHA256.

The driver prints OBSERVATION_STATUS,JOB_ID,PLAN_SHA256,SHA256,DOWNLOAD and
TRANSFER_CHECKSUM; when a profile is available it also prints HOST_LIMIT_STATUS
and BLOCKERS. The archive contains exactly plan.json,job.json,raw-records.json,
accounting.txt,review.json. No license, environment dump, workbook or unrelated
project is included. Raw paths/PIDs/log prefixes remain private and outside Git.
No command is supplied to reset claims, extend the budget or submit follow-on work.

## Qualification and the legacy Quality failure

Tests inject scheduler/kernel effects into disposable directories and exercise
public start/batch/status/wait/collection dispatch, frozen scope, acknowledgement
failure, predecessor preservation and negative/partial/cached archive replay.
Linux CI additionally checks Bash argument guards and physical source closure
before/after the exact690-case combined cohort, without failures/errors/skips.
Local Windows qualification:677passed/13 explicit Linux-only skips; no real Bash
or Linux primitive acceptance is claimed from Windows. Platform skips are disclosed;
no software test is installed NPAD acceptance. Exact published blob equality and
all six exact-head checks precede Ready and the separate merge request.

PR97's first general Quality attempt failed the unchanged h300 legacy
failed_cleanup_hang test: control_error instead of cleanup_watchdog. Its single
same-head rerun passed; original failure is retained in
[PR97's qualification record](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/97).
Direct final-name failure-cleanup publication is a source-visible possible race,
not a demonstrated cause of that run. Investigate and qualify this interaction
inside the normal/native functional package before native/h300 admission.
This observation-only entry never calls that supervisor. No test assertion or
historical executable is changed to bypass the failure.

## Remaining S2 PR estimate — not an execution promise

Baseline: **six PRs including this operational observation PR**, or five after
its merge. Plan a working range of **six to nine including this PR**, allowing
zero to three evidence-driven correction/protocol changes. This is not a cap or
a guarantee: an unsupported environment may require NPAD coordination and a new
approved protocol; engineering cannot silently remove contracted experiments.

| Planned functional PR | Complete scope and dependency |
| --- | --- |
| Current observation gate | Qualified wrapper/driver/tests/runbook/collection and pinned human CLI; no downstream admission |
| Finish A | Audit observation, resolve justified installed blockers, qualify complete normal admission and audit handoff; normal live evidence still required |
| S2-P2 | Accepted normal audit plus one release/collector/runbook for all five adverse cases; not one PR per case |
| S2-P3 | Audit all adverse cases; integrate licensed native miniature/partial paths, fresh source/runtime/license and reconcile390s synthetic versus300s h300 cleanup budgets |
| S2-P4 | Audit miniature; qualify one homogeneous h300 block with five cold serial arms4,1,8,2,16, fresh input/allocation/license and complete collection |
| S2-P5 | Audit all attempted/unrun arms, compare quality/resources, justify next configuration or inconclusive decision, record full S2 exit |

Prepare reusable P2-P4 software/result schemas while evidence is pending, but live
blocks remain serial and predecessor-audited. The five-thread analytical result
is not the integrated native or h300 contrast. One six-hour h300 request remains
16CPUs/192GiB,96 requested CPU-h, five global1800s optimization windows; it is not
the whole remaining S2 cost. Native-miniature budget is still to be frozen.
Negative/censored outcomes are retained; no-incumbent is not infeasibility and
capped runs are not ordinary speedup measurements. Positive speedup is not an
exit condition, but an unrun contracted grid does not silently close S2.

S3/S4 remain cancelled; later h400, existing-SCIP h215, conditional h500 and
S6-A/S6-B remain planned. EVPI/VSS excluded. No model, data, formulation, tolerance,
scientific budget or manuscript change. Main/develop synchronization stays after
article review. Queue/support/audit/merge time is additional and uncertain.
