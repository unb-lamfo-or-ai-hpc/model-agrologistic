"""Closed h400 profile/input qualification, not a scheduler or native worker.

The public CLI can describe, prepare, check and package a proposal only. Neither
this package nor any receipt can admit a job, a repeat or the conditional h500.
Historical scientific/validation modules and execution certificates stay intact.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import re
import sys
import tarfile
from dataclasses import asdict
from pathlib import Path

from scripts import mvp2_s2_allocation_diagnostic as source
from scripts import mvp2_s2_h300_products as products
from scripts import mvp2_s2_h300_runtime as input_tools
from src.logic.model_config import SolverConfig

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "h400-post-s2-proposal-v1"
S2_MERGE = "5f9daa55b3afb5bbcb3449bc83c970cf10a28ca6"
ANCHORS = {
    "docs/mvp2_h400_input_policy.json": (
        "629d7bc66bf548df12e4145c19c2d2a97445cd31699716b07dac627bcef94a7e"
    ),
    "docs/mvp2_h400_control_review_2200384.json": (
        "128cc72e1210d239b038ccd991d19485c0898ad4d3ce07b8463a3383b7603636"
    ),
    "docs/evidence/s2_p5_2215308_review.json": (
        "7efc05da849b502a32ecfae501e8704acc4c78437c5e287fe0ab47ea48770e8e"
    ),
}
FLAGS = {
    "h400_execution_admitted": False,
    "repeats_admitted": False,
    "h500_execution_admitted": False,
    "automatic_follow_on_allowed": False,
    "production_isolation_certified": False,
}
OBLIGATIONS = [
    "qualified_exact_source_and_scientific_byte_parity",
    "fresh_private_input_runtime_and_native_parameter_checks",
    "fresh_allocation_finite_memory_affinity_and_license_capability",
    "exclusive_new_claim_and_single_owned_numeric_step",
    "bounded_phases_targeted_stop_and_terminal_partial_collection",
    "preserved_worker_and_fresh_independent_reports_and_equivalence_witness",
    "unchanged_original_full_hierarchy_and_feasibility_certification",
    "complete_linux_operational_wrapper_qualification_and_human_admission",
]
require = input_tools.d.require


def solver_profile():
    """Inherit the accepted S1 eight-hour global budget, not the S2 one-hour window."""
    return SolverConfig(
        backend="gurobipy",
        solver_name="gurobi",
        threads=4,
        seed=42,
        time_limit=28800,
        mip_gap=0.1,
        compact_python_indices=False,
        compute_iis=False,
        solver_options={"SoftMemLimit": 128, "NumericFocus": 1},
        multiobjective_stage_options={role: {"Method": 2} for role in input_tools.d.ROLES},
        collect_solver_diagnostics=True,
        collect_resource_diagnostics=True,
        resource_sample_seconds=5.0,
        resource_max_samples=8192,
    )


def proposal():
    """Fixed candidate and prospective external budgets; no execution authority."""
    return {
        "schema_version": SCHEMA,
        "status": "candidate_qualified_in_software_execution_closed",
        "s2_documentary_merge": S2_MERGE,
        "basis": dict(ANCHORS),
        "case": "h400-direct",
        "solver": asdict(solver_profile()),
        "allocation_proposal": {
            "partition": "intel-256",
            "nodes": 1,
            "tasks": 1,
            "logical_cpus": 16,
            "memory_mib": 196608,
            "walltime_seconds": 43200,
            "exclusive_node_required": False,
        },
        "budget_proposal": {
            "fresh_admission_seconds": 600,
            "build_seconds": 1800,
            "global_native_seconds": 28800,
            "shared_late_return_and_export_seconds": 900,
            "cleanup_seconds": 300,
            "worker_hard_seconds": 32400,
            "independent_review_seconds": 1800,
            "stop_and_collection_reserve_seconds": 300,
            "minimum_wall_seconds": 35100,
        },
        "runtime_required": {"python": "3.13.15", "gurobipy": "13.0.3"},
        "variable_guard": 42426624,
        "transfer_proposal": {
            "expanded_bytes": 256 * 1024**2,
            "oversize_disposition": "preserved_export_failure_never_truncate",
        },
        "selection": "four_threads_conservative_candidate_not_proven_winner",
        "acceptance_policy": {
            "full_success_requires": [
                "original_independent_feasibility_accepted",
                "all_three_original_priority_certificates_accepted",
                "closed_source_input_runtime_resource_and_terminal_evidence",
                "declared_native_and_external_budgets_respected",
                "independent_human_evidence_review",
            ],
            "partial_negative_records": [
                "feasible_partial_hierarchy",
                "no_incumbent_not_infeasibility",
                "build_failure",
                "export_failure",
                "validation_rejected",
                "scheduler_or_resource_failure",
                "unknown_effect_preserved",
            ],
            "zero_service_gap_sentinel": "retain_raw_and_original_certification_no_prefix_patch",
            "h400_success_necessary_not_sufficient_for_h500_admission": True,
        },
        "pending_obligations": list(OBLIGATIONS),
        **FLAGS,
    }


def evidence_basis():
    """Check pinned public documentary anchors, not fresh private residuals."""
    for name, digest in ANCHORS.items():
        require(products.sha_file(ROOT / name) == digest, "Public evidence anchor drift.")
    s1 = products.read(ROOT / "docs/mvp2_h400_control_review_2200384.json")
    s2 = products.read(ROOT / "docs/evidence/s2_p5_2215308_review.json")
    require(
        s1["job_id"] == "2200384"
        and s1["status"] == "accepted"
        and s1["summary"]["lexicographic_completed_stage_count"] == 3
        and s2["execution"]["five_arm_evidence_accounted"] is True
        and s2["p5_exit_assessment"]["inconclusive_general_thread_ranking"] is True,
        "Accepted basis unavailable; no inferred h400 selection.",
    )
    return {"s1_job": s1["job_id"], "s2_job": s2["execution"]["job_id"]}


def fresh_input(reference):
    """Real Excel/ExperimentSpec integration without importing or constructing a solver."""
    from src.logic.excel_loader import load_model_data_from_excel
    from src.logic.experiment_runner import (
        _data_signature,
        estimate_model_size,
        load_experiment_manifest,
    )
    from src.logic.mathematical_contract import prepare_model_data
    from src.logic.run_integrity import scientific_identity

    policy = products.read(ROOT / "docs/mvp2_h400_input_policy.json")
    require(
        products.sha_file(reference) == policy["reference_manifest_sha256"],
        "Reference manifest drift.",
    )
    manifest = load_experiment_manifest(reference)
    matches = [
        s
        for s in manifest.experiments
        if s.metadata.get("warehouse_population") == 400
        and s.model.mode == "sto"
        and s.model.objective_policy == "lexicographic"
        and s.model.use_direct_origin_customer is True
    ]
    require(len(matches) == 1, "Expected exactly one h400 direct reference.")
    spec = matches[0]
    require(
        spec.calculate_evpi_vss is False
        and spec.resume_evpi_vss is False
        and spec.max_estimated_variables == policy["reference_limit"]
        and spec.loader.include_transshipment_routes is True,
        "Scientific flags/guard drift.",
    )
    require(
        spec.loader.include_direct_origin_customer_routes is True,
        "Direct routes must be loaded, not just enabled in the model.",
    )
    expected, observed = asdict(solver_profile()), asdict(spec.solver)
    # Diagnostics and verbosity are observational; scientific options stay exact.
    for field in (
        "backend",
        "solver_name",
        "threads",
        "seed",
        "time_limit",
        "mip_gap",
        "compact_python_indices",
        "compute_iis",
        "solver_options",
    ):
        require(
            type(observed[field]) is type(expected[field]) and observed[field] == expected[field],
            "Scientific solver profile drift.",
        )
    require(
        observed["multiobjective_stage_options"] in ({}, expected["multiobjective_stage_options"]),
        "Per-priority method/time drift.",
    )
    require(products.sha_file(spec.workbook) == policy["workbook_sha256"], "Workbook drift.")
    data = prepare_model_data(load_model_data_from_excel(spec.workbook, spec.loader), spec.model)
    counts = _data_signature(data)["counts"]
    estimate = asdict(estimate_model_size(data, spec.model))
    require(
        all(counts[k] == v for k, v in policy["counts"].items())
        and all(estimate[k] == v for k, v in policy["snapshot_fields"].items()),
        "Fresh h400 dimension/route drift.",
    )
    # Same qualified metadata-only NaN tagging as S2; no numeric imputation.
    view = input_tools._identity_view(data)
    return {
        "reference_sha256": policy["reference_manifest_sha256"],
        "workbook_sha256": policy["workbook_sha256"],
        "data_sha256": scientific_identity(view),
        "config_sha256": scientific_identity(spec.model),
        "loader_sha256": scientific_identity(spec.loader),
        "counts": {k: counts[k] for k in policy["counts"]},
        "size": {k: estimate[k] for k in policy["snapshot_fields"]},
        "private_paths_published": False,
    }


def validate_plan(plan):
    evidence_basis()
    require(
        set(plan)
        == {"schema_version", "source_commit", "source_files", "proposal", "input", "plan_scope"},
        "Plan schema drift.",
    )
    require(
        plan["schema_version"] == "h400-post-s2-plan-v1"
        and b"".join(products.chunks(plan["proposal"])) == b"".join(products.chunks(proposal()))
        and plan["plan_scope"] == "software_preparation_not_live_admission",
        "Closed proposal drift.",
    )
    require(
        isinstance(plan["source_commit"], str)
        and re.fullmatch(r"[0-9a-f]{40}", plan["source_commit"]),
        "Full source required.",
    )
    files = plan["source_files"]
    require(
        isinstance(files, dict)
        and files
        and all(
            isinstance(k, str)
            and k
            and "\\" not in k
            and ":" not in k
            and not k.startswith("/")
            and ".." not in k.split("/")
            and isinstance(v, str)
            and re.fullmatch(r"[0-9a-f]{64}", v)
            for k, v in files.items()
        ),
        "Source inventory grammar.",
    )
    identity = plan["input"]
    require(
        set(identity)
        == {
            "reference_sha256",
            "workbook_sha256",
            "data_sha256",
            "config_sha256",
            "loader_sha256",
            "counts",
            "size",
            "private_paths_published",
        },
        "Input identity schema.",
    )
    policy = products.read(ROOT / "docs/mvp2_h400_input_policy.json")
    require(
        b"".join(products.chunks(identity["counts"])) == b"".join(products.chunks(policy["counts"]))
        and b"".join(products.chunks(identity["size"]))
        == b"".join(products.chunks(policy["snapshot_fields"]))
        and identity["private_paths_published"] is False,
        "Input identity dimensions/scope drift.",
    )
    for field in (
        "reference_sha256",
        "workbook_sha256",
        "data_sha256",
        "config_sha256",
        "loader_sha256",
    ):
        require(
            isinstance(identity[field], str) and re.fullmatch(r"[0-9a-f]{64}", identity[field]),
            "Input hash grammar.",
        )
    require(
        identity["reference_sha256"] == policy["reference_manifest_sha256"]
        and identity["workbook_sha256"] == policy["workbook_sha256"],
        "Input anchor drift.",
    )
    return plan


def prepare(commit, reference, destination):
    """New local proposal only; no claim, scheduler lookup, license or optimization."""
    evidence_basis()
    files = source.source_files(ROOT, commit)
    identity = fresh_input(reference)
    require(source.source_files(ROOT, commit) == files, "Source changed during input load.")
    plan = validate_plan(
        {
            "schema_version": "h400-post-s2-plan-v1",
            "source_commit": commit,
            "source_files": files,
            "proposal": proposal(),
            "input": identity,
            "plan_scope": "software_preparation_not_live_admission",
        }
    )
    target = products.safe(destination)
    require(
        not target.exists() and not target.is_relative_to(ROOT) and not ROOT.is_relative_to(target),
        "New isolated output outside source required.",
    )
    target.mkdir()
    products.publish(target / "plan.json", plan)
    return plan


def pack(plan_path, destination):
    """Metadata proposal carrier, NOT a live/terminal HPC evidence archive."""
    plan = validate_plan(products.read(plan_path))
    raw = b"".join(products.chunks(plan))
    target = products.safe(destination)
    require(not target.exists(), "Existing carrier must be preserved.")
    with target.open("xb") as output:
        with tarfile.open(fileobj=output, mode="w:gz", format=tarfile.USTAR_FORMAT) as stream:
            member = tarfile.TarInfo("plan.json")
            member.size, member.mode = len(raw), 0o600
            stream.addfile(member, io.BytesIO(raw))
    return products.sha_file(target)


def audit(path, checksum):
    """Bounded regular metadata, no extraction and no inferred scientific acceptance."""
    path = products.safe(path)
    require(
        path.stat().st_size <= products.METADATA and products.sha_file(path) == checksum,
        "Carrier hash/size drift.",
    )
    with gzip.open(path, "rb") as compressed:
        expanded = compressed.read(products.METADATA + 1)
    require(len(expanded) <= products.METADATA, "Expanded carrier bound.")
    with tarfile.open(fileobj=io.BytesIO(expanded), mode="r:") as stream:
        member = stream.next()
        require(
            member is not None
            and member.name == "plan.json"
            and member.isfile()
            and not member.pax_headers
            and 0 < member.size <= products.METADATA,
            "Carrier member scope.",
        )
        raw = stream.extractfile(member).read(products.METADATA + 1)
        require(len(raw) == member.size and stream.next() is None, "Carrier size/inventory.")
    plan = validate_plan(input_tools.c.decode_json(raw))
    require(raw == b"".join(products.chunks(plan)), "Noncanonical proposal bytes.")
    canonical = io.BytesIO()
    with tarfile.open(fileobj=canonical, mode="w", format=tarfile.USTAR_FORMAT) as stream:
        member = tarfile.TarInfo("plan.json")
        member.size, member.mode = len(raw), 0o600
        stream.addfile(member, io.BytesIO(raw))
    require(expanded == canonical.getvalue(), "Noncanonical tar/trailing payload.")
    return {
        "status": "proposal_integrity_replayed_not_live_qualified",
        "plan_sha256": hashlib.sha256(raw).hexdigest(),
        "source_commit": plan["source_commit"],
        **FLAGS,
    }


def execute(*_args, **_kwargs):
    raise PermissionError("H400 operational admission incomplete; all jobs/repeats remain closed.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "describe",
            "prepare",
            "check",
            "pack",
            "audit",
            "start",
            "batch",
            "worker",
            "resume",
        ),
    )
    parser.add_argument("--source")
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--sha256")
    args = parser.parse_args(argv)
    if args.action in {"start", "batch", "worker", "resume"}:
        execute()
    if args.action == "describe":
        evidence_basis()
        value = proposal()
    elif args.action == "prepare":
        require(all((args.source, args.reference, args.output)), "Preparation arguments required.")
        value = prepare(args.source, args.reference, args.output)
    elif args.action == "check":
        require(args.plan is not None, "Plan required.")
        value = validate_plan(products.read(args.plan))
    elif args.action == "pack":
        require(args.plan is not None and args.output is not None, "Packaging arguments required.")
        value = {"sha256": pack(args.plan, args.output), **FLAGS}
    else:
        require(args.archive is not None and args.sha256, "Archive/anchor required.")
        value = audit(args.archive, args.sha256)
    sys.stdout.write(b"".join(products.chunks(value)).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
