"""Auditable route-filter decisions and connectivity-repair candidates.

Policy repair uses eligible materialized routes, not invented distances. Its
deterministic path ordering is a greedy coverage mechanism, not a proof of a
globally minimum repair network. Reachability alone does not establish
throughput feasibility or domestic-service attainment.
"""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from math import ceil, isfinite
from typing import Any

from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData
from src.logic.route_coverage import build_route_coverage_audit
from src.logic.route_filtering import SelectedRoutes, select_routes

type Route = tuple[str, str, str]
type TaggedNode = tuple[str, str]

ROUTE_DECISION_FIELDS = (
    "route_type",
    "source",
    "destination",
    "product",
    "customer_class",
    "family_enabled",
    "group_node_role",
    "group_node",
    "distance_km",
    "rank_within_group",
    "group_candidate_count",
    "selection_cutoff_count",
    "selected_by_base_rule",
    "selected",
    "selection_reason",
)

CONNECTIVITY_GAP_FIELDS = (
    "customer",
    "customer_class",
    "product",
    "gap_cause",
    "selected_dc_routes",
    "selected_oc_routes",
    "candidate_inbound_routes",
    "repair_status",
    "minimal_added_route_count",
    "added_distance_km",
    "path_distance_km",
    "path_edge_count",
)


class RouteConnectivityError(ValueError):
    """Raised when the declared connectivity contract cannot be repaired."""

CONNECTIVITY_REPAIR_FIELDS = (
    "customer",
    "customer_class",
    "product",
    "path_order",
    "route_type",
    "source",
    "destination",
    "distance_km",
    "is_added_route",
    "rank_within_group",
    "group_candidate_count",
    "selection_cutoff_count",
)


@dataclass(frozen=True, slots=True)
class _RouteFamily:
    route_type: str
    routes: set[Route]
    distances: dict[tuple[str, str], float]
    enabled: bool


@dataclass(frozen=True, slots=True)
class _Edge:
    route_type: str
    source_node: TaggedNode
    target_node: TaggedNode
    source: str
    destination: str
    product: str
    distance_km: float
    selected: bool

    @property
    def signature(self) -> str:
        return (
            f"{self.route_type}:{self.source}:{self.destination}:"
            f"{self.product}"
        )


def build_route_connectivity_diagnostics(
    data: ModelData,
    config: ModelConfig,
) -> dict[str, list[dict[str, Any]]]:
    """Explain filtering decisions and propose real-route connectivity repairs.

    Repairs are diagnostic only. For each disconnected customer/product pair,
    the method finds a path in the full eligible route graph while minimizing
    the number of excluded routes first, their distance second, and total path
    distance third. It never mutates the routes consumed by an optimizer.
    """

    selected = select_routes(data, config)
    decisions = _route_filter_decisions(data, config, selected)
    decision_index = {
        (
            str(record["route_type"]),
            str(record["source"]),
            str(record["destination"]),
            str(record["product"]),
        ): record
        for record in decisions
    }
    coverage = build_route_coverage_audit(data, config)
    active_supply = _active_supply_pairs(data, config)

    gaps: list[dict[str, Any]] = []
    repair_records: list[dict[str, Any]] = []
    for customer_record in coverage["customer_coverage"]:
        if customer_record["reachable_from_active_supply"]:
            continue

        customer = str(customer_record["customer"])
        customer_class = str(customer_record["customer_class"])
        product = str(customer_record["product"])
        selected_dc = int(customer_record["selected_dc_routes"])
        selected_oc = int(customer_record["selected_oc_routes"])
        candidate_inbound = sum(
            route_product == product and route_customer == customer
            for _, route_customer, route_product in data.routes_dc
        )
        if config.use_direct_origin_customer:
            candidate_inbound += sum(
                route_product == product and route_customer == customer
                for _, route_customer, route_product in data.routes_oc
            )

        path = _minimal_repair_path(
            data,
            config,
            selected,
            active_supply,
            customer,
            product,
        )
        if path is None:
            repair_status = "no_candidate_path"
            added_count: int | None = None
            added_distance: float | None = None
            path_distance: float | None = None
            path_edge_count: int | None = None
        else:
            repair_status = "candidate_path_found"
            added_edges = [edge for edge in path if not edge.selected]
            added_count = len(added_edges)
            added_distance = sum(edge.distance_km for edge in added_edges)
            path_distance = sum(edge.distance_km for edge in path)
            path_edge_count = len(path)
            for path_order, edge in enumerate(path, start=1):
                decision = decision_index[
                    (
                        edge.route_type,
                        edge.source,
                        edge.destination,
                        edge.product,
                    )
                ]
                repair_records.append(
                    {
                        "customer": customer,
                        "customer_class": customer_class,
                        "product": product,
                        "path_order": path_order,
                        "route_type": edge.route_type,
                        "source": edge.source,
                        "destination": edge.destination,
                        "distance_km": edge.distance_km,
                        "is_added_route": not edge.selected,
                        "rank_within_group": decision["rank_within_group"],
                        "group_candidate_count": decision[
                            "group_candidate_count"
                        ],
                        "selection_cutoff_count": decision[
                            "selection_cutoff_count"
                        ],
                    }
                )

        gaps.append(
            {
                "customer": customer,
                "customer_class": customer_class,
                "product": product,
                "gap_cause": (
                    "no_selected_inbound_route"
                    if selected_dc + selected_oc == 0
                    else "selected_inbound_disconnected_upstream"
                ),
                "selected_dc_routes": selected_dc,
                "selected_oc_routes": selected_oc,
                "candidate_inbound_routes": candidate_inbound,
                "repair_status": repair_status,
                "minimal_added_route_count": added_count,
                "added_distance_km": added_distance,
                "path_distance_km": path_distance,
                "path_edge_count": path_edge_count,
            }
        )

    return {
        "route_filter_decisions": decisions,
        "connectivity_gaps": gaps,
        "connectivity_repair_candidates": repair_records,
    }


def apply_connectivity_repair(
    data: ModelData,
    config: ModelConfig,
    selected: SelectedRoutes,
) -> SelectedRoutes:
    """Add the smallest deterministic paths required by the policy contract.

    Domestic customer/product pairs are repaired individually. Export is a
    surplus-disposition option, so the default contract requires at least one
    reachable export sink per active product. The stronger all-sinks contract
    remains configurable for resilience studies. Each iteration reuses routes
    added earlier, which makes the repair deterministic and parsimonious but
    does not claim a globally minimum Steiner network.
    """

    current = SelectedRoutes(
        od=set(selected.od),
        dc=set(selected.dc),
        dd=set(selected.dd),
        oc=set(selected.oc),
    )
    repairs: dict[str, set[Route]] = {
        "OD": set(),
        "DC": set(),
        "DD": set(),
        "OC": set(),
    }
    active_supply = _active_supply_pairs(data, config)

    for customer, product in sorted(_active_customer_pairs(data, config, "domestic")):
        path = _minimal_repair_path(
            data,
            config,
            current,
            active_supply,
            customer,
            product,
        )
        if path is None:
            raise RouteConnectivityError(
                "No finite eligible path can connect active domestic demand "
                f"for customer={customer!r}, product={product!r}."
            )
        current = _add_path(current, repairs, path)

    active_export = _active_customer_pairs(data, config, "export")
    export_by_product: dict[str, list[str]] = {}
    for customer, product in active_export:
        export_by_product.setdefault(product, []).append(customer)

    for product, customers in sorted(export_by_product.items()):
        if config.connectivity_export_policy == "all_active_customer_product_pairs":
            for customer in sorted(customers):
                path = _minimal_repair_path(
                    data,
                    config,
                    current,
                    active_supply,
                    customer,
                    product,
                )
                if path is None:
                    raise RouteConnectivityError(
                        "No finite eligible path can connect active export demand "
                        f"for customer={customer!r}, product={product!r}."
                    )
                current = _add_path(current, repairs, path)
            continue

        candidate_paths = [
            path
            for customer in sorted(customers)
            if (
                path := _minimal_repair_path(
                    data,
                    config,
                    current,
                    active_supply,
                    customer,
                    product,
                )
            )
            is not None
        ]
        if not candidate_paths:
            raise RouteConnectivityError(
                "No finite eligible path reaches an export sink for active "
                f"product={product!r}."
            )
        current = _add_path(
            current,
            repairs,
            min(candidate_paths, key=_path_score),
        )

    return SelectedRoutes(
        od=current.od,
        dc=current.dc,
        dd=current.dd,
        oc=current.oc,
        repair_od=repairs["OD"],
        repair_dc=repairs["DC"],
        repair_dd=repairs["DD"],
        repair_oc=repairs["OC"],
    )


def _active_customer_pairs(
    data: ModelData,
    config: ModelConfig,
    customer_class: str,
) -> set[tuple[str, str]]:
    if customer_class == "domestic":
        values = data.demand_dom_s if config.mode == "sto" else data.demand_dom
    else:
        values = data.demand_exp_s if config.mode == "sto" else data.demand_exp
    node_index = 1 if config.mode == "sto" else 0
    product_index = 2 if config.mode == "sto" else 1
    return {
        (str(key[node_index]), str(key[product_index]))
        for key, value in values.items()
        if float(value) > 0.0
    }


def _add_path(
    selected: SelectedRoutes,
    repairs: dict[str, set[Route]],
    path: tuple[_Edge, ...],
) -> SelectedRoutes:
    route_sets: dict[str, set[Route]] = {
        "OD": set(selected.od),
        "DC": set(selected.dc),
        "DD": set(selected.dd),
        "OC": set(selected.oc),
    }
    for edge in path:
        route = (edge.source, edge.destination, edge.product)
        if route not in route_sets[edge.route_type]:
            route_sets[edge.route_type].add(route)
            repairs[edge.route_type].add(route)
    return SelectedRoutes(
        od=route_sets["OD"],
        dc=route_sets["DC"],
        dd=route_sets["DD"],
        oc=route_sets["OC"],
    )


def _path_score(path: tuple[_Edge, ...]) -> tuple[object, ...]:
    added = [edge for edge in path if not edge.selected]
    return (
        len(added),
        sum(edge.distance_km for edge in added),
        sum(edge.distance_km for edge in path),
        tuple(edge.signature for edge in path),
    )


def _route_filter_decisions(
    data: ModelData,
    config: ModelConfig,
    selected: SelectedRoutes,
) -> list[dict[str, Any]]:
    selected_by_type: dict[str, set[Route]] = {
        "OD": set(selected.od),
        "DC": set(selected.dc),
        "DD": set(selected.dd),
        "OC": set(selected.oc),
    }
    records: list[dict[str, Any]] = []
    for family in _route_families(data, config):
        grouped: dict[tuple[str, str], list[Route]] = {}
        for route in family.routes:
            grouped.setdefault(_selection_group(route, family, config), []).append(
                route
            )

        for (group_node, _product), candidates in sorted(grouped.items()):
            ordered = sorted(
                candidates,
                key=lambda route: (_distance(family, route), route),
            )
            cutoff = _selection_cutoff(len(ordered), config)
            for rank, route in enumerate(ordered, start=1):
                source, destination, route_product = route
                selected_by_base = family.enabled and rank <= cutoff
                is_selected = route in selected_by_type[family.route_type]
                if not family.enabled:
                    reason = "route_family_disabled"
                elif config.route_filter_strategy == "none":
                    reason = "unfiltered"
                elif selected_by_base:
                    reason = "within_group_cutoff"
                elif route in _repair_routes(selected, family.route_type):
                    reason = "connectivity_repair"
                elif is_selected:
                    reason = "coverage_augmentation"
                else:
                    reason = "outside_group_cutoff"
                records.append(
                    {
                        "route_type": family.route_type,
                        "source": source,
                        "destination": destination,
                        "product": route_product,
                        "customer_class": _customer_class(
                            data,
                            family.route_type,
                            destination,
                        ),
                        "family_enabled": family.enabled,
                        "group_node_role": _group_node_role(family, config),
                        "group_node": group_node,
                        "distance_km": _distance(family, route),
                        "rank_within_group": rank,
                        "group_candidate_count": len(ordered),
                        "selection_cutoff_count": cutoff if family.enabled else 0,
                        "selected_by_base_rule": selected_by_base,
                        "selected": is_selected,
                        "selection_reason": reason,
                    }
                )
    return sorted(
        records,
        key=lambda record: (
            str(record["route_type"]),
            str(record["product"]),
            str(record["group_node"]),
            int(record["rank_within_group"]),
            str(record["source"]),
            str(record["destination"]),
        ),
    )


def _route_families(
    data: ModelData,
    config: ModelConfig,
) -> tuple[_RouteFamily, ...]:
    return (
        _RouteFamily("OD", set(data.routes_od), data.dist_od, True),
        _RouteFamily("DC", set(data.routes_dc), data.dist_dc, True),
        _RouteFamily(
            "DD",
            set(data.routes_dd),
            data.dist_dd,
            config.use_warehouse_transshipment,
        ),
        _RouteFamily(
            "OC",
            set(data.routes_oc),
            data.dist_oc,
            config.use_direct_origin_customer,
        ),
    )


def _selection_group(
    route: Route,
    family: _RouteFamily,
    config: ModelConfig,
) -> tuple[str, str]:
    source, destination, product = route
    if config.route_filter_strategy in {
        "thesis_pareto",
        "connectivity_preserving_pareto",
    }:
        return source, product
    if family.route_type in {"OD", "DD"}:
        return source, product
    return destination, product


def _group_node_role(family: _RouteFamily, config: ModelConfig) -> str:
    if config.route_filter_strategy in {
        "thesis_pareto",
        "connectivity_preserving_pareto",
    }:
        return "source"
    return "source" if family.route_type in {"OD", "DD"} else "destination"


def _selection_cutoff(candidate_count: int, config: ModelConfig) -> int:
    if config.route_filter_strategy == "none":
        return candidate_count
    if config.route_filter_strategy == "top_k":
        return min(candidate_count, int(config.route_top_k or 0))
    return max(1, ceil(candidate_count * config.pareto_fraction))


def _repair_routes(selected: SelectedRoutes, route_type: str) -> set[Route]:
    return set(getattr(selected, f"repair_{route_type.lower()}", set()))


def _distance(family: _RouteFamily, route: Route) -> float:
    return float(family.distances.get((route[0], route[1]), float("inf")))


def _customer_class(data: ModelData, route_type: str, destination: str) -> str:
    if route_type not in {"DC", "OC"}:
        return ""
    if destination in data.domestic_customers:
        return "domestic"
    if destination in data.export_customers:
        return "export"
    return "unknown"


def _active_supply_pairs(
    data: ModelData,
    config: ModelConfig,
) -> set[tuple[str, str]]:
    values = data.supply_s if config.mode == "sto" else data.supply
    node_index = 1 if config.mode == "sto" else 0
    product_index = 2 if config.mode == "sto" else 1
    return {
        (str(key[node_index]), str(key[product_index]))
        for key, value in values.items()
        if float(value) > 0.0
    }


def _minimal_repair_path(
    data: ModelData,
    config: ModelConfig,
    selected: SelectedRoutes,
    active_supply: set[tuple[str, str]],
    customer: str,
    product: str,
) -> tuple[_Edge, ...] | None:
    adjacency = _full_adjacency(data, config, selected, product)
    origins = sorted(
        origin
        for origin, active_product in active_supply
        if active_product == product
    )
    target = ("customer", customer)
    serial = count()
    heap: list[
        tuple[
            int,
            float,
            float,
            tuple[str, ...],
            str,
            str,
            int,
            tuple[_Edge, ...],
        ]
    ] = []
    best: dict[TaggedNode, tuple[int, float, float, tuple[str, ...]]] = {}

    for origin in origins:
        node = ("origin", origin)
        signature = (f"origin:{origin}",)
        key = (0, 0.0, 0.0, signature)
        best[node] = key
        heappush(
            heap,
            (0, 0.0, 0.0, signature, node[0], node[1], next(serial), ()),
        )

    while heap:
        (
            added_count,
            added_distance,
            total_distance,
            signature,
            node_type,
            node_id,
            _,
            path,
        ) = heappop(heap)
        node = (node_type, node_id)
        key = (added_count, added_distance, total_distance, signature)
        if best.get(node) != key:
            continue
        if node == target:
            return path

        for edge in adjacency.get(node, ()):
            is_added = not edge.selected
            next_key = (
                added_count + int(is_added),
                added_distance + (edge.distance_km if is_added else 0.0),
                total_distance + edge.distance_km,
                (*signature, edge.signature),
            )
            previous = best.get(edge.target_node)
            if previous is not None and previous <= next_key:
                continue
            best[edge.target_node] = next_key
            heappush(
                heap,
                (
                    *next_key,
                    edge.target_node[0],
                    edge.target_node[1],
                    next(serial),
                    (*path, edge),
                ),
            )
    return None


def _full_adjacency(
    data: ModelData,
    config: ModelConfig,
    selected: SelectedRoutes,
    product: str,
) -> dict[TaggedNode, tuple[_Edge, ...]]:
    adjacency: dict[TaggedNode, list[_Edge]] = {}
    selected_by_type: dict[str, set[Route]] = {
        "OD": set(selected.od),
        "DC": set(selected.dc),
        "DD": set(selected.dd),
        "OC": set(selected.oc),
    }

    def add(
        route_type: str,
        route: Route,
        source_type: str,
        target_type: str,
        distances: dict[tuple[str, str], float],
    ) -> None:
        source, destination, route_product = route
        if route_product != product:
            return
        distance = float(distances.get((source, destination), float("inf")))
        if not isfinite(distance):
            return
        source_node = (source_type, source)
        edge = _Edge(
            route_type=route_type,
            source_node=source_node,
            target_node=(target_type, destination),
            source=source,
            destination=destination,
            product=route_product,
            distance_km=distance,
            selected=route in selected_by_type[route_type],
        )
        adjacency.setdefault(source_node, []).append(edge)

    for route in data.routes_od:
        add("OD", route, "origin", "warehouse", data.dist_od)
    for route in data.routes_dc:
        add("DC", route, "warehouse", "customer", data.dist_dc)
    if config.use_warehouse_transshipment:
        for route in data.routes_dd:
            add("DD", route, "warehouse", "warehouse", data.dist_dd)
    if config.use_direct_origin_customer:
        for route in data.routes_oc:
            add("OC", route, "origin", "customer", data.dist_oc)

    return {
        node: tuple(sorted(edges, key=lambda edge: edge.signature))
        for node, edges in adjacency.items()
    }

