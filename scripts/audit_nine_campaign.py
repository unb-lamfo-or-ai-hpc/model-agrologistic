"""Report every requested instance, including missing inputs and incomplete hierarchies."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def classify_stages(stages, independent_status):
    """A relaxed gap never substitutes for service or independent feasibility."""
    roles = {s.get("stage_role"): s for s in stages}
    if independent_status != "accepted":
        return "independent_validation_not_accepted"
    if len(stages) != 3 or set(roles) != {
            "unmet_demand", "emergency_capacity", "economic_cost"}:
        return "incomplete_hierarchy"
    service = roles["unmet_demand"]
    value = service.get("final_objective_value", service.get("objective_value"))
    if value is None or not math.isfinite(float(value)) or abs(float(value)) > 1.01e-6:
        return "service_shortfall"
    for role in ("emergency_capacity", "economic_cost"):
        stage = roles[role]
        gap = stage.get("mip_gap")
        if gap is None or not math.isfinite(float(gap)) or not 0 <= float(gap) <= 0.10:
            return "gap_target_not_attained"
    if any(s.get("within_mip_degradation_limit") is not True for s in stages):
        return "hierarchy_degradation_not_certified"
    return "accepted_at_ten_percent"


def selected_indices(requested, count):
    """Keep original campaign indices; a pilot is not a full-campaign claim."""
    indices = list(range(count)) if requested is None else list(requested)
    if not indices or len(set(indices)) != len(indices):
        raise ValueError("Select at least one index without duplicates.")
    if any(index < 0 or index >= count for index in indices):
        raise ValueError("Selected index is outside the campaign.")
    return indices


def main(argv=None):
    from src.logic.experiment_runner import (
        _checkpoint_identity,
        inspect_experiment,
        load_experiment_manifest,
    )
    from src.logic.run_integrity import verify_completion

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--indices", nargs="+", type=int,
                        help="Audit only these original campaign indices.")
    parser.add_argument("--output-dir", type=Path,
                        help="Write a new report directory without replacing earlier reports.")
    parser.add_argument("--require-accepted", action="store_true",
                        help="Return nonzero after reporting if a selected case is not accepted.")
    args = parser.parse_args(argv)
    manifest = load_experiment_manifest(args.manifest)
    try:
        indices = selected_indices(args.indices, len(manifest.experiments))
    except ValueError as exc:
        parser.error(str(exc))
    destination = args.manifest.resolve().parent
    if args.output_dir is not None:
        destination = args.output_dir.resolve()
        if destination.is_relative_to(manifest.output_dir.resolve()):
            parser.error("Report directory must be outside the source runs directory.")
        if destination.exists():
            parser.error("Report directory already exists; choose a new snapshot path.")
        destination.mkdir(parents=True)
    records, stage_rows = [], []
    for index in indices:
        spec = manifest.experiments[index]
        row = {"index": index, "name": spec.name,
               "warehouses": spec.metadata.get("warehouse_population"),
               "target_gap": spec.solver.mip_gap,
               "time_budget_seconds": spec.solver.time_limit}
        run_dir = manifest.output_dir / spec.name
        try:
            if args.preflight:
                estimate = inspect_experiment(spec, manifest.output_dir)
                row.update(asdict(estimate))
                row["status"] = ("preflight_ready" if spec.max_estimated_variables is None
                                 or estimate.total_variables <= spec.max_estimated_variables
                                 else "size_gate_requires_resource_review")
            else:
                valid, reason = verify_completion(run_dir, _checkpoint_identity(spec))
                if not valid:
                    raise ValueError(reason)
                result = json.loads((run_dir / "result.json").read_text())["result"]
                independent = json.loads((run_dir / "independent_validation.json").read_text())
                summary = json.loads((run_dir / "run_summary.json").read_text())
                metadata = result.get("metadata", {})
                stages = metadata.get("lexicographic_stages", [])
                row["status"] = classify_stages(
                    stages, independent.get("status")
                )
                row.update(metadata.get("timings", {}))
                row["solver_status"] = result.get("status")
                row["independent_validation_status"] = independent.get("status")
                for field in (
                    "peak_rss_mb", "domestic_service_level", "total_unmet_demand",
                    "material_balance_ok", "economic_cost", "penalized_cost",
                    "emergency_static_capacity", "emergency_reception_capacity",
                    "capacity_adequacy_status", "total_direct_flow",
                    "minimum_scenario_service_level", "maximum_scenario_service_level",
                    "lexicographic_overall_status", "service_certification_status",
                ):
                    row[field] = summary.get(field)
                for stage in stages:
                    stage_rows.append({"name": spec.name, **stage})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            row.update(status="not_available_or_failed", reason=str(exc))
        records.append(row)
    prefix = "nine_preflight" if args.preflight else "nine_results"
    for name, rows in ((prefix, records), ("nine_stage_gaps", stage_rows)):
        if not rows:
            continue
        (destination / f"{name}.json").write_text(
            json.dumps(rows, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        fields = list(dict.fromkeys(key for row in rows for key in row))
        with (destination / f"{name}.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    print(destination / f"{prefix}.csv")
    accepted_status = "preflight_ready" if args.preflight else "accepted_at_ten_percent"
    accepted_count = sum(row["status"] == accepted_status for row in records)
    receipt = {
        "schema_version": "nine-campaign-audit-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "audit_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "mode": "preflight" if args.preflight else "completed_results",
        "campaign_instance_count": len(manifest.experiments),
        "selected_indices": indices,
        "selected_instance_count": len(indices),
        "unassessed_indices": [i for i in range(len(manifest.experiments)) if i not in indices],
        "accepted_instance_count": accepted_count,
        "overall_status": "accepted" if accepted_count == len(indices) else "not_accepted",
        "scope": "selected_instances_only",
    }
    (destination / "nine_audit_manifest.json").write_text(
        json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"NINE AUDIT: {receipt['overall_status']} ({accepted_count}/{len(indices)} selected)")
    return int(args.require_accepted and accepted_count != len(indices))


if __name__ == "__main__":
    raise SystemExit(main())
