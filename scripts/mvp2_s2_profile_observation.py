"""Prospective non-lossy prerequisite observation and independent replay.

Only explicit injected readers are selected by observe. Public execution denies;
the versioned software driver cannot dispatch start/batch from its CLI either.
Historical PR95 certificates and enforcement requirements are unchanged.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Observation software qualification only; execution is closed.")

import math
import os
import re
import time

from scripts import mvp2_s2_profile_diagnostics as diag

legacy = diag.p
e, lc, q, s, a = legacy.e, legacy.lc, legacy.q, legacy.s, legacy.a
FLAGS, LIMIT = dict(legacy.FLAGS), legacy.LIMIT
query_record, query_text = legacy.query_record, legacy.query_text
OPERATIONS = ("placement", "mount_mapping", "descriptor", "hierarchy", "inventory")
ERRORS = {
    "deadline_exhausted",
    "permission_denied",
    "not_found",
    "operating_system_error",
    "invalid_evidence",
}


def execute(*_args, **_kwargs):
    raise PermissionError("No observation, normal, adverse, native or repeat admission.")


class KernelReader(e.KernelReader):
    """Independent host primitives; no privilege escalation or host mutation."""

    def host_namespace(self, name):
        s.require(name in e.NAMESPACES, "Fixed namespace required.")
        info = os.stat("/proc/1/ns/" + name)
        return [info.st_dev, info.st_ino]

    def host_limit(self):
        directory = q.r._Directory("/proc/sys/user")
        try:
            return directory.read("max_user_namespaces")
        finally:
            directory.close()


def observe(job, kernel, query, *, clock=time.monotonic):
    """Read once per stage; independent failures survive without hidden retries.

    The 90-second cooperative deadline cannot interrupt a blocking syscall.
    No worker, IPC, srun, prctl, affinity, signal or controller write is used.
    """
    q._hash(job["source_commit"], 40)
    q._hash(job["plan_sha256"])
    s.require(type(kernel.fixture) is bool, "Reader provenance required.")
    started = clock()
    s.require(type(started) in {int, float} and math.isfinite(started), "Finite clock.")
    deadline, channels = started + 90, {}

    def capture(name, call):
        error, value = None, None
        if clock() >= deadline:
            error = "budget_exhausted"
        else:
            try:
                value = call()
                s.require(len(q.c.encoded(value)) <= LIMIT, "Channel bound.")
                if clock() >= deadline:
                    value, error = None, "budget_exhausted"
            except (
                OSError,
                ValueError,
                UnicodeError,
                KeyError,
                TypeError,
                IndexError,
                AttributeError,
            ):
                value, error = None, "invalid_or_unavailable"
        channels[name] = {"value": value, "error": error}

    host = diag.host_components(
        read_namespace=kernel.host_namespace,
        read_limit=kernel.host_limit,
        clock=clock,
        deadline=deadline,
    )
    capture("observer", lambda: kernel.process(kernel.self_pid()))
    for name in ("allocation", "batch_members"):
        capture(name, lambda name=name: query(name))
    observer = channels["observer"]["value"]
    controllers = {}
    for controller in lc.CONTROLLERS:
        records = {}

        def read(operation, controller=controller, records=records):
            s.require(observer is not None, "Observer unavailable.")
            if operation == "placement":
                return diag.batch_placement(
                    controller, observer["scopes"][controller], job["job_id"], job["uid"]
                )
            placement = records["placement"]["value"]
            s.require(placement is not None, "Placement unavailable.")
            if operation == "mount_mapping":
                raw = kernel.mountinfo(kernel.self_pid())
                return {
                    "raw": raw,
                    "mount_id": e.mount_id(raw, controller, placement["mount"]),
                }
            mount_id = records["mount_mapping"]["value"]
            s.require(mount_id is not None, "Mount mapping unavailable.")
            if operation == "descriptor":
                return kernel.descriptor(
                    placement["mount"],
                    placement["parent"],
                    placement["member_scope"],
                    placement["member_scope"],
                    mount_id["mount_id"],
                )
            descriptor = records["descriptor"]["value"]
            s.require(descriptor is not None, "Descriptor unavailable.")
            if operation == "hierarchy":
                # Retain the actual permission facts, even when policy rejects them.
                # The old real reader may itself reject before returning those facts.
                return kernel.hierarchy(placement["mount"])
            return kernel.inventory(descriptor)

        for operation in OPERATIONS:
            records[operation] = diag.capture_primitive(
                controller + "_" + operation,
                lambda operation=operation, read=read: read(operation),
                clock=clock,
                deadline=deadline,
                validate=lambda _value: None,
            )
        controllers[controller] = records
    capture("observer_second", lambda: kernel.process(kernel.self_pid()))
    elapsed = clock() - started
    s.require(
        type(elapsed) in {int, float} and math.isfinite(elapsed) and 0 <= elapsed <= 720,
        "Capture duration.",
    )
    result = {
        "schema_version": "s2-profile-diagnostic-observation-v2",
        **{key: job[key] for key in ("source_commit", "job_id", "plan_sha256", "uid")},
        "node": kernel.node(),
        "host": host,
        "channels": channels,
        "controllers": controllers,
        "elapsed_seconds": elapsed,
        "fixture": kernel.fixture,
        **FLAGS,
    }
    s.require(len(q.c.encoded(result)) <= LIMIT, "Observation byte bound.")
    return result


def primitive(record, stage):
    """Validate producer diagnostics before consuming any purported value."""
    q._keys(record, {"stage", "value", "error", "errno", "software_components_only", *FLAGS})
    error, number = record["error"], record["errno"]
    s.require(
        record["stage"] == stage
        and record["software_components_only"] is True
        and all(record[k] is False for k in FLAGS),
        "Primitive binding/flags.",
    )
    s.require(error is None or error in ERRORS, "Primitive error grammar.")
    s.require(number is None or type(number) is int and 1 <= number <= 65535, "Errno grammar.")
    s.require(error is None or record["value"] is None, "Ambiguous primitive.")
    s.require(error is not None or number is None, "Success with errno.")
    s.require(
        error in {"permission_denied", "not_found", "operating_system_error"} or number is None,
        "Unexpected errno.",
    )
    if error == "permission_denied":
        s.require(number in {None, 1, 13}, "Permission errno drift.")
    if error == "not_found":
        s.require(number in {2, 20}, "Missing errno drift.")
    return record["value"] if error is None else None


def review(value, job):
    """Derive the same conservative obligations without trusting a summary flag."""
    q._keys(
        value,
        {
            "schema_version",
            "source_commit",
            "job_id",
            "plan_sha256",
            "uid",
            "node",
            "host",
            "channels",
            "controllers",
            "elapsed_seconds",
            "fixture",
            *FLAGS,
        },
    )
    s.require(
        value["schema_version"] == "s2-profile-diagnostic-observation-v2"
        and all(value[k] == job[k] for k in ("source_commit", "job_id", "plan_sha256", "uid"))
        and type(value["fixture"]) is bool
        and all(value[k] is False for k in FLAGS),
        "Observation binding/flags.",
    )
    q._hash(job["source_commit"], 40)
    q._hash(job["plan_sha256"])
    s.require(
        type(job["uid"]) is int
        and 0 < job["uid"] < 2**32
        and type(job["job_id"]) is str
        and re.fullmatch(r"[1-9][0-9]{0,9}", job["job_id"]),
        "Job grammar.",
    )
    elapsed = value["elapsed_seconds"]
    s.require(
        type(elapsed) in {int, float} and math.isfinite(elapsed) and 0 <= elapsed <= 720,
        "Capture duration.",
    )
    s.require(
        type(value["node"]) is str
        and re.fullmatch(r"[A-Za-z0-9_.-]{1,255}", value["node"])
        and a.scheduler_node(value["node"]) == value["node"],
        "Node grammar.",
    )
    host = value["host"]
    q._keys(host, {"schema_version", "channels", *FLAGS})
    s.require(
        host["schema_version"] == "s2-closed-host-diagnostics-v1"
        and all(host[k] is False for k in FLAGS),
        "Host schema/flags.",
    )
    q._keys(host["channels"], {*e.NAMESPACES, "max_user_namespaces"})
    namespaces = {
        name: primitive(host["channels"][name], "host_namespace_" + name) for name in e.NAMESPACES
    }
    limit = primitive(host["channels"]["max_user_namespaces"], "host_user_namespace_limit")
    q._keys(value["channels"], {"observer", "observer_second", "allocation", "batch_members"})
    for channel in value["channels"].values():
        q._keys(channel, {"value", "error"})
        s.require(
            channel["error"] is None or channel["error"] in legacy.ERRORS, "Channel error grammar."
        )
        s.require(channel["error"] is None or channel["value"] is None, "Ambiguous channel.")
    q._keys(value["controllers"], lc.CONTROLLERS)
    facts, diagnostics = {}, {}
    for controller, records in value["controllers"].items():
        q._keys(records, set(OPERATIONS))
        facts[controller] = {op: primitive(records[op], controller + "_" + op) for op in OPERATIONS}
        diagnostics[controller] = {
            op: {"error": records[op]["error"], "errno": records[op]["errno"]} for op in OPERATIONS
        }
    checks = {}

    def check(name, call):
        try:
            s.require(call() is True, "Prerequisite not observed.")
            checks[name] = True
        except (OSError, ValueError, UnicodeError, KeyError, TypeError, IndexError, AttributeError):
            checks[name] = False

    channels = value["channels"]
    observer, second = channels["observer"]["value"], channels["observer_second"]["value"]
    check("host_user_namespaces_disabled", lambda: type(limit) is int and limit == 0)

    def identity():
        for inode in namespaces.values():
            lc.inode(inode)
        return (
            observer["identity"]["uid"] == job["uid"]
            and observer["namespaces"] == namespaces
            and observer["uid_map"].split() == ["0", "0", "4294967295"]
            and lc.stable(observer["identity"]) == lc.stable(second["identity"])
            and observer["scopes"] == second["scopes"]
            and observer["namespaces"] == second["namespaces"]
        )

    check("observer_namespace_and_identity", identity)
    check(
        "current_allocation",
        lambda: bool(
            a.review_allocation(
                query_text(channels["allocation"]["value"]),
                job["job_id"],
                job["uid"],
                value["node"],
            )
        ),
    )
    check(
        "current_batch_membership",
        lambda: (
            observer["identity"]["pid"]
            in e.batch_members(query_text(channels["batch_members"]["value"]), job["job_id"])
        ),
    )
    for controller in lc.CONTROLLERS:

        def controller_check(controller=controller):
            record = facts[controller]
            placement = diag.batch_placement(
                controller, observer["scopes"][controller], job["job_id"], job["uid"]
            )
            s.require(record["placement"] == placement, "Recomputed placement drift.")
            descriptor, inventory = record["descriptor"], record["inventory"]
            q._keys(
                descriptor,
                {
                    "mount",
                    "parent",
                    "worker",
                    "supervisor",
                    "mount_id",
                    "mount_identity",
                    "parent_identity",
                    "worker_identity",
                    "supervisor_identity",
                },
            )
            mapping = record["mount_mapping"]
            q._keys(mapping, {"raw", "mount_id"})
            s.require(
                descriptor["mount"] == placement["mount"]
                and descriptor["parent"] == placement["parent"]
                and descriptor["worker"] == descriptor["supervisor"] == placement["member_scope"]
                and descriptor["mount_id"] == mapping["mount_id"]
                and e.mount_id(mapping["raw"], controller, placement["mount"])
                == mapping["mount_id"],
                "Controller descriptor binding.",
            )
            s.require(
                type(mapping["mount_id"]) is int and mapping["mount_id"] > 0,
                "Mount mapping required.",
            )
            e.hierarchy_policy(record["hierarchy"])
            s.require(
                inventory["mount_identity"] == descriptor["mount_identity"]
                and inventory["parent_identity"] == descriptor["parent_identity"]
                and inventory["mount_id"] == descriptor["mount_id"]
                and inventory["groups"][0]["identity"] == descriptor["parent_identity"],
                "Controller inventory drift.",
            )
            for role in ("mount", "parent", "worker", "supervisor"):
                lc.inode(descriptor[role + "_identity"])
            members, paths, locations = lc.tree(inventory, descriptor)
            pid = observer["identity"]["pid"]
            leaf = str(
                s._absolute(placement["member_scope"]).relative_to(s._absolute(placement["parent"]))
            )
            s.require(
                pid in members
                and lc.stable(members[pid]) == lc.stable(observer["identity"])
                and locations[pid] == leaf
                and paths.get(leaf) == descriptor["worker_identity"]
                and descriptor["worker_identity"] == descriptor["supervisor_identity"],
                "Observed member not bound to actual batch leaf.",
            )
            hierarchy = {v["relative"]: v["directory"]["identity"] for v in record["hierarchy"]}
            mount = s._absolute(placement["mount"])
            for role in ("mount", "parent", "worker", "supervisor"):
                relative = str(s._absolute(descriptor[role]).relative_to(mount))
                s.require(
                    hierarchy.get("" if relative == "." else relative)
                    == descriptor[role + "_identity"],
                    "Hierarchy/descriptor binding drift.",
                )
            parent_relative = str(s._absolute(placement["parent"]).relative_to(mount))
            s.require(
                all(
                    hierarchy.get(parent_relative + ("/" + name if name else "")) == inode
                    for name, inode in paths.items()
                ),
                "Hierarchy/inventory binding drift.",
            )
            return True

        check(controller + "_whole_hierarchy_readonly", controller_check)
    records = [
        *host["channels"].values(),
        *(record for group in value["controllers"].values() for record in group.values()),
    ]
    check(
        "capture_within_budget",
        lambda: (
            elapsed < 90
            and not any(r["error"] == "deadline_exhausted" for r in records)
            and not any(c["error"] == "budget_exhausted" for c in channels.values())
        ),
    )
    check(
        "channel_evidence_complete",
        lambda: (
            all(r["error"] is None for r in records)
            and all(c["error"] is None for c in channels.values())
        ),
    )
    blockers = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "s2-profile-diagnostic-review-v2",
        **{key: job[key] for key in ("source_commit", "job_id", "plan_sha256")},
        "observation_sha256": s.digest(value),
        "observation_provenance": "software_fixture"
        if value["fixture"]
        else "kernel_reads_not_live_qualified",
        "checks": checks,
        "blockers": blockers,
        "host_limit_status": "unavailable"
        if limit is None
        else "observed_zero"
        if type(limit) is int and limit == 0
        else "observed_unsupported"
        if type(limit) is int and 0 < limit <= s.MAX_COUNTER
        else "invalid_evidence",
        "host_diagnostics": {
            name: {"error": r["error"], "errno": r["errno"]} for name, r in host["channels"].items()
        },
        "controller_diagnostics": diagnostics,
        "status": "prerequisites_observed_not_admitted" if not blockers else "blocked_environment",
        "unproven": [
            "worker_no_new_privs_and_peer_binding",
            "worker_step_resources_and_disjoint_roles",
            "parent_persistence_and_no_escape_during_execution",
            "quiet_cleanup_and_scan_cadence",
            "filesystem_crash_durability",
        ],
        **FLAGS,
    }
