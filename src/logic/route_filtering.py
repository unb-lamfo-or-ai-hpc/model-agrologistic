"""Deterministic route selection shared by optimization backends and preflight."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from math import ceil

from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData, RouteDC, RouteDD, RouteOC, RouteOD


@dataclass(frozen=True, slots=True)
class SelectedRoutes:
    """Route sets after applying structural flags and distance filtering."""

    od: set[RouteOD]
    dc: set[RouteDC]
    dd: set[RouteDD]
    oc: set[RouteOC]
    repair_od: set[RouteOD] = field(default_factory=set)
    repair_dc: set[RouteDC] = field(default_factory=set)
    repair_dd: set[RouteDD] = field(default_factory=set)
    repair_oc: set[RouteOC] = field(default_factory=set)


def select_routes(data: ModelData, config: ModelConfig) -> SelectedRoutes:
    """Select compact routes while preserving end-to-end flow coverage.

    OD routes are grouped by origin/product, DC and OC routes by
    customer/product, and DD routes by source warehouse/product. A top-k or
    Pareto selection is first applied inside each group. DC routes are then
    augmented so every warehouse/product selected on an OD route has an
    outbound customer route and, when available, an export route. When direct
    routes are enabled, every origin/product also keeps its nearest domestic
    customer and export exits.
    """

    if config.route_filter_strategy == "thesis_pareto":
        return _select_thesis_pareto_routes(data, config)

    if config.route_filter_strategy == "connectivity_preserving_pareto":
        from src.logic.route_connectivity import apply_connectivity_repair

        base_routes = _select_thesis_pareto_routes(data, config)
        return apply_connectivity_repair(data, config, base_routes)

    od = _select(
        data.routes_od,
        config,
        group=lambda route: (route[0], route[2]),
        distance=lambda route: data.dist_od.get((route[0], route[1]), float("inf")),
    )
    dc = _select(
        data.routes_dc,
        config,
        group=lambda route: (route[1], route[2]),
        distance=lambda route: data.dist_dc.get((route[0], route[1]), float("inf")),
    )
    dc.update(_outbound_routes_for_selected_warehouses(data, config, od))

    oc: set[RouteOC] = set()
    if config.use_direct_origin_customer:
        oc = _select(
            data.routes_oc,
            config,
            group=lambda route: (route[1], route[2]),
            distance=lambda route: data.dist_oc.get(
                (route[0], route[1]), float("inf")
            ),
        )
        oc.update(_direct_routes_for_all_origins(data, config))

    return SelectedRoutes(
        od=od,
        dc=dc,
        dd=(
            _select(
                data.routes_dd,
                config,
                group=lambda route: (route[0], route[2]),
                distance=lambda route: data.dist_dd.get(
                    (route[0], route[1]), float("inf")
                ),
            )
            if config.use_warehouse_transshipment
            else set()
        ),
        oc=oc,
    )


def _select_thesis_pareto_routes(
    data: ModelData,
    config: ModelConfig,
) -> SelectedRoutes:
    """Reproduce the historical 80/20 route construction exactly.

    The historical implementation retained the shortest ceil(0.20 * n)
    candidates in each source/product group. It did not add routes after
    filtering to repair network coverage. The configured fraction remains
    explicit so controlled sensitivity runs can reuse the historical grouping
    without being mislabeled as the thesis's 20 percent experiment.
    """

    return SelectedRoutes(
        od=_select(
            data.routes_od,
            config,
            group=lambda route: (route[0], route[2]),
            distance=lambda route: data.dist_od.get(
                (route[0], route[1]), float("inf")
            ),
        ),
        dc=_select(
            data.routes_dc,
            config,
            group=lambda route: (route[0], route[2]),
            distance=lambda route: data.dist_dc.get(
                (route[0], route[1]), float("inf")
            ),
        ),
        dd=(
            _select(
                data.routes_dd,
                config,
                group=lambda route: (route[0], route[2]),
                distance=lambda route: data.dist_dd.get(
                    (route[0], route[1]), float("inf")
                ),
            )
            if config.use_warehouse_transshipment
            else set()
        ),
        oc=(
            _select(
                data.routes_oc,
                config,
                group=lambda route: (route[0], route[2]),
                distance=lambda route: data.dist_oc.get(
                    (route[0], route[1]), float("inf")
                ),
            )
            if config.use_direct_origin_customer
            else set()
        ),
    )


def _select[Route: (RouteOD, RouteDC, RouteDD, RouteOC)](
    routes: set[Route],
    config: ModelConfig,
    *,
    group: Callable[[Route], tuple[str, str]],
    distance: Callable[[Route], float],
) -> set[Route]:
    if config.route_filter_strategy == "none":
        return set(routes)

    grouped: dict[tuple[str, str], list[Route]] = {}
    for route in routes:
        grouped.setdefault(group(route), []).append(route)

    selected: set[Route] = set()
    for candidates in grouped.values():
        ordered = sorted(candidates, key=lambda route: (distance(route), route))
        if config.route_filter_strategy == "top_k":
            keep = min(len(ordered), int(config.route_top_k or 0))
        else:
            keep = max(1, ceil(len(ordered) * config.pareto_fraction))
        selected.update(ordered[:keep])
    return selected


def _outbound_routes_for_selected_warehouses(
    data: ModelData,
    config: ModelConfig,
    selected_od: set[RouteOD],
) -> set[RouteDC]:
    """Keep outbound coverage for every warehouse receiving filtered OD flow."""

    if config.route_filter_strategy == "none":
        return set()

    inbound_groups = {(warehouse, product) for _, warehouse, product in selected_od}
    candidates = {
        route
        for route in data.routes_dc
        if (route[0], route[2]) in inbound_groups
    }
    selected = _select(
        candidates,
        config,
        group=lambda route: (route[0], route[2]),
        distance=lambda route: data.dist_dc.get((route[0], route[1]), float("inf")),
    )

    export_candidates = {
        route for route in candidates if route[1] in data.export_customers
    }
    selected.update(
        _nearest_per_group(
            export_candidates,
            group=lambda route: (route[0], route[2]),
            distance=lambda route: data.dist_dc.get(
                (route[0], route[1]), float("inf")
            ),
        )
    )
    return selected


def _direct_routes_for_all_origins(
    data: ModelData,
    config: ModelConfig,
) -> set[RouteOC]:
    """Keep domestic and export exits for every direct origin/product group."""

    if config.route_filter_strategy == "none":
        return set()

    selected: set[RouteOC] = set()
    for customers in (data.domestic_customers, data.export_customers):
        candidates = {
            route for route in data.routes_oc if route[1] in customers
        }
        selected.update(
            _nearest_per_group(
                candidates,
                group=lambda route: (route[0], route[2]),
                distance=lambda route: data.dist_oc.get(
                    (route[0], route[1]), float("inf")
                ),
            )
        )
    return selected


def _nearest_per_group[Route: (RouteOD, RouteDC, RouteDD, RouteOC)](
    routes: set[Route],
    *,
    group: Callable[[Route], tuple[str, str]],
    distance: Callable[[Route], float],
) -> set[Route]:
    grouped: dict[tuple[str, str], list[Route]] = {}
    for route in routes:
        grouped.setdefault(group(route), []).append(route)

    return {
        min(candidates, key=lambda route: (distance(route), route))
        for candidates in grouped.values()
    }

