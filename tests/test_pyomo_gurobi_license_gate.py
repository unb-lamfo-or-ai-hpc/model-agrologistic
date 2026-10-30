"""Fault controls for large-arm license admission; no license contents or scheduler."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_pyomo_h215_w as campaign
from scripts import pyomo_gurobi_license_gate as gate


def proof():
    return {
        "schema_version": gate.SCHEMA,
        "status": "accepted",
        "large_model_construction_allowed": True,
        "environment_scope": "gurobipy_default_environment_as_used_by_appsi",
        "probe_variable_count": 2001,
        "probe_constraint_count": 2001,
        "private_input_accessed": False,
        "gurobi_version": [13, 0, 3],
        "solver_status_code": 2,
        "objective_value": 2001,
    }


@pytest.mark.parametrize("job,step", [("", ""), ("123", "batch"), ("0", "0"), ("123", "")])
def test_login_or_non_numeric_step_rejected_without_native_import(monkeypatch, job, step):
    monkeypatch.setenv("SLURM_JOB_ID", job)
    monkeypatch.setenv("SLURM_STEP_ID", step)
    monkeypatch.setattr(gate.policy, "check_file", lambda: pytest.fail("No file access"))
    record = gate.probe()
    assert record["status"] == "rejected"
    assert record["error_type"] == "ValueError"
    assert not gate.accepted(record)


@pytest.mark.parametrize("outcome", ["accepted", "restricted", "wrong_objective", "time_limit"])
def test_default_environment_only_and_credential_output_discarded(monkeypatch, capfd, outcome):
    monkeypatch.setattr(gate, "compute_context", lambda: None)
    monkeypatch.setattr(gate.policy, "check_file", lambda: None)
    events = []

    class NativeError(Exception):
        errno = 10010

    class Model:
        def __init__(self, name):
            # A custom Env argument would fail this constructor signature.
            print("SECRET license initialization")
            self.Params = SimpleNamespace()
            self.Status = 9 if outcome == "time_limit" else 2
            self.SolCount = 1
            self.ObjVal = 2001 if outcome != "wrong_objective" else 1

        def __enter__(self):
            return self

        def __exit__(self, *args):
            events.append("disposed")

        def addVars(self, size, *, lb, ub):
            assert (size, lb, ub) == (2001, 0, 2)
            return dict.fromkeys(range(size), 1)

        def addConstrs(self, rows):
            assert len(list(rows)) == 2001

        def setObjective(self, value, sense):
            assert (value, sense) == (2001, 1)

        def optimize(self):
            settings = (self.Params.OutputFlag, self.Params.TimeLimit, self.Params.Threads)
            assert settings == (0, 10, 1)
            if outcome == "restricted":
                print("SECRET native output")
                raise NativeError("SECRET connection details")

    monkeypatch.setitem(
        sys.modules, "gurobipy",
        SimpleNamespace(
            Model=Model, quicksum=sum, GRB=SimpleNamespace(MINIMIZE=1, OPTIMAL=2),
            gurobi=SimpleNamespace(version=lambda: (13, 0, 3)),
        ),
    )
    record = gate.probe()
    assert gate.accepted(record) == (outcome == "accepted")
    assert events == ["disposed"]
    assert "SECRET" not in json.dumps(record)
    assert "SECRET" not in "".join(capfd.readouterr())
    if outcome == "restricted":
        assert record["error_code"] == 10010


@pytest.mark.parametrize(
    "key,value",
    [
        ("status", "rejected"),
        ("environment_scope", "custom_env"),
        ("large_model_construction_allowed", False),
        ("probe_variable_count", 2000),
        ("probe_constraint_count", 2000),
        ("private_input_accessed", True),
        ("solver_status_code", 9),
        ("objective_value", float("nan")),
        ("gurobi_version", [13, 0, 2]),
        ("error_type", "GurobiError"),
    ],
)
def test_replay_rejects_incomplete_or_wrong_capacity_proof(key, value):
    record = proof()
    assert gate.accepted(record)
    record[key] = value
    assert not gate.accepted(record)


def test_failure_receipt_written_before_build_admission_error(tmp_path, monkeypatch):
    rejected = {**proof(), "status": "rejected", "large_model_construction_allowed": False}
    monkeypatch.setattr(gate, "probe", lambda: rejected)
    entry = {"job_id": "123", "step_id": "0", "source_commit": "a" * 40}
    with pytest.raises(ValueError, match="license capacity rejected"):
        campaign.Campaign("gurobi").license_admission(tmp_path, entry)
    assert json.loads((tmp_path / "gurobi_license.json").read_bytes()) == {
        "entry": entry, **rejected,
    }


def test_restricted_worker_stops_before_math_controls_or_private_build(tmp_path, monkeypatch):
    control = tmp_path / "control/sto"
    control.mkdir(parents=True)
    job = {"job_id": "123", "source_commit": "a" * 40, "plan_sha256": "b" * 64}
    entry = {
        **job, "mode": "sto", "step_id": "0",
        "pid": campaign.os.getpid(), "proc_start_ticks": 1,
    }
    for name in ("entry.json", "release.json"):
        campaign.r.r2.write(control / name, entry)
    arm = campaign.Campaign("gurobi")
    monkeypatch.setattr(arm, "load", lambda *a, **k: {"cbc_path": str(tmp_path / "unused")})
    monkeypatch.setattr(campaign.o, "job_receipt", lambda *a: job)
    monkeypatch.setattr(campaign.o, "verify_tools", lambda *a: None)
    monkeypatch.setattr(campaign.bootstrap, "proc_start", lambda *a: 1)
    monkeypatch.setattr(campaign.os, "sched_getaffinity", lambda *a: set(range(4)), raising=False)
    monkeypatch.setattr(gate, "probe", lambda: {**proof(), "status": "rejected"})
    for method in ("inspect_native", "run_math", "run_case"):
        monkeypatch.setattr(arm, method, lambda *a: pytest.fail("Must stop at license gate"))
    # Register restoration before the worker temporarily redirects its scratch paths.
    for name in ("TMPDIR", "TMP", "TEMP", "PATH"):
        monkeypatch.setenv(name, campaign.os.environ.get(name, ""))
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setenv("SLURM_STEP_ID", "0")
    stages = []

    def stage(name, operation):
        stages.append(name)
        return operation()

    with pytest.raises(ValueError, match="license capacity rejected"):
        arm.worker(tmp_path, job["source_commit"], "sto", entry=entry,
                   startup=SimpleNamespace(stage=stage))
    assert stages == ["tool_verification", "native_identity"]
    assert (control / "gurobi_license.json").is_file()


@pytest.mark.parametrize("solver", ["scip", "cbc"])
def test_other_engine_never_requires_or_imports_gurobi_license(tmp_path, monkeypatch, solver):
    monkeypatch.setattr(gate, "probe", lambda: pytest.fail("Unrelated solver"))
    campaign.Campaign(solver).license_admission(tmp_path, {})
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("fault", ["missing", "rejected", "wrong_entry"])
def test_successful_replay_requires_owned_license_receipt(tmp_path, monkeypatch, fault):
    from tests import test_pyomo_h215_operational as controls

    monkeypatch.setattr(controls, "m", campaign.Campaign("gurobi"))
    files, plan = controls.operational_files(tmp_path)
    if fault == "missing":
        del files["control/sto/gurobi_license.json"]
    else:
        record = json.loads(files["control/sto/gurobi_license.json"])
        if fault == "rejected":
            record["status"] = "rejected"
        else:
            record["entry"]["job_id"] = "999"
        files["control/sto/gurobi_license.json"] = campaign.r.r2.encoded(record)
    arm = campaign.Campaign("gurobi")
    monkeypatch.setattr(arm, "design", lambda _: plan)
    review = arm.portable_review(files)
    assert review["status"] == "pyomo_forensic_partial_preserved"
    assert not review["operational_receipts_closed"]


def test_login_cli_refuses_before_creating_report(tmp_path, monkeypatch):
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    output = tmp_path / "capacity.json"
    monkeypatch.setattr(sys, "argv", ["gate", "--output", str(output)])
    with pytest.raises(ValueError, match="compute step"):
        gate.main()
    assert not output.exists()


def test_wrapper_does_not_redirect_historical_collection_or_other_engines():
    source = (Path(campaign.ROOT) / "scripts/npad_pyomo_h215_w_native8h.sh").read_text(
        encoding="utf-8"
    )
    assert 'if [[ "$ACTION" = start && "$SOLVER" = gurobi ]]; then' in source
    assert "export GRB_LICENSE_FILE=" + gate.policy.LICENSE_FILE in source
    assert source.index("Existing Pyomo claim") < source.index("export GRB_LICENSE_FILE=")

