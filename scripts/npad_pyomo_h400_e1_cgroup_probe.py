"""Read memory-controller capabilities inside a public E1 Slurm allocation."""

import json
import os
import re
from pathlib import Path, PurePosixPath

EXPECTED_BYTES = 192 * 1024**3


def cgroup_locations(membership, mounts, job_id):
    relative, = [line[3:] for line in membership.splitlines() if line.startswith("0::")]
    group = PurePosixPath(relative)
    if not group.is_absolute() or ".." in group.parts:
        raise ValueError("Invalid cgroup membership path.")
    candidates = []
    for line in mounts.splitlines():
        left, right = line.split(" - ", 1)
        if right.split()[0] != "cgroup2":
            continue
        fields = left.split()
        root, mount = (
            PurePosixPath(re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), field))
            for field in fields[3:5]
        )
        if group.is_relative_to(root):
            candidates.append((root, mount))
    if not candidates:
        raise ValueError("No accessible unified cgroup v2 mount.")
    root, mount = min(candidates, key=lambda pair: len(pair[0].parts))
    target = f"job_{job_id}"
    if target not in group.parts or target in root.parts:
        raise ValueError("Slurm job scope or its ancestors are not visible.")
    job = PurePosixPath(*group.parts[: group.parts.index(target) + 1])
    return mount, mount / job.relative_to(root), mount / group.relative_to(root)


def memory_snapshot(mount, job, member):
    levels = {}
    for directory in (member, *member.parents):
        if not directory.is_relative_to(mount):
            break
        limit_file = directory / "memory.max"
        if limit_file.is_file():
            raw = limit_file.read_text(encoding="ascii").strip()
            levels[str(directory)] = None if raw == "max" else int(raw)
    job_key = str(job)
    if job_key not in levels:
        raise ValueError("Slurm job memory.max is unavailable.")
    effective = min(
        (limit for limit in levels.values() if limit is not None), default=None
    )
    events = {
        name: int(value)
        for name, value in (
            line.split() for line in (job / "memory.events").read_text(encoding="ascii").splitlines()
        )
    }
    peak = int((job / "memory.peak").read_text(encoding="ascii"))
    current = int((job / "memory.current").read_text(encoding="ascii"))
    ready = (
        levels[job_key] == EXPECTED_BYTES and effective == EXPECTED_BYTES
        and events["oom"] == 0 and events["oom_kill"] == 0
    )
    return {
        "status": "cgroup_memory_capabilities_present" if ready else "cgroup_memory_profile_differs",
        "job_cgroup": job_key,
        "member_cgroup": str(member),
        "effective_member_limit_bytes": effective,
        "ancestor_limits_bytes": levels,
        "job_current_bytes": current,
        "job_peak_bytes": peak,
        "job_memory_events": events,
    }


def main():
    job_id = os.environ.get("SLURM_JOB_ID", "")
    result = {
        "job_id": job_id,
        "step_id": os.environ.get("SLURM_STEP_ID", "batch"),
        "private_execution_admitted": False,
    }
    try:
        if not re.fullmatch(r"[1-9][0-9]*", job_id):
            raise ValueError("A Slurm job ID is required.")
        locations = cgroup_locations(
            Path("/proc/self/cgroup").read_text(encoding="ascii"),
            Path("/proc/self/mountinfo").read_text(encoding="ascii"),
            job_id,
        )
        result.update(memory_snapshot(*(Path(path) for path in locations)))
        result["affinity_logical_cpus"] = len(os.sched_getaffinity(0))
    except (KeyError, OSError, ValueError) as error:
        result.update(status="cgroup_memory_probe_unavailable", reason=str(error))
    print(json.dumps(result, indent=2))
    return int(result["status"] != "cgroup_memory_capabilities_present")


if __name__ == "__main__":
    raise SystemExit(main())
