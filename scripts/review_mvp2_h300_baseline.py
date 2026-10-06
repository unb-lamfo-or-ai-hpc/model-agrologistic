"""Read-only retrospective review of the pinned 2198528 transfer; never submit jobs.

This verifies original NPAD validation evidence, not a fresh residual validation
against the private workbook. The original rejected collection is immutable.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import sys
import tarfile
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import collect_mvp2_h300_baseline as collector  # noqa: E402
from scripts import collect_mvp2_pair_preflight as transfer  # noqa: E402
from scripts import mvp2_h300_baseline as baseline  # noqa: E402
from scripts.audit_nine_campaign import classify_stages  # noqa: E402
from src.logic.mathematical_contract import canonical_hash  # noqa: E402
from src.logic.run_integrity import file_sha256  # noqa: E402

ARCHIVE_SHA = "43311a0000a3fb09f535ea273bd889ba1a6e09bf728460f0f28b764242e400c2"
SOURCE = "d70cade148e190e98d41a5ac3d4e040353f2c6ec"
JOB = "2198528"
PREFIX = "runs/mvp2_h300_warehouse_baseline/"


def safe_assets(archive, expected_sha):
    """Bound memory and reject links, traversal, duplicates and ambiguous names."""
    baseline.require(file_sha256(archive) == expected_sha, "Archive checksum differs.")
    with tarfile.open(archive, "r:gz") as package:
        members = []
        total = 0
        for member in package:
            name = member.name
            baseline.require(
                member.isfile()
                and "\\" not in name
                and ":" not in name
                and not name.startswith("/")
                and str(PurePosixPath(name)) == name
                and ".." not in PurePosixPath(name).parts
                and 0 <= member.size <= 200_000_000,
                "Unsafe evidence member.",
            )
            members.append(member)
            total += member.size
            baseline.require(
                len(members) <= 100 and total <= 300_000_000,
                "Evidence expansion exceeds review bounds.",
            )
        baseline.require(
            len({m.name for m in members}) == len(members), "Duplicate evidence members."
        )
        return {m.name: package.extractfile(m).read() for m in members}


def hash_catalog(assets, catalog):
    baseline.require(isinstance(catalog, dict) and bool(catalog), "Empty artifact catalog.")
    for name, digest in catalog.items():
        baseline.require(
            name in assets and transfer.digest(assets[name]) == digest,
            f"Artifact hash mismatch: {name}",
        )


def review(archive, input_run, execution_checkout):
    archive, input_run, execution_checkout = (
        Path(p).resolve() for p in (archive, input_run, execution_checkout)
    )
    assets = safe_assets(archive, ARCHIVE_SHA)

    def read(name):
        return json.loads(assets[name])

    checks = []

    def require(valid, label):
        baseline.require(valid, label)
        checks.append(label)

    policy = read("review/baseline_policy.json")
    require(policy == baseline.policy(), "pinned_versioned_policy")
    plan, admission = read("baseline_plan.json"), read("baseline_admission.json")
    closure, collected = read("baseline_execution.json"), read("collection.json")
    expected = {
        "baseline_plan.json",
        "campaign.yaml",
        "input_accounting.txt",
        "source_commit.txt",
        "tool_hashes.json",
        "submission.txt",
        "scheduler/job.txt",
        "scheduler/node.txt",
        "cgroup_observation.json",
        "worker_status.json",
        "license_capability.json",
        "baseline_admission.json",
        "baseline_execution.json",
        "logs/control.out",
        "logs/control-exit.json",
        "logs/audit.out",
        f"slurm-{JOB}.out",
        *(
            f"comparison/{n}"
            for n in (
                "nine_audit_manifest.json",
                "nine_results.json",
                "nine_results.csv",
                "nine_stage_gaps.json",
                "nine_stage_gaps.csv",
            )
        ),
        *(PREFIX + n for n in (*collector.PRODUCTS, "run_completion.json")),
        "review/baseline_policy.json",
    }
    require(
        set(collected["artifacts"]) == expected
        and set(assets) == expected | {"collection.json", "accounting.txt"},
        "59_allowlisted_members_57_transfer_artifacts",
    )
    hash_catalog(assets, collected["artifacts"])
    require(
        collected["status"] == "evidence_rejected"
        and collected["acceptance_errors"]
        == ["ValueError: Solved input audit differs: model_audit.json"],
        "original_rejection_preserved_and_explained",
    )
    accounting = transfer.terminal_accounting(assets["accounting.txt"].decode(), JOB)
    require(
        accounting
        == collected["accounting"]
        == {"job_id": JOB, "state": "COMPLETED", "exit_code": "0:0"},
        "successful_terminal_accounting",
    )
    require(
        assets["source_commit.txt"].decode().strip() == SOURCE
        and assets["submission.txt"].decode().strip() == f"MVP2_H300_BASELINE_JOB={JOB}",
        "original_source_and_single_submission",
    )
    tools = read("tool_hashes.json")
    require(
        tools == plan["tools"] == admission["tools"]
        and set(tools) == set(baseline.TOOLS)
        and all(file_sha256(execution_checkout / n) == h for n, h in tools.items())
        and collected["collector_sha256"] == tools["scripts/collect_mvp2_h300_baseline.py"],
        "original_execution_tools_not_relabelled_to_current_head",
    )
    input_assets = transfer.evidence_snapshot(input_run, policy["input_job_id"])
    original = json.loads(input_assets["audit/preflight/pair_preflight.json"])
    require(
        not transfer.receipt_errors(input_assets, policy["input_job_id"])
        and transfer.digest(input_assets["prepared/resource_contrast_plan.json"])
        == policy["input_plan_sha256"]
        and transfer.digest(input_assets["audit/preflight/pair_preflight.json"])
        == policy["input_receipt_sha256"]
        and input_assets["audit/source_commit.txt"].decode().strip()
        == policy["input_source_commit"]
        and all(file_sha256(execution_checkout / n) == h for n, h in original["tools"].items()),
        "original_input_receipt_12_products_and_source_tools",
    )
    require(
        plan["schema_version"] == "mvp2-h300-baseline-plan-v1"
        and plan["status"] == "prepared_not_admitted"
        and plan["policy_sha256"] == transfer.digest(assets["review/baseline_policy.json"])
        and plan["campaign_sha256"] == transfer.digest(assets["campaign.yaml"])
        and plan["input_accounting_sha256"] == transfer.digest(assets["input_accounting.txt"])
        and transfer.terminal_accounting(
            assets["input_accounting.txt"].decode(), policy["input_job_id"]
        )
        == {"job_id": policy["input_job_id"], "state": "COMPLETED", "exit_code": "0:0"}
        and plan["scope"] == policy["scope"]
        and plan["allocation_profile"] == policy["allocation_profile"]
        and plan["production_explicit_lifecycle_allowed"] is False,
        "immutable_plan_policy_input_accounting",
    )
    campaign = yaml.safe_load(assets["campaign.yaml"])
    expected_spec = copy.deepcopy(
        yaml.safe_load(input_assets["prepared/campaign.yaml"])["experiments"][0]
    )
    expected_spec["name"] = policy["experiment_name"]
    expected_spec["max_estimated_variables"] = policy["execution_limit"]
    expected_spec["metadata"].update(
        resource_contrast_arm="baseline_control",
        resource_contrast_scope=policy["scope"],
        baseline_size_review=policy["review_id"],
    )
    require(
        campaign
        == {
            "version": 1,
            "continue_on_error": False,
            "output_dir": collected["preserved_execution"] + "/runs",
            "experiments": [expected_spec],
        },
        "only_approved_control_derivation",
    )
    resource = baseline.allocation(
        assets["scheduler/job.txt"].decode(),
        assets["scheduler/node.txt"].decode(),
        job_id=JOB,
        node_name=admission["allocation"]["node"],
        cgroup=read("cgroup_observation.json"),
    )
    require(
        all(
            v["source_commit"] == SOURCE
            and v["allocation"] == resource
            and v["baseline_plan_sha256"] == transfer.digest(assets["baseline_plan.json"])
            and v["scope"] == plan["scope"]
            for v in (admission, closure)
        )
        and admission["schema_version"] == "mvp2-h300-baseline-admission-v1"
        and admission["status"] == "admitted"
        and admission["policy_sha256"] == plan["policy_sha256"]
        and admission["production_explicit_lifecycle_allowed"] is False
        and admission["license_capability_sha256"]
        == transfer.digest(assets["license_capability.json"])
        and baseline.license_accepted(read("license_capability.json"))
        and closure["schema_version"] == "mvp2-h300-baseline-execution-v1"
        and closure["status"] == "process_returned"
        and closure["optimization_attempted"] is True
        and closure["control_return_code"] == closure["audit_return_code"] == 0,
        "fresh_allocation_license_admission_and_execution",
    )
    worker = read("worker_status.json")
    require(
        worker["job_id"] == JOB
        and worker["status"] == "completed"
        and worker["phase"] == "complete"
        and worker["exit_code"] == 0
        and read("logs/control-exit.json") == {"index": 0, "return_code": 0},
        "worker_and_control_exit_zero",
    )
    completed = read(PREFIX + "run_completion.json")
    require(
        completed["schema_version"] == 1
        and completed["status"] == "complete"
        and set(completed["artifacts"]) == set(collector.PRODUCTS),
        "33_named_closed_products",
    )
    hash_catalog(assets, {PREFIX + n: h for n, h in completed["artifacts"].items()})
    result = read(PREFIX + "result.json")
    metadata = result["result"]["metadata"]
    identity = metadata["implementation_identity"]
    payload = {k: v for k, v in identity.items() if k != "sha256"}
    require(
        identity == original["implementation"]
        and canonical_hash(payload) == identity["sha256"] == policy["implementation_sha256"]
        and identity["sources"]
        == {
            p.name: hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
            for p in sorted((execution_checkout / "src/logic").glob("*.py"))
        },
        "44_normalized_sources_and_original_runtime_identity",
    )
    spec = copy.deepcopy(result["experiment"])
    require(
        all(
            spec[k] == expected_spec[k]
            for k in ("name", "model", "solver", "loader", "metadata", "max_estimated_variables")
        )
        and spec["workbook"] == expected_spec["workbook"]
        and spec["workbook_sha256"]
        == json.loads(input_assets["prepared/resource_contrast_plan.json"])["workbook_sha256"]
        and spec["calculate_evpi_vss"] is False
        and spec["resume_evpi_vss"] is False,
        "serialized_spec_retains_mathematics_and_solver_contract",
    )
    spec.pop("resume_evpi_vss")
    spec["implementation"] = identity["sha256"]
    run_hash = transfer.digest(
        json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )
    require(
        run_hash == completed["run_identity"] == metadata["run_identity"],
        "run_identity_recomputed_with_original_runtime_not_local_runtime",
    )
    preflight = read(PREFIX + "preflight.json")
    preflight.pop("execution", None)
    require(preflight == original["model_size"], "exact_normalized_preflight_parity")
    original_audit = json.loads(
        input_assets["audit/preflight/mvp2_h300_warehouse_control/model_audit.json"]
    )
    solved_audit = read(PREFIX + "model_audit.json")
    baseline.check_solved_model_audit(original_audit, solved_audit)
    require(
        all(
            transfer.digest(assets[PREFIX + n])
            == original["artifacts"][f"mvp2_h300_warehouse_control/{n}"]
            for n in baseline.inputs.PRODUCTS[1:]
            if n != "model_audit.json"
        ),
        "full_input_audit_parity_and_four_unchanged_connectivity_products",
    )
    validation = read(PREFIX + "independent_validation.json")
    require(
        validation["status"] == metadata["independent_validation_status"] == "accepted"
        and validation["failed_check_count"] == 0
        and validation["failure_samples"] == []
        and bool(validation["families"])
        and all(
            v["failed"] == 0 and v["checked"] > 0 and math.isfinite(v["max_residual"])
            for v in validation["families"].values()
        )
        and validation["mathematical_contract"] == metadata["mathematical_contract"],
        "original_independent_validation_32_families_no_failed_checks",
    )
    stages = metadata["lexicographic_stages"]
    hierarchy = read("comparison/nine_audit_manifest.json")
    require(
        classify_stages(stages, validation["status"]) == "accepted_at_ten_percent"
        and stages
        == [
            {k: v for k, v in s.items() if k != "name"}
            for s in read("comparison/nine_stage_gaps.json")
        ]
        and hierarchy["overall_status"] == "accepted"
        and hierarchy["selected_indices"] == [0]
        and hierarchy["accepted_instance_count"] == hierarchy["campaign_instance_count"] == 1
        and hierarchy["manifest_sha256"] == plan["campaign_sha256"]
        and hierarchy["audit_script_sha256"] == tools["scripts/audit_nine_campaign.py"],
        "hierarchy_reclassified_from_original_stage_certificates",
    )
    resource_manifest = read(PREFIX + "resources/manifest.json")
    require(
        resource_manifest["status"] == "closed" and len(resource_manifest["artifacts"]) == 6,
        "closed_resource_manifest",
    )
    hash_catalog(
        assets, {PREFIX + "resources/" + n: h for n, h in resource_manifest["artifacts"].items()}
    )
    termination = read(PREFIX + "resources/termination.json")
    rows = list(
        csv.DictReader(io.StringIO(assets[PREFIX + "resources/resource_timeseries.csv"].decode()))
    )
    progress = list(
        csv.DictReader(io.StringIO(assets[PREFIX + "resources/stage_progress.csv"].decode()))
    )
    require(
        termination["execution_status"] == "optimal"
        and termination["exception_type"] is None
        and termination["dropped_samples"] == {"resource": 0, "progress": 0}
        and termination["inspection_errors"] == []
        and termination["samples"] == {"resource": len(rows), "progress": len(progress)}
        and all(
            not r["observation_errors"] and int(r["cgroup_limit_bytes"]) == 206158430208
            for r in rows
        )
        and read(PREFIX + "resources/runtime_capabilities.json")["sampling_solver_api_calls"]
        is False,
        "telemetry_counts_caps_errors_and_solver_api_isolation",
    )
    phase_peaks = {}
    for row in rows:
        peak = phase_peaks.setdefault(
            row["phase"], {"samples": 0, "tree_rss_gib": 0, "cgroup_gib": 0}
        )
        peak["samples"] += 1
        peak["tree_rss_gib"] = max(peak["tree_rss_gib"], int(row["process_tree_rss_bytes"]) / 2**30)
        peak["cgroup_gib"] = max(peak["cgroup_gib"], int(row["cgroup_current_bytes"]) / 2**30)
    native = [float(r["solver_memory_bytes"]) / 2**30 for r in progress if r["solver_memory_bytes"]]
    return {
        "schema_version": "mvp2-h300-retrospective-review-v1",
        "status": "accepted",
        "reviewer_sha256": file_sha256(Path(__file__)),
        "archive_sha256": ARCHIVE_SHA,
        "job_id": JOB,
        "execution_source_commit": SOURCE,
        "original_collection_status": collected["status"],
        "original_collection_rewritten": False,
        "checks_passed": checks,
        "run_identity": run_hash,
        "validation_families": len(validation["families"]),
        "qualification": (
            "Original NPAD residual validation verified, not rerun against private workbook; "
            "one baseline, no causal performance claim."
        ),
        "summary": read(PREFIX + "run_summary.json"),
        "stages": stages,
        "model_findings": solved_audit["findings"],
        "matrix": read(PREFIX + "resources/matrix_statistics.json"),
        "telemetry": {
            "phase_peaks": phase_peaks,
            "termination": termination,
            "peak_reported_native_memory_gib": max(native) if native else None,
            "last_live_tree_cpu_seconds": float(rows[-1]["process_tree_cpu_seconds"]),
            "max_observed_native_threads": max(int(r["root_native_threads"]) for r in rows),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--input-run", required=True, type=Path)
    parser.add_argument("--execution-checkout", required=True, type=Path)
    args = parser.parse_args()
    # Stdout only: caller chooses a new report path; no extraction or source writes.
    print(
        json.dumps(
            review(args.archive, args.input_run, args.execution_checkout), indent=2, allow_nan=False
        )
    )


if __name__ == "__main__":
    main()
