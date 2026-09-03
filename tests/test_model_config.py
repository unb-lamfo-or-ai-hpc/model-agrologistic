import pytest

from src.logic.model_config import ModelConfig
from src.logic.optimization_gurobipy import _set_objective_policy


class FakeGRB:
    MINIMIZE = 1


class FakeModel:
    def __init__(self) -> None:
        self.ModelSense = None
        self.objective = None
        self.objectives = []

    def setObjective(self, expression, sense) -> None:
        self.objective = (expression, sense)

    def setObjectiveN(self, expression, **kwargs) -> None:
        self.objectives.append((expression, kwargs))


def test_operating_days_use_period_override_and_thirty_day_fallback():
    config = ModelConfig(days_per_period_by_period={"2026-02": 28.0})

    assert config.operating_days("2026-01") == pytest.approx(30.0)
    assert config.operating_days("2026-02") == pytest.approx(28.0)


def test_period_day_overrides_must_be_positive():
    with pytest.raises(ValueError, match="days_per_period_by_period"):
        ModelConfig(days_per_period_by_period={"2026-02": 0.0})


def test_objective_policy_must_be_supported():
    with pytest.raises(ValueError, match="objective_policy"):
        ModelConfig(objective_policy="unsupported")


def test_penalty_policy_uses_one_weighted_objective():
    model = FakeModel()

    _set_objective_policy(
        model=model,
        GRB=FakeGRB,
        config=ModelConfig(objective_policy="penalty"),
        penalized_cost="penalized",
        unmet_quantity="unmet",
        emergency_quantity="emergency",
        economic_cost="economic",
    )

    assert model.objective == ("penalized", FakeGRB.MINIMIZE)
    assert model.objectives == []


def test_lexicographic_policy_orders_service_slacks_before_economic_cost():
    model = FakeModel()

    _set_objective_policy(
        model=model,
        GRB=FakeGRB,
        config=ModelConfig(objective_policy="lexicographic"),
        penalized_cost="penalized",
        unmet_quantity="unmet",
        emergency_quantity="emergency",
        economic_cost="economic",
    )

    assert model.ModelSense == FakeGRB.MINIMIZE
    assert [expression for expression, _ in model.objectives] == [
        "unmet",
        "emergency",
        "economic",
    ]
    assert [options["priority"] for _, options in model.objectives] == [3, 2, 1]
