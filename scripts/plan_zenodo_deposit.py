"""Create an unapproved, per-file Zenodo curation plan from an existing inventory."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
KNOWN_INVALID_500 = "6fa1a28514b920f24e321a484a279d39158a3cb1946be903c783b636621c07eb"


def classify(path, digest, original_status):
    """A category is a review recommendation, never publication authorization."""
    parts = PurePosixPath(path).parts
    if (original_status.startswith("excluded") or any(
            p.lower() in {"secrets", ".git", "credentials", "tokens"}
            or p.lower().startswith(".env") for p in parts)
            or PurePosixPath(path).suffix.lower() in {".lic", ".pem", ".key"}):
        return "excluded", "sensitive_or_link"
    if digest == KNOWN_INVALID_500:
        return "invalid_input_evidence", "blocked_for_validated_input_publication"
    if any(p in {"__pycache__", ".pytest_cache", ".ruff_cache", "dist"}
           or p.endswith(".egg-info") for p in parts):
        return "excluded", "regenerable_software_artifact"
    if path.startswith(("templates/", "raw/", "manifests/")):
        return "canonical_inputs", "review_origin_and_redistribution_rights"
    if path.startswith("processed/"):
        if "before_" in path or "/solver_v020/" in path:
            return "research_history", "superseded_input_requires_version_label"
        return "processed_inputs", "validate_transformations_and_source_hashes"
    if path.startswith("results/validation/"):
        return "validation_evidence", "select_authoritative_runs_and_label_failures"
    if path.startswith("results/reproducibility/"):
        return "publication_outputs", "reconcile_with_manuscript_and_selected_runs"
    if path.startswith("results/releases/"):
        return "historical_release", "retain_complete_release_hash_contract"
    if path.startswith("results/hpc/nine-connectivity-"):
        return "campaign_in_progress", "not_a_completed_experimental_release"
    if path.startswith("results/hpc/"):
        return "research_history", "classify_run_identity_acceptance_and_failure_reason"
    return "documentation_or_other", "manual_content_review"


def build_plan(inventory, source_contract):
    seen, rows, hashes = set(), [], Counter()
    for item in inventory["files"]:
        path = item["path"]
        p = PurePosixPath(path)
        if (p.is_absolute() or ".." in p.parts or "\\" in path or ":" in path
                or not p.parts or p.as_posix() != path or path in seen):
            raise ValueError(f"Unsafe or duplicate inventory path: {path!r}")
        seen.add(path)
        digest = item.get("sha256")
        if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"Invalid SHA256 for {path}")
        size = item.get("size_bytes", 0)
        if type(size) is not int or size < 0:
            raise ValueError(f"Invalid size for {path}")
        if digest:
            hashes[digest] += 1
        package, status = classify(path, digest, item.get("status", ""))
        rows.append({"path": path, "size_bytes": size, "sha256": digest,
                     "proposed_package": package, "review_status": status,
                     "approved_for_upload": False, "license": "unreviewed",
                     "scientific_identity": "unreviewed"})
    for row in rows:
        row["same_hash_file_count"] = hashes[row["sha256"]] if row["sha256"] else 0
    groups = {}
    for row in rows:
        group = groups.setdefault(row["proposed_package"], {"file_count": 0, "size_bytes": 0})
        group["file_count"] += 1
        group["size_bytes"] += row["size_bytes"]
    source_matches = [r["path"] for r in rows if r["sha256"] == source_contract["source_sha256"]]
    return {
        "schema_version": "zenodo-curation-plan-v1", "status": "draft_only",
        "draft_url": "https://zenodo.org/uploads/22751909",
        "upload_performed": False, "publication_authorized": False,
        "file_count": len(rows), "total_bytes": sum(r["size_bytes"] for r in rows),
        "package_summary": groups, "duplicate_hash_groups": sum(n > 1 for n in hashes.values()),
        "source_contract": source_contract, "matching_population_source_paths": source_matches,
        "population_source_status": "hash_present_rights_pending" if source_matches
                                    else "missing_expected_source_hash",
        "required_release_gates": ["source_rights", "content_screening", "scientific_selection",
                                   "input_validation", "archive_hash_verification",
                                   "reproduction_check", "curator_approval"],
        "duplicate_policy": "Do not remove copies from checksum-bound releases without a mapping.",
        "files": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    contract_path = ROOT / "data/manifests/warehouse_population_source_v020.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    plan = build_plan(inventory, contract)
    plan["inventory_sha256"] = hashlib.sha256(args.inventory.read_bytes()).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "zenodo_curation_plan.json").write_text(
        json.dumps(plan, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with (args.output_dir / "zenodo_curation_plan.csv").open(
            "w", newline="", encoding="utf-8") as stream:
        fields = list(plan["files"][0]) if plan["files"] else ["path", "approved_for_upload"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(plan["files"])
    print(args.output_dir / "zenodo_curation_plan.json")


if __name__ == "__main__":
    main()
