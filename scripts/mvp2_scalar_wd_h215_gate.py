"""Input-only W/D h215 qualification; no solver, scheduler or execution admission.

W cells are reconstructed inputs, NOT repetitions. Only D DET/STO are proposed
future solves. A new operational package and human decisions are still required.
"""

from __future__ import annotations

import argparse
import io
import math
import subprocess
import tarfile
from dataclasses import asdict, fields, replace
from pathlib import Path

from scripts import mvp2_scalar_r3a_operational as old
from src.logic.excel_loader import load_model_data_from_excel
from src.logic.experiment_runner import estimate_model_size
from src.logic.mathematical_contract import prepare_model_data
from src.logic.model_validation import validate_or_raise_model_data
from src.logic.route_filtering import select_routes

r = old.r
ROOT = Path(__file__).resolve().parents[1]
CLAIM = ".mvp2-scalar-wd-h215-preparation-v1"
W_SHA = "81890b546d720ad5999d11f44fd499337aad937e32773db39067796f73660534"
W_SOURCE = "5f73871b6320da71e308e436f5cd780cdcfedae2"
W_PLAN = "e9f9b26c91585fde271876a1dab6b51dcd63110b83e9600b3781165a66a7a722"
PENALTY_SHA = "e0f93593659c35d14b85cdaddecbe020edb375376f5e30ae99b05bed876d276f"
RATES = {"unmet": 90000, "static": 45000, "reception": 45000}
COMMON = ("od", "dc", "dd")


def closed():
    return {
        **r.closed(),
        "d_execution_admitted": False,
        "w_repetition_admitted": False,
        "resource_envelope_approved_for_d": False,
    }


def resource_proposal():
    return {
        **old.budget(),
        "status": "proposed_for_new_d_pair_not_approved",
        "scope": "Two D cells only; historical W is not rerun.",
        **closed(),
    }


def source_inventory(root):
    """Same raw tracked-byte contract, one Git archive instead of N subprocesses.

    Read Git objects as data only. Reject export-ignored/missing/link/extra Python
    source; no archive extraction, executable import or relaxed EOL comparison.
    """
    head = r.r2.command(["git", "rev-parse", "HEAD"], cwd=root)
    listing = r.r2.command(["git", "ls-files", "-z"], cwd=root)
    r.require(head.returncode == listing.returncode == 0, "Source Git identity unavailable.")
    raw = subprocess.check_output(["git", "archive", "--format=tar", "HEAD"], cwd=root, timeout=30)
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for member in archive:
            if member.isdir():
                continue
            r.require(
                member.isfile() and r._safe_name(member.name) and member.name not in files,
                "Invalid Git source object.",
            )
            path = old.regular(root / member.name)
            content = archive.extractfile(member).read()
            r.require(path.read_bytes() == content, "Raw HEAD-byte mismatch: " + member.name)
            files[member.name] = r.r2.digest(content)
    r.require(
        set(files) == set(filter(None, listing.stdout.split("\0"))),
        "Full tracked source inventory differs.",
    )
    inventory = {"source_commit": head.stdout.strip(), "files": files}
    r.r2.verify_source(inventory, root)
    return inventory


def proposed_specs(workbook):
    """Derive from the original 4h profile; change only the two topology switches."""
    cases = {}
    for original in old.specs(workbook):
        mode = original.model.mode
        cases[f"W_{mode}"] = original
        cases[f"D_{mode}"] = replace(
            original,
            name=f"scalar_h215_d_{mode}",
            loader=replace(original.loader, include_direct_origin_customer_routes=True),
            model=replace(original.model, use_direct_origin_customer=True),
        )
    return cases


def _normalize(value, *, unbounded_export=False):
    """Strict indexed scientific hashing; only positive infinite export caps allowed.

    Optional geography/metadata is excluded explicitly, not sanitized to disguise
    NaN. Unbounded export caps are represented as typed values, never finite caps.
    """
    if isinstance(value, dict):
        return [
            [_normalize(k), _normalize(v, unbounded_export=unbounded_export)]
            for k, v in sorted(value.items(), key=lambda item: repr(item[0]))
        ]
    if isinstance(value, (set, list, tuple)):
        ordered = sorted(value, key=repr) if isinstance(value, set) else value
        return [_normalize(v, unbounded_export=unbounded_export) for v in ordered]
    if isinstance(value, float) and not math.isfinite(value):
        r.require(unbounded_export and value == math.inf, "Nonfinite scientific input.")
        return {"export_upper_bound": "positive_infinity"}
    return value


def common_data_hashes(data):
    excluded = {"routes_oc", "dist_oc", "duration_oc", "node_info", "metadata"}
    return {
        field.name: r.r2.digest(
            r.r2.encoded(
                _normalize(
                    getattr(data, field.name),
                    unbounded_export=field.name in {"demand_exp", "demand_exp_s"},
                )
            )
        )
        for field in fields(data)
        if field.name not in excluded
    }


def inspect_cell(spec, *, loader=load_model_data_from_excel):
    """Read/prepare/estimate only; never construct a mathematical solver model."""
    data = prepare_model_data(loader(spec.workbook, spec.loader), spec.model)
    validate_or_raise_model_data(data, spec.model)
    graph = select_routes(data, spec.model)
    contract = data.metadata["mathematical_contract"]
    edges = {
        family: [list(edge) for edge in sorted(getattr(graph, family))]
        for family in (*COMMON, "oc")
    }
    estimate = asdict(estimate_model_size(data, spec.model))
    r.require(estimate["total_variables"] <= spec.max_estimated_variables, "Size guard exceeded.")
    return {
        "specification": r.strict_json(r.r2.encoded(r.spec_payload(spec))),
        "estimate": estimate,
        "common_data_sha256": common_data_hashes(data),
        "edges": edges,
        "edge_sha256": {k: r.r2.digest(r.r2.encoded(v)) for k, v in edges.items()},
        "contract": r.strict_json(r.r2.encoded(contract)),
        "effective_probabilities": (
            dict(data.scenario_prob) if spec.model.mode == "sto" else {"deterministic": 1.0}
        ),
        "warehouse_data": data,
    }


def compare_pair(w, d):
    """Reject confounding settings, coefficients, graph repair or scientific data."""
    wp, dp = [r.strict_json(r.r2.encoded(cell["specification"])) for cell in (w, d)]
    r.require(
        wp["model"]["use_direct_origin_customer"] is False
        and wp["loader"]["include_direct_origin_customer_routes"] is False
        and dp["model"]["use_direct_origin_customer"] is True
        and dp["loader"]["include_direct_origin_customer_routes"] is True,
        "Both topology switches must be explicit.",
    )
    for p in (wp, dp):
        p.pop("name")
        p["model"].pop("use_direct_origin_customer")
        p["loader"].pop("include_direct_origin_customer_routes")
    r.require(wp == dp, "Non-topology configuration differs.")
    r.require(w["common_data_sha256"] == d["common_data_sha256"], "Common data/costs differ.")
    r.require(
        w["effective_probabilities"] == d["effective_probabilities"], "Scenario weights differ."
    )
    r.require(all(w["edges"][k] == d["edges"][k] for k in COMMON), "Common retained arcs differ.")
    r.require(not w["edges"]["oc"] and d["edges"]["oc"], "Missing direct-network extension.")
    for family, rate in RATES.items():
        for cell in (w, d):
            vector = cell["contract"]["penalty_vector"][family]
            r.require(vector and all(row[-1] == rate for row in vector), "Effective penalty drift.")
    r.require(
        w["contract"]["penalty_vector"] == d["contract"]["penalty_vector"],
        "Penalty vector differs.",
    )
    delta = len(d["edges"]["oc"]) * w["estimate"]["period_count"] * w["estimate"]["scenario_count"]
    r.require(
        d["estimate"]["total_variables"] - w["estimate"]["total_variables"] == delta,
        "Unexpected non-direct variable growth.",
    )
    return {
        "common_arcs_identical": True,
        "common_data_identical": True,
        "penalties_identical": True,
        "added_direct_arcs": len(d["edges"]["oc"]),
        "added_flow_variables": delta,
        "causal_runtime_comparison_admitted": False,
        **closed(),
    }


def historical_w(archive):
    """Replay the original accepted archive, never import or execute archive code."""
    r.require(r.file_hash(old.regular(archive)) == W_SHA, "Original W archive checksum differs.")
    review = old.audit(archive, W_SHA)
    r.require(
        review["status"] == "pair_quality_target_met" and review["job_id"] == "2217990",
        "Historical W evidence not accepted.",
    )
    with tarfile.open(archive, "r:gz") as tar:

        def read(name):
            return r.strict_json(tar.extractfile(name).read())

        plan, job = read("plan.json"), read("job.json")
        r.require(
            plan["source_commit"] == W_SOURCE and job["plan_sha256"] == W_PLAN,
            "Historical W source/plan differs.",
        )
        receipts = {
            mode: read(f"cases/scalar_h215_{mode}/input_receipt.json") for mode in old.MODES
        }
        scientific_sources = {
            k: v for k, v in read("source.json")["files"].items() if k.startswith("src/logic/")
        }
    return {
        "source_commit": W_SOURCE,
        "plan_sha256": W_PLAN,
        "archive_sha256": W_SHA,
        "review": review,
        "receipts": receipts,
        "scientific_sources": scientific_sources,
    }


def inspect_comparison(workbook, selection, previous):
    cells, comparisons = {}, {}
    for label, spec in proposed_specs(workbook).items():
        cell = inspect_cell(spec)
        membership = r.warehouses.membership_receipt(cell.pop("warehouse_data"), selection)
        mode = spec.model.mode
        prior = previous["receipts"][mode]
        r.require(membership == prior["warehouse_selection"], "Original W membership differs.")
        cell["warehouse_selection"] = membership
        r.require(
            cell["contract"]["penalty_vector_sha256"] == PENALTY_SHA, "Frozen penalty hash differs."
        )
        expected_counts = {
            "od": 3182,
            "dc": 3440,
            "dd": 18490,
            "oc": 592 if label.startswith("D") else 0,
        }
        r.require(
            {k: len(v) for k, v in cell["edges"].items()} == expected_counts,
            "Reviewed h215 graph counts differ.",
        )
        r.require(
            cell["estimate"]["period_count"] == 60
            and cell["estimate"]["scenario_count"] == (1 if mode == "det" else 9),
            "Reviewed period/scenario shape differs.",
        )
        if label.startswith("W"):
            actual, expected = cell["specification"].copy(), prior["experiment"].copy()
            actual.pop("workbook")
            expected.pop("workbook")
            r.require(actual == expected, "Historical W full configuration differs.")
            r.require(
                cell["contract"] == prior["mathematical_contract"],
                "Historical W graph/objective contract differs.",
            )
            r.require(
                cell["effective_probabilities"] == prior["effective_scenario_probabilities"],
                "Historical W scenario weights differ.",
            )
        cells[label] = cell
    for mode in old.MODES:
        comparisons[mode] = compare_pair(cells[f"W_{mode}"], cells[f"D_{mode}"])
    return cells, comparisons


def prepare(output, sha, *, workbook, population, order, audit, w_archive):
    output = Path(output).absolute()
    r.require(
        output.name == CLAIM and not output.exists() and not output.is_symlink(),
        "Fresh exclusive preparation directory required; preserve previous claims.",
    )
    paths = [old.regular(p) for p in (workbook, population, order, audit, w_archive)]
    before = [r.file_hash(p) for p in paths]
    r.require(before[0] == old.WORKBOOK_SHA, "Original h215 workbook checksum differs.")
    materialization = old.materialization(r.strict_json(paths[3].read_bytes()))
    selection = r.warehouses.read_policy(paths[1], paths[2], old.POPULATION_SHA, old.ORDER_SHA, 215)
    previous = historical_w(paths[4])
    inventory = source_inventory(ROOT)
    r.require(inventory["source_commit"] == sha, "Exact source commit differs.")
    r.require(
        {k: v for k, v in inventory["files"].items() if k.startswith("src/logic/")}
        == previous["scientific_sources"],
        "Scientific source differs from original W.",
    )
    r.r2.verify_source(inventory, ROOT)
    output.mkdir(mode=0o700)
    r.r2.write(output / "source.json", inventory)
    r.r2.write(output / "warehouse_selection.json", selection)
    try:
        cells, comparisons = inspect_comparison(paths[0], selection, previous)
        r.require(
            before == [r.file_hash(p) for p in paths], "Input/evidence drift during preparation."
        )
        r.r2.verify_source(inventory, ROOT)
        for label, cell in cells.items():
            r.r2.write(output / (label + ".json"), cell)
        artifact_sha256 = {p.name: r.file_hash(p) for p in sorted(output.iterdir())}
        plan = {
            "schema_version": "scalar-wd-h215-preparation-v1",
            "status": "input_comparability_qualified_execution_closed",
            "source_commit": sha,
            "artifact_sha256": artifact_sha256,
            "input_sha256": dict(
                zip(
                    ("workbook", "population", "order", "materialization", "historical_w_archive"),
                    before,
                    strict=True,
                )
            ),
            "historical_w": {k: v for k, v in previous.items() if k != "receipts"},
            "materialization": materialization,
            "new_cells_proposed": ["D_det", "D_sto"],
            "w_cells": "Input reconstruction only; no solve or W repetition.",
            "comparisons": comparisons,
            "resource_proposal": resource_proposal(),
            "required_next_decisions": [
                "new_D_resource_and_two_cell_design_approval",
                "complete_operational_package_qualification",
                "explicit_merge_and_pinned_human_execution",
            ],
            **closed(),
        }
        r.r2.write(output / "plan.json", plan)
        names = [p for p in sorted(output.iterdir()) if p.is_file()]
        r.r2.write(output / "inventory.json", {p.name: r.file_hash(p) for p in names})
        audit_preparation(output, sha, r.file_hash(output / "plan.json"))
    except Exception as exc:
        r.r2.write(
            output / "preparation_failure.json", {"error_kind": type(exc).__name__, **closed()}
        )
        raise
    return {"status": plan["status"], "plan_sha256": r.file_hash(output / "plan.json"), **closed()}


def audit_preparation(output, sha, plan_sha256):
    """Replay sealed preparation receipts, not fresh private-input validation."""
    output = Path(output)
    r.require(output.name == CLAIM and not output.is_symlink(), "Dedicated preparation directory.")
    expected = {
        "source.json",
        "warehouse_selection.json",
        "W_det.json",
        "D_det.json",
        "W_sto.json",
        "D_sto.json",
        "plan.json",
    }
    r.require(
        {p.name for p in output.iterdir()} == expected | {"inventory.json"},
        "Preparation incomplete or contains unexpected files.",
    )
    r.require(
        r.file_hash(old.regular(output / "plan.json")) == plan_sha256,
        "External preparation plan anchor differs.",
    )
    inventory = r.strict_json(old.regular(output / "inventory.json").read_bytes())
    r.require(set(inventory) == expected, "Preparation inventory scope differs.")
    r.require(
        all(r.file_hash(old.regular(output / n)) == digest for n, digest in inventory.items()),
        "Preparation artifact hash differs.",
    )
    plan = r.strict_json((output / "plan.json").read_bytes())
    r.require(
        plan["artifact_sha256"]
        == {n: digest for n, digest in inventory.items() if n != "plan.json"},
        "Plan-bound preparation artifacts differ.",
    )
    r.require(
        plan["schema_version"] == "scalar-wd-h215-preparation-v1"
        and plan["source_commit"] == sha
        and plan["new_cells_proposed"] == ["D_det", "D_sto"]
        and plan["resource_proposal"] == resource_proposal()
        and all(plan[k] is False for k in closed()),
        "Preparation scope/admission differs.",
    )
    for mode in old.MODES:
        cells = [
            r.strict_json((output / f"{topology}_{mode}.json").read_bytes())
            for topology in ("W", "D")
        ]
        r.require(compare_pair(*cells) == plan["comparisons"][mode], "Comparison replay differs.")
    return {
        "status": "preparation_receipts_replayed_execution_closed",
        "source_commit": sha,
        "plan_sha256": plan_sha256,
        "qualification": "Receipt integrity replay; no fresh private-input load or solve.",
        **closed(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("prepare", "audit", "proposal", "start", "batch", "worker", "repeat")
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--source-sha")
    parser.add_argument("--plan-sha256")
    for name in ("workbook", "population", "order", "audit", "w-archive"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args(argv)
    if args.action not in {"prepare", "audit", "proposal"}:
        parser.exit(2, "W_D_EXECUTION_CLOSED; NO_JOB_OR_REPEAT_ADMITTED\n")
    if args.action == "proposal":
        result = resource_proposal()
    elif args.action == "audit":
        r.require(
            args.output_dir is not None and args.source_sha and args.plan_sha256,
            "Output/source/external plan hash required.",
        )
        result = audit_preparation(args.output_dir, args.source_sha, args.plan_sha256)
    else:
        required = (
            args.output_dir,
            args.source_sha,
            args.workbook,
            args.population,
            args.order,
            args.audit,
            args.w_archive,
        )
        r.require(all(x is not None for x in required), "All input/source/output paths required.")
        result = prepare(
            args.output_dir,
            args.source_sha,
            workbook=args.workbook,
            population=args.population,
            order=args.order,
            audit=args.audit,
            w_archive=args.w_archive,
        )
    print(r.r2.encoded(result).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
