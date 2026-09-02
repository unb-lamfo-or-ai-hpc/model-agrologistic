import json

import pytest

from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import OptimizationResult, calculate_evpi_vss
from src.logic.optimization_gurobipy import _gurobi_status_name
from src.logic.stochastic_analysis_gurobipy import (
    _expected_value_data,
    _single_scenario_data,
)
from tests.test_gurobipy_transshipment import require_gurobi_available


def capacity_newsvendor_data() -> ModelData:
    scenarios = ["baixo", "alto"]
    periods = ["t1", "t2"]

    return ModelData(
        origins=["O1"],
        warehouses=["W1"],
        existing_warehouses=["W1"],
        candidate_warehouses=[],
        bulk_eligible_warehouses=[],
        customers=["C1"],
        domestic_customers=["C1"],
        export_customers=[],
        products=["soy"],
        periods=periods,
        routes_od={("O1", "W1", "soy")},
        routes_dc={("W1", "C1", "soy")},
        supply={
            ("O1", "soy", "t1"): 5.0,
            ("O1", "soy", "t2"): 0.0,
        },
        demand_dom={
            ("C1", "soy", "t1"): 0.0,
            ("C1", "soy", "t2"): 5.0,
        },
        scenarios=scenarios,
        scenario_prob={"baixo": 0.5, "alto": 0.5},
        supply_s={
            ("baixo", "O1", "soy", "t1"): 0.0,
            ("baixo", "O1", "soy", "t2"): 0.0,
            ("alto", "O1", "soy", "t1"): 10.0,
            ("alto", "O1", "soy", "t2"): 0.0,
        },
        demand_dom_s={
            ("baixo", "C1", "soy", "t1"): 0.0,
            ("baixo", "C1", "soy", "t2"): 0.0,
            ("alto", "C1", "soy", "t1"): 0.0,
            ("alto", "C1", "soy", "t2"): 10.0,
        },
        dist_od={("O1", "W1"): 1.0},
        dist_dc={("W1", "C1"): 1.0},
        freight_origin={"O1": 0.0},
        freight_dest={"C1": 0.0},
        freight_warehouse={"W1": 0.0},
        transshipment_cost={"W1": 0.0},
        storage_tariff={("W1", "soy"): 0.0},
        static_capacity={"W1": 0.0},
        reception_capacity={"W1": 100.0},
        shipping_capacity={"W1": 100.0},
        max_expand_capacity={"W1": 10.0},
        expand_fixed_cost={"W1": 0.0},
        expand_variable_cost={"W1": 6.0},
        unmet_demand_penalty={("C1", "soy"): 1_000.0},
        emergency_static_capacity_penalty={"W1": 10.0},
        emergency_reception_capacity_penalty={"W1": 1_000.0},
    )


def stochastic_config() -> ModelConfig:
    return ModelConfig(
        mode="sto",
        allow_capacity_expansion=True,
        allow_bulkification=False,
        days_per_period=1.0,
        evpi_vss_tolerance=1e-7,
    )


def gurobi_config() -> SolverConfig:
    return SolverConfig(
        backend="gurobipy",
        solver_name="gurobi",
        mip_gap=0.0,
        time_limit=60,
        threads=1,
        tee=False,
    )


def expansion_capacity(result) -> float:
    return result.warehouse_decisions[0]["expansion_capacity"]


def test_gurobi_status_name_reports_resource_limits():
    class FakeGRB:
        MEM_LIMIT = 17

    class FakeModel:
        Status = 17

    assert _gurobi_status_name(FakeModel(), FakeGRB()) == "MEM_LIMIT"


def test_expected_value_projection_uses_scenario_probabilities():
    data = capacity_newsvendor_data()

    projected = _expected_value_data(data)

    assert projected.scenarios == []
    assert projected.supply[("O1", "soy", "t1")] == pytest.approx(5.0)
    assert projected.demand_dom[("C1", "soy", "t2")] == pytest.approx(5.0)
    assert projected.metadata["deterministic_projection"] == "expected_value"


def test_wait_and_see_projection_preserves_one_scenario_realization():
    data = capacity_newsvendor_data()

    projected = _single_scenario_data(data, "alto")

    assert projected.scenarios == []
    assert projected.supply[("O1", "soy", "t1")] == pytest.approx(10.0)
    assert projected.demand_dom[("C1", "soy", "t2")] == pytest.approx(10.0)
    assert projected.metadata["deterministic_projection"] == "wait_and_see:alto"


def test_evpi_vss_match_analytical_capacity_example():
    require_gurobi_available()

    result = calculate_evpi_vss(
        data=capacity_newsvendor_data(),
        model_config=stochastic_config(),
        solver_config=gurobi_config(),
    )

    assert result.recourse_problem == pytest.approx(50.0)
    assert result.wait_and_see == pytest.approx(30.0)
    assert result.expected_value_problem == pytest.approx(30.0)
    assert result.expected_result_of_ev_solution == pytest.approx(55.0)
    assert result.evpi == pytest.approx(20.0)
    assert result.vss == pytest.approx(5.0)


def test_evpi_vss_preserve_auditable_intermediate_decisions():
    require_gurobi_available()

    result = calculate_evpi_vss(
        data=capacity_newsvendor_data(),
        model_config=stochastic_config(),
        solver_config=gurobi_config(),
    )

    assert expansion_capacity(result.recourse_problem_result) == pytest.approx(0.0)
    assert expansion_capacity(
        result.expected_value_problem_result
    ) == pytest.approx(5.0)
    assert expansion_capacity(result.expected_result_result) == pytest.approx(5.0)
    assert expansion_capacity(
        result.wait_and_see_results["baixo"]
    ) == pytest.approx(0.0)
    assert expansion_capacity(
        result.wait_and_see_results["alto"]
    ) == pytest.approx(10.0)
    assert result.expected_result_result.metadata["first_stage_fixed"] is True


def test_evpi_vss_report_formulas_and_probabilities():
    require_gurobi_available()

    result = calculate_evpi_vss(
        data=capacity_newsvendor_data(),
        model_config=stochastic_config(),
        solver_config=gurobi_config(),
    )

    assert result.metadata["evpi_formula"] == "RP - WS"
    assert result.metadata["vss_formula"] == "EEV - RP"
    assert result.metadata["scenario_probabilities"] == {
        "baixo": 0.5,
        "alto": 0.5,
    }
    assert result.metadata["consistency_warnings"] == []


def test_evpi_vss_checkpoints_resume_every_completed_solve(tmp_path, monkeypatch):
    import src.logic.stochastic_analysis_gurobipy as analysis

    calls: list[str] = []

    def fake_stochastic(**kwargs):
        label = "eev" if kwargs.get("fixed_first_stage") is not None else "rp"
        calls.append(label)
        return OptimizationResult(
            status="optimal",
            objective_value=55.0 if label == "eev" else 50.0,
            warehouse_decisions=[{"warehouse": "W1", "open": 1.0}],
            raw_solver_result=object(),
        )

    def fake_deterministic(*, data, **_kwargs):
        source = data.metadata["deterministic_projection"]
        calls.append(source)
        objectives = {
            "expected_value": 30.0,
            "wait_and_see:baixo": 0.0,
            "wait_and_see:alto": 60.0,
        }
        return OptimizationResult(
            status="optimal",
            objective_value=objectives[source],
            warehouse_decisions=[{"warehouse": "W1", "open": 1.0}],
            raw_solver_result=object(),
        )

    monkeypatch.setattr(analysis, "solve_stochastic_model_gurobipy", fake_stochastic)
    monkeypatch.setattr(analysis, "_solve_deterministic_core", fake_deterministic)
    checkpoint_dir = tmp_path / "checkpoints"

    first = analysis.calculate_evpi_vss_gurobipy(
        data=capacity_newsvendor_data(),
        model_config=stochastic_config(),
        solver_config=gurobi_config(),
        checkpoint_dir=checkpoint_dir,
        checkpoint_identity="workbook-and-config-sha",
    )

    assert calls == [
        "rp",
        "expected_value",
        "eev",
        "wait_and_see:baixo",
        "wait_and_see:alto",
    ]
    assert first.evpi == pytest.approx(20.0)
    assert first.vss == pytest.approx(5.0)

    calls.clear()
    resumed = analysis.calculate_evpi_vss_gurobipy(
        data=capacity_newsvendor_data(),
        model_config=stochastic_config(),
        solver_config=gurobi_config(),
        checkpoint_dir=checkpoint_dir,
        checkpoint_identity="workbook-and-config-sha",
        resume=True,
    )

    assert calls == []
    assert resumed.evpi == pytest.approx(20.0)
    assert resumed.vss == pytest.approx(5.0)
    assert resumed.metadata["restored_checkpoint_steps"] == [
        "rp",
        "ev",
        "eev",
        "ws_000",
        "ws_001",
    ]
    progress = json.loads(
        (checkpoint_dir / "progress.json").read_text(encoding="utf-8")
    )
    assert progress["status"] == "complete"
    assert progress["completed_count"] == 5
    assert progress["total_steps"] == 5


def test_evpi_vss_resume_rejects_a_different_experiment(tmp_path):
    import src.logic.stochastic_analysis_gurobipy as analysis

    checkpoint_dir = tmp_path / "checkpoints"
    analysis._CheckpointStore.create(
        checkpoint_dir,
        identity="first-experiment",
        resume=False,
        total_steps=5,
    )

    with pytest.raises(ValueError, match="do not match"):
        analysis._CheckpointStore.create(
            checkpoint_dir,
            identity="changed-experiment",
            resume=True,
            total_steps=5,
        )

