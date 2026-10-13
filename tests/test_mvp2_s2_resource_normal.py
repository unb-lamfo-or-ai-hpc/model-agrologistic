"""Normal launcher integration through fakes; never Slurm or a solver process."""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_compute_identity as identity
from scripts import mvp2_s2_resource_normal as n
from tests import test_mvp2_s2_batch_adapter as old


def process(pid):
    value = old.process(pid)
    for key, scope in value["scopes"].items():
        scope["scope"] = f"/cg/{key}/job_500000/" + ("step_batch" if pid == 10 else "step_7")
    value["scopes"]["cpuacct"]["scope"] = "/cg/cpuacct/shared"
    return value


def snapshot(scopes, count=1):
    value = old.snapshot(scopes, count)
    supervisor = scopes["memory"]["scope"].endswith("step_batch")
    for index, (key, entry) in enumerate(value["scopes"].items()):
        entry["inode"] = [1, 99 if key == "cpuacct" else index + (10 if supervisor else 20)]
    value["counters"].update(
        cpuset_cpu_count=2,
        effective_reported_memory_limit_bytes=(2048 if supervisor else 256) * 1024**2,
        memory_limit_bytes=2**60,
    )
    return value


def capture(adapter, *, initial):
    worker = snapshot(adapter.worker["scopes"])
    supervisor = snapshot(adapter.supervisor["scopes"])
    allocation = n.allocation_scope(adapter.worker["scopes"], adapter.item["job_id"])
    parent = {"path_sha256": n.s.digest(allocation["scope"]), "inode": [1, 100], "cpus": [0, 32]}
    return {
        "allocation_cpuset": allocation,
        "worker_chain": [{**worker["scopes"]["cpuset"], "cpus": [0, 32]}, copy.deepcopy(parent)],
        "supervisor_chain": [
            {**supervisor["scopes"]["cpuset"], "cpus": [0, 32]},
            copy.deepcopy(parent),
        ],
        "supervisor_snapshot": supervisor,
        "initial_affinity": [0] if initial else None,
    }


@pytest.fixture
def adapter(tmp_path, monkeypatch):
    plan = old.plan.__wrapped__()
    plan["run"] = str(tmp_path / "run")
    monkeypatch.setattr(a, "validate_spec", lambda v: copy.deepcopy(v))
    monkeypatch.setattr(
        a, "sha_file", lambda path, *args: "e" * 64 if str(path).endswith("python") else "d" * 64
    )
    monkeypatch.setattr(identity, "verify_compute_runtime", identity.expected_compute_runtime)
    clock = [0]
    transport = old.Transport()
    transport.worker_command = lambda: a.worker_argv(plan)
    result = n.ResourceNormalAdapter(
        plan,
        transport=transport,
        clock=lambda: clock[0],
        record=process,
        snapshot=lambda scopes: snapshot(scopes, transport.count),
        pid_absent=lambda pid: transport.count == 0,
        server_factory=old.Server,
        exe_path=lambda _pid: "/runtime/python",
        capture=capture,
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


def start_fixture(adapter):
    # Explicitly exercise the inherited component with fake spawn/server only.
    # Production ResourceNormalAdapter.launch itself remains unconditionally shut.
    a.BatchAdapter.launch(adapter)
    adapter.handshake()


def finish_fixture(adapter):
    adapter.test_clock[0] = 60
    assert adapter.tick() == "TERM_exact_step"
    adapter.transport.count = 0
    adapter.transport.handle.process.poll = lambda: 0
    for now in (62, 64, 67):
        adapter.test_clock[0] = now
        adapter.tick()
    assert adapter.controller.state == "candidate_closed"
    adapter.preserve()
    return json.loads((adapter.root / "resource-evidence.json").read_text())


def test_full_normal_handshake_sampling_exact_cleanup_and_collection(adapter, tmp_path):
    start_fixture(adapter)
    assert adapter.server.releases and len(adapter.resources) == 2
    assert adapter.controller.item == adapter.resource_contract
    assert adapter.server.releases[0]["contract_sha256"] == n.s.digest(adapter.resource_contract)
    assert adapter.resources[0]["resource"]["cpuacct_relation"] == "equal"
    value = finish_fixture(adapter)
    assert adapter.transport.signals == [("7", "TERM")]
    assert n.review(value, adapter.item)["controller_state"] == "candidate_closed"
    before = {
        v.name: hashlib.sha256(v.read_bytes()).hexdigest()
        for v in adapter.root.iterdir()
        if v.is_file()
    }
    result = n.collect(adapter.root, tmp_path / "collection", adapter.item)
    assert result["review"]["worker_cpu_usage_ns"] is None
    assert all(result[k] is False for k in n.p.FLAGS)
    assert "/cg/" not in (tmp_path / "collection/evidence.json").read_text()
    after = {
        v.name: hashlib.sha256(v.read_bytes()).hexdigest()
        for v in adapter.root.iterdir()
        if v.is_file()
    }
    assert before == after
    with pytest.raises(FileExistsError):
        n.collect(adapter.root, tmp_path / "collection", adapter.item)


@pytest.mark.parametrize("argv", [[], ["start"], ["batch"], ["worker"], ["collect"], ["--admit"]])
def test_public_cli_closed_before_project_imports(argv):
    result = subprocess.run(
        [sys.executable, "-B", "-I", str(Path(n.__file__).resolve()), *argv],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert b"Resource-normal execution remains closed" in result.stderr
    assert b"ModuleNotFoundError" not in result.stderr


def test_launch_denies_without_creating_claim(adapter):
    with pytest.raises(PermissionError):
        adapter.launch()
    assert not Path(adapter.item["run"]).exists()
    assert not adapter.launch_attempted
    with pytest.raises(PermissionError):
        n.execute_normal(object(), admit=True)


@pytest.mark.parametrize(
    "mutation",
    [
        "outside_cpu",
        "affinity_two",
        "affinity_foreign",
        "inode",
        "allocation",
        "supervisor_memory",
        "fixture",
        "missing",
    ],
)
def test_barrier_rejects_bad_observations_before_ipc(adapter, mutation):
    def bad(instance, *, initial):
        value = capture(instance, initial=initial)
        if mutation == "outside_cpu":
            value["worker_chain"][0]["cpus"] = [0, 99]
        elif mutation == "affinity_two":
            value["initial_affinity"] = [0, 32]
        elif mutation == "affinity_foreign":
            value["initial_affinity"] = [99]
        elif mutation == "inode":
            value["worker_chain"][0]["inode"] = [1, 999]
        elif mutation == "allocation":
            value["allocation_cpuset"]["scope"] += "/other"
        elif mutation == "supervisor_memory":
            value["supervisor_snapshot"]["counters"]["effective_reported_memory_limit_bytes"] *= 2
        elif mutation == "fixture":
            value["supervisor_snapshot"]["synthetic_observation"] = True
        else:
            del value["worker_chain"]
        return value

    adapter.capture = bad
    a.BatchAdapter.launch(adapter)
    with pytest.raises((ValueError, KeyError)):
        adapter.handshake()
    assert not adapter.server.releases
    adapter.preserve(failure_code="adapter_failure_preserved")
    value = json.loads((adapter.root / "resource-evidence.json").read_text())
    assert n.review(value, adapter.item)["controller_state"] == "blocked_unbound"


@pytest.mark.parametrize(
    "mutation", ["ids", "inode", "limit", "scope", "affinity", "missing", "rollback"]
)
def test_sampling_fault_routes_exact_step_stop_without_admission(adapter, mutation):
    start_fixture(adapter)

    def bad(instance, *, initial):
        value = capture(instance, initial=initial)
        if mutation == "ids":
            value["worker_chain"][0]["cpus"] = [1, 32]
        elif mutation == "inode":
            value["worker_chain"][-1]["inode"] = [1, 998]
        elif mutation == "limit":
            value["supervisor_snapshot"]["counters"]["effective_reported_memory_limit_bytes"] //= 2
        elif mutation == "scope":
            value["supervisor_snapshot"]["scopes"]["memory"]["inode"] = [1, 998]
        elif mutation == "affinity":
            value["initial_affinity"] = [0]
        elif mutation == "missing":
            raise FileNotFoundError("scope removed, not cleanup proof")
        return value

    adapter.capture = bad
    if mutation == "rollback":

        def rolled(scopes):
            value = snapshot(scopes)
            value["counters"]["cpu_usage_ns"] = 0
            return value

        adapter.snapshot = rolled
    adapter.test_clock[0] = 2
    assert adapter.tick() == "TERM_exact_step"
    assert adapter.samples[-1]["fault"] is True
    assert adapter.transport.signals == [("7", "TERM")]
    adapter.preserve(failure_code="adapter_failure_preserved")
    value = json.loads((adapter.root / "resource-evidence.json").read_text())
    assert n.review(value, adapter.item)["controller_state"] == "term"


def test_cleanup_deadline_and_latched_stop_use_versioned_controller(adapter):
    start_fixture(adapter)
    adapter.test_clock[0] = 2
    assert adapter.tick(force_fault=True) == "TERM_exact_step"
    adapter.test_clock[0] = 7
    assert adapter.tick() == "KILL_exact_step"
    adapter.test_clock[0] = 392
    assert adapter.tick() == "preserve_blocked_attempt"
    assert adapter.transport.signals == [("7", "TERM"), ("7", "KILL")]
    adapter.preserve()
    assert (
        n.review(json.loads((adapter.root / "resource-evidence.json").read_text()), adapter.item)[
            "controller_state"
        ]
        == "blocked"
    )


@pytest.mark.parametrize(
    "field", [*n.p.FLAGS, "cpu_usage", "event", "sample", "proposal", "source", "status"]
)
def test_independent_replay_rejects_tampering(adapter, field):
    start_fixture(adapter)
    value = finish_fixture(adapter)
    if field in n.p.FLAGS:
        value[field] = True
    elif field == "cpu_usage":
        value["resources"][0]["resource"]["worker_cpu_usage_ns"] = 0
    elif field == "event":
        value["events"][-1]["payload"]["state"] = "blocked"
    elif field == "sample":
        value["resources"].pop()
    elif field == "proposal":
        value["proposal"]["profile"]["allocation_cpus"] = 4
    elif field == "source":
        value["attempt"]["source"]["worker_sha256"] = "1" * 64
    else:
        value["attempt"]["status"] = "blocked"
    with pytest.raises(ValueError):
        n.review(value, adapter.item)


def test_one_observation_partial_carrier_remains_unbound(adapter):
    calls = [0]

    def once(instance, *, initial):
        calls[0] += 1
        if calls[0] == 2:
            raise FileNotFoundError("partial barrier")
        return capture(instance, initial=initial)

    adapter.capture = once
    a.BatchAdapter.launch(adapter)
    with pytest.raises(FileNotFoundError):
        adapter.handshake()
    adapter.preserve(failure_code="adapter_failure_preserved")
    value = json.loads((adapter.root / "resource-evidence.json").read_text())
    assert len(value["barriers"]) == 1
    assert n.review(value, adapter.item)["controller_state"] == "blocked_unbound"
    assert not adapter.server.releases


def test_legacy_stays_strict_and_new_receipts_are_not_legacy(adapter):
    start_fixture(adapter)
    with pytest.raises(ValueError):
        a.validate_snapshot(adapter.initial_snapshot)
    with pytest.raises(ValueError):
        n.q.verify_events(adapter.contract, adapter.controller.events)
    assert adapter.contract["profile"] == n.q.PROFILE


def test_cpu_path_resolution_does_not_guess_allocation():
    scopes = process(20)["scopes"]
    assert n.allocation_scope(scopes, "500000")["scope"].endswith("job_500000")
    with pytest.raises(ValueError):
        n.allocation_scope(scopes, "500001")


def test_reader_uses_exact_cpu_ids_and_stable_inode(tmp_path):
    parent = tmp_path / "job_500000"
    leaf = parent / "step_7"
    leaf.mkdir(parents=True)
    for path in (parent, leaf):
        (path / "cpuset.cpus").write_text("0,32")
    # Real no-follow file reads in a local fixture; never a real cgroup.
    scope = {"mount": tmp_path.as_posix(), "scope": leaf.as_posix()}
    allocation = {"mount": tmp_path.as_posix(), "scope": parent.as_posix()}
    if sys.platform != "linux":
        pytest.skip("POSIX cgroup path grammar; Linux CI exercises real no-follow reads")
    result = n.read_cpu_chain(scope, allocation)
    assert [v["cpus"] for v in result] == [[0, 32], [0, 32]]
    (leaf / "cpuset.cpus").write_text("0,33")
    with pytest.raises(ValueError):
        n.read_cpu_chain(scope, allocation)


def test_initial_affinity_reader_binds_birth_and_scopes():
    class Directory:
        def __init__(self, path):
            assert path == "/proc/20"

        def read(self, name):
            assert name == "status"
            return "Name: python\nCpus_allowed_list:\t0"

        def close(self):
            pass

    assert n.read_initial_affinity(process(20), record=process, directory=Directory) == [0]

    def reused(pid):
        value = process(pid)
        value["identity"]["starttime"] += 1
        return value

    with pytest.raises(ValueError):
        n.read_initial_affinity(process(20), record=reused, directory=Directory)


def test_legacy_release_digest_stays_legacy(adapter):
    start_fixture(adapter)
    assert a.BatchAdapter.release_digest(adapter) == n.s.digest(adapter.contract)
    assert adapter.release_digest() != a.BatchAdapter.release_digest(adapter)


@pytest.mark.skipif(sys.platform != "linux", reason="Linux no-follow directory semantics")
def test_cpu_reader_rejects_symlink_and_replaced_inode(tmp_path):
    parent = tmp_path / "job_500000"
    leaf = parent / "step_7"
    leaf.mkdir(parents=True)
    for path in (parent, leaf):
        (path / "cpuset.cpus").write_text("0,32")
    link = parent / "linked"
    link.symlink_to(leaf, target_is_directory=True)
    allocation = {"mount": tmp_path.as_posix(), "scope": parent.as_posix()}
    with pytest.raises(OSError):
        n.read_cpu_chain({"mount": tmp_path.as_posix(), "scope": link.as_posix()}, allocation)
    calls = [0]

    def changed(path):
        fd = n.q.r._Directory(path)
        calls[0] += 1
        if calls[0] == 3:
            fd.identity = [1, 999999]
        return fd

    with pytest.raises(ValueError):
        n.read_cpu_chain(
            {"mount": tmp_path.as_posix(), "scope": leaf.as_posix()}, allocation, directory=changed
        )


def test_collection_rejects_durable_record_drift_and_partial_file(adapter, tmp_path):
    start_fixture(adapter)
    finish_fixture(adapter)
    path = adapter.root / "event-0000.json"
    saved = path.read_bytes()
    path.write_text("{}")
    with pytest.raises(ValueError):
        n.collect(adapter.root, tmp_path / "bad-collection", adapter.item)
    assert not (tmp_path / "bad-collection").exists()
    path.write_bytes(saved)
    (adapter.root / "resource-evidence.json").write_text("{")
    with pytest.raises(ValueError):
        n.collect(adapter.root, tmp_path / "partial-collection", adapter.item)
    assert not (tmp_path / "partial-collection").exists()
