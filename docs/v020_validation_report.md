# v0.2 mathematical contract and validation results

## Bounded demonstration outcome

The selected NPAD experiment comprises ten reference configurations. Nine were
accepted. The final warehouse-only nine-scenario execution returned a
service-feasible, independently validated incumbent but did not complete the
three-stage objective hierarchy. Development of the bounded MVP is closed with
this computational limitation explicitly retained.

The original four-level certificate remains **rejected**. Levels 1-3 were
accepted; level 4 remains **pending** in the frozen validator's terminology.
Closing development is not equivalent to accepting the original ten-case
certificate. The target relative MIP gap remains 0.01 (1%), not 0.10 (10%).
No model, numerical tolerance or acceptance rule was changed for this closure.

The [immutable NPAD report](evidence/pr25-final/v020_validation_report.json)
and [structured closure observations](evidence/pr25-final/closure.json)
contain the implementation fingerprint and reference identities.
The [evidence guide](evidence/pr25-final/README.md) describes their scope.

## Four validation levels

| Level | Outcome | Evidence and interpretation |
|---|---|---|
| 1: mathematical and data contract | Accepted | Selected network, penalties, activation, conservation and unit contracts match the reference formulation |
| 2: software and licensed analytical tests | Accepted | NPAD Ruff, pytest and build returned zero; no licensed tests were skipped |
| 3: independent solution validation | Accepted | Exported local residuals, costs and usable incumbents passed the independent checker |
| 4: HPC reference demonstration | Pending in the original certificate | Nine references accepted; the warehouse-only nine-scenario hierarchy is incomplete |

The quality receipt's generic sentence about skipped licensed tests is a
conditional qualification, not evidence that any test was skipped:
`skipped_tests` is zero. The successful software suite does not erase a failed
HPC reference. The tested implementation fingerprint is
`c9cfe18e8c1fe19d4e5659139804b4b8dea7b650d4c5e0c3dcb8b5afde4f3042`.

## Reference configurations

| Model family | Scenarios | Direct arcs | Outcome |
|---|---:|---|---|
| Thesis-method, alpha 0.8 | 1 | Disabled | Accepted |
| Thesis-method, alpha 0.8 | 1 | Enabled | Accepted |
| Thesis-method, alpha 0.8 | 3 | Disabled | Accepted |
| Thesis-method, alpha 0.8 | 3 | Enabled | Accepted |
| Policy service-first | 1 | Disabled | Accepted |
| Policy service-first, 14,400 s | 1 | Enabled | Accepted |
| Policy service-first | 3 | Disabled | Accepted |
| Policy service-first | 3 | Enabled | Accepted |
| Policy service-first, 14,400 s | 9 | Enabled | Accepted |
| Policy service-first, dual simplex/four threads | 9 | Disabled | Rejected: incomplete hierarchy |

Policy references use 215 warehouses and the grouped 20% road-arc rule with
declared connectivity handling. Acceptance does not certify all alpha values,
route fractions, warehouse populations or unique investment decisions.
OSRM data preparation at 500 warehouses is not a completed optimization study.

## Final warehouse-only trial

Job 2091731 used the intel-256 partition, four CPUs, 192 GiB of allocated
memory, dual simplex and a 14,400-second optimization budget. Slurm reports
FAILED with exit 1:0 after 04:05:46. Maximum RSS was 28,572,324 KiB
(approximately 27.25 GiB). Its solver-stage export identifies a time limit,
not an out-of-memory termination or an infeasible model.

| Stage | Status | Incumbent | Bound | Relative gap | Optimizer time (s) |
|---|---|---:|---:|---:|---:|
| Expected unmet demand | OPTIMAL | 0 | -2.852e-9 | Not informative at zero objective | 484.263 |
| Expected capacity-violation score | TIME_LIMIT | 159,075,421,601.43033 | 0 | 100% | 13,916.598 |
| Economic cost | Not executed | Not available | Not available | Not available | Not available |

The service target and independent residual/cost checks were accepted. The
capacity score is not a monetary objective or an installed-capacity estimate.
The capacity pass's incumbent and zero lower bound cannot establish quality
within 1%, or even 10%. The unexecuted economic pass has no final economic
optimum or gap. The near-zero service bound and relative-gap sentinel must not
be interpreted as failure of the separately certified domestic-service target.

Earlier warehouse-only trials reached soft-memory limits with economic gaps
near 46.37%. Changing solver method and thread count reduced observed memory
consumption in the last trial, but the hierarchy stopped at an earlier stage.
The combined changes and different progress preclude a causal speedup claim.
All unsuccessful attempts remain part of the development evidence.

## Mathematical and numerical qualifications

- Reception overflow is tonnes within a period, after nominal daily capacity
  is multiplied by operating days. Multiplying the slack by 30 again is wrong.
- Static exceedance is a warehouse-period stock quantity; summing it across
  periods does not yield installed storage capacity. The secondary objective
  is an explicit equal-weight violation score, not a construction target.
- Separate capacity slacks are not equivalent to a shared historical slack:
  under a common rate, fixed exceedances incur a sum rather than their maximum.
- Networks and penalty vectors are frozen across RP, EV, WS and EEV projections.
  Scalar value metrics require compatible objectives and valid bound intervals;
  intervals crossing zero do not establish the sign of stochastic value.
- Independent feasibility checks do not establish nominal physical capacity
  adequacy, unique investment plans, historical numerical replication or a
  complete scalability frontier.
- The historical OSM snapshot and forecasting path were not reconstructed.
  The thesis-method results are qualified reproductions with extensions, not
  exact matches to all published thesis tables.
- v0.1 evidence is retained as historical development evidence. This changed
  v0.2 model has no automatic external TRL accreditation.

## Further research

The warehouse-only nine-scenario limitation motivates scenario decomposition,
controlled solver-method/thread experiments and larger nested candidate
populations. Benders decomposition and native SCIP support require their own
formulation and validation work. A complete 15/20/25% screening campaign and
the practical scalability frontier are not established by the bounded MVP.

The historical [dual retry procedure](pr25_warehouse_dual_retry.md) and its
preceding resource experiments remain reproducibility records, not required
additional runs for this development closure. The earlier detailed
[implementation audit](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/d7081273909cbabc33d1e9c0b819982894420a4e/docs/v020_validation_report.md)
is preserved at its original commit.
