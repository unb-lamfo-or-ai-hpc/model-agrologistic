"""Small analytical scalar qualifications; no scheduler, private input or HPC job."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from src.logic.mathematical_contract import extensive_form_inputs, prepare_model_data
from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import OptimizationResult, scalar_mip_gap, solve_model
from src.logic.solution_validation import validate_solution
from tests.test_gurobipy_transshipment import require_gurobi_available


def economic_data():
    return ModelData(
        origins=["O"],
        warehouses=["W"],
        existing_warehouses=["W"],
        candidate_warehouses=[],
        bulk_eligible_warehouses=[],
        customers=["C"],
        domestic_customers=["C"],
        export_customers=[],
        products=["P"],
        periods=["t"],
        routes_od={("O", "W", "P")},
        routes_dc={("W", "C", "P")},
        dist_od={("O", "W"): 2},
        dist_dc={("W", "C"): 3},
        freight_origin={"O": 4},
        freight_warehouse={"W": 2},
        transshipment_cost={"W": 1},
        supply={("O", "P", "t"): 10},
        demand_dom={("C", "P", "t"): 10},
        storage_tariff={("W", "P"): 2},
        static_capacity={"W": 100},
        reception_capacity={"W": 100},
        shipping_capacity={"W": 100},
        unmet_demand_penalty={("C", "P"): 1000},
        emergency_static_capacity_penalty={"W": 2000},
        emergency_reception_capacity_penalty={"W": 3000},
    )


def scenario_data(data, probabilities):
    return replace(
        data,
        scenarios=list(probabilities),
        scenario_prob=probabilities,
        supply_s={(s, *k): v for s in probabilities for k, v in data.supply.items()},
        demand_dom_s={(s, *k): v for s in probabilities for k, v in data.demand_dom.items()},
        demand_exp_s={(s, *k): v for s in probabilities for k, v in data.demand_exp.items()},
    )


def qualified_solver(backend):
    import os

    if backend == "gurobipy":
        if os.environ.get("AGRO_REQUIRE_NATIVE_SOLVERS") == "1":
            import gurobipy as gp

            with gp.Env(empty=True) as env:
                env.setParam("OutputFlag", 0)
                env.start()
        else:
            require_gurobi_available()
    else:
        pytest.importorskip("pyscipopt")
    return SolverConfig(
        backend=backend,
        solver_name="gurobi" if backend == "gurobipy" else "scip",
        threads=1,
        time_limit=30,
        mip_gap=0,
    )


def assert_validation(data, config, result):
    report = validate_solution(prepare_model_data(data, config), config, result)
    assert report["status"] == "accepted", report["failure_samples"]
    assert sum(report["reconstructed_costs"].values()) == pytest.approx(result.objective_value)
    # First/second-stage decisions describe STO recourse, not objective priorities.
    assert not any(
        "lexicographic" in k or k.startswith("objective_priority") for k in result.metadata
    )
    assert "solver_stages" not in result.metadata
    return report


@pytest.mark.parametrize("policy", ["lexicographic", "service_first", "unknown"])
def test_only_scalar_policy_can_be_selected(policy):
    with pytest.raises(ValueError, match="objective_policy"):
        ModelConfig(objective_policy=policy)


@pytest.mark.parametrize("option", ["ObjNumber", "ObjNRelTol", "MultiObjMethod", "MultiObjPre"])
def test_old_solver_options_fail_before_import_or_execution(option):
    with pytest.raises(ValueError, match="Multiobjective"):
        SolverConfig(solver_options={option: 0})


def test_projection_uses_base_arrays_not_a_selected_or_expected_scenario():
    original = scenario_data(economic_data(), {"different": 1.0})
    original.supply_s["different", "O", "P", "t"] = 999
    projected, config = extensive_form_inputs(original, ModelConfig())
    assert config.mode == "sto"
    assert projected.scenario_prob == {"deterministic": 1.0}
    assert projected.supply_s == {("deterministic", "O", "P", "t"): 10}
    assert original.supply_s["different", "O", "P", "t"] == 999


def test_sparse_deterministic_arrays_keep_implicit_zero_semantics():
    original = economic_data()
    original.periods.append("second")
    projected, _ = extensive_form_inputs(original, ModelConfig())
    assert projected.supply_s["deterministic", "O", "P", "second"] == 0
    assert projected.demand_dom_s["deterministic", "C", "P", "second"] == 0
    assert ("O", "P", "second") not in original.supply


@pytest.mark.parametrize("backend", ["gurobipy", "pyscipopt"])
def test_det_equals_one_scenario_sto_and_hand_calculated_cost(backend):
    solver = qualified_solver(backend)
    data = economic_data()
    deterministic = solve_model(data, ModelConfig(), solver)
    stochastic_data = scenario_data(data, {"only": 1.0})
    stochastic = solve_model(stochastic_data, ModelConfig(mode="sto"), solver)
    # Ten tonnes: OD=(2*4+1), DC=(3*2); no investment, inventory or slack.
    assert deterministic.objective_value == pytest.approx(150)
    assert stochastic.objective_value == pytest.approx(150)
    assert deterministic.cost_breakdown == pytest.approx(stochastic.cost_breakdown)
    assert deterministic.metrics["total_flow"] == pytest.approx(20)
    assert deterministic.metrics["total_unmet_demand"] == pytest.approx(0)
    assert deterministic.metrics["total_emergency_capacity"] == pytest.approx(0)
    assert_validation(data, ModelConfig(), deterministic)
    assert_validation(stochastic_data, ModelConfig(mode="sto"), stochastic)
    assert all("scenario" not in r for r in deterministic.flows)
    assert all("scenario" in r for r in stochastic.flows)
    assert all("scenario" not in r for r in stochastic.warehouse_decisions)


@pytest.mark.parametrize("backend", ["gurobipy", "pyscipopt"])
@pytest.mark.parametrize("kind", ["unmet", "static", "reception"])
def test_three_distinct_slacks_have_separate_units_and_penalties(backend, kind):
    data = economic_data()
    if kind == "unmet":
        data.demand_dom["C", "P", "t"] = 12
        expected = 150 + 2 * 1000
    elif kind == "static":
        data.demand_dom["C", "P", "t"] = 0
        data.static_capacity["W"] = 6
        expected = 90 + 10 * 2 + 4 * 2000
    else:
        data.reception_capacity["W"] = 6 / 30
        expected = 150 + 4 * 3000
    result = solve_model(data, ModelConfig(), qualified_solver(backend))
    assert result.objective_value == pytest.approx(expected)
    assert_validation(data, ModelConfig(), result)
    assert set(result.cost_breakdown) >= {"unmet_demand", "emergency_static", "emergency_reception"}
    assert {r["capacity_type"] for r in result.emergency_capacity} <= {"static", "reception"}


@pytest.mark.parametrize("backend", ["gurobipy", "pyscipopt"])
def test_expected_cost_uses_unequal_probabilities(backend):
    data = scenario_data(economic_data(), {"low": 0.25, "high": 0.75})
    data.supply_s["high", "O", "P", "t"] = 20
    data.demand_dom_s["high", "C", "P", "t"] = 20
    result = solve_model(data, ModelConfig(mode="sto"), qualified_solver(backend))
    assert result.objective_value == pytest.approx(0.25 * 150 + 0.75 * 300)
    assert_validation(data, ModelConfig(mode="sto"), result)


@pytest.mark.parametrize("backend", ["gurobipy", "pyscipopt"])
def test_duplicate_scenario_split_keeps_investment_once(backend):
    data = economic_data()
    data.existing_warehouses = []
    data.candidate_warehouses = ["W"]
    data.static_capacity = {"W": 0}
    data.reception_capacity = {"W": 0}
    data.shipping_capacity = {"W": 0}
    data.max_candidate_capacity = {"W": 100}
    data.opening_fixed_cost = {"W": 7}
    data.candidate_capacity_cost = {"W": 5}
    solver = qualified_solver(backend)
    config = ModelConfig(mode="sto", days_per_period=1)
    single = scenario_data(data, {"one": 1.0})
    split = scenario_data(data, {"a": 0.2, "b": 0.3, "c": 0.5})
    first = solve_model(single, config, solver)
    duplicated = solve_model(split, config, solver)
    # Throughput gain=.2: 10 tonnes need 50 investment tonnes, plus opening.
    assert first.objective_value == pytest.approx(150 + 7 + 50 * 5)
    assert duplicated.objective_value == pytest.approx(first.objective_value)
    assert duplicated.cost_breakdown["opening"] == pytest.approx(7)
    assert duplicated.cost_breakdown["candidate_capacity"] == pytest.approx(250)
    assert_validation(split, config, duplicated)
    corrupted = deepcopy(duplicated)
    corrupted.cost_breakdown["opening"] *= 3
    assert (
        validate_solution(prepare_model_data(split, config), config, corrupted)["status"]
        == "rejected"
    )


@pytest.mark.parametrize("backend", ["gurobipy", "pyscipopt"])
def test_timeout_without_incumbent_is_not_a_feasible_solution(backend):
    result = OptimizationResult(status="time_limit", solver_backend=backend)
    assert not result.has_solution


@pytest.mark.parametrize("objective", [float("inf"), float("nan"), -float("inf")])
def test_nonfinite_objective_is_not_a_usable_incumbent(objective):
    assert not OptimizationResult(status="feasible", objective_value=objective).has_solution


def test_archived_modules_cannot_leak_from_another_editable_install():
    import importlib.util

    import src

    assert list(src.__path__) == [str(Path(__file__).resolve().parents[1] / "src")]
    assert importlib.util.find_spec("src.logic.stochastic_analysis_gurobipy") is None
    assert importlib.util.find_spec("src.logic.scip_lexicographic") is None


@pytest.mark.parametrize("backend", ["gurobipy", "pyscipopt"])
@pytest.mark.parametrize("mode", ["det", "sto"])
def test_real_excel_to_independent_validation_and_closed_artifacts(tmp_path, backend, mode):
    import json

    from src.logic.excel_loader import ExcelLoaderConfig
    from src.logic.experiment_runner import ExperimentSpec, run_experiment
    from src.logic.run_integrity import verify_completion
    from tests.test_excel_loader import build_tiny_golden_excel

    workbook = tmp_path / "input.xlsx"
    build_tiny_golden_excel(workbook)
    spec = ExperimentSpec(
        "excel",
        workbook,
        loader=ExcelLoaderConfig(include_stochastic_scenarios=True),
        model=ModelConfig(mode=mode),
        solver=qualified_solver(backend),
    )
    summary = run_experiment(spec, tmp_path / "results", progress=lambda *_: None)
    run = tmp_path / "results/excel"
    result = json.loads((run / "result.json").read_text())
    assert summary.independent_validation_status == "accepted"
    assert result["schema_version"] == 2
    assert verify_completion(run, result["result"]["metadata"]["run_identity"])[0]
    assert not (run / "lexicographic_stages.csv").exists()
    assert not (run / "evpi_vss_decomposition.csv").exists()
    original = (run / "run_completion.json").read_bytes()
    with pytest.raises(FileExistsError):
        run_experiment(spec, tmp_path / "results", progress=lambda *_: None)
    assert (run / "run_completion.json").read_bytes() == original


@pytest.mark.parametrize("removed", ["calculate_evpi_vss", "resume_evpi_vss"])
def test_removed_manifest_options_are_not_silently_ignored(tmp_path, removed):
    from src.logic.experiment_runner import load_experiment_manifest

    path = tmp_path / "manifest.yaml"
    path.write_text(
        "version: 2\nexperiments:\n  - name: bad\n    workbook: absent.xlsx\n"
        f"    {removed}: false\n"
    )
    with pytest.raises(ValueError, match="archived experiment fields"):
        load_experiment_manifest(path)


def test_version_one_is_not_silently_migrated(tmp_path):
    from src.logic.experiment_runner import load_experiment_manifest

    path = tmp_path / "old.yaml"
    path.write_text("version: 1\nexperiments: [{name: old, workbook: absent.xlsx}]\n")
    with pytest.raises(ValueError, match="manifest version"):
        load_experiment_manifest(path)


def test_npad_batch_optimization_is_blocked_before_loading(monkeypatch, tmp_path):
    from scripts.run_batch_hpc import main

    monkeypatch.setenv("SLURM_JOB_ID", "123")
    with pytest.raises(SystemExit, match="R1 scalar software only"):
        main([str(tmp_path / "does-not-exist.yaml")])
    assert not list(tmp_path.iterdir())


def test_inspection_cannot_overwrite_existing_evidence(tmp_path):
    from src.logic.experiment_runner import ExperimentSpec, inspect_experiment

    directory = tmp_path / "preserved"
    directory.mkdir()
    audit = directory / "model_audit.json"
    audit.write_bytes(b"original certificate\n")
    spec = ExperimentSpec("preserved", tmp_path / "absent.xlsx")
    with pytest.raises(FileExistsError, match="Preserve existing evidence"):
        inspect_experiment(spec, tmp_path)
    assert audit.read_bytes() == b"original certificate\n"


def test_historical_results_cannot_receive_a_scalar_reaudit(tmp_path):
    from src.logic.experiment_runner import ExperimentSpec, audit_existing_run

    directory = tmp_path / "historical"
    directory.mkdir()
    result = directory / "result.json"
    result.write_text('{"schema_version":1}\n')
    spec = ExperimentSpec("historical", tmp_path / "absent.xlsx")
    with pytest.raises(ValueError, match="Historical result schema"):
        audit_existing_run(spec, tmp_path)
    assert sorted(p.name for p in directory.iterdir()) == ["result.json"]
    assert result.read_text() == '{"schema_version":1}\n'


@pytest.mark.parametrize(
    "incumbent,bound,expected",
    [
        (100.0, 80.0, 0.2),
        (-100.0, -120.0, 0.2),
        (0.0, 0.0, 0.0),
        (0.0, -1.0, None),
        (None, 0.0, None),
        (1.0, None, None),
        (float("inf"), 0.0, None),
        (1.0, float("nan"), None),
        (1.0, 2.0, None),
    ],
)
def test_scalar_gap_preserves_missing_zero_and_invalid_bound_cases(incumbent, bound, expected):
    actual = scalar_mip_gap(incumbent, bound)
    assert actual is None if expected is None else actual == pytest.approx(expected)


@pytest.mark.parametrize(
    "native,incumbent,expected",
    [
        ("optimal", True, "optimal"),
        ("gaplimit", True, "feasible"),
        ("timelimit", True, "time_limit"),
        ("timelimit", False, "time_limit"),
        ("infeasible", False, "infeasible"),
        ("memlimit", False, "error"),
    ],
)
def test_scip_status_keeps_incumbent_and_native_termination_distinct(native, incumbent, expected):
    from src.logic.optimization_scip import _scalar_status

    assert _scalar_status(native, incumbent) == expected
