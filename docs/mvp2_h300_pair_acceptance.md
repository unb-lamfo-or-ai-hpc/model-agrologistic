# S1-A h300 descriptive transfer: terminal acceptance

Reviewed 7 October 2026. Experimental source:
`0e663c8bd8d9c5c4b27dbb09db3f1375ad52257d` (PR #49).
Subsequent documentation commits are not the experimental source.

## Disposition and reproducible review

Job **2199525** is accepted as one descriptive, compact-first h300
warehouse-only pair. Both fresh processes completed the three priorities,
original independent validation and joint quality audit. S1-A is experimentally
complete; this does not close all of Sprint 1. Compaction remains optional.
No repetition, smaller allocation or next optimization is admitted by collection.

Archive: `h300-pair-evidence-2199525.tar.gz`; SHA-256:
`5e52e56887dcb57b9c6209fb884129bf85cc322779fc17c2279c589519d4c1d9`.
The supplied adjacent checksum and transferred bytes agree. The original run is
`/home/vrrcelestino/model-agrologistic-hygiene-audit/mvp2-h300-s1a-4gaHSdn2`;
preserve it and its durable claim. Original collection and portable review report
`accepted`. A separate local replay using the unchanged collector also reports
`accepted`:

```bash
python scripts/collect_mvp2_h300_pair.py \
  --archive h300-pair-evidence-2199525.tar.gz \
  --sha256 5e52e56887dcb57b9c6209fb884129bf85cc322779fc17c2279c589519d4c1d9 \
  --review-output NEW_h300_pair_review_2199525.json
```

Use the original experimental checkout and a new output path. This command reads
the bounded archive without extraction, private workbook access or optimization.
It verifies the two original NPAD independent-validation certificates; it does
not independently recompute residuals locally. There are 120 regular members:
118 catalog-hashed payloads plus collection and accounting records. Transfer,
completion and telemetry hashes, original input evidence, source/runtime/tool
identities, semantic audits, license/allocation gates and hierarchy certificates
pass the unchanged portable reviewer. No workbook or license contents are published.

## Execution and qualification

- Fixed case: 300 hubs, nine scenarios, sixty periods, no direct origin/customer
  arcs; canonical control index 0 and compact index 1, execution order **[1, 0]**.
- Original input job 2198085 and its exact size exception remain bound. Actual
  matrix: **25,107,544 variables**, 890,642 linear constraints, 94,635,126 nonzeros,
  166,320 general constraints and 392 integer variables, including binaries.
- Gurobi 13.0.3, native three-priority hierarchy, Method 2, four solver threads,
  seed 42, inherited MIPGap 0.1; unchanged core and formulation. Fresh licensed
  capability probe accepted before either arm.
- Slurm: `intel-256`, node `r1i3n3`, one task, four requested CPUs per task;
  scheduler allocated 24 logical CPUs. Affinity also spans 24 logical CPUs. These
  are not 24 solver threads or evidence of thread scalability or node exclusivity.
- Observed finite cgroup-v1 limit: **206,158,430,208 bytes (192 GiB)**. The memory
  gate is based on the actual cap, not the partition name. QoS: `preempt`.
- Root and batch: `COMPLETED`, `0:0`, elapsed **11:42:23**. Both arm return codes,
  worker completion and joint auditor return code are zero; acceptance also
  requires the numerical and integrity gates, not just those return codes.
- NPAD focused regression before submission: **363 passed**, zero failures,
  errors or skips, 98.67 seconds. Local Windows qualification before execution:
  324 Python cases passed and 39 Bash-dependent cases explicitly deselected;
  Ruff and sdist/wheel build passed. Linux CI covered the shell cases separately.

## Descriptive resource comparison

Control executes second; compact executes first. Percent change is
`100 * (compact / control - 1)`. Times below use 3,600 seconds per hour.

| Indicator | Control | Compact | Compact vs control |
| --- | ---: | ---: | ---: |
| Optimization seconds | 20,584.8192 | 20,245.6816 | -1.65% |
| Optimization hours | 5.7180 | 5.6238 | -1.65% |
| End-to-end seconds | 21,241.0232 | 20,875.5904 | -1.72% |
| End-to-end hours | 5.9003 | 5.7988 | -1.72% |
| Model-build seconds | 445.6495 | 428.6067 | -3.82% |
| Application high-water RSS, GiB | 59.8286 | 57.9129 | -3.20% |
| Sampled process-tree RSS peak, GiB | 58.1810 | 56.3741 | -3.11% |
| Sampled cgroup charged-memory peak, GiB | 58.4463 | 56.5030 | -3.32% |
| Observed native solver-memory peak, GiB | 39.926549 | 39.926557 | Essentially unchanged |

Application RSS reduction is **1.9157 GiB**. The project summary field
`peak_rss_mb` is expressed in MiB; divide by 1,024 for GiB. Native, cgroup,
sampled tree RSS and application high-water RSS are different measurements.
Slurm batch MaxRSS is **61,339,300 KiB (~58.50 GiB)** for the whole batch;
it must not be assigned to either arm or substituted for application RSS.

Exactly one compact-arm event releases **24,944,760 Python-index entries**;
the control has no such event. The recorded phase-start/event timestamps span
about 2.846 seconds. This is not a causal measurement of reclaimed memory or
total performance overhead. Essentially identical native peaks are consistent
with Python-side representation compaction, not native solver-matrix compression.
That explanation is an inference, not a separately controlled allocation study.

### Phase coverage and CPU interpretation

| Sampled process-tree phase peak, GiB | Control | Compact |
| --- | ---: | ---: |
| Model build | 20.2999 | 20.2452 |
| Service stage | 41.2457 | 39.2871 |
| Capacity stage | 57.0914 | 55.1157 |
| Economic stage | 58.1810 | 56.3741 |
| Result extraction | 27.4884 | 25.9635 |
| Native-model disposal | 17.6274 | 17.7907 |
| Independent validation | 4.3863 | 4.1027 |

Control/compact telemetry has 4,104/4,038 resource samples and 71/74 progress
events, zero reported dropped samples or inspection errors, and clean sampler
termination. Median resource intervals are approximately 5.05 seconds, but
maximum gaps are **171.49/173.78 seconds**, with **17/15 intervals over ten
seconds**. Zero reported drops does not imply continuous coverage. Short-lived
peaks, including build and disposal transitions, may be missed; native-memory
observations are callback-limited rather than continuously measured.

Reported sampler inspection work / elapsed observation time is **3.57%/3.51%**;
this is an accounting ratio, not measured causal overhead. Observed process-tree
CPU-seconds / elapsed time is approximately **1.605/1.601 effective cores** over
the observation, not solver-thread utilization or a scaling result. Maximum
observed root-process native thread counts are 7/8, which can include helpers;
the solver parameter remains four threads.

## Numerical acceptance and hierarchy interpretation

Both original validators accept **32 constraint families and 2,362,490 checks
per arm**, with zero failures. All three stage certificates coincide except for
their recorded runtimes: objectives, retained bounds, iteration/node counts and
solver work units match. Seventeen corresponding CSV exports are byte-identical,
including flows, inventories, decisions, unmet demand, capacity, scenario
diagnostics, presolved matrices and interhub exports. Observed numerical behavior
and exported solutions are preserved in this pair, not universally proved.

| Priority | Control / compact runtime, seconds | Shared certificate |
| --- | ---: | --- |
| Service | 1,166.5094 / 1,165.4761 | Final unmet demand 9.98546e-7; within absolute tolerance 1e-6 |
| Capacity | 11,774.1668 / 11,582.2809 | Pass objective 328,334,362.5005; bound 327,520,771.9455; pass gap 0.247793% |
| Economic | 7,626.3169 / 7,479.8147 | Final cost 396,098,981,252.4231; bound 395,769,768,427.9276; pass gap 0.083114% |

The final emergency-capacity objective is approximately **360,354,208.1956** in
both arms, **9.7522% above** its intermediate capacity-pass objective. Its
relative difference from the retained bound, using
`(final_capacity - retained_bound) / abs(final_capacity)`, is **9.1114%**, not
0.247793%. The unchanged inherited MIPGap 0.1 degradation envelope permits this
result even with zero explicit relative objective tolerance; the archived
hierarchy certificate accepts its inherited limit. Do not claim exact global
lexicographic optimality or interpret the intermediate gap as final-capacity
quality. Near-zero service objectives require the absolute certificate, not an
ill-conditioned relative gap. Small reconstruction-rounding differences between
summary and stage final values are not arm differences.

Both semantic model audits retain `EMERGENCY_CAPACITY_REQUIRED` for all nine
scenarios and informational `INVESTMENT_CAPACITY_SATURATED` for candidate
capacity. All 154 eligible candidates are at their upper capacity bounds.
Mathematical validation does not establish capacity adequacy without emergency
variables. The weighted emergency-capacity objective is not installed physical
capacity; penalty-inclusive cost is not an observed expenditure estimate.

## Scientific conclusion and next boundary

The descriptive h300 screen reproduces lower application RSS with optional
compaction and unchanged numerical outputs. This pair also has lower runtime;
the earlier h215 pairs did not show a consistent runtime gain. One fixed-order
pair on a shared cluster cannot isolate treatment, order, contention or run-to-run
variation. Do not claim significance, causal speedup, native-memory compression,
safe allocation reduction or performance dominance. The historical h300 job
2198528 is context, not an extra matched replicate.

Close **S1-A** with compaction **opt-in**, the original resource/numerical contract
unchanged and no automatic repeat. Next **S1-B** separately qualifies h400 with
direct arcs: input-only size/connectivity/source checks first; then review the
evidence and define allocation/license/time admission before any single
instrumented control optimization. Existing h300 or h215 receipts cannot admit
h400. **S1-C** reconciles evidence and Sprint 1 exit items afterward. Thread
screening belongs to S2; production explicit lifecycle, reduced memory and
frontier expansion remain separately conditional. No manuscript or MVP1 change
is part of this acceptance, and no new NPAD CLI action is required for PR #49
closure. Merge into develop requires the user's separate authorization after
passing final checks and Ready status.
