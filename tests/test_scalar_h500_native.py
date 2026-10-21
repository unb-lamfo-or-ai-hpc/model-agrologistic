"""Real tiny native one-arm lifecycle; controlled Slurm/WLS transport, not NPAD h500."""

import os
import subprocess
import sys
import threading
from dataclasses import replace
from types import SimpleNamespace

from scripts import mvp2_scalar_h500_operational as m
from tests.test_excel_loader import build_tiny_golden_excel
from tests.test_gurobipy_transshipment import require_gurobi_available
from tests.test_scalar_h300_operational import hardware_fixture
from tests.test_scalar_r3a import SHA, tiny_selection, tiny_spec
from tests.test_scalar_r3a_operational import allocation_text


def test_real_cold_worker_original_validation_controller_collection_and_replay(
    tmp_path, monkeypatch
):
    if os.environ.get("AGRO_REQUIRE_NATIVE_SOLVERS") != "1":
        require_gurobi_available()
    workbook = tmp_path / "public.xlsx"
    build_tiny_golden_excel(workbook)
    template = tiny_spec(workbook, "sto")
    spec = replace(
        template,
        name=m.c.CASE,
        loader=replace(
            template.loader,
            scenario_generation_mode="cartesian",
            penalty_policy="fixed",
            default_unmet_demand_penalty=90000,
            default_emergency_static_penalty=45000,
            default_emergency_reception_penalty=45000,
        ),
        solver=replace(
            template.solver,
            threads=1,
            time_limit=14400,
            mip_gap=0.01,
            seed=42,
            solver_options={"SoftMemLimit": 160},
            collect_resource_diagnostics=True,
        ),
        max_estimated_variables=10000,
    )
    selection = tiny_selection()
    source = {"source_commit": SHA, "files": {}}
    shape = {"warehouses": 2, "periods": 2, "sto_scenarios": 9}
    from tests.test_scalar_h500_operational import fixture

    files, _ = fixture()
    material = files["materialization.original.json"]
    plan = {
        "source_commit": SHA,
        "resources": m.c.PROFILE,
        "source_inventory_sha256": m.r.r2.digest(m.r.r2.encoded(source)),
        "warehouse_selection_sha256": m.r.r2.digest(m.r.r2.encoded(selection)),
        "materialization_original_sha256": m.r.r2.digest(material),
        "expected_shape": shape,
        "cases": [m.r.spec_payload(spec)],
        "python_sha256": m.r.file_hash(sys.executable),
        "tools": dict.fromkeys(m.o.TOOLS, sys.executable),
        "tool_sha256": dict.fromkeys(m.o.TOOLS, m.r.file_hash(sys.executable)),
        **m.r.closed(),
    }
    plan = m.r.strict_json(m.r.r2.encoded(plan))
    claim = tmp_path / m.CLAIM
    claim.mkdir()
    for name, value in (
        ("plan.json", plan),
        ("source.json", source),
        ("warehouse_selection.json", selection),
    ):
        m.r.r2.write(claim / name, value)
    (claim / "materialization.original.json").write_bytes(material)
    job = {"job_id": "123", "source_commit": SHA, "plan_sha256": m.r.file_hash(claim / "plan.json")}
    m.r.r2.write(claim / "job.json", job)
    monkeypatch.setattr(m, "load", lambda *_: plan)
    monkeypatch.setattr(
        m.c, "design", lambda *_: plan
    )  # Explicit public tiny profile, not400 rows.
    monkeypatch.setattr(m.c, "specs", lambda _: [spec])
    monkeypatch.setattr(m.c, "SHAPE", shape)
    monkeypatch.setattr(m.o, "verify_tools", lambda *_: None)
    monkeypatch.setattr(m.previous, "hardware", lambda _: hardware_fixture())
    monkeypatch.setattr(m.os, "getuid", lambda: 1271, raising=False)
    monkeypatch.setattr(m.os, "sched_getaffinity", lambda _: set(range(16)), raising=False)
    monkeypatch.setattr(m.os, "sched_setaffinity", lambda *_: None, raising=False)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setenv("SLURM_STEP_ID", "0")
    from scripts import probe_npad_gurobi_license as probe

    monkeypatch.setattr(
        probe,
        "probe",
        lambda: {
            "status": "accepted",
            "probe_variable_count": 2001,
            "probe_constraint_count": 2001,
            "objective_value": 2001,
            "license_file": probe.LICENSE_FILE,
            "gurobi_version": [13, 0, 3],
            "qualification": "Controlled capability transport, not WLS.",
        },
    )

    def command(argv, **_):
        if argv[0] == "scontrol" and argv[3] == "job":
            text = allocation_text(TimeLimit="08:00:00")
        elif argv[0] == "scontrol" and argv[3] == "step":
            text = "StepId=123.0 UserId=1271 CPUs=24 Nodes=1 Tasks=1 State=RUNNING NodeList=r1i3n5"
        elif argv[0] == "sacct":
            text = "123.0|COMPLETED|0:0|30|123K\n"
        else:
            raise AssertionError("No live scheduler allowed in native software qualification")
        return SimpleNamespace(returncode=0, stdout=text, stderr="")

    class LocalProcess:
        returncode = None

        def __init__(self, argv, **_):
            assert "--time=05:45:00" in argv and "--cpus-per-task=24" in argv
            self.error = None

            def run():
                try:
                    m.worker(claim, SHA)
                    self.returncode = 0
                except Exception as exc:
                    self.error, self.returncode = exc, 1

            self.thread = threading.Thread(target=run)
            self.thread.start()

        def poll(self):
            return self.returncode

        def wait(self, timeout):
            self.thread.join(timeout)
            if self.thread.is_alive():
                raise subprocess.TimeoutExpired("public_native_worker", timeout)
            if self.error:
                raise self.error
            return self.returncode

    def supervise(claim, sha, allocated, receipt):
        return m.o.supervise(
            claim,
            sha,
            m.ARM,
            allocated,
            receipt,
            command=command,
            popen=LocalProcess,
            invoke=m.invocation,
            step_cpus=24,
            bind_step=m.previous.bind_step,
            phase_profile=m.c.PROFILE,
            whole_arm_seconds=20700,
            reviewer=lambda c, s, _a, _t: m.review_arm(c, s),
        )

    monkeypatch.setattr(m, "supervise", supervise)
    monkeypatch.setattr(m.r.r2, "command", command)
    assert m.batch(claim, SHA) == 0
    product = claim / "cases" / spec.name / "products" / spec.name
    assert m.r.r2.read(product / "independent_validation.json")["status"] == "accepted"
    assert m.r.r2.read(claim / "control/t1/native_terminal.json")["solution_count"] > 0
    assert (claim / "cases" / spec.name / "warehouses_used.csv").is_file()
    assert m.r.r2.read(claim / "control/t1/controller.json")["status"] == "closed_feasible_arm"
    raw = (
        "123|COMPLETED|0:0|200|\n123.batch|COMPLETED|0:0|200|123K\n"
        "123.extern|COMPLETED|0:0|200|1K\n123.0|COMPLETED|0:0|30|123K\n"
    )
    saved = m.collect(claim, SHA, command=lambda *_: SimpleNamespace(returncode=0, stdout=raw))
    assert saved["operational_receipts_closed"] and saved["quality_target_met"]
    assert m.audit(claim / m.ARCHIVE, saved["sha256"])["quality_target_met"]
    assert not saved["additional_execution_admitted"] and not saved["automatic_follow_on_allowed"]
