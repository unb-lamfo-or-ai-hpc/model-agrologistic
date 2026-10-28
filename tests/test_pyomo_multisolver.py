"""Public real Pyomo HiGHS/CBC controls; no private inputs, scheduler or HPC."""

import copy
import importlib.util
import json
import os
import shutil
from dataclasses import replace

import pytest

from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.optimization import solve_model
from src.logic.optimization_pyomo import build_model, normalized_status, settings
from src.logic.pyomo_bounds import POLICY, candidate_slack_bounds
from tests.test_scalar_contract import (
    assert_validation,
    economic_data,
    qualified_solver,
    scenario_data,
)


def available(solver):
    required = os.environ.get("AGRO_REQUIRE_PYOMO_SOLVERS") == "1"
    missing = (
        importlib.util.find_spec("pyomo") is None
        or (solver == "highs" and importlib.util.find_spec("highspy") is None)
        or (solver == "cbc" and shutil.which("cbc") is None)
    )
    if missing:
        if required:
            pytest.fail("Required cloud Pyomo/native solver missing; no skips accepted.")
        pytest.skip("Optional Pyomo/native solver not installed in this profile.")


def config(solver):
    available(solver)
    return SolverConfig(
        backend="pyomo", solver_name=solver, threads=1, seed=42, time_limit=30, mip_gap=0,
        solver_options={"indicator_reformulation": POLICY},
    )


def test_reformulation_is_explicit_and_solver_options_are_not_silently_remapped():
    with pytest.raises(ValueError, match="Explicit indicator"):
        settings(SolverConfig(backend="pyomo", solver_name="highs"))
    with pytest.raises(ValueError, match="Unqualified"):
        settings(SolverConfig(
            backend="pyomo", solver_name="highs",
            solver_options={"indicator_reformulation": POLICY, "SoftMemLimit": 1},
        ))


@pytest.mark.parametrize("solver", ["highs", "cbc"])
def test_real_det_sto_hand_calculated_cost_and_independent_certificate(solver):
    data = economic_data()
    before = copy.deepcopy(data)
    result = solve_model(data, ModelConfig(), config(solver))
    sto_data = scenario_data(data, {"only": 1.0})
    sto = solve_model(sto_data, ModelConfig(mode="sto"), config(solver))
    assert data == before
    assert result.objective_value == pytest.approx(150)
    assert sto.objective_value == pytest.approx(150)
    assert_validation(data, ModelConfig(), result)
    assert_validation(sto_data, ModelConfig(mode="sto"), sto)
    assert result.mip_gap == pytest.approx(0, abs=1e-9)
    assert result.metadata["native_model_lifecycle"][0]["status"] == "disposed"
    assert result.metadata["pyomo_reformulation"]["policy"] == POLICY
    assert not result.metadata["pyomo_reformulation"]["entire_redundant_slack_region_preserved"]
    assert not result.warehouse_decisions[0].get("scenario")
    assert all("scenario" in row for row in sto.flows)
    json.dumps(result.metadata, allow_nan=False)


@pytest.mark.parametrize("solver", ["highs", "cbc"])
@pytest.mark.parametrize("kind", ["unmet", "static", "reception"])
def test_three_slacks_units_and_costs(solver, kind):
    data = economic_data()
    expected = 150
    if kind == "unmet":
        data.demand_dom["C", "P", "t"] = 12
        expected += 2000
    elif kind == "static":
        data.demand_dom["C", "P", "t"] = 0
        data.static_capacity["W"] = 6
        expected = 90 + 20 + 8000
    else:
        data.reception_capacity["W"] = 6 / 30
        expected += 12000
    result = solve_model(data, ModelConfig(), config(solver))
    assert result.objective_value == pytest.approx(expected)
    assert_validation(data, ModelConfig(), result)


@pytest.mark.parametrize("solver", ["highs", "cbc"])
def test_unequal_probabilities_and_scenario_split_count_investment_once(solver):
    data = scenario_data(economic_data(), {"low": 0.25, "high": 0.75})
    data.supply_s["high", "O", "P", "t"] = 6
    data.demand_dom_s["high", "C", "P", "t"] = 6
    result = solve_model(data, ModelConfig(mode="sto"), config(solver))
    assert result.objective_value == pytest.approx(0.25 * 150 + 0.75 * 90)
    assert_validation(data, ModelConfig(mode="sto"), result)
    original = economic_data()
    original.existing_warehouses = []
    original.candidate_warehouses = ["W"]
    original.static_capacity = {"W": 0}
    original.reception_capacity = {"W": 0}
    original.shipping_capacity = {"W": 0}
    original.max_candidate_capacity = {"W": 100}
    original.opening_fixed_cost = {"W": 17}
    original.candidate_capacity_cost = {"W": 2}
    cfg = ModelConfig(candidate_capacity_mode="scalable", capacity_coupling_policy="daily_factors")
    det = solve_model(original, cfg, config(solver))
    split = scenario_data(original, {"one": 0.2, "two": 0.8})
    sto = solve_model(split, replace(cfg, mode="sto"), config(solver))
    assert det.objective_value == pytest.approx(sto.objective_value)
    assert det.cost_breakdown["opening"] == pytest.approx(17)
    assert_validation(original, cfg, det)
    assert_validation(split, replace(cfg, mode="sto"), sto)


@pytest.mark.parametrize("solver", ["highs", "cbc"])
def test_infeasible_no_incumbent_never_exports_zero_cost_or_decisions(solver):
    data = economic_data()
    data.static_capacity["W"] = 0
    data.shipping_capacity["W"] = 0
    cfg = ModelConfig(allow_emergency_static_capacity=False)
    result = solve_model(data, cfg, config(solver))
    assert result.status == "infeasible" and not result.has_solution
    assert result.objective_value is None
    assert result.flows == [] and result.warehouse_decisions == []
    assert result.cost_breakdown == {}
    assert result.metadata["native_model_lifecycle"][0]["status"] == "disposed"


@pytest.mark.parametrize("solver", ["highs", "cbc"])
def test_public_parity_against_native_reference(solver):
    result = solve_model(economic_data(), ModelConfig(), config(solver))
    reference = solve_model(economic_data(), ModelConfig(), qualified_solver("gurobipy"))
    assert result.objective_value == pytest.approx(reference.objective_value)
    assert result.cost_breakdown == pytest.approx(reference.cost_breakdown)


@pytest.mark.parametrize("native,usable,status", [
    ("maxTimeLimit", False, "time_limit"), ("maxTimeLimit", True, "time_limit"),
    ("infeasible", False, "infeasible"), ("unbounded", False, "unbounded"),
    ("unknown", False, "error"), ("optimal", False, "error"),
])
def test_normalized_negative_terminations_preserve_no_incumbent(native, usable, status):
    assert normalized_status(native, usable) == status


def test_circulation_reception_bound_uses_hard_shipping_not_supply_only():
    data = scenario_data(economic_data(), {"s": 1.0})
    data.candidate_warehouses = ["W"]
    data.existing_warehouses = []
    data.max_candidate_capacity = {"W": 100}
    bounds, proof = candidate_slack_bounds(data, ModelConfig(mode="sto"))
    assert bounds["static"]["s", "W", "t"] == 10
    assert bounds["reception"]["s", "W", "t"] > 10
    assert proof["equivalence"] == "physical_investment_projection_and_optimal_scalar_value"
    data.emergency_reception_capacity_penalty["W"] = -1
    with pytest.raises(ValueError, match="nonnegative"):
        candidate_slack_bounds(data, ModelConfig(mode="sto"))


def test_cumulative_inventory_bound_includes_previous_periods_and_initial_stock():
    data = economic_data()
    data.periods = ["t", "u"]
    data.supply["O", "P", "u"] = 8
    data.initial_inventory["W", "P"] = 3
    data.candidate_warehouses = ["W"]
    data.existing_warehouses = []
    data.max_candidate_capacity = {"W": 100}
    bounds, _ = candidate_slack_bounds(scenario_data(data, {"s": 1}), ModelConfig(mode="sto"))
    assert bounds["static"]["s", "W", "u"] == 21


@pytest.mark.parametrize("solver", ["highs", "cbc"])
def test_guard_precedes_model_allocation_and_solver_launch(solver):
    available(solver)
    with pytest.raises(ValueError, match="guard exceeded"):
        build_model(economic_data(), ModelConfig(), max_variables=1)


@pytest.mark.parametrize("solver", ["highs", "cbc"])
@pytest.mark.parametrize("mode", ["det", "sto"])
def test_excel_export_original_validation_and_immutable_completion(tmp_path, solver, mode):
    from src.logic.excel_loader import ExcelLoaderConfig
    from src.logic.experiment_runner import ExperimentSpec, run_experiment
    from src.logic.run_integrity import verify_completion
    from tests.test_excel_loader import build_tiny_golden_excel

    workbook = tmp_path / "public.xlsx"
    build_tiny_golden_excel(workbook)
    spec = ExperimentSpec(
        "public", workbook, loader=ExcelLoaderConfig(include_stochastic_scenarios=True),
        model=ModelConfig(mode=mode), solver=config(solver),
    )
    summary = run_experiment(spec, tmp_path / "results", progress=lambda *_: None)
    run = tmp_path / "results/public"
    result = json.loads((run / "result.json").read_bytes())
    assert summary.independent_validation_status == "accepted"
    assert verify_completion(run, result["result"]["metadata"]["run_identity"])[0]
    receipt = (run / "run_completion.json").read_bytes()
    with pytest.raises(FileExistsError):
        run_experiment(spec, tmp_path / "results", progress=lambda *_: None)
    assert (run / "run_completion.json").read_bytes() == receipt


@pytest.mark.parametrize("solver", ["highs", "cbc"])
def test_active_candidate_slacks_have_unchanged_stock_and_period_units(solver):
    data = economic_data()
    data.existing_warehouses = []
    data.candidate_warehouses = ["W"]
    data.static_capacity = {"W": 0}
    data.reception_capacity = {"W": 0}
    data.shipping_capacity = {"W": 0}
    data.max_candidate_capacity = {"W": 2}
    data.opening_fixed_cost = {"W": 17}
    data.demand_dom["C", "P", "t"] = 0
    cfg = ModelConfig(
        candidate_capacity_mode="fixed", capacity_coupling_policy="daily_factors",
        candidate_reception_daily_factor=0.1, candidate_shipping_daily_factor=1,
    )
    result = solve_model(data, cfg, config(solver))
    assert result.objective_value == pytest.approx(28127)
    assert_validation(data, cfg, result)
    slacks = {r["capacity_type"]: r["value"] for r in result.emergency_capacity}
    assert slacks == pytest.approx({"static": 8, "reception": 4})


def test_native_handle_and_model_are_cleared_when_adapter_raises(monkeypatch):
    from types import SimpleNamespace

    available("highs")
    import pyomo.contrib.appsi.solvers as solvers

    calls = []
    class Fake:
        def __init__(self):
            self.config = SimpleNamespace()
            self.highs_options = {}
            self._solver_model = SimpleNamespace(clear=lambda: calls.append("native_clear"))
            self._last_results_object = None

        def available(self):
            return True

        def set_instance(self, model):
            self.model = model
            calls.append(model)

        def solve(self, model):
            raise RuntimeError("public native failure")
    monkeypatch.setattr(solvers, "Highs", Fake)
    with pytest.raises(RuntimeError, match="public native failure"):
        solve_model(economic_data(), ModelConfig(), config("highs"))
    assert "native_clear" in calls
    assert len(list(calls[0].component_objects())) == 0


@pytest.mark.parametrize("solver", ["highs", "cbc"])
def test_real_unbounded_control_never_publishes_a_finite_optimum(solver):
    data = economic_data()
    # Public adverse control only: an existing-facility slack has no upper bound.
    # The proof changes candidate slack representatives only; this control has none.
    data.emergency_static_capacity_penalty["W"] = -1
    result = solve_model(data, ModelConfig(), config(solver), validate=False)
    assert result.status in {"unbounded", "error"}
    assert not result.has_solution and result.objective_value is None
    assert result.flows == [] and result.cost_breakdown == {}
    assert result.metadata["objective_bound"] is None
    assert result.metadata["native_model_lifecycle"][0]["status"] == "disposed"
