"""Versioned four-level acceptance for explicitly selected v0.2 reference runs."""

from __future__ import annotations

import json
import math
from pathlib import Path

from src.logic.experiment_runner import _checkpoint_identity, load_experiment_manifest
from src.logic.mathematical_contract import MATHEMATICAL_CONTRACT_VERSION
from src.logic.run_integrity import implementation_identity, verify_completion


def assess_run(spec, root: Path) -> dict:
    """Distinguish pending evidence, failed checks and accepted reference output."""
    directory = root / spec.name
    valid, reason = verify_completion(directory, _checkpoint_identity(spec))
    if not valid:
        return {"name": spec.name, "status": "pending", "reason": reason, "checks": {}}
    payload = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    independent = json.loads(
        (directory / "independent_validation.json").read_text(encoding="utf-8")
    )
    result = payload["result"]
    metadata = result.get("metadata", {})
    checks = {
        "current_mathematical_contract": metadata.get("mathematical_contract", {}).get("version")
        == MATHEMATICAL_CONTRACT_VERSION,
        "independent_local_residuals_and_costs": independent.get("status") == "accepted",
        "selected_network_and_penalties_match": (
            independent.get("mathematical_contract") == metadata.get("mathematical_contract")
        ),
        "usable_incumbent": result.get("status") in {"optimal", "feasible", "time_limit"},
    }
    if spec.model.objective_policy == "lexicographic":
        service = independent.get("service_by_scenario", [])
        checks["domestic_service_by_scenario"] = bool(service) and all(
            row["unmet_tons"] <= 1e-5 for row in service
        )
        checks["three_completed_passes"] = metadata.get("lexicographic_completed_stage_count") == 3
        checks["service_target_certified"] = (
            metadata.get("service_certification_status") == "certified_zero_within_tolerance"
        )
        stages = metadata.get("lexicographic_stages", [])
        checks["stage_final_values_reported"] = len(stages) == 3 and all(
            r.get("final_objective_value") is not None for r in stages
        )
    if spec.calculate_evpi_vss:
        analysis = (payload.get("stochastic_performance") or {}).get("metadata", {})
        statuses = [analysis.get(name + "_certification_status") for name in ("evpi", "vss")]
        checks["value_metric_intervals"] = all(
            status in {"certified_positive", "certified_nonnegative", "numerically_indeterminate"}
            for status in statuses
        )
        checks["eev_first_stage_fixed"] = analysis.get("eev_fixed_decisions_valid") is True
        components = analysis.get("component_validation", {})
        checks["all_reference_solutions_validated"] = len(components) == len(
            independent.get("service_by_scenario", [])
        ) + 3 and all(r.get("status") == "accepted" for r in components.values())
    timing = metadata.get("timings", {})
    timing_fields = (
        "data_read_seconds",
        "model_build_seconds",
        "optimization_seconds",
        "result_extraction_seconds",
        "independent_validation_seconds",
        "artifact_export_seconds",
        "end_to_end_seconds",
        "postoptimality_seconds",
    )
    checks["phase_timing_complete"] = all(
        isinstance(timing.get(k), (int, float)) and math.isfinite(timing[k]) and timing[k] >= 0
        for k in timing_fields
    )
    execution = payload.get("execution", {})
    checks["hpc_execution_identified"] = bool(execution.get("slurm_job_id"))
    return {
        "name": spec.name,
        "status": "accepted" if all(checks.values()) else "rejected",
        "checks": checks,
        "objective_policy": spec.model.objective_policy,
        "scenario_count": len(independent.get("service_by_scenario", [])),
        "run_identity": metadata.get("run_identity"),
        "value_metric_interpretation": "Report indeterminate intervals without a sign claim.",
        "emergency_capacity_is_rejection_condition": False,
    }


def build_validation_report(plan: dict, project_root: Path, quality: dict) -> dict:
    """Produce four levels without borrowing the historical v0.1 certificate."""
    runs = []
    for campaign in plan["campaigns"]:
        manifest = load_experiment_manifest(project_root / campaign["manifest"])
        root = project_root / campaign["output_dir"]
        for index in campaign["indices"]:
            row = assess_run(manifest.experiments[index], root)
            row["profile"] = campaign["profile"]
            runs.append(row)
    implementation = implementation_identity()
    quality_ok = (
        quality.get("implementation_sha256") == implementation["sha256"]
        and quality.get("status") == "accepted"
        and quality.get("skipped_tests") == 0
    )
    complete = bool(runs) and all(r["status"] == "accepted" for r in runs)
    level1 = bool(runs) and all(r["checks"].get("current_mathematical_contract") for r in runs)
    level3 = bool(runs) and all(
        r["checks"].get("independent_local_residuals_and_costs") for r in runs
    )
    levels = [
        {
            "level": 1,
            "name": "mathematical_and_data_contract",
            "status": "accepted" if level1 else "pending",
        },
        {
            "level": 2,
            "name": "software_and_licensed_analytical_tests",
            "status": "accepted" if quality_ok else "pending",
        },
        {
            "level": 3,
            "name": "independent_solution_validation",
            "status": "accepted" if level3 else "pending",
        },
        {
            "level": 4,
            "name": "hpc_reference_demonstration",
            "status": "accepted" if complete else "pending",
        },
    ]
    rejected = any(r["status"] == "rejected" for r in runs)
    return {
        "schema_version": "v020-four-level-validation-v1",
        "implementation": implementation,
        "overall_status": "rejected"
        if rejected
        else "accepted"
        if complete and quality_ok
        else "pending",
        "levels": levels,
        "runs": runs,
        "quality": quality,
        "scope": plan["scope"],
        "plan": plan,
        "historical_numerical_replication": "not_established",
        "limitations": [
            "Separate slacks are not equivalent to the historical shared-slack penalty.",
            "The historical OSM snapshot and forecasting path are not reconstructed.",
            "Acceptance covers selected runs, not all configurations or unique investments.",
            "Emergency quantities diagnose violations, not installed capacity recommendations.",
            "No automatic certification of manuscript, TRL or the full scalability frontier.",
        ],
    }


def report_markdown(report: dict) -> str:
    lines = ["# v0.2 four-level validation", "", f"Overall: **{report['overall_status']}**", ""]
    lines += [f"- Level {r['level']} — {r['name']}: {r['status']}" for r in report["levels"]]
    lines += ["", "## Reference executions", ""]
    lines += [f"- {r['name']}: {r['status']}" for r in report["runs"]]
    lines += [
        "",
        "## Qualification of scientific claims",
        "",
        *[f"- {s}" for s in report["limitations"]],
    ]
    return "\n".join(lines) + "\n"
