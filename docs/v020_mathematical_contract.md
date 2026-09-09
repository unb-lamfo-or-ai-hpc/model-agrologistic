# v0.2.0 mathematical contract

## Purpose

Version 0.2.0 restores the mathematical parameterization used in Artur's
deterministic and stochastic case studies. The only deliberate structural
extension is that static-capacity and reception-capacity feasibility slacks
are represented separately because they have different physical units.

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

## Complete recourse and candidate activation

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
economically valid.

Emergency-capacity penalty rates equal fifty times the largest reference
expansion or storage rate, subject to a floor of 100. The unmet-demand rate is
customer-indexed, as in the thesis rule: it equals one hundred times the
largest applicable route, expansion, or storage rate for that customer and is
then replicated across products in the canonical data structure. These rates
preserve feasibility and support qualitative capacity-gap interpretation; they
are not observed shortage prices.

Static and reception slacks must be reported separately and may not be summed
as if they were dimensionally identical. Their activation is a research
result, not an automatic acceptance failure. Domestic service and material
balance remain the primary validity conditions.

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

## Evidence profiles

### Thesis-compatible bounded reproduction

`experiments/v020_thesis_compatible.yaml` contains six deterministic and six
coupled three-scenario stochastic configurations: interhub factors 0.8, 1.0,
and 1.2 crossed with direct arcs disabled and enabled. Supply and demand use
minus 20 percent, central, and plus 20 percent coupled scenarios with
probabilities 0.33, 0.34, and 0.33. Initial stock fills existing static
capacity and is divided equally among products.

This is a mathematical reproduction on the bounded reconstructed instance.
The historical OSRM matrix and forecasting path remain unavailable, and this
limitation is carried in the evidence metadata.

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
2. thesis deterministic and three-scenario profiles pass dry-run preflight;
3. all reduced policy profiles pass staged preflight;
4. licensed Gurobi solves validate representative thesis deterministic and
   stochastic profiles;
5. licensed Gurobi solves validate the 20-percent policy deterministic and
   nine-scenario profiles within the approved HPC envelope;
6. the time-limit study exports incumbent objective, MIP gap, and the three
   timing regions;
7. material balance, domestic service, separate emergency slacks, investment
   decisions, EVPI/VSS decomposition, and provenance remain dimensionally
   valid.

Version 0.2.0 remains a development candidate until this gate is complete.
