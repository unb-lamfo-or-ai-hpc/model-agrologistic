"""Package successful or failed terminal input jobs without submitting a job."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path

PRODUCTS = (
    "preflight.json", "model_audit.json", "interhub_connectivity_audit.json",
    "interhub_components.csv", "interhub_repair_edges.csv", "interhub_path_summary.csv",
)
TERMINAL = {
    "COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL",
    "PREEMPTED", "BOOT_FAIL", "DEADLINE", "REVOKED",
}


def terminal_accounting(text, job_id):
    rows = [line.split("|") for line in text.splitlines() if line.strip()]
    matching = [row for row in rows if row[0].strip() == job_id]
    if len(matching) != 1 or len(matching[0]) < 3:
        raise ValueError("Require one exact root job accounting row.")
    row = matching[0]
    if not row[1].strip():
        raise ValueError("Accounting state is missing.")
    state = row[1].strip().split()[0].rstrip("+")
    if state not in TERMINAL:
        raise ValueError(f"Job {job_id} is not terminal: {state}")
    return {"job_id": job_id, "state": state, "exit_code": row[2].strip()}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def evidence_snapshot(run, job_id):
    """Read only named audit products; never traverse a checkout or license file."""
    names = [
        "prepared/campaign.yaml", "prepared/resource_contrast_plan.json",
        "audit/source_commit.txt", "audit/tool_hashes.json", "audit/submission.txt",
        "audit/scheduler/job.txt", "audit/scheduler/node.txt", "audit/worker_status.json",
        "audit/input_size_review.json",
        f"audit/slurm-{job_id}.out", "audit/preflight/pair_preflight.json",
        "audit/preflight/pair_preflight_diagnostics.json",
    ]
    names += [
        f"audit/preflight/mvp2_{case}_{arm}/{product}"
        for case in ("h215_warehouse", "h300_warehouse")
        for arm in ("control", "compact") for product in PRODUCTS
    ]
    assets = {}
    for name in names:
        path = run / name
        if path.is_symlink() or not path.resolve().is_relative_to(run):
            raise ValueError(f"Evidence path escapes the run or is a symlink: {name}")
        if path.is_file():
            assets[name] = path.read_bytes()
    return assets


def receipt_errors(assets, job_id):
    """Separate terminal success and input receipt integrity from archive creation."""
    try:
        receipt = json.loads(assets["audit/preflight/pair_preflight.json"])
        plan = json.loads(assets["prepared/resource_contrast_plan.json"])
        tools = json.loads(assets["audit/tool_hashes.json"])
        errors = []
        for label, valid in (
            ("receipt schema", receipt.get("schema_version")
             == "mvp2-resource-pair-preflight-v1"),
            ("accepted receipt", receipt.get("status") == "accepted"),
            ("input-only receipt", receipt.get("optimization_executed") is False
             and receipt.get("large_instance_submission_allowed") is False),
            ("case identity", receipt.get("case", "h215-warehouse") == plan["case"]
             and plan["case"] in ("h215-warehouse", "h300-warehouse")),
            ("job identity", str(receipt["allocation"]["job_id"]) == job_id),
            ("plan hash", receipt["plan_sha256"]
             == digest(assets["prepared/resource_contrast_plan.json"])),
            ("campaign hash", receipt["campaign_sha256"]
             == digest(assets["prepared/campaign.yaml"])),
            ("submitted tools", receipt["tools"] == tools),
        ):
            if not valid:
                errors.append(label)
        size_checks = receipt.get("size_checks", {})
        if plan["case"] == "h300-warehouse":
            required_arms = {f"mvp2_h300_warehouse_{arm}" for arm in ("control", "compact")}
            if (set(size_checks) != required_arms or any(
                type(check.get("total_variables")) is not int
                or type(check.get("reference_limit")) is not int
                or check["total_variables"] <= 0 or check["reference_limit"] <= 0
                or check["total_variables"] != receipt["model_size"]["total_variables"]
                or check.get("within_reference_limit") is not
                (check["total_variables"] <= check["reference_limit"])
                or (check["total_variables"] > check["reference_limit"]
                    and not check.get("input_size_review"))
                or check.get("scope") != "input_inspection_only"
                or check.get("optimization_allowed") is not False
                for check in size_checks.values()
            )):
                errors.append("two complete input-only size checks")
        if any(check.get("input_size_review") for check in size_checks.values()):
            review_bytes = assets["audit/input_size_review.json"]
            review = json.loads(review_bytes)
            expected_arms = {f"mvp2_h300_warehouse_{arm}" for arm in ("control", "compact")}
            if (plan["case"] != "h300-warehouse"
                    or digest(review_bytes) != tools["docs/mvp2_h300_input_size_review.json"]
                    or review.get("schema_version") != "mvp2-input-size-review-v1"
                    or review.get("scope") != "input_inspection_only"
                    or review.get("optimization_allowed") is not False
                    or any(plan.get(key) != value for key, value in review["plan_fields"].items())
                    or any(receipt["model_size"].get(key) != value
                           for key, value in review["snapshot_fields"].items())
                    or receipt["model_size"]["data_signature"]["counts"] != review["counts"]
                    or any(receipt["artifacts"].get(f"{arm}/{name}") != value
                           for arm in expected_arms
                           for name, value in review["audit_sha256"].items())
                    or set(size_checks) != expected_arms
                    or any(check.get("input_size_review") != review["review_id"]
                           or check.get("total_variables")
                           != review["snapshot_fields"]["total_variables"]
                           or check.get("reference_limit") != review["reference_limit"]
                           or check.get("excess_variables") != check["total_variables"]
                           - check["reference_limit"] or check["excess_variables"] <= 0
                           or check.get("scope") != "input_inspection_only"
                           or check.get("within_reference_limit") is not False
                           or check.get("optimization_allowed") is not False
                           for check in size_checks.values())):
                errors.append("reviewed input-only size profile")
        expected = {
            f"mvp2_{plan['case'].replace('-', '_')}_{arm}/{product}"
            for arm in ("control", "compact") for product in PRODUCTS
        }
        artifacts = receipt["artifacts"]
        if set(artifacts) != expected:
            errors.append("twelve expected input products")
        for name in expected:
            asset = assets.get(f"audit/preflight/{name}")
            if asset is None or digest(asset) != artifacts.get(name):
                errors.append(f"artifact hash: {name}")
        return errors
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        return [f"Missing or malformed receipt evidence: {error}"]


def collect(run_dir, output_dir, job_id, *, accounting_text=None):
    if not re.fullmatch(r"[0-9]+", job_id):
        raise ValueError("Require a numeric standalone job ID.")
    run, output = Path(run_dir).resolve(), Path(output_dir).resolve()
    if not run.is_dir() or output.exists() or any(
        output.is_relative_to(run / folder) for folder in ("audit", "prepared", "source")
    ):
        raise ValueError("Require a preserved run and a new collection directory.")
    assets = evidence_snapshot(run, job_id)
    submission = assets.get("audit/submission.txt", b"").decode("utf-8").strip()
    if submission != f"MVP2_PAIR_PREFLIGHT_JOB={job_id}":
        raise ValueError("The preserved submission does not identify this job.")
    if accounting_text is None:
        accounting_text = subprocess.check_output([
            "sacct", "-n", "-P", "-j", job_id,
            "--format=JobIDRaw,State,ExitCode,Elapsed,MaxRSS,NodeList",
        ], text=True)
    accounting = terminal_accounting(accounting_text, job_id)
    errors = receipt_errors(assets, job_id)
    status = (
        "terminal_failure" if accounting["state"] != "COMPLETED"
        or accounting["exit_code"] != "0:0" else
        "receipt_rejected" if errors else "accepted"
    )
    summary = {
        "schema_version": "mvp2-input-preflight-collection-v1",
        "status": status, "scope": "terminal_input_job_evidence",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "preserved_run": str(run), "accounting": accounting,
        "receipt_validation_errors": errors,
        "source_commit": assets.get("audit/source_commit.txt", b"").decode().strip(),
        "collector_sha256": digest(Path(__file__).read_bytes()),
        "artifacts": {name: digest(data) for name, data in assets.items()},
        "qualification": "Packaging a failed job does not accept its input or admit a solve.",
    }
    output.mkdir(parents=True, exist_ok=False)
    summary_bytes = (json.dumps(summary, indent=2) + "\n").encode()
    assets.update({"collection.json": summary_bytes,
                   "accounting.txt": accounting_text.encode()})
    archive = output / f"input-preflight-evidence-{job_id}.tar.gz"
    with tarfile.open(archive, "x:gz") as package:
        for name, data in assets.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            package.addfile(info, io.BytesIO(data))
    checksum = digest(archive.read_bytes())
    (output / "collection.json").write_bytes(summary_bytes)
    (output / f"{archive.name}.sha256").write_text(f"{checksum}  {archive.name}\n")
    return summary, archive, checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    args = parser.parse_args()
    summary, archive, checksum = collect(args.run_dir, args.output_dir, args.job_id)
    print(f"COLLECTION_STATUS={summary['status']}")
    print(f"SHA256={checksum}")
    print(f"DOWNLOAD={archive}")


if __name__ == "__main__":
    main()
