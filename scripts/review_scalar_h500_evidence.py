"""Read-only h500 original-certificate replay and redacted S5 evidence synthesis."""

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path

from scripts import mvp2_scalar_h500_operational as original
from scripts.review_scalar_h300_evidence import close, read_archive, require

PENALTIES = ("unmet_demand", "emergency_static", "emergency_reception")
DECISIONS = ("flows.csv", "inventories.csv", "unmet_demand.csv", "warehouse_decisions.csv")


def summarize(files, replay):
    """Summarize accepted original receipts, never recompute private-input residuals."""
    require(
        replay["status"] == "h500_quality_target_met"
        and replay["quality_target_met"]
        and replay["operational_receipts_closed"]
        and replay["resource_observations_complete"]
        and not replay["resource_observation_blockers"]
        and not replay["missing_or_rejected"]
        and len(replay["arms"]) == 1
        and all(
            replay[k] is False
            for k in ("additional_execution_admitted", "execution_admitted",
                      "repeats_admitted", "automatic_follow_on_allowed")
        ),
        "Complete accepted original h500 evidence required.",
    )
    def read(name):
        return original.r.strict_json(files[name])
    arm = replay["arms"][0]
    require(
        arm["case_name"] == original.c.CASE
        and arm["mode"] == "sto"
        and arm["threads"] == 1,
        "One STO/W h500 observation required.",
    )
    base = "cases/" + original.c.CASE + "/"
    product = base + "products/" + original.c.CASE + "/"
    plan = read("plan.json")
    validation = read(product + "independent_validation.json")
    summary = read(product + "run_summary.json")
    receipt = read(base + "input_receipt.json")
    used = read(base + "warehouses_used.json")
    require(
        validation["status"] == "accepted"
        and validation["failed_check_count"] == 0
        and validation["absolute_tolerance"] == 1e-5
        and validation["relative_tolerance"] == 1e-8,
        "Original validation or tolerances differ.",
    )
    costs = validation["reconstructed_costs"]
    require(len(costs) == 14 and all(math.isfinite(v) for v in costs.values()), "Cost components.")
    penalties = sum(costs[k] for k in PENALTIES)
    economic = sum(v for k, v in costs.items() if k not in PENALTIES)
    gap = abs(arm["objective"] - arm["bound"]) / abs(arm["objective"])
    for actual, expected in (
        (economic, arm["economic_cost"]),
        (penalties, arm["artificial_penalties"]),
        (economic + penalties, arm["objective"]),
        (gap, arm["common_gap"]),
    ):
        require(close(actual, expected), "Cost/gap arithmetic differs.")
    require(gap <= 0.01, "Original scalar quality target not met.")
    physical = arm["physical_diagnostics"]
    require(
        close(penalties / (economic + penalties), physical["penalty_cost_share"])
        and close(
            summary["served_domestic_demand"] / summary["total_domestic_demand"],
            physical["domestic_service_level"],
        ),
        "Penalty share or domestic-service arithmetic differs.",
    )
    for cost, quantity, rate in (
        ("unmet_demand", "total_unmet_demand", 90000),
        ("emergency_static", "emergency_static_capacity", 45000),
        ("emergency_reception", "emergency_reception_capacity", 45000),
    ):
        require(close(costs[cost], physical[quantity] * rate), "Penalty/quantity units differ.")
    probs = receipt["effective_scenario_probabilities"]
    require(len(probs) == 9 and all(close(p, 1 / 9) for p in probs.values()), "Probabilities.")
    require(
        used["count"] == len(used["included"]) == 500
        and used["existing_count"] == 146
        and used["candidate_count"] == 354,
        "Frozen h500 population differs.",
    )
    progress = csv.DictReader(
        io.StringIO(files[product + "resources/solver_progress.csv"].decode())
    )
    maxima = dict.fromkeys(("iterations", "nodes", "solver_memory_bytes"))
    for row in progress:
        for key in maxima:
            if row.get(key):
                value = float(row[key])
                require(math.isfinite(value) and value >= 0, "Invalid sampled solver progress.")
                maxima[key] = value if maxima[key] is None else max(maxima[key], value)

    warehouses = list(
        csv.DictReader(io.StringIO(files[product + "warehouse_decisions.csv"].decode()))
    )
    candidates = [row for row in warehouses if row["is_candidate"].lower() in ("true", "1")]
    require(len(warehouses) == 500 and len(candidates) == 354, "Decision population differs.")
    investment = {
        "candidate_activations": sum(float(row["open"]) > 0.5 for row in candidates),
        "positive_candidate_capacity_count": sum(
            float(row["candidate_capacity"]) > 1e-7 for row in candidates
        ),
        "candidate_capacity_tonnes": sum(
            float(row["candidate_capacity"]) for row in candidates
        ),
        "positive_expansion_count": sum(
            float(row["expansion_capacity"]) > 1e-7 for row in warehouses
        ),
        "expansion_capacity_tonnes": sum(float(row["expansion_capacity"]) for row in warehouses),
        "positive_bulk_capacity_count": sum(
            float(row["bulk_capacity"]) > 1e-7 for row in warehouses
        ),
        "bulk_capacity_tonnes": sum(float(row["bulk_capacity"]) for row in warehouses),
    }
    flows = {kind: {"expected_arc_tonnes": 0.0, "positive_records": 0}
             for kind in ("OD", "DC", "DD", "OC")}
    for row in csv.DictReader(io.StringIO(files[product + "flows.csv"].decode())):
        value = float(row["value"])
        require(math.isfinite(value) and value >= 0, "Invalid original flow quantity.")
        target = flows[row["route_type"]]
        target["expected_arc_tonnes"] += probs[row["scenario"]] * value
        target["positive_records"] += int(value > 1e-7)
    require(flows["OC"]["positive_records"] == 0, "W observation cannot contain direct flows.")
    rows = original.r.r2.accounting(files["accounting.txt"].decode(), replay["job_id"])
    root = next(row for row in rows if row["job_id"] == replay["job_id"])
    measured = replay["resource_observations"]
    hardware = read("hardware.json")
    return {
        "schema_version": "scalar-h500-external-review-v1",
        **replay,
        "plan_sha256": hashlib.sha256(files["plan.json"]).hexdigest(),
        "original_archived_review_identical": True,
        "original_review_sha256": hashlib.sha256(files["review.json"]).hexdigest(),
        "original_validation_sha256": hashlib.sha256(
            files[product + "independent_validation.json"]
        ).hexdigest(),
        "original_validation_failed_checks": validation["failed_check_count"],
        "original_absolute_tolerance": validation["absolute_tolerance"],
        "original_relative_tolerance": validation["relative_tolerance"],
        "reviewer_scope": (
            "Original certificate/integrity replay and aggregate arithmetic; "
            "not fresh private-input residual recomputation or optimization."
        ),
        "gap_percent": gap * 100,
        "reconstructed_costs": costs,
        "resources": plan["resources"],
        "matrix": read(product + "resources/matrix_statistics.json"),
        "resource_termination": read(product + "resources/termination.json"),
        "runtime_capabilities": read(product + "resources/runtime_capabilities.json"),
        "sampled_solver_progress": {"sampled_max_" + k: v for k, v in maxima.items()},
        "resource_scopes_converted": {
            "sampled_application_rss_gib": measured["sampled_application_peak_bytes"] / 1024**3,
            "slurm_step_max_rss_gib": measured["slurm_step_max_rss_bytes"] / 1024**3,
            "sampled_native_memory_decimal_gb": measured["sampled_native_peak_bytes"] / 1e9,
            "qualification": "Separate original scopes; no new headroom or next-size gate.",
        },
        "terminal_accounting": rows,
        "allocated_logical_cpu_hours_arithmetic": 24 * root["elapsed_seconds"] / 3600,
        "cpu_arithmetic_qualification": "Allocated CPU-time product, not utilization or billing.",
        "hardware": {
            k: hardware[k]
            for k in ("cpu_model", "physical_cores_observed", "affinity_logical_cpus", "topology")
        },
        "warehouse_receipt": {
            k: used[k]
            for k in (
                "count", "existing_count", "candidate_count", "csv_sha256",
                "ordered_ids_sha256", "criterion", "selection_method", "selection_seed",
            )
        },
        "workbook_sha256": plan["cases"][0]["workbook_sha256"],
        "selected_network_sha256": validation["mathematical_contract"]["selected_network_sha256"],
        "penalty_vector_sha256": validation["mathematical_contract"]["penalty_vector_sha256"],
        "original_source_inventory_file_count": len(read("source.json")["files"]),
        "phase_controller": read("control/t1/controller.json"),
        "investment": investment,
        "flows": flows,
        "flow_scope": (
            "Expected arc volumes retain scenario weights. DC is destination arrivals; "
            "OD/DD count network legs and cannot be added as unique delivered grain."
        ),
        "decision_artifact_sha256": {
            name: hashlib.sha256(files[product + name]).hexdigest() for name in DECISIONS
        },
        "interpretation": (
            "One accepted original h500 STO/W observation. No exact zero-gap optimum, "
            "full service, causal speedup, independent replication or additional execution."
        ),
    }


def review(path, checksum):
    files, inventory = read_archive(path, checksum)
    replay = original.portable_review(files)
    require(
        replay == original.r.strict_json(files["review.json"]),
        "External replay differs from archived original review.",
    )
    return {
        **summarize(files, replay),
        "archive_sha256": checksum,
        "archive_bytes": path.stat().st_size,
        "archive_inventory": inventory,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = review(args.archive, args.sha256)
    encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
        print(json.dumps({k: result[k] for k in ("status", "job_id", "archive_sha256")}))
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
