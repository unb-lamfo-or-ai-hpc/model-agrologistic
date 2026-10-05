# MVP 2.0: second h215 resource pair

## Scientific acceptance and provenance

NPAD job 2184508 completed in 05:37:09 with exit 0:0. The batch step also
completed, reporting MaxRSS 64433916K (61.4490 GiB under Slurm's KiB convention).
Both arms returned zero and the preserved campaign auditor accepted 2/2.
Each preserved independent report contains 1,894,179 checks across 32 families,
zero failures and status accepted. These reports were inspected, not recomputed
from a newly loaded workbook.

The order was compact then control, canonical indices [1, 0], on intel-256
node r1i3n4, using commit `5bfaa7a58fab5e714a8fd427fdd79a72976dd0a7`.
The reviewed archive is
`pr44-pair2-evidence-2184508-20261005T103800Z-84e67e7a.tar.gz`, SHA-256
`6224ac47ba4fd04bcdb75f76ce4014c734d2fde5bb173e903a1c28f786bbe07c`.

The archive contains 69 safe regular members without duplicate paths or license
payloads. All 67 transfer-catalogue payload hashes were independently rechecked.
For each arm, six telemetry payloads and 25 available completion-bound products
match their manifests. Eight completion-listed products per arm remain absent
from this transfer, including standalone flows/inventories CSVs. The NPAD
transfer receipt reports rechecking all 33 completion products per arm locally;
this is distinct from the 25 products rechecked here. No new full mathematical
validation is claimed from this archive inspection.

Both result.json files are present and contain exported sparse solution fields.
Canonical JSON fingerprints match between the two arms for 198,915 flow entries,
87,530 inventory entries, 30,230 emergency-capacity entries, 215 warehouse
decision entries, one unmet-demand entry, cost breakdown, metrics and exported
first/second-stage decision collections. This strengthens observed exported
solution parity for this pair only. It proves neither solution uniqueness nor
universal formulation equivalence, and is not a coefficient fingerprint.

The campaign matches pair 1 byte-for-byte after excluding only its top-level
output_dir. All ten tool hashes for each pair match their corresponding pinned
Git source bytes. Runtime and qualified implementation identity are unchanged:
Python 3.13.15, Gurobi 13.0.3, PySCIPOpt 6.2.1 and core identity
`b4de41ade0b3c55f8f20a66480cffa275421f8157444b1db3000a9eb50f2d351`.

## Matched observations

Within-pair deltas below mean compact minus control, divided by control for
percentages. RSS is the application's reported peak, converted from MiB to GiB.

| Metric | Pair 1 control | Pair 1 compact | Pair 2 control | Pair 2 compact |
| --- | ---: | ---: | ---: | ---: |
| Optimization, seconds | 8867.5448 | 9357.5008 | 9758.8912 | 9730.2901 |
| End-to-end, seconds | 9219.5733 | 9717.2769 | 10115.3809 | 10091.8732 |
| Application peak RSS, GiB | 61.5443 | 60.3258 | 61.6490 | 60.4392 |
| Sampled process-tree peak RSS, GiB | 61.2642 | 60.0457 | 61.3689 | 60.3553 |
| Native Gurobi peak, decimal GB | 68.390206 | 68.390215 | 68.390175 | 68.390203 |

| Within-pair contrast | Pair 1, control first | Pair 2, compact first |
| --- | ---: | ---: |
| Application RSS difference, GiB | -1.2185 | -1.2098 |
| Application RSS difference, percent | -1.9799 | -1.9624 |
| Optimization difference, seconds | +489.9560 | -28.6011 |
| Optimization difference, percent | +5.5253 | -0.2931 |

The RSS reduction is repeated descriptively under opposite orders. Optimization
time does not show a consistent benefit. Pair 2's control and compact times
were respectively 10.052% and 3.984% above pair 1; changing order and shared
node r1i3n5 to r1i3n4 also changes execution conditions. Two nonrandomized,
shared-node serial pairs do not identify a causal memory or speed effect.
Native memory is essentially unchanged. No lower allocation is admitted.

All four observations have matching recorded stage objectives, bounds, gaps,
iteration/node counts, solution counts and work units. Presolved matrix CSV
hashes also match across all four. The original matrix still has 14,054,654
columns, 661,057 rows and 52,068,826 nonzeros, plus 74,520 general constraints.
This is observed parity, not a proof that arbitrary instances are equivalent.

Capacity pass gap remains 0.0253285%, and economic pass gap 0.00187379%.
The final capacity score remains 453,385,018.2159882 versus the second-pass
incumbent 412,263,125.6303728, a 9.9747% increase. The final score's relative
difference to the retained bound is approximately 9.0930% using final-score
denominator. Preserve inherited MIPGap 0.1 degradation semantics; do not
mislabel the intermediate 0.0253% as the final capacity certificate.
Near-zero service is certified with absolute tolerance, not its 1e100 relative
gap sentinel. See the [native MIP priority documentation](https://docs.gurobi.com/projects/optimizer/en/current/features/multiobjective.html#multi-objective-mip).

## Telemetry and allocation boundaries

Pair 2 recorded one compaction event at elapsed 299.20026 seconds, releasing
13,937,940 Python index entries. Phase-boundary records are not extra events.
Economic optimization remains the sampled RSS peak phase. Construction sampled
peaks were 11.7127/11.6822 GiB, and compaction still occurs after construction.

There are 1956/1952 OS samples and 48/48 native callback samples, control/compact.
No drops or inspection errors were reported. Maximum OS intervals were
99.2603/100.7116 seconds despite the nominal five-second interval; ten/eight
intervals exceed ten seconds. Transient peaks may remain unobserved.
Sampler work is 375.6967/391.5685 seconds, not causal overhead. End-to-end CPU
averages are 1.8797/1.8840 cores and 5.2827/5.2825 core-hours; these are not
solver-only utilization or a four-thread scaling result.

The scheduler records 196608 MiB, 24 allocated CPUs, four CPUs per task and
effective QoS preempt. CPU affinity exposes 24 logical CPUs. Effective stage
parameters report Threads 4, Method 2, NumericFocus 1, SoftMemLimit 128 decimal
GB and MIPGap 0.1. Do not equate requested CPUs, allocated CPUs, affinity and
effective parallel speedup. Application RSS, sampled process tree, cgroup,
native memory and Slurm batch MaxRSS have different measurement scopes.

## Reviewed continuation

1. Count jobs 2151415 and 2184508 as accepted pairs 1 and 2.
2. Next submit only pair 3, control then compact, in a new immutable execution.
   Keep the already qualified experimental source at commit 5bfaa7a; subsequent
   evidence-only documentation commits do not require changing that source.
3. Recheck the original preflight identity, inputs, runtime, source and focused
   154-test gate on NPAD. Reject any changed or incomplete prerequisite.
4. Preserve seed 42, four solver threads, stage parameters, hierarchy semantics,
   memory profile, input population and fresh-process isolation. Do not add
   strict locks, thread scaling, lower-memory allocations or larger instances.
5. Collect terminal scheduler state and complete scientific/resource evidence
   immediately after pair 3, including on failure, without resubmitting it.
6. Review all three paired deltas before deciding whether a fourth reversed pair
   or better sampling qualification is needed. Three pairs are still unbalanced
   and not a powered causal experiment. No pair 4 is automatically authorized.

Compaction remains opt-in. PR #44 remains draft and no merge or larger campaign
follows automatically. Frozen MVP 1.0, manuscript, dataset and dependencies are
unchanged. The assistant did not submit an NPAD job.
