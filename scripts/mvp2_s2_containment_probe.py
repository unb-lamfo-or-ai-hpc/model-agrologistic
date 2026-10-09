"""Read-only, solver-free S2 containment facts; never execution admission."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import stat
import sys
from pathlib import Path, PurePosixPath

from scripts import mvp2_h300_resources as resources

SCHEMA = "s2-containment-input-v1"
LIMIT = 1024 * 1024
TOOLS = (
    "scripts/mvp2_s2_containment_probe.py",
    "scripts/mvp2_h300_resources.py",
    "scripts/npad_mvp2_s2_containment.sh",
    "scripts/mvp2_s2_containment_driver.py",
    "scripts/run_mvp2_s2_containment.slurm",
    "docs/mvp2_s2_miniature_protocol.json",
    "pyproject.toml",
)
FLAGS = {
    "native_miniature_admitted": False,
    "production_admitted": False,
    "repeats_admitted": False,
    "live_isolation_proven": False,
}
ERRORS = {
    "not_linux",
    "allocation_missing",
    "cgroup_v1",
    "hybrid_hierarchy",
    "membership_invalid",
    "mount_ambiguous",
    "namespace_relative_root",
    "scope_read_failed",
    "scope_changed",
    "domain_unavailable",
    "cpu_unavailable",
    "finite_memory_unavailable",
    "delegation_not_observed",
    "scoped_kill_unavailable",
    "probe_read_failed",
    "unsupported_partition",
    "unknown_hierarchy",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def digest(value):
    return sha(encoded(value))


def encoded(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()


def decode(payload):
    require(len(payload) <= LIMIT, "Oversized input evidence.")

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate key.")
            result[key] = value
        return result

    def reject(_value):
        raise ValueError("Nonfinite value.")

    return json.loads(payload, object_pairs_hook=pairs, parse_constant=reject)


def bounded(path, limit=LIMIT):
    path = Path(path)
    require(not any(p.is_symlink() for p in (path, *path.parents)), "Linked input path.")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "Nonregular input.")
        payload = stream.read(limit + 1)
    require(len(payload) <= limit, "Oversized input.")
    return payload


def source_identity(root, commit):
    require(type(commit) is str and re.fullmatch(r"[0-9a-f]{40}", commit), "Bad commit.")
    root = Path(root)
    return {
        "source_commit_declared": commit,
        "tool_bytes_sha256": {n: sha(bounded(root / n)) for n in TOOLS},
    }


def membership(text):
    """Classify v1/hybrid explicitly; never guess a writable scope from names."""
    rows = [line.split(":", 2) for line in text.splitlines() if line]
    require(rows and all(len(r) == 3 and r[0].isdigit() for r in rows), "Invalid membership.")
    unified = [r[2] for r in rows if r[:2] == ["0", ""]]
    if not unified:
        return "v1", None
    require(len(unified) == 1, "Ambiguous membership.")
    path = PurePosixPath(unified[0])
    require(
        path.is_absolute() and ".." not in path.parts and str(path) == unified[0],
        "Invalid membership path.",
    )
    return ("v2" if len(rows) == 1 else "hybrid"), path


def mount_scope(text, current):
    candidates = []
    for line in text.splitlines():
        if " - cgroup2 " not in line:
            continue
        fields = line.split()
        require(len(fields) >= 10, "Malformed mount.")

        def unescape(s):
            return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), s)

        root, mount = PurePosixPath(unescape(fields[3])), PurePosixPath(unescape(fields[4]))
        require(
            root.is_absolute() and mount.is_absolute() and ".." not in root.parts + mount.parts,
            "Invalid mount path.",
        )
        if current == root or root in current.parents:
            candidates.append((root, mount, Path(str(mount / current.relative_to(root)))))
    require(len(candidates) == 1, "No unique cgroup2 mount mapping.")
    return candidates[0]


def access(path, mode):
    # Metadata observation only: never open cgroup.kill/procs for write as a probe.
    return os.access(path, mode, effective_ids=True)


def scope_facts(scope, mount, *, can_access=access):
    """Read this process's scope and bounded visible ancestor memory limits only."""
    scope, mount = Path(scope), Path(str(mount))
    require(scope == mount or mount in scope.parents, "Scope escaped mount.")
    facts = {
        "scope_sha256": sha(str(scope).encode()),
        "mount_sha256": sha(str(mount).encode()),
        "scope_id": None,
        "domain": False,
        "cpu_stat_readable": False,
        "memory_current_bytes": None,
        "effective_visible_memory_max_bytes": None,
        "directory_writable_observed": False,
        "procs_writable_observed": False,
        "subtree_control_writable_observed": False,
        "memory_controller_available": False,
        "memory_controller_enabled_for_children": False,
        "kill_present": False,
        "kill_writable_observed": False,
        "parent_procs_writable_observed": None,
        "stable_scope_observed": False,
    }
    directory = resources._Directory(scope)
    try:
        facts["scope_id"] = directory.identity
        facts["domain"] = directory.read("cgroup.type") == "domain"
        cpu = resources._pairs(directory.read("cpu.stat"))
        facts["cpu_stat_readable"] = type(cpu.get("usage_usec")) is int
        facts["memory_current_bytes"] = resources._uint(directory.read("memory.current"))
        available = directory.read("cgroup.controllers").split()
        enabled = directory.read("cgroup.subtree_control").split()
        facts["memory_controller_available"] = "memory" in available
        facts["memory_controller_enabled_for_children"] = "memory" in enabled
        limits = []
        cursor = scope
        for _ in range(64):
            ancestor = resources._Directory(cursor)
            try:
                try:
                    text = ancestor.read("memory.max")
                    if text != "max":
                        limit = resources._uint(text)
                        require(limit > 0, "Zero memory ceiling.")
                        limits.append(limit)
                except FileNotFoundError:
                    require(cursor == mount, "Missing nonroot memory interface.")
            finally:
                ancestor.close()
            if cursor == mount:
                break
            cursor = cursor.parent
        else:
            raise ValueError("Ancestor depth bound exceeded.")
        facts["effective_visible_memory_max_bytes"] = min(limits) if limits else None
        for key, path in (
            ("directory", scope),
            ("procs", scope / "cgroup.procs"),
            ("subtree_control", scope / "cgroup.subtree_control"),
        ):
            facts[f"{key}_writable_observed"] = can_access(path, os.W_OK)
        kill = scope / "cgroup.kill"
        facts["kill_present"] = not kill.is_symlink() and kill.is_file()
        facts["kill_writable_observed"] = facts["kill_present"] and can_access(
            scope / "cgroup.kill", os.W_OK
        )
        if scope != mount:
            facts["parent_procs_writable_observed"] = can_access(
                scope.parent / "cgroup.procs", os.W_OK
            )
        check = resources._Directory(scope)
        try:
            facts["stable_scope_observed"] = check.identity == directory.identity
        finally:
            check.close()
    finally:
        directory.close()
    return facts


def reasons(record):
    errors = list(record["inspection_errors"])
    if record["platform"] != "linux":
        errors.append("not_linux")
    if record["allocation"] is None:
        errors.append("allocation_missing")
    elif record["allocation"]["partition"] != "intel-256":
        errors.append("unsupported_partition")
    mode = record["hierarchy_mode"]
    if mode == "unknown":
        errors.append("unknown_hierarchy")
    if mode in {"v1", "hybrid"}:
        errors.append("cgroup_v1" if mode == "v1" else "hybrid_hierarchy")
    if record["namespace_relative_root"]:
        errors.append("namespace_relative_root")
    facts = record["scope"]
    if facts is not None:
        for key, code in (
            ("stable_scope_observed", "scope_changed"),
            ("domain", "domain_unavailable"),
            ("cpu_stat_readable", "cpu_unavailable"),
        ):
            if not facts[key]:
                errors.append(code)
        if facts["effective_visible_memory_max_bytes"] is None:
            errors.append("finite_memory_unavailable")
        if not all(
            facts[k]
            for k in (
                "directory_writable_observed",
                "procs_writable_observed",
                "subtree_control_writable_observed",
                "memory_controller_available",
            )
        ):
            errors.append("delegation_not_observed")
        if not facts["kill_present"] or not facts["kill_writable_observed"]:
            errors.append("scoped_kill_unavailable")
    elif mode == "v2":
        errors.append("scope_read_failed")
    return sorted(set(errors))


def probe(source, nonce, *, environ=None):
    env = os.environ if environ is None else environ
    allocation = None
    if re.fullmatch(r"[0-9]+", env.get("SLURM_JOB_ID", "")):
        step = env.get("SLURM_STEP_ID", "batch")
        require(re.fullmatch(r"[0-9]+|batch|extern", step), "Invalid step ID.")
        allocation = {
            "job_id": env["SLURM_JOB_ID"],
            "step_id": step,
            "node_sha256": sha(platform.node().encode()),
            "partition": "intel-256" if env.get("SLURM_JOB_PARTITION") == "intel-256" else "other",
        }
    record = {
        "schema_version": SCHEMA,
        "source": source,
        "run_nonce": nonce,
        "platform": "linux" if sys.platform == "linux" else "other",
        "kernel_release_sha256": sha(platform.release().encode()),
        "allocation": allocation,
        "hierarchy_mode": "unknown",
        "namespace_relative_root": False,
        "scope": None,
        "inspection_errors": [],
        **FLAGS,
    }
    if sys.platform == "linux":
        proc = Path("/proc") / str(os.getpid())  # /proc/self is intentionally a symlink.
        try:
            mode, current = membership(bounded(proc / "cgroup").decode("ascii"))
            record["hierarchy_mode"] = mode
        except (OSError, ValueError, UnicodeError):
            record["inspection_errors"].append("membership_invalid")
            current = None
        if record["hierarchy_mode"] == "v2" and current is not None:
            record["namespace_relative_root"] = str(current) == "/"
            try:
                mount_root, mount, scope = mount_scope(
                    bounded(proc / "mountinfo").decode("ascii"), current
                )
            except (OSError, ValueError, UnicodeError):
                record["inspection_errors"].append("mount_ambiguous")
            else:
                try:
                    record["scope"] = scope_facts(scope, mount)
                    require(
                        membership(bounded(proc / "cgroup").decode("ascii")) == (mode, current),
                        "Membership changed.",
                    )
                    require(
                        mount_scope(bounded(proc / "mountinfo").decode("ascii"), current)
                        == (mount_root, mount, scope),
                        "Mount changed.",
                    )
                except (OSError, ValueError, UnicodeError, KeyError):
                    record["scope"] = None
                    record["inspection_errors"].append("scope_read_failed")
    record["blocking_reasons"] = reasons(record)
    record["status"] = (
        "capabilities_observed_not_qualified"
        if not record["blocking_reasons"]
        else "blocked_environment"
    )
    return record


def validate_source(expected_source):
    require(
        type(expected_source) is dict
        and set(expected_source) == {"source_commit_declared", "tool_bytes_sha256"},
        "Bad external source schema.",
    )
    commit = expected_source["source_commit_declared"]
    hashes = expected_source["tool_bytes_sha256"]
    require(
        type(commit) is str
        and re.fullmatch(r"[0-9a-f]{40}", commit)
        and type(hashes) is dict
        and set(hashes) == set(TOOLS)
        and all(type(v) is str and re.fullmatch(r"[0-9a-f]{64}", v) for v in hashes.values()),
        "Bad external source identity.",
    )


def verify(record, expected_source, nonce, job_id):
    """Portable replay with external source/attempt/job; facts never grant authority."""
    validate_source(expected_source)
    require(
        type(nonce) is str
        and re.fullmatch(r"[0-9a-f]{64}", nonce)
        and type(job_id) is str
        and re.fullmatch(r"[0-9]+", job_id),
        "Bad external attempt/job.",
    )
    require(
        type(record) is dict
        and set(record)
        == {
            "schema_version",
            "source",
            "run_nonce",
            "platform",
            "kernel_release_sha256",
            "allocation",
            "hierarchy_mode",
            "namespace_relative_root",
            "scope",
            "inspection_errors",
            "blocking_reasons",
            "status",
            *FLAGS,
        },
        "Probe schema drift.",
    )
    require(
        record["schema_version"] == SCHEMA
        and record["source"] == expected_source
        and record["run_nonce"] == nonce
        and re.fullmatch(r"[0-9a-f]{64}", nonce),
        "Source/attempt drift.",
    )
    require(all(record[k] is False for k in FLAGS), "Probe cannot admit execution.")
    require(
        record["platform"] in {"linux", "other"}
        and record["hierarchy_mode"] in {"unknown", "v1", "v2", "hybrid"}
        and type(record["namespace_relative_root"]) is bool,
        "Invalid platform/hierarchy.",
    )
    require(
        type(record["kernel_release_sha256"]) is str
        and re.fullmatch(r"[0-9a-f]{64}", record["kernel_release_sha256"]),
        "Bad kernel identity.",
    )
    allocation = record["allocation"]
    require(
        type(allocation) is dict
        and set(allocation) == {"job_id", "step_id", "node_sha256", "partition"}
        and allocation["job_id"] == job_id
        and re.fullmatch(r"[0-9]+", job_id)
        and type(allocation["step_id"]) is str
        and re.fullmatch(r"[0-9]+|batch|extern", allocation["step_id"])
        and type(allocation["node_sha256"]) is str
        and re.fullmatch(r"[0-9a-f]{64}", allocation["node_sha256"])
        and allocation["partition"] in {"intel-256", "other"},
        "Allocation identity drift.",
    )
    require(
        type(record["inspection_errors"]) is list
        and len(record["inspection_errors"]) <= len(ERRORS)
        and all(type(e) is str and e in ERRORS for e in record["inspection_errors"]),
        "Unsafe errors.",
    )
    facts = record["scope"]
    if facts is not None:
        bools = {
            "domain",
            "cpu_stat_readable",
            "directory_writable_observed",
            "procs_writable_observed",
            "subtree_control_writable_observed",
            "memory_controller_available",
            "memory_controller_enabled_for_children",
            "kill_present",
            "kill_writable_observed",
            "stable_scope_observed",
        }
        require(
            type(facts) is dict
            and set(facts)
            == {
                "scope_sha256",
                "mount_sha256",
                "scope_id",
                "memory_current_bytes",
                "effective_visible_memory_max_bytes",
                "parent_procs_writable_observed",
                *bools,
            },
            "Scope schema drift.",
        )
        require(all(type(facts[k]) is bool for k in bools), "Invalid scope boolean.")
        for key in ("scope_sha256", "mount_sha256"):
            require(
                type(facts[key]) is str and re.fullmatch(r"[0-9a-f]{64}", facts[key]),
                "Invalid scope digest.",
            )
        require(
            type(facts["scope_id"]) in {list, tuple}
            and len(facts["scope_id"]) == 2
            and all(type(n) is int and n >= 0 for n in facts["scope_id"]),
            "Invalid scope inode.",
        )
        for key in ("memory_current_bytes", "effective_visible_memory_max_bytes"):
            require(
                facts[key] is None or type(facts[key]) is int and facts[key] >= 0,
                "Invalid memory counter.",
            )
        require(facts["effective_visible_memory_max_bytes"] != 0, "Zero ceiling.")
        require(
            facts["parent_procs_writable_observed"] is None
            or type(facts["parent_procs_writable_observed"]) is bool,
            "Invalid parent observation.",
        )
        require(record["hierarchy_mode"] == "v2", "Scope without v2.")
    blocking = reasons(record)
    require(
        record["blocking_reasons"] == blocking
        and record["status"]
        == ("blocked_environment" if blocking else "capabilities_observed_not_qualified"),
        "Classification drift.",
    )
    return {
        "integrity_accepted": True,
        "status": record["status"],
        "blocking_reasons": blocking,
        **FLAGS,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    require(sys.version_info[:2] == (3, 13), "Use the existing Python 3.13 environment.")
    require(re.fullmatch(r"[0-9a-f]{64}", args.nonce), "Bad nonce.")
    root = Path(__file__).resolve().parents[1]
    require(
        Path(resources.__file__).resolve() == root / "scripts/mvp2_h300_resources.py",
        "Loaded observer root drift.",
    )
    source = source_identity(root, args.source_sha)
    record = probe(source, args.nonce)
    require(
        record["allocation"] is not None, "Run only in the explicitly requested Slurm allocation."
    )
    verify(record, source, args.nonce, record["allocation"]["job_id"])
    output = args.output.absolute()
    require(
        not any(p.is_symlink() for p in (output, *output.parents))
        and not any(output.is_relative_to(Path(p)) for p in ("/proc", "/sys", "/dev")),
        "Unsafe output.",
    )
    with output.open("xb") as stream:
        stream.write(encoded(record))
    print("S2_CONTAINMENT_INPUT=" + record["status"])
    print("NO_NATIVE_WORKER_OR_H300_ADMITTED")
    return 0  # A safely recorded unsupported environment is evidence, not a retry.


if __name__ == "__main__":
    raise SystemExit(main())
