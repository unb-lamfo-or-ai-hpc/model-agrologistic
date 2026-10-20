import csv
import json
from pathlib import Path

import pytest

from scripts.run_batch_hpc import selected_index
from src.logic.excel_loader import ExcelLoaderConfig
from src.logic.experiment_runner import (
    ExperimentManifest,
    ExperimentSpec,
    _scenario_performance_records,
    _weighted_record_total,
    aggregate_experiment_summaries,
    audit_existing_run,
    estimate_model_size,
    inspect_manifest,
    load_experiment_manifest,
    run_experiment,
    run_manifest,
)
from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import OptimizationResult


def model_data() -> ModelData:
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
        periods=["t1", "t2"],
        static_capacity={"W1": 100.0},
    )


def solved_result() -> OptimizationResult:
    return OptimizationResult(
        status="optimal",
        objective_value=123.0,
        solver_backend="gurobipy",
        solver_name="gurobi",
        model_mode="det",
        runtime_seconds=4.5,
        mip_gap=0.0,
        cost_breakdown={"transport": 123.0},
        warehouse_decisions=[
            {
                "warehouse": "W1",
                "open": 1.0,
                "candidate_capacity": 0.0,
                "expansion_capacity": 0.0,
                "bulk_capacity": 0.0,
            }
        ],
        flows=[
            {
                "route_type": "DC",
                "warehouse": "W1",
                "customer": "C1",
                "customer_type": "domestic",
                "product": "soy",
                "period": "t2",
                "value": 80.0,
            }
        ],
        inventories=[
            {
                "warehouse": "W1",
                "product": "soy",
                "period": "t2",
                "value": 20.0,
            }
        ],
        unmet_demand=[
            {
                "customer": "C1",
                "product": "soy",
                "period": "t1",
                "value": 5.0,
            }
        ],
        emergency_capacity=[
            {
                "warehouse": "W1",
                "period": "t1",
                "capacity_type": "static",
                "value": 10.0,
            },
            {
                "warehouse": "W1",
                "period": "t2",
                "capacity_type": "reception",
                "value": 20.0,
            },
        ],
        metrics={
            "objective_values": {
                "economic_cost": 123.0,
                "penalized_cost": 5_000_123.0,
            }
        },
        metadata={
            "timings": {
                "model_build_seconds": 1.25,
                "optimization_seconds": 3.25,
            }
        },
    )


def experiment(name: str = "det_baseline") -> ExperimentSpec:
    return ExperimentSpec(
        name=name,
        workbook=Path("input.xlsx"),
        loader=ExcelLoaderConfig(),
        model=ModelConfig(mode="det"),
        solver=SolverConfig(),
        metadata={"replicate": 1},
    )


def fake_loader(_path, _config):
    return model_data()


def fake_solver(**_kwargs):
    return solved_result()


def test_stochastic_diagnostic_totals_are_probability_weighted():
    result = OptimizationResult(
        status="optimal",
        objective_value=0.0,
        unmet_demand=[
            {"scenario": "low", "value": 10.0},
            {"scenario": "high", "value": 30.0},
        ],
        emergency_capacity=[
            {"scenario": "low", "capacity_type": "static", "value": 4.0},
            {"scenario": "high", "capacity_type": "static", "value": 12.0},
        ],
        metadata={"scenario_probabilities": {"low": 0.75, "high": 0.25}},
    )

    assert _weighted_record_total(result, result.unmet_demand) == pytest.approx(15.0)
    assert _weighted_record_total(
        result,
        result.emergency_capacity,
        capacity_type="static",
    ) == pytest.approx(6.0)


def test_scenario_performance_records_are_unweighted_and_complete():
    result = OptimizationResult(
        status="optimal",
        objective_value=0.0,
        flows=[
            {
                "scenario": "low",
                "route_type": "OC",
                "customer_type": "domestic",
                "value": 60.0,
            },
            {
                "scenario": "low",
                "route_type": "DC",
                "customer_type": "domestic",
                "value": 20.0,
            },
        ],
        unmet_demand=[{"scenario": "low", "value": 20.0}],
        emergency_capacity=[
            {
                "scenario": "low",
                "capacity_type": "static",
                "value": 3.0,
            },
            {
                "scenario": "low",
                "capacity_type": "reception",
                "value": 2.0,
            },
        ],
        metrics={
            "scenario_metrics": {
                "low": {
                    "probability": 0.25,
                    "operating_cost": 123.0,
                    "total_flow": 80.0,
                }
            },
            "storage": {
                "scenario_metrics": {
                    "low": {
                        "dynamic_capacity": 45.0,
                        "turnover": 1.5,
                    }
                }
            },
        },
        metadata={"scenario_probabilities": {"low": 0.25}},
    )

    records = _scenario_performance_records(result)

    assert len(records) == 1
    record = records[0]
    assert record["probability"] == pytest.approx(0.25)
    assert record["operating_cost"] == pytest.approx(123.0)
    assert record["total_direct_flow"] == pytest.approx(60.0)
    assert record["total_domestic_demand"] == pytest.approx(100.0)
    assert record["served_domestic_demand"] == pytest.approx(80.0)
    assert record["total_unmet_demand"] == pytest.approx(20.0)
    assert record["domestic_service_level"] == pytest.approx(0.8)
    assert record["emergency_static_capacity"] == pytest.approx(3.0)
    assert record["emergency_reception_capacity"] == pytest.approx(2.0)
    assert record["total_emergency_capacity"] == pytest.approx(5.0)
    assert record["dynamic_capacity"] == pytest.approx(45.0)
    assert record["turnover"] == pytest.approx(1.5)


def test_manifest_loads_defaults_and_resolves_relative_paths(tmp_path):
    workbook = tmp_path / "instance.xlsx"
    workbook.touch()
    manifest_path = tmp_path / "experiments.yaml"
    manifest_path.write_text(
        """
version: 2
output_dir: results
defaults:
  solver:
    time_limit: 90
  loader:
    include_stochastic_scenarios: true
    scenario_generation_mode: cartesian
experiments:
  - name: sto_2
    workbook: instance.xlsx
    model:
      mode: sto
    loader:
      stochastic_combinations:
        - [baixo, baixo]
        - [alto, alto]
      stochastic_probabilities: [0.4, 0.6]
""".strip(),
        encoding="utf-8",
    )

    manifest = load_experiment_manifest(manifest_path)
    spec = manifest.experiments[0]

    assert manifest.output_dir == (tmp_path / "results").resolve()
    assert spec.workbook == workbook.resolve()
    assert spec.solver.time_limit == 90
    assert spec.loader.stochastic_combinations == (
        ("baixo", "baixo"),
        ("alto", "alto"),
    )
    assert spec.loader.stochastic_probabilities == (0.4, 0.6)


def test_manifest_rejects_duplicate_and_unsafe_names(tmp_path):
    manifest_path = tmp_path / "experiments.yaml"
    manifest_path.write_text(
        """
version: 2
experiments:
  - {name: repeated, workbook: a.xlsx}
  - {name: repeated, workbook: b.xlsx}
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unique"):
        load_experiment_manifest(manifest_path)

    with pytest.raises(ValueError, match="Experiment name"):
        experiment("../escape")


def test_stochastic_spec_requires_scenario_loading():
    with pytest.raises(ValueError, match="include_stochastic_scenarios"):
        ExperimentSpec(
            name="invalid_sto",
            workbook=Path("input.xlsx"),
            model=ModelConfig(mode="sto"),
        )


def test_run_experiment_exports_complete_json_csv_and_metrics(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("SLURM_JOB_ID", "12345")
    monkeypatch.setenv("SLURM_ARRAY_TASK_ID", "7")
    summary = run_experiment(
        experiment(),
        tmp_path,
        loader=fake_loader,
        solver=fake_solver,
    )
    run_dir = tmp_path / "det_baseline"
    payload = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    preflight = json.loads((run_dir / "preflight.json").read_text(encoding="utf-8"))

    assert summary.status == "optimal"
    assert summary.objective_value == pytest.approx(123.0)
    assert summary.objective_policy == "penalty"
    assert summary.scenario_count == 1
    assert summary.economic_cost == pytest.approx(123.0)
    assert summary.penalized_cost == pytest.approx(5_000_123.0)
    assert summary.data_read_seconds is not None
    assert summary.data_read_seconds >= 0.0
    assert summary.model_build_seconds == pytest.approx(1.25)
    assert summary.optimization_seconds == pytest.approx(3.25)
    assert payload["result"]["metadata"]["timings"]["data_read_seconds"] == pytest.approx(
        summary.data_read_seconds
    )
    assert summary.dyn_cap == pytest.approx(600.0)
    assert summary.turnover == pytest.approx(6.0)
    assert summary.total_unmet_demand == pytest.approx(5.0)
    assert summary.total_domestic_demand == pytest.approx(85.0)
    assert summary.served_domestic_demand == pytest.approx(80.0)
    assert summary.domestic_service_level == pytest.approx(80.0 / 85.0)
    assert summary.minimum_scenario_service_level is None
    assert summary.maximum_scenario_service_level is None
    assert summary.total_direct_flow == pytest.approx(0.0)
    assert summary.emergency_static_capacity == pytest.approx(10.0)
    assert summary.emergency_reception_capacity == pytest.approx(20.0)
    assert summary.total_emergency_capacity == pytest.approx(30.0)
    assert summary.capacity_adequacy_status == "domestic_service_shortfall"
    assert summary.material_balance_ok is None
    assert summary.penalty_cost_share == pytest.approx(0.0)
    assert payload["schema_version"] == 2
    assert payload["experiment"]["metadata"] == {"replicate": 1}
    assert payload["result"]["metrics"]["DynCap"] == pytest.approx(600.0)
    assert payload["execution"]["slurm_job_id"] == "12345"
    assert payload["execution"]["slurm_array_task_id"] == "7"
    assert payload["execution"]["python_executable"]
    assert payload["execution"]["package_versions"]["pandas"]
    assert preflight["schema_version"] == 1
    assert preflight["workbook_sha256"] is None
    assert preflight["data_signature"]["counts"] == {
        "candidate_warehouses": 0,
        "domestic_customers": 1,
        "existing_warehouses": 1,
        "export_customers": 0,
        "origins": 1,
        "periods": 2,
        "products": 1,
        "scenarios": 0,
        "warehouses": 1,
    }
    assert preflight["data_signature"]["loader_warning_count"] == 0
    assert preflight["execution"]["package_versions"]["openpyxl"]
    assert summary.slurm_job_id == "12345"
    assert summary.slurm_array_task_id == "7"
    assert "raw_solver_result" not in payload["result"]

    expected_files = {
        "independent_validation.json",
        "run_completion.json",
        "result.json",
        "model_audit.json",
        "preflight.json",
        "run_summary.json",
        "warehouse_decisions.csv",
        "flows.csv",
        "inventories.csv",
        "unmet_demand.csv",
        "emergency_capacity.csv",
        "scenario_performance.csv",
        "storage_by_warehouse.csv",
        "storage_by_scenario.csv",
        "material_balance_by_scenario.csv",
        "capacity_gap_by_scenario.csv",
        "investment_saturation.csv",
        "emergency_capacity_daily.csv",
    }
    assert {path.name for path in run_dir.iterdir()} == expected_files
    assert (run_dir / "scenario_performance.csv").read_text(encoding="utf-8") == ""

    with (run_dir / "capacity_gap_by_scenario.csv").open(encoding="utf-8") as file:
        capacity_rows = list(csv.DictReader(file))
    assert capacity_rows[0]["status"] == "domestic_service_shortfall"

    with (run_dir / "emergency_capacity_daily.csv").open(encoding="utf-8") as file:
        emergency_rows = list(csv.DictReader(file))
    reception = next(row for row in emergency_rows if row["capacity_type"] == "reception")
    assert float(reception["days_in_period"]) == pytest.approx(30.0)
    assert float(reception["value_tons_per_day"]) == pytest.approx(20.0 / 30.0)

    with (run_dir / "storage_by_warehouse.csv").open(encoding="utf-8") as file:
        storage_rows = list(csv.DictReader(file))
    assert storage_rows[0]["warehouse"] == "W1"
    assert float(storage_rows[0]["dynamic_capacity"]) == pytest.approx(600.0)


def test_existing_result_can_be_audited_without_solving_again(tmp_path):
    spec = experiment()
    run_experiment(
        spec,
        tmp_path,
        loader=fake_loader,
        solver=fake_solver,
    )
    audit_path = tmp_path / spec.name / "model_audit.json"
    original = audit_path.read_bytes()

    rebuilt = audit_existing_run(spec, tmp_path, loader=fake_loader)
    audit = json.loads(rebuilt.read_text(encoding="utf-8"))

    assert rebuilt.parent.parent == audit_path.parent
    assert rebuilt.parent.name.startswith('scalar_reaudit_')
    assert audit_path.read_bytes() == original
    assert audit["solution"]["objective_value"] == pytest.approx(123.0)
    assert audit["solution"]["service"]["expected"] == pytest.approx(80.0 / 85.0)


def test_manifest_can_continue_after_a_failed_run(tmp_path):
    manifest = ExperimentManifest(
        experiments=[experiment("fails"), experiment("passes")],
        output_dir=tmp_path,
        continue_on_error=True,
    )
    calls = 0

    def sometimes_fails(**_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("solver unavailable")
        return solved_result()

    summaries = run_manifest(
        manifest,
        loader=fake_loader,
        solver=sometimes_fails,
    )

    assert [summary.status for summary in summaries] == ["error", "optimal"]
    failure = json.loads((tmp_path / "fails" / "run_summary.json").read_text(encoding="utf-8"))
    assert failure["error_type"] == "RuntimeError"
    assert failure["error_message"] == "solver unavailable"
    assert failure["runtime_seconds"] is not None
    assert failure["data_read_seconds"] is None
    assert failure["model_build_seconds"] is None
    assert failure["optimization_seconds"] is None
    assert "peak_rss_mb" in failure


def test_infeasible_result_exports_iis_diagnostic(tmp_path):
    result = OptimizationResult(
        status="infeasible",
        solver_backend="gurobipy",
        solver_name="gurobi",
        model_mode="det",
        metadata={
            "iis_computed": True,
            "iis_constraints": ["supply_balance[O1,soy,t1]"],
            "iis_bounds": [],
        },
    )

    summary = run_experiment(
        experiment("infeasible"),
        tmp_path,
        loader=fake_loader,
        solver=lambda **_kwargs: result,
        progress=lambda _message: None,
    )

    diagnostic = json.loads(
        (tmp_path / "infeasible" / "infeasibility.json").read_text(encoding="utf-8")
    )
    assert summary.status == "infeasible"
    assert diagnostic["iis_computed"] is True
    assert diagnostic["iis_constraints"] == ["supply_balance[O1,soy,t1]"]


def test_selected_indices_support_slurm_array_isolation(tmp_path):
    manifest = ExperimentManifest(
        experiments=[experiment("run_0"), experiment("run_1")],
        output_dir=tmp_path,
    )

    summaries = run_manifest(
        manifest,
        indices=[1],
        loader=fake_loader,
        solver=fake_solver,
    )

    assert [summary.name for summary in summaries] == ["run_1"]
    assert not (tmp_path / "run_0").exists()
    assert (tmp_path / "run_1" / "run_summary.json").is_file()
    assert not (tmp_path / "batch_summary.csv").exists()


def test_aggregate_summaries_builds_one_csv_after_array_completion(tmp_path):
    for name in ("run_0", "run_1"):
        run_experiment(
            experiment(name),
            tmp_path,
            loader=fake_loader,
            solver=fake_solver,
        )

    target = aggregate_experiment_summaries(tmp_path)

    with target.open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert [row["name"] for row in rows] == ["run_0", "run_1"]
    assert all(row["status"] == "optimal" for row in rows)


def test_manifest_rejects_out_of_range_index(tmp_path):
    manifest = ExperimentManifest(
        experiments=[experiment()],
        output_dir=tmp_path,
    )

    with pytest.raises(IndexError, match="valid range"):
        run_manifest(manifest, indices=[1])


def test_preflight_blocks_oversized_run_before_solver(tmp_path):
    spec = experiment("guarded")
    spec.max_estimated_variables = 1
    solver_called = False

    def should_not_solve(**_kwargs):
        nonlocal solver_called
        solver_called = True
        return solved_result()

    with pytest.raises(ValueError, match="above its safety limit"):
        run_experiment(
            spec,
            tmp_path,
            loader=fake_loader,
            solver=should_not_solve,
            progress=lambda _message: None,
        )

    assert solver_called is False
    assert (tmp_path / "guarded" / "preflight.json").is_file()


def test_inspect_manifest_reports_size_without_solving(tmp_path):
    manifest = ExperimentManifest(
        experiments=[experiment("planned")],
        output_dir=tmp_path,
    )

    estimates = inspect_manifest(
        manifest,
        loader=fake_loader,
        progress=lambda _message: None,
    )

    assert estimates[0] == estimate_model_size(model_data(), ModelConfig(mode="det"))
    assert (tmp_path / "planned" / "preflight.json").is_file()
    assert not (tmp_path / "planned" / "result.json").exists()


def test_slurm_array_index_is_used_unless_cli_overrides_it(monkeypatch):
    monkeypatch.setenv("SLURM_ARRAY_TASK_ID", "4")

    assert selected_index(None) == 4
    assert selected_index(2) == 2
