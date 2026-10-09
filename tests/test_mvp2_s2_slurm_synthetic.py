"""Offline transports/clocks/files only: no Slurm, fork tree, license or solver."""

import copy
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest

from scripts import mvp2_s2_slurm_step as s
from scripts import mvp2_s2_slurm_synthetic as q
from scripts import mvp2_s2_synthetic_worker as w


@pytest.fixture
def item():
    inventory = json.loads(
        (Path(__file__).resolve().parents[1] / "docs/mvp2_s2_slurm_site_inventory.json").read_text()
    )
    binding = {
        "job_id": "500000",
        "worker_step_id": "0",
        "supervisor_step_id": "batch",
        "nonce": "a" * 64,
        "source_commit": "b" * 40,
    }
    return q.contract(inventory, binding, "normal", "c" * 64, "d" * 64)


def closed(value):
    assert all(value[k] is False for k in q.FLAGS)


def scopes(name):
    return {key: {"scope": f"/cg/{key}/{name}", "mount": f"/cg/{key}"} for key in s.CONTROLLERS}


def process(pid):
    return {"pid": pid, "uid": 1000, "starttime": pid * 100, "state": "S"}


def barrier_args(item):
    worker, outside = scopes("worker"), scopes("batch")
    snapshot = {
        "schema_version": "s2-cgroup-v1-observation-v1",
        "synthetic_observation": True,
        "status": "observed_not_qualified",
        "errors": [],
        "scopes": {
            k: {"path_sha256": s.digest(v["scope"]), "inode": [1, i]}
            for i, (k, v) in enumerate(worker.items(), 1)
        },
        "counters": {
            "memory_usage_bytes": 1024,
            "memory_max_usage_bytes": 2048,
            "memory_limit_bytes": 256 * 1024**2,
            "memory_failcnt": 0,
            "cpu_usage_ns": 10,
            "cpuset_cpu_count": 1,
            "effective_reported_memory_limit_bytes": 256 * 1024**2,
            "freezer_group_count": 1,
            "freezer_unique_process_count": 1,
        },
        **s.FLAGS,
    }
    return {
        "item": item,
        "scheduler_pids": {20},
        "worker": process(20),
        "supervisor": process(10),
        "writer": process(10),
        "worker_scopes": worker,
        "outside_scopes": outside,
        "snapshot": snapshot,
        "member_records": [{"identity": process(20), "scopes": copy.deepcopy(worker)}],
    }


@pytest.fixture
def receipt(item):
    return q.barrier(**barrier_args(item))


def running(item, receipt):
    controller = q.Controller(item, 100)
    assert controller.release(101, receipt, receipt) == "release_barrier"
    return controller


def sample(receipt, **updates):
    result = {
        "scope_hash": receipt["scope_identity_sha256"],
        "members": 1,
        "writes_sha256": "e" * 64,
    }
    result.update(updates)
    return result


def cleaned(receipt, **updates):
    return sample(
        receipt,
        members=0,
        all_known_pids_absent=True,
        launcher_reaped=True,
        step_terminal=True,
        **updates,
    )


def test_public_boundaries_deny_before_any_input_or_write(tmp_path):
    class Bomb:
        def __getattribute__(self, _key):
            raise AssertionError("input accessed")

    for execute in (q.execute_synthetic, w.execute_worker):
        with pytest.raises(PermissionError):
            execute(Bomb(), directory=tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("flag", q.FLAGS)
def test_contract_never_promotes(item, flag):
    item[flag] = True
    with pytest.raises(ValueError):
        q.validate_contract(item)


@pytest.mark.parametrize(
    "key,value",
    [
        ("worker_cpus", 2),
        ("worker_memory_mib", 0),
        ("startup_seconds", True),
        ("quiet_seconds", 0),
        ("maximum_members", 1000),
    ],
)
def test_profile_drift(item, key, value):
    item["profile"][key] = value
    with pytest.raises(ValueError):
        q.validate_contract(item)


def test_fixed_launch_only_existing_numeric_job(item):
    proposal = q.launch_descriptor(
        item, "/venv/python", "/source/scripts/mvp2_s2_synthetic_worker.py", "/run"
    )
    closed(proposal)
    assert proposal["execution_admitted"] is False
    assert proposal["argv"][:3] == ["srun", "--jobid=500000", "--nodes=1"]
    assert "--export=NONE" in proposal["argv"]
    assert "--mem=256M" in proposal["argv"]
    assert not any(x in proposal["argv"] for x in ("sbatch", "--async", "--overlap", "--pty"))


@pytest.mark.parametrize("path", ["relative", "/", "/a/../b", "/a//b", "/a\nb", "C:\\x"])
def test_launch_path_rejected(item, path):
    with pytest.raises(ValueError):
        q.launch_descriptor(item, path, "/source/scripts/mvp2_s2_synthetic_worker.py", "/run")


def test_scheduler_listpids(item):
    assert q.parse_listpids(
        "PID JOBID STEPID LOCALID GLOBALID\n20 500000 0 0 0\n", item["binding"]
    ) == {20}


@pytest.mark.parametrize(
    "text",
    [
        "20 500000 0 0 0",
        "PID JOBID STEPID LOCALID GLOBALID\n20 8 0 0 0",
        "PID JOBID STEPID LOCALID GLOBALID\n20 500000 batch 0 0",
        "PID JOBID STEPID LOCALID GLOBALID\n20 500000 0 0 0\n20 500000 0 0 0",
        "PID JOBID STEPID LOCALID GLOBALID\n0 500000 0 0 0",
        "PID JOBID STEPID LOCALID GLOBALID\n20 500000 0 ? ?",
    ],
)
def test_scheduler_fail_closed(item, text):
    with pytest.raises(ValueError):
        q.parse_listpids(text, item["binding"])


def test_proc_identity_parentheses_and_zombie():
    text = "20 (a ) b) Z " + " ".join(["1"] * 18 + ["999", "0"])
    assert q.proc_identity(text, 1000, 20) == {
        "pid": 20,
        "uid": 1000,
        "starttime": 999,
        "state": "Z",
    }


@pytest.mark.parametrize(
    "mutation",
    [
        "uid",
        "writer",
        "shared",
        "missing",
        "counter_bool",
        "unlimited",
        "cpus",
        "member_escape",
        "member_reuse",
        "scope_hash",
        "member_count",
        "zombie",
    ],
)
def test_barrier_adverse(item, mutation):
    args = barrier_args(item)
    if mutation == "uid":
        args["worker"]["uid"] = 2
    elif mutation == "writer":
        args["writer"] = process(30)
    elif mutation == "shared":
        args["outside_scopes"] = args["worker_scopes"]
    elif mutation == "missing":
        args["snapshot"]["scopes"].pop("freezer")
    elif mutation == "counter_bool":
        args["snapshot"]["counters"]["memory_usage_bytes"] = True
    elif mutation == "unlimited":
        args["snapshot"]["counters"]["effective_reported_memory_limit_bytes"] = 2**63
    elif mutation == "cpus":
        args["snapshot"]["counters"]["cpuset_cpu_count"] = 2
    elif mutation == "member_escape":
        args["member_records"][0]["scopes"] = scopes("foreign")
    elif mutation == "member_reuse":
        args["member_records"][0]["identity"]["starttime"] += 1
    elif mutation == "scope_hash":
        args["snapshot"]["scopes"]["freezer"]["path_sha256"] = "f" * 64
    elif mutation == "member_count":
        args["snapshot"]["counters"]["freezer_unique_process_count"] = 2
    else:
        args["worker"]["state"] = "Z"
    with pytest.raises(ValueError):
        q.barrier(**args)


def test_barrier_counts_alone_cannot_prove_membership(item):
    args = barrier_args(item)
    args["member_records"] = []
    with pytest.raises(ValueError):
        q.barrier(**args)


def test_parent_deadlines_exact_signals_and_quiet_period(item, receipt):
    controller = running(item, receipt)
    assert controller.observe(160, **sample(receipt)) == "wait"
    assert controller.observe(161, **sample(receipt)) == "TERM_exact_step"
    assert controller.observe(165, **sample(receipt)) == "wait"
    assert controller.observe(166, **sample(receipt)) == "KILL_exact_step"
    assert controller.observe(167, **cleaned(receipt)) == "wait"
    assert controller.observe(170, **cleaned(receipt)) == "wait"
    assert controller.observe(172, **cleaned(receipt)) == "preserve_candidate_not_admission"
    reviewed = q.verify_events(item, controller.events)
    assert reviewed["status"] == "candidate_closed"
    closed(reviewed)
    assert reviewed["live_containment_qualified"] is False
    with pytest.raises(ValueError):
        controller.observe(173, **cleaned(receipt))


@pytest.mark.parametrize("missing", ["all_known_pids_absent", "launcher_reaped", "step_terminal"])
def test_empty_membership_alone_not_closure(item, receipt, missing):
    controller = running(item, receipt)
    controller.observe(102, **sample(receipt, worker_done=True))
    inputs = cleaned(receipt)
    inputs[missing] = False
    assert controller.observe(110, **inputs) == "KILL_exact_step"
    assert controller.observe(492, **inputs) == "preserve_blocked_attempt"
    assert q.verify_events(item, controller.events)["status"] == "blocked"


@pytest.mark.parametrize("invalid", [None, "f" * 64])
def test_missing_replaced_scope_stays_blocked(item, receipt, invalid):
    controller = running(item, receipt)
    inputs = cleaned(receipt)
    inputs["scope_hash"] = invalid
    assert controller.observe(102, **inputs) == "TERM_exact_step"
    assert controller.observe(107, **inputs) == "KILL_exact_step"
    assert controller.observe(492, **inputs) == "preserve_blocked_attempt"


def test_late_writes_reset_quiet_period(item, receipt):
    controller = running(item, receipt)
    controller.observe(102, **sample(receipt, worker_done=True))
    controller.observe(103, **cleaned(receipt))
    controller.observe(106, **cleaned(receipt))
    assert controller.observe(108, **cleaned(receipt, writes_sha256="f" * 64)) == "wait"
    controller.observe(111, **cleaned(receipt, writes_sha256="f" * 64))
    assert (
        controller.observe(113, **cleaned(receipt, writes_sha256="f" * 64))
        == "preserve_candidate_not_admission"
    )


def test_deadline_precedes_late_clean_sample(item, receipt):
    controller = running(item, receipt)
    controller.observe(102, **sample(receipt, fault=True))
    assert controller.observe(492, **cleaned(receipt)) == "preserve_blocked_attempt"


def test_unbound_startup_never_signals_guessed_step(item):
    controller = q.Controller(item, 100)
    assert controller.observe(130) == "preserve_unbound_attempt"
    assert q.verify_events(item, controller.events)["status"] == "blocked"


@pytest.mark.parametrize("now", [99, float("nan"), float("inf"), True, -1])
def test_clock_invalid(item, now):
    controller = q.Controller(item, 100)
    with pytest.raises(ValueError):
        controller.observe(now)


def test_changed_barrier_rejected(item, receipt):
    other = copy.deepcopy(receipt)
    other["identities_sha256"] = "f" * 64
    controller = q.Controller(item, 100)
    with pytest.raises(ValueError):
        controller.release(101, receipt, other)


def test_one_shot_launcher_and_exact_targets(tmp_path, item, receipt):
    calls = []
    launcher = q.Launcher(
        item,
        tmp_path / "claim",
        spawn=lambda argv: calls.append(argv),
        command=lambda argv, **limits: calls.append((argv, limits)),
    )
    launcher.launch("/venv/python", "/source/scripts/mvp2_s2_synthetic_worker.py", "/run")
    with pytest.raises(ValueError):
        launcher.launch("/venv/python", "/source/scripts/mvp2_s2_synthetic_worker.py", "/run")
    controller = running(item, receipt)
    controller.observe(161, **sample(receipt))
    with pytest.raises(ValueError):
        launcher.signal("TERM", controller.events)
    launcher.bind_barrier(receipt)
    launcher.signal("TERM", controller.events)
    assert calls[-1] == (
        ("scancel", "--signal=TERM", "500000.0"),
        {"timeout_seconds": 10, "max_output_bytes": 65536},
    )
    with pytest.raises(ValueError):
        launcher.signal("TERM", controller.events)
    with pytest.raises(ValueError):
        launcher.signal("KILL", controller.events)
    controller.observe(166, **sample(receipt))
    launcher.signal("KILL", controller.events)
    assert calls[-1][0] == ("scancel", "--signal=KILL", "500000.0")
    with pytest.raises(FileExistsError):
        q.Launcher(item, tmp_path / "claim", spawn=None, command=None)


def test_unknown_launch_ack_consumes_claim(tmp_path, item):
    def fail(_argv):
        raise TimeoutError("unknown acknowledgement")

    launcher = q.Launcher(item, tmp_path / "claim", spawn=fail, command=None)
    with pytest.raises(TimeoutError):
        launcher.launch("/venv/python", "/source/scripts/mvp2_s2_synthetic_worker.py", "/run")
    assert (tmp_path / "claim/launch-intent.json").exists()
    with pytest.raises(ValueError):
        launcher.launch("/venv/python", "/source/scripts/mvp2_s2_synthetic_worker.py", "/run")


@pytest.mark.parametrize("case", q.CASES)
def test_worker_phase_matrix_partial_receipts(tmp_path, item, case):
    assert q.CASES == w.CASES
    item["case"] = case
    directory = tmp_path / "worker"
    effect = []
    if case.endswith("failure"):
        with pytest.raises(RuntimeError):
            w.exercise_components(
                case,
                directory,
                "a" * 64,
                release=lambda: True,
                nested_factory=lambda: effect.append("nested"),
            )
    else:
        w.exercise_components(
            case,
            directory,
            "a" * 64,
            release=lambda: True,
            nested_factory=lambda: effect.append("nested"),
        )
    result = q.verify_worker_products(item, q.read_worker_products(directory))
    closed(result)
    assert result["worker_outcome"] == (
        "synthetic_failure" if case.endswith("failure") else "synthetic_complete_not_cleanup"
    )
    assert effect == (["nested"] if case == "nested_setsid_term_ignore" else [])


def test_worker_denies_unreleased_barrier(tmp_path):
    with pytest.raises(PermissionError):
        w.exercise_components(
            "normal", tmp_path / "worker", "a" * 64, release=lambda: False, nested_factory=None
        )
    assert not (tmp_path / "worker").exists()


@pytest.mark.parametrize(
    "products",
    [
        {"phase-1.json": {"nonce": "a" * 64, "phase": "optimization"}},
        {"terminal.json": {"nonce": "a" * 64, "status": "synthetic_complete"}},
        {"secrets.json": {}},
        {"phase-0.json": {"nonce": "f" * 64, "phase": "build"}},
    ],
)
def test_worker_adverse_replay(item, products):
    with pytest.raises(ValueError):
        q.verify_worker_products(item, products)


def test_archive_round_trip_external_binding_and_no_repeat(tmp_path, item, receipt):
    controller = running(item, receipt)
    controller.observe(102, **sample(receipt, fault=True))
    result = q.collect(tmp_path / "collection", item, controller.events)
    path = tmp_path / "collection/synthetic-evidence.tar.gz"
    review = q.audit_archive(path, result["sha256"], item)
    assert review["status"] == "term"
    assert review["worker"]["worker_outcome"] == "partial"
    closed(review)
    changed = copy.deepcopy(item)
    changed["binding"]["nonce"] = "f" * 64
    with pytest.raises(ValueError):
        q.audit_archive(path, result["sha256"], changed)
    with pytest.raises(ValueError):
        q.audit_archive(path, "0" * 64, item)
    with pytest.raises(FileExistsError):
        q.collect(tmp_path / "collection", item, controller.events)


@pytest.mark.parametrize("mutation", ["action", "state", "clock", "chain", "late", "admitting"])
def test_event_tampering_rejected(item, receipt, mutation):
    controller = running(item, receipt)
    controller.observe(161, **sample(receipt))
    events = copy.deepcopy(controller.events)
    if mutation == "action":
        events[-1]["payload"]["action"] = "KILL_exact_step"
    elif mutation == "state":
        events[-1]["payload"]["state"] = "candidate_closed"
    elif mutation == "clock":
        events[-1]["seconds"] = -1
    elif mutation == "chain":
        events[-1]["previous_sha256"] = "f" * 64
    elif mutation == "late":
        events.append(copy.deepcopy(events[-1]))
    else:
        events[0]["payload"]["first"]["production_admitted"] = True
    with pytest.raises(ValueError):
        q.verify_events(item, events)


@pytest.mark.parametrize("bad_name", ["../escape", "contract.json", "secret.lic"])
def test_archive_allowlist_and_duplicates(tmp_path, item, bad_name):
    result = q.collect(tmp_path / "collection", item, [])
    original = tmp_path / "collection/synthetic-evidence.tar.gz"
    with tarfile.open(original) as archive:
        products = [(member.name, archive.extractfile(member).read()) for member in archive]
    products.append((bad_name, b"{}"))
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, data in products:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    data = gzip.compress(buffer.getvalue())
    bad = tmp_path / "bad.tar.gz"
    bad.write_bytes(data)
    with pytest.raises(ValueError):
        q.audit_archive(bad, hashlib.sha256(data).hexdigest(), item)
    closed(result)


def test_decompression_bound(tmp_path, item):
    data = gzip.compress(b"0" * (q.LIMIT + 1))
    path = tmp_path / "bomb.tar.gz"
    path.write_bytes(data)
    with pytest.raises(ValueError):
        q.audit_archive(path, hashlib.sha256(data).hexdigest(), item)


def test_no_native_or_submission_imports():
    import ast

    for module in (q, w):
        tree = ast.parse(Path(module.__file__).read_text())
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        assert not any(
            name and any(x in name for x in ("gurobi", "scip", "pyomo", "subprocess"))
            for name in imports
        )


def test_fork_tree_not_called_by_fixture_or_cli(monkeypatch):
    monkeypatch.setattr(w.os, "fork", lambda: pytest.fail("fork not admitted"), raising=False)
    with pytest.raises(PermissionError):
        w.execute_worker()
    with pytest.raises(ValueError):
        w.fork_nested_components(duration_seconds=1)


def test_running_to_sleeping_state_is_not_pid_reuse(item):
    args = barrier_args(item)
    first = q.barrier(**args)
    args["worker"]["state"] = "R"
    args["member_records"][0]["identity"]["state"] = "R"
    second = q.barrier(**args)
    assert first["identities_sha256"] == second["identities_sha256"]


def test_barrier_record_is_immutable_after_release(item, receipt):
    controller = running(item, receipt)
    receipt["scope_identity_sha256"] = "f" * 64
    assert q.verify_events(item, controller.events)["status"] == "exercise"


def test_late_observation_preserves_blocked_evidence(item, receipt):
    controller = running(item, receipt)
    assert controller.observe(1000, **sample(receipt)) == "preserve_blocked_attempt"
    assert q.verify_events(item, controller.events)["status"] == "blocked"


def test_launcher_query_transport_bound(tmp_path, item):
    calls = []

    def command(argv, **limits):
        calls.append((argv, limits))
        return "PID JOBID STEPID LOCALID GLOBALID\n20 500000 0 0 0"

    launcher = q.Launcher(item, tmp_path / "claim", spawn=lambda _argv: None, command=command)
    launcher.launch("/python", "/source/scripts/mvp2_s2_synthetic_worker.py", "/run")
    assert launcher.listpids() == {20}
    assert calls == [
        (("scontrol", "listpids", "500000.0"), {"timeout_seconds": 10, "max_output_bytes": 65536})
    ]


def test_signal_ack_timeout_cannot_retry(tmp_path, item, receipt):
    def timeout(_argv, **_limits):
        raise TimeoutError("unknown signal ack")

    launcher = q.Launcher(item, tmp_path / "claim", spawn=lambda _argv: None, command=timeout)
    launcher.launch("/python", "/source/scripts/mvp2_s2_synthetic_worker.py", "/run")
    launcher.bind_barrier(receipt)
    controller = running(item, receipt)
    controller.observe(161, **sample(receipt))
    with pytest.raises(TimeoutError):
        launcher.signal("TERM", controller.events)
    assert (tmp_path / "claim/term-intent.json").exists()
    with pytest.raises(ValueError):
        launcher.signal("TERM", controller.events)


def test_symlink_evidence_path_rejected(tmp_path, item):
    original = tmp_path / "original"
    original.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(original, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation requires platform capability.")
    with pytest.raises(ValueError):
        q.collect(linked / "new", item, [])


@pytest.mark.parametrize("branch", ["parent", "child", "grandchild"])
def test_fork_tree_control_flow_only_no_live_process(monkeypatch, branch):
    from types import SimpleNamespace

    class Exit(BaseException):
        pass

    calls = []
    forks = iter({"parent": [20], "child": [0, 21], "grandchild": [0, 0]}[branch])

    def fake_exit(code):
        calls.append(("exit", code))
        raise Exit()

    fake_os = SimpleNamespace(
        name="posix",
        fork=lambda: next(forks),
        setsid=lambda: calls.append("setsid"),
        waitpid=lambda pid, flags: calls.append(("waitpid", pid, flags)),
        _exit=fake_exit,
    )
    monkeypatch.setattr(w, "os", fake_os)
    monkeypatch.setattr(
        w, "signal", SimpleNamespace(SIGTERM=15, SIG_IGN=1, signal=lambda *args: calls.append(args))
    )
    moments = iter([0, 121])
    monkeypatch.setattr(
        w,
        "time",
        SimpleNamespace(
            monotonic=lambda: next(moments), sleep=lambda _duration: pytest.fail("no live sleep")
        ),
    )
    if branch == "parent":
        assert w.fork_nested_components() == 20
        assert calls == []
    else:
        with pytest.raises(Exit):
            w.fork_nested_components()
        assert (15, 1) in calls
        if branch == "child":
            assert ("waitpid", 21, 0) in calls
        else:
            assert "setsid" in calls
