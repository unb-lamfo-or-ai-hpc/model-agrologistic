"""One prospective shared-reserve P4 release, never reuse the consumed PR106 claim.

Preparation/merge is not job admission. Only a human pinned command after merge,
with an explicit replacement-block acknowledgement, can consume the new slot.
Historical auditors, scientific bytes, source cohorts and archives stay intact.
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

from scripts import mvp2_s2_p4_release as previous
from scripts import mvp2_s2_p4_terminal_runtime as runtime

p, d, c, old, diag = runtime.p, runtime.d, runtime.c, runtime.old, runtime.diag
ROOT, BASE, REFERENCE = runtime.ROOT, previous.BASE, previous.REFERENCE
PARENT = "38ebfe256c262d2bd7c02d7ffd821b1e058ec578"
PRIOR = {
    "job_id": "2214130",
    "source_commit": "8d244ed3b3331b64b1e465e2b09b39df6ce9ab3b",
    "archive_sha256": "a60d826c56cbfb09b975d56295aec3b746c4a0eddb0e745cec0fe3ab066dfe74",
    "release_sha256": "56f7785fc150e207a3d95bd66094a6c49838f8fa081187d20b3ede6aa085cb5a",
}
INTEGRATION = (
    "scripts/mvp2_s2_p4_terminal_runtime.py",
    "scripts/mvp2_s2_p4_terminal_release.py",
    "scripts/mvp2_s2_p4_diagnostics.py",
    "scripts/npad_s2_p4_terminal.sh",
)
FLAGS = {**previous.FLAGS, "h300_execution_admitted": False}
ARCHIVE = "s2-p4-terminal-evidence.tar.gz"
MEMBERS = {
    "release.json",
    "prior.tar.gz",
    "native.tar.gz",
    "native-transfer.json",
    "diagnostics.json",
    "driver.json",
    "review.json",
}


def directory():
    return p.safe(BASE / runtime.CLAIM)


def prior_path():
    return p.safe(BASE / old.CLAIM / previous.ARCHIVE)


def predecessor(path):
    value = previous.audit(
        path,
        PRIOR["archive_sha256"],
        PRIOR["source_commit"],
        PRIOR["release_sha256"],
        PRIOR["job_id"],
    )
    d.require(
        value["reported_native_status"] == "forensic_partial_block"
        and value["unrun"] == [1, 8, 2, 16],
        "Original partial grid anchor.",
    )
    with tempfile.TemporaryDirectory(prefix="p4-prior-") as temp:
        temp = Path(temp)
        previous.members(path, temp)
        return old._validate(previous.native_metadata(temp / "native.tar.gz", "plan.json"))


def release(plan):
    runtime.validate(plan)
    d.require(all(name in plan["files"] for name in INTEGRATION), "Integrated source inventory.")
    d.require(
        all(plan["files"].get(k) == v for k, v in previous.o.a.TRANSPORT.items()),
        "Historical transport drift.",
    )
    return {
        "schema_version": "s2-p4-terminal-release-v1",
        "source_commit": plan["preparation"]["source_commit"],
        "parent_merge": PARENT,
        "native_plan_sha256": d.digest(plan),
        "prior": dict(PRIOR),
        "enforcement": dict(runtime.CONTRACT),
        "order": list(d.ORDER),
        "integration": {name: plan["files"][name] for name in INTEGRATION},
        "export_limit_bytes": p.LIMIT,
        "scope": "one_new_cold_serial_replacement_block",
        **FLAGS,
    }


def load_claim(target):
    target = p.safe(target)
    d.require(target.name == runtime.CLAIM, "Exclusive terminal claim required.")
    plan = runtime.validate(p.read(target / "plan.json"))
    sealed = p.read(target / "terminal-release.json")
    d.require(c.encoded(sealed) == c.encoded(release(plan)), "Terminal release/source drift.")
    return plan, sealed


def load(commit):
    old.entry.require_hash(commit, 40)
    target = directory()
    plan, sealed = load_claim(target)
    d.require(sealed["source_commit"] == commit, "Execution source drift.")
    return target, plan, sealed


def verify_origin(target, plan):
    d.require(
        p.read(target / "origin.json")
        == {"root": str(ROOT), "reference": str(REFERENCE), "python": sys.executable},
        "Compute origin.",
    )
    old.source.verify_tree(ROOT, plan["files"])


def start(commit, *, acknowledged=False, planner=runtime._plan, command=old.source.command):
    d.require(acknowledged is True, "One reviewed replacement block acknowledgement required.")
    old.entry.require_hash(commit, 40)
    target = directory()
    if target.exists():
        _, plan, sealed = load(commit)
        d.require(
            (target / "job.json").is_file(), "Consumed slot; no acknowledgement, never retry."
        )
        return {
            "status": "existing_job_collect_only",
            **previous.job_record(target, plan),
            "release_sha256": d.digest(sealed),
            **FLAGS,
        }
    prior = predecessor(prior_path())
    plan = planner(
        commit,
        ROOT,
        BASE / ".mvp2-s2-academic-v2-native_miniature/s2-academic-evidence.tar.gz",
        REFERENCE,
    )
    sealed = release(plan)
    d.require(
        all(plan[k] == prior[k] for k in ("runtime", "input", "protected")),
        "Prior scientific/runtime identities drift.",
    )
    target.mkdir(mode=0o700)
    p.publish(target / "plan.json", plan)
    p.publish(target / "terminal-release.json", sealed)
    p.publish(
        target / "origin.json",
        {"root": str(ROOT), "reference": str(REFERENCE), "python": sys.executable},
    )
    code = (
        "import sys;sys.dont_write_bytecode=True;sys.path.insert(0,"
        + repr(str(ROOT))
        + ");from scripts.mvp2_s2_p4_terminal_release import batch;raise SystemExit(batch("
        + repr(str(target))
        + ","
        + repr(commit)
        + "))"
    )
    with (target / "batch.sh").open("x", newline="\n") as stream:
        stream.write(
            "#!/bin/sh\nexec " + shlex.join([sys.executable, "-B", "-I", "-c", code]) + "\n"
        )
    argv = [
        "sbatch",
        "--parsable",
        "--partition=intel-256",
        "--account=sxdsouza",
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=16",
        "--mem=196608M",
        "--time=12:00:00",
        "--no-requeue",
        "--export=NONE",
        "--job-name=s2-p4-terminal",
        "--chdir=" + str(ROOT),
        "--output=" + str(target / "slurm.out"),
        "--error=" + str(target / "slurm.err"),
        str(target / "batch.sh"),
    ]
    p.publish(
        target / "submission-intent.json",
        {"release_sha256": d.digest(sealed), "argv_sha256": d.digest(argv)},
    )
    meta, raw = command(argv, timeout=30, limit=1024)
    p.publish(target / "submission-call.json", meta)
    d.require(
        meta["status"] == "complete"
        and meta["returncode"] == 0
        and re.fullmatch(rb"[1-9][0-9]*(?:;[A-Za-z0-9_-]+)?\n?", raw),
        "Unknown submission acknowledgement consumes slot; never retry.",
    )
    job = {"job_id": raw.decode().strip().split(";")[0], "plan_sha256": d.digest(plan)}
    p.publish(target / "job.json", job)
    return {
        "status": "submitted_one_replacement_block_only",
        **job,
        "release_sha256": d.digest(sealed),
        **FLAGS,
    }


def batch(path, commit, *, execute=runtime._batch, verify=verify_origin):
    target, plan, sealed = load(commit)
    d.require(
        p.safe(path) == target and sys.platform == "linux" and os.getuid() > 0,
        "Non-root dedicated compute claim.",
    )
    with (target / "batch-slot").open("x"):
        pass
    phase, good = "origin_source", False
    try:
        verify(target, plan)
        for key in old.ENVIRONMENT:
            os.environ[key] = "1"
        phase = "fresh_admission_and_serial_block"
        block = execute(target)
        good = block["stop_reason"] is None and not block["unrun"] and len(block["arms"]) == 5
        outcome = {"status": "block_returned", "error_kind": None}
    except BaseException as error:
        outcome = {"status": "blocked_or_interrupted", "error_kind": type(error).__name__}
    p.publish(
        target / "driver-outcome.json",
        {**outcome, "phase": phase, "release_sha256": d.digest(sealed), **FLAGS},
    )
    return 0 if good else 2


def status(commit, *, command=old.source.command):
    target, plan, sealed = load(commit)
    job = previous.job_record(target, plan)
    text = old.query(
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


def _diagnostics(target, plan, reported):
    arms = []
    for item in reported["arms"]:
        threads = item["threads"]
        path = target / "arms" / f"t{threads}"
        value = {
            "threads": threads,
            "status": "missing_or_invalid",
            "catalogue": None,
            "records": None,
        }
        try:
            attempt = p.read(path / "attempt.json")
            ident = runtime.worker_identity(plan, threads, attempt["step_id"])
            catalogue = diag.catalogue(
                path / "diagnostics", ident, profile_factory=runtime.solver_profile
            )
            records = {
                name: p.read(path / "diagnostics" / name, limit=2048) for name in catalogue["files"]
            }
            value.update(status="prefix_verified", catalogue=catalogue, records=records)
        except Exception:
            pass  # Unknown/raw/private payload stays local, never copied to carrier.
        arms.append(value)
    return {"schema_version": "s2-p4-terminal-diagnostics-v1", "arms": arms, **FLAGS}


def verify_diagnostics(value, plan, reported, native_archive):
    d.require(
        set(value) == {"schema_version", "arms", *FLAGS}
        and value["schema_version"] == "s2-p4-terminal-diagnostics-v1"
        and all(value[k] is False for k in FLAGS)
        and [x["threads"] for x in value["arms"]] == [x["threads"] for x in reported["arms"]],
        "Diagnostic block binding.",
    )
    complete = bool(value["arms"])
    for arm in value["arms"]:
        d.require(
            set(arm) == {"threads", "status", "catalogue", "records"}, "Diagnostic arm schema."
        )
        if arm["status"] == "missing_or_invalid":
            d.require(
                arm["catalogue"] is None and arm["records"] is None, "Raw diagnostics denied."
            )
            complete = False
            continue
        d.require(
            arm["status"] == "prefix_verified" and type(arm["records"]) is dict,
            "Diagnostic status.",
        )
        base = f"arms/t{arm['threads']}/"
        attempt = previous.native_metadata(native_archive, base + "attempt.json")
        d.require(
            attempt["enforcement_contract_sha256"] == d.digest(runtime.CONTRACT),
            "Parent enforcement binding.",
        )
        ident = runtime.worker_identity(plan, arm["threads"], attempt["step_id"])
        with tempfile.TemporaryDirectory(prefix="p4-diag-audit-") as temp:
            temp = Path(temp)
            d.require(set(arm["records"]) <= set(diag.NAMES), "Diagnostic member allowlist.")
            for name, record in arm["records"].items():
                p.publish(temp / name, record, limit=2048)
            d.require(
                diag.catalogue(temp, ident, profile_factory=runtime.solver_profile)
                == arm["catalogue"],
                "Diagnostic replay drift.",
            )
        returned = arm["catalogue"]["native_return_observed"]
        if returned:
            terminal = previous.native_metadata(
                native_archive, base + "native/native-terminal.json"
            )
            d.require(
                arm["records"]["native-return.json"]["terminal_sha256"] == d.digest(terminal),
                "Portable diagnostic terminal binding.",
            )
        complete = complete and returned
    return complete


def _members(path, destination):
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
            d.require(total <= p.LIMIT, "Expanded whole-block bound.")
            if item.name.endswith(".json"):
                d.require(item.size <= p.METADATA, "Metadata bound.")
            with (destination / item.name).open("xb") as output:
                source, copied = stream.extractfile(item), 0
                for raw in iter(lambda source=source: source.read(65536), b""):
                    copied += len(raw)
                    output.write(raw)
                d.require(copied == item.size, "Truncated release member.")
            found.add(item.name)
        tail = 0
        for raw in iter(lambda: stream.fileobj.read(65536), b""):
            tail += len(raw)
            d.require(total + tail <= p.LIMIT and not any(raw), "Release trailing payload/bound.")
    d.require(found == MEMBERS, "Missing release member.")


def summary(sealed, reported, driver, diagnostic_complete):
    return {
        "schema_version": "s2-p4-terminal-portable-v1",
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
        "diagnostics_complete_for_reported_arms": diagnostic_complete,
        "driver": driver,
        "fresh_private_input_revalidated_by_portable_auditor": False,
        **FLAGS,
    }


def audit(path, checksum, commit, release_sha, job):
    for value, length in ((checksum, 64), (commit, 40), (release_sha, 64)):
        old.entry.require_hash(value, length)
    d.require(re.fullmatch(r"[1-9][0-9]*", job or ""), "External job anchor.")
    d.require(p.sha_file(path) == checksum, "Archive checksum.")
    with tempfile.TemporaryDirectory(prefix="p4-terminal-audit-") as temp:
        temp = Path(temp)
        _members(path, temp)
        prior = predecessor(temp / "prior.tar.gz")
        transfer = p.read(temp / "native-transfer.json")
        d.require(set(transfer) == {"sha256", "files", "plan_sha256"}, "Native transfer schema.")
        p.unpack_review(temp / "native.tar.gz", transfer["sha256"], transfer["files"])
        plan = runtime.validate(previous.native_metadata(temp / "native.tar.gz", "plan.json"))
        sealed = p.read(temp / "release.json")
        d.require(
            c.encoded(sealed) == c.encoded(release(plan))
            and sealed["source_commit"] == commit
            and d.digest(sealed) == release_sha
            and sealed["native_plan_sha256"] == d.digest(plan)
            and transfer["plan_sha256"] == d.digest(plan)
            and all(plan[k] == prior[k] for k in ("runtime", "input", "protected"))
            and previous.native_metadata(temp / "native.tar.gz", "job.json")
            == {"job_id": job, "plan_sha256": d.digest(plan)},
            "Release/source/prior binding.",
        )
        reported = previous.native_metadata(temp / "native.tar.gz", "review.json")
        d.require(
            reported["job_id"] == job
            and reported["plan_sha256"] == d.digest(plan)
            and reported["status"]
            in {"five_arms_accounted_not_s2_closure", "forensic_partial_block"}
            and all(
                reported[k] is False
                for k in (
                    "scientific_configuration_selected",
                    "h300_execution_admitted",
                    "repeats_admitted",
                    "production_isolation_certified",
                )
            ),
            "Reported native binding.",
        )
        driver = p.read(temp / "driver.json")
        d.require(set(driver) == {"outcome"}, "Driver schema.")
        if driver["outcome"] is not None:
            outcome = driver["outcome"]
            d.require(
                outcome["release_sha256"] == release_sha
                and all(outcome[k] is False for k in FLAGS)
                and outcome["status"] in {"block_returned", "blocked_or_interrupted"},
                "Driver outcome binding.",
            )
        complete = verify_diagnostics(
            p.read(temp / "diagnostics.json"), plan, reported, temp / "native.tar.gz"
        )
        result = summary(sealed, reported, driver, complete)
        d.require(p.read(temp / "review.json") == result, "Portable review drift.")
        return result


def _once(path, value):
    if path.exists():
        d.require(p.read(path) == value, "Immutable collection drift.")
    else:
        p.publish(path, value)


def bundle(target, plan, sealed, reported):
    diagnostics = _diagnostics(target, plan, reported)
    driver = {
        "outcome": p.read(target / "driver-outcome.json")
        if (target / "driver-outcome.json").exists()
        else None
    }
    native_archive = target / "s2-h300-academic-evidence.tar.gz"
    complete = verify_diagnostics(diagnostics, plan, reported, native_archive)
    result = summary(sealed, reported, driver, complete)
    for name, value in (
        ("terminal-diagnostics.json", diagnostics),
        ("portable-driver.json", driver),
        ("portable-review.json", result),
    ):
        _once(target / name, value)
    sources = {
        "release.json": target / "terminal-release.json",
        "prior.tar.gz": prior_path(),
        "native.tar.gz": native_archive,
        "native-transfer.json": target / "transfer.json",
        "diagnostics.json": target / "terminal-diagnostics.json",
        "driver.json": target / "portable-driver.json",
        "review.json": target / "portable-review.json",
    }
    d.require(
        sum(((p.safe(x).stat().st_size + 511) // 512) * 512 + 512 for x in sources.values()) + 10240
        <= p.LIMIT,
        "Whole-block export bound; preserve originals, no truncation.",
    )
    archive = target / ARCHIVE
    if not archive.exists():
        pending = target / (ARCHIVE + ".pending")
        with (
            pending.open("xb") as output,
            tarfile.open(fileobj=output, mode="w:gz", format=tarfile.USTAR_FORMAT) as stream,
        ):
            for name, path in sorted(sources.items()):
                info = tarfile.TarInfo(name)
                info.size, info.mode = path.stat().st_size, 0o600
                with p.safe(path).open("rb") as source:
                    stream.addfile(info, source)
        d.require(pending.stat().st_size <= p.LIMIT, "Compressed whole-block bound.")
        pending.rename(archive)
    checksum = p.sha_file(archive)
    d.require(
        audit(archive, checksum, sealed["source_commit"], d.digest(sealed), reported["job_id"])
        == result,
        "Portable terminal replay.",
    )
    sidecar = p.safe(str(archive) + ".sha256")
    text = checksum + "  " + archive.name + "\n"
    if sidecar.exists():
        d.require(sidecar.read_text() == text, "Checksum sidecar drift.")
    else:
        with sidecar.open("x", newline="\n") as stream:
            stream.write(text)
    return {
        **result,
        "sha256": checksum,
        "download": str(archive),
        "transfer_checksum": str(sidecar),
    }


def collect(commit, *, command=old.source.command, recheck=runtime._recheck):
    target, plan, sealed = load(commit)
    job = previous.job_record(target, plan)
    report = runtime._collect(
        target, d.digest(plan), job["job_id"], command=command, recheck=recheck
    )
    return bundle(target, plan, sealed, report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("start", "status", "wait", "collect", "audit", "repeat", "worker")
    )
    parser.add_argument("source_sha")
    parser.add_argument("--one-reviewed-replacement-block-only", action="store_true")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--release-sha256")
    parser.add_argument("--job-id")
    args = parser.parse_args(argv)
    if args.action in {"repeat", "worker"}:
        old.entry.execute_h300()
    if args.action == "audit":
        result = audit(args.archive, args.sha256, args.source_sha, args.release_sha256, args.job_id)
    else:
        d.require(sys.platform == "linux" and os.getuid() > 0, "Non-root Linux required.")
        if args.action == "start":
            result = start(args.source_sha, acknowledged=args.one_reviewed_replacement_block_only)
        elif not directory().exists():
            print("P4_TERMINAL_STATUS=not_submitted; preserve bootstrap; no retry")
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
                    print(
                        "P4_TERMINAL_ACCOUNTING_PENDING; Ctrl-C safe; no resubmission", flush=True
                    )
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
