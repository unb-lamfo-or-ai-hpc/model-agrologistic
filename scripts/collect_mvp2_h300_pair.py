"""Collect terminal h300 pairs and review their transfers without private inputs."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import re
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import collect_mvp2_h300_baseline as old_collector  # noqa: E402
from scripts import mvp2_h300_pair as pair  # noqa: E402
from scripts.audit_nine_campaign import classify_stages  # noqa: E402
from src.logic.mathematical_contract import canonical_hash  # noqa: E402

PRODUCTS = old_collector.PRODUCTS
ARMS = ("mvp2_h300_warehouse_control", "mvp2_h300_warehouse_compact")
digest = pair.baseline.transfer.digest


def names(job):
    return (
        "pair_plan.json",
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
        "pair_admission.json",
        "pair_execution.json",
        "logs/audit.out",
        f"slurm-{job}.out",
        *(f"logs/arm-{i}{suffix}" for i in (0, 1) for suffix in (".out", "-exit.json")),
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
        *(f"runs/{arm}/{n}" for arm in ARMS for n in (*PRODUCTS, "run_completion.json")),
    )


def snapshot(execution, job):
    assets = {}
    for name in names(job):
        path = execution / name
        pair.require(
            not path.is_symlink() and path.resolve().is_relative_to(execution),
            f"Unsafe evidence path: {name}",
        )
        if path.is_file():
            assets[name] = path.read_bytes()
    assets["review/pair_policy.json"] = (ROOT / pair.POLICY).read_bytes()
    assets["review/input_policy.json"] = (
        json.dumps(pair.baseline.policy(), indent=2, allow_nan=False) + "\n"
    ).encode()
    try:
        record = pair.read(execution / "pair_plan.json")
        original = Path(record["input_run"])
        inputs = pair.baseline.transfer.evidence_snapshot(
            original, pair.baseline.policy()["input_job_id"]
        )
        assets.update({f"input/{n}": data for n, data in inputs.items()})
    except (OSError, ValueError, KeyError, TypeError) as exc:
        assets["review/input_snapshot_error.json"] = json.dumps(
            {"exception_type": type(exc).__name__}
        ).encode()
    return assets


def catalog_check(assets, catalog):
    pair.require(isinstance(catalog, dict) and bool(catalog), "Missing artifact catalog.")
    for name, expected in catalog.items():
        pair.require(
            name in assets and digest(assets[name]) == expected, f"Artifact hash mismatch: {name}"
        )


def validate_assets(assets, job):
    """Reclassify original certificates; never reconstruct or execute a model."""

    def read(name):
        return json.loads(assets[name])

    policy, input_policy = read("review/pair_policy.json"), read("review/input_policy.json")
    pair.require(
        policy == pair.policy() and input_policy == pair.baseline.policy(),
        "Transfer policies differ from the pinned review checkout.",
    )
    original = {n.removeprefix("input/"): v for n, v in assets.items() if n.startswith("input/")}
    receipt = json.loads(original["audit/preflight/pair_preflight.json"])
    pair.require(
        not pair.baseline.transfer.receipt_errors(original, input_policy["input_job_id"])
        and digest(original["prepared/resource_contrast_plan.json"])
        == input_policy["input_plan_sha256"]
        and digest(original["audit/preflight/pair_preflight.json"])
        == input_policy["input_receipt_sha256"]
        and original["audit/source_commit.txt"].decode().strip()
        == input_policy["input_source_commit"],
        "Original accepted input evidence differs.",
    )
    input_allocation = pair.baseline.inputs.allocation(
        original["audit/scheduler/job.txt"].decode(),
        original["audit/scheduler/node.txt"].decode(),
        job_id=input_policy["input_job_id"],
        node_name=receipt["allocation"]["node"],
    )
    input_worker = json.loads(original["audit/worker_status.json"])
    pair.require(
        input_allocation == receipt["allocation"]
        and receipt["tools"] == pair.baseline.inputs.tool_identity()
        and digest(original["audit/input_size_review.json"]) == input_policy["input_review_sha256"]
        and original["audit/submission.txt"].decode().strip()
        == f"MVP2_PAIR_PREFLIGHT_JOB={input_policy['input_job_id']}"
        and input_worker["status"] == "completed"
        and input_worker["exit_code"] == 0
        and input_worker["job_id"] == input_policy["input_job_id"]
        and input_worker["optimization_executed"] is False,
        "Original input allocation, worker, size review or tools differ.",
    )
    plan, admission, closure = (
        read(n) for n in ("pair_plan.json", "pair_admission.json", "pair_execution.json")
    )
    tools = read("tool_hashes.json")
    source = assets["source_commit.txt"].decode().strip()
    pair.require(
        bool(re.fullmatch(r"[0-9a-f]{40}", source))
        and assets["submission.txt"].decode().strip() == f"MVP2_H300_PAIR_JOB={job}"
        and tools == plan["tools"] == admission["tools"] == pair.tool_identity(),
        "Source, submission or pinned tools differ.",
    )
    pair.require(
        plan["schema_version"] == "mvp2-h300-pair-plan-v1"
        and plan["status"] == "prepared_not_admitted"
        and plan["policy_sha256"] == digest(assets["review/pair_policy.json"])
        and plan["campaign_sha256"] == digest(assets["campaign.yaml"])
        and plan["input_accounting_sha256"] == digest(assets["input_accounting.txt"])
        and pair.baseline.transfer.terminal_accounting(
            assets["input_accounting.txt"].decode(), input_policy["input_job_id"]
        )
        == {"job_id": input_policy["input_job_id"], "state": "COMPLETED", "exit_code": "0:0"}
        and plan["scope"] == policy["scope"]
        and pair.baseline.pair.validate_arm_order(plan["arm_order"]) == policy["arm_order"]
        and plan["allocation_profile"] == policy["allocation_profile"]
        and plan["production_explicit_lifecycle_allowed"] is False
        and plan["automatic_repeats_allowed"] is False,
        "Immutable pair plan/accounting/order differs.",
    )
    campaign = yaml.safe_load(assets["campaign.yaml"])
    expected_campaign = pair.campaign_from_original(
        yaml.safe_load(original["prepared/campaign.yaml"]), ROOT
    )
    expected_campaign["output_dir"] = campaign["output_dir"]
    pair.require(
        campaign == expected_campaign,
        "Pair campaign differs beyond the exact execution derivation.",
    )
    resource = pair.allocation(
        assets["scheduler/job.txt"].decode(),
        assets["scheduler/node.txt"].decode(),
        job_id=job,
        node_name=admission["allocation"]["node"],
        cgroup=read("cgroup_observation.json"),
    )
    pair.require(
        all(
            v["source_commit"] == source
            and v["allocation"] == resource
            and v["pair_plan_sha256"] == digest(assets["pair_plan.json"])
            and v["scope"] == policy["scope"]
            and v["arm_order"] == policy["arm_order"]
            for v in (admission, closure)
        )
        and admission["schema_version"] == "mvp2-h300-pair-admission-v1"
        and admission["status"] == "admitted"
        and admission["policy_sha256"] == plan["policy_sha256"]
        and admission["production_explicit_lifecycle_allowed"] is False
        and admission["automatic_repeats_allowed"] is False
        and admission["license_capability_sha256"] == digest(assets["license_capability.json"])
        and pair.baseline.license_accepted(read("license_capability.json"))
        and closure["schema_version"] == "mvp2-h300-pair-execution-v1"
        and closure["status"] == "process_returned"
        and closure["optimization_attempted"] is True
        and closure["arms"] == [{"index": i, "return_code": 0} for i in policy["arm_order"]]
        and closure["audit_return_code"] == 0,
        "Paired allocation/license/admission/process closure failed.",
    )
    worker = read("worker_status.json")
    pair.require(
        worker["job_id"] == job
        and worker["status"] == "completed"
        and worker["phase"] == "complete"
        and worker["exit_code"] == 0,
        "Worker did not close successfully.",
    )
    hierarchy = read("comparison/nine_audit_manifest.json")
    pair.require(
        hierarchy["overall_status"] == "accepted"
        and hierarchy["selected_indices"] == [0, 1]
        and hierarchy["accepted_instance_count"] == hierarchy["campaign_instance_count"] == 2
        and hierarchy["manifest_sha256"] == plan["campaign_sha256"]
        and hierarchy["audit_script_sha256"] == tools["scripts/audit_nine_campaign.py"],
        "Two-arm hierarchical audit failed.",
    )
    arms = {}
    for index, arm in enumerate(ARMS):
        prefix = f"runs/{arm}/"
        pair.require(
            read(f"logs/arm-{index}-exit.json") == {"index": index, "return_code": 0},
            "Arm process exit differs.",
        )
        completion = read(prefix + "run_completion.json")
        pair.require(
            completion["schema_version"] == 1
            and completion["status"] == "complete"
            and set(completion["artifacts"]) == set(PRODUCTS),
            "Require 33 closed products per arm.",
        )
        catalog_check(assets, {prefix + n: h for n, h in completion["artifacts"].items()})
        result = read(prefix + "result.json")
        metadata, spec = result["result"]["metadata"], result["experiment"]
        implementation = metadata["implementation_identity"]
        pair.require(
            implementation == receipt["implementation"]
            and canonical_hash({k: v for k, v in implementation.items() if k != "sha256"})
            == implementation["sha256"]
            == input_policy["implementation_sha256"]
            and implementation["sources"]
            == {
                p.name: hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
                for p in sorted((ROOT / "src/logic").glob("*.py"))
            },
            "Original core sources/runtime identity differs.",
        )
        expected = campaign["experiments"][index]
        pair.require(
            all(
                spec[k] == expected[k]
                for k in (
                    "name",
                    "workbook",
                    "loader",
                    "model",
                    "solver",
                    "metadata",
                    "max_estimated_variables",
                )
            )
            and spec["workbook_sha256"]
            == json.loads(original["prepared/resource_contrast_plan.json"])["workbook_sha256"]
            and spec["calculate_evpi_vss"] is False
            and spec["resume_evpi_vss"] is False,
            "Serialized arm mathematical/solver/data contract differs.",
        )
        payload = copy.deepcopy(spec)
        payload.pop("resume_evpi_vss", None)
        payload["implementation"] = implementation["sha256"]
        identity = digest(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        )
        pair.require(
            identity == completion["run_identity"] == metadata["run_identity"],
            "Original arm run identity differs.",
        )
        observed = read(prefix + "preflight.json")
        observed.pop("execution", None)
        pair.require(observed == receipt["model_size"], "Solved dimensions differ from input.")
        pair.baseline.check_solved_model_audit(
            json.loads(original[f"audit/preflight/{arm}/model_audit.json"]),
            read(prefix + "model_audit.json"),
        )
        pair.require(
            all(
                digest(assets[prefix + n]) == receipt["artifacts"][f"{arm}/{n}"]
                for n in pair.baseline.inputs.PRODUCTS[1:]
                if n != "model_audit.json"
            ),
            "Solved connectivity audit differs.",
        )
        validation = read(prefix + "independent_validation.json")
        pair.require(
            validation["status"] == metadata["independent_validation_status"] == "accepted"
            and validation["failed_check_count"] == 0
            and validation["failure_samples"] == []
            and bool(validation["families"])
            and all(
                v["failed"] == 0 and v["checked"] > 0 and math.isfinite(v["max_residual"])
                for v in validation["families"].values()
            )
            and validation["mathematical_contract"] == metadata["mathematical_contract"],
            "Original independent validation failed.",
        )
        stages = metadata["lexicographic_stages"]
        pair.require(
            classify_stages(stages, validation["status"]) == "accepted_at_ten_percent"
            and stages
            == [
                {k: v for k, v in s.items() if k != "name"}
                for s in read("comparison/nine_stage_gaps.json")
                if s["name"] == arm
            ],
            "Original hierarchy certificates failed reclassification.",
        )
        manifest = read(prefix + "resources/manifest.json")
        pair.require(
            manifest["status"] == "closed" and len(manifest["artifacts"]) == 6,
            "Resource manifest did not close.",
        )
        catalog_check(
            assets, {prefix + "resources/" + n: h for n, h in manifest["artifacts"].items()}
        )
        rows = list(
            csv.DictReader(
                io.StringIO(assets[prefix + "resources/resource_timeseries.csv"].decode())
            )
        )
        progress = list(
            csv.DictReader(io.StringIO(assets[prefix + "resources/stage_progress.csv"].decode()))
        )
        termination = read(prefix + "resources/termination.json")
        pair.require(
            bool(rows)
            and termination["exception_type"] is None
            and termination["dropped_samples"] == {"resource": 0, "progress": 0}
            and termination["inspection_errors"] == []
            and termination["samples"] == {"resource": len(rows), "progress": len(progress)}
            and read(prefix + "resources/runtime_capabilities.json")["sampling_solver_api_calls"]
            is False,
            "Telemetry closure or sampler isolation failed.",
        )
        compaction = [r for r in progress if r["event"] == "python_index_compaction"]
        pair.require(
            len(compaction) == index
            and (index == 0 or int(compaction[0]["python_index_entries"]) > 0),
            "Compaction event does not match the assigned arm.",
        )
        phase_peaks = {}
        for row in rows:
            stats = phase_peaks.setdefault(row["phase"], {"samples": 0, "tree_rss_gib": 0})
            stats["samples"] += 1
            stats["tree_rss_gib"] = max(
                stats["tree_rss_gib"], int(row["process_tree_rss_bytes"]) / 2**30
            )
        arms[arm] = {
            "summary": read(prefix + "run_summary.json"),
            "stages": stages,
            "run_identity": identity,
            "phase_peaks": phase_peaks,
            "termination": termination,
            "compaction_events": compaction,
        }
    return arms


def collect(execution, output, job, *, accounting_text=None):
    execution, output = Path(execution).resolve(), Path(output).resolve()
    pair.require(bool(re.fullmatch(r"[0-9]+", job)), "Require numeric standalone job.")
    protected = [execution, ROOT]
    try:
        record = pair.read(execution / "pair_plan.json")
        protected.append(Path(record["input_run"]).resolve())
    except (OSError, ValueError, KeyError, TypeError):
        pass  # The malformed plan is still transferred and cannot be accepted.
    pair.require(
        not output.exists()
        and not any(output.is_relative_to(p) or p.is_relative_to(output) for p in protected),
        "Choose new isolated collection output.",
    )
    pair.require(
        (execution / "submission.txt").read_text().strip() == f"MVP2_H300_PAIR_JOB={job}",
        "Submission does not identify this pair job.",
    )
    if accounting_text is None:
        accounting_text = subprocess.check_output(
            [
                "sacct",
                "-n",
                "-P",
                "-j",
                job,
                "--format=JobIDRaw,State,ExitCode,Elapsed,MaxRSS,NodeList",
            ],
            text=True,
        )
    accounting = pair.baseline.transfer.terminal_accounting(accounting_text, job)
    assets = snapshot(execution, job)
    errors = []
    try:
        pair.check_execution(execution / "pair_plan.json")
        pair.completion(execution / "pair_plan.json")
        validate_assets(assets, job)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
    status = (
        "terminal_failure"
        if accounting["state"] != "COMPLETED" or accounting["exit_code"] != "0:0"
        else "evidence_rejected"
        if errors
        else "accepted"
    )
    summary = {
        "schema_version": "mvp2-h300-pair-collection-v1",
        "status": status,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "accounting": accounting,
        "preserved_execution": str(execution),
        "acceptance_errors": errors,
        "collector_sha256": pair.sha(Path(__file__)),
        "artifacts": {n: digest(data) for n, data in assets.items()},
        "qualification": "Original validation evidence, no fresh residual or causal-effect claim.",
    }
    blob = (json.dumps(summary, indent=2, allow_nan=False) + "\n").encode()
    assets.update({"collection.json": blob, "accounting.txt": accounting_text.encode()})
    output.mkdir(parents=True, exist_ok=False)
    archive = output / f"h300-pair-evidence-{job}.tar.gz"
    with tarfile.open(archive, "x:gz") as package:
        for name, data in assets.items():
            member = tarfile.TarInfo(name)
            member.size, member.mode = len(data), 0o644
            package.addfile(member, io.BytesIO(data))
    checksum = pair.sha(archive)
    (output / "collection.json").write_bytes(blob)
    (output / f"{archive.name}.sha256").write_text(f"{checksum}  {archive.name}\n")
    return summary, archive, checksum


def safe_assets(archive, checksum):
    pair.require(pair.sha(archive) == checksum, "Archive checksum differs.")
    with tarfile.open(archive, "r:gz") as package:
        members, total = [], 0
        for member in package:
            name = member.name
            pair.require(
                member.isfile()
                and "\\" not in name
                and ":" not in name
                and not name.startswith("/")
                and str(PurePosixPath(name)) == name
                and ".." not in PurePosixPath(name).parts
                and 0 <= member.size <= 128_000_000,
                "Unsafe evidence member.",
            )
            members.append(member)
            total += member.size
            pair.require(
                len(members) <= 200 and total <= 512_000_000,
                "Evidence expansion exceeds bounded review.",
            )
        pair.require(len({m.name for m in members}) == len(members), "Duplicate evidence member.")
        return {m.name: package.extractfile(m).read() for m in members}


def review(archive, checksum):
    assets = safe_assets(archive, checksum)
    collected = json.loads(assets["collection.json"])
    catalog_check(assets, collected["artifacts"])
    pair.require(
        set(assets) == set(collected["artifacts"]) | {"collection.json", "accounting.txt"},
        "Transfer catalog does not cover every member.",
    )
    job = collected["accounting"]["job_id"]
    pair.require(bool(re.fullmatch(r"[0-9]+", job)), "Invalid archived job.")
    allowed = set(names(job)) | {
        "review/pair_policy.json",
        "review/input_policy.json",
        "review/input_snapshot_error.json",
    }
    input_names = {
        "prepared/campaign.yaml",
        "prepared/resource_contrast_plan.json",
        "audit/source_commit.txt",
        "audit/tool_hashes.json",
        "audit/submission.txt",
        "audit/scheduler/job.txt",
        "audit/scheduler/node.txt",
        "audit/worker_status.json",
        "audit/input_size_review.json",
        "audit/preflight/pair_preflight.json",
        "audit/preflight/pair_preflight_diagnostics.json",
        f"audit/slurm-{pair.baseline.policy()['input_job_id']}.out",
        *(f"audit/preflight/{arm}/{n}" for arm in ARMS for n in pair.baseline.inputs.PRODUCTS),
    }
    allowed.update(f"input/{n}" for n in input_names)
    pair.require(set(collected["artifacts"]).issubset(allowed), "Unlisted evidence member.")
    accounting = pair.baseline.transfer.terminal_accounting(assets["accounting.txt"].decode(), job)
    pair.require(accounting == collected["accounting"], "Archived accounting differs.")
    pair.require(
        collected["schema_version"] == "mvp2-h300-pair-collection-v1"
        and collected["collector_sha256"] == pair.sha(Path(__file__)),
        "Collector identity differs.",
    )
    result = {
        "schema_version": "mvp2-h300-pair-review-v1",
        "archive_sha256": checksum,
        "job_id": job,
        "original_collection_status": collected["status"],
    }
    if accounting["state"] != "COMPLETED" or accounting["exit_code"] != "0:0":
        pair.require(collected["status"] == "terminal_failure", "Failure collection misclassified.")
        return {
            **result,
            "status": "terminal_failure_preserved",
            "acceptance_errors": collected["acceptance_errors"],
        }
    pair.require(
        collected["status"] == "accepted" and not collected["acceptance_errors"],
        "Original collection was not accepted.",
    )
    campaign = yaml.safe_load(assets["campaign.yaml"])
    pair.require(
        campaign["output_dir"].replace("\\", "/")
        == collected["preserved_execution"].replace("\\", "/").rstrip("/") + "/runs",
        "Transfer execution output path differs.",
    )
    arms = validate_assets(assets, job)
    return {
        **result,
        "status": "accepted",
        "arms": arms,
        "qualification": "Two original NPAD validation reports verified; no private workbook "
        "read, new optimization or causal performance inference.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("execution", "output-dir", "archive", "review-output"):
        parser.add_argument(f"--{name}", type=Path)
    parser.add_argument("--job-id")
    parser.add_argument("--sha256")
    args = parser.parse_args()
    if args.archive:
        if not args.sha256 or not args.review_output or args.execution or args.output_dir:
            parser.error("Review requires archive/checksum/new review output only.")
        result = review(args.archive, args.sha256)
        pair.write(args.review_output, result)
        print(f"REVIEW_STATUS={result['status']}\nREVIEW={args.review_output}")
        return
    if any(v is None for v in (args.execution, args.output_dir, args.job_id)):
        parser.error("Collection requires execution/new output/job ID.")
    summary, archive, checksum = collect(args.execution, args.output_dir, args.job_id)
    print(f"COLLECTION_STATUS={summary['status']}\nSHA256={checksum}\nDOWNLOAD={archive}")


if __name__ == "__main__":
    main()
