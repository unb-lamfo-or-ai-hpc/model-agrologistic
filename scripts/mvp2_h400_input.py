"""Prepare and inspect exactly one h400 direct-enabled control; never solve."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import preflight_mvp2_resource_pair as inputs  # noqa: E402
from scripts.prepare_mvp2_resource_contrasts import STAGES, verify_qualification  # noqa: E402
from src.logic.experiment_runner import inspect_experiment, load_experiment_manifest  # noqa: E402
from src.logic.run_integrity import file_sha256, implementation_identity  # noqa: E402

ARM = "mvp2_h400_direct_control"
POLICY = "docs/mvp2_h400_input_policy.json"
TOOLS = (
    POLICY, "scripts/mvp2_h400_input.py", "scripts/collect_mvp2_h400_input.py",
    "scripts/submit_mvp2_h400_input.sh", "scripts/run_mvp2_h400_input.slurm",
    "scripts/npad_mvp2_h400_input.sh",
    "scripts/prepare_mvp2_resource_contrasts.py", "scripts/preflight_mvp2_resource_pair.py",
    "scripts/collect_mvp2_pair_preflight.py",
)
PRODUCTS = inputs.PRODUCTS


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def policy():
    value = json.loads((ROOT / POLICY).read_text(encoding="utf-8"))
    require(value["schema_version"] == "mvp2-h400-input-policy-v1"
            and value["case"] == "h400-direct"
            and value["scope"] == "input_inspection_only"
            and value["optimization_allowed"] is False, "Input-only policy required.")
    return value


def tool_identity():
    return {name: file_sha256(ROOT / name) for name in TOOLS}


def historical_profile():
    p = policy()
    historical = json.loads((ROOT / p["historical_comparison"]).read_text(encoding="utf-8"))
    cases = [row for row in historical if row["name"] == p["historical_case"]]
    require(len(cases) == 1, "Historical comparison identity differs.")
    return cases[0]


def reference_spec(reference, qualification):
    p = policy()
    require(file_sha256(reference) == p["reference_manifest_sha256"], "Reference hash differs.")
    require(file_sha256(qualification) == p["qualification_report_sha256"],
            "Qualification hash differs.")
    qualified = verify_qualification(qualification)
    manifest = load_experiment_manifest(reference)
    selected = [i for i, spec in enumerate(manifest.experiments)
                if spec.metadata.get("warehouse_population") == 400
                and spec.model.mode == "sto"
                and spec.model.objective_policy == "lexicographic"
                and spec.model.use_direct_origin_customer is True]
    require(selected == [p["reference_index"]], "Require exact unique h400-direct index.")
    spec = manifest.experiments[selected[0]]
    require(file_sha256(spec.workbook) == p["workbook_sha256"], "Workbook hash differs.")
    old = historical_profile()
    require(old["workbook_sha256"] == p["workbook_sha256"]
            and old["estimated_variables"] == p["snapshot_fields"]["total_variables"]
            and all(old["route_counts"][key] == p["snapshot_fields"][key]
                    for key in old["route_counts"]), "Historical size profile differs.")
    for name in ("model", "loader"):
        current = json.loads(json.dumps(asdict(getattr(spec, name))))
        require(all(current.get(key) == value for key, value in old[f"{name}_config"].items()),
                f"Reference {name} policy differs.")
    solver = spec.solver
    require(not spec.calculate_evpi_vss and not spec.resume_evpi_vss
            and type(spec.max_estimated_variables) is int
            and spec.max_estimated_variables == p["reference_limit"]
            and solver.backend == "gurobipy" and solver.solver_name == "gurobi"
            and solver.threads == 4 and solver.seed == 42 and solver.time_limit == 28800
            and solver.mip_gap == 0.1 and not solver.compact_python_indices
            and solver.solver_options == {"SoftMemLimit": 128, "NumericFocus": 1}
            and solver.multiobjective_stage_options in ({}, {r: {"Method": 2} for r in STAGES}),
            "Reference solver/control contract differs.")
    expected = asdict(spec)
    expected.update(name=ARM, workbook=str(spec.workbook.resolve()))
    expected["solver"].update(
        collect_resource_diagnostics=True, collect_solver_diagnostics=True,
        resource_sample_seconds=5.0, resource_max_samples=8192,
        multiobjective_stage_options={r: {"Method": 2} for r in STAGES},
    )
    expected["metadata"].update(mvp2_scope="s1b_h400_input_only")
    # JSON normalization matches YAML and portable receipts; no Path objects remain.
    return json.loads(json.dumps(expected)), qualified


def prepare(reference, qualification, destination, source):
    reference, qualification, destination = [Path(v).resolve()
                                              for v in (reference, qualification, destination)]
    require(bool(re.fullmatch(r"[0-9a-f]{40}", source)), "Full source commit required.")
    require(not destination.exists() and not any(destination.is_relative_to(p.parent)
            for p in (reference, qualification)), "New isolated preparation required.")
    spec, qualified = reference_spec(reference, qualification)
    destination.mkdir(parents=True, exist_ok=False)
    campaign = destination / "campaign.yaml"
    campaign.write_text(yaml.safe_dump({
        "version": 1, "output_dir": str(destination / "unused_solve_output"),
        "continue_on_error": False, "experiments": [spec],
    }, sort_keys=False), encoding="utf-8", newline="\n")
    load_experiment_manifest(campaign)
    plan = {
        "schema_version": "mvp2-h400-input-plan-v1", "status": "prepared_input_only",
        "case": "h400-direct", "source_commit": source, "scope": "input_inspection_only",
        "optimization_allowed": False, "reference_manifest": str(reference),
        "qualification_report": str(qualification),
        "qualified_source_commit": qualified["source_commit"],
        "reference_manifest_sha256": file_sha256(reference),
        "qualification_report_sha256": file_sha256(qualification),
        "workbook_sha256": policy()["workbook_sha256"],
        "reference_index": policy()["reference_index"], "spec": spec,
        "output_dir": str(destination / "unused_solve_output"),
        "campaign_sha256": file_sha256(campaign), "policy_sha256": file_sha256(ROOT / POLICY),
        "implementation": implementation_identity(), "tools": tool_identity(),
    }
    write(destination / "input_plan.json", plan)
    return destination / "input_plan.json"


def check_plan(path):
    path = Path(path).resolve()
    plan = json.loads(path.read_text(encoding="utf-8"))
    require(plan["schema_version"] == "mvp2-h400-input-plan-v1"
            and plan["status"] == "prepared_input_only" and plan["case"] == "h400-direct"
            and plan["scope"] == "input_inspection_only" and plan["optimization_allowed"] is False
            and re.fullmatch(r"[0-9a-f]{40}", plan["source_commit"])
            and plan["policy_sha256"] == file_sha256(ROOT / POLICY)
            and plan["tools"] == tool_identity()
            and plan["implementation"] == implementation_identity(), "Input plan identity differs.")
    spec, qualified = reference_spec(Path(plan["reference_manifest"]),
                                     Path(plan["qualification_report"]))
    p = policy()
    require(plan["spec"] == spec and plan["qualified_source_commit"] == qualified["source_commit"]
            and all(plan[key] == p[key] for key in (
                "reference_manifest_sha256", "qualification_report_sha256",
                "workbook_sha256", "reference_index")), "Reference plan differs.")
    campaign = path.parent / "campaign.yaml"
    require(file_sha256(campaign) == plan["campaign_sha256"], "Campaign hash differs.")
    expected = {"version": 1, "output_dir": str(path.parent / "unused_solve_output"),
                "continue_on_error": False, "experiments": [spec]}
    require(plan["output_dir"] == expected["output_dir"]
            and yaml.safe_load(campaign.read_text(encoding="utf-8")) == expected,
            "Single control campaign differs.")
    manifest = load_experiment_manifest(campaign)
    return plan, manifest.experiments[0]


def check_snapshot(snapshot, connectivity, audit, *, guard):
    p = policy()
    require(snapshot.get("workbook_sha256") == p["workbook_sha256"]
            and snapshot.get("data_signature", {}).get("counts") == p["counts"],
            "Population, scenario or workbook differs.")
    require(all(type(snapshot.get(k)) is int and snapshot[k] == v
                for k, v in p["snapshot_fields"].items()),
            "Exact size/direct-route profile differs.")
    components = ("flow_variables", "inventory_variables", "emergency_capacity_variables",
                  "investment_variables", "unmet_demand_variables")
    require(sum(snapshot[k] for k in components) == snapshot["total_variables"],
            "Variable decomposition differs.")
    products = connectivity.get("products", [])
    require(connectivity.get("schema_version") == "interhub-connectivity-v1"
            and connectivity.get("status") == "accepted"
            and connectivity.get("scope") == "potential_warehouse_graph_by_product"
            and connectivity.get("active_network_connectivity_guaranteed") is False
            and connectivity.get("throughput_feasibility_guaranteed") is False
            and sorted(row.get("product", "") for row in products) == ["Milho", "Soja"]
            and all(row.get("warehouses") == 400 and row.get("strongly_connected") is True
                    and row.get("final_edges") == 32000 for row in products),
            "Potential interhub connectivity differs.")
    findings = audit.get("findings", [])
    require(audit.get("schema_version") == 3 and "solution" not in audit
            and audit.get("input", {}).get("model_mode") == "sto"
            and audit.get("input", {}).get("objective_policy") == "lexicographic"
            and audit.get("summary") == {
                f"{severity}_count": sum(row.get("severity") == severity for row in findings)
                for severity in ("error", "warning", "info")}
            and audit["summary"]["error_count"] == 0, "Input audit rejected or inconsistent.")
    require(type(guard) is int and guard == p["reference_limit"], "Reference guard differs.")
    return {"scope": "input_inspection_only", "optimization_allowed": False,
            "total_variables": snapshot["total_variables"], "reference_limit": guard,
            "within_reference_limit": snapshot["total_variables"] <= guard,
            "excess_variables": max(0, snapshot["total_variables"] - guard)}


def preflight(path, destination, resource, *, inspector=inspect_experiment):
    path, destination = Path(path).resolve(), Path(destination).resolve()
    plan, spec = check_plan(path)
    protected = (path.parent, Path(plan["reference_manifest"]).parent,
                 Path(plan["qualification_report"]).parent)
    require(not destination.exists() and not any(destination.is_relative_to(p) for p in protected),
            "New isolated preflight directory required.")
    destination.mkdir(parents=True, exist_ok=False)
    diagnostic = {"schema_version": "mvp2-h400-input-diagnostics-v1", "status": "running",
                  "phase": "input_loading", "optimization_executed": False}
    try:
        inspector(spec, destination)
        diagnostic["phase"] = "snapshot_validation"
        folder = destination / ARM
        snapshot, audit, connectivity = [json.loads((folder / name).read_text(encoding="utf-8"))
                                         for name in PRODUCTS[:3]]
        snapshot.pop("execution", None)
        size = check_snapshot(snapshot, connectivity, audit, guard=spec.max_estimated_variables)
        diagnostic["phase"] = "identity_recheck"
        check_plan(path)
        result = {
            "schema_version": "mvp2-h400-input-preflight-v1", "status": "accepted",
            "case": "h400-direct", "source_commit": plan["source_commit"],
            "created_at_utc": datetime.now(UTC).isoformat(),
            "scope": "input_inspection_only", "optimization_executed": False,
            "large_instance_submission_allowed": False, "allocation": resource,
            "plan_sha256": file_sha256(path), "campaign_sha256": plan["campaign_sha256"],
            "policy_sha256": plan["policy_sha256"], "implementation": plan["implementation"],
            "tools": plan["tools"], "model_size": snapshot, "size_check": size,
            "artifacts": {f"{ARM}/{name}": file_sha256(folder / name) for name in PRODUCTS},
        }
    except Exception as error:
        diagnostic.update(status="failed", error_type=type(error).__name__,
                          error_message=str(error))
        write(destination / "input_diagnostics.json", diagnostic)
        raise
    diagnostic.update(status="accepted", phase="complete")
    write(destination / "input_diagnostics.json", diagnostic)
    write(destination / "input_preflight.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "check", "inspect"))
    for name in ("reference", "qualification", "plan", "output-dir", "job-file", "node-file"):
        parser.add_argument(f"--{name}", type=Path)
    for name in ("source", "job-id", "node-name"):
        parser.add_argument(f"--{name}")
    args = parser.parse_args()
    if args.action == "prepare":
        require(all(v is not None for v in (args.reference, args.qualification, args.output_dir,
                                            args.source)), "Preparation arguments missing.")
        print(prepare(args.reference, args.qualification, args.output_dir, args.source))
    elif args.action == "check":
        check_plan(args.plan)
    else:
        plan, _ = check_plan(args.plan)
        require(args.source == plan["source_commit"], "Submitted source differs.")
        resource = inputs.allocation(args.job_file.read_text(), args.node_file.read_text(),
                                     job_id=args.job_id, node_name=args.node_name)
        preflight(args.plan, args.output_dir, resource)
    print("H400 INPUT-ONLY CONTRACT: VERIFIED; BUILD AND OPTIMIZATION REMAIN CLOSED")


if __name__ == "__main__":
    main()
