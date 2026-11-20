"""Derive scientific outcomes from hash-audited original diagnostic receipts."""

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("audit_directory", type=Path)
ROOT = parser.parse_args().audit_directory.resolve()
CLAIM = ROOT / "diagnostics/claim"
PLAN = json.loads((ROOT / "plan.json").read_text())
TASKS = list(csv.DictReader((ROOT / "tasks.csv").open()))


def document(path):
    return json.loads(path.read_text()) if path.is_file() else {}


def number(pattern, text):
    matches = re.findall(pattern, text, re.M)
    return float(matches[-1]) if matches else None


observations = []
for index, task in enumerate(TASKS):
    item = PLAN["rows"][index]
    case = item["id"]
    leaf = CLAIM / case
    products = leaf / "case/products" / case
    summary = document(products / "run_summary.json")
    validation = document(products / "independent_validation.json")
    memory = document(leaf / "memory.json")
    runtime = document(leaf / "runtime.json")
    log = (
        (leaf / "gurobi-native.log").read_text(errors="replace")
        if (leaf / "gurobi-native.log").is_file()
        else ""
    )
    state = task["state"].split()[0]
    if state == "CANCELLED":
        outcome = "cancelled_during_run" if leaf.is_dir() else "cancelled_before_start"
    elif validation.get("status") == "accepted":
        assert summary["independent_validation_status"] == "accepted"
        assert validation["failed_check_count"] == 0
        assert summary["objective_value"] is not None and summary["objective_bound"] is not None
        common_gap = (summary["objective_value"] - summary["objective_bound"]) / abs(
            summary["objective_value"]
        )
        assert 0 <= common_gap <= 0.01 and abs(common_gap - summary["mip_gap"]) < 1e-9
        outcome = "validated"
    elif memory.get("guard_triggered"):
        outcome = "job_memory_guard"
    elif "Memory limit reached" in log:
        outcome = "native_soft_memory_limit"
    elif summary.get("status") == "time_limit":
        outcome = "time_limit_no_usable_incumbent"
    else:
        outcome = "unresolved"
    native = number(r"^Explored .*? in ([0-9.]+) seconds", log)
    root = number(r"^Root relaxation:.*?, ([0-9.]+) seconds", log)
    nodes = number(r"^Explored ([0-9]+) nodes", log)
    row = {
        "task": index,
        "case": case,
        "method": item["options"]["Method"],
        "profile": item["profile"],
        "threads": item["threads"],
        "repetition": item["repetition"],
        "slurm_state": state,
        "slurm_exit_code": task["exit_code"],
        "outcome": outcome,
        "original_summary_status": summary.get("status"),
        "validation_status": validation.get("status"),
        "failed_validation_checks": validation.get("failed_check_count"),
        "objective": summary.get("objective_value") if outcome == "validated" else None,
        "bound": summary.get("objective_bound"),
        "gap_fraction": summary.get("mip_gap") if outcome == "validated" else None,
        "economic_cost": summary.get("economic_cost") if outcome == "validated" else None,
        "economic_gap": None,
        "domestic_service": summary.get("domestic_service_level")
        if outcome == "validated"
        else None,
        "penalty_share": summary.get("penalty_cost_share") if outcome == "validated" else None,
        "root_seconds": root,
        "root_completed": bool(re.search(r"^Root relaxation: objective", log, re.M)),
        "native_log_seconds": native,
        "end_to_end_seconds": summary.get("end_to_end_seconds"),
        "nodes": int(nodes) if nodes is not None else None,
        "crossover_seconds": number(r"^Crossover time: ([0-9.]+) seconds", log),
        "job_cgroup_peak_bytes": memory.get("peak_bytes"),
        "guard_triggered": memory.get("guard_triggered"),
        "oom_kill_delta": memory.get("oom_kill_delta"),
        "failcnt_delta": memory.get("failcnt_delta"),
        "physical_cores": runtime.get("topology", {}).get("physical_cores"),
        "native_log_bound_printed": number(r"^Best objective [^,]*, best bound ([0-9.eE+-]+)", log),
        "work_log": number(r"^Explored .*\(([0-9.]+) work units\)", log),
        "input_receipt_present": (leaf / "case/input_receipt.json").is_file(),
    }
    observations.append(row)

assert not any(r["outcome"] == "unresolved" for r in observations)
accepted = [r for r in observations if r["outcome"] == "validated"]
groups = defaultdict(Counter)
for row in observations:
    groups[str(row["method"])][row["outcome"]] += 1
profiles = defaultdict(Counter)
for row in observations:
    profiles[(row["method"], row["profile"])][row["outcome"]] += 1
comparisons = []
for method in (1, 2, 4, 6):
    group = [r for r in accepted if r["method"] == method and r["profile"] == "standard"]
    base = next((r for r in group if r["threads"] == 1), None)
    for row in sorted(group, key=lambda r: r["threads"]):
        comparisons.append(
            {
                "method": method,
                "threads": row["threads"],
                "root_minutes": row["root_seconds"] / 60,
                "native_minutes": row["native_log_seconds"] / 60,
                "ratio_to_1_thread": base["native_log_seconds"] / row["native_log_seconds"]
                if base
                else None,
            }
        )
report = {
    "schema": "h300-root-block1-final-v1",
    "archive_sha256": json.loads((ROOT / "audit.json").read_text())["archive_sha256"],
    "source_commit": PLAN["source"],
    "planned_design_cells": 180,
    "submitted_cells": 60,
    "unsubmitted_cells": 120,
    "scientific_counts": dict(Counter(r["outcome"] for r in observations)),
    "by_method": dict(groups),
    "by_method_profile": [
        {"method": m, "profile": p, **dict(v)} for (m, p), v in sorted(profiles.items())
    ],
    "accepted_ranges": {
        key: [min(r[key] for r in accepted), max(r[key] for r in accepted)]
        for key in (
            "objective",
            "economic_cost",
            "gap_fraction",
            "domestic_service",
            "penalty_share",
            "nodes",
        )
    },
    "standard_profile_clocks": comparisons,
    "observations": observations,
    "validation_scope": (
        "Original accepted original-unit certificates and arithmetic/identity audit; "
        "no new optimization or claim of a fresh solution validation run"
    ),
    "classification_note": (
        "Original summary labels retained. Native soft-memory termination is identified "
        "from complete logs, including cases originally labelled error. "
        "No objective/service is promoted from unusable summaries."
    ),
}
(ROOT / "analysis.json").write_text(json.dumps(report, indent=2))
with (ROOT / "results.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(observations[0]))
    writer.writeheader()
    writer.writerows(observations)
print(json.dumps({k: v for k, v in report.items() if k != "observations"}, indent=2))
