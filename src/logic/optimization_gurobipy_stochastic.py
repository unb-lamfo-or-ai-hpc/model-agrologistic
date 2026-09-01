"""Two-stage stochastic extensive-form model for native gurobipy."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import OptimizationResult
from src.logic.optimization_gurobipy import (
    DEFAULT_PENALTY,
    VALUE_TOL,
    _active_warehouse_expr,
    _apply_solver_parameters,
    _effective_reception_capacity_expr,
    _effective_shipping_capacity_expr,
    _effective_static_capacity_expr,
    _expression_value,
    _import_gurobi,
    _infeasibility_metadata,
    _map_gurobi_status,
    _origin_to_customer_unit_cost,
    _origin_to_warehouse_unit_cost,
    _value,
    _warehouse_to_customer_unit_cost,
    _warehouse_to_warehouse_unit_cost,
)
from src.logic.route_filtering import select_routes


def solve_stochastic_model_gurobipy(
    data: ModelData,
    model_config: ModelConfig,
    solver_config: SolverConfig,
    *,
    fixed_first_stage: list[dict[str, Any]] | None = None,
) -> OptimizationResult:
    """Solve the risk-neutral two-stage extensive form."""

    gp, GRB = _import_gurobi()
    started_at = perf_counter()

    model = gp.Model("model_agrologistic_stochastic_extensive_form")
    _apply_solver_parameters(model, solver_config)

    scenarios = list(data.scenarios)
    routes = select_routes(data, model_config)
    od_keys = [
        (scenario, origin, warehouse, product, period)
        for scenario in scenarios
        for origin, warehouse, product in sorted(routes.od)
        for period in data.periods
    ]
    dc_keys = [
        (scenario, warehouse, customer, product, period)
        for scenario in scenarios
        for warehouse, customer, product in sorted(routes.dc)
        for period in data.periods
    ]
    oc_keys = [
        (scenario, origin, customer, product, period)
        for scenario in scenarios
        for origin, customer, product in sorted(routes.oc)
        for period in data.periods
        if model_config.use_direct_origin_customer
    ]
    dd_keys = [
        (scenario, warehouse_from, warehouse_to, product, period)
        for scenario in scenarios
        for warehouse_from, warehouse_to, product in sorted(routes.dd)
        for period in data.periods
        if model_config.use_warehouse_transshipment
    ]
    inventory_keys = [
        (scenario, warehouse, product, period)
        for scenario in scenarios
        for warehouse in data.warehouses
        for product in data.products
        for period in data.periods
    ]
    unmet_keys = [
        (scenario, customer, product, period)
        for scenario in scenarios
        for customer in data.domestic_customers
        for product in data.products
        for period in data.periods
    ]
    emergency_keys = [
        (scenario, warehouse, period)
        for scenario in scenarios
        for warehouse in data.warehouses
        for period in data.periods
    ]

    candidate_warehouses = list(data.candidate_warehouses)
    expansion_warehouses = [
        warehouse
        for warehouse in data.existing_warehouses
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

    # First-stage variables: one decision shared by every scenario.
    open_candidate = model.addVars(
        candidate_warehouses, vtype=GRB.BINARY, name="open_candidate"
    )
    candidate_capacity = model.addVars(
        candidate_warehouses,
        lb=0.0,
        vtype=GRB.CONTINUOUS,
        name="candidate_capacity",
    )
    expand_warehouse = model.addVars(
        expansion_warehouses, vtype=GRB.BINARY, name="expand_warehouse"
    )
    expand_capacity = model.addVars(
        expansion_warehouses,
        lb=0.0,
        vtype=GRB.CONTINUOUS,
        name="expand_capacity",
    )
    bulkify_warehouse = model.addVars(
        bulkification_warehouses, vtype=GRB.BINARY, name="bulkify_warehouse"
    )
    bulk_capacity = model.addVars(
        bulkification_warehouses,
        lb=0.0,
        vtype=GRB.CONTINUOUS,
        name="bulk_capacity",
    )

    # Second-stage variables: independent recourse for each scenario.
    flow_od = model.addVars(od_keys, lb=0.0, vtype=GRB.CONTINUOUS, name="flow_od")
    flow_dc = model.addVars(dc_keys, lb=0.0, vtype=GRB.CONTINUOUS, name="flow_dc")
    flow_oc = model.addVars(oc_keys, lb=0.0, vtype=GRB.CONTINUOUS, name="flow_oc")
    flow_dd = model.addVars(dd_keys, lb=0.0, vtype=GRB.CONTINUOUS, name="flow_dd")
    inventory = model.addVars(
        inventory_keys, lb=0.0, vtype=GRB.CONTINUOUS, name="inventory"
    )
    unmet_demand = model.addVars(
        unmet_keys,
        lb=0.0,
        ub=GRB.INFINITY if model_config.allow_unmet_domestic_demand else 0.0,
        vtype=GRB.CONTINUOUS,
        name="unmet_demand",
    )
    emergency_static_capacity = model.addVars(
        emergency_keys,
        lb=0.0,
        ub=(GRB.INFINITY if model_config.allow_emergency_static_capacity else 0.0),
        vtype=GRB.CONTINUOUS,
        name="emergency_static_capacity",
    )
    emergency_reception_capacity = model.addVars(
        emergency_keys,
        lb=0.0,
        ub=(
            GRB.INFINITY
            if model_config.allow_emergency_reception_capacity
            else 0.0
        ),
        vtype=GRB.CONTINUOUS,
        name="emergency_reception_capacity",
    )

    investment_costs = _build_investment_costs(
        gp=gp,
        data=data,
        model_config=model_config,
        candidate_warehouses=candidate_warehouses,
        expansion_warehouses=expansion_warehouses,
        bulkification_warehouses=bulkification_warehouses,
        open_candidate=open_candidate,
        candidate_capacity=candidate_capacity,
        expand_warehouse=expand_warehouse,
        expand_capacity=expand_capacity,
        bulkify_warehouse=bulkify_warehouse,
        bulk_capacity=bulk_capacity,
    )
    scenario_costs = _build_scenario_costs(
        gp=gp,
        data=data,
        scenarios=scenarios,
        od_keys=od_keys,
        dc_keys=dc_keys,
        oc_keys=oc_keys,
        dd_keys=dd_keys,
        inventory_keys=inventory_keys,
        unmet_keys=unmet_keys,
        emergency_keys=emergency_keys,
        flow_od=flow_od,
        flow_dc=flow_dc,
        flow_oc=flow_oc,
        flow_dd=flow_dd,
        inventory=inventory,
        unmet_demand=unmet_demand,
        emergency_static_capacity=emergency_static_capacity,
        emergency_reception_capacity=emergency_reception_capacity,
    )
    expected_costs = {
        component: gp.quicksum(
            data.scenario_prob[scenario] * scenario_costs[scenario][component]
            for scenario in scenarios
        )
        for component in next(iter(scenario_costs.values()))
    }
    model.setObjective(
        gp.quicksum(investment_costs.values())
        + gp.quicksum(expected_costs.values()),
        GRB.MINIMIZE,
    )

    _add_first_stage_constraints(
        model=model,
        data=data,
        model_config=model_config,
        candidate_warehouses=candidate_warehouses,
        expansion_warehouses=expansion_warehouses,
        bulkification_warehouses=bulkification_warehouses,
        open_candidate=open_candidate,
        candidate_capacity=candidate_capacity,
        expand_warehouse=expand_warehouse,
        expand_capacity=expand_capacity,
        bulkify_warehouse=bulkify_warehouse,
        bulk_capacity=bulk_capacity,
    )
    if fixed_first_stage is not None:
        _fix_first_stage_decisions(
            model=model,
            data=data,
            decisions=fixed_first_stage,
            open_candidate=open_candidate,
            candidate_capacity=candidate_capacity,
            expand_warehouse=expand_warehouse,
            expand_capacity=expand_capacity,
            bulkify_warehouse=bulkify_warehouse,
            bulk_capacity=bulk_capacity,
        )

    for scenario in scenarios:
        _add_scenario_constraints(
            gp=gp,
            model=model,
            data=data,
            model_config=model_config,
            scenario=scenario,
            flow_od=flow_od,
            flow_dc=flow_dc,
            flow_oc=flow_oc,
            flow_dd=flow_dd,
            inventory=inventory,
            unmet_demand=unmet_demand,
            emergency_static_capacity=emergency_static_capacity,
            emergency_reception_capacity=emergency_reception_capacity,
            open_candidate=open_candidate,
            candidate_capacity=candidate_capacity,
            expand_capacity=expand_capacity,
            bulk_capacity=bulk_capacity,
        )

    model.optimize()
    runtime_seconds = perf_counter() - started_at
    status = _map_gurobi_status(model, GRB)

    common_metadata = {
        "gurobi_status_code": model.Status,
        "solution_count": model.SolCount,
        "formulation": "two_stage_extensive_form",
        "scenario_probabilities": dict(data.scenario_prob),
        "first_stage_decisions": [
            "open_candidate",
            "candidate_capacity",
            "expand_warehouse",
            "expand_capacity",
            "bulkify_warehouse",
            "bulk_capacity",
        ],
        "first_stage_fixed": fixed_first_stage is not None,
        **_infeasibility_metadata(model, GRB, solver_config),
    }
    if model.SolCount == 0:
        return OptimizationResult(
            status=status,
            solver_backend="gurobipy",
            solver_name=solver_config.solver_name,
            model_mode=model_config.mode,
            runtime_seconds=runtime_seconds,
            metadata=common_metadata,
        )

    return _extract_stochastic_result(
        data=data,
        model_config=model_config,
        solver_config=solver_config,
        model=model,
        status=status,
        runtime_seconds=runtime_seconds,
        flow_od=flow_od,
        flow_dc=flow_dc,
        flow_oc=flow_oc,
        flow_dd=flow_dd,
        inventory=inventory,
        unmet_demand=unmet_demand,
        emergency_static_capacity=emergency_static_capacity,
        emergency_reception_capacity=emergency_reception_capacity,
        open_candidate=open_candidate,
        candidate_capacity=candidate_capacity,
        expand_warehouse=expand_warehouse,
        expand_capacity=expand_capacity,
        bulkify_warehouse=bulkify_warehouse,
        bulk_capacity=bulk_capacity,
        investment_costs=investment_costs,
        expected_costs=expected_costs,
        scenario_costs=scenario_costs,
        metadata=common_metadata,
    )


def _build_investment_costs(
    *,
    gp: Any,
    data: ModelData,
    model_config: ModelConfig,
    candidate_warehouses: list[str],
    expansion_warehouses: list[str],
    bulkification_warehouses: list[str],
    open_candidate: Any,
    candidate_capacity: Any,
    expand_warehouse: Any,
    expand_capacity: Any,
    bulkify_warehouse: Any,
    bulk_capacity: Any,
) -> dict[str, Any]:
    return {
        "opening": gp.quicksum(
            open_candidate[w] * data.opening_fixed_cost.get(w, 0.0)
            for w in candidate_warehouses
        ),
        "candidate_capacity": (
            gp.quicksum(
                candidate_capacity[w] * data.candidate_capacity_cost.get(w, 0.0)
                for w in candidate_warehouses
            )
            if model_config.candidate_capacity_mode == "scalable"
            else 0.0
        ),
        "expansion_fixed": gp.quicksum(
            expand_warehouse[w] * data.expand_fixed_cost.get(w, 0.0)
            for w in expansion_warehouses
        ),
        "expansion_variable": gp.quicksum(
            expand_capacity[w] * data.expand_variable_cost.get(w, 0.0)
            for w in expansion_warehouses
        ),
        "bulkification_fixed": gp.quicksum(
            bulkify_warehouse[w] * data.bulk_fixed_cost.get(w, 0.0)
            for w in bulkification_warehouses
        ),
        "bulkification_variable": gp.quicksum(
            bulk_capacity[w] * data.bulk_variable_cost.get(w, 0.0)
            for w in bulkification_warehouses
        ),
    }


def _build_scenario_costs(
    *,
    gp: Any,
    data: ModelData,
    scenarios: list[str],
    od_keys: list[tuple[str, ...]],
    dc_keys: list[tuple[str, ...]],
    oc_keys: list[tuple[str, ...]],
    dd_keys: list[tuple[str, ...]],
    inventory_keys: list[tuple[str, ...]],
    unmet_keys: list[tuple[str, ...]],
    emergency_keys: list[tuple[str, ...]],
    flow_od: Any,
    flow_dc: Any,
    flow_oc: Any,
    flow_dd: Any,
    inventory: Any,
    unmet_demand: Any,
    emergency_static_capacity: Any,
    emergency_reception_capacity: Any,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for scenario in scenarios:
        result[scenario] = {
            "transport_od": gp.quicksum(
                flow_od[key]
                * _origin_to_warehouse_unit_cost(data, key[1], key[2], key[3])
                for key in od_keys
                if key[0] == scenario
            ),
            "transport_dc": gp.quicksum(
                flow_dc[key]
                * _warehouse_to_customer_unit_cost(data, key[1], key[2], key[3])
                for key in dc_keys
                if key[0] == scenario
            ),
            "transport_oc": gp.quicksum(
                flow_oc[key]
                * _origin_to_customer_unit_cost(data, key[1], key[2], key[3])
                for key in oc_keys
                if key[0] == scenario
            ),
            "transport_dd": gp.quicksum(
                flow_dd[key]
                * _warehouse_to_warehouse_unit_cost(
                    data=data,
                    warehouse_from=key[1],
                    warehouse_to=key[2],
                    product=key[3],
                )
                for key in dd_keys
                if key[0] == scenario
            ),
            "storage": gp.quicksum(
                inventory[key] * data.storage_tariff.get((key[1], key[2]), 0.0)
                for key in inventory_keys
                if key[0] == scenario
            ),
            "unmet_demand": gp.quicksum(
                unmet_demand[key]
                * data.unmet_demand_penalty.get((key[1], key[2]), DEFAULT_PENALTY)
                for key in unmet_keys
                if key[0] == scenario
            ),
            "emergency_static": gp.quicksum(
                emergency_static_capacity[key]
                * data.emergency_static_capacity_penalty.get(key[1], DEFAULT_PENALTY)
                for key in emergency_keys
                if key[0] == scenario
            ),
            "emergency_reception": gp.quicksum(
                emergency_reception_capacity[key]
                * data.emergency_reception_capacity_penalty.get(
                    key[1], DEFAULT_PENALTY
                )
                for key in emergency_keys
                if key[0] == scenario
            ),
        }
    return result


def _add_first_stage_constraints(
    *,
    model: Any,
    data: ModelData,
    model_config: ModelConfig,
    candidate_warehouses: list[str],
    expansion_warehouses: list[str],
    bulkification_warehouses: list[str],
    open_candidate: Any,
    candidate_capacity: Any,
    expand_warehouse: Any,
    expand_capacity: Any,
    bulkify_warehouse: Any,
    bulk_capacity: Any,
) -> None:
    for warehouse in candidate_warehouses:
        maximum = data.max_candidate_capacity.get(warehouse, 0.0)
        if model_config.candidate_capacity_mode == "fixed":
            model.addConstr(
                candidate_capacity[warehouse] == maximum * open_candidate[warehouse],
                name=f"candidate_fixed_capacity[{warehouse}]",
            )
        else:
            model.addConstr(
                candidate_capacity[warehouse] <= maximum * open_candidate[warehouse],
                name=f"candidate_scalable_capacity[{warehouse}]",
            )

    for warehouse in expansion_warehouses:
        model.addConstr(
            expand_capacity[warehouse]
            <= data.max_expand_capacity[warehouse] * expand_warehouse[warehouse],
            name=f"expansion_capacity[{warehouse}]",
        )

    for warehouse in bulkification_warehouses:
        active = _active_warehouse_expr(data, open_candidate, warehouse)
        model.addConstr(
            bulk_capacity[warehouse]
            <= data.max_bulk_capacity[warehouse] * bulkify_warehouse[warehouse],
            name=f"bulkification_capacity[{warehouse}]",
        )
        model.addConstr(
            bulkify_warehouse[warehouse] <= active,
            name=f"bulkification_only_if_active[{warehouse}]",
        )


def _fix_first_stage_decisions(
    *,
    model: Any,
    data: ModelData,
    decisions: list[dict[str, Any]],
    open_candidate: Any,
    candidate_capacity: Any,
    expand_warehouse: Any,
    expand_capacity: Any,
    bulkify_warehouse: Any,
    bulk_capacity: Any,
) -> None:
    by_warehouse = {decision["warehouse"]: decision for decision in decisions}
    missing = sorted(set(data.warehouses) - set(by_warehouse))
    if missing:
        raise ValueError(
            "Fixed first-stage decisions are missing warehouses: "
            f"{missing}."
        )

    for warehouse in data.candidate_warehouses:
        decision = by_warehouse[warehouse]
        model.addConstr(
            open_candidate[warehouse] == round(float(decision["open"])),
            name=f"fix_open_candidate[{warehouse}]",
        )
        model.addConstr(
            candidate_capacity[warehouse]
            == float(decision["candidate_capacity"]),
            name=f"fix_candidate_capacity[{warehouse}]",
        )

    for warehouse in expand_capacity.keys():
        decision = by_warehouse[warehouse]
        model.addConstr(
            expand_warehouse[warehouse] == round(float(decision["expand"])),
            name=f"fix_expand_warehouse[{warehouse}]",
        )
        model.addConstr(
            expand_capacity[warehouse]
            == float(decision["expansion_capacity"]),
            name=f"fix_expand_capacity[{warehouse}]",
        )

    for warehouse in bulk_capacity.keys():
        decision = by_warehouse[warehouse]
        model.addConstr(
            bulkify_warehouse[warehouse] == round(float(decision["bulkify"])),
            name=f"fix_bulkify_warehouse[{warehouse}]",
        )
        model.addConstr(
            bulk_capacity[warehouse] == float(decision["bulk_capacity"]),
            name=f"fix_bulk_capacity[{warehouse}]",
        )


def _add_scenario_constraints(
    *,
    gp: Any,
    model: Any,
    data: ModelData,
    model_config: ModelConfig,
    scenario: str,
    flow_od: Any,
    flow_dc: Any,
    flow_oc: Any,
    flow_dd: Any,
    inventory: Any,
    unmet_demand: Any,
    emergency_static_capacity: Any,
    emergency_reception_capacity: Any,
    open_candidate: Any,
    candidate_capacity: Any,
    expand_capacity: Any,
    bulk_capacity: Any,
) -> None:
    for origin in data.origins:
        for product in data.products:
            for period in data.periods:
                model.addConstr(
                    flow_od.sum(scenario, origin, "*", product, period)
                    + flow_oc.sum(scenario, origin, "*", product, period)
                    == data.supply_s[scenario, origin, product, period],
                    name=f"supply_balance[{scenario},{origin},{product},{period}]",
                )

    for warehouse in data.warehouses:
        for product in data.products:
            for period_index, period in enumerate(data.periods):
                previous = (
                    data.initial_inventory.get((warehouse, product), 0.0)
                    if period_index == 0
                    else inventory[
                        scenario,
                        warehouse,
                        product,
                        data.periods[period_index - 1],
                    ]
                )
                inflow = (
                    flow_od.sum(scenario, "*", warehouse, product, period)
                    + flow_dd.sum(scenario, "*", warehouse, product, period)
                )
                outflow = (
                    flow_dc.sum(scenario, warehouse, "*", product, period)
                    + flow_dd.sum(scenario, warehouse, "*", product, period)
                )
                model.addConstr(
                    inventory[scenario, warehouse, product, period]
                    == previous + inflow - outflow,
                    name=f"inventory_balance[{scenario},{warehouse},{product},{period}]",
                )

    for customer in data.domestic_customers:
        for product in data.products:
            for period in data.periods:
                model.addConstr(
                    flow_dc.sum(scenario, "*", customer, product, period)
                    + flow_oc.sum(scenario, "*", customer, product, period)
                    + unmet_demand[scenario, customer, product, period]
                    == data.demand_dom_s[scenario, customer, product, period],
                    name=f"domestic_demand[{scenario},{customer},{product},{period}]",
                )

    for customer in data.export_customers:
        for product in data.products:
            for period in data.periods:
                model.addConstr(
                    flow_dc.sum(scenario, "*", customer, product, period)
                    + flow_oc.sum(scenario, "*", customer, product, period)
                    <= data.demand_exp_s[scenario, customer, product, period],
                    name=f"export_upper_bound[{scenario},{customer},{product},{period}]",
                )

    for warehouse in data.warehouses:
        active = _active_warehouse_expr(data, open_candidate, warehouse)
        for period in data.periods:
            static_capacity = _effective_static_capacity_expr(
                data,
                candidate_capacity,
                expand_capacity,
                bulk_capacity,
                warehouse,
            )
            model.addConstr(
                gp.quicksum(
                    inventory[scenario, warehouse, product, period]
                    for product in data.products
                )
                <= static_capacity
                + emergency_static_capacity[scenario, warehouse, period],
                name=f"static_capacity[{scenario},{warehouse},{period}]",
            )

            reception_capacity = _effective_reception_capacity_expr(
                data, model_config, candidate_capacity, warehouse
            )
            model.addConstr(
                gp.quicksum(
                    flow_od.sum(scenario, "*", warehouse, product, period)
                    + flow_dd.sum(scenario, "*", warehouse, product, period)
                    for product in data.products
                )
                <= reception_capacity
                + emergency_reception_capacity[scenario, warehouse, period],
                name=f"reception_capacity[{scenario},{warehouse},{period}]",
            )

            shipping_capacity = _effective_shipping_capacity_expr(
                data, model_config, candidate_capacity, warehouse
            )
            model.addConstr(
                gp.quicksum(
                    flow_dc.sum(scenario, warehouse, "*", product, period)
                    + flow_dd.sum(scenario, warehouse, "*", product, period)
                    for product in data.products
                )
                <= shipping_capacity,
                name=f"shipping_capacity[{scenario},{warehouse},{period}]",
            )

            big_m = _scenario_period_big_m(data, scenario, period)
            model.addConstr(
                emergency_static_capacity[scenario, warehouse, period]
                <= big_m * active,
                name=(
                    f"emergency_static_only_if_active[{scenario},{warehouse},{period}]"
                ),
            )
            model.addConstr(
                emergency_reception_capacity[scenario, warehouse, period]
                <= big_m * active,
                name=(
                    f"emergency_reception_only_if_active[{scenario},{warehouse},{period}]"
                ),
            )


def _scenario_period_big_m(data: ModelData, scenario: str, period: str) -> float:
    supply = sum(
        data.supply_s[scenario, origin, product, period]
        for origin in data.origins
        for product in data.products
    )
    demand = sum(
        data.demand_dom_s[scenario, customer, product, period]
        for customer in data.domestic_customers
        for product in data.products
    )
    initial = sum(
        data.initial_inventory.get((warehouse, product), 0.0)
        for warehouse in data.warehouses
        for product in data.products
    )
    return max(1.0, supply + initial, demand)


def _extract_stochastic_result(
    *,
    data: ModelData,
    model_config: ModelConfig,
    solver_config: SolverConfig,
    model: Any,
    status: str,
    runtime_seconds: float,
    flow_od: Any,
    flow_dc: Any,
    flow_oc: Any,
    flow_dd: Any,
    inventory: Any,
    unmet_demand: Any,
    emergency_static_capacity: Any,
    emergency_reception_capacity: Any,
    open_candidate: Any,
    candidate_capacity: Any,
    expand_warehouse: Any,
    expand_capacity: Any,
    bulkify_warehouse: Any,
    bulk_capacity: Any,
    investment_costs: dict[str, Any],
    expected_costs: dict[str, Any],
    scenario_costs: dict[str, dict[str, Any]],
    metadata: dict[str, Any],
) -> OptimizationResult:
    flows: list[dict[str, Any]] = []
    for scenario, origin, warehouse, product, period in flow_od.keys():
        value = _value(flow_od[scenario, origin, warehouse, product, period])
        if value > VALUE_TOL:
            flows.append(
                {
                    "scenario": scenario,
                    "route_type": "OD",
                    "origin": origin,
                    "warehouse": warehouse,
                    "customer": None,
                    "product": product,
                    "period": period,
                    "value": value,
                }
            )
    for scenario, warehouse, customer, product, period in flow_dc.keys():
        value = _value(flow_dc[scenario, warehouse, customer, product, period])
        if value > VALUE_TOL:
            flows.append(
                {
                    "scenario": scenario,
                    "route_type": "DC",
                    "origin": None,
                    "warehouse": warehouse,
                    "customer": customer,
                    "customer_type": (
                        "export" if customer in data.export_customers else "domestic"
                    ),
                    "product": product,
                    "period": period,
                    "value": value,
                }
            )
    for scenario, origin, customer, product, period in flow_oc.keys():
        value = _value(flow_oc[scenario, origin, customer, product, period])
        if value > VALUE_TOL:
            flows.append(
                {
                    "scenario": scenario,
                    "route_type": "OC",
                    "origin": origin,
                    "warehouse": None,
                    "customer": customer,
                    "customer_type": (
                        "export" if customer in data.export_customers else "domestic"
                    ),
                    "product": product,
                    "period": period,
                    "value": value,
                }
            )
    for scenario, warehouse_from, warehouse_to, product, period in flow_dd.keys():
        value = _value(
            flow_dd[scenario, warehouse_from, warehouse_to, product, period]
        )
        if value > VALUE_TOL:
            flows.append(
                {
                    "scenario": scenario,
                    "route_type": "DD",
                    "warehouse_from": warehouse_from,
                    "warehouse_to": warehouse_to,
                    "product": product,
                    "period": period,
                    "value": value,
                }
            )

    inventories = _extract_scenario_values(
        inventory,
        ("scenario", "warehouse", "product", "period"),
    )
    unmet_records = _extract_scenario_values(
        unmet_demand,
        ("scenario", "customer", "product", "period"),
    )
    emergency_records: list[dict[str, Any]] = []
    for capacity_type, variables in (
        ("static", emergency_static_capacity),
        ("reception", emergency_reception_capacity),
    ):
        for scenario, warehouse, period in variables.keys():
            value = _value(variables[scenario, warehouse, period])
            if value > VALUE_TOL:
                emergency_records.append(
                    {
                        "scenario": scenario,
                        "warehouse": warehouse,
                        "period": period,
                        "capacity_type": capacity_type,
                        "value": value,
                    }
                )

    warehouse_decisions = _extract_warehouse_decisions(
        data=data,
        open_candidate=open_candidate,
        candidate_capacity=candidate_capacity,
        expand_warehouse=expand_warehouse,
        expand_capacity=expand_capacity,
        bulkify_warehouse=bulkify_warehouse,
        bulk_capacity=bulk_capacity,
    )
    cost_breakdown = {
        **{name: _expression_value(expr) for name, expr in investment_costs.items()},
        **{name: _expression_value(expr) for name, expr in expected_costs.items()},
    }
    scenario_metrics: dict[str, dict[str, float]] = {}
    for scenario in data.scenarios:
        scenario_metrics[scenario] = {
            "probability": data.scenario_prob[scenario],
            "operating_cost": sum(
                _expression_value(expr)
                for expr in scenario_costs[scenario].values()
            ),
            "total_flow": sum(
                record["value"]
                for record in flows
                if record["scenario"] == scenario
            ),
            "total_unmet_demand": sum(
                record["value"]
                for record in unmet_records
                if record["scenario"] == scenario
            ),
            "total_emergency_capacity": sum(
                record["value"]
                for record in emergency_records
                if record["scenario"] == scenario
            ),
        }
    expected_operating_cost = sum(
        data.scenario_prob[scenario] * values["operating_cost"]
        for scenario, values in scenario_metrics.items()
    )
    investment_cost = sum(
        _expression_value(expression) for expression in investment_costs.values()
    )

    return OptimizationResult(
        status=status,
        objective_value=float(model.ObjVal),
        solver_backend="gurobipy",
        solver_name=solver_config.solver_name,
        model_mode=model_config.mode,
        runtime_seconds=runtime_seconds,
        mip_gap=getattr(model, "MIPGap", None),
        cost_breakdown=cost_breakdown,
        warehouse_decisions=warehouse_decisions,
        flows=flows,
        inventories=inventories,
        unmet_demand=unmet_records,
        emergency_capacity=emergency_records,
        metrics={
            "investment_cost": investment_cost,
            "expected_operating_cost": expected_operating_cost,
            "scenario_metrics": scenario_metrics,
        },
        metadata={
            **metadata,
            "candidate_capacity_mode": model_config.candidate_capacity_mode,
            "second_stage_decisions": [
                "flow_od",
                "flow_dc",
                "flow_oc",
                "flow_dd",
                "inventory",
                "unmet_demand",
                "emergency_static_capacity",
                "emergency_reception_capacity",
            ],
        },
    )


def _extract_scenario_values(
    variables: Any,
    fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for key in variables.keys():
        value = _value(variables[key])
        if value > VALUE_TOL:
            records.append({**dict(zip(fields, key)), "value": value})
    return records


def _extract_warehouse_decisions(
    *,
    data: ModelData,
    open_candidate: Any,
    candidate_capacity: Any,
    expand_warehouse: Any,
    expand_capacity: Any,
    bulkify_warehouse: Any,
    bulk_capacity: Any,
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for warehouse in data.warehouses:
        if warehouse in data.candidate_warehouses:
            open_value = _value(open_candidate[warehouse])
            candidate_value = _value(candidate_capacity[warehouse])
        else:
            open_value = 1.0 if warehouse in data.existing_warehouses else 0.0
            candidate_value = 0.0
        expand_value = (
            _value(expand_warehouse[warehouse]) if warehouse in expand_capacity else 0.0
        )
        expansion_value = (
            _value(expand_capacity[warehouse]) if warehouse in expand_capacity else 0.0
        )
        bulkify_value = (
            _value(bulkify_warehouse[warehouse]) if warehouse in bulk_capacity else 0.0
        )
        bulk_value = (
            _value(bulk_capacity[warehouse]) if warehouse in bulk_capacity else 0.0
        )
        decisions.append(
            {
                "warehouse": warehouse,
                "is_existing": warehouse in data.existing_warehouses,
                "is_candidate": warehouse in data.candidate_warehouses,
                "open": open_value,
                "candidate_capacity": candidate_value,
                "expand": expand_value,
                "expansion_capacity": expansion_value,
                "bulkify": bulkify_value,
                "bulk_capacity": bulk_value,
                "static_capacity": data.static_capacity.get(warehouse, 0.0),
                "effective_static_capacity": (
                    data.static_capacity.get(warehouse, 0.0)
                    + candidate_value
                    + expansion_value
                    + bulk_value
                ),
            }
        )
    return decisions

