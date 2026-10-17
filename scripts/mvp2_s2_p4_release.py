"""One explicitly reviewed P4 academic block; no repeat or automatic follow-on.

The legacy plans/certificates remain closed and byte-identical. This separate
release binds them to a new source cohort and the previously unused P4 claim.
Portable replay checks reported evidence, not fresh private-input residuals.
"""

from __future__ import annotations

import argparse
import gzip
import os
import re
import shlex
import sys
import tarfile
import tempfile
import time
from pathlib import Path

from scripts import mvp2_s2_p4_observation as o

r, p, d, c = o.a.r, o.a.p, o.a.d, o.a.c
ROOT = Path(__file__).resolve().parents[1]
BASE = o.BASE
REFERENCE = o.REFERENCE
PARENT = "d70816fdd6c3d99ef05711731a9dda17cd5210dd"
OBS = {
    "source": "7ff70904d6c690ced0c9e035e003da3d6ce6e4a6",
    "job": "2213305",
    "archive": "4d52bdd46775f6b7ca1393e6387e125ddd199c59ed9bc77c9dcc2217af32546e",
    "plan": "f177d17c0510c4b18993bbc409a33415744fcdc3f9570d0843ddc0df462b73c2",
}
MEMBERS = {
    "release.json",
    "predecessor.tar.gz",
    "native.tar.gz",
    "native-transfer.json",
    "review.json",
    "driver.json",
}
ARCHIVE = "s2-p4-release-evidence.tar.gz"
FLAGS = {
    "repeats_admitted": False,
    "automatic_follow_on_allowed": False,
    "scientific_configuration_selected": False,
    "s2_closed": False,
    "production_isolation_certified": False,
}


def predecessor(path):
    result = o.audit(path, OBS["archive"], OBS["source"], OBS["plan"], OBS["job"])
    d.require(result["status"] == "prerequisites_observed_execution_closed", "Predecessor blocked.")
    with tarfile.open(path, "r:gz") as stream:
        return c.decode_json(stream.extractfile("plan.json").read())["p4_plan"]


def release(plan):
    r._validate(plan)
    return {
        "schema_version": "s2-p4-operational-release-v1",
        "source_commit": plan["preparation"]["source_commit"],
        "parent_merge": PARENT,
        "native_plan_sha256": d.digest(plan),
        "predecessor": OBS,
        "scope": "one_cold_serial_diagnostic_block",
        "order": list(d.ORDER),
        "policy_sha256": d.digest(d.policy()),
        "export_limit_bytes": p.LIMIT,
        **FLAGS,
    }


def directory():
    return p.safe(BASE / r.CLAIM)


def load(commit):
    r.entry.require_hash(commit, 40)
    target = directory()
    plan = r._validate(p.read(target / "plan.json"))
    sealed = p.read(target / "release.json")
    d.require(
        sealed == release(plan) and sealed["source_commit"] == commit, "Release/source drift."
    )
    return target, plan, sealed


def dispatch(target, commit):
    code = (
        "import sys;sys.dont_write_bytecode=True;sys.path.insert(0,"
        + repr(str(ROOT))
        + ");from scripts.mvp2_s2_p4_release import batch;raise SystemExit(batch("
        + repr(str(target))
        + ","
        + repr(commit)
        + "))"
    )
    return [sys.executable, "-B", "-I", "-c", code]


def start(commit, *, acknowledged=False, planner=r._plan, command=r.source.command):
    d.require(acknowledged is True, "One reviewed h300 block acknowledgement required.")
    r.entry.require_hash(commit, 40)
    target = directory()
    if target.exists():
        _, plan, sealed = load(commit)
        d.require(
            (target / "job.json").exists(), "Consumed slot without acknowledgement; no retry."
        )
        job = job_record(target, plan)
        return {
            "status": "existing_job_collect_only",
            **job,
            "release_sha256": d.digest(sealed),
            **FLAGS,
        }
    old = predecessor(BASE / o.CLAIM / "s2-p4-observation-evidence.tar.gz")
    plan = planner(
        commit,
        ROOT,
        BASE / ".mvp2-s2-academic-v2-native_miniature/s2-academic-evidence.tar.gz",
        REFERENCE,
    )
    sealed = release(plan)
    d.require(
        all(plan[k] == old[k] for k in ("runtime", "input", "protected")),
        "Observed runtime/input/scientific-source drift.",
    )
    d.require(
        all(plan["files"].get(k) == v for k, v in o.a.TRANSPORT.items()),
        "Qualified transport drift.",
    )
    # Exclusive creation is the durable one-slot boundary, even on unknown ack.
    target.mkdir(mode=0o700)
    p.publish(target / "plan.json", plan)
    p.publish(target / "release.json", sealed)
    p.publish(
        target / "origin.json",
        {
            "root": str(ROOT),
            "reference": str(REFERENCE),
            "python": sys.executable,
        },
    )
    with (target / "batch.sh").open("x", newline="\n") as stream:
        stream.write("#!/bin/sh\nexec " + shlex.join(dispatch(target, commit)) + "\n")
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
        "--job-name=s2-p4-h300",
        "--chdir=" + str(ROOT),
        "--output=" + str(target / "slurm.out"),
        "--error=" + str(target / "slurm.err"),
        str(target / "batch.sh"),
    ]
    p.publish(
        target / "submission-intent.json",
        {
            "release_sha256": d.digest(sealed),
            "argv_sha256": d.digest(argv),
        },
    )
    meta, raw = command(argv, timeout=30, limit=1024)
    p.publish(target / "submission-call.json", meta)
    d.require(
        meta["status"] == "complete"
        and meta["returncode"] == 0
        and re.fullmatch(rb"[1-9][0-9]*(?:;[A-Za-z0-9_-]+)?\n?", raw),
        "Unknown submission acknowledgement; preserve claim, never retry.",
    )
    job = {"job_id": raw.decode().strip().split(";")[0], "plan_sha256": d.digest(plan)}
    p.publish(target / "job.json", job)
    return {
        "status": "submitted_one_h300_block_only",
        **job,
        "release_sha256": d.digest(sealed),
        **FLAGS,
    }


def job_record(target, plan):
    job = p.read(target / "job.json")
    d.require(
        set(job) == {"job_id", "plan_sha256"}
        and re.fullmatch(r"[1-9][0-9]*", job["job_id"])
        and job["plan_sha256"] == d.digest(plan),
        "Job binding.",
    )
    return job


def batch(path, commit, *, execute=r._batch, verify=r.source.verify_tree):
    target, plan, sealed = load(commit)
    d.require(p.safe(path) == target, "Dedicated release claim.")
    d.require(sys.platform == "linux" and os.getuid() > 0, "Non-root compute required.")
    with (target / "batch-slot").open("x"):
        pass
    phase = "origin_source"
    try:
        d.require(
            p.read(target / "origin.json")
            == {
                "root": str(ROOT),
                "reference": str(REFERENCE),
                "python": sys.executable,
            },
            "Compute source origin.",
        )
        verify(ROOT, plan["files"])
        for key in r.ENVIRONMENT:
            os.environ[key] = "1"
        phase = "fresh_admission_and_serial_block"
        value = execute(target)
        good = value["stop_reason"] is None and not value["unrun"] and len(value["arms"]) == 5
        outcome = {"status": "block_returned", "error_kind": None}
    except BaseException as error:
        good = False
        outcome = {"status": "blocked_or_interrupted", "error_kind": type(error).__name__}
    p.publish(
        target / "driver-outcome.json",
        {
            **outcome,
            "phase": phase,
            "release_sha256": d.digest(sealed),
            **FLAGS,
        },
    )
    return 0 if good else 2


def status(commit, *, command=r.source.command):
    target, plan, _ = load(commit)
    job = job_record(target, plan)
    text = r.query(
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
    return {"status": "accounting_observed", **job, "accounting": text, **FLAGS}


def members(path, destination):
    """Bounded streaming extraction into fixed, private temporary filenames only."""
    d.require(p.safe(path).stat().st_size <= p.LIMIT, "Compressed release bound.")
    found, total = set(), 10240
    with gzip.open(path, "rb") as compressed, tarfile.open(fileobj=compressed, mode="r|") as stream:
        for item in stream:
            d.require(
                item.name in MEMBERS
                and item.name not in found
                and item.isfile()
                and not item.pax_headers
                and 0 <= item.size <= p.LIMIT,
                "Release member scope.",
            )
            total += ((item.size + 511) // 512) * 512 + 512
            d.require(total <= p.LIMIT, "Expanded release bound.")
            if item.name.endswith(".json"):
                d.require(item.size <= p.METADATA, "Release metadata bound.")
            with (destination / item.name).open("xb") as output:
                source = stream.extractfile(item)
                copied = 0
                for raw in iter(lambda source=source: source.read(65536), b""):
                    copied += len(raw)
                    output.write(raw)
                d.require(copied == item.size, "Truncated member.")
            found.add(item.name)
        tail = 0
        for raw in iter(lambda: stream.fileobj.read(65536), b""):
            tail += len(raw)
            d.require(total + tail <= p.LIMIT and not any(raw), "Release trailing bytes/bound.")
    d.require(found == MEMBERS, "Incomplete release bundle.")


def native_metadata(path, name):
    with tarfile.open(path, "r:gz") as stream:
        item = stream.getmember(name)
        d.require(item.size <= p.METADATA, "Native metadata bound.")
        return c.decode_json(stream.extractfile(item).read())


def audit(path, checksum, commit, release_sha, job):
    for value, length in ((checksum, 64), (commit, 40), (release_sha, 64)):
        r.entry.require_hash(value, length)
    d.require(re.fullmatch(r"[1-9][0-9]*", job or ""), "External job anchor.")
    d.require(p.sha_file(path) == checksum, "Release archive anchor.")
    with tempfile.TemporaryDirectory(prefix="p4-release-audit-") as temp:
        temp = Path(temp)
        members(path, temp)
        old = predecessor(temp / "predecessor.tar.gz")
        transfer = p.read(temp / "native-transfer.json")
        d.require(set(transfer) == {"sha256", "files", "plan_sha256"}, "Native transfer schema.")
        p.unpack_review(temp / "native.tar.gz", transfer["sha256"], transfer["files"])
        plan = r._validate(native_metadata(temp / "native.tar.gz", "plan.json"))
        sealed = p.read(temp / "release.json")
        d.require(
            sealed == release(plan)
            and sealed["source_commit"] == commit
            and d.digest(sealed) == release_sha
            and all(plan[k] == old[k] for k in ("input", "runtime", "protected"))
            and all(plan["files"].get(k) == v for k, v in o.a.TRANSPORT.items())
            and transfer["plan_sha256"] == d.digest(plan)
            and native_metadata(temp / "native.tar.gz", "job.json")
            == {"job_id": job, "plan_sha256": d.digest(plan)},
            "External release/native/predecessor binding.",
        )
        reported = native_metadata(temp / "native.tar.gz", "review.json")
        d.require(
            reported["job_id"] == job
            and reported["plan_sha256"] == d.digest(plan)
            and reported["status"]
            in {"five_arms_accounted_not_s2_closure", "forensic_partial_block"}
            and all(
                reported[k] is False
                for k in (
                    "scientific_configuration_selected",
                    "repeats_admitted",
                    "production_isolation_certified",
                )
            ),
            "Native reported review binding.",
        )
        driver = p.read(temp / "driver.json")
        d.require(set(driver) == {"outcome"}, "Portable driver schema.")
        if driver["outcome"] is not None:
            outcome = driver["outcome"]
            d.require(
                outcome["release_sha256"] == release_sha
                and all(outcome[k] is False for k in FLAGS)
                and outcome["status"] in {"block_returned", "blocked_or_interrupted"},
                "Driver outcome binding.",
            )
        result = summary(sealed, reported, driver)
        d.require(p.read(temp / "review.json") == result, "Portable review drift.")
        return result


def summary(sealed, reported, driver=None):
    return {
        "schema_version": "s2-p4-release-portable-v1",
        "status": "portable_integrity_replayed_p5_required",
        "release_sha256": d.digest(sealed),
        "native_plan_sha256": sealed["native_plan_sha256"],
        "job_id": reported["job_id"],
        "reported_native_status": reported["status"],
        "reported_arms": reported["arms"],
        "unrun": reported["unrun"],
        "unaccounted": reported["unaccounted"],
        "accounting_error": reported["accounting_error"],
        "validation_error": reported["validation_error"],
        "driver": driver if driver is not None else {"outcome": None},
        "fresh_private_input_revalidated_by_portable_auditor": False,
        **FLAGS,
    }


def bundle(target, sealed, reported):
    driver = {
        "outcome": p.read(target / "driver-outcome.json")
        if (target / "driver-outcome.json").exists()
        else None,
    }
    sources = {
        "release.json": target / "release.json",
        "predecessor.tar.gz": BASE / o.CLAIM / "s2-p4-observation-evidence.tar.gz",
        "native.tar.gz": target / "s2-h300-academic-evidence.tar.gz",
        "native-transfer.json": target / "transfer.json",
        "review.json": target / "portable-review.json",
        "driver.json": target / "portable-driver.json",
    }
    if sources["driver.json"].exists():
        d.require(p.read(sources["driver.json"]) == driver, "Immutable driver record drift.")
    else:
        p.publish(sources["driver.json"], driver)
    result = summary(sealed, reported, driver)
    if sources["review.json"].exists():
        d.require(p.read(sources["review.json"]) == result, "Immutable portable review drift.")
    else:
        p.publish(sources["review.json"], result)
    d.require(
        sum(((p.safe(x).stat().st_size + 511) // 512) * 512 + 512 for x in sources.values()) + 10240
        <= p.LIMIT,
        "Whole-block release export bound; preserve originals, no truncation.",
    )
    archive = target / ARCHIVE
    if not archive.exists():
        pending = target / (ARCHIVE + ".pending")
        with (
            pending.open("xb") as output,
            tarfile.open(fileobj=output, mode="w:gz", format=tarfile.USTAR_FORMAT) as stream,
        ):
            for name, file in sorted(sources.items()):
                item = tarfile.TarInfo(name)
                item.size, item.mode = file.stat().st_size, 0o600
                with p.safe(file).open("rb") as source:
                    stream.addfile(item, source)
        d.require(pending.stat().st_size <= p.LIMIT, "Compressed release export bound.")
        pending.rename(archive)
    checksum = p.sha_file(archive)
    d.require(
        audit(archive, checksum, sealed["source_commit"], d.digest(sealed), reported["job_id"])
        == result,
        "Release replay.",
    )
    sidecar = Path(str(archive) + ".sha256")
    text = checksum + "  " + archive.name + "\n"
    if sidecar.exists():
        d.require(p.safe(sidecar).read_text() == text, "Release checksum sidecar drift.")
    else:
        with sidecar.open("x", newline="\n") as stream:
            stream.write(text)
    return {
        **result,
        "sha256": checksum,
        "download": str(archive),
        "transfer_checksum": str(sidecar),
    }


def collect(commit, *, command=r.source.command, recheck=r._recheck):
    target, plan, sealed = load(commit)
    job = job_record(target, plan)
    reported = r._collect(target, d.digest(plan), job["job_id"], command=command, recheck=recheck)
    return bundle(target, sealed, reported)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("start", "status", "wait", "collect", "audit", "repeat", "worker")
    )
    parser.add_argument("source_sha")
    parser.add_argument("--one-reviewed-h300-block-only", action="store_true")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--release-sha256")
    parser.add_argument("--job-id")
    args = parser.parse_args(argv)
    if args.action in {"repeat", "worker"}:
        r.entry.execute_h300()
    if args.action == "audit":
        result = audit(args.archive, args.sha256, args.source_sha, args.release_sha256, args.job_id)
    else:
        d.require(sys.platform == "linux" and os.getuid() > 0, "Non-root Linux required.")
        if args.action == "start":
            result = start(args.source_sha, acknowledged=args.one_reviewed_h300_block_only)
        elif not directory().exists():
            print("P4_RELEASE_STATUS=not_submitted; preserve bootstrap; no collection or retry")
            return 2
        elif args.action == "status":
            result = status(args.source_sha)
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
                    print("P4_ACCOUNTING_PENDING; Ctrl-C safe; no resubmission", flush=True)
                    time.sleep(20)
    print(c.encoded(result).decode(), end="")
    print("PRESERVE_CLAIM=" + str(directory()))
    for key, label in (
        ("job_id", "JOB_ID"),
        ("release_sha256", "RELEASE_SHA256"),
        ("native_plan_sha256", "NATIVE_PLAN_SHA256"),
        ("sha256", "SHA256"),
        ("download", "DOWNLOAD"),
        ("transfer_checksum", "TRANSFER_CHECKSUM"),
    ):
        if key in result:
            print(label + "=" + result[key])
    print("NO_REPEAT_AUTOMATIC_FOLLOW_ON_OR_S2_CLOSURE_ADMITTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
