"""Fixed trusted academic worker; never accepts workbooks, arbitrary commands or h300."""

from __future__ import annotations

import os
import signal
import time
from pathlib import Path

from scripts import mvp2_s2_academic as a
from scripts import mvp2_s2_allocation_diagnostic as d


def publish(root, name, value):
    d.write_new(Path(root) / name, value)


def resources():
    """Root-only pre-exit observation, not lifetime tree CPU or continuous peak coverage."""
    import resource

    value = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "scope": "root_process_pre_exit_linux",
        "peak_rss_kib": value.ru_maxrss,
        "user_cpu_seconds": value.ru_utime,
        "system_cpu_seconds": value.ru_stime,
        "tree_cpu_seconds": None,
        "continuous_peak_coverage": False,
    }


def process_identity(pid):
    """PID reuse guard for observation, not a no-escape/isolation certificate."""
    text = Path(f"/proc/{pid}/stat").read_text()
    rest = text[text.rfind(")") + 2 :].split()
    return {"pid": pid, "start_ticks": int(rest[19])}


def absent(identity):
    try:
        return process_identity(identity["pid"]) != identity
    except FileNotFoundError:
        return True
    except (OSError, ValueError, IndexError):
        return None


def nested(root, p, *, pause=time.sleep):
    """Exactly two extra processes; self-exit is safety, never forced-stop evidence."""
    # Keep the fixed challenge root alive through TERM so KILL, rather than
    # incidental root exit/step teardown, is the intended termination path.
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    child = os.fork()
    if child == 0:
        try:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            grandchild = os.fork()
            if grandchild == 0:
                try:
                    os.setsid()
                    signal.signal(signal.SIGTERM, signal.SIG_IGN)
                    publish(root, "nested-grandchild.json", process_identity(os.getpid()))
                    pause(120)
                finally:
                    os._exit(0)
            publish(root, "nested-child.json", process_identity(os.getpid()))
            os.waitpid(grandchild, 0)
        finally:
            os._exit(0)
    deadline = time.monotonic() + 10
    names = ("nested-child.json", "nested-grandchild.json")
    while not all((Path(root) / name).is_file() for name in names):
        a.require(time.monotonic() < deadline, "Nested startup deadline.")
        pause(0.05)
    publish(
        root,
        "nested.json",
        {
            "plan_sha256": a.digest(p),
            "extra_processes": 2,
            "identities": [a.c.read_json(Path(root) / x) for x in names],
        },
    )
    os.waitpid(child, 0)


def exercise(stage, root, p, *, nested_factory=nested):
    """Exact failure prefixes are distinct from unexpected exceptions/partial native work."""
    phases = []
    for phase in ("build", "optimization", "export", "disposal"):
        phases.append(phase)
        if stage == phase + "_failure":
            publish(
                root,
                "worker-result.json",
                {
                    "plan_sha256": a.digest(p),
                    "outcome": "expected_phase_failure",
                    "phases": phases,
                    "resources": resources(),
                },
            )
            return 3
    if stage == "nested_setsid_term_ignore":
        nested_factory(root, p)
    publish(
        root,
        "worker-result.json",
        {
            "plan_sha256": a.digest(p),
            "outcome": "synthetic_complete",
            "phases": phases,
            "resources": resources(),
        },
    )
    return 0


def native(root, p):
    """One real native fixture using unchanged h300 solver/profile and residual rules."""
    from scripts import mvp2_h300_native_worker as worker
    from scripts import mvp2_h300_partial as partial
    from scripts import probe_npad_gurobi_license as license_probe

    os.environ["GRB_LICENSE_FILE"] = license_probe.LICENSE_FILE
    # Capability check is the existing fixed 2001-variable public license probe,
    # not an agricultural observation. Never transfer license contents or its path.
    capability = license_probe.probe()
    safe = {
        k: capability[k]
        for k in ("status", "gurobi_version", "error_type", "error_code")
        if k in capability
    }
    publish(root, "license.json", safe)
    a.require(capability["status"] == "accepted", "Fresh native license rejected.")
    data, config = a.fixture()
    anchor = partial.anchor(
        data,
        config,
        source_commit=p["source_commit"],
        runtime_sha256=a.digest(p["runtime"]),
        workbook_sha256=p["fixture"]["data_sha256"],
        threads=4,
    )
    report = worker._integrate_native(Path(root) / "native", data, config, anchor)
    a.require(
        report["classification"]["disposition"] == "complete_accepted_hierarchy",
        "Native fixture not complete/accepted.",
    )
    publish(
        root,
        "worker-result.json",
        {"plan_sha256": a.digest(p), "outcome": "native_complete", "resources": resources()},
    )
    return 0


def run(root, p, job, *, execute_native=native, clock=time.monotonic, pause=time.sleep):
    a.validate_plan(p)
    a.require(os.environ.get("SLURM_JOB_ID") == job, "Worker job mismatch.")
    step_number = os.environ.get("SLURM_STEP_ID", "")
    a.require(step_number.isdecimal(), "Worker must be a numeric Slurm step.")
    a.require(a.runtime() == p["runtime"], "Worker runtime drift.")
    affinity = sorted(os.sched_getaffinity(0))
    requested = 4 if p["stage"] == "native_miniature" else 1
    a.require(len(affinity) >= requested, "Worker CPU deficit.")
    # Trusted-worker affinity choice, NOT proof of a hard cgroup CPU ceiling.
    os.sched_setaffinity(0, affinity[:requested])
    publish(
        root,
        "worker-start.json",
        {
            "plan_sha256": a.digest(p),
            "job_id": job,
            "step_id": job + "." + step_number,
            "uid": os.getuid(),
            "identity": process_identity(os.getpid()),
            "affinity": sorted(os.sched_getaffinity(0)),
            "runtime_sha256": a.digest(p["runtime"]),
        },
    )
    end = clock() + 30
    release = Path(root) / "worker-release.json"
    while not release.exists():
        a.require(clock() < end, "Worker release deadline.")
        pause(0.05)
    a.require(
        a.c.read_json(release)
        == {"plan_sha256": a.digest(p), "job_id": job, "step_id": job + "." + step_number},
        "Release mismatch.",
    )
    try:
        return (
            execute_native(root, p)
            if p["stage"] == "native_miniature"
            else exercise(p["stage"], root, p)
        )
    except BaseException as error:
        publish(
            root,
            "worker-failure.json",
            {"plan_sha256": a.digest(p), "error_type": type(error).__name__},
        )
        raise
