import pytest

from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData
from src.logic.model_validation import (
    ModelDataValidationError,
    validate_model_data,
    validate_or_raise_model_data,
)


def tiny_valid_data() -> ModelData:
    return ModelData(
        origins=["O1"],
        warehouses=["W1", "W2"],
        existing_warehouses=["W1"],
        candidate_warehouses=["W2"],
        bulk_eligible_warehouses=["W1"],
        customers=["C1"],
        domestic_customers=["C1"],
        export_customers=[],
        products=["soy"],
        periods=["t1"],
        routes_od={("O1", "W1", "soy"), ("O1", "W2", "soy")},
        routes_dc={("W1", "C1", "soy"), ("W2", "C1", "soy")},
        supply={("O1", "soy", "t1"): 100.0},
        demand_dom={("C1", "soy", "t1"): 100.0},
        dist_od={("O1", "W1"): 100.0, ("O1", "W2"): 150.0},
        dist_dc={("W1", "C1"): 80.0, ("W2", "C1"): 60.0},
        static_capacity={"W1": 120.0},
        reception_capacity={"W1": 100.0},
        shipping_capacity={"W1": 100.0},
        max_candidate_capacity={"W2": 200.0},
        opening_fixed_cost={"W2": 1000.0},
        candidate_capacity_cost={"W2": 10.0},
        unmet_demand_penalty={("C1", "soy"): 1_000_000.0},
        emergency_static_capacity_penalty={"W1": 1_000_000.0, "W2": 1_000_000.0},
        emergency_reception_capacity_penalty={"W1": 1_000_000.0, "W2": 1_000_000.0},
    )


def test_valid_tiny_data_passes_validation():
    data = tiny_valid_data()

    result = validate_model_data(data)

    assert result.is_valid
    assert result.errors == []


def test_validate_or_raise_does_not_raise_for_valid_data():
    data = tiny_valid_data()

    validate_or_raise_model_data(data)


def test_duplicate_origin_is_invalid():
    data = tiny_valid_data()
    data.origins.append("O1")

    result = validate_model_data(data)

    assert not result.is_valid
    assert any(issue.code == "DUPLICATE_VALUES" for issue in result.errors)


def test_candidate_warehouse_must_belong_to_warehouses():
    data = tiny_valid_data()
    data.candidate_warehouses.append("W3")

    result = validate_model_data(data)

    assert not result.is_valid
    assert any(issue.code == "INVALID_SUBSET" for issue in result.errors)


def test_negative_supply_is_invalid():
    data = tiny_valid_data()
    data.supply[("O1", "soy", "t1")] = -1.0

    result = validate_model_data(data)

    assert not result.is_valid
    assert any(issue.code == "NEGATIVE_VALUE" for issue in result.errors)


def test_invalid_route_node_is_invalid():
    data = tiny_valid_data()
    data.routes_od.add(("UNKNOWN", "W1", "soy"))

    result = validate_model_data(data)

    assert not result.is_valid
    assert any(issue.code == "INVALID_ROUTE_NODE" for issue in result.errors)


def test_missing_distance_is_invalid_when_distances_are_required():
    data = tiny_valid_data()
    del data.dist_od[("O1", "W1")]

    result = validate_model_data(data, require_distances=True)

    assert not result.is_valid
    assert any(issue.code == "MISSING_DISTANCE" for issue in result.errors)


def test_missing_distance_is_allowed_when_distances_are_not_required():
    data = tiny_valid_data()
    del data.dist_od[("O1", "W1")]

    result = validate_model_data(data, require_distances=False)

    assert result.is_valid


def test_scalable_candidate_capacity_requires_variable_capacity_cost():
    data = tiny_valid_data()
    data.candidate_capacity_cost = {}

    result = validate_model_data(
        data,
        config=ModelConfig(candidate_capacity_mode="scalable"),
    )

    assert not result.is_valid
    assert any(
        issue.code == "MISSING_REQUIRED_PARAMETER"
        and issue.location == "candidate_capacity_cost"
        for issue in result.errors
    )


def test_fixed_candidate_capacity_does_not_require_variable_capacity_cost():
    data = tiny_valid_data()
    data.candidate_capacity_cost = {}

    result = validate_model_data(
        data,
        config=ModelConfig(candidate_capacity_mode="fixed"),
    )

    assert result.is_valid


def test_stochastic_mode_requires_scenarios():
    data = tiny_valid_data()

    result = validate_model_data(
        data,
        config=ModelConfig(mode="sto"),
    )

    assert not result.is_valid
    assert any(issue.code == "MISSING_SCENARIOS" for issue in result.errors)


def test_stochastic_probabilities_must_sum_to_one():
    data = tiny_valid_data()
    data.scenarios = ["low", "high"]
    data.scenario_prob = {
        "low": 0.3,
        "high": 0.3,
    }

    result = validate_model_data(
        data,
        config=ModelConfig(mode="sto"),
    )

    assert not result.is_valid
    assert any(
        issue.code == "INVALID_SCENARIO_PROBABILITY_SUM"
        for issue in result.errors
    )


def test_valid_stochastic_structure_passes_validation():
    data = tiny_valid_data()
    data.scenarios = ["low", "expected", "high"]
    data.scenario_prob = {
        "low": 0.25,
        "expected": 0.50,
        "high": 0.25,
    }
    data.supply_s = {
        ("low", "O1", "soy", "t1"): 80.0,
        ("expected", "O1", "soy", "t1"): 100.0,
        ("high", "O1", "soy", "t1"): 120.0,
    }
    data.demand_dom_s = {
        ("low", "C1", "soy", "t1"): 90.0,
        ("expected", "C1", "soy", "t1"): 100.0,
        ("high", "C1", "soy", "t1"): 110.0,
    }

    result = validate_model_data(
        data,
        config=ModelConfig(mode="sto"),
    )

    assert result.is_valid


def test_validate_or_raise_raises_for_invalid_data():
    data = tiny_valid_data()
    data.origins.append("O1")

    with pytest.raises(ModelDataValidationError):
        validate_or_raise_model_data(data)