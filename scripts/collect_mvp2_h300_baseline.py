"""Collect one terminal h300 baseline, including full named completion products."""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import mvp2_h300_baseline as baseline  # noqa: E402
from scripts.collect_mvp2_pair_preflight import digest, terminal_accounting  # noqa: E402

PRODUCTS = (
    "result.json",
    "run_summary.json",
    "independent_validation.json",
    "model_audit.json",
    "flows.csv",
    "inventories.csv",
    "warehouse_decisions.csv",
    "unmet_demand.csv",
    "emergency_capacity.csv",
    "lexicographic_stages.csv",
    "preflight.json",
    "scenario_performance.csv",
    "material_balance_by_scenario.csv",
    "capacity_gap_by_scenario.csv",
    "investment_saturation.csv",
    "emergency_capacity_daily.csv",
    "evpi_vss_decomposition.csv",
    "storage_by_warehouse.csv",
    "storage_by_scenario.csv",
    "solver_diagnostics.json",
    "solver_stage_progress.csv",
    "solver_presolved_matrix.csv",
    "interhub_connectivity_audit.json",
    "interhub_components.csv",
    "interhub_repair_edges.csv",
    "interhub_path_summary.csv",
    *(
        f"resources/{name}"
        for name in (
            "runtime_capabilities.json",
            "allocation_receipt.json",
            "matrix_statistics.json",
            "resource_timeseries.csv",
            "stage_progress.csv",
            "termination.json",
            "manifest.json",
        )
    ),
)


def snapshot(execution, job):
    names = [
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
        f"slurm-{job}.out",
        *(
            f"comparison/{name}"
            for name in (
                "nine_audit_manifest.json",
                "nine_results.json",
                "nine_results.csv",
                "nine_stage_gaps.json",
                "nine_stage_gaps.csv",
            )
        ),
    ]
    folder = f"runs/{baseline.policy()['experiment_name']}"
    names += [f"{folder}/{name}" for name in (*PRODUCTS, "run_completion.json")]
    assets = {}
    for name in names:
        path = execution / name
        if path.is_symlink() or not path.resolve().is_relative_to(execution):
            raise ValueError(f"Unsafe evidence path: {name}")
        if path.is_file():
            assets[name] = path.read_bytes()
    # Include the small versioned admission policy, never the checkout or a license.
    assets["review/baseline_policy.json"] = (ROOT / baseline.POLICY).read_bytes()
    return assets


def acceptance_errors(execution, job):
    try:
        plan = execution / "baseline_plan.json"
        record, _ = baseline.check_execution(plan)
        admission = baseline.pair.read(execution / "baseline_admission.json")
        closure = baseline.pair.read(execution / "baseline_execution.json")
        source = (execution / "source_commit.txt").read_text().strip()
        baseline.require(bool(re.fullmatch(r"[0-9a-f]{40}", source)), "Invalid execution source.")
        tools = baseline.pair.read(execution / "tool_hashes.json")
        resource = baseline.allocation(
            (execution / "scheduler/job.txt").read_text(),
            (execution / "scheduler/node.txt").read_text(),
            job_id=job,
            node_name=admission["allocation"]["node"],
            cgroup=baseline.pair.read(execution / "cgroup_observation.json"),
        )
        for value in (admission, closure):
            baseline.require(
                value["source_commit"] == source
                and value["baseline_plan_sha256"] == baseline.file_sha256(plan)
                and value["allocation"] == resource
                and value["scope"] == record["scope"],
                "Admission/closure identity drift.",
            )
        baseline.require(
            admission["schema_version"] == "mvp2-h300-baseline-admission-v1"
            and admission["status"] == "admitted"
            and admission["tools"] == tools == baseline.tool_identity()
            and admission["policy_sha256"] == record["policy_sha256"]
            and admission["license_capability_sha256"]
            == baseline.file_sha256(execution / "license_capability.json")
            and baseline.license_accepted(baseline.pair.read(execution / "license_capability.json"))
            and admission["production_explicit_lifecycle_allowed"] is False
            and closure["schema_version"] == "mvp2-h300-baseline-execution-v1"
            and closure["optimization_attempted"] is True
            and closure["control_return_code"] == closure["audit_return_code"] == 0,
            "Execution is not a closed admitted control baseline.",
        )
        worker = baseline.pair.read(execution / "worker_status.json")
        baseline.require(
            worker["job_id"] == job
            and worker["status"] == "completed"
            and worker["phase"] == "complete"
            and worker["exit_code"] == 0,
            "Worker did not close successfully.",
        )
        completed = baseline.completion(plan)
        baseline.require(
            set(completed["artifacts"]) == set(PRODUCTS),
            "Require all 33 named completion products.",
        )
        return []
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return [f"{type(exc).__name__}: {exc}"]


def collect(execution, output, job, *, accounting_text=None):
    execution, output = Path(execution).resolve(), Path(output).resolve()
    baseline.require(bool(re.fullmatch(r"[0-9]+", job)), "Require numeric standalone job.")
    baseline.require(
        execution.is_dir()
        and not output.exists()
        and not output.is_relative_to(execution)
        and not execution.is_relative_to(output)
        and not output.is_relative_to(ROOT),
        "Choose new isolated collection output.",
    )
    if (execution / "baseline_plan.json").is_file():
        original = Path(baseline.pair.read(execution / "baseline_plan.json")["input_run"]).resolve()
        baseline.require(
            not output.is_relative_to(original) and not original.is_relative_to(output),
            "Collection must not modify preserved input evidence.",
        )
    baseline.require(
        (execution / "submission.txt").read_text().strip() == f"MVP2_H300_BASELINE_JOB={job}",
        "Submission does not identify this job.",
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
    accounting = terminal_accounting(accounting_text, job)
    errors = acceptance_errors(execution, job)
    assets = snapshot(execution, job)
    status = (
        "terminal_failure"
        if accounting["state"] != "COMPLETED" or accounting["exit_code"] != "0:0"
        else "evidence_rejected"
        if errors
        else "accepted"
    )
    summary = {
        "schema_version": "mvp2-h300-baseline-collection-v1",
        "status": status,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "accounting": accounting,
        "preserved_execution": str(execution),
        "acceptance_errors": errors,
        "collector_sha256": digest(Path(__file__).read_bytes()),
        "artifacts": {name: digest(data) for name, data in assets.items()},
        "qualification": "A terminal archive is not acceptance; failure evidence is preserved too.",
    }
    data = (json.dumps(summary, indent=2, allow_nan=False) + "\n").encode()
    assets.update({"collection.json": data, "accounting.txt": accounting_text.encode()})
    output.mkdir(parents=True, exist_ok=False)
    archive = output / f"h300-baseline-evidence-{job}.tar.gz"
    with tarfile.open(archive, "x:gz") as package:
        for name, blob in assets.items():
            member = tarfile.TarInfo(name)
            member.size, member.mode = len(blob), 0o644
            package.addfile(member, io.BytesIO(blob))
    checksum = digest(archive.read_bytes())
    (output / "collection.json").write_bytes(data)
    (output / f"{archive.name}.sha256").write_text(f"{checksum}  {archive.name}\n")
    return summary, archive, checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--job-id", required=True)
    args = parser.parse_args()
    summary, archive, checksum = collect(args.execution, args.output_dir, args.job_id)
    print(f"COLLECTION_STATUS={summary['status']}\nSHA256={checksum}\nDOWNLOAD={archive}")


if __name__ == "__main__":
    main()
