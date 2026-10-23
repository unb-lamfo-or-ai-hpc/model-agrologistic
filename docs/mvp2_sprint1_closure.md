# MVP2 S1-C: evidence consolidation and bounded Sprint 1 closure

## Decision and integration boundary

Prepared 8 October 2026 after PR #51 was merged into develop at
`76855e0de84d4f081f1c97facc19d2b036923575`. This is a documentary closure,
not a new run, scientific-core change or retrospective alteration of receipts.
S1-A and S1-B experimental observations are accepted and integrated. S1-C and
the adopted bounded S1 scope close when this documentary PR is merged after
review. Until then closure is proposed, not integrated.

The evidence supports licensed miniature lifecycle qualification, bounded
instrumentation, observed numerical preservation with optional compaction, and
accepted native-hierarchy execution at h215/h300/h400. It does NOT establish
causal acceleration, a reduced allocation, a universal size limit or production
explicit-rebuild equivalence. Those limits are part of the closure decision.
The older roadmap's broader engineering ambitions are explicitly deferred or
superseded below, rather than declared accomplished.

## Fixed contract

MVP1 `v0.2.0-mvp1` remains frozen. Canonical core/runtime receipt SHA-256:
`b4de41ade0b3c55f8f20a66480cffa275421f8157444b1db3000a9eb50f2d351`.
Production S1 uses Python 3.13.15/Gurobi 13.0.3, nine scenarios, sixty periods,
two products, native service/capacity/economic priorities, four solver threads,
seed 42, Method 2, NumericFocus 1, MIPGap=0.1 and SoftMemLimit=128 decimal GB.
The h300/h400 isolated manifests permit their exact reviewed variable estimates;
the original 25M guard is not globally relaxed. No model/solver tolerance change
is introduced by this consolidation.

Full acceptance requires original independent feasibility, all three certified
priorities under inherited degradation limits and closed evidence, not merely
Slurm COMPLETED/0:0. Portable replay verifies preserved certificates/identities;
it is not a new residual computation or private-workbook reload. OPTIMAL under
these tolerances is not an exact zero-gap mathematical optimum.

## Traceable evidence inventory

Every source is an executed immutable commit, not a later documentation or
merge head. All archive hashes below refer to supplied transfers. Individual
reports retain detailed product hashes, allocation, validator and tool identities.
The accepted h300 baseline has an explicitly separate retrospective review.

| Observation | Job | Executed source | Transfer SHA-256 | Disposition and authoritative report |
| --- | --- | --- | --- | --- |
| Corrected licensed miniatures | 2143922 | `f9aa74abecfe416bac9f505b55c4eeacf4b111be` | Qualification report: `b9e4b2a5bb7ecf66b0c54432986c3033bf381bdea223fc914ddefa7dcc24bde7` | 138 tests, no skips; twelve Gurobi/SCIP observations; [lifecycle](mvp2_resource_lifecycle.md) |
| h215 pair 1, control then compact | 2151415 | `77af8af91fa7f358275afc255c9ab5d9630b4b9a` | `0c17ac4e147de844be716e4fe89a66299a706462670af38fba3cf7bf01f726c3` | Both accepted; [pilot](mvp2_h215_resource_pilot.md) |
| h215 pair 2, compact then control | 2184508 | `5bfaa7a58fab5e714a8fd427fdd79a72976dd0a7` | `6224ac47ba4fd04bcdb75f76ce4014c734d2fde5bb173e903a1c28f786bbe07c` | Both accepted; [consolidation](mvp2_h215_resource_consolidation.md) |
| h215 pair 3, control then compact | 2196511 | `5bfaa7a58fab5e714a8fd427fdd79a72976dd0a7` | `6622e831122d2024dee4f5e20951100ef98f78937b766d2294c23908b97d6929` | Both accepted; [consolidation](mvp2_h215_resource_consolidation.md) |
| h300 input-only retry | 2198085 | `3957f84ff49ac500eecf25b85e6b710b4b3b1010` | `97395d29b802e558d3ac88db8c8e74cf3447d165782530a9c8d7cafd59f106fb` | Input accepted, no solve; [input](mvp2_h300_input_acceptance.md) |
| h300 separate baseline | 2198528 | `d70cade148e190e98d41a5ac3d4e040353f2c6ec` | `43311a0000a3fb09f535ea273bd889ba1a6e09bf728460f0f28b764242e400c2` | Original collector rejected; retrospective accepted; [report](mvp2_h300_baseline_acceptance.md), [review](mvp2_h300_baseline_review.json) |
| h300 descriptive compact-first pair | 2199525 | `0e663c8bd8d9c5c4b27dbb09db3f1375ad52257d` | `5e52e56887dcb57b9c6209fb884129bf85cc322779fc17c2279c589519d4c1d9` | Both accepted; [pair](mvp2_h300_pair_acceptance.md) |
| h400 direct input-only | 2200298 | `de8c9a138526f63883cc2672077fbee4d38c8c60` | `d668f35cff87dcfd7f90c03a14d7b332571e581821ee5a90b80b2ab52e67b8e3` | Input accepted, no solve; [input](mvp2_h400_input_acceptance.md) |
| h400 direct, one uncompacted control | 2200384 | `e2fdc6eead8349fb40008be38858fa0160ac74c8` | `08b60d687227e5e21fe18594ee2bdfe050c57cb5ebf1cc1351ca78632f8b4b3a` | Original and portable reviews accepted; [report](mvp2_h400_control_acceptance.md), [review](mvp2_h400_control_review_2200384.json) |

Archive names, in the same order after the miniature report:

- `pr44-resource-evidence-2151415.tar.gz`
- `pr44-pair2-evidence-2184508-20261005T103800Z-84e67e7a.tar.gz`
- `pr44-pair3-evidence-2196511-20261005T202357Z-1b7a8351.tar.gz`
- `input-preflight-evidence-2198085.tar.gz`
- `h300-baseline-evidence-2198528.tar.gz`
- `h300-pair-evidence-2199525.tar.gz`
- `h400-input-evidence-2200298.tar.gz`
- `h400-control-evidence-2200384.tar.gz`

Transfer completeness is not identical across these records. The h215 pilot
supplies 11 of 33 completion-bound products per arm locally and no full solution
vector; pairs 2/3 supply 25 of 33 locally per arm, with original NPAD closure
receipts and full solution JSON. h300 baseline/pair and h400 control transfers
support all 33 run products per arm. Original large validation certificates
cover 32 families: 1,894,179 checks per h215 arm, 2,362,490 per h300 pair arm,
and 2,534,202 for h400 control, with zero failures. Do not claim all pilot
solution-vector bytes or an identical transfer inventory were replayed.

The h215 pilot source differs from pairs 2/3. Three pairs are not randomized,
balanced, same-node replications of one immutable binary. The separate h300
baseline is not another replicate of the descriptive pair.

## Results and how to read them

Control/compact values below are per application; Slurm measures a whole batch
and is not a per-arm memory observation. GiB means 2^30 bytes. Optimization
time excludes preparation/extraction/validation; it is not end-to-end time.

| Case | Optimization seconds, control / compact | Application peak RSS GiB, control / compact | Inference permitted |
| --- | --- | --- | --- |
| h215 pair 1 | 8867.5448 / 9357.5008 | 61.5443 / 60.3258 | Compact runtime +5.53%, RSS -1.98%; descriptive |
| h215 pair 2 | 9758.8912 / 9730.2901 | 61.6490 / 60.4392 | Runtime -0.29%, RSS -1.96%; descriptive |
| h215 pair 3 | 9833.2961 / 9697.9314 | 61.5416 / 60.5480 | Runtime -1.38%, RSS -1.61%; descriptive |
| h300 single pair | 20584.8192 / 20245.6816 | 59.8286 / 57.9129 | Runtime -1.65%, RSS -3.20%; one pair only |
| h400 single control | 27925.2887 / not run | 101.1107 / not run | 7.7570 h optimization, 8.0566 h application total; no contrast |

All ten large S1 arms complete the inherited hierarchy and original validation.
The h300 baseline's acceptance is retrospective, not its original collector
status. Observed h215 stage/search metrics agree; h300 pair stage metrics and
17 corresponding CSVs agree apart from timing. This supports preservation of
observed numerical behavior, not universal equivalence or unique solutions.

Post-build compaction cannot reduce construction peak. Native memory is
essentially unchanged in paired arms; do not describe lower Python/application
RSS as native solver compression. Shared nodes, fixed/nonrandom order and
limited repeats preclude statistical significance or causal performance claims.
No default change or reduction of the 192 GiB allocation is recommended.

### Intermediate gap is not final-capacity quality

For final capacity F, pass incumbent I and retained bound B, report both
`100*(F-I)/I` (increase over the pass) and `100*(F-B)/abs(F)` (relative difference
to the retained bound, normalized by the final value). The latter is not an
increase normalized by B. The capacity pass gap belongs to the pass solution,
not the final economic-pass solution. Native MIPGap can permit subsequent
degradation even when ObjNRelTol is zero.

| Case | Capacity pass gap | Final capacity increase over pass | Final relative difference to retained bound | Economic pass gap |
| --- | --- | --- | --- | --- |
| h215 paired arms | 0.0253285% | 9.9747% | 9.0930% | 0.00187379% |
| h300 baseline / pair | 0.247793% | 9.7522% | 9.1114% | 0.083114% |
| h400 control | 0.0642526% | 9.93575% | 9.09622% | 0.00370470% |

These outcomes pass inherited priority checks. Near-zero service remains
within its certified absolute allowance. Emergency capacity is still required;
configured candidate investment limits saturate. Penalty shares around 97%
are model penalty composition, not observed financial costs. Do not portray
effectively complete service as a network needing no emergency provision.

### Resource and telemetry limitations

h300 warehouse-only has 25,107,544 variables; h400 direct has 42,426,624. Different
population, direct arcs and decision composition prevent treating their runtimes
as a pure size-scaling effect. The accepted h400 point does not overturn the
MVP1 historical thirteen-attempt cohort or certify every h400 configuration.

Large allocations requested 192 GiB and four CPUs per task but recorded 24
allocated CPUs; the solver still used four configured threads. Shared-node/QOS
conditions are disclosed, not exclusive-node guarantees. SoftMemLimit=128 is
decimal GB, not 128 GiB; actual cgroup admission was finite and independently
checked. Application RSS, periodic process tree, cgroup, native observations
and Slurm MaxRSS have different scope/cadence and must not be substituted.

h400 application peak RSS 101.1107 GiB contrasts with sampled tree 99.2597,
cgroup 99.4901, native observed 68.4298 and Slurm batch 98.2444 GiB. Its telemetry
has 5560 OS rows, 141 events and 126 native observations, zero reported
drops/errors, but a maximum sampling gap of 277.8354 seconds. h300 pair gaps
reach approximately 171/174 seconds. Bounded receipts are intact; continuous
five-second phase peaks and causal instrumentation overhead are not established.
Collection work time is not runtime overhead. Miniature overhead controls do
not quantify production overhead. Do not infer precise CPU efficiency from
configured threads or instantaneous peak memory from sparse sampling.

## Adopted exit criteria and explicit deferrals

| Criterion | Evidence / disposition | S1 exit decision |
| --- | --- | --- |
| Licensed analytical/miniature parity and priority-lock semantics | Corrected job 2143922 accepted, including restricted reuse/rebuild MIPs | Met within miniature scope; not generalized to original LPs or large production models |
| Native ownership and exception/no-incumbent cleanup | Implemented/tested; shared Gurobi environment remains owned separately | Met as lifecycle behavior; allocator return of all bytes to OS is not guaranteed |
| Optional compaction numerical behavior | Six h215 arms plus two h300 pair arms, full hierarchy and original validation | Met as observed preservation; default-off retained |
| Positive control and bounded progression | h215 accepted; h300 input/baseline/pair and h400 input/control accepted | Met for exact admitted profiles only |
| Preparation/allocation/license/transfer integrity | Original identities, finite gates, completion products and review receipts | Met with disclosed pilot transfer incompleteness and retrospective h300 review |
| Memory/time explanation | Distinct units/scopes, unchanged native memory, variable timing effects, sampling gaps disclosed | Bounded observational explanation met; no causal gain, complete phase peak or overhead claim |
| Production explicit reuse/rebuild, scalable fingerprints, generalized copy elimination | Miniature-only evidence is insufficient for these extensions | Explicitly deferred, not delivered or admitted |
| Crossover/basis changes and reduced/higher-memory allocation | No separate supported/certified production contrast | Deferred; not required to close adopted S1 scope |
| Exact-head documentary CI, Ready review and integration | Required on this S1-C PR | Closure pending PR review/merge; no self-certified integration |

This narrows the earlier broad S1 ambition transparently. It does not claim
every original engineering hypothesis succeeded. No fourth h215 pair, repeated
h300 pair, h400 compaction arm, private data publication or rerun is necessary
for this documentary closure.

## Adverse outcomes remain part of the record

- Miniature job 2143416: 128/130 passed, two ObjBound objective-mode failures;
  corrected separately, not relabelled license or memory failure.
- h215 restricted-license job 2151211 and failed pre-submission pair3 bootstrap
  remain diagnostic history; no solve is inferred from absent receipts.
- h300 input job 2198038 failed 1:0; transfer SHA-256
  `538f02f71d9194e22d964a1d18271258488ee20173ee24f1452490147a93eb36`.
  Retry 2198085 is a separate accepted observation, not erasure of that failure.
- h300 baseline 2198528 originally returned evidence_rejected when a post-solve
  enriched model-audit file was compared as an unchanged input hash. A separate
  corrected retrospective review accepted preserved evidence without rerunning
  optimization; original rejection and executed-source identities remain intact.
- MVP1 unsuccessful/time/memory-limited configurations stay in their original
  cohort. No new accepted observation retrospectively changes their outcome.

## Reconciliation with coauthors and next action

The [updated roadmap](mvp2_hpc_roadmap.md) records the agreements supplied on
7 October: strategic agricultural-network/computational focus, homogeneous
comparisons, no Benders implementation in this study, conditional alternative
solvers and conditional frontier expansion. Preserve full systematic review,
coauthor review freeze and human/manual final LaTeX integration at S6. Identify
the email-linked authoritative manuscript then; its URL was not supplied.
EVPI/VSS and section 3.8 exclusion remain S6; no calculations are pending now.

After S1-C integration, prepare a separately qualified S2 thread-screening
protocol before any NPAD action: candidate grid 1/2/4/8/16, common seed 42,
fixed model/method/memory/compaction, selected exact reference and bounded
diagnostic windows, fresh resource/license admission, auditable collection and
no duplicate submissions. The protocol PR must justify the chosen case and
scope; this closure does not authorize a sweep or a new optimization.

This PR changes documentation only. No CLI action is needed for S1-C, no merge
is performed by the assistant, and no manuscript, presentation, runtime,
scientific model, historical receipt, code release or Zenodo deposit is changed.
