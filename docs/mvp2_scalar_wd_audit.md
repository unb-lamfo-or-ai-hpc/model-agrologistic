# Scalar MVP2 W and D topology audit

Audit date: 22 October 2026. Inspected develop source:
`6fb43389ea70b02d0f54c959a2bfff8d53d83af4`.
This report is a documentary audit and a prospective design, **not execution
admission**. The maintainer explicitly requested this independent PR; that
request permits committing this report despite the supplied audit template's
generic prohibition on creating a PR. Model, manifests, tests, budgets, original
data, claims and certificates are unchanged. PR120 remains independently draft.

## A. Implementation and mathematical status

W forbids direct origin-to-destination transport. D permits it; D does not
require positive direct flow, prohibit warehouse use, or remove transshipment.
The manuscript terminology is Origin–Warehouse–Destination. Legacy serialized
labels retain their original meanings:

| Internal family | Scientific family | Endpoints | Unit transport/handling cost, BRL/t |
| --- | --- | --- | --- |
| OD | OW | Origin → warehouse | Origin freight × distance + receiving warehouse charge |
| DC | WD | Warehouse → destination | Dispatching warehouse freight × distance |
| DD | WW | Warehouse → warehouse | Interhub factor × dispatching warehouse freight × distance + receiving charge |
| OC | OD (direct) | Origin → destination | Origin freight × distance; no warehouse receiving charge |

Every source link below is pinned to the inspected develop commit, not to a
moving branch. These functions were read, not inferred from their names.

| Layer | Actual source and function | Finding |
| --- | --- | --- |
| Configuration | [model_config.py, ModelConfig](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/6fb43389ea70b02d0f54c959a2bfff8d53d83af4/src/logic/model_config.py#L199) | `use_direct_origin_customer` defaults false; transshipment is a distinct switch |
| Loader | [excel_loader.py, load_model_data_from_excel](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/6fb43389ea70b02d0f54c959a2bfff8d53d83af4/src/logic/excel_loader.py#L365) | OC construction additionally requires `include_direct_origin_customer_routes`; the model switch alone cannot recreate absent input arcs |
| Selection | [route_filtering.py, select_routes](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/6fb43389ea70b02d0f54c959a2bfff8d53d83af4/src/logic/route_filtering.py#L44) | Both switches, actual distances, product eligibility and sparse selection matter; retained routes differ from raw distance rows |
| Connectivity | [route_connectivity.py, apply_connectivity_repair](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/6fb43389ea70b02d0f54c959a2bfff8d53d83af4/src/logic/route_connectivity.py#L231) | Direct paths can replace the need to repair warehouse-mediated paths; common-family equality must be checked explicitly |
| Effective inputs | [mathematical_contract.py, prepare_model_data](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/6fb43389ea70b02d0f54c959a2bfff8d53d83af4/src/logic/mathematical_contract.py#L98) | Freezes graph and indexed penalties; changing a frozen route policy is rejected, rather than silently reusing its identity |
| DET dispatch | [optimization_gurobipy.py, solve_model_gurobipy](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/6fb43389ea70b02d0f54c959a2bfff8d53d83af4/src/logic/optimization_gurobipy.py#L23) | Original DET arrays become one probability-one scenario in the same extensive-form builder; output scenario fields are projected back |
| Gurobi DET/STO | [optimization_gurobipy_stochastic.py, solve_stochastic_model_gurobipy](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/6fb43389ea70b02d0f54c959a2bfff8d53d83af4/src/logic/optimization_gurobipy_stochastic.py#L40) | OC variables enter supply and domestic/export arrival sums, not warehouse stock/handling; first-stage investments remain shared |
| SCIP DET/STO | [optimization_scip.py, solve_model_scip](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/6fb43389ea70b02d0f54c959a2bfff8d53d83af4/src/logic/optimization_scip.py#L59) | Same four arc families and scalar costing helpers; native SCIP balances and slack indicators, not a second scientific topology |
| Costs | [optimization_gurobipy.py, four unit-cost helpers](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/6fb43389ea70b02d0f54c959a2bfff8d53d83af4/src/logic/optimization_gurobipy.py#L353) | Distances/freight/receiving costs as above; scenario weighting occurs once in the extensive-form objective |
| Independent validation | [solution_validation.py, validate_solution](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/6fb43389ea70b02d0f54c959a2bfff8d53d83af4/src/logic/solution_validation.py#L37) | Independently reconstructs all four flow families, frozen-arc membership, supply/demand/export, warehouse balances/capacities, investments and 14 cost components |

**Conclusion:** both topologies are implemented for DET/STO in Gurobi and SCIP.
This is a source-and-software-support finding, not evidence of a large scalar D
experiment. Tests include direct-only feasibility, economic direct use, split
flows and shared export bounds in `tests/test_gurobipy_direct_origin_customer.py`;
`tests/test_scip_backend.py::test_transshipment_and_direct_route_selection` covers
native SCIP. Scalar singleton/multiple-scenario and independent-validator tests
cover the shared formulation. These do not constitute a matched h215 W×D campaign.

### A switch can have effects beyond adding variables

The current `thesis_dynamic` policy recalculates shortage weights from selected
DC **and OC** costs (`prepare_model_data`), after the loader's own initial
penalty calculation (`excel_loader._build_penalty_rates`). Enabling OC can thus
change objective coefficients, not just feasible transport. Existing accepted
operational gates assert every effective 90000/45000/45000 entry and reject
drift; they do not authorize a new D case. Graph repair is another possible
confounder. A matched design must verify actual indexed coefficients and the
OD/DC/DD edge sets, not merely equal YAML defaults or equal row counts.

## B. Evidence inventory

The original archives were read without importing code from them. SHA256,
`input_receipt.json` model flags/retained counts and positive-flow record
families were checked. No original certificate was rewritten.

Local input-only inspection of the exact40edb665… workbook additionally rebuilt
the two retained graphs without constructing a solver model or optimizing.
For this h215 input, OD/DC/DD are **set-identical**, D adds592 product-specific
OC arcs, and both effective indexed penalty vectors have SHA256
`e0f93593659c35d14b85cdaddecbe020edb375376f5e30ae99b05bed876d276f`.
Thus the two identified confounders do not materialize in this inspected input.
This finding must still be rebound to any future qualified execution source.
The [compact input inspection](evidence/scalar_wd_h215_input_inspection_20261022.json)
is retained separately from the archive ledger; it is not a D solve.
Expected added flow variables are35520 for DET and319680 for nine-scenario STO,
giving1597694 and14374334 total variables respectively under unchanged indexing.

| Accepted scalar observation | Job / source prefix | W/D | Retained OD / DC / DD / OC (product-indexed, before scenario-period replication) |
| --- | --- | --- | --- |
| h215 DET | 2217990 / 5f73871b | W | 3182 / 3440 / 18490 / 0 |
| h215 STO, nine equiprobable | 2217990 / 5f73871b | W | 3182 / 3440 / 18490 / 0 |
| h300 STO, five thread observations | 2218193 / 04ba9edc | W | 4440 / 4800 / 36000 / 0 in every arm |
| h400 STO, one thread | 2219884 / d9ca710d | W | 5920 / 6400 / 64000 / 0 |

All eight receipts set `use_direct_origin_customer=false`; their loaders also
disable OC construction, and no exported positive-flow row has family OC.
Archive identities and compact findings are in
[the audit ledger](evidence/scalar_wd_audit_20261022.json).
The h500 job2220382 has only its previously supplied RUNNING snapshot: current
terminal state and results are unverified, and it is not a W×D comparison.

Historical manifests such as `experiments/v020_policy_mvp.yaml` and
`v020_thesis_compatible.yaml` contain W/D alternatives. Several are version1;
active scalar parsing rejects that version. A planned D row, old numerical
result, tiny analytical test or historical hierarchical certificate is not an
accepted current-scalar D counterpart. None was identified in this accepted
h215/h300/h400 cohort. DET versus STO is also not a pure topology contrast.

## C. Scientific significance and limits

W forces shipment through warehouse reception/shipping and may incentivize
opening and handling investments. D can bypass those constraints for direct
shipments, potentially altering hub utilization, capacity investment, storage,
export allocation and artificial slacks. The model still allocates all supply,
does not create a fourth slack, and does not require use of every available site.
Included sites, candidate activation, positive investment and positive use must
be reported separately, especially with zero fixed activation costs.

With the same common arcs and costs, mapping W into D by setting direct flows
to zero proves feasible-set inclusion and a weakly smaller *exact* minimum.
It does not prove strict improvement, fewer investments, a shorter run, or a
better finite-budget incumbent. Extra continuous variables/columns may improve
the relaxation and bypass bottlenecks, or increase construction/memory/search.
Both observations are empirical questions. Penalized quality ≤1% concerns the
scalar total, not zero slack or economic-subtotal precision. The frozen penalties
remain artificial trade-offs, not monetary expenditures or service guarantees.

For a nested graph with `n_OC` product-specific direct arcs, D adds
`n_OC × periods × scenarios` continuous flow variables and corresponding balance
nonzeros. It adds no first-stage binary by itself. Constraint counts need not
grow at the algebraic level, though presolve/indicators and repairs can alter
solver-reported dimensions. Retain linear rows, general constraints, binary and
continuous counts, raw and presolved metrics with their respective scopes.

## D. Minimum comparative experiment PROPOSED ONLY

Begin with h215, not an immediate cross-scale campaign. A complete DET/STO W×D
factorial consists of four cells. Only the two D cells are missing as scientific
topology observations. First qualify input-only W/D preparation and compare it
to the original h215 receipts; do not submit a job to diagnose input differences.

**Preferred minimum: two new cold D solves**, DET then STO, if their W restriction
is identical to the accepted h215 input/network/penalty contract. Reuse W's
original certificates as historical controls. This establishes a conditional
structural/solution comparison, not a contemporaneous causal runtime estimate.
If common arcs/coefficients cannot be preserved, stop for researcher approval
of the design; do not silently recalibrate or change route policy. A four-cell
new block is an alternative only if contemporaneous performance comparison is
required and its W repetitions receive explicit approval. No repeated statistical
performance campaign is proposed as a publication prerequisite.

Proposed budget, **not approved**: mirror h215's per-arm global TimeLimit14400s,
Threads4, gap0.01, Seed42, compaction off, SoftMemLimit160 decimal GB; one serial
14h allocation with24 logical CPUs/192GiB, same homogeneous node family and
affinity, and ≤1GiB expanded transfer. This is336 logical-CPU·h reserved,
not measured consumption or a reliable D-runtime forecast. Two solves permit
8h native optimization and the existing phase/cleanup margins. Admission must
first show D fits the size/memory/transfer guards; spare walltime does not grant
extra optimization or automatic retries. A four-cell allocation needs a new
explicit phase sum, not an assumed14h or48h reservation.

Prerequisites and acceptance:

1. Exact original h215 OSRM workbook hash40edb665…; actual215 IDs/roles/order,
   supplier/customer/product/60-period records, initial stocks and cost vectors
   identical. DET original singleton and STO nine Cartesian1/9 cases remain fixed.
2. Loader admits OC from that same workbook; same OSRM dataset/profile and no
   fallback/live requests. Freeze/compare OD/DC/DD edge hashes and direct edge
   list. Any repair difference is reported and blocks a topology-only claim.
3. Every indexed penalty entry remains90000/45000/45000 after preparation.
   No coefficient override or altered policy is implemented by this audit.
4. Single scalar objective, original capacities/indicators/units/tolerances,
   code/backend/version/solver options and telemetry scopes match. Bind all
   identities before a fresh exclusive claim. Retain all prior claims unchanged.
5. Export variables/rows/nonzeros/retained arcs; construction/optimization/end-to-end
   time and phase-memory; incumbent, bound, native/common gap and stop reason;
   investment/transport/storage and each artificial penalty; opened/expanded/
   bulkified sites and quantities; direct/mediated flows by product/time/scenario;
   and original independent residual/objective receipts.
6. Separate scheduler completion, valid incumbent and scalar quality attainment
   (≤0.01). Above-target or no-incumbent outcomes remain censored/negative evidence,
   not infeasibility proof or grounds to discard/repeat. Compare bound intervals
   `[best bound, incumbent]`; do not assert optimal topology superiority from
   incumbent ordering alone. Report common economic and slack components.

## E. Roadmap and decisions

This audit fits R3's topology verification and R5/S6-A's scientific synthesis.
PR120's new Appendices C/D should cite the terminology and input dependencies,
without claiming D was experimentally evaluated. The independent audit PR has
no dependency on merging the still-draft editorial work. h500 collection and
the separately deferred SCIP/h215 decision keep their existing boundaries.

Researcher decision required: whether to authorize the proposed two-cell D
qualification/execution package, or require four contemporaneous cells. Input
and resource qualification, Ready, merge authorization and pinned human CLI
must precede any future job. This report does not activate a manifest, create
an executable launcher, alter approved budgets, or reopen cancelled S3/S4,
EVPI/VSS, calibration, Benders, or protected-main integration timing.

## Software/document qualification

Related existing route-selection/connectivity and independent-validator tests:
39 passed, no failures/skips, on Windows/Python3.13. No optimization tests or
HPC commands were invoked for this audit. Git scope inspection must confirm
only AGENTS/checkpoint/report and compact derived JSON changes; original
scientific source, experiments and evidence receipts remain byte-identical
to the pinned develop base. Existing required PR CI is a software gate only.
