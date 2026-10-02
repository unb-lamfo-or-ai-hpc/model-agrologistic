# Solver comparison: exported audit evidence

Six SCIP attempts and three Gurobi all-barrier attempts are included in the supplied archives. This is not the complete historical comparison cohort.

| Backend | Hubs | Direct | Outcome | Optimization (s) | App. peak RSS (GiB) |
| --- | ---: | --- | --- | ---: | ---: |
| SCIP | 215 | False | time_limit_without_incumbent | 28813.50 | 97.12 |
| SCIP | 215 | True | time_limit_without_incumbent | 28820.57 | 94.98 |
| Gurobi | 300 | False | quality_certified | 20382.05 | 59.77 |
| SCIP | 300 | False | mem_limit_without_incumbent | 711.13 | 127.06 |
| SCIP | 300 | False | time_limit_without_incumbent | 28823.09 | 153.98 |
| SCIP | 300 | True | mem_limit_without_incumbent | 660.69 | 128.18 |
| SCIP | 300 | True | time_limit_without_incumbent | 28820.45 | 155.06 |
| Gurobi | 400 | False | valid_incumbent_not_certified | 28826.89 | 111.76 |
| Gurobi | 400 | True | valid_incumbent_not_certified | 28840.96 | 96.23 |

## Interpretation

SCIP has four time-limit and two memory-limit terminations without incumbents. The legacy audit classification independent_validation_not_accepted does not mean that an available candidate violated the model: no candidate was exported. Scenario service extrema of 1.0 in those reports are unsubstantiated defaults and are null in the comparison; original values remain explicitly recorded.

Gurobi has one quality-certified all-barrier case (300 warehouse) and two independently valid but uncertified 400-hub incumbents in this subset. Historical Gurobi 215 and direct-300 accepted cases require their original audits before inclusion in this generated table. Do not interpret omissions as failed solves.

Application RSS, Slurm batch MaxRSS, and terminal SCIP-accounted memory are different measurements. Stage terminal dimensions are not necessarily the dimensions printed immediately after presolve. A null no-incumbent JSON gap is unavailable, consistent with the native log reporting infinite gap; it is not zero or a finite 100-percent gap.

The six included SCIP campaign YAML hashes match their audit declarations. Gurobi campaign YAML, original workbooks, completion manifests and solution files are not supplied in these archives, so paired numerical-input equivalence and full underlying-artifact revalidation are not claimed.
