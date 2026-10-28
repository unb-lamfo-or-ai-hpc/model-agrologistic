# MVP2.0 continuation checkpoint — 28 October 2026

## Implementation progress after authorized PR133 integration

PR133 merged at4608250d…; the native8h/Slurm12h package and its frozen
82cb58ff… human handoff are complete, awaiting manual NPAD execution/evidence.
PR134 implements the scalar Pyomo HiGHS/CBC version with public miniature
qualification and the explicitly proved bounded-slack representation.
See [the implementation/qualification boundary](pyomo_multisolver.md).
Its own merge remains a human gate. The older implementation-stub descriptions
below are the retained design-stage snapshot, not the current software state.
M1 is implemented; M2 still needs installed-runtime, small/medium build/resource
evidence and a complete separate large-instance operational package.
CBC is implemented/tested on public controls, without a population experiment.
No moving develop pin, automatic solver fallback, additional SCIP attempt,
h215 HiGHS/CBC job or new scientific observation is admitted by this update.


This is the active plan, superseding pending-SCIP and pending-h500 descriptions
in older dated checkpoints. Preserve those histories and their original claims.

## Completed and still open

S0/S1 and the adopted S2 work are closed in their retained original evidence.
The former broad S3/new-solvers and S4/decomposition campaigns remain cancelled;
the researcher's current bounded solver requests are explicit extensions,
not resurrection of that old campaign. S5 closed with authorized PR130.
Accepted scalar Gurobi evidence is eleven observations: nine W across
h215/h300/h400/h500 and two D at h215. The separate scalar SCIP STO/W h215 job
2225638 is now an audited negative observation: timelimit, zero solutions,
no usable incumbent, normal operational closure. It is not a twelfth accepted
feasible solution. See [the original audit](mvp2_scalar_scip_h215_w_results.md).

PR131 was merged with explicit authorization at
`083e5759ee5bb4d4d2982c4dcf2ffd12f2afb476`. Source actually executed:
`cbd64d86914dd416ed16b6a58ffe1069401e3aad`; plan:
`1af2f262961cfcca46edfca6a2663e5e82267b3dab0dcefedebea3785761a7fe`;
archive: `41557726ecd93ab67a5764077ea18a35e08db4d6f97123a03ebd6b72930ebf68`.

## Sprints and complete functional PRs

| Sprint / PR package | Deliverable and exit evidence | Dependency / human gate |
| --- | --- | --- |
| S6-A1 — this results/checkpoint PR | Safe original archive/source/certificate audit; negative SCIP result in manuscript; redacted ledger; revised plan | Exact-head native, analytical, quality and rendered document qualification; own merge approval |
| S6-A2 — next SCIP 8 h operational PR | One fresh cold STO/W h215 observation; predecessor hash; 12 h reservation, 8 h native ceiling; full driver/worker/phase/collector/auditor/test/runbook package | Prior audit integration; no old claim edits; own qualified merge; human inventory and pinned NPAD CLI |
| S6-A3 — longer SCIP results PR | Audit original positive or negative terminal evidence, sparse telemetry qualification, manuscript comparison | Human terminal collection and MobaXterm transfer; independent audit; own merge |
| M1 — multisolver contract/Pyomo core PR | Implement currently empty DET/STO Pyomo backend; explicit capability matrix; proved indicator translation; common result/validator; analytical and cross-backend public controls | No large HPC test; exact-head equivalence/resource/export/negative-path CI; own merge |
| M2 — HiGHS qualification/operational PR | Version-pinned interface, original-scale build estimate, miniature/medium correctness and resource gates; complete one-shot h215 protocol if gates pass | Existing-runtime inventory first; user intervention for missing HPC/local packages; own merge and human CLI |
| M3 — HiGHS results / optional CBC qualification PRs | Retain every outcome; audit before adding further solvers; CBC only after its separate capability/parity/resource gates | No automatic fallback, solver sweep or failure-seeking selection; own merges and distinct human executions |
| S6-A4 — integrated scientific/coauthor PR | Reconcile final manuscript, all observations/limitations, captions, author responses and figures | Can progress alongside solver preparation; do not mark unperformed experiments as results |
| S6-B1 — reproducibility and submission package PR | Exact source/results inventory, scripts, appendices, editable source/PDF, rights, declarations, references and author checklist | No raw restricted input/archive publication; GAMS compilation/parity remains unperformed unless actually qualified |
| S6-B2 — final branch/review delivery PR(s) | Recheck develop/main heads and main-only history; normal reviewed integration, final rendered bundle and author-approved snapshot | Explicit merge approvals; separate publication/release/deposit/submission authorization |

PR numbers after this checkpoint are assigned only when created. Do not reserve
invented numbers or promise a count that excludes necessary evidence corrections.
Keep whole operational paths together instead of issuing fragmentary launcher PRs.

The new requests make the longer SCIP run and a qualified HiGHS attempt planned
experimental extensions. A negative outcome is a valid scientific observation,
not a reason to keep tuning until success or failure. If a formulation, installed
runtime or resource gate blocks an extension, report the actual blocker and
obtain the researcher's scope decision before declaring that requested work
complete. CBC is an additional candidate, not an indispensable unbounded sweep.
Editorial work should proceed while human jobs run; final closure must reconcile
the requested extensions and author decisions rather than silently omit them.

## One longer SCIP observation: proposed budget

Hypothesis: doubling the native window may allow progress beyond the observed
root-level work and possibly a usable incumbent under the same scientific
contract. Success is not presumed; no-incumbent, above-gap, rejected, memory,
preemption, operational and time-limited outcomes are all retained.

| Phase / resource | Proposed ceiling |
| --- | --- |
| Input/build | 3,600 s |
| Native optimization | 28,800 s (8 h), one optimize call |
| Return/disposal/export | 900 s |
| Independent validation / review | 1,800 s |
| Worker numeric step | 35,100 s (9 h 45 min) |
| Setup/cleanup outside step | 1,800 s |
| Planned total | 36,900 s (10 h 15 min) |
| Slurm reservation / reserve | 43,200 s (12 h) / 6,300 s (1 h 45 min) |
| Allocation / worker affinity / solver ceiling | 24 logical CPUs / 16 logical CPUs / 4 threads |
| Memory | 192 GiB allocation; original SCIP limits/memory=163840 MB |

Reservation product: 288 logical CPU-hours, not measured utilization or a charge
estimate. Verify partition/account/QoS/12 h availability in the later human
preflight; the original 8 h allocation does not prove a 12 h job will be admitted.

Keep original h215 workbook/population/order/W predecessor, source math,
native versions (or separately review a version change), Seed42, gap0.01,
penalties90000/45000/45000, units and residual tolerances1e-5/1e-8.
No concurrent-mode switch, warm start, solver tuning, extra DET/D arm or changed
constraint representation is bundled into the longer-window observation.
Use a new claim such as `.mvp2-scalar-scip-h215-w-native8h-v1`, below the allowed
audit directory. The original claim and its driver remain immutable. The future
protocol must bind both the original archive digest and the new source/plan,
record uncertain submission as consumed, and refuse repeats on existing claims.

Qualify observation in a process independent of the native solver if feasible,
without solver API calls from a sampling thread. Record actual sample intervals,
probe duration, failures and phase/step ownership. The current sampling gap is
observed; GIL blocking or observer-caused slowdown is not independently proven.
Any instrumentation correction must be separately tested, declared as an
operational difference and must not alter mathematical source or solver settings.
Do not require dense telemetry by changing the historical acceptance certificate.

Stop after this one new observation. Audit it before proposing tuning, a third
SCIP window, another population or execution of a new backend.

## Multisolver direction and completion calendar

See [the architecture plan](mvp2_multisolver_plan.md). PySCIPOpt is already native;
Pyomo currently raises not-implemented. Agnostic dispatch/data/result types exist,
but scalar formulation/equivalence, capabilities, bounds, lifecycle and telemetry
need implementation for each additional backend. Availability is not qualification.

Planning starts on 28 October. The retained 15 November methodological milestone,
23 December consolidation and 31 December submission target are review targets,
not promises. Reassess after the longer SCIP/HiGHS gates and coauthor response;
January 2027 remains the conservative completion window if those dependencies
slip. Final MVP2 closure needs reproducible retained results and author approval,
not every solver succeeding. GAMS compilation/numerical parity, new routing,
penalty calibration, EVPI/VSS and decomposition are not silently added.

## Authority and next owner

Codex edits branches, checkpoints and PRs autonomously through GitHub; no local
clone, new environment or local package installation. Only the researcher merges
after authorization, executes NPAD CLI and transfers originals with MobaXterm.
No new files in the NPAD home root. Raw evidence stays temporary/restricted.

This checkpoint releases no new scheduler/solver execution. Next Codex step after
this PR's authorized integration is the complete longer-SCIP operational package;
multisolver/Pyomo implementation and coauthor preparation may proceed in separate
qualified PRs. Final publication, dataset update and journal submission remain
explicit human decisions. Earlier Pages approval stays bound to its old snapshot.
