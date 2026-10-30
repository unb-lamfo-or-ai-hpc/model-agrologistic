"""Minimal owned worker entry before site initialization or application imports.

Invoked with Python -B -I -S. Full provenance/input checks remain in the released
worker. This module uses only the standard library and never calls a scheduler.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
import re
import sys
import time
import traceback
from pathlib import Path

SOLVERS = ("gurobi", "scip", "cbc")
DRIVER = "scripts.mvp2_pyomo_h215_w"
BOOTSTRAP = "scripts/pyomo_worker_bootstrap.py"
DRIVER_FILE = DRIVER.replace(".", "/") + ".py"
STAGES = (
    "bootstrap_identity",
    "exact_release",
    "site_initialization",
    "driver_import",
    "plan_validation",
    "source_verification",
    "runtime_fingerprints",
    "input_hashes",
    "tool_verification",
    "native_identity",
    "public_qualification",
    "runtime_receipt",
)


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()


def regular(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "Regular unlinked receipt required.")
    return path


def publish(path, value):
    """Publish complete JSON exclusively, with the same IPC semantics as the supervisor."""
    pending = path.with_name("." + path.name + ".pending")
    with pending.open("xb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())
    if os.name == "nt":
        os.rename(pending, path)
    else:
        os.link(pending, path)
        pending.unlink()


def proc_start(pid):
    fields = (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
    return int(fields[19])


class Recorder:
    """Begin records survive a killed process; completed stages retain measured durations."""

    def __init__(self, control, entry, *, clock=time.monotonic):
        self.control, self.entry, self.clock = control, entry, clock
        self.completed = []

    def stage(self, name, operation, *, started=None):
        require(name == STAGES[len(self.completed)], "Startup stage order differs.")
        number = len(self.completed)
        started = self.clock() if started is None else started
        base = self.control / f"startup-{number:02d}-{name}"
        before = {
            "schema_version": "pyomo-startup-stage-v1",
            "entry": self.entry,
            "stage": name,
            "event": "begin",
            "elapsed_seconds": started - self.entry["started_monotonic"],
        }
        publish(base.with_name(base.name + "-begin.json"), before)
        try:
            result = operation()
        except BaseException as exc:
            ended = self.clock()
            publish(
                base.with_name(base.name + "-failed.json"),
                {
                    **before,
                    "event": "failed",
                    "elapsed_seconds": ended - self.entry["started_monotonic"],
                    "duration_seconds": ended - started,
                    "error_kind": type(exc).__name__,
                },
            )
            raise
        ended = self.clock()
        publish(
            base.with_name(base.name + "-complete.json"),
            {
                **before,
                "event": "complete",
                "elapsed_seconds": ended - self.entry["started_monotonic"],
                "duration_seconds": ended - started,
            },
        )
        self.completed.append(name)
        return result


def identity(claim, sha, root, solver, *, origin=None):
    """Read only small immutable receipts and the two pinned executable files."""
    require(re.fullmatch(r"[0-9a-f]{40}", sha), "Full source SHA required.")
    require(
        solver in SOLVERS
        and (
            claim.name == f".mvp2-pyomo-{solver}-h215-w-native8h-v1"
            or (
                solver == "gurobi"
                and claim.name == ".mvp2-pyomo-gurobi-h215-w-native8h-license-v2"
            )
        )
        and not claim.is_symlink()
        and claim.parent.name.startswith("model-agrologistic")
        and claim.parent.name != "model-agrologistic",
        "Dedicated existing output claim required.",
    )
    require(
        root.name == "source"
        and root.parent.name.startswith("pyomo-h215-w-driver-")
        and root.parent.parent == claim.parent,
        "Owned source root required.",
    )
    control = claim / "control/sto"
    require(
        control.is_dir() and not control.is_symlink() and Path.cwd().resolve() == control.resolve(),
        "Owned control cwd required.",
    )
    plan_raw = regular(claim / "plan.json").read_bytes()
    plan = json.loads(plan_raw)
    source_raw = regular(claim / "source.json").read_bytes()
    source = json.loads(source_raw)
    job = json.loads(regular(claim / "job.json").read_bytes())
    require(
        plan["solver_name"] == solver
        and plan["source_commit"] == source["source_commit"] == job["source_commit"] == sha
        and Path(plan["source_root"]).resolve() == root
        and hashlib.sha256(plan_raw).hexdigest() == job["plan_sha256"]
        and hashlib.sha256(source_raw).hexdigest() == plan["artifact_sha256"]["source.json"],
        "Bootstrap source/plan/job binding differs.",
    )
    for name in (BOOTSTRAP, DRIVER_FILE):
        require(
            hashlib.sha256(regular(root / name).read_bytes()).hexdigest() == source["files"][name],
            "Pinned bootstrap/driver bytes differ.",
        )
    step = os.environ.get("SLURM_STEP_ID", "")
    require(
        re.fullmatch(r"[1-9][0-9]*", job["job_id"])
        and os.environ.get("SLURM_JOB_ID") == job["job_id"]
        and step.isdigit(),
        "Owned numeric step required.",
    )
    return {
        **job,
        "mode": "sto",
        "step_id": step,
        "pid": os.getpid(),
        "proc_start_ticks": proc_start(os.getpid()),
        "started_monotonic": time.monotonic() if origin is None else origin,
    }


def release(control, entry, *, clock=time.monotonic, sleep=time.sleep):
    until = clock() + 60
    while not (control / "release.json").exists() and clock() < until:
        sleep(0.1)
    require(
        json.loads(regular(control / "release.json").read_bytes()) == entry,
        "Exact-step release required.",
    )


def launch(claim, sha, root, solver):
    """No site-packages or application imports until the exact supervisor release."""
    origin = time.monotonic()
    control = claim / "control/sto"
    entry = identity(claim, sha, root, solver, origin=origin)
    publish(control / "entry.json", entry)
    publish(
        control / "phase-00.json",
        {
            "entry": entry,
            "phase": "input_build",
            "elapsed_seconds": 0.0,
        },
    )
    recorder = Recorder(control, entry)
    recorder.stage("bootstrap_identity", lambda: None, started=origin)
    publish(
        control / "bootstrap.json",
        {
            "entry": entry,
            "schema_version": "pyomo-bootstrap-v1",
            "isolated": sys.flags.isolated == 1,
            "no_site": sys.flags.no_site == 1,
            "no_user_site": sys.flags.no_user_site == 1,
            "native_or_application_loaded_before_release": any(
                n.split(".")[0]
                in {"gurobipy", "pyscipopt", "highspy", "pyomo", "numpy", "pandas", "src"}
                or n == DRIVER
                for n in sys.modules
            ),
            "full_provenance_pending": True,
        },
    )
    recorder.stage("exact_release", lambda: release(control, entry))

    def initialize_site():
        import site

        site.main()
        require(site.ENABLE_USER_SITE is False, "User site must remain disabled.")

    recorder.stage("site_initialization", initialize_site)
    sys.path.insert(0, str(root))
    module = recorder.stage("driver_import", lambda: importlib.import_module(DRIVER))
    module.campaign_for_claim(solver, claim).worker(
        claim, sha, "sto", entry=entry, startup=recorder
    )


def review(files, job):
    """Describe partial startup precisely; never manufacture native solver evidence."""
    base = "control/sto/"
    names = sorted(n for n in files if n.startswith(base + "startup-") and n.endswith(".json"))
    if not names:
        return {"status": "absent", "completed_stages": [], "last_stage": None}
    entry = json.loads(files[base + "entry.json"])
    require(all(entry[k] == v for k, v in job.items()), "Startup job binding differs.")
    completed, last, durations = [], None, {}
    previous = -1.0
    active = None
    for name in names:
        event = json.loads(files[name])
        require(
            event["schema_version"] == "pyomo-startup-stage-v1" and event["entry"] == entry,
            "Startup identity differs.",
        )
        elapsed = event["elapsed_seconds"]
        require(
            type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= previous,
            "Startup clock differs.",
        )
        previous = elapsed
        last = event["stage"]
        require(last == STAGES[len(completed)], "Startup stage order differs.")
        if event["event"] == "begin":
            require(active is None, "Duplicate startup begin.")
            active = elapsed
        else:
            require(
                active is not None and event["event"] in {"complete", "failed"},
                "Startup completion without begin.",
            )
            require(
                math.isclose(event["duration_seconds"], elapsed - active, abs_tol=1e-5),
                "Startup duration differs.",
            )
            if event["event"] == "failed":
                return {
                    "status": "failed",
                    "completed_stages": completed,
                    "last_stage": last,
                    "error_kind": event["error_kind"],
                    "stage_seconds": durations,
                }
            durations[last] = event["duration_seconds"]
            completed.append(last)
            active = None
    if completed != list(STAGES):
        return {
            "status": "incomplete",
            "completed_stages": completed,
            "last_stage": last,
            "stage_seconds": durations,
        }
    receipt = json.loads(files[base + "bootstrap.json"])
    require(
        receipt["schema_version"] == "pyomo-bootstrap-v1"
        and receipt["entry"] == entry
        and all(receipt[k] is True for k in ("isolated", "no_site", "no_user_site"))
        and receipt["native_or_application_loaded_before_release"] is False
        and receipt["full_provenance_pending"] is True
        and json.loads(files[base + "release.json"]) == entry,
        "Minimal bootstrap/release contract differs.",
    )
    return {
        "status": "complete",
        "completed_stages": completed,
        "last_stage": last,
        "stage_seconds": durations,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim", type=Path, required=True)
    parser.add_argument("--solver", choices=SOLVERS, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--mode", choices=("sto",), required=True)
    args = parser.parse_args(argv)
    require(
        sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.no_user_site == 1,
        "Invoke minimal bootstrap with -B -I -S.",
    )
    root = Path(__file__).resolve().parents[1]
    try:
        launch(args.claim.absolute(), args.source_sha, root, args.solver)
    except BaseException:
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
