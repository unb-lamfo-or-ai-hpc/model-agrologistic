"""Synthetic read-only cgroup receipts; no solver, jobs, network or children."""

import copy
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from scripts import mvp2_h300_resources as resources

IDENTITY = "a" * 64


def write(path, value):
    path.write_text(str(value), encoding="ascii")


def group(path, *, pids="", populated=0, cpu=100):
    path.mkdir(parents=True)
    for name, value in {
        "cgroup.type": "domain",
        "memory.max": 1024,
        "memory.current": 12,
        "cpu.stat": f"usage_usec {cpu}\nuser_usec 40\nsystem_usec 60\n",
        "memory.events": "low 0\nmax 0\noom 2\noom_kill 1\n",
        "cgroup.events": f"populated {populated}\nfrozen 0\n",
        "cgroup.procs": pids,
    }.items():
        write(path / name, value)


def proc(path, pid=123, starttime=77):
    directory = path / str(pid)
    directory.mkdir(parents=True, exist_ok=True)
    fields = ["S"] + ["0"] * 21
    fields[19] = str(starttime)
    write(directory / "stat", f"{pid} (name with ) spaces) " + " ".join(fields))


@pytest.fixture
def observed(tmp_path):
    allocation = tmp_path / "allocation"
    child = allocation / "owned"
    group(child)
    proc(tmp_path / "proc")
    observer = resources.CgroupV2Observer(
        allocation, child, owned={123: 77}, proc_root=tmp_path / "proc", test_only=True
    )
    return observer, child, tmp_path / "proc"


def receipt(observer):
    now, phase = [10.0], ["startup"]
    recorder = resources.ResourceSampler(
        lambda: {"cgroup": observer.read(), "process_tree": None},
        lambda: phase[0],
        identity=IDENTITY,
        clock=lambda: now[0],
    )
    recorder.sample()
    now[0], phase[0] = 11.0, "build"
    recorder.sample()
    now[0], phase[0] = 12.0, "cleanup"
    return recorder.finish()


def test_empty_nested_scope_final_counters_and_lifetime_cpu(observed):
    observer, child, _ = observed
    group(child / "nested")
    value = receipt(observer)
    value["final"]["cgroup"]["cpu_usage_usec"] += 3_600_000_000
    summary = resources.verify_sampling(value, IDENTITY)
    assert summary["sampling_valid"] and not summary["containment_closed"]
    assert summary["synthetic_observation"] is True
    assert summary["allocation_tree_closed"] is False
    assert summary["production_admitted"] is False
    assert summary["measured_lifetime_cpu_hours"] == 1
    assert summary["max_gap_ms"] == 1000
    assert summary["sample_count"] == 3
    assert value["final"]["cgroup"]["memory_peak_bytes"] is None
    assert value["final"]["cgroup"]["oom"] == 2
    assert value["final"]["cgroup"]["oom_kill"] == 1
    assert value["final"]["process_tree"] is None


def test_nested_populated_prevents_closure_even_when_root_pid_exited(observed):
    observer, child, _ = observed
    group(child / "nested", populated=1, pids="123\n")
    value = receipt(observer)
    assert not resources.verify_sampling(value, IDENTITY)["containment_closed"]


def test_pid_reuse_and_unowned_member_are_explicit(observed):
    observer, child, proc_root = observed
    write(child / "cgroup.procs", "123\n")
    write(child / "cgroup.events", "populated 1\n")
    assert not observer.read()["errors"]
    proc(proc_root, starttime=78)
    assert "pid_reused" in observer.read()["errors"]
    write(child / "cgroup.procs", "999\n")
    assert "unowned_member" in observer.read()["errors"]


@pytest.mark.parametrize("limit", ["max", "0", "-1", "NaN", "1 2"])
def test_memory_limit_must_be_positive_finite(observed, limit):
    observer, child, proc_root = observed
    write(child / "memory.max", limit)
    with pytest.raises(ValueError):
        resources.CgroupV2Observer(
            observer.allocation, child, owned={123: 77}, proc_root=proc_root, test_only=True
        )


def test_root_and_shared_scope_rejected(observed):
    observer, child, _ = observed
    for parent, target in ((child, child), (child, observer.allocation)):
        with pytest.raises(ValueError):
            resources.CgroupV2Observer(parent, target, owned={123: 77}, test_only=True)


def test_recreated_scope_inode_rejected(observed):
    observer, child, _ = observed
    child.rename(child.with_name("old"))
    group(child)
    value = observer.read()
    assert "scope_identity_changed" in value["errors"]
    assert value["cpu_usage_usec"] is None


def test_symlink_rejected_when_available(observed):
    observer, child, _ = observed
    link = child / "linked"
    try:
        link.symlink_to(child, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation unavailable to this account")
    assert observer.read()["errors"]
    with pytest.raises((OSError, ValueError)):
        resources.CgroupV2Observer(observer.allocation, link, owned={123: 77}, test_only=True)


def test_missing_and_malformed_counters_stay_null(observed):
    observer, child, _ = observed
    (child / "memory.current").unlink()
    write(child / "cpu.stat", "usage_usec 1\nusage_usec 2\n")
    value = observer.read()
    assert value["memory_current_bytes"] is None and value["cpu_usage_usec"] is None
    assert len(value["errors"]) == 2


def test_read_bounds_and_no_files_modified(observed):
    observer, child, _ = observed
    before = {str(p): p.read_bytes() for p in child.rglob("*") if p.is_file()}
    observer.read()
    assert before == {str(p): p.read_bytes() for p in child.rglob("*") if p.is_file()}
    write(child / "cpu.stat", "x" * (resources.MAX_BYTES + 1))
    assert observer.read()["cpu_usage_usec"] is None


def test_nested_identity_memory_limit_and_group_bound(observed):
    observer, child, proc_root = observed
    group(child / "nested")
    value = receipt(observer)
    nested_id = hashlib.sha256(str(child / "nested").encode("utf-8")).hexdigest()
    nested = next(g for g in value["final"]["cgroup"]["subtree"] if g["node_id"] == nested_id)
    nested["id"][1] += 1
    assert "nested_identity_changed" in resources.verify_sampling(value, IDENTITY)["errors"]
    value = receipt(observer)
    value["final"]["cgroup"]["memory_max_bytes"] += 1
    assert "memory_limit_changed" in resources.verify_sampling(value, IDENTITY)["errors"]
    with pytest.raises(ValueError, match="Invalid dedicated scope"):
        resources.CgroupV2Observer(
            observer.allocation,
            child,
            owned={123: 77},
            proc_root=proc_root,
            test_only=True,
            max_groups=1,
        )


def test_inter_sample_gap_and_exact_five_second_boundary(observed):
    value = receipt(observed[0])
    value["final"]["at_ms"] = value["ended_ms"] = 16_000
    assert resources.verify_sampling(value, IDENTITY)["sampling_valid"]
    value["final"]["at_ms"] = value["ended_ms"] = 16_001
    assert "sampling_gap_exceeded" in resources.verify_sampling(value, IDENTITY)["errors"]


@pytest.mark.parametrize(
    "mutation,code",
    [
        (lambda v: v["final"]["cgroup"].update(cpu_usage_usec=1), "lifetime_cpu_reset"),
        (lambda v: v["final"].update(at_ms=9_000), "clock_rollback"),
        (lambda v: v["final"].update(phase="startup"), "phase_rollback_or_missing"),
        (lambda v: v.update(started_ms=0), "sampling_gap_exceeded"),
        (lambda v: v.update(ended_ms=20_000), "sampling_gap_exceeded"),
        (lambda v: v["final"].update(cgroup=None), "missing_cgroup"),
        (lambda v: v["final"].update(phase="build"), "final_observation_before_cleanup"),
    ],
)
def test_replay_invalidates_bad_evidence(observed, mutation, code):
    value = receipt(observed[0])
    mutation(value)
    summary = resources.verify_sampling(value, IDENTITY)
    assert code in summary["errors"]
    assert not summary["sampling_valid"] and not summary["containment_closed"]
    assert summary["measured_lifetime_cpu_hours"] is None


def test_identity_scope_and_strict_schema(observed):
    value = receipt(observed[0])
    with pytest.raises(ValueError):
        resources.verify_sampling(value, "b" * 64)
    for key in ("containment_closed", "allocation_tree_closed", "anything"):
        altered = copy.deepcopy(value)
        altered[key] = True
        with pytest.raises(ValueError):
            resources.verify_sampling(altered, IDENTITY)
    value["final"]["cgroup"]["scope"]["child_id"][1] += 1
    value["final"]["cgroup"]["subtree"][0]["id"] = value["final"]["cgroup"]["scope"]["child_id"][:]
    assert "scope_identity_changed" in resources.verify_sampling(value, IDENTITY)["errors"]


def test_sampler_cadence_bound_final_slot_and_failure_metadata(observed):
    now, phase, calls = [1.0], ["startup"], []

    def probe():
        calls.append(True)
        raise OSError("synthetic missing probe")

    recorder = resources.ResourceSampler(
        probe, lambda: phase[0], identity=IDENTITY, max_samples=2, clock=lambda: now[0]
    )
    recorder.sample()
    now[0] = 1.1
    assert recorder.sample() is None
    now[0], phase[0] = 2.0, "cleanup_after_failure"
    value = recorder.finish()
    assert len(calls) == 2 and len(value["samples"]) == 1
    summary = resources.verify_sampling(value, IDENTITY)
    assert not summary["sampling_valid"] and "sample_bound_reached" in summary["errors"]
    assert value["final"]["cgroup"] is None and value["final"]["errors"]
    with pytest.raises(ValueError):
        recorder.sample()


def test_cadence_skips_without_callback_and_detects_suppressed_rollback(observed):
    now, phase, calls = [1.0], ["startup"], []

    def probe():
        calls.append(True)
        return {"cgroup": observed[0].read(), "process_tree": None}

    recorder = resources.ResourceSampler(
        probe, lambda: phase[0], identity=IDENTITY, clock=lambda: now[0]
    )
    recorder.sample()
    now[0] = 1.5
    assert recorder.sample() is None and len(calls) == 1
    now[0] = 1.4
    recorder.sample()
    now[0], phase[0] = 2.0, "cleanup_after_failure"
    assert "clock_rollback" in resources.verify_sampling(recorder.finish(), IDENTITY)["errors"]


def test_production_denial_is_unconditional():
    with pytest.raises(PermissionError, match="disabled"):
        resources.production_entry(containment_closed=True, allocation_tree_closed=True)


def test_scope_paths_are_only_sha256_and_hash_drift_is_rejected(observed):
    observer, child, _ = observed
    value = receipt(observer)
    scope = value["final"]["cgroup"]["scope"]
    assert (
        scope["allocation_path_sha256"]
        == hashlib.sha256(str(observer.allocation).encode("utf-8")).hexdigest()
    )
    assert scope["child_path_sha256"] == hashlib.sha256(str(child).encode("utf-8")).hexdigest()
    assert str(child) not in json.dumps(value)
    assert str(observer.allocation) not in json.dumps(value)
    for bad in ("/secret/path", "a" * 63, "A" * 64, None):
        altered = copy.deepcopy(value)
        altered["final"]["cgroup"]["scope"]["child_path_sha256"] = bad
        with pytest.raises(ValueError, match="digests"):
            resources.verify_sampling(altered, IDENTITY)
    value["final"]["cgroup"]["scope"]["child_path_sha256"] = "b" * 64
    value["final"]["cgroup"]["subtree"][0]["node_id"] = "b" * 64
    assert "scope_identity_changed" in resources.verify_sampling(value, IDENTITY)["errors"]


@pytest.mark.parametrize("level", ["receipt", "sample", "cgroup"])
@pytest.mark.parametrize(
    "bad",
    [
        ["unknown_error"],
        ["Authorization: Bearer sk-secret"],
        [123],
        "scope_read_failed",
        [None],
        {"secret": "token"},
        ["probe_read_failed"] * (resources.MAX_ERRORS + 1),
    ],
)
def test_public_replay_rejects_unknown_or_malformed_errors(observed, level, bad):
    value = receipt(observed[0])
    target = (
        value
        if level == "receipt"
        else value["final"]
        if level == "sample"
        else value["final"]["cgroup"]
    )
    target["errors"] = bad
    with pytest.raises(ValueError, match="error codes"):
        resources.verify_sampling(value, IDENTITY)


@pytest.mark.parametrize(
    "bad_path",
    [
        "../secret",
        "/secret",
        "x\\secret",
        "token=sk-secret",
        "sk-secret-alphanumeric-credential",
        "secret:token",
        "a\nb",
        "a" * 65,
        "x/" * 16 + "x",
    ],
)
def test_legacy_subtree_path_fields_are_rejected(observed, bad_path):
    value = receipt(observed[0])
    value["final"]["cgroup"]["subtree"].append(
        {"path": bad_path, "id": [1, 2], "populated": 0, "pids": []}
    )
    with pytest.raises(ValueError, match="schema fields"):
        resources.verify_sampling(value, IDENTITY)


def test_observer_omits_unsafe_directory_names(observed):
    observer, child, _ = observed
    group(child / "token=sk-secret")
    value = observer.read()
    assert "unsafe_nested_path" in value["errors"]
    assert "sk-secret" not in json.dumps(value)


def test_credential_named_scope_and_nested_directories_are_opaque(tmp_path):
    marker = "sk-credential-marker"
    allocation = tmp_path / (marker + "-allocation")
    child = allocation / (marker + "-child")
    nested = child / (marker + "-nested")
    leaf = nested / (marker + "-leaf")
    for path in (child, nested, leaf):
        group(path)
    observer = resources.CgroupV2Observer(allocation, child, owned={123: 77}, test_only=True)
    value = receipt(observer)
    summary = resources.verify_sampling(value, IDENTITY)
    assert summary["sampling_valid"] and summary["synthetic_observation"]
    assert not summary["containment_closed"]
    assert marker not in json.dumps(value) and marker not in json.dumps(summary)
    scope = value["final"]["cgroup"]["scope"]
    nodes = {node["node_id"]: node for node in value["final"]["cgroup"]["subtree"]}
    root_id = scope["child_path_sha256"]
    nested_id = hashlib.sha256(str(nested).encode("utf-8")).hexdigest()
    leaf_id = hashlib.sha256(str(leaf).encode("utf-8")).hexdigest()
    assert nodes[root_id]["parent_id"] is None
    assert nodes[root_id]["id"] == scope["child_id"]
    assert nodes[nested_id]["parent_id"] == root_id
    assert nodes[leaf_id]["parent_id"] == nested_id
    assert all(
        set(node) == {"node_id", "parent_id", "id", "populated", "pids"} for node in nodes.values()
    )


@pytest.mark.parametrize(
    "location", ["allocation_path_sha256", "child_path_sha256", "node_id", "parent_id"]
)
def test_credential_markers_in_scope_or_node_fields_are_rejected(observed, location):
    value = receipt(observed[0])
    final = value["final"]["cgroup"]
    target = final["scope"] if location.endswith("sha256") else final["subtree"][0]
    target[location] = "sk-credential-marker"
    with pytest.raises(ValueError) as error:
        resources.verify_sampling(value, IDENTITY)
    assert "sk-credential-marker" not in str(error.value)


@pytest.mark.parametrize(
    "case", ["orphan", "cycle", "root_parent", "duplicate", "missing_root", "root_inode"]
)
def test_node_topology_requires_connected_unique_root(observed, case):
    observer, child, _ = observed
    group(child / "nested")
    group(child / "nested" / "leaf")
    value = receipt(observer)
    final = value["final"]["cgroup"]
    root_id = final["scope"]["child_path_sha256"]
    root = next(g for g in final["subtree"] if g["node_id"] == root_id)
    nested = next(g for g in final["subtree"] if g["parent_id"] == root_id)
    leaf = next(g for g in final["subtree"] if g["parent_id"] == nested["node_id"])
    if case == "orphan":
        leaf["parent_id"] = "b" * 64
    elif case == "cycle":
        nested["parent_id"] = leaf["node_id"]
    elif case == "root_parent":
        root["parent_id"] = leaf["node_id"]
    elif case == "duplicate":
        final["subtree"].append(copy.deepcopy(nested))
    elif case == "missing_root":
        final["subtree"].remove(root)
    else:
        root["id"][1] += 1
    with pytest.raises(ValueError):
        resources.verify_sampling(value, IDENTITY)


def test_callback_and_os_exception_payloads_never_enter_receipts(observed, monkeypatch):
    credential = "Authorization: Bearer sk-secret C:/private/passwords.txt"

    def fail():
        raise OSError(credential)

    recorder = resources.ResourceSampler(fail, fail, identity=IDENTITY, clock=lambda: 1.0)
    recorder.sample()
    value = recorder.finish()
    assert value["final"]["errors"] == ["phase_read_failed", "probe_read_failed"]
    assert credential not in json.dumps(value) and "sk-secret" not in json.dumps(value)
    observer, _, _ = observed
    original = resources._Directory.read

    def failed_read(directory, name):
        if name in ("cpu.stat", "cgroup.procs"):
            raise OSError(credential)
        return original(directory, name)

    monkeypatch.setattr(resources._Directory, "read", failed_read)
    observation = observer.read()
    assert observation["errors"] == ["cpu_usage_usec_invalid", "scope_read_failed"]
    assert credential not in json.dumps(observation) and "sk-secret" not in json.dumps(observation)


def test_collector_rejects_malformed_probe_errors_without_echo(observed):
    observation = observed[0].read()
    observation["errors"] = ["Authorization: Bearer sk-secret"]
    recorder = resources.ResourceSampler(
        lambda: {"cgroup": observation, "process_tree": None},
        lambda: "cleanup",
        identity=IDENTITY,
        clock=lambda: 1.0,
    )
    recorder.sample()
    value = recorder.finish()
    assert value["final"]["cgroup"] is None
    assert value["final"]["errors"] == ["probe_read_failed"]
    assert "sk-secret" not in json.dumps(value)


def test_synthetic_evidence_never_qualifies_containment(observed):
    value = receipt(observed[0])
    summary = resources.verify_sampling(value, IDENTITY)
    assert summary["sampling_valid"] and summary["synthetic_observation"]
    assert not summary["containment_closed"] and not summary["production_admitted"]
    assert not summary["allocation_tree_closed"]
    # Pure replay branch coverage; toggling fixture receipts is not live qualification.
    live_shaped = copy.deepcopy(value)
    for record in [*live_shaped["samples"], live_shaped["final"]]:
        record["cgroup"]["scope"]["test_only"] = False
    summary = resources.verify_sampling(live_shaped, IDENTITY)
    assert not summary["synthetic_observation"] and summary["containment_closed"]
    assert not summary["production_admitted"] and not summary["allocation_tree_closed"]
    live_shaped["samples"][0]["cgroup"]["scope"]["test_only"] = True
    summary = resources.verify_sampling(live_shaped, IDENTITY)
    assert summary["synthetic_observation"] and not summary["containment_closed"]


@pytest.mark.skipif(
    sys.platform != "linux", reason="Linux read-only current-process proc qualification"
)
def test_current_process_starttime_read_only():
    first = resources._starttime(Path("/proc"), os.getpid())
    assert first > 0 and resources._starttime(Path("/proc"), os.getpid()) == first
