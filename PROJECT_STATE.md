# Model Agrologistic — MVP 2.0 checkpoint

Updated 9 October 2026. This public checkpoint contains scope and provenance,
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
- Current PR scope: closed synthetic launcher/controller components through
  injected transports, strict process/scope barrier checks, fixed synthetic
  phases and portable partial/adverse evidence replay. No live batch adapter,
  admitted worker CLI or execution admission. No real fork tree runs in fixtures.
  No NPAD CLI, native miniature, h300 optimization or repeat is admitted.
- Next gates: actual bounded batch adapter and explicit synthetic-only gate,
  then live containment audit; licensed miniature integration; fresh h300
  admission; one diagnostic block and evidence/decision. S2 is not complete.
  A limited window cannot establish full-budget speedup from censored timings.
- Maintainer scope decision: cancel former S3 (new solvers) and S4
  (decomposition). No HiGHS/CPLEX/decomposition implementation is required.
- After S2, requalify the existing SCIP/SoPlex h215 root-LP bottleneck with a
  small justified hypothesis set and positive controls; no universal inability
  claim or indiscriminate tuning campaign. Then assess h500 Gurobi, preferably
  direct-enabled to preserve the accepted h400 policy, through separate gates.
- S6: substantive computational/HPC discussion, full adverse-result provenance,
  coauthor reconciliation and reproducibility packaging. Remove section 3.8 and
  EVPI/VSS then; those calculations are not remaining work. Article/presentation
  remain unchanged before S6. Release/deposit/submission require later decisions.
- Maintainer requested main/develop reconciliation only at S2 closure. On
  9 October, GitHub at develop `a4ce020` reports 111 commits ahead / 1 behind main;
  this is a dated UI observation, not a frozen final comparison. Recheck both
  exact heads at closure, incorporate main-only history into develop by reviewed
  PR if needed, then propose develop into protected main. Verify main ancestry
  and equal integrated trees; do not force-push, bypass or weaken protection.
  A merge commit on main can require a final main-to-develop back-merge to leave
  develop literally not behind main. No synchronization is performed now.

See [authoritative roadmap](docs/mvp2_hpc_roadmap.md),
[S1 evidence ledger](docs/mvp2_sprint1_closure.md),
[closed native integration](docs/mvp2_h300_native_worker.md) and
[whole-worker evidence/resource gate](docs/mvp2_h300_worker_evidence.md) and
[containment prerequisite and operational runbook](docs/mvp2_s2_containment_gate.md).
The completed input-only gate is followed by the
[closed Slurm-step design and v1 observation gate](docs/mvp2_s2_slurm_step_gate.md).
The next software layer is the
[closed synthetic controller and collection](docs/mvp2_s2_synthetic_controller.md).
Merge requires maintainer approval after exact-head qualification and Ready.
