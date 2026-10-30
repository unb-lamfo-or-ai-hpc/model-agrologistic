"""Public campaign lifecycle/fault controls; no real scheduler or private inputs."""

import hashlib
import json
import os
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from scripts import mvp2_pyomo_h215_w as driver
from scripts import pyomo_campaign_contract as contract
from scripts import pyomo_worker_bootstrap as b
from tests.test_scalar_highs_h215_8h_startup import fixture as original_fixture
from tests.test_scalar_r3a_operational import allocation_text

SHA = "a" * 40
m = driver.Campaign("gurobi")


@pytest.fixture(params=driver.SOLVERS, autouse=True)
def arm(request, monkeypatch):
    monkeypatch.setattr(sys.modules[__name__], "m", driver.Campaign(request.param))


def fixture():
    files, plan, oldbase = original_fixture()
    oldcase = oldbase.split("/")[1]
    files = {name.replace(oldcase, m.CASE): raw for name, raw in files.items()}
    base = oldbase.replace(oldcase, m.CASE)
    result = driver.r.strict_json(files[base + "result.json"])
    result["result"]["solver_name"] = m.solver
    metadata = result["result"]["metadata"]
    metadata.update(
        pyomo_solver_interface=contract.INTERFACES[m.solver],
        solver_versions=contract.VERSIONS[m.solver],
        effective_native_options=contract.PARAMETERS[m.solver].copy()
        if m.solver != "cbc"
        else None,
        requested_cbc_options=contract.PARAMETERS["cbc"].copy() if m.solver == "cbc" else None,
        common_linear_matrix={
            "schema_version": "ordered-pyomo-linear-matrix-v1",
            "sha256": "c" * 64,
            "variables": 14054654,
            "binary_variables": 307,
            "linear_constraints": 735577,
        },
        native_counters={},
    )
    update(files, base, "result.json", lambda value: value.update(result))
    files["control/sto/cbc-native.log"] = (
        "\n".join(
            ("ratioGap" if k == "ratio" else k) + " was changed from default to " + str(v)
            for k, v in contract.PARAMETERS["cbc"].items()
        )
    ).encode()
    return files, plan, base


SOURCE_ROOT = driver.ROOT


def operational_files(tmp_path):
    files, plan, _ = fixture()
    plan.update(environment={"python": "3.13.15"}, python_sha256="d" * 64)

    def put(name, value):
        files[name] = driver.r.r2.encoded(value)

    put("plan.json", plan)
    job = {
        "job_id": "123",
        "source_commit": SHA,
        "plan_sha256": driver.r.r2.digest(files["plan.json"]),
    }
    put("job.json", job)
    allocation = allocation_text(TimeLimit="12:00:00")
    allocated = driver.o.allocation(allocation, "123", 1271, walltime="12:00:00")
    put("allocation_query.json", {"returncode": 0, "stdout": allocation})
    put("allocation.json", allocated)
    put("batch_entry.json", job)
    entry = {
        **job,
        "mode": "sto",
        "step_id": "0",
        "pid": 999,
        "proc_start_ticks": 100,
        "started_monotonic": 10.0,
    }
    base = "control/sto/"
    if m.solver == "gurobi":
        put(
            base + "gurobi_license.json",
            {
                "entry": entry,
                "schema_version": "pyomo-gurobi-default-license-v1",
                "status": "accepted",
                "large_model_construction_allowed": True,
                "environment_scope": "gurobipy_default_environment_as_used_by_appsi",
                "probe_variable_count": 2001,
                "probe_constraint_count": 2001,
                "private_input_accessed": False,
                "gurobi_version": [13, 0, 3],
                "solver_status_code": 2,
                "objective_value": 2001,
            },
        )
    put(base + "entry.json", entry)
    put(base + "release.json", entry)
    put(
        base + "step_query.json",
        {
            "returncode": 0,
            "stdout": "StepId=123.0 UserId=1271 CPUs=16 Nodes=1 Tasks=1 "
            "State=RUNNING NodeList=r1i3n5",
        },
    )
    events = [
        {"entry": entry, "phase": phase, "elapsed_seconds": float(i)}
        for i, phase in enumerate(driver.o.PHASES)
    ]
    for i, event in enumerate(events):
        put(base + f"phase-{i:02d}.json", event)
    usage = driver.o.phase_usage(events, events[-1]["elapsed_seconds"], profile=m.PROFILE)
    put(
        base + "controller.json",
        {
            "status": "closed_feasible_arm",
            "step_id": "0",
            "local_client_reaped": True,
            "usage": usage,
            "product_review_seconds": 1.0,
        },
    )
    raw = "123.0|COMPLETED|0:0|60|123K\n"
    put(base + "terminal_step.json", {"row": driver.r.r2.accounting(raw, "123")[0], "raw": raw})
    assessment = m.case_review(files, plan)
    put(base + "review.json", assessment)
    build = {
        "solver": m.solver,
        "pyomo": "6.10.1",
        "population_optimized": False,
        "native_version": {"gurobi": "13.0.3", "scip": "10.0.2", "cbc": "2.10.13.0"}[m.solver],
    }
    put(base + "native_build.json", build)
    put(
        base + "runtime.json",
        {
            "native": build,
            "python": "3.13.15",
            "python_sha256": plan["python_sha256"],
            "solver_threads": 4,
            "affinity_logical_cpus": list(range(16)),
        },
    )
    put(
        base + "qualification.json",
        {"tests": 71, "failures": 0, "errors": 0, "skipped": 0, "status": "accepted"},
    )
    put(
        base + "native_terminal.json",
        {
            "entry": entry,
            "time_limit_seconds": 28800,
            "runtime_seconds": 2.0,
            **{
                k: assessment[k]
                for k in (
                    "parameter_evidence",
                    "common_linear_matrix",
                    "reformulation",
                    "native_counters",
                )
            },
        },
    )
    put("batch_outcome.json", {"status": "one_pyomo_observation_returned"})
    files["accounting.txt"] = (
        "123|COMPLETED|0:0|60|\n123.batch|COMPLETED|0:0|60|123K\n" + raw
    ).encode()
    recorder = b.Recorder(tmp_path, entry, clock=lambda: 10.0)
    for stage in b.STAGES:
        recorder.stage(stage, lambda: None)
    for path in tmp_path.glob("startup-*.json"):
        files[base + path.name] = path.read_bytes()
    put(
        base + "bootstrap.json",
        {
            "schema_version": "pyomo-bootstrap-v1",
            "entry": entry,
            "isolated": True,
            "no_site": True,
            "no_user_site": True,
            "native_or_application_loaded_before_release": False,
            "full_provenance_pending": True,
        },
    )
    return files, plan


def test_complete_operational_replay_closes_with_original_certificates(tmp_path, monkeypatch):
    files, plan = operational_files(tmp_path)
    monkeypatch.setattr(m, "design", lambda _: plan)
    result = m.portable_review(files)
    assert result["operational_receipts_closed"], result
    assert result["status"] == "pyomo_quality_target_met"
    assert result["common_gap"] == 0.005


@pytest.mark.parametrize(
    "member",
    [
        "runtime.json",
        "native_terminal.json",
        "phase-02.json",
        "qualification.json",
        "terminal_step.json",
    ],
)
def test_incomplete_receipts_never_close_as_operational_success(tmp_path, monkeypatch, member):
    files, plan = operational_files(tmp_path)
    monkeypatch.setattr(m, "design", lambda _: plan)
    del files["control/sto/" + member]
    result = m.portable_review(files)
    assert not result["operational_receipts_closed"]
    assert result["status"] == "pyomo_forensic_partial_preserved"


def update(files, base, name, transform):
    value = driver.r.strict_json(files[base + name])
    transform(value)
    files[base + name] = driver.r.r2.encoded(value)
    completion = driver.r.strict_json(files[base + "run_completion.json"])
    completion["artifacts"][name] = driver.r.r2.digest(files[base + name])
    files[base + "run_completion.json"] = driver.r.r2.encoded(completion)


def test_existing_claim_never_submits_or_collects(tmp_path, monkeypatch):
    # This case exercises the LOGIN existing-claim guard even when pytest itself
    # runs inside a public compute-node qualification allocation.
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    claim = tmp_path / m.CLAIM
    claim.mkdir()
    sentinel = claim / "original"
    sentinel.write_bytes(b"preserve")
    monkeypatch.setattr(m, "output_location", lambda *_: None)
    with pytest.raises(ValueError, match="Existing Pyomo claim"):
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


@pytest.mark.parametrize(
    "kind,classification",
    [
        ("quality", "quality_target_met"),
        ("wide", "validated_feasible_above_target_or_uncertified_bound"),
        ("missing_bound", "validated_feasible_above_target_or_uncertified_bound"),
        ("rejected", "incumbent_validation_rejected"),
        ("none", "no_usable_incumbent"),
    ],
)
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
        update(
            files,
            base,
            "independent_validation.json",
            lambda v: v.update(
                status=status,
                failed_check_count=1 if kind == "rejected" else 0,
            ),
        )
        update(
            files,
            base,
            "run_summary.json",
            lambda v: v.update(
                independent_validation_status=status,
            ),
        )
    report = m.case_review(files, plan)
    assert report["classification"] == classification
    assert report["quality_target_met"] is (kind == "quality")
    assert not report["additional_highs_execution_admitted"] and not report["repeats_admitted"]


@pytest.mark.parametrize("state", ["OUT_OF_MEMORY", "TIMEOUT", "FAILED", "COMPLETED"])
def test_partial_terminal_observation_is_preserved_without_success(state, monkeypatch):
    files, plan, _ = fixture()
    files = {"plan.json": driver.r.r2.encoded(plan)}
    job = {
        "job_id": "123",
        "source_commit": SHA,
        "plan_sha256": driver.r.r2.digest(files["plan.json"]),
    }
    files["job.json"] = driver.r.r2.encoded(job)
    files["accounting.txt"] = f"123|{state}|1:0|60|\n123.batch|{state}|1:0|60|123K\n".encode()
    monkeypatch.setattr(m, "design", lambda _: plan)
    report = m.portable_review(files)
    assert report["status"] == "pyomo_forensic_partial_preserved"
    assert not report["quality_target_met"] and not report["operational_receipts_closed"]
    assert not report["highs_execution_admitted"]


def test_transport_preserves_partial_and_rejects_overwrite_or_changed_checksum(
    tmp_path,
    monkeypatch,
):
    claim = tmp_path / m.CLAIM
    claim.mkdir()
    plan = {"cases": [{}], "source_commit": SHA}
    driver.r.r2.write(claim / "plan.json", plan)
    job = {
        "job_id": "123",
        "source_commit": SHA,
        "plan_sha256": driver.r.file_hash(claim / "plan.json"),
    }
    driver.r.r2.write(claim / "job.json", job)
    monkeypatch.setattr(m, "load", lambda *_: plan)
    monkeypatch.setattr(m, "design", lambda _: plan)
    response = SimpleNamespace(
        returncode=0,
        stdout="123|OUT_OF_MEMORY|0:125|60|\n123.batch|OUT_OF_MEMORY|0:125|60|123K\n",
    )
    result = m.collect(claim, SHA, command=lambda *_: response)
    assert result["status"] == "pyomo_forensic_partial_preserved"
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


def test_admission_check_is_test_only_and_rejects_before_claim(monkeypatch):
    from types import SimpleNamespace

    def command(argv, **_):
        assert argv == driver.ADMISSION_COMMAND and "--test-only" in argv
        assert "--time=12:00:00" in argv
        return SimpleNamespace(returncode=1, stdout="", stderr="rejected")

    monkeypatch.setattr(driver.r.r2, "command", command)
    with pytest.raises(ValueError, match="no claim/job"):
        m.admission_test()


def cold_fixture(tmp_path, *, controlled=False, fail=False):
    base = tmp_path / "model-agrologistic-public"
    root = base / "pyomo-h215-w-driver-public/source"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts/__init__.py").write_text("")
    (root / b.BOOTSTRAP).write_bytes((SOURCE_ROOT / b.BOOTSTRAP).read_bytes())
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
    driver = (
        driver.replace("FAIL_VALUE", repr(fail))
        + "\nclass Campaign:\n    def __init__(self, solver): pass\n"
        "    worker = staticmethod(worker)\n"
    )
    (root / b.DRIVER_FILE).write_text(driver)
    claim = base / m.CLAIM
    claim.mkdir()
    files = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in (b.BOOTSTRAP, b.DRIVER_FILE)
    }
    source = b.encoded({"source_commit": SHA, "files": files})
    plan = b.encoded(
        {
            "source_commit": SHA,
            "source_root": str(root),
            "solver_name": m.solver,
            "artifact_sha256": {"source.json": hashlib.sha256(source).hexdigest()},
        }
    )
    job = {"job_id": "123", "source_commit": SHA, "plan_sha256": hashlib.sha256(plan).hexdigest()}
    (claim / "source.json").write_bytes(source)
    (claim / "plan.json").write_bytes(plan)
    (claim / "job.json").write_bytes(b.encoded(job))
    control = claim / "control/sto"
    if not controlled:
        control.mkdir(parents=True)
    argv = [
        sys.executable,
        "-B",
        "-I",
        "-S",
        str(root / b.BOOTSTRAP),
        "--claim",
        str(claim),
        "--source-sha",
        SHA,
        "--mode",
        "sto",
        "--solver",
        m.solver,
    ]
    env = {
        **os.environ,
        "SLURM_JOB_ID": "123",
        "SLURM_STEP_ID": "0",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    return claim, control, root, job, argv, env


def until(path, process):
    deadline = time.monotonic() + 10
    while not path.exists():
        assert process.poll() is None, "Child failed before receipt: " + str(path)
        assert time.monotonic() < deadline, "Public child receipt timeout"
        time.sleep(0.01)


def startup_files(claim):
    return {
        p.relative_to(claim).as_posix(): p.read_bytes() for p in claim.rglob("*") if p.is_file()
    }


@pytest.mark.skipif(sys.platform != "linux", reason="Linux /proc cold worker")
@pytest.mark.parametrize("fail", [False, True])
def test_cold_bootstrap_publishes_before_import_and_retains_failed_stage(tmp_path, fail):
    claim, control, root, job, argv, env = cold_fixture(tmp_path, fail=fail)
    child = subprocess.Popen(
        argv, cwd=control, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
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


@pytest.mark.skipif(sys.platform != "linux", reason="Linux /proc cold worker")
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


@pytest.mark.skipif(sys.platform != "linux", reason="Linux /proc cold worker")
def test_released_slow_import_survives_old_45s_guard_with_unchanged_build_budget(
    tmp_path,
    monkeypatch,
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

    monkeypatch.setattr(driver.o.os, "getuid", lambda: 1271, raising=False)
    allocated = driver.o.allocation(
        allocation_text(TimeLimit="12:00:00"), "123", 1271, walltime="12:00:00"
    )
    outcome = driver.o.supervise(
        claim,
        SHA,
        "sto",
        allocated,
        job,
        command=command,
        popen=popen,
        clock=lambda: time.monotonic() + offset[0],
        sleep=sleep,
        reviewer=lambda *_: None,
        invoke=lambda *_: [],
        step_cpus=16,
        bind_step=lambda *a: driver.o.step_binding(*a, cpus=16),
        whole_arm_seconds=35100,
        phase_profile=m.PROFILE,
    )
    assert outcome["status"] == "closed_feasible_arm", outcome
    assert b.review(startup_files(claim), job)["status"] == "complete"
    assert offset[0] > 45 and all(c.poll() == 0 for c in children)
    assert (
        driver.o.phase_usage(
            [
                {
                    "phase": "input_build",
                    "elapsed_seconds": 0.0,
                }
            ],
            3601,
            profile=m.PROFILE,
        )["stop_reason"]
        == "input_build_watchdog"
    )
