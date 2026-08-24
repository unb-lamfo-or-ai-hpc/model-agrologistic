"""
Native gurobipy backend for agricultural logistics optimization.

Current implementation:
- deterministic MILP core;
- origin -> warehouse flows;
- warehouse -> domestic customer flows;
- inventory balance;
- existing and candidate warehouse capacities;
- candidate opening and scalable/fixed candidate capacity;
- unmet domestic demand;
- emergency static capacity;
- emergency reception capacity.

Not implemented yet:
- stochastic formulation;
- warehouse-to-warehouse transshipment;
- direct origin-to-customer flow;
- export demand;
- expansion;
- bulkification;
- EVPI/VSS.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any

from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import (
    OptimizationBackendNotImplementedError,
    OptimizationResult,
    configure_gurobi_wls_license,
)


DEFAULT_PENALTY = 1_000_000.0
VALUE_TOL = 1e-7


def solve_model_gurobipy(
    data: ModelData,
    model_config: ModelConfig,
    solver_config: SolverConfig,
) -> OptimizationResult:
    """
    Solve the agricultural logistics model using native gurobipy.
    """

    configure_gurobi_wls_license(solver_config)

    if model_config.mode != "det":
        raise OptimizationBackendNotImplementedError(
            "The native gurobipy backend currently supports only "
            "ModelConfig(mode='det'). The stochastic model will be implemented later."
        )

    if data.routes_dd:
        raise OptimizationBackendNotImplementedError(
            "Warehouse-to-warehouse transshipment routes are not implemented yet."
        )

    if model_config.use_direct_origin_customer or data.routes_oc:
        raise OptimizationBackendNotImplementedError(
            "Direct origin-to-customer routes are not implemented yet."
        )

    if data.demand_exp:
        raise OptimizationBackendNotImplementedError(
            "Export demand constraints are not implemented yet."
        )

    return _solve_deterministic_core(
        data=data,
        model_config=model_config,
        solver_config=solver_config,
    )


def _solve_deterministic_core(
    data: ModelData,
    model_config: ModelConfig,
    solver_config: SolverConfig,
) -> OptimizationResult:
    gp, GRB = _import_gurobi()

    started_at = perf_counter()

    model = gp.Model("model_agrologistic_deterministic")
    _apply_solver_parameters(model, solver_config)

    # ------------------------------------------------------------------
    # Index sets
    # ------------------------------------------------------------------

    od_keys = [
        (origin, warehouse, product, period)
        for origin, warehouse, product in sorted(data.routes_od)
        for period in data.periods
    ]

    dc_keys = [
        (warehouse, customer, product, period)
        for warehouse, customer, product in sorted(data.routes_dc)
        for period in data.periods
    ]

    inventory_keys = [
        (warehouse, product, period)
        for warehouse in data.warehouses
        for product in data.products
        for period in data.periods
    ]

    unmet_keys = [
        (customer, product, period)
        for customer in data.domestic_customers
        for product in data.products
        for period in data.periods
    ]

    emergency_keys = [
        (warehouse, period)
        for warehouse in data.warehouses
        for period in data.periods
    ]

    candidate_warehouses = list(data.candidate_warehouses)

    # ------------------------------------------------------------------
    # Variables
    # ------------------------------------------------------------------

    flow_od = model.addVars(
        od_keys,
        lb=0.0,
        vtype=GRB.CONTINUOUS,
        name="flow_od",
    )

    flow_dc = model.addVars(
        dc_keys,
        lb=0.0,
        vtype=GRB.CONTINUOUS,
        name="flow_dc",
    )

    inventory = model.addVars(
        inventory_keys,
        lb=0.0,
        vtype=GRB.CONTINUOUS,
        name="inventory",
    )

    open_candidate = model.addVars(
        candidate_warehouses,
        vtype=GRB.BINARY,
        name="open_candidate",
    )

    candidate_capacity = model.addVars(
        candidate_warehouses,
        lb=0.0,
        vtype=GRB.CONTINUOUS,
        name="candidate_capacity",
    )

    unmet_ub = GRB.INFINITY if model_config.allow_unmet_domestic_demand else 0.0

    unmet_demand = model.addVars(
        unmet_keys,
        lb=0.0,
        ub=unmet_ub,
        vtype=GRB.CONTINUOUS,
        name="unmet_demand",
    )

    emergency_static_ub = (
        GRB.INFINITY if model_config.allow_emergency_static_capacity else 0.0
    )
    emergency_reception_ub = (
        GRB.INFINITY if model_config.allow_emergency_reception_capacity else 0.0
    )

    emergency_static_capacity = model.addVars(
        emergency_keys,
        lb=0.0,
        ub=emergency_static_ub,
        vtype=GRB.CONTINUOUS,
        name="emergency_static_capacity",
    )

    emergency_reception_capacity = model.addVars(
        emergency_keys,
        lb=0.0,
        ub=emergency_reception_ub,
        vtype=GRB.CONTINUOUS,
        name="emergency_reception_capacity",
    )

    # ------------------------------------------------------------------
    # Objective
    # ------------------------------------------------------------------

    transport_od_cost = gp.quicksum(
        flow_od[origin, warehouse, product, period]
        * _origin_to_warehouse_unit_cost(data, origin, warehouse, product)
        for origin, warehouse, product, period in od_keys
    )

    transport_dc_cost = gp.quicksum(
        flow_dc[warehouse, customer, product, period]
        * _warehouse_to_customer_unit_cost(data, warehouse, customer, product)
        for warehouse, customer, product, period in dc_keys
    )

    storage_cost = gp.quicksum(
        inventory[warehouse, product, period]
        * data.storage_tariff.get((warehouse, product), 0.0)
        for warehouse, product, period in inventory_keys
    )

    opening_cost = gp.quicksum(
        open_candidate[warehouse] * data.opening_fixed_cost.get(warehouse, 0.0)
        for warehouse in candidate_warehouses
    )

    if model_config.candidate_capacity_mode == "scalable":
        candidate_capacity_cost = gp.quicksum(
            candidate_capacity[warehouse]
            * data.candidate_capacity_cost.get(warehouse, 0.0)
            for warehouse in candidate_warehouses
        )
    else:
        candidate_capacity_cost = 0.0

    unmet_demand_cost = gp.quicksum(
        unmet_demand[customer, product, period]
        * data.unmet_demand_penalty.get((customer, product), DEFAULT_PENALTY)
        for customer, product, period in unmet_keys
    )

    emergency_static_cost = gp.quicksum(
        emergency_static_capacity[warehouse, period]
        * data.emergency_static_capacity_penalty.get(warehouse, DEFAULT_PENALTY)
        for warehouse, period in emergency_keys
    )

    emergency_reception_cost = gp.quicksum(
        emergency_reception_capacity[warehouse, period]
        * data.emergency_reception_capacity_penalty.get(warehouse, DEFAULT_PENALTY)
        for warehouse, period in emergency_keys
    )

    objective = (
        transport_od_cost
        + transport_dc_cost
        + storage_cost
        + opening_cost
        + candidate_capacity_cost
        + unmet_demand_cost
        + emergency_static_cost
        + emergency_reception_cost
    )

    model.setObjective(objective, GRB.MINIMIZE)

    # ------------------------------------------------------------------
    # Candidate capacity constraints
    # ------------------------------------------------------------------

    for warehouse in candidate_warehouses:
        max_capacity = data.max_candidate_capacity.get(warehouse, 0.0)

        if model_config.candidate_capacity_mode == "fixed":
            model.addConstr(
                candidate_capacity[warehouse]
                == max_capacity * open_candidate[warehouse],
                name=f"candidate_fixed_capacity[{warehouse}]",
            )
        else:
            model.addConstr(
                candidate_capacity[warehouse]
                <= max_capacity * open_candidate[warehouse],
                name=f"candidate_scalable_capacity[{warehouse}]",
            )

    # ------------------------------------------------------------------
    # Supply balance
    #
    # Critical rule:
    # Do not skip zero supply. If supply is zero, the equality forces
    # outgoing flow to zero.
    # ------------------------------------------------------------------

    for origin in data.origins:
        for product in data.products:
            for period in data.periods:
                rhs = data.supply.get((origin, product, period), 0.0)

                model.addConstr(
                    flow_od.sum(origin, "*", product, period) == rhs,
                    name=f"supply_balance[{origin},{product},{period}]",
                )

    # ------------------------------------------------------------------
    # Inventory balance
    # ------------------------------------------------------------------

    for warehouse in data.warehouses:
        for product in data.products:
            for period_index, period in enumerate(data.periods):
                previous_inventory = (
                    data.initial_inventory.get((warehouse, product), 0.0)
                    if period_index == 0
                    else inventory[warehouse, product, data.periods[period_index - 1]]
                )

                inflow = flow_od.sum("*", warehouse, product, period)
                outflow = flow_dc.sum(warehouse, "*", product, period)

                model.addConstr(
                    inventory[warehouse, product, period]
                    == previous_inventory + inflow - outflow,
                    name=f"inventory_balance[{warehouse},{product},{period}]",
                )

    # ------------------------------------------------------------------
    # Domestic demand balance
    #
    # Critical rule:
    # Do not skip zero demand. If demand is zero, the equality forces
    # incoming flow plus unmet demand to zero.
    # ------------------------------------------------------------------

    for customer in data.domestic_customers:
        for product in data.products:
            for period in data.periods:
                rhs = data.demand_dom.get((customer, product, period), 0.0)

                model.addConstr(
                    flow_dc.sum("*", customer, product, period)
                    + unmet_demand[customer, product, period]
                    == rhs,
                    name=f"domestic_demand[{customer},{product},{period}]",
                )

    # ------------------------------------------------------------------
    # Warehouse capacities
    # ------------------------------------------------------------------

    for warehouse in data.warehouses:
        for period in data.periods:
            static_capacity = _effective_static_capacity_expr(
                data=data,
                candidate_capacity=candidate_capacity,
                warehouse=warehouse,
            )

            model.addConstr(
                gp.quicksum(
                    inventory[warehouse, product, period]
                    for product in data.products
                )
                <= static_capacity + emergency_static_capacity[warehouse, period],
                name=f"static_capacity[{warehouse},{period}]",
            )

            reception_capacity = _effective_reception_capacity_expr(
                data=data,
                model_config=model_config,
                candidate_capacity=candidate_capacity,
                warehouse=warehouse,
            )

            model.addConstr(
                gp.quicksum(
                    flow_od[origin, warehouse, product, period]
                    for origin, route_warehouse, product in data.routes_od
                    if route_warehouse == warehouse
                )
                <= reception_capacity + emergency_reception_capacity[warehouse, period],
                name=f"reception_capacity[{warehouse},{period}]",
            )

            shipping_capacity = _effective_shipping_capacity_expr(
                data=data,
                model_config=model_config,
                candidate_capacity=candidate_capacity,
                warehouse=warehouse,
            )

            model.addConstr(
                gp.quicksum(
                    flow_dc[warehouse, customer, product, period]
                    for route_warehouse, customer, product in data.routes_dc
                    if route_warehouse == warehouse
                )
                <= shipping_capacity,
                name=f"shipping_capacity[{warehouse},{period}]",
            )

    # ------------------------------------------------------------------
    # Emergency capacity must be tied to active infrastructure
    #
    # Critical rule:
    # A closed candidate warehouse cannot use emergency capacity.
    # ------------------------------------------------------------------

    for warehouse in data.warehouses:
        active = _active_warehouse_expr(
            data=data,
            open_candidate=open_candidate,
            warehouse=warehouse,
        )

        for period in data.periods:
            big_m = _period_big_m(data, period)

            model.addConstr(
                emergency_static_capacity[warehouse, period] <= big_m * active,
                name=f"emergency_static_only_if_active[{warehouse},{period}]",
            )

            model.addConstr(
                emergency_reception_capacity[warehouse, period] <= big_m * active,
                name=f"emergency_reception_only_if_active[{warehouse},{period}]",
            )

    # ------------------------------------------------------------------
    # Solve
    # ------------------------------------------------------------------

    model.optimize()

    runtime_seconds = perf_counter() - started_at
    status = _map_gurobi_status(model, GRB)

    if model.SolCount == 0:
        return OptimizationResult(
            status=status,
            solver_backend="gurobipy",
            solver_name=solver_config.solver_name,
            model_mode=model_config.mode,
            runtime_seconds=runtime_seconds,
            metadata={
                "gurobi_status_code": model.Status,
                "solution_count": model.SolCount,
            },
        )

    return _extract_deterministic_result(
        data=data,
        model_config=model_config,
        solver_config=solver_config,
        model=model,
        status=status,
        runtime_seconds=runtime_seconds,
        flow_od=flow_od,
        flow_dc=flow_dc,
        inventory=inventory,
        open_candidate=open_candidate,
        candidate_capacity=candidate_capacity,
        unmet_demand=unmet_demand,
        emergency_static_capacity=emergency_static_capacity,
        emergency_reception_capacity=emergency_reception_capacity,
        cost_components={
            "transport_od": transport_od_cost,
            "transport_dc": transport_dc_cost,
            "storage": storage_cost,
            "opening": opening_cost,
            "candidate_capacity": candidate_capacity_cost,
            "unmet_demand": unmet_demand_cost,
            "emergency_static": emergency_static_cost,
            "emergency_reception": emergency_reception_cost,
        },
    )


# ---------------------------------------------------------------------
# Gurobi utilities
# ---------------------------------------------------------------------


def _import_gurobi() -> tuple[Any, Any]:
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except ImportError as exc:
        raise RuntimeError(
            "gurobipy is not installed. Install it with: "
            "pip install 'gurobipy>=13.0.2,<14'"
        ) from exc

    return gp, GRB


def _apply_solver_parameters(model: Any, solver_config: SolverConfig) -> None:
    model.Params.OutputFlag = 1 if solver_config.tee else 0

    if solver_config.time_limit is not None:
        model.Params.TimeLimit = solver_config.time_limit

    model.Params.MIPGap = solver_config.mip_gap

    if solver_config.threads is not None:
        model.Params.Threads = solver_config.threads

    if solver_config.seed is not None:
        model.Params.Seed = solver_config.seed

    if solver_config.log_file:
        model.Params.LogFile = solver_config.log_file

    ignored_options = {
        "license_file",
        "GRB_LICENSE_FILE",
    }

    for option_name, option_value in solver_config.solver_options.items():
        if option_name in ignored_options:
            continue
        model.setParam(option_name, option_value)


def _map_gurobi_status(model: Any, GRB: Any) -> str:
    if model.Status == GRB.OPTIMAL:
        return "optimal"

    if model.Status == GRB.INFEASIBLE:
        return "infeasible"

    if model.Status == GRB.UNBOUNDED:
        return "unbounded"

    if model.Status == GRB.TIME_LIMIT:
        return "time_limit"

    if model.SolCount > 0:
        return "feasible"

    return "error"


# ---------------------------------------------------------------------
# Model expression helpers
# ---------------------------------------------------------------------


def _active_warehouse_expr(
    data: ModelData,
    open_candidate: Any,
    warehouse: str,
) -> Any:
    if warehouse in data.existing_warehouses:
        return 1.0

    if warehouse in data.candidate_warehouses:
        return open_candidate[warehouse]

    return 0.0


def _effective_static_capacity_expr(
    data: ModelData,
    candidate_capacity: Any,
    warehouse: str,
) -> Any:
    capacity = data.static_capacity.get(warehouse, 0.0)

    if warehouse in data.candidate_warehouses:
        capacity = capacity + candidate_capacity[warehouse]

    return capacity


def _effective_reception_capacity_expr(
    data: ModelData,
    model_config: ModelConfig,
    candidate_capacity: Any,
    warehouse: str,
) -> Any:
    capacity = data.reception_capacity.get(warehouse, 0.0) * model_config.days_per_period

    # Minimal deterministic core assumption:
    # for candidate facilities, the chosen static capacity is also used as
    # an aggregate per-period reception bound.
    if warehouse in data.candidate_warehouses:
        capacity = capacity + candidate_capacity[warehouse]

    return capacity


def _effective_shipping_capacity_expr(
    data: ModelData,
    model_config: ModelConfig,
    candidate_capacity: Any,
    warehouse: str,
) -> Any:
    capacity = data.shipping_capacity.get(warehouse, 0.0) * model_config.days_per_period

    # Minimal deterministic core assumption:
    # for candidate facilities, the chosen static capacity is also used as
    # an aggregate per-period shipping bound.
    if warehouse in data.candidate_warehouses:
        capacity = capacity + candidate_capacity[warehouse]

    return capacity


def _period_big_m(data: ModelData, period: str) -> float:
    supply = sum(
        data.supply.get((origin, product, period), 0.0)
        for origin in data.origins
        for product in data.products
    )

    demand = sum(
        data.demand_dom.get((customer, product, period), 0.0)
        for customer in data.domestic_customers
        for product in data.products
    )

    initial_inventory = sum(
        data.initial_inventory.get((warehouse, product), 0.0)
        for warehouse in data.warehouses
        for product in data.products
    )

    return max(1.0, supply + initial_inventory, demand)


def _origin_to_warehouse_unit_cost(
    data: ModelData,
    origin: str,
    warehouse: str,
    product: str,
) -> float:
    del product

    distance = data.dist_od.get((origin, warehouse), 0.0)
    freight = data.freight_origin.get(origin, 0.0)

    return distance * freight


def _warehouse_to_customer_unit_cost(
    data: ModelData,
    warehouse: str,
    customer: str,
    product: str,
) -> float:
    del warehouse, product

    distance = data.dist_dc.get((warehouse, customer), 0.0)
    freight = data.freight_dest.get(customer, 0.0)

    return distance * freight


# ---------------------------------------------------------------------
# Result extraction
# ---------------------------------------------------------------------


def _extract_deterministic_result(
    data: ModelData,
    model_config: ModelConfig,
    solver_config: SolverConfig,
    model: Any,
    status: str,
    runtime_seconds: float,
    flow_od: Any,
    flow_dc: Any,
    inventory: Any,
    open_candidate: Any,
    candidate_capacity: Any,
    unmet_demand: Any,
    emergency_static_capacity: Any,
    emergency_reception_capacity: Any,
    cost_components: dict[str, Any],
) -> OptimizationResult:
    flows: list[dict[str, Any]] = []

    for origin, warehouse, product, period in flow_od.keys():
        value = _value(flow_od[origin, warehouse, product, period])
        if value > VALUE_TOL:
            flows.append(
                {
                    "route_type": "OD",
                    "origin": origin,
                    "warehouse": warehouse,
                    "customer": None,
                    "product": product,
                    "period": period,
                    "value": value,
                }
            )

    for warehouse, customer, product, period in flow_dc.keys():
        value = _value(flow_dc[warehouse, customer, product, period])
        if value > VALUE_TOL:
            flows.append(
                {
                    "route_type": "DC",
                    "origin": None,
                    "warehouse": warehouse,
                    "customer": customer,
                    "product": product,
                    "period": period,
                    "value": value,
                }
            )

    inventories: list[dict[str, Any]] = []

    for warehouse, product, period in inventory.keys():
        value = _value(inventory[warehouse, product, period])
        if value > VALUE_TOL:
            inventories.append(
                {
                    "warehouse": warehouse,
                    "product": product,
                    "period": period,
                    "value": value,
                }
            )

    unmet_records: list[dict[str, Any]] = []

    for customer, product, period in unmet_demand.keys():
        value = _value(unmet_demand[customer, product, period])
        if value > VALUE_TOL:
            unmet_records.append(
                {
                    "customer": customer,
                    "product": product,
                    "period": period,
                    "value": value,
                }
            )

    emergency_records: list[dict[str, Any]] = []

    for warehouse, period in emergency_static_capacity.keys():
        value = _value(emergency_static_capacity[warehouse, period])
        if value > VALUE_TOL:
            emergency_records.append(
                {
                    "warehouse": warehouse,
                    "period": period,
                    "capacity_type": "static",
                    "value": value,
                }
            )

    for warehouse, period in emergency_reception_capacity.keys():
        value = _value(emergency_reception_capacity[warehouse, period])
        if value > VALUE_TOL:
            emergency_records.append(
                {
                    "warehouse": warehouse,
                    "period": period,
                    "capacity_type": "reception",
                    "value": value,
                }
            )

    warehouse_decisions: list[dict[str, Any]] = []

    for warehouse in data.warehouses:
        if warehouse in data.candidate_warehouses:
            open_value = _value(open_candidate[warehouse])
            candidate_capacity_value = _value(candidate_capacity[warehouse])
        else:
            open_value = 1.0 if warehouse in data.existing_warehouses else 0.0
            candidate_capacity_value = 0.0

        warehouse_decisions.append(
            {
                "warehouse": warehouse,
                "is_existing": warehouse in data.existing_warehouses,
                "is_candidate": warehouse in data.candidate_warehouses,
                "open": open_value,
                "candidate_capacity": candidate_capacity_value,
                "static_capacity": data.static_capacity.get(warehouse, 0.0),
                "effective_static_capacity": (
                    data.static_capacity.get(warehouse, 0.0)
                    + candidate_capacity_value
                ),
            }
        )

    cost_breakdown = {
        name: _expression_value(expression)
        for name, expression in cost_components.items()
    }

    metrics = {
        "total_flow": sum(record["value"] for record in flows),
        "total_unmet_demand": sum(record["value"] for record in unmet_records),
        "total_emergency_capacity": sum(record["value"] for record in emergency_records),
    }

    mip_gap = getattr(model, "MIPGap", None)

    return OptimizationResult(
        status=status,
        objective_value=float(model.ObjVal),
        solver_backend="gurobipy",
        solver_name=solver_config.solver_name,
        model_mode=model_config.mode,
        runtime_seconds=runtime_seconds,
        mip_gap=mip_gap,
        cost_breakdown=cost_breakdown,
        warehouse_decisions=warehouse_decisions,
        flows=flows,
        inventories=inventories,
        unmet_demand=unmet_records,
        emergency_capacity=emergency_records,
        metrics=metrics,
        metadata={
            "gurobi_status_code": model.Status,
            "solution_count": model.SolCount,
            "candidate_capacity_mode": model_config.candidate_capacity_mode,
        },
    )


def _value(variable: Any) -> float:
    return float(variable.X)


def _expression_value(expression: Any) -> float:
    if isinstance(expression, (int, float)):
        return float(expression)

    return float(expression.getValue())