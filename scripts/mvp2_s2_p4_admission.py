"""Bounded P4 prerequisite observation, never h300 execution admission.

No scheduler submission or agricultural model construction exists in this module.
An explicitly requested observation in an existing allocation may use only the
designated 2001-variable public license capability probe, not the h300 worker.
"""

from __future__ import annotations

import argparse
import gzip
import io
import os
import re
import subprocess
import sys
import tarfile
import time
from pathlib import Path

from scripts import mvp2_h300_controls as c
from scripts import mvp2_h300_thread_contract as d
from scripts import mvp2_s2_h300_academic as entry
from scripts import mvp2_s2_h300_products as p
from scripts import mvp2_s2_h300_runtime as r

ROOT = Path(__file__).resolve().parents[1]
CLAIM = ".mvp2-s2-p4-admission-v1"
P4_HEAD = "a958314746ed7ce66d43c88579da14b391d564bb"
P4_MERGE = "1c8503586c627849b061b7062cc7b78f0c940df3"
PR101_TRANSPORT = {
    "scripts/mvp2_s2_h300_academic.py": (
        "b08a581b3568b60956f0b0890c91cc6bfe130699cc0497295f408a865ea13538"
    ),
    "scripts/mvp2_s2_h300_runtime.py": (
        "f1ebdf77be384e5b1cfed39dcaf372a36262f2157df96488947a0bb6a518c36d"
    ),
    "scripts/mvp2_s2_h300_products.py": (
        "d1df3fa5b82a93c3fede0f404bd22bfe5f04e65a09dd2cca613890f7fb447225"
    ),
    "scripts/npad_s2_h300_academic.sh": (
        "03cf513f04361606ea20a43cd5918109c94c813896ae72451297dc743c7e177f"
    ),
}
# Current operational repair is separately source-bound; original PR101 bytes
# remain named for historical replay with their original qualified source.
TRANSPORT = {
    **PR101_TRANSPORT,
    "scripts/mvp2_s2_h300_runtime.py": (
        "85354beaffbf16b5d96305653333ae85afe66d7e4db54f5c99a2964df61cb5cf"
    ),
}
FLAGS = {
    "h300_execution_admitted": False,
    "repeats_admitted": False,
    "production_isolation_certified": False,
    "automatic_follow_on_allowed": False,
}
EXPORT = {
    "whole_block_bytes": p.LIMIT,
    "metadata_reserve_bytes": p.RESERVE,
    "actual_incumbent_fit": "not_established",
    "native_extraction_rss_bounded": False,
}
FILES = {"plan.json", "job.json", "records.json", "accounting.txt", "review.json"}
LIMIT = 8 * 1024**2


def validate(value):
    expected = {
        "schema_version": "s2-p4-admission-plan-v1",
        "p4_head": P4_HEAD,
        "p4_merge": P4_MERGE,
        "transport": TRANSPORT,
        "p3": entry.P3,
        "p4_plan": value["p4_plan"],
        "export_budget": EXPORT,
        "observer_seconds": 580,
        "cleanup_seconds": 20,
        **FLAGS,
    }
    d.require(c.encoded(value) == c.encoded(expected), "Admission contract drift.")
    r._validate(value["p4_plan"])
    runtime = value["p4_plan"]["runtime"]
    d.require(
        runtime["python_version"] == "3.13.15"
        and runtime["distributions"].get("gurobipy") == "13.0.3",
        "Runtime version drift.",
    )
    d.require(
        all(value["p4_plan"]["files"].get(k) == v for k, v in TRANSPORT.items()),
        "Unqualified P4 transport bytes.",
    )
    expected_input = p.read(ROOT / "docs/mvp2_h300_input_size_review.json")
    identity = value["p4_plan"]["input"]
    d.require(
        set(identity)
        == {"workbook_sha256", "reference_sha256", "data_sha256", "config_sha256", "counts", "size"}
        and d.digest(identity["counts"]) == d.digest(expected_input["counts"])
        and d.digest(identity["size"]) == d.digest(expected_input["snapshot_fields"]),
        "Input dimensions/routes.",
    )
    entry.require_hash(identity["data_sha256"])
    entry.require_hash(identity["config_sha256"])
    return value


def record_dir(path):
    path = p.safe(path)
    d.require(path.name == CLAIM and ROOT not in path.parents, "Dedicated admission record only.")
    return path


def prepare(target, commit, p3, reference, *, planner=r._plan):
    """Solver-free fresh input/source inspection before an exclusive NEW record."""
    target = record_dir(target)
    entry.require_hash(commit, 40)
    if target.exists():
        old = validate(p.read(target / "plan.json"))
        d.require(
            old["p4_plan"]["preparation"]["source_commit"] == commit, "Existing source drift."
        )
        return {"status": "existing_record_no_new_admission", "plan_sha256": d.digest(old), **FLAGS}
    for name, digest in TRANSPORT.items():
        d.require(p.sha_file(ROOT / name) == digest, "Current P4 transport drift.")
    native_plan = planner(commit, ROOT, p3, reference)
    value = validate(
        {
            "schema_version": "s2-p4-admission-plan-v1",
            "p4_head": P4_HEAD,
            "p4_merge": P4_MERGE,
            "transport": dict(TRANSPORT),
            "p3": dict(entry.P3),
            "p4_plan": native_plan,
            "export_budget": dict(EXPORT),
            "observer_seconds": 580,
            "cleanup_seconds": 20,
            **FLAGS,
        }
    )
    target.mkdir()  # Do not create/reuse an optimization claim or old run.
    p.publish(target / "plan.json", value)
    p.publish(
        target / "origin.json",
        {"root": str(ROOT), "python": sys.executable, "reference": str(Path(reference).absolute())},
    )
    return {"status": "prepared_execution_closed", "plan_sha256": d.digest(value), **FLAGS}


def load(target, expected):
    target = record_dir(target)
    entry.require_hash(expected)
    value = validate(p.read(target / "plan.json"))
    d.require(d.digest(value) == expected, "External admission plan anchor.")
    return target, value


def _observe_worker(
    target,
    *,
    recheck=r._recheck,
    environment=r._environment,
    probe=r._license,
    close_source=r.source.verify_tree,
):
    target = record_dir(target)
    value = validate(p.read(target / "plan.json"))
    job = p.read(target / "job.json")
    d.require(
        job["admission_plan_sha256"] == d.digest(value)
        and os.environ.get("SLURM_JOB_ID") == job["job_id"],
        "Observer job binding.",
    )
    origin = p.read(target / "origin.json")
    d.require(
        origin["root"] == str(ROOT) and origin["python"] == sys.executable, "Observer origin."
    )
    phase, observation = "source_runtime_input", None
    try:
        for name, digest in TRANSPORT.items():
            d.require(p.sha_file(ROOT / name) == digest, "Observer transport drift.")
        recheck(value["p4_plan"], ROOT, origin["reference"])
        phase = "allocation"
        allocation = environment(value["p4_plan"], job["job_id"])
        phase = "designated_license_capability_only"
        capability = probe()
        phase = "source_closure"
        close_source(ROOT, value["p4_plan"]["files"])
        observation = {
            "admission_plan_sha256": d.digest(value),
            "job_id": job["job_id"],
            "environment": allocation,
            "license": capability,
            "input_sha256": d.digest(value["p4_plan"]["input"]),
            "runtime_sha256": d.digest(value["p4_plan"]["runtime"]),
            "export_budget": dict(EXPORT),
            "capability_model_variables": 2001,
            "agricultural_model_built": False,
            **FLAGS,
        }
        p.publish(target / "observation.json", observation)
        phase = "complete"
        return 0
    except BaseException as error:
        p.publish(
            target / "diagnostic.json",
            {
                "phase": phase,
                "error_kind": type(error).__name__,
                "admission_plan_sha256": d.digest(value),
                **FLAGS,
            },
        )
        return 2


def observe(
    target, expected, job, *, acknowledged=False, popen=subprocess.Popen, clock=time.monotonic
):
    """One bounded observer in an EXISTING human allocation. No submission path."""
    d.require(acknowledged is True, "One observation-only acknowledgement required.")
    d.require(
        sys.platform == "linux"
        and os.getuid() > 0
        and re.fullmatch(r"[1-9][0-9]*", job or "")
        and os.environ.get("SLURM_JOB_ID") == job,
        "Existing non-root allocation required.",
    )
    target, value = load(target, expected)
    if (target / "job.json").exists():
        d.require(
            p.read(target / "job.json") == {"job_id": job, "admission_plan_sha256": expected},
            "Existing observer job drift.",
        )
        return {"status": "existing_observation_collect_only", **FLAGS}
    p.publish(target / "job.json", {"job_id": job, "admission_plan_sha256": expected})
    code = (
        "import sys;sys.dont_write_bytecode=True;sys.path.insert(0,"
        + repr(str(ROOT))
        + ");from scripts.mvp2_s2_p4_admission import _observe_worker;"
        + "raise SystemExit(_observe_worker("
        + repr(str(target))
        + "))"
    )
    start = clock()
    process, term, kill, reaped, error_kind, status = (
        None,
        False,
        False,
        False,
        None,
        "launch_failed",
    )
    try:
        with (
            (target / "observer.out").open("xb") as out,
            (target / "observer.err").open("xb") as err,
        ):
            process = popen(
                [sys.executable, "-B", "-I", "-c", code],
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
            )
            try:
                process.wait(timeout=max(0.1, start + 580 - clock()))
                reaped = True
                status = "complete" if process.returncode == 0 else "worker_failed"
            except subprocess.TimeoutExpired:
                status = "observer_timeout"
                process.terminate()  # This trusted local observer only, never a Slurm job.
                term = True
                try:
                    process.wait(timeout=max(0.1, start + 590 - clock()))
                except subprocess.TimeoutExpired:
                    process.kill()
                    kill = True
                    process.wait(timeout=max(0.1, start + 600 - clock()))
                reaped = True
    except BaseException as error:
        error_kind = type(error).__name__
        if process is not None and process.poll() is None:
            process.kill()
            kill = True
            try:
                process.wait(timeout=max(0.1, start + 600 - clock()))
                reaped = True
            except subprocess.TimeoutExpired:
                pass  # Unknown local cleanup is preserved, never promoted to success.
    result = {
        "status": status,
        "admission_plan_sha256": expected,
        "job_id": job,
        "term_sent": term,
        "kill_sent": kill,
        "local_client_reaped": reaped,
        "return_code": process.returncode if process else None,
        "error_kind": error_kind,
        "elapsed_seconds": clock() - start,
        "global_cleanup_proven": False,
        **FLAGS,
    }
    p.publish(target / "supervision.json", result)
    return result


def review(value, job, records, accounting):
    """Canonical metadata replay. Never validates an agricultural incumbent."""
    validate(value)
    d.require(re.fullmatch(r"[1-9][0-9]*", job or ""), "External job grammar.")
    rows = r.accounting(accounting, job, [])
    d.require(
        set(records) <= {"observation.json", "diagnostic.json", "supervision.json"},
        "Unallowlisted admission record.",
    )
    observed, supervisor = records.get("observation.json"), records.get("supervision.json")
    valid = (
        observed is not None
        and supervisor is not None
        and supervisor.get("admission_plan_sha256") == d.digest(value)
        and supervisor.get("job_id") == job
        and supervisor.get("status") == "complete"
        and supervisor.get("local_client_reaped") is True
        and type(supervisor.get("return_code")) is int
        and supervisor.get("return_code") == 0
        and supervisor.get("global_cleanup_proven") is False
        and supervisor.get("term_sent") is False
        and supervisor.get("kill_sent") is False
        and supervisor.get("error_kind") is None
        and all(x["state"] == "COMPLETED" and x["exit_code"] == "0:0" for x in rows.values())
        and "diagnostic.json" not in records
    )
    for record in records.values():
        d.require(all(record.get(k) is v for k, v in FLAGS.items()), "Admission permission drift.")
        d.require(record.get("admission_plan_sha256") == d.digest(value), "Record plan drift.")
    if valid:
        d.number(supervisor["elapsed_seconds"], "Observer elapsed")
        d.require(supervisor["elapsed_seconds"] <= 600, "Observer deadline exceeded.")
        env = observed["environment"]
        allocation = env["allocation"]
        fields = allocation["scheduler_fields"]
        fresh = r.academic.allocation(
            " ".join(k + "=" + v for k, v in fields.items()),
            job,
            allocation["uid"],
            {"cpus": 16, "memory_mib": 196608, "wall_seconds": 21600},
        )
        affinity = env["affinity"]
        d.require(
            fresh == allocation
            and type(allocation["uid"]) is int
            and allocation["uid"] > 0
            and isinstance(affinity, list)
            and 16 <= len(affinity) <= fresh["allocated_cpus"]
            and all(type(x) is int and x >= 0 for x in affinity)
            and affinity == sorted(set(affinity))
            and [x["cpu"] for x in env["topology"]] == affinity,
            "Allocation/affinity/topology observation drift.",
        )
        d.require(
            observed
            == {
                "admission_plan_sha256": d.digest(value),
                "job_id": job,
                "environment": env,
                "license": {"status": "accepted", "gurobi_version": [13, 0, 3]},
                "input_sha256": d.digest(value["p4_plan"]["input"]),
                "runtime_sha256": d.digest(value["p4_plan"]["runtime"]),
                "export_budget": EXPORT,
                "capability_model_variables": 2001,
                "agricultural_model_built": False,
                **FLAGS,
            }
            and env["runtime_sha256"] == observed["runtime_sha256"]
            and set(env["native_thread_environment"]) == set(r.ENVIRONMENT)
            and env["exclusive_node"] is False
            and env["production_isolation_certified"] is False,
            "Prerequisite observation binding drift.",
        )
    return {
        "schema_version": "s2-p4-admission-review-v1",
        "source_commit": value["p4_plan"]["preparation"]["source_commit"],
        "plan_sha256": d.digest(value),
        "job_id": job,
        "status": "prerequisites_observed_execution_closed"
        if valid
        else "negative_or_incomplete_evidence_preserved",
        "accounting": rows,
        "export_fit_established": False,
        "agricultural_solution_validated": False,
        "future_allocation_admitted": False,
        **FLAGS,
    }


def collect(target, expected, job, *, command=r.source.command):
    target, value = load(target, expected)
    d.require(
        p.read(target / "job.json") == {"job_id": job, "admission_plan_sha256": expected},
        "External job anchor.",
    )
    text = r.query(
        [
            "sacct",
            "-j",
            job,
            "--noheader",
            "--parsable2",
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
        ],
        command=command,
    )
    records = {
        name: p.read(target / name)
        for name in ("observation.json", "diagnostic.json", "supervision.json")
        if (target / name).exists()
    }
    result = review(value, job, records, text)  # Requires terminal accounting before publication.
    files = {
        "plan.json": c.encoded(value),
        "job.json": c.encoded(p.read(target / "job.json")),
        "records.json": c.encoded(records),
        "accounting.txt": text.encode(),
        "review.json": c.encoded(result),
    }
    d.require(sum(map(len, files.values())) + 10240 <= LIMIT, "Admission metadata envelope.")
    archive = target / "s2-p4-admission-evidence.tar.gz"
    artifacts = {name: r.academic.sha(raw) for name, raw in files.items()}
    if archive.exists():
        transfer = p.read(target / "transfer.json")
        checksum = transfer["sha256"]
        d.require(
            transfer == {"sha256": checksum, "plan_sha256": expected, "artifacts": artifacts},
            "Immutable admission record hashes drift.",
        )
        sidecar = archive.with_suffix(archive.suffix + ".sha256")
        d.require(
            p.safe(sidecar).read_bytes() == (checksum + "  " + archive.name + "\n").encode(),
            "Checksum sidecar drift.",
        )
        d.require(
            audit(archive, checksum, result["source_commit"], expected, job) == result,
            "Immutable admission collection drift.",
        )
    else:
        with (
            archive.open("xb") as output,
            tarfile.open(fileobj=output, mode="w:gz", format=tarfile.USTAR_FORMAT) as stream,
        ):
            for name in sorted(files):
                item = tarfile.TarInfo(name)
                item.size = len(files[name])
                item.mode = 0o600
                stream.addfile(item, io.BytesIO(files[name]))
        checksum = p.sha_file(archive)
        d.require(
            audit(archive, checksum, result["source_commit"], expected, job) == result,
            "Admission transfer replay.",
        )
        p.publish(
            target / "transfer.json",
            {"sha256": checksum, "plan_sha256": expected, "artifacts": artifacts},
        )
        with archive.with_suffix(archive.suffix + ".sha256").open("x", newline="\n") as sidecar:
            sidecar.write(checksum + "  " + archive.name + "\n")
    return {"review": result, "sha256": checksum, "download": str(archive), **FLAGS}


def audit(path, checksum, commit, expected, job):
    """Externally anchored, bounded metadata archive; no extraction or native call."""
    entry.require_hash(checksum)
    entry.require_hash(commit, 40)
    entry.require_hash(expected)
    d.require(
        p.safe(path).stat().st_size <= LIMIT and p.sha_file(path) == checksum, "Archive anchor."
    )
    with gzip.open(path, "rb") as source:
        raw = source.read(LIMIT + 1)
    d.require(len(raw) <= LIMIT, "Expanded metadata envelope.")
    files, end = {}, 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as source:
        for item in source:
            d.require(
                item.isfile()
                and item.name in FILES
                and item.name not in files
                and not item.pax_headers
                and item.size <= LIMIT,
                "Archive member scope.",
            )
            files[item.name] = source.extractfile(item).read()
            end = item.offset_data + ((item.size + 511) // 512) * 512
    d.require(set(files) == FILES and not any(raw[end:]), "Archive closure/trailing bytes.")
    value = validate(c.decode_json(files["plan.json"]))
    d.require(
        d.digest(value) == expected and value["p4_plan"]["preparation"]["source_commit"] == commit,
        "External plan/source anchors.",
    )
    d.require(
        c.decode_json(files["job.json"]) == {"job_id": job, "admission_plan_sha256": expected},
        "External archive job anchor.",
    )
    result = review(
        value, job, c.decode_json(files["records.json"]), files["accounting.txt"].decode()
    )
    d.require(result == c.decode_json(files["review.json"]), "Canonical admission replay drift.")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "check",
            "prepare",
            "observe",
            "collect",
            "wait",
            "audit",
            "start",
            "batch",
            "worker",
            "solve",
            "repeat",
        ),
    )
    parser.add_argument("--record-dir", type=Path)
    parser.add_argument("--source-sha")
    parser.add_argument("--p3-archive", type=Path)
    parser.add_argument("--reference-manifest", type=Path)
    parser.add_argument("--plan-sha256")
    parser.add_argument("--job-id")
    parser.add_argument("--one-observation-only", action="store_true")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--sha256")
    args = parser.parse_args(argv)
    if args.action in {"start", "batch", "worker", "solve", "repeat"}:
        entry.execute_h300()  # No source/input read, claim, scheduler or solver effects.
    if args.action == "check":
        d.budget_ledger()
        print("P4_ADMISSION_SOFTWARE=CHECKED; H300_AND_REPEATS_BLOCKED")
        return 0
    if args.action == "prepare":
        d.require(
            args.record_dir is not None
            and args.p3_archive is not None
            and args.reference_manifest is not None,
            "Explicit prerequisite paths required.",
        )
        result = prepare(args.record_dir, args.source_sha, args.p3_archive, args.reference_manifest)
    elif args.action == "observe":
        result = observe(
            args.record_dir, args.plan_sha256, args.job_id, acknowledged=args.one_observation_only
        )
    elif args.action == "audit":
        result = audit(args.archive, args.sha256, args.source_sha, args.plan_sha256, args.job_id)
    else:
        while True:
            try:
                result = collect(args.record_dir, args.plan_sha256, args.job_id)
                break
            except ValueError as error:
                if args.action != "wait" or str(error) not in {
                    "Accounting not terminal.",
                    "Missing/unexpected accounting row.",
                }:
                    raise
                print("ADMISSION_ACCOUNTING_PENDING; Ctrl-C safe; no submission", flush=True)
                time.sleep(20)
    print(c.encoded(result).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
