"""One immutable observation-only operational slot; downstream gates stay closed.

The PR97 observer and closed entries remain unchanged. This separately qualified
entry owns a distinct claim/source/plan/archive and cannot dispatch a worker.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import os
import re
import shlex
import sys
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mvp2_s2_allocation_diagnostic as d  # noqa: E402
from scripts import mvp2_s2_lifecycle_profile_driver as preserved  # noqa: E402
from scripts import mvp2_s2_lifecycle_release as release  # noqa: E402
from scripts import mvp2_s2_profile_observation as p  # noqa: E402

q, s, a = p.q, p.s, p.a
BASE = d.BASE
BASE_COMMIT = "adbb835b591558ffc39dd6127b22b86cc92fbf15"
CLAIM = ".mvp2-s2-profile-operational-v1"
ENTRY = "scripts/mvp2_s2_profile_operational.py"
TOOLS = {"sbatch", "scontrol", "sacct"}
FILES = {"plan.json", "job.json", "raw-records.json", "accounting.txt", "review.json"}
RAW_FILES = {
    "observation.json",
    "batch-failure.json",
    "submission-result.json",
    "batch.sh",
    "slurm.out",
    "slurm.err",
}
ARCHIVE = "s2-profile-operational-evidence.tar.gz"
LIMIT = 32 * 1024**2
SCOPE = {
    "purpose": "read_only_prerequisite_observation",
    "slots": 1,
    "cpus": 2,
    "memory_mib": 2048,
    "scheduler_seconds": 720,
    "capture_seconds": 90,
    "worker_route": "absent",
    "automatic_follow_on": "forbidden",
}


def claim_path():
    return d.safe(BASE / CLAIM)


# Same byte formats/allowlists, not a call into the old claim or old review.
sealed_path = preserved.sealed_path
raw_record = preserved.raw_record
read_record = preserved.read_record
validate_records = preserved.validate_records
pack = preserved.pack
validate_job = preserved.validate_job


def validate_plan(plan, commit, expected=None):
    q._keys(
        plan,
        {
            "schema_version",
            "operational_scope",
            "source_commit",
            "base_commit",
            "checkout",
            "files",
            "python",
            "python_sha256",
            "tools",
            "tools_sha256",
            "uid",
            *p.FLAGS,
        },
    )
    q._hash(commit, 40)
    s.require(
        plan["schema_version"] == "s2-profile-operational-plan-v1"
        and s.digest(plan["operational_scope"]) == s.digest(SCOPE)
        and plan["source_commit"] == commit
        and plan["base_commit"] == BASE_COMMIT
        and type(plan["uid"]) is int
        and 0 < plan["uid"] < 2**32
        and all(plan[k] is False for k in p.FLAGS),
        "Plan binding/flags.",
    )
    root = sealed_path(plan["checkout"])
    s.require(
        root.name == "source"
        and root.parent.parent == PurePosixPath(BASE.as_posix())
        and re.fullmatch(r"s2-profile-operational-driver-[A-Za-z0-9]{8}", root.parent.name),
        "Reviewed source location required.",
    )
    sealed_path(plan["python"])
    q._hash(plan["python_sha256"])
    q._keys(plan["tools"], TOOLS)
    q._keys(plan["tools_sha256"], TOOLS)
    for name in TOOLS:
        sealed_path(plan["tools"][name])
        q._hash(plan["tools_sha256"][name])
    s.require(
        type(plan["files"]) is dict
        and 1 <= len(plan["files"]) <= 1024
        and {
            ENTRY,
            "scripts/mvp2_s2_profile_observation.py",
            "scripts/mvp2_s2_profile_diagnostics.py",
        }
        <= plan["files"].keys(),
        "Profile source closure.",
    )
    for name, sha in plan["files"].items():
        s.require(a.safe_repo_name(name), "Source path grammar.")
        q._hash(sha)
    sha = d.digest(d.encode(plan))
    s.require(expected is None or expected == sha, "Plan digest drift.")
    return sha


def script(plan):
    argv = [
        plan["python"],
        "-B",
        "-I",
        plan["checkout"] + "/" + ENTRY,
        "batch",
        "--source-sha",
        plan["source_commit"],
        "--plan-sha",
        validate_plan(plan, plan["source_commit"]),
    ]
    return ("#!/bin/sh\nexec " + shlex.join(argv) + "\n").encode("ascii")


def submit_argv(plan):
    root = claim_path()
    return [
        plan["tools"]["sbatch"],
        "--parsable",
        "--job-name=mvp2-s2-profile-operational",
        "--account=sxdsouza",
        "--partition=intel-256",
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=2",
        "--mem=2048M",
        "--time=00:12:00",
        "--no-requeue",
        "--export=NONE",
        "--chdir=" + str(root),
        "--output=" + str(root / "slurm-%j.out"),
        "--error=" + str(root / "slurm-%j.err"),
        str(root / "batch.sh"),
    ]


def intent(plan):
    return {
        "plan_sha256": validate_plan(plan, plan["source_commit"]),
        "script_sha256": d.digest(script(plan)),
        "argv_sha256": d.digest(d.encode(submit_argv(plan))),
        **p.FLAGS,
    }


def runtime(plan, role):
    s.require(role in {"login", "batch", "collect"}, "Role required.")
    d.verify_tree(Path(plan["checkout"]), plan["files"])
    s.require(
        Path(sys.executable).resolve().as_posix() == plan["python"]
        and a.sha_file(plan["python"]) == plan["python_sha256"],
        "Python identity drift.",
    )
    for name in TOOLS if role == "login" else {"scontrol"} if role == "batch" else {"sacct"}:
        s.require(a.sha_file(plan["tools"][name]) == plan["tools_sha256"][name], "Role tool drift.")


def load_plan(commit, expected=None):
    plan = d.load(claim_path() / "plan.json", 1024**2)
    sha = validate_plan(plan, commit, expected)
    s.require(Path(plan["checkout"]) / ENTRY == Path(__file__).resolve(), "Original source only.")
    s.require(
        d.load(claim_path() / "submission-intent.json") == intent(plan)
        and d.read(claim_path() / "batch.sh", 8192) == script(plan),
        "Submission intent/script drift.",
    )
    return plan, sha


def load_job(plan, sha):
    job = validate_job(d.load(claim_path() / "job.json"), plan, sha)
    receipt = d.load(claim_path() / "submission-result.json")
    q._keys(receipt, {"meta", "acknowledgement_base64"})
    raw = base64.b64decode(receipt["acknowledgement_base64"], validate=True)
    s.require(
        p.query_text(p.query_record(receipt["meta"], raw)) == job["job_id"] + "\n",
        "Preserved acknowledgement/job drift.",
    )
    return job


def start(commit):
    d.host()
    root = claim_path()
    if root.exists():
        return collect(commit)  # Never repair/reset/discover another claim.
    checkout = Path(__file__).resolve().parents[1]
    git = d.tool("git")
    d.checked([git, "-C", str(checkout), "merge-base", "--is-ancestor", BASE_COMMIT, commit])
    d.checked([git, "-C", str(checkout), "merge-base", "--is-ancestor", commit, "origin/develop"])
    plan = {
        "schema_version": "s2-profile-operational-plan-v1",
        "operational_scope": dict(SCOPE),
        "source_commit": commit,
        "base_commit": BASE_COMMIT,
        "checkout": checkout.as_posix(),
        "files": d.source_files(checkout, commit),
        "python": Path(sys.executable).resolve().as_posix(),
        "python_sha256": a.sha_file(Path(sys.executable).resolve()),
        "tools": {name: d.tool(name) for name in TOOLS},
        "uid": os.getuid(),
        **p.FLAGS,
    }
    plan["tools_sha256"] = {name: a.sha_file(path) for name, path in plan["tools"].items()}
    sha = validate_plan(plan, commit)
    runtime(plan, "login")
    root.mkdir(
        mode=0o700, exist_ok=False
    )  # Reservation consumes the slot, even after interruption.
    release.sync_directory(root.parent)
    d.write_new(root / "plan.json", plan)
    with (root / "batch.sh").open("xb") as stream:
        stream.write(script(plan))
        stream.flush()
        os.fsync(stream.fileno())
    d.write_new(root / "submission-intent.json", intent(plan))
    runtime(plan, "login")
    d.write_new(root / "submission-called.json", {"plan_sha256": sha, **p.FLAGS})
    try:
        meta, raw = d.command(submit_argv(plan), timeout=30)
        d.write_new(
            root / "submission-result.json",
            {"meta": meta, "acknowledgement_base64": base64.b64encode(raw).decode("ascii")},
        )
        s.require(
            meta["status"] == "complete"
            and meta["returncode"] == 0
            and re.fullmatch(rb"[1-9][0-9]{0,9}\n", raw),
            "Unknown submission; preserve, never retry or guess job.",
        )
        job = {
            "job_id": raw[:-1].decode("ascii"),
            "source_commit": commit,
            "plan_sha256": sha,
            "uid": plan["uid"],
        }
        validate_job(job, plan, sha)
        d.write_new(root / "job.json", job)
    except (Exception, KeyboardInterrupt):
        d.write_new(
            root / "submission-unknown.json", {"status": "unknown_effect_no_retry", **p.FLAGS}
        )
        print("OBSERVATION_STATUS=unknown_submission_preserved_no_retry")
        return 2
    print("OBSERVATION_STATUS=submitted_observation_only")
    print("JOB_ID=" + job["job_id"])
    print("PLAN_SHA256=" + sha)
    print("PRESERVE_CLAIM=" + str(root))
    return 0


def batch(commit, expected):
    d.host()
    root, phase = claim_path(), "plan"
    try:
        plan, sha = load_plan(commit, expected)
        deadline = time.monotonic() + 30
        while not (root / "job.json").exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        job = load_job(plan, sha)
        s.require(
            os.environ.get("SLURM_JOB_ID") == job["job_id"] and os.getuid() == job["uid"],
            "Compute allocation/UID drift.",
        )
        phase = "source_runtime"
        runtime(plan, "batch")  # No Git/sbatch lookup on compute.
        phase = "prerequisite_observation"

        def query(name):
            argv = (
                [plan["tools"]["scontrol"], "-o", "show", "job", job["job_id"]]
                if name == "allocation"
                else [
                    plan["tools"]["scontrol"],
                    "listpids",
                    job["job_id"] + "." + a.BATCH_QUERY_STEP,
                ]
            )
            meta, raw = d.command(argv, timeout=1)
            return p.query_record(meta, raw)

        observation = p.observe(job, p.KernelReader(), query)
        d.write_new(root / "observation.json", observation)
        result = p.review(observation, job)
        print("OBSERVATION_STATUS=" + result["status"])
        print("BLOCKERS=" + ",".join(result["blockers"]))
        return 0  # Completion means the observation was preserved, not compatibility.
    except (Exception, KeyboardInterrupt):
        d.write_new(
            root / "batch-failure.json",
            {
                "schema_version": "s2-profile-operational-failure-v1",
                "source_commit": commit,
                "plan_sha256": expected,
                "phase": phase,
                "error_kind": "invalid_or_unavailable",
                **p.FLAGS,
            },
        )
        print("OBSERVATION_STATUS=observation_incomplete_preserved")
        return 2


def review(plan, job, records, accounting_text, expected_commit, expected_plan_sha, expected_job):
    sha = validate_plan(plan, expected_commit, expected_plan_sha)
    validate_job(job, plan, sha)
    s.require(job["job_id"] == expected_job, "External job anchor drift.")
    rows, done = d.accounting(accounting_text.encode("ascii"), expected_job)
    s.require(done, "Root/batch/extern terminal accounting required; no numeric worker expected.")
    decoded = validate_records(records)
    disposition, outcome = "missing_observation_preserved", None
    if "observation.json" in decoded:
        try:
            outcome = p.review(d.decode(decoded["observation.json"]), job)
            disposition = outcome["status"]
            if disposition == "prerequisites_observed_not_admitted" and (
                "batch-failure.json" in decoded
                or any(
                    row["state"] != "COMPLETED" or row["exit_code"] != "0:0"
                    for row in rows.values()
                )
            ):
                disposition = "partial_observation_preserved"
            elif (
                disposition == "prerequisites_observed_not_admitted"
                and outcome["observation_provenance"] == "software_fixture"
            ):
                disposition = "software_fixture_preserved_not_admitted"
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, UnicodeError):
            disposition = "rejected_observation_preserved"
    return {
        "schema_version": "s2-profile-operational-terminal-review-v1",
        "source_commit": expected_commit,
        "job_id": expected_job,
        "plan_sha256": sha,
        "disposition": disposition,
        "profile": outcome,
        "accounting_sha256": hashlib.sha256(accounting_text.encode()).hexdigest(),
        "raw_record_sha256": {k: v.get("sha256") for k, v in records.items()},
        **p.FLAGS,
    }


def audit(path, checksum, commit, plan_sha, job):
    q._hash(checksum)
    raw = a._file(path, LIMIT + 1024**2)
    s.require(hashlib.sha256(raw).hexdigest() == checksum, "Archive checksum drift.")
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as zipped:
        unpacked = zipped.read(LIMIT + 1024**2 + 1)
    s.require(len(unpacked) <= LIMIT + 1024**2, "Decompression bound.")
    records, end = {}, 0
    with tarfile.open(fileobj=io.BytesIO(unpacked), mode="r:") as archive:
        for member in archive:
            s.require(
                member.name in FILES
                and member.name not in records
                and member.isfile()
                and not member.pax_headers
                and 0 < member.size <= LIMIT,
                "Archive member grammar.",
            )
            records[member.name] = archive.extractfile(member).read()
            end = member.offset_data + ((member.size + 511) // 512) * 512
    s.require(records.keys() == FILES and not any(unpacked[end:]), "Missing/trailing archive data.")
    result = review(
        d.decode(records["plan.json"]),
        d.decode(records["job.json"]),
        d.decode(records["raw-records.json"]),
        records["accounting.txt"].decode("ascii"),
        commit,
        plan_sha,
        job,
    )
    s.require(result == d.decode(records["review.json"]), "Nonrecomputable terminal review.")
    return result


def status(commit):
    d.host()
    plan, sha = load_plan(commit)
    root = claim_path()
    if not (root / "job.json").exists() or (root / "submission-unknown.json").exists():
        print("OBSERVATION_STATUS=unacknowledged_preserve_no_retry")
        return plan, sha, None, None
    job = load_job(plan, sha)
    runtime(plan, "collect")
    meta, raw = d.command(
        [
            plan["tools"]["sacct"],
            "--noheader",
            "--parsable2",
            "--jobs=" + job["job_id"],
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
        ],
        timeout=5,
    )
    s.require(
        meta["status"] == "complete" and meta["returncode"] == 0,
        "Accounting query failed; collect later, never resubmit.",
    )
    _rows, done = d.accounting(raw, job["job_id"])
    print("JOB_ID=" + job["job_id"])
    print(
        "OBSERVATION_STATUS="
        + ("terminal_accounting_observed" if done else "nonterminal_or_accounting_pending")
    )
    return plan, sha, job, raw if done else None


def collect(commit):
    d.host()
    root = claim_path()
    plan, sha = load_plan(commit)
    cached = root / "collection.json"
    if cached.exists():
        saved = d.load(cached)
        q._keys(saved, {"archive", "sha256", "job_id", "plan_sha256"})
        path = d.safe(saved["archive"])
        s.require(
            path.name == ARCHIVE
            and path.parent.parent == root
            and re.fullmatch(r"collection-[a-z0-9_]{8}", path.parent.name)
            and saved["plan_sha256"] == sha,
            "Cached archive location/binding.",
        )
        job = load_job(plan, sha)
        s.require(saved["job_id"] == job["job_id"], "Cached job drift.")
        s.require(
            d.read(Path(str(path) + ".sha256"))
            == (saved["sha256"] + "  " + ARCHIVE + "\n").encode("ascii"),
            "Cached sidecar drift.",
        )
        result = audit(path, saved["sha256"], commit, sha, job["job_id"])
    else:
        plan, sha, job, raw = status(commit)
        if job is None:
            return 2
        if raw is None:
            return 0
        records = {}
        for name in sorted(RAW_FILES):
            actual = (
                "slurm-" + job["job_id"] + "." + name[6:] if name.startswith("slurm.") else name
            )
            path = root / actual
            d.safe(path)
            if path.exists():
                records[name] = read_record(path, p.LIMIT if name == "observation.json" else 65536)
        result = review(plan, job, records, raw.decode("ascii"), commit, sha, job["job_id"])
        payloads = {
            "plan.json": d.encode(plan),
            "job.json": d.encode(job),
            "raw-records.json": d.encode(records),
            "accounting.txt": raw,
            "review.json": d.encode(result),
        }
        s.require(sum(map(len, payloads.values())) <= LIMIT, "Transfer byte bound.")
        directory = Path(tempfile.mkdtemp(prefix="collection-", dir=root))
        release.sync_directory(root)
        path = directory / ARCHIVE
        pack(path, payloads)
        checksum = a.sha_file(path)
        s.require(
            audit(path, checksum, commit, sha, job["job_id"]) == result, "Archive round-trip drift."
        )
        with Path(str(path) + ".sha256").open("x", encoding="ascii", newline="\n") as stream:
            stream.write(checksum + "  " + ARCHIVE + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        release.sync_directory(directory)
        saved = {
            "archive": str(path),
            "sha256": checksum,
            "job_id": job["job_id"],
            "plan_sha256": sha,
        }
        d.write_new(cached, saved)
    print("OBSERVATION_STATUS=" + result["disposition"])
    print("JOB_ID=" + result["job_id"])
    print("PLAN_SHA256=" + result["plan_sha256"])
    profile = result["profile"]
    if profile is not None:
        print("HOST_LIMIT_STATUS=" + profile["host_limit_status"])
        print("BLOCKERS=" + ",".join(profile["blockers"]))
    print("SHA256=" + saved["sha256"])
    print("DOWNLOAD=" + saved["archive"])
    print("TRANSFER_CHECKSUM=" + saved["archive"] + ".sha256")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "batch", "status", "collect", "wait", "audit"))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--plan-sha")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--job")
    args = parser.parse_args()
    q._hash(args.source_sha, 40)
    try:
        if args.action == "audit":
            q._hash(args.plan_sha)
            print(
                d.encode(
                    audit(args.archive, args.sha256, args.source_sha, args.plan_sha, args.job)
                ).decode(),
                end="",
            )
            return 0
        if args.action == "batch":
            q._hash(args.plan_sha)
            return batch(args.source_sha, args.plan_sha)
        if args.action == "status":
            status(args.source_sha)
            return 0
        if args.action == "wait":
            while True:
                _plan, _sha, job, raw = status(args.source_sha)
                if job is None:
                    return 2
                if raw is not None:
                    return collect(args.source_sha)
                time.sleep(20)
        return {"start": start, "collect": collect}[args.action](args.source_sha)
    finally:
        print("NO_NORMAL_ADVERSE_NATIVE_MINIATURE_H300_OR_REPEAT_ADMITTED")


if __name__ == "__main__":
    raise SystemExit(main())
