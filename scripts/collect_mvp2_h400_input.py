"""Collect or portably review one terminal h400 input job; no submission API."""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import collect_mvp2_pair_preflight as transfer  # noqa: E402
from scripts import mvp2_h400_input as gate  # noqa: E402
from src.logic.run_integrity import implementation_identity  # noqa: E402


def names(job):
    return {
        "prepared/campaign.yaml", "prepared/input_plan.json", "audit/source_commit.txt",
        "audit/tool_hashes.json", "audit/submission.txt", "audit/scheduler/job.txt",
        "audit/scheduler/node.txt", "audit/worker_status.json", f"audit/slurm-{job}.out",
        "audit/preflight/input_preflight.json", "audit/preflight/input_diagnostics.json",
        *(f"audit/preflight/{gate.ARM}/{name}" for name in gate.PRODUCTS),
    }


def validate(assets, job):
    """Replay closed input gates; absent reference files are not rehashed locally."""
    gate.require(set(assets) == names(job), "Complete allowlisted input evidence required.")
    plan = json.loads(assets["prepared/input_plan.json"])
    receipt = json.loads(assets["audit/preflight/input_preflight.json"])
    worker = json.loads(assets["audit/worker_status.json"])
    diagnostics = json.loads(assets["audit/preflight/input_diagnostics.json"])
    source = assets["audit/source_commit.txt"].decode().strip()
    p = gate.policy()
    gate.require(re.fullmatch(r"[0-9a-f]{40}", source)
                 and source == plan["source_commit"] == receipt["source_commit"],
                 "Source receipt differs.")
    gate.require(plan["schema_version"] == "mvp2-h400-input-plan-v1"
                 and plan["status"] == "prepared_input_only" and plan["case"] == "h400-direct"
                 and plan["scope"] == "input_inspection_only"
                 and plan["optimization_allowed"] is False
                 and all(plan[key] == p[key] for key in (
                     "reference_index", "reference_manifest_sha256",
                     "qualification_report_sha256", "workbook_sha256")), "Pinned plan differs.")
    tools = json.loads(assets["audit/tool_hashes.json"])
    gate.require(tools == gate.tool_identity() == plan["tools"] == receipt["tools"]
                 and plan["policy_sha256"] == receipt["policy_sha256"]
                 == tools[gate.POLICY], "Tool/policy receipt differs.")
    gate.require(plan["implementation"] == receipt["implementation"]
                 and plan["implementation"]["sources"] == implementation_identity()["sources"],
                 "Implementation source differs; runtime receipt must be retained.")
    gate.require(receipt["schema_version"] == "mvp2-h400-input-preflight-v1"
                 and receipt["case"] == "h400-direct" and receipt["status"] == "accepted"
                 and receipt["scope"] == "input_inspection_only"
                 and receipt["optimization_executed"] is False
                 and receipt["large_instance_submission_allowed"] is False
                 and receipt["plan_sha256"] == transfer.digest(assets["prepared/input_plan.json"])
                 and receipt["campaign_sha256"] == plan["campaign_sha256"]
                 == transfer.digest(assets["prepared/campaign.yaml"]), "Input receipt differs.")
    spec = plan["spec"]
    campaign = yaml.safe_load(assets["prepared/campaign.yaml"])
    gate.require(campaign == {
        "version": 1, "output_dir": plan["output_dir"],
        "continue_on_error": False, "experiments": [spec],
    } and campaign["output_dir"].replace("\\", "/").endswith("/prepared/unused_solve_output"),
        "Serialized single control differs.")
    old = gate.historical_profile()
    gate.require(spec["name"] == gate.ARM and spec["metadata"]["warehouse_population"] == 400
                 and spec["metadata"]["mvp2_scope"] == "s1b_h400_input_only"
                 and not spec["calculate_evpi_vss"] and not spec["resume_evpi_vss"]
                 and all(spec[name][key] == value for name in ("model", "loader")
                         for key, value in old[f"{name}_config"].items())
                 and spec["solver"]["compact_python_indices"] is False
                 and spec["solver"]["threads"] == 4 and spec["solver"]["seed"] == 42
                 and spec["solver"]["backend"] == "gurobipy"
                 and spec["solver"]["solver_name"] == "gurobi"
                 and spec["solver"]["time_limit"] == 28800 and spec["solver"]["mip_gap"] == 0.1
                 and spec["solver"]["solver_options"] == {"SoftMemLimit": 128, "NumericFocus": 1}
                 and spec["solver"]["multiobjective_stage_options"]
                 == {r: {"Method": 2} for r in gate.STAGES}, "Control contract differs.")
    resource = receipt["allocation"]
    replayed = gate.inputs.allocation(assets["audit/scheduler/job.txt"].decode(),
                                     assets["audit/scheduler/node.txt"].decode(),
                                     job_id=job, node_name=resource["node"])
    gate.require(replayed == resource, "Allocation receipt differs.")
    gate.require(worker == {
        "schema_version": "mvp2-h400-input-worker-v1", "job_id": job,
        "source_commit": source, "status": "completed", "exit_code": 0,
        "phase": "complete", "optimization_executed": False,
    } and diagnostics == {
        "schema_version": "mvp2-h400-input-diagnostics-v1", "status": "accepted",
        "phase": "complete", "optimization_executed": False,
    }, "Worker/diagnostic closure differs.")
    expected = {f"{gate.ARM}/{name}" for name in gate.PRODUCTS}
    gate.require(set(receipt["artifacts"]) == expected, "Six named input products required.")
    for name, checksum in receipt["artifacts"].items():
        gate.require(transfer.digest(assets[f"audit/preflight/{name}"]) == checksum,
                     f"Input product changed: {name}")
    snapshot, audit, connectivity = [json.loads(assets[f"audit/preflight/{gate.ARM}/{name}"])
                                     for name in gate.PRODUCTS[:3]]
    snapshot.pop("execution", None)
    size = gate.check_snapshot(snapshot, connectivity, audit, guard=spec["max_estimated_variables"])
    gate.require(snapshot == receipt["model_size"] and size == receipt["size_check"],
                 "Reconstructed snapshot/size differs.")
    return {"source_commit": source, "model_size": snapshot, "size_check": size,
            "allocation": resource, "implementation": plan["implementation"]}


def safe_assets(archive, checksum):
    gate.require(transfer.digest(Path(archive).read_bytes()) == checksum,
                 "Archive checksum differs.")
    assets, total = {}, 0
    with tarfile.open(archive, "r:gz") as package:
        for member in package:
            name = member.name
            gate.require(member.isfile() and name not in assets and "\\" not in name
                         and str(PurePosixPath(name)) == name
                         and not PurePosixPath(name).is_absolute()
                         and ".." not in PurePosixPath(name).parts
                         and 0 <= member.size <= 64_000_000, "Unsafe archive member.")
            total += member.size
            gate.require(len(assets) < 40 and total <= 128_000_000, "Archive exceeds review bound.")
            assets[name] = package.extractfile(member).read()
    return assets


def review(archive, checksum):
    assets = safe_assets(archive, checksum)
    collection = json.loads(assets.pop("collection.json"))
    accounting_text = assets.pop("accounting.txt").decode()
    job = collection["accounting"]["job_id"]
    gate.require(re.fullmatch(r"[0-9]+", job) and set(assets).issubset(names(job)),
                 "Unknown archived evidence.")
    gate.require(collection["schema_version"] == "mvp2-h400-input-collection-v1"
                 and collection["collector_sha256"] == transfer.digest(Path(__file__).read_bytes())
                 and collection["artifacts"] == {name: transfer.digest(data)
                                                for name, data in assets.items()}
                 and assets["audit/submission.txt"].decode().strip()
                 == f"MVP2_H400_INPUT_JOB={job}",
                 "Collection identity/hash differs.")
    accounting = transfer.terminal_accounting(accounting_text, job)
    gate.require(collection["accounting"] == accounting, "Terminal accounting differs.")
    if accounting["state"] != "COMPLETED" or accounting["exit_code"] != "0:0":
        gate.require(collection["status"] == "terminal_failure", "Failure misclassified.")
        return {"status": "terminal_failure_preserved", "job_id": job,
                "archive_sha256": checksum, "optimization_allowed": False}
    gate.require(collection["status"] == "accepted" and not collection["acceptance_errors"],
                 "Completed evidence rejected; preserve and diagnose without resubmitting.")
    result = validate(assets, job)
    return {"schema_version": "mvp2-h400-input-review-v1", "status": "accepted", "job_id": job,
            "archive_sha256": checksum, **result, "optimization_allowed": False,
            "qualification": "Original input-only receipts replayed; absent reference/workbook/"
            "qualification files not rehashed locally. No build, solve or solution validation."}


def collect(run, output, job, *, accounting_text=None):
    run, output = Path(run).resolve(), Path(output).resolve()
    gate.require(re.fullmatch(r"[0-9]+", job) and run.is_dir() and not output.exists()
                 and not any(output.is_relative_to(run / name)
                             for name in ("source", "prepared", "audit")),
                 "New collection required.")
    assets = {}
    for name in sorted(names(job)):
        path = run / name
        gate.require(not path.is_symlink() and path.resolve().is_relative_to(run),
                     "Evidence path escapes preserved run.")
        if path.is_file():
            gate.require(path.stat().st_size <= 64_000_000, "Evidence member too large.")
            assets[name] = path.read_bytes()
    gate.require(assets.get("audit/submission.txt", b"").decode().strip()
                 == f"MVP2_H400_INPUT_JOB={job}", "Submission job differs.")
    if accounting_text is None:
        accounting_text = subprocess.check_output([
            "sacct", "-n", "-P", "-j", job,
            "--format=JobIDRaw,State,ExitCode,Elapsed,MaxRSS,NodeList"], text=True)
    accounting = transfer.terminal_accounting(accounting_text, job)
    errors = []
    try:
        validate(assets, job)
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        errors.append(str(error))
    status = "terminal_failure" if accounting["state"] != "COMPLETED" or accounting["exit_code"] \
        != "0:0" else "evidence_rejected" if errors else "accepted"
    summary = {"schema_version": "mvp2-h400-input-collection-v1", "status": status,
               "accounting": accounting, "acceptance_errors": errors,
               "collector_sha256": transfer.digest(Path(__file__).read_bytes()),
               "artifacts": {name: transfer.digest(data) for name, data in assets.items()}}
    output.mkdir(parents=True, exist_ok=False)
    gate.write(output / "collection.json", summary)
    assets.update({"collection.json": (output / "collection.json").read_bytes(),
                   "accounting.txt": accounting_text.encode()})
    archive = output / f"h400-input-evidence-{job}.tar.gz"
    with tarfile.open(archive, "x:gz") as package:
        for name, data in sorted(assets.items()):
            member = tarfile.TarInfo(name)
            member.size, member.mode = len(data), 0o644
            package.addfile(member, io.BytesIO(data))
    checksum = transfer.digest(archive.read_bytes())
    archive.with_name(archive.name + ".sha256").write_text(f"{checksum}  {archive.name}\n")
    return summary, archive, checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run", "output-dir", "archive", "review-output"):
        parser.add_argument(f"--{name}", type=Path)
    for name in ("job-id", "sha256"):
        parser.add_argument(f"--{name}")
    args = parser.parse_args()
    if args.archive:
        gate.require(args.sha256 and args.review_output and not args.run and not args.output_dir,
                     "Review requires archive/checksum/new output only.")
        result = review(args.archive, args.sha256)
        gate.write(args.review_output, result)
        print(f"REVIEW_STATUS={result['status']}\nREVIEW={args.review_output}")
    else:
        summary, archive, checksum = collect(args.run, args.output_dir, args.job_id)
        print(f"COLLECTION_STATUS={summary['status']}\nSHA256={checksum}\nDOWNLOAD={archive}")
        print(f"TRANSFER_ARCHIVE={archive}\nTRANSFER_CHECKSUM={archive}.sha256")


if __name__ == "__main__":
    main()
