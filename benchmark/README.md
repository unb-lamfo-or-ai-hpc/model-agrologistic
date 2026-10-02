# Historical benchmark assets

These files retain the historical source-pool context: supply, demand, warehouse
registry, initial stock, investment and handling costs, storage tariffs and
freight rates. `benchmark_config.json` belongs to the exploratory benchmark
workflow; it is not the current v0.2 final reference plan.

The authoritative reconstruction process verifies the external pinned assets in
[the source contract](../data/manifests/mvp_data_contract.json). Follow the
[reproduction protocol](../docs/artur_reproduction_protocol.md), including the
distinction between raw, normalized and solver-adapted instances.

This directory alone cannot reproduce the published thesis tables. Generated
instance selection, duplicate-key handling, routing snapshot, scenario path and
solver configuration all affect results. The historical OSM snapshot and
forecasting path remain unreconstructed. Separate slacks also change the shared
historical penalty objective.

Preserve original files. Do not edit them to match a target objective value or
treat an unbounded export marker as domestic demand. Audit redistribution and
attribution obligations before including these third-party data in a publication.
