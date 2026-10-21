"""Read-only h300 certificate replay and redacted diagnostic synthesis; no solver."""

import argparse
import csv
import hashlib
import io
import json
import math
import tarfile
from pathlib import Path

from scripts import mvp2_scalar_h300_operational as original

PENALTIES = ("unmet_demand", "emergency_static", "emergency_reception")
DECISIONS = ("warehouse_decisions.csv", "flows.csv", "inventories.csv", "unmet_demand.csv")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read_archive(path, checksum):
    """Stream bounded regular members without extracting or executing their contents."""
    require(
        original.r.file_hash(original.o.regular(path)) == checksum, "External checksum differs."
    )
    files, size = {}, 0
    with tarfile.open(path, "r|gz") as stream:
        for member in stream:
            require(
                member.isfile() and original.r._safe_name(member.name) and member.name not in files,
                "Unsafe/duplicate archive member.",
            )
            size += member.size
            require(size <= original.MAX_BYTES and len(files) < original.MAX_FILES, "Archive cap.")
            files[member.name] = stream.extractfile(member).read()
    inventory = original.r.strict_json(files.pop("inventory.json"))
    require(inventory == {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}, "Inventory.")
    return files, {"members": len(files) + 1, "expanded_bytes": size}


def close(a, b):
    """Arithmetic consistency only; never replaces original residual tolerances."""
    return math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, rel_tol=1e-8, abs_tol=1e-5)


def summarize(files, replay):
    """Supplement an accepted ORIGINAL replay; do not manufacture acceptance from summaries."""
    require(
        replay["status"] == "block_quality_target_met"
        and replay["quality_target_met"]
        and replay["operational_receipts_closed"]
        and not replay["missing_or_rejected"],
        "Full accepted original block required.",
    )

    def read(name):
        return original.r.strict_json(files[name])

    plan = read("plan.json")
    hardware = read("hardware.json")
    arms, populations, networks = [], [], []
    for arm in replay["arms"]:
        case = "cases/" + arm["case_name"] + "/"
        products = case + "products/" + arm["case_name"] + "/"
        summary = read(products + "run_summary.json")
        validation = read(products + "independent_validation.json")
        receipt = read(case + "input_receipt.json")
        used = read(case + "warehouses_used.json")
        runtime = read(f"control/t{arm['threads']}/runtime.json")
        costs = validation["reconstructed_costs"]
        require(
            validation["status"] == "accepted" and validation["failed_check_count"] == 0,
            "Original residual rejection.",
        )
        require(
            validation["absolute_tolerance"] == 1e-5 and validation["relative_tolerance"] == 1e-8,
            "Original tolerances.",
        )
        require(
            used["count"] == 300
            and used["existing_count"] == 146
            and used["candidate_count"] == 154,
            "Warehouse counts.",
        )
        require(runtime["solver_threads"] == arm["threads"], "Thread receipt.")
        probabilities = receipt["effective_scenario_probabilities"]
        require(
            len(probabilities) == 9 and all(close(p, 1 / 9) for p in probabilities.values()),
            "Scenario probabilities.",
        )
        penalties = sum(costs[k] for k in PENALTIES)
        economic = sum(v for k, v in costs.items() if k not in PENALTIES)
        objective, bound = arm["objective"], arm["bound"]
        require(
            close(economic, arm["economic_cost"]) and close(economic + penalties, objective),
            "Cost arithmetic.",
        )
        gap = abs(objective - bound) / abs(objective)
        require(gap <= 0.01 and close(gap, arm["common_gap"]), "Gap arithmetic.")
        physical = arm["physical_diagnostics"]
        require(
            close(physical["penalty_cost_share"], penalties / (economic + penalties)),
            "Penalty share.",
        )
        require(
            close(
                physical["domestic_service_level"],
                summary["served_domestic_demand"] / summary["total_domestic_demand"],
            ),
            "Service arithmetic.",
        )
        require(
            close(costs["unmet_demand"], physical["total_unmet_demand"] * 90000)
            and close(costs["emergency_static"], physical["emergency_static_capacity"] * 45000)
            and close(
                costs["emergency_reception"], physical["emergency_reception_capacity"] * 45000
            ),
            "Slack units/costs.",
        )
        progress = list(
            csv.DictReader(
                io.StringIO(files[products + "resources/solver_progress.csv"].decode("utf-8"))
            )
        )
        observed = {}
        for key in ("iterations", "nodes", "solver_memory_bytes"):
            values = [float(row[key]) for row in progress if row.get(key)]
            require(all(math.isfinite(v) and v >= 0 for v in values), "Progress number.")
            observed["sampled_max_" + key] = max(values, default=None)
        hashes = {name: hashlib.sha256(files[products + name]).hexdigest() for name in DECISIONS}
        populations.append(used["csv_sha256"])
        networks.append(validation["mathematical_contract"]["selected_network_sha256"])
        arms.append(
            {
                **arm,
                "gap_percent": gap * 100,
                "application_sampled_peak_rss_gib": physical["peak_rss_mb"] / 1024,
                "reconstructed_costs": costs,
                "original_validation_sha256": hashlib.sha256(
                    files[products + "independent_validation.json"]
                ).hexdigest(),
                "original_absolute_tolerance": validation["absolute_tolerance"],
                "original_relative_tolerance": validation["relative_tolerance"],
                "original_validation_failed_checks": validation["failed_check_count"],
                "warehouse_csv_sha256": used["csv_sha256"],
                "warehouse_ordered_ids_sha256": used["ordered_ids_sha256"],
                "selection_criterion": used["criterion"],
                "selection_seed": used["selection_seed"],
                "matrix": read(products + "resources/matrix_statistics.json"),
                "resource_termination": read(products + "resources/termination.json"),
                "sampled_solver_progress": observed,
                "decision_artifact_sha256": hashes,
            }
        )
    require([a["threads"] for a in arms] == [4, 1, 8, 2, 16], "Complete ordered grid.")
    require(len(set(populations)) == len(set(networks)) == 1, "Population/network drift.")
    return {
        "schema_version": "scalar-h300-external-review-v1",
        "status": "accepted_scalar_h300_block",
        "source_commit": plan["source_commit"],
        "plan_sha256": hashlib.sha256(files["plan.json"]).hexdigest(),
        "job_id": replay["job_id"],
        "qualification": (
            "Original receipt/integrity replay and arithmetic checks; "
            "no fresh private-input residual re-solve."
        ),
        "operational_receipts_closed": True,
        "quality_target_met": True,
        "penalty_rates": replay["penalty_rates"],
        "hardware": {
            k: hardware[k]
            for k in ("cpu_model", "physical_cores_observed", "affinity_logical_cpus", "topology")
        },
        "terminal_accounting": original.r.r2.accounting(
            files["accounting.txt"].decode(), replay["job_id"]
        ),
        "same_warehouse_population_and_order": True,
        "same_selected_network_sha256": networks[0],
        "decision_artifacts_identical_across_arms": {
            name: len({a["decision_artifact_sha256"][name] for a in arms}) == 1
            for name in DECISIONS
        },
        "arms": arms,
        "interpretation": (
            "One cold serial observation per thread level; "
            "no causal ranking or automatic h400 selection."
        ),
        "scientific_configuration_selected": False,
        **original.r.closed(),
    }


def review(path, checksum):
    files, inventory = read_archive(path, checksum)
    # Existing verifier retains authority over all phase/step/source/validator gates.
    replay = original.portable_review(files)
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
