import hashlib
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts import pyomo_h400_e1 as e1
from scripts import pyomo_h400_e1_memory as memory
from scripts import pyomo_scaling_campaign as engine


def clean_snapshot():
    return {
        "status": "cgroup_memory_capabilities_present",
        "controller": "cgroup_v1",
        "job_cgroup": "/slurm/job_41",
        "effective_member_limit_bytes": e1.MEMORY_BYTES,
        "job_current_bytes": 1024,
        "job_peak_bytes": 2048,
        "job_memory_events": {"oom_kill": 0, "failcnt": 0, "under_oom": 0},
    }


def test_guard_latches_and_allows_exact_step_cleanup(monkeypatch):
    sample = clean_snapshot()
    crossed = {**sample, "job_peak_bytes": e1.limits()["e1_job_peak_bytes"]}
    getter = Mock(side_effect=[sample, sample, crossed, crossed])
    monkeypatch.setattr(memory.probe, "memory_snapshot", getter)
    guard = memory.JobMemoryGuard("41", scope=lambda _: ("cgroup_v1", None, None, None))
    with pytest.raises(ValueError, match="owned step"):
        guard.clock()
    guard.check()
    assert getter.call_count == 3
    assert guard.receipt()["guard_triggered"] is True


def test_supervisor_signals_only_the_bound_step_on_memory_guard(tmp_path, monkeypatch):
    controller = engine.o
    monkeypatch.setattr(controller.os, "getuid", lambda: 1271, raising=False)
    job = {"job_id": "41", "source_commit": "a" * 40, "plan_sha256": "b" * 64}
    process = Mock()
    process.poll.return_value = None
    process.wait.return_value = -15

    def popen(*_args, **_kwargs):
        controller.publish(tmp_path / "control/sto/entry.json", {
            **job, "mode": "sto", "step_id": "0", "started_monotonic": 0,
        })
        return process

    command = Mock(return_value=SimpleNamespace(
        returncode=0, stderr="",
        stdout="StepId=41.0 UserId=1271 CPUs=16 Nodes=1 Tasks=1 State=RUNNING NodeList=node",
    ))
    clock = Mock(side_effect=[0.0, 0.0, ValueError("Memory threshold")])
    outcome = controller.supervise(
        tmp_path, job["source_commit"], "sto", {"NodeList": "node", "UserId": "user(1271)"}, job,
        command=command, popen=popen, clock=clock, sleep=lambda _: None,
        step_cpus=16, bind_step=lambda *args: controller.step_binding(*args, cpus=16),
        reviewer=lambda *_: pytest.fail("No product review"),
    )
    assert [call.args[0] for call in command.call_args_list] == [
        ["scontrol", "-o", "show", "step", "41.0"], ["scancel", "--signal=TERM", "41.0"],
    ]
    assert outcome["status"] == "partial" and outcome["next_arm_allowed"] is False


def test_worker_rejects_a_different_job_scope():
    initial = clean_snapshot()
    with pytest.raises(ValueError, match="192 GiB hierarchical v1"):
        memory.require_matching_snapshot({**initial, "job_cgroup": "/slurm/job_42"}, initial)


def test_campaign_is_a_separate_four_cell_profile(tmp_path):
    original, current = tmp_path / engine.c.CAMPAIGN, tmp_path / memory.CAMPAIGN
    assert len(engine.campaign_cells(original)) == 90 and engine.campaign_limit(original) == 2
    assert engine.campaign_cells(current) == list(e1.CASES) and engine.campaign_limit(current) == 1


def test_start_requires_preceding_collected_pilot(tmp_path, monkeypatch):
    current = tmp_path / memory.CAMPAIGN
    first, second = e1.CASES[:2]
    manifest = {"cells": list(e1.CASES), "source_commit": "a" * 40}
    read = Mock(return_value=("row", "memory"))
    audit = Mock(return_value={"status": "e1_resource_criteria_rejected"})
    monkeypatch.setattr(e1, "read_cell", read)
    monkeypatch.setattr(e1, "evaluate", audit)
    engine.admit_cell(current, first, [], manifest)
    read.assert_not_called()
    with pytest.raises(ValueError, match="Prior E1 pilot"):
        engine.admit_cell(current, second, [], manifest)
    read.assert_called_once_with(current, first["id"])
    assert audit.call_args.kwargs == {"prefix": True}


def test_public_probe_evidence_rejects_any_changed_log(tmp_path):
    evidence = tmp_path / "docs/evidence"
    evidence.mkdir(parents=True)
    probe_name = "npad_pyomo_h400_e1_cgroup_probe.py"
    for version, job in enumerate(("2247610", "2247615"), 1):
        claim = tmp_path / f".mvp2-pyomo-h400-e1-cgroup-public-v{version}"
        claim.mkdir()
        (claim / "submitted-job.txt").write_text(job + "\n")
        (claim / probe_name).write_bytes(b"probe")
        log = claim / f"slurm-{job}.err"
        log.write_bytes(b"stderr")
        if version == 2:
            (claim / "source-identity.txt").write_bytes(memory.V2_IDENTITY)
        (evidence / f"npad_pyomo_h400_e1_cgroup_{job}_20261109.json").write_text(json.dumps({
            "probe_sha256": hashlib.sha256(b"probe").hexdigest(),
            "transferred_logs": {log.name: {"sha256": hashlib.sha256(b"stderr").hexdigest()}},
        }))
    assert len(memory.public_probe_evidence(tmp_path, tmp_path)) == 5
    log.write_bytes(b"changed")
    with pytest.raises(ValueError, match="2247615/slurm-2247615.err"):
        memory.public_probe_evidence(tmp_path, tmp_path)
