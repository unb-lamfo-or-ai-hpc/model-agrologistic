"""One approved cold h300 thread block; exclusive human admission and terminal replay."""

from __future__ import annotations

import argparse
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

from scripts import mvp2_scalar_h300 as h
from scripts import mvp2_scalar_r3a_operational as o

r = h.r
ROOT = h.ROOT
CLAIM = ".mvp2-scalar-h300-30h-v1"
ARCHIVE = "scalar-h300-30h-evidence.tar.gz"
SCHEMA = "scalar-h300-operational-v1"
STATUS = "prepared_for_one_human_block"
PROFILE = {**h.proposal(), "status": "maintainer_approved_20261020", "required_decisions": []}
ARMS = tuple(f"t{n}" for n in h.ORDER)
MAX_BYTES, MAX_FILES = 1024**3, 4096


def materialization(audit):
    p = audit["distance_provenance"]
    counts = p["route_count_by_arc_type"]
    maxima = {"DD": 89700, "OD": 11100, "DC": 11100, "OC": 1369}
    r.require(
        audit["schema_version"] == 1
        and audit["output_workbook_sha256"] == h.WORKBOOK_SHA
        and audit["distance_status"] == "osrm_authoritative"
        and p["provider"] == "osrm"
        and p["profile"] == "driving"
        and p["dataset_id"] == o.DATASET
        and set(counts) == set(maxima)
        and all(type(counts[k]) is int and 0 < counts[k] <= maxima[k] for k in counts)
        and p["route_count"] == sum(counts.values())
        and p["route_count_by_source"] == {"osrm": p["route_count"]}
        and p["fallback_count"] == 0
        and all(
            type(p[k]) is int and p[k] >= 0
            for k in ("osrm_request_count", "osrm_cache_miss_count", "osrm_cache_write_count")
        ),
        "Frozen OSRM h300 materialization differs; preserve, do not regenerate.",
    )
    return audit


def design_review(files):
    return h.review(files, schema=SCHEMA, status=STATUS, resource_profile=PROFILE)


def prepare(claim, sha, workbook, population, order, materialization_path, predecessor):
    r.require(claim.name == CLAIM and not claim.exists(), "Fresh exclusive h300 operational claim.")
    r.require(re.fullmatch(r"[0-9a-f]{40}", sha), "Full reviewed source SHA.")
    r.require(
        r.file_hash(h.input_file(workbook, "h300 workbook")) == h.WORKBOOK_SHA,
        "h300 workbook hash differs.",
    )
    original_audit = h.input_file(materialization_path, "h300 materialization audit").read_bytes()
    materialization(r.strict_json(original_audit))
    parent = h.verify_h215(predecessor)
    selection = r.warehouses.read_policy(population, order, o.POPULATION_SHA, o.ORDER_SHA, 300)
    inventory = r.r2.source_inventory(ROOT)
    r.require(inventory["source_commit"] == sha, "Wrong source head.")
    r.r2.verify_source(inventory, ROOT)
    tools = {k: str(o.regular(Path(shutil.which(k) or "").resolve())) for k in o.TOOLS}
    plan = {
        "schema_version": SCHEMA,
        "status": STATUS,
        "source_commit": sha,
        "source_root": str(ROOT),
        "python": sys.executable,
        "python_sha256": r.file_hash(sys.executable),
        "tools": tools,
        "tool_sha256": {k: r.file_hash(v) for k, v in tools.items()},
        "source_inventory_sha256": r.r2.digest(r.r2.encoded(inventory)),
        "warehouse_selection_sha256": r.r2.digest(r.r2.encoded(selection)),
        "materialization_original_sha256": r.r2.digest(original_audit),
        "predecessor": parent,
        "resources": PROFILE,
        "cases": [r.spec_payload(s) for s in h.specs(workbook)],
        "expected_shape": h.SHAPE,
        "frozen_rates": h.RATES,
        "one_block_human_acknowledgement_required": True,
        **r.closed(),
    }
    plan = r.strict_json(r.r2.encoded(plan))
    files = {
        "plan.json": r.r2.encoded(plan),
        "source.json": r.r2.encoded(inventory),
        "warehouse_selection.json": r.r2.encoded(selection),
    }
    design_review(files)
    r.require(r.file_hash(workbook) == h.WORKBOOK_SHA, "Workbook changed during preparation.")
    claim.mkdir(mode=0o700)
    for name, value in files.items():
        with (claim / name).open("xb") as stream:
            stream.write(value)
    with (claim / "materialization.original.json").open("xb") as stream:
        stream.write(original_audit)
    return plan


def load(claim, sha):
    r.require(
        claim.name == CLAIM and not claim.is_symlink(), "Dedicated unlinked operational claim."
    )
    files = {
        n: o.regular(claim / n).read_bytes()
        for n in ("plan.json", "source.json", "warehouse_selection.json")
    }
    design_review(files)
    p = r.strict_json(files["plan.json"])
    r.require(
        p["source_commit"] == sha and Path(p["source_root"]).resolve() == ROOT,
        "Source commit/root differs.",
    )
    r.r2.verify_source(r.strict_json(files["source.json"]), ROOT)
    r.require(r.file_hash(sys.executable) == p["python_sha256"], "Python drift.")
    original = o.regular(claim / "materialization.original.json").read_bytes()
    r.require(r.r2.digest(original) == p["materialization_original_sha256"], "Audit drift.")
    materialization(r.strict_json(original))
    return p


def invocation(action, claim, sha, *extra):
    return [
        sys.executable,
        "-B",
        "-I",
        "-c",
        "import runpy,sys;sys.dont_write_bytecode=True;sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('scripts.mvp2_scalar_h300_operational',run_name='__main__')",
        str(ROOT),
        action,
        "--claim",
        str(claim),
        "--source-sha",
        sha,
        *extra,
    ]


def start(claim, sha, acknowledged, paths, *, command=r.r2.command):
    r.require(acknowledged, "Human acknowledgement for one reviewed h300 block required.")
    r.require(sys.version_info[:2] == (3, 13) and not os.environ.get("SLURM_JOB_ID"), "Login only.")
    if claim.exists():
        load(claim, sha)
        o.job_receipt(claim, sha)
        return {"status": "existing_claim_collect_only", **r.closed()}
    from scripts.probe_npad_gurobi_license import check_file

    check_file()  # Metadata/path access only; no login solver or secret read.
    plan = prepare(claim, sha, **paths)
    token = r.r2.digest(r.r2.encoded(plan))
    with (claim / "batch.sh").open("x", newline="\n") as f:
        f.write("#!/bin/sh\nexec " + shlex.join(invocation("batch", claim, sha)) + "\n")
    r.r2.write(
        claim / "submission_intent.json",
        {"plan_sha256": token, "one_human_block_acknowledged": True, "automatic_retry": False},
    )
    q = command(
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
            "--time=1-06:00:00",
            "--no-requeue",
            "--export=ALL",
            "--job-name=scalar-h300-30h",
            "--chdir=" + str(claim),
            "--output=" + str(claim / "slurm.out"),
            "--error=" + str(claim / "slurm.err"),
            str(claim / "batch.sh"),
        ]
    )
    r.r2.write(
        claim / "submission.json",
        {"returncode": q.returncode, "stdout": q.stdout, "stderr": q.stderr},
    )
    match = re.fullmatch(r"([1-9][0-9]*)(?:;[A-Za-z0-9_.-]+)?\s*", q.stdout)
    r.require(
        q.returncode == 0 and match, "Submission uncertain; preserve consumed claim, never retry."
    )
    job = {"job_id": match[1], "source_commit": sha, "plan_sha256": token}
    o.publish(claim / "job.json", job)
    return {"status": "submitted_one_h300_30h_block", **job, **r.closed()}


def allocation(text, job, uid):
    raw = o.fields(text).get("TimeLimit", "")
    match = re.fullmatch(r"(?:(\d+)-)?(\d+):([0-5]\d):([0-5]\d)", raw)
    r.require(match is not None, "Allocation time grammar.")
    d, hours, minutes, seconds = [int(v or 0) for v in match.groups()]
    r.require(
        (not d or hours < 24) and d * 86400 + hours * 3600 + minutes * 60 + seconds == 108000,
        "Approved 30h allocation required.",
    )
    return o.allocation(text, job, uid, walltime=raw)


def bind_step(text, entry, allocated, uid):
    # All24 allocated CPUs belong to every serial step; workers explicitly use
    # the SAME16 logical affinity IDs. This avoids a changing16-CPU Slurm subset.
    return o.step_binding(text, entry, allocated, uid, cpus=24)


def hardware(pool):
    r.require(
        len(pool) == len(set(pool)) == 16 and all(type(v) is int and v >= 0 for v in pool),
        "Sixteen distinct logical CPU IDs required.",
    )
    cpuinfo = Path("/proc/cpuinfo").read_text().split("\n\n")[0]
    identity = {}
    for line in cpuinfo.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() in {"vendor_id", "cpu family", "model", "model name", "stepping"}:
            identity[key.strip()] = value.strip()
    r.require("model name" in identity, "CPU model unavailable.")
    topology = []
    for cpu in pool:
        base = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        topology.append(
            {
                "logical_cpu": cpu,
                "socket": int((base / "physical_package_id").read_text()),
                "core": int((base / "core_id").read_text()),
            }
        )
    return {
        "host": platform.node(),
        "cpu_model": identity,
        "topology": topology,
        "affinity_logical_cpus": pool,
        "physical_cores_observed": len({(v["socket"], v["core"]) for v in topology}),
    }


def input_reviewer(data, receipt):
    probabilities = receipt["effective_scenario_probabilities"]
    r.require(
        len(probabilities) == 9 and all(v == 1 / 9 for v in probabilities.values()),
        "Nine equiprobable scenarios required.",
    )
    receipt["frozen_penalty_review"] = h.penalty_receipt(
        receipt["mathematical_contract"],
        warehouse_ids=data.warehouses,
        demand_pairs={(c, p) for c in data.domestic_customers for p in data.products},
    )


def worker(claim, sha, arm):
    plan = load(claim, sha)
    job = o.job_receipt(claim, sha)
    step = os.environ.get("SLURM_STEP_ID", "")
    r.require(
        os.environ.get("SLURM_JOB_ID") == job["job_id"] and step.isdigit() and arm in ARMS,
        "Worker owned job/numeric step/arm required.",
    )
    control = claim / "control" / arm
    entry = {
        **job,
        "step_id": step,
        "mode": arm,
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
    r.require(set(pool) <= set(os.sched_getaffinity(0)), "Common CPU pool unavailable in step.")
    os.sched_setaffinity(0, pool)
    r.require(
        sorted(os.sched_getaffinity(0)) == pool and hardware(pool) == baseline,
        "Common affinity/hardware drift before solve.",
    )
    from scripts.probe_npad_gurobi_license import probe

    capability = probe()
    r.r2.write(control / "license_capability.json", capability)
    r.require(capability["status"] == "accepted", "Fresh designated WLS capability rejected.")
    selected = h.specs(plan["cases"][0]["workbook"])[ARMS.index(arm)]
    r.require(
        r.strict_json(r.r2.encoded(r.spec_payload(selected))) == plan["cases"][ARMS.index(arm)],
        "Frozen arm/input settings drift.",
    )
    r.r2.write(
        control / "runtime.json",
        {
            **baseline,
            "python": platform.python_version(),
            "python_sha256": r.file_hash(sys.executable),
            "gurobi_version": capability["gurobi_version"],
            "solver_threads": selected.solver.threads,
            "slurm_step_allocated_cpus": 24,
            "worker_affinity_logical_cpus": 16,
        },
    )
    o.run_case(
        selected,
        claim / "cases" / selected.name,
        h.SHAPE,
        r.r2.read(claim / "warehouse_selection.json"),
        control,
        entry,
        input_reviewer=input_reviewer,
    )
    load(claim, sha)


def science_review(files, plan):
    adapted = {**plan, "selection_sha256": plan["warehouse_selection_sha256"]}
    report = o.scalar_review(files, adapted, expected_count=5, include_case_names=True)
    accepted, rejected = [], list(report["missing_or_rejected"])
    for arm in report["arms"]:
        try:
            prefix = "cases/" + arm["case_name"]
            receipt = r.strict_json(files[prefix + "/input_receipt.json"])
            vector = h.penalty_receipt(
                receipt["mathematical_contract"],
                warehouse_ids=[
                    v["warehouse_id"] for v in receipt["warehouse_selection"]["included"]
                ],
            )
            r.require(
                receipt["frozen_penalty_review"] == vector,
                "Effective penalty gate receipt differs.",
            )
            summary = r.strict_json(
                files[prefix + "/products/" + arm["case_name"] + "/run_summary.json"]
            )
            arm["physical_diagnostics"] = {
                key: summary.get(key)
                for key in (
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
            accepted.append(arm)
        except (ValueError, KeyError, TypeError) as exc:
            rejected.append({"name": arm["case_name"], "error_kind": type(exc).__name__})
    feasible = (
        len(accepted) == 5
        and not rejected
        and all(a["classification"] == "validated_feasible" for a in accepted)
    )
    quality = feasible and all(a["scalar_gap_target_met"] for a in accepted)
    return {
        "status": "block_quality_target_met"
        if quality
        else ("block_feasible_quality_censored" if feasible else "partial_or_rejected_preserved"),
        "arms": accepted,
        "missing_or_rejected": rejected,
        "quality_target_met": quality,
        "penalty_rates": h.RATES,
        "scientific_configuration_selected": False,
        "interpretation": (
            "Original certificate replay; single serial observations, no causal thread ranking."
        ),
        **r.closed(),
    }


def snapshot(claim):
    return o.snapshot(claim, archive_name=ARCHIVE)


def review_arm(claim, sha, arm):
    plan = load(claim, sha)
    review = science_review(snapshot(claim), plan)
    chosen = next(
        (a for a in review["arms"] if a["case_name"] == plan["cases"][ARMS.index(arm)]["name"]),
        None,
    )
    r.require(
        chosen and chosen["classification"] == "validated_feasible", "Validated incumbent required."
    )
    r.r2.write(claim / "control" / arm / "review.json", chosen)
    return chosen


def review_process(claim, sha, arm, remaining):
    control = claim / "control" / arm
    with (control / "review.out").open("xb") as out, (control / "review.err").open("xb") as err:
        result = subprocess.run(
            invocation("review", claim, sha, "--mode", arm),
            stdout=out,
            stderr=err,
            timeout=remaining,
            check=False,
        )
    r.require(result.returncode == 0, "Independent product review failed; preserve logs.")


def supervise(claim, sha, arm, allocated, job):
    return o.supervise(
        claim,
        sha,
        arm,
        allocated,
        job,
        invoke=invocation,
        step_cpus=24,
        bind_step=bind_step,
        reviewer=review_process,
        whole_arm_seconds=18900,
    )


def batch(claim, sha):
    outcome = {
        "status": "blocked_or_partial",
        "completed_arms": [],
        "unrun": list(ARMS),
        **r.closed(),
    }
    phase = "source_and_job_binding"
    try:
        plan = load(claim, sha)
        o.verify_tools(plan)
        until = time.monotonic() + 30
        while not (claim / "job.json").exists() and time.monotonic() < until:
            time.sleep(0.1)
        job = o.job_receipt(claim, sha)
        r.require(job["job_id"] == os.environ.get("SLURM_JOB_ID"), "Batch job differs.")
        r.r2.write(claim / "batch_entry.json", job)
        phase = "allocation_and_common_hardware"
        q = r.r2.command(["scontrol", "-o", "show", "job", job["job_id"]])
        r.r2.write(
            claim / "allocation_query.json",
            {"returncode": q.returncode, "stdout": q.stdout, "stderr": q.stderr},
        )
        r.require(q.returncode == 0, "Allocation query failed.")
        allocated = allocation(q.stdout, job["job_id"], os.getuid())
        r.r2.write(claim / "allocation.json", allocated)
        pool = sorted(os.sched_getaffinity(0))[:16]
        r.r2.write(claim / "hardware.json", hardware(pool))
        for arm in ARMS:
            phase = "serial_" + arm
            outcome["unrun"].remove(arm)
            result = supervise(claim, sha, arm, allocated, job)
            r.require(result["next_arm_allowed"], "Stop block; preserve partial/unrun arms.")
            outcome["completed_arms"].append(arm)
        load(claim, sha)
        outcome.update(status="block_returned", source_verified_after=True)
    except Exception as exc:
        outcome.update(error_kind=type(exc).__name__, failure_phase=phase)
    r.r2.write(claim / "batch_outcome.json", outcome)
    return int(outcome["status"] != "block_returned")


def portable_review(files):
    design_review(files)
    plan, job = (r.strict_json(files[n]) for n in ("plan.json", "job.json"))
    r.require(
        job["source_commit"] == plan["source_commit"]
        and re.fullmatch(r"[1-9][0-9]*", job["job_id"])
        and job["plan_sha256"] == r.r2.digest(files["plan.json"]),
        "Job/plan binding differs.",
    )
    original = files["materialization.original.json"]
    r.require(
        r.r2.digest(original) == plan["materialization_original_sha256"],
        "Original materialization hash.",
    )
    materialization(r.strict_json(original))
    rows = r.r2.accounting(files["accounting.txt"].decode(), job["job_id"])
    r.require(r.r2.terminal(rows, job["job_id"]), "Terminal accounting required.")
    science = science_review(files, plan)
    operational, reason = False, None
    try:
        q = r.strict_json(files["allocation_query.json"])
        owner = re.fullmatch(r"[^()]+\(([0-9]+)\)", o.fields(q["stdout"])["UserId"])
        r.require(q["returncode"] == 0 and owner, "Owner query absent.")
        allocated = allocation(q["stdout"], job["job_id"], int(owner[1]))
        r.require(
            allocated == r.strict_json(files["allocation.json"])
            and r.strict_json(files["batch_entry.json"]) == job,
            "Allocation/batch replay differs.",
        )
        baseline = r.strict_json(files["hardware.json"])
        pool = baseline["affinity_logical_cpus"]
        r.require(
            len(pool) == len(set(pool)) == 16 and all(type(v) is int and v >= 0 for v in pool),
            "Common CPU pool differs.",
        )
        wanted = {job["job_id"], job["job_id"] + ".batch"}
        runtimes = []
        scientific_by_case = {a["case_name"]: a for a in science["arms"]}
        for arm in ARMS:
            base = "control/" + arm + "/"
            entry = r.strict_json(files[base + "entry.json"])
            r.require(
                all(entry[k] == v for k, v in job.items())
                and entry["mode"] == arm
                and r.strict_json(files[base + "release.json"]) == entry,
                "Entry/release differs.",
            )
            q = r.strict_json(files[base + "step_query.json"])
            r.require(q["returncode"] == 0, "Step query failed.")
            exact = bind_step(q["stdout"], entry, allocated, int(owner[1]))
            wanted.add(exact)
            control = r.strict_json(files[base + "controller.json"])
            ev = [r.strict_json(files[n]) for n in sorted(files) if n.startswith(base + "phase-")]
            r.require(
                ev and all(v["entry"] == entry for v in ev) and ev[-1]["phase"] == "complete",
                "Phase stream differs.",
            )
            usage = o.phase_usage(ev, ev[-1]["elapsed_seconds"])
            r.require(
                control["status"] == "closed_feasible_arm"
                and control["local_client_reaped"]
                and control["step_id"] == entry["step_id"]
                and usage == control["usage"]
                and usage["stop_reason"] is None,
                "Controller/phase closure differs.",
            )
            chosen = scientific_by_case[plan["cases"][ARMS.index(arm)]["name"]]
            r.require(
                r.strict_json(files[base + "review.json"]) == chosen
                and chosen["classification"] == "validated_feasible",
                "Post-worker scientific review missing/different.",
            )
            terminal = r.strict_json(files[base + "native_terminal.json"])
            r.require(
                terminal["entry"] == entry
                and terminal["solution_count"] > 0
                and terminal["time_limit_seconds"] == 14400
                and type(terminal["runtime_seconds"]) in (float, int)
                and math.isfinite(terminal["runtime_seconds"])
                and 0 <= terminal["runtime_seconds"] <= 15300,
                "Original native terminal/budget evidence differs.",
            )
            seconds = control["product_review_seconds"]
            r.require(
                type(seconds) in (float, int)
                and math.isfinite(seconds)
                and seconds >= 0
                and seconds + usage["seconds"]["independent_validation"] <= 1800,
                "Combined validation budget differs.",
            )
            capability, runtime = (
                r.strict_json(files[base + n]) for n in ("license_capability.json", "runtime.json")
            )
            from scripts.probe_npad_gurobi_license import LICENSE_FILE

            r.require(
                capability["status"] == "accepted"
                and capability["license_file"] == LICENSE_FILE
                and capability["probe_variable_count"] == 2001
                and capability["probe_constraint_count"] == 2001
                and abs(capability["objective_value"] - 2001) <= 1e-6
                and capability["gurobi_version"][0] == 13,
                "Fresh designated WLS capability differs.",
            )
            r.require(
                all(runtime[k] == v for k, v in baseline.items())
                and runtime["python"].startswith("3.13.")
                and runtime["python_sha256"] == plan["python_sha256"]
                and runtime["gurobi_version"] == capability["gurobi_version"]
                and runtime["solver_threads"] == h.ORDER[ARMS.index(arm)]
                and runtime["slurm_step_allocated_cpus"] == 24
                and runtime["worker_affinity_logical_cpus"] == 16,
                "Runtime/common hardware differs.",
            )
            runtimes.append((runtime["python"], runtime["gurobi_version"]))
        numeric = {
            x["job_id"] for x in rows if "." in x["job_id"] and x["job_id"].split(".")[-1].isdigit()
        }
        r.require(
            len(wanted) == 7
            and wanted <= {x["job_id"] for x in rows}
            and numeric == wanted - {job["job_id"], job["job_id"] + ".batch"}
            and all(v == runtimes[0] for v in runtimes)
            and all(
                x["state"] == "COMPLETED"
                and x["exit_code"] == "0:0"
                and x["elapsed_seconds"] <= (18900 if x["job_id"] in numeric else 108000)
                for x in rows
            ),
            "Unexpected/missing/failed/over-budget accounting step.",
        )
        outcome = r.strict_json(files["batch_outcome.json"])
        r.require(
            outcome["status"] == "block_returned"
            and outcome["completed_arms"] == list(ARMS)
            and not outcome["unrun"]
            and outcome["source_verified_after"],
            "Unclosed serial block.",
        )
        operational = True
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        reason = type(exc).__name__
    return {
        **science,
        "status": science["status"] if operational else "forensic_partial_block_preserved",
        "operational_receipts_closed": operational,
        "operational_error_kind": reason,
        "job_id": job["job_id"],
        "source_commit": plan["source_commit"],
        "production_isolation_certified": False,
    }


def collect(claim, sha, *, command=r.r2.command):
    load(claim, sha)
    marker = claim / "collection.json"
    if marker.exists():
        saved = r.r2.read(o.regular(marker))
        r.require(
            saved["archive"] == ARCHIVE
            and r.file_hash(o.regular(claim / ARCHIVE)) == saved["sha256"],
            "Preserved archive changed; never overwrite.",
        )
        return saved
    job = o.job_receipt(claim, sha)
    q = command(
        [
            "sacct",
            "-j",
            job["job_id"],
            "--noheader",
            "--parsable2",
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
        ]
    )
    r.require(q.returncode == 0, "Accounting unavailable; preserve and collect later.")
    rows = r.r2.accounting(q.stdout, job["job_id"])
    wanted = {job["job_id"], job["job_id"] + ".batch"}
    for arm in ARMS:
        entry = claim / "control" / arm / "entry.json"
        if entry.exists():
            e = r.r2.read(o.regular(entry))
            r.require(
                e["job_id"] == job["job_id"] and e["step_id"].isdigit(),
                "Launched step identity differs.",
            )
            wanted.add(job["job_id"] + "." + e["step_id"])
    by_id = {x["job_id"]: x for x in rows}
    if (
        not wanted <= by_id.keys()
        or any(by_id[k]["state"] not in r.r2.TERMINAL for k in wanted)
        or any(row["state"] not in r.r2.TERMINAL for row in rows)
    ):
        return {"status": "nonterminal_or_accounting_pending", **r.closed()}
    saved_accounting = claim / "terminal_accounting.json"
    if not saved_accounting.exists():
        r.r2.write(saved_accounting, {"raw": q.stdout, "rows": rows})
    files = snapshot(claim)
    files["accounting.txt"] = r.r2.read(saved_accounting)["raw"].encode()
    report = portable_review(files)
    files["review.json"] = r.r2.encoded(report)
    files["inventory.json"] = r.r2.encoded({n: r.r2.digest(b) for n, b in files.items()})
    r.require(
        len(files) <= MAX_FILES and sum(map(len, files.values())) <= MAX_BYTES,
        "Expanded transfer cap exceeded; preserve without truncation.",
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
    r.require(
        re.fullmatch(r"[0-9a-f]{64}", checksum) and r.file_hash(o.regular(archive)) == checksum,
        "External checksum differs.",
    )
    files, size = {}, 0
    with tarfile.open(archive, "r:gz") as tar:
        for m in tar:
            r.require(
                m.isfile() and r._safe_name(m.name) and m.name not in files,
                "Unsafe/duplicate archive member.",
            )
            size += m.size
            r.require(size <= MAX_BYTES and len(files) < MAX_FILES, "Archive cap exceeded.")
            files[m.name] = tar.extractfile(m).read()
    inventory = r.strict_json(files.pop("inventory.json"))
    r.require(
        inventory == {n: r.r2.digest(b) for n, b in files.items()}, "Archive inventory differs."
    )
    return portable_review(files)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
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
    p.add_argument("--claim", type=Path)
    p.add_argument("--source-sha")
    p.add_argument("--mode", choices=ARMS)
    p.add_argument("--one-reviewed-h300-block", action="store_true")
    for n in ("workbook", "population", "order", "materialization-path", "predecessor", "archive"):
        p.add_argument("--" + n, type=Path)
    p.add_argument("--sha256")
    args = p.parse_args(argv)
    if args.action == "budget":
        result = PROFILE
    elif args.action == "audit":
        result = audit(args.archive, args.sha256)
    else:
        r.require(args.claim is not None and args.source_sha is not None, "Claim/source required.")
        claim = args.claim.absolute()
        if args.action == "start":
            result = start(
                claim,
                args.source_sha,
                args.one_reviewed_h300_block,
                {
                    n: getattr(args, n)
                    for n in (
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
            worker(claim, args.source_sha, args.mode)
            return 0
        elif args.action == "review":
            result = review_arm(claim, args.source_sha, args.mode)
        elif args.action == "status":
            load(claim, args.source_sha)
            job = o.job_receipt(claim, args.source_sha)
            q = r.r2.command(
                [
                    "sacct",
                    "-j",
                    job["job_id"],
                    "--noheader",
                    "--parsable2",
                    "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
                ]
            )
            result = {
                "status": "accounting_observed",
                "raw": q.stdout,
                "query_returncode": q.returncode,
                **job,
                **r.closed(),
            }
        else:
            while True:
                result = collect(claim, args.source_sha)
                if args.action != "wait" or result["status"] != "nonterminal_or_accounting_pending":
                    break
                print(
                    "NONTERMINAL; Ctrl-C safe; repeat wait/collect, never reset a claim.",
                    flush=True,
                )
                time.sleep(20)
    print(json.dumps(result, sort_keys=True, allow_nan=False), flush=True)
    print("NO_REPEAT_LARGER_INSTANCE_OR_AUTOMATIC_FOLLOW_ON_ADMITTED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
