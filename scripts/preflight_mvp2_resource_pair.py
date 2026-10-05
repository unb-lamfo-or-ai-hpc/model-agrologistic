"""Verify immutable positive-control inputs without building or solving a MIP."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.prepare_mvp2_resource_contrasts import STAGES, verify_qualification  # noqa: E402
from scripts.validate_scip_memory_resources import fields, memory_mib  # noqa: E402
from src.logic.experiment_runner import inspect_experiment, load_experiment_manifest  # noqa: E402
from src.logic.run_integrity import file_sha256, implementation_identity  # noqa: E402

TOOLS = (
    "scripts/prepare_mvp2_resource_contrasts.py",
    "scripts/preflight_mvp2_resource_pair.py",
    "scripts/submit_mvp2_pair_preflight.sh",
    "scripts/run_mvp2_pair_preflight.slurm",
)
PRODUCTS = (
    "preflight.json", "model_audit.json", "interhub_connectivity_audit.json",
    "interhub_components.csv", "interhub_repair_edges.csv", "interhub_path_summary.csv",
)
PREFLIGHT_CASES = {"h215-warehouse": 215, "h300-warehouse": 300}


def tool_identity():
    return {name: file_sha256(ROOT / name) for name in TOOLS}


def check_plan(path):
    """Reconstruct both arms from the frozen reference and recheck all evidence."""
    path = Path(path).resolve()
    plan = json.loads(path.read_text(encoding="utf-8"))
    if (
        plan.get("schema_version") != "mvp2-resource-contrast-plan-v1"
        or plan.get("status") != "prepared_not_admitted"
        or plan.get("case") not in PREFLIGHT_CASES
        or plan.get("contrast") != "compact_python_indices"
        or plan.get("large_instance_submission_allowed") is not False
        or plan.get("production_explicit_lifecycle_allowed") is not False
        or plan.get("implementation") != implementation_identity()
        or plan.get("preparer_sha256") != file_sha256(ROOT / TOOLS[0])
    ):
        raise ValueError("Require a qualified warehouse-only h215 or h300 input plan.")
    population = PREFLIGHT_CASES[plan["case"]]
    qualification = Path(plan["qualification_report"]).resolve()
    reference = Path(plan["reference_manifest"]).resolve()
    campaign = path.parent / "campaign.yaml"
    for asset, key in ((qualification, "qualification_report_sha256"),
                       (reference, "reference_manifest_sha256"),
                       (campaign, "campaign_sha256")):
        if file_sha256(asset) != plan[key]:
            raise ValueError(f"Changed evidence: {key}")
    report = verify_qualification(qualification)
    if report.get("source_commit") != plan.get("qualified_source_commit"):
        raise ValueError("Qualified commit mismatch.")
    index = plan["reference_index"]
    baseline = load_experiment_manifest(reference)
    if type(index) is not int or not 0 <= index < len(baseline.experiments):
        raise ValueError("Invalid reference index.")
    spec = baseline.experiments[index]
    if (spec.metadata.get("warehouse_population") != population
            or spec.model.use_direct_origin_customer):
        raise ValueError("Reference population or warehouse-only policy changed.")
    if file_sha256(spec.workbook) != plan["workbook_sha256"]:
        raise ValueError("Workbook checksum mismatch.")
    manifest = load_experiment_manifest(campaign)
    if (manifest.output_dir != path.parent / "runs" or not manifest.continue_on_error
            or len(manifest.experiments) != 2
            or any(path.parent.is_relative_to(p.parent) for p in (reference, qualification))):
        raise ValueError("Require isolated, immutable two-arm destinations.")
    for actual, arm, compact in zip(manifest.experiments, ("control", "compact"),
                                    (False, True), strict=True):
        expected = asdict(spec)
        expected["name"] = f"mvp2_{plan['case'].replace('-', '_')}_{arm}"
        expected["solver"].update(
            collect_resource_diagnostics=True, resource_sample_seconds=5.0,
            resource_max_samples=8192, collect_solver_diagnostics=True,
            compact_python_indices=compact,
            multiobjective_stage_options={role: {"Method": 2} for role in STAGES},
        )
        expected["metadata"] = copy.deepcopy(spec.metadata)
        expected["metadata"].update(
            resource_contrast_arm=arm,
            reference_manifest_sha256=plan["reference_manifest_sha256"],
            reference_workbook_sha256=plan["workbook_sha256"],
            resource_contrast_scope="post_build_python_indices_only",
        )
        if asdict(actual) != expected:
            raise ValueError("Pair differs from the controlled reference contract.")
    return plan, manifest


def allocation(job_text, node_text, *, job_id, node_name):
    """Reuse the observed NPAD TRES grammar, without memory environment variables."""
    job, node = fields(job_text), fields(node_text)
    if (job.get("JobId") != job_id or node.get("NodeName") != node_name
            or job.get("JobState") != "RUNNING" or job.get("Partition") != "intel-256"
            or job.get("NumNodes") != "1" or job.get("NodeList") != node_name
            or job.get("BatchHost") != node_name
            or "ArrayJobId" in job or "ArrayTaskId" in job
            or int(job.get("CPUs/Task", "0")) < 4
            or int(job.get("NumCPUs", "0")) < 4
            or job_text.count("JobId=") != 1 or node_text.count("NodeName=") != 1):
        raise ValueError("Require the exact standalone running preflight allocation.")
    memories = {memory_mib(job[key]) for key in ("TRES", "AllocTRES") if key in job}
    if memories != {16384} or int(node.get("RealMemory", "0")) < 16384:
        raise ValueError("Require the reviewed 16-GiB preflight allocation.")
    return {"job_id": job_id, "node": node_name, "partition": job["Partition"],
            "allocated_memory_mib": 16384, "allocated_cpus": int(job["NumCPUs"]),
            "cpus_per_task": int(job["CPUs/Task"]), "effective_qos": job.get("QOS")}


def preflight(path, destination, resource_record, *, inspector=inspect_experiment):
    """Export new input snapshots and a closed receipt; no optimizer is called."""
    path, destination = Path(path).resolve(), Path(destination).resolve()
    plan, manifest = check_plan(path)
    submitted_tools = tool_identity()
    protected = (path.parent, Path(plan["reference_manifest"]).resolve().parent,
                 Path(plan["qualification_report"]).resolve().parent)
    if destination.exists() or any(destination.is_relative_to(p) for p in protected):
        raise ValueError("Choose a new preflight directory outside preserved evidence.")
    destination.mkdir(parents=True, exist_ok=False)
    snapshots = []
    for spec in manifest.experiments:
        inspector(spec, destination)
        folder = destination / spec.name
        snapshot = json.loads((folder / "preflight.json").read_text(encoding="utf-8"))
        snapshot.pop("execution", None)
        counts = snapshot["data_signature"]["counts"]
        connectivity = json.loads((folder / "interhub_connectivity_audit.json").read_text())
        if (counts["warehouses"] != PREFLIGHT_CASES[plan["case"]]
                or counts["scenarios"] != 9
                or counts["periods"] != 60 or snapshot["scenario_count"] != 9
                or snapshot["period_count"] != 60
                or any(snapshot[key] != 0 for key in (
                    "routes_oc", "base_routes_oc", "repair_routes_oc"
                ))
                or snapshot["workbook_sha256"] != plan["workbook_sha256"]
                or spec.max_estimated_variables is None
                or not 0 < snapshot["total_variables"] <= spec.max_estimated_variables
                or connectivity.get("status") != "accepted"):
            raise ValueError("Population, scenario, size or connectivity preflight failed.")
        snapshots.append(snapshot)
    if snapshots[0] != snapshots[1]:
        raise ValueError("The two arms loaded different model data or dimensions.")
    for name in PRODUCTS[1:]:
        if len({file_sha256(destination / spec.name / name)
                for spec in manifest.experiments}) != 1:
            raise ValueError(f"The arms differ in {name}.")
    # Recheck source/data/evidence after loading, before closing the snapshot.
    check_plan(path)
    if tool_identity() != submitted_tools:
        raise ValueError("Preflight tools changed during input inspection.")
    artifacts = {f"{spec.name}/{name}": file_sha256(destination / spec.name / name)
                 for spec in manifest.experiments for name in PRODUCTS}
    result = {
        "schema_version": "mvp2-resource-pair-preflight-v1",
        "status": "accepted", "case": plan["case"],
        "created_at_utc": datetime.now(UTC).isoformat(),
        "plan_sha256": file_sha256(path), "campaign_sha256": plan["campaign_sha256"],
        "workbook_sha256": plan["workbook_sha256"], "implementation": implementation_identity(),
        "tools": tool_identity(), "allocation": resource_record,
        "model_size": snapshots[0], "artifacts": artifacts,
        "optimization_executed": False, "large_instance_submission_allowed": False,
        "qualification": (
            "Input preflight only; solve allocation and paired admission remain required."
        ),
    }
    (destination / "pair_preflight.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--tool-identity", action="store_true")
    for key in ("output-dir", "job-file", "node-file"):
        parser.add_argument(f"--{key}", type=Path)
    for key in ("job-id", "node-name", "tools"):
        parser.add_argument(f"--{key}")
    args = parser.parse_args()
    check_plan(args.plan)
    if args.tool_identity:
        print(json.dumps(tool_identity()))
    elif args.check:
        print("MVP2 PAIR CONTRACT: VERIFIED; LARGE SUBMISSION REMAINS CLOSED")
    else:
        if any(getattr(args, key) is None for key in (
                "output_dir", "job_file", "node_file", "job_id", "node_name", "tools")):
            parser.error("Preflight requires exact allocation records and submitted tool hashes.")
        if json.loads(args.tools) != tool_identity():
            raise ValueError("Preflight tools changed after submission.")
        resource = allocation(args.job_file.read_text(), args.node_file.read_text(),
                              job_id=args.job_id, node_name=args.node_name)
        preflight(args.plan, args.output_dir, resource)
        print(args.output_dir / "pair_preflight.json")
        print("MVP2 PAIR INPUT PREFLIGHT: ACCEPTED; LARGE SUBMISSION REMAINS CLOSED")


if __name__ == "__main__":
    main()
