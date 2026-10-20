"""Five real tiny native arms with controlled transport; no NPAD or actual WLS probe."""

import os
import subprocess
import sys
import threading
from dataclasses import replace
from types import SimpleNamespace

from scripts import mvp2_scalar_h300_operational as m
from tests.test_excel_loader import build_tiny_golden_excel
from tests.test_gurobipy_transshipment import require_gurobi_available
from tests.test_scalar_h300_operational import audit_fixture, hardware_fixture
from tests.test_scalar_r3a import SHA, tiny_selection, tiny_spec
from tests.test_scalar_r3a_operational import allocation_text


def test_real_five_cold_native_workers_control_original_validation_and_portable_collection(
    tmp_path, monkeypatch
):
    if os.environ.get("AGRO_REQUIRE_NATIVE_SOLVERS") != "1":
        require_gurobi_available()
    from src.logic import model_validation

    checked = []
    original_validate = model_validation.validate_or_raise_model_data

    def validate(**kwargs):
        checked.append(kwargs["config"].mode)
        assert kwargs["require_distances"]
        return original_validate(**kwargs)

    monkeypatch.setattr(model_validation, "validate_or_raise_model_data", validate)
    workbook = tmp_path / "public.xlsx"
    build_tiny_golden_excel(workbook)
    specs = []
    for threads in m.h.ORDER:
        spec = tiny_spec(workbook, "sto")
        specs.append(
            replace(
                spec,
                name=f"scalar_h300_t{threads}",
                loader=replace(
                    spec.loader,
                    scenario_generation_mode="cartesian",
                    penalty_policy="fixed",
                    default_unmet_demand_penalty=90000,
                    default_emergency_static_penalty=45000,
                    default_emergency_reception_penalty=45000,
                ),
                solver=replace(
                    spec.solver,
                    threads=threads,
                    time_limit=14400,
                    mip_gap=0.01,
                    seed=42,
                    solver_options={"SoftMemLimit": 160},
                    collect_resource_diagnostics=True,
                ),
                max_estimated_variables=10000,
            )
        )
    shape = {"warehouses": 2, "periods": 2, "sto_scenarios": 9}
    selection = tiny_selection()
    source = {"source_commit": SHA, "files": {}}
    material = m.r.r2.encoded(audit_fixture())
    plan = {
        "schema_version": m.SCHEMA,
        "status": m.STATUS,
        "source_commit": SHA,
        "source_inventory_sha256": m.r.r2.digest(m.r.r2.encoded(source)),
        "warehouse_selection_sha256": m.r.r2.digest(m.r.r2.encoded(selection)),
        "materialization_original_sha256": m.r.r2.digest(material),
        "resources": m.PROFILE,
        "expected_shape": shape,
        "cases": [m.r.spec_payload(s) for s in specs],
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
        m, "design_review", lambda *_: {"status": "explicit_public_tiny_config_fixture"}
    )
    monkeypatch.setattr(m.o, "verify_tools", lambda *_: None)
    monkeypatch.setattr(m.h, "specs", lambda _: specs)
    monkeypatch.setattr(m.h, "SHAPE", shape)
    monkeypatch.setattr(m, "hardware", lambda _: hardware_fixture())
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
            "qualification": "Explicit transport fixture, not live designated WLS observation.",
        },
    )

    def command(argv, **_):
        if argv[0] == "scontrol" and argv[3] == "job":
            text = allocation_text(TimeLimit="1-06:00:00")
        elif argv[0] == "scontrol" and argv[3] == "step":
            text = (
                f"StepId={argv[-1]} UserId=1271 CPUs=24 Nodes=1 Tasks=1 "
                "State=RUNNING NodeList=r1i3n5"
            )
        elif argv[0] == "sacct":
            text = "123." + os.environ["SLURM_STEP_ID"] + "|COMPLETED|0:0|30|123K\n"
        else:
            raise AssertionError("No actual scheduler/stop allowed")
        return SimpleNamespace(returncode=0, stdout=text, stderr="")

    class LocalProcess:
        returncode = None

        def __init__(self, argv, **_):
            self.error = None
            arm = argv[-1]

            def target():
                try:
                    m.worker(claim, SHA, arm)
                    self.returncode = 0
                except Exception as exc:
                    self.error, self.returncode = exc, 1

            self.thread = threading.Thread(target=target)
            self.thread.start()

        def poll(self):
            return self.returncode

        def wait(self, timeout):
            self.thread.join(timeout)
            if self.thread.is_alive():
                raise subprocess.TimeoutExpired("local_worker", timeout)
            if self.error:
                raise self.error
            return self.returncode

    def supervise(c, sha, arm, allocated, receipt):
        monkeypatch.setenv("SLURM_STEP_ID", str(m.ARMS.index(arm)))
        return m.o.supervise(
            c,
            sha,
            arm,
            allocated,
            receipt,
            command=command,
            popen=LocalProcess,
            invoke=m.invocation,
            step_cpus=24,
            bind_step=m.bind_step,
            whole_arm_seconds=18900,
            reviewer=lambda c, s, a, _: m.review_arm(c, s, a),
        )

    monkeypatch.setattr(m, "supervise", supervise)
    monkeypatch.setattr(m.r.r2, "command", command)
    assert m.batch(claim, SHA) == 0
    assert checked == ["sto"] * 5
    for arm, spec in zip(m.ARMS, specs, strict=True):
        control = claim / "control" / arm
        product = claim / "cases" / spec.name / "products" / spec.name
        assert m.r.r2.read(product / "independent_validation.json")["status"] == "accepted"
        assert m.r.r2.read(control / "native_terminal.json")["solution_count"] > 0
        receipt = m.r.r2.read(claim / "cases" / spec.name / "input_receipt.json")
        assert receipt["frozen_penalty_review"]["rates"] == m.h.RATES
        assert (product / "resources/manifest.json").is_file()
        assert (claim / "cases" / spec.name / "warehouses_used.csv").is_file()
    raw = (
        "123|COMPLETED|0:0|200|\n123.batch|COMPLETED|0:0|200|123K\n"
        "123.extern|COMPLETED|0:0|200|1K\n"
        + "".join(f"123.{i}|COMPLETED|0:0|30|1K\n" for i in range(5))
    )
    saved = m.collect(claim, SHA, command=lambda *_: SimpleNamespace(returncode=0, stdout=raw))
    assert saved["operational_receipts_closed"] and len(saved["arms"]) == 5
    assert saved["quality_target_met"] == all(
        a["common_gap"] is not None and a["common_gap"] <= 0.01 for a in saved["arms"]
    )
    assert (
        m.audit(claim / m.ARCHIVE, saved["sha256"])["quality_target_met"]
        == saved["quality_target_met"]
    )
    assert all(saved[k] is False for k in m.r.closed())
