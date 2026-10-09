"""Stdlib-only synthetic worker components; standalone execution remains closed.

No solver, workbook, license, shell, scheduler or arbitrary command. The bounded
fork tree is not exercised by this software gate. A future live adapter must
bind the actual step and establish the outside-supervisor barrier first.
"""

from __future__ import annotations

import json
import os
import signal
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


def fork_nested_components(*, duration_seconds=120):
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
                    while time.monotonic() < end:
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


if __name__ == "__main__":
    execute_worker()
