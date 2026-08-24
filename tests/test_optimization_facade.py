import pytest
import os

from src.logic.model_config import ModelConfig, RunConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.model_validation import ModelDataValidationError
from src.logic.optimization import (
    OptimizationBackendNotImplementedError,
    OptimizationResult,
    solve_model,
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


def test_facade_dispatches_to_gurobipy_backend(monkeypatch):
    import src.logic.optimization_gurobipy as gurobi_backend

    data = tiny_valid_data()

    def fake_solve_model_gurobipy(data, model_config, solver_config):
        return OptimizationResult(
            status="optimal",
            objective_value=123.0,
            solver_backend=solver_config.backend,
            solver_name=solver_config.solver_name,
            model_mode=model_config.mode,
        )

    monkeypatch.setattr(
        gurobi_backend,
        "solve_model_gurobipy",
        fake_solve_model_gurobipy,
    )

    result = solve_model(
        data=data,
        model_config=ModelConfig(mode="det"),
        solver_config=SolverConfig(backend="gurobipy", solver_name="gurobi"),
    )

    assert result.status == "optimal"
    assert result.objective_value == 123.0
    assert result.solver_backend == "gurobipy"
    assert result.solver_name == "gurobi"
    assert result.model_mode == "det"
    assert result.has_solution is True


def test_facade_dispatches_to_pyomo_backend(monkeypatch):
    import src.logic.optimization_pyomo as pyomo_backend

    data = tiny_valid_data()

    def fake_solve_model_pyomo(data, model_config, solver_config):
        return OptimizationResult(
            status="optimal",
            objective_value=456.0,
            solver_backend=solver_config.backend,
            solver_name=solver_config.solver_name,
            model_mode=model_config.mode,
        )

    monkeypatch.setattr(
        pyomo_backend,
        "solve_model_pyomo",
        fake_solve_model_pyomo,
    )

    result = solve_model(
        data=data,
        model_config=ModelConfig(mode="det"),
        solver_config=SolverConfig(backend="pyomo", solver_name="scip"),
    )

    assert result.status == "optimal"
    assert result.objective_value == 456.0
    assert result.solver_backend == "pyomo"
    assert result.solver_name == "scip"
    assert result.model_mode == "det"


def test_facade_accepts_run_config(monkeypatch):
    import src.logic.optimization_pyomo as pyomo_backend

    data = tiny_valid_data()

    def fake_solve_model_pyomo(data, model_config, solver_config):
        return OptimizationResult(
            status="optimal",
            objective_value=789.0,
            solver_backend=solver_config.backend,
            solver_name=solver_config.solver_name,
            model_mode=model_config.mode,
        )

    monkeypatch.setattr(
        pyomo_backend,
        "solve_model_pyomo",
        fake_solve_model_pyomo,
    )

    run_config = RunConfig(
        model=ModelConfig(mode="det"),
        solver=SolverConfig(backend="pyomo", solver_name="scip"),
        run_name="test_run",
    )

    result = solve_model(data=data, run_config=run_config)

    assert result.status == "optimal"
    assert result.objective_value == 789.0
    assert result.solver_backend == "pyomo"
    assert result.solver_name == "scip"
    assert result.model_mode == "det"


def test_facade_rejects_mixing_run_config_with_explicit_configs():
    data = tiny_valid_data()

    with pytest.raises(ValueError):
        solve_model(
            data=data,
            run_config=RunConfig(),
            model_config=ModelConfig(),
        )


def test_facade_validates_data_before_dispatching():
    data = tiny_valid_data()
    data.origins.append("O1")

    with pytest.raises(ModelDataValidationError):
        solve_model(
            data=data,
            model_config=ModelConfig(mode="det"),
            solver_config=SolverConfig(backend="gurobipy", solver_name="gurobi"),
        )


def test_gurobipy_backend_stub_raises_not_implemented():
    data = tiny_valid_data()
    data.scenarios = ["expected"]
    data.scenario_prob = {"expected": 1.0}

    with pytest.raises(OptimizationBackendNotImplementedError):
        solve_model(
            data=data,
            model_config=ModelConfig(mode="sto"),
            solver_config=SolverConfig(backend="gurobipy", solver_name="gurobi"),
        )


def test_pyomo_backend_stub_raises_not_implemented():
    data = tiny_valid_data()

    with pytest.raises(OptimizationBackendNotImplementedError):
        solve_model(
            data=data,
            model_config=ModelConfig(mode="det"),
            solver_config=SolverConfig(backend="pyomo", solver_name="scip"),
        )

def test_facade_configures_gurobi_wls_license_from_default_path(
    monkeypatch,
    tmp_path,
):
    import src.logic.optimization as optimization
    import src.logic.optimization_gurobipy as gurobi_backend

    data = tiny_valid_data()

    license_file = tmp_path / "gurobi.lic"
    license_file.write_text(
        "WLSACCESSID=dummy\n"
        "WLSSECRET=dummy\n"
        "LICENSEID=123\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("GRB_LICENSE_FILE", raising=False)
    monkeypatch.setattr(
        optimization,
        "DEFAULT_GUROBI_LICENSE_FILE",
        str(license_file),
    )

    def fake_solve_model_gurobipy(data, model_config, solver_config):
        return OptimizationResult(
            status="optimal",
            objective_value=1.0,
            solver_backend=solver_config.backend,
            solver_name=solver_config.solver_name,
            model_mode=model_config.mode,
        )

    monkeypatch.setattr(
        gurobi_backend,
        "solve_model_gurobipy",
        fake_solve_model_gurobipy,
    )

    result = solve_model(
        data=data,
        model_config=ModelConfig(mode="det"),
        solver_config=SolverConfig(backend="gurobipy", solver_name="gurobi"),
    )

    assert result.status == "optimal"
    assert os.environ["GRB_LICENSE_FILE"] == str(license_file)


def test_facade_respects_explicit_gurobi_license_file_in_solver_options(
    monkeypatch,
    tmp_path,
):
    import src.logic.optimization_gurobipy as gurobi_backend

    data = tiny_valid_data()

    license_file = tmp_path / "custom_gurobi.lic"
    license_file.write_text(
        "WLSACCESSID=dummy\n"
        "WLSSECRET=dummy\n"
        "LICENSEID=123\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("GRB_LICENSE_FILE", raising=False)

    def fake_solve_model_gurobipy(data, model_config, solver_config):
        return OptimizationResult(
            status="optimal",
            objective_value=1.0,
            solver_backend=solver_config.backend,
            solver_name=solver_config.solver_name,
            model_mode=model_config.mode,
        )

    monkeypatch.setattr(
        gurobi_backend,
        "solve_model_gurobipy",
        fake_solve_model_gurobipy,
    )

    result = solve_model(
        data=data,
        model_config=ModelConfig(mode="det"),
        solver_config=SolverConfig(
            backend="gurobipy",
            solver_name="gurobi",
            solver_options={
                "license_file": str(license_file),
            },
        ),
    )

    assert result.status == "optimal"
    assert os.environ["GRB_LICENSE_FILE"] == str(license_file)