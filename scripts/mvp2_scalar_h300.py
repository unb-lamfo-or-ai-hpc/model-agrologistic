"""Consolidated h300 preparation and fixed-penalty gate; no job entry point.

The public CLI only hashes/binds existing artifacts. Excel preflight is a pure
software seam for the later reviewed runtime; no solver/Slurm is imported here.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import tarfile
from dataclasses import replace
from pathlib import Path

from scripts import mvp2_scalar_r3a as r
from scripts import mvp2_scalar_r3a_operational as previous

ROOT = r.ROOT
CLAIM = ".mvp2-scalar-h300-preparation-v1"
ARCHIVE = "scalar-h300-preparation-evidence.tar.gz"
H215_SHA = "81890b546d720ad5999d11f44fd499337aad937e32773db39067796f73660534"
H215_SOURCE = "5f73871b6320da71e308e436f5cd780cdcfedae2"
H215_PLAN = "e9f9b26c91585fde271876a1dab6b51dcd63110b83e9600b3781165a66a7a722"
WORKBOOK_SHA = "7761cce77cf93dcba2f617714f0117c1f2ead4de0c3f27149daceba447e0c7d1"
RATES = {"unmet": 90000, "static": 45000, "reception": 45000}
ORDER = (4, 1, 8, 2, 16)
SHAPE = {"warehouses": 300, "periods": 60, "sto_scenarios": 9}
MAX_VARIABLES = 30000000
MAX_BYTES = 16 * 1024**2  # Preparation-only receipts, not native solution transfer.


def input_file(path, label):
    """Identify the rejected input without following a link or guessing another path."""
    path = Path(path)
    r.require(not path.is_symlink(), f"{label}: symbolic link refused: {path}")
    r.require(path.exists(), f"{label}: missing or inaccessible file: {path}")
    r.require(path.is_file(), f"{label}: not a regular file: {path}")
    return previous.regular(path)


def penalty_receipt(contract, *, warehouse_ids=None, demand_pairs=None):
    """Check every effective rate after route selection, not merely loader defaults."""
    from src.logic.mathematical_contract import canonical_hash

    vector = contract["penalty_vector"]
    r.require(set(vector) == set(RATES), "Three separate penalty families required.")
    r.require(
        contract["penalty_vector_sha256"] == canonical_hash(vector), "Penalty vector hash differs."
    )
    for family, rate in RATES.items():
        rows = vector[family]
        width = 3 if family == "unmet" else 2
        r.require(isinstance(rows, list) and bool(rows), "Empty penalty family.")
        r.require(
            all(isinstance(row, (list, tuple)) and len(row) == width for row in rows),
            "Malformed penalty row.",
        )
        keys = [tuple(row[:-1]) for row in rows]
        r.require(
            all(all(isinstance(v, str) and v for v in key) for key in keys)
            and len(set(keys)) == len(keys)
            and all(type(row[-1]) in (int, float) and row[-1] == rate for row in rows),
            "Effective penalty drift/duplicate identifier; preserve input and stop.",
        )
        expected = demand_pairs if family == "unmet" else warehouse_ids
        if expected is not None:
            expected = set(expected) if family == "unmet" else {(v,) for v in expected}
            r.require(set(keys) == expected, "Missing/extra penalty identifiers.")
    r.require(
        {row[0] for row in vector["static"]} == {row[0] for row in vector["reception"]},
        "Storage/reception warehouse coverage differs.",
    )
    r.require(
        contract["emergency_static_unit"] == "stock_tonnes_at_warehouse_period"
        and contract["emergency_reception_unit"] == "overflow_tonnes_in_period",
        "Penalty physical units differ.",
    )
    return {
        "status": "effective_penalties_match_accepted_h215",
        "rates": dict(RATES),
        "penalty_vector_sha256": contract["penalty_vector_sha256"],
        "family_counts": {k: len(v) for k, v in vector.items()},
        "coefficient_changes": False,
        **r.closed(),
    }


def verify_h215(archive):
    r.require(r.file_hash(previous.regular(archive)) == H215_SHA, "Accepted h215 hash required.")
    report = previous.audit(archive, H215_SHA)
    r.require(
        report["status"] == "pair_quality_target_met"
        and report["operational_receipts_closed"]
        and report["job_id"] == "2217990"
        and [a["mode"] for a in report["arms"]] == ["det", "sto"]
        and all(a["scalar_gap_target_met"] for a in report["arms"]),
        "Accepted h215 pair required.",
    )
    with tarfile.open(archive, "r:gz") as tar:
        plan = r.strict_json(tar.extractfile("plan.json").read())
        r.require(plan["source_commit"] == H215_SOURCE, "h215 source differs.")
        r.require(
            r.r2.digest(tar.extractfile("plan.json").read()) == H215_PLAN, "h215 plan differs."
        )
        for mode in ("det", "sto"):
            receipt = r.strict_json(
                tar.extractfile(f"cases/scalar_h215_{mode}/input_receipt.json").read()
            )
            population = receipt["warehouse_selection"]["included"]
            penalty_receipt(
                receipt["mathematical_contract"],
                warehouse_ids=[m["warehouse_id"] for m in population],
            )
    return {
        "archive_sha256": H215_SHA,
        "source_commit": H215_SOURCE,
        "plan_sha256": H215_PLAN,
        "job_id": "2217990",
        "status": "accepted_scalar_h215_success",
        "rates": dict(RATES),
        "qualification": "Original certificate replay; no fresh private-input residual solve.",
        **r.closed(),
    }


def proposal():
    """Arithmetic proposal only; existing four-hour native budget is retained."""
    per_arm = 1800 + 14400 + 900 + 1800
    blocks = []
    for number, (levels, wall) in enumerate(((ORDER, 108000),), 1):
        planned = len(levels) * per_arm + 1800
        blocks.append(
            {
                "block": number,
                "threads": list(levels),
                "slurm_wall_seconds": wall,
                "planned_seconds": planned,
                "reserve_seconds": wall - planned,
                "reserved_logical_cpu_hours": 24 * wall / 3600,
            }
        )
    return {
        "status": "resource_and_order_proposal_not_execution_admission",
        "thread_order": list(ORDER),
        "blocks": blocks,
        "allocated_logical_cpus": 24,
        "fixed_worker_logical_cpu_pool": 16,
        "memory_mib": 196608,
        "soft_memory_decimal_gb": 160,
        "native_time_limit_seconds_per_arm": 14400,
        "input_build_seconds_per_arm": 1800,
        "shared_late_return_export_seconds_per_arm": 900,
        "validation_seconds_per_arm": 1800,
        "step_seconds": per_arm,
        "setup_cleanup_seconds_per_block": 1800,
        "reserved_logical_cpu_hours_total": sum(b["reserved_logical_cpu_hours"] for b in blocks),
        "five_arm_minimum_seconds": 5 * per_arm + 1800,
        "expanded_native_transfer_bytes_per_block_proposal": 1024**3,
        "npad_job_ceiling_seconds_maintainer_confirmed": 172800,
        "required_decisions": ["one_30h_allocation_resource_envelope", "serial_thread_order"],
        **r.closed(),
    }


def specs(workbook):
    from src.logic.experiment_runner import load_experiment_manifest

    templates = load_experiment_manifest(r.MANIFEST).experiments
    sto = templates[1]
    return [
        replace(
            sto,
            name=f"scalar_h300_t{threads}",
            workbook=Path(workbook),
            solver=replace(sto.solver, threads=threads, time_limit=14400),
            max_estimated_variables=MAX_VARIABLES,
        )
        for threads in ORDER
    ]


def preflight(spec, selection):
    """Load frozen Excel, select routes and verify rates before model construction."""
    from src.logic.mathematical_contract import prepare_model_data

    original, receipt = r.preflight(spec, SHAPE, selection)
    data = prepare_model_data(original, spec.model)
    probabilities = receipt["effective_scenario_probabilities"]
    r.require(
        len(probabilities) == 9 and all(v == 1 / 9 for v in probabilities.values()),
        "Nine equiprobable Cartesian scenarios required.",
    )
    receipt["frozen_penalty_review"] = penalty_receipt(
        receipt["mathematical_contract"],
        warehouse_ids=data.warehouses,
        demand_pairs={(c, p) for c in data.domestic_customers for p in data.products},
    )
    return original, receipt


def prepare(claim, sha, workbook, population, order, predecessor):
    """Hash-only human preparation; no scheduler, license, database or Excel ETL."""
    claim = Path(claim)
    r.require(claim.name == CLAIM and not claim.exists(), "Fresh dedicated preparation claim.")
    r.require(re.fullmatch(r"[0-9a-f]{40}", sha), "Full reviewed source required.")
    input_file(workbook, "h300 workbook")
    r.require(r.file_hash(workbook) == WORKBOOK_SHA, "Historical h300 workbook hash differs.")
    parent = verify_h215(predecessor)
    selection = r.warehouses.read_policy(
        population, order, previous.POPULATION_SHA, previous.ORDER_SHA, 300
    )
    inventory = r.r2.source_inventory(ROOT)
    r.require(inventory["source_commit"] == sha, "Wrong source head.")
    r.r2.verify_source(inventory, ROOT)
    plan = {
        "schema_version": "scalar-h300-preparation-v1",
        "status": "prepared_optimization_closed",
        "source_commit": sha,
        "source_root": str(ROOT),
        "source_inventory_sha256": r.r2.digest(r.r2.encoded(inventory)),
        "warehouse_selection_sha256": r.r2.digest(r.r2.encoded(selection)),
        "predecessor": parent,
        "cases": [r.spec_payload(s) for s in specs(workbook)],
        "expected_shape": SHAPE,
        "frozen_rates": dict(RATES),
        "resources": proposal(),
        **r.closed(),
    }
    r.require(r.file_hash(workbook) == WORKBOOK_SHA, "Input changed during preparation.")
    claim.mkdir(mode=0o700)
    r.r2.write(claim / "source.json", inventory)
    r.r2.write(claim / "warehouse_selection.json", selection)
    r.r2.write(claim / "plan.json", plan)
    return {"status": plan["status"], "plan_sha256": r.file_hash(claim / "plan.json"), **r.closed()}


def review(
    files,
    *,
    schema="scalar-h300-preparation-v1",
    status="prepared_optimization_closed",
    resource_profile=None,
):
    plan = r.strict_json(files["plan.json"])
    source = r.strict_json(files["source.json"])
    selection = r.strict_json(files["warehouse_selection.json"])
    r.require(
        plan["schema_version"] == schema
        and plan["status"] == status
        and re.fullmatch(r"[0-9a-f]{40}", plan["source_commit"])
        and all(plan[k] is False for k in r.closed())
        and plan["resources"] == (proposal() if resource_profile is None else resource_profile)
        and plan["frozen_rates"] == RATES
        and plan["expected_shape"] == SHAPE,
        "h300 preparation contract drift.",
    )
    r.require(
        r.r2.digest(files["source.json"]) == plan["source_inventory_sha256"]
        and source["source_commit"] == plan["source_commit"]
        and r.r2.digest(files["warehouse_selection.json"]) == plan["warehouse_selection_sha256"]
        and selection["target_population"] == 300
        and selection["population_manifest_sha256"] == previous.POPULATION_SHA
        and selection["population_order_sha256"] == previous.ORDER_SHA
        and bool(selection["selection_method"].strip())
        and bool(selection["selection_seed"].strip())
        and len(selection["members"]) == 300
        and len({m["warehouse_id"] for m in selection["members"]}) == 300
        and sum(m["population_role"] == "existing" for m in selection["members"]) == 146,
        "Source/population binding differs.",
    )
    members = selection["members"]
    r.require(
        sorted(m["candidate_rank"] for m in members if m["population_role"] == "candidate")
        == list(range(1, 155))
        and all(
            m["selection_stratum"] == "protected_existing" and m["candidate_rank"] is None
            for m in members
            if m["population_role"] == "existing"
        )
        and all(
            (m["selection_stratum"] == "canonical_gold_anchor") == (m["candidate_rank"] <= 69)
            for m in members
            if m["population_role"] == "candidate"
        ),
        "Frozen warehouse role/rank/anchor criterion differs.",
    )
    parent = plan["predecessor"]
    r.require(
        parent["archive_sha256"] == H215_SHA
        and parent["source_commit"] == H215_SOURCE
        and parent["plan_sha256"] == H215_PLAN
        and parent["job_id"] == "2217990"
        and parent["status"] == "accepted_scalar_h215_success"
        and parent["rates"] == RATES
        and all(parent[k] is False for k in r.closed()),
        "h215 predecessor binding differs.",
    )
    cases = plan["cases"]
    r.require(len(cases) == len(ORDER), "Five distinct thread arms required.")
    expected = specs(Path(cases[0]["workbook"]))
    for case, template in zip(cases, expected, strict=True):
        # Recreate full settings without requiring private workbook bytes for replay.
        from dataclasses import asdict

        r.require(
            case["name"] == template.name
            and case["workbook"] == cases[0]["workbook"]
            and case["workbook_sha256"] == WORKBOOK_SHA
            and case["loader"] == r.strict_json(r.r2.encoded(asdict(template.loader)))
            and case["model"] == r.strict_json(r.r2.encoded(asdict(template.model)))
            and case["solver"] == r.strict_json(r.r2.encoded(asdict(template.solver)))
            and case["max_estimated_variables"] == MAX_VARIABLES
            and case["metadata"] == template.metadata,
            "Scientific/thread/input profile differs.",
        )
    return {
        "status": "preparation_integrity_replayed_execution_closed",
        "source_commit": plan["source_commit"],
        "penalty_rates": dict(RATES),
        "thread_order": list(ORDER),
        "qualification": (
            "Plan/receipt integrity only; private h300 Excel preflight still required."
        ),
        **r.closed(),
    }


def collect(claim):
    claim = Path(claim)
    r.require(claim.name == CLAIM and not claim.is_symlink(), "Dedicated unlinked preparation.")
    names = {"plan.json", "source.json", "warehouse_selection.json"}
    files = {n: previous.regular(claim / n).read_bytes() for n in names}
    result = review(files)
    marker = claim / "collection.json"
    if marker.exists():
        saved = r.strict_json(previous.regular(marker).read_bytes())
        r.require(
            saved["archive"] == ARCHIVE
            and saved["status"] == result["status"]
            and r.file_hash(previous.regular(claim / ARCHIVE)) == saved["sha256"],
            "Preserved collection changed.",
        )
        return saved
    files["inventory.json"] = r.r2.encoded({n: r.r2.digest(b) for n, b in files.items()})
    r.require(sum(map(len, files.values())) <= MAX_BYTES, "Preparation transfer cap exceeded.")
    archive = claim / ARCHIVE
    with archive.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as tar:
        for name, content in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size = len(content)
            member.mode = 0o600
            tar.addfile(member, io.BytesIO(content))
    checksum = r.file_hash(archive)
    with Path(str(archive) + ".sha256").open("x") as stream:
        stream.write(checksum + "  " + ARCHIVE + "\n")
    result.update(archive=ARCHIVE, sha256=checksum)
    r.r2.write(marker, result)
    return result


def audit(archive, checksum):
    r.require(
        re.fullmatch(r"[0-9a-f]{64}", checksum)
        and r.file_hash(previous.regular(archive)) == checksum,
        "External preparation checksum differs.",
    )
    files = {}
    size = 0
    with tarfile.open(archive, "r:gz") as tar:
        for m in tar:
            r.require(
                m.isfile()
                and m.name
                in {"plan.json", "source.json", "warehouse_selection.json", "inventory.json"}
                and m.name not in files,
                "Unexpected/linked/duplicate preparation member.",
            )
            size += m.size
            r.require(size <= MAX_BYTES, "Expanded preparation cap exceeded.")
            files[m.name] = tar.extractfile(m).read()
    inventory = r.strict_json(files.pop("inventory.json"))
    r.require(inventory == {n: r.r2.digest(b) for n, b in files.items()}, "Inventory differs.")
    return review(files)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("proposal", "prepare", "collect", "audit"))
    parser.add_argument("--claim", type=Path)
    parser.add_argument("--source-sha")
    parser.add_argument("--workbook", type=Path)
    parser.add_argument("--population", type=Path)
    parser.add_argument("--order", type=Path)
    parser.add_argument("--predecessor", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--sha256")
    args = parser.parse_args(argv)
    if args.action == "proposal":
        result = proposal()
    elif args.action == "audit":
        result = audit(args.archive, args.sha256)
    elif args.action == "collect":
        result = collect(args.claim)
    else:
        result = prepare(
            args.claim,
            args.source_sha,
            args.workbook,
            args.population,
            args.order,
            args.predecessor,
        )
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    print("NO_JOB_REPEAT_LARGER_INSTANCE_OR_AUTOMATIC_FOLLOW_ON_ADMITTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
