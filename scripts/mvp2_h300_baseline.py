"""Qualify one h300 control baseline without extending the h215 pair admitter."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import admit_mvp2_resource_pair as pair  # noqa: E402
from scripts import collect_mvp2_pair_preflight as transfer  # noqa: E402
from scripts import preflight_mvp2_resource_pair as inputs  # noqa: E402
from src.logic.experiment_runner import _checkpoint_identity, load_experiment_manifest  # noqa: E402
from src.logic.resource_telemetry import cgroup_memory  # noqa: E402
from src.logic.run_integrity import file_sha256, verify_completion  # noqa: E402

POLICY = "docs/mvp2_h300_baseline_policy.json"
TOOLS = (
    *pair.TOOLS,
    "scripts/collect_mvp2_pair_preflight.py",
    POLICY,
    "scripts/mvp2_h300_baseline.py",
    "scripts/submit_mvp2_h300_baseline.sh",
    "scripts/run_mvp2_h300_baseline.slurm",
    "scripts/collect_mvp2_h300_baseline.py",
    "scripts/npad_mvp2_h300_baseline.sh",
)


def policy():
    return pair.read(ROOT / POLICY)


def tool_identity():
    return {name: file_sha256(ROOT / name) for name in TOOLS}


def require(valid, reason):
    if not valid:
        raise ValueError(reason)


def license_accepted(capability):
    """One capability contract is used both at admission and terminal collection."""
    return (
        capability.get("status") == "accepted"
        and capability.get("schema_version") == "npad-gurobi-license-capability-v1"
        and capability.get("license_file") == pair.LICENSE_FILE
        and capability.get("large_model_construction_allowed") is True
        and capability.get("probe_variable_count") == pair.PROBE_SIZE
        and capability.get("probe_constraint_count") == pair.PROBE_SIZE
        and capability.get("solver_status_code") == 2
        and type(capability.get("objective_value")) in (int, float)
        and abs(capability["objective_value"] - pair.PROBE_SIZE) <= 1e-6
    )


def check_inputs(run):
    """Recheck the reviewed original receipt and qualification, never rewrite them."""
    run = Path(run).resolve()
    review = policy()
    plan_path = run / "prepared/resource_contrast_plan.json"
    receipt_path = run / "audit/preflight/pair_preflight.json"
    require(file_sha256(plan_path) == review["input_plan_sha256"], "Input plan changed.")
    require(file_sha256(receipt_path) == review["input_receipt_sha256"], "Input receipt changed.")
    plan, manifest = inputs.check_plan(plan_path)
    assets = transfer.evidence_snapshot(run, review["input_job_id"])
    require(
        not transfer.receipt_errors(assets, review["input_job_id"]),
        "Original paired input products or size review changed.",
    )
    receipt = pair.read(receipt_path)
    require(
        plan["case"] == "h300-warehouse"
        and receipt["implementation"]["sha256"] == review["implementation_sha256"]
        and receipt["tools"] == inputs.tool_identity()
        and assets["audit/source_commit.txt"].decode().strip() == review["input_source_commit"]
        and assets["audit/submission.txt"].decode().strip()
        == f"MVP2_PAIR_PREFLIGHT_JOB={review['input_job_id']}"
        and transfer.digest(assets["audit/input_size_review.json"])
        == review["input_review_sha256"],
        "Input source/tool/review identity changed.",
    )
    observed = inputs.allocation(
        assets["audit/scheduler/job.txt"].decode(),
        assets["audit/scheduler/node.txt"].decode(),
        job_id=review["input_job_id"],
        node_name=receipt["allocation"]["node"],
    )
    require(observed == receipt["allocation"], "Original scheduler allocation changed.")
    worker = json.loads(assets["audit/worker_status.json"])
    diagnostics = json.loads(assets["audit/preflight/pair_preflight_diagnostics.json"])
    require(
        worker.get("status") == "completed"
        and worker.get("exit_code") == 0
        and worker.get("job_id") == review["input_job_id"]
        and worker.get("optimization_executed") is False
        and diagnostics.get("status") == "accepted"
        and diagnostics.get("optimization_executed") is False
        and diagnostics.get("size_checks") == receipt["size_checks"],
        "Original input worker/diagnostics did not close.",
    )
    for spec in manifest.experiments:
        folder = receipt_path.parent / spec.name
        snapshot = pair.read(folder / "preflight.json")
        snapshot.pop("execution")
        hashes = {name: file_sha256(folder / name) for name in inputs.PRODUCTS[1:]}
        size = inputs.check_snapshot(
            plan,
            spec,
            snapshot,
            pair.read(folder / "interhub_connectivity_audit.json"),
            audit_hashes=hashes,
        )
        require(
            snapshot == receipt["model_size"]
            and size == receipt["size_checks"][spec.name]
            and snapshot["total_variables"] == review["execution_limit"]
            and spec.max_estimated_variables == review["reference_limit"],
            "Exact reviewed h300 dimensions changed.",
        )
    return plan, receipt


def derived_campaign(run, destination):
    """Change only the explicitly reviewed execution envelope, not mathematics."""
    review = policy()
    original = yaml.safe_load((Path(run) / "prepared/campaign.yaml").read_text())
    control = copy.deepcopy(original["experiments"][0])
    require(
        control["name"] == "mvp2_h300_warehouse_control"
        and control["solver"]["compact_python_indices"] is False,
        "Require the original uncompacted control.",
    )
    control["name"] = review["experiment_name"]
    control["max_estimated_variables"] = review["execution_limit"]
    control["metadata"].update(
        resource_contrast_arm="baseline_control",
        resource_contrast_scope=review["scope"],
        baseline_size_review=review["review_id"],
    )
    return {
        "version": 1,
        "output_dir": str(Path(destination) / "runs"),
        "continue_on_error": False,
        "experiments": [control],
    }


def protect(destination, run, plan):
    destination, run = Path(destination).resolve(), Path(run).resolve()
    protected = (
        ROOT,
        run,
        Path(plan["reference_manifest"]).resolve().parent,
        Path(plan["qualification_report"]).resolve().parent,
    )
    require(
        not any(destination.is_relative_to(p) or p.is_relative_to(destination) for p in protected),
        "Execution overlaps source or preserved evidence.",
    )


def prepare(run, destination, accounting_text):
    run, destination = Path(run).resolve(), Path(destination).resolve()
    review = policy()
    require(
        transfer.terminal_accounting(accounting_text, review["input_job_id"])
        == {"job_id": review["input_job_id"], "state": "COMPLETED", "exit_code": "0:0"},
        "Original input job lacks successful terminal accounting.",
    )
    plan, _ = check_inputs(run)
    protect(destination, run, plan)
    require(not destination.exists(), "Choose a new execution directory.")
    destination.mkdir(parents=True, exist_ok=False)
    raw = derived_campaign(run, destination)
    (destination / "campaign.yaml").write_text(
        yaml.safe_dump(raw, sort_keys=False), encoding="utf-8", newline="\n"
    )
    load_experiment_manifest(destination / "campaign.yaml")
    (destination / "input_accounting.txt").write_text(accounting_text, encoding="utf-8")
    record = {
        "schema_version": "mvp2-h300-baseline-plan-v1",
        "status": "prepared_not_admitted",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "input_run": str(run),
        "policy_sha256": file_sha256(ROOT / POLICY),
        "tools": tool_identity(),
        "input_accounting_sha256": file_sha256(destination / "input_accounting.txt"),
        "campaign_sha256": file_sha256(destination / "campaign.yaml"),
        "scope": review["scope"],
        "allocation_profile": review["allocation_profile"],
        "production_explicit_lifecycle_allowed": False,
    }
    pair.write(destination / "baseline_plan.json", record)
    return record


def check_execution(path):
    path = Path(path).resolve()
    record, review = pair.read(path), policy()
    require(
        record.get("schema_version") == "mvp2-h300-baseline-plan-v1"
        and record.get("status") == "prepared_not_admitted"
        and record.get("policy_sha256") == file_sha256(ROOT / POLICY)
        and record.get("tools") == tool_identity()
        and record.get("scope") == review["scope"]
        and record.get("allocation_profile") == review["allocation_profile"]
        and record.get("production_explicit_lifecycle_allowed") is False,
        "Baseline policy, tools or scope changed.",
    )
    plan, _ = check_inputs(record["input_run"])
    protect(path.parent, record["input_run"], plan)
    require(
        file_sha256(path.parent / "input_accounting.txt") == record["input_accounting_sha256"]
        and transfer.terminal_accounting(
            (path.parent / "input_accounting.txt").read_text(), review["input_job_id"]
        )
        == {"job_id": review["input_job_id"], "state": "COMPLETED", "exit_code": "0:0"},
        "Input terminal accounting changed.",
    )
    campaign = path.parent / "campaign.yaml"
    require(
        file_sha256(campaign) == record["campaign_sha256"]
        and yaml.safe_load(campaign.read_text())
        == derived_campaign(record["input_run"], path.parent),
        "Derived single-control campaign changed.",
    )
    manifest = load_experiment_manifest(campaign)
    require(len(manifest.experiments) == 1, "Only one control baseline is allowed.")
    return record, manifest


def allocation(job_text, node_text, *, job_id, node_name, cgroup):
    resource = pair.allocation(job_text, node_text, job_id=job_id, node_name=node_name)
    require(resource["cpus_per_task"] == 4, "Require four CPUs per task.")
    job = pair.fields(job_text)
    require(
        job.get("NumTasks") == "1" and job.get("TimeLimit") == "12:00:00",
        "Require one task and the reviewed 12-hour job wall time.",
    )
    require(
        cgroup.get("error") is None
        and type(cgroup.get("limit_bytes")) is int
        and cgroup["limit_bytes"] >= policy()["allocation_profile"]["minimum_cgroup_limit_bytes"],
        "Actual finite cgroup memory cap is missing or below 192 GiB.",
    )
    return {**resource, "tasks": 1, "walltime_seconds": 43200, "cgroup": cgroup}


def execute(path, resource, submitted_tools, source, *, runner=subprocess.run):
    """Fresh license probe then one control process; failures retain their records."""
    path = Path(path).resolve()
    record, _ = check_execution(path)
    frozen = file_sha256(path)
    require(
        submitted_tools == tool_identity() and re.fullmatch(r"[0-9a-f]{40}", source),
        "Submitted tools or pinned source invalid.",
    )
    require(
        resource["allocated_memory_mib"] == 196608
        and resource["cpus_per_task"] == 4
        and resource["partition"] == "intel-256"
        and resource["cgroup"].get("error") is None
        and resource["cgroup"]["limit_bytes"] >= 206158430208,
        "Fresh solve resources have not been admitted.",
    )
    destination = path.parent
    require(
        not any(
            (destination / name).exists()
            for name in (
                "logs",
                "runs",
                "comparison",
                "baseline_admission.json",
                "baseline_execution.json",
            )
        ),
        "Baseline already started; duplicate execution rejected.",
    )
    (destination / "logs").mkdir()
    env = dict(
        os.environ,
        PYTHONNOUSERSITE="1",
        PYTHONDONTWRITEBYTECODE="1",
        AGROLOGISTIC_SOURCE_COMMIT=source,
        GRB_LICENSE_FILE=pair.LICENSE_FILE,
    )
    for name in ("SCIPOPTDIR", "SLURM_ARRAY_TASK_ID"):
        env.pop(name, None)

    def recheck():
        require(file_sha256(path) == frozen, "Prepared plan changed during execution.")
        check_execution(path)

    license_report = destination / "license_capability.json"
    try:
        probe = runner(
            [
                sys.executable,
                str(ROOT / "scripts/probe_npad_gurobi_license.py"),
                "--output",
                str(license_report),
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=60,
        )
        capability = pair.read(license_report)
        licensed = probe.returncode == 0 and license_accepted(capability)
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        licensed = False
    recheck()
    pair.write(
        destination / "baseline_admission.json",
        {
            "schema_version": "mvp2-h300-baseline-admission-v1",
            "status": "admitted" if licensed else "license_capability_rejected",
            "source_commit": source,
            "tools": submitted_tools,
            "scope": record["scope"],
            "allocation": resource,
            "baseline_plan_sha256": frozen,
            "policy_sha256": record["policy_sha256"],
            "license_capability_sha256": file_sha256(license_report)
            if license_report.exists()
            else None,
            "production_explicit_lifecycle_allowed": False,
        },
    )
    result = {
        "schema_version": "mvp2-h300-baseline-execution-v1",
        "source_commit": source,
        "baseline_plan_sha256": frozen,
        "allocation": resource,
        "scope": record["scope"],
        "optimization_attempted": False,
    }
    if not licensed:
        pair.write(
            destination / "baseline_execution.json",
            {**result, "status": "license_capability_rejected"},
        )
        return 1
    print("H300 BASELINE: FRESH ALLOCATION AND LICENSE CAPABILITY ACCEPTED", flush=True)
    recheck()
    with (destination / "logs/control.out").open("x", encoding="utf-8") as log:
        process = runner(
            [
                sys.executable,
                str(ROOT / "scripts/run_batch_hpc.py"),
                str(destination / "campaign.yaml"),
                "--index",
                "0",
            ],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    pair.write(
        destination / "logs/control-exit.json", {"index": 0, "return_code": process.returncode}
    )
    recheck()
    with (destination / "logs/audit.out").open("x", encoding="utf-8") as log:
        audit = runner(
            [
                sys.executable,
                str(ROOT / "scripts/audit_nine_campaign.py"),
                str(destination / "campaign.yaml"),
                "--output-dir",
                str(destination / "comparison"),
                "--require-accepted",
            ],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    recheck()
    pair.write(
        destination / "baseline_execution.json",
        {
            **result,
            "status": "process_returned",
            "optimization_attempted": True,
            "control_return_code": process.returncode,
            "audit_return_code": audit.returncode,
            "qualification": "Closure alone is not scientific or performance acceptance.",
        },
    )
    return int(process.returncode != 0 or audit.returncode != 0)


def check_solved_model_audit(original, solved):
    """Input parity is semantic; solution enrichment is mandatory, not byte drift.

    experiment_runner replaces the input-only audit with build_model_audit(...,
    result). Keep the entire input mapping and original findings, while checking
    the final audit independently. Closure hashes still protect the full file.
    """
    require(
        original.get("schema_version") == solved.get("schema_version") == 3
        and isinstance(original.get("input"), dict)
        and bool(original["input"])
        and solved.get("input") == original["input"],
        "Solved model audit input/schema differs from accepted h300.",
    )
    for audit in (original, solved):
        findings = audit.get("findings")
        require(isinstance(findings, list), "Model audit findings are missing.")
        require(
            all(
                isinstance(f, dict) and f.get("severity") in ("error", "warning", "info")
                for f in findings
            ),
            "Malformed model audit findings.",
        )
        require(
            audit.get("summary")
            == {
                f"{severity}_count": sum(f["severity"] == severity for f in findings)
                for severity in ("error", "warning", "info")
            }
            and not any(f["severity"] == "error" for f in findings),
            "Model audit errors or inconsistent severity summary.",
        )
    require(
        solved["findings"][: len(original["findings"])] == original["findings"]
        and isinstance(solved.get("solution"), dict)
        and bool(solved["solution"])
        and solved.get("independent_validation_status") == "accepted",
        "Solved model audit lacks retained findings or accepted solution enrichment.",
    )


def completion(path):
    """Verify every closed product and the existing independent/hierarchy audit."""
    path = Path(path).resolve()
    record, manifest = check_execution(path)
    spec = manifest.experiments[0]
    folder = manifest.output_dir / spec.name
    valid, reason = verify_completion(folder, _checkpoint_identity(spec))
    require(valid, reason)
    original = pair.read(Path(record["input_run"]) / "audit/preflight/pair_preflight.json")
    observed = pair.read(folder / "preflight.json")
    observed.pop("execution", None)
    require(observed == original["model_size"], "Solved input snapshot differs from accepted h300.")
    for name in inputs.PRODUCTS[1:]:
        if name == "model_audit.json":
            input_path = (
                Path(record["input_run"]) / "audit/preflight/mvp2_h300_warehouse_control" / name
            )
            require(
                file_sha256(input_path)
                == original["artifacts"][f"mvp2_h300_warehouse_control/{name}"],
                "Original input model audit hash changed.",
            )
            check_solved_model_audit(pair.read(input_path), pair.read(folder / name))
            continue
        require(
            file_sha256(folder / name)
            == original["artifacts"][f"mvp2_h300_warehouse_control/{name}"],
            f"Solved input audit differs: {name}",
        )
    require(
        pair.read(folder / "independent_validation.json")["status"] == "accepted",
        "Independent solution validation rejected.",
    )
    audit = pair.read(path.parent / "comparison/nine_audit_manifest.json")
    require(
        audit.get("overall_status") == "accepted"
        and audit.get("selected_indices") == [0]
        and audit.get("accepted_instance_count") == 1
        and audit.get("manifest_sha256") == file_sha256(path.parent / "campaign.yaml")
        and audit.get("audit_script_sha256")
        == file_sha256(ROOT / "scripts/audit_nine_campaign.py"),
        "Existing hierarchical quality audit is not accepted.",
    )
    return pair.read(folder / "run_completion.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-run", type=Path)
    parser.add_argument("--input-accounting", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--tool-identity", action="store_true")
    for key in ("job-file", "node-file"):
        parser.add_argument(f"--{key}", type=Path)
    for key in ("job-id", "node-name", "tools", "source-commit"):
        parser.add_argument(f"--{key}")
    args = parser.parse_args()
    if args.plan is None:
        if any(v is None for v in (args.input_run, args.input_accounting, args.output_dir)):
            parser.error(
                "Preparation requires original input run, terminal accounting and new output."
            )
        prepare(args.input_run, args.output_dir, args.input_accounting.read_text())
        print("H300 BASELINE: PREPARED; FRESH ALLOCATION/LICENSE ADMISSION STILL REQUIRED")
        return 0
    check_execution(args.plan)
    if args.tool_identity:
        print(json.dumps(tool_identity()))
        return 0
    if args.check:
        require(
            not (args.plan.parent / ".submission-claimed").exists()
            and not (args.plan.parent / "baseline_admission.json").exists(),
            "Baseline already claimed or admitted.",
        )
        print("H300 SINGLE CONTROL CONTRACT: VERIFIED")
        return 0
    if any(
        getattr(args, key) is None
        for key in ("job_file", "node_file", "job_id", "node_name", "tools", "source_commit")
    ):
        parser.error("Execution requires submitted source/tools and fresh scheduler records.")
    cgroup = cgroup_memory()
    pair.write(args.plan.parent / "cgroup_observation.json", cgroup)
    resource = allocation(
        args.job_file.read_text(),
        args.node_file.read_text(),
        job_id=args.job_id,
        node_name=args.node_name,
        cgroup=cgroup,
    )
    return execute(args.plan, resource, json.loads(args.tools), args.source_commit)


if __name__ == "__main__":
    raise SystemExit(main())
