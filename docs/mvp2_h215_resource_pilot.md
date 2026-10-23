# MVP 2.0: h215 licensed resource pilot

## Scope and evidence

NPAD job 2151415 ran the control and compact arms sequentially, in that order,
from commit `77af8af91fa7f358275afc255c9ab5d9630b4b9a`. The execution directory is
`/home/vrrcelestino/model-agrologistic-hygiene-audit/mvp2-license-clean-sbo7jP9K/execution`.
The earlier restricted-license job 2151211 remains preserved and is not a
resource-frontier observation.

The transferred `pr44-resource-evidence-2151415.tar.gz` has SHA-256
`0c17ac4e147de844be716e4fe89a66299a706462670af38fba3cf7bf01f726c3`.
Inspection found 34 regular files and no duplicate or unsafe member paths.
The archive does not include the license. The solve-plan, campaign and license
capability identities agree with their admission/audit records. All ten recorded
tool hashes agree with the pinned source bytes.

For each arm, the six telemetry payload hashes agree with `resources/manifest.json`.
The completion record also agrees with the seven resources files, independent
validation, solver diagnostics and the two native progress/matrix CSV files:
eleven present completion-bound products per arm. Twenty-two other products
listed across both completion records are not in this deliberately limited
archive. In particular, full result and sparse-flow products are absent.
The inspection therefore verifies this subset, not a new independent validation
of all solution data or a fresh execution of the full campaign auditor.
The preserved auditor accepted 2/2 results, and the transferred independent
validation reports contain zero failed checks.

The license capability probe was accepted (2001 variables and constraints,
optimal objective 2001). The observed runtime was Python 3.13.15, Gurobi 13.0.3
and PySCIPOpt 6.2.1. Allocation was intel-256 node r1i3n5, 196608 MiB, 24
allocated CPUs, four requested CPUs and effective QoS preempt. Solver threads
remained four. Scheduler completion was `COMPLETED`, exit 0:0, elapsed 05:16:03.

## Numerical acceptance is separate from resource benefit

| Measurement | Control | Compact |
| --- | ---: | ---: |
| Optimization seconds | 8867.5448 | 9357.5008 |
| End-to-end seconds | 9219.5733 | 9717.2769 |
| Application-reported peak RSS, GiB | 61.5443 | 60.3258 |
| Sampled process-tree peak RSS, GiB | 61.2642 | 60.0457 |
| Native Gurobi peak memory, decimal GB | 68.390206 | 68.390215 |
| Capacity pass gap, percent | 0.0253285 | 0.0253285 |
| Economic pass gap, percent | 0.00187379 | 0.00187379 |
| Final economic cost | 399443942519.84393 | 399443942519.84393 |
| Final unmet demand | 9.98546056507621e-7 | 9.98546056507621e-7 |
| Hierarchy / preserved independent validation | complete / accepted | complete / accepted |

Application RSS was 1.2185 GiB (1.9799%) lower with compaction; optimization
was 489.9560 seconds (5.5253%) longer. A single fixed-order pair on a shared
node cannot establish that either difference was caused by compaction.
Native memory peaks were essentially unchanged. Accounting scopes differ;
application peak, sampled process-tree RSS, cgroup and scheduler values must
not be forced to agree. Matching aggregates, stage bounds and search counts
support preservation of observed numerical behavior, not identity of all
solution vectors, uniqueness or a universal mathematical equivalence proof.

### Native priority allowance

The capacity pass incumbent was 412263125.6303728 and its bound was
412158705.6528855. The final solution's capacity score was 453385018.2159882:
9.9747% above the pass incumbent and approximately 9.0930% relative difference
from the retained bound, using the final score as denominator. The diagnostics
accept the inherited MIP degradation limit. The configured `MIPGap=0.1` enters
the native multiobjective base allowance; `ObjNRelTol=0` does not remove it.
The 0.0253% pass gap is not the final capacity score's certificate. See the
[Gurobi multiobjective MIP documentation](https://docs.gurobi.com/projects/optimizer/en/current/features/multiobjective.html#multi-objective-mip).
This experiment preserves that contract, rather than introducing strict locks.
Emergency-capacity aggregates are relaxation diagnostics, not installed-capacity
recommendations.

## Telemetry observations and limitations

The compact arm records exactly one `python_index_compaction` event, at elapsed
292.16869 seconds, with 13937940 Python index entries released. Two OS samples
labelled with the compaction phase do not constitute two compaction events.
Compaction follows construction and cannot lower an earlier construction peak.

| Phase: sampled process-tree maximum RSS, GiB | Control | Compact |
| --- | ---: | ---: |
| Construction | 11.6714 | 11.6060 |
| Service optimization | 22.9870 | 21.6900 |
| Capacity optimization | 31.4987 | 29.8596 |
| Economic optimization | 61.2642 | 60.0457 |
| Extraction | 16.4639 | 15.1847 |
| Disposal | 10.7029 | 10.5986 |
| Independent validation | 3.4796 | 3.3763 |
| Export | 3.5541 | 3.4607 |

Economic-phase cgroup peaks were 61.4076 and 60.3007 GiB. The original matrix
had 14054654 columns, 661057 rows and 52068826 nonzeros, plus 74520 general
constraints. The reported presolved matrices agree between arms:

| Pass | Variables | Rows | Nonzeros |
| --- | ---: | ---: | ---: |
| Service | 1247482 | 41604 | 3654531 |
| Capacity | 12026537 | 606538 | 45048213 |
| Economic | 12208341 | 610269 | 46215809 |

There are 1777/1877 OS samples and 45/47 native callback samples. The reports
record no dropped samples or sampling errors. However, the largest observed OS
sample intervals were 154.6790/98.2572 seconds, despite a nominal five-second
interval. Zero drops does not imply continuous or regular coverage; unobserved
transient peaks remain possible. Sampler work totals were 385.1006/391.6384
seconds, not estimates of causal performance overhead.

End-to-end sampled process-tree CPU use averaged 1.8965/1.8781 cores and
4.8582/5.0706 core-hours. These aggregate loading, construction, solving and
export work; they are not solver-only utilization or evidence of four-thread
speedup. Shared-node contention, order effects and sampling coverage remain
limitations.

## Focused continuation of PR #44

1. Keep compaction optional and preserve the nine-scenario h215 contract,
   four threads, seed 42, Method 2 in all three objectives, tolerances, memory
   conditions and fresh-process isolation. No optimizer or preflight-core change
   is needed for the order-aware orchestration extension.
2. Run order/admission regressions on NPAD in the existing venv313. Recheck the
   original input qualification and preflight artifacts; no new input preflight
   is needed if these gates accept unchanged core, tools, runtime and inputs.
3. Submit only pair 2, compact then control, from a new pinned clean checkout
   and execution directory. The existing submitter requests one 192 GiB node,
   four CPUs and 18 hours; it inherits QoS, performs test-only admission, rejects
   duplicates and probes license capability before either large construction.
4. Review pair 2's scientific audit, completion hashes, telemetry and scheduler
   records before requesting pair 3, control then compact. Pair 1 already exists;
   the immediate plan is two additional pairs, not three additional pairs.
5. Compare paired deltas and variability descriptively. Three observations are
   not a balanced or powered causal study. Decide whether another reversed pair
   or improved sampling qualification is necessary before a performance claim.
6. Only then consider separately admitted h300 warehouse-only and h400
   direct-enabled cases. Thread scaling (1/2/4/8/16), memory-cap contrasts and
   production explicit stage rebuilding remain separate future qualifications.

PR #44 remains a draft targeting develop. Neither merge, ready-for-review
promotion, compaction-by-default nor a larger campaign follows automatically
from acceptance of the pilot.
