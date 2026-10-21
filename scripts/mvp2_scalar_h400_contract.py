"""Approved one-arm scalar h400 contract; no scheduler or optimization entry point."""

import re
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

from scripts import mvp2_scalar_h300 as h
from scripts import mvp2_scalar_r3a_operational as o

r = h.r
ROOT = h.ROOT
WORKBOOK_SHA = "c3085456997714ef5a8bdbf61e2c9a5e578c2636003947427cf58933d21ceb13"
H300_SHA = "dc5969fa391dc81590210ef7e6f89abbb5df554e4bc5b2032ba9eafe1a67f3fc"
H300_SOURCE = "04ba9edccc93f40ab36cbc3264039a7edf2f6f51"
H300_PLAN = "000a760b3c263cfd7e88fb75714ac5f125df9c4e27332045c761a75bd60bffb1"
SHAPE = {"warehouses": 400, "periods": 60, "sto_scenarios": 9}
MAX_VARIABLES = 45000000
CASE = "scalar_h400_t1"
PROFILE = {
    "status": "maintainer_approved_20261021",
    "allocated_logical_cpus": 24,
    "worker_affinity_logical_cpus": 16,
    "solver_threads": 1,
    "memory_mib": 196608,
    "soft_memory_decimal_gb": 160,
    "slurm_wall_seconds": 28800,
    "build_input_seconds_per_arm": 3600,
    "native_time_limit_seconds_per_arm": 14400,
    "late_return_export_seconds_per_arm": 900,
    "validation_seconds_per_arm": 1800,
    "step_seconds": 20700,
    "setup_cleanup_seconds": 1800,
    "contingency_seconds": 6300,
    "reservation_logical_cpu_hours": 192,
    "expanded_transfer_bytes": 1024**3,
    "max_regular_members": 4096,
}
ELIGIBILITY = {
    "common_gap_max": 0.01,
    "os_rss_max_bytes": 0.8 * 192 * 1024**3,
    "native_memory_max_bytes": 0.8 * 160 * 10**9,
    "separate_h500_input_resource_admission_required": True,
    "automatic_follow_on_allowed": False,
}


def specs(workbook):
    from src.logic.experiment_runner import load_experiment_manifest

    template = load_experiment_manifest(r.MANIFEST).experiments[1]
    return [
        replace(
            template,
            name=CASE,
            workbook=Path(workbook),
            solver=replace(template.solver, threads=1, time_limit=14400),
            max_estimated_variables=MAX_VARIABLES,
        )
    ]


def predecessor(archive):
    from scripts.review_scalar_h300_evidence import review

    report = review(h.input_file(archive, "accepted h300 evidence"), H300_SHA)
    r.require(
        report["status"] == "accepted_scalar_h300_block"
        and report["source_commit"] == H300_SOURCE
        and report["plan_sha256"] == H300_PLAN
        and report["job_id"] == "2218193"
        and report["quality_target_met"]
        and report["operational_receipts_closed"]
        and [a["threads"] for a in report["arms"]] == [4, 1, 8, 2, 16]
        and report["penalty_rates"] == h.RATES,
        "Accepted original h300 block required.",
    )
    return {
        "archive_sha256": H300_SHA,
        "source_commit": H300_SOURCE,
        "plan_sha256": H300_PLAN,
        "job_id": "2218193",
        "rates": h.RATES,
        "status": "accepted_scalar_h300_predecessor",
        **r.closed(),
    }


def read_selection(workbook, population, order):
    import pandas as pd

    from src.logic.warehouse_population import _population_role

    selection = r.warehouses.read_policy(
        h.input_file(population, "population manifest"),
        h.input_file(order, "population order"),
        o.POPULATION_SHA,
        o.ORDER_SHA,
        400,
        reviewed_nested_target=400,
    )
    frame = pd.read_excel(workbook, sheet_name="Warehouses", dtype={"CDA": str}).dropna(how="all")
    r.require(
        {"CDA", "Status"} <= set(frame.columns) and frame["CDA"].notna().all(),
        "Materialized h400 warehouse identity columns/values differ.",
    )
    ids = frame["CDA"].str.strip().tolist()
    roles = frame["Status"].map(_population_role).tolist()
    r.require(all(ids), "Empty warehouse ID.")
    r.warehouses.membership_receipt(
        SimpleNamespace(
            warehouses=ids,
            existing_warehouses=[
                v for v, role in zip(ids, roles, strict=True) if role == "existing"
            ],
            candidate_warehouses=[
                v for v, role in zip(ids, roles, strict=True) if role == "candidate"
            ],
        ),
        selection,
    )
    selection["materialized_membership"] = {
        "workbook_sha256": r.file_hash(workbook),
        "ordered_ids": ids,
        "scope": "Warehouse IDs/roles only; full scientific preflight required on compute.",
    }
    return selection


def materialization(audit):
    p = audit["distance_provenance"]
    counts = p["route_count_by_arc_type"]
    maxima = {"DD": 159600, "OD": 14800, "DC": 14800, "OC": 1369}
    r.require(
        audit["schema_version"] == 1
        and audit["output_workbook_sha256"] == WORKBOOK_SHA
        and audit["distance_status"] == "osrm_authoritative"
        and p["provider"] == "osrm"
        and p["profile"] == "driving"
        and p["dataset_id"] == o.DATASET
        and set(counts) == set(maxima)
        and all(type(counts[k]) is int and 0 < counts[k] <= maxima[k] for k in counts)
        and p["route_count"] == sum(counts.values())
        and p["route_count_by_source"] == {"osrm": p["route_count"]}
        and p["fallback_count"] == 0
        and all(
            type(p[k]) is int and p[k] >= 0
            for k in ("osrm_request_count", "osrm_cache_miss_count", "osrm_cache_write_count")
        ),
        "Frozen OSRM h400 audit differs; preserve, do not regenerate.",
    )
    return audit


def design(files):
    plan, source, selection = [
        r.strict_json(files[n]) for n in ("plan.json", "source.json", "warehouse_selection.json")
    ]
    r.require(
        plan["schema_version"] == "scalar-h400-operational-v1"
        and plan["status"] == "prepared_for_one_human_h400"
        and plan["resources"] == PROFILE
        and plan["h500_criteria"] == ELIGIBILITY
        and plan["frozen_rates"] == h.RATES
        and plan["expected_shape"] == SHAPE
        and all(plan[k] is False for k in r.closed()),
        "h400 contract differs.",
    )
    r.require(
        re.fullmatch(r"[0-9a-f]{40}", plan["source_commit"])
        and source["source_commit"] == plan["source_commit"]
        and r.r2.digest(files["source.json"]) == plan["source_inventory_sha256"]
        and r.r2.digest(files["warehouse_selection.json"]) == plan["warehouse_selection_sha256"],
        "Source/selection binding differs.",
    )
    members = selection["members"]
    existing = [m for m in members if m["population_role"] == "existing"]
    candidates = [m for m in members if m["population_role"] == "candidate"]
    actual = selection["materialized_membership"]
    r.require(
        selection["target_population"] == len(members) == 400
        and len({m["warehouse_id"] for m in members}) == 400
        and len(existing) == 146
        and len(candidates) == 254
        and selection["population_manifest_sha256"] == o.POPULATION_SHA
        and selection["population_order_sha256"] == o.ORDER_SHA
        and selection["checkpoint_derivation"] == r.warehouses.h400_derivation()
        and selection["selection_seed"].strip()
        and selection["selection_method"].strip()
        and selection["criterion"].strip()
        and actual["workbook_sha256"] == WORKBOOK_SHA
        and len(actual["ordered_ids"]) == len(set(actual["ordered_ids"])) == 400
        and set(actual["ordered_ids"]) == {m["warehouse_id"] for m in members}
        and all(
            m["candidate_rank"] is None and m["selection_stratum"] == "protected_existing"
            for m in existing
        )
        and sorted(m["candidate_rank"] for m in candidates) == list(range(1, 255))
        and all(
            (m["selection_stratum"] == "canonical_gold_anchor") == (m["candidate_rank"] <= 69)
            for m in candidates
        ),
        "Frozen h400 population/roles/anchors/ranks differ.",
    )
    parent = plan["predecessor"]
    r.require(
        parent
        == {
            "archive_sha256": H300_SHA,
            "source_commit": H300_SOURCE,
            "plan_sha256": H300_PLAN,
            "job_id": "2218193",
            "rates": h.RATES,
            "status": "accepted_scalar_h300_predecessor",
            **r.closed(),
        },
        "Original h300 predecessor binding differs.",
    )
    cases = plan["cases"]
    r.require(len(cases) == 1, "One h400 arm only.")
    case = cases[0]
    template = specs(Path(case["workbook"]))[0]
    expected = {
        "name": template.name,
        "workbook": str(template.workbook),
        "workbook_sha256": WORKBOOK_SHA,
        "loader": asdict(template.loader),
        "model": asdict(template.model),
        "solver": asdict(template.solver),
        "max_estimated_variables": MAX_VARIABLES,
        "metadata": template.metadata,
    }
    # A sealed Linux path is a lexical identifier during portable replay, not
    # a request to open that private workbook on the reviewer's operating system.
    # Preserve old local Windows receipts too; only POSIX-form case strings use
    # forward-slash serialization. All other fields and equality remain strict.
    if case["workbook"].startswith("/") and "\\" not in case["workbook"]:
        expected["workbook"] = template.workbook.as_posix()
    r.require(case == r.strict_json(r.r2.encoded(expected)), "h400 scientific/input profile drift.")
    return plan
