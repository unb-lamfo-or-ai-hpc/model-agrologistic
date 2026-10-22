# Scalar results, agricultural outputs and supplementary evidence

## Existing evidence and what can be stated now

| Cohort / source | Existing evidence | Allowed use / missing dependency |
| --- | --- | --- |
| R1 software | Analytical DET/single-scenario STO, probability splitting, units, costs, Gurobi/SCIP tests; see scalar R1 qualification | Mathematical/software evidence on small cases; not large-instance resource performance |
| R2 job2217613 | Accepted small native cases and original DET/STO residuals; exact source/plan/archive in the R2 review | Operational/mathematical qualification, not scalar size frontier |
| Scalar h215 job2217990 | Accepted DET/STO original certificates, gap targets and resource/physical summaries | Principal existing scalar baseline; detailed vectors/cost/input joins still need availability/inventory verification |
| Scalar h300 job2218193 | Researcher reports RUNNING, source04ba9edc; plan000a760b... | Preparation/execution status only; every outcome, vector and resource result awaits terminal collection and review |
| Scalar h400 / existing-SCIP h215 / h500 | Planned separate gates | No current outcome or admission from this editorial PR; h500 remains conditional on its existing h400 gate |
| MVP1 / hierarchical MVP2 | Frozen original cohorts and S2 closure | Historical context/supplement only; no substitution for scalar performance or investment findings |

The [accepted h215 ledger](../evidence/scalar_h215_2217990_review.json) contains:

| Quantity | DET | STO | Scope |
| --- | ---: | ---: | --- |
| Native runtime,s |122.514958 |2445.517971 | Optimizer-reported runtime, not construction or Slurm elapsed |
| Achieved native gap,% |0.0008121363 |0.7401594783 | Current scalar objective; configured target1% |
| Domestic service,% |91.8611844 |92.2673837 | Preserve the original summary definition/weights |
| Penalty share,% |96.5917779 |96.9865311 | Artificial penalty contribution to total |
| Shortage,t |55157764.56712728 |52404901.4756365 | DET total; STO expected total |
| Stock exceedance,t-period |77844818.9532763 |109069101.65344787 | DET total; STO expected total across warehouse-periods |
| Reception overflow,t |57340372.36206411 |67843194.81333904 | DET total; STO expected period-overflow total |
| Original residual certificate |accepted |accepted | Original validation replay, not newly recomputed private residuals |

Display fewer digits in the article where they do not hide a threshold. Keep
the table above and original ledger for traceability. The researcher accepts
this pair under the fixed-coefficient contract; its physical slack quantities
do not impose a new rejection rule. STO is not an expected-value reformulation
of DET, and the two costs do not measure the value of stochastic information.

## Proposed main and supplementary outputs

| ID / output | Scientific purpose | Source and existing evidence | Missing data / required work | New optimization needed? | Acceptance criterion |
| --- | --- | --- | --- | --- | --- |
| T1 Scalar experiment design | Identify denominator and varying factors | Frozen h215/h300 plans, manifests, source/runtime/warehouse receipts | Populate actual completed/unrun arms after terminal audit; later approved gates separately | No | One row per attempt/arm with actual state, model/scenarios/routes, configured budgets and independent status |
| T2 DET/STO computational baseline | Show effects of scenario structure at the same population | h215 run_summary.json, input_receipt.json, solver diagnostics, resource/accounting receipts | Recover dimensions/nonzeros, best bound/objective and phase/measurement scopes from originals | No, extract existing outputs | Native/common gaps and targets correctly labelled; no unavailable field filled from subtraction or another scope |
| T3 Agricultural decisions | Report what the model selects | warehouse_decisions.csv plus warehouses_used.csv/json | Verify original exported vectors, quantity thresholds and ID/role binding | No | Candidate activation, positive candidate capacity, expansion/conversion activations and positive quantities separately reported |
| T4 Cost composition | Distinguish expenditure and artificial penalties | result.json cost_breakdown; original input costs and independent_validation.json | Extract opening/candidate/expansion/bulk costs, four transport/handling terms, storage and each penalty | No | Investment once plus expected operations and penalties reconstructs the original objective within its existing validation rule |
| F1 Scalar computational pipeline | Explain developed workflow accessibly | Current scalar source and accepted artifacts | New diagram specification: input/route/scenario preparation, sparse construction, one optimize call, independent validation, reporting | No | No priority passes, learning module or distributed MILP claim; data versus solver phases explicit |
| F2 Validated infrastructure map | Make chosen locations and infrastructure decisions visible | Accepted scalar decisions; original registry/input coordinates and region IDs | Rights-aware CDA join, unique-ID checks, separate symbols and positive-quantity indicators | No | Exactly one common first-stage plan per chosen STO case; unselected candidates distinguishable; coordinates not invented or merged by coincidence |
| F3 Investment composition | Show capital expenditure by decision category/region | Same original decisions/costs as T4 | Reconstruct category totals; join regions where allowed | No | Sum agrees with the original once-charged investment total; input-currency/horizon label |
| F4 Capacity-pressure heatmaps | Show where and when permitted violations concentrate | emergency_capacity.csv; original capacities/days; scenario probabilities; geographic join | Region-period expected values, scenario-specific/worst-case panels, denominators and peaks | No | Separate stock and reception units; maxima identify scenario/location/time; no sum of unlike quantities as installed capacity |
| F5 Resource-quality comparison | Characterize scalar h300 thread behavior | Terminal h300 diagnostics and same-block runtime/hardware evidence | Complete collector and independent review; include censored/no-incumbent/unrun outcomes | Only the already-running approved block | Same input/contract; CPU/SMT/affinity and order recorded; one observation per level disclosed; no universal ranking |
| F6 Workflow phase timing | Improve readability of the historical slide18 idea | Nonoverlapping recorded clocks from accepted scalar arms | Build a new scalar chart; use null for missing/overlapping phases | No | Phase definitions and outer clocks explicit; never relabel historical priorities as scalar phases |
| T5 Operating outcomes | Link grain allocation and utilization to the selected infrastructure | flows.csv, inventories.csv, storage_by_warehouse.csv, scenario_performance.csv and input demands | Separate domestic/export roles, selected OD/DC/DD/OC usage and inventory utilization | No | Product/period/scenario-aware totals; optional exports and repeated transport legs interpreted correctly |
| S1 Input dimensions and economics | Reproduce physical/economic basis | Original workbook/audits, warehouse membership, original manifests | Totals of supply/domestic demand/export bounds, capacity, costs, currency/price-year facts | No | Every field has unit and source; missing price-year/currency fact is explicit; rights respected |
| S2 Scenario design | Reproduce the nine finite realizations | Input multiplier levels; recorded Cartesian mode and effective probabilities | Exact nine multiplier pairs and weights, base DET arrays treated separately | No | Nine weights1/9 sum to one; source levels verified; no normalization of inactive workbook rows |
| S3 Historical context | Preserve earlier positive, partial and failed evidence | Existing original MVP1/S1/S2 ledgers and supplementary review | State policy/runtime/budget differences and match each claim to its original cohort | No | No pooling of hierarchy/scalar outcomes or replacing original false/rejected certificates |
| S4 Reproducibility | Bind every displayed result/figure to source | Original completion inventories, validation, source/input/runtime identities | Tidy table/figure provenance and read-only generation manifest | No | Exact inputs and script version hash-bound; originals retained; public rights/access boundaries described |
| S5 Full literature review | Preserve the full review and search trail | manuscript/supplement plus prior reconciliation | Author confirmation of search chronology, alternative-source count and item-level records | No | Corrected figures follow documentary records rather than arithmetic invention |

This is an extraction specification and inventory. It does not claim that the
private h215 archive is presently available to this PR workspace. Reuse its
accepted original outputs when supplied/located. The h300 collector already
exports decisions and diagnostics; do not modify or rerun its live source to add
editorial metrics. Any missing retained field is a post-run retrieval question,
not automatic justification for repeating optimization.

## Actual export contract and extraction rules

`src/logic/experiment_runner.py: _export_run_artifacts` writes `result.json`,
`model_audit.json`, `warehouse_decisions.csv`, `flows.csv`, `inventories.csv`,
`unmet_demand.csv`, `emergency_capacity.csv`, `scenario_performance.csv`,
`material_balance_by_scenario.csv`, `capacity_gap_by_scenario.csv`,
`investment_saturation.csv`, `emergency_capacity_daily.csv`,
`storage_by_warehouse.csv` and `storage_by_scenario.csv`. Confirm the actual
product directory through its original completion inventory rather than guessing
a path or reconstructing a certificate. Empty sparse exports can mean no positive
record in that family, but only a closed successful export establishes that scope.

The investment rows currently include warehouse,is_existing,is_candidate,open,
candidate_capacity,expand,expansion_capacity,bulkify,bulk_capacity,static_capacity
and effective_static_capacity. Join by exact warehouse identifier. A location can
have duplicate coordinates while remaining a distinct facility. Check source
IDs, roles, uniqueness and region completeness before geographic aggregation.

First-stage counts are not probability-weighted. For validated binary activations,
a display classification above0.5 can describe the discrete decision; report the
original numeric value and validation status in its source data. Count positive
capacity/use separately using a declared reporting threshold consistent with
original numerical tolerances. Such display thresholds do not modify the model,
original certificates or acceptance rules. No positive minimum capacity is added.

Use the exact coefficients and quantity fields from the original run to
reconstruct opening/candidate capacity, expansion and bulk-handling expenditure.
Keep zero fixed costs as recorded. Do not impose a new fixed/variable cost split.
Some `scenario_metrics.operating_cost` exports include penalty components: use
the individual cost_breakdown keys (`transport_od`, `transport_dc`, `transport_dd`,
`transport_oc`, `storage`, `unmet_demand`, `emergency_static`, `emergency_reception`
and investment keys) rather than assuming a field named operating_cost is the
unpenalized economic subtotal. Reconcile against the original objective and
independent cost reconstruction; do not sum overlapping summaries.

For scenario-specific quantity Q_s, its expected total is sum_s pi_s Q_s. Preserve
per-scenario values and provide extrema when scientifically useful. Domestic
aggregate service may be reported as1 - expected_shortage/expected_demand when
that matches the original summary definition. The expected scenario service
ratio is a different statistic when demand totals differ; label it separately.
Use null/N/A for zero-denominator ratios, never an imputed perfect service value.

The sum of flow values over all transport legs counts transshipment repeatedly.
It cannot represent unique grain supply. Use origin dispatch/delivered demand
for mass accounting; tonne-km deliberately weights each used leg by its original
distance. Label all region and export-role aggregations precisely.

Stock exceedance totals aggregate state violations over periods. For infrastructure
interpretation, report warehouse-period peaks and their locations, keeping
expected peaks distinct from peaks of expected values. Reception overflow is
period tonnes; the daily equivalent divides by recorded operating days. A suggested
stock-pressure ratio is q^K_{wts}/K_w(X) when nominal capacity is positive, and
reception pressure is q^R_{wts}/(d_t R_w(X)) when that denominator is positive.
Alternative ratios against scenario supply/demand need matching time, region
and commodity scope. Do not compare a stock sum across60 periods directly to
one period's supply or call it extra installed tonnes.

## Representative solution rule for coauthor review

Use the accepted h215 DET and STO pair to establish the two model roles. Add a
scalar h300 representative only after terminal/evidence review. Choose the case
by declared scientific coverage and available validated outputs, recording its
quality status, rather than selecting a visually appealing outcome. A feasible
censored solution may be interpreted if clearly labelled and approved for that
role; it cannot be called a target-met optimum. If alternatives have indistinguishable
quality, first-stage patterns may differ because optimal plans need not be unique.
Do not infer that one geography is a robust real-world recommendation.

Public maps and row-level candidate information remain subject to source rights
and author disclosure decisions. Aggregated tables can be prepared while those
decisions are pending. No new optimization is necessary merely to improve the
agricultural explanation of a solution whose original decisions were retained.
