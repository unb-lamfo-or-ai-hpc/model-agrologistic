# S2 A job2212000: Slurm22.05 resource-reader correction

15 October 2026. PR #99 merged into develop at
`b6100b8120a60d21d49a5f308a8f929191e2238a`. Reviewed experimental source:
`faa7ec6ee2629a34210917f81a34193ad7fc6c6c`.

## Immutable negative evidence

| Anchor | Value |
| --- | --- |
| Job | `2212000` |
| Stage | normal A, academic profile v1 |
| Plan SHA256 | `66f911b103a7d62d4016d8e3baf1253399c7009fb108140cb23652efd7411131` |
| Archive SHA256 | `52f4e69ad527972f253cd81a1e9cdcc0925ca2fad30b14e2fbf19918c1b4f533` |
| Root/batch | FAILED,1:0,4s; batch MaxRSS1084K |
| Extern | COMPLETED,0:0,4s |
| Numeric worker step | Not present in preserved accounting |
| Records | Empty object |
| Independent replay | `evidence_not_accepted`, canonical review reproduced |

The transferred archive and sidecar match the external checksum. The original
claim/run/archive/checksum, source and rejected result stay unchanged. This is
neither a native solver/license failure nor an agricultural infeasibility result.
No normal, adverse, native or h300 live acceptance follows.

## Confirmed mechanism and provenance limits

The maintainer supplied the bounded slurm.err traceback: the batch passed
source/runtime checks and reached allocation validation, then raised
ValueError("Requested resources.") before srun. A subsequent read-only terminal
scontrol query reported JobState=FAILED, NumNodes1, NumCPUs2, NumTasks1,
CPUs/Task2, TRES cpu2/mem2G/node1, MinMemoryNode2G and TimeLimit00:12:00;
ReqTRES and AllocTRES were absent. Identity/account/partition/node checks had
already passed in the batch. The terminal query is supplemental maintainer
evidence, not an original running-state archive member or a new job observation.
It is never relabelled RUNNING. Tests construct an explicitly synthetic running
fixture from its redacted resource fields.

The PR99 reader expected ReqTRES, substituted an empty string for its absence,
then compared cpu0 against the requested cpu2. Absence is not a measured resource
deficit. Slurm22.05's authoritative
[job output implementation](https://github.com/SchedMD/slurm/blob/slurm-22-05-11-1/src/api/job_info.c#L649)
prints TRES from the allocated record while running (requested otherwise), and
prints CPUs/Task plus MinMemoryNode/MinMemoryCPU. TRES must not be renamed
ReqTRES: requested resources and allocated CPU rounding are different facts.
The earlier repository allocation diagnostic already preserved this distinction;
the new academic path failed to reuse that installed-format knowledge.

## Complete corrective delivery

- Support explicit ReqTRES where available, or the reviewed single-task
  CPUs/Task+MinMemoryNode request fields on Slurm22.05. Validate the allocated
  TRES/AllocTRES independently against NumCPUs and exact node memory. Keep the
  existing allowance for allocated CPU rounding above the fixed request.
- Reject missing, malformed, duplicated or contradictory resource aliases,
  wrong requests, per-CPU memory, multiple nodes/tasks, identity or walltime drift.
  Budgets, affinity, scientific formulation, solver settings and validators do
  not change. This corrects serialization compatibility, not resource criteria.
- Preserve allowlisted scheduler fields in allocation.json and independently
  recompute those fields during archive replay. A portable bounded batch
  diagnostic retains the phase, exception class and selected scheduler fields
  even before worker launch. No exception message, raw traceback, private path,
  environment dump or license text enters the portable evidence.
- Use distinct academic-v2 claims for all seven stages, never a reset/reuse of v1.
  A v2 normal start must first replay the exact rejected job2212000 archive with
  its external source/plan/job/checksum anchors. Missing/corrupt history blocks
  before new claim creation or submission. Negative history is not acceptance.
- Keep one reviewed human slot per stage and A -> five independently audited
  P2 outcomes -> complete accepted native P3 -> separately qualified P4. Same-source
  predecessor replay, unknown-ack consumption and cached immutable collection stay.

No NPAD execution occurs during this repair. Complete exact-head Linux checks,
mark Ready and obtain this repair's separate merge authorization before supplying
a newly pinned successor CLI. Do not reuse the PR99 start command or invent a
new claim by manually editing the old launcher. P2/P3/h300/repeats stay blocked.

## Qualification and limits

Regressions cover the actual redacted field shape, terminal-state rejection,
modern/legacy equivalence, synthetic/native budgets, CPU allocation rounding,
conflicting/missing/duplicate resources, redaction/replay tampering, early batch
diagnostics, no launch on rejection, historical checksum binding and immutable
namespace/cache semantics. Scheduler/native effects are injected; no installed
NPAD success is claimed from these tests. Original archive replay remains negative.
Local platform skips and exact-head Linux CI are reported separately in the PR.

Local focused qualification:277 academic/native/partial/control cases,
275passed/two explicit POSIX process-group skips, zero failures/errors. The new
recovery module adds33 cases; the human bootstrap exercises119 academic cases.
Exact-head Linux CI requires all277 cohort cases without skips. These counts
do not claim a full Windows suite or live NPAD success.

S2 remains open. This is an evidence-driven correction, not a new scientific
campaign. P4/P5, later h400/existing-SCIP-h215/conditional h500/S6-A/S6-B remain;
S3/S4 cancelled, EVPI/VSS excluded and main synchronization after article review.
