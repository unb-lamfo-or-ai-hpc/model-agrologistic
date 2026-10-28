"""Real public tiny HiGHS lifecycle with controlled Slurm transport; never NPAD."""

import os
import subprocess
import sys
import threading
from dataclasses import replace
from types import SimpleNamespace

import pytest

from scripts import mvp2_scalar_highs_h215_8h_startup as m
from tests.test_excel_loader import build_tiny_golden_excel
from tests.test_scalar_r3a import SHA, tiny_selection, tiny_spec
from tests.test_scalar_r3a_operational import allocation_text


def native_required():
    if os.environ.get("AGRO_REQUIRE_NATIVE_SOLVERS") == "1":
        __import__("highspy")
    else:
        pytest.importorskip("highspy")


def test_real_native_build_and_fresh_scalar_gate(tmp_path):
    native_required()
    fingerprint = m.environment()
    assert fingerprint == m.environment()
    assert set(fingerprint["package_sha256"]) == {"pyomo", "highspy"}
    build = m.inspect_native()
    assert build["highs"] == "1.15.1" and build["pyomo"] == "6.10.1"
    assert not build["population_optimized"]
    assert m.run_math(tmp_path) == {
        "tests": 3, "failures": 0, "errors": 0, "skipped": 0, "status": "accepted",
    }


def test_real_worker_controller_original_validation_collection_and_replay(tmp_path, monkeypatch):
    native_required()
    import highspy
    highspy.Highs.resetGlobalScheduler(True)
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
            original.solver, backend="pyomo", solver_name="highs", time_limit=28800,
            threads=4, mip_gap=0.01, seed=42, collect_resource_diagnostics=False,
            solver_options={"indicator_reformulation": m.POLICY, "pyomo_max_variables": 16000000},
            log_file="highs-native.log",
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
    def fixture_load(*_, startup=None):
        if startup is not None:
            for name in ("plan_validation", "source_verification", "runtime_fingerprints",
                         "input_hashes"):
                startup.stage(name, lambda: None)
        return plan
    monkeypatch.setattr(m, "load", fixture_load)
    monkeypatch.setattr(m, "design", lambda _: plan)
    monkeypatch.setattr(m.o, "verify_tools", lambda *_: None)
    monkeypatch.setattr(m, "recheck_inputs", lambda *_: None)
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
        "tests": 3, "failures": 0, "errors": 0, "skipped": 0, "status": "accepted",
    })

    def command(argv, **_):
        if argv[0] == "scontrol" and argv[3] == "job":
            text = allocation_text(TimeLimit="12:00:00")
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
                    # Controlled transport uses real startup receipts and worker;
                    # the isolated CLI bootstrap is separately exercised in subprocess tests.
                    control = claim / "control/sto"
                    entry = {
                        **job, "mode": "sto", "step_id": "0", "pid": os.getpid(),
                        "proc_start_ticks": m.bootstrap.proc_start(os.getpid()),
                        "started_monotonic": m.time.monotonic(),
                    }
                    m.o.publish(control / "entry.json", entry)
                    m.o.publish(control / "phase-00.json", {
                        "entry": entry, "phase": "input_build", "elapsed_seconds": 0.0,
                    })
                    startup = m.bootstrap.Recorder(control, entry)
                    startup.stage("bootstrap_identity", lambda: None)
                    m.o.publish(control / "bootstrap.json", {
                        "entry": entry, "schema_version": "highs-bootstrap-v2",
                        "isolated": True, "no_site": True, "no_user_site": True,
                        "native_or_application_loaded_before_release": False,
                        "full_provenance_pending": True,
                    })
                    startup.stage("exact_release", lambda: m.bootstrap.release(control, entry))
                    startup.stage("site_initialization", lambda: None)
                    startup.stage("driver_import", lambda: None)
                    m.worker(claim, SHA, "sto", entry=entry, startup=startup)
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
    assert report["status"] == "highs_quality_target_met", report
    assert not report["repeats_admitted"] and not report["additional_highs_execution_admitted"]
    assert m.audit(claim / m.ARCHIVE, report["sha256"])["status"] == report["status"]
    monkeypatch.chdir(tmp_path)
    highspy.Highs.resetGlobalScheduler(True)



def test_real_isolated_bootstrap_reaches_public_highs_worker(tmp_path):
    """Actual -I -S process and solver; only public input/provenance/transport seams."""
    native_required()
    import hashlib
    import json

    from scripts import highs_worker_bootstrap as b
    from tests.test_scalar_highs_h215_8h_startup import cold_fixture, until

    claim, control, root, _, argv, env = cold_fixture(tmp_path)
    workbook = claim.parent / "public.xlsx"
    build_tiny_golden_excel(workbook)
    selected = replace(
        tiny_spec(workbook, "sto"), name=m.CASE, max_estimated_variables=10000,
        loader=replace(
            tiny_spec(workbook, "sto").loader,
            scenario_generation_mode="cartesian", penalty_policy="fixed",
            default_unmet_demand_penalty=90000, default_emergency_static_penalty=45000,
            default_emergency_reception_penalty=45000,
        ),
        solver=replace(
            tiny_spec(workbook, "sto").solver, backend="pyomo", solver_name="highs",
            time_limit=28800, threads=4, mip_gap=0.01, seed=42,
            collect_resource_diagnostics=False, log_file="highs-native.log",
            solver_options={"indicator_reformulation": m.POLICY, "pyomo_max_variables": 16000000},
        ),
    )
    selection = tiny_selection()
    shape = {"warehouses": 2, "periods": 2, "sto_scenarios": 9}
    _, receipt = m.r.preflight(selected, shape, selection)
    for name, value in (
        ("historical_w.json", {"receipts": {"sto": receipt}}),
        ("warehouse_selection.json", selection),
    ):
        (claim / name).write_bytes(b.encoded(value))
    # The small public adapter loads the actual worker source, then supplies
    # deterministic fixture inputs. It cannot invoke any scheduler or private case.
    adapter = r"""
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

def worker(claim, sha, mode, *, entry, startup):
    repo = Path(REPO_VALUE)
    sys.path.insert(0, str(repo))
    import scripts
    scripts.__path__.append(str(repo / "scripts"))
    location = repo / "scripts/mvp2_scalar_highs_h215_8h_startup.py"
    spec = importlib.util.spec_from_file_location("public_actual_highs_worker", location)
    actual = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(actual)
    from tests.test_scalar_r3a import tiny_spec
    workbook = claim.parent / "public.xlsx"
    original = tiny_spec(workbook, "sto")
    selected = replace(
        original, name=actual.CASE, max_estimated_variables=10000,
        loader=replace(original.loader, scenario_generation_mode="cartesian",
                       penalty_policy="fixed", default_unmet_demand_penalty=90000,
                       default_emergency_static_penalty=45000,
                       default_emergency_reception_penalty=45000),
        solver=replace(original.solver, backend="pyomo", solver_name="highs",
                       time_limit=28800, threads=4, mip_gap=0.01, seed=42,
                       collect_resource_diagnostics=False, log_file="highs-native.log",
                       solver_options={"indicator_reformulation": actual.POLICY,
                                       "pyomo_max_variables":16000000}),
    )
    actual.SHAPE = {"warehouses":2,"periods":2,"sto_scenarios":9}
    actual.spec = lambda _: selected
    plan = json.loads((claim/"plan.json").read_bytes())
    def fixture_load(*_, startup=None):
        if startup is not None:
            for name in ("plan_validation","source_verification","runtime_fingerprints",
                         "input_hashes"):
                startup.stage(name, lambda: None)
        return plan
    actual.load = fixture_load
    actual.o.verify_tools = lambda _: None
    actual.os.sched_getaffinity = lambda _: set(range(16))
    def compare(_selected, _data, receipt, previous):
        receipt=actual.r.strict_json(actual.r.r2.encoded(receipt))
        assert receipt["mathematical_contract"] == previous["receipts"]["sto"][
            "mathematical_contract"]
        assert receipt["warehouse_selection"] == previous["receipts"]["sto"][
            "warehouse_selection"]
    actual.compare_input = compare
    actual.worker(claim, sha, mode, entry=entry, startup=startup)
"""
    adapter = adapter.replace("REPO_VALUE", repr(str(m.ROOT)))
    (root / b.DRIVER_FILE).write_text(adapter)
    source = json.loads((claim / "source.json").read_bytes())
    source["files"][b.DRIVER_FILE] = hashlib.sha256(adapter.encode()).hexdigest()
    (claim / "source.json").write_bytes(b.encoded(source))
    plan = json.loads((claim / "plan.json").read_bytes())
    plan.update(
        cases=[m.r.spec_payload(selected)], python_sha256=m.r.file_hash(sys.executable),
        environment={"python": m.platform.python_version()},
        artifact_sha256={"source.json": m.r.file_hash(claim / "source.json")},
    )
    (claim / "plan.json").write_bytes(b.encoded(m.r.strict_json(m.r.r2.encoded(plan))))
    job = {"job_id": "123", "source_commit": SHA,
           "plan_sha256": m.r.file_hash(claim / "plan.json")}
    (claim / "job.json").write_bytes(b.encoded(job))
    child = subprocess.Popen(argv, cwd=control, env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    try:
        until(control / "bootstrap.json", child)
        entry = json.loads((control / "entry.json").read_bytes())
        b.publish(control / "release.json", entry)
        out, err = child.communicate(timeout=180)
        assert child.returncode == 0, (out.decode(), err.decode())
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)
    files = {p.relative_to(claim).as_posix(): p.read_bytes()
             for p in claim.rglob("*") if p.is_file() and not p.is_symlink()}
    assert b.review(files, job)["status"] == "complete"
    result = m.case_review(files, m.r.r2.read(claim / "plan.json"))
    assert result["quality_target_met"] and result["original_validation_status"] == "accepted"
    assert (control / "qualification.json").exists()
    assert result["native_status"] == "optimal"
    assert not result["additional_highs_execution_admitted"]
