from dataclasses import replace

import pytest

from src.logic.mathematical_contract import prepare_model_data
from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization_gurobipy import (
    _effective_reception_capacity_expr,
    _solve_deterministic_core,
)
from src.logic.optimization_gurobipy_stochastic import solve_stochastic_model_gurobipy
from src.logic.route_filtering import select_routes
from src.logic.stochastic_analysis_gurobipy import _single_scenario_data
from tests.test_gurobipy_transshipment import require_gurobi_available


def tiny_data():
    return ModelData(
        origins=["O"], warehouses=["W"], existing_warehouses=["W"],
        candidate_warehouses=[], bulk_eligible_warehouses=[],
        customers=["C"], domestic_customers=["C"], export_customers=[],
        products=["P"], periods=["t"],
        routes_od={("O", "W", "P")}, routes_dc={("W", "C", "P")},
        dist_od={("O", "W"): 1.0}, dist_dc={("W", "C"): 1.0},
        supply={("O", "P", "t"): 3030.0},
        demand_dom={("C", "P", "t"): 3030.0},
        static_capacity={"W": 0.0}, reception_capacity={"W": 100.0},
        shipping_capacity={"W": 1000.0},
        freight_origin={"O": 1.0}, freight_warehouse={"W": 1.0},
        unmet_demand_penalty={("C", "P"): 10000.0},
        emergency_static_capacity_penalty={"W": 100.0},
        emergency_reception_capacity_penalty={"W": 100.0},
    )


@pytest.mark.parametrize("policy", ["zero", "target", "penalized"])
def test_unsupported_terminal_policy_fails_before_solver(policy):
    with pytest.raises(ValueError, match="terminal_inventory_policy"):
        prepare_model_data(tiny_data(), ModelConfig(terminal_inventory_policy=policy))


def test_penalties_use_selected_routes_not_discarded_long_routes():
    data = tiny_data()
    data.customers.append("FAR")
    data.domestic_customers.append("FAR")
    data.routes_dc.add(("W", "FAR", "P"))
    data.dist_dc["W", "FAR"] = 10000.0
    data.metadata["penalty_policy"] = "thesis_dynamic"
    config = ModelConfig(route_filter_strategy="thesis_pareto", pareto_fraction=0.2)
    prepared = prepare_model_data(data, config)
    assert prepared.unmet_demand_penalty["FAR", "P"] == 10000.0
    assert prepared.metadata["mathematical_contract"]["penalty_scope"].startswith("selected_routes")
    assert "_frozen_routes" not in data.metadata
    assert select_routes(prepared, config).dc == {("W", "C", "P")}


def test_scenario_projections_keep_identical_routes_and_penalties():
    data = tiny_data()
    data.scenarios = ["s"]
    data.scenario_prob = {"s": 1.0}
    data.supply_s = {("s", *key): value for key, value in data.supply.items()}
    data.demand_dom_s = {("s", *key): value for key, value in data.demand_dom.items()}
    config = ModelConfig(mode="sto", route_filter_strategy="connectivity_preserving_pareto")
    prepared = prepare_model_data(data, config)
    projected = _single_scenario_data(prepared, "s")
    assert prepare_model_data(projected, replace(config, mode="det")) is projected
    assert select_routes(prepared, config) == select_routes(projected, replace(config, mode="det"))
    with pytest.raises(ValueError, match="different route policy"):
        prepare_model_data(prepared, replace(config, pareto_fraction=0.25))


@pytest.mark.parametrize("days,overflow", [(28, 230.0), (30, 30.0), (31, 0.0)])
def test_daily_conversion_precedes_the_period_slack_without_a_license(days, overflow):
    data = tiny_data()
    capacity = _effective_reception_capacity_expr(
        data, ModelConfig(days_per_period=days), {}, {}, {}, "W", "t"
    )
    assert max(0.0, 3030.0 - capacity) == overflow
    assert capacity == 100.0 * days


@pytest.mark.parametrize("days,expected", [(28, 230.0), (30, 30.0), (31, 0.0)])
@pytest.mark.parametrize("mode", ["det", "sto"])
def test_reception_slack_is_period_overflow_in_both_backends(days, expected, mode):
    require_gurobi_available()
    data = tiny_data()
    config = ModelConfig(mode=mode, days_per_period_by_period={"t": days})
    solver = SolverConfig(mip_gap=0.0, threads=1, time_limit=30)
    if mode == "sto":
        data.scenarios = ["s"]
        data.scenario_prob = {"s": 1.0}
        data.supply_s = {("s", *key): value for key, value in data.supply.items()}
        data.demand_dom_s = {("s", *key): value for key, value in data.demand_dom.items()}
        result = solve_stochastic_model_gurobipy(data, config, solver)
    else:
        result = _solve_deterministic_core(data, config, solver)
    overflow = sum(
        r["value"] for r in result.emergency_capacity if r["capacity_type"] == "reception"
    )
    assert overflow == pytest.approx(expected, abs=1e-5)
    assert overflow / days == pytest.approx(expected / days, abs=1e-5)


def test_shared_and_separate_slacks_are_not_cost_equivalent():
    require_gurobi_available()
    import gurobipy as gp

    values = []
    for shared in (True, False):
        with gp.Model() as model:
            model.Params.OutputFlag = 0
            stock = model.addVar(lb=100.0)
            reception = stock if shared else model.addVar(lb=80.0)
            model.addConstr(reception >= 80.0)
            model.setObjective(7.0 * (stock if shared else stock + reception))
            model.optimize()
            values.append(model.ObjVal)
    assert values == pytest.approx([700.0, 1260.0])
