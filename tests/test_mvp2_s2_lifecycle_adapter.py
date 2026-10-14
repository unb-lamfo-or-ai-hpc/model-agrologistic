"""Independent verifier/operational integration with fixtures; no Slurm or worker."""

import copy
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_s2_lifecycle_adapter as m
from tests import test_mvp2_s2_lifecycle_protocol as f

e, lc, s, q, a = m.e, m.lc, m.s, m.q, m.a
HEADER = "PID JOBID STEPID LOCALID GLOBALID\n"


def status(**changes):
    data = {
        "Uid": "1000 1000 1000 1000",
        "Gid": "1000 1000 1000 1000",
        "Groups": "1000",
        "CapEff": "0000000000000000",
        "CapPrm": "0",
        "CapInh": "0",
        "CapAmb": "0",
        "NoNewPrivs": "1",
        "Threads": "1",
    }
    data.update(changes)
    return "\n".join(key + ":\t" + value for key, value in data.items())


class FixtureKernel:
    fixture = True

    def __init__(self, spec, digest, item):
        self.spec, self.digest, self.item = spec, digest, item
        self.exited, self.client_reaped = False, False
        self.worker_status = status()
        self.host_value = {
            "max_user_namespaces": 0,
            "namespaces": {key: [1, i + 1] for i, key in enumerate(e.NAMESPACES)},
        }
        self.fd_inventory = []
        self.delegated = False
        self.replace_anchor = False
        self.foreign = False
        self.steps = None
        self.fail_method = None

    def self_pid(self):
        return 10

    def peer(self, _connection):
        return {"pid": 20, "uid": 1000, "gid": 1000}

    def process(self, pid, *, protected=False):
        if self.fail_method == "process":
            raise PermissionError("private details must never appear publicly")
        role = "worker" if pid == 20 else "batch"
        scopes = {
            key: {"mount": "/cg/" + key, "scope": "/cg/" + key + "/job/" + role}
            for key in s.CONTROLLERS
        }
        scopes["cpuacct"] = {"mount": "/cg/cpuacct", "scope": "/cg/cpuacct/job/batch"}
        return {
            "identity": f.process(pid),
            "scopes": scopes,
            "status": self.worker_status if protected else status(NoNewPrivs="0"),
            "uid_map": "0 0 4294967295",
            "namespaces": copy.deepcopy(self.host_value["namespaces"]),
            "fd_inventory": copy.deepcopy(self.fd_inventory) if protected else None,
            "executable": self.spec["tools"]["srun"] if pid == 12 else self.spec["python"],
            "argv": m.worker_arguments(self.spec, self.digest, self.item)
            if pid == 20
            else ["owned-batch"],
            "ppid": 11 if pid == 10 else 10,
        }

    def host(self):
        return copy.deepcopy(self.host_value)

    def descriptor(self, mount, parent, worker, supervisor, mount_id):
        return {
            "mount": mount,
            "parent": parent,
            "worker": worker,
            "supervisor": supervisor,
            "mount_id": mount_id,
            "mount_identity": [1, 1],
            "parent_identity": [1, 2],
            "worker_identity": [1, 20],
            "supervisor_identity": [1, 10],
        }

    def hierarchy(self, _mount):
        result = []
        names = ["", "job", "job/batch"] + ([] if self.exited else ["job/worker"])
        for index, name in enumerate(names):
            children = sorted(
                n[len(name) + 1 :] if name else n
                for n in names
                if n and n.rpartition("/")[0] == name
            )
            value = {"relative": name, "children": children}
            for key in ("directory", "tasks", "procs"):
                value[key] = {
                    "identity": [1, index * 10 + 100],
                    "uid": 0,
                    "mode": 0o755 if key == "directory" else 0o644,
                    "acl": "absent_or_unsupported",
                }
            if self.delegated:
                value["procs"]["uid"] = 1000
            result.append(value)
        return result

    def mountinfo(self, _pid):
        return "\n".join(
            f"50 1 0:1 / /cg/{key} rw - cgroup cgroup rw,{key}" for key in s.CONTROLLERS
        )

    def inventory(self, descriptor):
        if self.fail_method == "inventory":
            raise FileNotFoundError("private path")
        bound = {"controllers": {"k": descriptor}}
        value = f.inventory(bound, alive=not self.exited)["k"]
        value["groups"][1]["members"].append(f.process(11))
        if not self.client_reaped:
            value["groups"][1]["members"].append(f.process(12))
        if self.foreign:
            value["groups"][0]["members"].append(f.process(99))
        return value

    def anchors(self, descriptor):
        value = {
            key: copy.deepcopy(descriptor[key])
            for key in ("mount_identity", "parent_identity", "supervisor_identity")
        }
        if self.replace_anchor:
            value["parent_identity"][1] += 1
        return value

    def step_status(self, _descriptors):
        return (
            copy.deepcopy(self.steps)
            if self.steps is not None
            else dict.fromkeys(lc.CONTROLLERS, "missing" if self.exited else "available")
        )

    def resources(self, item, _worker, _supervisor, _descriptors, *, initial_affinity):
        value = copy.deepcopy(f.fixtures()[2]["resources"])
        value["contract_sha256"] = s.digest(item["resource_contract"])
        return value

    def absence(self, _identity):
        return "absent" if self.exited else "present"


class FixtureRPC:
    def __init__(self, kernel):
        self.kernel, self.calls = kernel, []
        self.accounting_pending = False

    def command(self, argv, *, timeout_seconds, max_output_bytes):
        self.calls.append(tuple(argv))
        assert timeout_seconds == 1 and max_output_bytes == 65536
        if "show" in argv and "job" in argv:
            return (
                "JobId=123 UserId=u(1000) JobState=RUNNING NumNodes=1 NumCPUs=2 "
                "NodeList=n1 BatchHost=n1 TimeLimit=00:12:00 MinMemoryNode=2G"
            )
        if "show" in argv and "step" in argv:
            return (
                "StepId=123.0 UserId=1000 Nodes=1 NodeList=n1 "
                "State=RUNNING CPUs=1 Tasks=1 TimeLimit=00:09:00"
            )
        if "listpids" in argv:
            if argv[-1].endswith("." + a.BATCH_QUERY_STEP):
                return HEADER + "\n".join(f"{pid} 123 batch - -" for pid in (10, 11, 12))
            return HEADER + "20 123 0 0 0"
        assert argv[0] == self.kernel.spec["tools"]["sacct"]
        state = "COMPLETED" if self.kernel.exited and not self.accounting_pending else "RUNNING"
        return "123|RUNNING|0:0|12\n123.batch|RUNNING|0:0|12\n123.0|" + state + "|0:0|1"


class Clock:
    def __init__(self):
        self.value = 0

    def __call__(self):
        self.value += 1
        return self.value


class Server:
    def __init__(self, handshake):
        self.handshake, self.peer, self.released = handshake, object(), False

    def accept(self, remaining):
        assert 0 < remaining <= 30
        return copy.deepcopy(self.handshake), {"pid": 20, "uid": 1000}

    def release(self, *_args):
        pytest.fail("Closed adapter must never release IPC")


@pytest.fixture
def context(monkeypatch):
    item, _, _ = f.fixtures()
    files = {name: "d" * 64 for name in m.CLOSURE | m.identity.REQUIRED}
    manifest = {
        "schema_version": "s2-sealed-source-v1",
        "source_commit": "b" * 40,
        "files": files,
        "source": m.identity.source_summary(files),
    }
    legacy = item["resource_contract"]["legacy_contract"]
    legacy["source_sha256"] = manifest["source"]["source_sha256"]
    legacy["worker_sha256"] = manifest["source"]["worker_sha256"]
    spec = a.specification(
        checkout="/source",
        run="/runs/new-unreserved",
        python="/runtime/python",
        tools={key: "/tools/" + key for key in a.TOOLS},
        tools_sha256={key: "d" * 64 for key in a.TOOLS},
        python_sha256="e" * 64,
        source_commit="b" * 40,
        nonce="a" * 64,
        job_id="123",
        case="normal",
        inventory=json.loads(Path("docs/mvp2_s2_slurm_site_inventory.json").read_text()),
    )
    digest = s.digest(manifest)
    source_calls = []

    def source(checkout, value, commit, expected):
        source_calls.append(checkout)
        assert value == manifest and expected == digest and commit == "b" * 40
        return copy.deepcopy(manifest["source"])

    monkeypatch.setattr(m.identity, "verify_compute_source", source)
    monkeypatch.setattr(
        m.identity,
        "verify_compute_runtime",
        lambda value, role: m.identity.expected_compute_runtime(value, role),
    )
    kernel = FixtureKernel(spec, digest, item)
    rpc = FixtureRPC(kernel)
    queries = m.FixedQueries(spec, legacy["binding"], rpc)
    clock = Clock()
    launcher = SimpleNamespace(pid=12, poll=lambda: 0 if kernel.client_reaped else None)
    adapter = m.OperationalAdapter(
        spec, manifest, digest, item, kernel=kernel, queries=queries, clock=clock, launcher=launcher
    )
    handshake = m.worker_components(
        spec, manifest, digest, item, prctl=lambda code, *_args: 1 if code == 39 else 0
    )
    candidate = {
        "worker_pid": 20,
        "supervisor_pid": 10,
        "owned_batch": [
            {"role": "batch_shell", "pid": 11},
            {"role": "local_srun_client", "pid": 12},
        ],
        "parents": {key: "/cg/" + key + "/job" for key in lc.CONTROLLERS},
        "node": "n1",
    }
    return SimpleNamespace(
        adapter=adapter,
        kernel=kernel,
        rpc=rpc,
        queries=queries,
        clock=clock,
        launcher=launcher,
        server=Server(handshake),
        candidate=candidate,
        item=item,
        source_calls=source_calls,
    )


def prepare(ctx):
    result = ctx.adapter.prepare_components(ctx.server, ctx.candidate)
    assert result["failures"] == [], result
    assert result["protocol"]["state"] == "running"
    return result


def products():
    values = f.products()
    writes = dict.fromkeys(lc.WRITE_FILES)
    writes.update({"worker/" + name: s.digest(value) for name, value in values.items()})
    return values, writes


def terminal_text():
    return (
        "123|COMPLETED|0:0|14\n123.batch|COMPLETED|0:0|14\n"
        "123.extern|COMPLETED|0:0|14\n123.0|COMPLETED|0:0|1"
    )


def test_integrated_independent_binding_fast_exit_and_terminal_replay(context):
    ctx = context
    result = prepare(ctx)
    assert result["ipc_released"] is False and all(result[key] is False for key in lc.FLAGS)
    ctx.kernel.exited = ctx.kernel.client_reaped = True
    for _ in range(5):
        result = ctx.adapter.observe_components(products)
        if result["protocol"]["state"] == "software_candidate_closed":
            break
    assert result["protocol"]["state"] == "software_candidate_closed", result
    review = ctx.adapter.terminal_review(terminal_text())
    assert review["disposition"] == "software_replayed_not_live_qualified", review
    assert review["replay"]["software_review"]["state"] == "software_candidate_closed"
    assert ctx.source_calls and not ctx.server.released
    assert result["observation_provenance"] == "software_fixture"
    assert not any(
        value in json.dumps(review)
        for value in ("/source", "/cg/", '"pid"', '"uid"', "private details")
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("Uid", "0 0 0 0"),
        ("Uid", "1000 0 1000 1000"),
        ("Gid", "1000 0 1000 1000"),
        ("CapEff", "1"),
        ("CapPrm", "1"),
        ("CapInh", "1"),
        ("CapAmb", "1"),
        ("NoNewPrivs", "0"),
        ("Threads", "2"),
    ],
)
def test_security_profile_is_independently_checked_not_from_handshake(context, field, value):
    context.kernel.worker_status = status(**{field: value})
    result = context.adapter.prepare_components(context.server, context.candidate)
    assert result["status"] == "blocked_environment_or_observation"
    assert result["protocol"]["state"] == "startup" and result["ipc_released"] is False
    assert result["environment_error_sites"] == ["worker_credentials_namespaces_or_fds"]
    assert (
        context.adapter.terminal_review(terminal_text())["disposition"]
        == "negative_or_partial_preserved"
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "userns",
        "write_fd",
        "permission",
        "peer_pid",
        "peer_uid",
        "peer_gid",
        "source",
        "runtime",
        "nonce",
        "manifest",
        "foreign",
        "supervisor",
        "kernel_read",
        "parent_path",
    ],
)
def test_pre_barrier_faults_preserve_evidence_and_never_bind(context, monkeypatch, mutation):
    ctx = context
    if mutation == "userns":
        ctx.kernel.host_value["max_user_namespaces"] = 100
    elif mutation == "write_fd":
        ctx.kernel.fd_inventory = [{"filesystem_type": e.CGROUP_MAGIC, "flags": os.O_WRONLY}]
    elif mutation == "permission":
        ctx.kernel.delegated = True
    elif mutation.startswith("peer_"):
        peer = {"pid": 20, "uid": 1000, "gid": 1000}
        peer[mutation[5:]] += 1
        monkeypatch.setattr(ctx.kernel, "peer", lambda _connection: peer)
    elif mutation in {"source", "runtime"}:

        def fail(*_args, **_kwargs):
            raise ValueError("private source info")

        monkeypatch.setattr(
            m.identity,
            "verify_compute_source" if mutation == "source" else "verify_compute_runtime",
            fail,
        )
    elif mutation in {"nonce", "manifest"}:
        ctx.server.handshake["nonce" if mutation == "nonce" else "manifest_sha256"] = "f" * 64
    elif mutation == "foreign":
        ctx.kernel.foreign = True
    elif mutation == "supervisor":
        ctx.candidate["supervisor_pid"] = 99
    elif mutation == "kernel_read":
        ctx.kernel.fail_method = "process"
    else:
        ctx.candidate["parents"]["cpuset"] = "/foreign"
    result = ctx.adapter.prepare_components(ctx.server, ctx.candidate)
    assert result["status"] == "blocked_environment_or_observation", mutation
    assert result["protocol"]["state"] == "startup" and result["ipc_released"] is False
    review = ctx.adapter.terminal_review(terminal_text())
    assert review["disposition"] in {"negative_or_partial_preserved", "rejected_evidence_preserved"}
    assert "private source info" not in json.dumps(review)


def test_live_sampling_then_missing_step_keeps_independent_parent_proof(context):
    prepare(context)
    result = context.adapter.observe_components(products)
    assert result["protocol"]["state"] == "running", result
    context.kernel.exited = context.kernel.client_reaped = True
    result = context.adapter.observe_components(products)
    assert result["protocol"]["state"] == "cleanup", result
    assert context.adapter.observations[-1]["result"]["packet"]["step_scopes"] == dict.fromkeys(
        lc.CONTROLLERS, "missing"
    )
    assert context.adapter.observations[-1]["result"]["packet"]["resources"] is None


@pytest.mark.parametrize(
    "fault", ["parent_replaced", "inventory_read", "foreign_pid", "permissions", "cadence"]
)
def test_continuation_invalidates_unknown_parent_or_resource_coverage(context, fault):
    prepare(context)
    context.kernel.exited = context.kernel.client_reaped = True
    if fault == "parent_replaced":
        context.kernel.replace_anchor = True
    elif fault == "inventory_read":
        context.kernel.fail_method = "inventory"
    elif fault == "foreign_pid":
        context.kernel.foreign = True
    elif fault == "permissions":
        context.kernel.delegated = True
    else:
        context.clock.value += 10
    result = context.adapter.observe_components(products)
    assert (
        result["status"] == "blocked_environment_or_observation"
        or result["protocol"]["state"] == "blocked"
    )
    assert all(result[key] is False for key in lc.FLAGS)
    with pytest.raises(ValueError):
        context.adapter.observe_components(products)


def test_short_terminal_accounting_lag_cannot_count_as_quiet(context):
    prepare(context)
    context.kernel.exited = context.kernel.client_reaped = True
    context.rpc.accounting_pending = True
    result = context.adapter.observe_components(products)
    assert not result["failures"] and result["protocol"]["state"] == "cleanup"
    assert context.adapter.observations[-1]["result"]["accounting_pending"] is True
    context.rpc.accounting_pending = False
    result = context.adapter.observe_components(products)
    assert not result["failures"] and result["protocol"]["state"] == "cleanup"


@pytest.mark.parametrize(
    "mutation", ["missing_record", "extra_record", "permission", "result", "error_site"]
)
def test_independent_frame_replay_rejects_drift(context, mutation):
    prepare(context)
    frame = copy.deepcopy(context.adapter.frames[0])
    if mutation == "missing_record":
        frame["kernel"].pop()
    elif mutation == "extra_record":
        frame["kernel"].append(copy.deepcopy(frame["kernel"][-1]))
    elif mutation == "permission":
        entry = next(v for v in frame["kernel"] if v["method"] == "hierarchy")
        entry["value"][0]["procs"]["mode"] = 0o666
    elif mutation == "result":
        frame["result"]["cleanup_accepted"] = True
    else:
        frame["error_site"] = "invented"
    with pytest.raises(ValueError):
        m.replay_frame(context.item, frame)


def test_observation_replay_binds_raw_kernel_facts_and_journal(context):
    prepare(context)
    context.kernel.exited = context.kernel.client_reaped = True
    context.adapter.observe_components(products)
    frame = context.adapter.observations[0]
    serialized = json.loads(json.dumps(frame))
    assert (
        m.replay_observation(context.item, context.adapter.original, serialized) == frame["result"]
    )
    frame["result"]["packet"]["inventories"] = None
    assert (
        context.adapter.terminal_review(terminal_text())["disposition"]
        == "rejected_evidence_preserved"
    )


def test_cumulative_evidence_and_read_only_query_bounds(context):
    with pytest.raises(ValueError):
        context.queries.query("launch")
    assert context.rpc.calls == []
    context.adapter.evidence_bytes = 32 * 1024**2
    result = context.adapter.prepare_components(context.server, context.candidate)
    assert result["status"] == "blocked_environment_or_observation"


def test_nested_terminal_journal_rejection_is_not_reported_as_replayed(context, monkeypatch):
    prepare(context)
    monkeypatch.setattr(
        m.package, "collect", lambda *_args, **_kwargs: {"disposition": "rejected_journal"}
    )
    assert (
        context.adapter.terminal_review(terminal_text())["disposition"]
        == "rejected_evidence_preserved"
    )


def test_worker_migration_during_live_sampling_blocks(context, monkeypatch):
    prepare(context)
    original = context.kernel.process

    def migrated(pid, *, protected=False):
        value = original(pid, protected=protected)
        if pid == 20:
            value["scopes"]["memory"]["scope"] = "/cg/memory/elsewhere"
        return value

    monkeypatch.setattr(context.kernel, "process", migrated)
    result = context.adapter.observe_components(products)
    assert result["status"] == "blocked_environment_or_observation"
    assert result["ipc_released"] is False


def test_closed_launch_denies_before_observation(context):
    with pytest.raises(PermissionError):
        context.adapter.launch()
    assert context.rpc.calls == [] and context.adapter.frames == []


@pytest.mark.parametrize("module", [e, m])
@pytest.mark.parametrize(
    "action",
    ["start", "batch", "worker", "collect", "normal", "adverse", "native", "h300", "retry"],
)
def test_public_entry_denies_before_imports_or_io(module, action, tmp_path):
    result = subprocess.run(
        [sys.executable, "-B", "-I", str(Path(module.__file__).resolve()), action],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0 and "PermissionError" in result.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("result", [-1, 0])
def test_hardening_failure_cannot_be_a_worker_release(result):
    with pytest.raises(ValueError):
        e.harden_worker_components(lambda *_args: result)


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Real Linux fstatfs and kernel peer credentials; no Slurm/worker",
)
def test_linux_real_read_only_filesystem_and_ipc_primitives(tmp_path):
    directory = q.r._Directory(tmp_path)
    try:
        assert e.filesystem_type(directory.fd) != e.CGROUP_MAGIC
    finally:
        directory.close()
    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    try:
        assert e.KernelReader().peer(left) == {
            "pid": os.getpid(),
            "uid": os.getuid(),
            "gid": os.getgid(),
        }
    finally:
        left.close()
        right.close()
    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        with pytest.raises(ValueError):
            e.KernelReader().peer(left)
    finally:
        left.close()
        right.close()
    assert e.security_fields(Path("/proc/self/status").read_text()).keys() == set(e.SECURITY_FIELDS)
