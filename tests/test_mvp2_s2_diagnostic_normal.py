"""Closed integration with fake scheduler/kernel/clock; never a live execution."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import mvp2_s2_diagnostic_normal as n
from tests import test_mvp2_s2_resource_normal as old

adapter = old.adapter


@pytest.fixture
def diagnostic(adapter):
    item = n.DiagnosticNormalAdapter(
        adapter.item,
        transport=adapter.transport,
        clock=adapter.clock,
        record=adapter.record,
        snapshot=adapter.snapshot,
        pid_absent=adapter.pid_absent,
        server_factory=adapter.server_factory,
        exe_path=adapter.exe_path,
        capture=adapter.capture,
    )
    item.preflight(
        uid=1000,
        pid=10,
        node="node",
        source=adapter.source,
        tool_sha256=adapter.item["tools_sha256"],
        python_sha256=adapter.item["python_sha256"],
    )
    item.test_clock = adapter.test_clock
    return item


def phases(adapter):
    (adapter.root / "worker").mkdir()
    for i, phase in enumerate(("build", "optimization", "export", "disposal")):
        n.c.write_once(
            adapter.root / "worker" / f"phase-{i}.json",
            {"nonce": adapter.item["nonce"], "phase": phase},
        )
    n.c.write_once(
        adapter.root / "worker/terminal.json",
        {"nonce": adapter.item["nonce"], "status": "synthetic_complete"},
    )


def preserve(adapter):
    adapter.preserve()
    return json.loads((adapter.root / "diagnostic-evidence.json").read_bytes())


def test_closed_launch_requires_explicit_transport_and_has_no_effect(diagnostic):
    with pytest.raises(PermissionError):
        diagnostic.launch()
    assert not diagnostic.launch_attempted and not Path(diagnostic.item["run"]).exists()
    with pytest.raises(ValueError):
        n.DiagnosticNormalAdapter(diagnostic.item, transport=None)


def test_fast_exit_with_retained_empty_scopes_uses_original_quiet_proof(diagnostic, tmp_path):
    old.start_fixture(diagnostic)
    phases(diagnostic)
    diagnostic.transport.count = 0
    diagnostic.transport.handle.process.poll = lambda: 0
    diagnostic.test_clock[0] = 1
    assert diagnostic.tick() == "TERM_exact_step"
    first = diagnostic.diagnostics[0]
    assert not first["diagnostic"]["any_unavailable"]
    assert first["payloads"]["members"]["members"] == 0
    assert first["payloads"]["accounting"]["500000.7"]["state"] == "COMPLETED"
    for seconds in (3, 5, 8):
        diagnostic.test_clock[0] = seconds
        diagnostic.tick()
    assert diagnostic.controller.state == "candidate_closed"
    value = preserve(diagnostic)
    result = n.review(value, diagnostic.item)
    assert result["controller_state"] == "candidate_closed"
    assert all(result[k] is False for k in n.p.FLAGS)
    before = {str(p): p.read_bytes() for p in diagnostic.root.rglob("*") if p.is_file()}
    carrier = n.collect_components(diagnostic.root, tmp_path / "collection", diagnostic.item)
    assert carrier["evidence"] == value
    assert before == {str(p): p.read_bytes() for p in diagnostic.root.rglob("*") if p.is_file()}
    with pytest.raises(FileExistsError):
        n.collect_components(diagnostic.root, tmp_path / "collection", diagnostic.item)


@pytest.mark.parametrize("missing", ["members", "resources"])
def test_fast_exit_missing_scope_or_membership_remains_blocked_but_keeps_lifecycle(
    diagnostic, missing
):
    old.start_fixture(diagnostic)
    phases(diagnostic)
    diagnostic.transport.count = 0
    diagnostic.transport.handle.process.poll = lambda: 0

    def unavailable(*args):
        raise FileNotFoundError("/private/secret")

    if missing == "members":
        diagnostic._members = unavailable
    else:
        diagnostic.snapshot = unavailable
    diagnostic.test_clock[0] = 1
    assert diagnostic.tick() == "TERM_exact_step"
    record = diagnostic.diagnostics[0]
    assert record["diagnostic"]["observations"][missing]["error_kind"] == "missing"
    event = diagnostic.controller.events[-1]["payload"]["inputs"]
    assert event["worker_done"] and event["step_terminal"] and event["all_known_pids_absent"]
    assert event["fault"] and event["scope_hash"] is None
    if missing == "members":
        assert event["members"] is None
    assert "/private" not in str(record)
    diagnostic.test_clock[0] = 392
    assert diagnostic.tick() == "preserve_blocked_attempt"
    assert n.review(preserve(diagnostic), diagnostic.item)["controller_state"] == "blocked"


@pytest.mark.parametrize("channel", ["launcher", "accounting", "products", "absence"])
def test_independent_channel_failure_does_not_erase_other_channels(diagnostic, channel):
    old.start_fixture(diagnostic)
    phases(diagnostic)

    def unavailable(*args, **kwargs):
        raise TimeoutError("secret")

    if channel == "launcher":
        diagnostic.handle.pump = unavailable
    elif channel == "accounting":
        original = diagnostic._query
        diagnostic._query = lambda tool, *args: (
            unavailable() if tool == "sacct" else original(tool, *args)
        )
    elif channel == "products":
        diagnostic._products = unavailable
    else:
        diagnostic.pid_absent = unavailable
    diagnostic.test_clock[0] = 1
    diagnostic.tick()
    record = diagnostic.diagnostics[0]
    assert record["diagnostic"]["observations"][channel]["error_kind"] == "timeout"
    assert len(record["payloads"]) == 5
    assert n.review(preserve(diagnostic), diagnostic.item)["controller_state"] == "term"


@pytest.mark.parametrize(
    "field", ["payload", "hash", "time", "sample", "event", "missing", "flag", "cadence"]
)
def test_replay_rejects_diagnostic_tampering(diagnostic, field):
    old.start_fixture(diagnostic)
    diagnostic.test_clock[0] = 1
    diagnostic.tick()
    value = preserve(diagnostic)
    record = value["diagnostics"][0]
    if field == "payload":
        record["payloads"]["members"]["members"] = 0
    elif field == "hash":
        record["diagnostic"]["observations"]["members"]["semantic_sha256"] = "0" * 64
    elif field == "time":
        record["seconds"] += 1
    elif field == "sample":
        record["sample_sha256"] = "0" * 64
    elif field == "event":
        record["event_sha256"] = "0" * 64
    elif field == "missing":
        del record["payloads"]["members"]
    elif field == "flag":
        record["live_containment_qualified"] = True
    else:
        record["cadence_exceeded"] = True
    with pytest.raises((ValueError, KeyError)):
        n.review(value, diagnostic.item)


def test_corrupt_final_is_forensic_not_reconstructed(diagnostic, tmp_path):
    old.start_fixture(diagnostic)
    diagnostic.test_clock[0] = 1
    diagnostic.tick()
    preserve(diagnostic)
    (diagnostic.root / "diagnostic-evidence.json").write_bytes(b"{")
    result = n.collect_components(diagnostic.root, tmp_path / "forensic", diagnostic.item)
    assert result["evidence"] is None
    assert result["review"]["status"] == "forensic_rejected_not_qualified"
    assert (diagnostic.root / "diagnostic-evidence.json").read_bytes() == b"{"


def test_latched_stop_and_cadence_still_block_cleanup(diagnostic):
    old.start_fixture(diagnostic)
    diagnostic.test_clock[0] = 1
    diagnostic.tick(force_fault=True)
    diagnostic.test_clock[0] = 8
    diagnostic.tick()
    assert diagnostic.diagnostics[-1]["cadence_exceeded"]
    assert diagnostic.controller.state == "kill"
    assert n.review(preserve(diagnostic), diagnostic.item)["controller_state"] == "kill"


@pytest.mark.parametrize("action", ["start", "batch", "worker", "collect", "--admit", "retry"])
def test_module_cli_denies_before_effects(tmp_path, action):
    result = subprocess.run(
        [sys.executable, "-B", "-I", n.__file__, action],
        cwd=tmp_path,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode != 0 and b"PermissionError" in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_frozen_runtime_does_not_select_diagnostic_adapter():
    root = Path(n.__file__).parent
    for name in (
        "mvp2_s2_resource_operational.py",
        "mvp2_s2_resource_normal.py",
        "npad_s2_resource_normal.sh",
    ):
        assert "DiagnosticNormalAdapter" not in (root / name).read_text()
    original = json.loads(
        (root.parent / "docs/evidence/s2_resource_normal_2210506_review.json").read_bytes()
    )
    assert original["outcome"] == "normal_not_qualified" and original["sample_count"] == 186


@pytest.mark.parametrize("drift", ["inode", "memory", "cpu"])
def test_resource_drift_never_becomes_fast_exit_acceptance(diagnostic, drift):
    old.start_fixture(diagnostic)
    phases(diagnostic)
    original = diagnostic.snapshot

    def wrong(scopes):
        value = original(scopes)
        if drift == "inode":
            value["scopes"]["memory"]["inode"][1] += 1
        elif drift == "memory":
            value["counters"]["effective_reported_memory_limit_bytes"] //= 2
        else:
            value["counters"]["cpuset_cpu_count"] = 3
        return value

    diagnostic.snapshot = wrong
    diagnostic.test_clock[0] = 1
    assert diagnostic.tick() == "TERM_exact_step"
    assert (
        diagnostic.diagnostics[0]["diagnostic"]["observations"]["resources"]["status"]
        == "unavailable"
    )
    assert diagnostic.controller.events[-1]["payload"]["inputs"]["worker_done"]
    assert n.review(preserve(diagnostic), diagnostic.item)["controller_state"] == "term"


@pytest.mark.parametrize("corrupt", ["sample", "resource_barrier", "extra_diagnostic"])
def test_collection_rejects_durable_journal_disagreement(diagnostic, tmp_path, corrupt):
    old.start_fixture(diagnostic)
    diagnostic.test_clock[0] = 1
    diagnostic.tick()
    preserve(diagnostic)
    name = {
        "sample": "sample-0000.json",
        "resource_barrier": "resource-barrier-0.json",
        "extra_diagnostic": "diagnostic-sample-0001.json",
    }[corrupt]
    (diagnostic.root / name).write_bytes(b"{}")
    result = n.collect_components(diagnostic.root, tmp_path / "rejected", diagnostic.item)
    assert result["evidence"] is None
    assert result["review"]["status"] == "forensic_rejected_not_qualified"
    assert (diagnostic.root / name).read_bytes() == b"{}"


def test_unknown_pid_absence_is_not_false_precision(diagnostic):
    old.start_fixture(diagnostic)
    diagnostic.pid_absent = lambda pid: None
    diagnostic.test_clock[0] = 1
    diagnostic.tick()
    assert (
        diagnostic.diagnostics[0]["diagnostic"]["observations"]["absence"]["status"]
        == "unavailable"
    )
    assert not diagnostic.controller.events[-1]["payload"]["inputs"]["all_known_pids_absent"]
    assert n.review(preserve(diagnostic), diagnostic.item)["controller_state"] == "term"


def test_interruption_has_no_retry_or_signal(diagnostic):
    old.start_fixture(diagnostic)

    def stop(**kwargs):
        raise KeyboardInterrupt

    diagnostic.handle.pump = stop
    with pytest.raises(KeyboardInterrupt):
        diagnostic.tick()
    assert not diagnostic.samples and not diagnostic.diagnostics
    assert not diagnostic.transport.signals


def test_missing_final_preserves_forensic_inventory(diagnostic, tmp_path):
    old.start_fixture(diagnostic)
    diagnostic.test_clock[0] = 1
    diagnostic.tick()
    preserve(diagnostic)
    (diagnostic.root / "diagnostic-evidence.json").unlink()
    result = n.collect_components(diagnostic.root, tmp_path / "missing", diagnostic.item)
    assert (
        result["evidence"] is None
        and result["review"]["status"] == "forensic_preserved_not_qualified"
    )
    assert "diagnostic-sample-0000.json" in result["inventory"]
