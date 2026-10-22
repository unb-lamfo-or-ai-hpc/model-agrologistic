"""Tiny real native D DET/STO + original validation, with fake Slurm transport.

No NPAD, private workbook, W repetition or live designated WLS probe. Explicit
public-fixture adapters bypass h215 identity/shape only inside this test.
"""

import os
import subprocess
import sys
import threading
from dataclasses import replace
from types import SimpleNamespace

from scripts import mvp2_scalar_wd_h215_operational as d
from tests.test_excel_loader import build_tiny_golden_excel
from tests.test_gurobipy_transshipment import require_gurobi_available
from tests.test_scalar_r3a import tiny_selection
from tests.test_scalar_r3a_operational import allocation_text, osrm_audit

SHA = "a" * 40


def test_real_D_worker_det_nine_scenario_sto_exact_controller_validation_and_transfer(
    tmp_path, monkeypatch
):
    if os.environ.get("AGRO_REQUIRE_NATIVE_SOLVERS") != "1":
        require_gurobi_available()
    import gurobipy as gp

    workbook = tmp_path / "public.xlsx"
    build_tiny_golden_excel(workbook)
    before = workbook.read_bytes()
    shape = {"warehouses": 2, "periods": 2, "det_scenarios": 1, "sto_scenarios": 9}
    policy = {
        **tiny_selection(),
        "population_manifest_sha256": d.o.POPULATION_SHA,
        "population_order_sha256": d.o.ORDER_SHA,
    }
    candidates = d.g.proposed_specs(workbook)
    for label, spec in candidates.items():
        candidates[label] = replace(
            spec,
            loader=replace(
                spec.loader,
                compute_haversine_distances=True,
                use_workbook_distances=False,
                required_distance_source="any",
                penalty_policy="fixed",
                default_unmet_demand_penalty=90000,
                default_emergency_static_penalty=45000,
                default_emergency_reception_penalty=45000,
            ),
            model=replace(spec.model, route_filter_strategy="none"),
        )
    selected = [candidates["D_" + mode] for mode in d.MODES]
    cells = {}
    for label, spec in candidates.items():
        cell = d.g.inspect_cell(spec)
        cell["warehouse_selection"] = d.r.warehouses.membership_receipt(
            cell.pop("warehouse_data"), policy
        )
        cells[label] = cell
    comparisons = {
        mode: d.g.compare_pair(cells["W_" + mode], cells["D_" + mode]) for mode in d.MODES
    }
    assert len(cells["D_sto"]["effective_probabilities"]) == 9
    previous = {
        "archive_sha256": d.g.W_SHA,
        "source_commit": d.g.W_SOURCE,
        "plan_sha256": d.g.W_PLAN,
        "scientific_sources": {},
        "review": {
            "job_id": "2217990",
            "status": "pair_quality_target_met",
            "qualification": "Synthetic transport fixture, not original historical evidence.",
        },
        "receipts": {
            mode: {
                "experiment": cells["W_" + mode]["specification"],
                "mathematical_contract": cells["W_" + mode]["contract"],
                "warehouse_selection": cells["W_" + mode]["warehouse_selection"],
                "effective_scenario_probabilities": cells["W_" + mode]["effective_probabilities"],
            }
            for mode in d.MODES
        },
    }
    files = {
        "source.json": d.r.r2.encoded({"source_commit": SHA, "files": {}}),
        "warehouse_selection.json": d.r.r2.encoded(policy),
        "historical_w.json": d.r.r2.encoded(previous),
        "materialization.original.json": d.r.r2.encoded(osrm_audit()),
    }
    plan = {
        "schema_version": "scalar-wd-h215-operational-v1",
        "source_commit": SHA,
        "source_root": str(d.ROOT),
        "python": sys.executable,
        "python_sha256": d.r.file_hash(sys.executable),
        "tools": dict.fromkeys(d.o.TOOLS, sys.executable),
        "tool_sha256": dict.fromkeys(d.o.TOOLS, d.r.file_hash(sys.executable)),
        "profile": d.PROFILE,
        "budget": d.budget(),
        "expected_shape": shape,
        "cases": [d.r.spec_payload(s) for s in selected],
        "selection_sha256": d.r.r2.digest(files["warehouse_selection.json"]),
        "artifact_sha256": {n: d.r.r2.digest(b) for n, b in files.items()},
        "input_paths": dict.fromkeys(d.INPUT_KEYS, str(workbook)),
        "input_sha256": {
            "workbook": d.o.WORKBOOK_SHA,
            "population": d.o.POPULATION_SHA,
            "order": d.o.ORDER_SHA,
            "w_archive": d.g.W_SHA,
            "materialization": d.r.r2.digest(files["materialization.original.json"]),
        },
        **d.closed(),
    }
    plan = d.r.strict_json(d.r.r2.encoded(plan))
    claim = tmp_path / d.CLAIM
    claim.mkdir()
    for name, raw in {**files, "plan.json": d.r.r2.encoded(plan)}.items():
        (claim / name).write_bytes(raw)
    job = {"job_id": "123", "source_commit": SHA, "plan_sha256": d.r.file_hash(claim / "plan.json")}
    d.r.r2.write(claim / "job.json", job)
    # Fixed public-fixture seams only. No production CLI option permits these overrides.
    monkeypatch.setattr(d, "SHAPE", shape)
    monkeypatch.setattr(d, "specs", lambda _: selected)
    monkeypatch.setattr(d, "case_contract", lambda _: None)
    monkeypatch.setattr(d, "load", lambda *_: plan)
    monkeypatch.setattr(d, "recheck_inputs", lambda *_: None)
    monkeypatch.setattr(d.g, "inspect_comparison", lambda *_: (cells, comparisons))
    monkeypatch.setattr(
        d.g,
        "source_inventory",
        lambda *_: (_ for _ in ()).throw(AssertionError("No Git on compute")),
    )
    monkeypatch.setattr(d.o, "verify_tools", lambda *_: None)
    monkeypatch.setattr(d.os, "getuid", lambda: 1271, raising=False)
    monkeypatch.setattr(d.os, "sched_getaffinity", lambda _: set(range(4)), raising=False)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setenv("SLURM_STEP_ID", "0")
    from scripts import probe_npad_gurobi_license as license_probe

    monkeypatch.setattr(
        license_probe,
        "probe",
        lambda: {
            "status": "accepted",
            "probe_variable_count": 2001,
            "probe_constraint_count": 2001,
            "objective_value": 2001,
            "license_file": license_probe.LICENSE_FILE,
            "gurobi_version": list(gp.gurobi.version()),
            "qualification": "Injected fixture, not a live WLS capability.",
        },
    )

    def command(argv, **_):
        if argv[0] == "scontrol" and argv[3] == "job":
            text = allocation_text()
        elif argv[0] == "scontrol" and argv[3] == "step":
            text = (
                f"StepId={argv[-1]} UserId=1271 CPUs=4 Nodes=1 Tasks=1 "
                "State=RUNNING NodeList=r1i3n5"
            )
        elif argv[0] == "sacct":
            text = f"123.{os.environ['SLURM_STEP_ID']}|COMPLETED|0:0|30|123K\n"
        else:
            raise AssertionError("No real scheduler or cancellation")
        return SimpleNamespace(returncode=0, stdout=text, stderr="")

    class LocalWorker:
        returncode = None

        def __init__(self, argv, **_):
            self.error = None
            mode = argv[-1]

            def target():
                try:
                    d.worker(claim, SHA, mode)
                    self.returncode = 0
                except Exception as exc:
                    import traceback

                    traceback.print_exc()  # Public fixture only; no NPAD/WLS secrets here.
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

    original_supervise = d.o.supervise

    def supervise(c, sha, mode, allocated, j):
        monkeypatch.setenv("SLURM_STEP_ID", str(d.MODES.index(mode)))
        return original_supervise(
            c,
            sha,
            mode,
            allocated,
            j,
            invoke=d.invocation,
            reviewer=lambda c, s, m, _timeout: d.review_arm(c, s, m),
            command=command,
            popen=LocalWorker,
            phase_profile=d.PROFILE,
            whole_arm_seconds=18900,
        )

    monkeypatch.setattr(d, "supervise", supervise)
    monkeypatch.setattr(d.r.r2, "command", command)
    assert d.batch(claim, SHA) == 0
    for mode, spec in zip(d.MODES, selected, strict=True):
        control = claim / "control" / mode
        assert d.r.r2.read(control / "review.json")["classification"] == "validated_feasible"
        assert d.r.r2.read(control / "native_terminal.json")["time_limit_seconds"] == 14400
        assert (claim / "cases" / spec.name / "warehouses_used.csv").exists()
        products = claim / "cases" / spec.name / "products" / spec.name
        assert d.r.r2.read(products / "independent_validation.json")["status"] == "accepted"
        assert d.r.r2.read(products / "resources/matrix_statistics.json")
    raw = (
        "123|COMPLETED|0:0|100|\n123.batch|COMPLETED|0:0|100|123K\n123.extern|COMPLETED|0:0|100|1K\n"
        "123.0|COMPLETED|0:0|30|123K\n123.1|COMPLETED|0:0|30|123K\n"
    )
    report = d.collect(
        claim, SHA, command=lambda *_: SimpleNamespace(returncode=0, stdout=raw, stderr="")
    )
    assert report["operational_receipts_closed"], report
    assert all(
        a["has_usable_incumbent"] and a["classification"] == "validated_feasible"
        for a in report["arms"]
    )
    assert all(
        a["diagnostics"]["positive_flows_by_family"]["OC"]["positive_records"] > 0
        for a in report["arms"]
    )
    assert d.audit(claim / report["archive"], report["sha256"])["status"] == report["status"]
    assert not report["w_repetition_admitted"] and not report["automatic_follow_on_allowed"]
    assert workbook.read_bytes() == before
