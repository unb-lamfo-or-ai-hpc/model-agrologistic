"""Offline lifecycle protocol, bounded local primitives and forensic replay only."""

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import mvp2_s2_lifecycle_package as package
from tests import test_mvp2_s2_synthetic_resources as f

lc, o = package.lc, package.o
H = "e" * 64


def process(pid):
    return {"pid": pid, "uid": 1000, "starttime": 100 * pid, "state": "S"}


def fixtures(case="normal"):
    resource = f.contract()
    resource["legacy_contract"]["case"] = case
    item = lc.contract(resource)
    value = f.observed()
    value["contract_sha256"] = lc.s.digest(resource)
    value["identities_sha256"] = lc.s.digest([lc.stable(process(20)), lc.stable(process(10))])
    bound = {
        "binding": copy.deepcopy(resource["legacy_contract"]["binding"]),
        "worker": process(20),
        "supervisor": process(10),
        "resource_scope_sha256": value["scope_sha256"],
        "controllers": {},
        "owned_batch": [],
    }
    for key in lc.CONTROLLERS:
        bound["controllers"][key] = {
            "mount": "/cg/" + key,
            "parent": "/cg/" + key + "/job",
            "worker": "/cg/" + key + "/job/worker",
            "supervisor": "/cg/" + key + "/job/batch",
            "mount_id": 50,
            "mount_identity": [1, 1],
            "parent_identity": [1, 2],
            "worker_identity": [1, 20],
            "supervisor_identity": [1, 10],
        }
    bound["assurance"] = {
        "binding_sha256": lc.s.digest(bound["binding"]),
        "boundary_sha256": lc.s.digest(bound),
        "checks": {
            key: {"status": "checked_not_attested", "evidence_sha256": H} for key in lc.ASSURANCES
        },
    }
    initial = {"inventories": inventory(bound, alive=True), "resources": value}
    return item, bound, initial


def inventory(bound, *, alive):
    result = {}
    for key, descriptor in bound["controllers"].items():
        groups = [
            {"relative": "", "identity": [1, 2], "members": []},
            {"relative": "batch", "identity": [1, 10], "members": [process(10)]},
        ]
        if alive:
            groups.append({"relative": "worker", "identity": [1, 20], "members": [process(20)]})
        result[key] = {
            k: copy.deepcopy(descriptor[k])
            for k in ("mount_id", "mount_identity", "parent_identity")
        }
        result[key]["groups"] = groups
    return result


def products(case="normal"):
    count = {
        "build_failure": 1,
        "optimization_failure": 2,
        "export_failure": 3,
        "disposal_failure": 4,
    }.get(case, 4)
    result = {
        f"phase-{i}.json": {"nonce": "a" * 64, "phase": name}
        for i, name in enumerate(("build", "optimization", "export", "disposal"))
        if i < count
    }
    if case.endswith("_failure"):
        result["failure.json"] = {"nonce": "a" * 64, "status": "synthetic_phase_failure"}
    else:
        result["terminal.json"] = {"nonce": "a" * 64, "status": "synthetic_complete"}
    return result


def sample(protocol, *, alive=False):
    case = protocol.item["resource_contract"]["legacy_contract"]["case"]
    files = products(case)
    writes = dict.fromkeys(lc.WRITE_FILES)
    writes.update({"worker/" + name: lc.s.digest(value) for name, value in files.items()})
    return {
        "inventories": inventory(protocol.bound, alive=alive),
        "resources": copy.deepcopy(protocol.resource.previous) if alive else None,
        "step_scopes": dict.fromkeys(lc.CONTROLLERS, "available" if alive else "missing"),
        "accounting": {"job_step": "123.0", "state": "COMPLETED", "exit_code": "0:0"},
        "absence": {lc.s.digest(v): "absent" for v in protocol.known.values()},
        "launcher_reaped": not alive,
        "products": files,
        "writes": writes,
        "assurance_sha256": lc.s.digest(protocol.bound["assurance"]),
    }


def running(case="normal"):
    item, bound, first = fixtures(case)
    result = lc.Protocol(item)
    result.bind(1, bound, first, copy.deepcopy(first))
    return result


def cleanup(case="normal"):
    result = running(case)
    result.sample(2, sample(result, alive=True))
    result.end(3)
    return result


@pytest.mark.parametrize("case", lc.q.CASES)
def test_complete_software_path_all_cases_is_not_admission(case):
    protocol = cleanup(case)
    for now in range(4, 10):
        result = protocol.sample(now, sample(protocol))
    assert result["state"] == "software_candidate_closed"
    assert lc.replay(protocol.item, json.loads(json.dumps(protocol.journal))) == result
    assert all(result[k] is False for k in lc.FLAGS)
    assert result["environment_attested"] is False and result["installed_cleanup_proven"] is False
    assert protocol.item["resource_contract"]["legacy_contract"]["profile"] == lc.q.PROFILE


@pytest.mark.parametrize("key", lc.FLAGS)
def test_all_admission_and_cleanup_flags_remain_false(key):
    item, _, _ = fixtures()
    item[key] = True
    with pytest.raises(ValueError):
        lc.Protocol(item)


@pytest.mark.parametrize("key", lc.ASSURANCES)
def test_no_environment_assurance_is_optional(key):
    item, bound, first = fixtures()
    bound["assurance"]["checks"][key]["status"] = "unknown"
    protocol = lc.Protocol(item)
    with pytest.raises(ValueError, match="assurance"):
        protocol.bind(1, bound, first, first)
    assert protocol.bound is None and protocol.state == "startup"


@pytest.mark.parametrize(
    "mutation",
    [
        "source",
        "resource_scope",
        "nonce",
        "aliased",
        "ancestry",
        "mount",
        "assurance",
        "extra_member",
        "role_location",
        "pid_reuse",
        "initial_missing",
        "resource_identity",
    ],
)
def test_initial_boundary_and_resource_drift_blocks(mutation):
    item, bound, first = fixtures()
    if mutation in {"source", "nonce"}:
        bound["binding"]["source_commit" if mutation == "source" else "nonce"] = "f" * (
            40 if mutation == "source" else 64
        )
    elif mutation == "resource_scope":
        first["resources"]["scope_sha256"] = "f" * 64
    elif mutation == "aliased":
        bound["controllers"]["freezer"]["parent_identity"] = [1, 20]
    elif mutation == "ancestry":
        bound["controllers"]["cpuset"]["worker"] = "/elsewhere"
    elif mutation == "mount":
        first["inventories"]["memory"]["mount_id"] += 1
    elif mutation == "assurance":
        bound["assurance"]["boundary_sha256"] = "f" * 64
    elif mutation == "extra_member":
        first["inventories"]["memory"]["groups"][0]["members"] = [process(99)]
    elif mutation == "role_location":
        for value in first["inventories"].values():
            value["groups"][0]["members"] = value["groups"][2]["members"]
            value["groups"][2]["members"] = []
    elif mutation == "pid_reuse":
        first["inventories"]["memory"]["groups"][2]["members"][0]["starttime"] += 1
    elif mutation == "initial_missing":
        first["inventories"]["memory"]["groups"].pop()
    else:
        first["resources"]["identities_sha256"] = "f" * 64
    with pytest.raises(ValueError):
        lc.Protocol(item).bind(1, bound, first, first)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_parent",
        "replaced_parent",
        "mount_replaced",
        "unknown_member",
        "reused_supervisor",
        "supervisor_gone",
        "role_replaced",
        "controller_disagreement",
        "incomplete_absence",
        "absence_unknown",
        "leader_only",
        "step_wrong",
        "step_running",
        "empty_products",
        "late_product_nonce",
        "assurance",
        "query_process",
        "synthesized_resources",
        "migration",
        "late_write",
    ],
)
def test_post_exit_unknowns_never_become_clean(mutation):
    protocol = cleanup()
    packet = sample(protocol)
    if mutation == "missing_parent":
        packet["inventories"] = None
    elif mutation == "replaced_parent":
        packet["inventories"]["memory"]["parent_identity"] = [1, 99]
    elif mutation == "mount_replaced":
        packet["inventories"]["cpuset"]["mount_identity"] = [1, 99]
    elif mutation in {"unknown_member", "query_process", "migration", "reused_supervisor"}:
        for tree in packet["inventories"].values():
            if mutation == "reused_supervisor":
                tree["groups"][1]["members"][0]["starttime"] += 1
            else:
                tree["groups"][0]["members"].append(process(20 if mutation == "migration" else 99))
    elif mutation == "supervisor_gone":
        for tree in packet["inventories"].values():
            tree["groups"][1]["members"] = []
    elif mutation == "role_replaced":
        packet["inventories"]["memory"]["groups"].append(
            {"relative": "worker", "identity": [1, 99], "members": []}
        )
    elif mutation == "controller_disagreement":
        packet["inventories"]["memory"]["groups"][0]["members"] = [process(20)]
    elif mutation == "incomplete_absence":
        packet["absence"] = {}
    elif mutation in {"absence_unknown", "leader_only"}:
        packet["absence"][next(iter(packet["absence"]))] = (
            "unavailable" if mutation == "absence_unknown" else "present"
        )
    elif mutation == "step_wrong":
        packet["accounting"]["job_step"] = "123.1"
    elif mutation == "step_running":
        packet["accounting"]["state"] = "RUNNING"
    elif mutation == "empty_products":
        packet["products"] = {}
    elif mutation in {"late_product_nonce", "late_write"}:
        packet["products"]["terminal.json"]["nonce"] = "f" * 64
    elif mutation == "assurance":
        packet["assurance_sha256"] = "f" * 64
    else:
        packet["resources"] = protocol.resource.previous
    result = protocol.sample(4, packet)
    assert result["state"] != "software_candidate_closed" and result["cleanup_accepted"] is False
    assert lc.replay(protocol.item, protocol.journal) == result


def test_nested_descendants_outlive_leader_and_require_all_absence():
    protocol = running("nested_setsid_term_ignore")
    protocol.register(1.1, process(21), process(20), H)
    protocol.register(1.2, process(22), process(21), H)
    packet = sample(protocol, alive=True)
    for tree in packet["inventories"].values():
        tree["groups"].append(
            {
                "relative": "worker/detached",
                "identity": [1, 21],
                "members": [process(21), process(22)],
            }
        )
    protocol.sample(2, packet)
    protocol.end(3)
    for now in range(4, 10):
        packet = sample(protocol)
        packet["absence"][lc.token(process(22))] = "present"
        assert protocol.sample(now, packet)["state"] == "cleanup"
    for now in range(10, 16):
        result = protocol.sample(now, sample(protocol))
    assert result["state"] == "software_candidate_closed"


@pytest.mark.parametrize("mutation", ["foreign_parent", "reuse", "supervisor", "uid"])
def test_registration_never_uses_uid_or_process_group_as_ownership(mutation):
    protocol = running()
    child, parent = process(21), process(20)
    if mutation == "foreign_parent":
        parent = process(99)
    elif mutation == "reuse":
        child = process(20)
    elif mutation == "supervisor":
        child = process(10)
    else:
        child["uid"] += 1
    with pytest.raises(ValueError):
        protocol.register(1.1, child, parent, H)


def test_quiet_interval_requires_five_seconds_and_three_or_more_samples():
    protocol = cleanup()
    for now in (4, 5, 6, 7, 8):
        assert protocol.sample(now, sample(protocol))["state"] == "cleanup"
    assert protocol.sample(9, sample(protocol))["state"] == "software_candidate_closed"
    with pytest.raises(ValueError):
        protocol.sample(10, sample(protocol))


def test_product_disappearance_resets_quiet_then_requires_fresh_interval():
    protocol = cleanup()
    for now in (4, 5, 6):
        protocol.sample(now, sample(protocol))
    packet = sample(protocol)
    packet["products"] = {}
    packet["writes"] = dict.fromkeys(lc.WRITE_FILES)
    protocol.sample(7, packet)
    for now in range(8, 13):
        assert protocol.sample(now, sample(protocol))["state"] == "cleanup"
    assert protocol.sample(13, sample(protocol))["state"] == "software_candidate_closed"


@pytest.mark.parametrize("now", [3, 2, 9, 393, 660])
def test_clock_gap_rollback_and_deadline_block_before_acceptance(now):
    protocol = cleanup()
    assert protocol.sample(now, sample(protocol))["state"] == "blocked"
    with pytest.raises(ValueError):
        protocol.sample(now + 1, sample(protocol))


@pytest.mark.parametrize(
    "key", ["worker_cpus", "worker_memory_limit_bytes", "scope_sha256", "worker_memory_failcnt"]
)
def test_live_enforcement_drift_blocks(key):
    protocol = running()
    packet = sample(protocol, alive=True)
    packet["resources"][key] = {
        "worker_cpus": [99],
        "worker_memory_limit_bytes": 2**63,
        "scope_sha256": "f" * 64,
        "worker_memory_failcnt": -1,
    }[key]
    assert protocol.sample(2, packet)["state"] == "blocked"


def test_independent_capture_preserves_other_channels_without_empty_substitution():
    adapter = package.QualificationAdapter(fixtures()[0])
    item, bound, first = fixtures()
    adapter.protocol.bind(1, bound, first, first)
    packet = sample(adapter.protocol, alive=True)
    readers = {k: (lambda value=value: value) for k, value in packet.items()}

    def failed():
        raise FileNotFoundError("private path must never be exported")

    readers["inventories"] = failed
    result = adapter.observe(2, readers)
    assert result["state"] == "blocked"
    assert adapter.channels[0]["inventories"]["value"] is None
    assert adapter.channels[0]["products"]["status"] == "available"
    assert "private path" not in json.dumps(adapter.channels)


def test_late_heartbeat_writes_restart_full_quiet_interval():
    protocol = cleanup()
    for now in (4, 5, 6):
        protocol.sample(now, sample(protocol))
    for now in range(7, 12):
        packet = sample(protocol)
        packet["writes"]["heartbeat.pending"] = H
        assert protocol.sample(now, packet)["state"] == "cleanup"
    assert protocol.sample(12, packet)["state"] == "software_candidate_closed"


def test_identity_bound_batch_roles_not_broad_uid_exclusions():
    item, bound, first = fixtures()
    bound["owned_batch"] = [
        {"role": role, "process": process(pid), "ownership_evidence_sha256": H}
        for role, pid in (("batch_shell", 11), ("local_srun_client", 12))
    ]
    bound["assurance"]["boundary_sha256"] = lc.s.digest(
        {k: v for k, v in bound.items() if k != "assurance"}
    )
    for tree in first["inventories"].values():
        tree["groups"][1]["members"].extend([process(11), process(12)])
    protocol = lc.Protocol(item)
    protocol.bind(1, bound, first, first)
    protocol.end(2)
    for now in range(3, 9):
        packet = sample(protocol)
        for tree in packet["inventories"].values():
            tree["groups"][1]["members"].extend([process(11), process(12)])
        assert protocol.sample(now, packet)["state"] == "cleanup"
    for now in range(9, 15):
        packet = sample(protocol)
        for tree in packet["inventories"].values():
            tree["groups"][1]["members"].append(process(11))
        result = protocol.sample(now, packet)
    assert result["state"] == "software_candidate_closed"


def test_registration_events_cannot_mask_a_resource_sampling_gap():
    protocol = running()
    for now, pid in ((2, 21), (4, 22), (6, 23)):
        protocol.register(now, process(pid), process(20), H)
    assert protocol.sample(7, sample(protocol, alive=True))["state"] == "blocked"


@pytest.mark.parametrize("role", ["worker", "supervisor"])
def test_zombie_initial_roles_cannot_pass_the_software_barrier(role):
    item, bound, first = fixtures()
    bound[role]["state"] = "Z"
    with pytest.raises(ValueError, match="initial role"):
        lc.Protocol(item).bind(1, bound, first, first)


def test_terminal_accounting_disagreement_is_retained_as_rejected_forensics():
    protocol = cleanup()
    packet = sample(protocol)
    packet["accounting"]["state"] = "FAILED"
    packet["accounting"]["exit_code"] = "2:0"
    protocol.sample(4, packet)
    result = collected(protocol)
    assert result["disposition"] == "rejected_journal" and result["software_review"] is None


def test_cleanup_deadline_wins_even_with_regular_negative_observations():
    protocol = cleanup()
    for now in range(4, 393):
        packet = sample(protocol)
        packet["absence"][lc.token(process(20))] = "present"
        assert protocol.sample(now, packet)["state"] == "cleanup"
    assert protocol.sample(393, sample(protocol))["state"] == "blocked"


def collected(protocol, journal=None, **changes):
    journal = protocol.journal if journal is None else journal
    args = {
        "source_commit": "b" * 40,
        "job_id": "123",
        "contract_sha256": lc.s.digest(protocol.item),
        "expected_journal_sha256": lc.s.digest(journal),
    }
    args.update(changes)
    return package.collect(
        protocol.item,
        journal,
        "123|COMPLETED|0:0|14\n123.batch|COMPLETED|0:0|14\n123.0|COMPLETED|0:0|1",
        **args,
    )


def test_terminal_replay_redacts_private_paths_and_process_identities():
    protocol = cleanup()
    before = copy.deepcopy(protocol.journal)
    result = collected(protocol)
    assert result["disposition"] == "software_replayed_not_live_qualified"
    assert result["software_review"]["state"] == "cleanup"
    assert protocol.journal == before and all(result[k] is False for k in lc.FLAGS)
    assert not any(text in json.dumps(result) for text in ("/cg/", '"pid"', '"uid"', '"starttime"'))
    assert not any(
        result["readiness"][key]
        for key in ("live_adapter_implemented", "operational_claim_reserved")
    )


@pytest.mark.parametrize(
    "key,value", [("job_id", "321"), ("source_commit", "f" * 40), ("contract_sha256", "f" * 64)]
)
def test_external_collection_drift_rejected(key, value):
    with pytest.raises(ValueError):
        collected(cleanup(), **{key: value})


def test_missing_and_corrupt_journals_are_forensic_only():
    protocol = cleanup()
    result = package.collect(
        protocol.item,
        None,
        "123|FAILED|2:0|1\n123.batch|FAILED|2:0|1\n123.0|FAILED|2:0|1",
        source_commit="b" * 40,
        job_id="123",
        contract_sha256=lc.s.digest(protocol.item),
        expected_journal_sha256=H,
    )
    assert result["disposition"] == "missing_journal" and result["software_review"] is None
    journal = copy.deepcopy(protocol.journal)
    journal[-1]["previous_sha256"] = "f" * 64
    assert collected(protocol, journal)["disposition"] == "rejected_journal"
    assert (
        collected(protocol, expected_journal_sha256="f" * 64)["disposition"] == "rejected_journal"
    )


def test_terminal_collection_cannot_invent_missing_numeric_step():
    protocol = cleanup()
    with pytest.raises(ValueError, match="Terminal"):
        package.collect(
            protocol.item,
            protocol.journal,
            "123|COMPLETED|0:0|1\n123.batch|COMPLETED|0:0|1",
            source_commit="b" * 40,
            job_id="123",
            contract_sha256=lc.s.digest(protocol.item),
            expected_journal_sha256=lc.s.digest(protocol.journal),
        )


@pytest.mark.parametrize("module", [lc, o, package])
@pytest.mark.parametrize(
    "action", ["start", "collect", "normal", "adverse", "native", "h300", "retry"]
)
def test_every_public_entry_denies_before_io(module, action, tmp_path):
    result = subprocess.run(
        [sys.executable, "-B", "-I", str(Path(module.__file__).resolve()), action],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0 and "PermissionError" in result.stderr
    assert list(tmp_path.iterdir()) == []


def write_group(path, pids):
    path.mkdir(parents=True)
    (path / "cgroup.procs").write_text("\n".join(map(str, pids)), encoding="ascii")


def test_local_recursive_reader_deduplicates_kernel_tgids_without_aliasing(tmp_path):
    root = tmp_path / "tree"
    write_group(root, [20, 20, 10])
    write_group(root / "child", [21])
    records = o.read_tree(root, process)
    assert [v["pid"] for v in records[0]["members"]] == [10, 20]
    assert records[1]["relative"] == "child"


@pytest.mark.parametrize(
    "mutation", ["missing", "moving", "pid_drift", "group_bound", "depth_bound", "reuse"]
)
def test_local_reader_missing_races_and_bounds_never_return_empty(tmp_path, mutation):
    root = tmp_path / "tree"
    write_group(root, [20])
    resolver, kwargs = process, {}
    if mutation == "missing":
        (root / "cgroup.procs").unlink()
    elif mutation == "moving":
        write_group(root / "child", [20])
    elif mutation == "pid_drift":

        def resolver(_pid):
            return process(99)
    elif mutation in {"group_bound", "depth_bound"}:
        write_group(root / "child", [])
        kwargs = {"maximum_groups": 1} if mutation == "group_bound" else {"maximum_depth": 0}
    else:
        calls = []

        def resolver(pid):
            calls.append(pid)
            value = process(pid)
            value["starttime"] += len(calls)
            return value

    with pytest.raises((ValueError, OSError)):
        o.read_tree(root, resolver, **kwargs)


@pytest.mark.skipif(
    sys.platform != "linux", reason="Linux real no-follow and proc identity primitives; no Slurm"
)
def test_linux_no_follow_and_current_process_identity(tmp_path):
    root = tmp_path / "tree"
    write_group(root, [os.getpid()])
    text = Path("/proc/self/stat").read_text()
    identity = lc.q.proc_identity(text, os.getuid(), os.getpid())
    assert o.read_tree(root, lambda _pid: identity)[0]["members"][0]["pid"] == os.getpid()
    (tmp_path / "alias").symlink_to(root, target_is_directory=True)
    with pytest.raises((ValueError, OSError)):
        o.read_tree(tmp_path / "alias", lambda _pid: identity)
