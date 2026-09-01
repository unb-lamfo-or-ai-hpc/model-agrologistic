"""Network-aware safe bounds for multi-period emergency capacity variables."""

from __future__ import annotations

from collections import defaultdict

from src.logic.model_data import ModelData
from src.logic.route_filtering import SelectedRoutes


def deterministic_inventory_bounds(
    data: ModelData,
    routes: SelectedRoutes,
) -> dict[tuple[str, str], float]:
    """Bound inventory by supply that can reach each warehouse through the network."""

    reachable = _reachable_sources(data, routes)
    bounds: dict[tuple[str, str], float] = {}
    for warehouse in data.warehouses:
        running_supply = 0.0
        initial = _reachable_initial_inventory(data, reachable, warehouse)
        for period in data.periods:
            running_supply += sum(
                data.supply.get((origin, product, period), 0.0)
                for origin, product in reachable[warehouse]["origin_products"]
            )
            bounds[warehouse, period] = max(1.0, initial + running_supply)
    return bounds


def stochastic_inventory_bounds(
    data: ModelData,
    routes: SelectedRoutes,
) -> dict[tuple[str, str, str], float]:
    """Return network-aware cumulative bounds for every stochastic scenario."""

    reachable = _reachable_sources(data, routes)
    bounds: dict[tuple[str, str, str], float] = {}
    for scenario in data.scenarios:
        for warehouse in data.warehouses:
            running_supply = 0.0
            initial = _reachable_initial_inventory(data, reachable, warehouse)
            for period in data.periods:
                running_supply += sum(
                    data.supply_s.get(
                        (scenario, origin, product, period), 0.0
                    )
                    for origin, product in reachable[warehouse]["origin_products"]
                )
                bounds[scenario, warehouse, period] = max(
                    1.0, initial + running_supply
                )
    return bounds


def _reachable_sources(
    data: ModelData,
    routes: SelectedRoutes,
) -> dict[str, dict[str, set[tuple[str, str]]]]:
    reverse_dd: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for source, destination, product in routes.dd:
        reverse_dd[product][destination].add(source)

    origins_by_destination: dict[tuple[str, str], set[str]] = defaultdict(set)
    for origin, warehouse, product in routes.od:
        origins_by_destination[warehouse, product].add(origin)

    reachable: dict[str, dict[str, set[tuple[str, str]]]] = {}
    for target in data.warehouses:
        origin_products: set[tuple[str, str]] = set()
        warehouse_products: set[tuple[str, str]] = set()
        for product in data.products:
            predecessor_warehouses = _reverse_reachable(
                target, reverse_dd[product]
            )
            warehouse_products.update(
                (warehouse, product) for warehouse in predecessor_warehouses
            )
            for warehouse in predecessor_warehouses:
                origin_products.update(
                    (origin, product)
                    for origin in origins_by_destination[warehouse, product]
                )
        reachable[target] = {
            "origin_products": origin_products,
            "warehouse_products": warehouse_products,
        }
    return reachable


def _reverse_reachable(
    target: str,
    predecessors: dict[str, set[str]],
) -> set[str]:
    reachable = {target}
    pending = [target]
    while pending:
        destination = pending.pop()
        for source in predecessors.get(destination, set()):
            if source in reachable:
                continue
            reachable.add(source)
            pending.append(source)
    return reachable


def _reachable_initial_inventory(
    data: ModelData,
    reachable: dict[str, dict[str, set[tuple[str, str]]]],
    warehouse: str,
) -> float:
    return sum(
        data.initial_inventory.get((source, product), 0.0)
        for source, product in reachable[warehouse]["warehouse_products"]
    )

