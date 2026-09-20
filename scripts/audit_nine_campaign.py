"""Report every requested instance, including missing inputs and incomplete hierarchies."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def classify_stages(stages, independent_status):
    """A relaxed gap never substitutes for service or independent feasibility."""
    roles = {s.get("stage_role"): s for s in stages}
    if independent_status != "accepted":
        return "independent_validation_not_accepted"
    if set(roles) != {"unmet_demand", "emergency_capacity", "economic_cost"}:
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


def main():
    from src.logic.experiment_runner import (
        _checkpoint_identity,
        inspect_experiment,
        load_experiment_manifest,
    )
    from src.logic.run_integrity import verify_completion

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    manifest = load_experiment_manifest(args.manifest)
    records, stage_rows = [], []
    for index, spec in enumerate(manifest.experiments):
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
                row["peak_rss_mb"] = summary.get("peak_rss_mb")
                for stage in stages:
                    stage_rows.append({"name": spec.name, **stage})
        except (OSError, ValueError, KeyError) as exc:
            row.update(status="not_available_or_failed", reason=str(exc))
        records.append(row)
    prefix = "nine_preflight" if args.preflight else "nine_results"
    destination = args.manifest.resolve().parent
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


if __name__ == "__main__":
    main()
