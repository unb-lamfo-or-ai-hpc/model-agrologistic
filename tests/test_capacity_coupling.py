from types import SimpleNamespace

import pytest

from src.logic.model_config import ModelConfig
from src.logic.optimization_gurobipy import (
    _effective_reception_capacity_expr,
    _effective_shipping_capacity_expr,
    _effective_static_capacity_expr,
)


def capacity_data():
    return SimpleNamespace(
        static_capacity={"W1": 100.0, "C1": 0.0},
        reception_capacity={"W1": 10.0, "C1": 0.0},
        shipping_capacity={"W1": 12.0, "C1": 0.0},
        candidate_warehouses=["C1"],
    )


def test_period_equivalent_policy_preserves_existing_mvp_semantics():
    data = capacity_data()
    config = ModelConfig(days_per_period=30.0)
    candidate = {"C1": 50.0}
    expansion = {"W1": 20.0}
    bulkification = {"W1": 5.0}

    assert _effective_static_capacity_expr(
        data, config, candidate, expansion, bulkification, "W1"
    ) == pytest.approx(125.0)
    assert _effective_reception_capacity_expr(
        data, config, candidate, expansion, bulkification, "W1", "t1"
    ) == pytest.approx(300.0)
    assert _effective_shipping_capacity_expr(
        data, config, candidate, expansion, bulkification, "C1", "t1"
    ) == pytest.approx(50.0)


def test_daily_factor_policy_matches_historical_capacity_coupling():
    data = capacity_data()
    config = ModelConfig(
        capacity_coupling_policy="daily_factors",
        days_per_period=30.0,
        candidate_reception_daily_factor=0.20,
        candidate_shipping_daily_factor=0.20,
        expansion_reception_daily_factor=0.20,
        expansion_shipping_daily_factor=0.20,
        bulkification_reception_daily_factor=1.0,
        bulkification_shipping_daily_factor=1.0,
    )
    candidate = {"C1": 50.0}
    expansion = {"W1": 20.0}
    bulkification = {"W1": 5.0}

    assert _effective_static_capacity_expr(
        data, config, candidate, expansion, bulkification, "W1"
    ) == pytest.approx(120.0)
    assert _effective_reception_capacity_expr(
        data, config, candidate, expansion, bulkification, "W1", "t1"
    ) == pytest.approx(570.0)
    assert _effective_shipping_capacity_expr(
        data, config, candidate, expansion, bulkification, "W1", "t1"
    ) == pytest.approx(630.0)
    assert _effective_reception_capacity_expr(
        data, config, candidate, expansion, bulkification, "C1", "t1"
    ) == pytest.approx(300.0)
    assert _effective_shipping_capacity_expr(
        data, config, candidate, expansion, bulkification, "C1", "t1"
    ) == pytest.approx(300.0)


def test_capacity_coupling_policy_and_factors_are_validated():
    with pytest.raises(ValueError, match="capacity_coupling_policy"):
        ModelConfig(capacity_coupling_policy="unsupported")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="must be non-negative"):
        ModelConfig(expansion_reception_daily_factor=-0.01)
