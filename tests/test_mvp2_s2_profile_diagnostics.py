"""Closed diagnostic correction and fixed-job redaction; fixtures, no NPAD reads."""

import copy
import errno
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import mvp2_s2_profile_diagnostics as d
from tests import test_mvp2_s2_lifecycle_profile as f


def scope(controller, suffix="step_batch", job=d.JOB, uid=1000):
    return {
        "mount": "/cg/" + controller,
        "scope": "/cg/" + controller + "/slurm/uid_" + str(uid) + "/job_" + job + "/" + suffix,
    }


def historical_fixture():
    """Emulated archive facts, not a claim to have performed kernel observations."""
    value = f.observation()
    value.update(
        source_commit=d.SOURCE,
        job_id=d.JOB,
        plan_sha256=d.PLAN_SHA,
        fixture=False,
        elapsed_seconds=0.04,
    )
    for key in ("host", *d.p.lc.CONTROLLERS):
        value["channels"][key] = {"value": None, "error": "invalid_or_unavailable"}
    observer = value["channels"]["observer"]["value"]
    for controller in d.p.lc.CONTROLLERS:
        observer["scopes"][controller] = scope(
            controller, "step_batch/task_0" if controller == "memory" else "step_batch"
        )
    value["observer_second"] = copy.deepcopy(observer)
    for key in ("allocation", "batch_members"):
        record = value["channels"][key]["value"]
        raw = d.p.query_text(record).replace("123", d.JOB).encode()
        value["channels"][key]["value"] = d.p.query_record(f.meta(raw), raw)
    job = {key: value[key] for key in ("job_id", "source_commit", "plan_sha256", "uid")}
    profile = d.p.review(value, job)
    review = {
        "source_commit": d.SOURCE,
        "job_id": d.JOB,
        "plan_sha256": d.PLAN_SHA,
        "disposition": "blocked_environment",
        "profile": profile,
        "accounting_sha256": "e" * 64,
        **d.FLAGS,
    }
    return review, value


@pytest.mark.parametrize("controller", d.p.lc.CONTROLLERS)
def test_direct_batch_is_bound_to_exact_uid_job_and_mount(controller):
    result = d.batch_placement(controller, scope(controller), d.JOB, 1000)
    assert result["layout"] == "batch_step"
    assert result["parent"].endswith("uid_1000/job_" + d.JOB)
    assert all(result[k] is False for k in d.FLAGS)


def test_memory_task0_resolves_job_not_step_as_parent():
    result = d.batch_placement("memory", scope("memory", "step_batch/task_0"), d.JOB, 1000)
    assert result["layout"] == "batch_task_0"
    assert result["parent"].endswith("job_" + d.JOB)
    assert result["step"].endswith("step_batch")
    assert result["member_scope"].endswith("step_batch/task_0")


@pytest.mark.parametrize(
    "controller,suffix",
    [
        ("memory", "step_batch/task_1"),
        ("memory", "step_batch/task_0/child"),
        ("memory", "step_0/task_0"),
        ("memory", "step_batch_other/task_0"),
        ("freezer", "step_batch/task_0"),
        ("cpuset", "step_batch/task_0"),
        ("memory", "step_batch/../step_batch"),
        ("memory", "step_batch/task_0/"),
    ],
)
def test_unreviewed_descendants_or_aliases_do_not_become_batch(controller, suffix):
    with pytest.raises(ValueError):
        d.batch_placement(controller, scope(controller, suffix), d.JOB, 1000)


@pytest.mark.parametrize("change", ["job", "uid", "mount", "relative", "prefix", "controller"])
def test_path_identity_drift_rejected(change):
    item = scope("memory", "step_batch/task_0")
    controller = "memory"
    if change == "job":
        item = scope("memory", "step_batch/task_0", job="999")
    elif change == "uid":
        item = scope("memory", "step_batch/task_0", uid=1001)
    elif change == "mount":
        item["mount"] = "/other"
    elif change == "relative":
        item["scope"] = "relative"
    elif change == "prefix":
        item = scope("memory", "step_batch/task_0", uid=10000)
    else:
        controller = "cpuacct"
    with pytest.raises(ValueError):
        d.batch_placement(controller, item, d.JOB, 1000)


@pytest.mark.parametrize(
    "number,label",
    [
        (errno.EACCES, "permission_denied"),
        (errno.EPERM, "permission_denied"),
        (errno.ENOENT, "not_found"),
        (errno.EIO, "operating_system_error"),
        (errno.ESTALE, "operating_system_error"),
    ],
)
def test_controlled_errno_survives_without_exception_text(number, label):
    def fail():
        raise OSError(number, "private-path-secret")

    result = d.capture_primitive(
        "freezer_descriptor", fail, clock=lambda: 0, deadline=90, validate=lambda _v: None
    )
    assert result["error"] == label and result["errno"] == number and result["value"] is None
    assert "private-path-secret" not in json.dumps(result)
    assert all(result[k] is False for k in d.FLAGS)


def test_unreadable_pid1_does_not_erase_readable_namespace_limit():
    seen = []

    def namespace(name):
        seen.append(name)
        raise PermissionError(errno.EACCES, "private namespace")

    result = d.host_components(
        read_namespace=namespace, read_limit=lambda: "6191584\n", clock=lambda: 0, deadline=90
    )
    assert seen == list(d.p.e.NAMESPACES)
    assert result["channels"]["max_user_namespaces"]["value"] == 6191584
    assert all(result["channels"][key]["error"] == "permission_denied" for key in d.p.e.NAMESPACES)
    assert all(result[k] is False for k in d.FLAGS)


def test_unavailable_limit_does_not_erase_readable_namespaces():
    def missing():
        raise FileNotFoundError(errno.ENOENT, "private limit")

    result = d.host_components(
        read_namespace=lambda _name: [1, 2], read_limit=missing, clock=lambda: 0, deadline=90
    )
    assert all(result["channels"][key]["value"] == [1, 2] for key in d.p.e.NAMESPACES)
    assert result["channels"]["max_user_namespaces"]["error"] == "not_found"


@pytest.mark.parametrize("raw", ["-1", "True", "", "1.5", "x", "9" * 21])
def test_invalid_limit_remains_invalid_not_zero(raw):
    result = d.host_components(
        read_namespace=lambda _name: [1, 2], read_limit=lambda: raw, clock=lambda: 0, deadline=90
    )
    assert result["channels"]["max_user_namespaces"]["value"] is None
    assert result["channels"]["max_user_namespaces"]["error"] == "invalid_evidence"


def test_expired_deadline_never_calls_reader_or_retries():
    called = []
    result = d.capture_primitive(
        "host_user_namespace_limit",
        lambda: called.append(1),
        clock=lambda: 90,
        deadline=90,
        validate=lambda _v: None,
    )
    assert called == [] and result["error"] == "deadline_exhausted"


def test_slow_success_cannot_extend_deadline_or_become_positive():
    times = iter([89, 91])
    result = d.capture_primitive(
        "cpuset_inventory",
        lambda: [1],
        clock=lambda: next(times),
        deadline=90,
        validate=lambda _v: None,
    )
    assert result["error"] == "deadline_exhausted" and result["value"] is None


def test_clock_rollback_rejects_result():
    times = iter([5, 4])
    with pytest.raises(ValueError):
        d.capture_primitive(
            "cpuset_inventory",
            lambda: 1,
            clock=lambda: next(times),
            deadline=90,
            validate=lambda _v: None,
        )


@pytest.mark.parametrize(
    "stage", ["unknown", "private-path-secret", "worker_release", "scancel", "memory_chmod"]
)
def test_arbitrary_stage_not_a_dispatch_capability(stage):
    with pytest.raises(ValueError):
        d.capture_primitive(
            stage, lambda: 0, clock=lambda: 0, deadline=90, validate=lambda _v: None
        )


def test_unavailable_evidence_is_not_a_timeout_and_preserves_old_predicate():
    review, value = historical_fixture()
    assert review["profile"]["checks"]["bounded_capture"] is False
    before = copy.deepcopy((review, value))
    timing = d.timing_diagnosis(value)
    assert timing["capture_within_budget"] and not timing["deadline_reported_by_channel"]
    assert not timing["channel_evidence_complete"]
    result = d.derive_outcome(review, value)
    assert result["original_disposition"] == "blocked_environment"
    assert result["host_namespace_limit"]["value"] is None
    assert result["installed_compatibility"] == "unresolved"
    assert (review, value) == before
    assert all(result[k] is False for k in d.FLAGS)
    encoded = json.dumps(result)
    assert "/cg/" not in encoded and "uid_1000" not in encoded and '"pid"' not in encoded


@pytest.mark.parametrize("key", d.FLAGS)
def test_derived_audit_cannot_accept_admitting_review(key):
    review, value = historical_fixture()
    review[key] = True
    with pytest.raises(ValueError):
        d.derive_outcome(review, value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_commit", "c" * 40),
        ("job_id", "999"),
        ("plan_sha256", "c" * 64),
        ("disposition", "accepted"),
    ],
)
def test_fixed_original_anchor_drift_blocks(field, value):
    review, obs = historical_fixture()
    review[field] = value
    with pytest.raises(ValueError):
        d.derive_outcome(review, obs)


def test_no_self_certifying_or_unknown_archive_checksum(monkeypatch):
    monkeypatch.setattr(d.old, "audit", lambda *_a: pytest.fail("No read before expected checksum"))
    with pytest.raises(ValueError):
        d.audit_components("unread", "c" * 64)


def test_public_derived_certificate_is_redacted_and_negative():
    value = json.loads(Path("docs/evidence/s2_profile_2211568_review.json").read_text())
    assert value["archive_sha256"] == d.ARCHIVE_SHA and value["job_id"] == d.JOB
    assert value["original_disposition"] == "blocked_environment"
    assert value["timing_diagnosis"]["capture_within_budget"]
    assert value["host_namespace_limit"]["value"] is None
    assert all(value[k] is False for k in d.FLAGS)
    text = json.dumps(value)
    assert "vrrcelestino" not in text and "/proc/" not in text and "uid_1271" not in text


@pytest.mark.parametrize(
    "action",
    ["start", "worker", "normal", "release", "stop", "collect", "retry", "native", "h300", "admit"],
)
def test_all_direct_entries_deny_before_io(action):
    with pytest.raises(PermissionError):
        d.execute(action)
    result = subprocess.run(
        [sys.executable, "-B", "-I", "scripts/mvp2_s2_profile_diagnostics.py", action],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode != 0 and b"PermissionError" in result.stderr
