from src.logic.model_data import ModelData
from src.logic.optimization_gurobipy import (
    _cumulative_inventory_big_m,
    _period_big_m,
)
from src.logic.optimization_gurobipy_stochastic import (
    _scenario_cumulative_inventory_big_m,
    _scenario_period_big_m,
)


def multi_period_data() -> ModelData:
    return ModelData(
        origins=["O1"],
        warehouses=["W1"],
        existing_warehouses=["W1"],
        candidate_warehouses=[],
        bulk_eligible_warehouses=[],
        customers=["C1"],
        domestic_customers=["C1"],
        export_customers=[],
        products=["soy"],
        periods=["t1", "t2", "t3"],
        supply={
            ("O1", "soy", "t1"): 100.0,
            ("O1", "soy", "t2"): 20.0,
            ("O1", "soy", "t3"): 5.0,
        },
        demand_dom={
            ("C1", "soy", "t1"): 0.0,
            ("C1", "soy", "t2"): 50.0,
            ("C1", "soy", "t3"): 0.0,
        },
        scenarios=["low", "high"],
        scenario_prob={"low": 0.5, "high": 0.5},
        supply_s={
            ("low", "O1", "soy", "t1"): 10.0,
            ("low", "O1", "soy", "t2"): 2.0,
            ("low", "O1", "soy", "t3"): 1.0,
            ("high", "O1", "soy", "t1"): 200.0,
            ("high", "O1", "soy", "t2"): 40.0,
            ("high", "O1", "soy", "t3"): 10.0,
        },
        demand_dom_s={
            (scenario, "C1", "soy", period): 0.0
            for scenario in ("low", "high")
            for period in ("t1", "t2", "t3")
        },
        initial_inventory={("W1", "soy"): 7.0},
    )


def test_deterministic_static_big_m_accumulates_prior_supply():
    data = multi_period_data()

    assert _period_big_m(data, "t3") == 12.0
    assert _cumulative_inventory_big_m(data, "t3") == 132.0


def test_stochastic_static_big_m_is_scenario_specific_and_cumulative():
    data = multi_period_data()

    assert _scenario_period_big_m(data, "high", "t3") == 17.0
    assert _scenario_cumulative_inventory_big_m(data, "low", "t3") == 20.0
    assert _scenario_cumulative_inventory_big_m(data, "high", "t3") == 257.0

