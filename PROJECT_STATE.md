# Model Agrologistic — MVP 2.0 checkpoint

Updated 12 October 2026. This public checkpoint contains scope and provenance,
not private evidence, credentials, local host paths or execution authority.

## Latest operational checkpoint — allocation diagnosis

PR #74 remains separate from develop. Its diagnostic job 2208438 at source
`1c33692f9affdf3ec5dece387a9425cf5b2fd671` completed 0:0 in three seconds.
Archive SHA-256 `7042a46430a2bac242080306e86a5a81f6c165949ca537abba4c5d329980157e`
independently replays `observed_mismatch_or_query_failure`. The query succeeded;
seven comparisons matched. Only NodeList and BatchHost failed: Slurm short node
`r1i3n5` versus local FQDN `r1i3n5.npad.internal`. No memory/CPU/time mismatch
was observed. [Evidence and bounded correction](docs/mvp2_s2_node_identity_evidence.md)
retain the original negative diagnostic, plan/source identities and limitations.
Reported NPAD tests: 59 passed, zero failures/errors/skips; XML not transferred.

The same PR now qualifies the observed rack-FQDN mapping only for `.npad.internal`,
retains both exact allocation node checks and carries that scheduler identity
into the worker handshake. Other domains are not shortened. Resource, membership,
peer, source/runtime, controller and scientific checks remain unchanged.
This is software correction, not live normal/containment acceptance. All old
claims remain consumed; no normal retry or diagnostic repeat is admitted.
Next owner: agent completes exact-head CI and Ready; maintainer decides merge.
A fresh normal-only execution gate must subsequently bind corrected merged source
and a distinct immutable claim. Earlier next-action statements below are historical.

### Prior diagnostic planning (preserved)

PR #73 merged into develop at `478d5ee513994a20e8788f1f504b195a7f67f346`.
Job 2208339, frozen source `f96d9729f2a3bf7a8310094aa8a675b224b203d1`,
failed 2:0 in four seconds. The independently replayed archive SHA-256 is
`b10d4e4c2930a4dce0ea685b8aa0af4a1effff815da878e652c50712e4f3cc95`;
release `baeed8c999179e36f824b9faf9fa2f5caac3885b1099c385c59b3db302f40e46`.
Outcome remains `no_attempt_receipt`, wrapper `blocked_before_launch`, phase
preflight, ValueError at original adapter line 485 (`review_allocation`).
This is later than the supervisor membership guard, not worker acceptance.
The portable carrier has no raw allocation response and cannot identify the
failed predicate. Empty stderr is consistent with a handled rejection.

Maintainer-supplied accounting for jobs 2208056/2208339 reports two requested
and allocated CPUs, 2G memory, one node, twelve minutes. It does not reproduce
the exact live `scontrol` field representation. The later `scontrol` record was
unavailable. No resource increase, relaxed identity check or cause is inferred.
NPAD regression was reported as 595 passed/two intentional skips; source inventory
was verified. Both consumed claims and all original evidence remain immutable.

The [allocation diagnostic protocol](docs/mvp2_s2_allocation_diagnostic.md)
supplies one bounded observation-only batch, field-by-field comparison, durable
claim, terminal/cached collection and portable audit. It does not modify the
normal adapter or launch a worker. A qualified immutable diagnostic PR head may
be observed before merge under the maintainer's approved diagnostic scope.
The same PR remains draft for the observed-data correction and final qualification;
there is no normal retry or automatic next gate. Next owner: agent qualifies and
freezes the diagnostic handoff; maintainer executes/returns evidence. Earlier
"next owner" statements below are historical. S2 remains fully planned and open.

## Preserved history and scientific scope

- MVP1 `v0.2.0-mvp1` stays frozen. S0 and adopted S1 scope are closed.
- S1 accepted evidence includes h215 pairs, h300 warehouse-only baseline/pair
  and one h400 direct control. Compaction remains optional/default-off; causal
  acceleration and smaller resource allocations are not established.
- S2 PRs #53--#57 are integrated. PR #57 merged into develop at
  `cac69ba0e86958b39d85e48ec8513f65bc2dd5e1`. Licensed analytical thread
  miniatures are accepted, but the h300 thread block has not been executed.
- Whole-worker evidence/source/runtime/cohort binding is software-qualified;
  effective live containment is not yet established.
- PR #58 merged at `9bf4160b20b6909a594e931f4da14d576f840776`.
  Input-only job 2202795 evidence is independently accepted (SHA-256
  `68604864018944b1afe7d546207a1a8881a5a473fed5a49896f389d0fcef325e`),
  but the probe is blocked_environment: observed cgroup v1, not the required v2.
  Collection success is not effective containment or S2 closure.
- The subsequent read-only inventory declares Slurm cgroup tracking/task plugins,
  linux accounting, KillWait 300 s and UnkillableStepTimeout 60 s; both observed
  client versions are 22.05.11. It proves neither daemon versions nor live limits.
- PR #59 merged at `a4ce020d01298a292ab10819d21355775a562b85`: closed
  numeric-step contract and read-only cgroup-v1 observer are software-qualified.
- PR #60 merged at `4472c8429a2aa99d10a716d827f1f6bfa0ec022a`: closed
  synthetic controller/launcher and portable evidence components are integrated.
- PR #61 merged at `dd68588a5bdfe1f6536e357dab049509678659e4`:
  real bounded POSIX transport, kernel-peer IPC bridge,
  raw HEAD/runtime/allocation preflight, actual-step binding, durable controller
  integration and terminal partial/adverse collection. Public batch/worker CLIs
  remain closed. Offline software evidence is not installed NPAD containment.
  No real synthetic tree, native miniature, h300 or repeat is admitted.
- PR #62 merged at `01016fbbbdfdc6dd7cf005488105b4d3181f671d`.
  Its read-only bootstrap stopped in regression before the envelope probe:
  maintainer reports 166 passed, one failed, one intentional skip, exit 1 and
  no submitted job. The real local IPC fixture used an oversized pytest socket
  path; this is not a solver, license or live-containment result. The reported
  run directory's present location is unresolved; preserve any original files.
  The [envelope recovery correction](docs/mvp2_s2_envelope_recovery.md) uses an
  exclusive short test socket, retains the production byte-length guard, adds
  negative boundary coverage and a versioned location-aware read-only driver.
  Corrected source must be merged and pinned before observing the envelope.
- PR #63 merged at `0dccbfd5d25c4db97a74baf5da3766d7433c82a1`.
  The independently audited read-only archive at source
  `7532beea7ffa429ba9f34bfd091bd60069efc4f8` has SHA-256
  `e86c703eb59336230ed9c3af6efc4fd602f9acf2b702ddbbb4553c650346b45a`.
  Outcome observed_not_admitted; Python/tool identities and declared Slurm
  settings recorded, not live job/step grammar or effective containment.
  [Public original records](docs/evidence/s2-envelope-pr63/README.md) retain
  the old source identity. Maintainer reports 169 passed, one intentional skip,
  exit zero and preserved run; XML/private envelope were not transferred.
- PR #65 merged first at `b7506e0efbc520411d80d2394d8b7d06a27d3dc9`,
  then PR #64 at `60c43d7a52389eee2822a08701801792a9b79548`, following
  explicit maintainer authorization. Both develop push Quality runs passed.
  Frozen first-normal source remains `12691638cd85d5218725bf704dc6b9452b1ca90c`.
- First-normal synthetic job 2207167 failed, root/batch exit 2:0 after two seconds.
  Independently verified archive SHA-256:
  `03ee4d87bf69994fc4f0401e206a67109539ad2dfe0770cd3246b7415e952007`.
  [Public semantic records](docs/evidence/s2-first-normal-2207167/records.json)
  reproduce the original v1 review: integrity_replayed_not_live_qualified,
  batch blocked_before_launch, controller not_replayed, worker outcome unknown,
  null worker contract and no inner worker bundle. This is accepted integrity
  of a negative operational observation, not a qualified normal test.
  Reported NPAD regression: 241 passed/two intentional platform skips; XML
  not transferred. Subsequent maintainer-supplied log inspection reports empty
  stderr, stdout with only the blocked status, and the expected frozen batch
  command. Those raw logs were not transferred or committed independently.
  The swallowed pre-launch exception's cause/phase cannot be reconstructed.
- PR #66 merged into develop at `f51688b9692058e2d0a639125b65fb5f1ff805ac`.
  Its exact-head four checks passed; local qualification reported 507 passed
  and five Windows capability/platform skips. Versioned [normal batch diagnostics](docs/mvp2_s2_first_normal.md)
  record fixed phases/error categories and allowlisted module/line locations,
  never exception messages or raw scheduler responses. Legacy v1 replay stays
  unchanged; no historical receipt is upgraded or given an invented diagnosis.
  The diagnostic correction does not admit a new submission or retry.
  Preserve original source, run, claim and collection; do not patch the consumed
  NPAD checkout. The next scoped [normal recovery gate](docs/mvp2_s2_normal_recovery.md)
  qualifies one independent claim, immutable predecessor binding and one bounded
  normal-only observation with the same resource limits. No root cause or live
  qualification is assumed. Human CLI is deferred until this gate is qualified,
  Ready, reviewed and merged; no adverse/native/h300/repeat is released.
- PR #67 merged at `fe56d465720d396ebfb2c7f202fb0482db0d91ad`.
  Recovery job 2207181 at `c74f316e30a1b034368ce15b4877d03f31c5d09b`
  failed 1:0 in two seconds. Independently verified recovery archive SHA-256:
  `264037fafd7ef52a74e3854b35213228a257d2f3f98f8f55e5ec29fc4eab8b8f`.
  [Audited records and supplemental diagnosis](docs/evidence/s2-normal-recovery-2207181/README.md)
  retain missing_terminal_batch_receipt, unknown worker and no live qualification.
  Maintainer-supplied stderr identifies missing `/usr/bin/git` while rechecking
  predecessor login tools on the batch host, outside shared diagnostics. This
  is not proof of the original 2207167 cause or a solver/license failure.
  The [closed compute identity correction](docs/mvp2_s2_compute_identity.md)
  separates login raw-Git provenance from compute file/runtime checks and covers
  early entry failures. Successor protocol/evidence integration is still required;
  no retry or new normal job is admitted. Preserve both consumed attempts.
- PR #68 merged into develop at `a2501f81cd4c45916b09227a378fe1505e97e190`.
  The [successor closed integration](docs/mvp2_s2_compute_integration.md) connects
  sealed login provenance and both immutable predecessors to Git-free batch,
  worker and adapter checks, role-specific v2 attempt/collection semantics and
  bounded early-log collection. Historical readers/certificates stay unchanged.
  This is offline software qualification, not installed NPAD qualification.
  A fresh immutable one-shot driver and its CLI wiring remain a separate gate;
  the new public entry denies execution and no claim/job/retry is admitted.
- PR #69 merged into develop at `d6ab499c634bd03432f968c76df61d5cc521b862`.
  The [one-shot normal operational gate](docs/mvp2_s2_compute_normal.md) now
  supplies the fresh driver, immutable pre-effect proposal/job-release binding,
  actual Git-free batch/worker routes and portable terminal collection.
  This proposed gate permits only one normal synthetic observation after its
  own qualification, authorized merge and maintainer CLI execution. No new job
  is reported here. Unknown effects consume the new claim; both earlier attempts
  remain read-only. Independent terminal review still precedes adverse cases,
  native miniature, h300 or repeats; no live-containment or S2-closure claim.
- PR #70 merged into develop at `1463dcf8b3280e5799edbf017daafc71e49bd70a`.
  The maintainer authorized its one normal observation at frozen source
  `d83d4e3e569b140da76d65f7b9615f638dba5798`. Reported NPAD regression:
  481 passed/two intentional skips in 27.07 s. Preparation then failed with
  `Extra source directory` while sealing current source, before claim creation
  or sbatch. Read-only follow-up confirms `scripts/__pycache__` in the current
  checkout and both predecessors, and CLAIM_ABSENT. No new job or terminal
  archive exists for this bootstrap. These are maintainer-supplied observations,
  not a newly checksum-audited NPAD carrier; preserve the failed checkout/XML.
  Local reproduction establishes that isolated regression subprocesses without
  explicit `-B` ignore PYTHONDONTWRITEBYTECODE and create the cache. The
  [scoped correction](docs/mvp2_s2_compute_normal.md#bytecode-recovery--12-october-2026)
  prevents that contamination, checks physical closure before/after regression,
  and distinguishes strict current execution source from immutable historical
  tracked-byte evidence. Historical caches are neither deleted, imported nor
  certified; original archives/receipts retain their identities and semantics.
  A fresh corrected checkout/source needs exact-head qualification, authorized
  merge and a separately authorized normal-only CLI. Absence of the unused
  claim does not authorize a retry; any later existing/unknown claim blocks
  substitution. No adverse/native/h300/repeat gate is released.
- PR #71 merged into develop at `c68b7505c854124ea37df50d6b1d07dd3fa680db`.
  Its authorized normal job 2208056 at source
  `7bb3bd60036e504ea3290f077282948a612728da` failed 2:0 in five seconds.
  [Independent terminal audit and client diagnosis](docs/evidence/s2-compute-normal-2208056/README.md)
  verify archive `b9efc61243e0adddf2c7f15e9e8f2d89152e038221ca53d82ef207bf1d06d59b`
  and replay `no_attempt_receipt`. The outer wrapper identifies preflight
  `Supervisor not in batch step` at original adapter line 711. Empty stderr is
  consistent with a handled exception. Source review of Slurm 22.05.11 identifies
  unsupported symbolic `.batch` input and previously unhandled descendant `- -`
  task IDs. Raw installed query output is unavailable; no live reproduction is
  claimed. The bounded parser/transport correction keeps membership enforcement,
  rejects reserved worker/signal aliases and qualifies software paths only.
  The compute claim is consumed; earlier unused-claim wording is historical.
  A new one-shot gate bound to this negative predecessor still needs complete
  qualification and explicit merge/execution approval. No new claim or job is
  admitted by the correction; preserve all three attempts. No live normal,
  adverse, native, h300, repeat or S2-closure acceptance follows from this audit.
- PR #72 merged with explicit maintainer authorization into develop at
  `7005b08e596ac47df3d9a9d6af13c2c563f07d64`; four exact-head checks passed.
  The [successor normal gate](docs/mvp2_s2_normal_successor.md) supplies complete
  start/batch/worker/collect/audit wiring with a distinct immutable claim and
  three-history release. The job 2208056 source, proposal, release, receipt,
  wrapper, logs and checksum-bound archive are read-only prerequisites.
  The historical reader is retained; current compute verification uses sealed
  bytes, never historical imports or Git. No new normal observation has run.
  Next owner: agent qualifies the successor PR; maintainer authorizes merge
  only after Ready and separately authorizes/executes its frozen normal CLI.
  All adverse/native/h300/repeat admission flags remain false.
- S2 remains FULLY planned and open: P2 normal audit/adverse qualification;
  P3 adverse containment audit/licensed native integration; P4 licensed audit
  and fresh h300 admission; P5 diagnostic 1/2/4/8/16-thread block audit,
  resource/quality interpretation and configuration decision. Missing evidence
  may justify scoped corrections, never bypass. No repeat is automatically
  admitted; limited/censored windows do not establish full-budget speedup.
- Maintainer scope decision: cancel former S3 (new solvers) and S4
  (decomposition). No HiGHS/CPLEX/decomposition implementation is required.
- Approved 10 October: after S2 select a candidate h400 computational profile
  from actual resource/quality evidence, then separately admit one new validated
  attempt. The accepted S1 h400 control stays accepted and is not rewritten.
  Requalify existing SCIP/SoPlex h215 with an explicit root-LP hypothesis,
  smaller positive controls and one bounded justified execution; no universal
  inability claim or indiscriminate tuning. Keep h500 planned, conditional on
  the new h400 success/resource gate, not on SCIP success. No new solver.
- S6-A consolidates MVP2 results and HPC interpretation; MVP1 is historical
  context only where needed. S6-B prepares the MVP2-focused manuscript,
  figures/supplement and reproducibility package. Preserve the authoritative
  coauthor revision and original certificates. Remove section 3.8/EVPI/VSS
  at S6, not now. Release/deposit/submission need later decisions.
  December 2026 is a target, not a commitment: the base planning window is
  January 2027 if sequential containment/experimental reviews slip. Do not
  reduce approved experiments to claim the editorial target was met.
  The revised 12 October mandate preserves M2 methodological validation on
  15 November, M3 scientific consolidation on 23 December and M4 submission
  target on 31 December. These targets do not erase the conservative forecast;
  reassess after live normal/adverse evidence. Use complete functional PRs and
  focused/related/final qualification; no general refactor or runtime migration.
- PR #64 portable memory is integrated into develop by the authorized merge
  above. Earlier independent/HOLD wording describes its initial proposal only.
  Its files are now part of develop and any later reviewed main promotion unless
  an explicit scope decision changes that promotion. No main merge is authorized
  by this checkpoint. Next owners: agent qualifies the fresh normal-only
  operational driver; maintainer reviews merge only after Ready, then executes
  the separately frozen CLI. Do not run a branch-head script before that handoff.
  Independent terminal audit precedes every later admission.
- Maintainer requested main/develop reconciliation only at S2 closure. On
  9 October, GitHub at develop `a4ce020` reports 111 commits ahead / 1 behind main;
  this is a dated UI observation, not a frozen final comparison. Recheck both
  exact heads at closure, incorporate main-only history into develop by reviewed
  PR if needed, then propose develop into protected main. Verify main ancestry
  and equal integrated trees; do not force-push, bypass or weaken protection.
  A merge commit on main can require a final main-to-develop back-merge to leave
  develop literally not behind main. No synchronization is performed now.
- Main ruleset `model-agrologistic-main-protect` (24804465) is Active, targeting
  only main. PDF snapshot SHA-256
  `b2860c7cfc51bca4387a03e8dd92fc1a4232caf633fea435543080b9c3d25866`
  and read-only live settings review on 9 October confirm restrict creations,
  updates and deletions; required status check `check-branch` (Any source);
  Organization admin has Always allow bypass. Require-PR, linear-history,
  up-to-date-before-merge and block-force-push boxes are not selected. This is
  not immutability or proof of a particular actor's admin/bypass role. Recheck
  all effective rules/check provenance at S2 closure; no rule is changed or
  bypassed. The check's implementation/provenance is not yet audited here.

See [authoritative roadmap](docs/mvp2_hpc_roadmap.md),
[S1 evidence ledger](docs/mvp2_sprint1_closure.md),
[closed native integration](docs/mvp2_h300_native_worker.md) and
[whole-worker evidence/resource gate](docs/mvp2_h300_worker_evidence.md) and
[containment prerequisite and operational runbook](docs/mvp2_s2_containment_gate.md).
The completed input-only gate is followed by the
[closed Slurm-step design and v1 observation gate](docs/mvp2_s2_slurm_step_gate.md).
The next software layer is the
[closed synthetic controller and collection](docs/mvp2_s2_synthetic_controller.md).
The current integration gate is the
[closed real batch adapter](docs/mvp2_s2_batch_adapter.md).
The following gate is the
[closed operational proposal and read-only envelope](docs/mvp2_s2_operational_protocol.md).
Merge requires maintainer approval after exact-head qualification and Ready.
