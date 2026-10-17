"""Complete 3600s/12h integration with explicit scheduler/native/metadata doubles."""

import copy
import gzip
import io
import os
import subprocess
import sys
import tarfile
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from scripts import mvp2_s2_p4_terminal_release as q
from tests import test_mvp2_h300_native_worker as native_fixture
from tests.test_mvp2_h300_partial import fixture as result_fixture
from tests.test_mvp2_s2_h300_runtime import Clock, command_result
from tests.test_mvp2_s2_p4_admission import plan as reference_fixture

r, p, d = q.runtime, q.p, q.d
SOURCE = "c" * 40


def plan():
    value = reference_fixture()["p4_plan"]
    value["files"].update({name: p.sha_file(q.ROOT / name) for name in q.INTEGRATION})
    info = value["preparation"]
    value["schema_version"] = "s2-p4-terminal-plan-v2"
    value["preparation"] = r.preparation(
        SOURCE, info["runtime_sha256"], info["input_sha256"], info["protected_source_sha256"]
    )
    return r.validate(value)


def submit(tmp_path, monkeypatch, reply="456\n"):
    value = plan()
    prior = r.reference_plan(value)
    prior["preparation"]["source_commit"] = "b" * 40
    monkeypatch.setattr(q, "BASE", tmp_path)
    old_claim = tmp_path / q.old.CLAIM
    old_claim.mkdir()
    (old_claim / q.previous.ARCHIVE).write_bytes(b"IMMUTABLE ORIGINAL CARRIER")
    monkeypatch.setattr(q, "predecessor", lambda path: copy.deepcopy(prior))
    calls = []

    def command(argv, **kwargs):
        assert kwargs == {"timeout": 30, "limit": 1024}
        assert (q.directory() / "submission-intent.json").exists()
        calls.append(argv)
        return command_result(reply)

    result = q.start(SOURCE, acknowledged=True, planner=lambda *a: value, command=command)
    return value, result, calls


def install_backend(monkeypatch, result, calls, fail=None):
    original = native_fixture.fake_model

    def model(solver, calls, **kwargs):
        value = original(solver, calls, **kwargs)
        value.Params.TimeLimit = solver.time_limit
        value.Params.OutputFlag = 0
        return value

    monkeypatch.setattr(native_fixture, "fake_model", model)
    native_fixture.install_backend(monkeypatch, result, calls, fail=fail)


@pytest.mark.parametrize("threads", d.GRID)
def test_one_hour_global_profile_only_time_limit_changes(threads):
    expected = asdict(r.old.native.solver_profile(threads))
    expected["time_limit"] = 3600
    assert asdict(r.solver_profile(threads)) == expected
    assert all(
        "TimeLimit" not in v
        for v in r.solver_profile(threads).multiobjective_stage_options.values()
    )
    value = plan()
    assert all(arm["solver"]["time_limit"] == 3600 for arm in value["preparation"]["arms"])
    assert value["preparation"]["allocation"]["walltime_seconds"] == 43200
    assert r.CONTRACT["minimum_ledger_seconds"] == 5 * 5700 + 600 + 900 + 600 == 30600
    assert r.CONTRACT["block_seconds"] - 30600 == 12600


@pytest.mark.parametrize("field", ["time", "arm", "wall", "source", "input"])
def test_versioned_plan_rejects_drift(field):
    value = plan()
    if field == "time":
        value["preparation"]["arms"][0]["solver"]["time_limit"] = 1800
    elif field == "arm":
        value["preparation"]["budget"]["child_watchdog_seconds"] = 5701
    elif field == "wall":
        value["preparation"]["allocation"]["walltime_seconds"] = 21600
    elif field == "source":
        value["files"]["src/fixed.py"] = "f" * 64
    else:
        value["input"]["workbook_sha256"] = "f" * 64
    with pytest.raises(ValueError):
        r.validate(value)


def test_versioned_planner_real_old_seam(monkeypatch):
    reference = r.reference_plan(plan())
    monkeypatch.setattr(r.old, "_plan", lambda *a, **k: copy.deepcopy(reference))
    value = r._plan(SOURCE, q.ROOT, "test-p3", "test-reference")
    assert value == plan()
    assert reference["preparation"]["arms"][0]["solver"]["time_limit"] == 1800
    value["preparation"]["budget_ledger"]["repeats_admitted"] = 0
    with pytest.raises(ValueError, match="plan/ledger drift"):
        r.validate(value)


@pytest.mark.parametrize(
    "returned,export,expected",
    [
        (3599, 100, None),
        (3600, 100, None),
        (3650, 849, None),
        (3650, 850, "return_export_watchdog"),
        (4499, 0, None),
        (4500, 0, "return_export_watchdog"),
    ],
)
def test_shared_return_reserve_not_early_native_stop(returned, export, expected):
    guard = r.SharedDeadlines(0, 5700)
    assert guard.observe(0, ["build"]) is None
    assert guard.observe(530, ["build", "optimization"]) is None
    reason = guard.observe(530 + returned, ["build", "optimization", "export_validation"])
    if reason is None:
        reason = guard.observe(530 + returned + export, list(r.c.PHASES))
    assert reason == expected


@pytest.mark.parametrize(
    "phase,at,reason",
    [
        ("build", 900, "build_watchdog"),
        ("optimization", 5030, "return_export_watchdog"),
        ("cleanup", 1000, "cleanup_watchdog"),
        ("block", 5700, "child_or_block_watchdog"),
    ],
)
def test_every_non_optimizer_bound_still_finite(phase, at, reason):
    guard = r.SharedDeadlines(0, 5700)
    guard.observe(0, ["build"])
    if phase in {"optimization", "cleanup"}:
        guard.observe(530, ["build", "optimization"])
    if phase == "cleanup":
        guard.observe(600, ["build", "optimization", "export_validation"])
        guard.observe(700, list(r.c.PHASES))
    events = list(r.c.PHASES) if phase == "cleanup" else guard.seen
    assert guard.observe(at, events) == reason


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), -1])
def test_invalid_monotonic_observations(bad):
    guard = r.SharedDeadlines(0, 5700)
    with pytest.raises(ValueError):
        guard.observe(bad, ["build"])


def test_failure_cleanup_never_resets_hard_window():
    guard = r.SharedDeadlines(0, 5700)
    guard.observe(0, ["build"])
    guard.observe(100, ["build", "optimization"])
    assert guard.observe(200, ["build", "optimization"], aborted=True) is None
    assert guard.observe(500, ["build", "optimization"], aborted=True) == "cleanup_watchdog"
    with pytest.raises(ValueError):
        guard.observe(501, ["build", "optimization"], aborted=False)


@pytest.mark.parametrize(
    "native,count,stages",
    [("OPTIMAL", 1, 3), ("TIME_LIMIT", 1, 1), ("TIME_LIMIT", 0, 0), ("MEM_LIMIT", 1, 1)],
)
def test_actual_backend_seams_disposal_and_3600_diagnostics(
    native, count, stages, tmp_path, monkeypatch
):
    result, data, config, _ = result_fixture(native, count, stages)
    calls = []
    install_backend(monkeypatch, result, calls)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setenv("SLURM_STEP_ID", "0")
    monkeypatch.setattr(r.old.worker_tools, "resources", lambda: {"scope": "fixture-root"})
    value = plan()
    report = r._native(
        tmp_path,
        value,
        4,
        "reference",
        p.LIMIT,
        recheck=lambda *a: (data, config),
        check=lambda: None,
    )
    assert report["classification"]["independently_feasible"] is bool(count)
    assert calls[-1] == "dispose"
    catalogue = q.diag.catalogue(
        tmp_path / "diagnostics",
        r.worker_identity(value, 4, "123.0"),
        profile_factory=r.solver_profile,
    )
    assert catalogue["native_return_observed"]
    assert p.read(tmp_path / "diagnostics/native-ready.json")["profile_sha256"] == d.digest(
        asdict(r.solver_profile(4))
    )
    with pytest.raises(ValueError):
        q.diag.catalogue(tmp_path / "diagnostics", r.worker_identity(value, 4, "123.0"))


@pytest.mark.parametrize("failure", ["construction", "optimization", "extraction"])
def test_native_failure_preserves_safe_evidence_and_disposal(failure, tmp_path, monkeypatch):
    result, data, config, _ = result_fixture()
    calls = []
    install_backend(monkeypatch, result, calls, fail=failure)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setenv("SLURM_STEP_ID", "0")
    with pytest.raises(ValueError):
        r._native(
            tmp_path,
            plan(),
            4,
            "reference",
            p.LIMIT,
            recheck=lambda *a: (data, config),
            check=lambda: None,
        )
    assert calls[-1] == "dispose"
    assert (tmp_path / "native/failure.json").exists()
    assert (tmp_path / "diagnostics/license-selection.json").exists()


def test_submission_exact_12h_and_no_repetition(tmp_path, monkeypatch):
    value, result, calls = submit(tmp_path, monkeypatch)
    assert result["job_id"] == "456" and len(calls) == 1
    assert "--time=12:00:00" in calls[0]
    assert "--cpus-per-task=16" in calls[0] and "--mem=196608M" in calls[0]
    resumed = q.start(SOURCE, acknowledged=True, command=lambda *a, **k: pytest.fail("resubmit"))
    assert resumed["status"] == "existing_job_collect_only"
    assert q.prior_path().read_bytes() == b"IMMUTABLE ORIGINAL CARRIER"
    assert q.directory().name != q.old.CLAIM


def test_unacknowledged_before_any_effect(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "BASE", tmp_path)
    with pytest.raises(ValueError):
        q.start(SOURCE, command=lambda *a, **k: pytest.fail("submission"))
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("reply", ["", "warning\n456\n", "0\n", "456 bad\n"])
def test_unknown_ack_consumes_new_claim(reply, tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="Unknown submission"):
        submit(tmp_path, monkeypatch, reply)
    with pytest.raises(ValueError, match="Consumed slot"):
        q.start(SOURCE, acknowledged=True, command=lambda *a, **k: pytest.fail("retry"))


@pytest.mark.parametrize("drift", ["runtime", "input", "protected", "transport"])
def test_predecessor_identity_drift_before_new_claim(drift, tmp_path, monkeypatch):
    monkeypatch.setattr(q, "BASE", tmp_path)
    value = plan()
    prior = r.reference_plan(value)
    if drift == "transport":
        value["files"]["scripts/mvp2_s2_h300_runtime.py"] = "e" * 64
    else:
        prior[drift]["different"] = "drift"
    monkeypatch.setattr(q, "predecessor", lambda path: prior)
    with pytest.raises(ValueError):
        q.start(
            SOURCE,
            acknowledged=True,
            planner=lambda *a: value,
            command=lambda *a, **k: pytest.fail("submit"),
        )
    assert not q.directory().exists()


def closed_block(tmp_path, monkeypatch, stop=None, native="OPTIMAL", count=1, stages=3):
    value, _, _ = submit(tmp_path, monkeypatch)
    target = q.directory()
    monkeypatch.setenv("SLURM_JOB_ID", "456")
    monkeypatch.setattr(r.old.worker_tools, "resources", lambda: {"scope": "fixture-root"})
    data, config = result_fixture(native, count, stages)[1:3]
    executed = []

    def run_arm(path, plan, threads, job, env, reference, remaining, hard, **kwargs):
        index = len(executed)
        executed.append(threads)
        path.mkdir()
        monkeypatch.setenv("SLURM_STEP_ID", str(index))
        result = result_fixture(native, count, stages)[0]
        install_backend(monkeypatch, result, [])
        r._native(
            path,
            plan,
            threads,
            reference,
            remaining,
            recheck=lambda *a: (data, config),
            check=lambda: None,
        )
        attempt = {
            "step_id": f"456.{index}",
            "stop_reason": "watchdog_fixture" if index == stop else None,
            "local_client_reaped": True,
            "return_code": 0,
            "threads": threads,
            "enforcement_contract_sha256": d.digest(r.CONTRACT),
        }
        p.publish(path / "attempt.json", attempt)
        return attempt

    def command(argv, **kwargs):
        job = argv[argv.index("-j") + 1]
        if "." in job:
            return command_result(f"{job}|COMPLETED|0:0|4\n")
        return command_result(
            "\n".join(
                f"{name}|COMPLETED|0:0|8"
                for name in [
                    "456",
                    "456.batch",
                    "456.extern",
                    *(f"456.{i}" for i in range(len(executed))),
                ]
            )
        )

    def recheck(*a):
        return data, config

    block = r._batch(
        target,
        recheck=recheck,
        environment=lambda *a, **k: {"same": True},
        license_check=lambda: {"status": "accepted"},
        run_arm=run_arm,
        independent=lambda path, data, config, anchor, remaining: p.review(
            path / "native/products", data, config, anchor
        ),
        command=command,
        clock=Clock(),
    )
    return target, value, block, command, recheck


@pytest.mark.parametrize("stop", [None, 0, 2, 4])
def test_full_serial_grid_partial_prefix_and_portable_audit(stop, tmp_path, monkeypatch):
    target, value, block, command, recheck = closed_block(tmp_path, monkeypatch, stop)
    assert [x["threads"] for x in block["arms"]] == list(d.ORDER[: len(block["arms"])])
    result = q.collect(SOURCE, command=command, recheck=recheck)
    assert result["reported_native_status"] == (
        "five_arms_accounted_not_s2_closure" if stop is None else "forensic_partial_block"
    )
    assert result["unrun"] == list(d.ORDER[len(block["arms"]) :])
    audited = q.audit(result["download"], result["sha256"], SOURCE, result["release_sha256"], "456")
    assert all(audited[k] is False for k in q.FLAGS)
    assert audited["fresh_private_input_revalidated_by_portable_auditor"] is False
    assert q.collect(SOURCE, command=command, recheck=recheck) == result


@pytest.mark.parametrize("count,stages", [(0, 0), (1, 1)])
def test_censored_native_run_not_promoted_to_full_hierarchy(count, stages, tmp_path, monkeypatch):
    target, value, block, command, recheck = closed_block(
        tmp_path, monkeypatch, native="TIME_LIMIT", count=count, stages=stages
    )
    result = q.collect(SOURCE, command=command, recheck=recheck)
    expected = "no_incumbent" if count == 0 else "feasible_partial_hierarchy"
    assert all(
        x["review"]["classification"]["disposition"] == expected for x in result["reported_arms"]
    )
    assert not result["s2_closed"] and not result["scientific_configuration_selected"]


@pytest.mark.parametrize("tamper", ["checksum", "source", "release", "job", "cache", "prior"])
def test_portable_external_anchors_and_immutable_cache(tamper, tmp_path, monkeypatch):
    target, value, block, command, recheck = closed_block(tmp_path, monkeypatch, 0)
    result = q.collect(SOURCE, command=command, recheck=recheck)
    args = [result["download"], result["sha256"], SOURCE, result["release_sha256"], "456"]
    if tamper in {"checksum", "source", "release", "job"}:
        index = {"checksum": 1, "source": 2, "release": 3, "job": 4}[tamper]
        args[index] = "d" * (40 if tamper == "source" else 64) if tamper != "job" else "999"
        with pytest.raises(ValueError):
            q.audit(*args)
    elif tamper == "cache":
        (target / "portable-review.json").write_bytes(b"{}")
        with pytest.raises(ValueError):
            q.collect(SOURCE, command=command, recheck=recheck)
        assert (target / "portable-review.json").read_bytes() == b"{}"
    else:
        # The genuine canonical predecessor is audited separately against external anchors.
        monkeypatch.setattr(q, "predecessor", lambda *a: (_ for _ in ()).throw(ValueError("prior")))
        with pytest.raises(ValueError):
            q.audit(*args)


@pytest.mark.parametrize("kind", ["extra", "duplicate", "link", "missing", "tail"])
def test_hostile_outer_carriers(kind, tmp_path, monkeypatch):
    target, value, block, command, recheck = closed_block(tmp_path, monkeypatch, 0)
    result = q.collect(SOURCE, command=command, recheck=recheck)
    with tarfile.open(result["download"], "r:gz") as stream:
        files = [(x.name, stream.extractfile(x).read()) for x in stream]
    if kind == "extra":
        files.append(("../escape", b"x"))
    if kind == "duplicate":
        files.append(files[0])
    if kind == "missing":
        files.pop()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:", format=tarfile.USTAR_FORMAT) as stream:
        for i, (name, raw) in enumerate(files):
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            if kind == "link" and i == 0:
                info.type, info.linkname, info.size = tarfile.SYMTYPE, "../escape", 0
            stream.addfile(info, io.BytesIO(raw))
    bad = tmp_path / "bad.tar.gz"
    bad.write_bytes(gzip.compress(buffer.getvalue() + (b"evil" if kind == "tail" else b"")))
    with pytest.raises(ValueError):
        q.audit(bad, p.sha_file(bad), SOURCE, result["release_sha256"], "456")


def test_early_batch_failure_is_unaccounted_not_unrun(tmp_path, monkeypatch):
    submit(tmp_path, monkeypatch)

    def command(*a, **k):
        return command_result(
            "456|FAILED|2:0|4\n456.batch|FAILED|2:0|4\n456.extern|COMPLETED|0:0|4"
        )

    result = q.collect(SOURCE, command=command, recheck=lambda *a: (None, None))
    assert result["unaccounted"] == list(d.ORDER) and result["unrun"] == []
    assert result["diagnostics_complete_for_reported_arms"] is False
    assert q.collect(SOURCE, command=command, recheck=lambda *a: (None, None)) == result


@pytest.mark.parametrize("action", ["worker", "repeat"])
def test_old_public_execution_routes_stay_closed(action):
    with pytest.raises(PermissionError):
        q.main([action, SOURCE])


@pytest.mark.parametrize("mode", ["success", "verify_failure", "execute_failure"])
def test_batch_entry_seals_negative_or_positive_outcome(mode, tmp_path, monkeypatch):
    value, _, _ = submit(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(os, "getuid", lambda: 1271, raising=False)

    def verify(*a):
        if mode == "verify_failure":
            raise ValueError("test verifier")

    def execute(path):
        assert all(os.environ[k] == "1" for k in r.old.ENVIRONMENT)
        if mode == "execute_failure":
            raise ValueError("test execute")
        return {"stop_reason": None, "unrun": [], "arms": [{}] * 5}

    assert q.batch(q.directory(), SOURCE, execute=execute, verify=verify) == (
        0 if mode == "success" else 2
    )
    assert p.read(q.directory() / "driver-outcome.json")["status"] == (
        "block_returned" if mode == "success" else "blocked_or_interrupted"
    )
    with pytest.raises(FileExistsError):
        q.batch(q.directory(), SOURCE, execute=execute, verify=verify)


def test_real_supervisor_survives_800_samples_then_stops_exact_step(tmp_path, monkeypatch):
    value, clock, calls = plan(), Clock(), []
    monkeypatch.setattr(os, "getuid", lambda: 1271, raising=False)
    env = {"allocation": {"node": "fixture-node"}}
    p.publish(
        tmp_path / "worker-start.json",
        {
            "plan_sha256": d.digest(value),
            "uid": 1271,
            "threads": 4,
            "environment_sha256": d.digest(env),
            "step_id": "123.7",
            "pid": 999,
        },
    )
    journal = r.c.PhaseJournal(
        tmp_path / "native", d.digest({"plan": d.digest(value), "threads": 4})
    )
    journal.enter("build")

    def pause(seconds):
        clock.now += max(seconds, 5)
        if clock.now >= 500 and journal.index == 1:
            journal.enter("optimization")

    def command(argv, **kwargs):
        calls.append(argv)
        return command_result(
            "StepId=123.7 UserId=1271 State=RUNNING Nodes=1 NodeList=fixture-node Tasks=1 CPUs=16"
            if argv[0] == "scontrol"
            else ""
        )

    process = SimpleNamespace(
        returncode=None, poll=lambda: None, wait=lambda **k: setattr(process, "returncode", 143)
    )
    result = r._supervise(
        process,
        tmp_path,
        value,
        4,
        "123",
        env,
        5700,
        command=command,
        clock=clock,
        pause=pause,
        sample=lambda pid: {"scope_fixture": True},
    )
    assert result["stop_reason"] == "return_export_watchdog"
    assert result["local_client_reaped"] and not result["global_cleanup_proven"]
    assert 800 < len(p.read(tmp_path / "resources.json")["samples"]) < 1200
    assert [x for x in calls if x[0] == "scancel"] == [
        ["scancel", "--signal=TERM", "123.7"],
        ["scancel", "--signal=KILL", "123.7"],
    ]


def test_unbound_supervisor_no_broad_cancellation(tmp_path):
    clock, calls = Clock(), []
    process = SimpleNamespace(
        returncode=None,
        poll=lambda: None,
        terminate=lambda: None,
        wait=lambda **k: setattr(process, "returncode", -9),
    )
    result = r._supervise(
        process,
        tmp_path,
        plan(),
        4,
        "123",
        {},
        100,
        clock=clock,
        pause=clock.sleep,
        command=lambda *a, **k: calls.append(a) or command_result(),
        sample=lambda pid: {},
    )
    assert result["stop_reason"] == "unbound_startup" and not calls


def test_new_arm_argv_retains_full_pool_and_95_minute_hard_limit(tmp_path):
    calls = []

    def popen(argv, **kwargs):
        calls.append((argv, kwargs))
        return object()

    result = r._arm(
        tmp_path / "t4",
        plan(),
        4,
        "123",
        {},
        "reference",
        p.LIMIT,
        5700,
        popen=popen,
        supervise=lambda *a, **k: {"fixture": True},
    )
    assert result == {"fixture": True}
    argv, kwargs = calls[0]
    assert "--time=01:35:00" in argv and "--cpus-per-task=16" in argv
    assert "--export=ALL" in argv and "terminal_runtime import _dispatch" in argv[-1]
    assert kwargs["shell"] is False and "env" not in kwargs


def test_complete_wrapper_contains_fixed_merge_source_and_qualified_gate():
    script = (q.ROOT / "scripts/npad_s2_p4_terminal.sh").read_text()
    assert q.PARENT in script and "origin/develop" in script
    assert "terminal-release.json" in script and r.CLAIM in script
    assert "--one-reviewed-replacement-block-only" in script
    assert "pip install" not in script and "reset" not in script


@pytest.mark.parametrize("mode", ["extra", "foreign_terminal", "profile", "missing"])
def test_diagnostic_sidecar_is_independently_replayed(mode, tmp_path, monkeypatch):
    target, value, block, command, recheck = closed_block(tmp_path, monkeypatch, 0)
    reported = r._collect(target, d.digest(value), "456", command=command, recheck=recheck)
    sidecar = q._diagnostics(target, value, reported)
    arm = sidecar["arms"][0]
    if mode == "extra":
        arm["records"]["private.log"] = {"secret": "never-export"}
    elif mode == "foreign_terminal":
        arm["records"]["native-return.json"]["terminal_sha256"] = "f" * 64
    elif mode == "profile":
        arm["records"]["native-ready.json"]["profile_sha256"] = "f" * 64
    else:
        del arm["records"]["optimization.json"]
    with pytest.raises(ValueError):
        q.verify_diagnostics(sidecar, value, reported, target / "s2-h300-academic-evidence.tar.gz")


def test_small_whole_block_bound_preserves_all_native_originals(tmp_path, monkeypatch):
    target, value, block, command, recheck = closed_block(tmp_path, monkeypatch, 0)
    report = r._collect(target, d.digest(value), "456", command=command, recheck=recheck)
    path = target / "s2-h300-academic-evidence.tar.gz"
    original = path.read_bytes()
    monkeypatch.setattr(p, "LIMIT", 1024)
    with pytest.raises(ValueError):
        q.bundle(target, value, q.release(value), report)
    assert path.read_bytes() == original and not (target / q.ARCHIVE).exists()


@pytest.mark.skipif(sys.platform != "linux", reason="Actual Bash wrapper semantics; no cluster")
@pytest.mark.parametrize("action", ["status", "wait", "collect"])
def test_actual_wrapper_absent_claim_no_effect(action, tmp_path):
    script = (
        (q.ROOT / "scripts/npad_s2_p4_terminal.sh").read_text().replace(str(q.BASE), str(tmp_path))
    )
    path = tmp_path / "wrapper.sh"
    path.write_text(script)
    result = subprocess.run(["bash", str(path), action, SOURCE], capture_output=True, text=True)
    assert result.returncode == 2 and "not_submitted" in result.stderr
    assert list(tmp_path.iterdir()) == [path]
