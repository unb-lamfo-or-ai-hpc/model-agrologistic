"""Human-only, one-claim/one-job progressive Gurobi/HiGHS Pyomo campaign."""

# ruff: noqa: E402 -- isolated script entry explicitly adds its exact source root.

from __future__ import annotations

import argparse
import contextlib
import csv
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import mvp2_scalar_r3a as r
from scripts import mvp2_scalar_r3a_operational as o
from scripts import pyomo_scaling_contract as c
from scripts import pyomo_worker_bootstrap as bootstrap
from scripts.qualify_pyomo_scaling import accepted, digest, environment, verify_source, write_json
from scripts.scip_external_observer import ExternalObserver, review_external

BASE = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
DRIVER = "scripts/pyomo_scaling_campaign.py"
BOOTSTRAP = "scripts/pyomo_scaling_bootstrap.py"
MAX_JSON = 1024**3


def regular(path):
    path = Path(path)
    c.require(path.is_file() and not path.is_symlink(), "Regular unlinked file required.")
    return path


def read(path):
    path = regular(path)
    c.require(path.stat().st_size <= MAX_JSON, "JSON exceeds explicit1GiB parser cap.")
    return r.strict_json(path.read_bytes())


def login():
    c.require(
        platform.system() == "Linux"
        and sys.version_info[:2] == (3, 13)
        and not os.environ.get("SLURM_JOB_ID"),
        "Existing Linux3.13 login only.",
    )


def campaign_location(directory):
    c.require(
        directory.name == c.CAMPAIGN
        and not directory.is_symlink()
        and directory.parent.resolve() == BASE,
        "Dedicated new campaign below audit base.",
    )


def run_location(claim):
    campaign_location(claim.parent)
    c.require(
        not claim.is_symlink() and claim.name == c.select(claim.name)["id"],
        "Dedicated immutable run claim required.",
    )


def invocation(action, directory, sha, *extra):
    return [
        sys.executable,
        "-B",
        "-I",
        str(ROOT / DRIVER),
        action,
        "--directory",
        str(directory),
        "--source-sha",
        sha,
        *extra,
    ]


def selection(population, inputs):
    if population == 300:
        from scripts.mvp2_scalar_h300 import read_selection
    elif population == 400:
        from scripts.mvp2_scalar_h400_contract import read_selection
    else:
        from scripts.mvp2_scalar_h500_contract import read_selection
    return read_selection(
        Path(inputs["workbook"]), Path(inputs["population"]), Path(inputs["order"])
    )


def check_inputs(population, inputs):
    ref = c.reference(population)
    expected = {
        "workbook": ref["workbook_sha256"],
        "population": c.POPULATION_SHA,
        "order": c.ORDER_SHA,
        "materialization": ref["materialization_sha256"],
    }
    c.require(set(inputs) == set(expected), "Four original input paths required.")
    for key, value in expected.items():
        c.require(digest(regular(inputs[key])) == value, "Original input differs: " + key)
    return expected


def default_inputs():
    processed = BASE.parent / "model-agrologistic/data/processed"
    return {
        str(p): {
            "workbook": str(processed / f"nine_population_osrm_v1/warehouses_{p}/model_input.xlsx"),
            "materialization": str(
                processed
                / f"nine_population_osrm_v1/warehouses_{p}/osrm_materialization_audit.json"
            ),
            "population": str(
                processed / "warehouse_population_v020/warehouse_population_manifest.json"
            ),
            "order": str(processed / "warehouse_population_v020/warehouse_population_order.csv"),
        }
        for p in c.POPULATIONS
    }


def init(directory, sha, inputs):
    login()
    campaign_location(directory)
    c.require(not directory.exists(), "Preserve existing campaign; init cannot reset it.")
    qualified = BASE / c.QUALIFICATION
    plan, result = read(qualified / "plan.json"), read(qualified / "result.json")
    accepted(plan, result)
    public_query = r.r2.command(
        [
            "sacct",
            "-j",
            result["job_id"],
            "--noheader",
            "--parsable2",
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
        ]
    )
    c.require(public_query.returncode == 0, "Public accounting unavailable; init must wait.")
    public_rows = r.r2.accounting(public_query.stdout, result["job_id"])
    required_public = {result["job_id"], result["job_id"] + ".batch", result["job_id"] + ".0"}
    c.require(
        required_public <= {row["job_id"] for row in public_rows}
        and all(
            row["state"] == "COMPLETED" and row["exit_code"] == "0:0"
            for row in public_rows
            if row["job_id"] in required_public
        ),
        "Public qualification scheduler receipts are not closed.",
    )
    c.require(
        ROOT == qualified / "source" and sha == plan["source_commit"],
        "Use the exact public-qualified source, not a new checkout.",
    )
    verify_source(ROOT, plan["source_files"])
    c.require(environment() == plan["runtime"], "Qualified runtime differs.")
    c.require(
        set(inputs) == {str(p) for p in c.POPULATIONS}, "All three frozen populations required."
    )
    frozen = {
        p: {k: str(regular(v).absolute()) for k, v in paths.items()} for p, paths in inputs.items()
    }
    hashes = {p: check_inputs(int(p), paths) for p, paths in frozen.items()}
    tools = {name: str(Path(shutil.which(name) or "").resolve()) for name in (*o.TOOLS, "sbatch")}
    tools_sha = {name: digest(regular(path)) for name, path in tools.items()}
    manifest = {
        "schema_version": c.SCHEMA,
        "source_commit": sha,
        "source_root": str(ROOT),
        "python": sys.executable,
        "runtime": plan["runtime"],
        "source_files": plan["source_files"],
        "public_receipts": {
            name: digest(qualified / name)
            for name in (
                "plan.json",
                "result.json",
                "qualification.xml",
                "license-capability.json",
                "public-allocation.json",
            )
        },
        "public_accounting": {"raw": public_query.stdout, "rows": public_rows},
        "inputs": frozen,
        "input_sha256": hashes,
        "profile": c.PROFILE,
        "tools": tools,
        "tool_sha256": tools_sha,
        "cells": c.cells(),
        "schedule_seed": c.SCHEDULE_SEED,
        "max_concurrent": c.MAX_CONCURRENT,
        "automatic_follow_on_allowed": False,
        "automatic_retry_allowed": False,
    }
    directory.mkdir(mode=0o700)
    write_json(directory / "campaign.json", manifest)
    return {
        "status": "prepared_no_job",
        "campaign_sha256": c.digest(manifest),
        "cells": len(c.cells()),
        "first_stage": "four_h300_pilots",
        "automatic_follow_on_allowed": False,
    }


def load_campaign(directory, sha, *, expensive=True):
    campaign_location(directory)
    plan = read(directory / "campaign.json")
    c.require(
        plan["schema_version"] == c.SCHEMA
        and plan["source_commit"] == sha
        and re.fullmatch(r"[0-9a-f]{40}", sha)
        and Path(plan["source_root"]) == ROOT
        and Path(plan["python"]) == Path(sys.executable)
        and plan["profile"] == c.PROFILE
        and plan["cells"] == c.cells()
        and plan["schedule_seed"] == c.SCHEDULE_SEED
        and plan["max_concurrent"] == c.MAX_CONCURRENT
        and plan["automatic_follow_on_allowed"] is False
        and plan["automatic_retry_allowed"] is False,
        "Frozen campaign drift.",
    )
    qualified = BASE / c.QUALIFICATION
    for name, expected in plan["public_receipts"].items():
        c.require(digest(regular(qualified / name)) == expected, "Public qualification drift.")
    public = read(qualified / "plan.json")
    accepted(public, read(qualified / "result.json"))
    c.require(
        public["source_files"] == plan["source_files"] and public["runtime"] == plan["runtime"],
        "Qualification source/runtime differs.",
    )
    if expensive:
        verify_source(ROOT, plan["source_files"])
        c.require(environment() == plan["runtime"], "Runtime changed after qualification.")
    return plan


def load_run(claim, sha, *, expensive=True):
    run_location(claim)
    campaign = load_campaign(claim.parent, sha, expensive=expensive)
    plan = read(claim / "plan.json")
    item = c.select(claim.name)
    expected = r.strict_json(
        c.encoded(
            r.spec_payload(
                c.specification(item, campaign["inputs"][str(item["population"])]["workbook"])
            )
        )
    )
    c.require(
        plan["schema_version"] == c.SCHEMA + "-run"
        and plan["cell"] == item
        and plan["source_commit"] == sha
        and plan["profile"] == c.PROFILE
        and plan["source_root"] == str(ROOT)
        and plan["claim_path"] == str(claim)
        and plan["campaign_sha256"] == c.digest(campaign)
        and plan["cases"] == [expected]
        and plan["selection_sha256"] == digest(claim / "warehouse_selection.json"),
        "Run/source/input/profile binding differs.",
    )
    if expensive:
        check_inputs(item["population"], campaign["inputs"][str(item["population"])])
        verify_tools(campaign)
    return plan, campaign


def verify_tools(plan):
    for name, path in plan["tools"].items():
        c.require(
            str(Path(shutil.which(name) or "").resolve()) == path
            and digest(regular(path)) == plan["tool_sha256"][name],
            "Scheduler tool identity drift.",
        )


def archive_report(claim, marker):
    archive = regular(claim / "evidence.tar.gz")
    c.require(digest(archive) == marker["sha256"], "Preserved archive differs.")
    with tarfile.open(archive, "r:gz") as tar:
        members = [m for m in tar if m.name == "campaign_observation.json"]
        c.require(
            len(members) == 1 and members[0].isfile() and members[0].size <= 1024**2,
            "Unique bounded archived observation required.",
        )
        report = r.strict_json(tar.extractfile(members[0]).read())
    c.require(report == marker["observation"], "Collection/archive observation differs.")
    return report


def observations(directory):
    result = []
    for item in c.cells():
        claim = directory / item["id"]
        if (claim / "collection.json").exists():
            result.append(archive_report(claim, read(claim / "collection.json")))
    return result


@contextlib.contextmanager
def submission_lock(directory):
    """No expiry/reclamation of uncertain submission locks."""
    lock = directory / "submission.lock"
    lock.mkdir()
    try:
        yield
    finally:
        # The run's durable intent still prevents resubmission after a failure.
        lock.rmdir()


def capacity(directory, command):
    active = []
    for item in c.cells():
        claim = directory / item["id"]
        if not claim.exists():
            continue
        c.require(
            (claim / "job.json").is_file(),
            "Uncertain claimed/submitted run; reconcile original receipt before continuing.",
        )
        job = read(claim / "job.json")
        query = command(
            [
                "sacct",
                "-j",
                job["job_id"],
                "--noheader",
                "--parsable2",
                "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
            ]
        )
        c.require(query.returncode == 0, "Accounting unavailable; concurrency cannot be proved.")
        rows = r.r2.accounting(query.stdout, job["job_id"])
        root = next((row for row in rows if row["job_id"] == job["job_id"]), None)
        if root is None or root["state"] not in r.r2.TERMINAL:
            active.append(job["job_id"])
    c.require(len(active) < c.MAX_CONCURRENT, "Two campaign jobs already active or uncertain.")
    return active


def scheduler_arguments():
    return [
        "--account=sxdsouza",
        "--partition=intel-256",
        "--qos=preempt",
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=24",
        "--mem=192G",
        "--time=12:00:00",
        "--exclusive",
        "--no-requeue",
    ]


def start(directory, sha, identity, acknowledged, *, command=r.r2.command):
    login()
    c.require(acknowledged, "Explicit one-cell human acknowledgement required.")
    campaign = load_campaign(directory, sha)
    verify_tools(campaign)
    item, claim = c.select(identity), directory / identity
    c.require(not claim.exists() and not claim.is_symlink(), "Existing claim: collect only.")
    with submission_lock(directory):
        prior = observations(directory)
        c.admit(item, prior, c.digest(campaign))
        capacity(directory, command)
        inputs = campaign["inputs"][str(item["population"])]
        check_inputs(item["population"], inputs)
        selected = selection(item["population"], inputs)
        probe = command(["sbatch", "--test-only", *scheduler_arguments(), "--wrap=/usr/bin/true"])
        c.require(
            probe.returncode == 0, "12h/exclusive scheduler admission rejected; no run claim."
        )
        if item["solver"] == "gurobi":
            from scripts.probe_npad_gurobi_license import check_file

            check_file()  # Metadata only; capacity is checked again on compute.
        plan = {
            "schema_version": c.SCHEMA + "-run",
            "cell": item,
            "source_commit": sha,
            "source_root": str(ROOT),
            "claim_path": str(claim),
            "profile": c.PROFILE,
            "campaign_sha256": c.digest(campaign),
            "selection_sha256": c.digest(selected),
            "cases": [r.spec_payload(c.specification(item, inputs["workbook"]))],
            "created_at_utc": datetime.now(UTC).isoformat(),
            "planned_schedule_index": next(
                i for i, value in enumerate(c.cells()) if value["id"] == identity
            ),
            "actual_submission_index": sum(
                (directory / value["id"]).exists() for value in c.cells()
            ),
        }
        claim.mkdir(mode=0o700)
        write_json(claim / "plan.json", plan)
        write_json(claim / "campaign.json", campaign)
        write_json(claim / "warehouse_selection.json", selected)
        write_json(
            claim / "admission.json",
            {
                "returncode": probe.returncode,
                "stdout": probe.stdout,
                "stderr": probe.stderr,
                "job_submitted": False,
            },
        )
        script = (
            "#!/bin/bash\nset -euo pipefail\n"
            "export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic\n"
            "export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1\n"
            "export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1\n"
            "exec " + shlex.join(invocation("batch", claim, sha)) + "\n"
        )
        with (claim / "batch.sh").open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(script)
        write_json(
            claim / "submission_intent.json", {"cell": identity, "plan_sha256": c.digest(plan)}
        )
        result = command(
            [
                "sbatch",
                "--parsable",
                *scheduler_arguments(),
                "--job-name=pyomo-" + identity,
                "--chdir=" + str(claim),
                "--output=" + str(claim / "slurm.out"),
                "--error=" + str(claim / "slurm.err"),
                str(claim / "batch.sh"),
            ]
        )
        write_json(
            claim / "submission_response.json",
            {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr},
        )
        match = re.fullmatch(r"([1-9][0-9]*)(?:;[A-Za-z0-9_-]+)?\s*", result.stdout)
        c.require(
            result.returncode == 0 and match,
            "Submission uncertain; preserve intent and never repeat start.",
        )
        job = {"job_id": match[1], "source_commit": sha, "plan_sha256": c.digest(plan)}
        write_json(claim / "job.json", job)
        return {
            "status": "submitted_one_cell_only",
            "cell": item,
            **job,
            "automatic_follow_on_allowed": False,
        }


def allocation(
    text, job, uid, *, walltime="12:00:00", memory=("192G", "196608M"), requested_cpus=24
):
    fields = o.fields(text)
    expected = {
        "JobId": job,
        "NumNodes": "1",
        "TimeLimit": walltime,
        "Partition": "intel-256",
        "Account": "sxdsouza",
        "QOS": "preempt",
        "JobState": "RUNNING",
    }
    c.require(
        all(fields.get(k) == v for k, v in expected.items())
        and re.fullmatch(r"[^()\s]+\(" + str(uid) + r"\)", fields.get("UserId", ""))
        and fields.get("MinMemoryNode") in memory
        and exclusive_observed(fields)
        and fields.get("NumCPUs", "").isdigit()
        and int(fields["NumCPUs"]) >= requested_cpus
        and re.fullmatch(r"[A-Za-z0-9_-]+", fields.get("NodeList", "")),
        "Exclusive allocation/resource/owner profile differs.",
    )
    return fields


def exclusive_observed(fields):
    aliases = {"Shared": {"0", "EXCLUSIVE"}, "OverSubscribe": {"NO", "EXCLUSIVE"}}
    observed = [fields[key] in allowed for key, allowed in aliases.items() if key in fields]
    return bool(observed) and all(observed)


def batch(claim, sha):
    outcome = {
        "status": "forensic_partial",
        "source_verified_after": False,
        "automatic_follow_on_allowed": False,
    }
    try:
        _, campaign = load_run(claim, sha)
        deadline = time.monotonic() + 30
        while not (claim / "job.json").exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        job = o.job_receipt(claim, sha)
        c.require(os.environ.get("SLURM_JOB_ID") == job["job_id"], "Compute job differs.")
        query = r.r2.command(["scontrol", "-o", "show", "job", job["job_id"]], timeout=15)
        write_json(
            claim / "allocation_query.json",
            {"returncode": query.returncode, "stdout": query.stdout, "stderr": query.stderr},
        )
        c.require(query.returncode == 0, "Allocation query failed.")
        allocated = allocation(query.stdout, job["job_id"], os.getuid())
        write_json(claim / "allocation.json", allocated)

        def invoke(action, directory, source, *extra):
            c.require(action == "worker", "Worker-only supervisor dispatch.")
            return [
                "--chdir=" + str(directory / "control/sto"),
                sys.executable,
                "-B",
                "-I",
                "-S",
                str(ROOT / BOOTSTRAP),
                "--claim",
                str(directory),
                "--source-sha",
                source,
            ]

        def reviewer(directory, source, mode, remaining):
            with (
                (directory / "control/sto/review.out").open("xb") as out,
                (directory / "control/sto/review.err").open("xb") as err,
            ):
                process = subprocess.run(
                    invocation("review", directory, source),
                    stdout=out,
                    stderr=err,
                    timeout=remaining,
                    check=False,
                )
            c.require(process.returncode == 0, "Original product review failed.")

        observer = ExternalObserver(claim, job)
        try:
            result = o.supervise(
                claim,
                sha,
                "sto",
                allocated,
                job,
                invoke=invoke,
                reviewer=reviewer,
                step_cpus=16,
                bind_step=lambda *args: o.step_binding(*args, cpus=16),
                whole_arm_seconds=c.PROFILE["step_seconds"],
                phase_profile=c.PROFILE,
                sleep=observer.sleep,
            )
        finally:
            observer.finish()
        c.require(result["status"] == "closed_feasible_arm", "Owned step not closed.")
        load_run(claim, sha)
        outcome.update(status="one_observation_returned", source_verified_after=True)
        c.require(campaign["profile"] == c.PROFILE, "Profile drift.")
    except Exception as error:
        outcome["error_kind"] = type(error).__name__
    write_json(claim / "batch_outcome.json", outcome)
    return int(outcome["status"] != "one_observation_returned")


def worker(claim, sha, *, entry, startup):
    control = claim / "control/sto"
    plan = startup.stage("plan_validation", lambda: load_run(claim, sha, expensive=False)[0])
    campaign = read(claim.parent / "campaign.json")
    startup.stage("source_verification", lambda: verify_source(ROOT, campaign["source_files"]))
    startup.stage(
        "runtime_fingerprints",
        lambda: c.require(environment() == campaign["runtime"], "Worker runtime drift."),
    )
    item = plan["cell"]
    inputs = campaign["inputs"][str(item["population"])]
    startup.stage("input_hashes", lambda: check_inputs(item["population"], inputs))
    c.require(
        read(control / "release.json") == entry == read(control / "entry.json")
        and entry["pid"] == os.getpid()
        and entry["proc_start_ticks"] == bootstrap.proc_start(os.getpid()),
        "Exact released worker identity differs.",
    )
    startup.stage("tool_verification", lambda: verify_tools(campaign))
    affinity = sorted(os.sched_getaffinity(0))
    c.require(len(affinity) == 16, "Common16-logical-CPU worker pool required.")
    temporary = control / "native-temporary"
    temporary.mkdir()
    os.environ.update(TMPDIR=str(temporary), TMP=str(temporary), TEMP=str(temporary))

    def native_identity():
        if item["solver"] == "gurobi":
            from scripts import pyomo_gurobi_license_gate as license_gate

            record = license_gate.probe()
            write_json(control / "license-capability.json", record)
            c.require(license_gate.accepted(record), "Default-environment capacity rejected.")
        return {"solver": item["solver"], "packages": c.PACKAGES}

    startup.stage("native_identity", native_identity)
    # The complete paired 1/2/4/8/16 controls were executed in the public job;
    # bind its immutable accepted receipts rather than creating a warm start.
    startup.stage("public_qualification", lambda: load_campaign(claim.parent, sha, expensive=False))
    from scripts.mvp2_scalar_wd_h215_operational import hardware_observation

    hardware = hardware_observation()
    c.require(
        hardware.get("cpu_model") and "observation_error" not in hardware,
        "Hardware class unavailable.",
    )
    topology = cpu_topology(affinity)
    startup.stage(
        "runtime_receipt",
        lambda: write_json(
            control / "runtime.json",
            {
                "affinity_logical_cpus": affinity,
                "solver_threads": item["threads"],
                "hardware": hardware,
                "cpu_topology": topology,
                "hardware_class_sha256": c.digest(
                    {
                        "machine": hardware["machine"],
                        "cpu_model": hardware["cpu_model"],
                        "affinity_physical_cores": topology["physical_cores"],
                        "logical_threads_per_core": topology["logical_threads_per_core"],
                    }
                ),
                "thread_semantics": "Logical CPU ceiling; no actual parallel utilization claim.",
            },
        ),
    )
    run_case(claim, plan, inputs, entry)
    load_run(claim, sha)


def cpu_topology(affinity):
    """Preserve the logical-to-physical mapping; never label logical CPUs as cores."""
    mapping, counts = [], {}
    for cpu in affinity:
        directory = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        package = int(regular(directory / "physical_package_id").read_text())
        core = int(regular(directory / "core_id").read_text())
        mapping.append({"logical_cpu": cpu, "package": package, "core": core})
        counts[package, core] = counts.get((package, core), 0) + 1
    return {
        "mapping": mapping,
        "physical_cores": len(counts),
        "logical_threads_per_core": sorted(counts.values()),
    }


def run_case(claim, plan, inputs, entry):
    from src.logic.experiment_runner import run_experiment
    from src.logic.optimization import solve_model
    from src.logic.optimization_pyomo import PHASE_OBSERVER

    item = plan["cell"]
    control = claim / "control/sto"
    phases = ["input_build"]

    def mark(name):
        c.require(
            len(phases) < len(o.PHASES) and name == o.PHASES[len(phases)], "Phase order differs."
        )
        o.publish(
            control / f"phase-{len(phases):02d}.json",
            {
                "entry": entry,
                "phase": name,
                "elapsed_seconds": time.monotonic() - entry["started_monotonic"],
            },
        )
        phases.append(name)

    def solve(**kwargs):
        token = PHASE_OBSERVER.set(mark)
        try:
            result = solve_model(**kwargs)
        finally:
            PHASE_OBSERVER.reset(token)
        c.effective_parameters(item, result.metadata)
        write_json(
            control / "native_terminal.json",
            {
                "entry": entry,
                "metadata": result.metadata,
                "status": result.status,
                "objective": result.objective_value,
                "bound": result.metadata["objective_bound"],
            },
        )
        mark("independent_validation")
        return result

    def progress(message):
        if "exporting structured artifacts" in message:
            mark("artifact_export")

    def runner(*args, **kwargs):
        kwargs.update(solver=solve, progress=progress)
        return run_experiment(*args, **kwargs)

    spec = c.specification(item, inputs["workbook"])
    r.run_case_software(
        spec,
        claim / "cases" / item["id"],
        {"warehouses": item["population"], "periods": 60, "sto_scenarios": 9},
        read(claim / "warehouse_selection.json"),
        runner=runner,
        input_reviewer=lambda data, receipt: c.input_certificate(item["population"], receipt),
    )
    mark("complete")


def review_products(claim, plan):
    from src.logic.optimization import OptimizationResult, scalar_mip_gap

    item = plan["cell"]
    directory = claim / "cases" / item["id"]
    products = directory / "products" / item["id"]
    result, completion, validation, summary = [
        read(products / name)
        for name in (
            "result.json",
            "run_completion.json",
            "independent_validation.json",
            "run_summary.json",
        )
    ]
    native = result["result"]
    metadata = native["metadata"]
    c.require(
        result["schema_version"] == 2
        and result["experiment"] == plan["cases"][0]
        and native["solver_backend"] == "pyomo"
        and native["solver_name"] == item["solver"]
        and native["model_mode"] == "sto"
        and completion["status"] == "complete"
        and completion["run_identity"] == metadata["run_identity"],
        "Product identity differs.",
    )
    required = {
        "result.json",
        "run_summary.json",
        "independent_validation.json",
        "preflight.json",
        "model_audit.json",
    }
    c.require(required <= completion["artifacts"].keys(), "Incomplete products.")
    for name, expected in completion["artifacts"].items():
        c.require(
            r._safe_name(name) and digest(regular(products / name)) == expected,
            "Completion artifact drift.",
        )
    receipt = read(directory / "input_receipt.json")
    c.require(receipt["experiment"] == plan["cases"][0], "Input receipt case differs.")
    input_binding = c.input_certificate(item["population"], receipt)
    population = read(directory / "warehouses_used.json")
    c.require(
        population == receipt["warehouse_selection"]
        and regular(directory / "warehouses_used.csv").read_bytes()
        == r.warehouses.csv_bytes(population["included"]),
        "Actual membership differs.",
    )
    parameters = c.effective_parameters(item, metadata)
    terminal = read(claim / "control/sto/native_terminal.json")
    c.require(
        terminal["entry"] == read(claim / "control/sto/entry.json")
        and terminal["status"] == native["status"]
        and terminal["objective"] == native["objective_value"]
        and terminal["bound"] == metadata["objective_bound"]
        and all(
            terminal["metadata"][key] == metadata[key]
            for key in (
                "common_linear_matrix",
                "pyomo_reformulation",
                "effective_native_options",
                "solver_termination",
                "native_counters",
                "solver_versions",
            )
        ),
        "Native terminal and exported product differ.",
    )
    usable = OptimizationResult(
        status=native["status"], objective_value=native["objective_value"]
    ).has_solution
    accepted_incumbent = usable and validation["status"] == "accepted"
    c.require(
        not usable
        or (
            accepted_incumbent
            and validation["failed_check_count"] == 0
            and validation["validator_version"] == "mvp2-scalar-independent-residuals-v1"
            and validation["absolute_tolerance"] == 1e-5
            and validation["relative_tolerance"] == 1e-8
            and all(v["failed"] == 0 for v in validation["families"].values())
        ),
        "Original incumbent residual validation rejected.",
    )
    c.require(
        summary["independent_validation_status"] == validation["status"],
        "Summary validation binding differs.",
    )
    termination = metadata["solver_termination"]
    c.require(
        termination in {"TerminationCondition.optimal", "TerminationCondition.maxTimeLimit"},
        "Unexpected terminal status; preserve and review separately.",
    )
    c.require(
        usable or termination == "TerminationCondition.maxTimeLimit",
        "An optimal terminal result requires a usable incumbent.",
    )
    gap = (
        scalar_mip_gap(native["objective_value"], metadata.get("objective_bound"))
        if usable
        else None
    )
    return {
        "native_result_returned": True,
        "has_usable_incumbent": usable,
        "incumbent_validation_rejected": False,
        "objective": native["objective_value"],
        "bound": metadata.get("objective_bound"),
        "common_gap": gap,
        "native_gap": metadata.get("pyomo_native_gap"),
        "native_status": termination,
        "original_validation_status": validation["status"],
        "quality_target_met": accepted_incumbent and gap is not None and gap <= 0.01,
        "classification": "validated_feasible" if accepted_incumbent else "no_usable_incumbent",
        "input_binding": input_binding,
        "matrix_sha256": metadata["common_linear_matrix"]["sha256"],
        "common_linear_matrix": metadata["common_linear_matrix"],
        "bounds_sha256": metadata["pyomo_reformulation"]["bounds_sha256"],
        "reformulation": metadata["pyomo_reformulation"],
        "effective_parameters": parameters,
        "native_counters": metadata["native_counters"],
        "timings": metadata["timings"],
        "economic_cost": summary.get("economic_cost") if usable else None,
        "penalized_total": summary.get("penalized_cost") if usable else None,
    }


def evidence_files(claim):
    files, total = {}, 0
    for path in sorted(claim.rglob("*")):
        relative = path.relative_to(claim).as_posix()
        c.require(not path.is_symlink(), "Linked evidence rejected.")
        if not path.is_file() or "native-temporary" in path.parts:
            continue
        if relative in {"evidence.tar.gz", "evidence.tar.gz.sha256", "collection.json"}:
            continue
        c.require(
            r._safe_name(relative)
            and path.suffix.lower() not in {".lic", ".xlsx", ".sqlite", ".sqlite3", ".db"},
            "Forbidden evidence member.",
        )
        total += path.stat().st_size
        c.require(
            total <= c.PROFILE["expanded_transfer_bytes"]
            and len(files) < c.PROFILE["max_regular_members"] - 2,
            "Evidence cap exceeded; preserve without truncating.",
        )
        files[relative] = path
    return files


def small_controls(files):
    prefixes = ("control/sto/",)
    return {
        name: path.read_bytes()
        for name, path in files.items()
        if (name.startswith(prefixes) and path.suffix == ".json")
        or name in {"external-observer.json", "external-resource-timeseries.csv"}
    }


def operational_closure(claim, job, rows, wanted, controls):
    """Replay owned allocation, exact step, phase budgets and cold startup."""
    entry = read(claim / "control/sto/entry.json")
    c.require(
        read(claim / "control/sto/release.json") == entry
        and all(entry[k] == v for k, v in job.items()),
        "Entry/release/job differs.",
    )
    query = read(claim / "allocation_query.json")
    fields = o.fields(query["stdout"])
    owner = re.fullmatch(r"[^()]+\(([0-9]+)\)", fields["UserId"])
    c.require(owner and query["returncode"] == 0, "Allocation receipt missing.")
    allocated = allocation(query["stdout"], job["job_id"], int(owner[1]))
    c.require(allocated == read(claim / "allocation.json"), "Allocation replay differs.")
    step = read(claim / "control/sto/step_query.json")
    c.require(step["returncode"] == 0, "Step query failed.")
    o.step_binding(step["stdout"], entry, allocated, int(owner[1]), cpus=16)
    events = o.events_at(claim / "control/sto", entry)
    c.require([e["phase"] for e in events] == list(o.PHASES), "Complete phase ledger required.")
    usage = o.phase_usage(events, events[-1]["elapsed_seconds"], profile=c.PROFILE)
    c.require(
        usage["stop_reason"] is None and events[-1]["elapsed_seconds"] <= c.PROFILE["step_seconds"],
        "Original phase budget was exceeded.",
    )
    startup = bootstrap.review(controls, job)
    controller = read(claim / "control/sto/controller.json")
    batch_record = read(claim / "batch_outcome.json")
    closed = (
        all(
            row["state"] == "COMPLETED" and row["exit_code"] == "0:0"
            for row in rows
            if row["job_id"] in wanted
        )
        and controller["status"] == "closed_feasible_arm"
        and controller["local_client_reaped"] is True
        and controller["step_id"] == entry["step_id"]
        and controller["usage"] == usage
        and batch_record["source_verified_after"] is True
        and batch_record["status"] == "one_observation_returned"
        and startup["status"] == "complete"
    )
    return closed, startup


def collect(claim, sha, *, command=r.r2.command):
    login()
    plan, campaign = load_run(claim, sha)
    marker = claim / "collection.json"
    if marker.exists():
        saved = read(marker)
        archive_report(claim, saved)
        c.require(
            regular(claim / "evidence.tar.gz.sha256").read_text().strip()
            == saved["sha256"] + "  evidence.tar.gz",
            "Preserved checksum differs.",
        )
        return saved
    c.require(
        not any(
            (claim / name).exists()
            for name in ("evidence.tar.gz", "campaign_observation.json", "inventory.json")
        ),
        "Incomplete previous collection preserved; do not overwrite or restart.",
    )
    job = o.job_receipt(claim, sha)
    query = command(
        [
            "sacct",
            "-j",
            job["job_id"],
            "--noheader",
            "--parsable2",
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
        ]
    )
    c.require(query.returncode == 0, "Accounting unavailable; collect later without retry.")
    rows = r.r2.accounting(query.stdout, job["job_id"])
    wanted = {job["job_id"], job["job_id"] + ".batch"}
    entry_path = claim / "control/sto/entry.json"
    if entry_path.exists():
        entry = read(entry_path)
        c.require(
            all(entry[k] == v for k, v in job.items()) and entry["step_id"].isdigit(),
            "Owned step differs.",
        )
        wanted.add(job["job_id"] + "." + entry["step_id"])
    if not wanted <= {row["job_id"] for row in rows} or any(
        row["state"] not in r.r2.TERMINAL for row in rows
    ):
        return {"status": "nonterminal_or_accounting_pending", "job_id": job["job_id"]}
    terminal = claim / "terminal_accounting.json"
    if not terminal.exists():
        write_json(terminal, {"raw": query.stdout, "rows": rows})
    rows = read(terminal)["rows"]
    files = evidence_files(claim)
    report = {
        "cell": plan["cell"],
        "campaign_sha256": c.digest(campaign),
        **job,
        "profile": c.PROFILE,
        "accounting": rows,
        "native_result_returned": False,
        "classification": "build_or_execution_incomplete",
        "objective": None,
        "bound": None,
        "common_gap": None,
        "native_gap": None,
        "operational_receipts_closed": False,
        "incumbent_validation_rejected": False,
        "automatic_follow_on_allowed": False,
        "status": "forensic_partial_preserved",
    }
    controls = small_controls(files)
    report["resource_observation"] = review_external(controls, job)
    try:
        science = review_products(claim, plan)
        runtime = read(claim / "control/sto/runtime.json")
        report.update(
            science,
            worker_affinity_logical_cpus=len(runtime["affinity_logical_cpus"]),
            hardware_class_sha256=runtime["hardware_class_sha256"],
        )
        closed, startup = operational_closure(claim, job, rows, wanted, controls)
        report.update(
            startup=startup,
            operational_receipts_closed=closed,
            status="observation_collected" if closed else "forensic_partial_preserved",
        )
    except Exception as error:
        report["review_error_kind"] = type(error).__name__
    load_run(claim, sha)
    report_path = claim / "campaign_observation.json"
    write_json(report_path, report)
    files["campaign_observation.json"] = report_path
    inventory = {name: digest(path) for name, path in files.items()}
    inventory_path = claim / "inventory.json"
    write_json(inventory_path, inventory)
    files["inventory.json"] = inventory_path
    c.require(
        len(files) <= c.PROFILE["max_regular_members"]
        and sum(p.stat().st_size for p in files.values()) <= c.PROFILE["expanded_transfer_bytes"],
        "Final archive cap exceeded; preserve files.",
    )
    archive = claim / "evidence.tar.gz"
    # Stream all large products; no aggregate multi-gigabyte in-memory snapshot.
    with archive.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as tar:
        for name, path in sorted(files.items()):
            info = tar.gettarinfo(str(path), arcname=name)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mode = 0o600
            with path.open("rb") as source:
                tar.addfile(info, source)
            expected = inventory[name] if name != "inventory.json" else digest(inventory_path)
            c.require(
                digest(path) == expected,
                "Evidence changed during streaming; preserve partial archive.",
            )
    checksum = digest(archive)
    with (claim / "evidence.tar.gz.sha256").open("x", encoding="utf-8") as stream:
        stream.write(checksum + "  evidence.tar.gz\n")
    saved = {"sha256": checksum, "archive": str(archive), "observation": report}
    write_json(marker, saved)
    return saved


def tables(directory, sha, output):
    """All90 planned cells remain visible; failures/timeouts are never dropped."""
    login()
    manifest = load_campaign(directory, sha)
    observed = {row["cell"]["id"]: row for row in observations(directory)}
    c.require(
        output.parent.resolve() == directory and not output.exists() and not output.is_symlink(),
        "Fresh table directory under campaign required.",
    )
    output.mkdir()
    configs, results = [], []
    for item in c.cells():
        configs.append(
            {
                **item,
                "interface": "appsi_" + item["solver"],
                "formulation": c.POLICY,
                "highs_parallel": "on" if item["solver"] == "highs" else "not_applicable",
                "memory_mib": c.PROFILE["memory_mib"],
                "worker_logical_cpus": 16,
                "slurm_seconds": 43200,
                "source_commit": sha,
                "campaign_sha256": c.digest(manifest),
            }
        )
        row = observed.get(item["id"], {})
        claimed = (directory / item["id"]).exists()
        timing = row.get("timings", {})
        results.append(
            {
                "id": item["id"],
                "population": item["population"],
                "solver": item["solver"],
                "threads": item["threads"],
                "repetition": item["repetition"],
                "status": row.get("status", "claimed_not_collected" if claimed else "not_started"),
                "job_id": row.get("job_id"),
                "classification": row.get("classification"),
                "objective": row.get("objective"),
                "bound": row.get("bound"),
                "common_gap_fraction": row.get("common_gap"),
                "native_gap_fraction": row.get("native_gap"),
                "quality_target_met": row.get("quality_target_met"),
                "validation_status": row.get("original_validation_status"),
                "solver_reported_seconds": timing.get("solver_reported_runtime_seconds"),
                "optimization_seconds": timing.get("optimization_seconds"),
                "model_build_seconds": timing.get("model_build_seconds"),
                "matrix_identity_seconds": timing.get("matrix_identity_seconds"),
                "solver_transfer_seconds": timing.get("solver_transfer_seconds"),
                "end_to_end_seconds": timing.get("end_to_end_seconds"),
                "sampled_worker_tree_peak_bytes": row.get("resource_observation", {}).get(
                    "sampled_worker_tree_peak_bytes"
                ),
                "matrix_sha256": row.get("matrix_sha256"),
                "operational_receipts_closed": row.get("operational_receipts_closed"),
            }
        )
    for name, rows in (("configurations.csv", configs), ("results.csv", results)):
        with (output / name).open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    write_json(output / "observations.json", list(observed.values()))
    return {
        "status": "comparative_tables_written",
        "planned_cells": 90,
        "collected": len(observed),
        "output": str(output),
        "scope": "Descriptive temporal repetitions; no automatic significance claim.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("inventory", "init", "status", "start", "batch", "review", "collect", "tables"),
    )
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--cell")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--acknowledge-one-cell", action="store_true")
    args = parser.parse_args()
    if args.action == "inventory":
        login()
        inputs = default_inputs() if args.inputs is None else read(args.inputs)
        result = {
            "scope": "read_only_metadata_and_hashes_no_solver_no_scheduler_no_files_created",
            "inputs": inputs,
            "verified_sha256": {p: check_inputs(int(p), paths) for p, paths in inputs.items()},
            "environment": environment(),
        }
    elif args.action == "init":
        inputs = default_inputs() if args.inputs is None else read(args.inputs)
        result = init(args.directory, args.source_sha, inputs)
    elif args.action == "start":
        result = start(args.directory, args.source_sha, args.cell, args.acknowledge_one_cell)
    elif args.action == "status":
        login()
        campaign = load_campaign(args.directory, args.source_sha)
        observed = observations(args.directory)
        pending = []
        for item in c.cells():
            if (args.directory / item["id"]).exists():
                continue
            try:
                c.admit(item, observed, c.digest(campaign))
                pending.append(item)
            except ValueError:
                pass
        result = {
            "collected": len(observed),
            "eligible_unclaimed": pending,
            "automatic_follow_on_allowed": False,
        }
    elif args.action == "batch":
        return batch(args.directory, args.source_sha)
    elif args.action == "tables":
        c.require(args.output is not None, "Fresh local table output required.")
        result = tables(args.directory, args.source_sha, args.output)
    elif args.action == "review":
        plan, _ = load_run(args.directory, args.source_sha)
        result = review_products(args.directory, plan)
        write_json(args.directory / "control/sto/review.json", result)
    else:
        result = collect(args.directory, args.source_sha)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
