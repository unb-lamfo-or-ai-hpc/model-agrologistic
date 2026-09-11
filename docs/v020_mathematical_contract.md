# v0.2.0 mathematical contract

## Purpose

Version 0.2.0 reconstructs a thesis-compatible core and explicitly separates
it from the policy extension. Stock exceedance and reception overflow have
separate feasibility variables. This changes a shared-slack penalty from
P*max(stock_excess, reception_overflow) to P*(stock_excess + reception_overflow)
for a fixed plan with both violations; numerical equivalence is not claimed.

This contract supersedes the exploratory v0.1 network-policy formulation for
new experiments. The accepted v0.1.0 certification package remains immutable
development evidence and must not be relabeled as thesis-compatible evidence.

## Thesis-compatible equations and policies

The transport costs are defined as follows:

- OD combines origin-to-warehouse freight and the receiving warehouse
  transshipment charge;
- DC uses the sending warehouse freight rate and the warehouse-to-customer
  distance;
- DD uses the sending warehouse freight rate, interhub distance, the explicit
  interhub factor, and the receiving warehouse transshipment charge;
- OC uses the origin freight rate and direct origin-to-customer distance.

All supply is allocated to domestic demand, export flow, or inventory.
Domestic demand is an equality with an unmet-demand slack. Export demand is an
upper bound. Initial inventory is explicit and shared by all scenarios.

Candidate capacity is static capacity and is available only when the candidate
is opened. Expansion and bulkification modify daily reception and shipping
throughput through the configured factors and the operating days in each
period. Expansion and bulkification are mutually exclusive at a warehouse.
The thesis-compatible default is the daily-factor capacity policy.

## Conditional feasibility relaxation and candidate activation

Unmet demand, emergency static capacity, and emergency reception capacity are
feasibility devices with thesis-compatible dynamic Big-M penalty rates. Their
quantities are not bounded by an arbitrary network-derived Big-M. Therefore,
an existing warehouse or an opened candidate may use as much emergency slack
as feasibility requires, and the large objective coefficient exposes the
result as a strategic capacity gap.

This does not authorize capacity at a closed candidate. Candidate regular
capacity is linked to the opening binary, while the two emergency variables
are independent variables. Indicator constraints consequently force both
emergency slacks to zero whenever the candidate opening binary is zero.
Removing those indicators would create a ghost warehouse that could receive
or store material without paying the opening decision. Complete recourse is
thus available over the active infrastructure, while opening semantics remain
economically valid. This is not a proof of complete recourse for every input:
shipping capacity, origin connectivity, export bounds, and activation remain
hard constraints. An isolated positive-supply origin is still infeasible.

Emergency-capacity penalty rates equal fifty times the largest reference
expansion or storage rate, subject to a floor of 100. The unmet-demand rate is
customer-indexed, as in the thesis rule: it equals one hundred times the
largest applicable route, expansion, or storage rate for that customer and is
then replicated across products in the canonical data structure. These rates
preserve feasibility and support qualitative capacity-gap interpretation; they
are not observed shortage prices.

Reception slack is added AFTER daily throughput is multiplied by operating
days. It is overflow tonnes within the period, not tonnes/day. Its daily
equivalent is obtained by division by operating days. Multiplying the slack
by 30 in the objective would apply the conversion twice and is prohibited.

The policy capacity stage uses an equal-weight additive violation score for
stock exceedance and reception overflow, probability-weighted under
uncertainty. This score is not installed capacity. Export each component,
its period aggregation, and its physical peak separately. Emergency use is a
research result, not an automatic acceptance failure.

Before optimization, the selected network and dynamic penalty vector are
frozen together. Historical dynamic penalties inspect selected DC/OC routes,
not discarded routes. RP, EV, WS, and EEV retain the same frozen network and
penalties; scenario projection does not recompute connectivity repair.

Only free terminal inventory is currently implemented by the native backend.
Other policies and nonzero terminal penalties fail explicitly before a solve.

Candidate/expansion investments use tonnes of static capacity. Their daily
throughput factors have units 1/day. The tonne-based bulkification investment
uses explicit daily factors too; its historical coefficient of 1/day maps it
to daily handling. Costs and upper bounds must use that declared investment
basis, not silently switch between tonnes and tonnes/day. Bulkification does
not add static capacity under daily_factors.

The hierarchy is solved within declared MIP and objective tolerances. Setting
ObjNRelTol to zero does not remove the Gurobi MIPGap/MIPGapAbs contribution to
the admissible level of previous objectives. Record pass-end and final values,
bounds, effective tolerances, and observed degradation separately. Classical
monetary EVPI/VSS is restricted to a common scalar penalty objective.

## Route policies

The `thesis_pareto` policy reproduces the historical grouped nearest-edge
rule: OD and OC are grouped by origin and product; DC and DD are grouped by
sending warehouse and product. The shortest ceiling fraction is retained in
each group with deterministic distance and identifier tie-breaking. No
coverage-repair routes are added after filtering.

The historical thesis profile fixes this fraction at 20 percent. The policy
profile reuses the same grouped operator at 15, 20, and 25 percent as a
controlled edge-density sensitivity factor. In that profile the word
"fraction" is preferred to "Pareto": the experiments do not claim that the
selected network is Pareto-optimal.

The `pareto` and `top_k` policies remain archived exploratory v0.1 methods.
Their results are not numerically comparable with the thesis reproduction.

## Road-distance contract

OSRM is the primary road-distance authority for thesis-compatible v0.2
evidence. Distance calculation is a preprocessing step: the adapter queries
the OSRM Table service for every OD, DC, DD, and OC pair and materializes the
result in the solver workbook. Optimization, EVPI/VSS, and restart operations
therefore remain offline and consume an immutable matrix.

The Table service reports distance along the fastest route selected by the
configured OSRM profile. The grouped 20-percent thesis filter subsequently
ranks those materialized road distances. The result must not be described as a
Euclidean or Haversine nearest-neighbour network.

Haversine multiplied by the configured tortuosity factor is allowed only when
OSRM returns no route for a pair or snaps an endpoint beyond the declared
distance threshold. Each fallback records its source and reason in the
Distancias sheet and in distance_audit.csv. OSRM connection failures, timeouts,
HTTP failures, malformed responses, and unsupported response codes are fatal;
they cannot silently change the distance method.

The adapter audit records the endpoint, profile, OSRM data version when
reported, operator-provided dataset identifier, request count, and route counts
by source and fallback reason. A thesis experiment requires
required_distance_source set to osrm_primary and rejects legacy workbooks
without this provenance. Exact numerical replication additionally requires the
historical OSM extract and OSRM profile. Without those artifacts, the run is
method-compatible rather than bitwise identical to the historical thesis.

GraphHopper is a planned multimodal extension and is outside the v0.2 thesis
gate. It may later replace Haversine fallback with explicit rail or waterway
paths, but it must use the same materialized-matrix and provenance contract.

## Evidence profiles

### Thesis-compatible bounded reproduction

`experiments/v020_thesis_compatible.yaml` contains six deterministic and six
coupled three-scenario stochastic configurations: interhub factors 0.8, 1.0,
and 1.2 crossed with direct arcs disabled and enabled. Supply and demand use
minus 20 percent, central, and plus 20 percent coupled scenarios with
probabilities 0.33, 0.34, and 0.33. Initial stock fills existing static
capacity and is divided equally among products.

This is a mathematical reproduction on the bounded reconstructed instance.
The OSRM matrix is rebuilt and frozen with route-level provenance. The exact
historical OSM extract and forecasting path remain unavailable, and those
limitations are carried in the evidence metadata.

### Reduced-network policy MVP

`experiments/v020_policy_mvp.yaml` excludes the complete network. It crosses:

- deterministic, coupled three-scenario stochastic, and Cartesian
  nine-scenario stochastic formulations;
- direct origin-to-customer arcs disabled and enabled;
- grouped nearest-edge fractions of 15, 20, and 25 percent.

These 18 runs use the canonical gold workbook and a 3,600-second reference
limit. They are policy extensions for public-investment analysis, not thesis
replications. Runs must be submitted by index and promoted progressively
rather than launched as an uncontrolled batch.

`experiments/v020_policy_time_limit.yaml` holds the nine-scenario, direct,
20-percent configuration fixed and varies only the time limit over 600, 3,600,
and 14,400 seconds with a zero target MIP gap. This isolates the relationship
among runtime, incumbent objective, best bound, and reported MIP gap.

The warehouse-population scalability protocol and solver roadmap are specified
in `docs/v020_policy_experiment_design.md`.

## Timing evidence

Every primary solve reports three non-overlapping measurements:

- `data_read_seconds`: workbook loading and canonical-data construction;
- `model_build_seconds`: route selection and Gurobi model construction before
  calling `model.optimize()`;
- `optimization_seconds`: wall time spent inside `model.optimize()`.

`runtime_seconds` remains the backward-compatible build-plus-optimization
measurement. For EVPI/VSS campaigns, the three component fields describe the
primary RP solve; checkpointed WS, EV, and EEV solves remain traceable in
their individual result artifacts.

## Solver provision

Gurobi remains the validated v0.2 reference backend. The solver facade now
reserves an explicit `pyscipopt` backend identifier, and the optional `scip`
dependency group installs PySCIPOpt. The reserved backend raises a clear
not-implemented error until its native formulation exists. SCIP results may
enter comparative evidence only after formulation-parity, status-mapping,
parameter, and EVPI/VSS tests pass. Until then, SCIP is a provision rather than
a validated substitute.

## Acceptance gate

PR #25 is accepted only after:

1. all unit and integration tests pass;
2. the OSRM matrix passes provenance and route-coverage audits before any solve;
3. thesis deterministic and three-scenario profiles pass dry-run preflight;
4. all reduced policy profiles pass staged preflight;
5. licensed Gurobi solves validate representative thesis deterministic and
   stochastic profiles;
6. licensed Gurobi solves validate the 20-percent policy deterministic and
   nine-scenario profiles within the approved HPC envelope;
7. the time-limit study exports incumbent objective, MIP gap, and the three
   timing regions;
8. material balance, domestic service, separate emergency slacks, investment
   decisions, EVPI/VSS decomposition, and provenance remain dimensionally
   valid.

Version 0.2.0 remains a development candidate until this gate is complete.
