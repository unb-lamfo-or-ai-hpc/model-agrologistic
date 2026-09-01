from src.logic.capacity_bounds import (
    deterministic_inventory_bounds,
    stochastic_inventory_bounds,
)
from src.logic.model_data import ModelData
from src.logic.route_filtering import SelectedRoutes


def bounded_network_data() -> ModelData:
    return ModelData(
        origins=["O1", "O2"],
        warehouses=["W1", "W2", "W3"],
        existing_warehouses=["W1", "W2", "W3"],
        candidate_warehouses=[],
        bulk_eligible_warehouses=[],
        customers=[],
        domestic_customers=[],
        export_customers=[],
        products=["soy"],
        periods=["t1", "t2"],
        supply={
            ("O1", "soy", "t1"): 10.0,
            ("O1", "soy", "t2"): 20.0,
            ("O2", "soy", "t1"): 1000.0,
            ("O2", "soy", "t2"): 2000.0,
        },
        scenarios=["base"],
        scenario_prob={"base": 1.0},
        supply_s={
            ("base", "O1", "soy", "t1"): 15.0,
            ("base", "O1", "soy", "t2"): 30.0,
            ("base", "O2", "soy", "t1"): 1500.0,
            ("base", "O2", "soy", "t2"): 3000.0,
        },
        initial_inventory={
            ("W1", "soy"): 5.0,
            ("W2", "soy"): 7.0,
            ("W3", "soy"): 11.0,
        },
    )


def selected_network() -> SelectedRoutes:
    return SelectedRoutes(
        od={("O1", "W1", "soy"), ("O2", "W3", "soy")},
        dc=set(),
        dd={("W1", "W2", "soy")},
        oc=set(),
    )


def test_deterministic_bounds_exclude_unreachable_supply():
    bounds = deterministic_inventory_bounds(
        bounded_network_data(), selected_network()
    )

    assert bounds["W1", "t2"] == 35.0
    assert bounds["W2", "t2"] == 42.0
    assert bounds["W3", "t2"] == 3011.0


def test_stochastic_bounds_are_scenario_specific():
    bounds = stochastic_inventory_bounds(
        bounded_network_data(), selected_network()
    )

    assert bounds["base", "W2", "t2"] == 57.0
    assert bounds["base", "W3", "t2"] == 4511.0

