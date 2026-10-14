"""Transferred-archive interpretation with fake records only; no NPAD effects."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import mvp2_s2_fast_exit_audit as audit
from tests import test_mvp2_s2_fast_exit as fixtures

C, J, H = fixtures.C, fixtures.J, fixtures.H


def observation_records():
    obs = fixtures.report()
    for item in obs["samples"]:
        channels = item["channels"]
        channels["controllers"] = {
            "status": "available",
            "value": {k: {"status": "missing", "value": None} for k in audit.f.s.CONTROLLERS},
        }
        channels["controllers"]["value"]["cpuacct"] = {
            "status": "available",
            "value": {
                "identity": [32, 1979],
                "files": {
                    "cgroup.procs": {"status": "available", "value": [7, 8]},
                    "cpuacct.usage": {"status": "available", "value": 100},
                },
            },
        }
        channels["leader"] = {"status": "available", "value": "known_pid_absent"}
        channels["accounting"] = {
            "status": "available",
            "value": {
                "stdout_sha256": H,
                "data": audit.f.a.accounting(f"{J}.0|COMPLETED|0:0|1", J),
            },
        }
        channels["products"] = {
            "status": "available",
            "value": {
                name: {"status": "available", "value": {"sha256": H}}
                for name in [*[f"phase-{i}.json" for i in range(4)], "terminal.json"]
            },
        }
    return fixtures.records(obs)


def replay(tmp_path, records, **changes):
    path = tmp_path / "archive.tar.gz"
    audit.f.d.pack(path, records)
    before = audit.f.a.sha_file(path)
    args = {"commit": C, "job": J, "plan_sha": H, **changes}
    result = audit.audit_archive(path, before, **args)
    assert audit.f.a.sha_file(path) == before
    return result


def test_observed_missing_scopes_require_decision_never_cleanup(tmp_path):
    value = replay(tmp_path, observation_records())
    assert value["outcome"] == "post_exit_step_scopes_unobservable_protocol_decision_required"
    assert value["protocol_decision_required"] is True and value["sample_count"] == 5
    assert value["reported_product_receipts_stable"] is True
    assert all(sample["exact_step_member_count"] is None for sample in value["samples"])
    assert all(sample["shared_cpuacct_direct_member_count"] == 2 for sample in value["samples"])
    assert all(value[key] is False for key in audit.f.FLAGS)
    for key in (
        "cleanup_accepted",
        "normal_retry_admitted",
        "scope_deletion_mechanism_proven",
        "original_2210506_exception_identified",
        "worker_only_cpu_usage_available",
        "full_run_memory_peak_available",
        "raw_product_contents_in_portable_archive",
        "exact_post_exit_rpc_failure_reason_in_portable_archive",
    ):
        assert value[key] is False


@pytest.mark.parametrize(
    "key,value", [("commit", "d" * 40), ("job", "54321"), ("plan_sha", "b" * 64)]
)
def test_external_identity_drift_rejected(tmp_path, key, value):
    with pytest.raises(ValueError):
        replay(tmp_path, observation_records(), **{key: value})


def test_checksum_drift_before_interpretation(tmp_path):
    path = tmp_path / "archive.tar.gz"
    audit.f.d.pack(path, observation_records())
    with pytest.raises(ValueError, match="checksum"):
        audit.audit_archive(path, "0" * 64, commit=C, job=J, plan_sha=H)


def test_archive_changed_between_validation_and_interpretation(monkeypatch, tmp_path):
    path = tmp_path / "archive.tar.gz"
    audit.f.d.pack(path, observation_records())
    sha = audit.f.a.sha_file(path)
    original = audit.f.audit

    def change(*args):
        result = original(*args)
        path.write_bytes(b"corrupt disposable test carrier")
        return result

    monkeypatch.setattr(audit.f, "audit", change)
    with pytest.raises(ValueError, match="changed"):
        audit.audit_archive(path, sha, commit=C, job=J, plan_sha=H)


def test_forensic_only_and_no_samples_stay_unknown(tmp_path):
    value = replay(tmp_path, fixtures.records(None))
    assert value["outcome"] == "forensic_only_no_live_qualification"
    assert value["sample_count"] == 0 and value["reported_product_receipts_stable"] is None
    assert value["initial_reported_observations"] is None
    assert value["cleanup_accepted"] is False


def test_nonzero_leaf_is_incomplete_not_success(tmp_path):
    records = observation_records()
    obs = records["observation.json"]
    obs.update(status="incomplete", local_client_returncode=2)
    value = replay(tmp_path, records)
    assert value["outcome"] == "incomplete_observation_no_live_qualification"
    assert len(value["samples"]) == 5 and value["cleanup_accepted"] is False


@pytest.mark.parametrize(
    "failed", ["controllers", "members", "products", "accounting", "leader", "step"]
)
def test_unavailable_channel_does_not_erase_others(tmp_path, failed):
    records = observation_records()
    records["observation.json"]["samples"][0]["channels"][failed] = fixtures.unavailable()
    value = replay(tmp_path, records)
    item = value["samples"][0]
    assert item["channel_statuses"][failed] == "unavailable"
    if failed != "products":
        assert item["product_file_statuses"]["terminal.json"] == "available"
    if failed != "accounting":
        assert item["accounted_worker_step"]["state"] == "COMPLETED"
    assert value["cleanup_accepted"] is False


def test_real_observed_empty_not_missing_and_not_automatic_cleanup(tmp_path):
    records = observation_records()
    for item in records["observation.json"]["samples"]:
        item["channels"]["members"] = {
            "status": "available",
            "value": {"stdout_sha256": H, "data": []},
        }
    value = replay(tmp_path, records)
    assert all(item["exact_step_member_count"] == 0 for item in value["samples"])
    assert value["outcome"] == "post_exit_observations_require_independent_protocol_review"
    assert value["cleanup_accepted"] is False


def test_changing_product_hashes_not_reported_stable(tmp_path):
    records = observation_records()
    records["observation.json"]["samples"][-1]["channels"]["products"]["value"]["terminal.json"][
        "value"
    ]["sha256"] = "b" * 64
    assert replay(tmp_path, records)["reported_product_receipts_stable"] is False


def test_missing_product_hashes_not_reported_stable(tmp_path):
    records = observation_records()
    records["observation.json"]["samples"][0]["channels"]["products"]["value"]["terminal.json"] = {
        "status": "missing",
        "value": None,
    }
    assert replay(tmp_path, records)["reported_product_receipts_stable"] is False


def test_unlimited_direct_memory_not_effective_unlimited_or_peak():
    initial = {
        "summary": None,
        "limits": {
            "worker": {
                "error_kind": None,
                "memory_limit_bytes": 9223372036854771712,
                "hierarchical_memory_limit_bytes": 268435456,
                "cpuset_cpu_count": 2,
            }
        },
    }
    result = audit.initial_summary(initial)["limits"]["worker"]
    assert result["direct_limit_is_unlimited_sentinel"] is True
    assert result["reported_effective_memory_limit_bytes"] == 268435456
    initial["limits"]["worker"]["error_kind"] = "FileNotFoundError"
    assert (
        audit.initial_summary(initial)["limits"]["worker"]["reported_effective_memory_limit_bytes"]
        is None
    )


@pytest.mark.parametrize(
    "action", ["start", "normal", "adverse", "native", "h300", "retry", "admit"]
)
def test_cli_non_audit_denies_before_effects(action, tmp_path):
    run = subprocess.run(
        [sys.executable, "-B", "-I", str(Path(audit.__file__).resolve()), action],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert run.returncode != 0 and "audit only" in run.stderr
    assert list(tmp_path.iterdir()) == []


def test_committed_public_review_has_fixed_refs_no_personal_paths():
    path = Path(__file__).parents[1] / "docs/evidence/s2_fast_exit_2210952_review.json"
    value = json.loads(path.read_bytes())
    assert value["source_commit"] == "021ba83d99132c5b872873439ae00cc82aec3793"
    assert value["job_id"] == "2210952"
    assert (
        value["archive_sha256"]
        == "e3c01f0b5db22b99b61b3a214eee42a694d1893d0f52c5b9b370d6a486b7561d"
    )
    assert (
        value["plan_sha256"] == "bd1b423377bf4aaaacf2fa6e5a03f1c2e6bb0c3cef4d6c044c81e504be720359"
    )
    assert value["sample_count"] == 5 and all(value[k] is False for k in audit.f.FLAGS)
    assert value["cleanup_accepted"] is False and value["protocol_decision_required"] is True
    for role in ("worker", "supervisor"):
        limits = value["initial_reported_observations"]["limits"][role]
        assert limits["direct_memory_limit_bytes"] == 9223372036854771712
        assert limits["direct_limit_is_unlimited_sentinel"] is True
    assert not any(
        text in json.dumps(value) for text in ("/home/", "C:/", "D:/", "C:\\", 'pid":', 'uid":')
    )


def test_interpretation_does_not_mutate_records(tmp_path):
    records = observation_records()
    before = copy.deepcopy(records)
    replay(tmp_path, records)
    assert records == before
