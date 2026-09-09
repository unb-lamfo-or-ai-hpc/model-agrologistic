# v0.2.0 policy experiment design

## Research question

The policy profile evaluates which candidate openings, capacity expansions,
and bulkification investments remain useful under uncertain supply and demand,
while explicitly measuring the computational frontier of the MILP. It does not
assume that every physically possible route is operationally realistic.

## Gate P1: network and uncertainty sensitivity

Use `experiments/v020_policy_mvp.yaml` on the canonical gold workbook. The
factorial design contains 18 configurations:

- formulation: deterministic, coupled three scenarios, or Cartesian nine
  scenarios;
- direct arcs: disabled or enabled;
- grouped nearest-edge fraction: 15, 20, or 25 percent.

The 20-percent cases are the reference. The 15- and 25-percent cases measure
local sensitivity without assigning causal or optimality meaning to the edge
fraction. Compare feasibility status, domestic service, material balance,
separate emergency slacks, investment decisions, objective components, MIP
gap, and timing regions.

Route filtering must pass the audit described in
`docs/v020_route_connectivity_audit.md` before these configurations are used as
policy evidence. The historical `thesis_pareto` strategy is retained only for
reproduction. The policy experiments use the separately named
`connectivity_preserving_pareto` strategy. It requires every active domestic
customer/product pair and at least one export sink per active product to be
reachable. No Big-M distance or synthetic route may be used to repair the
graph. Preflight reports the base and repair counts for each route family.

Submit one index at a time. Promote the three-scenario and nine-scenario cases
only after the corresponding deterministic preflight and solve are accepted.

## Gate P2: time-to-gap profile

Use `experiments/v020_policy_time_limit.yaml`. Hold the nine-scenario,
20-percent, direct-arc configuration and random seed fixed. Run 600, 3,600, and
14,400 seconds with a zero target gap so that the time limit, rather than an
early relative-gap stop, defines the observation.

Record solver status, incumbent objective, best bound when available, MIP gap,
data-read time, model-build time, optimization time, peak memory, and node
count when available. A time-limited feasible solution is evidence, not a
failure, provided its incumbent, bound, and provenance are preserved.

## Gate P3: warehouse-population scalability

The canonical workbook contains roughly 200 warehouses and cannot establish a
frontier up to the approximately 18,000 real facilities of interest. Build
versioned, immutable workbooks from an auditable real warehouse registry at
the following target populations:

`215, 500, 1,000, 2,000, 5,000, 10,000, 18,000`.

Do not create scale by duplicating or cloning facilities. Each population must
record source identifiers, geographic and capacity coverage, selection rule,
seed when sampling is unavoidable, row counts, and SHA-256 identity. Keep
products, periods, scenario design, direct-arc policy, edge fraction, solver
version, seed, thread count, and hardware fixed within each scaling series.

Run preflight before optimization. Advance to the next population only when the
current case fits the approved memory envelope and produces a usable
incumbent. Stop escalation after an estimated-size rejection, an out-of-memory
termination, or two consecutive runs without a usable incumbent at 14,400
seconds. The largest accepted population defines the demonstrated
computational frontier; it is not evidence that larger real networks are
mathematically infeasible.

## Gate P4: solver parity

Gurobi is the reference solver. The repository reserves a native
`pyscipopt` backend identifier and provides an optional PySCIPOpt dependency;
the backend remains deliberately unimplemented. Before SCIP is used as
evidence, implement it and pass parity tests for:

- all first- and second-stage variables and constraints;
- grouped route filtering and direct-arc policies;
- separate complete-recourse slacks and candidate activation;
- objective components and dynamic penalties;
- deterministic and stochastic status and MIP-gap mapping;
- first-stage fixing and EVPI/VSS decomposition.

Compare solutions within declared numerical tolerances rather than requiring
identical branch-and-bound paths.

## Reporting contract

Every policy result must retain the experiment manifest, workbook hash, source
commit, environment, solver configuration, route counts, estimated variable
count, three timing regions, status, incumbent, bound or MIP gap, memory, model
audit, and structured solution artifacts. Results are extensions of the thesis
case study and must not be presented as direct numerical replication.

