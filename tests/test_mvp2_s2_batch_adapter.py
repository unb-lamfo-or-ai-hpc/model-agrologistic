"""Closed real adapter qualification; no Slurm/solver/license/synthetic fork tree."""

import copy
import hashlib
import io
import json
import struct
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_h300_controls as c
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_slurm_step as s
from scripts import mvp2_s2_synthetic_worker as w


def test_isolated_cli_denies_before_project_imports():
    result = subprocess.run(
        [sys.executable, "-I", str(Path(a.__file__).resolve())],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0
    assert b"PermissionError: S2 batch execution remains closed" in result.stderr
    assert b"ModuleNotFoundError" not in result.stderr


@pytest.fixture
def plan():
    inventory = json.loads(
        (Path(__file__).resolve().parents[1] / "docs/mvp2_s2_slurm_site_inventory.json").read_text()
    )
    return a.specification(
        checkout="/source",
        run="/run/case",
        python="/runtime/python",
        tools={key: "/tools/" + key for key in a.TOOLS},
        tools_sha256={key: "d" * 64 for key in a.TOOLS},
        python_sha256="e" * 64,
        source_commit="b" * 40,
        nonce="a" * 64,
        job_id="500000",
        case="normal",
        inventory=inventory,
    )


def process(pid):
    return {
        "identity": {"pid": pid, "uid": 1000, "starttime": pid * 100, "state": "S"},
        "scopes": {
            key: {"scope": f"/cg/{key}/{'batch' if pid == 10 else 'worker'}", "mount": f"/cg/{key}"}
            for key in s.CONTROLLERS
        },
    }


def snapshot(scopes, count=1):
    return {
        "schema_version": "s2-cgroup-v1-observation-v1",
        "synthetic_observation": False,
        "status": "observed_not_qualified",
        "errors": [],
        **s.FLAGS,
        "scopes": {
            key: {"path_sha256": s.digest(value["scope"]), "inode": [1, i]}
            for i, (key, value) in enumerate(scopes.items(), 1)
        },
        "counters": {
            "memory_usage_bytes": 100,
            "memory_max_usage_bytes": 100,
            "memory_limit_bytes": 256 * 1024**2,
            "memory_failcnt": 0,
            "cpu_usage_ns": 1000,
            "cpuset_cpu_count": 1,
            "effective_reported_memory_limit_bytes": 256 * 1024**2,
            "freezer_group_count": 1,
            "freezer_unique_process_count": count,
        },
    }


class Transport:
    def __init__(self):
        self.calls, self.signals, self.count = [], [], 1
        self.source = {"source_sha256": "c" * 64, "tracked_count": 3, "worker_sha256": "f" * 64}
        self.handle = SimpleNamespace(
            process=SimpleNamespace(poll=lambda: None),
            pump=lambda **kw: False,
            close_pipes=lambda: None,
        )

    def command(self, argv, **kwargs):
        assert kwargs == {"timeout_seconds": 10, "max_output_bytes": 65536}
        self.calls.append(argv)
        if argv[-1] == "--version":
            return "slurm 22.05.11\n"
        if argv[1:3] == ("listpids", "500000.batch"):
            return "PID JOBID STEPID LOCALID GLOBALID\n10 500000 batch 0 0\n"
        if argv[1:4] == ("-o", "show", "job"):
            return (
                "JobId=500000 UserId=user(1000) JobState=RUNNING NumNodes=1 "
                "NumCPUs=2 NodeList=node BatchHost=node TimeLimit=00:12:00 MinMemoryNode=2G"
            )
        if argv[1:4] == ("-o", "show", "step"):
            return (
                "StepId=500000.7 UserId=user(1000) Nodes=node State=RUNNING "
                "CPUs=1 Tasks=1 TimeLimit=00:09:00"
            )
        if argv[1:3] == ("listpids", "500000.7"):
            return "PID JOBID STEPID LOCALID GLOBALID\n" + (
                "20 500000 7 0 0\n" if self.count else ""
            )
        if argv[0].endswith("/sacct"):
            return (
                "500000|RUNNING|0:0|20\n500000.batch|RUNNING|0:0|20\n500000.7|"
                + ("RUNNING" if self.count else "COMPLETED")
                + "|0:0|20\n"
            )
        raise AssertionError(argv)

    def bind(self, binding):
        assert binding["worker_step_id"] == "7"

    def spawn(self, argv):
        self.calls.append(argv)
        return self.handle

    def signal(self, binding, name):
        self.signals.append((binding["worker_step_id"], name))


class Server:
    def __init__(self, _path):
        self.releases = []
        self.closed = False

    def accept(self, _remaining):
        return {
            "nonce": "a" * 64,
            "job_id": "500000",
            "worker_step_id": "7",
            "worker_sha256": "f" * 64,
            "python_sha256": "e" * 64,
            "python_version": [3, 13],
        }, {"pid": 20, "uid": 1000}

    def release(self, value, _remaining):
        self.releases.append(value)

    def close(self):
        self.closed = True


@pytest.fixture
def adapter(plan, tmp_path, monkeypatch):
    # POSIX path grammar has its own tests. Filesystem fixture remaps only run
    # to the Windows temporary directory; all live observers/transports are fakes.
    plan["run"] = str(tmp_path / "run")
    monkeypatch.setattr(a, "validate_spec", lambda value: copy.deepcopy(value))
    monkeypatch.setattr(
        a, "sha_file", lambda path, *args: "e" * 64 if str(path).endswith("python") else "d" * 64
    )
    clock = [0]
    transport = Transport()
    result = a.BatchAdapter(
        plan,
        transport=transport,
        clock=lambda: clock[0],
        record=process,
        snapshot=lambda scopes: snapshot(scopes, transport.count),
        pid_absent=lambda pid: transport.count == 0,
        server_factory=Server,
        exe_path=lambda _pid: "/runtime/python",
    )
    result.preflight(
        uid=1000,
        pid=10,
        node="node",
        source=transport.source,
        tool_sha256=plan["tools_sha256"],
        python_sha256=plan["python_sha256"],
    )
    result.test_clock = clock
    return result


def test_public_cli_denies_before_input_or_io(monkeypatch):
    monkeypatch.setattr(a, "validate_spec", lambda *_: pytest.fail("inspected input"))
    with pytest.raises(PermissionError):
        a.execute_batch(object())
    with pytest.raises(PermissionError):
        w.execute_worker(object())


@pytest.mark.parametrize("key", a.FLAGS)
def test_plan_cannot_admit(plan, key):
    plan[key] = True
    with pytest.raises(ValueError):
        a.validate_spec(plan)


@pytest.mark.parametrize(
    "key,value",
    [
        ("run", "/source/run"),
        ("checkout", "/"),
        ("python", "relative"),
        ("nonce", "x"),
        ("job_id", "500000.7"),
        ("case", "native"),
        ("python_sha256", "bad"),
    ],
)
def test_plan_drift_rejected(plan, key, value):
    plan[key] = value
    with pytest.raises(ValueError):
        a.validate_spec(plan)


def test_plan_launch_has_no_guessed_step_or_arbitrary_option(plan):
    argv = a.worker_argv(plan)
    assert "worker_step_id" not in plan
    assert "--jobid=500000" in argv and "--exact" in argv and "--export=NONE" in argv
    assert not any(x in argv for x in ("sbatch", "--async", "--overlap", "--pty"))
    assert argv[-2:] == ("--closed-contract", "/run/case/worker-plan.json")


@pytest.mark.parametrize(
    "name", ["../x", "/tmp/x", "a//b", "a/./b", "a/.git/config", "x:y", "a\nb", "-x"]
)
def test_source_names_reject_escape(name):
    assert not a.safe_repo_name(name)


def test_raw_checkout_binary_and_crlf_gate(plan, monkeypatch):
    names = [
        "scripts/mvp2_s2_batch_adapter.py",
        "scripts/mvp2_s2_synthetic_worker.py",
        "scripts/mvp2_s2_slurm_synthetic.py",
        "figures/x.pdf",
    ]
    blobs = {name: (b"%PDF\xff\x00\r\n" if name.endswith("pdf") else b"x\n") for name in names}
    working = dict(blobs)
    monkeypatch.setattr(
        a,
        "_file",
        lambda path, _limit: working[str(path).replace("\\", "/").split("/source/", 1)[1]],
    )

    def command(argv, **_kwargs):
        tail = argv[4:]
        if tail == ("rev-parse", "HEAD"):
            return plan["source_commit"] + "\n"
        if tail[0] == "status":
            return ""
        if tail[0] == "ls-files":
            return "".join("100644 " + "1" * 40 + " 0\t" + name + "\0" for name in names)
        return blobs[tail[-1][5:]]

    receipt = a.verify_checkout(plan, command)
    assert receipt["tracked_count"] == 4
    working[names[0]] = b"x\r\n"
    with pytest.raises(ValueError, match="Raw HEAD"):
        a.verify_checkout(plan, command)


def test_binary_hashes_checked_against_frozen_envelope(plan, monkeypatch):
    monkeypatch.setattr(
        a, "sha_file", lambda path: "e" * 64 if path.endswith("python") else "d" * 64
    )
    assert a.verify_binaries(plan, plan["tools_sha256"], plan["python_sha256"])
    with pytest.raises(ValueError, match="envelope"):
        a.verify_binaries(plan, plan["tools_sha256"], "0" * 64)


def test_real_transport_allowlist_one_shot_and_unknown_ack(plan, monkeypatch):
    transport = a.RealTransport(plan)
    opened = []

    def open_process(argv):
        opened.append(argv)
        return SimpleNamespace(query_result=lambda *_: "", process=object())

    monkeypatch.setattr(transport, "_open", open_process)
    for argv in [
        ("/tools/sbatch", "x"),
        ("/tools/scancel", "500000"),
        ("/tools/scontrol", "update", "JobId=500000"),
        ("/tools/scontrol", "listpids", "500000.7"),
    ]:
        with pytest.raises(ValueError):
            transport.command(argv)
    transport.spawn(a.worker_argv(plan))
    with pytest.raises(ValueError):
        transport.spawn(a.worker_argv(plan))
    binding = {
        "job_id": "500000",
        "worker_step_id": "7",
        "supervisor_step_id": "batch",
        "nonce": "a" * 64,
        "source_commit": "b" * 40,
    }
    with pytest.raises(ValueError):
        transport.signal(binding, "TERM")
    transport.bind(binding)
    transport.signal(binding, "TERM")
    transport.signal(binding, "KILL")
    with pytest.raises(ValueError):
        transport.signal(binding, "KILL")
    assert opened[-2:] == [
        ("/tools/scancel", "--signal=TERM", "500000.7"),
        ("/tools/scancel", "--signal=KILL", "500000.7"),
    ]
    transport.rpcs = a.MAX_RPC
    with pytest.raises(ValueError):
        transport.command(("/tools/srun", "--version"))


@pytest.mark.parametrize(
    "replacement",
    [
        "NumCPUs=3",
        "NumNodes=2",
        "TimeLimit=UNLIMITED",
        "JobState=PENDING",
        "MinMemoryNode=4G",
        "NodeList=other",
    ],
)
def test_allocation_mismatch_blocks(replacement):
    text = Transport().command(
        ("/tools/scontrol", "-o", "show", "job", "500000"),
        timeout_seconds=10,
        max_output_bytes=65536,
    )
    key = replacement.split("=", 1)[0]
    altered = " ".join(replacement if part.startswith(key + "=") else part for part in text.split())
    with pytest.raises(ValueError):
        a.review_allocation(altered, "500000", 1000, "node")


@pytest.mark.parametrize("text", ["", "StepId=500000.7 StepId=500000.7", "a=b\nc=d"])
def test_ambiguous_scheduler_grammar(text):
    with pytest.raises(ValueError):
        a.fields(text)


def test_binding_release_durable_before_effect_and_exact_actual_id(adapter):
    adapter.launch()
    adapter.handshake()
    assert adapter.contract["binding"]["worker_step_id"] == "7"
    assert adapter.server.releases[0]["worker_step_id"] == "7"
    assert (adapter.root / "event-0000.json").exists()
    assert (adapter.root / "binding.json").exists()
    with pytest.raises(ValueError):
        adapter.launch()
    with pytest.raises(ValueError):
        adapter.handshake()


def test_existing_claim_is_not_written_or_retried(adapter):
    root = Path(adapter.item["run"])
    root.mkdir()
    (root / "original").write_text("preserve")
    with pytest.raises(FileExistsError):
        adapter.launch()
    assert adapter.preserve()["status"] == "blocked_unbound"
    assert sorted(x.name for x in root.iterdir()) == ["original"]
    with pytest.raises(ValueError):
        adapter.launch()


@pytest.mark.parametrize(
    "field,value",
    [
        ("nonce", "0" * 64),
        ("job_id", "500001"),
        ("worker_step_id", "batch"),
        ("worker_sha256", "0" * 64),
        ("python_version", [3, 12]),
    ],
)
def test_bad_handshake_never_releases_or_signals(adapter, field, value):
    adapter.launch()
    original = adapter.server.accept

    def corrupt(remaining):
        hello, peer = original(remaining)
        hello[field] = value
        return hello, peer

    adapter.server.accept = corrupt
    with pytest.raises(ValueError):
        adapter.handshake()
    assert not adapter.server.releases and not adapter.transport.signals
    assert adapter.preserve()["status"] == "blocked_unbound"


def test_fixture_snapshot_cannot_release_ipc(adapter):
    adapter.launch()
    adapter.snapshot = lambda scopes: {**snapshot(scopes), "synthetic_observation": True}
    with pytest.raises(ValueError):
        adapter.handshake()
    assert adapter.server.releases == []


def finish(adapter):
    adapter.launch()
    adapter.handshake()
    adapter.test_clock[0] = 62
    assert adapter.tick() == "TERM_exact_step"
    assert (adapter.root / "term-intent.json").exists()
    adapter.transport.count = 0
    adapter.transport.handle.process.poll = lambda: 0
    for now in (63, 66, 69):
        adapter.test_clock[0] = now
        action = adapter.tick()
    assert action == "preserve_candidate_not_admission"
    return adapter.preserve()


def test_parent_controller_clean_quiet_replay_and_terminal_bundle(adapter, tmp_path, monkeypatch):
    report = finish(adapter)
    assert all(report[key] is False for key in a.FLAGS)
    monkeypatch.undo()  # Restore real hashing and grammar; fixture run path remap below only.
    monkeypatch.setattr(a, "validate_spec", lambda value: copy.deepcopy(value))
    text = "500000|COMPLETED|0:0|70\n500000.batch|COMPLETED|0:0|70\n500000.7|COMPLETED|0:0|62\n"
    destination = tmp_path / "collection"
    result = a.collect_terminal_components(
        adapter.root, destination, adapter.item, adapter.contract, text
    )
    review = a.audit_bundle(
        destination / "batch-evidence.tar.gz",
        result["sha256"],
        adapter.item,
        adapter.contract,
        "500000",
    )
    assert review["controller_state"] == "candidate_closed"
    assert review["worker"]["worker_outcome"] == "partial"
    assert review["live_containment_qualified"] is False
    with pytest.raises(ValueError):
        a.audit_bundle(
            destination / "batch-evidence.tar.gz",
            result["sha256"],
            adapter.item,
            adapter.contract,
            "500001",
        )
    with pytest.raises(FileExistsError):
        a.collect_terminal_components(
            adapter.root, destination, adapter.item, adapter.contract, text
        )


def test_changed_scope_missing_membership_and_late_write_do_not_close(adapter):
    adapter.launch()
    adapter.handshake()
    adapter.test_clock[0] = 2
    adapter.snapshot = lambda scopes: {**snapshot(scopes), "status": "blocked_observation"}
    assert adapter.tick() == "TERM_exact_step"
    adapter.test_clock[0] = 7
    assert adapter.tick() == "KILL_exact_step"
    assert adapter.transport.signals == [("7", "TERM"), ("7", "KILL")]
    adapter.test_clock[0] = 392
    assert adapter.tick() == "preserve_blocked_attempt"


def test_unknown_signal_ack_preserves_one_intent(adapter):
    adapter.launch()
    adapter.handshake()
    adapter.transport.signal = lambda *_: (_ for _ in ()).throw(TimeoutError())
    adapter.test_clock[0] = 62
    with pytest.raises(TimeoutError):
        adapter.tick()
    assert (adapter.root / "term-intent.json").exists()
    assert (
        adapter.preserve(failure_code="adapter_failure_preserved")["failure_code"]
        == "adapter_failure_preserved"
    )


@pytest.mark.parametrize(
    "counter,value",
    [
        ("memory_limit_bytes", 0),
        ("cpuset_cpu_count", 2),
        ("freezer_unique_process_count", 65),
        ("memory_failcnt", True),
    ],
)
def test_resource_drift_blocks(counter, value):
    value_snapshot = snapshot(process(20)["scopes"])
    value_snapshot["counters"][counter] = value
    with pytest.raises(ValueError):
        a.validate_snapshot(value_snapshot)


@pytest.mark.parametrize(
    "text",
    [
        "500000|COMPLETED|0:0\n",
        "500001|COMPLETED|0:0|1\n",
        "500000|COMPLETED+|0:0|1\n",
        "500000|COMPLETED|0:0|1\n500000|COMPLETED|0:0|1\n",
    ],
)
def test_accounting_ambiguity_fails_closed(text):
    with pytest.raises(ValueError):
        a.accounting(text, "500000")


def test_unbound_terminal_bundle_and_checksum_extra_member_rejection(plan, tmp_path):
    report = {
        "schema_version": "s2-batch-attempt-v1",
        "specification_sha256": s.digest(plan),
        "status": "blocked_unbound",
        "source": None,
        "runtime": None,
        "sample_count": 0,
        "failure_code": "adapter_failure_preserved",
        "live_containment_qualified": False,
        **a.FLAGS,
    }
    records = {
        "contract.json": None,
        "events.json": [],
        "worker.json": {},
        "adapter.json": {"attempt": report, "samples": []},
        "accounting.json": {
            "500000": {"state": "FAILED", "exit_code": "1:0", "elapsed_seconds": 2},
            "500000.batch": {"state": "FAILED", "exit_code": "1:0", "elapsed_seconds": 2},
        },
        "review.json": None,
    }
    records["review.json"] = a.review_bundle(records, plan, None, "500000")
    receipt = a.pack_bundle(tmp_path / "out", records, plan, None, "500000")
    target = tmp_path / "out/batch-evidence.tar.gz"
    assert (
        a.audit_bundle(target, receipt["sha256"], plan, None, "500000")["controller_state"]
        == "blocked_unbound"
    )
    with pytest.raises(ValueError, match="checksum"):
        a.audit_bundle(target, "0" * 64, plan, None, "500000")
    altered = tmp_path / "extra.tar.gz"
    with tarfile.open(altered, "w:gz") as archive:
        payload = b"{}"
        info = tarfile.TarInfo("../escape.json")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    with pytest.raises(ValueError, match="member"):
        a.audit_bundle(
            altered,
            hashlib.sha256(altered.read_bytes()).hexdigest(),
            plan,
            None,
            "500000",
        )


@pytest.mark.parametrize("case", w.CASES)
@pytest.mark.parametrize("fault", [None, "peer", "release", "late"])
def test_actual_worker_bridge_mocked_ipc_release_and_partial_phases(
    case, fault, tmp_path, monkeypatch
):
    plan = {
        "nonce": "a" * 64,
        "job_id": "500000",
        "case": case,
        "worker_sha256": hashlib.sha256(b"worker").hexdigest(),
        "python_sha256": hashlib.sha256(b"python").hexdigest(),
        "supervisor_pid": 10,
        "uid": 1000,
    }
    plan_path = tmp_path / "worker-plan.json"
    plan_path.write_bytes(c.encoded(plan))
    original = w._bounded_file

    def read(path, maximum):
        if Path(path) == plan_path:
            return original(path, maximum)
        return b"worker" if str(path).endswith("mvp2_s2_synthetic_worker.py") else b"python"

    monkeypatch.setattr(w, "_bounded_file", read)
    monkeypatch.setattr(w.sys, "platform", "linux")
    monkeypatch.setattr(w.os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setenv("SLURM_JOB_ID", "500000")
    monkeypatch.setenv("SLURM_STEP_ID", "7")
    connection = SimpleNamespace(
        settimeout=lambda *_: None,
        connect=lambda *_: None,
        getsockopt=lambda *_: struct.pack("3i", 11 if fault == "peer" else 10, 1000, 1000),
        send=lambda payload: len(payload),
        recv=lambda *_: c.encoded(
            {
                "nonce": ("0" if fault == "release" else "a") * 64,
                "worker_step_id": "7",
                "contract_sha256": "f" * 64,
            }
        ),
        close=lambda: None,
    )
    monkeypatch.setattr(w.socket, "SOCK_SEQPACKET", 5, raising=False)
    monkeypatch.setattr(w.socket, "AF_UNIX", 1, raising=False)
    monkeypatch.setattr(w.socket, "SO_PEERCRED", 17, raising=False)
    monkeypatch.setattr(w.socket, "socket", lambda *_: connection)
    monkeypatch.setattr(w, "fork_nested_components", lambda **_: 123)
    if fault == "late":
        values = iter((0, 31))
        monkeypatch.setattr(w.time, "monotonic", lambda: next(values))
    if fault is not None:
        with pytest.raises((ValueError, TimeoutError)):
            w.session_components(plan_path)
        assert not (tmp_path / "worker").exists()
        return
    if case.endswith("_failure"):
        with pytest.raises(RuntimeError):
            w.session_components(plan_path)
        assert (tmp_path / "worker/failure.json").exists()
    else:
        w.session_components(plan_path)
        assert (tmp_path / "worker/terminal.json").exists()


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Linux nonblocking pipe qualification; no Slurm or synthetic tree",
)
def test_real_posix_pipe_draining_overflow_timeout_and_reaping():
    for code, seconds, maximum, expected in [
        ("import os; os.write(1,b'out'); os.write(2,b'err')", 2, 100, None),
        ("import os; os.write(2,b'x'*100000)", 2, 128, ValueError),
        ("import time; time.sleep(10)", 0.2, 100, TimeoutError),
    ]:
        process = subprocess.Popen(
            (sys.executable, "-I", "-c", code),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        handle = a.PipeHandle(process)
        if expected is None:
            assert handle.query_result(seconds, maximum) == "out"
        else:
            with pytest.raises(expected):
                handle.query_result(seconds, maximum)
        assert process.poll() is not None


@pytest.mark.skipif(
    sys.platform != "linux", reason="Linux kernel peer-credential IPC; no Slurm or worker exercise"
)
def test_real_local_seqpacket_handshake_kernel_peer_credentials(tmp_path):
    import os
    import socket
    import threading

    # Reproduce the NPAD long-home-path failure before exercising a short fixture.
    # Production's 100-encoded-byte guard must remain unchanged and fail closed.
    oversized = tmp_path / ("x" * 101) / "ipc.sock"
    with pytest.raises(ValueError, match="IPC path bound/exists"):
        a.BarrierServer(oversized)
    assert not oversized.exists()
    # Do not derive a Unix socket from pytest's arbitrarily long --basetemp.
    # This directory contains ONLY disposable local test IPC, never run evidence.
    with tempfile.TemporaryDirectory(prefix="s2i-", dir="/tmp") as directory:
        path = Path(directory) / "ipc.sock"
        assert len(os.fsencode(path)) <= 100
        server = a.BarrierServer(path)
        results, errors = [], []

        def client():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as connection:
                    connection.settimeout(2)
                    connection.connect(str(path))
                    connection.send(c.encoded({"nonce": "a" * 64}))
                    results.append(c.decode_json(connection.recv(4096)))
            except BaseException as error:
                errors.append(type(error).__name__)

        thread = threading.Thread(target=client)
        thread.start()
        try:
            hello, peer = server.accept(2)
            assert hello == {"nonce": "a" * 64}
            assert peer == {"pid": os.getpid(), "uid": os.getuid()}
            server.release({"released": False}, 2)
        finally:
            server.close()
            thread.join(timeout=3)
        assert not thread.is_alive() and not errors and results == [{"released": False}]


@pytest.mark.parametrize("basename", ["x" * 101, "é" * 60])
def test_ipc_encoded_path_guard_rejects_before_socket_creation(tmp_path, monkeypatch, basename):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(a.socket, "socket", lambda *_: pytest.fail("Oversized IPC reached socket"))
    path = tmp_path / basename / "ipc.sock"
    with pytest.raises(ValueError, match="IPC path bound/exists"):
        a.BarrierServer(path)
    assert not path.exists()


def test_late_write_changes_fingerprint_and_restarts_quiet_period(adapter):
    adapter.launch()
    adapter.handshake()
    adapter.test_clock[0] = 62
    adapter.tick()
    adapter.transport.count = 0
    adapter.transport.handle.process.poll = lambda: 0
    for now, counter in ((63, None), (66, 1), (69, 2), (72, 2), (74, 2)):
        if counter is not None:
            (adapter.root / "heartbeat.json").write_bytes(
                c.encoded({"nonce": "a" * 64, "counter": counter})
            )
        adapter.test_clock[0] = now
        action = adapter.tick()
        if now < 74:
            assert adapter.controller.state != "candidate_closed"
    assert action == "preserve_candidate_not_admission"
