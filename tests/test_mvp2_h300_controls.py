"""Real synthetic children plus deterministic deadline/serial-ledger regressions."""

import copy
import os
import sys
import time
from pathlib import Path

import pytest

from scripts import mvp2_h300_controls as control
from tests.test_mvp2_h300_thread_contract import environment

IDENTITY = "a" * 64
FIXTURE = Path(__file__).with_name("h300_control_fixture.py")


@pytest.mark.parametrize("phase", control.PHASES)
def test_phase_cap_never_resets(phase):
    guard = control.Deadlines(0, 100, caps=(10, 10, 10, 10))
    index = control.PHASES.index(phase)
    for i in range(index + 1):
        assert guard.observe(i, list(control.PHASES[: i + 1])) is None
    assert guard.observe(index + 9, list(control.PHASES[: index + 1])) is None
    assert guard.observe(index + 10, list(control.PHASES[: index + 1])) == f"{phase}_watchdog"


def test_late_transition_does_not_hide_overrun():
    guard = control.Deadlines(0, 100, caps=(10,) * 4)
    assert guard.observe(0, ["build"]) is None
    assert guard.observe(10, ["build", "optimization"]) == "build_watchdog"


@pytest.mark.parametrize(
    "events", [["optimization"], ["build", "build"], list(control.PHASES) + ["cleanup"]]
)
def test_bad_phase_order(events):
    with pytest.raises(ValueError):
        control.Deadlines(0, 100).observe(1, events)


def test_clock_and_phase_rollback():
    guard = control.Deadlines(2, 100)
    guard.observe(3, ["build", "optimization"])
    with pytest.raises(ValueError):
        guard.observe(2, ["build", "optimization"])
    with pytest.raises(ValueError):
        guard.observe(4, ["build"])


@pytest.mark.parametrize("deadline", [5, 40])
def test_hard_cap_even_with_new_phase(deadline):
    guard = control.Deadlines(0, deadline, caps=(10,) * 4)
    assert guard.observe(deadline, list(control.PHASES)) == "child_or_block_watchdog"


def test_journal_is_contiguous_exclusive_and_identity_bound(tmp_path):
    journal = control.PhaseJournal(tmp_path / "journal", IDENTITY)
    for phase in control.PHASES:
        journal.enter(phase)
    assert control.phase_events(journal.directory, IDENTITY) == list(control.PHASES)
    with pytest.raises(ValueError):
        journal.enter("cleanup")
    with pytest.raises(FileExistsError):
        control.PhaseJournal(journal.directory, IDENTITY)
    with pytest.raises(ValueError):
        control.phase_events(journal.directory, "b" * 64)


def test_journal_hole_and_duplicate_json_rejected(tmp_path):
    control.write_once(tmp_path / "phase-1.json", {"anything": 1})
    with pytest.raises(ValueError):
        control.phase_events(tmp_path, IDENTITY)
    for text in ('{"x":1,"x":2}', '{"nested":{"x":1,"x":2}}', '{"x":NaN}'):
        with pytest.raises(ValueError):
            control.decode_json(text)


def test_pipeline_closes_cleanup_on_export_failure(tmp_path):
    journal = control.PhaseJournal(tmp_path / "journal", IDENTITY)
    cleaned = []

    def export(_result):
        raise RuntimeError("Synthetic failure")

    with pytest.raises(RuntimeError):
        control.run_phases(
            journal, lambda: "model", lambda _model: "result", export, lambda: cleaned.append(True)
        )
    assert cleaned == [True]
    assert control.phase_events(journal.directory, IDENTITY) == list(control.PHASES)


@pytest.mark.parametrize(
    "mode,reason",
    [
        ("complete", None),
        ("fail", "child_failure"),
        ("build_hang", "build_watchdog"),
        ("opt_hang", "optimization_watchdog"),
        ("export_hang", "export_validation_watchdog"),
        ("cleanup_hang", "cleanup_watchdog"),
        ("failed_cleanup_hang", "cleanup_watchdog"),
        ("malformed", "control_error"),
    ],
)
def test_real_short_child_is_reaped(mode, reason, tmp_path):
    journal = tmp_path / "journal"
    process = control.spawn_owned([sys.executable, str(FIXTURE), str(journal), IDENTITY, mode])
    # Start-up envelope is independent of shortened post-start phase windows.
    report = control.supervise(
        process,
        journal,
        IDENTITY,
        time.monotonic() + 8,
        caps=(2, 0.15, 0.15, 0.15),
        poll_seconds=0.01,
    )
    assert report["stop_reason"] == reason
    assert process.poll() is not None
    assert report["production_admitted"] is False
    if mode in {"complete", "fail"}:
        assert process.returncode == (0 if mode == "complete" else 3)
    assert report["owned_group_closed"] is (os.name == "posix")
    assert report["allocation_tree_closed"] is False


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group semantics; Linux CI qualifies")
@pytest.mark.parametrize("mode", ["ignore_term", "orphan"])
def test_group_escalation_and_orphan_stop(mode, tmp_path):
    process = control.spawn_owned(
        [sys.executable, str(FIXTURE), str(tmp_path / "journal"), IDENTITY, mode]
    )
    report = control.supervise(
        process,
        tmp_path / "journal",
        IDENTITY,
        time.monotonic() + 4,
        caps=(0.8, 0.1, 0.1, 0.1),
        poll_seconds=0.01,
    )
    assert process.poll() is not None
    assert report["stop_reason"] in {"build_watchdog", "live_descendants"}
    # A remaining zombie/group gives false, never permission to start another arm.
    assert report["production_admitted"] is False


def closed_records():
    return (
        {
            "return_code": 0,
            "stop_reason": None,
            "owned_group_closed": True,
            "allocation_tree_closed": True,
        },
        {
            "integrity_accepted": True,
            "products_closed": True,
            "censor_reason": "time_limit",
            "disposition": "feasible_partial_hierarchy",
        },
    )


def test_all_distinct_censored_arms_are_one_shot(tmp_path):
    ledger = control.BlockLedger(tmp_path / "ledger", environment(), 0)
    for index, threads in enumerate(control.design.ORDER):
        ledger.begin(threads, environment(threads), index * 3900)
        assert ledger.finish(*closed_records(), index * 3900 + 3000)
    assert ledger.not_executed() == []
    with pytest.raises(ValueError):
        ledger.begin(4, environment(), 20000)
    with pytest.raises(FileExistsError):
        control.BlockLedger(ledger.directory, environment(), 0)


@pytest.mark.parametrize(
    "part,key,value",
    [
        (0, "return_code", 1),
        (0, "stop_reason", "optimization_watchdog"),
        (0, "owned_group_closed", False),
        (0, "allocation_tree_closed", False),
        (1, "integrity_accepted", False),
        (1, "products_closed", False),
        (1, "censor_reason", "scheduler_memory"),
        (1, "censor_reason", "preemption"),
        (1, "disposition", "unvalidated_incumbent"),
    ],
)
def test_adverse_closure_stops_remaining_block(part, key, value, tmp_path):
    ledger = control.BlockLedger(tmp_path / "ledger", environment(), 0)
    ledger.begin(4, environment(), 1)
    records = list(closed_records())
    records[part][key] = value
    assert ledger.finish(*records, 10) is False
    assert ledger.not_executed() == [1, 8, 2, 16]
    with pytest.raises(ValueError):
        ledger.begin(1, environment(1), 11)


def test_overlap_repeat_environment_and_headroom_stop(tmp_path):
    ledger = control.BlockLedger(tmp_path / "ledger", environment(), 0)
    ledger.begin(4, environment(), 0)
    with pytest.raises(ValueError):
        ledger.begin(4, environment(), 0)
    ledger.finish(*closed_records(), 10)
    with pytest.raises(ValueError):
        ledger.begin(4, environment(), 11)
    changed = copy.deepcopy(environment(1))
    changed["node"] = "other-node"
    with pytest.raises(ValueError):
        ledger.begin(1, changed, 11)
    assert ledger.stopped
    other = control.BlockLedger(tmp_path / "other", environment(), 0)
    with pytest.raises(ValueError):
        other.begin(4, environment(), 17000)
    assert other.stopped


@pytest.mark.parametrize("fake_flags", [{}, {"accepted": True}, {"production_admitted": True}])
def test_execution_gate_cannot_be_enabled(fake_flags):
    with pytest.raises(PermissionError):
        control.execute_h300(**fake_flags)


def resource_rows():
    return [
        {
            "elapsed_seconds": t,
            "phase": "optimization",
            "process_tree_rss_bytes": (1 + t) * 1024**3,
            "process_tree_cpu_seconds": 10 - t,
            "cgroup_current_bytes": 5 * 1024**3,
            "application_peak_rss_bytes": None,
            "native_peak_decimal_gb": 2,
            "observation_errors": 0,
        }
        for t in (0, 2)
    ]


def test_scoped_resource_peaks_do_not_impute_exited_child_cpu():
    summary = control.resource_summary(resource_rows())
    assert summary["sampled_tree_peak_rss_gib"] == 3
    assert summary["sampled_cgroup_peak_gib"] == 5
    assert summary["observed_application_highwater_rss_gib"] is None
    assert summary["observed_native_memory_gib"] == 2 * 10**9 / 1024**3
    assert summary["last_live_tree_cpu_seconds"] == 8
    assert summary["measured_lifetime_cpu_hours"] is None
    assert summary["maximum_sample_gap_seconds"] == 2
    assert not summary["continuous_peak_coverage_proven"]


@pytest.mark.parametrize(
    "key,value",
    [
        ("elapsed_seconds", -1),
        ("phase", "unknown"),
        ("process_tree_rss_bytes", float("nan")),
        ("observation_errors", True),
    ],
)
def test_resource_schema_drift_rejected(key, value):
    rows = resource_rows()
    rows[1][key] = value
    with pytest.raises(ValueError):
        control.resource_summary(rows)


def test_missing_samples_are_not_zero():
    summary = control.resource_summary([])
    assert summary["samples"] == 0
    assert summary["sampled_tree_peak_rss_gib"] is None
    assert summary["last_live_tree_cpu_seconds"] is None


def test_invalid_supervisor_config_still_reaps_owned_child(tmp_path):
    process = control.spawn_owned(
        [sys.executable, str(FIXTURE), str(tmp_path / "journal"), IDENTITY, "build_hang"]
    )
    with pytest.raises(ValueError):
        control.supervise(
            process, tmp_path / "journal", IDENTITY, time.monotonic() + 4, poll_seconds=2
        )
    assert process.poll() is not None


def test_failure_cleanup_has_its_own_cap_and_cannot_rollback():
    guard = control.Deadlines(0, 100, caps=(10, 10, 10, 2))
    guard.observe(1, ["build"], aborted=True)
    assert guard.observe(2, ["build"], aborted=True) is None
    assert guard.observe(3, ["build"], aborted=True) == "cleanup_watchdog"
    with pytest.raises(ValueError):
        guard.observe(4, ["build"], aborted=False)


def test_cleanup_still_called_if_failure_journal_publication_fails(tmp_path):
    journal = control.PhaseJournal(tmp_path / "journal", IDENTITY)
    control.write_once(journal.directory / "failure-cleanup.json", {})
    cleaned = []

    def build():
        raise RuntimeError("synthetic build failure")

    with pytest.raises(FileExistsError):
        control.run_phases(
            journal, build, lambda _m: None, lambda _r: None, lambda: cleaned.append(True)
        )
    assert cleaned == [True]
