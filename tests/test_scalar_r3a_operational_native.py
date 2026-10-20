"""Real tiny native worker/controller/collection with controlled local Slurm transport.

No NPAD, live Slurm, designated WLS probe or large-instance qualification.
"""

import json
import os
import subprocess
import sys
import threading
from types import SimpleNamespace

from scripts import mvp2_scalar_r3a_operational as o
from tests.test_excel_loader import build_tiny_golden_excel
from tests.test_gurobipy_transshipment import require_gurobi_available
from tests.test_scalar_r3a import SHA, SHAPE, tiny_selection, tiny_spec
from tests.test_scalar_r3a_operational import allocation_text, osrm_audit


def test_real_worker_parent_phase_control_two_arms_original_residuals_and_terminal_transfer(
    tmp_path,
    monkeypatch,
):
    if os.environ.get("AGRO_REQUIRE_NATIVE_SOLVERS") != "1":
        require_gurobi_available()
    workbook = tmp_path / "public.xlsx"
    build_tiny_golden_excel(workbook)
    selected = [tiny_spec(workbook, mode) for mode in o.MODES]
    for spec in selected:
        spec.solver.threads = 4
        spec.solver.time_limit = 14400
        spec.solver.mip_gap = 0.01
        spec.solver.collect_resource_diagnostics = True
    selection = tiny_selection()
    inventory = {"source_commit": SHA, "files": {}}
    material = osrm_audit()
    plan = {
        "schema_version": "scalar-h215-operational-v1",
        "source_commit": SHA,
        "source_inventory_sha256": o.r.r2.digest(o.r.r2.encoded(inventory)),
        "profile": o.PROFILE,
        "budget": o.budget(),
        "expected_shape": SHAPE,
        "cases": [o.r.spec_payload(s) for s in selected],
        "selection_sha256": o.r.r2.digest(o.r.r2.encoded(selection)),
        "materialization_sha256": o.r.r2.digest(o.r.r2.encoded(material)),
        "materialization_original_sha256": o.r.r2.digest(o.r.r2.encoded(material)),
        "tools": dict.fromkeys(o.TOOLS, sys.executable),
        "tool_sha256": dict.fromkeys(o.TOOLS, o.r.file_hash(sys.executable)),
        **o.r.closed(),
    }
    plan = o.r.strict_json(o.r.r2.encoded(plan))
    claim = tmp_path / o.CLAIM
    claim.mkdir()
    for name, value in (
        ("plan.json", plan),
        ("source.json", inventory),
        ("warehouse_selection.json", selection),
        ("materialization.json", material),
        ("materialization.original.json", material),
    ):
        o.r.r2.write(claim / name, value)
    job = {"job_id": "123", "source_commit": SHA, "plan_sha256": o.r.file_hash(claim / "plan.json")}
    o.r.r2.write(claim / "job.json", job)
    from scripts import probe_npad_gurobi_license as license_probe

    monkeypatch.setattr(
        license_probe,
        "probe",
        lambda: {
            "status": "accepted",
            "probe_variable_count": 2001,
            "probe_constraint_count": 2001,
            "objective_value": 2001,
            "qualification": "Injected capability fixture, not a live WLS observation.",
        },
    )
    monkeypatch.setattr(o, "SHAPE", SHAPE)
    monkeypatch.setattr(o, "specs", lambda _: selected)
    monkeypatch.setattr(o, "case_contract", lambda _: None)
    monkeypatch.setattr(o, "load", lambda *_a, **_kw: plan)
    monkeypatch.setattr(o, "verify_tools", lambda _: None)
    monkeypatch.setattr(o.os, "getuid", lambda: 1271, raising=False)
    monkeypatch.setattr(o.os, "sched_getaffinity", lambda _: set(range(4)), raising=False)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setenv("SLURM_STEP_ID", "0")

    def command(argv, **_):
        if argv[0] == "scontrol" and argv[3] == "job":
            text = allocation_text()
        elif argv[0] == "scontrol" and argv[3] == "step":
            text = f"StepId={argv[-1]} UserId=1271 CPUs=4 Nodes=r1i3n5"
        elif argv[0] == "sacct":
            step = os.environ["SLURM_STEP_ID"]
            text = f"123.{step}|COMPLETED|0:0|30|123K\n"
        else:
            raise AssertionError("No actual scheduler/stop allowed")
        return SimpleNamespace(returncode=0, stdout=text, stderr="")

    class LocalProcess:
        """A worker thread models transport only; real Gurobi math runs inside it."""

        returncode = None

        def __init__(self, argv, **_kw):
            self.error = None
            mode = argv[-1]

            def target():
                try:
                    o.worker(claim, SHA, mode)
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

    original = o.supervise

    def supervise(c, sha, mode, allocated, j):
        monkeypatch.setenv("SLURM_STEP_ID", str(o.MODES.index(mode)))
        return original(
            c,
            sha,
            mode,
            allocated,
            j,
            command=command,
            popen=LocalProcess,
            reviewer=lambda c, s, m, _timeout: o.review_arm(c, s, m),
        )

    monkeypatch.setattr(o, "supervise", supervise)
    monkeypatch.setattr(o.r.r2, "command", command)
    assert o.batch(claim, SHA) == 0
    for mode, spec in zip(o.MODES, selected, strict=True):
        control = claim / "control" / mode
        observed = o.events_at(control, o.r.r2.read(control / "entry.json"))
        assert [e["phase"] for e in observed] == list(o.PHASES)
        assert o.r.r2.read(control / "review.json")["classification"] == "validated_feasible"
        assert o.r.r2.read(control / "native_terminal.json")["solution_count"] > 0
        products = claim / "cases" / spec.name / "products" / spec.name
        assert o.r.r2.read(products / "independent_validation.json")["status"] == "accepted"
        assert (claim / "cases" / spec.name / "warehouses_used.csv").is_file()
    raw = (
        "123|COMPLETED|0:0|100|\n123.batch|COMPLETED|0:0|100|123K\n"
        "123.extern|COMPLETED|0:0|100|1K\n123.0|COMPLETED|0:0|30|123K\n"
        "123.1|COMPLETED|0:0|30|123K\n"
    )
    receipt = o.collect(claim, SHA, command=lambda *_: SimpleNamespace(returncode=0, stdout=raw))
    assert receipt["status"] == "pair_quality_target_met"
    assert receipt["operational_receipts_closed"]
    assert not receipt["h300_admitted"]
    result = o.audit(claim / receipt["archive"], receipt["sha256"])
    assert result["quality_target_met"]
    assert json.loads((claim / "batch_outcome.json").read_bytes())["unrun"] == []
