"""Real common-form parity and transfer controls for new Pyomo adapters."""

from dataclasses import replace

import pytest

from src.logic.model_config import ModelConfig
from src.logic.optimization import solve_model
from src.logic.pyomo_linear_matrix import matrix_identity
from src.logic.pyomo_scip_adapter import ScipAdapter
from tests.test_pyomo_multisolver import available, config
from tests.test_scalar_contract import assert_validation, economic_data, scenario_data


def test_all_four_solvers_receive_the_same_ordered_matrix():
    data = scenario_data(economic_data(), {"low": 0.25, "high": 0.75})
    matrices = []
    for solver in ("gurobi", "scip", "cbc", "highs"):
        result = solve_model(data, ModelConfig(mode="sto"), config(solver))
        assert_validation(data, ModelConfig(mode="sto"), result)
        assert result.objective_value == pytest.approx(150)
        matrices.append(result.metadata["common_linear_matrix"])
    assert all(matrix == matrices[0] for matrix in matrices)


@pytest.mark.parametrize("solver", ["gurobi", "scip"])
def test_seed_is_a_recorded_native_parameter_and_strategy_is_not_forced(solver):
    result = solve_model(economic_data(), ModelConfig(), config(solver))
    options = result.metadata["effective_native_options"]
    if solver == "gurobi":
        assert options["Seed"] == 42
        assert options["Method"] == -1 and options["Presolve"] == -1
    else:
        assert options["randomization/randomseedshift"] == 42
    assert result.metadata["timings"]["solver_transfer_seconds"] >= 0


def test_scip_transfer_preserves_negative_bounds_ranged_rows_and_objective_constant():
    available("scip")
    import pyomo.environ as pyo

    model = pyo.ConcreteModel()
    model.x = pyo.Var(bounds=(-3, 4))
    model.y = pyo.Var(domain=pyo.Binary)
    model.row = pyo.Constraint(expr=pyo.inequality(-2, model.x + model.y, 1))
    model.obj = pyo.Objective(expr=2 * model.x + model.y + 7)
    adapter = ScipAdapter()
    try:
        adapter.set_instance(model, config("scip"))
        result = adapter.solve()
        assert result.usable and result.objective == pytest.approx(2)
        assert pyo.value(model.x) == pytest.approx(-3)
        assert pyo.value(model.y) == pytest.approx(1)
    finally:
        adapter.close()
    assert adapter.native is None and adapter.variables == []


def test_matrix_identity_detects_coefficient_bounds_and_objective_drift():
    available("gurobi")
    import pyomo.environ as pyo

    model = pyo.ConcreteModel()
    model.x = pyo.Var(bounds=(0, 5))
    model.row = pyo.Constraint(expr=model.x >= 2)
    model.obj = pyo.Objective(expr=model.x + 3)
    initial = matrix_identity(model)["sha256"]
    model.x.setub(6)
    assert matrix_identity(model)["sha256"] != initial
    model.x.setub(5)
    model.obj.set_value(model.x + 4)
    assert matrix_identity(model)["sha256"] != initial
    model.obj.set_value(model.x + 3)
    model.row.set_value(2 * model.x >= 2)
    assert matrix_identity(model)["sha256"] != initial


def test_nonlinear_matrix_is_rejected_before_native_allocation():
    available("gurobi")
    import pyomo.environ as pyo

    model = pyo.ConcreteModel()
    model.x = pyo.Var(bounds=(0, 5))
    model.obj = pyo.Objective(expr=model.x**2)
    with pytest.raises(ValueError, match="linear"):
        matrix_identity(model)


@pytest.mark.parametrize("solver", ["gurobi", "scip"])
def test_tiny_time_limit_cannot_invent_an_incumbent(solver):
    result = solve_model(
        economic_data(), ModelConfig(), replace(config(solver), time_limit=1e-9),
        validate=False,
    )
    if not result.has_solution:
        assert result.objective_value is None
        assert result.flows == [] and result.cost_breakdown == {}
    assert result.metadata["native_model_lifecycle"][0]["status"] == "disposed"


@pytest.mark.parametrize("solver", ["gurobi", "scip"])
def test_new_adapter_disposes_native_problem_after_solve_exception(monkeypatch, solver):
    available(solver)
    captured = []
    if solver == "gurobi":
        from pyomo.contrib.appsi.solvers import Gurobi

        def fail(adapter, model):
            captured.append(adapter)
            raise RuntimeError("public injected solve failure")

        monkeypatch.setattr(Gurobi, "solve", fail)
    else:
        def fail(adapter):
            captured.append(adapter)
            raise RuntimeError("public injected solve failure")

        monkeypatch.setattr(ScipAdapter, "solve", fail)
    with pytest.raises(RuntimeError, match="public injected solve failure"):
        solve_model(economic_data(), ModelConfig(), config(solver))
    adapter = captured[0]
    if solver == "gurobi":
        assert adapter._solver_model is None
    else:
        assert adapter.native is None and adapter.native_variables == []
