# Warehouse population scalability protocol

> MVP boundary: OSRM materialization has been exercised at 215 and 500
> warehouses. Larger populations, the definitive 14,400-second solve frontier
> and the full sensitivity campaign are deferred. Registry levels below define
> future experiments, not a requirement to optimize all 18,000 facilities.

## Purpose

The policy extension evaluates how model size and stochastic dimensionality affect
computational performance while preserving a traceable relationship with the
canonical 215-facility study. It is separate from the thesis-compatible bounded
reproduction. No result from an enlarged population may be presented as a numerical
replication of the thesis.

## Source registry and canonical anchor

The source registry contains real Brazilian storage facilities identified by a
unique CDA code. The audit preserves all 146 existing facilities. The 69 candidate
facilities already present in the canonical gold workbook define the first
population level, so the 215-facility baseline remains unchanged.

Candidate facilities with nonpositive observed static capacity are excluded before
sampling. Facilities that share coordinates remain distinct records because a
shared coordinate does not imply a duplicated facility identifier. The OSRM cache
can nevertheless reuse coordinate-pair queries for these facilities.

The registered nested checkpoints are 215, 500, 1,000, 2,000, 5,000, 10,000,
and 18,000 facilities. The 18,000 level is a registry ceiling, not a solve
target or feasibility claim. After the canonical anchor, candidates are ranked
deterministically across state, warehouse type, and observed static-capacity
quartile. A SHA-256 seeded order resolves ties and makes the selection independent
of source-row order.

## Solver translation contract

The registry describes observed physical facilities, but its candidate rows do not
directly encode investment-model semantics. Candidate source capacity cannot be
loaded as immediately available capacity because a closed candidate must not behave
as an existing warehouse. Each materialized solver workbook must therefore apply
the following translation:

- candidate base static capacity is zero;
- candidate base reception capacity is zero;
- candidate base shipping capacity is zero;
- candidate maximum static capacity is the observed source static capacity;
- candidate investment cost comes from the canonical investment-cost table;
- zero cost placeholders in the registry are never interpreted as free investment.

The existing-warehouse records retain their observed base capacities. This contract
preserves the activation constraint: candidate capacity becomes available only when
the facility is opened.

## Progressive computational gates

The experiment is intentionally not a full factorial design.

1. Audit and freeze the nested real-facility populations.
2. Materialize one solver workbook per accepted population and validate the
   translation contract.
3. Run solver-free preflight checks for route coverage, variable count, and memory
   risk.
4. Solve the deterministic reference configuration while increasing population
   size. Stop escalation when a documented resource criterion is reached or no
   accepted incumbent is produced within 14,400 seconds.
5. At accepted population sizes, escalate uncertainty from deterministic to three
   coupled scenarios and then to nine Cartesian scenarios.
6. Evaluate direct-arc and 15%, 20%, and 25% route-density sensitivity only at
   selected reference sizes, rather than multiplying every population by every
   policy combination.
7. At selected computational frontiers, compare 600, 3,600, and 14,400 second time
   limits and report incumbent quality, bound, MIP gap, and phase-specific runtime.

For the reference frontier, a population is classified as computationally solved
only when the 14,400-second run returns a feasible incumbent with a relative MIP
gap no greater than 1%, passes material balance, satisfies domestic demand within
the registered numerical tolerance, allocates all supply, and terminates without a
numerical or memory failure. A time-limit result with a feasible incumbent but a
larger gap remains scientifically informative, but it is classified as censored
rather than solved. The 1% gap is the default frontier criterion and must be stated
with every reported threshold; sensitivity results may use a different registered
gap without silently changing the reference definition.

## Sparse-route interpretation at scale

A fixed fraction of every possible warehouse-to-warehouse pair grows quadratically.
At 18,000 facilities, the complete directed DD graph alone contains approximately
324 million ordered pairs before products, periods, and scenarios are introduced.
It is therefore unsuitable as a routine solve configuration.

The 15%, 20%, and 25% edge-fraction rules remain appropriate for comparison near
the canonical population. Enlarged-population experiments should preserve a
controlled average route degree derived from those reference configurations. A
coordinate-based screen may identify candidate neighbors efficiently, but OSRM
distance remains authoritative for retained road routes. The
`connectivity_preserving_pareto` repair remains the final safeguard and must report
base and repair edges separately.

This large-population sparse rule is a policy-model extension. It must not be
described as the historical thesis filter or as a Pareto optimum.

## Required reporting

Every run must identify the population manifest and source hashes, population size,
scenario count and probabilities, direct-arc policy, route-density policy, retained
and repair edge counts, solver and version, time limit, MIP gap, data-read time,
model-build time, optimization time, peak memory, feasibility-slack use, domestic
service, material balance, investment decisions, and objective decomposition.

The largest successfully solved instance and the first rejected, resource-limited,
or 14,400-second-censored instance jointly bracket the observed computational
frontier. Reaching 18,000 facilities is neither expected nor required. This frontier
is an empirical property of the tested hardware and configuration, not a universal
limit of the mathematical formulation.
