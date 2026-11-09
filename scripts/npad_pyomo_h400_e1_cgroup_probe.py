"""Read memory-controller capabilities inside a public E1 Slurm allocation."""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path, PurePosixPath

EXPECTED_BYTES = 192 * 1024**3
EXERCISE_BYTES = 128 * 1024**2
EXERCISE_INCREMENT = 32 * 1024**2


def cgroup_locations(membership, mounts, job_id):
    groups = {}
    for line in membership.splitlines():
        number, controllers, path = line.split(":", 2)
        if "memory" in controllers.split(","):
            groups["cgroup_v1"] = path
        elif number == "0" and not controllers:
            groups["cgroup_v2"] = path
    version = "cgroup_v1" if "cgroup_v1" in groups else "cgroup_v2"
    if version not in groups:
        raise ValueError("No memory-controller membership in /proc/self/cgroup.")
    relative = groups[version]
    group = PurePosixPath(relative)
    if not group.is_absolute() or ".." in group.parts:
        raise ValueError("Invalid cgroup membership path.")
    candidates = []
    for line in mounts.splitlines():
        left, right = line.split(" - ", 1)
        fs, _, options = right.split()
        matches = (
            fs == "cgroup" and "memory" in options.split(",")
            if version == "cgroup_v1" else fs == "cgroup2"
        )
        if not matches:
            continue
        fields = left.split()
        root, mount = (
            PurePosixPath(re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), field))
            for field in fields[3:5]
        )
        if group.is_relative_to(root):
            candidates.append((root, mount))
    if not candidates:
        raise ValueError(f"No accessible memory-controller mount for {version}.")
    root, mount = min(candidates, key=lambda pair: len(pair[0].parts))
    target = f"job_{job_id}"
    if target not in group.parts or target in root.parts:
        raise ValueError("Slurm job scope or its ancestors are not visible.")
    job = PurePosixPath(*group.parts[: group.parts.index(target) + 1])
    return version, mount, mount / job.relative_to(root), mount / group.relative_to(root)


def counters(path):
    return {
        name: int(value)
        for name, value in (
            line.split() for line in path.read_text(encoding="ascii").splitlines()
        )
    }


def memory_snapshot(version, mount, job, member):
    v1 = version == "cgroup_v1"
    limit_name = "memory.limit_in_bytes" if v1 else "memory.max"
    levels = {}
    for directory in (member, *member.parents):
        if not directory.is_relative_to(mount):
            break
        limit_file = directory / limit_name
        if limit_file.is_file():
            raw = limit_file.read_text(encoding="ascii").strip()
            levels[str(directory)] = None if raw == "max" else int(raw)
    job_key = str(job)
    if job_key not in levels:
        raise ValueError(f"Slurm job {limit_name} is unavailable.")
    effective = min(
        (limit for limit in levels.values() if limit is not None), default=None
    )
    if v1:
        if (job / "memory.use_hierarchy").read_text(encoding="ascii").strip() != "1":
            raise ValueError("The v1 job memory controller is not hierarchical.")
        effective = min(effective, counters(member / "memory.stat")["hierarchical_memory_limit"])
        events = counters(job / "memory.oom_control")
        events["failcnt"] = int((job / "memory.failcnt").read_text(encoding="ascii"))
        counters_clear = (
            events["failcnt"] == 0 and events["under_oom"] == 0 and events["oom_kill"] == 0
        )
    else:
        events = counters(job / "memory.events")
        counters_clear = events["oom"] == 0 and events["oom_kill"] == 0
    peak = int((job / ("memory.max_usage_in_bytes" if v1 else "memory.peak")).read_text(
        encoding="ascii"
    ))
    current = int(current_file(version, job).read_text(encoding="ascii"))
    ready = (
        levels[job_key] == EXPECTED_BYTES and effective == EXPECTED_BYTES
        and counters_clear
    )
    return {
        "status": "cgroup_memory_capabilities_present" if ready else "cgroup_memory_profile_differs",
        "controller": version,
        "job_cgroup": job_key,
        "member_cgroup": str(member),
        "effective_member_limit_bytes": effective,
        "ancestor_limits_bytes": levels,
        "job_current_bytes": current,
        "job_peak_bytes": peak,
        "job_memory_events": events,
    }


def current_file(version, job):
    return job / ("memory.usage_in_bytes" if version == "cgroup_v1" else "memory.current")


def stop_owned_process(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return process.wait(timeout=2)
    try:
        return process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return process.wait(timeout=2)


def watch(process, usage_file, ceiling, interval=0.2):
    while True:
        current = int(usage_file.read_text(encoding="ascii"))
        if current >= ceiling:
            return {"trigger_bytes": current, "child_exit": stop_owned_process(process)}
        try:
            return {"trigger_bytes": None, "child_exit": process.wait(timeout=interval)}
        except subprocess.TimeoutExpired:
            continue


def exercise_guard(version, job, before):
    if os.environ.get("SLURM_STEP_ID") != "0":
        raise ValueError("The public guard exercise requires step 0.")
    threshold = before + EXERCISE_INCREMENT
    if threshold + EXERCISE_BYTES > EXPECTED_BYTES // 10:
        raise ValueError("Public exercise baseline is unexpectedly high.")
    # bytearray pages are touched individually to charge physical memory.
    body = (
        "import sys,time\n"
        "pages = bytearray(int(sys.argv[1]))\n"
        "for i in range(0, len(pages), 4096): pages[i] = 1\n"
        "time.sleep(5)\n"
    )
    with subprocess.Popen(
        [sys.executable, "-B", "-I", "-c", body, str(EXERCISE_BYTES)],
        start_new_session=True,
    ) as process:
        try:
            result = watch(process, current_file(version, job), threshold)
        finally:
            if process.poll() is None:
                stop_owned_process(process)
    return {"threshold_bytes": threshold, **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exercise", action="store_true")
    args = parser.parse_args()
    job_id = os.environ.get("SLURM_JOB_ID", "")
    result = {
        "job_id": job_id,
        "step_id": os.environ.get("SLURM_STEP_ID", "batch"),
        "private_execution_admitted": False,
    }
    try:
        if not re.fullmatch(r"[1-9][0-9]*", job_id):
            raise ValueError("A Slurm job ID is required.")
        version, *locations = cgroup_locations(
            Path("/proc/self/cgroup").read_text(encoding="ascii"),
            Path("/proc/self/mountinfo").read_text(encoding="ascii"),
            job_id,
        )
        mount, job, member = (Path(path) for path in locations)
        result.update(memory_snapshot(version, mount, job, member))
        result["affinity_logical_cpus"] = len(os.sched_getaffinity(0))
        if args.exercise and result["status"] == "cgroup_memory_capabilities_present":
            if result["affinity_logical_cpus"] != 16:
                raise ValueError("The public exercise requires 16 logical CPUs in step affinity.")
            exercise = exercise_guard(version, job, result["job_current_bytes"])
            result.update(memory_snapshot(version, mount, job, member), exercise=exercise)
            if exercise["trigger_bytes"] is None or exercise["child_exit"] != -signal.SIGTERM:
                result["status"] = "cgroup_public_guard_exercise_rejected"
    except (KeyError, OSError, ValueError) as error:
        result.update(status="cgroup_memory_probe_unavailable", reason=str(error))
    print(json.dumps(result, indent=2))
    return int(result["status"] != "cgroup_memory_capabilities_present")


if __name__ == "__main__":
    raise SystemExit(main())
