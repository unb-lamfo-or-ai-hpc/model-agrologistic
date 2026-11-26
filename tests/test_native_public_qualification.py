"""Public native qualification preparation and analytical vectors; no native execution."""

import copy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from scripts import qualify_mvp3_native as cli
from src.logic.mathematical_contract import extensive_form_inputs
from src.logic.model_lifecycle import managed_model_solve
from src.logic.native_effective import (
    finish_effective_result,
    prepare_effective_native,
    reference_solver_config,
)
from src.logic.native_public_controls import (
    check_native_environment,
    control_specs,
    expected,
    make_control,
    public_solver_config,
)
from src.logic.optimization import OptimizationResult
from src.logic.optimization_gurobipy_stochastic import create_native_model, populate_native_model
from src.logic.solution_validation import COST_NAMES
from tests.test_effective_policy import export_data
from tests.test_native_effective import GP, GRB, SymbolicNativeModel


def test_public_catalog_has_no_thread_factorial_or_private_case():
    controls = control_specs()
    assert len(controls) == len({s["id"] for s in controls}) == 32
    assert all(s["id"].startswith("public-native-") for s in controls)
    assert public_solver_config().time_limit == 60
    assert reference_solver_config().time_limit == 28800
    assert cli.LIMITS == {"models": 32, "native_seconds_each": 60, "wall_seconds": 2700,
                          "workers": 1, "Method": -1, "Threads": 0}


@pytest.mark.parametrize("control", control_specs(), ids=lambda c: c["id"])
def test_public_controls_reach_actual_native_construction_without_solver(control):
    data, cfg = make_control(control["id"])
    solver = public_solver_config()
    context = prepare_effective_native(data, cfg, solver)
    native_data, native_cfg = extensive_form_inputs(data, cfg)
    model = SymbolicNativeModel()
    populate_native_model(GP, GRB, model, native_data, native_cfg, solver,
                          effective_context=context)
    assert sum(map(len, model.variables.values())) <= 128
    assert len(model.constraints) <= 256
    assert len(native_data.scenarios) == (9 if control["mode"] == "sto" else 1)
    target = expected(control)
    if target["classification"] == "infeasible":
        largest = max(native_data.supply_s.values())
        ceiling = data.max_candidate_capacity.get("W", data.max_expand_capacity.get("W"))
        hard_shipping = 0 if control["kind"] == "blocked" else ceiling * 6
        beta = control["beta"]
        assert largest * beta > hard_shipping
        return
    installed = target["installed_t"]
    costs = dict.fromkeys(COST_NAMES, 0.0)
    costs["candidate_capacity" if control["kind"] == "candidate" else "expansion_variable"] = (
        installed * (1250 if control["kind"] == "candidate" else 900))
    result = OptimizationResult(
        status="optimal", objective_value=target["objective"], cost_breakdown=costs,
        warehouse_decisions=[{"warehouse": "W", "open": 1, "candidate_capacity": (
            installed if control["kind"] == "candidate" else 0),
            "expand": int(control["kind"] == "expansion"), "expansion_capacity": (
            installed if control["kind"] == "expansion" else 0), "bulkify": 0, "bulk_capacity": 0}],
    )
    scenarios = data.scenarios if cfg.mode == "sto" else [None]
    for i, scenario in enumerate(scenarios):
        factor = 0.5 + i / 8 if cfg.mode == "sto" else 1
        prefix = {"scenario": scenario} if cfg.mode == "sto" else {}
        export = target["expected_export_t"] * factor
        served = 10 * factor - export
        for kind, a, b, tonnes in (("OD", "O", "W", 10*factor),
                                    ("DC", "W", "C", served), ("DC", "W", "X", export)):
            endpoints = {"origin": a, "warehouse": b} if kind == "OD" else {
                "warehouse": a, "customer": b}
            result.flows.append({**prefix, **endpoints, "route_type": kind, "product": "P",
                                 "period": "t", "value": tonnes})
        result.inventories.append({**prefix, "warehouse": "W", "product": "P", "period": "t",
                                   "value": 0})
        result.unmet_demand.append({**prefix, "customer": "C", "product": "P", "period": "t",
                                    "value": export})
        result.emergency_capacity += [{**prefix, "warehouse": "W", "period": "t",
                                       "capacity_type": k, "value": 0}
                                      for k in ("static", "reception")]
        probability = 1/9 if cfg.mode == "sto" else 1
        costs["transport_od"] += probability * 90 * factor
        costs["transport_dc"] += probability * (2000 * served + 8 * export)
        costs["unmet_demand"] += probability * 1000 * export
    assert sum(costs.values()) == pytest.approx(target["objective"])
    finish_effective_result(context, result)
    assert result.metadata["effective_validation"]["status"] == "accepted"
    assert result.metadata["effective_dense_coverage"]["status"] == "accepted"
    # These values are analytical test vectors, never an observed native certificate.
    assert not cli.accept_result(control, result)
    # Exercise the receipt gate with a clearly artificial metadata double.
    receipt = copy.deepcopy(result)
    receipt.metadata.update(certificate_double(2))
    assert cli.accept_result(control, receipt)
    receipt.objective_value += 1
    assert not cli.accept_result(control, receipt)


def certificate_double(status):
    return {"gurobi_status_code": status,
            "native_model_lifecycle": [{"status": "disposed"}],
            "effective_native_parameters": {"full_public_default_audit": {
                "checked": 102, "nondefaults": ["OutputFlag", "TimeLimit"]}},
            "matrix": {"variables": 10, "constraints": 20}}


def test_infeasible_receipt_requires_native_status_and_no_objective():
    control = next(c for c in control_specs() if c["kind"] == "blocked")
    result = OptimizationResult(status="infeasible", metadata=certificate_double(3))
    assert cli.accept_result(control, result)
    result.metadata["gurobi_status_code"] = 4  # INF_OR_UNBD is not an infeasibility proof.
    assert not cli.accept_result(control, result)
    result.metadata["gurobi_status_code"] = 3
    result.objective_value = 0
    assert not cli.accept_result(control, result)


def test_public_budget_rejects_private_or_mutated_fixture_before_native_import():
    data, cfg = export_data()
    with pytest.raises(ValueError, match="Unknown public"):
        prepare_effective_native(data, cfg, public_solver_config())
    data, cfg = make_control(control_specs()[0]["id"])
    altered = copy.deepcopy(data)
    altered.shipping_capacity["W"] += 1
    with pytest.raises(ValueError, match="differs"):
        prepare_effective_native(altered, cfg, public_solver_config())
    with pytest.raises(ValueError, match="Rev4 automatic"):
        prepare_effective_native(data, cfg, replace(reference_solver_config(), time_limit=60))


@pytest.mark.parametrize("public", [False, True])
def test_environment_ownership_is_explicit_and_disposed(public):
    calls = []
    environment = object() if public else None
    config = public_solver_config() if public else reference_solver_config()
    check_native_environment(config, environment)
    with pytest.raises(ValueError, match="owned environment"):
        check_native_environment(config, None if public else object())

    def factory(name, **kwargs):
        calls.append((name, kwargs))
        return SimpleNamespace(dispose=lambda: calls.append("disposed"))

    @managed_model_solve
    def construction_only():
        create_native_model(SimpleNamespace(Model=factory), environment)
        return SimpleNamespace(metadata={})

    assert construction_only().metadata["native_model_lifecycle"][0]["status"] == "disposed"
    assert calls[0][1] == ({"env": environment} if public else {})
    assert calls[-1] == "disposed"


def prepared(tmp_path, monkeypatch):
    claim = tmp_path / "claim"
    source = claim / "source"
    (source / "scripts").mkdir(parents=True)
    (source / "src").mkdir()
    raw = b"# Frozen test source; never executed.\n"
    (source / "scripts/qualify_mvp3_native.py").write_bytes(raw)
    plan = cli.plan_record("a" * 40, {"scripts/qualify_mvp3_native.py": raw})
    cli.write_new(claim / "plan.json", plan)
    monkeypatch.setattr(cli, "ROOT", source)
    return claim, plan, cli.sha(cli.encoded(plan))


def test_plan_is_source_bound_and_cannot_enable_execution_or_expand_budget(tmp_path, monkeypatch):
    claim, plan, digest = prepared(tmp_path, monkeypatch)
    assert cli.verify_plan(claim, digest)[1]["execution_authorized"] is False
    plan["limits"]["native_seconds_each"] = 28800
    (claim / "plan.json").write_bytes(cli.encoded(plan))
    with pytest.raises(ValueError, match="scope differs"):
        cli.verify_plan(claim, cli.sha(cli.encoded(plan)))
    assert cli.LIMITS["native_seconds_each"] == 60


def test_source_drift_is_rejected_before_any_native_action(tmp_path, monkeypatch):
    claim, _, digest = prepared(tmp_path, monkeypatch)
    (claim / "source/scripts/qualify_mvp3_native.py").write_bytes(b"changed")
    with pytest.raises(ValueError, match="identity differs"):
        cli.verify_plan(claim, digest)


def test_missing_ack_and_consumed_claim_never_start_worker(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="acknowledgement"):
        cli.execute(tmp_path, "a"*64, "")
    claim, _, digest = prepared(tmp_path, monkeypatch)
    monkeypatch.setattr(cli.importlib.metadata, "version", lambda _: "14.0.0")
    original = b"original consumed start"
    (claim / "started.json").write_bytes(original)
    with pytest.raises(FileExistsError):
        cli.execute(claim, digest, cli.ACK)
    assert (claim / "started.json").read_bytes() == original


def test_owned_worker_timeout_preserves_consumed_claim(tmp_path, monkeypatch):
    claim, _, digest = prepared(tmp_path, monkeypatch)
    monkeypatch.setattr(cli.importlib.metadata, "version", lambda _: "14.0.0")

    def timeout(*args, **kwargs):
        assert kwargs["timeout"] == 2700
        raise cli.subprocess.TimeoutExpired(["owned-public-worker"], 2700)

    monkeypatch.setattr(cli.subprocess, "run", timeout)
    result = cli.execute(claim, digest, cli.ACK)
    assert result["status"] == "owned_worker_wall_timeout"
    assert cli.read(claim / "terminal.json")["claim_consumed"] is True


def test_collector_rejects_duplicate_or_missing_controls(tmp_path, monkeypatch):
    claim, _, _ = prepared(tmp_path, monkeypatch)
    cli.write_new(claim / "worker-result.json", {"status": "accepted", "engine_code": {"x": "hash"},
                  "records": [{"id": control_specs()[0]["id"]}] * 32})
    with pytest.raises(ValueError, match="inventory"):
        cli.verify_worker_report(claim)


def test_public_defaults_audit_does_not_read_connection_values():
    names = [f"SoftwareParameter{i}" for i in range(100)] + ["OutputFlag", "TimeLimit", "WLSSecret"]
    parameters = type("Parameters", (), {n: n for n in names})
    calls = []

    def info(name):
        calls.append(name)
        assert name != "WLSSecret"
        current = {"TimeLimit": 60, "OutputFlag": 0}.get(name, 0)
        default = {"TimeLimit": float("inf"), "OutputFlag": 1}.get(name, 0)
        return name, float, current, 0, 1e100, default

    report = cli.full_default_audit(SimpleNamespace(getParamInfo=info),
                                    SimpleNamespace(Param=parameters))
    assert report["checked"] == 102 and "WLSSecret" not in calls
    assert report["connection_parameter_values_read_or_exported"] is False


def test_incomplete_native_certificate_cannot_be_accepted():
    result = OptimizationResult(status="optimal", objective_value=10170)
    assert not cli.accept_result(control_specs()[0], result)
    with pytest.raises(ValueError, match="source commit"):
        cli.source_snapshot("--not-a-revision")
