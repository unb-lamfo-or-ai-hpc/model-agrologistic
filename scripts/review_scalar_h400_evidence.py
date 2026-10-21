"""Read-only h400 original-certificate replay and redacted scientific synthesis."""

import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath

from scripts import mvp2_scalar_h400_contract as contract
from scripts import mvp2_scalar_h400_operational as original
from scripts.review_scalar_h300_evidence import close, read_archive, require


def review(path, checksum):
    files, inventory = read_archive(path, checksum)
    def read(name):
        return json.loads(files[name])
    plan = read("plan.json")
    replay = original.portable_review(files)
    adapter = "Qualified POSIX lexical serialization in contract reader; no runtime monkeypatch."
    require(replay == read("review.json"), "External replay differs from archived original review.")
    require(replay["status"] == "h400_quality_target_met", "Quality not accepted.")
    require(replay["operational_receipts_closed"], "Operational closure not accepted.")
    require(
        replay["h500_preconditions_met"] and not replay["h500_execution_admitted"],
        "Eligibility/admission distinction differs.",
    )
    base = "cases/scalar_h400_t1/products/scalar_h400_t1/"
    arm = replay["arms"][0]
    validation = read(base + "independent_validation.json")
    summary = read(base + "run_summary.json")
    used = read("cases/scalar_h400_t1/warehouses_used.json")
    receipt = read("cases/scalar_h400_t1/input_receipt.json")
    costs = validation["reconstructed_costs"]
    penalties = sum(costs[k] for k in ("unmet_demand", "emergency_static", "emergency_reception"))
    economic = sum(
        v
        for k, v in costs.items()
        if k not in ("unmet_demand", "emergency_static", "emergency_reception")
    )
    require(
        validation["status"] == "accepted" and validation["failed_check_count"] == 0,
        "Original validation differs.",
    )
    require(
        validation["absolute_tolerance"] == 1e-5 and validation["relative_tolerance"] == 1e-8,
        "Original tolerances differ.",
    )
    for actual, expected in (
        (economic, arm["economic_cost"]),
        (penalties, arm["artificial_penalties"]),
        (economic + penalties, arm["objective"]),
        (abs(arm["objective"] - arm["bound"]) / abs(arm["objective"]), arm["common_gap"]),
    ):
        require(close(actual, expected), "Cost/gap arithmetic differs.")
    physical = arm["physical_diagnostics"]
    require(
        close(
            summary["served_domestic_demand"] / summary["total_domestic_demand"],
            physical["domestic_service_level"],
        ),
        "Service arithmetic differs.",
    )
    require(
        close(penalties / (economic + penalties), physical["penalty_cost_share"]),
        "Penalty share differs.",
    )
    for cost, quantity, rate in (
        ("unmet_demand", "total_unmet_demand", 90000),
        ("emergency_static", "emergency_static_capacity", 45000),
        ("emergency_reception", "emergency_reception_capacity", 45000),
    ):
        require(close(costs[cost], physical[quantity] * rate), "Penalty/quantity units differ.")
    probs = receipt["effective_scenario_probabilities"]
    require(len(probs) == 9 and all(close(v, 1 / 9) for v in probs.values()), "Probabilities.")
    require(
        used["count"] == len(used["included"]) == 400
        and used["existing_count"] == 146
        and used["candidate_count"] == 254,
        "Included membership differs.",
    )
    progress = list(
        csv.DictReader(io.StringIO(files[base + "resources/solver_progress.csv"].decode()))
    )
    maxima = {}
    for key in ("iterations", "nodes", "solver_memory_bytes"):
        values = [float(row[key]) for row in progress if row.get(key)]
        require(all(math.isfinite(v) and v >= 0 for v in values), "Sampled progress differs.")
        maxima["sampled_max_" + key] = max(values, default=None)
    measured = replay["headroom_observations"]
    thresholds = contract.ELIGIBILITY
    headroom = {
        "application_peak_gib": measured["sampled_application_peak_bytes"] / 1024**3,
        "slurm_step_max_rss_gib": measured["slurm_step_max_rss_bytes"] / 1024**3,
        "native_peak_decimal_gb": measured["sampled_native_peak_bytes"] / 1e9,
        "os_limit_gib": thresholds["os_rss_max_bytes"] / 1024**3,
        "native_limit_decimal_gb": thresholds["native_memory_max_bytes"] / 1e9,
        "application_headroom_fraction_of_requested": 1
        - measured["sampled_application_peak_bytes"] / (192 * 1024**3),
        "native_headroom_fraction_of_soft_limit": 1
        - measured["sampled_native_peak_bytes"] / (160e9),
    }
    rows = original.r.r2.accounting(files["accounting.txt"].decode(), replay["job_id"])
    hardware = read("hardware.json")
    root = next(row for row in rows if row["job_id"] == replay["job_id"])
    return {
        "schema_version": "scalar-h400-external-review-v1",
        **replay,
        "archive_sha256": checksum,
        "archive_bytes": path.stat().st_size,
        "archive_inventory": inventory,
        "plan_sha256": hashlib.sha256(files["plan.json"]).hexdigest(),
        "reviewer_scope": (
            "Original certificate replay plus arithmetic; no private-input residual re-solve"
        ),
        "replay_path_adapter": adapter,
        "original_archived_review_identical": True,
        "original_validation_sha256": hashlib.sha256(
            files[base + "independent_validation.json"]
        ).hexdigest(),
        "original_validation_failed_checks": validation["failed_check_count"],
        "original_absolute_tolerance": validation["absolute_tolerance"],
        "original_relative_tolerance": validation["relative_tolerance"],
        "reconstructed_costs": costs,
        "gap_percent": arm["common_gap"] * 100,
        "matrix": read(base + "resources/matrix_statistics.json"),
        "resource_termination": read(base + "resources/termination.json"),
        "sampled_solver_progress": maxima,
        "headroom_converted": headroom,
        "terminal_accounting": rows,
        "allocated_logical_cpu_hours_arithmetic": 24 * root["elapsed_seconds"] / 3600,
        "cpu_arithmetic_qualification": (
            "Allocated CPU-time product, not measured CPU utilization or billing."
        ),
        "hardware": {
            k: hardware[k]
            for k in ("cpu_model", "physical_cores_observed", "affinity_logical_cpus", "topology")
        },
        "warehouse_receipt": {
            k: used[k]
            for k in (
                "count",
                "existing_count",
                "candidate_count",
                "csv_sha256",
                "ordered_ids_sha256",
                "criterion",
                "selection_method",
                "selection_seed",
            )
        },
        "workbook_sha256": plan["cases"][0]["workbook_sha256"],
        "selected_network_sha256": validation["mathematical_contract"]["selected_network_sha256"],
        "phase_controller": read("control/t1/controller.json"),
        "decision_artifact_sha256": {
            name: hashlib.sha256(files[base + name]).hexdigest()
            for name in (
                "flows.csv",
                "inventories.csv",
                "unmet_demand.csv",
                "warehouse_decisions.csv",
            )
        },
        "bootstrap_directory_name": PurePosixPath(plan["source_root"]).parent.name,
        "interpretation": (
            "One observed h400 scalar success; no exact-optimality, full-service, "
            "causal speedup or automatic h500 claim."
        ),
    }


def main(argv=None):
    import argparse

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
