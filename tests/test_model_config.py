import pytest

from src.logic.model_config import ModelConfig, RunConfig, SolverConfig


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