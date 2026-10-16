"""One human P4 prerequisite observation; never agricultural execution admission."""

from __future__ import annotations

import argparse
import gzip
import io
import os
import re
import shlex
import sys
import tarfile
import time
from pathlib import Path

from scripts import mvp2_s2_p4_admission as a

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
CLAIM = ".mvp2-s2-p4-observation-v1"
PARENT = "279a081a8d100c787b65ca620d2b69ef36e88342"
REFERENCE = Path(
    "/home/vrrcelestino/model-agrologistic/data/results/hpc/"
    "nine-connectivity-corrected-20260914T180739Z/campaign.yaml"
)
MEMBERS = {"plan.json", "driver.json", "records.json", "accounting.txt", "review.json"}
LIMIT = a.LIMIT


def directory(path):
    path = a.p.safe(path)
    a.d.require(path == BASE / CLAIM, "Dedicated observational claim only.")
    return path


def load(path, commit):
    path = directory(path)
    a.entry.require_hash(commit, 40)
    plan = a.validate(a.p.read(BASE / a.CLAIM / "plan.json"))
    receipt = a.p.read(path / "plan.json")
    expected = {
        "schema_version": "s2-p4-observation-driver-v1",
        "source_commit": commit,
        "parent_merge": PARENT,
        "admission_plan_sha256": a.d.digest(plan),
        "allocation": a.d.policy()["allocation"],
        **a.FLAGS,
    }
    a.d.require(a.c.encoded(receipt) == a.c.encoded(expected), "Observation driver drift.")
    a.d.require(plan["p4_plan"]["preparation"]["source_commit"] == commit, "Source binding.")
    return path, receipt, plan


def dispatch(root, target, commit):
    # Fixed trusted Python; no user-controlled code, shell interpolation or worker route.
    code = (
        "import sys;sys.dont_write_bytecode=True;sys.path.insert(0,"
        + repr(str(root))
        + ");from scripts.mvp2_s2_p4_observation import batch;raise SystemExit(batch("
        + repr(str(target))
        + ","
        + repr(commit)
        + "))"
    )
    return [sys.executable, "-B", "-I", "-c", code]


def start(commit, *, acknowledged=False, prepare=a.prepare, command=a.r.source.command):
    a.d.require(acknowledged is True, "One reviewed observation-only slot required.")
    a.entry.require_hash(commit, 40)
    target = directory(BASE / CLAIM)
    if target.exists():
        load(target, commit)
        if (target / "job.json").exists():
            return {
                "status": "existing_job_collect_only",
                **a.p.read(target / "job.json"),
                **a.FLAGS,
            }
        raise ValueError("Consumed slot without job acknowledgement; preserve, never resubmit.")
    a.d.require(not (BASE / a.CLAIM).exists(), "Existing prerequisite record; never reuse.")
    # No claim or sbatch until exact P3, runtime, source and fresh input checks pass.
    prepare(
        BASE / a.CLAIM,
        commit,
        BASE / ".mvp2-s2-academic-v2-native_miniature/s2-academic-evidence.tar.gz",
        REFERENCE,
    )
    plan = a.validate(a.p.read(BASE / a.CLAIM / "plan.json"))
    target.mkdir()
    receipt = {
        "schema_version": "s2-p4-observation-driver-v1",
        "source_commit": commit,
        "parent_merge": PARENT,
        "admission_plan_sha256": a.d.digest(plan),
        "allocation": a.d.policy()["allocation"],
        **a.FLAGS,
    }
    a.p.publish(target / "plan.json", receipt)
    a.p.publish(target / "origin.json", {"root": str(ROOT), "python": sys.executable})
    with (target / "batch.sh").open("x", newline="\n") as stream:
        stream.write("#!/bin/sh\nexec " + shlex.join(dispatch(ROOT, target, commit)) + "\n")
    argv = [
        "sbatch",
        "--parsable",
        "--partition=intel-256",
        "--account=sxdsouza",
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=16",
        "--mem=196608M",
        "--time=06:00:00",
        "--no-requeue",
        "--export=NONE",
        "--job-name=s2-p4-observe",
        "--chdir=" + str(ROOT),
        "--output=" + str(target / "slurm.out"),
        "--error=" + str(target / "slurm.err"),
        str(target / "batch.sh"),
    ]
    a.p.publish(
        target / "submission-intent.json",
        {"driver_plan_sha256": a.d.digest(receipt), "argv_sha256": a.d.digest(argv)},
    )
    meta, raw = command(argv, timeout=30, limit=1024)
    a.p.publish(target / "submission-call.json", meta)
    a.d.require(
        meta["status"] == "complete"
        and meta["returncode"] == 0
        and re.fullmatch(rb"[1-9][0-9]*(?:;[A-Za-z0-9_-]+)?\n?", raw),
        "Unknown submission acknowledgement; slot consumed, never retry.",
    )
    job = raw.decode().strip().split(";")[0]
    job_receipt = {"job_id": job, "driver_plan_sha256": a.d.digest(receipt)}
    a.p.publish(target / "job.json", job_receipt)
    return {"status": "submitted_prerequisite_observation_only", **job_receipt, **a.FLAGS}


def batch(path, commit, *, observer=a.observe, verify=a.r.source.verify_tree):
    """No Git, sbatch or agricultural worker on compute; preserve pre-observer failures."""
    target, receipt, plan = load(path, commit)
    job = os.environ.get("SLURM_JOB_ID", "")
    a.d.require(re.fullmatch(r"[1-9][0-9]*", job), "Compute allocation required.")
    # The submit acknowledgement may still be in flight on login. Bind job via live
    # allocation; login collector subsequently requires its separate exact receipt.
    with (target / "batch-slot").open("x"):
        pass
    phase = "origin_source"
    try:
        origin = a.p.read(target / "origin.json")
        a.d.require(origin == {"root": str(ROOT), "python": sys.executable}, "Batch origin.")
        verify(ROOT, plan["p4_plan"]["files"])
        for key in a.r.ENVIRONMENT:
            os.environ[key] = "1"
        phase = "bounded_prerequisite_observer"
        result = observer(BASE / a.CLAIM, a.d.digest(plan), job, acknowledged=True)
        good = result.get("status") == "complete" and result.get("local_client_reaped") is True
        outcome = {
            "status": "observation_returned" if good else "observation_failed",
            "phase": "complete",
            "error_kind": None,
        }
    except BaseException as error:
        good = False
        outcome = {
            "status": "blocked_before_or_during_observation",
            "phase": phase,
            "error_kind": type(error).__name__,
        }
    a.p.publish(
        target / "batch-outcome.json",
        {**outcome, "job_id": job, "driver_plan_sha256": a.d.digest(receipt), **a.FLAGS},
    )
    return 0 if good else 2


def status(commit, *, command=a.r.source.command):
    target, receipt, _ = load(BASE / CLAIM, commit)
    job = a.p.read(target / "job.json")
    a.d.require(job["driver_plan_sha256"] == a.d.digest(receipt), "Driver job drift.")
    text = a.r.query(
        [
            "sacct",
            "-j",
            job["job_id"],
            "--noheader",
            "--parsable2",
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
        ],
        command=command,
    )
    return job, text


def review(plan, driver, records, text):
    """Replay metadata only, including an empty worker record after early batch failure."""
    a.d.require(set(driver) == {"plan", "job", "batch"}, "Driver evidence schema.")
    summary = driver["plan"]
    source = plan["p4_plan"]["preparation"]["source_commit"]
    expected = {
        "schema_version": "s2-p4-observation-driver-v1",
        "source_commit": source,
        "parent_merge": PARENT,
        "admission_plan_sha256": a.d.digest(plan),
        "allocation": a.d.policy()["allocation"],
        **a.FLAGS,
    }
    a.d.require(a.c.encoded(summary) == a.c.encoded(expected), "Portable driver plan drift.")
    job = driver["job"]["job_id"]
    a.d.require(
        driver["job"] == {"job_id": job, "driver_plan_sha256": a.d.digest(summary)},
        "Portable driver job drift.",
    )
    inner = a.review(plan, job, records, text)
    outcome = driver["batch"]
    if outcome is not None:
        a.d.require(
            set(outcome)
            == {"status", "phase", "error_kind", "job_id", "driver_plan_sha256", *a.FLAGS},
            "Batch record schema.",
        )
        a.d.require(
            outcome["job_id"] == job
            and outcome["driver_plan_sha256"] == a.d.digest(summary)
            and all(outcome[k] is v for k, v in a.FLAGS.items()),
            "Batch binding drift.",
        )
    good = (
        inner["status"] == "prerequisites_observed_execution_closed"
        and outcome is not None
        and outcome["status"] == "observation_returned"
        and outcome["phase"] == "complete"
        and outcome["error_kind"] is None
    )
    return {
        "schema_version": "s2-p4-observation-review-v1",
        "source_commit": source,
        "driver_plan_sha256": a.d.digest(summary),
        "admission_plan_sha256": a.d.digest(plan),
        "job_id": job,
        "status": "prerequisites_observed_execution_closed"
        if good
        else "negative_or_incomplete_evidence_preserved",
        "prerequisite_review": inner,
        "batch_outcome": outcome,
        "future_allocation_admitted": False,
        **a.FLAGS,
    }


def audit(path, checksum, commit, plan_sha, job):
    a.entry.require_hash(checksum)
    a.entry.require_hash(commit, 40)
    a.entry.require_hash(plan_sha)
    a.d.require(
        a.p.safe(path).stat().st_size <= LIMIT and a.p.sha_file(path) == checksum, "Archive anchor."
    )
    with gzip.open(path, "rb") as stream:
        raw = stream.read(LIMIT + 1)
    a.d.require(len(raw) <= LIMIT, "Expanded observation envelope.")
    files, end = {}, 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as stream:
        for item in stream:
            a.d.require(
                item.isfile()
                and item.name in MEMBERS
                and item.name not in files
                and not item.pax_headers
                and item.size <= LIMIT,
                "Member scope.",
            )
            files[item.name] = stream.extractfile(item).read()
            end = item.offset_data + ((item.size + 511) // 512) * 512
    a.d.require(set(files) == MEMBERS and not any(raw[end:]), "Archive closure.")
    plan = a.validate(a.c.decode_json(files["plan.json"]))
    driver = a.c.decode_json(files["driver.json"])
    a.d.require(
        driver["plan"]["source_commit"] == commit
        and a.d.digest(driver["plan"]) == plan_sha
        and driver["job"]["job_id"] == job,
        "External source/plan/job anchors.",
    )
    result = review(
        plan, driver, a.c.decode_json(files["records.json"]), files["accounting.txt"].decode()
    )
    a.d.require(result == a.c.decode_json(files["review.json"]), "Canonical replay drift.")
    return result


def collect(commit, *, command=a.r.source.command):
    target, receipt, plan = load(BASE / CLAIM, commit)
    job, text = status(commit, command=command)
    record = BASE / a.CLAIM
    records = {
        name: a.p.read(record / name)
        for name in ("observation.json", "diagnostic.json", "supervision.json")
        if (record / name).exists()
    }
    if (record / "job.json").exists():
        a.d.require(
            a.p.read(record / "job.json")
            == {"job_id": job["job_id"], "admission_plan_sha256": a.d.digest(plan)},
            "Observer/driver job mismatch.",
        )
    else:
        a.d.require(not records, "Unbound observer records.")
    driver = {
        "plan": receipt,
        "job": job,
        "batch": a.p.read(target / "batch-outcome.json")
        if (target / "batch-outcome.json").exists()
        else None,
    }
    result = review(plan, driver, records, text)  # Terminal accounting required, even negative.
    files = {
        "plan.json": a.c.encoded(plan),
        "driver.json": a.c.encoded(driver),
        "records.json": a.c.encoded(records),
        "accounting.txt": text.encode(),
        "review.json": a.c.encoded(result),
    }
    a.d.require(sum(map(len, files.values())) + 10240 <= LIMIT, "Observation metadata bound.")
    archive = target / "s2-p4-observation-evidence.tar.gz"
    hashes = {name: a.r.academic.sha(raw) for name, raw in files.items()}
    if archive.exists():
        transfer = a.p.read(target / "transfer.json")
        checksum = transfer["sha256"]
        a.d.require(transfer == {"sha256": checksum, "artifacts": hashes}, "Cached record drift.")
        a.d.require(
            a.p.safe(archive.with_suffix(".gz.sha256")).read_bytes()
            == (checksum + "  " + archive.name + "\n").encode(),
            "Checksum sidecar drift.",
        )
    else:
        with (
            archive.open("xb") as output,
            tarfile.open(fileobj=output, mode="w:gz", format=tarfile.USTAR_FORMAT) as stream,
        ):
            for name, raw in sorted(files.items()):
                item = tarfile.TarInfo(name)
                item.size, item.mode = len(raw), 0o600
                stream.addfile(item, io.BytesIO(raw))
        checksum = a.p.sha_file(archive)
        a.d.require(
            audit(archive, checksum, commit, a.d.digest(receipt), job["job_id"]) == result,
            "Transfer replay.",
        )
        a.p.publish(target / "transfer.json", {"sha256": checksum, "artifacts": hashes})
        with archive.with_suffix(".gz.sha256").open("x", newline="\n") as stream:
            stream.write(checksum + "  " + archive.name + "\n")
    a.d.require(
        audit(archive, checksum, commit, a.d.digest(receipt), job["job_id"]) == result,
        "Immutable transfer replay.",
    )
    return {
        "status": result["status"],
        "job_id": job["job_id"],
        "driver_plan_sha256": a.d.digest(receipt),
        "sha256": checksum,
        "download": str(archive),
        "transfer_checksum": str(archive) + ".sha256",
        **a.FLAGS,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "start",
            "status",
            "wait",
            "collect",
            "audit",
            "solve",
            "worker",
            "repeat",
            "h300",
        ),
    )
    parser.add_argument("source_sha")
    parser.add_argument("--one-reviewed-observation-only", action="store_true")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--plan-sha256")
    parser.add_argument("--job-id")
    args = parser.parse_args(argv)
    if args.action in {"solve", "worker", "repeat", "h300"}:
        a.entry.execute_h300()
    if args.action == "start":
        a.d.require(sys.platform == "linux" and os.getuid() > 0, "Non-root Linux login required.")
        result = start(args.source_sha, acknowledged=args.one_reviewed_observation_only)
    elif args.action == "status":
        job, text = status(args.source_sha)
        result = {"status": "accounting_observation_only", **job, "accounting": text, **a.FLAGS}
    elif args.action == "audit":
        result = audit(args.archive, args.sha256, args.source_sha, args.plan_sha256, args.job_id)
    else:
        while True:
            try:
                result = collect(args.source_sha)
                break
            except ValueError as error:
                if args.action != "wait" or str(error) not in {
                    "Accounting not terminal.",
                    "Missing/unexpected accounting row.",
                }:
                    raise
                print("ACCOUNTING_PENDING; Ctrl-C safe; no resubmission", flush=True)
                time.sleep(20)
    print(a.c.encoded(result).decode(), end="")
    print("PRESERVE_CLAIM=" + str(BASE / CLAIM))
    if "job_id" in result:
        print("JOB_ID=" + result["job_id"])
    if "download" in result:
        print("SHA256=" + result["sha256"])
        print("PLAN_SHA256=" + result["driver_plan_sha256"])
        print("DOWNLOAD=" + result["download"])
        print("TRANSFER_CHECKSUM=" + result["transfer_checksum"])
    print("NO_H300_REPEAT_OR_AUTOMATIC_FOLLOW_ON_ADMITTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
