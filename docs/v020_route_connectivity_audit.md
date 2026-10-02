# v0.2.0 route-connectivity audit

## Purpose and scope

The route-connectivity audit separates reproduction from policy design. The
`thesis_pareto` strategy remains an unchanged reconstruction of the historical
filter: for every source/product group and route family, routes are ordered by
distance and destination identifier, and the shortest
`ceil(0.20 * candidate_count)` routes are retained. No route is added after
this historical selection. This behavior is required for thesis-compatible
comparisons even when the resulting graph is disconnected.

The current audit does not change the optimization graph. It explains every
selection decision and identifies the smallest set of already measured,
eligible routes that could repair each disconnected customer/product pair.
Consequently, audit results must not be interpreted as optimization results or
as a silently corrected thesis experiment.

## Historical equivalence

The historical implementation in `cvictorr2508/silodss`,
`src/logic/optimization.py` (blob
`b6220d741e9e22eeba732c5706b689fe0ad2bd0a`), constructs OD, DC, DD, and OC
candidate groups by source and product. It sorts each group by distance and
destination identifier and keeps at least one route, using the ceiling of 20
percent of the group size. The deterministic and stochastic code paths use the
same rule. The `thesis_pareto` implementation and its reported ranks follow
those semantics.

## Audit artifacts

Running `scripts/audit_route_coverage.py` preserves the existing per-run JSON
files and summary, and adds three deterministic CSV artifacts:

- `route_filter_decisions.csv` records every eligible route, its route family,
  source/product selection group, distance, deterministic tie-broken rank,
  cutoff, selected state, and selection reason;
- `connectivity_gaps.csv` records each unreachable active
  customer/product pair, distinguishes a missing inbound route from an inbound
  route disconnected upstream, and summarizes the diagnostic repair path;
- `connectivity_repair_candidates.csv` records every edge on that path and
  explicitly marks the excluded edges that would have to be added.

The diagnostic path is selected lexicographically: first minimize the number
of excluded routes, then minimize the distance of added routes, and finally
minimize total path distance. It searches only route families enabled by the
experiment and only finite distances already present in the model input. It
does not synthesize a distance, use a geographic straight line, or assign a
Big-M transport cost.

## Interpretation

A connectivity gap after an OSRM-complete materialization is a consequence of
the route-selection rule, not evidence that OSRM failed to find a road path.
The audit must therefore be read together with the workbook distance
provenance and adapter audit. A repair candidate is admissible only when its
distance has the accepted source required by the experiment.

The diagnostic criterion is deliberately structural. It establishes that a
path exists; it does not claim that the path has sufficient throughput or
storage capacity, nor that its warehouses will be opened by the MILP.
Capacity adequacy remains an optimization outcome and is reported separately
through unmet-demand and emergency-capacity slacks.

## Policy extension accepted after the audit gate

The policy profile uses a distinct `connectivity_preserving_pareto` strategy.
It starts from the same grouped fraction and adds only the real, excluded
routes required by an explicit service-connectivity contract. The contract is:

1. every active domestic customer/product pair must be reachable from at least
   one active supply origin;
2. every active product must have at least one reachable export sink when an
   export sink exists in the data;
3. all repair routes retain their measured distance and ordinary transport
   cost and are flagged as connectivity repairs;
4. the thesis-compatible profile remains unchanged;
5. the policy profile reports base and repaired route counts separately and
   evaluates 15, 20, and 25 percent fractions.

Repairs are applied in deterministic customer/product order and reuse routes
added for earlier pairs. Each path is lexicographically minimal under the
audit criterion. This is a transparent greedy connectivity heuristic; it does
not claim to solve a global Steiner-network problem. The MILP subsequently
decides whether the structurally available warehouses and routes should be
used, subject to ordinary investment, capacity, and cost constraints.

Requiring every export port to be reachable is a stronger resilience policy
and should be evaluated separately. It is not needed merely to preserve the
model's ability to allocate surplus supply to export.

## Reproducible audit command

From the repository root, after materializing the OSRM solver workbook:

```bash
python scripts/audit_route_coverage.py \
  experiments/v020_thesis_compatible.yaml \
  --indices 0 1 6 7 \
  --output-dir \
  data/results/hpc/v020_thesis_compatible_osrm/route_coverage
```

The audit is solver-free. Its three CSV files establish the traceable baseline
against which policy repair routes are reported.

