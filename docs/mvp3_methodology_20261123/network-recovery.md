# Recovery of historical 80/20 network selection

The author clarified on 23 November 2026 that “Pareto” in network preparation means the historical 80/20 edge filter. It is distinct from the proposed economic–service frontier of planning outcomes.

## Source and effective-reference evidence

The recovered implementation is pinned to develop commit `2391137cdbe4f86cdb784f9e4e545944fac2a688`:

- `src/logic/route_filtering.py`: `_select_thesis_pareto_routes`, `_select`, and `select_routes`.
- `src/logic/route_connectivity.py`: `apply_connectivity_repair`, `_minimal_repair_path`, `_path_score`, and `_full_adjacency`.
- The effective reference manifest SHA-256 is `80dfd864af958387a229ef5719a76fd6ca1db5fd060a658f89b404214be2b31f`.

The filter was introduced before the current reconciliation; repository history includes commit `3c686f0a3223124abe5925957625469046d3d7b7` (“Add connectivity-preserving policy filter”, 9 September 2026). This review recovers its semantics; it does not change its executable bytes.

## Exact recovered procedure

1. Use materialised eligible directed routes, product identities, and the enabled W families. OW/WD/WW map to mathematical OD/DC/DD.
2. For each family, group by source node and product. Sort by distance, then the full route tuple. Keep `max(1, ceil(0.20 * n))` routes from each nonempty group. This is a nearest-distance heuristic, not an empirical assertion about 80% of flow or value.
3. Build reachability paths from origins with positive supply of the product. Domestic pairs with positive demand are checked individually. STO activation is the union across its applicable scenarios and periods.
4. If a required path is absent, search the full eligible graph. The path ordering minimises lexicographically: added arc count, added arc distance, full path distance, deterministic path signature. The search permits warehouse hops and never fabricates a distance.
5. Add that path before processing the next target, retaining earlier additions. This is a sequential coverage repair, not a globally minimal Steiner-network claim.
6. The reference export policy is `one_sink_per_product`. The optional all-active-export-pairs policy is stronger. Strong interhub connectivity is a separate disabled setting.
7. Freeze selected routes, repair subsets and policy identity. Reproducing a frozen graph is distinct from re-running a selection procedure on a larger candidate pool.

## Independently replayed structural coverage

A standard-library multi-source breadth-first traversal was run against the effective tables after verifying all seven support-file digests. Role tags were derived from OW/WW/WD families, keeping customer labels separate from warehouse and origin labels. The audit uses unions of positive entries and does not certify period/scenario-specific capacity feasibility.

| Scope | Active source/product pairs | Reachable domestic pairs | Reachable export pairs | Domestic shortest paths | Recorded repair additions |
|---|---:|---:|---:|---|---:|
| h215 DET/W | 44 | 54/54 | 20/20 | 53 with 2 edges; 1 with 3 edges | 0 |
| h215 STO/W | 44 | 54/54 | 20/20 | 53 with 2 edges; 1 with 3 edges | 0 |
| h300 STO/W | 44 | 54/54 | 20/20 | 54 with 2 edges | 0 |
| h400 STO/W | 44 | 54/54 | 20/20 | 54 with 2 edges | 0 |
| h500 STO/W | 44 | 54/54 | 20/20 | 54 with 2 edges | 0 |

The h215 three-edge witness requires a warehouse-to-warehouse hop. The default policy only requires an export sink per product, but the actual frozen graph reaches all 20 active export pairs. Empty repair ledgers record that these frozen references contain no separately tagged additions; the observed coverage is verified independently rather than inferred from those empty ledgers.

The full selected product-indexed counts remain 25,112 / 45,240 / 76,320 / 115,400. Membership nesting does not imply arc nesting, because rankings and cutoffs can change as the candidate pool grows.

## Distinguishing missing values

A filtered arc is a known route omitted by the selection policy. A missing cache result is an acquisition/reconciliation issue. Neither is a zero distance. A selected arc carrying positive flow is a further solution-dependent object.

The historical OSRM client separately maps negative round-off distances in [-1,0) metres to an effective zero while preserving raw cache records. Coordinate coincidence alone is not a reason to invent or overwrite a distance.

## Reproduction

Run `audit_frozen_graph.py --support <identified-private-effective-bundle> --output <new-audit.json>` locally with Python 3.11 or later. It reads and verifies the support bundle, performs no routing/solver/HPC call, and refuses to overwrite an existing audit output. The accompanying JSON retains the aggregate results. The private input data are not redistributed here.
