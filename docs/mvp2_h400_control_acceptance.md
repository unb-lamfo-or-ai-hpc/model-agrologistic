# S1-B h400 direct-enabled control: accepted terminal observation

Reviewed 8 October 2026. This report closes the experimental observation admitted
by PR #51; it does not admit a repeat, h400 compaction pair, thread sweep, larger
instance or a changed time/memory envelope. Integration still requires separate
user merge authorization. The frozen MVP1 manuscript and results are unchanged.

## Evidence, identity and scope of review

Job **2200384**, experiment `mvp2_h400_direct_control`, experimental source
`e2fdc6eead8349fb40008be38858fa0160ac74c8`. Preserve the original run
`/home/vrrcelestino/model-agrologistic-hygiene-audit/mvp2-h400-s1b-qn9oDOTR`
and global claim `.mvp2-h400-control-s1b`. Original collection:
`collection-iqwDlynJ`, review `control_review.json`.

Archive `h400-control-evidence-2200384.tar.gz`, SHA-256:

```text
08b60d687227e5e21fe18594ee2bdfe050c57cb5ebf1cc1351ca78632f8b4b3a
```

User checksum, adjacent checksum file and local computed checksum agree.
Original NPAD collection/review and separate local portable replay are accepted.
The [portable review](mvp2_h400_control_review_2200384.json) preserves the exact
source, run identity, stage certificates, resource summaries and qualifications.
All 60 archive members are regular bounded allowlisted files; 123,561,570
expanded bytes. All 58 transfer catalog hashes, 33 closed run products, six
resource payload hashes and 22 tool identities were checked. The nested accepted
input archive retains the original 19-member h400 qualification of job 2200298.

The review replays the ORIGINAL NPAD independent validation and stage
certificates and rechecks original-input/core/runtime/run identities. It does
not reload absent private workbooks, rerun the mathematical validator or claim
independent recomputation of primal residuals. No archive instructions are
executed or arbitrary paths extracted. No license bytes or private workbook
are published. The documentation head must not replace the experimental source
in receipts or imply a rerun at the later documentation commit.

## Unchanged admitted contract and actual allocation

400 hubs (146 existing, 254 candidate), 37 origins, 27 domestic and 10 export
customers, two products, nine scenarios and sixty periods. Direct origin/customer
arcs and warehouse transshipment are enabled. Original connectivity and model
dimensions agree with accepted input job 2200298. Only the isolated derived
execution guard changes from 25,000,000 to exactly 42,426,624 estimated variables.

Gurobi 13.0.3, four solver threads, seed 42, `MIPGap=0.1`, Method 2 for all
three priority passes, `NumericFocus=1`, `SoftMemLimit=128` (solver GB).
Native hierarchy: unmet demand, emergency capacity, economic cost. Objective
relative tolerances remain zero; objective absolute tolerances are 1e-6.
Eight-hour optimization budget, nine-hour child guard, fifteen-minute auditor
guard and twelve-hour Slurm walltime. Compaction remains false; no explicit
production reuse/rebuild or formulation change. A fresh 2,001-variable license
capability probe was accepted before large construction.

Captured allocation: r1i3n4, intel-256, one task, four CPUs per task requested,
24 CPUs allocated, effective QOS preempt, 196,608 MiB requested memory and
finite cgroup limit **206,158,430,208 bytes = 192 GiB**. Solver Threads stayed
four: allocated CPUs are not evidence of a 24-thread solve or node exclusivity.
Worker/control/auditor returned zero with complete closures. Root/batch/extern
accounting is COMPLETED 0:0, elapsed **08:03:44**. The collector's terminal
observation at 2026-10-08T16:39:39Z is a collection time, not the run finish time;
the application records finish at 2026-10-07T22:59:53.638988Z.

## Computational result and hierarchy

| Metric | Observation |
| --- | ---: |
| Data read | 29.05 s |
| Model construction | 733.14 s (12.22 min) |
| Native optimization | 27,925.29 s (7.7570 h) |
| Application end-to-end | 29,003.81 s (8.0566 h) |
| Application-reported peak RSS | 101.1107 GiB |
| Periodically sampled process-tree peak RSS | 99.2597 GiB |
| Periodically sampled cgroup peak | 99.4901 GiB |
| Maximum reported native memory observation | 68.4298 GiB |
| Slurm batch MaxRSS | 103,016,748 KiB (98.2444 GiB) |
| Hierarchy / independent validation / campaign auditor | Complete / accepted / accepted |

The optimization completed within its eight-hour budget; end-to-end and Slurm
elapsed can exceed eight hours because construction, extraction, validation and
audit are separate work. These memory observations have different scope,
cadence and accounting semantics; they are not interchangeable. In particular,
native reported memory is not total application memory, and a 128-GB solver
SoftMemLimit is not a cap on the entire Python process/cgroup. Do not reduce
future resource allocation from this single observation.

| Priority pass | Termination | Pass incumbent | Retained bound | Pass gap | Pass time |
| --- | --- | ---: | ---: | ---: | ---: |
| Unmet demand | OPTIMAL, zero service certified within tolerance | 0 | 5.09317033e-10 | Relative gap unavailable/unstable at zero | 3,012.22 s |
| Emergency capacity | OPTIMAL under configured MIP contract | 253,405,210.0293 | 253,242,390.5111 | 0.0642526% | 13,750.53 s |
| Economic cost | OPTIMAL under configured MIP contract | 355,905,011,542.1016 | 355,891,826,341.4129 | 0.00370470% | 11,131.58 s |

`OPTIMAL` is the solver termination label under configured tolerances; it is
not a claim of zero-gap global optimality. Relative service gap at a zero
incumbent is not a useful metric (exported sentinel 1e100). The final unmet
demand objective is 1.000292286335025e-6, within the inherited service limit
1.0006093170329928e-6 and original-unit validation tolerances. Expected and
minimum-scenario domestic service are effectively 100% within tolerance.

### Capacity quality in the final solution is a different quantity

After the economic pass, emergency-capacity objective is **278,582,911.5140**,
an increase of **9.93575%** over the capacity-pass incumbent. The preserved
capacity bound is 253,242,390.5111. The descriptive relative difference,
using the FINAL objective as denominator, is:

```text
(278582911.5140021 - 253242390.51107278) / 278582911.5140021
= 0.09096222329364104 = 9.09622%
```

This is not the intermediate 0.0642526% pass gap. Nor is it an increase of
9.09622% *over the bound* (that latter expression uses a different denominator).
The native inherited `MIPGap=0.1` priority base can allow final capacity
degradation even with `ObjNRelTol=0`; the original stage certificate reports
`within_mip_degradation_limit=true` for all three passes. No priority rule or
tolerance was tightened or silently changed to achieve acceptance.

## Feasibility, model findings and scientific interpretation

Original independent validation: **2,534,202 checks in 32 families**, zero failed checks,
empty failure samples and finite residuals. Original absolute/relative
tolerances are 1e-5/1e-8, with sparse-export reconstruction budgets. This
certifies the exported incumbent's primal feasibility and cost reconstruction
under those rules, not global optimality or historical replication.

Domestic service is preserved through emergency capacity; the model audit
retains warnings `EMERGENCY_CAPACITY_REQUIRED` and
`DOMINANT_OBJECTIVE_COMPONENT`, and information
`INVESTMENT_CAPACITY_SATURATED`. Expected emergency static/reception aggregates
are 278,576,241.3947 and 6,670.1193; retain their model-defined aggregation,
not an unsupported interpretation as actual installed capacity.

Economic objective is 355,905,011,542.10223; penalized total is
12,892,136,029,672.201, with penalty share **97.23936%**. The Big-M penalty
contribution is penalty-dependent, not an observed financial cost. Near-perfect
service does NOT mean existing/planned physical capacity is sufficient. The
configured investment decision set is saturated while emergency capacity
remains necessary. These findings do not invalidate accepted primal feasibility.

Actual constructed matrix: 42,426,624 variables, 492 binary variables (integer
count includes binaries), 1,160,742 linear constraints, 161,336,486 nonzeros
and 274,320 general constraints. Presolved observations differ by pass and are
retained in the portable review; they are not a second independently built model.

## Telemetry coverage and limitations

Closed resource manifest, 5,560 OS/resource rows and 141 progress/event rows,
including 126 native-memory observations. No reported dropped rows,
inspection errors or control compaction event; sampler solver-API calls are
false. The maximum observed sampling gap is **277.8354 s**, despite the
requested five-second interval. No claim of continuous five-second coverage
or exact phase-boundary peak attribution is justified.

The highest periodically sampled RSS/cgroup usage is in the economic pass.
Capacity-pass peaks are 94.9983/95.2074 GiB; economic-pass peaks are
99.2597/99.4901 GiB. Low counts in extraction/disposal/independent validation
limit phase attribution. Reported sampler work totals 1,258.66 s; this is not
an experimentally measured causal overhead or a value to subtract from runtime.

One run establishes an accepted point of the monolithic computational envelope,
not a universal h400 limit, a causal improvement over historical runs, a
compaction benefit, thread scaling or guaranteed adequacy of memory on another
node/profile. Comparisons across h215/h300/h400 also change network population
and sometimes direct-arc structure; do not label them controlled size effects.

## Disposition and next boundary

The one h400 S1-B control observation is accepted and documented. PR #51 can
become Ready for review after final documentation-head checks; merge remains
subject to separate user authorization. S1-B integration closes with that
merge. Sprint 1 as a whole still needs S1-C evidence/exit reconciliation in a
separate scoped PR. No new NPAD CLI action or optimization is required now.

Then qualify S2 thread screening independently, preserving common data, method,
seed and memory. Larger instances or new solvers remain conditional; Benders
is outside this study's implementation scope, as recorded from the coauthor
meeting. Roadmap reconciliation belongs to S1-C, not a change to this executed
source or to the manuscript. EVPI/VSS/section 3.8 changes remain deferred to S6.
