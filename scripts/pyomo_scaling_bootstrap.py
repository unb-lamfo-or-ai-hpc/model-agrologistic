"""Standard-library-only cold entry; site/native imports wait for exact-step release."""

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path


def require(value, message):
    if not value:
        raise ValueError(message)


def regular(path):
    require(path.is_file() and not path.is_symlink(), "Regular source/receipt required.")
    return path


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def identity(
    claim,
    sha,
    root,
    *,
    started,
    audit_base=Path("/home/vrrcelestino/model-agrologistic-hygiene-audit"),
):
    original = (
        claim.parent.name == ".mvp2-pyomo-scaling-native8h-v1"
        and root == audit_base / ".mvp2-pyomo-scaling-public-v1/source"
        and re.fullmatch(r"h(300|400|500)-w-sto-(gurobi|highs)-t(1|2|4|8|16)-r[123]", claim.name)
    )
    e1 = (
        claim.parent.name == ".mvp2-pyomo-h400-e1-native8h-v1"
        and root == audit_base / ".mvp2-pyomo-h400-e1-public-v2/source"
        and re.fullmatch(r"h400-w-sto-(gurobi|highs)-t(1|16)-r1", claim.name)
    )
    e2 = (
        claim.parent.name == ".mvp2-pyomo-h400-e2-native8h-v1"
        and root == audit_base / ".mvp2-pyomo-h400-e2-public-v1/source"
        and re.fullmatch(r"h400-w-sto-(gurobi|highs)-t(2|4|8)-r1", claim.name)
    )
    require(
        re.fullmatch(r"[0-9a-f]{40}", sha)
        and (original or e1 or e2)
        and not claim.is_symlink()
        and claim.parent.parent == audit_base
        and not claim.parent.is_symlink(),
        "Dedicated qualified source/run claim required.",
    )
    control = claim / "control/sto"
    require(
        control.is_dir() and not control.is_symlink() and Path.cwd() == control,
        "Owned worker control cwd required.",
    )
    raw = regular(claim / "plan.json").read_bytes()
    plan = json.loads(raw)
    campaign = json.loads(regular(claim.parent / "campaign.json").read_bytes())
    job = json.loads(regular(claim / "job.json").read_bytes())
    require(
        plan["source_commit"] == campaign["source_commit"] == job["source_commit"] == sha
        and plan["cell"]["id"] == claim.name
        and plan["campaign_sha256"] == hashlib.sha256(canonical(campaign)).hexdigest()
        and plan["source_root"] == campaign["source_root"] == str(root)
        and hashlib.sha256(raw).hexdigest() == job["plan_sha256"],
        "Bootstrap source/plan/job binding differs.",
    )
    for name in (
        "scripts/pyomo_scaling_bootstrap.py",
        "scripts/pyomo_scaling_campaign.py",
        "scripts/pyomo_worker_bootstrap.py",
    ):
        require(
            hashlib.sha256(regular(root / name).read_bytes()).hexdigest()
            == campaign["source_files"][name],
            "Pinned bootstrap/driver differs.",
        )
    step = os.environ.get("SLURM_STEP_ID", "")
    require(
        re.fullmatch(r"[1-9][0-9]*", job["job_id"])
        and os.environ.get("SLURM_JOB_ID") == job["job_id"]
        and step.isdigit(),
        "Owned numeric compute step required.",
    )
    proc = (Path("/proc") / str(os.getpid()) / "stat").read_text().rsplit(")", 1)[1].split()
    return {
        **job,
        "mode": "sto",
        "step_id": step,
        "pid": os.getpid(),
        "proc_start_ticks": int(proc[19]),
        "started_monotonic": started,
    }


def launch(claim, sha):
    started = time.monotonic()
    root = Path(__file__).resolve().parents[1]
    entry = identity(claim, sha, root, started=started)
    # Load the already hash-checked standard-library helper, without adding the
    # application package to sys.path or triggering site initialization.
    spec = importlib.util.spec_from_file_location(
        "owned_bootstrap", root / "scripts/pyomo_worker_bootstrap.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    control = claim / "control/sto"
    helper.publish(control / "entry.json", entry)
    helper.publish(
        control / "phase-00.json", {"entry": entry, "phase": "input_build", "elapsed_seconds": 0.0}
    )
    recorder = helper.Recorder(control, entry)
    recorder.stage("bootstrap_identity", lambda: None, started=started)
    helper.publish(
        control / "bootstrap.json",
        {
            "entry": entry,
            "schema_version": "pyomo-bootstrap-v1",
            "isolated": sys.flags.isolated == 1,
            "no_site": sys.flags.no_site == 1,
            "no_user_site": sys.flags.no_user_site == 1,
            "native_or_application_loaded_before_release": any(
                name.split(".")[0] in {"src", "pyomo", "highspy", "gurobipy", "numpy", "pandas"}
                or name == "scripts.pyomo_scaling_campaign"
                for name in sys.modules
            ),
            "full_provenance_pending": True,
        },
    )
    recorder.stage("exact_release", lambda: helper.release(control, entry))

    def initialize_site():
        import site

        site.main()
        require(site.ENABLE_USER_SITE is False, "User site disabled.")

    recorder.stage("site_initialization", initialize_site)
    sys.path.insert(0, str(root))
    driver = recorder.stage(
        "driver_import", lambda: importlib.import_module("scripts.pyomo_scaling_campaign")
    )
    driver.worker(claim, sha, entry=entry, startup=recorder)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim", required=True, type=Path)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    try:
        launch(args.claim, args.source_sha)
    except Exception as error:
        # Preserve code locations without printing possible native/license text.
        print(
            json.dumps(
                {
                    "error_kind": type(error).__name__,
                    "frames": [
                        {"file": Path(frame.filename).name, "line": frame.lineno}
                        for frame in traceback.extract_tb(error.__traceback__)
                    ],
                }
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
