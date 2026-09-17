"""Controlled numerical changes, observational telemetry and licensed parity."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts import prepare_stagewise_campaign as preparation
from scripts.prepare_nine_scenario_campaign import campaign
from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.solver_diagnostics import SolverDiagnostics, configure_stages


@pytest.mark.parametrize("case", preparation.CASES)
def test_preparer_preserves_science_and_selects_only_unresolved_cases(tmp_path, monkeypatch, case):
    baseline, workbook, original = fixture_campaign(tmp_path, monkeypatch, case)
    target = tmp_path / "new"
    output = preparation.prepare(baseline, target, case)
    observed = yaml.safe_load(output.read_text())
    _, index, role = preparation.CASES[case]
    assert observed["defaults"]["solver"].pop("multiobjective_stage_options") == {
        role: {"Method": 2}
    }
    assert observed["defaults"]["solver"].pop("collect_solver_diagnostics") is True
    # The generator has no overrides for time, gap, threads, tolerances or equations.
    observed["experiments"][0]["name"] = original["experiments"][index]["name"]
    observed["output_dir"] = original["output_dir"]
    original["experiments"] = [original["experiments"][index]]
    assert observed == original
    assert preparation.sha256(workbook) == preparation.BASELINES[preparation.CASES[case][0]][1]
    receipt = json.loads((target / "stagewise_contract.json").read_text())
    assert receipt["target_stage"] == role
    assert receipt["manifest_sha256"] == preparation.sha256(output)
    preparation.verify_prepared(output)
    with pytest.raises(FileExistsError):
        preparation.prepare(baseline, target, case)


def fixture_campaign(tmp_path, monkeypatch, case="h400-direct"):
    population, _, _ = preparation.CASES[case]
    workbook = tmp_path / "input.xlsx"
    workbook.write_bytes(b"fixture-only")
    old = tmp_path / "old"
    old.mkdir()
    source = campaign(
        Path(__file__).resolve().parents[1],
        old / "runs",
        populations=(population,),
        workbook_overrides={population: workbook},
        max_estimated_variables=43000000,
        resource_review_note="Test-only reviewed guard.",
    )
    baseline = old / "campaign.yaml"
    baseline.write_text(yaml.safe_dump(source))
    monkeypatch.setitem(
        preparation.BASELINES,
        population,
        (preparation.sha256(baseline), preparation.sha256(workbook)),
    )
    return baseline, workbook, source


@pytest.mark.parametrize("change", ["manifest", "workbook", "nested", "missing_evidence"])
def test_preparer_rejects_unsafe_inputs(tmp_path, monkeypatch, change):
    baseline, workbook, _ = fixture_campaign(tmp_path, monkeypatch)
    target = tmp_path / "new"
    profile = "barrier"
    if change == "manifest":
        baseline.write_text(baseline.read_text() + "\n")
    elif change == "workbook":
        workbook.write_bytes(b"changed")
    elif change == "nested":
        target = baseline.parent / "nested"
    else:
        profile = "primal"
    with pytest.raises(ValueError):
        preparation.prepare(baseline, target, "h400-direct", profile)
    assert not target.exists()


@pytest.mark.parametrize("profile", ["barrier-sparse", "primal"])
def test_followup_requires_same_case_barrier_evidence(tmp_path, monkeypatch, profile):
    baseline, _, _ = fixture_campaign(tmp_path, monkeypatch)
    previous = tmp_path / "result.json"
    previous.write_text(
        json.dumps(
            {
                "experiment": {"name": "nine_h400_p20_direct_gurobi_stage_barrier"},
                "result": {
                    "metadata": {
                        "solver_diagnostics": {
                            "effective_stage_parameters": {"emergency_capacity": {"Method": 2}}
                        }
                    }
                },
            }
        )
    )
    output = preparation.prepare(
        baseline,
        tmp_path / "new",
        "h400-direct",
        profile,
        previous,
        "Reviewed capacity root memory evidence.",
    )
    actual = yaml.safe_load(output.read_text())
    assert actual["defaults"]["solver"]["multiobjective_stage_options"] == {
        "emergency_capacity": preparation.PROFILES[profile]
    }
    previous.write_text(previous.read_text().replace("h400", "h300"))
    with pytest.raises(ValueError, match="same case"):
        preparation.prepare(baseline, tmp_path / "bad", "h400-direct", profile, previous, "reason")


@pytest.mark.parametrize(
    "options",
    [
        None,
        [],
        {"unmet_demand": {"Method": 2}},
        {"emergency_capacity": {"Method": 1}},
        {"economic_cost": {"TimeLimit": 100}},
        {"economic_cost": {"MIPGap": 0.2}},
        {"economic_cost": {"Method": True}},
        {"economic_cost": {"Method": "2"}},
        {"economic_cost": {}},
        {"economic_cost": {"PreSparsify": 3}},
    ],
)
def test_stage_parameter_scope_is_strict(options):
    with pytest.raises(ValueError):
        SolverConfig(multiobjective_stage_options=options)


def test_backend_and_bool_validation():
    with pytest.raises(ValueError):
        SolverConfig(backend="pyscipopt", solver_name="scip", collect_solver_diagnostics=True)
    with pytest.raises(ValueError):
        SolverConfig(collect_solver_diagnostics="yes")


@pytest.mark.parametrize("change", ["output", "source", "manifest", "workbook"])
def test_launch_contract_rechecks_input_and_code(tmp_path, monkeypatch, change):
    baseline, workbook, _ = fixture_campaign(tmp_path, monkeypatch)
    output = preparation.prepare(baseline, tmp_path / "new", "h400-direct")
    if change == "output":
        (output.parent / "runs").mkdir()
    elif change == "source":
        monkeypatch.setattr(preparation, "protocol_source_sha256", lambda: "changed")
    elif change == "manifest":
        output.write_text(output.read_text() + "\n")
    else:
        workbook.write_bytes(b"changed")
    with pytest.raises(ValueError):
        preparation.verify_prepared(output)


def test_environments_change_only_requested_pass():
    calls = []
    model = SimpleNamespace(
        getMultiobjEnv=lambda index: SimpleNamespace(
            setParam=lambda name, value: calls.append((index, name, value))
        )
    )
    configure_stages(
        model,
        {"economic_cost": {"Method": 2}},
        ("unmet_demand", "emergency_capacity", "economic_cost"),
    )
    assert calls == [(2, "Method", 2)]
    with pytest.raises(ValueError):
        configure_stages(model, {}, ("unmet_demand", "economic_cost"))


class FakeModel:
    NumConstrs, NumVars, DNumNZs, NumGenConstrs = 10, 100, 500, 2
    MemUsed, MaxMemUsed = 2, 3

    def __init__(self):
        self.values = {}

    def update(self):
        pass

    def getParamInfo(self, name):
        return name, int, {"Method": -1, "TimeLimit": 28800}.get(name, 0), 0, 0, 0

    def cbGet(self, code):
        return self.values[code]


def telemetry_fixture():
    codes = (
        "MESSAGE",
        "MSG_STRING",
        "MULTIOBJ",
        "MULTIOBJ_OBJCNT",
        "MULTIOBJ_RUNTIME",
        "MULTIOBJ_STATUS",
        "MIP",
        "SIMPLEX",
        "BARRIER",
        "PRESOLVE",
        "POLLING",
        "RUNTIME",
        "MEMUSED",
        "MAXMEMUSED",
        "MIP_OBJBST",
        "MIP_OBJBND",
        "MIP_NODCNT",
        "MIP_ITRCNT",
        "MIP_CUTCNT",
    )
    cb = SimpleNamespace(**{code: code for code in codes})
    model = FakeModel()
    clock = [0.0]
    observer = SolverDiagnostics(model, cb, {}, clock=lambda: clock[0])
    model.values = dict.fromkeys(codes, 0.0)
    return model, cb, clock, observer


def test_matrix_observation_and_stage_assignment():
    model, cb, _, observer = telemetry_fixture()
    model.values[cb.MSG_STRING] = "Presolved: 1,000 rows, 20,000 columns, 60,000 nonzeros\n"
    observer.observe(model, cb.MESSAGE)
    model.values[cb.MSG_STRING] = (
        "Multi-objectives: optimize objective 2 (minimize_emergency_capacity) ...\n"
        "Presolved: 998 rows, 19,999 columns, 59,999 nonzeros\n"
        "Factor NZ : 1.6e+08\n"
    )
    observer.observe(model, cb.MESSAGE)
    result = observer.finish(model)
    assert result["matrix_observations"][0]["scope"] == "global_presolve"
    assert result["matrix_observations"][1]["stage_role"] == "emergency_capacity"
    assert result["matrix_observations"][1]["nonzeros"] == 59999
    assert len(result["root_events"]) == 1
    assert result["original_matrix"]["general_constraints"] == 2


def test_sampling_missing_values_and_no_false_zero_gap():
    model, cb, clock, observer = telemetry_fixture()
    observer.stage = 2
    model.values[cb.MIP_OBJBST] = 1e100
    observer.observe(model, cb.MIP)
    observer.observe(model, cb.MIP)
    assert len(observer.progress) == 1
    assert observer.progress[0]["incumbent"] is None
    assert observer.progress[0]["relative_gap"] is None
    clock[0] = 31
    model.values[cb.MIP_OBJBST], model.values[cb.MIP_OBJBND] = 100, 20
    observer.observe(model, cb.MIP)
    assert observer.progress[-1]["relative_gap"] == 0.8
    model.values[cb.MULTIOBJ_OBJCNT] = 2
    observer.observe(model, cb.MULTIOBJ)
    assert len(observer.progress) == 3
    assert observer.progress[-1]["event"] == "MULTIOBJ"
    assert observer.finish(model)["status"] == "recorded_with_missing_fields"
    # A missing callback field is explicit, not fabricated numerical evidence.
    json.dumps(observer.finish(model), allow_nan=False)


def test_observation_failure_does_not_interrupt_solver_callback():
    model, cb, _, observer = telemetry_fixture()
    model.values[cb.MSG_STRING] = None
    observer.observe(model, cb.MESSAGE)
    result = observer.finish(model)
    assert result["status"] == "recorded_with_missing_fields"
    assert result["matrix_observation_status"] == "not_observed"


def test_diagnostics_export_is_bound_to_completion_receipt(tmp_path):
    from src.logic.experiment_runner import run_experiment
    from tests.test_experiment_runner import experiment, fake_loader, solved_result

    model, cb, _, observer = telemetry_fixture()
    model.values[cb.MSG_STRING] = "Presolved: 8 rows, 15 columns, 30 nonzeros"
    observer.observe(model, cb.MESSAGE)
    observer.observe(model, cb.MIP)
    result = solved_result()
    result.metadata["solver_diagnostics"] = observer.finish(model)
    run_experiment(experiment(), tmp_path, loader=fake_loader, solver=lambda **_: result)
    run = tmp_path / "det_baseline"
    receipt = json.loads((run / "run_completion.json").read_text())
    for name in (
        "solver_diagnostics.json",
        "solver_stage_progress.csv",
        "solver_presolved_matrix.csv",
    ):
        assert receipt["artifacts"][name] == preparation.sha256(run / name)


@pytest.mark.parametrize("role", ["emergency_capacity", "economic_cost"])
def test_licensed_stagewise_parity(role):
    from src.logic.optimization import solve_model
    from tests.test_gurobipy_stochastic import two_scenario_data
    from tests.test_gurobipy_transshipment import require_gurobi_available

    require_gurobi_available()
    config = ModelConfig(
        mode="sto", objective_policy="lexicographic", days_per_period=1, allow_bulkification=False
    )
    solver = SolverConfig(threads=1, time_limit=30, mip_gap=0, tee=True)
    reference = solve_model(two_scenario_data(), config, solver)
    changed = copy.deepcopy(solver)
    changed.multiobjective_stage_options = {role: {"Method": 2}}
    changed.collect_solver_diagnostics = True
    result = solve_model(two_scenario_data(), config, changed)
    assert result.status == reference.status == "optimal"
    assert result.metadata["lexicographic_overall_status"] == "complete"
    diagnostic = result.metadata["solver_diagnostics"]
    assert diagnostic["effective_stage_parameters"][role]["Method"] == 2
    assert diagnostic["effective_stage_parameters"]["unmet_demand"]["Method"] == -1
    terminal = [row for row in diagnostic["progress"] if row["event"] == "MULTIOBJ"]
    assert [row["stage_number"] for row in terminal] == [1, 2, 3]
    assert not diagnostic["unavailable_callback_fields"]
    for observed, original in zip(
        result.metadata["lexicographic_stages"],
        reference.metadata["lexicographic_stages"],
        strict=True,
    ):
        assert observed["objective_value"] == pytest.approx(original["objective_value"], abs=1e-5)
