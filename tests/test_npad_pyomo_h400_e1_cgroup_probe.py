from pathlib import PurePosixPath

import pytest

from scripts.npad_pyomo_h400_e1_cgroup_probe import (
    EXPECTED_BYTES,
    cgroup_locations,
    memory_snapshot,
    watch,
)

MOUNTINFO = "24 20 0:21 / /sys/fs/cgroup rw - cgroup2 cgroup rw\n"


def test_job_and_step_paths():
    member = "0::/system.slice/slurmstepd.scope/job_41/step_0/user/task_0\n"
    version, mount, job, step = cgroup_locations(member, MOUNTINFO, "41")
    assert version == "cgroup_v2"
    assert mount == PurePosixPath("/sys/fs/cgroup")
    assert job == mount / "system.slice/slurmstepd.scope/job_41"
    assert step == job / "step_0/user/task_0"


@pytest.mark.parametrize("job_id", ["1", "42"])
def test_job_scope_must_match(job_id):
    with pytest.raises(ValueError, match="Slurm job scope"):
        cgroup_locations("0::/job_41/step_batch\n", MOUNTINFO, job_id)


def test_hybrid_uses_active_memory_controller():
    membership = "0::/unified\n5:memory:/slurm/uid_1000/job_41/step_0\n"
    mounts = MOUNTINFO + "25 20 0:22 / /cgroup/memory rw - cgroup cgroup rw,memory\n"
    version, mount, job, step = cgroup_locations(membership, mounts, "41")
    assert version == "cgroup_v1"
    assert mount == PurePosixPath("/cgroup/memory")
    assert job == mount / "slurm/uid_1000/job_41"
    assert step == job / "step_0"


def test_explicit_missing_memory_controller():
    with pytest.raises(ValueError, match="No memory-controller membership"):
        cgroup_locations("5:cpu:/job_41/step_batch\n", MOUNTINFO, "41")


@pytest.mark.parametrize("scenario", ["matching", "ancestor_limit", "step_limit", "oom"])
def test_memory_snapshot(tmp_path, scenario):
    job = tmp_path / "job_41"
    step = job / "step_0"
    step.mkdir(parents=True)
    (tmp_path / "memory.max").write_text(
        str(EXPECTED_BYTES - 1) if scenario == "ancestor_limit" else "max"
    )
    (job / "memory.max").write_text(str(EXPECTED_BYTES))
    (step / "memory.max").write_text(
        str(EXPECTED_BYTES - 1) if scenario == "step_limit" else "max"
    )
    (job / "memory.current").write_text("1024")
    (job / "memory.peak").write_text("2048")
    (job / "memory.events").write_text(f"oom {int(scenario == 'oom')}\noom_kill 0\n")
    result = memory_snapshot("cgroup_v2", tmp_path, job, step)
    assert (result["status"] == "cgroup_memory_capabilities_present") == (
        scenario == "matching"
    )
    assert result["job_peak_bytes"] == 2048


@pytest.mark.parametrize("scenario", ["matching", "hierarchy", "limit", "failcnt", "oom_kill"])
def test_v1_memory_snapshot(tmp_path, scenario):
    job = tmp_path / "job_41"
    step = job / "step_0"
    step.mkdir(parents=True)
    (job / "memory.limit_in_bytes").write_text(str(EXPECTED_BYTES))
    (job / "memory.use_hierarchy").write_text("0" if scenario == "hierarchy" else "1")
    effective = EXPECTED_BYTES - int(scenario == "limit")
    (step / "memory.stat").write_text(f"hierarchical_memory_limit {effective}\n")
    (job / "memory.usage_in_bytes").write_text("1024")
    (job / "memory.max_usage_in_bytes").write_text("2048")
    (job / "memory.failcnt").write_text(str(int(scenario == "failcnt")))
    (job / "memory.oom_control").write_text(
        f"oom_kill_disable 0\nunder_oom 0\noom_kill {int(scenario == 'oom_kill')}\n"
    )
    if scenario == "hierarchy":
        with pytest.raises(ValueError, match="not hierarchical"):
            memory_snapshot("cgroup_v1", tmp_path, job, step)
        return
    result = memory_snapshot("cgroup_v1", tmp_path, job, step)
    assert (result["status"] == "cgroup_memory_capabilities_present") == (scenario == "matching")
    assert result["job_peak_bytes"] == 2048


@pytest.mark.parametrize("usage", [1, 2])
def test_watch_uses_owned_process(tmp_path, monkeypatch, usage):
    from unittest.mock import Mock

    from scripts import npad_pyomo_h400_e1_cgroup_probe as probe

    process = Mock()
    process.wait.return_value = 0
    stop = Mock(return_value=-15)
    monkeypatch.setattr(probe, "stop_owned_process", stop)
    usage_file = tmp_path / "usage"
    usage_file.write_text(str(usage))
    assert watch(process, usage_file, ceiling=2) == {
        "trigger_bytes": 2 if usage == 2 else None,
        "child_exit": -15 if usage == 2 else 0,
    }
    assert stop.call_count == int(usage == 2)
