"""Stdlib-only synthetic worker components; standalone execution remains closed.

No solver, workbook, license, shell, scheduler or arbitrary command. The bounded
fork tree is not exercised by this software gate. A future live adapter must
bind the actual step and establish the outside-supervisor barrier first.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import socket
import stat
import struct
import sys
import time
from pathlib import Path

CASES = (
    "normal",
    "nested_setsid_term_ignore",
    "build_failure",
    "optimization_failure",
    "export_failure",
    "disposal_failure",
)
PHASES = ("build", "optimization", "export", "disposal")


def execute_worker(*_args, **_kwargs):
    raise PermissionError("Standalone synthetic worker execution is closed.")


def _write_once(directory, name, item):
    data = (json.dumps(item, sort_keys=True, allow_nan=False) + "\n").encode()
    if len(data) > 4096:
        raise ValueError("Synthetic event bound.")
    with (directory / name).open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def exercise_components(case, directory, nonce, *, release, nested_factory):
    """Fixed phase callbacks after an injected barrier; no implicit process launch.

    This function is not an admission boundary. The future adapter owns source,
    allocation, handshake and actual process checks. CLI stays denied regardless
    of arguments or environment. Phase-failure records are deliberately partial.
    """
    if type(case) is not str or case not in CASES:
        raise ValueError("Unknown case.")
    if (
        type(nonce) is not str
        or len(nonce) != 64
        or any(x not in "0123456789abcdef" for x in nonce)
    ):
        raise ValueError("Bad nonce.")
    if release() is not True:
        raise PermissionError("Barrier has not released this worker.")
    directory = Path(directory)
    directory.mkdir(exist_ok=False)
    owned = None
    try:
        for index, phase in enumerate(PHASES):
            _write_once(directory, f"phase-{index}.json", {"nonce": nonce, "phase": phase})
            if case == "nested_setsid_term_ignore" and index == 0:
                owned = nested_factory()
            if case == phase + "_failure":
                raise RuntimeError("synthetic_phase_failure")
        _write_once(directory, "terminal.json", {"nonce": nonce, "status": "synthetic_complete"})
    except RuntimeError:
        _write_once(
            directory, "failure.json", {"nonce": nonce, "status": "synthetic_phase_failure"}
        )
        raise
    return owned


def fork_nested_components(*, duration_seconds=120, heartbeat=None):
    """Future POSIX exercise: exactly child + detached grandchild; no fork loop.

    Grandchild ignores TERM and has an independent 120-second self-exit bound.
    The immediate child ignores TERM, waits/reaps its child normally, then exits.
    A forced Slurm kill must still be observed externally, never assumed from
    these cooperative safety bounds. No memory pressure or extra files.
    Not called by CLI, controller or any offline fixture in this gate.
    """
    if os.name != "posix" or type(duration_seconds) is not int or duration_seconds != 120:
        raise ValueError("Unqualified fork profile.")
    child = os.fork()
    if child == 0:
        try:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            grandchild = os.fork()
            if grandchild == 0:
                try:
                    os.setsid()
                    signal.signal(signal.SIGTERM, signal.SIG_IGN)
                    end = time.monotonic() + 120
                    counter = 0
                    while time.monotonic() < end:
                        if heartbeat is not None and counter < 120:
                            heartbeat(counter)
                            counter += 1
                            time.sleep(min(1, max(0, end - time.monotonic())))
                            continue
                        time.sleep(min(0.1, max(0, end - time.monotonic())))
                finally:
                    os._exit(0)
            while True:
                try:
                    os.waitpid(grandchild, 0)
                    break
                except InterruptedError:
                    continue
        finally:
            os._exit(0)
    return child


def _strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate IPC key.")
            result[key] = value
        return result

    def constant(_value):
        raise ValueError("Nonfinite IPC JSON.")

    return json.loads(data, object_pairs_hook=pairs, parse_constant=constant)


def _bounded_file(path, maximum):
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("Unsafe worker path.")
    if any(x.is_symlink() or x.is_junction() for x in (path, *path.parents)):
        raise ValueError("Linked worker path.")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    with os.fdopen(os.open(path, flags), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("Nonregular worker file.")
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("Worker file bound.")
    return data


def session_components(plan_path):
    """Actual IPC bridge, NOT an admitted standalone worker entry point.

    The peer checks numeric IDs independently with Slurm/proc before release.
    SLURM_* fields are handshake candidates, not authorization. Only fixed stdlib
    synthetic phases and at most two nested processes are available.
    """
    if sys.platform != "linux" or sys.version_info[:2] != (3, 13):
        raise ValueError("Unqualified worker runtime.")
    plan_path = Path(plan_path)
    plan = _strict_json(_bounded_file(plan_path, 4096))
    if type(plan) is not dict or set(plan) != {
        "nonce",
        "job_id",
        "case",
        "worker_sha256",
        "python_sha256",
        "supervisor_pid",
        "uid",
    }:
        raise ValueError("Worker plan schema.")
    for key in ("nonce", "worker_sha256", "python_sha256"):
        if (
            type(plan[key]) is not str
            or len(plan[key]) != 64
            or any(x not in "0123456789abcdef" for x in plan[key])
        ):
            raise ValueError("Worker plan digest.")
    if (
        type(plan["supervisor_pid"]) is not int
        or plan["supervisor_pid"] <= 0
        or type(plan["uid"]) is not int
        or plan["uid"] != os.getuid()
        or plan["case"] not in CASES
    ):
        raise ValueError("Worker plan identity.")
    measured_worker = hashlib.sha256(_bounded_file(Path(__file__).absolute(), 1024**2)).hexdigest()
    measured_python = hashlib.sha256(
        _bounded_file(Path(sys.executable).resolve(), 128 * 1024**2)
    ).hexdigest()
    if (measured_worker, measured_python) != (plan["worker_sha256"], plan["python_sha256"]):
        raise ValueError("Worker source/runtime drift.")
    job, step = os.environ.get("SLURM_JOB_ID", ""), os.environ.get("SLURM_STEP_ID", "")
    if (
        job != plan["job_id"]
        or not job.isascii()
        or not job.isdecimal()
        or job.startswith("0")
        or not step.isascii()
        or not step.isdecimal()
        or len(step) > 10
        or (len(step) > 1 and step.startswith("0"))
    ):
        raise ValueError("Missing/unreviewed scheduler handshake.")
    root = plan_path.parent
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    end = time.monotonic() + 30
    try:
        connection.settimeout(30)
        connection.connect(str(root / "ipc.sock"))
        peer_pid, peer_uid, _gid = struct.unpack(
            "3i",
            connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")),
        )
        if (peer_pid, peer_uid) != (plan["supervisor_pid"], plan["uid"]):
            raise ValueError("Unexpected supervisor peer.")
        hello = {
            "nonce": plan["nonce"],
            "job_id": job,
            "worker_step_id": step,
            "worker_sha256": measured_worker,
            "python_sha256": measured_python,
            "python_version": [3, 13],
        }
        payload = (json.dumps(hello, sort_keys=True) + "\n").encode()
        if connection.send(payload) != len(payload):
            raise ValueError("Incomplete hello.")
        remaining = end - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Worker startup deadline.")
        connection.settimeout(remaining)
        data = connection.recv(4097)
        if len(data) > 4096:
            raise ValueError("Oversized release.")
        release = _strict_json(data)
        if (
            type(release) is not dict
            or set(release) != {"nonce", "contract_sha256", "worker_step_id"}
            or release["nonce"] != plan["nonce"]
            or release["worker_step_id"] != step
            or type(release["contract_sha256"]) is not str
            or len(release["contract_sha256"]) != 64
            or any(x not in "0123456789abcdef" for x in release["contract_sha256"])
            or time.monotonic() >= end
        ):
            raise ValueError("Invalid/late release.")
    finally:
        connection.close()

    def heartbeat(counter):
        temporary = root / "heartbeat.pending"
        _write_once(root, temporary.name, {"nonce": plan["nonce"], "counter": counter})
        # One mutable, fixed-name challenge product; never a phase success marker.
        target = root / "heartbeat.json"
        if target.is_symlink() or target.is_junction():
            raise ValueError("Linked heartbeat.")
        os.replace(temporary, target)

    return exercise_components(
        plan["case"],
        root / "worker",
        plan["nonce"],
        release=lambda: True,
        nested_factory=lambda: fork_nested_components(heartbeat=heartbeat),
    )


if __name__ == "__main__":
    execute_worker()
