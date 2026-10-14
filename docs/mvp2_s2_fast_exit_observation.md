# S2 bounded post-fast-exit observation: complete operational package

Terminal update, 14 October 2026: PR #90 merged at
`e2a40c8f1e6d87d82cbe7edbef370e78145f0024`; job2210952's
[audit and protocol decision](mvp2_s2_fast_exit_2210952_audit.md) are available.
The observation claim is consumed/collection-only. Historical start instructions
below do not authorize another job, claim reset or normal retry. Missing scopes
remain unknown, not empty. No new CLI action is needed before the separate
protocol decision; all admission flags remain false.

14 October 2026. Integration base after PR #89:
`40a55f5270c6921f28349024de0dcce69befcab1`.
Authority: [checkpoint](../PROJECT_STATE.md), [completion plan](mvp2_s2_operational_completion.md).

## Question and non-negotiable boundary

Normal job2210506 passed initial barriers and four stdlib phases, but all 186
later samples faulted. Its precise installed exception and scope lifetime are
unconfirmed. Preserve its [negative audit](mvp2_s2_normal_2210506_audit.md), claim,
receipts and original archive SHA256
`0239bbec7edd29cf384e7949d441ec6fb3e8474f77c735799978620fc74aa642`.
This separate observation asks what is actually readable after a fast leaf exits.
It cannot retroactively identify the old exception or certify normal cleanup.

No solver, workbook, license, nested process, native worker, normal controller,
scancel, cgroup write, repeat, arbitrary command or automatic next release is
provided. Only fixed stdlib phases run after kernel-peer and current scheduler/
resource checks. The unchanged phase component returns immediately afterwards;
there is no artificial hold or heartbeat. This is an observation workload, not
normal/adverse qualification. All containment/admission flags remain false.

## Fixed request and observation budget

| Item | Fixed request / bound |
| --- | --- |
| Allocation | Account sxdsouza; intel-256; one node/task; 2 requested CPUs; 2048 MiB; 00:05:00; no requeue; export NONE |
| Leaf step | One task/CPU; exact; 256 MiB; cpu-bind=threads; immediate 10; 00:02:00; kill-on-bad-exit=1; export NONE |
| Initial live gate | Exact job/step/node/UID/kernel peer; worker affinity one CPU; cpusets at most two logical CPUs; effective worker memory at most256MiB/supervisor2048MiB |
| IPC / local client | Bounded acknowledgement30s, server handshake30s, leaf socket45s, initial RPCs2s each, local srun wait60s; only owned local client may be killed/reaped on timeout |
| Post-exit samples | Exactly five requested offsets0/1/3/6/10seconds after local client reaping; actual start times preserved; three independent bounded RPCs per sample,2s each |
| Exclusive claim | `.mvp2-s2-fast-exit-observation-v1`; consumed before submission; no reset or resubmission |

The five-minute allocation is a separately disclosed diagnostic budget, not an
extension or reduction of normal's historical12-minute/390-second policy. It
requests 1/6CPU-hour and 1/6GiB-hour; these are request arithmetic, not actual
allocated/billed resources or measured CPU. Slurm termination/queue latency is
not guaranteed by a requested timelimit. No long solver job is scientifically
justified before this observability question is resolved.

## What each sample means

The [pure observer](../scripts/mvp2_s2_fast_exit.py) catches channels independently.
Its [one-shot driver](../scripts/mvp2_s2_fast_exit_observation.py) and
[Bash wrapper](../scripts/npad_s2_fast_exit_observation.sh) are delivered together.

| Channel | Evidence / interpretation |
| --- | --- |
| Four controllers | Open each original no-follow directory independently and compare device/inode. Read each allowlisted file independently. Distinguish directory missing, file missing, denied, invalid and unavailable. Values are direct members/limits/counters, never recursive descendant proof. cpuacct can be shared and is not attributed worker CPU. |
| listpids | Bind exact numeric job.step; valid header-only response means observed empty only. Nonzero RPC, missing response or unrecognized grammar is unknown, never empty. |
| Step | Exact StepId plus recognized state; disappeared step is unavailable, not automatically clean. |
| Accounting | Wide numeric-ID rows, including attributed cancellation; root/batch completion is not worker/cleanup/scientific success. |
| Products | Independently read the fixed nonce-bound four-phase/terminal prefix; missing and malformed products remain explicit. |
| Known leader | Stable PID/starttime presence, absence or PID reuse; absence is not descendant absence or a whole-step cleanup certificate. |

Sampling starts after owned local srun reaping; it does not reconstruct the
precise kernel worker exit instant. RPC duration can delay requested offsets;
five samples are not a claimed uniform high-frequency resource time series.
Raw initial proc captures, mapped scopes, query responses and srun logs remain
private on NPAD. Public carriers contain allowlisted observations/metadata only.

## Operational lifecycle and complete human CLI

Before execution: qualify focused/expanded regression, exact-head Linux CI,
physical source closure and Bash syntax; mark Ready; obtain separate merge
authorization. The final PR release comment supplies the immutable full source
SHA and Bash SHA256, plus concrete copy/paste commands. Do not run an unmerged
branch or substitute develop/latest for that pin.

Download the pinned Bash file with curl and check its SHA256. The same file takes
`start`, `status`, `wait` and `collect`, each followed by the full reviewed source
SHA. On fresh start it creates a new isolated checkout, verifies every tracked
raw HEAD byte, role tools/interpreter and physical source, runs the exact153-case
offline input gate with output outside source, rechecks source, reserves the new
claim exclusively, persists intent, then submits at most once. Compute verifies
sealed source/runtime without login Git/sbatch. Batch and leaf roles are exclusive.

Existing `start` becomes collect only. Missing acknowledgement stops without
guessing a job. `wait` is Ctrl-C-safe and only repeats read-only collection.
After terminal accounting use `collect` or `wait`: it prints `DOWNLOAD`,
`TRANSFER_CHECKSUM`, `SHA256`, `JOB_ID` and `PLAN_SHA256`. Transfer both files
using MobaXterm and share them for independent audit. Preserve the complete
bootstrap/source/run/claim and all original receipts. Never reset a claim.

The portable archive has exactly anchor/observation/accounting/entry records.
Absent or invalid observation receipts produce a separate terminal-forensic
outcome; allowlisted error category/reviewed code location can survive failures
before dispatch. Original invalid bytes remain on NPAD and their hash is kept
where readable. No arbitrary log messages/paths/environment/licenses are exported.
The collector checks stable capture, exact root/batch and any bound numeric-step
terminal accounting, bounded archive/checksum and portable semantic replay.
Cached collection replays the same artifact without new scheduler queries or
recapture. Integrity replay is never live qualification; all flags stay false.

## Decision after independent evidence audit

1. Retained scopes with real empty membership: assess feasibility of unchanged
   strict cleanup and qualify one separate normal release with diagnostics.
2. Missing/replaced scopes or unavailable/unrecognized member queries: preserve
   unknown and present a specific evidence-backed protocol decision. No silent
   missing-to-empty, terminal-only fallback, artificial linger or timing increase.
3. Early environment/identity failure: audit the exact phase/category/site and
   existing private records before any corrected successor. Do not retry blindly.

None of these observations alone accepts normal A, closes S2 or admits P2-P4.

## Parallel software preparation, serial live release

The [closed slot inventory](../scripts/mvp2_s2_followup_inventory.py) enumerates
eleven unrun slots and rejects completion/admission changes. It is not an
executor or authenticated live receipt reviewer. Preparation reuses these
existing qualified components rather than adding solvers or scientific factors:

| Package | Existing software to reuse | Remaining full-package qualification |
| --- | --- | --- |
| P2 | `mvp2_s2_synthetic_worker.py`, independent diagnostic adapter, strict exact-step controller | One complete release for all five adverse cases, expected prefixes, separate immutable attempts, stop on unknown effects and terminal/cleanup audits; no admission yet |
| P3 | `mvp2_h300_native_worker.py`, controls, worker evidence and analytical fixtures | Fresh installed runtime/license, integrated native miniature, real resources/partial exports, frozen native budget and explicit300/390-second cleanup compatibility; no admission yet |
| P4 | h300 thread contract/policy, native worker, partial/terminal evidence | One homogeneous six-hour allocation,16requestedCPUs/192GiB, cold serial4/1/8/2/16,1800-second global optimize windows, per-arm stop/unrun inventory; no admission yet |

Prepare these integration/test/result-table surfaces while waiting for evidence;
do not turn the inventory into a pre-submitted afterok chain. P5 independently
compares quality/resources and records exit or inconclusive configuration; an
unrun contracted grid does not silently close full S2. Scientific/h400/SCIP/h500/
S6 scope, S3/S4 cancellation, EVPI/VSS exclusion and final post-article branch
reconciliation remain unchanged. No article or original certificate is edited.
