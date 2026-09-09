from __future__ import annotations

import pytest

from src.logic.excel_loader import ExcelLoaderConfig, _build_penalty_rates
from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData
from src.logic.optimization_gurobipy import (
    _origin_to_warehouse_unit_cost,
    _warehouse_to_customer_unit_cost,
    _warehouse_to_warehouse_unit_cost,
)


def test_thesis_transport_cost_equations_use_the_correct_endpoint_rates():
    data = ModelData(
        dist_od={("O1", "W1"): 10.0},
        dist_dc={("W1", "C1"): 500.0},
        dist_dd={("W1", "W2"): 30.0},
        freight_origin={"O1": 2.0},
        freight_dest={"C1": 99.0},
        freight_warehouse={"W1": 3.0, "W2": 4.0},
        transshipment_cost={"W1": 5.0, "W2": 7.0},
    )
    config = ModelConfig(interhub_factor=0.8)

    assert _origin_to_warehouse_unit_cost(data, "O1", "W1", "soy") == pytest.approx(
        25.0
    )
    assert _warehouse_to_customer_unit_cost(
        data, "W1", "C1", "soy"
    ) == pytest.approx(1500.0)
    assert _warehouse_to_warehouse_unit_cost(
        data, "W1", "W2", "soy", config
    ) == pytest.approx(727.0)


def test_thesis_dynamic_penalties_follow_the_historical_scaling_rule():
    unmet, emergency_static, emergency_reception = _build_penalty_rates(
        config=ExcelLoaderConfig(
            compute_haversine_distances=False,
            penalty_policy="thesis_dynamic",
        ),
        warehouses=["W1"],
        domestic_customers=["C1"],
        products=["soy"],
        routes_dc={("W1", "C1", "soy")},
        routes_oc={("O1", "C1", "soy")},
        dist_dc={("W1", "C1"): 500.0},
        dist_oc={("O1", "C1"): 25.0},
        freight_origin={"O1": 2.0},
        freight_warehouse={"W1": 3.0},
        expand_variable_cost={"W1": 1050.0},
        storage_tariff={("W1", "soy"): 20.0},
    )

    assert emergency_static == {"W1": pytest.approx(52_500.0)}
    assert emergency_reception == {"W1": pytest.approx(52_500.0)}
    assert unmet == {("C1", "soy"): pytest.approx(150_000.0)}


def test_fixed_penalties_remain_available_for_archived_v010_replay():
    unmet, emergency_static, emergency_reception = _build_penalty_rates(
        config=ExcelLoaderConfig(
            compute_haversine_distances=False,
            penalty_policy="fixed",
            default_unmet_demand_penalty=11.0,
            default_emergency_static_penalty=22.0,
            default_emergency_reception_penalty=33.0,
        ),
        warehouses=["W1"],
        domestic_customers=["C1"],
        products=["soy"],
        routes_dc=set(),
        routes_oc=set(),
        dist_dc={},
        dist_oc={},
        freight_origin={},
        freight_warehouse={},
        expand_variable_cost={},
        storage_tariff={},
    )

    assert unmet == {("C1", "soy"): 11.0}
    assert emergency_static == {"W1": 22.0}
    assert emergency_reception == {"W1": 33.0}
