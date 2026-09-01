"""Deterministic route selection shared by optimization backends and preflight."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Callable, TypeVar

from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData, RouteDC, RouteDD, RouteOC, RouteOD


Route = TypeVar("Route", RouteOD, RouteDC, RouteDD, RouteOC)


@dataclass(frozen=True, slots=True)
class SelectedRoutes:
    """Route sets after applying structural flags and distance filtering."""

    od: set[RouteOD]
    dc: set[RouteDC]
    dd: set[RouteDD]
    oc: set[RouteOC]


def select_routes(data: ModelData, config: ModelConfig) -> SelectedRoutes:
    """Select compact routes while preserving end-to-end flow coverage.

    OD routes are grouped by origin/product, DC and OC routes by
    customer/product, and DD routes by source warehouse/product. A top-k or
    Pareto selection is first applied inside each group. DC routes are then
    augmented so every warehouse/product selected on an OD route has an
    outbound customer route and, when available, an export route.
    """

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
        oc=(
            _select(
                data.routes_oc,
                config,
                group=lambda route: (route[1], route[2]),
                distance=lambda route: data.dist_oc.get(
                    (route[0], route[1]), float("inf")
                ),
            )
            if config.use_direct_origin_customer
            else set()
        ),
    )


def _select(
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


def _nearest_per_group(
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

