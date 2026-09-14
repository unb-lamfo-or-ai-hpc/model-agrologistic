"""Collect read-only NPAD evidence; optionally test scheduler requests without submitting jobs."""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def capture(command, *, cwd=ROOT):
    """Keep errors as evidence and never invoke a shell or disclose environment variables."""
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=30)
        return {"command": command, "return_code": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": command, "return_code": None, "error": str(exc)}


def resource_observations(association_text, partition_text, *, account, partition, qos,
                          memory_mib=196608, solver_threads=4):
    """Conservative observations, not a replacement for the scheduler's policy resolution."""
    observed_qos = set()
    for line in association_text.splitlines():
        cells = line.split("|")
        if len(cells) >= 5 and cells[1] == account and cells[2] in ("", partition):
            observed_qos.update(cells[3].split(","))
    match = re.search(r"\bMaxMemPerCPU=(\d+)\b", partition_text)
    cap = int(match.group(1)) if match else None
    minimum = math.ceil(memory_mib / cap) if cap else None
    return {
        "requested_qos": qos, "observed_association_qos": sorted(observed_qos - {""}),
        "qos_explicitly_observed": qos in observed_qos,
        "qos_qualification": "requires_scheduler_test_and_account_confirmation",
        "requested_memory_mib": memory_mib, "solver_threads": solver_threads,
        "partition_max_memory_per_cpu_mib": cap,
        "arithmetic_minimum_allocated_cpus": minimum,
        "allocation_review_required": minimum is None or minimum > solver_threads,
        "qualification": "Arithmetic is advisory; Slurm may enforce other or inherited limits.",
    }


def file_record(path, expected_sha256=None):
    path = Path(path)
    row = {"path": str(path), "exists": path.is_file()}
    if path.is_file():
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        row.update(size_bytes=path.stat().st_size, sha256=digest)
        if expected_sha256 is not None:
            row["matches_expected_sha256"] = digest == expected_sha256
    return row


def scheduler_test_commands(account, partition, qos, minimum_cpus):
    """All generated requests are validation-only, never real submissions."""
    return [["sbatch", "--test-only", f"--account={account}",
             f"--partition={partition}", f"--qos={qos}",
             "--nodes=1", "--ntasks=1", f"--cpus-per-task={cpus}",
             "--mem=192G", "--time=12:00:00", "--wrap=true"]
            for cpus in sorted({4, max(4, minimum_cpus or 4)})]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-workbook", type=Path)
    parser.add_argument("--campaign-manifest", type=Path)
    parser.add_argument("--account", default="sxdsouza")
    parser.add_argument("--partition", default="intel-256")
    parser.add_argument("--qos", default="qos1")
    parser.add_argument("--test-scheduler", action="store_true",
                        help="Use sbatch --test-only; no job is submitted or executed.")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    assoc = capture(["sacctmgr", "-nP", "show", "assoc", "where", f"user={getpass.getuser()}",
                     "format=Cluster,Account,Partition,QOS,DefaultQOS"])
    part = capture(["scontrol", "show", "partition", args.partition])
    obs = resource_observations(assoc.get("stdout", ""), part.get("stdout", ""),
                                account=args.account, partition=args.partition, qos=args.qos)
    commands = [assoc, part, capture(["sacctmgr", "-nP", "show", "qos", "where",
                                    f"name={args.qos}", "format=Name,MaxWall,MaxTRESPU"]),
                capture(["git", "rev-parse", "HEAD"]), capture(["git", "status", "--short"])]
    tests = []
    if args.test_scheduler:
        for command in scheduler_test_commands(
                args.account, args.partition, args.qos,
                obs["arithmetic_minimum_allocated_cpus"]):
            tests.append(capture(command))
    source_manifest = ROOT / "data/manifests/warehouse_population_source_v020.json"
    source = json.loads(source_manifest.read_text(encoding="utf-8"))
    packages = {}
    for package in ("gurobipy", "pyscipopt", "pandas", "openpyxl"):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = "not_installed"
    report = {
        "schema_version": "npad-readiness-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "review_required", "jobs_submitted": False,
        "python": sys.executable, "python_version": sys.version.split()[0],
        "packages": packages, "resource_observations": obs,
        "commands": commands, "scheduler_test_only": tests,
        "source_contract": source,
        "source_workbook": (file_record(args.source_workbook, source["source_sha256"])
                            if args.source_workbook else {"status": "path_not_supplied"}),
        "workbooks": [file_record(ROOT / "data/processed/policy_population_v020_osrm"
                                   / f"warehouses_{size}/model_input.xlsx")
                      for size in (215, 300, 400, 500)],
        "workbook_qualification": "Existence/hash only; numeric/model preflight still required.",
        "scip_backend_qualification": "not_implemented; package installation alone is insufficient",
    }
    if args.campaign_manifest:
        report["campaign_manifest"] = file_record(args.campaign_manifest)
        preflight = args.campaign_manifest.parent / "nine_preflight.json"
        report["preflight_file"] = file_record(preflight)
        if preflight.is_file():
            report["preflight_observation"] = json.loads(preflight.read_text(encoding="utf-8"))
    target = args.output_dir / "npad_readiness.json"
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
