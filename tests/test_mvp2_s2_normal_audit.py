"""Audit and reproduce fast normal exit through fake effects only."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import mvp2_s2_normal_audit as n
from tests import test_mvp2_s2_resource_launcher as fixtures
from tests import test_mvp2_s2_resource_normal as normal

adapter = normal.adapter
attempt = fixtures.attempt


def test_bound_archive_audit_never_promotes_candidate(attempt, tmp_path):
    adapter, release, _value = attempt
    result = n.f.collect_components(
        adapter.root, tmp_path / "collection", release, fixtures.accounting()
    )
    before = fixtures.hashes(adapter.root)
    report = n.audit_archive(
        result["download"],
        result["sha256"],
        commit=adapter.item["source_commit"],
        job="500000",
        release_digest=n.f.s.digest(release),
    )
    assert report["outcome"] == "candidate_requires_independent_live_audit"
    assert report["barrier_count"] == 2
    assert report["cleanup_accepted"] is False and report["retry_admitted"] is False
    assert all(report[k] is False for k in n.f.normal.p.FLAGS)
    assert fixtures.hashes(adapter.root) == before
    with pytest.raises(ValueError):
        n.audit_archive(
            result["download"],
            "0" * 64,
            commit=adapter.item["source_commit"],
            job="500000",
            release_digest=n.f.s.digest(release),
        )


def test_member_disappearance_couples_old_reads_and_blocks_without_rewriting(adapter):
    normal.start_fixture(adapter)
    calls = []
    adapter.transport.handle.process.poll = lambda: 0
    adapter.pid_absent = lambda pid: True

    def unavailable():
        calls.append("members")
        raise FileNotFoundError("private path must not escape")

    adapter._members = unavailable
    adapter.snapshot = lambda _: pytest.fail("Snapshot incorrectly reached")
    adapter.test_clock[0] = 1
    assert adapter.tick() == "TERM_exact_step"
    sample = adapter.samples[-1]
    event = adapter.controller.events[-1]["payload"]["inputs"]
    assert sample["fault"] and sample["snapshot"] is None
    assert sample["accounting_sha256"] == n.f.s.digest({})
    assert event["members"] is None and event["writes_sha256"] is None
    assert not event["step_terminal"] and not event["worker_done"]
    assert event["launcher_reaped"] and event["all_known_pids_absent"]
    adapter.test_clock[0] = 392
    assert adapter.tick() == "preserve_blocked_attempt"
    assert calls == ["members", "members"]
    assert adapter.controller.state == "blocked"


@pytest.mark.parametrize("failed", n.CHANNELS)
def test_closed_diagnostics_continue_independent_reads_without_admission(failed):
    calls = []

    def reader(name):
        def read():
            calls.append(name)
            if name == failed:
                raise FileNotFoundError("/private/secret")
            return {"observed": name}

        return read

    result = n.observe_channels({name: reader(name) for name in n.CHANNELS})
    assert calls == list(n.CHANNELS)
    assert result["any_unavailable"]
    assert result["observations"][failed] == {
        "status": "unavailable",
        "semantic_sha256": None,
        "error_kind": "missing",
    }
    assert "/private" not in str(result)
    assert all(result[k] is False for k in n.f.normal.p.FLAGS)
    assert all(
        result["observations"][name]["status"] == "observed_not_qualified"
        for name in n.CHANNELS
        if name != failed
    )


@pytest.mark.parametrize(
    "error,kind",
    [
        (TimeoutError, "timeout"),
        (OSError, "os_error"),
        (ValueError, "invalid_observation"),
        (KeyError, "invalid_observation"),
    ],
)
def test_message_free_error_classes(error, kind):
    def bad():
        raise error("secret")

    result = n.observe_channels({name: bad for name in n.CHANNELS})
    assert all(v["error_kind"] == kind for v in result["observations"].values())
    assert "secret" not in str(result)


def test_absent_members_never_becomes_empty_or_accepted():
    result = n.observe_channels({name: lambda: {"members": None} for name in n.CHANNELS})
    assert not result["any_unavailable"]  # Hashable data is not validated live evidence.
    assert all(v["status"] == "observed_not_qualified" for v in result["observations"].values())
    assert not result["live_containment_qualified"] and not result["remote_cleanup_proven"]
    with pytest.raises(ValueError):
        n.observe_channels({"members": lambda: None})


@pytest.mark.parametrize("argv", [[], ["start"], ["retry"], ["probe"], ["h300"], ["audit"]])
def test_cli_denies_effect_routes_and_requires_all_external_bindings(tmp_path, argv):
    completed = subprocess.run(
        [sys.executable, "-B", "-I", n.__file__, *argv],
        cwd=tmp_path,
        capture_output=True,
        timeout=10,
    )
    assert completed.returncode != 0
    assert b"ModuleNotFoundError" not in completed.stderr
    assert list(tmp_path.iterdir()) == []


def test_no_operational_driver_or_controller_uses_diagnostic_seam():
    root = Path(n.__file__).parent
    for name in (
        "mvp2_s2_resource_operational.py",
        "mvp2_s2_resource_normal.py",
        "mvp2_s2_batch_adapter.py",
        "npad_s2_resource_normal.sh",
    ):
        assert "mvp2_s2_normal_audit" not in (root / name).read_text()
    readers = {name: lambda: {} for name in n.CHANNELS}
    unchanged = copy.copy(readers)
    n.observe_channels(readers)
    assert readers == unchanged


def test_interruption_is_not_swallowed_or_retried():
    calls = []

    def stop():
        calls.append("stop")
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        n.observe_channels({name: stop for name in n.CHANNELS})
    assert calls == ["stop"]


def test_archive_changed_between_reads_is_rejected(monkeypatch):
    monkeypatch.setattr(n.f, "audit", lambda *args, **kwargs: {})
    monkeypatch.setattr(n.f.a, "_file", lambda *args: b"changed")
    with pytest.raises(ValueError, match="Archive changed"):
        n.audit_archive("unused", "0" * 64, commit="a" * 40, job="500000", release_digest="b" * 64)


def test_public_negative_review_cannot_be_mistaken_for_normal_acceptance():
    path = (
        Path(__file__).resolve().parents[1] / "docs/evidence/s2_resource_normal_2210506_review.json"
    )
    report = json.loads(path.read_bytes())
    assert report["job_id"] == "2210506"
    assert (
        report["archive_sha256"]
        == "0239bbec7edd29cf384e7949d441ec6fb3e8474f77c735799978620fc74aa642"
    )
    assert report["portable_review"]["controller_state"] == "blocked"
    assert report["outcome"] == "normal_not_qualified"
    assert report["sample_count"] == report["fault_sample_count"] == 186
    assert report["barrier_count"] == 2 and report["usable_resource_sample_count"] == 0
    assert report["worker_terminal_status"] == "synthetic_complete"
    assert report["initial_resource_observation"]["worker_cpu_usage_ns"] is None
    assert report["cleanup_accepted"] is False and report["retry_admitted"] is False
    assert all(report[k] is False for k in n.f.normal.p.FLAGS)
