import pytest

from src.logic.model_config import ModelConfig, RunConfig, SolverConfig
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


def test_default_solver_config_uses_gurobipy():
    config = SolverConfig()

    assert config.backend == "gurobipy"
    assert config.solver_name == "gurobi"
    assert config.mip_gap == 0.01
    assert config.time_limit == 3600


def test_pyomo_scip_solver_config_is_valid():
    config = SolverConfig(
        backend="pyomo",
        solver_name="scip",
        mip_gap=0.05,
        time_limit=120,
    )

    assert config.backend == "pyomo"
    assert config.solver_name == "scip"
    assert config.mip_gap == 0.05
    assert config.time_limit == 120


def test_invalid_solver_backend_raises_error():
    with pytest.raises(ValueError):
        SolverConfig(backend="invalid")  # type: ignore[arg-type]


def test_invalid_gurobipy_solver_name_raises_error():
    with pytest.raises(ValueError):
        SolverConfig(backend="gurobipy", solver_name="scip")


def test_negative_mip_gap_raises_error():
    with pytest.raises(ValueError):
        SolverConfig(mip_gap=-0.01)


def test_default_model_config_is_deterministic():
    config = ModelConfig()

    assert config.mode == "det"
    assert config.candidate_capacity_mode == "scalable"
    assert config.allow_unmet_domestic_demand is True
    assert config.allow_emergency_static_capacity is True
    assert config.allow_emergency_reception_capacity is True
    assert config.terminal_inventory_policy == "free"
    assert config.objective_policy == "penalty"
    assert config.capacity_coupling_policy == "daily_factors"
    assert config.interhub_factor == pytest.approx(1.0)
    assert config.separate_emergency_capacity_slacks is True
    assert config.days_per_period == pytest.approx(30.0)


def test_stochastic_model_config_is_valid():
    config = ModelConfig(mode="sto")

    assert config.mode == "sto"


def test_fixed_candidate_capacity_mode_is_valid():
    config = ModelConfig(candidate_capacity_mode="fixed")

    assert config.candidate_capacity_mode == "fixed"


def test_invalid_candidate_capacity_mode_raises_error():
    with pytest.raises(ValueError):
        ModelConfig(candidate_capacity_mode="invalid")  # type: ignore[arg-type]


def test_invalid_terminal_inventory_policy_raises_error():
    with pytest.raises(ValueError):
        ModelConfig(terminal_inventory_policy="invalid")  # type: ignore[arg-type]


def test_invalid_route_filter_strategy_raises_error():
    with pytest.raises(ValueError):
        ModelConfig(route_filter_strategy="invalid")  # type: ignore[arg-type]


def test_invalid_pareto_fraction_raises_error():
    with pytest.raises(ValueError):
        ModelConfig(pareto_fraction=0.0)

    with pytest.raises(ValueError):
        ModelConfig(pareto_fraction=1.5)


def test_invalid_route_top_k_raises_error():
    with pytest.raises(ValueError):
        ModelConfig(route_top_k=0)


def test_run_config_combines_model_and_solver_config():
    run_config = RunConfig(
        model=ModelConfig(mode="sto"),
        solver=SolverConfig(backend="pyomo", solver_name="scip"),
        run_name="test_run",
        output_dir="outputs/test_run",
    )

    assert run_config.model.mode == "sto"
    assert run_config.solver.backend == "pyomo"
    assert run_config.solver.solver_name == "scip"
    assert run_config.run_name == "test_run"


def test_operating_days_use_period_override_and_thirty_day_fallback():
    config = ModelConfig(days_per_period_by_period={"2026-02": 28.0})

    assert config.operating_days("2026-01") == pytest.approx(30.0)
    assert config.operating_days("2026-02") == pytest.approx(28.0)


def test_period_day_overrides_must_be_positive():
    with pytest.raises(ValueError, match="days_per_period_by_period"):
        ModelConfig(days_per_period_by_period={"2026-02": 0.0})


def test_objective_policy_must_be_supported():
    with pytest.raises(ValueError, match="objective_policy"):
        ModelConfig(objective_policy="unsupported")  # type: ignore[arg-type]


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


def test_lexicographic_policy_prioritizes_domestic_service():
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
    assert [options["name"] for _, options in model.objectives] == [
        "minimize_unmet_demand",
        "minimize_emergency_capacity",
        "minimize_economic_cost",
    ]


def test_v020_rejects_ambiguous_emergency_slack_and_negative_interhub_factor():
    with pytest.raises(ValueError, match="requires separate"):
        ModelConfig(separate_emergency_capacity_slacks=False)

    with pytest.raises(ValueError, match="interhub_factor"):
        ModelConfig(interhub_factor=-0.01)
