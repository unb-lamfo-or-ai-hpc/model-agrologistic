"""Real public tiny SCIP lifecycle with controlled Slurm transport; never NPAD."""

import os
import subprocess
import sys
import threading
from dataclasses import replace
from types import SimpleNamespace

import pytest

from scripts import mvp2_scalar_scip_h215 as m
from tests.test_excel_loader import build_tiny_golden_excel
from tests.test_scalar_r3a import SHA, tiny_selection, tiny_spec
from tests.test_scalar_r3a_operational import allocation_text


def native_required():
    if os.environ.get("AGRO_REQUIRE_NATIVE_SOLVERS") == "1":
        __import__("pyscipopt")
    else:
        pytest.importorskip("pyscipopt")


def test_real_native_build_and_fresh_scalar_gate(tmp_path):
    native_required()
    build = m.inspect_native()
    assert build["scip"] == "10.0.2" and build["lp_solver"] == "SoPlex8.0.2"
    assert not build["population_optimized"]
    assert m.run_math(tmp_path) == {
        "tests": 9, "failures": 0, "errors": 0, "skipped": 0, "status": "accepted",
    }


def test_real_worker_controller_original_validation_collection_and_replay(tmp_path, monkeypatch):
    native_required()
    workbook = tmp_path / "public.xlsx"
    build_tiny_golden_excel(workbook)
    original = tiny_spec(workbook, "sto")
    selected = replace(
        original, name=m.CASE, max_estimated_variables=10000,
        loader=replace(
            original.loader, scenario_generation_mode="cartesian", penalty_policy="fixed",
            default_unmet_demand_penalty=90000, default_emergency_static_penalty=45000,
            default_emergency_reception_penalty=45000,
        ),
        solver=replace(
            original.solver, backend="pyscipopt", solver_name="scip", time_limit=14400,
            threads=4, mip_gap=0.01, seed=42, collect_resource_diagnostics=True,
            solver_options={"limits/memory": 163840}, log_file="scip-native.log",
        ),
    )
    selection = tiny_selection()
    shape = {"warehouses": 2, "periods": 2, "sto_scenarios": 9}
    _, receipt = m.r.preflight(selected, shape, selection)
    previous = {"receipts": {"sto": receipt}}
    claim = tmp_path / m.CLAIM
    claim.mkdir()
    environment = {"python": m.platform.python_version()}
    plan = {
        "source_commit": SHA, "cases": [m.r.spec_payload(selected)],
        "python_sha256": m.r.file_hash(sys.executable), "environment": environment,
    }
    plan = m.r.strict_json(m.r.r2.encoded(plan))
    for name, value in (
        ("plan.json", plan), ("historical_w.json", previous),
        ("warehouse_selection.json", selection),
    ):
        m.r.r2.write(claim / name, value)
    job = {"job_id": "123", "source_commit": SHA, "plan_sha256": m.r.file_hash(claim / "plan.json")}
    m.r.r2.write(claim / "job.json", job)
    monkeypatch.setattr(m, "SHAPE", shape)
    monkeypatch.setattr(m, "spec", lambda _: selected)
    monkeypatch.setattr(m, "load", lambda *_: plan)
    monkeypatch.setattr(m, "design", lambda _: plan)
    monkeypatch.setattr(m.o, "verify_tools", lambda *_: None)
    monkeypatch.setattr(m.d, "recheck_inputs", lambda *_: None)
    monkeypatch.setattr(m.os, "getuid", lambda: 1271, raising=False)
    monkeypatch.setattr(m.os, "sched_getaffinity", lambda _: set(range(16)), raising=False)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setenv("SLURM_STEP_ID", "0")

    def compare(_selected, _data, actual, prior):
        actual = m.r.strict_json(m.r.r2.encoded(actual))
        assert actual["mathematical_contract"] == prior["receipts"]["sto"]["mathematical_contract"]
        assert actual["warehouse_selection"] == prior["receipts"]["sto"]["warehouse_selection"]

    monkeypatch.setattr(m, "compare_input", compare)
    # The full native gate is exercised separately above; this seam controls only
    # duplicate tiny qualification, never population model/independent validation.
    monkeypatch.setattr(m, "run_math", lambda _: {
        "tests": 9, "failures": 0, "errors": 0, "skipped": 0, "status": "accepted",
    })

    def command(argv, **_):
        if argv[0] == "scontrol" and argv[3] == "job":
            text = allocation_text(TimeLimit="08:00:00")
        elif argv[0] == "scontrol" and argv[3] == "step":
            text = "StepId=123.0 UserId=1271 CPUs=16 Nodes=1 Tasks=1 State=RUNNING NodeList=r1i3n5"
        elif argv[0] == "sacct":
            text = "123.0|COMPLETED|0:0|30|123K\n"
        else:
            raise AssertionError("No live scheduler or stop is allowed")
        return SimpleNamespace(returncode=0, stdout=text, stderr="")

    class LocalProcess:
        returncode = None

        def __init__(self, argv, **_):
            assert "--cpus-per-task=16" in argv
            assert "--chdir=" + str(claim / "control/sto") in argv
            monkeypatch.chdir(claim / "control/sto")
            self.error = None

            def target():
                try:
                    m.worker(claim, SHA, "sto")
                    self.returncode = 0
                except Exception as exc:
                    import traceback
                    (claim / "public_worker_traceback.txt").write_text(traceback.format_exc())
                    self.error, self.returncode = exc, 1

            self.thread = threading.Thread(target=target)
            self.thread.start()

        def poll(self):
            return self.returncode

        def wait(self, timeout):
            self.thread.join(timeout)
            if self.thread.is_alive():
                raise subprocess.TimeoutExpired("public_worker", timeout)
            if self.error:
                raise self.error
            return self.returncode

    original_supervise = m.o.supervise

    def controlled(*args, **kwargs):
        kwargs.update(
            command=command, popen=LocalProcess,
            reviewer=lambda c, s, mode, _remaining: m.review_arm(c, s, mode),
        )
        return original_supervise(*args, **kwargs)

    monkeypatch.setattr(m.o, "supervise", controlled)
    monkeypatch.setattr(m.r.r2, "command", command)
    exit_code = m.batch(claim, SHA)
    if exit_code:
        details = {
            p.relative_to(claim).as_posix(): p.read_text()
            for p in claim.rglob("*.json")
            if p.name in {"batch_outcome.json", "controller.json", "case_outcome.json"}
        }
        trace = claim / "public_worker_traceback.txt"
        details["trace"] = trace.read_text() if trace.exists() else "No worker traceback"
        raise AssertionError(details)
    products = claim / "cases" / m.CASE / "products" / m.CASE
    validation = m.r.r2.read(products / "independent_validation.json")
    assert validation["status"] == "accepted" and validation["failed_check_count"] == 0
    assert m.r.r2.read(claim / "control/sto/native_terminal.json")["effective_parameters"] == (
        m.EXPECTED_PARAMS
    )
    raw = (
        "123|COMPLETED|0:0|100|\n123.batch|COMPLETED|0:0|100|123K\n"
        "123.extern|COMPLETED|0:0|100|1K\n123.0|COMPLETED|0:0|30|123K\n"
    )
    report = m.collect(
        claim, SHA, command=lambda *_: SimpleNamespace(returncode=0, stdout=raw),
    )
    assert report["operational_receipts_closed"], report
    assert report["status"] == "scip_quality_target_met", report
    assert not report["repeats_admitted"] and not report["highs_execution_admitted"]
    assert m.audit(claim / m.ARCHIVE, report["sha256"])["status"] == report["status"]
    monkeypatch.chdir(tmp_path)
