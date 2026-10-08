"""Qualify thread settings on analytical miniatures; never run production inputs."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import admit_mvp2_resource_pair as pair  # noqa: E402
from scripts import collect_mvp2_pair_preflight as transfer  # noqa: E402
from scripts import mvp2_h300_baseline as baseline  # noqa: E402
from scripts.audit_nine_campaign import classify_stages  # noqa: E402
from scripts.validate_scip_memory_resources import fields, memory_mib  # noqa: E402
from src.logic.excel_loader import ExcelLoaderConfig  # noqa: E402
from src.logic.experiment_runner import (  # noqa: E402
    ExperimentSpec,
    _checkpoint_identity,
    run_experiment,
)
from src.logic.model_config import ModelConfig, SolverConfig  # noqa: E402
from src.logic.resource_telemetry import cgroup_memory  # noqa: E402
from src.logic.run_integrity import (  # noqa: E402
    file_sha256,
    implementation_identity,
    scientific_identity,
    verify_completion,
)
from src.logic.solver_diagnostics import ROLES  # noqa: E402
from tests.test_gurobipy_stochastic import two_scenario_data  # noqa: E402

POLICY = "docs/mvp2_threads_policy.json"
TOOLS = (
    POLICY, "scripts/mvp2_threads.py", "scripts/npad_mvp2_threads.sh",
    "scripts/run_mvp2_threads.slurm", "scripts/probe_npad_gurobi_license.py",
    "tests/test_gurobipy_stochastic.py",
    "scripts/audit_nine_campaign.py",
)
PRODUCTS = (
    "result.json", "run_summary.json", "independent_validation.json", "model_audit.json",
    "flows.csv", "inventories.csv", "warehouse_decisions.csv", "unmet_demand.csv",
    "emergency_capacity.csv", "lexicographic_stages.csv", "preflight.json",
    "scenario_performance.csv", "material_balance_by_scenario.csv", "capacity_gap_by_scenario.csv",
    "investment_saturation.csv", "emergency_capacity_daily.csv", "evpi_vss_decomposition.csv",
    "storage_by_warehouse.csv", "storage_by_scenario.csv", "run_completion.json",
    "solver_diagnostics.json", "solver_stage_progress.csv", "solver_presolved_matrix.csv",
    "resources/runtime_capabilities.json", "resources/allocation_receipt.json",
    "resources/matrix_statistics.json", "resources/resource_timeseries.csv",
    "resources/stage_progress.csv", "resources/termination.json", "resources/manifest.json",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def policy():
    record = pair.read(ROOT / POLICY)
    require(record["grid"] == [1, 2, 4, 8, 16]
            and record["order"] == [4, 1, 8, 2, 16]
            and record["seed"] == 42
            and record["miniature_seconds"] == 60
            and record["miniature_soft_memory_gb"] == 1
            and record["miniature_allocation_mib"] == 16384
            and record["miniature_cpus_per_task"] == 16
            and record["miniature_walltime_seconds"] == 1800
            and record["large_instance_submission_allowed"] is False
            and record["automatic_repeats_allowed"] is False,
            "Unqualified miniature policy change.")
    return record


def tools():
    return {name: file_sha256(ROOT / name) for name in TOOLS}


def fixture_data():
    """Keep service nontrivial without reading any production workbook."""
    data = two_scenario_data()
    data.demand_dom[("C1", "soy", "t1")] = 20.0
    data.demand_dom_s[("base", "C1", "soy", "t1")] = 20.0
    data.demand_dom_s[("otimista", "C1", "soy", "t1")] = 50.0
    return data


def spec(threads, output):
    review = policy()
    require(type(threads) is int and threads in review["grid"], "Unqualified thread count.")
    return ExperimentSpec(
        f"threads-{threads}", Path(output) / "analytical-fixture",
        loader=ExcelLoaderConfig(include_stochastic_scenarios=True),
        model=ModelConfig(mode="sto", objective_policy="lexicographic", days_per_period=1),
        solver=SolverConfig(
            threads=threads, seed=42, time_limit=60, mip_gap=0.1,
            solver_options={"SoftMemLimit": 1, "NumericFocus": 1},
            multiobjective_stage_options={role: {"Method": 2} for role in ROLES},
            collect_solver_diagnostics=True, collect_resource_diagnostics=True,
            compact_python_indices=False,
        ), max_estimated_variables=100000,
    )


def prepare(output, source):
    output = Path(output).resolve()
    require(re.fullmatch(r"[0-9a-f]{40}", source) is not None, "Require full source SHA.")
    require(not output.is_relative_to(ROOT) and not ROOT.is_relative_to(output),
            "Output overlaps source.")
    output.mkdir(parents=True, exist_ok=False)
    record = {
        "schema_version": "mvp2-threads-plan-v1", "source_commit": source,
        "policy": policy(), "tools": tools(), "implementation": implementation_identity(),
        "fixture_sha256": scientific_identity(fixture_data()),
        "large_instance_submission_allowed": False,
    }
    pair.write(output / "plan.json", record)
    return record


def check(output):
    record = pair.read(Path(output) / "plan.json")
    require(record.get("schema_version") == "mvp2-threads-plan-v1"
            and re.fullmatch(r"[0-9a-f]{40}", record.get("source_commit", "")) is not None
            and record.get("policy") == policy() and record.get("tools") == tools()
            and record.get("implementation") == implementation_identity()
            and record.get("fixture_sha256") == scientific_identity(fixture_data())
            and record.get("large_instance_submission_allowed") is False,
            "Source/runtime/tool/policy qualification changed.")
    return record


def allocation(job_text, node_text, job_id, node_name, cgroup, affinity):
    job, node = fields(job_text), fields(node_text)
    require(job_text.count("JobId=") == 1 and node_text.count("NodeName=") == 1
            and re.fullmatch(r"[0-9]+", job_id) is not None
            and job.get("JobId") == job_id and job.get("JobState") == "RUNNING"
            and job.get("Partition") == "intel-256" and job.get("NumNodes") == "1"
            and job.get("NumTasks") == "1"
            and job.get("NodeList") == node_name and job.get("BatchHost") == node_name
            and node.get("NodeName") == node_name
            and "ArrayJobId" not in job and "ArrayTaskId" not in job,
            "Require exact standalone running qualification allocation.")
    require(int(job.get("CPUs/Task", "0")) == 16
            and int(job.get("NumCPUs", "0")) >= 16 and affinity >= 16,
            "At least 16 accessible CPUs are required; allocation is not usage.")
    require({memory_mib(job[key]) for key in ("TRES", "AllocTRES") if key in job} == {16384}
            and int(node.get("RealMemory", "0")) >= 196608
            and type(cgroup.get("limit_bytes")) is int
            and 16384 * 1024**2 <= cgroup["limit_bytes"] <= int(node["RealMemory"]) * 1024**2,
            "Require 16 GiB allocation and finite observed cgroup on intel-256 class.")
    return {"job_id": job_id, "node": node_name, "partition": "intel-256",
            "allocated_memory_mib": 16384, "allocated_cpus": int(job["NumCPUs"]),
            "cpus_per_task": 16, "accessible_cpus": affinity, "cgroup": cgroup}


def arm(output, threads):
    output = Path(output).resolve()
    check(output)
    experiment = spec(threads, output)
    run = run_experiment(experiment, output / "miniatures",
                         loader=lambda *_: fixture_data(), progress=lambda *_: None)
    require(run.status == "optimal" and run.independent_validation_status == "accepted"
            and run.lexicographic_completed_stage_count == 3
            and run.lexicographic_overall_status == "complete",
            "Miniature did not complete independent validation and hierarchy.")
    verify_arm(output, threads)
    return 0


def verify_arm(output, threads):
    folder = Path(output) / "miniatures" / f"threads-{threads}"
    valid, reason = verify_completion(folder, _checkpoint_identity(spec(threads, output)))
    require(valid, reason)
    summary = pair.read(folder / "run_summary.json")
    require(summary["status"] == "optimal"
            and summary["independent_validation_status"] == "accepted"
            and summary["lexicographic_completed_stage_count"] == 3
            and summary["lexicographic_overall_status"] == "complete",
            "Incomplete miniature hierarchy or residual acceptance.")
    result = pair.read(folder / "result.json")["result"]
    independent = pair.read(folder / "independent_validation.json")
    require(classify_stages(result.get("metadata", {}).get("lexicographic_stages", []),
                            independent.get("status")) == "accepted_at_ten_percent",
            "Inherited service/gap/degradation audit rejected.")
    settings = pair.read(folder / "solver_diagnostics.json")["effective_stage_parameters"]
    for role in ROLES:
        require(settings[role]["Threads"] == threads and settings[role]["Method"] == 2
                and settings[role]["MIPGap"] == 0.1 and settings[role]["SoftMemLimit"] == 1
                and settings[role]["NumericFocus"] == 1 and settings[role]["TimeLimit"] == 60,
                "Observed per-pass settings differ from the miniature contract.")
    return summary


def execute(output, job_id, node_name, runner=subprocess.run):
    output = Path(output).resolve()
    plan = check(output)
    (output / ".execution-claimed").mkdir()
    resource = allocation((output / "scheduler/job.txt").read_text(),
                          (output / "scheduler/node.txt").read_text(), job_id, node_name,
                          cgroup_memory(), len(os.sched_getaffinity(0)))
    pair.write(output / "allocation.json", resource)
    env = dict(os.environ, GRB_LICENSE_FILE=pair.LICENSE_FILE,
               AGROLOGISTIC_SOURCE_COMMIT=plan["source_commit"],
               PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")
    probe = runner([sys.executable, str(ROOT / "scripts/probe_npad_gurobi_license.py"),
                    "--output", str(output / "license.json")], env=env, cwd=ROOT,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   check=False, timeout=60)
    require(probe.returncode == 0 and baseline.license_accepted(pair.read(output / "license.json")),
            "Fresh license capability rejected; no miniature grid starts.")
    observations = []
    for threads in policy()["order"]:
        check(output)
        try:
            process = runner([sys.executable, str(Path(__file__).resolve()), "arm",
                              "--output", str(output), "--threads", str(threads)],
                             env=env, cwd=ROOT, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, check=False, timeout=180)
        except Exception as error:
            pair.write(output / f"arm-{threads}.json", {
                "threads": threads, "error_type": type(error).__name__, "status": "failed"})
            raise
        pair.write(output / f"arm-{threads}.json", {
            "threads": threads, "return_code": process.returncode})
        require(process.returncode == 0, f"Miniature threads={threads} failed; preserve evidence.")
        summary = verify_arm(output, threads)
        observations.append({"threads": threads, "status": summary["status"],
                             "independent_validation": summary["independent_validation_status"]})
    check(output)
    pair.write(output / "qualification.json", {
        "schema_version": "mvp2-threads-qualification-v1", "status": "accepted",
        "source_commit": plan["source_commit"], "plan_sha256": file_sha256(output / "plan.json"),
        "allocation": resource, "observations": observations,
        "large_instance_submission_allowed": False, "performance_acceptance": False,
        "qualification": "Parameter/closure qualification only; not production thread utilization.",
    })
    return 0


def collect(output, accounting, destination):
    output, destination = Path(output).resolve(), Path(destination).resolve()
    plan = check(output)
    submission = pair.read(output / "submission.json")
    job = submission["job_id"]
    require(re.fullmatch(r"[0-9]+", job) is not None
            and submission["source_commit"] == plan["source_commit"],
            "Submission identity changed.")
    terminal = transfer.terminal_accounting(accounting, job)
    require(terminal is not None, "No unambiguous terminal root accounting; retry collection only.")
    require(not destination.is_relative_to(output) and not output.is_relative_to(destination)
            and not destination.is_relative_to(ROOT) and not ROOT.is_relative_to(destination),
            "Collection overlaps source/evidence.")
    errors = []
    try:
        require(terminal["state"] == "COMPLETED" and terminal["exit_code"] == "0:0",
                "Scheduler did not close successfully.")
        report = pair.read(output / "qualification.json")
        require(report["status"] == "accepted" and report["source_commit"] == plan["source_commit"]
                and report["plan_sha256"] == file_sha256(output / "plan.json")
                and report["large_instance_submission_allowed"] is False
                and report["performance_acceptance"] is False
                and report["observations"] == [
                    {"threads": t, "status": "optimal", "independent_validation": "accepted"}
                    for t in policy()["order"]], "Qualification receipt changed.")
        observed = allocation((output / "scheduler/job.txt").read_text(),
                              (output / "scheduler/node.txt").read_text(), job,
                              report["allocation"]["node"], report["allocation"]["cgroup"],
                              report["allocation"]["accessible_cpus"])
        require(observed == report["allocation"] == pair.read(output / "allocation.json")
                and baseline.license_accepted(pair.read(output / "license.json")),
                "Original allocation/license evidence changed.")
        require(pair.read(output / "worker_status.json") == {
            "job_id": job, "exit_code": 0, "status": "completed"}, "Worker did not close.")
        for threads in policy()["order"]:
            require(pair.read(output / f"arm-{threads}.json") == {
                "threads": threads, "return_code": 0}, "Child process did not close.")
            verify_arm(output, threads)
    except (OSError, ValueError, KeyError, TypeError) as error:
        errors.append(type(error).__name__)
    destination.mkdir(parents=True, exist_ok=False)
    assets = {"accounting.txt": accounting.encode()}
    names = ["plan.json", "submission.json", "allocation.json", "license.json",
             "qualification.json", "worker_status.json", "scheduler/job.txt", "scheduler/node.txt"]
    names += [f"arm-{threads}.json" for threads in policy()["order"]]
    for name in names:
        path = output / name
        require(not path.is_symlink() and path.resolve().is_relative_to(output),
                "Reject linked evidence.")
        if path.is_file():
            assets[name] = path.read_bytes()
    # Enumerate fixture products; never traverse arbitrary JSON, raw logs or credentials.
    for threads in policy()["order"]:
        for product in PRODUCTS:
            path = output / "miniatures" / f"threads-{threads}" / product
            require(not path.is_symlink() and path.resolve().is_relative_to(output),
                    "Reject linked products.")
            if path.is_file():
                assets[path.relative_to(output).as_posix()] = path.read_bytes()
    record = {"schema_version": "mvp2-threads-collection-v1",
              "status": "accepted" if not errors else "evidence_rejected",
              "scope": "licensed_miniature_parameter_qualification",
              "terminal": terminal, "errors": errors, "source_commit": plan["source_commit"],
              "large_instance_submission_allowed": False,
              "artifacts": {name: transfer.digest(data) for name, data in assets.items()}}
    assets["collection.json"] = (json.dumps(record, indent=2) + "\n").encode()
    archive = destination / f"threads-qualification-evidence-{job}.tar.gz"
    with tarfile.open(archive, "x:gz") as stream:
        for name, data in sorted(assets.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            stream.addfile(info, io.BytesIO(data))
    checksum = file_sha256(archive)
    (archive.with_suffix(archive.suffix + ".sha256")).write_text(
        f"{checksum}  {archive.name}\n", encoding="utf-8")
    print(f"COLLECTION_STATUS={record['status']}\nSHA256={checksum}\nDOWNLOAD={archive}")
    print(f"TRANSFER_CHECKSUM={archive}.sha256\nNo production job or repeat is admitted.")
    return int(bool(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "check", "execute", "arm", "collect"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source")
    parser.add_argument("--threads", type=int)
    parser.add_argument("--job")
    parser.add_argument("--node")
    parser.add_argument("--accounting", type=Path)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        require(args.source is not None, "Require pinned source.")
        prepare(args.output, args.source)
    elif args.action == "check":
        check(args.output)
    elif args.action == "arm":
        return arm(args.output, args.threads)
    elif args.action == "execute":
        require(args.job is not None and args.node is not None, "Require allocation identity.")
        try:
            rc = execute(args.output, args.job, args.node)
            status = {"job_id": args.job, "exit_code": rc, "status": "completed"}
        except Exception as error:
            rc = 1
            status = {"job_id": args.job, "exit_code": rc, "status": "failed",
                      "error_type": type(error).__name__}
        pair.write(args.output / "worker_status.json", status)
        return rc
    else:
        require(args.accounting is not None and args.destination is not None,
                "Require terminal accounting and new collection directory.")
        return collect(args.output, args.accounting.read_text(), args.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
