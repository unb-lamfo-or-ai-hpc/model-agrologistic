"""Offline resource-contract integration; no Slurm, process or solver execution."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import mvp2_s2_batch_adapter as legacy_adapter
from scripts import mvp2_s2_synthetic_resources as p


def maps(role):
    return {
        key: {"mount": "/cg/" + key, "scope": "/cg/" + key + "/job/" + role}
        for key in p.s.CONTROLLERS
    }


def contract():
    inventory = json.loads(Path("docs/mvp2_s2_slurm_site_inventory.json").read_text())
    binding = {
        "job_id": "123",
        "worker_step_id": "0",
        "supervisor_step_id": "batch",
        "nonce": "a" * 64,
        "source_commit": "b" * 40,
    }
    return p.contract(p.q.contract(inventory, binding, "normal", "c" * 64, "d" * 64))


def snapshot(scopes, inode, memory_mib):
    return {
        "schema_version": "s2-cgroup-v1-observation-v1",
        "synthetic_observation": True,
        "status": "observed_not_qualified",
        "errors": [],
        "scopes": {
            k: {"path_sha256": p.s.digest(v["scope"]), "inode": [1, inode]}
            for k, v in scopes.items()
        },
        "counters": {
            "memory_usage_bytes": 10,
            "memory_max_usage_bytes": 20,
            "memory_limit_bytes": 2**63 - 4096,
            "memory_failcnt": 0,
            "cpu_usage_ns": 100,
            "cpuset_cpu_count": 2,
            "effective_reported_memory_limit_bytes": memory_mib * 1024**2,
            "freezer_group_count": 1,
            "freezer_unique_process_count": 1,
        },
        **p.s.FLAGS,
    }


def inputs():
    w, sup = maps("worker"), maps("batch")
    w["cpuacct"] = copy.deepcopy(sup["cpuacct"])
    ws, ss = snapshot(w, 20, 256), snapshot(sup, 10, 2048)
    ws["scopes"]["cpuacct"]["inode"] = [1, 10]
    return dict(
        worker_scopes=w,
        supervisor_scopes=sup,
        allocation_cpuset={"mount": "/cg/cpuset", "scope": "/cg/cpuset/job"},
        worker_snapshot=ws,
        supervisor_snapshot=ss,
        worker_cpus=[0, 32],
        allocation_cpus=[0, 32],
        initial_affinity=[0],
        identities_sha256="e" * 64,
    )


def observed():
    return p.observe(contract(), **inputs())


def test_end_to_end_resource_gate_export_replay_and_no_admission():
    item = contract()
    first = p.observe(item, **inputs())
    second = copy.deepcopy(first)
    second["cpuacct_scope_usage_ns"] += 1
    gate = p.ResourceGate(item)
    report = gate.bind(first, second)
    assert report["status"] == "resource_checks_passed_not_live_qualified"
    assert first["worker_cpu_usage_ns"] is None
    assert all(report[k] is False for k in p.FLAGS)
    portable = json.loads(json.dumps(second))
    assert gate.sample(portable)["worker_cpu_usage_ns"] is None
    assert "/cg/" not in json.dumps(portable)
    second["worker_cpus"].append(99)
    assert gate.previous["worker_cpus"] == [0, 32]


def test_profile_is_exactly_legacy_except_explicit_resource_policy():
    item = contract()
    assert item["legacy_contract"]["profile"] == p.q.PROFILE
    assert item["resource_policy"]["worker_cpuset_max_logical_cpus"] == 2
    assert item["legacy_contract"]["profile"]["worker_cpus"] == 1
    assert item["legacy_contract"]["profile"]["allocation_wall_seconds"] == 720


@pytest.mark.parametrize("key", p.FLAGS)
def test_neither_contract_nor_observation_can_admit(key):
    item, value = contract(), observed()
    item[key] = True
    with pytest.raises(ValueError):
        p.validate_contract(item)
    value[key] = True
    with pytest.raises(ValueError):
        p.validate_observation(value, contract())


@pytest.mark.parametrize(
    "field,value",
    [
        ("worker_cpus", [0, 32, 33]),
        ("worker_cpus", []),
        ("worker_cpus", [0, 1]),
        ("worker_cpus", [0, 0]),
        ("worker_cpus", [False, 32]),
        ("worker_cpus", [32, 0]),
        ("allocation_cpus", [0]),
        ("allocation_cpus", [0, 32, 64]),
        ("initial_affinity", [0, 32]),
        ("initial_affinity", [1]),
    ],
)
def test_membership_not_just_cardinality(field, value):
    args = inputs()
    args[field] = value
    with pytest.raises(ValueError):
        p.observe(contract(), **args)


def test_one_cpu_subset_is_allowed_and_not_exclusive():
    args = inputs()
    args["worker_cpus"] = [0]
    args["worker_snapshot"]["counters"]["cpuset_cpu_count"] = 1
    value = p.observe(contract(), **args)
    assert value["exclusive_cpu_placement_proven"] is False


@pytest.mark.parametrize("controller", ["memory", "freezer", "cpuset"])
@pytest.mark.parametrize("relation", ["equal", "parent", "child", "alias"])
def test_enforcement_separation_never_relaxed(controller, relation):
    args = inputs()
    if relation == "alias":
        args["worker_snapshot"]["scopes"][controller]["inode"] = [1, 10]
    else:
        outside = args["supervisor_scopes"][controller]["scope"]
        path = (
            outside
            if relation == "equal"
            else (
                str(Path(outside).parent).replace("\\", "/")
                if relation == "parent"
                else outside + "/child"
            )
        )
        args["worker_scopes"][controller]["scope"] = path
        args["worker_snapshot"]["scopes"][controller]["path_sha256"] = p.s.digest(path)
    with pytest.raises(ValueError):
        p.observe(contract(), **args)


@pytest.mark.parametrize("scope", ["/cg/cpuset/other", "/cg/cpuset/job/worker"])
def test_allocation_parent_must_contain_both_roles(scope):
    args = inputs()
    args["allocation_cpuset"]["scope"] = scope
    with pytest.raises(ValueError):
        p.observe(contract(), **args)


@pytest.mark.parametrize("role,limit", [("worker", 257), ("supervisor", 2049)])
def test_memory_not_expanded(role, limit):
    args = inputs()
    args[role + "_snapshot"]["counters"]["effective_reported_memory_limit_bytes"] = limit * 1024**2
    with pytest.raises(ValueError):
        p.observe(contract(), **args)


@pytest.mark.parametrize("value", [0, 100, False])
def test_shared_cpu_usage_never_exported_as_worker_usage(value):
    obs = observed()
    obs["worker_cpu_usage_ns"] = value
    with pytest.raises(ValueError):
        p.validate_observation(obs, contract())


def test_disjoint_accounting_also_requires_independent_attribution():
    args = inputs()
    args["worker_scopes"]["cpuacct"] = maps("worker")["cpuacct"]
    args["worker_snapshot"]["scopes"]["cpuacct"] = {
        "path_sha256": p.s.digest(args["worker_scopes"]["cpuacct"]["scope"]),
        "inode": [1, 20],
    }
    obs = p.observe(contract(), **args)
    assert obs["cpuacct_relation"] == "disjoint" and obs["worker_cpu_usage_ns"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("worker_cpus", [0]),
        ("initial_affinity", [32]),
        ("identities_sha256", "f" * 64),
        ("scope_sha256", "f" * 64),
        ("worker_memory_limit_bytes", 128 * 1024**2),
        ("cpuacct_scope_usage_ns", 99),
        ("worker_memory_peak_bytes", 19),
    ],
)
def test_barrier_and_sampling_drift_fail_closed(field, value):
    obs, changed = observed(), observed()
    changed[field] = value
    with pytest.raises(ValueError):
        p.ResourceGate(contract()).bind(obs, changed)
    gate = p.ResourceGate(contract())
    gate.bind(obs, obs)
    with pytest.raises(ValueError):
        gate.sample(changed)


def test_legacy_gate_still_rejects_two_cpus_and_shared_accounting():
    args = inputs()
    with pytest.raises(ValueError):
        legacy_adapter.validate_snapshot(args["worker_snapshot"])
    with pytest.raises(ValueError):
        p.s.separated_scopes(args["worker_scopes"], args["supervisor_scopes"])
    with pytest.raises(ValueError):
        p.q.validate_contract(contract())


@pytest.mark.parametrize("text", ["", "0,0", "0-999999", "0-1,1", "secret", "-1"])
def test_cpu_parser_rejects_ambiguous_or_unbounded_input(text):
    with pytest.raises(ValueError):
        p.cpu_ids(text)


def test_saved_affinity_parser_and_missing_duplicate_rejection():
    assert p.affinity("Name:\tworker\nCpus_allowed_list:\t0\n") == [0]
    assert p.affinity("Cpus_allowed_list:\t0,32\n") == [0, 32]
    for raw in ("", "Cpus_allowed_list:\t0\nCpus_allowed_list:\t0\n"):
        with pytest.raises(ValueError):
            p.affinity(raw)


def test_execution_entry_denies_before_import_or_scheduler_lookup():
    proc = subprocess.run(
        [sys.executable, "-B", "-I", "scripts/mvp2_s2_synthetic_resources.py", "start"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "Resource qualification only; no execution admitted" in proc.stderr
    assert "ModuleNotFoundError" not in proc.stderr
