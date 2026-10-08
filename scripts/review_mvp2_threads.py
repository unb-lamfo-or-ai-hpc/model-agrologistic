"""Read-only portable audit of the original licensed S2 miniature qualification.

Reconstruct public-fixture residuals without a solver or private workbook. Never
extract an archive, rewrite original receipts, submit jobs or admit production.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import sys
import tarfile
from dataclasses import fields
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import mvp2_threads as screen  # noqa: E402
from src.logic.experiment_runner import _spec_payload, prepare_model_data  # noqa: E402
from src.logic.mathematical_contract import canonical_hash  # noqa: E402
from src.logic.objective_diagnostics import stage_degradation_records  # noqa: E402
from src.logic.optimization import OptimizationResult  # noqa: E402
from src.logic.solution_validation import validate_solution  # noqa: E402

SOURCE = "04e8c0f8bd1255215f63f7592b027eac7a346b76"
JOB = "2202239"
ARCHIVE_SHA = "985002c13784ba071054e4c0db412cb41eefa60366f777866ce3eb3d52b586b2"
QUALIFICATION = Path(
    "/home/vrrcelestino/model-agrologistic-hygiene-audit/mvp2-threads-s2-hqEO7Eip/qualification"
)


def safe_assets(archive, expected_sha=ARCHIVE_SHA):
    screen.require(screen.file_sha256(archive) == expected_sha, "Archive checksum differs.")
    assets, total = {}, 0
    with tarfile.open(archive, "r:gz") as package:
        for member in package:
            name = member.name
            screen.require(
                member.isfile()
                and name not in assets
                and "\\" not in name
                and ":" not in name
                and not name.startswith("/")
                and str(PurePosixPath(name)) == name
                and ".." not in PurePosixPath(name).parts
                and 0 <= member.size <= 1_000_000,
                "Unsafe evidence member.",
            )
            total += member.size
            screen.require(
                len(assets) < 200 and total <= 20_000_000,
                "Evidence expansion exceeds review bounds.",
            )
            assets[name] = package.extractfile(member).read()
    return assets


def hash_catalog(assets, catalog):
    screen.require(isinstance(catalog, dict) and bool(catalog), "Empty hash catalog.")
    screen.require(
        all(
            name in assets and screen.transfer.digest(assets[name]) == digest
            for name, digest in catalog.items()
        ),
        "Artifact hash mismatch.",
    )


def review_arm(assets, threads, implementation):
    prefix = f"miniatures/threads-{threads}/"

    def read(name):
        return json.loads(assets[prefix + name])

    completed = read("run_completion.json")
    screen.require(
        completed["schema_version"] == 1
        and completed["status"] == "complete"
        and set(completed["artifacts"]) == set(screen.PRODUCTS) - {"run_completion.json"},
        "Incomplete product catalog.",
    )
    hash_catalog(assets, {prefix + n: h for n, h in completed["artifacts"].items()})
    document = read("result.json")
    expected = screen.spec(threads, QUALIFICATION)
    expected_payload = json.loads(json.dumps(_spec_payload(expected)))
    expected_payload["workbook"] = (QUALIFICATION / "analytical-fixture").as_posix()
    screen.require(document["experiment"] == expected_payload, "Serialized spec drift.")
    result = document["result"]
    metadata = result["metadata"]
    payload = copy.deepcopy(document["experiment"])
    payload.pop("resume_evpi_vss")
    payload["implementation"] = implementation["sha256"]
    identity = screen.transfer.digest(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )
    screen.require(
        identity == completed["run_identity"] == metadata["run_identity"]
        and metadata["implementation_identity"] == implementation,
        "Original runtime/run identity drift.",
    )
    execution = document["execution"]
    screen.require(
        execution["slurm_job_id"] == JOB
        and execution["source_commit_declared"] == SOURCE
        and execution["slurm_array_job_id"] is None
        and execution["slurm_array_task_id"] is None,
        "Original execution identity drift.",
    )
    summary = read("run_summary.json")
    screen.require(
        result["status"] == summary["status"] == "optimal"
        and summary["independent_validation_status"] == "accepted"
        and summary["lexicographic_completed_stage_count"] == 3
        and summary["lexicographic_overall_status"] == "complete",
        "Miniature hierarchy incomplete.",
    )
    names = {field.name for field in fields(OptimizationResult)} - {"raw_solver_result"}
    reconstructed = OptimizationResult(**{k: v for k, v in result.items() if k in names})
    validation = validate_solution(
        prepare_model_data(screen.fixture_data(), expected.model), expected.model, reconstructed
    )
    validation = json.loads(json.dumps(validation))
    screen.require(
        validation == read("independent_validation.json")
        and validation["status"] == "accepted"
        and validation["failed_check_count"] == 0,
        "Public fixture residual revalidation differs or fails.",
    )
    stages = metadata["lexicographic_stages"]
    recomputed = stage_degradation_records(
        stages,
        result["metrics"]["objective_values"],
        mip_gap=0.1,
        mip_gap_abs=1e-10,
        objective_abs_tol=expected.model.feasibility_tolerance,
    )
    screen.require(
        stages == recomputed
        and [s["stage_role"] for s in stages] == list(screen.ROLES)
        and all(s["status"] == "OPTIMAL" and s["status_code"] == 2 for s in stages)
        and screen.classify_stages(stages, validation["status"]) == "accepted_at_ten_percent",
        "Original hierarchy certificate drift.",
    )
    diagnostics = read("solver_diagnostics.json")
    for role in screen.ROLES:
        settings = diagnostics["effective_stage_parameters"][role]
        screen.require(
            all(
                settings[k] == v
                for k, v in {
                    "Threads": threads,
                    "Method": 2,
                    "TimeLimit": 60,
                    "SoftMemLimit": 1,
                    "MIPGap": 0.1,
                    "MIPGapAbs": 1e-10,
                    "NumericFocus": 1,
                }.items()
            ),
            "Observed per-stage parameter drift.",
        )
    manifest = read("resources/manifest.json")
    screen.require(
        manifest["status"] == "closed"
        and set(manifest["artifacts"])
        == {
            "runtime_capabilities.json",
            "allocation_receipt.json",
            "matrix_statistics.json",
            "resource_timeseries.csv",
            "stage_progress.csv",
            "termination.json",
        },
        "Resource manifest incomplete.",
    )
    hash_catalog(assets, {prefix + "resources/" + n: h for n, h in manifest["artifacts"].items()})
    resources = list(
        csv.DictReader(io.StringIO(assets[prefix + "resources/resource_timeseries.csv"].decode()))
    )
    progress = list(
        csv.DictReader(io.StringIO(assets[prefix + "resources/stage_progress.csv"].decode()))
    )
    termination = read("resources/termination.json")
    screen.require(
        termination["execution_status"] == "optimal"
        and termination["exception_type"] is None
        and termination["dropped_samples"] == {"resource": 0, "progress": 0}
        and termination["inspection_errors"] == []
        and termination["samples"] == {"resource": len(resources), "progress": len(progress)}
        and bool(resources)
        and bool(progress)
        and all(
            not row["observation_errors"] and int(row["cgroup_limit_bytes"]) == 16 * 1024**3
            for row in resources
        ),
        "Resource closure/observations inconsistent.",
    )
    return {
        "threads": threads,
        "status": "accepted",
        "run_identity": identity,
        "residual_families": len(validation["families"]),
        "residual_checks": sum(f["checked"] for f in validation["families"].values()),
        "hierarchy": "complete",
        "optimization_seconds": summary["optimization_seconds"],
        "application_seconds": summary["end_to_end_seconds"],
        "resource_samples": len(resources),
        "progress_samples": len(progress),
        "final_unmet_demand": summary["total_unmet_demand"],
        "final_emergency_capacity": summary["total_emergency_capacity"],
        "economic_cost": summary["economic_cost"],
    }


def review_assets(assets):
    def read(name):
        return json.loads(assets[name])

    expected = {
        "accounting.txt",
        "plan.json",
        "submission.json",
        "allocation.json",
        "license.json",
        "qualification.json",
        "worker_status.json",
        "scheduler/job.txt",
        "scheduler/node.txt",
        "bootstrap/login-recovery.json",
        *[f"arm-{p}.json" for p in screen.policy()["grid"]],
        *[f"miniatures/threads-{p}/{n}" for p in screen.policy()["grid"] for n in screen.PRODUCTS],
    }
    collection = read("collection.json")
    screen.require(
        set(assets) == expected | {"collection.json"} and set(collection["artifacts"]) == expected,
        "Transfer allowlist differs.",
    )
    hash_catalog(assets, collection["artifacts"])
    screen.require(
        collection["schema_version"] == "mvp2-threads-collection-v1"
        and collection["status"] == "accepted"
        and collection["errors"] == []
        and collection["source_commit"] == SOURCE
        and collection["scope"] == "licensed_miniature_parameter_qualification"
        and collection["large_instance_submission_allowed"] is False,
        "Original collection identity/status differs.",
    )
    terminal = screen.transfer.terminal_accounting(assets["accounting.txt"].decode(), JOB)
    screen.require(
        terminal
        == collection["terminal"]
        == {"job_id": JOB, "state": "COMPLETED", "exit_code": "0:0"},
        "Terminal accounting differs.",
    )
    plan, report = read("plan.json"), read("qualification.json")
    screen.require(
        plan["schema_version"] == "mvp2-threads-plan-v1"
        and plan["source_commit"] == SOURCE
        and plan["policy"] == screen.policy()
        and plan["tools"] == screen.tools()
        and plan["fixture_sha256"] == screen.scientific_identity(screen.fixture_data())
        and plan["login_recovery_sha256"]
        == screen.transfer.digest(assets["bootstrap/login-recovery.json"])
        and plan["large_instance_submission_allowed"] is False,
        "Original plan/tools/fixture/recovery drift.",
    )
    runtime = plan["implementation"]
    screen.require(
        canonical_hash({k: v for k, v in runtime.items() if k != "sha256"}) == runtime["sha256"]
        and runtime["sources"]
        == {
            p.name: hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
            for p in sorted((ROOT / "src/logic").glob("*.py"))
        },
        "Original normalized implementation identity drift.",
    )
    recovery = read("bootstrap/login-recovery.json")
    screen.require(
        recovery["schema_version"] == "s2-login-recovery-v1"
        and recovery["status"] == "pre_submission_only"
        and recovery["original_source"] == "0360c25c2486daf99c223ca18f6bf80cb2af8238"
        and recovery["original_tests"] == {"tests": 56, "failures": 0, "errors": 0, "skipped": 0}
        and all(
            recovery[k] is False
            for k in ("active_original_processes", "active_s2_jobs", "original_submission_products")
        ),
        "Original bootstrap recovery differs.",
    )
    allocation = read("allocation.json")
    observed = screen.allocation(
        assets["scheduler/job.txt"].decode(),
        assets["scheduler/node.txt"].decode(),
        JOB,
        allocation["node"],
        allocation["cgroup"],
        allocation["accessible_cpus"],
    )
    screen.require(
        observed == allocation == report["allocation"]
        and screen.baseline.license_accepted(read("license.json"))
        and read("submission.json") == {"job_id": JOB, "source_commit": SOURCE}
        and read("worker_status.json") == {"job_id": JOB, "exit_code": 0, "status": "completed"},
        "Original allocation/license/process receipts differ.",
    )
    screen.require(
        report["schema_version"] == "mvp2-threads-qualification-v1"
        and report["source_commit"] == SOURCE
        and report["status"] == "accepted"
        and report["plan_sha256"] == screen.transfer.digest(assets["plan.json"])
        and report["large_instance_submission_allowed"] is False
        and report["performance_acceptance"] is False
        and report["observations"]
        == [
            {"threads": p, "status": "optimal", "independent_validation": "accepted"}
            for p in screen.policy()["order"]
        ],
        "Qualification receipt differs.",
    )
    arms = []
    for threads in screen.policy()["order"]:
        screen.require(
            read(f"arm-{threads}.json") == {"threads": threads, "return_code": 0},
            "Cold child did not close.",
        )
        arms.append(review_arm(assets, threads, runtime))
    return {
        "schema_version": "s2-portable-review-v1",
        "status": "accepted",
        "execution_source_commit": SOURCE,
        "job_id": JOB,
        "archive_sha256": ARCHIVE_SHA,
        "member_count": len(assets),
        "transfer_hashes_verified": len(expected),
        "original_collection_rewritten": False,
        "allocation": allocation,
        "original_runtime": {k: v for k, v in runtime.items() if k != "sources"},
        "arms": arms,
        "fresh_public_fixture_residual_revalidation": True,
        "large_instance_submission_allowed": False,
        "performance_acceptance": False,
        "qualification": "Miniature settings/closure only, not production speedup or utilization.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    screen.require(not output.is_relative_to(ROOT), "Review output overlaps source.")
    report = review_assets(safe_assets(args.archive))
    report["reviewer_sha256"] = screen.file_sha256(Path(__file__))
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"REVIEW_STATUS={report['status']}\nREVIEW={output}")


if __name__ == "__main__":
    main()
