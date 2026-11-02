"""Finite human-submitted Slurm graph around the immutable c493be8c engine.

No compute action submits jobs. Original workers, inputs and consumed claims
stay intact. A new queue is submitted in hold and requires a separate release.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import time
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
ENGINE_ROOT = BASE / ".mvp2-pyomo-scaling-public-v1/source"
CAMPAIGN = BASE / ".mvp2-pyomo-scaling-native8h-v1"
QUEUE = BASE / ".mvp2-pyomo-scaling-serial-v1"
PUBLIC = BASE / ".mvp2-pyomo-scaling-serial-public-v3"
ENGINE_SHA = "c493be8cd127c5175fc7eb111400229e64b8e3c0"
ENGINE_DRIVER_SHA = "27d90f396d50a6778ca7ccb0bf2f11878186ef58e343128aabedcb1057b4ec2d"
CAMPAIGN_SHA = "3cae7c318032108caa936d70b2883f20d055066f89a78e24610f261832763b58"
SCHEDULE = "experiments/pyomo_scaling_serial_schedule_v1.json"
FILES = (
    "scripts/pyomo_serial_queue.py",
    "scripts/pyomo_serial_collection.py",
    "scripts/qualify_pyomo_serial.py",
    "scripts/pyomo_serial_smoke.py",
    "scripts/pyomo_serial_storage.py",
    "tests/test_pyomo_serial_queue.py",
    "tests/test_pyomo_serial_collection.py",
    "tests/test_pyomo_serial_smoke.py",
    "tests/test_pyomo_serial_storage.py",
    SCHEDULE,
)
ATTACHED = {
    "h300-w-sto-highs-t16-r1": (
        "2231591",
        "925a1de072ce8fd86e4cdfaa675cfe5250d5fd72c1ab4866e8704bac019dc1dc",
    ),
    "h300-w-sto-gurobi-t16-r1": (
        "2231593",
        "4be92d10eb6a5e944e0c290f1f50ba8aa3be6eabd681cc2f38386f2d1c397e2d",
    ),
}
ANCHORS = {
    "h300-w-sto-highs-t1-r1": (
        "2231226",
        "412f4d4d3b7faa7cb913a4da3a537a6804926840fb859bfc22bfd72e11fe702b",
    ),
    "h300-w-sto-gurobi-t1-r1": (
        "2231228",
        "a07f2629dbdd663dbc0a5549d4cdc5f026c866507a884c1c8cb53c9e277985f1",
    ),
}
TERMINAL = {
    "COMPLETED",
    "CANCELLED",
    "FAILED",
    "TIMEOUT",
    "PREEMPTED",
    "OUT_OF_MEMORY",
    "NODE_FAIL",
    "BOOT_FAIL",
    "DEADLINE",
    "REVOKED",
}


def require(value, message):
    if not value:
        raise ValueError(message)


def regular(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "Regular unlinked file required.")
    return path


def digest(path):
    with regular(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def write(path, value):
    with Path(path).open("xb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())


def read(path):
    path = regular(path)
    require(path.stat().st_size <= 4 * 1024**2, "Bounded queue JSON required.")
    return json.loads(path.read_bytes())


def run(argv, *, timeout=60):
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)


def login():
    require(
        platform.system() == "Linux"
        and sys.version_info[:2] == (3, 13)
        and not os.environ.get("SLURM_JOB_ID"),
        "Existing Linux3.13 login only.",
    )


def location(path=QUEUE):
    path = Path(path)
    require(
        path.name == QUEUE.name and path.parent.resolve() == BASE and not path.is_symlink(),
        "Dedicated serial queue under audit base required.",
    )
    return path


def slug(identity):
    require(re.fullmatch(r"(?:solve|control):[a-z0-9-]+", identity), "Unknown node identity.")
    return identity.replace(":", "__")


def load_engine():
    path = ENGINE_ROOT / "scripts/pyomo_scaling_campaign.py"
    require(digest(path) == ENGINE_DRIVER_SHA, "Qualified engine driver differs.")
    spec = importlib.util.spec_from_file_location("agrologistic_qualified_scaling_engine", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def source_files(root=ROOT):
    return {name: digest(root / name) for name in FILES}


def storage_module():
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import pyomo_serial_storage

    return pyomo_serial_storage


def check_storage(manifest):
    storage_module().check_growth(BASE, CAMPAIGN, manifest, command=run)


def verify_sources(root, expected):
    require(set(expected) == set(FILES), "Exact controller source allowlist required.")
    require(source_files(root) == expected, "Controller source drift.")


def schedule(path=None):
    plan = read(path or ROOT / SCHEDULE)
    require(
        plan["qualified_engine_commit"] == ENGINE_SHA and plan["campaign_sha256"] == CAMPAIGN_SHA,
        "Frozen engine/campaign differs.",
    )
    nodes = plan["jobs"]
    seen, ancestors = set(), {}
    for node in nodes:
        slug(node["id"])
        require(node["id"] not in seen and set(node["parents"]) <= seen, "Invalid DAG.")
        ancestors[node["id"]] = set(node["parents"])
        for parent in node["parents"]:
            ancestors[node["id"]].update(ancestors[parent])
        seen.add(node["id"])
    require(len(nodes) == 95, "Exact finite95-node graph required.")
    solves = [n for n in nodes if n["kind"] == "scientific_solve"]
    require(
        len(solves) == 88 and len({n["cell"] for n in solves}) == 88,
        "Exact88 unique remaining scientific cells required.",
    )
    require(not set(ANCHORS) & {n["cell"] for n in solves}, "Consumed one-thread cell repeated.")
    for node in solves:
        match = re.fullmatch(
            r"h(300|400|500)-w-sto-(gurobi|highs)-t(1|2|4|8|16)-r([123])", node["cell"]
        )
        require(
            match
            and node["id"] == "solve:" + node["cell"]
            and node["solver"] == match[2]
            and node["threads"] == int(match[3]),
            "Scientific identity differs.",
        )
        require(
            node["seed"] == 42
            and node["native_seconds"] == 28800
            and node["mip_gap_target"] == 0.01
            and node["memory_mib"] == 196608
            and node["requested_cpus"] == 24
            and node["worker_logical_cpus"] == 16
            and node["exclusive"] is True
            and node["wall_seconds"] == 43200,
            "Scientific resource/stopping contract differs.",
        )
    for solver in ("gurobi", "highs"):
        lane = [n for n in solves if n["solver"] == solver]
        require(len(lane) == 44, "Two44-cell lanes required.")
        require(
            all(a["id"] in ancestors[b["id"]] for a, b in pairwise(lane)),
            "Per-solver order does not bound concurrency.",
        )
    return plan


def accounting(job, *, command=run):
    require(re.fullmatch(r"[1-9][0-9]*", job), "Numeric owned job required.")
    result = command(
        [
            "sacct",
            "-j",
            job,
            "--noheader",
            "--parsable2",
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
        ]
    )
    require(result.returncode == 0, "Accounting unavailable.")
    rows = []
    for line in result.stdout.splitlines():
        fields = line.split("|")
        if fields and fields[0] == job:
            require(len(fields) >= 5, "Incomplete root accounting.")
            state = fields[1].split()[0].rstrip("+")
            rows.append({"job_id": job, "state": state, "exit_code": fields[2]})
    require(len(rows) == 1, "Unique root accounting required.")
    return rows[0]


def current_jobs(*, command=run):
    result = command(["squeue", "--array", "--noheader", "--user", str(os.getuid()), "--format=%i"])
    require(result.returncode == 0, "User queue unavailable.")
    rows = result.stdout.split()
    require(
        all(re.fullmatch(r"[1-9][0-9]*(?:_[0-9]+)?", r) for r in rows),
        "Expanded array/job accounting required.",
    )
    return rows


def verify_qualification(engine, sha):
    script_dir = str(ROOT / "scripts")
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from qualify_pyomo_serial import NEW_EXPECTED_TESTS, NEW_TESTS

    plan, result = read(PUBLIC / "plan.json"), read(PUBLIC / "result.json")
    require(
        NEW_EXPECTED_TESTS > 0
        and plan["new_expected_tests"] == NEW_EXPECTED_TESTS
        and plan["new_tests"] == list(NEW_TESTS)
        and plan["expected_tests"] == 111 + NEW_EXPECTED_TESTS
        and result["status"] == "accepted"
        and result["pytest_exit"] == 0
        and result["source_verified_after"] is True
        and result["original_receipts_verified_after"] is True
        and result["engine_sources_verified_after"] is True
        and result["license_capacity_accepted"] is True
        and result["exclusive_allocation_verified"] is True
        and result["dependency_smoke_accepted"] is True
        and result["affinity_logical_cpus"] == 16
        and result["runtime_verified_after"] is True
        and result["counts"]["failures"] == 0
        and result["counts"]["errors"] == 0
        and result["counts"]["skipped"] == 0
        and result["counts"]["tests"] == plan["expected_tests"]
        and result["source_commit"] == plan["source_commit"] == sha
        and result["plan_sha256"] == hashlib.sha256(encoded(plan)).hexdigest()
        and result["private_execution_admitted"] is False,
        "Exact new public controller qualification required.",
    )
    require(ROOT == PUBLIC / "source", "Use the qualified controller source.")
    verify_sources(ROOT, plan["controller_files"])
    require(engine.environment() == plan["runtime"], "Qualified runtime drift.")
    return plan, result


def root_context(queue, sha, *, expensive=True):
    location(queue)
    manifest = read(queue / "queue.json")
    require(
        manifest["controller_commit"] == sha
        and manifest["controller_root"] == str(ROOT)
        and manifest["engine_commit"] == ENGINE_SHA
        and manifest["campaign_sha256"] == CAMPAIGN_SHA,
        "Queue/source binding differs.",
    )
    verify_sources(ROOT, manifest["controller_files"])
    require(
        digest(PUBLIC / "plan.json") == manifest["public_plan_sha256"]
        and digest(PUBLIC / "result.json") == manifest["public_result_sha256"],
        "Original controller qualification receipts changed.",
    )
    require(manifest["schedule"] == schedule(), "Queue graph changed.")
    engine = load_engine()
    campaign = engine.load_campaign(CAMPAIGN, ENGINE_SHA, expensive=expensive)
    if expensive:
        engine.verify_tools(campaign)
    require(engine.c.digest(campaign) == CAMPAIGN_SHA, "Original campaign drift.")
    return manifest, engine, campaign


def node_at(manifest, identity):
    matches = [node for node in manifest["schedule"]["jobs"] if node["id"] == identity]
    require(len(matches) == 1, "Unknown finite graph node.")
    return matches[0]


def node_directory(queue, node):
    parent = queue / "jobs"
    directory = parent / slug(node["id"])
    require(not parent.is_symlink() and not directory.is_symlink(), "Linked job directory.")
    return directory


def make_run_plan(engine, campaign, item, selection, index, controller_sha=None):
    claim = CAMPAIGN / item["id"]
    inputs = campaign["inputs"][str(item["population"])]
    return {
        "schema_version": engine.c.SCHEMA + "-run",
        "cell": item,
        "source_commit": ENGINE_SHA,
        "source_root": str(engine.ROOT),
        "claim_path": str(claim),
        "profile": engine.c.PROFILE,
        "campaign_sha256": CAMPAIGN_SHA,
        "selection_sha256": engine.c.digest(selection),
        "cases": [engine.r.spec_payload(engine.c.specification(item, inputs["workbook"]))],
        "created_at_utc": datetime.now(UTC).isoformat(),
        "planned_schedule_index": next(
            i for i, x in enumerate(engine.c.cells()) if x["id"] == item["id"]
        ),
        "actual_submission_index": None,
        "serial_schedule_index": index,
        "submission_mode": "bounded_pre_submitted_serial_graph_v1",
        "serial_controller_commit": controller_sha,
    }


def script_text(queue, node, sha):
    action = "batch" if node["kind"] == "scientific_solve" else "control"
    if node["kind"] == "final_consolidation":
        action = "final"
    argv = [
        sys.executable,
        "-B",
        "-I",
        str(ROOT / "scripts/pyomo_serial_queue.py"),
        action,
        "--queue",
        str(queue),
        "--controller-sha",
        sha,
        "--node",
        node["id"],
    ]
    return (
        "#!/bin/bash\nset -euo pipefail\n"
        "export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic\n"
        "export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1\n"
        "export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1\n"
        "exec " + shlex.join(argv) + "\n"
    )


def prepare(queue, sha, *, storage_budget_gib=None):
    login()
    location(queue)
    require(not queue.exists(), "Existing serial claim preserved; never prepare again.")
    require(
        type(storage_budget_gib) is int and storage_budget_gib >= 32,
        "Confirm at least32GiB usable output/archive budget from quota/site information.",
    )
    storage = storage_module()
    initial_storage = storage.check_initial(BASE, storage_budget_gib, command=run)
    engine = load_engine()
    qualification, result = verify_qualification(engine, sha)
    closed_public = accounting(result["job_id"])
    require(
        closed_public["state"] == "COMPLETED" and closed_public["exit_code"] == "0:0",
        "Public controller job not terminal.",
    )
    campaign = engine.load_campaign(CAMPAIGN, ENGINE_SHA)
    require(engine.c.digest(campaign) == CAMPAIGN_SHA, "Original campaign differs.")
    graph = schedule()
    for identity, (job, checksum) in ANCHORS.items():
        saved = engine.read(CAMPAIGN / identity / "collection.json")
        row = engine.archive_report(CAMPAIGN / identity, saved)
        require(
            saved["sha256"] == checksum
            and row["job_id"] == job
            and row["operational_receipts_closed"] is True,
            "Original anchor drift.",
        )
    attached = {}
    for identity, (job, plan_sha) in ATTACHED.items():
        plan, _ = engine.load_run(CAMPAIGN / identity, ENGINE_SHA)
        receipt = engine.o.job_receipt(CAMPAIGN / identity, ENGINE_SHA)
        require(
            receipt["job_id"] == job
            and receipt["plan_sha256"] == plan_sha
            and engine.c.digest(plan) == plan_sha,
            "Existing16-thread pilot differs.",
        )
        attached["solve:" + identity] = {**receipt, "attached_existing": True}
    for node in graph["jobs"]:
        if node["kind"] == "scientific_solve" and node["cell"] not in ATTACHED:
            claim = CAMPAIGN / node["cell"]
            require(
                not claim.exists() and not claim.is_symlink(),
                "Unexpected claimed cell; reconcile without resubmission.",
            )
    require(len(current_jobs()) + 93 <= 95, "Insufficient submission slots with reserve.")
    engine.verify_tools(campaign)
    for node in (
        graph["jobs"][0],
        next(n for n in graph["jobs"] if n["kind"] == "pilot_collection_and_gate"),
        graph["jobs"][-1],
    ):
        probe = run(
            [
                "sbatch",
                "--test-only",
                "--hold",
                "--kill-on-invalid-dep=yes",
                *scheduler_args(node, engine),
                "--wrap=/usr/bin/true",
            ]
        )
        require(probe.returncode == 0, "Exact scheduler profile rejected; no new queue created.")
    selected = {}
    for population in engine.c.POPULATIONS:
        inputs = campaign["inputs"][str(population)]
        engine.check_inputs(population, inputs)
        selected[population] = engine.selection(population, inputs)
    queue.mkdir(mode=0o700)
    (queue / "jobs").mkdir()
    manifest = {
        "schema_version": "paired-pyomo-serial-queue-v1",
        "controller_commit": sha,
        "controller_root": str(ROOT),
        "controller_files": qualification["controller_files"],
        "engine_commit": ENGINE_SHA,
        "campaign_sha256": CAMPAIGN_SHA,
        "schedule": graph,
        "attached": attached,
        "public_plan_sha256": digest(PUBLIC / "plan.json"),
        "public_result_sha256": digest(PUBLIC / "result.json"),
        "created_at_utc": datetime.now(UTC).isoformat(),
        "unbounded_or_compute_submission_allowed": False,
        "storage_budget_gib_confirmed_in_human_CLI": storage_budget_gib,
        "storage_at_prepare": initial_storage,
        "campaign_allocated_bytes_at_prepare": storage.directory_usage(CAMPAIGN),
        "storage_projection_basis": (
            "Measured h300 claims about114MiB;32GiB planning minimum,16GiB live reserve;"
            " quota and aggregate growth checked before further construction/collection;"
            " not a guarantee that all90cells fit or a bound on native scratch"
        ),
    }
    write(queue / "queue.json", manifest)
    for index, node in enumerate(graph["jobs"]):
        directory = node_directory(queue, node)
        directory.mkdir()
        write(directory / "node.json", node)
        if node["id"] in attached:
            write(directory / "job.json", {**attached[node["id"]], "attached_existing": True})
            continue
        if node["kind"] == "scientific_solve":
            item = engine.c.select(node["cell"])
            claim = CAMPAIGN / item["id"]
            selection = selected[item["population"]]
            plan = make_run_plan(engine, campaign, item, selection, index, sha)
            claim.mkdir(mode=0o700)
            engine.write_json(claim / "plan.json", plan)
            engine.write_json(claim / "campaign.json", campaign)
            engine.write_json(claim / "warehouse_selection.json", selection)
        (directory / "batch.sh").write_text(
            script_text(queue, node, sha), encoding="utf-8", newline="\n"
        )
    write(
        queue / "prepared.json",
        {
            "queue_sha256": digest(queue / "queue.json"),
            "new_jobs": 93,
            "attached_jobs": 2,
            "submitted": False,
        },
    )
    return {
        "status": "prepared_no_new_job",
        "queue": str(queue),
        "new_jobs": 93,
        "attached_jobs": {k: v["job_id"] for k, v in attached.items()},
    }


def scheduler_args(node, engine):
    if node["kind"] == "scientific_solve":
        return engine.scheduler_arguments()
    minutes = node["wall_seconds"] // 60
    return [
        "--account=sxdsouza",
        "--partition=intel-256",
        "--qos=preempt",
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=" + str(node["requested_cpus"]),
        "--mem=" + str(node["memory_mib"]) + "M",
        f"--time={minutes // 60:02}:{minutes % 60:02}:00",
        "--no-requeue",
    ]


def dependencies(node, receipts, attached, *, command=run):
    jobs = []
    for parent in node["parents"]:
        job = receipts[parent]["job_id"]
        if parent in attached and accounting(job, command=command)["state"] in TERMINAL:
            continue  # Terminal original receipt, not a stale MinJobAge dependency.
        jobs.append(job)
    return node["dependency_condition"] + ":" + ":".join(jobs) if jobs else None


def submit(queue, sha, *, command=run):
    login()
    manifest, engine, _ = root_context(queue, sha)
    prepared = read(queue / "prepared.json")
    require(prepared["queue_sha256"] == digest(queue / "queue.json"), "Prepared queue drift.")
    require(
        not (queue / "submission_intent.json").exists(),
        "Existing submission intent: preserve and never repeat submit.",
    )
    require(
        len(current_jobs(command=command)) + prepared["new_jobs"] <= 95,
        "Submission headroom changed.",
    )
    write(
        queue / "submission_intent.json",
        {
            "queue_sha256": digest(queue / "queue.json"),
            "new_jobs": prepared["new_jobs"],
            "hold": True,
        },
    )
    receipts = dict(manifest["attached"])
    for node in manifest["schedule"]["jobs"]:
        if node["id"] in receipts:
            continue
        directory = node_directory(queue, node)
        dependency = dependencies(node, receipts, manifest["attached"], command=command)
        argv = [
            "sbatch",
            "--parsable",
            "--hold",
            "--kill-on-invalid-dep=yes",
            *scheduler_args(node, engine),
            "--job-name=serial-" + slug(node["id"]),
            "--chdir=" + str(directory),
            "--output=" + str(directory / "slurm.out"),
            "--error=" + str(directory / "slurm.err"),
        ]
        if dependency:
            argv.append("--dependency=" + dependency)
        argv.append(str(directory / "batch.sh"))
        write(directory / "submission_intent.json", {"argv": argv, "dependency": dependency})
        try:
            result = command(argv)
        except Exception as error:
            write(
                directory / "submission_error.json",
                {"error_kind": type(error).__name__, "automatic_retry_allowed": False},
            )
            raise ValueError(
                "Uncertain submission; new jobs remain held; preserve receipts."
            ) from error
        write(
            directory / "submission_response.json",
            {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr},
        )
        match = re.fullmatch(r"([1-9][0-9]*)(?:;[A-Za-z0-9_-]+)?\s*", result.stdout)
        require(
            result.returncode == 0 and match,
            "Rejected/uncertain submission; do not release or repeat submit.",
        )
        job = {
            "job_id": match[1],
            "node": node["id"],
            "controller_commit": sha,
            "queue_sha256": digest(queue / "queue.json"),
            "dependency": dependency,
            "submission_index": len(receipts),
            "attached_existing": False,
        }
        write(directory / "job.json", job)
        if node["kind"] == "scientific_solve":
            claim = CAMPAIGN / node["cell"]
            original_job = {
                "job_id": job["job_id"],
                "source_commit": ENGINE_SHA,
                "plan_sha256": engine.c.digest(engine.read(claim / "plan.json")),
            }
            engine.write_json(claim / "submission_intent.json", original_job)
            engine.write_json(claim / "job.json", original_job)
        receipts[node["id"]] = job
    require(len(receipts) == 95, "Incomplete graph remains held.")
    write(
        queue / "submitted.json",
        {
            "receipts": receipts,
            "new_jobs": prepared["new_jobs"],
            "queue_sha256": digest(queue / "queue.json"),
            "held": True,
        },
    )
    return {
        "status": "all_new_jobs_submitted_held",
        "new_jobs": prepared["new_jobs"],
        "attached_jobs": 2,
        "release_performed": False,
    }


def dependency_pairs(text):
    text = re.sub(r"\([^)]*\)", "", text)
    if not text:
        return set()
    result = set()
    for clause in text.split(","):
        kind, *ids = clause.split(":")
        require(
            kind in {"afterok", "afterany"}
            and ids
            and all(re.fullmatch(r"[1-9][0-9]*", x) for x in ids),
            "Unsupported or weakened dependency.",
        )
        result.update((kind, job) for job in ids)
    return result


def verify_pending(fields, job, node, directory, uid, satisfied=()):
    require(
        fields.get("JobId") == job["job_id"]
        and fields.get("JobState") == "PENDING"
        and fields.get("Priority") == "0"
        and fields.get("Reason") == "JobHeldUser"
        and re.fullmatch(r"[^()]+\(" + str(uid) + r"\)", fields.get("UserId", ""))
        and fields.get("WorkDir") == str(directory)
        and fields.get("Command") == str(directory / "batch.sh")
        and fields.get("Partition") == "intel-256"
        and fields.get("Account") == "sxdsouza"
        and fields.get("QOS") == "preempt"
        and fields.get("Requeue") == "0",
        "Held job ownership/profile drift.",
    )
    minutes = node["wall_seconds"] // 60
    expected_time = f"{minutes // 60:02}:{minutes % 60:02}:00"
    memory = fields.get("MinMemoryNode")
    require(
        fields.get("TimeLimit") == expected_time
        and fields.get("NumNodes") in {"1", "1-1"}
        and fields.get("NumCPUs", "").isdigit()
        and int(fields["NumCPUs"]) >= node["requested_cpus"]
        and memory in {str(node["memory_mib"]) + "M", str(node["memory_mib"] // 1024) + "G"},
        "Held time/CPU/memory profile differs.",
    )
    if node["exclusive"]:
        aliases = {"Shared": {"0", "EXCLUSIVE"}, "OverSubscribe": {"NO", "EXCLUSIVE"}}
        observed = [fields[k] in allowed for k, allowed in aliases.items() if k in fields]
        require(observed and all(observed), "Held exclusive request differs.")
    observed = dependency_pairs(fields.get("Dependency", "(null)"))
    expected = dependency_pairs(job["dependency"] or "")
    require(
        observed <= expected and expected - observed <= set(satisfied), "Queued dependency differs."
    )


def release(queue, sha, *, command=run):
    login()
    manifest, engine, _ = root_context(queue, sha)
    submitted = read(queue / "submitted.json")
    require(
        submitted["queue_sha256"] == digest(queue / "queue.json")
        and len(submitted["receipts"]) == 95,
        "Complete submitted graph required.",
    )
    require(
        not (queue / "release_intent.json").exists(), "Existing release intent; reconcile only."
    )
    ids = []
    for node in manifest["schedule"]["jobs"]:
        directory = node_directory(queue, node)
        job = read(directory / "job.json")
        require(job == submitted["receipts"][node["id"]], "Job receipt drift.")
        if job.get("attached_existing"):
            continue
        require(
            (directory / "batch.sh").read_text(encoding="utf-8") == script_text(queue, node, sha),
            "Queued script changed.",
        )
        query = command(["scontrol", "-o", "show", "job", job["job_id"]])
        require(query.returncode == 0, "Held job unavailable.")
        satisfied = set()
        expected = dependency_pairs(job["dependency"] or "")
        for parent in node["parents"]:
            if parent in manifest["attached"]:
                external = manifest["attached"][parent]["job_id"]
                row = accounting(external, command=command)
                for kind, dep_job in expected:
                    if (
                        dep_job == external
                        and row["state"] in TERMINAL
                        and (
                            kind == "afterany"
                            or row["state"] == "COMPLETED"
                            and row["exit_code"] == "0:0"
                        )
                    ):
                        satisfied.add((kind, external))
        verify_pending(engine.o.fields(query.stdout), job, node, directory, os.getuid(), satisfied)
        ids.append(job["job_id"])
    require(len(ids) == submitted["new_jobs"], "New job count differs.")
    write(
        queue / "release_intent.json",
        {"job_ids": ids, "queue_sha256": digest(queue / "queue.json")},
    )
    try:
        result = command(["scontrol", "release", ",".join(ids)])
    except Exception as error:
        write(
            queue / "release_error.json",
            {"error_kind": type(error).__name__, "automatic_retry_allowed": False},
        )
        raise ValueError("Release uncertain; do not repeat, inspect original jobs.") from error
    write(
        queue / "release_response.json",
        {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr},
    )
    require(result.returncode == 0, "Release uncertain; do not repeat, inspect original jobs.")
    write(queue / "released.json", {"job_ids": ids, "queue_sha256": digest(queue / "queue.json")})
    return {
        "status": "bounded_graph_released",
        "new_jobs": len(ids),
        "attached_jobs": 2,
        "automatic_retry_or_extra_submissions": False,
    }


def compute_context(queue, sha, identity):
    manifest, engine, campaign = root_context(queue, sha)
    node = node_at(manifest, identity)
    directory = node_directory(queue, node)
    job = read(directory / "job.json")
    require(
        not job.get("attached_existing") and os.environ.get("SLURM_JOB_ID") == job["job_id"],
        "Owned controller job required.",
    )
    deadline = time.monotonic() + 120
    while not (queue / "released.json").exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    require(
        (queue / "released.json").is_file(), "Complete release not confirmed; no private build."
    )
    released = read(queue / "released.json")
    require(
        released["queue_sha256"] == digest(queue / "queue.json")
        and job["job_id"] in released["job_ids"]
        and job["queue_sha256"] == released["queue_sha256"],
        "Explicit complete release required.",
    )
    submitted = read(queue / "submitted.json")
    require(submitted["receipts"][identity] == job, "Controller job receipt differs.")
    query = run(["scontrol", "-o", "show", "job", job["job_id"]])
    require(query.returncode == 0, "Controller allocation unavailable.")
    verify_running(engine.o.fields(query.stdout), job, node, directory, os.getuid())
    return manifest, engine, campaign, node, directory


def verify_running(fields, job, node, directory, uid):
    require(fields.get("JobState") == "RUNNING", "Owned job is not running.")
    held_fields = dict(
        fields,
        JobState="PENDING",
        Priority="0",
        Reason="JobHeldUser",
        Dependency=job["dependency"] or "(null)",
    )
    verify_pending(held_fields, job, node, directory, uid)


def required_pilots(engine, item):
    populations = []
    position = engine.c.POPULATIONS.index(item["population"])
    if position:
        populations.append(engine.c.POPULATIONS[position - 1])
    if not item["pilot"]:
        populations.append(item["population"])
    observations = []
    for population in populations:
        for identity in sorted(engine.c.pilot_ids(population)):
            saved = engine.read(CAMPAIGN / identity / "collection.json")
            observations.append(engine.archive_report(CAMPAIGN / identity, saved))
    return observations


def healthy_observation(row):
    return (
        row.get("operational_receipts_closed") is True
        and row.get("native_result_returned") is True
        and row.get("incumbent_validation_rejected") is False
    )


def health(queue, sha, identity):
    manifest, engine, _, node, directory = compute_context(queue, sha, identity)
    check_storage(manifest)
    require(node["kind"] == "scientific_solve", "Scientific preflight only.")
    item = engine.c.select(node["cell"])
    prior = required_pilots(engine, item)
    engine.c.admit(item, prior, CAMPAIGN_SHA)
    for parent in node["parents"]:
        predecessor = node_at(manifest, parent)
        if predecessor["kind"] != "scientific_solve":
            report = read(node_directory(queue, predecessor) / "stage_result.json")
            require(report["status"] == "accepted", "Predecessor stage not accepted.")
            continue
        claim = CAMPAIGN / predecessor["cell"]
        plan, _ = engine.load_run(claim, ENGINE_SHA)
        job = engine.o.job_receipt(claim, ENGINE_SHA)
        query = run(
            [
                "sacct",
                "-j",
                job["job_id"],
                "--noheader",
                "--parsable2",
                "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
            ]
        )
        require(query.returncode == 0, "Predecessor accounting unavailable.")
        rows = engine.r.r2.accounting(query.stdout, job["job_id"])
        entry = engine.read(claim / "control/sto/entry.json")
        wanted = {job["job_id"], job["job_id"] + ".batch", job["job_id"] + "." + entry["step_id"]}
        require(
            wanted <= {row["job_id"] for row in rows}
            and all(
                row["state"] == "COMPLETED" and row["exit_code"] == "0:0"
                for row in rows
                if row["job_id"] in wanted
            ),
            "Predecessor not closed.",
        )
        science = engine.review_products(claim, plan)
        files = engine.evidence_files(claim)
        closed, _ = engine.operational_closure(
            claim, job, rows, wanted, engine.small_controls(files)
        )
        require(
            closed
            and science["native_result_returned"]
            and not science["incumbent_validation_rejected"],
            "Predecessor review rejected.",
        )
        if not item["pilot"]:
            proof = engine.c.gate(item["population"], prior, CAMPAIGN_SHA)
            runtime = engine.read(claim / "control/sto/runtime.json")
            require(
                [science["matrix_sha256"], science["bounds_sha256"]] == proof["matrix_and_bounds"]
                and runtime["hardware_class_sha256"] == proof["hardware_class_sha256"],
                "Predecessor algebra/hardware drift.",
            )
    write(
        directory / "health.json",
        {"status": "accepted", "cell": item["id"], "fresh_optimization": False},
    )
    return 0


def batch(queue, sha, identity):
    _, engine, _, node, directory = compute_context(queue, sha, identity)
    require(node["kind"] == "scientific_solve", "Scientific node required.")
    before = time.monotonic()
    argv = [
        sys.executable,
        "-B",
        "-I",
        str(ROOT / "scripts/pyomo_serial_queue.py"),
        "health",
        "--queue",
        str(queue),
        "--controller-sha",
        sha,
        "--node",
        identity,
    ]
    with (directory / "health.out").open("xb") as out, (directory / "health.err").open("xb") as err:
        result = subprocess.run(argv, stdout=out, stderr=err, timeout=300, check=False)
    write(
        directory / "preflight.json",
        {
            "seconds": time.monotonic() - before,
            "returncode": result.returncode,
            "scope": "Outside unchanged worker/application clocks",
        },
    )
    require(result.returncode == 0, "Serial preflight rejected; no private build started.")
    query = run(["scontrol", "-o", "show", "job", os.environ["SLURM_JOB_ID"]])
    require(query.returncode == 0, "Remaining envelope unavailable.")
    runtime = engine.o.fields(query.stdout).get("RunTime", "")
    match = re.fullmatch(r"(?:(\d+)-)?(\d+):(\d+):(\d+)", runtime)
    require(match, "Elapsed root time unavailable.")
    elapsed = int(match[1] or 0) * 86400 + int(match[2]) * 3600 + int(match[3]) * 60 + int(match[4])
    # Spend preflight from the existing30min job contingency. Retain the full
    # 11h worker plus30min setup/cleanup; never reduce/reset its8h native budget.
    require(
        elapsed <= engine.c.PROFILE["contingency_seconds"],
        "Preflight consumed the contingency; no private build started.",
    )
    # The original batch supervisor releases a new, cold -I -S worker process.
    # No predecessor incumbent or live native object enters that process.
    return engine.batch(CAMPAIGN / node["cell"], ENGINE_SHA)


def collect_stage(queue, sha, identity):
    manifest, engine, _, node, directory = compute_context(queue, sha, identity)
    check_storage(manifest)
    require(
        node["kind"] in {"pilot_collection_and_gate", "population_collection"},
        "Finite collection stage required.",
    )
    script_dir = str(ROOT / "scripts")
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from pyomo_serial_collection import collect

    output = directory / "cases"
    output.mkdir()
    records = []
    stage_deadline = time.monotonic() + node["wall_seconds"] - 900
    for cell in node["cells"]:
        try:
            check_storage(manifest)
            require(time.monotonic() < stage_deadline, "Collection stage reserve reached.")
            deadline = min(time.monotonic() + 300, stage_deadline)
            while True:
                saved = collect(engine, CAMPAIGN / cell, ENGINE_SHA, command=run)
                if saved.get("status") != "nonterminal_or_accounting_pending":
                    break
                require(time.monotonic() < deadline, "Bounded accounting wait exhausted.")
                time.sleep(5)
            write(output / (cell + ".json"), saved)
            records.append(saved.get("observation", saved))
        except Exception as error:
            failure = {
                "cell_id": cell,
                "status": "collection_preserved_needs_review",
                "error_kind": type(error).__name__,
                "automatic_retry_allowed": False,
            }
            write(output / (cell + ".error.json"), failure)
            records.append(failure)
    accepted = all(healthy_observation(row) for row in records)
    report = {
        "status": "rejected",
        "node": identity,
        "rows": records,
        "extra_submission_or_retry": False,
    }
    try:
        require(accepted and len(records) == len(node["cells"]), "Stage not operationally closed.")
        population = node["population"]
        pilots = []
        for cell in sorted(engine.c.pilot_ids(population)):
            saved = engine.read(CAMPAIGN / cell / "collection.json")
            pilots.append(engine.archive_report(CAMPAIGN / cell, saved))
        proof = engine.c.gate(population, pilots, CAMPAIGN_SHA)
        for row in records:
            require(
                [row["matrix_sha256"], row["bounds_sha256"]] == proof["matrix_and_bounds"]
                and row["hardware_class_sha256"] == proof["hardware_class_sha256"],
                "Stage matrix/bounds/hardware differs from four pilots.",
            )
        report.update(status="accepted", population_gate=proof)
    except Exception as error:
        report["error_kind"] = type(error).__name__
    write(directory / "stage_result.json", report)
    return int(report["status"] != "accepted")


def final(queue, sha, identity):
    manifest, engine, _, node, directory = compute_context(queue, sha, identity)
    require(node["kind"] == "final_consolidation", "Final node required.")
    output = directory / "tables"
    output.mkdir()
    configs, results = [], []
    nodes = {n.get("cell"): n for n in manifest["schedule"]["jobs"] if "cell" in n}
    for item in engine.c.cells():
        claim = CAMPAIGN / item["id"]
        row = {}
        if (claim / "collection.json").exists():
            saved = engine.read(claim / "collection.json")
            row = engine.archive_report(claim, saved)
        elif item["id"] in nodes:
            stage = node_at(manifest, "control:" + nodes[item["id"]]["stage"])
            case_path = node_directory(queue, stage) / "cases" / (item["id"] + ".json")
            if case_path.exists():
                saved = read(case_path)
                require(
                    saved.get("status") == "not_executed_scheduler_cancelled"
                    and saved["cell"]["id"] == item["id"],
                    "Unexpected unarchived case record.",
                )
                row = saved
        state = "not_started"
        job_id = None
        if (claim / "job.json").exists():
            job_id = engine.o.job_receipt(claim, ENGINE_SHA)["job_id"]
            state = accounting(job_id)["state"]
        configs.append(
            {
                **item,
                "interface": "appsi_" + item["solver"],
                "engine_commit": ENGINE_SHA,
                "controller_commit": sha,
                "highs_parallel": "on" if item["solver"] == "highs" else "not_applicable",
                "worker_logical_cpus": 16,
                "memory_mib": 196608,
                "slurm_seconds": 43200,
            }
        )
        timing = row.get("timings", {})
        results.append(
            {
                "id": item["id"],
                "population": item["population"],
                "solver": item["solver"],
                "threads": item["threads"],
                "repetition": item["repetition"],
                "job_id": job_id,
                "scheduler_state": state,
                "status": row.get("status", "not_executed_or_uncollected"),
                "objective": row.get("objective"),
                "bound": row.get("bound"),
                "common_gap": row.get("common_gap"),
                "native_gap": row.get("native_gap"),
                "quality_target_met": row.get("quality_target_met"),
                "classification": row.get("classification"),
                "validation": row.get("original_validation_status"),
                "native_seconds": timing.get("solver_reported_runtime_seconds"),
                "end_to_end_seconds": timing.get("end_to_end_seconds"),
                "sampled_peak_bytes": row.get("resource_observation", {}).get(
                    "sampled_worker_tree_peak_bytes"
                ),
                "matrix_sha256": row.get("matrix_sha256"),
                "operational_receipts_closed": row.get("operational_receipts_closed"),
                "serial_node": nodes.get(item["id"], {}).get("id"),
            }
        )
    for name, rows in (("configurations.csv", configs), ("results.csv", results)):
        with (output / name).open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    write(
        directory / "final_result.json",
        {
            "status": "all_90_cell_states_exported",
            "rows": 90,
            "new_results_imputed": False,
            "files": {p.name: digest(p) for p in output.iterdir()},
        },
    )
    return 0


def status(queue, sha):
    login()
    manifest, _, _ = root_context(queue, sha, expensive=False)
    rows = []
    for node in manifest["schedule"]["jobs"]:
        path = node_directory(queue, node) / "job.json"
        if path.exists():
            job = read(path)
            rows.append({"node": node["id"], **accounting(job["job_id"])})
    return {
        "status": "read_only_queue_status",
        "jobs": rows,
        "released": (queue / "released.json").exists(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("prepare", "submit", "release", "status", "health", "batch", "control", "final"),
    )
    parser.add_argument("--queue", type=Path, default=QUEUE)
    parser.add_argument("--controller-sha", required=True)
    parser.add_argument("--node")
    parser.add_argument("--storage-budget-gib", type=int)
    args = parser.parse_args()
    if args.action in {"prepare", "submit", "release", "status"}:
        if args.action == "prepare":
            result = prepare(
                args.queue, args.controller_sha, storage_budget_gib=args.storage_budget_gib
            )
        else:
            result = globals()[args.action](args.queue, args.controller_sha)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    require(args.node is not None, "Owned compute node required.")
    action = {"health": health, "batch": batch, "control": collect_stage, "final": final}[
        args.action
    ]
    return action(args.queue, args.controller_sha, args.node)


if __name__ == "__main__":
    raise SystemExit(main())
