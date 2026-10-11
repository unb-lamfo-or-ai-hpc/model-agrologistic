# Model Agrologistic — MVP 2.0 checkpoint

Updated 11 October 2026. This public checkpoint contains scope and provenance,
not private evidence, credentials, local host paths or execution authority.

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
- PR #64 portable memory is integrated into develop by the authorized merge
  above. Earlier independent/HOLD wording describes its initial proposal only.
  Its files are now part of develop and any later reviewed main promotion unless
  an explicit scope decision changes that promotion. No main merge is authorized
  by this checkpoint. Next owners: agent qualifies the closed compute identity
  correction, then a complete successor integration/admission; maintainer reviews
  merge only after Ready. No NPAD execution is requested by this correction.
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
