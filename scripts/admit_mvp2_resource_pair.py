"""Admit one serial positive-control pair from reviewed, immutable input evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import preflight_mvp2_resource_pair as inputs  # noqa: E402
from scripts.probe_npad_gurobi_license import LICENSE_FILE, PROBE_SIZE  # noqa: E402
from scripts.validate_scip_memory_resources import fields, memory_mib  # noqa: E402
from src.logic.run_integrity import file_sha256  # noqa: E402

TOOLS = (*inputs.TOOLS, "scripts/admit_mvp2_resource_pair.py",
         "scripts/submit_mvp2_resource_pair.sh", "scripts/run_mvp2_resource_pair.slurm",
         "scripts/run_batch_hpc.py", "scripts/audit_nine_campaign.py",
         "scripts/probe_npad_gurobi_license.py")


def identity(value):
    """Bind JSON content independently of transfer whitespace and line endings."""
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def tool_identity():
    return {name: file_sha256(ROOT / name) for name in TOOLS}


def check_inputs(plan_path, receipt_path, reviewed_identity):
    """Verify original NPAD products, rather than trusting a pasted acceptance label."""
    plan_path, receipt_path = Path(plan_path).resolve(), Path(receipt_path).resolve()
    plan, manifest = inputs.check_plan(plan_path)
    if plan["case"] != "h215-warehouse":
        raise ValueError("Solve admission is qualified only for h215-warehouse.")
    receipt = read(receipt_path)
    if identity(receipt) != reviewed_identity:
        raise ValueError("Input receipt differs from the reviewed JSON identity.")
    if (receipt.get("schema_version") != "mvp2-resource-pair-preflight-v1"
            or receipt.get("status") != "accepted"
            or receipt.get("case", "h215-warehouse") != "h215-warehouse"
            or receipt.get("optimization_executed") is not False
            or receipt.get("large_instance_submission_allowed") is not False
            or receipt.get("implementation") != plan["implementation"]
            or receipt.get("tools") != inputs.tool_identity()
            or receipt.get("plan_sha256") != file_sha256(plan_path)
            or receipt.get("campaign_sha256") != plan["campaign_sha256"]
            or receipt.get("workbook_sha256") != plan["workbook_sha256"]):
        raise ValueError("Input preflight contract or evidence identity changed.")
    allocation = receipt["allocation"]
    scheduler = receipt_path.parent.parent / "scheduler"
    observed = inputs.allocation(
        (scheduler / "job.txt").read_text(), (scheduler / "node.txt").read_text(),
        job_id=allocation["job_id"], node_name=allocation["node"],
    )
    if allocation != observed:
        raise ValueError("Preflight allocation does not match its captured scheduler records.")
    expected = {f"{spec.name}/{name}" for spec in manifest.experiments
                for name in inputs.PRODUCTS}
    if set(receipt.get("artifacts", {})) != expected:
        raise ValueError("Require all twelve original paired input products.")
    snapshots = []
    for spec in manifest.experiments:
        folder = receipt_path.parent / spec.name
        for name in inputs.PRODUCTS:
            if file_sha256(folder / name) != receipt["artifacts"][f"{spec.name}/{name}"]:
                raise ValueError(f"Changed preflight product: {spec.name}/{name}")
        snapshot = read(folder / "preflight.json")
        snapshot.pop("execution", None)
        if (snapshot != receipt["model_size"]
                or snapshot["data_signature"]["counts"]["warehouses"] != 215
                or snapshot["scenario_count"] != 9 or snapshot["period_count"] != 60
                or snapshot["total_variables"] != 14054654
                or read(folder / "interhub_connectivity_audit.json")["status"] != "accepted"):
            raise ValueError("Unexpected positive-control dimensions or connectivity.")
        snapshots.append(snapshot)
    if snapshots[0] != snapshots[1] or any(
            receipt["artifacts"][f"{manifest.experiments[0].name}/{name}"] !=
            receipt["artifacts"][f"{manifest.experiments[1].name}/{name}"]
            for name in inputs.PRODUCTS[1:]):
        raise ValueError("Input products differ between arms.")
    return plan, manifest, receipt


def validate_arm_order(order):
    """Keep arm indices canonical while admitting either serial execution order."""
    if (not isinstance(order, (list, tuple)) or len(order) != 2
            or any(type(index) is not int for index in order)
            or set(order) != {0, 1}):
        raise ValueError("Arm order must contain each canonical index (0 and 1) once.")
    return list(order)


def prepare(plan_path, receipt_path, reviewed_identity, destination, *, arm_order=(0, 1)):
    arm_order = validate_arm_order(arm_order)
    plan_path, receipt_path = Path(plan_path).resolve(), Path(receipt_path).resolve()
    plan, _, _ = check_inputs(plan_path, receipt_path, reviewed_identity)
    destination = Path(destination).resolve()
    protected = (ROOT, plan_path.parent, receipt_path.parent.parent,
                 Path(plan["reference_manifest"]).resolve().parent,
                 Path(plan["qualification_report"]).resolve().parent)
    if (destination.exists() or any(destination.is_relative_to(p)
                                   or p.is_relative_to(destination) for p in protected)):
        raise ValueError("Choose a new execution directory outside preserved evidence/source.")
    raw = yaml.safe_load((plan_path.parent / "campaign.yaml").read_text())
    raw["output_dir"] = str(destination / "runs")
    destination.mkdir(parents=True, exist_ok=False)
    campaign = destination / "campaign.yaml"
    with campaign.open("x", encoding="utf-8") as stream:
        yaml.safe_dump(raw, stream, sort_keys=False)
    result = {
        "schema_version": "mvp2-pair-solve-plan-v1",
        "status": "ready_for_single_pair_submission",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "input_plan": str(plan_path), "input_plan_sha256": file_sha256(plan_path),
        "input_receipt": str(receipt_path), "input_receipt_sha256": file_sha256(receipt_path),
        "reviewed_receipt_identity": reviewed_identity,
        "campaign_sha256": file_sha256(campaign), "tools": tool_identity(),
        "arm_order": arm_order, "production_explicit_lifecycle_allowed": False,
        "allocation_profile": {"partition": "intel-256", "memory_mib": 196608,
                               "solver_threads": 4, "optimization_seconds_per_arm": 28800},
        "qualification": "One serial observation pair; no performance benefit asserted.",
    }
    write(destination / "solve_plan.json", result)
    return result


def check_execution(path):
    path = Path(path).resolve()
    record = read(path)
    validate_arm_order(record.get("arm_order"))
    if (record.get("schema_version") != "mvp2-pair-solve-plan-v1"
            or record.get("status") != "ready_for_single_pair_submission"
            or record.get("tools") != tool_identity()
            or record.get("production_explicit_lifecycle_allowed") is not False
            or record.get("allocation_profile") != {
                "partition": "intel-256", "memory_mib": 196608,
                "solver_threads": 4, "optimization_seconds_per_arm": 28800}):
        raise ValueError("Execution tools or paired solve plan changed.")
    for field in ("input_plan", "input_receipt"):
        if file_sha256(Path(record[field])) != record[f"{field}_sha256"]:
            raise ValueError(f"Changed execution evidence: {field}")
    _, manifest, _ = check_inputs(record["input_plan"], record["input_receipt"],
                                   record["reviewed_receipt_identity"])
    campaign = path.parent / "campaign.yaml"
    original = yaml.safe_load((Path(record["input_plan"]).parent / "campaign.yaml").read_text())
    original["output_dir"] = str(path.parent / "runs")
    if (file_sha256(campaign) != record["campaign_sha256"]
            or yaml.safe_load(campaign.read_text()) != original):
        raise ValueError("Execution manifest differs beyond its new output directory.")
    protected = (ROOT, Path(record["input_plan"]).parent,
                 Path(record["input_receipt"]).parent.parent)
    if any(path.parent.is_relative_to(p) or p.is_relative_to(path.parent) for p in protected):
        raise ValueError("Execution directory overlaps preserved evidence/source.")
    return record, manifest


def allocation(job_text, node_text, *, job_id, node_name):
    job, node = fields(job_text), fields(node_text)
    if (job.get("JobId") != job_id or node.get("NodeName") != node_name
            or job.get("JobState") != "RUNNING" or job.get("Partition") != "intel-256"
            or job.get("NumNodes") != "1" or job.get("NodeList") != node_name
            or job.get("BatchHost") != node_name or "ArrayJobId" in job or "ArrayTaskId" in job
            or int(job.get("CPUs/Task", "0")) < 4 or int(job.get("NumCPUs", "0")) < 4
            or job_text.count("JobId=") != 1 or node_text.count("NodeName=") != 1):
        raise ValueError("Require the exact standalone running paired-solve allocation.")
    memories = {memory_mib(job[key]) for key in ("TRES", "AllocTRES") if key in job}
    if memories != {196608} or int(node.get("RealMemory", "0")) < 196608:
        raise ValueError("Require 192 GiB allocated memory on the reviewed node class.")
    return {"job_id": job_id, "node": node_name, "partition": job["Partition"],
            "allocated_memory_mib": 196608, "allocated_cpus": int(job["NumCPUs"]),
            "cpus_per_task": int(job["CPUs/Task"]), "effective_qos": job.get("QOS")}


def execute(path, resource, submitted_tools, source_commit, *, runner=subprocess.run):
    """Fresh sequential processes; scientific acceptance is delegated to the existing audit."""
    path = Path(path).resolve()
    record, _ = check_execution(path)
    plan_sha256 = file_sha256(path)

    def recheck():
        if file_sha256(path) != plan_sha256:
            raise ValueError("Prepared solve plan changed during execution.")
        check_execution(path)

    if submitted_tools != tool_identity():
        raise ValueError("Tools changed after scheduler submission.")
    if (not source_commit or len(source_commit) != 40
            or any(c not in "0123456789abcdef" for c in source_commit)):
        raise ValueError("Require the login-node pinned source commit.")
    if resource.get("allocated_memory_mib") != 196608:
        raise ValueError("Solve allocation has not been admitted.")
    destination = path.parent
    if any((destination / name).exists() for name in (
            "runs", "logs", "comparison", "solve_admission.json", "pair_execution.json")):
        raise ValueError("Execution already started; preserve it and prepare a new pair.")
    (destination / "logs").mkdir()
    env = dict(os.environ, PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1",
               AGROLOGISTIC_SOURCE_COMMIT=source_commit, GRB_LICENSE_FILE=LICENSE_FILE)
    env.pop("SCIPOPTDIR", None)
    env.pop("SLURM_ARRAY_TASK_ID", None)
    license_report = destination / "license_capability.json"
    try:
        license_process = runner(
            [sys.executable, str(ROOT / "scripts/probe_npad_gurobi_license.py"),
             "--output", str(license_report)], cwd=ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=60,
        )
        capability = read(license_report)
        license_ok = (license_process.returncode == 0
                      and capability.get("schema_version") == "npad-gurobi-license-capability-v1"
                      and capability.get("status") == "accepted"
                      and capability.get("license_file") == LICENSE_FILE
                      and capability.get("large_model_construction_allowed") is True
                      and capability.get("probe_variable_count") == PROBE_SIZE
                      and capability.get("probe_constraint_count") == PROBE_SIZE
                      and capability.get("solver_status_code") == 2
                      and abs(capability.get("objective_value", float("inf")) - PROBE_SIZE) <= 1e-6)
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        license_ok = False
    recheck()
    admission = {"schema_version": "mvp2-pair-solve-admission-v1",
                 "status": "admitted" if license_ok else "license_capability_rejected",
                 "created_at_utc": datetime.now(UTC).isoformat(),
                 "solve_plan_sha256": file_sha256(path), "source_commit": source_commit,
                 "allocation": resource, "tools": submitted_tools,
                 "arm_order": record["arm_order"], "scope": "one_h215_warehouse_serial_pair",
                 "license_file": LICENSE_FILE, "license_capability_accepted": license_ok,
                 "license_capability_sha256": (file_sha256(license_report)
                                               if license_report.is_file() else None)}
    write(destination / "solve_admission.json", admission)
    if not license_ok:
        write(destination / "pair_execution.json", {
            "schema_version": "mvp2-pair-execution-v1", "status": "license_capability_rejected",
            "optimization_attempted": False, "arm_processes": [],
            "arm_order": record["arm_order"],
            "source_commit": source_commit, "allocation": resource,
            "solve_plan_sha256": file_sha256(path),
            "qualification": "No large model constructed; license capability was not established.",
        })
        print("STOP: NPAD license capability rejected; no large model constructed.")
        return 1
    print("NPAD GUROBI LICENSE CAPABILITY: ACCEPTED", flush=True)
    observations = []
    campaign = destination / "campaign.yaml"
    for index in record["arm_order"]:
        recheck()
        with (destination / "logs" / f"arm-{index}.out").open("x", encoding="utf-8") as log:
            process = runner([sys.executable, str(ROOT / "scripts/run_batch_hpc.py"),
                              str(campaign), "--index", str(index)],
                             cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
        observations.append({"index": index, "return_code": process.returncode})
        write(destination / "logs" / f"arm-{index}-exit.json", observations[-1])
    recheck()
    with (destination / "logs/audit.out").open("x", encoding="utf-8") as log:
        audit = runner([sys.executable, str(ROOT / "scripts/audit_nine_campaign.py"),
                        str(campaign), "--output-dir", str(destination / "comparison"),
                        "--require-accepted"], cwd=ROOT, env=env, stdout=log,
                       stderr=subprocess.STDOUT, check=False)
    recheck()
    result = {"schema_version": "mvp2-pair-execution-v1",
              "status": "both_processes_returned", "optimization_attempted": True,
              "arm_processes": observations, "audit_return_code": audit.returncode,
              "arm_order": record["arm_order"],
              "source_commit": source_commit, "allocation": resource,
              "solve_plan_sha256": file_sha256(path),
              "qualification": "Execution closure is not scientific or performance acceptance."}
    write(destination / "pair_execution.json", result)
    return int(any(o["return_code"] for o in observations) or audit.returncode != 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-plan", type=Path)
    parser.add_argument("--input-receipt", type=Path)
    parser.add_argument("--reviewed-receipt-identity")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--arm-order", choices=("control,compact", "compact,control"),
                        help="Preparation only; default control,compact. Arm indices stay fixed.")
    parser.add_argument("--solve-plan", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--tool-identity", action="store_true")
    for key in ("job-file", "node-file"):
        parser.add_argument(f"--{key}", type=Path)
    for key in ("job-id", "node-name", "tools", "source-commit"):
        parser.add_argument(f"--{key}")
    args = parser.parse_args()
    if args.solve_plan is None:
        if any(v is None for v in (args.input_plan, args.input_receipt,
                                  args.reviewed_receipt_identity, args.output_dir)):
            parser.error("Preparation requires reviewed input evidence and a new output directory.")
        prepare(args.input_plan, args.input_receipt,
                args.reviewed_receipt_identity, args.output_dir,
                arm_order=(1, 0) if args.arm_order == "compact,control" else (0, 1))
        print(args.output_dir / "solve_plan.json")
        print("MVP2 SINGLE PAIR: PREPARED; ALLOCATION GATE STILL REQUIRED")
        return 0
    if args.arm_order is not None:
        parser.error("Execution order is read from the prepared solve plan; do not override it.")
    check_execution(args.solve_plan)
    if args.tool_identity:
        print(json.dumps(tool_identity()))
    elif args.check:
        if (args.solve_plan.parent / "solve_admission.json").exists():
            raise ValueError("Pair already admitted; duplicate submission rejected.")
        print("MVP2 SINGLE PAIR CONTRACT: VERIFIED")
    else:
        if any(getattr(args, key) is None for key in (
                "job_file", "node_file", "job_id", "node_name", "tools", "source_commit")):
            parser.error("Execution requires tool/source identities and exact allocation.")
        resource = allocation(args.job_file.read_text(), args.node_file.read_text(),
                              job_id=args.job_id, node_name=args.node_name)
        return execute(args.solve_plan, resource, json.loads(args.tools), args.source_commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
