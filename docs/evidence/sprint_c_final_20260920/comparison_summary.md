# Nine-scenario solver comparison

## Research question and scope

Which tested warehouse populations produce an independently valid incumbent and complete the service/capacity/economic hierarchy at a 10% per-stage gap target within a nominal 28800-second optimization budget?

The supplied campaign cohort contains 13 attempts: seven Gurobi and six SCIP/SoPlex attempts. Earlier failed configurations are retained alongside subsequent repeats. Preflight-only cases and launcher failures are not solver attempts.

| Solver / method | Hubs | Direct | Outcome | Capacity gap (%) | Economic gap (%) | Optimization (s) | RSS (GiB) |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| Gurobi historical automatic | 215 | False | quality_certified | 0.025484 | 0.016569 | 12324.93 | 47.67 |
| SCIP/SoPlex sequential | 215 | False | time_limit_without_incumbent | — | — | 28813.50 | 97.12 |
| Gurobi historical automatic | 215 | True | quality_certified | 0.869098 | 0.013726 | 9655.85 | 45.29 |
| SCIP/SoPlex sequential | 215 | True | time_limit_without_incumbent | — | — | 28820.57 | 94.98 |
| Gurobi historical automatic | 300 | False | valid_incumbent_not_certified | 0.175520 | 50.520259 | 28833.37 | 80.22 |
| Gurobi all-barrier | 300 | False | quality_certified | 0.247793 | 0.083114 | 20382.05 | 59.77 |
| SCIP/SoPlex sequential | 300 | False | mem_limit_without_incumbent | — | — | 711.13 | 127.06 |
| SCIP/SoPlex sequential | 300 | False | time_limit_without_incumbent | — | — | 28823.09 | 153.98 |
| Gurobi historical automatic | 300 | True | quality_certified | 1.287429 | 0.067684 | 26409.00 | 80.99 |
| SCIP/SoPlex sequential | 300 | True | mem_limit_without_incumbent | — | — | 660.69 | 128.18 |
| SCIP/SoPlex sequential | 300 | True | time_limit_without_incumbent | — | — | 28820.45 | 155.06 |
| Gurobi all-barrier | 400 | False | valid_incumbent_not_certified | 100.000000 | — | 28826.89 | 111.76 |
| Gurobi all-barrier | 400 | True | valid_incumbent_not_certified | 0.064253 | 99.999813 | 28840.96 | 96.23 |

## Findings

Four Gurobi attempts are quality-certified (4 total). The two 215-hub cases, historical direct-300 case, and all-barrier warehouse-300 case meet the declared 10% criterion. Historical warehouse-300 retains a 50.520259% economic gap; its all-barrier repeat is a separate accepted attempt. Both all-barrier 400-hub runs retain independently valid incumbents but fail the quality criterion. The warehouse case stops in capacity; the direct case stops in economics. Both are time-limited, not the earlier mixed-method memory-limited runs.

All six SCIP attempts lack an incumbent: two original 300-hub memory stops and four time-limit outcomes at 215/300 hubs. Increasing the internal memory budget from 131072 to 393216 MB removed the observed early memory stop, but did not produce a solution within the budget. Memory and hardware changed together. No cost, achieved service or finite gap is imputed. Original 1.0 scenario-service defaults are retained as suppressed raw fields, not performance evidence.

The largest tested quality-certified Gurobi population is 300; valid incumbents exist at 400. SCIP has no demonstrated incumbent among tested 215/300 cases. This does not identify a smaller SCIP frontier, prove infeasibility, or establish a universal maximum. No 400-hub SCIP solve or 500-hub solve is claimed.

## Evidence reconciliation

All 11 audit-declared campaign hashes were verified. All 81 supplied completion-bound artifact hashes match. All 8 cross-solver pairings match reported workbook hashes, explicit model/loader settings, scenario aggregate signatures, input parameter summaries, size/route counts and interhub audit contents. Historical audits are now included.

Reported workbook hashes and exported input summaries reconciled; raw workbook bytes, full coefficient matrices and full solutions not revalidated. Missing source declarations are preserved; implementation equivalence is not inferred.

Pair matching is scoped to exported records: aggregates are not full coefficient hashes. Runtime versions differ; source_commit_declared is absent in these preflights. Opaque run identities differ legitimately with backend/configuration. A full algebraic equivalence proof or replay is not claimed. All exported failures remain visible.

## Interpretation and limitations

The common nominal gap is not an identical realized priority relaxation: inherited capacity limits depend on each pass's bound and incumbent. Report pass and final objective values separately. Service at zero uses the absolute certificate, not the relative-gap sentinel. Feasibility with emergency variables does not certify installed capacity. Stock exceedance aggregated across periods is not an investment recommendation; reception overflow is already a period quantity and must not be multiplied by 30 again.

Application optimization time, native solver runtime, scheduler elapsed, application RSS and Slurm MaxRSS have different scopes. Configured threads are not allocated CPU counts. These are single attempts, not replicated statistical estimates. No economic ratio, speedup or hardware-neutral ranking can be inferred without SCIP incumbents.

## Closure and next phase

Sprint C is complete as a descriptive, provenance-qualified comparison of this frozen cohort. It does not certify absent data or a universal frontier. Sprint D updates the English documentation; Sprint E integrates evidence into the manuscript and collaborator package. Larger networks, alternative LP strategies and decomposition remain future experiments. No new optimization is required for this reporting closure.

## Runtime and memory

![Runtime and memory by attempt](runtime_memory_comparison.png)
