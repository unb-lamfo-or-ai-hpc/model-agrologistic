"""Read-only v2 input preflight and case catalog; never admit execution."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.logic.mvp3_preparation import case_catalog, read_protocol  # noqa: E402

BUNDLE_FILES = {
    "arcs.csv",
    "configs.json",
    "metadata.json",
    "nodes.json",
    "parameters.csv",
    "sets.csv",
    "sources.json",
}


def stable_hash(path, *, max_bytes=128 * 1024**2):
    """Refuse symlinks, special files, size overruns and observed live changes."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError("A regular immutable input file is required.")
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
            raise ValueError("Input type or read budget differs.")
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
        after = os.fstat(stream.fileno())
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise ValueError("Input changed during inspection.")
    return digest


def inspect_inputs(baseline, registry, bundle):
    """Metadata and file identities only; no registry-site audit or model build."""
    import openpyxl

    protocol = read_protocol()
    receipts = {}
    for role, path in (("baseline", baseline), ("registry", registry)):
        pin = protocol["workbooks"][role]
        digest = stable_hash(path)
        if digest != pin["sha256"]:
            raise ValueError("The frozen v2 workbook identity differs: " + role)
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            ident = dict(list(wb["Identification"].values)[1:])
            if (
                ident.get("workbook_version") != 2
                or ident.get("presentation_schema") != pin["presentation_schema"]
            ):
                raise ValueError("Workbook edition or presentation schema differs.")
            if role == "baseline":
                if ident.get("schema") != protocol["computational_schema"]:
                    raise ValueError("Computational schema differs.")
                controls = {r[0]: r[1] for r in list(wb["Controls"].values)[1:]}
                if (
                    controls["K"] != 1
                    or controls["beta_enabled"] != 0
                    or controls["alpha_enabled"] != 0
                    or controls["beta"] is not None
                    or controls["alpha"] is not None
                ):
                    raise ValueError("The frozen reference must remain neutral.")
        finally:
            wb.close()
        receipts[role] = {
            "sha256": digest,
            "workbook_version": 2,
            "presentation_schema": pin["presentation_schema"],
        }
    bundle = Path(bundle)
    manifest_path = bundle / "manifest.json"
    manifest_digest = stable_hash(manifest_path, max_bytes=1024**2)
    if manifest_digest != protocol["normalized_manifest_sha256"]:
        raise ValueError("The frozen normalized manifest identity differs.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["schema"] != protocol["computational_schema"]:
        raise ValueError("Normalized schema differs.")
    if set(manifest["files"]) != BUNDLE_FILES:
        raise ValueError("Normalized bundle file set differs.")
    if (
        manifest["source_identities"]["effective_workbook"]["sha256"]
        != receipts["baseline"]["sha256"]
    ):
        raise ValueError("CSV export is not bound to the approved v2 baseline.")
    for name, digest in manifest["files"].items():
        if stable_hash(bundle / name) != digest:
            raise ValueError("Normalized file identity differs: " + name)
    for mode, digest in protocol["h215_input_identities"].items():
        if manifest["cases"].get("215:" + mode) != digest:
            raise ValueError("The h215 effective coefficient identity differs.")
    if stable_hash(manifest_path, max_bytes=1024**2) != manifest_digest:
        raise ValueError("Normalized manifest changed during inspection.")
    return {
        "workbooks": receipts,
        "normalized_manifest_sha256": manifest_digest,
        "normalized_files_verified": len(BUNDLE_FILES),
        "h215_input_identities": protocol["h215_input_identities"],
    }


def preparation_report(inputs=None):
    protocol = read_protocol()
    cases = case_catalog()
    try:
        installed = importlib.metadata.version("gurobipy")
    except importlib.metadata.PackageNotFoundError:
        installed = None
    return {
        "status": protocol["status"],
        "develop_plan_changed": False,
        "plan_revision_in_draft_pr": protocol["plan_revision_in_draft_pr"],
        "new_jobs": 0,
        "execution_authorized": False,
        "implementation": protocol["implementation"],
        "expected_gurobi": protocol["gurobi_version"],
        "installed_distribution": installed,
        "native_engine_or_license_tested": False,
        "native_policy_integration_qualified": False,
        "h215_primary_cases": sum(c["population"] == 215 and c["repetition"] == 1 for c in cases),
        "h215_additional_repetitions": sum(
            c["population"] == 215 and c["repetition"] > 1 for c in cases
        ),
        "later_population_primary_cases": sum(c["population"] > 215 for c in cases),
        "budget_at_three_repetitions": {
            "observations": len(cases) * 3,
            "native_limit_hours": len(cases) * 3 * protocol["native_options"]["TimeLimit"] / 3600,
            "allocation_limit_hours": len(cases)
            * 3
            * protocol["resources"]["max_job_wall_seconds"]
            / 3600,
            "memory_gib": protocol["resources"]["memory_gib"],
            "scope": "Optional budget scenario only; further repetitions not fixed or authorized",
        },
        "inputs": inputs,
        "pending_admission_gates": protocol["required_admission_gates"],
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--bundle", type=Path)
    args = parser.parse_args()
    paths = (args.baseline, args.registry, args.bundle)
    if any(paths) and not all(paths):
        parser.error("Baseline, registry and normalized bundle must be supplied together.")
    inputs = inspect_inputs(*paths) if all(paths) else None
    print(json.dumps(preparation_report(inputs), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
