"""Independent prerequisite observation/replay; never a normal admission test.

Only the separate observation driver selects the real read-only kernel reader.
There is no worker, IPC release, hardening, affinity or host-setting mutation.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Use the separately reviewed observation wrapper; normal stays closed.")

import copy
import re
import time
from pathlib import PurePosixPath

from scripts import mvp2_s2_environment as e

lc, q, s, a = e.lc, e.q, e.s, e.a
FLAGS = {**lc.FLAGS, "live_containment_qualified": False, "synthetic_execution_admitted": False}
CHANNELS = {"host", "observer", "allocation", "batch_members", *lc.CONTROLLERS}
LIMIT = 16 * 1024**2
ERRORS = {"invalid_or_unavailable", "budget_exhausted"}


def execute(*_args, **_kwargs):
    raise PermissionError("No normal, adverse, native or repeat admission.")


def query_record(meta, raw):
    import base64

    s.require(type(raw) is bytes and len(raw) <= 65536, "Query byte bound.")
    return {"meta": copy.deepcopy(meta), "raw_base64": base64.b64encode(raw).decode("ascii")}


def query_text(value):
    import base64

    from scripts import mvp2_s2_allocation_diagnostic as d

    q._keys(value, {"meta", "raw_base64"})
    meta = value["meta"]
    q._keys(
        meta,
        {
            "status",
            "returncode",
            "stdout_bytes",
            "stderr_bytes",
            "stdout_prefix_sha256",
            "stderr_prefix_sha256",
        },
    )
    raw = base64.b64decode(value["raw_base64"], validate=True)
    s.require(
        len(raw) <= 65536 and d.digest(raw) == meta["stdout_prefix_sha256"], "Query checksum."
    )
    s.require(
        meta["status"] == "complete"
        and type(meta["returncode"]) is int
        and meta["returncode"] == 0
        and type(meta["stdout_bytes"]) is int
        and meta["stdout_bytes"] == len(raw)
        and type(meta["stderr_bytes"]) is int
        and 0 <= meta["stderr_bytes"] <= 65536,
        "Unsuccessful/incomplete query.",
    )
    q._hash(meta["stderr_prefix_sha256"])
    return raw.decode("ascii")


def observe(job, kernel, query, *, clock=time.monotonic):
    """Capture independent channels even when another prerequisite is unsupported.

    The 90s cooperative budget does not bound a blocking kernel/filesystem call.
    The allocation has its own 12-minute scheduler limit. No worker is created.
    """
    q._hash(job["source_commit"], 40)
    s.require(type(kernel.fixture) is bool, "Observation provenance required.")
    started, channels = clock(), {}

    def capture(name, call):
        error, value = None, None
        if clock() - started >= 90:
            error = "budget_exhausted"
        else:
            try:
                value = call()
            except (OSError, ValueError, UnicodeError, KeyError, TypeError, IndexError):
                error = "invalid_or_unavailable"
        channels[name] = {"value": value, "error": error}

    capture("host", kernel.host)
    capture("observer", lambda: kernel.process(kernel.self_pid()))
    for name in ("allocation", "batch_members"):
        capture(name, lambda name=name: query(name))
    observer = channels["observer"]["value"]
    for controller in lc.CONTROLLERS:

        def controller_read(controller=controller):
            s.require(observer is not None, "Observer unavailable.")
            scope = observer["scopes"][controller]
            actual = PurePosixPath(scope["scope"])
            s.require(
                actual.name == "step_batch" and actual.parent.name == "job_" + job["job_id"],
                "Current batch/job cgroup identity required.",
            )
            mount_id = e.mount_id(kernel.mountinfo(kernel.self_pid()), controller, scope["mount"])
            descriptor = kernel.descriptor(
                scope["mount"], str(actual.parent), str(actual), str(actual), mount_id
            )
            hierarchy = kernel.hierarchy(scope["mount"])
            e.hierarchy_policy(hierarchy)
            inventory = kernel.inventory(descriptor)
            return {"descriptor": descriptor, "hierarchy": hierarchy, "inventory": inventory}

        capture(controller, controller_read)
    second = None
    try:
        second = kernel.process(kernel.self_pid())
    except (OSError, ValueError, UnicodeError, KeyError, TypeError, IndexError):
        pass
    result = {
        "schema_version": "s2-lifecycle-profile-observation-v1",
        "source_commit": job["source_commit"],
        "job_id": job["job_id"],
        "plan_sha256": job["plan_sha256"],
        "uid": job["uid"],
        "node": kernel.node(),
        "channels": channels,
        "observer_second": second,
        "elapsed_seconds": clock() - started,
        "fixture": kernel.fixture,
        **FLAGS,
    }
    s.require(len(q.c.encoded(result)) <= LIMIT, "Observation byte bound.")
    return result


def review(value, job):
    """Recompute a prerequisite screen; success cannot attest to live cleanup."""
    q._keys(
        value,
        {
            "schema_version",
            "source_commit",
            "job_id",
            "plan_sha256",
            "uid",
            "node",
            "channels",
            "observer_second",
            "elapsed_seconds",
            "fixture",
            *FLAGS,
        },
    )
    s.require(
        value["schema_version"] == "s2-lifecycle-profile-observation-v1"
        and all(value[k] == job[k] for k in ("source_commit", "job_id", "plan_sha256", "uid"))
        and all(value[k] is False for k in FLAGS)
        and type(value["fixture"]) is bool
        and type(value["elapsed_seconds"]) in {int, float}
        and 0 <= value["elapsed_seconds"] <= 720
        and type(value["node"]) is str
        and re.fullmatch(r"[A-Za-z0-9_.-]{1,255}", value["node"])
        and a.scheduler_node(value["node"]) == value["node"],
        "Observation binding/flags/time drift.",
    )
    q._keys(value["channels"], CHANNELS)
    failed, checks = [], {}
    for channel in value["channels"].values():
        q._keys(channel, {"value", "error"})
        s.require(channel["error"] is None or channel["error"] in ERRORS, "Channel error grammar.")
        s.require(channel["error"] is None or channel["value"] is None, "Ambiguous channel.")

    def check(name, call):
        try:
            s.require(call() is True, "Prerequisite not observed.")
            checks[name] = True
        except (OSError, ValueError, UnicodeError, KeyError, TypeError, IndexError, AttributeError):
            checks[name] = False
            failed.append(name)

    channels = value["channels"]
    host, observer = channels["host"]["value"], channels["observer"]["value"]
    check(
        "host_user_namespaces_disabled",
        lambda: type(host["max_user_namespaces"]) is int and host["max_user_namespaces"] == 0,
    )
    check(
        "observer_namespace_and_identity",
        lambda: (
            observer["identity"]["uid"] == job["uid"] != 0
            and observer["namespaces"] == host["namespaces"]
            and observer["uid_map"].split() == ["0", "0", "4294967295"]
            and lc.stable(observer["identity"]) == lc.stable(value["observer_second"]["identity"])
            and observer["scopes"] == value["observer_second"]["scopes"]
            and observer["namespaces"] == value["observer_second"]["namespaces"]
        ),
    )
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
            record = channels[controller]["value"]
            descriptor = record["descriptor"]
            scope = observer["scopes"][controller]
            s.require(
                descriptor["mount"] == scope["mount"]
                and descriptor["worker"] == descriptor["supervisor"] == scope["scope"]
                and PurePosixPath(scope["scope"]).name == "step_batch"
                and PurePosixPath(scope["scope"]).parent.name == "job_" + job["job_id"]
                and descriptor["parent"] == str(PurePosixPath(scope["scope"]).parent),
                "Controller/current batch drift.",
            )
            e.hierarchy_policy(record["hierarchy"])
            inventory = record["inventory"]
            s.require(
                inventory["mount_identity"] == descriptor["mount_identity"]
                and inventory["parent_identity"] == descriptor["parent_identity"]
                and inventory["mount_id"] == descriptor["mount_id"]
                and inventory["groups"][0]["identity"] == descriptor["parent_identity"],
                "Controller parent/inventory drift.",
            )
            for role in ("mount", "parent", "worker", "supervisor"):
                lc.inode(descriptor[role + "_identity"])
            return True

        check(controller + "_whole_hierarchy_readonly", controller_check)
    check(
        "bounded_capture",
        lambda: (
            value["elapsed_seconds"] < 90 and all(v["error"] is None for v in channels.values())
        ),
    )
    return {
        "schema_version": "s2-lifecycle-profile-review-v1",
        "source_commit": job["source_commit"],
        "job_id": job["job_id"],
        "plan_sha256": job["plan_sha256"],
        "observation_sha256": s.digest(value),
        "observation_provenance": "software_fixture"
        if value["fixture"]
        else "kernel_reads_not_live_qualified",
        "checks": checks,
        "blockers": sorted(failed),
        "status": "prerequisites_observed_not_admitted" if not failed else "blocked_environment",
        "unproven": [
            "worker_no_new_privs_and_peer_binding",
            "worker_step_resources_and_disjoint_roles",
            "parent_persistence_and_no_escape_during_execution",
            "quiet_cleanup_and_scan_cadence",
            "filesystem_crash_durability",
        ],
        **FLAGS,
    }
