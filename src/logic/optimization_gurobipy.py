from __future__ import annotations

from time import perf_counter
from typing import Any

from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData

DEFAULT_PENALTY = 1_000_000.0
VALUE_TOL = 1e-7


def _finite_attribute(model, name):
    from math import isfinite

    try:
        value = float(getattr(model, name))
        return value if isfinite(value) else None
    except (AttributeError, RuntimeError):
        return None


def solve_model_gurobipy(data, model_config, solver_config):
    """Use one extensive-form builder for DET and STO, with one scalar solve."""
    from src.logic.mathematical_contract import extensive_form_inputs
    from src.logic.optimization import configure_gurobi_wls_license, project_deterministic_result
    from src.logic.optimization_gurobipy_stochastic import solve_stochastic_model_gurobipy

    configure_gurobi_wls_license(solver_config)
    prepared, config = extensive_form_inputs(data, model_config)
    result = solve_stochastic_model_gurobipy(prepared, config, solver_config)
    return project_deterministic_result(result) if model_config.mode == "det" else result


def _solve_deterministic_core(data, model_config, solver_config):
    """Compatibility entry point; no second mathematical implementation."""
    if model_config.mode != "det":
        raise ValueError("Deterministic entry point requires mode='det'.")
    return solve_model_gurobipy(data, model_config, solver_config)


def _optimize_scalar(model, GRB, *, native_phase_hook=None):
    """One native call; preserve phase seams and objective-independent telemetry."""
    from src.logic.resource_telemetry import CURRENT, gurobi_message, observed_matrix, phase

    observed_matrix(model, "gurobipy")
    if native_phase_hook is not None:
        native_phase_hook("native_ready", model, GRB)
    phase("optimization")
    if native_phase_hook is not None:
        native_phase_hook("optimization", model, GRB)
    session = CURRENT.get()
    started = perf_counter()
    progress = {"time_to_first_incumbent_seconds": None}

    def observe(native_model, where):
        if where == GRB.Callback.MIPSOL and progress["time_to_first_incumbent_seconds"] is None:
            progress["time_to_first_incumbent_seconds"] = perf_counter() - started
        gurobi_message(native_model, where, GRB.Callback, session)

    model.optimize(observe)
    if native_phase_hook is not None:
        native_phase_hook("export_validation", model, GRB)
    return progress


def _import_gurobi() -> tuple[Any, Any]:
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except ImportError as exc:
        raise RuntimeError(
            "gurobipy is not installed. Install it with: pip install 'gurobipy>=13.0.2,<14'"
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
            constraint.ConstrName for constraint in model.getConstrs() if constraint.IISConstr
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
            "iis_truncated": (len(constraint_names) > limit or len(bound_names) > limit),
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
        (name for name in names if getattr(GRB, name, object()) == model.Status),
        f"UNKNOWN_{model.Status}",
    )


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

    if model_config.capacity_coupling_policy == "period_equivalent" and warehouse in bulk_capacity:
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
    capacity = data.reception_capacity.get(warehouse, 0.0) * model_config.operating_days(period)

    if model_config.capacity_coupling_policy == "period_equivalent":
        # Preserve the established MVP interpretation for all existing runs.
        if warehouse in data.candidate_warehouses:
            capacity = capacity + candidate_capacity[warehouse]
        return capacity

    days = model_config.operating_days(period)
    if warehouse in data.candidate_warehouses:
        capacity += (
            candidate_capacity[warehouse] * model_config.candidate_reception_daily_factor * days
        )
    if warehouse in expand_capacity:
        capacity += (
            expand_capacity[warehouse] * model_config.expansion_reception_daily_factor * days
        )
    if warehouse in bulk_capacity:
        capacity += (
            bulk_capacity[warehouse] * model_config.bulkification_reception_daily_factor * days
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
    capacity = data.shipping_capacity.get(warehouse, 0.0) * model_config.operating_days(period)

    if model_config.capacity_coupling_policy == "period_equivalent":
        # Preserve the established MVP interpretation for all existing runs.
        if warehouse in data.candidate_warehouses:
            capacity = capacity + candidate_capacity[warehouse]
        return capacity

    days = model_config.operating_days(period)
    if warehouse in data.candidate_warehouses:
        capacity += (
            candidate_capacity[warehouse] * model_config.candidate_shipping_daily_factor * days
        )
    if warehouse in expand_capacity:
        capacity += expand_capacity[warehouse] * model_config.expansion_shipping_daily_factor * days
    if warehouse in bulk_capacity:
        capacity += (
            bulk_capacity[warehouse] * model_config.bulkification_shipping_daily_factor * days
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


def _value(variable: Any) -> float:
    return float(variable.X)


def _expression_value(expression: Any) -> float:
    if isinstance(expression, int | float):
        return float(expression)

    return float(expression.getValue())
