from pathlib import PurePosixPath

import pytest

from scripts.npad_pyomo_h400_e1_cgroup_probe import (
    EXPECTED_BYTES,
    cgroup_locations,
    memory_snapshot,
)

MOUNTINFO = "24 20 0:21 / /sys/fs/cgroup rw - cgroup2 cgroup rw\n"


def test_job_and_step_paths():
    member = "0::/system.slice/slurmstepd.scope/job_41/step_0/user/task_0\n"
    mount, job, step = cgroup_locations(member, MOUNTINFO, "41")
    assert mount == PurePosixPath("/sys/fs/cgroup")
    assert job == mount / "system.slice/slurmstepd.scope/job_41"
    assert step == job / "step_0/user/task_0"


@pytest.mark.parametrize("job_id", ["1", "42"])
def test_job_scope_must_match(job_id):
    with pytest.raises(ValueError, match="Slurm job scope"):
        cgroup_locations("0::/job_41/step_batch\n", MOUNTINFO, job_id)


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
    result = memory_snapshot(tmp_path, job, step)
    assert (result["status"] == "cgroup_memory_capabilities_present") == (
        scenario == "matching"
    )
    assert result["job_peak_bytes"] == 2048
