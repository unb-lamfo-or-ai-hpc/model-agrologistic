"""Public nonnative controls; safe login regression, never a scheduler or solver."""

import copy
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import highs_worker_bootstrap as b
from scripts import mvp2_scalar_highs_h215_8h_startup as m
from tests.test_scalar_r3a_operational import allocation_text

SHA = "a" * 40


def fixture():
    files = {}
    case = "cases/" + m.CASE + "/"
    base = case + "products/" + m.CASE + "/"

    def put(name, value):
        files[name] = m.r.r2.encoded(value)

    selection = {"included": [], "count": 215}
    contract = {"public": "fixture"}
    experiment = {"public": "fixture"}
    plan = {"cases": [experiment], "source_commit": SHA}
    native = {
        "status": "feasible", "objective_value": 100.0, "objective_bound": 99.5,
        "solver_backend": "pyomo", "solver_name": "highs", "model_mode": "sto",
        "metadata": {
            "run_identity": "fixture", "effective_highs_options": m.EXPECTED_PARAMS.copy(),
            "pyomo_solver_interface": "appsi_highs",
            "solver_versions": {"pyomo": "6.10.1", "highspy": "1.15.1"},
            "highs_native_version": "1.15.1",
            "pyomo_reformulation": {
                "policy": m.POLICY,
                "equivalence": "physical_investment_projection_and_optimal_scalar_value",
                "entire_redundant_slack_region_preserved": False,
                "bounds_sha256": "b" * 64, "candidate_slack_bounds": 0, "maximum_bound": 0,
            },
            "solver_termination": "gaplimit", "pyomo_native_gap": 0.0051,
            "timings": {"solver_reported_runtime_seconds": 2.0},
        },
    }
    put(base + "result.json", {"schema_version": 2, "experiment": experiment, "result": native})
    put(base + "independent_validation.json", {
        "status": "accepted", "failed_check_count": 0,
        "validator_version": "mvp2-scalar-independent-residuals-v1",
        "absolute_tolerance": 1e-5, "relative_tolerance": 1e-8,
        "families": {"public": {"failed": 0}},
    })
    put(base + "run_summary.json", {"independent_validation_status": "accepted"})
    put(base + "preflight.json", {})
    put(base + "model_audit.json", {})
    put(base + "run_completion.json", {
        "status": "complete", "run_identity": "fixture",
        "artifacts": {name: m.r.r2.digest(files[base + name]) for name in (
            "result.json", "independent_validation.json", "run_summary.json",
            "preflight.json", "model_audit.json",
        )},
    })
    put(case + "input_receipt.json", {
        "experiment": experiment, "mathematical_contract": contract,
        "effective_scenario_probabilities": {"public": 1.0}, "warehouse_selection": selection,
    })
    put(case + "warehouses_used.json", selection)
    files[case + "warehouses_used.csv"] = m.r.warehouses.csv_bytes([])
    put("historical_w.json", {"receipts": {"sto": {
        "mathematical_contract": contract, "effective_scenario_probabilities": {"public": 1.0},
        "warehouse_selection": selection,
    }}})
    return files, plan, base


def update(files, base, name, transform):
    value = m.r.strict_json(files[base + name])
    transform(value)
    files[base + name] = m.r.r2.encoded(value)
    completion = m.r.strict_json(files[base + "run_completion.json"])
    completion["artifacts"][name] = m.r.r2.digest(files[base + name])
    files[base + "run_completion.json"] = m.r.r2.encoded(completion)


def test_one_frozen_contract_preserves_science_and_uses_no_gurobi_parameters(tmp_path):
    workbook = tmp_path / "public"
    workbook.write_bytes(b"public")
    selected = m.spec(workbook)
    payload = m.r.spec_payload(selected)
    payload["workbook_sha256"] = m.o.WORKBOOK_SHA
    payload = m.r.strict_json(m.r.r2.encoded(payload))
    m.case_contract([payload])
    original = m.o.specs(workbook)[1]
    assert selected.model == original.model and selected.loader == original.loader
    assert selected.solver.backend == "pyomo" and selected.model.mode == "sto"
    assert selected.solver.solver_options == {
        "indicator_reformulation": m.POLICY, "pyomo_max_variables": 16000000,
    }
    assert selected.solver.threads == 4 and selected.solver.time_limit == 28800
    assert not selected.model.use_direct_origin_customer
    changed = copy.deepcopy(payload)
    changed["model"]["use_direct_origin_customer"] = True
    with pytest.raises(ValueError, match="Frozen one-arm"):
        m.case_contract([changed])


def test_budget_and_authority_cannot_admit_follow_on():
    assert m.budget()["step_seconds"] == 35100
    assert m.budget()["reserve_seconds"] == 6300
    assert all(value is False for value in m.closed().values())
    assert "solver_soft_memory_decimal_gb" not in m.PROFILE


@pytest.mark.parametrize("parent", [
    "/home/vrrcelestino", "/home/vrrcelestino/model-agrologistic",
    "/home/vrrcelestino/other", "/tmp/model-agrologistic",
])
def test_output_cannot_write_home_input_or_unapproved_root(parent):
    with pytest.raises(ValueError, match="dedicated"):
        m.output_location(Path(parent) / m.CLAIM)


def test_output_allows_only_project_sibling():
    m.output_location(Path("/home/vrrcelestino/model-agrologistic-hygiene-audit") / m.CLAIM)


def test_existing_claim_never_submits_or_collects(tmp_path, monkeypatch):
    # This case exercises the LOGIN existing-claim guard even when pytest itself
    # runs inside a public compute-node qualification allocation.
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    claim = tmp_path / m.CLAIM
    claim.mkdir()
    sentinel = claim / "original"
    sentinel.write_bytes(b"preserve")
    monkeypatch.setattr(m, "output_location", lambda *_: None)
    with pytest.raises(ValueError, match="Existing HiGHS claim"):
        m.start(claim, SHA, True, {}, command=lambda *_: pytest.fail("No scheduler"))
    assert sentinel.read_bytes() == b"preserve"


def test_compute_context_refuses_start_without_touching_existing_claim(tmp_path, monkeypatch):
    monkeypatch.setenv("SLURM_JOB_ID", "2227457")
    claim = tmp_path / m.CLAIM
    claim.mkdir()
    sentinel = claim / "original"
    sentinel.write_bytes(b"preserve")
    monkeypatch.setattr(m, "output_location", lambda *_: None)
    with pytest.raises(ValueError, match="Login Python3.13 only"):
        m.start(claim, SHA, True, {}, command=lambda *_: pytest.fail("No scheduler"))
    assert sentinel.read_bytes() == b"preserve"
    assert not (claim / "submission_intent.json").exists()


def test_acknowledgement_precedes_preparation(tmp_path):
    with pytest.raises(ValueError, match="Explicit human"):
        m.start(tmp_path / m.CLAIM, SHA, False, {})


def test_fingerprint_reads_installed_metadata_without_native_import(tmp_path, monkeypatch):
    module = tmp_path / "fixture.py"
    module.write_bytes(b"public distribution fixture")
    monkeypatch.setattr(m, "distribution", lambda name: SimpleNamespace(
        version="6.10.1" if name == "pyomo" else "1.15.1",
        files=[module.name], locate_file=lambda _: module,
    ))
    report = m.environment()
    assert report["pyomo"] == "6.10.1" and report["highspy"] == "1.15.1"
    assert set(report["package_sha256"]) == {"pyomo", "highspy"}



@pytest.mark.parametrize("kind,classification", [
    ("quality", "quality_target_met"),
    ("wide", "validated_feasible_above_target_or_uncertified_bound"),
    ("missing_bound", "validated_feasible_above_target_or_uncertified_bound"),
    ("rejected", "incumbent_validation_rejected"),
    ("none", "no_usable_incumbent"),
])
def test_negative_outcomes_are_distinct_and_cannot_admit_another_solver(kind, classification):
    files, plan, base = fixture()
    if kind in {"wide", "missing_bound", "none"}:
        def alter(value):
            result = value["result"]
            result["objective_bound"] = 50.0 if kind == "wide" else None
            if kind == "none":
                result["status"] = "error"
                result["objective_value"] = None
                result["metadata"]["solver_termination"] = "memlimit"
        update(files, base, "result.json", alter)
    if kind in {"rejected", "none"}:
        status = "rejected" if kind == "rejected" else "no_solution"
        update(files, base, "independent_validation.json", lambda v: v.update(
            status=status, failed_check_count=1 if kind == "rejected" else 0,
        ))
        update(files, base, "run_summary.json", lambda v: v.update(
            independent_validation_status=status,
        ))
    report = m.case_review(files, plan)
    assert report["classification"] == classification
    assert report["quality_target_met"] is (kind == "quality")
    assert not report["additional_highs_execution_admitted"] and not report["repeats_admitted"]


@pytest.mark.parametrize("kind", ["parameters", "tolerance", "residuals", "identity", "digest"])
def test_original_certificate_or_parameter_drift_is_rejected(kind):
    files, plan, base = fixture()
    if kind == "parameters":
        update(files, base, "result.json", lambda v: v["result"]["metadata"].update(
            effective_highs_options={},
        ))
    elif kind == "tolerance":
        update(files, base, "independent_validation.json", lambda v: v.update(
            absolute_tolerance=1.0,
        ))
    elif kind == "residuals":
        update(files, base, "independent_validation.json", lambda v: v.update(
            families={"bad": {"failed": 1}},
        ))
    elif kind == "identity":
        update(files, base, "result.json", lambda v: v["result"]["metadata"].update(
            run_identity="different",
        ))
    else:
        files[base + "model_audit.json"] = b"changed"
    with pytest.raises(ValueError):
        m.case_review(files, plan)


@pytest.mark.parametrize("state", ["OUT_OF_MEMORY", "TIMEOUT", "FAILED", "COMPLETED"])
def test_partial_terminal_observation_is_preserved_without_success(state, monkeypatch):
    files, plan, _ = fixture()
    files = {"plan.json": m.r.r2.encoded(plan)}
    job = {"job_id": "123", "source_commit": SHA,
           "plan_sha256": m.r.r2.digest(files["plan.json"])}
    files["job.json"] = m.r.r2.encoded(job)
    files["accounting.txt"] = f"123|{state}|1:0|60|\n123.batch|{state}|1:0|60|123K\n".encode()
    monkeypatch.setattr(m, "design", lambda _: plan)
    report = m.portable_review(files)
    assert report["status"] == "highs_forensic_partial_preserved"
    assert not report["quality_target_met"] and not report["operational_receipts_closed"]
    assert not report["highs_execution_admitted"]


def test_transport_preserves_partial_and_rejects_overwrite_or_changed_checksum(
    tmp_path, monkeypatch,
):
    claim = tmp_path / m.CLAIM
    claim.mkdir()
    plan = {"cases": [{}], "source_commit": SHA}
    m.r.r2.write(claim / "plan.json", plan)
    job = {"job_id": "123", "source_commit": SHA,
           "plan_sha256": m.r.file_hash(claim / "plan.json")}
    m.r.r2.write(claim / "job.json", job)
    monkeypatch.setattr(m, "load", lambda *_: plan)
    monkeypatch.setattr(m, "design", lambda _: plan)
    response = SimpleNamespace(
        returncode=0,
        stdout="123|OUT_OF_MEMORY|0:125|60|\n123.batch|OUT_OF_MEMORY|0:125|60|123K\n",
    )
    result = m.collect(claim, SHA, command=lambda *_: response)
    assert result["status"] == "highs_forensic_partial_preserved"
    archive = claim / m.ARCHIVE
    assert m.audit(archive, result["sha256"])["status"] == result["status"]
    original = archive.read_bytes()
    assert m.collect(claim, SHA, command=lambda *_: pytest.fail("No scheduler")) == result
    assert archive.read_bytes() == original
    archive.write_bytes(b"changed")
    with pytest.raises(ValueError, match="Preserved transfer"):
        m.collect(claim, SHA, command=lambda *_: response)


def test_snapshot_rejects_private_workbook_and_links(tmp_path):
    root = tmp_path / "claim"
    root.mkdir()
    (root / "private.xlsx").write_bytes(b"private")
    with pytest.raises(ValueError, match="Forbidden private"):
        m.snapshot(root)


def test_wrapper_never_installs_or_uses_license_or_automatic_highs():
    source = (m.ROOT / "scripts/npad_scalar_highs_h215_w_native8h_startup.sh").read_text()
    assert "pip install" not in source and "conda " not in source
    assert "GRB_LICENSE_FILE" not in source and "gurobi.lic" not in source
    assert "--one-reviewed-highs-w" in source
    assert "Existing HiGHS claim" in source


def test_parallel_claims_and_native_sources_remain_separate():
    from scripts import mvp2_scalar_scip_h215_8h as native

    assert m.CLAIM != native.CLAIM and m.ARCHIVE != native.ARCHIVE
    assert m.PROFILE["native_time_limit_seconds_per_arm"] == 28800
    assert m.PROFILE["slurm_wall_seconds"] == 43200
    assert m.budget()["planned_seconds"] == 36900
    assert m.budget()["reservation_logical_cpu_hours"] == 288
    assert m.PYOMO_PATHS == {
        "src/logic/optimization_pyomo.py", "src/logic/pyomo_bounds.py",
    }
    assert m.spec.__module__ != native.spec.__module__


def test_admission_check_is_test_only_and_rejects_before_claim(monkeypatch):
    from types import SimpleNamespace

    def command(argv, **_):
        assert argv == m.ADMISSION_COMMAND and "--test-only" in argv
        assert "--time=12:00:00" in argv
        return SimpleNamespace(returncode=1, stdout="", stderr="rejected")
    monkeypatch.setattr(m.r.r2, "command", command)
    with pytest.raises(ValueError, match="no claim/job"):
        m.admission_test()


def test_design_binds_inputs_scope_and_all_native_sources(tmp_path, monkeypatch):
    workbook = tmp_path / "public"
    workbook.write_bytes(b"public")
    payload = m.r.spec_payload(m.spec(workbook))
    payload["workbook_sha256"] = m.o.WORKBOOK_SHA
    source_files = {
        "src/logic/optimization.py": "c" * 64,
        "src/logic/optimization_pyomo.py": "a" * 64,
        "src/logic/pyomo_bounds.py": "b" * 64,
    }
    artifacts = {
        "source.json": {"source_commit": SHA, "files": source_files},
        "historical_w.json": {
            "archive_sha256": m.g.W_SHA, "source_commit": m.g.W_SOURCE,
            "plan_sha256": m.g.W_PLAN,
            "review": {"job_id": "2217990", "status": "pair_quality_target_met"},
            "scientific_sources": {
                "src/logic/optimization.py": "c" * 64,
                "src/logic/optimization_pyomo.py": "d" * 64,
            },
        },
        "warehouse_selection.json": {
            "target_population": 215, "population_manifest_sha256": m.o.POPULATION_SHA,
            "population_order_sha256": m.o.ORDER_SHA,
        },
        "materialization.original.json": {},
        "failed_highs.json": {
            "job_id": "2226407", "source_commit": m.FAILED_SOURCE,
            "status": "highs_forensic_partial_preserved", "operational_receipts_closed": False,
        },
        "admission_test.json": {
            "argv": m.ADMISSION_COMMAND, "returncode": 0, "job_submitted": False,
        },
    }
    files = {name: m.r.r2.encoded(value) for name, value in artifacts.items()}
    plan = {
        "schema_version": "scalar-highs-h215-w-native8h-startup-v2", "source_commit": SHA,
        "failed_highs_plan_sha256": m.FAILED_PLAN,
        "profile": m.PROFILE, "budget": m.budget(), "expected_shape": m.SHAPE,
        "cases": [payload], "environment": {"pyomo": "6.10.1", "highspy": "1.15.1"},
        "artifact_sha256": {name: m.r.r2.digest(raw) for name, raw in files.items()},
        "input_sha256": {
            "workbook": m.o.WORKBOOK_SHA, "population": m.o.POPULATION_SHA,
            "order": m.o.ORDER_SHA, "w_archive": m.g.W_SHA,
            "failed_highs_archive": m.FAILED_SHA,
            "materialization": m.r.r2.digest(files["materialization.original.json"]),
        }, **m.closed(),
    }
    files["plan.json"] = m.r.r2.encoded(plan)
    monkeypatch.setattr(m.o, "materialization", lambda _: None)
    assert m.design(files)["source_commit"] == SHA
    for key in ("workbook", "population", "order", "w_archive", "failed_highs_archive"):
        altered = copy.deepcopy(plan)
        altered["input_sha256"][key] = "0" * 64
        with pytest.raises(ValueError, match="Frozen inputs"):
            m.design({**files, "plan.json": m.r.r2.encoded(altered)})
    for key in m.closed():
        altered = copy.deepcopy(plan)
        altered[key] = True
        with pytest.raises(ValueError, match="scope"):
            m.design({**files, "plan.json": m.r.r2.encoded(altered)})
    for change in ("modify", "remove", "extra"):
        drift = copy.deepcopy(artifacts["source.json"])
        if change == "modify":
            drift["files"]["src/logic/optimization.py"] = "0" * 64
        elif change == "remove":
            drift["files"].pop("src/logic/optimization.py")
        else:
            drift["files"]["src/logic/undeclared.py"] = "0" * 64
        raw = m.r.r2.encoded(drift)
        altered = copy.deepcopy(plan)
        altered["artifact_sha256"]["source.json"] = m.r.r2.digest(raw)
        with pytest.raises(ValueError, match="Native source"):
            m.design({**files, "source.json": raw, "plan.json": m.r.r2.encoded(altered)})


@pytest.mark.parametrize("key,value", [
    ("policy", "arbitrary_big_m"),
    ("entire_redundant_slack_region_preserved", True),
    ("maximum_bound", -1),
    ("bounds_sha256", "missing"),
])
def test_reformulation_provenance_cannot_be_relabelled(key, value):
    files, plan, base = fixture()
    update(files, base, "result.json", lambda v: v["result"]["metadata"][
        "pyomo_reformulation"
    ].update({key: value}))
    with pytest.raises(ValueError, match="reformulation"):
        m.case_review(files, plan)


# Real -I -S child controls use public files and a synthetic application module.
# They never import a solver, call a scheduler, read private input or access NPAD.


def cold_fixture(tmp_path, *, controlled=False, fail=False):
    base = tmp_path / "model-agrologistic-public"
    root = base / "scalar-highs-h215-w-native8h-startup-driver-public/source"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts/__init__.py").write_text("")
    (root / b.BOOTSTRAP).write_bytes((m.ROOT / b.BOOTSTRAP).read_bytes())
    # Wait during import: entry/release must already exist. Tests can advance the
    # supervisor clock beyond 45 seconds while this real child remains alive.
    driver = """
import pathlib,time,json,os
control=pathlib.Path.cwd()
(control/"application-imported").write_text("after release")
while not (control/"allow-import").exists():
    time.sleep(0.01)
FAIL = FAIL_VALUE

def worker(claim, sha, mode, *, entry, startup):
    if FAIL:
        def reject():
            raise ValueError("public failure")
        startup.stage("plan_validation", reject)
    for name in ("plan_validation","source_verification","runtime_fingerprints",
                 "input_hashes","tool_verification","native_identity",
                 "public_qualification","runtime_receipt"):
        startup.stage(name, lambda: None)
    for i,name in enumerate(("optimization","native_return","independent_validation",
                             "artifact_export","complete"),1):
        raw={"entry":entry,"phase":name,"elapsed_seconds":time.monotonic()-entry["started_monotonic"]}
        (control/("phase-"+str(i).zfill(2)+".json")).write_text(json.dumps(raw))
"""
    driver = driver.replace("FAIL_VALUE", repr(fail))
    (root / b.DRIVER_FILE).write_text(driver)
    claim = base / b.CLAIM
    claim.mkdir()
    files = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
             for name in (b.BOOTSTRAP, b.DRIVER_FILE)}
    source = b.encoded({"source_commit": SHA, "files": files})
    plan = b.encoded({
        "source_commit": SHA, "source_root": str(root),
        "artifact_sha256": {"source.json": hashlib.sha256(source).hexdigest()},
    })
    job = {"job_id": "123", "source_commit": SHA, "plan_sha256": hashlib.sha256(plan).hexdigest()}
    (claim / "source.json").write_bytes(source)
    (claim / "plan.json").write_bytes(plan)
    (claim / "job.json").write_bytes(b.encoded(job))
    control = claim / "control/sto"
    if not controlled:
        control.mkdir(parents=True)
    argv = [sys.executable, "-B", "-I", "-S", str(root / b.BOOTSTRAP),
            "--claim", str(claim), "--source-sha", SHA, "--mode", "sto"]
    env = {**os.environ, "SLURM_JOB_ID": "123", "SLURM_STEP_ID": "0",
           "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    return claim, control, root, job, argv, env


def until(path, process):
    deadline = time.monotonic() + 10
    while not path.exists():
        assert process.poll() is None, "Child failed before receipt: " + str(path)
        assert time.monotonic() < deadline, "Public child receipt timeout"
        time.sleep(0.01)


def startup_files(claim):
    return {p.relative_to(claim).as_posix(): p.read_bytes()
            for p in claim.rglob("*") if p.is_file()}


@pytest.mark.parametrize("fail", [False, True])
def test_cold_bootstrap_publishes_before_import_and_retains_failed_stage(tmp_path, fail):
    claim, control, root, job, argv, env = cold_fixture(tmp_path, fail=fail)
    child = subprocess.Popen(argv, cwd=control, env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    try:
        until(control / "bootstrap.json", child)
        assert not (control / "application-imported").exists()
        entry = json.loads((control / "entry.json").read_bytes())
        receipt = json.loads((control / "bootstrap.json").read_bytes())
        assert receipt["no_site"] and receipt["isolated"] and receipt["no_user_site"]
        assert not receipt["native_or_application_loaded_before_release"]
        b.publish(control / "release.json", entry)
        until(control / "application-imported", child)
        partial = b.review(startup_files(claim), job)
        assert partial["status"] == "incomplete" and partial["last_stage"] == "driver_import"
        (control / "allow-import").write_text("continue")
        _, error = child.communicate(timeout=15)
        assert child.returncode == int(fail), error.decode()
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)
    result = b.review(startup_files(claim), job)
    assert result["status"] == ("failed" if fail else "complete")
    if fail:
        assert result["last_stage"] == "plan_validation" and result["error_kind"] == "ValueError"
        assert b"public failure" in error
        assert not (control / "phase-01.json").exists()
    else:
        assert result["completed_stages"] == list(b.STAGES)
        tampered = startup_files(claim)
        raw = json.loads(tampered["control/sto/bootstrap.json"])
        raw["native_or_application_loaded_before_release"] = True
        tampered["control/sto/bootstrap.json"] = b.encoded(raw)
        with pytest.raises(ValueError, match="bootstrap/release"):
            b.review(tampered, job)


@pytest.mark.parametrize("change", ["source", "plan", "job", "release", "flags"])
def test_cold_bootstrap_refuses_changed_identity_before_application_import(tmp_path, change):
    claim, control, root, job, argv, env = cold_fixture(tmp_path)
    if change == "source":
        (root / b.DRIVER_FILE).write_text("raise AssertionError('not pinned')")
    elif change == "plan":
        (claim / "plan.json").write_bytes((claim / "plan.json").read_bytes() + b" ")
    elif change == "job":
        env["SLURM_JOB_ID"] = "999"
    elif change == "flags":
        argv.remove("-S")
    else:
        b.publish(control / "release.json", {"wrong": "release"})
    result = subprocess.run(argv, cwd=control, env=env, capture_output=True, timeout=10)
    assert result.returncode != 0
    assert not (control / "application-imported").exists()
    assert not (control / "phase-01.json").exists()


def test_released_slow_import_survives_old_45s_guard_with_unchanged_build_budget(
    tmp_path, monkeypatch,
):
    claim, control, root, job, argv, env = cold_fixture(tmp_path, controlled=True)
    offset = [0.0]
    children = []

    def popen(_argv, **kwargs):
        child = subprocess.Popen(argv, cwd=control, env=env, **kwargs)
        children.append(child)
        return child

    def command(args, **_):
        if args[0] == "scontrol":
            text = "StepId=123.0 UserId=1271 CPUs=16 Nodes=1 Tasks=1 State=RUNNING NodeList=r1i3n5"
        elif args[0] == "sacct":
            text = "123.0|COMPLETED|0:0|60|123K\n"
        else:
            raise AssertionError("No live scheduler or stop in this successful public test")
        return SimpleNamespace(returncode=0, stdout=text, stderr="")

    def sleep(_):
        if (control / "application-imported").exists():
            # A real child is still initializing while controller time is >45s.
            offset[0] = 55.0
            (control / "allow-import").write_text("continue")
        time.sleep(0.01)

    monkeypatch.setattr(m.o.os, "getuid", lambda: 1271, raising=False)
    allocated = m.o.allocation(allocation_text(TimeLimit="12:00:00"), "123", 1271,
                               walltime="12:00:00")
    outcome = m.o.supervise(
        claim, SHA, "sto", allocated, job, command=command, popen=popen,
        clock=lambda: time.monotonic() + offset[0], sleep=sleep,
        reviewer=lambda *_: None, invoke=lambda *_: [], step_cpus=16,
        bind_step=lambda *a: m.o.step_binding(*a, cpus=16),
        whole_arm_seconds=35100, phase_profile=m.PROFILE,
    )
    assert outcome["status"] == "closed_feasible_arm", outcome
    assert b.review(startup_files(claim), job)["status"] == "complete"
    assert offset[0] > 45 and all(c.poll() == 0 for c in children)
    assert m.o.phase_usage([{
        "phase": "input_build", "elapsed_seconds": 0.0,
    }], 3601, profile=m.PROFILE)["stop_reason"] == "input_build_watchdog"


def test_minimal_invocation_and_consumed_predecessor_are_not_a_new_solver_policy():
    from scripts import mvp2_scalar_highs_h215_8h as prior
    argv = m.invocation("worker", Path("/public") / m.CLAIM, SHA, "--mode", "sto")
    assert "-S" in argv and "highs_worker_bootstrap.py" in " ".join(argv)
    assert m.CLAIM != prior.CLAIM and m.ARCHIVE != prior.ARCHIVE and m.CASE != prior.CASE
    assert m.EXPECTED_PARAMS == prior.EXPECTED_PARAMS
    assert m.PROFILE["build_input_seconds_per_arm"] == prior.PROFILE["build_input_seconds_per_arm"]
    assert m.PYOMO_PATHS == prior.PYOMO_PATHS
    assert m.INPUT_KEYS == (*prior.INPUT_KEYS, "failed_highs_archive")



def test_original_launchers_and_supervisor_keep_their_exact_git_bytes():
    expected = {
        "scripts/mvp2_scalar_highs_h215_8h.py": "918d0efc6b9f9eecfb2df47e7e4c1d251ab19502",
        "scripts/mvp2_scalar_r3a_operational.py": "01689bd30aa12ed06263391f33511ea8b204d35f",
        "scripts/npad_scalar_highs_h215_w_native8h.sh": "3110f5768dc2e3c5a5d238a166f6b7276b921957",
    }
    for name, digest in expected.items():
        raw = (m.ROOT / name).read_bytes()
        header = ("blob " + str(len(raw)) + "\0").encode()
        assert hashlib.sha1(header + raw).hexdigest() == digest
