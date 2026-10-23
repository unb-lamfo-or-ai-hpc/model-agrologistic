# MVP 2.0: accepted third h215 pair and three-pair decision

## Decision and scope

The planned initial h215 sequence is complete: jobs 2151415, 2184508 and
2196511 provide three accepted serial pairs, six accepted arms. Post-build
Python index compaction remains opt-in. There is repeated lower observed
application RSS, but no consistent optimization-time benefit, native-memory
reduction, smaller-allocation admission or causal performance claim.

Close this initial descriptive h215 gate without automatically launching a
fourth pair. Retain all positive and negative observations. Three pairs are
unbalanced (control first twice, compact first once), nonrandomized, fixed-seed
and executed on shared nodes. Further repetitions require a distinct question
and design; they are not required merely to obtain a favorable speed result.

This closes the initial h215 observation gate, not all of Sprint 1 or MVP 2.0.
Scale admission at h300/h400 and the later independent thread-scaling,
SCIP and rebuilding work remain open. PR #44 stays draft until the user
authorizes promotion; merge also requires explicit user confirmation.

## Third-pair provenance and scientific acceptance

Job 2196511 and its batch/extern steps completed with exit 0:0, elapsed
05:37:48, on intel-256 node r1i3n4. Batch MaxRSS was 64322064K, a scheduler
measurement distinct from application and sampled process-tree RSS.
The order was control then compact, canonical indices [0, 1]. Both arm
processes and the campaign auditor returned zero. The preserved auditor
accepted 2/2; each independent report is accepted with zero failures,
1,894,179 checks in 32 families. The mathematical validator was not rerun
during this archive review.

The experimental commit remains
`5bfaa7a58fab5e714a8fd427fdd79a72976dd0a7`.
Archive: `pr44-pair3-evidence-2196511-20261005T202357Z-1b7a8351.tar.gz`.
Verified SHA-256:
`6622e831122d2024dee4f5e20951100ef98f78937b766d2294c23908b97d6929`.
All 69 regular members have safe unique paths; no license payload is present.
All 67 transfer-catalogue hashes match. Per arm, six telemetry payload hashes
and 25 present completion-bound products were checked locally. Eight of the
33 completion products are absent from this transfer, including standalone
flow/inventory CSVs. The NPAD collection receipt separately reports rehashing
33/33 there. These scopes must not be conflated with fresh full validation.

Both result.json files are available. Canonical fingerprints of their exported
solution fields agree within pair 3 and across all four arms of pairs 2 and 3:
198,915 flows, 87,530 inventories, 30,230 emergency-capacity entries, 215
warehouse decisions, unmet demand, cost/metric and first/second-stage fields.
Pair 1's transferred archive has no full result.json, so full-vector parity
across all six arms is not claimed. Across all six, recorded stage objectives,
bounds, final scores, gaps, iteration/node counts, solution counts and work
units match, as do presolved matrix CSV hashes. This is observed numerical
parity, not uniqueness, universal equivalence or a coefficient fingerprint.

All three campaigns match after removing only top-level output_dir. Ten tool
hashes per pair match their pinned Git blobs. Original reviewed preflight
identity, runtime and numerical implementation are unchanged: Python 3.13.15,
Gurobi 13.0.3, PySCIPOpt 6.2.1 and core identity
`b4de41ade0b3c55f8f20a66480cffa275421f8157444b1db3000a9eb50f2d351`.

## Three matched observations

RSS is the application's reported peak, converted from MiB to GiB. Deltas
mean compact minus control; percentages divide by control. Lower RSS is a
descriptive observation, not the amount by which a future allocation can fall.

| Pair / job | Order | Node | Control optimization (s) | Compact optimization (s) | Time delta | Control RSS (GiB) | Compact RSS (GiB) | RSS delta |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 / 2151415 | control, compact | r1i3n5 | 8867.5448 | 9357.5008 | +5.5253% | 61.5443 | 60.3258 | -1.9799% |
| 2 / 2184508 | compact, control | r1i3n4 | 9758.8912 | 9730.2901 | -0.2931% | 61.6490 | 60.4392 | -1.9624% |
| 3 / 2196511 | control, compact | r1i3n4 | 9833.2961 | 9697.9314 | -1.3766% | 61.5416 | 60.5480 | -1.6147% |

RSS differences are -1.2185, -1.2098 and -0.9937 GiB. Optimization differences
are +489.9560, -28.6011 and -135.3647 seconds. Do not average these three
contrasts into an estimated causal effect or declare significance from them.
Pair 3 end-to-end times were 10195.8438/10050.9640 seconds (control/compact).
Native peaks were 68.390213/68.390207 decimal GB; native memory was essentially
unchanged across the entire sequence. No memory-limit termination was reported.

## Unchanged hierarchy and substantive solution

All arms completed the three priorities under the existing native Gurobi
MIPGap 0.1 degradation semantics, without strict locks or a changed formulation.
Effective parameters remain four threads, seed 42, Method 2 in all objectives,
NumericFocus 1 and SoftMemLimit 128 decimal GB. The instance remains h215,
nine scenarios, 60 periods and no direct origin-customer arcs; per-arm declared
budget remains 28,800 seconds, scheduler request 192 GiB and 18 hours.

Service is zero within 1e-6 absolute tolerance (reported unmet demand
9.98546056507621e-7). The 1e100 relative-gap sentinel is not a useful service
gap. The capacity pass gap is 0.0253285%, and economic pass gap 0.00187379%.
Capacity rises from pass incumbent 412,263,125.6303728 to final score
453,385,018.2159882 (+9.9747%); relative difference to the retained capacity
bound is about 9.0930%, with final-score denominator. The small intermediate
gap is not a final capacity certificate. ObjNRelTol=0 does not suppress the
inherited native MIPGap degradation allowance.

Pair 3's economic cost is 399,443,942,519.84393 and the reported penalized cost
is 20,801,769,762,239.293; do not substitute one for the other or infer cost
units not specified in the data. Emergency static capacity is
382,850,606.6441069 and reception capacity 70,534,411.57187805, in the model's
declared units. Emergency capacity remains required: near-complete service
does not mean the original infrastructure alone is adequate. Material balance
passed; direct flow is zero as required by this instance.

## Telemetry limitations

Pair 3 records exactly one compaction event at 291.71368 seconds, releasing
13,937,940 Python index entries after construction. Control has no such event.
Sampled construction peaks were 11.6823/11.6893 GiB; compaction cannot reduce
an earlier construction peak. The sampled peak occurs in economic optimization:
61.3022/60.3101 GiB, versus application peaks 61.5416/60.5480 GiB.

OS samples: 1970/1944. Native callback samples: 48/48. No drops or inspection
errors were reported, but maximum OS intervals are 106.2863/100.4149 seconds,
with ten intervals over ten seconds per arm despite nominal five-second
sampling. Transient peaks can be missed. Sampling work 396.2171/393.0984
seconds is not a causal overhead estimate. End-to-end CPU averages
1.8811/1.8824 cores and 5.3286/5.2568 core-hours are not solver-only utilization
or evidence for four-thread scaling.

Allocation records 196608 MiB, 24 allocated CPUs, four requested CPUs per task,
24 affinity-visible logical CPUs and effective QoS preempt. Keep requested,
allocated, affinity and actual parallel work separate. Application RSS, native
GB, sampled process tree, cgroup and scheduler MaxRSS have distinct scopes.

## Checkout incident and recovery

The first pair-3 bootstrap stopped before tests/preparation/submission. A fresh
checkout appeared dirty for two historical manuscript files because
manuscript/.gitattributes forces '* text eol=lf' with only PNG marked binary.
The defect was reproduced locally. It is not a solver or scientific failure.
The original failed directory and claim were preserved.

Recovery used a fresh isolated clone with two local-only '-text' exceptions in
.git/info/attributes, installed before checkout. Every one of the 367 tracked
files was checked byte-for-byte against its HEAD blob; the index/worktree
remained clean. No archived manuscript, tracked attributes, model, dependency,
source commit or experimental tool was changed. All 154 focused NPAD tests
passed without skips, and license/contract admission succeeded. Six local
recovery regressions passed. No reset, skip-worktree or assume-unchanged was
used. A Slurm test-only identifier is not the submitted job 2196511.

## Gated next development step

1. Preserve the three accepted jobs and their evidence; keep compaction opt-in.
2. Finish review of PR #44 against exact-head CI; request explicit approval
   before ready-for-review promotion or merge into develop. Do not auto-merge.
3. Prepare a separate h300 warehouse-only input-preflight/admission extension
   with regressions for population, immutable evidence and resource profiles.
   The existing production preflight/admitter is restricted to h215: changing
   a command-line case or reusing the h215 receipt cannot admit h300.
4. Request only the new input preflight on NPAD after that extension is tested;
   review population/input hashes and prospective matrix size before any solve.
   Admit a single h300 baseline observation separately, not a queued h300/h400
   campaign. Keep the four-thread profile and hierarchy unchanged at first.
5. Consider h400 direct-enabled only after h300 evidence. Treat thread scaling,
   lower-memory profiles, telemetry redesign and cold rebuilding as separate
   qualified contrasts; do not mix them into the scale observation.

No fourth pair, larger job, ready-review transition or merge follows from this
report. Frozen MVP 1.0, manuscript/dataset, dependencies and Pages remain
unchanged. The assistant reviewed evidence; the user executed NPAD commands.
