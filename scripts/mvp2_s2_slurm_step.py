"""Closed Slurm-step contract and read-only cgroup-v1 observations.

No scheduler invocation, native import, cgroup write or admission entry point.
Bindings and observations are not capabilities or remote attestation. The
future launcher must establish the actual job/step/scope relationship first.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath

from scripts import mvp2_h300_resources as r

FLAGS = {
    "live_isolation_proven": False,
    "native_miniature_admitted": False,
    "production_admitted": False,
    "repeats_admitted": False,
}
CONTROLLERS = ("memory", "cpuacct", "freezer", "cpuset")
CONFIG_KEYS = {
    "JobAcctGatherType",
    "KillWait",
    "ProctrackType",
    "SelectType",
    "SelectTypeParameters",
    "TaskPlugin",
    "TaskPluginParam",
    "UnkillableStepTimeout",
}
MAX_COUNTER = 2**64 - 1
UNLIMITED_FLOOR = 2**60


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def seconds(value):
    require(type(value) is str and re.fullmatch(r"[0-9]{1,5} sec", value), "Unknown duration.")
    result = int(value.split()[0])
    require(0 <= result <= 3600, "Duration outside qualified design bound.")
    return result


def review_inventory(item):
    require(
        type(item) is dict
        and set(item)
        == {
            "schema_version",
            "config_query_succeeded",
            "declared_configuration",
            "scontrol_client_version",
            "srun_client_version",
            *FLAGS,
        }
        and item["schema_version"] == "s2-slurm-declared-config-v1"
        and item["config_query_succeeded"] is True
        and all(item[k] is False for k in FLAGS),
        "Invalid or admitting inventory.",
    )
    require(
        item["scontrol_client_version"] == item["srun_client_version"] == "slurm 22.05.11",
        "Unreviewed client version.",
    )
    cfg = item["declared_configuration"]
    require(type(cfg) is dict and set(cfg) == CONFIG_KEYS, "Configuration inventory drift.")
    expected = {
        "JobAcctGatherType": "jobacct_gather/linux",
        "ProctrackType": "proctrack/cgroup",
        "SelectType": "select/cons_tres",
        "SelectTypeParameters": "CR_CPU_MEMORY",
        "TaskPluginParam": "threads",
    }
    require(all(cfg[k] == v for k, v in expected.items()), "Unreviewed site declaration.")
    require(
        type(cfg["TaskPlugin"]) is str
        and sorted(cfg["TaskPlugin"].split(",")) == ["task/affinity", "task/cgroup"],
        "Required task declarations absent or ambiguous.",
    )
    kill, unkillable = seconds(cfg["KillWait"]), seconds(cfg["UnkillableStepTimeout"])
    require((kill, unkillable) == (300, 60), "Cleanup declaration drift.")
    return {
        "inventory_sha256": digest(item),
        "declared_candidate": "slurm_owned_numeric_worker_step",
        "cleanup_observation_budget_seconds": kill + unkillable + 30,
        "accounting_is_cgroup_lifetime_measurement": False,
        **FLAGS,
    }


def binding(item):
    require(
        type(item) is dict
        and set(item)
        == {"job_id", "worker_step_id", "supervisor_step_id", "nonce", "source_commit"},
        "Step binding schema drift.",
    )
    for key, pattern in (
        ("job_id", r"[1-9][0-9]{0,19}"),
        ("worker_step_id", r"0|[1-9][0-9]{0,9}"),
        ("nonce", r"[0-9a-f]{64}"),
        ("source_commit", r"[0-9a-f]{40}"),
    ):
        require(
            type(item[key]) is str and re.fullmatch(pattern, item[key]), "Invalid step identity."
        )
    require(item["supervisor_step_id"] == "batch", "Only an outside batch supervisor is designed.")
    return dict(item)


def signal_descriptor(item, signal):
    """Return an inert exact-target proposal; never execute it or return authority."""
    item = binding(item)
    require(type(signal) is str and signal in {"TERM", "KILL"}, "Unsupported signal.")
    return {
        "argv": ["scancel", "--signal=" + signal, item["job_id"] + "." + item["worker_step_id"]],
        "binding_sha256": digest(item),
        "execution_admitted": False,
        **FLAGS,
    }


def qualification_plan(inventory, step):
    candidate, step = review_inventory(inventory), binding(step)
    return {
        "schema_version": "s2-slurm-step-design-v1",
        "binding": step,
        "site_review": candidate,
        "proposed_synthetic_profile": {
            "nodes": 1,
            "allocation_cpus": 2,
            "allocation_memory_mib": 2048,
            "worker_cpus": 1,
            "worker_memory_mib": 256,
            "startup_seconds": 30,
            "exercise_seconds": 60,
            "term_grace_seconds": 5,
            "cleanup_observation_seconds": candidate["cleanup_observation_budget_seconds"],
            "allocation_wall_seconds": 720,
        },
        "term_proposal": signal_descriptor(step, "TERM"),
        "kill_proposal": signal_descriptor(step, "KILL"),
        "launcher_implemented": False,
        "synthetic_execution_admitted": False,
        **FLAGS,
    }


def _absolute(text):
    require(
        type(text) is str and "\\" not in text and not any(ord(c) < 32 for c in text),
        "Unsafe scope path.",
    )
    path = PurePosixPath(text)
    require(
        path.is_absolute()
        and not text.startswith("//")
        and ".." not in path.parts
        and str(path) == text,
        "Noncanonical scope path.",
    )
    return path


def memberships(text):
    require(type(text) is str and len(text) <= 65536, "Oversized membership.")
    result, identifiers = {}, set()
    for line in text.splitlines():
        parts = line.split(":", 2)
        require(
            len(parts) == 3 and re.fullmatch(r"[1-9][0-9]*", parts[0]), "Expected pure cgroup v1."
        )
        require(parts[0] not in identifiers, "Duplicate hierarchy.")
        identifiers.add(parts[0])
        path = _absolute(parts[2])
        controllers = parts[1].split(",")
        require(
            all(re.fullmatch(r"[A-Za-z0-9_=.-]+", c) for c in controllers), "Invalid controller."
        )
        for controller in controllers:
            require(controller not in result, "Duplicate controller membership.")
            result[controller] = path
    require(all(k in result for k in CONTROLLERS), "Missing v1 controller.")
    return {k: result[k] for k in CONTROLLERS}


def mapped_scopes(member_text, mount_text):
    """Map actual membership/mount data, never infer Slurm ownership from names."""
    require(type(mount_text) is str and len(mount_text) <= 1024 * 1024, "Oversized mounts.")
    members, result = memberships(member_text), {}
    for controller, current in members.items():
        candidates = []
        for line in mount_text.splitlines():
            if " - cgroup " not in line:
                continue
            left, right = line.split(" - ", 1)
            fields, tail = left.split(), right.split()
            require(len(fields) >= 6 and len(tail) >= 3, "Malformed cgroup mount.")
            if controller not in tail[2].split(","):
                continue

            def unescape(value):
                return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), value)

            root, mount = _absolute(unescape(fields[3])), _absolute(unescape(fields[4]))
            require(str(root) == "/", "Namespaced mount root not qualified.")
            require(current != root, "Shared controller root is not a worker scope.")
            candidates.append((mount / current.relative_to(root), mount))
        require(len(candidates) == 1, "Missing or ambiguous controller mapping.")
        scope, mount = candidates[0]
        result[controller] = {"scope": str(scope), "mount": str(mount)}
    return result


def separated_scopes(worker, supervisor):
    require(type(worker) is dict and type(supervisor) is dict, "Invalid scope maps.")
    require(set(worker) == set(supervisor) == set(CONTROLLERS), "Scope controller drift.")
    for key in CONTROLLERS:
        w, s = worker[key], supervisor[key]
        for item in (w, s):
            _validate_scope(item)
        require(w["mount"] == s["mount"], "Controller mount differs.")
        wp, sp = _absolute(w["scope"]), _absolute(s["scope"])
        require(
            wp != sp and wp not in sp.parents and sp not in wp.parents,
            "Shared/nested supervisor scope.",
        )
    return {"distinct_non_nested_scopes_observed": True, "step_ownership_proven": False, **FLAGS}


def _validate_scope(item, *, test_only=False):
    require(type(item) is dict and set(item) == {"scope", "mount"}, "Scope schema drift.")
    if test_only:
        require(all(type(item[k]) is str for k in item), "Invalid fixture paths.")
        scope, mount = Path(item["scope"]), Path(item["mount"])
        require(scope.is_absolute() and ".." not in scope.parts, "Invalid fixture scope.")
    else:
        scope, mount = _absolute(item["scope"]), _absolute(item["mount"])
    require(mount in scope.parents, "Scope must be below its controller mount.")


def _uint(text):
    require(re.fullmatch(r"[0-9]{1,20}", text), "Invalid counter.")
    value = int(text)
    require(value <= MAX_COUNTER, "Counter overflow.")
    return value


def _cpus(text):
    require(re.fullmatch(r"[0-9,-]+", text) and len(text) <= 4096, "Invalid cpuset.")
    cpus = set()
    for part in text.split(","):
        ends = part.split("-")
        require(len(ends) in {1, 2}, "Malformed CPU range.")
        start, end = int(ends[0]), int(ends[-1])
        require(0 <= start <= end <= 1048575 and end - start <= 4095, "CPU range bound.")
        values = set(range(start, end + 1))
        require(not (values & cpus), "Overlapping CPU range.")
        cpus |= values
        require(len(cpus) <= 4096, "Cpuset bound.")
    return len(cpus)


def read_v1_snapshot(scopes, *, test_only=False, max_groups=128):
    """Bounded observations only; no emptiness/cleanup/admission authority.

    Caller supplies externally bound scopes. Live mode checks actual mount type,
    not job ownership. Freezer membership covers a bounded subtree; no raw PID,
    path, hostname, environment or exception message is exported. No missing
    scope is accepted as successful cleanup.
    """
    require(type(test_only) is bool and (test_only or sys.platform == "linux"), "Linux required.")
    require(type(max_groups) is int and 1 <= max_groups <= 128, "Group bound.")
    require(type(scopes) is dict and set(scopes) == set(CONTROLLERS), "Scope map drift.")
    for item in scopes.values():
        _validate_scope(item, test_only=test_only)
    if not test_only:
        own_proc = r._Directory(Path("/proc") / str(os.getpid()))
        try:
            mounts = own_proc.read("mountinfo")
        finally:
            own_proc.close()
        for controller in CONTROLLERS:
            mount = scopes[controller]["mount"]
            require(
                any(
                    " - cgroup " in line
                    and len(line.split()) >= 10
                    and line.split()[4] == mount
                    and controller in line.split(" - ", 1)[1].split()[2].split(",")
                    for line in mounts.splitlines()
                ),
                "Live v1 mount not established.",
            )
    report = {
        "schema_version": "s2-cgroup-v1-observation-v1",
        "synthetic_observation": test_only,
        "status": "observed_not_qualified",
        "errors": [],
        "counters": None,
        "scopes": {},
        **FLAGS,
    }
    opened = {}
    try:
        for key in CONTROLLERS:
            item = scopes[key]
            require(type(item) is dict and set(item) == {"scope", "mount"}, "Scope schema drift.")
            scope, mount = Path(item["scope"]), Path(item["mount"])
            require(
                scope.is_absolute() and mount in scope.parents and ".." not in scope.parts,
                "Invalid child scope.",
            )
            opened[key] = r._Directory(scope)
            report["scopes"][key] = {
                "path_sha256": digest(str(scope)),
                "inode": opened[key].identity,
            }
        memory = opened["memory"]
        counters = {
            "memory_usage_bytes": _uint(memory.read("memory.usage_in_bytes")),
            "memory_max_usage_bytes": _uint(memory.read("memory.max_usage_in_bytes")),
            "memory_limit_bytes": _uint(memory.read("memory.limit_in_bytes")),
            "memory_failcnt": _uint(memory.read("memory.failcnt")),
            "cpu_usage_ns": _uint(opened["cpuacct"].read("cpuacct.usage")),
            "cpuset_cpu_count": _cpus(opened["cpuset"].read("cpuset.cpus")),
        }
        require(memory.read("memory.use_hierarchy") == "1", "Hierarchical memory not observed.")
        stat = r._pairs(memory.read("memory.stat"))
        ceiling = stat.get("hierarchical_memory_limit")
        require(
            type(ceiling) is int and 0 < ceiling < UNLIMITED_FLOOR,
            "No finite hierarchical ceiling.",
        )
        require(0 < counters["memory_limit_bytes"] <= MAX_COUNTER, "Invalid memory ceiling.")
        counters["effective_reported_memory_limit_bytes"] = min(
            ceiling, counters["memory_limit_bytes"]
        )
        stack, nodes, pids = [(Path(scopes["freezer"]["scope"]), 0)], [], set()
        while stack:
            path, depth = stack.pop()
            require(depth <= 16 and len(nodes) < max_groups, "Subtree traversal bound.")
            directory = r._Directory(path)
            try:
                members = directory.read("cgroup.procs").splitlines()
                local = [_uint(pid) for pid in members]
                require(
                    all(pid > 0 for pid in local) and len(set(local)) == len(local),
                    "Invalid membership.",
                )
                require(not (set(local) & pids), "Membership changed during traversal.")
                pids.update(local)
                require(len(pids) <= 4096, "Membership bound.")
                nodes.append((path, directory.identity, sorted(local), directory.children()))
                stack.extend((path / name, depth + 1) for name in nodes[-1][3])
            finally:
                directory.close()
        for path, inode, members, children in nodes:
            check = r._Directory(path)
            try:
                require(
                    check.identity == inode and check.children() == children, "Subtree changed."
                )
                require(
                    sorted(_uint(pid) for pid in check.read("cgroup.procs").splitlines())
                    == members,
                    "Membership changed.",
                )
            finally:
                check.close()
        counters.update(freezer_group_count=len(nodes), freezer_unique_process_count=len(pids))
        for key, directory in opened.items():
            check = r._Directory(scopes[key]["scope"])
            try:
                require(check.identity == directory.identity, "Scope replaced.")
            finally:
                check.close()
        require(
            _uint(memory.read("memory.limit_in_bytes")) == counters["memory_limit_bytes"],
            "Memory limit changed.",
        )
        require(
            r._pairs(memory.read("memory.stat")).get("hierarchical_memory_limit") == ceiling,
            "Ancestor ceiling changed.",
        )
        report["counters"] = counters
    except (OSError, ValueError, UnicodeError, KeyError, IndexError):
        report["status"], report["errors"] = "blocked_observation", ["scope_or_counter_invalid"]
    finally:
        for directory in opened.values():
            directory.close()
    return report
