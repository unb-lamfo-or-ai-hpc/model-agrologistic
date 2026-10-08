"""Preserve terminal h400 control evidence and replay original quality certificates."""

from __future__ import annotations

import argparse
import copy
import csv
import io
import json
import math
import re
import subprocess
import sys
import tarfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import mvp2_h400_control as control  # noqa: E402
from scripts.audit_nine_campaign import classify_stages  # noqa: E402
from scripts.collect_mvp2_h300_baseline import PRODUCTS  # noqa: E402
from src.logic.mathematical_contract import canonical_hash  # noqa: E402

INPUT = "input/accepted_h400_input.tar.gz"


def names(job):
    return {
        "control_plan.json",
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
        "control_admission.json",
        "control_execution.json",
        "logs/control.out",
        "logs/control-exit.json",
        "logs/audit.out",
        f"slurm-{job}.out",
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
        *(
            f"runs/{control.policy()['experiment_name']}/{n}"
            for n in (*PRODUCTS, "run_completion.json")
        ),
        INPUT,
        "review/control_policy.json",
        "review/input_snapshot_error.json",
    }


def snapshot(execution, job):
    assets = {}
    for n in names(job) - {INPUT, "review/control_policy.json", "review/input_snapshot_error.json"}:
        path = execution / n
        control.require(
            not path.is_symlink() and path.resolve().is_relative_to(execution),
            "Evidence escapes run.",
        )
        if path.is_file():
            control.require(path.stat().st_size <= 128_000_000, "Evidence member exceeds bound.")
            assets[n] = path.read_bytes()
    assets["review/control_policy.json"] = json.dumps(control.policy(), indent=2).encode()
    try:
        path = Path(control.read(execution / "control_plan.json")["input_archive"])
        control.require(
            not path.is_symlink() and path.stat().st_size <= 128_000_000,
            "Unsafe original input archive.",
        )
        assets[INPUT] = path.read_bytes()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        assets["review/input_snapshot_error.json"] = json.dumps(
            {"exception_type": type(exc).__name__}
        ).encode()
    return assets


def catalog(assets, hashes):
    control.require(isinstance(hashes, dict) and bool(hashes), "Missing artifact catalog.")
    for n, checksum in hashes.items():
        control.require(n in assets and control.digest(assets[n]) == checksum, f"Hash differs: {n}")


def validate(assets, job):
    def read(n):
        return json.loads(assets[n])

    expected = names(job) - {"review/input_snapshot_error.json"}
    control.require(set(assets) == expected, "Complete single-control evidence required.")
    p = control.policy()
    original = control.original_assets(assets[INPUT])
    receipt = json.loads(original["audit/preflight/input_preflight.json"])
    control.require(read("review/control_policy.json") == p, "Transfer policy differs.")
    plan, admission, closure = [
        read(n) for n in ("control_plan.json", "control_admission.json", "control_execution.json")
    ]
    tools, source = read("tool_hashes.json"), assets["source_commit.txt"].decode().strip()
    control.require(
        bool(re.fullmatch(r"[0-9a-f]{40}", source))
        and source == plan["source_commit"]
        and assets["submission.txt"].decode().strip() == f"MVP2_H400_CONTROL_JOB={job}"
        and tools == plan["tools"] == admission["tools"] == control.tool_identity(),
        "Source/submission/tool drift.",
    )
    control.require(
        plan["schema_version"] == "mvp2-h400-control-plan-v1"
        and plan["status"] == "prepared_not_admitted"
        and plan["scope"] == p["scope"]
        and plan["policy_identity"] == control.policy_identity()
        and plan["allocation_profile"] == p["allocation_profile"]
        and plan["input_archive_sha256"] == p["input_archive_sha256"]
        and plan["automatic_repeats_allowed"] is False
        and plan["production_explicit_lifecycle_allowed"] is False
        and plan["campaign_sha256"] == control.digest(assets["campaign.yaml"])
        and plan["input_accounting_sha256"] == control.digest(assets["input_accounting.txt"])
        and control.inputs.transfer.terminal_accounting(
            assets["input_accounting.txt"].decode(), p["input_job_id"]
        )
        == {"job_id": p["input_job_id"], "state": "COMPLETED", "exit_code": "0:0"},
        "Plan/accounting identity differs.",
    )
    campaign = yaml.safe_load(assets["campaign.yaml"])
    expected_campaign = control.campaign_from_original(
        yaml.safe_load(original["prepared/campaign.yaml"]),
        Path(plan["input_run"]).parent / "unused",
    )
    expected_campaign["output_dir"] = campaign["output_dir"]
    control.require(
        campaign == expected_campaign, "Control derivation changed beyond reviewed scope."
    )
    resource = control.allocation(
        assets["scheduler/job.txt"].decode(),
        assets["scheduler/node.txt"].decode(),
        job_id=job,
        node_name=admission["allocation"]["node"],
        cgroup=read("cgroup_observation.json"),
    )
    control.require(
        all(
            r["source_commit"] == source
            and r["allocation"] == resource
            and r["scope"] == p["scope"]
            and r["control_plan_sha256"] == control.digest(assets["control_plan.json"])
            for r in (admission, closure)
        )
        and admission["schema_version"] == "mvp2-h400-control-admission-v1"
        and admission["status"] == "admitted"
        and admission["policy_identity"] == control.policy_identity()
        and admission["automatic_repeats_allowed"] is False
        and admission["production_explicit_lifecycle_allowed"] is False
        and admission["license_capability_sha256"]
        == control.digest(assets["license_capability.json"])
        and control.shared.license_accepted(read("license_capability.json"))
        and closure["schema_version"] == "mvp2-h400-control-execution-v1"
        and closure["status"] == "process_returned"
        and closure["optimization_attempted"] is True
        and closure["control_return_code"] == closure["audit_return_code"] == 0,
        "Fresh resource/license/admission/execution closure failed.",
    )
    control.require(
        read("worker_status.json")
        == {
            "schema_version": "mvp2-h400-control-worker-v1",
            "job_id": job,
            "source_commit": source,
            "phase": "complete",
            "exit_code": 0,
            "status": "completed",
        }
        and read("logs/control-exit.json") == {"index": 0, "return_code": 0},
        "Worker exit differs.",
    )
    audit = read("comparison/nine_audit_manifest.json")
    control.require(
        audit["overall_status"] == "accepted"
        and audit["selected_indices"] == [0]
        and audit["accepted_instance_count"] == audit["campaign_instance_count"] == 1
        and audit["manifest_sha256"] == plan["campaign_sha256"]
        and audit["audit_script_sha256"] == tools["scripts/audit_nine_campaign.py"],
        "Complete single-control hierarchical audit required.",
    )
    prefix = f"runs/{p['experiment_name']}/"
    completed = read(prefix + "run_completion.json")
    control.require(
        completed["schema_version"] == 1
        and completed["status"] == "complete"
        and set(completed["artifacts"]) == set(PRODUCTS),
        "33 closed products required.",
    )
    catalog(assets, {prefix + n: h for n, h in completed["artifacts"].items()})
    result = read(prefix + "result.json")
    spec, metadata = result["experiment"], result["result"]["metadata"]
    implementation = metadata["implementation_identity"]
    control.require(
        implementation == receipt["implementation"]
        and canonical_hash({k: v for k, v in implementation.items() if k != "sha256"})
        == implementation["sha256"]
        == p["implementation_sha256"],
        "Original runtime identity differs.",
    )
    control.require(
        all(
            spec[n] == campaign["experiments"][0][n]
            for n in (
                "name",
                "workbook",
                "loader",
                "model",
                "solver",
                "metadata",
                "max_estimated_variables",
            )
        )
        and spec["workbook_sha256"] == receipt["model_size"]["workbook_sha256"]
        and spec["calculate_evpi_vss"] is False
        and spec["resume_evpi_vss"] is False,
        "Serialized model/solver/workbook contract differs.",
    )
    payload = copy.deepcopy(spec)
    payload.pop("resume_evpi_vss", None)
    payload["implementation"] = implementation["sha256"]
    identity = control.digest(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )
    control.require(
        identity == completed["run_identity"] == metadata["run_identity"],
        "Original run identity differs.",
    )
    preflight = read(prefix + "preflight.json")
    preflight.pop("execution", None)
    control.require(preflight == receipt["model_size"], "Solved input dimensions differ.")
    control.shared.check_solved_model_audit(
        json.loads(original[f"audit/preflight/{p['experiment_name']}/model_audit.json"]),
        read(prefix + "model_audit.json"),
    )
    control.require(
        all(
            control.digest(assets[prefix + n])
            == receipt["artifacts"][f"{p['experiment_name']}/{n}"]
            for n in control.inputs.gate.PRODUCTS[1:]
            if n != "model_audit.json"
        ),
        "Solved connectivity products differ.",
    )
    validator = read(prefix + "independent_validation.json")
    control.require(
        validator["status"] == metadata["independent_validation_status"] == "accepted"
        and validator["failed_check_count"] == 0
        and validator["failure_samples"] == []
        and bool(validator["families"])
        and all(
            r["failed"] == 0 and r["checked"] > 0 and math.isfinite(r["max_residual"])
            for r in validator["families"].values()
        )
        and validator["mathematical_contract"] == metadata["mathematical_contract"],
        "Original independent validation failed.",
    )
    stages = metadata["lexicographic_stages"]
    control.require(
        classify_stages(stages, validator["status"]) == "accepted_at_ten_percent"
        and stages
        == [
            {k: v for k, v in s.items() if k != "name"}
            for s in read("comparison/nine_stage_gaps.json")
            if s["name"] == p["experiment_name"]
        ],
        "Hierarchy incomplete or outside the inherited ten-percent contract.",
    )
    manifest = read(prefix + "resources/manifest.json")
    control.require(
        manifest["status"] == "closed" and len(manifest["artifacts"]) == 6,
        "Resource manifest not closed.",
    )
    catalog(assets, {prefix + "resources/" + n: h for n, h in manifest["artifacts"].items()})
    rows = list(
        csv.DictReader(io.StringIO(assets[prefix + "resources/resource_timeseries.csv"].decode()))
    )
    progress = list(
        csv.DictReader(io.StringIO(assets[prefix + "resources/stage_progress.csv"].decode()))
    )
    termination = read(prefix + "resources/termination.json")
    control.require(
        bool(rows)
        and termination["exception_type"] is None
        and termination["inspection_errors"] == []
        and termination["dropped_samples"] == {"resource": 0, "progress": 0}
        and termination["samples"] == {"resource": len(rows), "progress": len(progress)}
        and all(
            not r["observation_errors"]
            and int(r["cgroup_limit_bytes"]) == p["allocation_profile"]["cgroup_limit_bytes"]
            for r in rows
        )
        and not any(r["event"] == "python_index_compaction" for r in progress)
        and read(prefix + "resources/runtime_capabilities.json")["sampling_solver_api_calls"]
        is False,
        "Telemetry/control isolation failed.",
    )
    times = [float(r["elapsed_seconds"]) for r in rows]
    control.require(
        all(math.isfinite(t) and t >= 0 for t in times) and times == sorted(times),
        "Invalid telemetry timestamps.",
    )
    phase_peaks = {}
    for r in rows:
        stats = phase_peaks.setdefault(
            r["phase"], {"samples": 0, "tree_rss_gib": 0, "cgroup_gib": 0}
        )
        stats["samples"] += 1
        stats["tree_rss_gib"] = max(stats["tree_rss_gib"], int(r["process_tree_rss_bytes"]) / 2**30)
        stats["cgroup_gib"] = max(stats["cgroup_gib"], int(r["cgroup_current_bytes"]) / 2**30)
    native = [
        float(r["solver_memory_bytes"]) / 2**30 for r in progress if r.get("solver_memory_bytes")
    ]
    return {
        "source_commit": source,
        "run_identity": identity,
        "summary": read(prefix + "run_summary.json"),
        "stages": stages,
        "validation_families": len(validator["families"]),
        "model_findings": read(prefix + "model_audit.json")["findings"],
        "matrix": read(prefix + "resources/matrix_statistics.json"),
        "phase_peaks": phase_peaks,
        "termination": termination,
        "peak_reported_native_memory_gib": max(native) if native else None,
        "maximum_sampling_gap_seconds": max(
            (b - a for a, b in zip(times, times[1:], strict=False)), default=None
        ),
    }


def collect(execution, output, job, *, accounting_text=None):
    execution, output = Path(execution).resolve(), Path(output).resolve()
    protected = [execution, ROOT]
    try:
        protected.append(Path(control.read(execution / "control_plan.json")["input_run"]).resolve())
    except (OSError, ValueError, KeyError, TypeError):
        pass  # A malformed plan remains transferable failure evidence.
    control.require(
        bool(re.fullmatch(r"[0-9]+", job))
        and not output.exists()
        and not any(output.is_relative_to(p) or p.is_relative_to(output) for p in protected),
        "New isolated collection required.",
    )
    control.require(
        (execution / "submission.txt").read_text().strip() == f"MVP2_H400_CONTROL_JOB={job}",
        "Submission differs.",
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
    accounting = control.inputs.transfer.terminal_accounting(accounting_text, job)
    assets, errors = snapshot(execution, job), []
    try:
        control.check_execution(execution / "control_plan.json")
        validate(assets, job)
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
        "schema_version": "mvp2-h400-control-collection-v1",
        "status": status,
        "accounting": accounting,
        "preserved_execution": str(execution),
        "collector_sha256": control.sha(Path(__file__)),
        "acceptance_errors": errors,
        "artifacts": {n: control.digest(v) for n, v in assets.items()},
    }
    output.mkdir(parents=True)
    control.write(output / "collection.json", summary)
    assets.update(
        {
            "collection.json": (output / "collection.json").read_bytes(),
            "accounting.txt": accounting_text.encode(),
        }
    )
    archive = output / f"h400-control-evidence-{job}.tar.gz"
    with tarfile.open(archive, "x:gz") as package:
        for n, data in sorted(assets.items()):
            member = tarfile.TarInfo(n)
            member.size, member.mode = len(data), 0o644
            package.addfile(member, io.BytesIO(data))
    checksum = control.sha(archive)
    (output / f"{archive.name}.sha256").write_text(f"{checksum}  {archive.name}\n")
    return summary, archive, checksum


def review(archive, checksum):
    archive = Path(archive)
    control.require(archive.stat().st_size <= 128_000_000, "Archive exceeds compressed bound.")
    assets = control.safe_payload(archive.read_bytes(), checksum)
    collected = json.loads(assets.pop("collection.json"))
    accounting_text = assets.pop("accounting.txt").decode()
    job = collected["accounting"]["job_id"]
    control.require(
        bool(re.fullmatch(r"[0-9]+", job))
        and set(assets).issubset(names(job))
        and collected["schema_version"] == "mvp2-h400-control-collection-v1"
        and collected["collector_sha256"] == control.sha(Path(__file__))
        and collected["artifacts"] == {n: control.digest(v) for n, v in assets.items()}
        and assets["submission.txt"].decode().strip() == f"MVP2_H400_CONTROL_JOB={job}",
        "Collection identity/catalog differs.",
    )
    accounting = control.inputs.transfer.terminal_accounting(accounting_text, job)
    control.require(accounting == collected["accounting"], "Terminal accounting differs.")
    base = {
        "schema_version": "mvp2-h400-control-review-v1",
        "job_id": job,
        "archive_sha256": checksum,
        "original_collection_status": collected["status"],
    }
    if accounting["state"] != "COMPLETED" or accounting["exit_code"] != "0:0":
        control.require(collected["status"] == "terminal_failure", "Failure misclassified.")
        return {
            **base,
            "status": "terminal_failure_preserved",
            "acceptance_errors": collected["acceptance_errors"],
        }
    control.require(
        collected["status"] == "accepted" and not collected["acceptance_errors"],
        "Original completed collection rejected; preserve without resubmission.",
    )
    campaign = yaml.safe_load(assets["campaign.yaml"])
    control.require(
        campaign["output_dir"].replace("\\", "/")
        == collected["preserved_execution"].replace("\\", "/").rstrip("/") + "/runs",
        "Output path differs.",
    )
    return {
        **base,
        "status": "accepted",
        **validate(assets, job),
        "qualification": "Original NPAD solution validation and hierarchy certificates replayed; "
        "no private workbook reload, new residual computation or causal performance claim.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("execution", "output-dir", "archive", "review-output"):
        p.add_argument(f"--{n}", type=Path)
    for n in ("job-id", "sha256"):
        p.add_argument(f"--{n}")
    args = p.parse_args()
    if args.archive:
        control.require(
            args.sha256 and args.review_output and not args.execution,
            "Review requires checksum/new output only.",
        )
        r = review(args.archive, args.sha256)
        control.write(args.review_output, r)
        print(f"REVIEW_STATUS={r['status']}\nREVIEW={args.review_output}")
    else:
        control.require(
            args.execution and args.output_dir and args.job_id, "Collection arguments missing."
        )
        r, archive, checksum = collect(args.execution, args.output_dir, args.job_id)
        print(f"COLLECTION_STATUS={r['status']}\nSHA256={checksum}\nDOWNLOAD={archive}")
        print(f"TRANSFER_ARCHIVE={archive}\nTRANSFER_CHECKSUM={archive}.sha256")


if __name__ == "__main__":
    main()
