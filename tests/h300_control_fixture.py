"""Short, solver-free child used only by S2 supervisor regressions."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.mvp2_h300_controls import PhaseJournal, run_phases  # noqa: E402


def main():
    directory, identity, mode = sys.argv[1:]
    journal = PhaseJournal(directory, identity)
    if mode in {"pipeline_partial", "pipeline_none"}:
        from scripts.mvp2_h300_partial import export_partial
        from tests.test_mvp2_h300_partial import fixture

        return run_phases(
            journal,
            lambda: fixture(count=0 if mode == "pipeline_none" else 1, stage_count=0),
            lambda inputs: inputs,
            lambda inputs: (export_partial(Path(directory).parent / "products", *inputs), 0)[1],
            lambda: None,
        )
    journal.enter("build")
    if mode == "failed_cleanup_hang":
        journal.failure_cleanup()
        time.sleep(30)
    if mode == "build_hang":
        time.sleep(30)
    if mode == "malformed":
        (Path(directory) / "phase-1.json").write_text('{"phase":"wrong"}')
        time.sleep(30)
    if mode == "ignore_term":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        (Path(directory) / "ready").write_text("ready")
        time.sleep(30)
    if mode == "orphan":
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        (Path(directory) / "descendant.pid").write_text(str(child.pid))
    journal.enter("optimization")
    if mode == "opt_hang":
        time.sleep(30)
    journal.enter("export_validation")
    if mode == "export_hang":
        time.sleep(30)
    if mode == "fail":
        return 3
    journal.enter("cleanup")
    if mode == "cleanup_hang":
        time.sleep(30)
    return 0


if __name__ == "__main__":
    os._exit(main())
