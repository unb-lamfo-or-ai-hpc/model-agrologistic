"""Minimal academic contract and independent replay; no execution effects here."""

from __future__ import annotations

import hashlib
import io
import re
import tarfile
from pathlib import Path

from scripts import mvp2_h300_controls as c
from scripts import mvp2_h300_thread_contract as design
from scripts import mvp2_s2_batch_adapter as old

ROOT = Path(__file__).resolve().parents[1]
STAGES = (
    "normal",
    "build_failure",
    "optimization_failure",
    "export_failure",
    "disposal_failure",
    "nested_setsid_term_ignore",
    "native_miniature",
)
LIMIT = 32 * 1024**2
FILES = {"plan.json", "job.json", "accounting.txt", "records.json", "review.json"}
RECORDS = {
    "batch-diagnostic.json",
    "allocation.json",
    "attempt.json",
    "worker-start.json",
    "worker-result.json",
    "worker-failure.json",
    "nested.json",
    "license.json",
    "native/phase-0.json",
    "native/phase-1.json",
    "native/phase-2.json",
    "native/phase-3.json",
    "native/failure-cleanup.json",
    "native/native-terminal.json",
    "native/failure.json",
    "native/products/observation.json",
    "native/products/incumbent.json",
    "native/products/independent_validation.json",
    "native/products/closure.json",
}
require = design.require
digest = design.digest


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def profile():
    value = c.read_json(ROOT / "docs/mvp2_s2_academic_profile.json")
    require(value["schema_version"] == "s2-academic-profile-v1", "Profile version.")
    require(value["stages"] == list(STAGES), "Stage scope.")
    require(
        value["synthetic"]
        == {
            "cpus": 2,
            "memory_mib": 2048,
            "wall_seconds": 720,
            "work_seconds": 180,
            "cleanup_seconds": 300,
        },
        "Synthetic envelope.",
    )
    require(
        value["native"]
        == {
            "cpus": 4,
            "memory_mib": 16384,
            "wall_seconds": 2400,
            "phase_seconds": [120, 1800, 120, 300],
        },
        "Native miniature envelope.",
    )
    require(
        all(
            value[k] is False
            for k in (
                "automatic_chaining",
                "automatic_repeats",
                "production_isolation_certified",
                "h300_execution_admitted",
            )
        ),
        "Admission drift.",
    )
    return value


def fixture():
    """The existing public analytical fixture, not a private workbook or new model."""
    from scripts import mvp2_threads as screen
    from src.logic.mathematical_contract import prepare_model_data

    config = screen.spec(4, ROOT).model
    return prepare_model_data(screen.fixture_data(), config), config


def runtime():
    from scripts.mvp2_h300_worker_evidence import runtime_receipt

    return runtime_receipt()


def plan(stage, source, files, runtime_record):
    require(stage in STAGES, "Unknown stage.")
    require(re.fullmatch(r"[0-9a-f]{40}", source or ""), "Full reviewed source required.")
    require(isinstance(files, dict) and 1 <= len(files) <= 1024, "Source inventory.")
    require(all(re.fullmatch(r"[0-9a-f]{64}", x) for x in files.values()), "Source hashes.")
    data, config = fixture()
    from src.logic.run_integrity import scientific_identity

    return {
        "schema_version": "s2-academic-plan-v1",
        "stage": stage,
        "source_commit": source,
        "profile": profile(),
        "files": files,
        "runtime": runtime_record,
        "fixture": {
            "data_sha256": scientific_identity(data),
            "config_sha256": scientific_identity(config),
        },
        "production_isolation_certified": False,
        "h300_execution_admitted": False,
    }


def validate_plan(value):
    require(
        set(value)
        == set(plan(value["stage"], value["source_commit"], value["files"], value["runtime"])),
        "Plan fields.",
    )
    require(
        value == plan(value["stage"], value["source_commit"], value["files"], value["runtime"]),
        "Plan drift.",
    )
    return value


def expected_phases(stage):
    phases = ["build", "optimization", "export", "disposal"]
    return (
        phases[: phases.index(stage.removesuffix("_failure")) + 1]
        if stage.endswith("_failure")
        else phases
    )


def scheduler_fields(text):
    """Keep only bounded resource/identity fields; exclude paths and arbitrary metadata."""
    pairs = re.findall(r"(?:^|\s)([A-Za-z][A-Za-z0-9_/:]*)=(\S*)", text)
    fields = dict(pairs)
    require(len(pairs) == len(fields), "Duplicate scheduler field.")
    selected = {
        key: fields[key]
        for key in (
            "JobId",
            "UserId",
            "JobState",
            "Partition",
            "Account",
            "NumNodes",
            "NumCPUs",
            "NumTasks",
            "CPUs/Task",
            "NodeList",
            "BatchHost",
            "ReqTRES",
            "TRES",
            "AllocTRES",
            "MinMemoryNode",
            "MinMemoryCPU",
            "TimeLimit",
        )
        if key in fields
    }
    require(all(len(v) <= 512 for v in selected.values()), "Scheduler field bound.")
    return selected


def allocation(text, job, uid, envelope):
    """Scheduler allocation observation, explicitly not kernel isolation proof."""
    fields = scheduler_fields(text)
    require(
        fields.get("JobId") == job
        and fields.get("JobState") == "RUNNING"
        and fields.get("NumNodes") == "1"
        and fields.get("Partition") == "intel-256"
        and fields.get("Account") == "sxdsouza",
        "Allocation identity/scope.",
    )
    require(fields.get("UserId", "").endswith(f"({uid})"), "Allocation UID.")
    require(
        fields.get("NodeList") == fields.get("BatchHost")
        and re.fullmatch(r"[A-Za-z0-9_-]+", fields.get("NodeList", "")),
        "Single node.",
    )
    require(int(fields.get("NumCPUs", "0")) >= envelope["cpus"], "Allocated CPU deficit.")
    from scripts.validate_scip_memory_resources import memory_mib

    def resources(value):
        entries = [item.split("=", 1) for item in value.split(",")]
        require(all(len(item) == 2 for item in entries), "Malformed resource TRES.")
        tres = dict(entries)
        require(len(entries) == len(tres), "Duplicate resource TRES.")
        require(re.fullmatch(r"[1-9][0-9]*", tres.get("cpu", "")), "Resource CPU grammar.")
        require(tres.get("node") == "1", "Resource node scope.")
        return int(tres["cpu"]), memory_mib(value)

    # Slurm22.05 prints TRES as allocation when running, NOT ReqTRES.
    # Keep requested CPU/node memory separate from the allocated CPU rounding.
    if "ReqTRES" in fields:
        requested_cpu, requested_mem = resources(fields["ReqTRES"])
        basis = "ReqTRES"
    else:
        require(fields.get("NumTasks") == "1", "One requested task required.")
        require(re.fullmatch(r"[1-9][0-9]*", fields.get("CPUs/Task", "")), "Task CPU grammar.")
        require("MinMemoryNode" in fields and "MinMemoryCPU" not in fields, "Node memory required.")
        requested_cpu = int(fields["CPUs/Task"])
        requested_mem = memory_mib("mem=" + fields["MinMemoryNode"])
        basis = "CPUs/Task+MinMemoryNode"
    require(
        requested_cpu == envelope["cpus"] and requested_mem == envelope["memory_mib"],
        "Requested resources.",
    )
    # Reject contradictory aliases rather than choosing whichever would pass.
    if "CPUs/Task" in fields:
        require(fields["CPUs/Task"] == str(requested_cpu), "Requested CPU aliases disagree.")
    if "NumTasks" in fields:
        require(fields["NumTasks"] == "1", "Requested task count.")
    if "MinMemoryNode" in fields:
        require(
            memory_mib("mem=" + fields["MinMemoryNode"]) == requested_mem,
            "Requested memory aliases disagree.",
        )
    require("MinMemoryCPU" not in fields, "Per-CPU memory is not this contract.")
    allocated = [resources(fields[k]) for k in ("TRES", "AllocTRES") if k in fields]
    require(allocated and len(set(allocated)) == 1, "Missing/contradictory allocated TRES.")
    require(
        allocated[0] == (int(fields["NumCPUs"]), envelope["memory_mib"]),
        "Allocated resources disagree.",
    )
    h, m, sec = map(int, fields.get("TimeLimit", "0:0:0").split(":"))
    require(h * 3600 + m * 60 + sec == envelope["wall_seconds"], "Walltime drift.")
    return {
        "job_id": job,
        "uid": uid,
        "node": fields["NodeList"],
        "requested": envelope,
        "allocated_cpus": int(fields["NumCPUs"]),
        "allocated_tres": fields.get("AllocTRES", fields.get("TRES")),
        "requested_resource_basis": basis,
        "scheduler_fields": fields,
        "scheduler_observation_only": True,
    }


def native_review(records, p):
    """Fresh residual/degradation checks; no fabricated parent containment receipt."""
    from scripts import mvp2_h300_partial as partial

    data, config = fixture()
    observation = records["native/products/observation.json"]
    anchor = partial.anchor(
        data,
        config,
        source_commit=p["source_commit"],
        runtime_sha256=digest(p["runtime"]),
        workbook_sha256=p["fixture"]["data_sha256"],
        threads=4,
    )
    require(observation["anchor"] == anchor, "Native external scientific identity.")
    terminal = records["native/native-terminal.json"]
    require(
        terminal["solution_count"] == observation["solution_count"]
        and terminal["native_status_name"] == observation["native_status"],
        "Native drift.",
    )
    assets = {
        k.removeprefix("native/products/"): c.encoded(v)
        for k, v in records.items()
        if k.startswith("native/products/")
    }
    closure = records["native/products/closure.json"]
    require(
        closure["anchor_sha256"] == digest(anchor)
        and closure["production_admitted"] is False
        and closure["repeats_admitted"] is False
        and closure["artifacts"] == {k: sha(v) for k, v in assets.items() if k != "closure.json"},
        "Native product bytes.",
    )
    require(records["license.json"]["status"] == "accepted", "Fresh license evidence.")
    require(records["license.json"].get("gurobi_version") is not None, "Native version missing.")
    for index, phase in enumerate(c.PHASES):
        require(
            records[f"native/phase-{index}.json"]
            == {
                "identity": digest(anchor),
                "index": index,
                "phase": phase,
            },
            "Native phase sequence.",
        )
    result = partial.evaluate(
        observation, records.get("native/products/incumbent.json"), data, config, anchor
    )
    require(
        result["validation"] == records["native/products/independent_validation.json"],
        "Fresh residual mismatch.",
    )
    return result


def review(p, job, records, accounting):
    """Unknown/incomplete outcomes stay negative; accepted is scoped to academic use."""
    validate_plan(p)
    require(re.fullmatch(r"[1-9][0-9]*", job or ""), "Job identity.")
    require(set(records) <= RECORDS, "Unallowlisted worker product.")
    row = old.accounting(accounting, job)
    # No unknown additional numeric steps can be silently omitted.
    attempt = records.get("attempt.json", {})
    step = attempt.get("step_id")
    known = {job, job + ".batch", job + ".extern"}
    if isinstance(step, str) and re.fullmatch(re.escape(job) + r"\.[0-9]+", step):
        known.add(step)
    checks = {
        "accounting_scope": set(row) <= known,
        "root_completed": row.get(job, {}).get("state") == "COMPLETED"
        and row.get(job, {}).get("exit_code") == "0:0",
        "batch_completed": row.get(job + ".batch", {}).get("state") == "COMPLETED"
        and row.get(job + ".batch", {}).get("exit_code") == "0:0",
        "extern_terminal": row.get(job + ".extern", {}).get("state") in old.TERMINAL,
        "step_terminal": row.get(step, {}).get("state") in old.TERMINAL,
        "attempt_bound": attempt.get("plan_sha256") == digest(p),
        "local_client_reaped": attempt.get("local_client_reaped") is True,
    }
    start = records.get("worker-start.json", {})
    checks["worker_bound"] = (
        start.get("plan_sha256") == digest(p)
        and start.get("job_id") == job
        and start.get("step_id") == step
        and start.get("runtime_sha256") == digest(p["runtime"])
    )
    alloc = records.get("allocation.json", {})
    envelope = p["profile"]["native" if p["stage"] == "native_miniature" else "synthetic"]
    checks["allocation_bound"] = (
        alloc.get("job_id") == job
        and alloc.get("requested") == envelope
        and "scheduler_fields" in alloc
    )
    if "scheduler_fields" in alloc:
        try:
            fields = alloc["scheduler_fields"]
            require(isinstance(fields, dict), "Scheduler field record.")
            require(
                all(
                    isinstance(k, str) and isinstance(v, str) and not re.search(r"\s", k + v)
                    for k, v in fields.items()
                ),
                "Scheduler field grammar.",
            )
            rebuilt = allocation(
                " ".join(f"{k}={v}" for k, v in fields.items()), job, alloc["uid"], envelope
            )
            checks["allocation_bound"] = checks["allocation_bound"] and rebuilt == alloc
        except (KeyError, ValueError, TypeError):
            checks["allocation_bound"] = False
    checks["uid_bound"] = start.get("uid") == alloc.get("uid") and type(start.get("uid")) is int
    result = records.get("worker-result.json", {})
    checks["result_bound"] = result.get("plan_sha256") == digest(p)
    checks["no_unplanned_stop"] = attempt.get("stop_reason") is None
    checks["initial_affinity"] = len(start.get("affinity", [])) == (
        4 if p["stage"] == "native_miniature" else 1
    )
    native = None
    stage = p["stage"]
    if stage == "native_miniature":
        try:
            native = native_review(records, p)
        except (KeyError, ValueError, TypeError):
            native = None
        checks["expected_outcome"] = (
            native is not None
            and native["classification"]["disposition"] == "complete_accepted_hierarchy"
            and row.get(step, {}).get("state") == "COMPLETED"
            and row.get(step, {}).get("exit_code") == "0:0"
            and result.get("outcome") == "native_complete"
        )
    elif stage == "nested_setsid_term_ignore":
        # Planned cancellation has no successful terminal worker result.
        checks["result_bound"] = True
        checks["no_unplanned_stop"] = attempt.get("stop_reason") == "planned_nested_stop"
        nested = records.get("nested.json", {})
        checks["expected_outcome"] = (
            nested.get("plan_sha256") == digest(p)
            and nested.get("extra_processes") == 2
            and attempt.get("stop_reason") == "planned_nested_stop"
            and attempt.get("term_sent") is True
            and attempt.get("kill_sent") is True
            and attempt.get("descendants_absent_observed") is True
            and row.get(step, {}).get("state") == "CANCELLED"
            and row.get(step, {}).get("exit_code") in {"0:9", "137:0"}
        )
    else:
        expected = "synthetic_complete" if stage == "normal" else "expected_phase_failure"
        checks["expected_outcome"] = (
            result.get("outcome") == expected
            and result.get("phases") == expected_phases(stage)
            and row.get(step, {}).get("state") == ("COMPLETED" if stage == "normal" else "FAILED")
            and row.get(step, {}).get("exit_code") == ("0:0" if stage == "normal" else "3:0")
        )
    return {
        "schema_version": "s2-academic-review-v1",
        "stage": stage,
        "job_id": job,
        "source_commit": p["source_commit"],
        "plan_sha256": digest(p),
        "checks": checks,
        "disposition": "academic_stage_accepted"
        if all(checks.values())
        else "evidence_not_accepted",
        "native": native,
        "cleanup_evidence": "scheduler_terminal_and_local_reap_not_global_proof",
        "production_isolation_certified": False,
        "h300_execution_admitted": False,
    }


def audit(path, checksum, source, expected_plan, job):
    raw = Path(path).read_bytes()
    require(len(raw) <= LIMIT and sha(raw) == checksum, "Archive checksum/size.")
    import gzip

    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        payload = stream.read(LIMIT + 1)
    require(len(payload) <= LIMIT, "Expanded archive bound.")
    files = {}
    end = 0
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
        for member in archive:
            require(
                member.isfile()
                and member.name in FILES
                and member.name not in files
                and not member.pax_headers
                and member.size <= LIMIT,
                "Archive member.",
            )
            files[member.name] = archive.extractfile(member).read()
            end = member.offset_data + ((member.size + 511) // 512) * 512
    require(set(files) == FILES and not any(payload[end:]), "Archive closure/trailing bytes.")
    p = c.decode_json(files["plan.json"])
    require(p["source_commit"] == source and digest(p) == expected_plan, "External source/plan.")
    require(
        c.decode_json(files["job.json"]) == {"job_id": job, "plan_sha256": expected_plan},
        "External job.",
    )
    result = review(p, job, c.decode_json(files["records.json"]), files["accounting.txt"].decode())
    require(c.decode_json(files["review.json"]) == result, "Canonical review mismatch.")
    return result


def prerequisites(stage, certificates, source):
    """Only freshly replayed predecessors; no approval booleans or afterok chain."""
    require(stage in STAGES, "Unknown stage.")
    expected = [] if stage == "normal" else ["normal"]
    if stage == "native_miniature":
        expected = list(STAGES[:-1])
    require(len(certificates) == len(expected), "Missing/extra predecessor.")
    for item, previous in zip(certificates, expected, strict=True):
        result = audit(*item)
        require(
            result["stage"] == previous
            and result["source_commit"] == source
            and result["disposition"] == "academic_stage_accepted",
            "Predecessor not accepted.",
        )


def execute_h300(*_args, **_kwargs):
    raise PermissionError("P4 needs its own qualified release and fresh admission.")
