"""Prepare, but never submit, a hash-bound Gurobi index-compaction contrast."""

from __future__ import annotations

import argparse
import copy
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.logic.experiment_runner import load_experiment_manifest  # noqa: E402
from src.logic.run_integrity import file_sha256, implementation_identity  # noqa: E402

CASES = {"h215-warehouse": (215, False), "h300-warehouse": (300, False), "h400-direct": (400, True)}
STAGES = ("unmet_demand", "emergency_capacity", "economic_cost")
REQUIRED_TESTS = {
    "test_reuse_rebuild_priority_lock_parity[gurobipy]",
    "test_licensed_gurobi_native_explicit_parity",
    "test_licensed_gurobi_compaction_parity",
    *(
        f"test_licensed_gurobi_multiobjective_factory_returns_to_single_objective[{count}-{mode}]"
        for count in (1, 3)
        for mode in ("reuse", "rebuild")
    ),
}


def verify_qualification(path):
    """Require closed, licensed miniature evidence for the current core/runtime."""
    path = Path(path).resolve()
    report = json.loads(path.read_text(encoding="utf-8"))
    if (
        report.get("schema_version") != "mvp2-resource-qualification-v1"
        or report.get("status") != "accepted"
        or report.get("scope") != "analytical_and_licensed_parity"
        or report.get("implementation_unchanged") is not True
        or report.get("skipped_tests") != 0
        or report.get("implementation") != implementation_identity()
    ):
        raise ValueError("Current, unchanged, licensed qualification is required.")
    steps = report.get("steps", [])
    if steps != [{"name": "ruff", "return_code": 0}, {"name": "pytest", "return_code": 0}]:
        raise ValueError("Qualification quality steps are incomplete.")
    artifacts = report.get("artifacts", {})
    if not {"pytest.xml", "pytest.log", "ruff.log"}.issubset(artifacts):
        raise ValueError("Qualification artifacts are incomplete.")
    for name, digest in artifacts.items():
        asset = (path.parent / name).resolve()
        if not asset.is_relative_to(path.parent) or file_sha256(asset) != digest:
            raise ValueError("Qualification artifact integrity mismatch.")
    cases = list(ET.parse(path.parent / "pytest.xml").getroot().iter("testcase"))
    names = [case.get("name") for case in cases]
    if (
        any(names.count(name) != 1 for name in REQUIRED_TESTS)
        or len(cases) != report.get("test_count")
        or any(
            case.find(tag) is not None for case in cases for tag in ("skipped", "failure", "error")
        )
    ):
        raise ValueError("Licensed objective-mode and compaction regressions must execute.")
    measurements = report.get("overhead_measurements", [])
    expected = {
        (backend, repeat, sampled)
        for backend in ("gurobipy", "pyscipopt")
        for repeat in range(3)
        for sampled in (False, True)
    }
    observed = [(row["backend"], row["repeat"], row["instrumented"]) for row in measurements]
    if len(observed) != len(expected) or set(observed) != expected or any(
        row.get("status") != "optimal" or row.get("independent_validation") != "accepted"
        for row in measurements
    ):
        raise ValueError("Validated miniature overhead pairs are incomplete.")
    return report


def prepare(reference, reference_sha256, index, qualification, destination, case):
    reference, qualification, destination = (
        Path(value).resolve() for value in (reference, qualification, destination)
    )
    if destination.exists():
        raise FileExistsError(destination)
    if any(destination.is_relative_to(p.parent) for p in (reference, qualification)):
        raise ValueError("The new pair must be outside reference and qualification directories.")
    if file_sha256(reference) != reference_sha256:
        raise ValueError("Reviewed reference manifest checksum mismatch.")
    qualified = verify_qualification(qualification)
    manifest = load_experiment_manifest(reference)
    if type(index) is not int or not 0 <= index < len(manifest.experiments):
        raise ValueError("Select one explicit reference index.")
    spec = manifest.experiments[index]
    population, direct = CASES[case]
    if (
        spec.model.mode != "sto"
        or spec.model.objective_policy != "lexicographic"
        or spec.model.use_direct_origin_customer != direct
        or spec.metadata.get("warehouse_population") != population
        or spec.calculate_evpi_vss
        or spec.resume_evpi_vss
        or spec.loader.scenario_generation_mode != "cartesian"
        or len(spec.loader.stochastic_supply_levels) != 3
        or len(spec.loader.stochastic_demand_levels) != 3
        or len(set(spec.loader.stochastic_supply_levels)) != 3
        or len(set(spec.loader.stochastic_demand_levels)) != 3
        or spec.model.pareto_fraction != 0.2
        or spec.model.route_filter_strategy != "connectivity_preserving_pareto"
        or not spec.model.interhub_strong_connectivity
    ):
        raise ValueError("The selected case must retain the nine-scenario connectivity contract.")
    solver = spec.solver
    if (
        solver.backend != "gurobipy"
        or solver.solver_name != "gurobi"
        or solver.threads != 4
        or solver.seed != 42
        or solver.time_limit != 28800
        or solver.mip_gap != 0.1
        or solver.solver_options != {"SoftMemLimit": 128, "NumericFocus": 1}
        or solver.multiobjective_stage_options not in ({}, {r: {"Method": 2} for r in STAGES})
        or solver.compact_python_indices
    ):
        raise ValueError("The matched reference requires the reviewed fixed resource profile.")
    workbook_digest = file_sha256(spec.workbook)
    arms = []
    for arm, compact in (("control", False), ("compact", True)):
        item = asdict(spec)
        item["workbook"] = str(spec.workbook.resolve())
        item["name"] = f"mvp2_{case.replace('-', '_')}_{arm}"
        item["solver"].update(
            collect_resource_diagnostics=True,
            resource_sample_seconds=5.0,
            resource_max_samples=8192,
            collect_solver_diagnostics=True,
            compact_python_indices=compact,
            multiobjective_stage_options={role: {"Method": 2} for role in STAGES},
        )
        item["metadata"] = copy.deepcopy(spec.metadata)
        item["metadata"].update(
            resource_contrast_arm=arm,
            reference_manifest_sha256=reference_sha256,
            reference_workbook_sha256=workbook_digest,
            resource_contrast_scope="post_build_python_indices_only",
        )
        arms.append(item)
    document = {
        "version": 1,
        "output_dir": str(destination / "runs"),
        "continue_on_error": True,
        "experiments": arms,
    }
    destination.mkdir(parents=True, exist_ok=False)
    target = destination / "campaign.yaml"
    target.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8", newline="\n")
    # Check the production parser, without loading or solving workbook data.
    load_experiment_manifest(target)
    receipt = {
        "schema_version": "mvp2-resource-contrast-plan-v1",
        "status": "prepared_not_admitted",
        "case": case,
        "reference_manifest": str(reference),
        "reference_manifest_sha256": reference_sha256,
        "reference_index": index,
        "workbook_sha256": workbook_digest,
        "qualification_report": str(qualification),
        "qualification_report_sha256": file_sha256(qualification),
        "qualified_source_commit": qualified.get("source_commit"),
        "implementation": implementation_identity(),
        "preparer_sha256": file_sha256(Path(__file__)),
        "campaign_sha256": file_sha256(target),
        "contrast": "compact_python_indices",
        "common_changes": "all-barrier and bounded telemetry in both arms",
        "large_instance_submission_allowed": False,
        "production_explicit_lifecycle_allowed": False,
        "next_gate": "Review preflight, scheduler allocation and pair admission before submission.",
    }
    (destination / "resource_contrast_plan.json").write_text(
        json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-manifest", type=Path, required=True)
    parser.add_argument("--reference-sha256", required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--qualification-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--case", choices=CASES, required=True)
    args = parser.parse_args()
    print(
        prepare(
            args.reference_manifest, args.reference_sha256, args.index,
            args.qualification_report, args.output_dir, args.case,
        )
    )
    print("MVP2 RESOURCE PAIR: PREPARED; LARGE SUBMISSION REMAINS CLOSED")


if __name__ == "__main__":
    main()
