# Four h300 pilots collected; public v3 qualification pending — 2 November 2026

Original HiGHS2231591 returned a regular native time-limit result with no usable
incumbent. Preserve original_validation_status=rejected and
incumbent_validation_rejected=false: usability/primal acceptance and operational
closure are different questions. Objective, financial subtotal and MIP gaps
remain null. A missing incumbent is not infeasibility or an invalid incumbent.
Original archive SHA8cf39b68 is human reported; the new t16 packages have not
been independently inspected locally. No investment map/vector is fabricated.

| Solver/threads/r1 | Native min | Application min | Common gap,% | Sampled peak GiB | Outcome |
| --- | ---: | ---: | ---: | ---: | --- |
| Gurobi1 | 48.229 | 91.794 | 0.00410523 | 74.535 | Original validation accepted |
| Gurobi16 | 71.898 | 115.084 | 0.00412035 | 103.359 | Original validation accepted; reported package |
| HiGHS1 | 401.435 | 443.350 | 0.00687938 | 84.820 | Original validation accepted |
| HiGHS16 | 480.630 | 512.671 | — | 90.260 | Time censored; no usable incumbent |

These are four observations, not three completed repeats per setting. The
reported HiGHS16 native runtime28837.772685s exceeds its configured28800s by
37.772685s; report actual runtime rather than replacing it by the setting.
The Slurm root30929s also includes workflow overhead. Its zero processed-node
counter and3039412 LP iterations are diagnostics, not proof of which internal
algorithmic phase caused the outcome. Native log inspection remains separate.
Do not compute completed-work speedup from this censored observation, conclude
open-source impossibility, select a thread winner, or infer identical solutions
from nearly equal Gurobi objectives. Equal seed values do not equalize internals.

Frozen workbook/selection/scenarios, ordered algebra, derived bounds and hardware
class agree across the reported records. Pure local replay of the unchanged
c493be8c metadata gate accepts all four operationally closed pilots, including
regular censoring; maximum sampled peak103.359GiB is below the153.6GiB headroom
threshold. This is not a local audit of the new archives, live cluster admission
or permission to start a cell. After accepted software qualification and merge,
the actual first control must reread original archives/receipts and evaluate the
same gate. No rule was changed to accommodate a missed quality target. Neither
HiGHS arms nor planned repetitions are removed; consumed R1 is never retried.

Partial configuration/result CSVs preserve all four states and native parameters.
Nulls stay blank in CSV with explicit classification. The first one-thread
packages were inspected; t16 rows are explicitly marked reported_collector_only.
The article's currently audited tables are not silently expanded by this record.

Public v3 was submitted as2231948/source334827d5, plan8e4947a8, with no new probe
submission/release. The last supplied accounting was RUNNING104s,64allocated
logical CPUs/16worker CPUs. License/allocation files exist; final result/XML
were still absent, which is expected before completion. Acceptance requires
248 tests without failures/errors/skips and source/runtime/original closure.
No merge, private queue release, new scientific start, deposit or PDF occurred.
