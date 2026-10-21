"""Approved one-arm scalar h500 contract; no scheduler or optimization entry point."""

import re
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

from scripts import mvp2_scalar_h300 as h
from scripts import mvp2_scalar_r3a_operational as o

r = h.r
ROOT = h.ROOT
WORKBOOK_SHA = "888fbff42e4f80817d4d5f0101049495c86c6ed4cda75f00813779dadab41515"
H400_SHA = "e0b58bb74ac254706d30f0f1863162df5d8a714751eadf43b28e7dbc0c5d5def"
H400_SOURCE = "d9ca710dd98b66a4d3421ebccee13d91673d468d"
H400_PLAN = "852f886d58f9bf1f78cee2000ae3d3103bb49f3a27c884e91d40deeca2057afe"
SHAPE = {"warehouses": 500, "periods": 60, "sto_scenarios": 9}
MAX_VARIABLES = 70000000
CASE = "scalar_h500_t1"
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
QUALITY = {
    "common_gap_max": 0.01,
    "original_absolute_tolerance": 1e-5,
    "original_relative_tolerance": 1e-8,
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
    """Replay the accepted original h400 gate, never optimize or reload private input."""
    from scripts.mvp2_scalar_h400_operational import audit

    report = audit(h.input_file(archive, "accepted h400 evidence"), H400_SHA)
    r.require(
        report["status"] == "h400_quality_target_met"
        and report["source_commit"] == H400_SOURCE
        and report["job_id"] == "2219884"
        and report["quality_target_met"]
        and report["operational_receipts_closed"]
        and report["h500_preconditions_met"]
        and not report["h500_execution_admitted"]
        and report["h500_blockers"] == []
        and [a["threads"] for a in report["arms"]] == [1]
        and report["penalty_rates"] == h.RATES,
        "Accepted original h400 quality/closure/headroom gate required.",
    )
    from scripts.review_scalar_h300_evidence import read_archive

    files, _ = read_archive(archive, H400_SHA)
    r.require(r.r2.digest(files["plan.json"]) == H400_PLAN, "Original h400 plan differs.")
    return {
        "archive_sha256": H400_SHA,
        "source_commit": H400_SOURCE,
        "plan_sha256": H400_PLAN,
        "job_id": "2219884",
        "rates": h.RATES,
        "status": "accepted_scalar_h400_predecessor",
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
        500,
    )
    frame = pd.read_excel(workbook, sheet_name="Warehouses", dtype={"CDA": str}).dropna(how="all")
    r.require(
        {"CDA", "Status"} <= set(frame.columns) and frame["CDA"].notna().all(),
        "Materialized h500 warehouse identity columns/values differ.",
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
    maxima = {"DD": 249500, "OD": 18500, "DC": 18500, "OC": 1369}
    r.require(
        audit["schema_version"] == 1
        and audit["input_workbook_sha256"]
        == "fce157696f778e192ecb88a6e9153dc82400f924f74f36b76f0a54916b0df170"
        and audit["output_workbook_sha256"] == WORKBOOK_SHA
        and audit["distance_status"] == "osrm_authoritative"
        and p["provider"] == "osrm"
        and p["profile"] == "driving"
        and p["dataset_id"] == o.DATASET
        and set(counts) == set(maxima)
        and all(type(counts[k]) is int and counts[k] == maxima[k] for k in counts)
        and p["route_count"] == sum(counts.values())
        and p["route_count_by_source"] == {"osrm": p["route_count"]}
        and p["fallback_count"] == 0
        and p["osrm_cache_hit_count"] == 288369
        and p["osrm_negative_distance_normalization_count"] == 6
        and all(
            type(p[k]) is int and p[k] == 0
            for k in ("osrm_request_count", "osrm_cache_miss_count", "osrm_cache_write_count")
        ),
        "Frozen OSRM h500 audit differs; preserve, do not regenerate.",
    )
    return audit


def design(files):
    plan, source, selection = [
        r.strict_json(files[n]) for n in ("plan.json", "source.json", "warehouse_selection.json")
    ]
    r.require(
        plan["schema_version"] == "scalar-h500-operational-v1"
        and plan["status"] == "prepared_for_one_human_h500"
        and plan["resources"] == PROFILE
        and plan["quality_criteria"] == QUALITY
        and plan["frozen_rates"] == h.RATES
        and plan["expected_shape"] == SHAPE
        and all(plan[k] is False for k in r.closed()),
        "h500 contract differs.",
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
        selection["target_population"] == len(members) == 500
        and len({m["warehouse_id"] for m in members}) == 500
        and len(existing) == 146
        and len(candidates) == 354
        and selection["population_manifest_sha256"] == o.POPULATION_SHA
        and selection["population_order_sha256"] == o.ORDER_SHA
        and "checkpoint_derivation" not in selection
        and selection["selection_seed"].strip()
        and selection["selection_method"].strip()
        and selection["criterion"].strip()
        and actual["workbook_sha256"] == WORKBOOK_SHA
        and len(actual["ordered_ids"]) == len(set(actual["ordered_ids"])) == 500
        and set(actual["ordered_ids"]) == {m["warehouse_id"] for m in members}
        and all(
            m["candidate_rank"] is None and m["selection_stratum"] == "protected_existing"
            for m in existing
        )
        and sorted(m["candidate_rank"] for m in candidates) == list(range(1, 355))
        and all(
            (m["selection_stratum"] == "canonical_gold_anchor") == (m["candidate_rank"] <= 69)
            for m in candidates
        ),
        "Frozen h500 population/roles/anchors/ranks differ.",
    )
    parent = plan["predecessor"]
    r.require(
        parent
        == {
            "archive_sha256": H400_SHA,
            "source_commit": H400_SOURCE,
            "plan_sha256": H400_PLAN,
            "job_id": "2219884",
            "rates": h.RATES,
            "status": "accepted_scalar_h400_predecessor",
            **r.closed(),
        },
        "Original h400 predecessor binding differs.",
    )
    cases = plan["cases"]
    r.require(len(cases) == 1, "One h500 arm only.")
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
    if case["workbook"].startswith("/") and "\\" not in case["workbook"]:
        expected["workbook"] = template.workbook.as_posix()
    r.require(case == r.strict_json(r.r2.encoded(expected)), "h500 scientific/input profile drift.")
    return plan
