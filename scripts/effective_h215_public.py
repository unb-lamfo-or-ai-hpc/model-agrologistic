"""Prepare or explicitly execute one public qualification; never submit jobs.

Execution is compute-only and limited to named public analytical controls.
No private experimental input or private solve command is accepted.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import os
import platform
import re
import shlex
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.effective_h215_public_controls import (  # noqa: E402
    control_specs,
    expected,
    make_control,
)
from scripts.qualify_pyomo_gurobi_license_v2 import extract_source, verify_source  # noqa: E402
from src.logic.effective_baseline import sha256  # noqa: E402

BASE = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
PYTHON = "/home/vrrcelestino/venv313/bin/python"
CLAIM = ".mvp2-h215-effective-policy-public-v1"
ACK = "PUBLIC_TINY_ONLY_NO_PRIVATE_EXECUTION"
VERSIONS = {"pyomo": "6.10.1", "gurobipy": "13.0.3"}
SOFTWARE_TEST_COUNT = 181


def write_new(path, record):
    with Path(path).open("x", encoding="utf-8") as f:
        f.write(json.dumps(record, indent=2, allow_nan=False) + "\n")


def location(path):
    path = Path(path).absolute()
    if path.name != CLAIM or path.parent.resolve() != BASE.resolve() or path.is_symlink():
        raise ValueError("Dedicated qualification claim under the audit project required.")
    return path


def runtime():
    versions = {name: importlib.metadata.version(name) for name in VERSIONS}
    if sys.version_info[:2] != (3, 13) or versions != VERSIONS:
        raise ValueError("Use the existing Python 3.13 / Pyomo 6.10.1 / Gurobi 13.0.3 environment.")
    code = {}
    for name in VERSIONS:
        distribution = importlib.metadata.distribution(name)
        code[name] = {
            str(p): sha256(distribution.locate_file(p))
            for p in distribution.files or ()
            if str(p).endswith((".py", ".so", ".pyd", ".dll"))
        }
        if not code[name]:
            raise ValueError("Installed package code identities are unavailable.")
    return {
        "versions": versions,
        "python": platform.python_version(),
        "python_sha256": sha256(sys.executable),
        "package_code": code,
    }


def batch_text(claim, source, digest):
    q = shlex.quote
    return f"""#!/bin/bash
#SBATCH --job-name=h215-policy-public
#SBATCH --partition=intel-256
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --hint=nomultithread
#SBATCH --mem=192G
#SBATCH --exclusive
#SBATCH --time=01:00:00
#SBATCH --output={claim}/slurm-%j.out
#SBATCH --error={claim}/slurm-%j.err
set -euo pipefail
umask 077
cd {q(str(BASE))}
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic
export TMPDIR={q(str(claim / "tmp"))} XDG_CACHE_HOME={q(str(claim / "cache"))}
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME"
exec srun --exact --ntasks=1 --cpus-per-task=16 --hint=nomultithread --cpu-bind=threads \\
 {q(PYTHON)} -B -I {q(str(source / "scripts/effective_h215_public.py"))} execute \\
 --claim {q(str(claim))} --plan-sha256 {digest} --ack {ACK}
"""


def prepare(claim, archive, source_sha, archive_sha):
    claim = location(claim)
    if platform.system() != "Linux" or not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("NPAD Linux and a full source SHA required.")
    archive = Path(archive).resolve()
    if not archive.is_relative_to(BASE.resolve()) or sha256(archive) != archive_sha:
        raise ValueError("Pinned public archive below the audit project required.")
    environment = runtime()  # Metadata only; no native engine or license imported.
    claim.mkdir(exist_ok=False)
    source = claim / "source"
    files = extract_source(archive, source, source_sha)
    if files.get("scripts/effective_h215_public.py") != sha256(__file__):
        raise ValueError("Bootstrap controller differs from the pinned source archive.")
    from scripts.check_effective_contract import TESTS

    plan = {
        "schema": "h215-effective-public-qualification-v1",
        "source_commit": source_sha,
        "archive_sha256": archive_sha,
        "source_files": files,
        "runtime": environment,
        "controls": control_specs(),
        "software_test_inventory": list(TESTS),
        "software_test_count": SOFTWARE_TEST_COUNT,
        "native_seconds_per_control": 30,
        "private_execution_allowed": False,
        "automatic_retry": False,
        "memory_bytes": 192 * 1024**3,
        "physical_affinity_cores": 16,
    }
    write_new(claim / "plan.json", plan)
    digest = sha256(claim / "plan.json")
    with (claim / "qualification.sh").open("x", encoding="utf-8", newline="\n") as f:
        f.write(batch_text(claim, source, digest))
    return {
        "status": "prepared_no_job",
        "claim": str(claim),
        "source_commit": source_sha,
        "plan_sha256": digest,
        "public_native_controls": len(plan["controls"]),
        "private_execution_allowed": False,
        "submission_performed": False,
    }


def compute_snapshot():
    from scripts import npad_pyomo_h400_e1_cgroup_probe as cg
    from scripts.pyomo_gurobi_license_gate import compute_context

    compute_context()  # Numeric Slurm job/step before native imports.
    allocation = subprocess.run(
        ["scontrol", "show", "job", "--oneliner", os.environ["SLURM_JOB_ID"]],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    fields = dict(word.split("=", 1) for word in allocation.stdout.split() if "=" in word)
    if (
        fields.get("Partition") != "intel-256"
        or fields.get("NumNodes") != "1"
        or fields.get("OverSubscribe") != "NO"
    ):
        raise ValueError("Exclusive single-node intel-256 allocation required.")
    affinity = sorted(os.sched_getaffinity(0))
    topology = []
    for cpu in affinity:
        path = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        topology.append(
            (int((path / "physical_package_id").read_text()), int((path / "core_id").read_text()))
        )
    if len(affinity) != 16 or len(set(topology)) != 16:
        raise ValueError("Sixteen distinct physical cores with one logical CPU each required.")
    context = cg.cgroup_locations(
        Path("/proc/self/cgroup").read_text(),
        Path("/proc/self/mountinfo").read_text(),
        os.environ["SLURM_JOB_ID"],
    )
    memory = cg.memory_snapshot(*context)
    if memory["status"] != "cgroup_memory_capabilities_present":
        raise ValueError("The inherited 192 GiB cgroup profile or counters differ.")
    return {
        "job_id": os.environ["SLURM_JOB_ID"],
        "step_id": os.environ["SLURM_STEP_ID"],
        "affinity": affinity,
        "topology": topology,
        "memory": memory,
        "allocation": {
            k: fields.get(k)
            for k in (
                "JobId",
                "Partition",
                "NumNodes",
                "NumCPUs",
                "CPUs/Task",
                "OverSubscribe",
                "NodeList",
            )
        },
    }


def run_native_control(control):
    # Only a named public analytical fixture can reach the common adapter.
    from src.logic.effective_gurobi_execution import settings, solve_effective_gurobi

    if control not in control_specs():
        raise ValueError("Unknown public control.")
    data, cfg, audit = make_control(control)
    profile = settings(
        threads=control["threads"],
        native_seconds=30,
        mip_gap=0,
        diagnostic_infeasible=control["kind"] == "infeasible",
    )
    result = solve_effective_gurobi(data, cfg, profile, max_variables=256)
    wanted = expected(control)
    metadata = result.metadata
    receipt = {
        "control": control,
        "matrix": metadata["common_linear_matrix"],
        "expected": wanted,
        "native_status": result.status,
        "native_solution_count": metadata["native_solution_count"],
        "effective_options": metadata["effective_native_options"],
        "scenario_sha256": audit["scenario_sha256"],
        "native_model_lifecycle": metadata["native_model_lifecycle"],
    }
    if wanted["classification"] == "infeasible":
        if result.status != "infeasible" or metadata["native_solution_count"]:
            raise ValueError("Analytical negative control was not proved infeasible.")
        return {**receipt, "status": "accepted_expected_infeasible", "result": None}
    certificate = metadata["effective_validation"]
    if (
        result.status != "optimal"
        or certificate["status"] != "accepted"
        or not math.isclose(result.objective_value, wanted["objective"], rel_tol=1e-9, abs_tol=1e-5)
    ):
        raise ValueError("Analytical optimum or independent certificate differs.")
    if control["kind"] == "candidate" and not math.isclose(
        result.warehouse_decisions[0]["candidate_capacity"], 10 / 6, abs_tol=1e-6
    ):
        raise ValueError("Public candidate investment differs.")
    return {**receipt, "status": "accepted", "result": asdict(result), "validation": certificate}


def execute(claim, plan_sha, ack):
    claim = location(claim)
    if ack != ACK or sha256(claim / "plan.json") != plan_sha:
        raise ValueError("Explicit public-only acknowledgment and exact plan digest required.")
    plan = json.loads((claim / "plan.json").read_text())
    from scripts.check_effective_contract import TESTS

    if (
        plan["private_execution_allowed"]
        or plan["controls"] != control_specs()
        or plan["software_test_inventory"] != list(TESTS)
        or plan["software_test_count"] != SOFTWARE_TEST_COUNT
    ):
        raise ValueError("Only the finite declared public inventory is admitted.")
    source = claim / "source"
    verify_source(source, plan["source_files"])
    if ROOT.resolve() != source.resolve() or runtime() != plan["runtime"]:
        raise ValueError("Execute from the exact prepared source and environment.")
    before = compute_snapshot()
    write_new(claim / "started.json", {"plan_sha256": plan_sha, "compute": before})
    record = {
        "status": "rejected",
        "source_commit": plan["source_commit"],
        "plan_sha256": plan_sha,
        "private_input_accessed": False,
        "public_controls": [],
        "new_private_jobs": 0,
    }
    try:
        child = subprocess.run(
            [
                sys.executable,
                "-B",
                "-I",
                str(source / "scripts/check_effective_contract.py"),
                "--output",
                str(claim / "data-checks"),
            ],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        with (claim / "data-checks.log").open("x", encoding="utf-8") as f:
            f.write(child.stdout + child.stderr)
        checks = json.loads((claim / "data-checks/result.json").read_text())
        if (
            child.returncode
            or checks["status"] != "accepted"
            or checks["tests"] != plan["software_test_count"]
            or checks["test_inventory"] != plan["software_test_inventory"]
        ):
            raise ValueError("The exact public software inventory did not pass.")
        from scripts import pyomo_gurobi_license_gate as license_gate

        license_receipt = license_gate.probe()
        write_new(claim / "license-capability.json", license_receipt)
        if not license_gate.accepted(license_receipt):
            raise ValueError("Default-environment license capacity was not admitted.")
        from pyomo.common.tee import capture_output

        for control in plan["controls"]:
            with capture_output(capture_fd=True):
                outcome = run_native_control(control)
            write_new(claim / f"control-{control['id']}.json", outcome)
            record["public_controls"].append({"id": control["id"], "status": outcome["status"]})
        verify_source(source, plan["source_files"])
        record.update(
            status="accepted_public_qualification",
            software_tests=checks["tests"],
            source_verified_after=True,
            compute_after=compute_snapshot(),
            private_execution_admitted=False,
        )
    except Exception as error:
        # Never export exception messages or native/license startup text.
        record["error_type"] = type(error).__name__
    write_new(claim / "result.json", record)
    return {
        "status": record["status"],
        "completed_public_controls": len(record["public_controls"]),
        "private_execution_admitted": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--claim", required=True, type=Path)
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--archive-sha256", required=True)
    p = sub.add_parser("execute")
    p.add_argument("--claim", required=True, type=Path)
    p.add_argument("--plan-sha256", required=True)
    p.add_argument("--ack", required=True)
    args = parser.parse_args()
    result = (
        prepare(args.claim, args.archive, args.source_sha, args.archive_sha256)
        if args.command == "prepare"
        else execute(args.claim, args.plan_sha256, args.ack)
    )
    print(json.dumps(result))
    return int(result["status"] == "rejected")


if __name__ == "__main__":
    raise SystemExit(main())
