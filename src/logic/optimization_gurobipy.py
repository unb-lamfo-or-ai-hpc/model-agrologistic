"""
Native gurobipy backend for agricultural logistics optimization.

Current implementation:
- deterministic MILP core;
- origin -> warehouse flows;
- direct origin -> customer flows;
- warehouse -> domestic/export customer flows;
- warehouse -> warehouse transshipment flows;
- inventory balance;
- existing and candidate warehouse capacities;
- candidate opening and scalable/fixed candidate capacity;
- scalable expansion of existing warehouse static capacity;
- scalable bulkification of eligible warehouse static capacity;
- unmet domestic demand;
- export demand upper bounds;
- emergency static capacity;
- emergency reception capacity.

EVPI/VSS analysis is implemented in stochastic_analysis_gurobipy.py.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any

from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import (
    OptimizationResult,
    configure_gurobi_wls_license,
)
from src.logic.route_filtering import select_routes

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

    if model_config.mode == "sto":
        from src.logic.optimization_gurobipy_stochastic import (
            solve_stochastic_model_gurobipy,
        )

        return solve_stochastic_model_gurobipy(
            data=data,
            model_config=model_config,
            solver_config=solver_config,
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

    routes = select_routes(data, model_config)

    od_keys = [
        (origin, warehouse, product, period)
        for origin, warehouse, product in sorted(routes.od)
        for period in data.periods
    ]

    dc_keys = [
        (warehouse, customer, product, period)
        for warehouse, customer, product in sorted(routes.dc)
        for period in data.periods
    ]

    oc_keys = [
        (origin, customer, product, period)
        for origin, customer, product in sorted(routes.oc)
        for period in data.periods
        if model_config.use_direct_origin_customer
    ]

    dd_keys = [
        (warehouse_from, warehouse_to, product, period)
        for warehouse_from, warehouse_to, product in sorted(routes.dd)
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
    expansion_warehouses = [
        warehouse
        for warehouse in data.warehouses
        if model_config.allow_capacity_expansion
        and data.max_expand_capacity.get(warehouse, 0.0) > 0.0
    ]
    bulkification_warehouses = [
        warehouse
        for warehouse in data.bulk_eligible_warehouses
        if model_config.allow_bulkification
        and warehouse in data.warehouses
        and data.max_bulk_capacity.get(warehouse, 0.0) > 0.0
    ]

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

    flow_oc = model.addVars(
        oc_keys,
        lb=0.0,
        vtype=GRB.CONTINUOUS,
        name="flow_oc",
    )

    flow_dd = model.addVars(
        dd_keys,
        lb=0.0,
        vtype=GRB.CONTINUOUS,
        name="flow_dd",
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

    expand_warehouse = model.addVars(
        expansion_warehouses,
        vtype=GRB.BINARY,
        name="expand_warehouse",
    )

    expand_capacity = model.addVars(
        expansion_warehouses,
        lb=0.0,
        vtype=GRB.CONTINUOUS,
        name="expand_capacity",
    )

    bulkify_warehouse = model.addVars(
        bulkification_warehouses,
        vtype=GRB.BINARY,
        name="bulkify_warehouse",
    )

    bulk_capacity = model.addVars(
        bulkification_warehouses,
        lb=0.0,
        vtype=GRB.CONTINUOUS,
        name="bulk_capacity",
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

    transport_oc_cost = gp.quicksum(
        flow_oc[origin, customer, product, period]
        * _origin_to_customer_unit_cost(data, origin, customer, product)
        for origin, customer, product, period in oc_keys
    )

    transport_dd_cost = gp.quicksum(
        flow_dd[warehouse_from, warehouse_to, product, period]
        * _warehouse_to_warehouse_unit_cost(
            data=data,
            warehouse_from=warehouse_from,
            warehouse_to=warehouse_to,
            product=product,
            model_config=model_config,
        )
        for warehouse_from, warehouse_to, product, period in dd_keys
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

    expansion_fixed_cost = gp.quicksum(
        expand_warehouse[warehouse] * data.expand_fixed_cost.get(warehouse, 0.0)
        for warehouse in expansion_warehouses
    )

    expansion_variable_cost = gp.quicksum(
        expand_capacity[warehouse]
        * data.expand_variable_cost.get(warehouse, 0.0)
        for warehouse in expansion_warehouses
    )

    bulkification_fixed_cost = gp.quicksum(
        bulkify_warehouse[warehouse]
        * data.bulk_fixed_cost.get(warehouse, 0.0)
        for warehouse in bulkification_warehouses
    )

    bulkification_variable_cost = gp.quicksum(
        bulk_capacity[warehouse]
        * data.bulk_variable_cost.get(warehouse, 0.0)
        for warehouse in bulkification_warehouses
    )

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

    economic_cost = (
        transport_od_cost
        + transport_dc_cost
        + transport_oc_cost
        + transport_dd_cost
        + storage_cost
        + opening_cost
        + candidate_capacity_cost
        + expansion_fixed_cost
        + expansion_variable_cost
        + bulkification_fixed_cost
        + bulkification_variable_cost
    )
    penalized_cost = (
        economic_cost
        + unmet_demand_cost
        + emergency_static_cost
        + emergency_reception_cost
    )
    unmet_quantity = gp.quicksum(unmet_demand[key] for key in unmet_keys)
    emergency_quantity = gp.quicksum(
        emergency_static_capacity[key] + emergency_reception_capacity[key]
        for key in emergency_keys
    )
    _set_objective_policy(
        model=model,
        GRB=GRB,
        config=model_config,
        penalized_cost=penalized_cost,
        unmet_quantity=unmet_quantity,
        emergency_quantity=emergency_quantity,
        economic_cost=economic_cost,
    )

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
    # Existing warehouse expansion constraints
    # ------------------------------------------------------------------

    for warehouse in expansion_warehouses:
        active = _active_warehouse_expr(
            data=data,
            open_candidate=open_candidate,
            warehouse=warehouse,
        )
        model.addConstr(
            expand_capacity[warehouse]
            <= data.max_expand_capacity[warehouse] * expand_warehouse[warehouse],
            name=f"expansion_capacity[{warehouse}]",
        )
        model.addConstr(
            expand_warehouse[warehouse] <= active,
            name=f"expansion_only_if_active[{warehouse}]",
        )

    # ------------------------------------------------------------------
    # Eligible warehouse bulkification constraints
    # ------------------------------------------------------------------

    for warehouse in bulkification_warehouses:
        active = _active_warehouse_expr(
            data=data,
            open_candidate=open_candidate,
            warehouse=warehouse,
        )
        model.addConstr(
            bulk_capacity[warehouse]
            <= data.max_bulk_capacity[warehouse] * bulkify_warehouse[warehouse],
            name=f"bulkification_capacity[{warehouse}]",
        )
        model.addConstr(
            bulkify_warehouse[warehouse] <= active,
            name=f"bulkification_only_if_active[{warehouse}]",
        )

    for warehouse in sorted(
        set(expansion_warehouses) & set(bulkification_warehouses)
    ):
        active = _active_warehouse_expr(
            data=data,
            open_candidate=open_candidate,
            warehouse=warehouse,
        )
        model.addConstr(
            expand_warehouse[warehouse] + bulkify_warehouse[warehouse] <= active,
            name=f"expansion_bulkification_exclusion[{warehouse}]",
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
                    flow_od.sum(origin, "*", product, period)
                    + flow_oc.sum(origin, "*", product, period)
                    == rhs,
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

                inflow = (
                    flow_od.sum("*", warehouse, product, period)
                    + flow_dd.sum("*", warehouse, product, period)
                )
                outflow = (
                    flow_dc.sum(warehouse, "*", product, period)
                    + flow_dd.sum(warehouse, "*", product, period)
                )

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
                    + flow_oc.sum("*", customer, product, period)
                    + unmet_demand[customer, product, period]
                    == rhs,
                    name=f"domestic_demand[{customer},{product},{period}]",
                )

    # ------------------------------------------------------------------
    # Export demand upper bounds
    #
    # Export markets are not mandatory demand nodes. They act as finite,
    # non-binding upper bounds used to represent an external market.
    # ------------------------------------------------------------------

    for customer in data.export_customers:
        for product in data.products:
            for period in data.periods:
                rhs = data.demand_exp.get((customer, product, period), 0.0)

                model.addConstr(
                    flow_dc.sum("*", customer, product, period)
                    + flow_oc.sum("*", customer, product, period)
                    <= rhs,
                    name=f"export_upper_bound[{customer},{product},{period}]",
                )

    # ------------------------------------------------------------------
    # Warehouse capacities
    # ------------------------------------------------------------------

    for warehouse in data.warehouses:
        for period in data.periods:
            static_capacity = _effective_static_capacity_expr(
                data=data,
                model_config=model_config,
                candidate_capacity=candidate_capacity,
                expand_capacity=expand_capacity,
                bulk_capacity=bulk_capacity,
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
                expand_capacity=expand_capacity,
                bulk_capacity=bulk_capacity,
                warehouse=warehouse,
                period=period,
            )

            model.addConstr(
                gp.quicksum(
                    flow_od.sum("*", warehouse, product, period)
                    + flow_dd.sum("*", warehouse, product, period)
                    for product in data.products
                )
                <= reception_capacity + emergency_reception_capacity[warehouse, period],
                name=f"reception_capacity[{warehouse},{period}]",
            )

            shipping_capacity = _effective_shipping_capacity_expr(
                data=data,
                model_config=model_config,
                candidate_capacity=candidate_capacity,
                expand_capacity=expand_capacity,
                bulk_capacity=bulk_capacity,
                warehouse=warehouse,
                period=period,
            )

            model.addConstr(
                gp.quicksum(
                    flow_dc.sum(warehouse, "*", product, period)
                    + flow_dd.sum(warehouse, "*", product, period)
                    for product in data.products
                )
                <= shipping_capacity,
                name=f"shipping_capacity[{warehouse},{period}]",
            )

    # ------------------------------------------------------------------
    # Emergency capacity must be tied to active candidate infrastructure.
    #
    # Emergency slacks are unbounded feasibility devices at active facilities.
    # Indicators prevent closed candidates from acting as ghost warehouses.
    # ------------------------------------------------------------------

    for warehouse in data.candidate_warehouses:
        for period in data.periods:
            model.addGenConstrIndicator(
                open_candidate[warehouse],
                False,
                emergency_static_capacity[warehouse, period] == 0.0,
                name=f"emergency_static_only_if_active[{warehouse},{period}]",
            )
            model.addGenConstrIndicator(
                open_candidate[warehouse],
                False,
                emergency_reception_capacity[warehouse, period] == 0.0,
                name=f"emergency_reception_only_if_active[{warehouse},{period}]",
            )

    # ------------------------------------------------------------------
    # Solve
    # ------------------------------------------------------------------

    model_build_seconds = perf_counter() - started_at
    optimization_started_at = perf_counter()
    model.optimize()
    optimization_seconds = perf_counter() - optimization_started_at

    runtime_seconds = perf_counter() - started_at
    status = _map_gurobi_status(model, GRB)

    if model.SolCount == 0:
        infeasibility = _infeasibility_metadata(model, GRB, solver_config)
        return OptimizationResult(
            status=status,
            solver_backend="gurobipy",
            solver_name=solver_config.solver_name,
            model_mode=model_config.mode,
            runtime_seconds=runtime_seconds,
            metadata={
                "gurobi_status_code": model.Status,
                "gurobi_status_name": _gurobi_status_name(model, GRB),
                "solution_count": model.SolCount,
                "objective_policy": model_config.objective_policy,
                "timings": {
                    "model_build_seconds": model_build_seconds,
                    "optimization_seconds": optimization_seconds,
                },
                **infeasibility,
            },
        )

    return _extract_deterministic_result(
        data=data,
        model_config=model_config,
        solver_config=solver_config,
        model=model,
        status=status,
        gurobi_status_name=_gurobi_status_name(model, GRB),
        runtime_seconds=runtime_seconds,
        model_build_seconds=model_build_seconds,
        optimization_seconds=optimization_seconds,
        flow_od=flow_od,
        flow_dc=flow_dc,
        flow_oc=flow_oc,
        flow_dd=flow_dd,
        inventory=inventory,
        open_candidate=open_candidate,
        candidate_capacity=candidate_capacity,
        expand_warehouse=expand_warehouse,
        expand_capacity=expand_capacity,
        bulkify_warehouse=bulkify_warehouse,
        bulk_capacity=bulk_capacity,
        unmet_demand=unmet_demand,
        emergency_static_capacity=emergency_static_capacity,
        emergency_reception_capacity=emergency_reception_capacity,
        cost_components={
            "transport_od": transport_od_cost,
            "transport_dc": transport_dc_cost,
            "transport_oc": transport_oc_cost,
            "transport_dd": transport_dd_cost,
            "storage": storage_cost,
            "opening": opening_cost,
            "candidate_capacity": candidate_capacity_cost,
            "expansion_fixed": expansion_fixed_cost,
            "expansion_variable": expansion_variable_cost,
            "bulkification_fixed": bulkification_fixed_cost,
            "bulkification_variable": bulkification_variable_cost,
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


def _set_objective_policy(
    *,
    model: Any,
    GRB: Any,
    config: ModelConfig,
    penalized_cost: Any,
    unmet_quantity: Any,
    emergency_quantity: Any,
    economic_cost: Any,
) -> None:
    """Configure the weighted or hierarchical service objective."""

    if config.objective_policy == "penalty":
        model.setObjective(penalized_cost, GRB.MINIMIZE)
        return

    model.ModelSense = GRB.MINIMIZE
    tolerance = config.feasibility_tolerance
    model.setObjectiveN(
        emergency_quantity,
        index=0,
        priority=3,
        weight=1.0,
        abstol=tolerance,
        reltol=0.0,
        name="minimize_emergency_capacity",
    )
    model.setObjectiveN(
        unmet_quantity,
        index=1,
        priority=2,
        weight=1.0,
        abstol=tolerance,
        reltol=0.0,
        name="minimize_unmet_demand",
    )
    model.setObjectiveN(
        economic_cost,
        index=2,
        priority=1,
        weight=1.0,
        abstol=0.0,
        reltol=0.0,
        name="minimize_economic_cost",
    )


def _infeasibility_metadata(
    model: Any,
    GRB: Any,
    solver_config: SolverConfig,
) -> dict[str, Any]:
    """Compute a bounded IIS diagnostic when explicitly requested."""

    if model.Status != GRB.INFEASIBLE or not solver_config.compute_iis:
        return {}

    started_at = perf_counter()
    try:
        model.computeIIS()
        constraint_names = [
            constraint.ConstrName
            for constraint in model.getConstrs()
            if constraint.IISConstr
        ]
        bound_names = [
            f"{variable.VarName}:{bound}"
            for variable in model.getVars()
            for bound, included in (
                ("lower", variable.IISLB),
                ("upper", variable.IISUB),
            )
            if included
        ]
        limit = solver_config.iis_max_items
        return {
            "iis_computed": True,
            "iis_minimal": bool(model.IISMinimal),
            "iis_runtime_seconds": perf_counter() - started_at,
            "iis_constraint_count": len(constraint_names),
            "iis_bound_count": len(bound_names),
            "iis_constraints": constraint_names[:limit],
            "iis_bounds": bound_names[:limit],
            "iis_truncated": (
                len(constraint_names) > limit or len(bound_names) > limit
            ),
        }
    except Exception as error:
        return {
            "iis_computed": False,
            "iis_error_type": type(error).__name__,
            "iis_error_message": str(error),
            "iis_runtime_seconds": perf_counter() - started_at,
        }


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


def _gurobi_status_name(model: Any, GRB: Any) -> str:
    """Return the symbolic Gurobi termination status for diagnostics."""

    names = (
        "LOADED",
        "OPTIMAL",
        "INFEASIBLE",
        "INF_OR_UNBD",
        "UNBOUNDED",
        "CUTOFF",
        "ITERATION_LIMIT",
        "NODE_LIMIT",
        "TIME_LIMIT",
        "SOLUTION_LIMIT",
        "INTERRUPTED",
        "NUMERIC",
        "SUBOPTIMAL",
        "INPROGRESS",
        "USER_OBJ_LIMIT",
        "WORK_LIMIT",
        "MEM_LIMIT",
        "LOCALLY_OPTIMAL",
        "LOCALLY_INFEASIBLE",
    )
    return next(
        (
            name
            for name in names
            if getattr(GRB, name, object()) == model.Status
        ),
        f"UNKNOWN_{model.Status}",
    )


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
    model_config: ModelConfig,
    candidate_capacity: Any,
    expand_capacity: Any,
    bulk_capacity: Any,
    warehouse: str,
) -> Any:
    capacity = data.static_capacity.get(warehouse, 0.0)

    if warehouse in data.candidate_warehouses:
        capacity = capacity + candidate_capacity[warehouse]

    if warehouse in expand_capacity:
        capacity = capacity + expand_capacity[warehouse]

    if (
        model_config.capacity_coupling_policy == "period_equivalent"
        and warehouse in bulk_capacity
    ):
        capacity = capacity + bulk_capacity[warehouse]

    return capacity


def _effective_reception_capacity_expr(
    data: ModelData,
    model_config: ModelConfig,
    candidate_capacity: Any,
    expand_capacity: Any,
    bulk_capacity: Any,
    warehouse: str,
    period: str,
) -> Any:
    capacity = (
        data.reception_capacity.get(warehouse, 0.0)
        * model_config.operating_days(period)
    )

    if model_config.capacity_coupling_policy == "period_equivalent":
        # Preserve the established MVP interpretation for all existing runs.
        if warehouse in data.candidate_warehouses:
            capacity = capacity + candidate_capacity[warehouse]
        return capacity

    days = model_config.operating_days(period)
    if warehouse in data.candidate_warehouses:
        capacity += (
            candidate_capacity[warehouse]
            * model_config.candidate_reception_daily_factor
            * days
        )
    if warehouse in expand_capacity:
        capacity += (
            expand_capacity[warehouse]
            * model_config.expansion_reception_daily_factor
            * days
        )
    if warehouse in bulk_capacity:
        capacity += (
            bulk_capacity[warehouse]
            * model_config.bulkification_reception_daily_factor
            * days
        )

    return capacity


def _effective_shipping_capacity_expr(
    data: ModelData,
    model_config: ModelConfig,
    candidate_capacity: Any,
    expand_capacity: Any,
    bulk_capacity: Any,
    warehouse: str,
    period: str,
) -> Any:
    capacity = (
        data.shipping_capacity.get(warehouse, 0.0)
        * model_config.operating_days(period)
    )

    if model_config.capacity_coupling_policy == "period_equivalent":
        # Preserve the established MVP interpretation for all existing runs.
        if warehouse in data.candidate_warehouses:
            capacity = capacity + candidate_capacity[warehouse]
        return capacity

    days = model_config.operating_days(period)
    if warehouse in data.candidate_warehouses:
        capacity += (
            candidate_capacity[warehouse]
            * model_config.candidate_shipping_daily_factor
            * days
        )
    if warehouse in expand_capacity:
        capacity += (
            expand_capacity[warehouse]
            * model_config.expansion_shipping_daily_factor
            * days
        )
    if warehouse in bulk_capacity:
        capacity += (
            bulk_capacity[warehouse]
            * model_config.bulkification_shipping_daily_factor
            * days
        )

    return capacity


def _period_big_m(data: ModelData, period: str) -> float:
    """Return a safe per-period bound for throughput slacks."""

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


def _cumulative_inventory_big_m(data: ModelData, period: str) -> float:
    """Return an inventory bound that respects accumulation over time.

    Inventory can carry all supply received in earlier periods. Bounding an
    emergency storage slack by only the current period's supply can therefore
    make a valid multi-period instance infeasible. Demand is omitted because
    it cannot increase warehouse inventory.
    """

    period_index = data.periods.index(period)
    elapsed_periods = data.periods[: period_index + 1]
    cumulative_supply = sum(
        data.supply.get((origin, product, elapsed_period), 0.0)
        for origin in data.origins
        for product in data.products
        for elapsed_period in elapsed_periods
    )
    initial_inventory = sum(
        data.initial_inventory.get((warehouse, product), 0.0)
        for warehouse in data.warehouses
        for product in data.products
    )

    return max(1.0, cumulative_supply + initial_inventory)


def _origin_to_warehouse_unit_cost(
    data: ModelData,
    origin: str,
    warehouse: str,
    product: str,
) -> float:
    del product

    distance = data.dist_od.get((origin, warehouse), 0.0)
    freight = data.freight_origin.get(origin, 0.0)

    receiving_handling_cost = data.transshipment_cost.get(warehouse, 0.0)

    return distance * freight + receiving_handling_cost


def _warehouse_to_customer_unit_cost(
    data: ModelData,
    warehouse: str,
    customer: str,
    product: str,
) -> float:
    del product

    distance = data.dist_dc.get((warehouse, customer), 0.0)
    freight = data.freight_warehouse.get(warehouse, 0.0)

    return distance * freight


def _origin_to_customer_unit_cost(
    data: ModelData,
    origin: str,
    customer: str,
    product: str,
) -> float:
    del product

    distance = data.dist_oc.get((origin, customer), 0.0)
    freight = data.freight_origin.get(origin, 0.0)

    return distance * freight


def _warehouse_to_warehouse_unit_cost(
    data: ModelData,
    warehouse_from: str,
    warehouse_to: str,
    product: str,
    model_config: ModelConfig,
) -> float:
    del product

    distance = data.dist_dd.get((warehouse_from, warehouse_to), 0.0)

    freight = data.freight_warehouse[warehouse_from]

    interhub_factor = model_config.interhub_factor
    receiving_handling_cost = data.transshipment_cost.get(warehouse_to, 0.0)

    return interhub_factor * distance * freight + receiving_handling_cost


# ---------------------------------------------------------------------
# Result extraction
# ---------------------------------------------------------------------


def _extract_deterministic_result(
    data: ModelData,
    model_config: ModelConfig,
    solver_config: SolverConfig,
    model: Any,
    status: str,
    gurobi_status_name: str,
    runtime_seconds: float,
    model_build_seconds: float,
    optimization_seconds: float,
    flow_od: Any,
    flow_dc: Any,
    flow_oc: Any,
    flow_dd: Any,
    inventory: Any,
    open_candidate: Any,
    candidate_capacity: Any,
    expand_warehouse: Any,
    expand_capacity: Any,
    bulkify_warehouse: Any,
    bulk_capacity: Any,
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
                    "customer_type": (
                        "export"
                        if customer in data.export_customers
                        else "domestic"
                    ),
                    "product": product,
                    "period": period,
                    "value": value,
                }
            )

    for origin, customer, product, period in flow_oc.keys():
        value = _value(flow_oc[origin, customer, product, period])
        if value > VALUE_TOL:
            flows.append(
                {
                    "route_type": "OC",
                    "origin": origin,
                    "warehouse": None,
                    "customer": customer,
                    "customer_type": (
                        "export"
                        if customer in data.export_customers
                        else "domestic"
                    ),
                    "product": product,
                    "period": period,
                    "value": value,
                }
            )

    for warehouse_from, warehouse_to, product, period in flow_dd.keys():
        value = _value(flow_dd[warehouse_from, warehouse_to, product, period])
        if value > VALUE_TOL:
            flows.append(
                {
                    "route_type": "DD",
                    "warehouse_from": warehouse_from,
                    "warehouse_to": warehouse_to,
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

        if warehouse in expand_capacity:
            expand_value = _value(expand_warehouse[warehouse])
            expansion_capacity_value = _value(expand_capacity[warehouse])
        else:
            expand_value = 0.0
            expansion_capacity_value = 0.0

        if warehouse in bulk_capacity:
            bulkify_value = _value(bulkify_warehouse[warehouse])
            bulk_capacity_value = _value(bulk_capacity[warehouse])
        else:
            bulkify_value = 0.0
            bulk_capacity_value = 0.0

        warehouse_decisions.append(
            {
                "warehouse": warehouse,
                "is_existing": warehouse in data.existing_warehouses,
                "is_candidate": warehouse in data.candidate_warehouses,
                "open": open_value,
                "candidate_capacity": candidate_capacity_value,
                "expand": expand_value,
                "expansion_capacity": expansion_capacity_value,
                "bulkify": bulkify_value,
                "bulk_capacity": bulk_capacity_value,
                "static_capacity": data.static_capacity.get(warehouse, 0.0),
                "effective_static_capacity": (
                    data.static_capacity.get(warehouse, 0.0)
                    + candidate_capacity_value
                    + expansion_capacity_value
                    + (
                        bulk_capacity_value
                        if model_config.capacity_coupling_policy
                        == "period_equivalent"
                        else 0.0
                    )
                ),
            }
        )

    cost_breakdown = {
        name: _expression_value(expression)
        for name, expression in cost_components.items()
    }
    economic_cost_value = sum(
        value
        for name, value in cost_breakdown.items()
        if name not in {"unmet_demand", "emergency_static", "emergency_reception"}
    )
    penalized_cost_value = sum(cost_breakdown.values())
    unmet_quantity_value = sum(record["value"] for record in unmet_records)
    emergency_quantity_value = sum(
        record["value"] for record in emergency_records
    )
    objective_values = {
        "unmet_demand": unmet_quantity_value,
        "emergency_capacity": emergency_quantity_value,
        "economic_cost": economic_cost_value,
        "penalized_cost": penalized_cost_value,
    }

    metrics = {
        "total_flow": sum(record["value"] for record in flows),
        "total_unmet_demand": unmet_quantity_value,
        "total_emergency_capacity": emergency_quantity_value,
        "objective_values": objective_values,
    }

    mip_gap = getattr(model, "MIPGap", None)

    return OptimizationResult(
        status=status,
        objective_value=(
            penalized_cost_value
            if model_config.objective_policy == "penalty"
            else emergency_quantity_value
        ),
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
            "gurobi_status_name": gurobi_status_name,
            "solution_count": model.SolCount,
            "timings": {
                "model_build_seconds": model_build_seconds,
                "optimization_seconds": optimization_seconds,
            },
            "candidate_capacity_mode": model_config.candidate_capacity_mode,
            "objective_policy": model_config.objective_policy,
            "objective_priority_order": (
                ["penalized_cost"]
                if model_config.objective_policy == "penalty"
                else [
                    "emergency_capacity",
                    "unmet_demand",
                    "economic_cost",
                ]
            ),
            "allow_capacity_expansion": model_config.allow_capacity_expansion,
            "allow_bulkification": model_config.allow_bulkification,
            "capacity_coupling_policy": model_config.capacity_coupling_policy,
            "interhub_factor": model_config.interhub_factor,
            "capacity_coupling_daily_factors": {
                "candidate_reception": model_config.candidate_reception_daily_factor,
                "candidate_shipping": model_config.candidate_shipping_daily_factor,
                "expansion_reception": model_config.expansion_reception_daily_factor,
                "expansion_shipping": model_config.expansion_shipping_daily_factor,
                "bulkification_reception": (
                    model_config.bulkification_reception_daily_factor
                ),
                "bulkification_shipping": (
                    model_config.bulkification_shipping_daily_factor
                ),
            },
        },
    )


def _value(variable: Any) -> float:
    return float(variable.X)


def _expression_value(expression: Any) -> float:
    if isinstance(expression, int | float):
        return float(expression)

    return float(expression.getValue())
