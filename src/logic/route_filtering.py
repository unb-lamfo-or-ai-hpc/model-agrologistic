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
    """Select nearest routes while preserving a connection for every group.

    OD routes are grouped by origin/product, DC and OC routes by
    customer/product, and DD routes by source warehouse/product. A top-k or
    Pareto selection is then applied independently inside each group.
    """

    return SelectedRoutes(
        od=_select(
            data.routes_od,
            config,
            group=lambda route: (route[0], route[2]),
            distance=lambda route: data.dist_od.get((route[0], route[1]), float("inf")),
        ),
        dc=_select(
            data.routes_dc,
            config,
            group=lambda route: (route[1], route[2]),
            distance=lambda route: data.dist_dc.get((route[0], route[1]), float("inf")),
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

