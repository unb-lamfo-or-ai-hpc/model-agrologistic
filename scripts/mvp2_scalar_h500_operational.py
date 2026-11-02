"""One approved h500 STO observation with original validation and terminal evidence."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

from scripts import mvp2_scalar_h300_operational as previous
from scripts import mvp2_scalar_h500_contract as c

o, r = c.o, c.r
ROOT = c.ROOT
CLAIM = ".mvp2-scalar-h500-8h-v1"
ARCHIVE = "scalar-h500-8h-evidence.tar.gz"
ARM = "t1"
NPAD_HOME = Path("/home/vrrcelestino")


def approved_claim(claim):
    """Confine CLI outputs to a project directory; never write in the home root."""
    claim = Path(claim).absolute()
    parent = claim.parent.resolve()
    home = NPAD_HOME.resolve()
    r.require(
        parent.parent == home
        and parent.name.startswith("model-agrologistic")
        and parent.name != "model-agrologistic"
        and claim.name == CLAIM
        and not claim.is_symlink(),
        "Use an approved model-agrologistic output directory, never the home root "
        "or the preserved input checkout.",
    )
    return parent / claim.name


def prepare(claim, sha, workbook, population, order, materialization_path, predecessor):
    r.require(
        claim.name == CLAIM and not claim.exists() and not claim.is_symlink(),
        "Fresh exclusive h500 claim required; preserve all earlier claims.",
    )
    r.require(re.fullmatch(r"[0-9a-f]{40}", sha), "Full reviewed source SHA.")
    r.require(
        r.file_hash(c.h.input_file(workbook, "h500 workbook")) == c.WORKBOOK_SHA,
        "Historical h500 workbook hash differs; never substitute input.",
    )
    audit = c.h.input_file(materialization_path, "h500 OSRM audit").read_bytes()
    c.materialization(r.strict_json(audit))
    parent = c.predecessor(predecessor)
    selection = c.read_selection(workbook, population, order)
    inventory = r.r2.source_inventory(ROOT)
    r.require(inventory["source_commit"] == sha, "Wrong source head.")
    r.r2.verify_source(inventory, ROOT)
    tools = {k: str(o.regular(Path(shutil.which(k) or "").resolve())) for k in o.TOOLS}
    plan = {
        "schema_version": "scalar-h500-operational-v1",
        "status": "prepared_for_one_human_h500",
        "source_commit": sha,
        "source_root": str(ROOT),
        "python": sys.executable,
        "python_sha256": r.file_hash(sys.executable),
        "tools": tools,
        "tool_sha256": {k: r.file_hash(v) for k, v in tools.items()},
        "source_inventory_sha256": r.r2.digest(r.r2.encoded(inventory)),
        "warehouse_selection_sha256": r.r2.digest(r.r2.encoded(selection)),
        "materialization_original_sha256": r.r2.digest(audit),
        "predecessor": parent,
        "resources": c.PROFILE,
        "quality_criteria": c.QUALITY,
        "cases": [r.spec_payload(s) for s in c.specs(workbook)],
        "expected_shape": c.SHAPE,
        "frozen_rates": c.h.RATES,
        **r.closed(),
    }
    files = {
        "plan.json": r.r2.encoded(plan),
        "source.json": r.r2.encoded(inventory),
        "warehouse_selection.json": r.r2.encoded(selection),
    }
    c.design(files)
    r.require(r.file_hash(workbook) == c.WORKBOOK_SHA, "Input changed during preparation.")
    claim.mkdir(mode=0o700)
    for name, value in {**files, "materialization.original.json": audit}.items():
        with (claim / name).open("xb") as stream:
            stream.write(value)
    return r.strict_json(files["plan.json"])


def load(claim, sha):
    r.require(claim.name == CLAIM and not claim.is_symlink(), "Dedicated unlinked h500 claim.")
    files = {
        n: o.regular(claim / n).read_bytes()
        for n in ("plan.json", "source.json", "warehouse_selection.json")
    }
    plan = c.design(files)
    r.require(
        plan["source_commit"] == sha and Path(plan["source_root"]).resolve() == ROOT,
        "Source head/root differs.",
    )
    r.r2.verify_source(r.strict_json(files["source.json"]), ROOT)
    r.require(r.file_hash(sys.executable) == plan["python_sha256"], "Python drift.")
    audit = o.regular(claim / "materialization.original.json").read_bytes()
    r.require(r.r2.digest(audit) == plan["materialization_original_sha256"], "OSRM audit drift.")
    c.materialization(r.strict_json(audit))
    return plan


def invocation(action, claim, sha, *extra):
    return [
        sys.executable,
        "-B",
        "-I",
        "-c",
        "import runpy,sys;sys.dont_write_bytecode=True;sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('scripts.mvp2_scalar_h500_operational',run_name='__main__')",
        str(ROOT),
        action,
        "--claim",
        str(claim),
        "--source-sha",
        sha,
        *extra,
    ]


def start(claim, sha, acknowledged, paths, *, command=r.r2.command):
    r.require(acknowledged, "One reviewed h500 observation must be acknowledged by human CLI.")
    r.require(sys.version_info[:2] == (3, 13) and not os.environ.get("SLURM_JOB_ID"), "Login only.")
    if claim.exists():
        load(claim, sha)
        o.job_receipt(claim, sha)
        return {"status": "existing_claim_collect_only", **r.closed()}
    from scripts.probe_npad_gurobi_license import check_file

    check_file()  # Designated file metadata only; no solver or secret read on login.
    plan = prepare(claim, sha, **paths)
    token = r.r2.digest(r.r2.encoded(plan))
    with (claim / "batch.sh").open("x", newline="\n") as stream:
        stream.write("#!/bin/sh\nexec " + shlex.join(invocation("batch", claim, sha)) + "\n")
    r.r2.write(
        claim / "submission_intent.json",
        {"plan_sha256": token, "one_h500_acknowledged": True, "automatic_retry": False},
    )
    result = command(
        [
            "sbatch",
            "--parsable",
            "--account=sxdsouza",
            "--partition=intel-256",
            "--qos=preempt",
            "--nodes=1",
            "--ntasks=1",
            "--cpus-per-task=24",
            "--mem=192G",
            "--time=08:00:00",
            "--no-requeue",
            "--export=ALL",
            "--job-name=scalar-h500-8h",
            "--chdir=" + str(claim),
            "--output=" + str(claim / "slurm.out"),
            "--error=" + str(claim / "slurm.err"),
            str(claim / "batch.sh"),
        ]
    )
    r.r2.write(
        claim / "submission.json",
        {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr},
    )
    match = re.fullmatch(r"([1-9][0-9]*)(?:;[A-Za-z0-9_.-]+)?\s*", result.stdout)
    r.require(
        result.returncode == 0 and match,
        "Submission uncertain; preserve the consumed claim, never retry.",
    )
    job = {"job_id": match[1], "source_commit": sha, "plan_sha256": token}
    o.publish(claim / "job.json", job)
    return {"status": "submitted_one_h500_only", **job, **r.closed()}


def allocation(text, job, uid):
    raw = o.fields(text).get("TimeLimit", "")
    match = re.fullmatch(r"(?:(\d+)-)?(\d+):([0-5]\d):([0-5]\d)", raw)
    r.require(match is not None, "Allocation time grammar.")
    days, hours, minutes, seconds = map(lambda v: int(v or 0), match.groups())
    r.require(
        (not days or hours < 24) and days * 86400 + hours * 3600 + minutes * 60 + seconds == 28800,
        "Approved eight-hour allocation required.",
    )
    return o.allocation(text, job, uid, walltime=raw)


def worker(claim, sha):
    plan = load(claim, sha)
    job = o.job_receipt(claim, sha)
    step = os.environ.get("SLURM_STEP_ID", "")
    r.require(
        os.environ.get("SLURM_JOB_ID") == job["job_id"] and step.isdigit(),
        "Owned job/numeric step required.",
    )
    control = claim / "control" / ARM
    entry = {
        **job,
        "mode": ARM,
        "step_id": step,
        "pid": os.getpid(),
        "started_monotonic": time.monotonic(),
    }
    o.publish(control / "entry.json", entry)
    until = time.monotonic() + 60
    while not (control / "release.json").exists() and time.monotonic() < until:
        time.sleep(0.1)
    r.require(r.r2.read(control / "release.json") == entry, "Owned-step release absent/different.")
    o.verify_tools(plan)
    baseline = r.r2.read(o.regular(claim / "hardware.json"))
    pool = baseline["affinity_logical_cpus"]
    r.require(set(pool) <= set(os.sched_getaffinity(0)), "Approved affinity unavailable.")
    os.sched_setaffinity(0, pool)
    r.require(
        sorted(os.sched_getaffinity(0)) == pool and previous.hardware(pool) == baseline,
        "CPU affinity/topology drift.",
    )
    from scripts.probe_npad_gurobi_license import probe

    capability = probe()
    r.r2.write(control / "license_capability.json", capability)
    r.require(capability["status"] == "accepted", "Fresh designated WLS capability rejected.")
    spec = c.specs(Path(plan["cases"][0]["workbook"]))[0]
    r.require(
        r.strict_json(r.r2.encoded(r.spec_payload(spec))) == plan["cases"][0],
        "Frozen h500 configuration/input differs.",
    )
    r.r2.write(
        control / "runtime.json",
        {
            **baseline,
            "python": platform.python_version(),
            "python_sha256": r.file_hash(sys.executable),
            "gurobi_version": capability["gurobi_version"],
            "solver_threads": 1,
            "slurm_step_allocated_cpus": 24,
            "worker_affinity_logical_cpus": 16,
        },
    )
    o.run_case(
        spec,
        claim / "cases" / spec.name,
        c.SHAPE,
        r.r2.read(claim / "warehouse_selection.json"),
        control,
        entry,
        input_reviewer=previous.input_reviewer,
    )
    load(claim, sha)


def science_review(files, plan):
    report = o.scalar_review(
        files,
        {**plan, "selection_sha256": plan["warehouse_selection_sha256"]},
        expected_count=1,
        include_case_names=True,
    )
    accepted, rejected = [], list(report["missing_or_rejected"])
    for arm in report["arms"]:
        try:
            prefix = "cases/" + arm["case_name"]
            receipt = r.strict_json(files[prefix + "/input_receipt.json"])
            vector = c.h.penalty_receipt(
                receipt["mathematical_contract"],
                warehouse_ids=[
                    m["warehouse_id"] for m in receipt["warehouse_selection"]["included"]
                ],
            )
            r.require(receipt["frozen_penalty_review"] == vector, "Effective penalty drift.")
            summary = r.strict_json(
                files[prefix + "/products/" + arm["case_name"] + "/run_summary.json"]
            )
            arm["physical_diagnostics"] = {
                k: summary.get(k)
                for k in (
                    "domestic_service_level",
                    "total_unmet_demand",
                    "emergency_static_capacity",
                    "emergency_reception_capacity",
                    "penalty_cost_share",
                    "minimum_scenario_service_level",
                    "maximum_scenario_service_level",
                    "peak_rss_mb",
                )
            }
            arm["absolute_gap"] = (
                abs(arm["objective"] - arm["bound"])
                if arm["objective"] is not None and arm["bound"] is not None
                else None
            )
            accepted.append(arm)
        except (KeyError, ValueError, TypeError) as exc:
            rejected.append({"name": arm["case_name"], "error_kind": type(exc).__name__})
    feasible = (
        len(accepted) == 1
        and not rejected
        and accepted[0]["classification"] == "validated_feasible"
    )
    quality = feasible and accepted[0]["scalar_gap_target_met"]
    return {
        "status": "h500_quality_target_met"
        if quality
        else (
            "h500_feasible_quality_censored" if feasible else "h500_partial_or_rejected_preserved"
        ),
        "arms": accepted,
        "missing_or_rejected": rejected,
        "quality_target_met": quality,
        "penalty_rates": c.h.RATES,
        "additional_execution_admitted": False,
        "qualification": "Original certificate replay, not fresh private-input residual re-solve.",
        **r.closed(),
    }


def snapshot(claim):
    return o.snapshot(claim, archive_name=ARCHIVE)


def review_arm(claim, sha):
    report = science_review(snapshot(claim), load(claim, sha))
    r.require(
        len(report["arms"]) == 1 and report["arms"][0]["classification"] == "validated_feasible",
        "Original validated incumbent required.",
    )
    chosen = report["arms"][0]
    r.r2.write(claim / "control" / ARM / "review.json", chosen)
    return chosen


def review_process(claim, sha, arm, remaining):
    r.require(arm == ARM, "Only the approved h500 arm.")
    target = claim / "control" / arm
    with (target / "review.out").open("xb") as out, (target / "review.err").open("xb") as err:
        result = subprocess.run(
            invocation("review", claim, sha), stdout=out, stderr=err, timeout=remaining, check=False
        )
    r.require(result.returncode == 0, "Post-worker review failed; preserve logs.")


def supervise(claim, sha, allocated, job):
    return o.supervise(
        claim,
        sha,
        ARM,
        allocated,
        job,
        invoke=invocation,
        step_cpus=24,
        bind_step=previous.bind_step,
        reviewer=review_process,
        whole_arm_seconds=c.PROFILE["step_seconds"],
        phase_profile=c.PROFILE,
    )


def batch(claim, sha):
    begun = time.monotonic()
    outcome = {"status": "blocked_or_partial", "completed_arms": [], "unrun": [ARM], **r.closed()}
    phase = "source_and_job_binding"
    try:
        plan = load(claim, sha)
        o.verify_tools(plan)
        until = time.monotonic() + 30
        while not (claim / "job.json").exists() and time.monotonic() < until:
            time.sleep(0.1)
        job = o.job_receipt(claim, sha)
        r.require(job["job_id"] == os.environ.get("SLURM_JOB_ID"), "Batch job mismatch.")
        r.r2.write(claim / "batch_entry.json", job)
        phase = "allocation_and_hardware"
        query = r.r2.command(["scontrol", "-o", "show", "job", job["job_id"]])
        r.r2.write(
            claim / "allocation_query.json",
            {"returncode": query.returncode, "stdout": query.stdout, "stderr": query.stderr},
        )
        r.require(query.returncode == 0, "Allocation query failed.")
        allocated = allocation(query.stdout, job["job_id"], os.getuid())
        r.r2.write(claim / "allocation.json", allocated)
        pool = sorted(os.sched_getaffinity(0))[:16]
        r.r2.write(claim / "hardware.json", previous.hardware(pool))
        phase = "h500_single_arm"
        r.require(
            time.monotonic() - begun <= c.PROFILE["setup_cleanup_seconds"],
            "Allocation setup budget exhausted; no worker admitted.",
        )
        outcome["unrun"] = []
        worker_started = time.monotonic()
        control = supervise(claim, sha, allocated, job)
        worker_span = time.monotonic() - worker_started
        r.require(control["next_arm_allowed"], "Stop; preserve partial h500 evidence.")
        load(claim, sha)
        auxiliary = time.monotonic() - begun - worker_span
        r.require(
            auxiliary <= c.PROFILE["setup_cleanup_seconds"], "Setup/cleanup budget exhausted."
        )
        outcome.update(
            status="h500_returned",
            completed_arms=[ARM],
            source_verified_after=True,
            auxiliary_seconds=auxiliary,
        )
    except Exception as exc:
        outcome.update(error_kind=type(exc).__name__, failure_phase=phase)
    r.r2.write(claim / "batch_outcome.json", outcome)
    return int(outcome["status"] != "h500_returned")


def rss_bytes(raw):
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([KMGT])", raw or "")
    r.require(match is not None, "Missing/unsupported Slurm RSS; do not infer zero.")
    value = float(match[1]) * 1024 ** ("KMGT".index(match[2]) + 1)
    r.require(math.isfinite(value) and value > 0, "Invalid Slurm RSS observation.")
    return value


def resource_observations(files, science, rows):
    """Report separate resource scopes; no frontier admission or new service rule."""
    measured, blockers = {}, []
    try:
        arm = science["arms"][0]
        entry = r.strict_json(files["control/" + ARM + "/entry.json"])
        exact = entry["job_id"] + "." + entry["step_id"]
        row = next(value for value in rows if value["job_id"] == exact)
        peak = arm["physical_diagnostics"]["peak_rss_mb"]
        r.require(
            type(peak) in (int, float) and math.isfinite(peak) and peak > 0, "OS peak absent."
        )
        measured["sampled_application_peak_bytes"] = peak * 1024**2
        r.require(
            math.isfinite(measured["sampled_application_peak_bytes"]), "OS peak bytes invalid."
        )
        measured["slurm_step_max_rss_bytes"] = rss_bytes(row["max_rss_raw"])
        prefix = "cases/" + arm["case_name"] + "/products/" + arm["case_name"] + "/resources/"
        telemetry = r.strict_json(files[prefix + "termination.json"])
        r.require(
            not telemetry["inspection_errors"]
            and all(v == 0 for v in telemetry["dropped_samples"].values()),
            "Incomplete resource telemetry.",
        )
        values = [
            float(row["solver_memory_bytes"])
            for row in csv.DictReader(io.StringIO(files[prefix + "solver_progress.csv"].decode()))
            if row.get("solver_memory_bytes")
        ]
        r.require(
            values and all(math.isfinite(v) and v > 0 for v in values), "Native memory absent."
        )
        measured["sampled_native_peak_bytes"] = max(values)
    except (ValueError, KeyError, TypeError, IndexError, StopIteration):
        blockers.append("missing_or_incomplete_separately_scoped_resource_evidence")
    return {
        "resource_observations_complete": not blockers,
        "resource_observation_blockers": blockers,
        "resource_observations": measured,
        "additional_execution_admitted": False,
    }


def portable_review(files):
    plan = c.design(files)
    job = r.strict_json(files["job.json"])
    r.require(
        re.fullmatch(r"[1-9][0-9]*", job["job_id"])
        and job["source_commit"] == plan["source_commit"]
        and job["plan_sha256"] == r.r2.digest(files["plan.json"]),
        "Job/plan binding.",
    )
    audit = files["materialization.original.json"]
    r.require(r.r2.digest(audit) == plan["materialization_original_sha256"], "OSRM audit binding.")
    c.materialization(r.strict_json(audit))
    rows = r.r2.accounting(files["accounting.txt"].decode(), job["job_id"])
    r.require(r.r2.terminal(rows, job["job_id"]), "Terminal accounting required.")
    science = science_review(files, plan)
    operational, error = False, None
    try:
        query = r.strict_json(files["allocation_query.json"])
        owner = re.fullmatch(r"[^()]+\(([0-9]+)\)", o.fields(query["stdout"])["UserId"])
        r.require(query["returncode"] == 0 and owner, "Allocation owner/query.")
        allocated = allocation(query["stdout"], job["job_id"], int(owner[1]))
        r.require(
            allocated == r.strict_json(files["allocation.json"])
            and r.strict_json(files["batch_entry.json"]) == job,
            "Allocation/batch replay.",
        )
        baseline = r.strict_json(files["hardware.json"])
        pool = baseline["affinity_logical_cpus"]
        r.require(
            len(pool) == len(set(pool)) == 16 and all(type(v) is int and v >= 0 for v in pool),
            "CPU pool.",
        )
        base = "control/" + ARM + "/"
        entry = r.strict_json(files[base + "entry.json"])
        r.require(
            all(entry[k] == v for k, v in job.items())
            and entry["mode"] == ARM
            and r.strict_json(files[base + "release.json"]) == entry,
            "Entry/release.",
        )
        query = r.strict_json(files[base + "step_query.json"])
        r.require(query["returncode"] == 0, "Step query failed.")
        exact = previous.bind_step(query["stdout"], entry, allocated, int(owner[1]))
        control = r.strict_json(files[base + "controller.json"])
        events = [r.strict_json(files[n]) for n in sorted(files) if n.startswith(base + "phase-")]
        r.require(
            events
            and all(e["entry"] == entry for e in events)
            and events[-1]["phase"] == "complete",
            "Phase closure.",
        )
        usage = o.phase_usage(events, events[-1]["elapsed_seconds"], profile=c.PROFILE)
        r.require(
            control["status"] == "closed_feasible_arm"
            and control["local_client_reaped"]
            and control["step_id"] == entry["step_id"]
            and control["usage"] == usage
            and usage["stop_reason"] is None,
            "Controller/phase budget.",
        )
        chosen = science["arms"][0]
        r.require(
            len(science["arms"]) == 1
            and not science["missing_or_rejected"]
            and chosen["classification"] == "validated_feasible"
            and r.strict_json(files[base + "review.json"]) == chosen,
            "Original product review.",
        )
        terminal = r.strict_json(files[base + "native_terminal.json"])
        r.require(
            terminal["entry"] == entry
            and terminal["solution_count"] > 0
            and terminal["time_limit_seconds"] == 14400
            and type(terminal["runtime_seconds"]) in (int, float)
            and math.isfinite(terminal["runtime_seconds"])
            and 0 <= terminal["runtime_seconds"] <= 15300,
            "Native terminal/budget.",
        )
        seconds = control["product_review_seconds"]
        r.require(
            type(seconds) in (int, float)
            and math.isfinite(seconds)
            and seconds >= 0
            and seconds + usage["seconds"]["independent_validation"] <= 1800,
            "Combined validation/review budget.",
        )
        capability = r.strict_json(files[base + "license_capability.json"])
        runtime = r.strict_json(files[base + "runtime.json"])
        from scripts.probe_npad_gurobi_license import LICENSE_FILE

        r.require(
            capability["status"] == "accepted"
            and capability["license_file"] == LICENSE_FILE
            and capability["probe_variable_count"] == capability["probe_constraint_count"] == 2001
            and abs(capability["objective_value"] - 2001) <= 1e-6
            and capability["gurobi_version"][0] == 13,
            "Fresh designated WLS capability.",
        )
        r.require(
            all(runtime[k] == v for k, v in baseline.items())
            and runtime["python"].startswith("3.13.")
            and runtime["python_sha256"] == plan["python_sha256"]
            and runtime["gurobi_version"] == capability["gurobi_version"]
            and runtime["solver_threads"] == 1
            and runtime["slurm_step_allocated_cpus"] == 24
            and runtime["worker_affinity_logical_cpus"] == 16,
            "Runtime/affinity/threads.",
        )
        wanted = {job["job_id"], job["job_id"] + ".batch", exact}
        numeric = {
            row["job_id"]
            for row in rows
            if row["job_id"].split(".")[-1].isdigit() and "." in row["job_id"]
        }
        r.require(
            wanted <= {row["job_id"] for row in rows}
            and numeric == {exact}
            and all(
                row["state"] == "COMPLETED"
                and row["exit_code"] == "0:0"
                and row["elapsed_seconds"] <= (20700 if row["job_id"] == exact else 28800)
                for row in rows
            ),
            "Accounting closure/budget.",
        )
        outcome = r.strict_json(files["batch_outcome.json"])
        r.require(
            outcome["status"] == "h500_returned"
            and outcome["completed_arms"] == [ARM]
            and outcome["unrun"] == []
            and outcome["source_verified_after"],
            "Batch closure.",
        )
        auxiliary = outcome["auxiliary_seconds"]
        r.require(
            type(auxiliary) in (int, float)
            and math.isfinite(auxiliary)
            and 0 <= auxiliary <= c.PROFILE["setup_cleanup_seconds"],
            "Setup/cleanup envelope differs.",
        )
        operational = True
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        error = type(exc).__name__
    resources = resource_observations(files, science, rows)
    return {
        **science,
        "status": (
            science["status"]
            if operational and resources["resource_observations_complete"]
            else (
                "h500_resource_review_deferred"
                if operational
                else "h500_forensic_partial_preserved"
            )
        ),
        "operational_receipts_closed": operational,
        "operational_error_kind": error,
        "job_id": job["job_id"],
        "source_commit": plan["source_commit"],
        "production_isolation_certified": False,
        **resources,
    }


def collect(claim, sha, *, command=r.r2.command):
    load(claim, sha)
    marker = claim / "collection.json"
    if marker.exists():
        saved = r.r2.read(o.regular(marker))
        r.require(
            saved["archive"] == ARCHIVE
            and r.file_hash(o.regular(claim / ARCHIVE)) == saved["sha256"],
            "Original archive drift; do not overwrite.",
        )
        sidecar = o.regular(Path(str(claim / ARCHIVE) + ".sha256")).read_text().strip()
        r.require(sidecar == saved["sha256"] + "  " + ARCHIVE, "Original checksum sidecar drift.")
        return saved
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
    r.require(query.returncode == 0, "Accounting unavailable; preserve and collect later.")
    rows = r.r2.accounting(query.stdout, job["job_id"])
    wanted = {job["job_id"], job["job_id"] + ".batch"}
    path = claim / "control" / ARM / "entry.json"
    if path.exists():
        entry = r.r2.read(o.regular(path))
        r.require(entry["job_id"] == job["job_id"] and entry["step_id"].isdigit(), "Step identity.")
        wanted.add(job["job_id"] + "." + entry["step_id"])
    by_id = {row["job_id"]: row for row in rows}
    if not wanted <= by_id.keys() or any(row["state"] not in r.r2.TERMINAL for row in rows):
        return {"status": "nonterminal_or_accounting_pending", **r.closed()}
    path = claim / "terminal_accounting.json"
    if not path.exists():
        r.r2.write(path, {"raw": query.stdout, "rows": rows})
    files = snapshot(claim)
    files["accounting.txt"] = r.r2.read(path)["raw"].encode()
    report = portable_review(files)
    files["review.json"] = r.r2.encoded(report)
    files["inventory.json"] = r.r2.encoded({n: r.r2.digest(b) for n, b in files.items()})
    r.require(
        len(files) <= 4096 and sum(map(len, files.values())) <= 1024**3,
        "Transfer envelope exceeded; preserve without truncation.",
    )
    archive = claim / ARCHIVE
    with archive.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as tar:
        for name, content in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size, member.mode = len(content), 0o600
            tar.addfile(member, io.BytesIO(content))
    report.update(
        archive=ARCHIVE,
        sha256=r.file_hash(archive),
        download=str(archive),
        transfer_checksum=str(archive) + ".sha256",
    )
    with Path(str(archive) + ".sha256").open("x") as stream:
        stream.write(report["sha256"] + "  " + ARCHIVE + "\n")
    r.r2.write(marker, report)
    return report


def audit(archive, checksum):
    from scripts.review_scalar_h300_evidence import read_archive

    files, _ = read_archive(archive, checksum)
    return portable_review(files)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "start",
            "batch",
            "worker",
            "review",
            "status",
            "wait",
            "collect",
            "audit",
            "budget",
        ),
    )
    parser.add_argument("--source-sha")
    parser.add_argument("--claim", type=Path)
    parser.add_argument("--mode", choices=(ARM,))  # Exact-step controller's compatible invocation.
    parser.add_argument("--one-reviewed-h500", action="store_true")
    for name in (
        "workbook",
        "population",
        "order",
        "materialization-path",
        "predecessor",
        "archive",
    ):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--sha256")
    args = parser.parse_args(argv)
    if args.action == "budget":
        report = {"resources": c.PROFILE, "quality_criteria": c.QUALITY, **r.closed()}
    elif args.action == "audit":
        report = audit(args.archive, args.sha256)
    else:
        r.require(
            args.claim is not None and args.source_sha is not None, "Claim and source required."
        )
        claim = approved_claim(args.claim)
        if args.action == "start":
            report = start(
                claim,
                args.source_sha,
                args.one_reviewed_h500,
                {
                    k: getattr(args, k)
                    for k in (
                        "workbook",
                        "population",
                        "order",
                        "materialization_path",
                        "predecessor",
                    )
                },
            )
        elif args.action == "batch":
            return batch(claim, args.source_sha)
        elif args.action == "worker":
            worker(claim, args.source_sha)
            return 0
        elif args.action == "review":
            report = review_arm(claim, args.source_sha)
        elif args.action == "status":
            load(claim, args.source_sha)
            job = o.job_receipt(claim, args.source_sha)
            query = r.r2.command(
                [
                    "sacct",
                    "-j",
                    job["job_id"],
                    "--noheader",
                    "--parsable2",
                    "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
                ]
            )
            report = {
                "status": "accounting_observed",
                "raw": query.stdout,
                "query_returncode": query.returncode,
                **job,
                **r.closed(),
            }
        else:
            while True:
                report = collect(claim, args.source_sha)
                if args.action != "wait" or report["status"] != "nonterminal_or_accounting_pending":
                    break
                print(
                    "NONTERMINAL; Ctrl-C safe; resume wait/collect, never reset a claim.",
                    flush=True,
                )
                time.sleep(20)
    print(json.dumps(report, sort_keys=True, allow_nan=False), flush=True)
    print("NO_REPEAT_LARGER_INSTANCE_OR_AUTOMATIC_FOLLOW_ON_ADMITTED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
