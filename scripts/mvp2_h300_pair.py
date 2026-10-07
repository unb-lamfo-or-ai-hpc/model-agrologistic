"""Admit one fresh h300 transfer pair using the accepted original input gate."""

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

from scripts import mvp2_h300_baseline as baseline  # noqa: E402
from src.logic.resource_telemetry import cgroup_memory  # noqa: E402

POLICY = "docs/mvp2_h300_pair_policy.json"
TOOLS = tuple(
    dict.fromkeys(
        (
            *baseline.TOOLS,
            POLICY,
            "scripts/mvp2_h300_pair.py",
            "scripts/collect_mvp2_h300_pair.py",
            "scripts/submit_mvp2_h300_pair.sh",
            "scripts/run_mvp2_h300_pair.slurm",
            "scripts/npad_mvp2_h300_pair.sh",
        )
    )
)
require = baseline.require
read = baseline.pair.read
write = baseline.pair.write
sha = baseline.file_sha256


def policy():
    review = read(ROOT / POLICY)
    require(
        review["input_policy_sha256"] == sha(ROOT / baseline.POLICY),
        "Accepted single-baseline input policy changed.",
    )
    return review


def tool_identity():
    return {name: sha(ROOT / name) for name in TOOLS}


def campaign_from_original(original, destination):
    """Raise only the exact reviewed execution guard and record the paired scope."""
    result = copy.deepcopy(original)
    result["output_dir"] = str(Path(destination) / "runs")
    require(len(result["experiments"]) == 2, "Require exactly the two accepted input arms.")
    for index, spec in enumerate(result["experiments"]):
        arm = ("control", "compact")[index]
        require(
            spec["name"] == f"mvp2_h300_warehouse_{arm}"
            and spec["solver"]["compact_python_indices"] is bool(index),
            "Canonical control/compact input arms changed.",
        )
        spec["max_estimated_variables"] = baseline.policy()["execution_limit"]
        spec["metadata"].update(
            resource_contrast_scope=policy()["scope"], paired_size_review=policy()["review_id"]
        )
    return result


def derived_campaign(run, destination):
    return campaign_from_original(
        yaml.safe_load((Path(run) / "prepared/campaign.yaml").read_text()), destination
    )


def prepare(run, destination, accounting_text):
    run, destination = Path(run).resolve(), Path(destination).resolve()
    review = policy()
    require(
        baseline.transfer.terminal_accounting(accounting_text, baseline.policy()["input_job_id"])
        == {"job_id": baseline.policy()["input_job_id"], "state": "COMPLETED", "exit_code": "0:0"},
        "Original input job lacks successful terminal accounting.",
    )
    plan, _ = baseline.check_inputs(run)
    baseline.protect(destination, run, plan)
    require(not destination.exists(), "Choose a new paired execution directory.")
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "campaign.yaml").write_text(
        yaml.safe_dump(derived_campaign(run, destination), sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )
    baseline.load_experiment_manifest(destination / "campaign.yaml")
    (destination / "input_accounting.txt").write_text(accounting_text, encoding="utf-8")
    record = {
        "schema_version": "mvp2-h300-pair-plan-v1",
        "status": "prepared_not_admitted",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "input_run": str(run),
        "policy_sha256": sha(ROOT / POLICY),
        "tools": tool_identity(),
        "input_accounting_sha256": sha(destination / "input_accounting.txt"),
        "campaign_sha256": sha(destination / "campaign.yaml"),
        "scope": review["scope"],
        "arm_order": review["arm_order"],
        "allocation_profile": review["allocation_profile"],
        "production_explicit_lifecycle_allowed": False,
        "automatic_repeats_allowed": False,
    }
    write(destination / "pair_plan.json", record)
    return record


def check_execution(path):
    path = Path(path).resolve()
    record, review = read(path), policy()
    require(
        record.get("schema_version") == "mvp2-h300-pair-plan-v1"
        and record.get("status") == "prepared_not_admitted"
        and record.get("policy_sha256") == sha(ROOT / POLICY)
        and record.get("tools") == tool_identity()
        and record.get("scope") == review["scope"]
        and baseline.pair.validate_arm_order(record.get("arm_order")) == review["arm_order"]
        and record.get("allocation_profile") == review["allocation_profile"]
        and record.get("production_explicit_lifecycle_allowed") is False
        and record.get("automatic_repeats_allowed") is False,
        "Paired policy, tools, order or scope changed.",
    )
    input_plan, _ = baseline.check_inputs(record["input_run"])
    baseline.protect(path.parent, record["input_run"], input_plan)
    require(
        sha(path.parent / "input_accounting.txt") == record["input_accounting_sha256"]
        and baseline.transfer.terminal_accounting(
            (path.parent / "input_accounting.txt").read_text(), baseline.policy()["input_job_id"]
        )
        == {"job_id": baseline.policy()["input_job_id"], "state": "COMPLETED", "exit_code": "0:0"},
        "Original input accounting changed.",
    )
    campaign = path.parent / "campaign.yaml"
    require(
        sha(campaign) == record["campaign_sha256"]
        and yaml.safe_load(campaign.read_text())
        == derived_campaign(record["input_run"], path.parent),
        "Paired campaign differs from the exact accepted input derivation.",
    )
    return record, baseline.load_experiment_manifest(campaign)


def allocation(job_text, node_text, *, job_id, node_name, cgroup):
    resource = baseline.pair.allocation(job_text, node_text, job_id=job_id, node_name=node_name)
    job = baseline.pair.fields(job_text)
    require(
        resource["cpus_per_task"] == 4
        and job.get("NumTasks") == "1"
        and job.get("TimeLimit") == "18:00:00",
        "Require one task, four CPUs per task and 18-hour paired wall time.",
    )
    require(
        cgroup.get("error") is None
        and type(cgroup.get("limit_bytes")) is int
        and cgroup["limit_bytes"] >= policy()["allocation_profile"]["minimum_cgroup_limit_bytes"],
        "Actual finite cgroup memory cap is missing or below 192 GiB.",
    )
    return {**resource, "tasks": 1, "walltime_seconds": 64800, "cgroup": cgroup}


def execute(path, resource, submitted_tools, source, *, runner=subprocess.run):
    """Probe once, run two fresh serial processes, then audit both canonical indices."""
    path = Path(path).resolve()
    record, _ = check_execution(path)
    frozen = sha(path)
    require(
        submitted_tools == tool_identity() and bool(re.fullmatch(r"[0-9a-f]{40}", source)),
        "Submitted tools or pinned source invalid.",
    )
    require(
        resource["allocated_memory_mib"] == 196608
        and resource["cpus_per_task"] == 4
        and resource["tasks"] == 1
        and resource["walltime_seconds"] == 64800
        and resource["partition"] == "intel-256"
        and resource["cgroup"].get("error") is None
        and resource["cgroup"]["limit_bytes"] >= 206158430208,
        "Fresh paired solve resources have not been admitted.",
    )
    destination = path.parent
    require(
        not any(
            (destination / n).exists()
            for n in ("logs", "runs", "comparison", "pair_admission.json", "pair_execution.json")
        ),
        "Pair already started; duplicate execution rejected.",
    )
    (destination / "logs").mkdir()
    env = dict(
        os.environ,
        PYTHONNOUSERSITE="1",
        PYTHONDONTWRITEBYTECODE="1",
        AGROLOGISTIC_SOURCE_COMMIT=source,
        GRB_LICENSE_FILE=baseline.pair.LICENSE_FILE,
    )
    for name in ("SCIPOPTDIR", "SLURM_ARRAY_TASK_ID", "SLURM_ARRAY_JOB_ID"):
        env.pop(name, None)

    def recheck():
        require(sha(path) == frozen, "Prepared pair plan changed during execution.")
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
        licensed = probe.returncode == 0 and baseline.license_accepted(read(license_report))
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        licensed = False
    recheck()
    common = {
        "source_commit": source,
        "pair_plan_sha256": frozen,
        "allocation": resource,
        "scope": record["scope"],
        "arm_order": record["arm_order"],
    }
    write(
        destination / "pair_admission.json",
        {
            **common,
            "schema_version": "mvp2-h300-pair-admission-v1",
            "status": "admitted" if licensed else "license_capability_rejected",
            "tools": submitted_tools,
            "policy_sha256": record["policy_sha256"],
            "license_capability_sha256": sha(license_report) if license_report.exists() else None,
            "production_explicit_lifecycle_allowed": False,
            "automatic_repeats_allowed": False,
        },
    )
    closure = {
        **common,
        "schema_version": "mvp2-h300-pair-execution-v1",
        "optimization_attempted": False,
        "arms": [],
        "audit_return_code": None,
        "status": "license_capability_rejected",
    }
    if not licensed:
        write(destination / "pair_execution.json", closure)
        return 1
    try:
        for index in record["arm_order"]:
            recheck()
            closure["optimization_attempted"] = True
            with (destination / f"logs/arm-{index}.out").open("x", encoding="utf-8") as log:
                process = runner(
                    [
                        sys.executable,
                        str(ROOT / "scripts/run_batch_hpc.py"),
                        str(destination / "campaign.yaml"),
                        "--index",
                        str(index),
                    ],
                    cwd=ROOT,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
            arm = {"index": index, "return_code": process.returncode}
            closure["arms"].append(arm)
            write(destination / f"logs/arm-{index}-exit.json", arm)
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
        closure.update(status="process_returned", audit_return_code=audit.returncode)
        recheck()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        closure.update(status="execution_exception", exception_type=type(exc).__name__)
        raise
    finally:
        write(destination / "pair_execution.json", closure)
    return int(
        any(arm["return_code"] != 0 for arm in closure["arms"]) or closure["audit_return_code"] != 0
    )


def completion(path):
    """Check full closures, exact inputs and solution-enriched audit for both arms."""
    path = Path(path).resolve()
    record, manifest = check_execution(path)
    original = read(Path(record["input_run"]) / "audit/preflight/pair_preflight.json")
    completed = {}
    for spec in manifest.experiments:
        folder = manifest.output_dir / spec.name
        valid, reason = baseline.verify_completion(folder, baseline._checkpoint_identity(spec))
        require(valid, reason)
        observed = read(folder / "preflight.json")
        observed.pop("execution", None)
        require(observed == original["model_size"], "Solved input dimensions differ from h300.")
        for name in baseline.inputs.PRODUCTS[1:]:
            if name == "model_audit.json":
                baseline.check_solved_model_audit(
                    read(Path(record["input_run"]) / f"audit/preflight/{spec.name}/{name}"),
                    read(folder / name),
                )
            else:
                require(
                    sha(folder / name) == original["artifacts"][f"{spec.name}/{name}"],
                    f"Solved connectivity audit differs: {spec.name}/{name}",
                )
        require(
            read(folder / "independent_validation.json")["status"] == "accepted",
            "Independent arm validation rejected.",
        )
        completed[spec.name] = read(folder / "run_completion.json")
    audit = read(path.parent / "comparison/nine_audit_manifest.json")
    require(
        audit.get("overall_status") == "accepted"
        and audit.get("selected_indices") == [0, 1]
        and audit.get("accepted_instance_count") == audit.get("campaign_instance_count") == 2
        and audit.get("manifest_sha256") == sha(path.parent / "campaign.yaml")
        and audit.get("audit_script_sha256") == sha(ROOT / "scripts/audit_nine_campaign.py"),
        "Both hierarchical quality audits must be accepted.",
    )
    return completed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input-run", "input-accounting", "output-dir", "plan", "job-file", "node-file"):
        parser.add_argument(f"--{name}", type=Path)
    for name in ("job-id", "node-name", "tools", "source-commit"):
        parser.add_argument(f"--{name}")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--tool-identity", action="store_true")
    args = parser.parse_args()
    if args.plan is None:
        if any(v is None for v in (args.input_run, args.input_accounting, args.output_dir)):
            parser.error("Require original input run/accounting and a new output directory.")
        prepare(args.input_run, args.output_dir, args.input_accounting.read_text())
        print("H300 PAIR: PREPARED; FRESH ALLOCATION/LICENSE ADMISSION STILL REQUIRED")
        return 0
    check_execution(args.plan)
    if args.tool_identity:
        print(json.dumps(tool_identity()))
        return 0
    if args.check:
        require(
            not (args.plan.parent / ".submission-claimed").exists()
            and not (args.plan.parent / "pair_admission.json").exists(),
            "Pair already claimed or admitted.",
        )
        print("H300 SINGLE DESCRIPTIVE PAIR CONTRACT: VERIFIED")
        return 0
    if any(
        getattr(args, key) is None
        for key in ("job_file", "node_file", "job_id", "node_name", "tools", "source_commit")
    ):
        parser.error("Require submitted source/tools and fresh scheduler records.")
    cgroup = cgroup_memory()
    write(args.plan.parent / "cgroup_observation.json", cgroup)
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
