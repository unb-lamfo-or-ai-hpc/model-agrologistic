"""
Canonical data structures for agricultural logistics optimization.

This module is intentionally solver-agnostic.

It must not import:
- gurobipy
- pyomo
- pandas
- torch
- dash
- plotly

The goal is to provide a common data contract for:
- native Gurobi models;
- Pyomo models, including SCIP;
- HPC batch execution;
- GNN dataset export.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeAlias


# ---------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------

NodeId: TypeAlias = str
ProductId: TypeAlias = str
PeriodId: TypeAlias = str
ScenarioId: TypeAlias = str

RouteOD: TypeAlias = tuple[NodeId, NodeId, ProductId]
"""Origin -> warehouse route: (origin, warehouse, product)."""

RouteDC: TypeAlias = tuple[NodeId, NodeId, ProductId]
"""Warehouse -> customer route: (warehouse, customer, product)."""

RouteDD: TypeAlias = tuple[NodeId, NodeId, ProductId]
"""Warehouse -> warehouse route: (warehouse_from, warehouse_to, product)."""

RouteOC: TypeAlias = tuple[NodeId, NodeId, ProductId]
"""Direct origin -> customer route: (origin, customer, product)."""

Key2: TypeAlias = tuple[str, str]
Key3: TypeAlias = tuple[str, str, str]
Key4: TypeAlias = tuple[str, str, str, str]


# ---------------------------------------------------------------------
# Optional node metadata
# ---------------------------------------------------------------------

@dataclass(slots=True)
class NodeInfo:
    """
    Optional metadata for origins, warehouses, and customers.

    These fields are useful for OSRM distance matrix construction and
    later GNN dataset generation, but they are not required by the MILP
    formulation itself.
    """

    node_id: NodeId
    node_type: str
    name: str | None = None
    state: str | None = None
    municipality: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------
# Main model data class
# ---------------------------------------------------------------------

@dataclass(slots=True)
class ModelData:
    """
    Canonical input data for deterministic and stochastic agricultural
    logistics optimization models.

    This class is shared by all solver backends. It contains only sets,
    parameters, route definitions, costs, capacities, and optional metadata.

    The optimization model itself must be implemented elsewhere.
    """

    # -----------------------------------------------------------------
    # Core sets
    # -----------------------------------------------------------------

    origins: list[NodeId]
    warehouses: list[NodeId]
    existing_warehouses: list[NodeId]
    candidate_warehouses: list[NodeId]
    bulk_eligible_warehouses: list[NodeId]

    customers: list[NodeId]
    domestic_customers: list[NodeId]
    export_customers: list[NodeId]

    products: list[ProductId]
    periods: list[PeriodId]

    # -----------------------------------------------------------------
    # Valid route sets
    # -----------------------------------------------------------------

    routes_od: set[RouteOD] = field(default_factory=set)
    routes_dc: set[RouteDC] = field(default_factory=set)
    routes_dd: set[RouteDD] = field(default_factory=set)
    routes_oc: set[RouteOC] = field(default_factory=set)

    # -----------------------------------------------------------------
    # Deterministic supply and demand
    #
    # supply[(origin, product, period)]
    # demand_dom[(customer, product, period)]
    # demand_exp[(export_customer, product, period)]
    # -----------------------------------------------------------------

    supply: dict[Key3, float] = field(default_factory=dict)
    demand_dom: dict[Key3, float] = field(default_factory=dict)
    demand_exp: dict[Key3, float] = field(default_factory=dict)

    # -----------------------------------------------------------------
    # Stochastic supply and demand
    #
    # supply_s[(scenario, origin, product, period)]
    # demand_dom_s[(scenario, customer, product, period)]
    # demand_exp_s[(scenario, export_customer, product, period)]
    # -----------------------------------------------------------------

    scenarios: list[ScenarioId] = field(default_factory=list)
    scenario_prob: dict[ScenarioId, float] = field(default_factory=dict)

    supply_s: dict[Key4, float] = field(default_factory=dict)
    demand_dom_s: dict[Key4, float] = field(default_factory=dict)
    demand_exp_s: dict[Key4, float] = field(default_factory=dict)

    # -----------------------------------------------------------------
    # Distance and duration matrices
    #
    # Distances are indexed only by node pair.
    # Product-dependent costs are handled separately.
    # -----------------------------------------------------------------

    dist_od: dict[Key2, float] = field(default_factory=dict)
    dist_dc: dict[Key2, float] = field(default_factory=dict)
    dist_dd: dict[Key2, float] = field(default_factory=dict)
    dist_oc: dict[Key2, float] = field(default_factory=dict)

    duration_od: dict[Key2, float] = field(default_factory=dict)
    duration_dc: dict[Key2, float] = field(default_factory=dict)
    duration_dd: dict[Key2, float] = field(default_factory=dict)
    duration_oc: dict[Key2, float] = field(default_factory=dict)

    # -----------------------------------------------------------------
    # Freight, handling, and storage costs
    #
    # freight_origin[(origin)]
    # freight_dest[(customer)]
    # freight_warehouse[(warehouse)]
    # transshipment_cost[(warehouse)]
    # storage_tariff[(warehouse, product)]
    # -----------------------------------------------------------------

    freight_origin: dict[NodeId, float] = field(default_factory=dict)
    freight_dest: dict[NodeId, float] = field(default_factory=dict)
    freight_warehouse: dict[NodeId, float] = field(default_factory=dict)
    transshipment_cost: dict[NodeId, float] = field(default_factory=dict)
    storage_tariff: dict[Key2, float] = field(default_factory=dict)

    # -----------------------------------------------------------------
    # Existing warehouse capacities
    # -----------------------------------------------------------------

    static_capacity: dict[NodeId, float] = field(default_factory=dict)
    reception_capacity: dict[NodeId, float] = field(default_factory=dict)
    shipping_capacity: dict[NodeId, float] = field(default_factory=dict)

    # -----------------------------------------------------------------
    # Candidate warehouse parameters
    #
    # max_candidate_capacity[d]
    # opening_fixed_cost[d]
    # candidate_capacity_cost[d]
    #
    # If candidate capacity mode is "fixed", opening_fixed_cost represents
    # opening the whole facility.
    #
    # If candidate capacity mode is "scalable", candidate_capacity_cost
    # should be used to price each unit of chosen capacity.
    # -----------------------------------------------------------------

    max_candidate_capacity: dict[NodeId, float] = field(default_factory=dict)
    opening_fixed_cost: dict[NodeId, float] = field(default_factory=dict)
    candidate_capacity_cost: dict[NodeId, float] = field(default_factory=dict)

    # -----------------------------------------------------------------
    # Expansion parameters
    # -----------------------------------------------------------------

    max_expand_capacity: dict[NodeId, float] = field(default_factory=dict)
    expand_fixed_cost: dict[NodeId, float] = field(default_factory=dict)
    expand_variable_cost: dict[NodeId, float] = field(default_factory=dict)

    # -----------------------------------------------------------------
    # Bulkification parameters
    # -----------------------------------------------------------------

    max_bulk_capacity: dict[NodeId, float] = field(default_factory=dict)
    bulk_fixed_cost: dict[NodeId, float] = field(default_factory=dict)
    bulk_variable_cost: dict[NodeId, float] = field(default_factory=dict)

    # -----------------------------------------------------------------
    # Initial inventory
    #
    # initial_inventory[(warehouse, product)]
    # -----------------------------------------------------------------

    initial_inventory: dict[Key2, float] = field(default_factory=dict)

    # -----------------------------------------------------------------
    # Penalties
    #
    # These are intentionally separated to avoid mixing different
    # operational violations in a single Big-M parameter.
    # -----------------------------------------------------------------

    unmet_demand_penalty: dict[Key2, float] = field(default_factory=dict)
    emergency_static_capacity_penalty: dict[NodeId, float] = field(default_factory=dict)
    emergency_reception_capacity_penalty: dict[NodeId, float] = field(default_factory=dict)

    # -----------------------------------------------------------------
    # Optional metadata
    # -----------------------------------------------------------------

    node_info: dict[NodeId, NodeInfo] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    # -----------------------------------------------------------------
    # Convenience properties
    # -----------------------------------------------------------------

    @property
    def is_stochastic(self) -> bool:
        """Return True if stochastic scenarios are defined."""
        return bool(self.scenarios)

    @property
    def all_nodes(self) -> list[NodeId]:
        """Return all known nodes without duplicates, preserving order."""
        seen: set[NodeId] = set()
        nodes: list[NodeId] = []

        for group in (self.origins, self.warehouses, self.customers):
            for node in group:
                if node not in seen:
                    seen.add(node)
                    nodes.append(node)

        return nodes

    @property
    def investment_nodes(self) -> list[NodeId]:
        """Return warehouses where first-stage investment decisions may occur."""
        seen: set[NodeId] = set()
        nodes: list[NodeId] = []

        for group in (
            self.candidate_warehouses,
            self.existing_warehouses,
            self.bulk_eligible_warehouses,
        ):
            for node in group:
                if node not in seen:
                    seen.add(node)
                    nodes.append(node)

        return nodes

