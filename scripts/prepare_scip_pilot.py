"""Admit one qualified 215-hub SCIP pilot without rewriting qualification evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.prepare_nine_scenario_campaign import campaign  # noqa: E402
from src.logic.run_integrity import file_sha256, implementation_identity  # noqa: E402

REQUIRED_ARTIFACTS = {
    "runtime.json", "native_build.log", "dependencies.log", "pytest.log", "pytest.xml", "ruff.log",
}
VARIABLE_LIMIT = 16_000_000


def verify_qualification(directory, identity):
    """Bind accepted licensed tests, native build and current numerical sources."""
    directory = directory.resolve()
    report = json.loads((directory / "qualification_report.json").read_text(encoding="utf-8"))
    if not (
        report.get("schema_version") == "scip-backend-qualification-v1"
        and report.get("status") == "accepted"
        and report.get("scope") == "analytical_and_licensed_parity"
        and report.get("implementation_unchanged") is True
        and report.get("skipped_tests") == 0
        and report.get("test_count", 0) >= 42
        and report.get("implementation_identity") == identity
        and {s["name"] for s in report.get("steps", [])}
        == {"ruff", "native_build", "dependencies", "pytest"}
        and all(s["return_code"] == 0 for s in report["steps"])
    ):
        raise ValueError("Current implementation requires accepted, unskipped licensed parity.")
    if set(report.get("artifacts", {})) != REQUIRED_ARTIFACTS:
        raise ValueError("Incomplete qualification artifact contract.")
    for name, digest in report["artifacts"].items():
        if file_sha256(directory / name) != digest:
            raise ValueError(f"Qualification artifact changed: {name}")
    runtime = json.loads((directory / "runtime.json").read_text(encoding="utf-8"))
    if not (
        runtime.get("status") == "runtime_available"
        and runtime.get("platform") == "Linux"
        and runtime.get("machine") == "x86_64"
        and runtime.get("user_site_disabled") is True
        and runtime.get("pyscipopt_version") == "6.2.1"
        and runtime.get("scip_version") == "10.0.2"
    ):
        raise ValueError("This pilot requires the reviewed Linux SCIP 10.0.2 runtime.")
    banner = (directory / "native_build.log").read_text(encoding="utf-8")
    if not all(token in banner for token in (
        "SCIP version 10.0.2", "precision: 8 byte", "LP solver: SoPlex 8.0.2",
    )):
        raise ValueError("The native build does not match the reviewed SCIP/SoPlex stack.")
    return file_sha256(directory / "qualification_report.json")


def pilot_document(workbook, destination, qualification_hash):
    """Preserve the policy mathematics; replace solver settings, not their names."""
    document = campaign(ROOT, destination / "runs", (215,), {215: workbook},
                        max_estimated_variables=VARIABLE_LIMIT)
    document["continue_on_error"] = False
    document["defaults"]["solver"] = {
        "backend": "pyscipopt", "solver_name": "scip", "mip_gap": 0.1,
        "time_limit": 28800, "threads": 4, "seed": 42, "tee": True,
        "compute_iis": False, "solver_options": {"limits/memory": 131072},
        "log_file": str(destination / "scip.log"),
    }
    document["experiments"] = document["experiments"][:1]
    run = document["experiments"][0]
    run["name"] = "nine_h215_p20_warehouse_scip_pilot"
    run["metadata"].update(
        backend_qualification="Analytical and licensed parity accepted; population pilot only",
        qualification_report_sha256=qualification_hash,
        lp_backend="SoPlex 8.0.2", solve_driver="sequential_optimize",
        resource_qualification="First 215-hub pilot; no memory/convergence guarantee",
    )
    return document


def prepare(destination, workbook, qualification):
    identity = implementation_identity()
    qualification_hash = verify_qualification(qualification, identity)
    if workbook.suffix.lower() != ".xlsx" or not workbook.is_file():
        raise ValueError("Supply the existing OSRM-materialized workbook.")
    document = pilot_document(workbook, destination, qualification_hash)
    destination.mkdir(parents=True, exist_ok=False)
    manifest = destination / "campaign.yaml"
    manifest.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    receipt = {
        "schema_version": "scip-215-pilot-admission-v1",
        "scope": "one_215_hub_warehouse_only_pilot",
        "qualification_directory": str(qualification),
        "qualification_report_sha256": qualification_hash,
        "implementation_identity": identity,
        "workbook": str(workbook), "workbook_sha256": file_sha256(workbook),
        "manifest_sha256": file_sha256(manifest),
        "helper_sha256": file_sha256(Path(__file__)),
        "worker_sha256": file_sha256(ROOT / "scripts/run_scip_pilot.slurm"),
        "lp_backend_review": "SCIP 10.0.2 / SoPlex 8.0.2 / 8-byte precision",
        "scheduler_memory_mib": 196608, "scheduler_cpus": 4,
        "scheduler_wall_seconds": 43200, "scip_memory_limit_mb": 131072,
        "optimization_budget_seconds": 28800,
        "larger_populations_admitted": False,
        "preflight_required": True,
    }
    (destination / "pilot_admission.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return manifest


def check(manifest, *, preflight=False):
    destination = manifest.parent
    receipt = json.loads((destination / "pilot_admission.json").read_text(encoding="utf-8"))
    identity = implementation_identity()
    qualification_hash = verify_qualification(Path(receipt["qualification_directory"]), identity)
    workbook = Path(receipt["workbook"])
    document = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    if not (
        receipt["implementation_identity"] == identity
        and receipt["qualification_report_sha256"] == qualification_hash
        and receipt["workbook_sha256"] == file_sha256(workbook)
        and receipt["manifest_sha256"] == file_sha256(manifest)
        and receipt["helper_sha256"] == file_sha256(Path(__file__))
        and receipt["worker_sha256"] == file_sha256(ROOT / "scripts/run_scip_pilot.slurm")
        and document == pilot_document(workbook, destination, qualification_hash)
    ):
        raise ValueError("Pilot source, environment, input or configuration changed.")
    if preflight:
        run = destination / "runs" / document["experiments"][0]["name"]
        validate_preflight(json.loads((run / "preflight.json").read_text()), receipt)
    print("SCIP PILOT INPUT CONTRACT: ACCEPTED")


def validate_preflight(payload, receipt):
    """The shared estimate excludes SCIP-internal indicator/transformation overhead."""
    if not (
        payload["workbook_sha256"] == receipt["workbook_sha256"]
        and payload["data_signature"]["counts"]["warehouses"] == 215
        and payload["scenario_count"] == 9
        and payload["period_count"] == 60
        and payload["routes_oc"] == 0
        and 0 < payload["total_variables"] <= VARIABLE_LIMIT
    ):
        raise ValueError("Preflight is outside the reviewed 215-hub, nine-scenario pilot.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-root", type=Path)
    parser.add_argument("--workbook", type=Path)
    parser.add_argument("--qualification-dir", type=Path)
    parser.add_argument("--check-manifest", type=Path)
    parser.add_argument("--check-preflight", action="store_true")
    args = parser.parse_args()
    if args.check_manifest:
        check(args.check_manifest.resolve(), preflight=args.check_preflight)
    else:
        if not all((args.campaign_root, args.workbook, args.qualification_dir)):
            parser.error("Preparation requires campaign-root, workbook and qualification-dir.")
        print(prepare(args.campaign_root.resolve(), args.workbook.resolve(),
                      args.qualification_dir.resolve()))


if __name__ == "__main__":
    main()
