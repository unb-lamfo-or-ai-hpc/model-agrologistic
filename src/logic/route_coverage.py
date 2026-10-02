"""Structural reachability diagnostics for filtered logistics networks."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from typing import Any

from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData
from src.logic.route_filtering import SelectedRoutes, select_routes

TaggedNode = tuple[str, str]


def build_route_coverage_audit(
    data: ModelData,
    config: ModelConfig,
) -> dict[str, Any]:
    """Audit whether active supply and demand pairs remain connected after filtering."""

    routes = select_routes(data, config)
    active_supply = (
        _positive_pairs(data.supply_s, 1, 2)
        if config.mode == "sto"
        else _positive_pairs(data.supply, 0, 1)
    )
    active_domestic = (
        _positive_pairs(data.demand_dom_s, 1, 2)
        if config.mode == "sto"
        else _positive_pairs(data.demand_dom, 0, 1)
    )
    active_export = (
        _positive_pairs(data.demand_exp_s, 1, 2)
        if config.mode == "sto"
        else _positive_pairs(data.demand_exp, 0, 1)
    )
    products = sorted(
        {
            product
            for _, product in active_supply | active_domestic | active_export
        }
    )

    product_records: list[dict[str, Any]] = []
    customer_records: list[dict[str, Any]] = []
    supply_records: list[dict[str, Any]] = []

    for product in products:
        adjacency = _adjacency(routes, product)
        supply_origins = sorted(
            origin for origin, item_product in active_supply if item_product == product
        )
        reachable_from_any: set[TaggedNode] = set()
        per_origin: dict[str, set[TaggedNode]] = {}
        for origin in supply_origins:
            reachable = _reachable(adjacency, ("origin", origin))
            per_origin[origin] = reachable
            reachable_from_any.update(reachable)

        domestic_customers = sorted(
            customer
            for customer, item_product in active_domestic
            if item_product == product
        )
        export_customers = sorted(
            customer
            for customer, item_product in active_export
            if item_product == product
        )
        missing_domestic = [
            customer
            for customer in domestic_customers
            if ("customer", customer) not in reachable_from_any
        ]
        missing_export = [
            customer
            for customer in export_customers
            if ("customer", customer) not in reachable_from_any
        ]

        for customer in domestic_customers + export_customers:
            customer_records.append(
                {
                    "product": product,
                    "customer": customer,
                    "customer_class": (
                        "domestic"
                        if customer in domestic_customers
                        else "export"
                    ),
                    "selected_dc_routes": sum(
                        route_product == product and route_customer == customer
                        for _, route_customer, route_product in routes.dc
                    ),
                    "selected_oc_routes": sum(
                        route_product == product and route_customer == customer
                        for _, route_customer, route_product in routes.oc
                    ),
                    "reachable_from_active_supply": (
                        ("customer", customer) in reachable_from_any
                    ),
                }
            )

        for origin, reachable in per_origin.items():
            supply_records.append(
                {
                    "product": product,
                    "origin": origin,
                    "reachable_warehouses": sum(
                        node_type == "warehouse"
                        for node_type, _ in reachable
                    ),
                    "reachable_domestic_customers": sum(
                        ("customer", customer) in reachable
                        for customer in domestic_customers
                    ),
                    "reachable_export_customers": sum(
                        ("customer", customer) in reachable
                        for customer in export_customers
                    ),
                }
            )

        product_records.append(
            {
                "product": product,
                "active_supply_origins": len(supply_origins),
                "active_domestic_customers": len(domestic_customers),
                "active_export_customers": len(export_customers),
                "missing_domestic_customers": missing_domestic,
                "missing_export_customers": missing_export,
                "supply_origins_without_domestic_path": [
                    origin
                    for origin, reachable in per_origin.items()
                    if not any(
                        ("customer", customer) in reachable
                        for customer in domestic_customers
                    )
                ],
                "supply_origins_without_export_path": [
                    origin
                    for origin, reachable in per_origin.items()
                    if not any(
                        ("customer", customer) in reachable
                        for customer in export_customers
                    )
                ],
            }
        )

    return {
        "schema_version": 1,
        "model_mode": config.mode,
        "route_filter_strategy": config.route_filter_strategy,
        "route_fraction": config.pareto_fraction,
        "direct_origin_customer": config.use_direct_origin_customer,
        "selected_route_counts": {
            "OD": len(routes.od),
            "DC": len(routes.dc),
            "DD": len(routes.dd),
            "OC": len(routes.oc),
        },
        "summary": {
            "all_active_domestic_customers_reachable": all(
                not record["missing_domestic_customers"]
                for record in product_records
            ),
            "all_active_export_customers_reachable": all(
                not record["missing_export_customers"]
                for record in product_records
            ),
            "active_supply_origin_product_pairs": len(active_supply),
            "active_domestic_customer_product_pairs": len(active_domestic),
            "active_export_customer_product_pairs": len(active_export),
            "unreachable_domestic_customer_product_pairs": sum(
                len(record["missing_domestic_customers"])
                for record in product_records
            ),
            "unreachable_export_customer_product_pairs": sum(
                len(record["missing_export_customers"])
                for record in product_records
            ),
            "supply_origin_product_pairs_without_domestic_path": sum(
                len(record["supply_origins_without_domestic_path"])
                for record in product_records
            ),
            "supply_origin_product_pairs_without_export_path": sum(
                len(record["supply_origins_without_export_path"])
                for record in product_records
            ),
        },
        "by_product": product_records,
        "customer_coverage": customer_records,
        "supply_origin_coverage": supply_records,
    }


def _positive_pairs(
    values: Mapping[tuple[str, ...], float],
    node_index: int,
    product_index: int,
) -> set[tuple[str, str]]:
    return {
        (str(key[node_index]), str(key[product_index]))
        for key, value in values.items()
        if float(value) > 0.0
    }


def _adjacency(routes: SelectedRoutes, product: str) -> dict[TaggedNode, set[TaggedNode]]:
    adjacency: dict[TaggedNode, set[TaggedNode]] = {}

    def add(source: TaggedNode, target: TaggedNode) -> None:
        adjacency.setdefault(source, set()).add(target)

    for origin, warehouse, route_product in routes.od:
        if route_product == product:
            add(("origin", origin), ("warehouse", warehouse))
    for source, destination, route_product in routes.dd:
        if route_product == product:
            add(("warehouse", source), ("warehouse", destination))
    for warehouse, customer, route_product in routes.dc:
        if route_product == product:
            add(("warehouse", warehouse), ("customer", customer))
    for origin, customer, route_product in routes.oc:
        if route_product == product:
            add(("origin", origin), ("customer", customer))
    return adjacency


def _reachable(
    adjacency: Mapping[TaggedNode, set[TaggedNode]],
    source: TaggedNode,
) -> set[TaggedNode]:
    visited = {source}
    queue = deque([source])
    while queue:
        node = queue.popleft()
        for target in adjacency.get(node, set()):
            if target not in visited:
                visited.add(target)
                queue.append(target)
    return visited
