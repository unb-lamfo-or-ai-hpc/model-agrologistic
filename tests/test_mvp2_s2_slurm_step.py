"""Offline closed-gate qualification. No Slurm commands or solver imports."""

import copy
import json
from pathlib import Path

import pytest

from scripts import mvp2_s2_slurm_step as s


@pytest.fixture
def inventory():
    path = Path(__file__).resolve().parents[1] / "docs/mvp2_s2_slurm_site_inventory.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def step():
    return {
        "job_id": "500000",
        "worker_step_id": "0",
        "supervisor_step_id": "batch",
        "nonce": "a" * 64,
        "source_commit": "b" * 40,
    }


def assert_closed(item):
    assert all(item[key] is False for key in s.FLAGS)


def test_plan_closed_and_cleanup_budget(inventory, step):
    result = s.qualification_plan(inventory, step)
    assert_closed(result)
    assert result["launcher_implemented"] is False
    assert result["synthetic_execution_admitted"] is False
    profile = result["proposed_synthetic_profile"]
    assert profile["cleanup_observation_seconds"] == 390
    assert profile["allocation_wall_seconds"] > 30 + 60 + 390 + 60
    assert result["site_review"]["accounting_is_cgroup_lifetime_measurement"] is False
    assert result["term_proposal"]["argv"] == ["scancel", "--signal=TERM", "500000.0"]
    assert result["kill_proposal"]["argv"] == ["scancel", "--signal=KILL", "500000.0"]
    assert result["kill_proposal"]["execution_admitted"] is False


@pytest.mark.parametrize("flag", s.FLAGS)
def test_inventory_cannot_admit(inventory, flag):
    inventory[flag] = True
    with pytest.raises(ValueError):
        s.review_inventory(inventory)


@pytest.mark.parametrize("value", [1, "true", None, False])
def test_inventory_query_requires_true(inventory, value):
    inventory["config_query_succeeded"] = value
    with pytest.raises(ValueError):
        s.review_inventory(inventory)


@pytest.mark.parametrize(
    "key,value",
    [
        ("JobAcctGatherType", "jobacct_gather/cgroup"),
        ("ProctrackType", "proctrack/linux"),
        ("SelectType", "select/linear"),
        ("SelectTypeParameters", "CR_CPU"),
        ("TaskPlugin", "task/affinity"),
        ("TaskPlugin", "task/cgroup,task/cgroup,task/affinity"),
        ("TaskPluginParam", "cores"),
        ("KillWait", "30 sec"),
        ("UnkillableStepTimeout", "600 sec"),
    ],
)
def test_site_drift_is_not_automatic_promotion(inventory, key, value):
    inventory["declared_configuration"][key] = value
    with pytest.raises(ValueError):
        s.review_inventory(inventory)


@pytest.mark.parametrize("field", ["scontrol_client_version", "srun_client_version"])
def test_version_drift(inventory, field):
    inventory[field] = "slurm 25.05.1"
    with pytest.raises(ValueError):
        s.review_inventory(inventory)


@pytest.mark.parametrize("value", ["300", "300 seconds", "-1 sec", "1.5 sec", "99999 sec", None])
def test_unknown_cleanup_duration(value):
    with pytest.raises(ValueError):
        s.seconds(value)


@pytest.mark.parametrize(
    "key,value",
    [
        ("job_id", "0"),
        ("job_id", "0500000"),
        ("job_id", "500000_1"),
        ("job_id", "500000+1"),
        ("job_id", "--me"),
        ("worker_step_id", "batch"),
        ("worker_step_id", "extern"),
        ("worker_step_id", "01"),
        ("worker_step_id", "-1"),
        ("worker_step_id", "0;echo"),
        ("supervisor_step_id", "0"),
        ("nonce", "a" * 63),
        ("source_commit", "develop"),
    ],
)
def test_target_rejects_broad_and_ambiguous_identity(step, key, value):
    step[key] = value
    with pytest.raises(ValueError):
        s.signal_descriptor(step, "KILL")


@pytest.mark.parametrize("value", ["STOP", "CONT", "USR1", "9", "--full"])
def test_signal_allowlist(step, value):
    with pytest.raises(ValueError):
        s.signal_descriptor(step, value)


def member_text(scope="/allocation/step0"):
    return "\n".join(f"{i}:{name}:{scope}" for i, name in enumerate(s.CONTROLLERS, 1))


def mount_text():
    return "\n".join(
        f"{i} 0 0:{i} / /sys/fs/cgroup/{name} rw - cgroup cgroup rw,{name}"
        for i, name in enumerate(s.CONTROLLERS, 1)
    )


def test_actual_mapping_not_slurm_path_guess():
    worker = s.mapped_scopes(member_text("/arbitrary/a"), mount_text())
    supervisor = s.mapped_scopes(member_text("/arbitrary/b"), mount_text())
    assert worker["memory"]["scope"] == "/sys/fs/cgroup/memory/arbitrary/a"
    separation = s.separated_scopes(worker, supervisor)
    assert separation["distinct_non_nested_scopes_observed"] is True
    assert separation["step_ownership_proven"] is False
    assert_closed(separation)


@pytest.mark.parametrize(
    "text",
    [
        "0::/job/step",
        member_text() + "\n0::/job/step",
        "1:memory:/job/step",
        member_text() + "\n8:memory:/elsewhere",
        member_text().replace("/allocation/step0", "/a/../b"),
        member_text().replace("/allocation/step0", "/a//b"),
        member_text().replace("/allocation/step0", "relative"),
    ],
)
def test_membership_fail_closed(text):
    with pytest.raises(ValueError):
        s.memberships(text)


def test_mounted_combined_cpu_controller():
    text = member_text().replace("2:cpuacct:", "2:cpu,cpuacct:")
    mounts = mount_text().replace("rw,cpuacct", "rw,cpu,cpuacct")
    assert s.mapped_scopes(text, mounts)["cpuacct"]["mount"].endswith("/cpuacct")


@pytest.mark.parametrize(
    "mounts",
    ["", mount_text() + "\n" + mount_text(), mount_text().replace(" / /sys", " /allocation /sys")],
)
def test_mounts_missing_duplicate_namespaced(mounts):
    with pytest.raises(ValueError):
        s.mapped_scopes(member_text(), mounts)


@pytest.mark.parametrize("scope", ["/allocation/step0", "/allocation/step0/child", "/allocation"])
def test_supervisor_must_be_outside(scope):
    with pytest.raises(ValueError):
        s.separated_scopes(
            s.mapped_scopes(member_text(), mount_text()),
            s.mapped_scopes(member_text(scope), mount_text()),
        )


@pytest.fixture
def scopes(tmp_path):
    result = {}
    for key in s.CONTROLLERS:
        mount = tmp_path / key
        scope = mount / "allocation" / "step"
        scope.mkdir(parents=True)
        result[key] = {"scope": str(scope), "mount": str(mount)}
    values = {
        "memory": {
            "memory.usage_in_bytes": "12345",
            "memory.max_usage_in_bytes": "34567",
            "memory.limit_in_bytes": "268435456",
            "memory.failcnt": "2",
            "memory.use_hierarchy": "1",
            "memory.stat": "cache 100\nhierarchical_memory_limit 134217728",
        },
        "cpuacct": {"cpuacct.usage": "1234567890"},
        "freezer": {"cgroup.procs": "123\n124"},
        "cpuset": {"cpuset.cpus": "2-3,5"},
    }
    for key, entries in values.items():
        for name, value in entries.items():
            (Path(result[key]["scope"]) / name).write_text(value, encoding="ascii")
    child = Path(result["freezer"]["scope"]) / "child"
    child.mkdir()
    (child / "cgroup.procs").write_text("125", encoding="ascii")
    return result


def test_v1_units_hierarchical_limit_and_nested_members(scopes):
    before = {
        p: p.read_bytes()
        for item in scopes.values()
        for p in Path(item["mount"]).rglob("*")
        if p.is_file()
    }
    got = s.read_v1_snapshot(scopes, test_only=True)
    assert got["status"] == "observed_not_qualified"
    assert got["synthetic_observation"] is True
    assert_closed(got)
    counters = got["counters"]
    assert counters["cpu_usage_ns"] == 1234567890
    assert counters["memory_usage_bytes"] == 12345
    assert counters["memory_failcnt"] == 2
    assert counters["effective_reported_memory_limit_bytes"] == 134217728
    assert counters["freezer_unique_process_count"] == 3
    assert counters["freezer_group_count"] == 2
    assert counters["cpuset_cpu_count"] == 3
    assert "oom" not in counters and "rss" not in counters and "core_hours" not in counters
    assert all(p.read_bytes() == value for p, value in before.items())
    text = json.dumps(got)
    assert scopes["memory"]["scope"] not in text
    assert "cgroup.procs" not in text


@pytest.mark.parametrize(
    "controller,name,value",
    [
        ("memory", "memory.use_hierarchy", "0"),
        ("memory", "memory.limit_in_bytes", "0"),
        ("memory", "memory.stat", "hierarchical_memory_limit 9223372036854771712"),
        ("memory", "memory.stat", "hierarchical_memory_limit 1\nhierarchical_memory_limit 2"),
        ("cpuacct", "cpuacct.usage", "-1"),
        ("cpuacct", "cpuacct.usage", str(2**64)),
        ("freezer", "cgroup.procs", "123\n123"),
        ("freezer", "cgroup.procs", "0"),
        ("cpuset", "cpuset.cpus", "0-2,2-4"),
        ("cpuset", "cpuset.cpus", "0-99999999"),
    ],
)
def test_invalid_resources_do_not_promote(scopes, controller, name, value):
    (Path(scopes[controller]["scope"]) / name).write_text(value, encoding="ascii")
    result = s.read_v1_snapshot(scopes, test_only=True)
    assert result["status"] == "blocked_observation"
    assert result["counters"] is None
    assert result["errors"] == ["scope_or_counter_invalid"]
    assert_closed(result)


def test_nested_group_bound(scopes):
    assert (
        s.read_v1_snapshot(scopes, test_only=True, max_groups=1)["status"] == "blocked_observation"
    )


def test_duplicate_cross_group_member(scopes):
    (Path(scopes["freezer"]["scope"]) / "child/cgroup.procs").write_text("123", encoding="ascii")
    assert s.read_v1_snapshot(scopes, test_only=True)["status"] == "blocked_observation"


def test_missing_scope_is_not_cleanup_success(scopes):
    altered = copy.deepcopy(scopes)
    altered["freezer"]["scope"] += "/absent"
    got = s.read_v1_snapshot(altered, test_only=True)
    assert got["status"] == "blocked_observation"
    assert_closed(got)


def test_empty_membership_is_not_isolation_proof(scopes):
    for path in Path(scopes["freezer"]["scope"]).rglob("cgroup.procs"):
        path.write_text("", encoding="ascii")
    got = s.read_v1_snapshot(scopes, test_only=True)
    assert got["counters"]["freezer_unique_process_count"] == 0
    assert_closed(got)


def test_replacement_and_limit_drift_are_blocked(scopes, monkeypatch):
    real_read = s.r._Directory.read
    calls = 0

    def drift(directory, name):
        nonlocal calls
        if name == "memory.limit_in_bytes":
            calls += 1
            if calls > 1:
                return "1"
        return real_read(directory, name)

    monkeypatch.setattr(s.r._Directory, "read", drift)
    assert s.read_v1_snapshot(scopes, test_only=True)["status"] == "blocked_observation"


def test_noncanonical_roots_blocked(scopes):
    scopes["memory"]["scope"] = scopes["memory"]["mount"]
    with pytest.raises(ValueError):
        s.read_v1_snapshot(scopes, test_only=True)


@pytest.mark.parametrize("signal", [[], {}, 1, None])
def test_signal_type_rejected(step, signal):
    with pytest.raises(ValueError):
        s.signal_descriptor(step, signal)


@pytest.mark.parametrize("scope", ["//a/b", "/a/../b", "/a//b", "relative", "/a/./b"])
def test_noncanonical_live_scope(scope):
    with pytest.raises(ValueError):
        s._validate_scope({"scope": scope, "mount": "/a"})


def test_no_scheduler_or_native_entrypoint():
    import ast

    tree = ast.parse(Path(s.__file__).read_text(encoding="utf-8"))
    imports = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
    assert imports <= {"hashlib", "json", "os", "re", "sys"}
    forbidden = {"Popen", "run", "system", "exec", "eval", "kill", "write_text", "write_bytes"}
    calls = {
        getattr(node.func, "attr", getattr(node.func, "id", ""))
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert not calls & forbidden


@pytest.mark.skipif(s.sys.platform != "linux", reason="Linux no-follow resource fixture")
def test_symlink_counter_blocked(scopes):
    path = Path(scopes["cpuacct"]["scope"]) / "cpuacct.usage"
    path.unlink()
    path.symlink_to(Path(scopes["memory"]["scope"]) / "memory.failcnt")
    assert s.read_v1_snapshot(scopes, test_only=True)["status"] == "blocked_observation"
