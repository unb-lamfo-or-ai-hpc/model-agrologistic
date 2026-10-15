"""Offline historical audit and closed, explicitly injected diagnostic components.

No operational dispatch, default kernel reader, file writer, claim or new slot.
The PR95 executable/auditor and its original negative result remain unchanged.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Closed diagnostic qualification only; no operational entry.")

import errno
import hashlib
import io
import math
import re
import tarfile
from pathlib import PurePosixPath

from scripts import mvp2_s2_lifecycle_profile_driver as old

p, q, s = old.p, old.q, old.s
SOURCE = "0b98e01cfb7b5cc27e6500c5c223ff39b17800bd"
JOB = "2211568"
PLAN_SHA = "140259faf649cf1559df73ee5ecdf4c7d23db32f9263ed4939483dd441cf9b7a"
ARCHIVE_SHA = "61d9ecf4504619d48238a16f0a6d96a91157704b530d3eea106c6242a204b4ab"
NS_STAGES = {"host_namespace_" + name for name in p.e.NAMESPACES}
STAGES = (
    NS_STAGES
    | {"host_user_namespace_limit"}
    | {
        controller + "_" + operation
        for controller in p.lc.CONTROLLERS
        for operation in ("placement", "mount_mapping", "descriptor", "hierarchy", "inventory")
    }
)
FLAGS = dict(p.FLAGS)


def execute(*_args, **_kwargs):
    raise PermissionError("Diagnostic software qualification does not admit execution.")


def batch_placement(controller, scope, job, uid):
    """Recognize exactly the two observed batch layouts, not arbitrary descendants.

    Path syntax alone is not ownership, filesystem or containment proof. The
    prospective observer must separately verify actual mounts/inodes/membership.
    """
    s.require(controller in p.lc.CONTROLLERS, "Enforcement controller required.")
    s.require(type(job) is str and re.fullmatch(r"[1-9][0-9]{0,9}", job), "Job grammar.")
    s.require(type(uid) is int and 0 < uid < 2**32, "UID grammar.")
    s._validate_scope(scope)
    leaf, mount = PurePosixPath(scope["scope"]), PurePosixPath(scope["mount"])
    if controller == "memory" and leaf.name == "task_0":
        step, layout = leaf.parent, "batch_task_0"
    else:
        step, layout = leaf, "batch_step"
    parent = step.parent
    s.require(
        step.name == "step_batch"
        and parent.name == "job_" + job
        and parent.parent.name == "uid_" + str(uid)
        and mount in parent.parents,
        "Exact current UID/job/batch ancestry required; do not guess a parent.",
    )
    return {
        "mount": str(mount),
        "parent": str(parent),
        "step": str(step),
        "member_scope": str(leaf),
        "layout": layout,
        **FLAGS,
    }


def capture_primitive(stage, read, *, clock, deadline, validate):
    """Keep controlled operation/errno, never exception text or arbitrary paths.

    Explicit callbacks are mandatory. This cannot hard-bound a blocking syscall;
    it merely records the deadline before/after a prospective read. No retry.
    """
    s.require(
        type(stage) is str
        and stage in STAGES
        and all(callable(v) for v in (read, clock, validate)),
        "Fixed stage and explicit dependencies required.",
    )
    s.require(type(deadline) in {int, float} and math.isfinite(deadline), "Finite deadline.")
    value, error, number = None, None, None
    at = clock()
    s.require(type(at) in {int, float} and math.isfinite(at), "Finite clock.")
    if at >= deadline:
        error = "deadline_exhausted"
    else:
        try:
            value = read()
            validate(value)
            s.require(len(q.c.encoded(value)) <= 4 * 1024**2, "Diagnostic value bound.")
        except OSError as exc:
            value = None
            number = exc.errno if type(exc.errno) is int and 1 <= exc.errno <= 65535 else None
            error = (
                "permission_denied"
                if isinstance(exc, PermissionError) or number in {errno.EACCES, errno.EPERM}
                else "not_found"
                if number in {errno.ENOENT, errno.ENOTDIR}
                else "operating_system_error"
            )
        except (ValueError, UnicodeError, KeyError, TypeError, IndexError, AttributeError):
            value, error = None, "invalid_evidence"
        after = clock()
        s.require(
            type(after) in {int, float} and math.isfinite(after) and after >= at, "Clock rollback."
        )
        if after >= deadline and error is None:
            value, error = None, "deadline_exhausted"
    return {
        "stage": stage,
        "value": value,
        "error": error,
        "errno": number,
        "software_components_only": True,
        **FLAGS,
    }


def host_components(*, read_namespace, read_limit, clock, deadline):
    """Independent host reads: unreadable PID1 namespace cannot erase the limit.

    No real reader/default is selected here; these are closed qualification seams.
    The zero-limit requirement is unchanged and any unavailable namespace blocks
    its own evidence obligation. No fallback, sudo, sysctl or namespace mutation.
    """
    s.require(
        callable(read_namespace) and callable(read_limit), "Explicit independent readers required."
    )
    channels = {}
    for name in p.e.NAMESPACES:
        channels[name] = capture_primitive(
            "host_namespace_" + name,
            lambda name=name: read_namespace(name),
            clock=clock,
            deadline=deadline,
            validate=p.lc.inode,
        )
    channels["max_user_namespaces"] = capture_primitive(
        "host_user_namespace_limit",
        lambda: s._uint(read_limit().strip()),
        clock=clock,
        deadline=deadline,
        validate=lambda value: s.require(
            type(value) is int and 0 <= value <= s.MAX_COUNTER, "Limit grammar."
        ),
    )
    return {"schema_version": "s2-closed-host-diagnostics-v1", "channels": channels, **FLAGS}


def timing_diagnosis(observation):
    """Separate a capture deadline from missing/invalid primitive evidence."""
    elapsed = observation["elapsed_seconds"]
    s.require(
        type(elapsed) in {int, float} and math.isfinite(elapsed) and 0 <= elapsed <= 720,
        "Capture duration grammar.",
    )
    q._keys(observation["channels"], p.CHANNELS)
    errors = {}
    for name, channel in observation["channels"].items():
        q._keys(channel, {"value", "error"})
        s.require(
            channel["error"] is None or channel["error"] in p.ERRORS,
            "Historical channel error grammar.",
        )
        s.require(
            channel["error"] is None or channel["value"] is None, "Ambiguous historical channel."
        )
        errors[name] = channel["error"]
    return {
        "elapsed_seconds": elapsed,
        "capture_within_budget": elapsed < 90,
        "deadline_reported_by_channel": any(
            error == "budget_exhausted" for error in errors.values()
        ),
        "channel_evidence_complete": all(error is None for error in errors.values()),
        "failed_channels": sorted(name for name, error in errors.items() if error is not None),
    }


def derive_outcome(review, observation):
    """Redact fixed-job conclusions; never reclassify the original certificate."""
    s.require(
        review["source_commit"] == SOURCE
        and review["job_id"] == JOB
        and review["plan_sha256"] == PLAN_SHA
        and review["disposition"] == "blocked_environment"
        and all(review[k] is False for k in FLAGS),
        "Fixed original review required.",
    )
    q._hash(review["accounting_sha256"])
    s.require(
        observation["source_commit"] == SOURCE
        and observation["job_id"] == JOB
        and observation["plan_sha256"] == PLAN_SHA
        and observation["fixture"] is False
        and all(observation[k] is False for k in FLAGS),
        "Fixed kernel-read observation required.",
    )
    job = {key: observation[key] for key in ("job_id", "source_commit", "plan_sha256", "uid")}
    s.require(review["profile"] == p.review(observation, job), "Original profile replay mismatch.")
    timing = timing_diagnosis(observation)
    observer = observation["channels"]["observer"]["value"]
    layouts = {
        key: batch_placement(key, observer["scopes"][key], JOB, observation["uid"])["layout"]
        for key in p.lc.CONTROLLERS
    }
    s.require(
        layouts == {"memory": "batch_task_0", "freezer": "batch_step", "cpuset": "batch_step"}
        and observation["channels"]["host"]["value"] is None,
        "Unexpected fixed-job evidence; do not generalize.",
    )
    return {
        "schema_version": "s2-profile-2211568-derived-audit-v1",
        "source_commit": SOURCE,
        "job_id": JOB,
        "archive_sha256": ARCHIVE_SHA,
        "plan_sha256": PLAN_SHA,
        "plan_anchor_provenance": "derived_from_bundle_and_recomputed_not_separately_attested",
        "original_disposition": review["disposition"],
        "original_observation_sha256": review["profile"]["observation_sha256"],
        "original_accounting_sha256": review["accounting_sha256"],
        "original_blockers": review["profile"]["blockers"],
        "timing_diagnosis": timing,
        "observed_batch_layouts": layouts,
        "host_namespace_limit": {"status": "unavailable_not_proven_unsupported", "value": None},
        "controller_diagnosis": {
            "memory": "direct_batch_leaf_assumption_rejects_observed_task_0_before_io",
            "freezer": "failing_primitive_and_errno_not_recorded",
            "cpuset": "failing_primitive_and_errno_not_recorded",
        },
        "host_diagnosis": "coupled_host_read_failed_primitive_and_errno_not_recorded",
        "original_certificate_preserved": True,
        "installed_compatibility": "unresolved",
        "next_action": "qualify_diagnostic_corrections_in_software_no_repeat_or_live_release",
        **FLAGS,
    }


def audit_components(path, expected_sha256):
    """Offline bounded read only, pinned to the user-supplied original archive."""
    s.require(expected_sha256 == ARCHIVE_SHA, "Fixed evidence checksum required.")
    review = old.audit(path, expected_sha256, SOURCE, PLAN_SHA, JOB)
    raw = old.a._file(path, old.LIMIT + 1024**2)
    s.require(hashlib.sha256(raw).hexdigest() == expected_sha256, "Archive changed after replay.")
    # The identical bytes already passed the original bounded allowlist/decompression
    # auditor. No archive path is ever extracted into a filesystem.
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        records = old.d.decode(archive.extractfile("raw-records.json").read())
    decoded = old.validate_records(records)
    s.require(
        decoded.get("observation.json") is not None, "Complete original observation required."
    )
    return derive_outcome(review, old.d.decode(decoded["observation.json"]))
