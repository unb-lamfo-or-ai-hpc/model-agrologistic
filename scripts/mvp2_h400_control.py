"""Admit one bounded h400 direct control from accepted immutable input evidence."""

from __future__ import annotations

import argparse
import copy
import io
import json
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import collect_mvp2_h400_input as inputs  # noqa: E402
from scripts import mvp2_h300_baseline as shared  # noqa: E402
from src.logic.resource_telemetry import cgroup_memory  # noqa: E402

POLICY = "docs/mvp2_h400_control_policy.json"
TOOLS = tuple(
    dict.fromkeys(
        (
            *inputs.gate.TOOLS,
            POLICY,
            "scripts/mvp2_h400_control.py",
            "scripts/collect_mvp2_h400_control.py",
            "scripts/submit_mvp2_h400_control.sh",
            "scripts/run_mvp2_h400_control.slurm",
            "scripts/npad_mvp2_h400_control.sh",
            "scripts/mvp2_h300_baseline.py",
            "scripts/admit_mvp2_resource_pair.py",
            "scripts/validate_scip_memory_resources.py",
            "scripts/run_batch_hpc.py",
            "scripts/audit_nine_campaign.py",
            "scripts/probe_npad_gurobi_license.py",
            "scripts/collect_mvp2_h300_baseline.py",
        )
    )
)
require, read, write, sha = shared.require, shared.pair.read, shared.pair.write, shared.file_sha256
digest = inputs.transfer.digest


def policy():
    p = read(ROOT / POLICY)
    require(
        p["schema_version"] == "mvp2-h400-control-policy-v1"
        and p["scope"] == "one_instrumented_h400_direct_control"
        and p["execution_limit"] == 42426624
        and p["reference_limit"] == 25000000
        and p["automatic_repeats_allowed"] is False
        and p["production_explicit_lifecycle_allowed"] is False
        and p["compaction_allowed"] is False,
        "Bounded single-control policy required.",
    )
    return p


def tool_identity():
    return {n: sha(ROOT / n) for n in TOOLS}


def policy_identity():
    return shared.pair.identity(policy())


def safe_payload(data, checksum, *, members=100, expanded=300_000_000):
    """Read regular bounded members only, including nested input evidence; never extract."""
    require(len(data) <= 128_000_000 and digest(data) == checksum, "Archive hash/size differs.")
    assets, total = {}, 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive:
            n = member.name
            require(
                member.isfile()
                and n not in assets
                and "\\" not in n
                and ":" not in n
                and not PurePosixPath(n).is_absolute()
                and ".." not in PurePosixPath(n).parts
                and str(PurePosixPath(n)) == n
                and 0 <= member.size <= 128_000_000,
                "Unsafe or duplicate evidence member.",
            )
            total += member.size
            require(len(assets) < members and total <= expanded, "Evidence expansion bound.")
            assets[n] = archive.extractfile(member).read()
    return assets


def original_assets(data):
    p = policy()
    assets = safe_payload(data, p["input_archive_sha256"], members=40, expanded=128_000_000)
    collection = json.loads(assets["collection.json"])
    payload = {n: v for n, v in assets.items() if n not in ("collection.json", "accounting.txt")}
    require(
        collection["status"] == "accepted"
        and not collection["acceptance_errors"]
        and collection["collector_sha256"] == sha(ROOT / "scripts/collect_mvp2_h400_input.py")
        and collection["artifacts"] == {n: digest(v) for n, v in payload.items()}
        and inputs.transfer.terminal_accounting(
            assets["accounting.txt"].decode(), p["input_job_id"]
        )
        == collection["accounting"]
        == {"job_id": p["input_job_id"], "state": "COMPLETED", "exit_code": "0:0"},
        "Original input collection/accounting differs.",
    )
    reviewed = inputs.validate(payload, p["input_job_id"])
    require(
        reviewed["source_commit"] == p["input_source_commit"]
        and reviewed["implementation"]["sha256"] == p["implementation_sha256"]
        and digest(assets["prepared/input_plan.json"]) == p["input_plan_sha256"]
        and digest(assets["audit/preflight/input_preflight.json"]) == p["input_receipt_sha256"],
        "Reviewed input identity differs.",
    )
    return assets


def check_inputs(run, archive):
    run, archive = Path(run).resolve(), Path(archive).resolve()
    require(
        archive.is_relative_to(run)
        and archive.is_file()
        and not archive.is_symlink()
        and archive.stat().st_size <= 128_000_000,
        "Require original bounded input archive.",
    )
    assets = original_assets(archive.read_bytes())
    for n in inputs.names(policy()["input_job_id"]):
        path = run / n
        require(
            not path.is_symlink()
            and path.resolve().is_relative_to(run)
            and path.is_file()
            and sha(path) == digest(assets[n]),
            f"Preserved input changed: {n}",
        )
    plan, _ = inputs.gate.check_plan(run / "prepared/input_plan.json")
    require(
        plan["implementation"]["sha256"] == policy()["implementation_sha256"],
        "Original runtime/core qualification differs.",
    )
    return plan, assets


def campaign_from_original(original, destination):
    raw = copy.deepcopy(original)
    require(
        len(raw["experiments"]) == 1 and raw["continue_on_error"] is False,
        "Exactly one accepted control required.",
    )
    spec = raw["experiments"][0]
    require(
        spec["name"] == policy()["experiment_name"]
        and spec["max_estimated_variables"] == policy()["reference_limit"]
        and spec["model"]["use_direct_origin_customer"] is True
        and spec["solver"]["compact_python_indices"] is False,
        "Accepted h400 direct control differs.",
    )
    spec["max_estimated_variables"] = policy()["execution_limit"]
    spec["metadata"].update(
        mvp2_scope=policy()["scope"], input_evidence_sha256=policy()["input_archive_sha256"]
    )
    raw["output_dir"] = str(Path(destination) / "runs")
    return raw


def protect(destination, run, plan):
    protected = (
        ROOT,
        Path(run).resolve(),
        Path(plan["reference_manifest"]).parent,
        Path(plan["qualification_report"]).parent,
    )
    require(
        not any(destination.is_relative_to(p) or p.is_relative_to(destination) for p in protected),
        "Execution overlaps preserved input/source.",
    )


def prepare(run, archive, destination, accounting, source):
    run, archive, destination = [Path(p).resolve() for p in (run, archive, destination)]
    require(bool(re.fullmatch(r"[0-9a-f]{40}", source)), "Full source commit required.")
    require(
        inputs.transfer.terminal_accounting(accounting, policy()["input_job_id"])
        == {"job_id": policy()["input_job_id"], "state": "COMPLETED", "exit_code": "0:0"},
        "Original successful terminal accounting required.",
    )
    original, _ = check_inputs(run, archive)
    protect(destination, run, original)
    require(not destination.exists(), "New execution required.")
    destination.mkdir(parents=True)
    raw = campaign_from_original(
        yaml.safe_load((run / "prepared/campaign.yaml").read_text()), destination
    )
    (destination / "campaign.yaml").write_text(
        yaml.safe_dump(raw, sort_keys=False), encoding="utf-8", newline="\n"
    )
    (destination / "input_accounting.txt").write_text(accounting, encoding="utf-8")
    plan = {
        "schema_version": "mvp2-h400-control-plan-v1",
        "status": "prepared_not_admitted",
        "source_commit": source,
        "input_run": str(run),
        "input_archive": str(archive),
        "input_archive_sha256": policy()["input_archive_sha256"],
        "policy_identity": policy_identity(),
        "tools": tool_identity(),
        "campaign_sha256": sha(destination / "campaign.yaml"),
        "input_accounting_sha256": sha(destination / "input_accounting.txt"),
        "scope": policy()["scope"],
        "allocation_profile": policy()["allocation_profile"],
        "automatic_repeats_allowed": False,
        "production_explicit_lifecycle_allowed": False,
    }
    write(destination / "control_plan.json", plan)
    check_execution(destination / "control_plan.json")
    return plan


def check_execution(path):
    path = Path(path).resolve()
    r, p = read(path), policy()
    require(
        r["schema_version"] == "mvp2-h400-control-plan-v1"
        and r["status"] == "prepared_not_admitted"
        and r["policy_identity"] == policy_identity()
        and r["tools"] == tool_identity()
        and r["scope"] == p["scope"]
        and r["allocation_profile"] == p["allocation_profile"]
        and r["input_archive_sha256"] == p["input_archive_sha256"]
        and r["automatic_repeats_allowed"] is False
        and r["production_explicit_lifecycle_allowed"] is False
        and bool(re.fullmatch(r"[0-9a-f]{40}", r["source_commit"])),
        "Control plan differs.",
    )
    original, _ = check_inputs(r["input_run"], r["input_archive"])
    protect(path.parent, r["input_run"], original)
    require(
        sha(path.parent / "input_accounting.txt") == r["input_accounting_sha256"]
        and inputs.transfer.terminal_accounting(
            (path.parent / "input_accounting.txt").read_text(), p["input_job_id"]
        )
        == {"job_id": p["input_job_id"], "state": "COMPLETED", "exit_code": "0:0"},
        "Input terminal accounting changed.",
    )
    require(
        sha(path.parent / "campaign.yaml") == r["campaign_sha256"]
        and yaml.safe_load((path.parent / "campaign.yaml").read_text())
        == campaign_from_original(
            yaml.safe_load((Path(r["input_run"]) / "prepared/campaign.yaml").read_text()),
            path.parent,
        ),
        "Only exact control derivation permitted.",
    )
    return r, shared.load_experiment_manifest(path.parent / "campaign.yaml")


def allocation(job_text, node_text, *, job_id, node_name, cgroup):
    resource = shared.allocation(
        job_text, node_text, job_id=job_id, node_name=node_name, cgroup=cgroup
    )
    require(
        cgroup["limit_bytes"] == policy()["allocation_profile"]["cgroup_limit_bytes"],
        "Require the exact finite 192-GiB cgroup cap.",
    )
    return resource


def execute(path, resource, submitted_tools, source, *, runner=subprocess.run):
    path = Path(path).resolve()
    record, _ = check_execution(path)
    require(
        source == record["source_commit"] and submitted_tools == tool_identity(),
        "Submitted source/tools changed.",
    )
    require(
        resource["allocated_memory_mib"] == 196608
        and resource["cpus_per_task"] == 4
        and resource["tasks"] == 1
        and resource["walltime_seconds"] == 43200
        and resource["partition"] == "intel-256"
        and resource["cgroup"].get("error") is None
        and resource["cgroup"]["limit_bytes"] == 206158430208,
        "Fresh bounded solve resources required.",
    )
    destination, frozen = path.parent, sha(path)
    require(
        not any(
            (destination / n).exists()
            for n in (
                "logs",
                "runs",
                "comparison",
                "control_admission.json",
                "control_execution.json",
            )
        ),
        "Control already started; no duplicate execution.",
    )
    (destination / "logs").mkdir()
    env = dict(
        os.environ,
        PYTHONNOUSERSITE="1",
        PYTHONDONTWRITEBYTECODE="1",
        AGROLOGISTIC_SOURCE_COMMIT=source,
        GRB_LICENSE_FILE=shared.pair.LICENSE_FILE,
    )
    for n in ("SCIPOPTDIR", "SLURM_ARRAY_TASK_ID", "SLURM_ARRAY_JOB_ID"):
        env.pop(n, None)
    common = {
        "source_commit": source,
        "control_plan_sha256": frozen,
        "allocation": resource,
        "scope": record["scope"],
    }
    closure = {
        **common,
        "schema_version": "mvp2-h400-control-execution-v1",
        "status": "license_capability_rejected",
        "optimization_attempted": False,
        "control_return_code": None,
        "audit_return_code": None,
    }

    def recheck():
        require(sha(path) == frozen, "Plan changed during execution.")
        check_execution(path)

    try:
        report = destination / "license_capability.json"
        try:
            probe = runner(
                [
                    sys.executable,
                    str(ROOT / "scripts/probe_npad_gurobi_license.py"),
                    "--output",
                    str(report),
                ],
                cwd=ROOT,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=60,
            )
            licensed = probe.returncode == 0 and shared.license_accepted(read(report))
        except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired):
            licensed = False
        recheck()
        write(
            destination / "control_admission.json",
            {
                **common,
                "schema_version": "mvp2-h400-control-admission-v1",
                "status": "admitted" if licensed else "license_capability_rejected",
                "tools": submitted_tools,
                "policy_identity": policy_identity(),
                "license_capability_sha256": sha(report) if report.exists() else None,
                "automatic_repeats_allowed": False,
                "production_explicit_lifecycle_allowed": False,
            },
        )
        if not licensed:
            return 1
        recheck()
        closure.update(status="control_started", optimization_attempted=True)
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
                timeout=policy()["allocation_profile"]["control_process_timeout_seconds"],
            )
        closure["control_return_code"] = process.returncode
        write(
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
                timeout=policy()["allocation_profile"]["audit_timeout_seconds"],
            )
        closure.update(status="process_returned", audit_return_code=audit.returncode)
        recheck()
        return int(process.returncode != 0 or audit.returncode != 0)
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        closure.update(status="execution_exception", exception_type=type(exc).__name__)
        raise
    finally:
        write(destination / "control_execution.json", closure)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in (
        "input-run",
        "input-archive",
        "input-accounting",
        "output-dir",
        "plan",
        "job-file",
        "node-file",
    ):
        p.add_argument(f"--{n}", type=Path)
    for n in ("source-commit", "tools", "job-id", "node-name"):
        p.add_argument(f"--{n}")
    p.add_argument("--check", action="store_true")
    p.add_argument("--tool-identity", action="store_true")
    args = p.parse_args()
    if args.plan is None:
        require(
            all(
                v is not None
                for v in (
                    args.input_run,
                    args.input_archive,
                    args.input_accounting,
                    args.output_dir,
                    args.source_commit,
                )
            ),
            "Missing preparation.",
        )
        prepare(
            args.input_run,
            args.input_archive,
            args.output_dir,
            args.input_accounting.read_text(),
            args.source_commit,
        )
        print("H400 CONTROL: PREPARED; FRESH ALLOCATION/LICENSE ADMISSION REQUIRED")
        return 0
    record, _ = check_execution(args.plan)
    if args.tool_identity:
        print(json.dumps(tool_identity()))
        return 0
    if args.check:
        require(
            args.source_commit == record["source_commit"]
            and not (args.plan.parent / ".submission-claimed").exists()
            and not (args.plan.parent / "control_admission.json").exists(),
            "Already claimed/source drift.",
        )
        print("H400 SINGLE INSTRUMENTED CONTROL CONTRACT: VERIFIED")
        return 0
    require(
        all(
            v is not None
            for v in (
                args.job_file,
                args.node_file,
                args.job_id,
                args.node_name,
                args.tools,
                args.source_commit,
            )
        ),
        "Missing execution arguments.",
    )
    group = cgroup_memory()
    write(args.plan.parent / "cgroup_observation.json", group)
    resource = allocation(
        args.job_file.read_text(),
        args.node_file.read_text(),
        job_id=args.job_id,
        node_name=args.node_name,
        cgroup=group,
    )
    return execute(args.plan, resource, json.loads(args.tools), args.source_commit)


if __name__ == "__main__":
    raise SystemExit(main())
