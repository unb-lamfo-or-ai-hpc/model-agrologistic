"""Consolidated A/P2/P3 transport; invocation needs explicit reviewed human CLI.

Effects are injectable; qualification/merge alone is not execution permission.
No host mutations, production dispatch, automatic follow-on or repeat route.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import shlex
import subprocess
import sys
import tarfile
import time
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mvp2_s2_academic as a  # noqa: E402
from scripts import mvp2_s2_academic_worker as w  # noqa: E402
from scripts import mvp2_s2_allocation_diagnostic as d  # noqa: E402

BASE = d.BASE
ENTRY = "scripts/mvp2_s2_academic_runtime.py"


class AccountingPending(ValueError):
    """The only resumable wait condition; corrupt/unknown evidence is not pending."""


def public_execute(*_args, **_kwargs):
    raise PermissionError("Require explicit one-slot academic CLI; no automatic execution.")


def envelope(p):
    return p["profile"]["native" if p["stage"] == "native_miniature" else "synthetic"]


def claim_path(stage):
    a.require(stage in a.STAGES, "Unknown stage.")
    return d.safe(BASE / (".mvp2-s2-academic-v1-" + stage))


def check_source(p, root):
    """Compute uses sealed raw bytes; Git is login-only, not an installed compute dependency."""
    d.verify_tree(Path(root), p["files"])
    a.require(a.runtime() == p["runtime"], "Runtime changed since login.")


def submit(stage, source, predecessors, *, root=a.ROOT, command=d.command):
    """Prospective one-shot seam; public start remains denied before any effect."""
    a.prerequisites(stage, predecessors, source)
    files = d.source_files(root, source)
    p = a.plan(stage, source, files, a.runtime())
    target = claim_path(stage)
    target.mkdir(exist_ok=False)
    d.write_new(target / "plan.json", p)
    d.write_new(target / "origin.json", {"checkout": str(root), "python": sys.executable})
    env = envelope(p)
    batch = (
        "#!/bin/sh\nexec "
        + shlex.join(
            [
                sys.executable,
                "-B",
                "-I",
                str(root / ENTRY),
                "batch",
                str(target),
            ]
        )
        + "\n"
    )
    with (target / "batch.sh").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(batch)
    argv = [
        "sbatch",
        "--parsable",
        "--account=sxdsouza",
        "--partition=intel-256",
        "--nodes=1",
        "--ntasks=1",
        f"--cpus-per-task={env['cpus']}",
        f"--mem={env['memory_mib']}M",
        f"--time={env['wall_seconds'] // 60}",
        "--export=NONE",
        "--no-requeue",
        f"--output={target}/slurm.out",
        f"--error={target}/slurm.err",
        str(target / "batch.sh"),
    ]
    d.write_new(target / "submission-intent.json", {"plan_sha256": a.digest(p), "argv": argv})
    # Reserve BEFORE calling sbatch. Any unknown acknowledgement consumes the slot.
    d.write_new(target / "submission-called.json", {"plan_sha256": a.digest(p)})
    meta, raw = command(argv, timeout=30, limit=65536)
    d.write_new(target / "submission-result.json", meta)
    a.require(
        meta["status"] == "complete" and meta["returncode"] == 0, "Submission unknown/failed."
    )
    job = raw.decode().strip()
    a.require(re.fullmatch(r"[1-9][0-9]*", job), "Ambiguous acknowledgement; preserve and stop.")
    d.write_new(target / "job.json", {"job_id": job, "plan_sha256": a.digest(p)})
    return target, job


def query(argv, *, command=d.command):
    meta, raw = command(argv, timeout=10, limit=65536)
    a.require(meta["status"] == "complete" and meta["returncode"] == 0, "Scheduler query failed.")
    return raw.decode("ascii")


def stop_step(job, step, *, command=d.command, pause=time.sleep):
    a.require(
        re.fullmatch(re.escape(job) + r"\.[0-9]+", step or ""), "Exact numeric step required."
    )
    statuses = []
    for sig in ("TERM", "KILL"):
        meta, _ = command(["scancel", "--signal=" + sig, step], timeout=10, limit=65536)
        statuses.append(meta["status"] == "complete" and meta["returncode"] == 0)
        if sig == "TERM":
            pause(5)
    return statuses


def supervise(
    target, p, job, process, *, clock=time.monotonic, pause=time.sleep, command=d.command
):
    """Bound local supervision; exact Slurm cleanup is observed, never certified globally."""
    start = clock()
    native = p["stage"] == "native_miniature"
    cap = 2340 if native else 180
    guard = a.c.Deadlines(start, start + cap, caps=(120, 1800, 120, 300)) if native else None
    identity = None
    if native:
        from scripts import mvp2_h300_partial as partial

        data, config = a.fixture()
        anchor = partial.anchor(
            data,
            config,
            source_commit=p["source_commit"],
            runtime_sha256=a.digest(p["runtime"]),
            workbook_sha256=p["fixture"]["data_sha256"],
            threads=4,
        )
        identity = a.digest(anchor)
    step, reason = None, None
    term = kill = False
    try:
        while process.poll() is None:
            path = target / "worker-start.json"
            if step is None and path.exists():
                hello = a.c.read_json(path)
                a.require(
                    hello["job_id"] == job
                    and hello["plan_sha256"] == a.digest(p)
                    and hello["uid"] == os.getuid()
                    and hello["runtime_sha256"] == a.digest(p["runtime"]),
                    "Worker binding.",
                )
                step = hello["step_id"]
                a.require(re.fullmatch(re.escape(job) + r"\.[0-9]+", step), "Numeric step.")
                d.write_new(
                    target / "worker-release.json",
                    {"job_id": job, "step_id": step, "plan_sha256": a.digest(p)},
                )
            elapsed = clock() - start
            if native:
                phases = a.c.phase_events(target / "native", identity)
                failure = a.c.failure_cleanup_event(target / "native", identity, phases)
                reason = guard.observe(clock(), phases, aborted=failure)
                if reason:
                    break
            if p["stage"] == "nested_setsid_term_ignore" and (target / "nested.json").exists():
                reason = "planned_nested_stop"
                break
            if elapsed > (30 if step is None else cap):
                reason = "startup_timeout" if step is None else "worker_watchdog"
                break
            pause(0.05)
    except BaseException:
        reason = "supervisor_error"
        raise
    finally:
        if reason is not None and step is not None:
            try:
                term, kill = stop_step(job, step, command=command, pause=pause)
            except (OSError, ValueError):
                reason = "cleanup_query_failure"
        reaped = False
        try:
            # Never consume a fresh cleanup budget after the hard batch envelope.
            remaining = max(0.1, min(295, envelope(p)["wall_seconds"] - (clock() - start) - 30))
            process.wait(timeout=remaining)
            reaped = True
        except subprocess.TimeoutExpired:
            # This kills/reaps the local srun client only. Unknown remote effects
            # remain negative and must not admit the next case.
            process.kill()
            process.wait(timeout=5)
        identities = []
        if (target / "nested.json").exists():
            identities = a.c.read_json(target / "nested.json")["identities"]
        descendants_absent = False
        quiet = 0
        quiet_end = min(clock() + 10, start + envelope(p)["wall_seconds"] - 20)
        while identities and clock() < quiet_end:
            quiet = quiet + 1 if all(w.absent(x) is True for x in identities) else 0
            if quiet >= 3:
                descendants_absent = True
                break
            pause(1)
        d.write_new(
            target / "attempt.json",
            {
                "plan_sha256": a.digest(p),
                "step_id": step,
                "stop_reason": reason,
                "term_sent": term,
                "kill_sent": kill,
                "local_client_reaped": reaped,
                "return_code": process.returncode,
                "observed_seconds": clock() - start,
                "descendants_absent_observed": descendants_absent,
                "global_cleanup_proven": False,
            },
        )


def batch(target, *, command=d.command, popen=subprocess.Popen):
    """Private real-transport seam; no public dispatch until an operational release."""
    target = d.safe(target)
    p = a.validate_plan(a.c.read_json(target / "plan.json"))
    a.require(target == claim_path(p["stage"]), "Claim scope.")
    origin = a.c.read_json(target / "origin.json")
    root = Path(origin["checkout"])
    a.require(root.resolve() == a.ROOT and origin["python"] == sys.executable, "Executing origin.")
    check_source(p, root)
    end = time.monotonic() + 30
    while not (target / "job.json").exists():
        a.require(time.monotonic() < end, "Acknowledgement not published.")
        time.sleep(0.05)
    receipt = a.c.read_json(target / "job.json")
    job = receipt["job_id"]
    a.require(
        receipt["plan_sha256"] == a.digest(p) and os.environ.get("SLURM_JOB_ID") == job,
        "Batch allocation mismatch.",
    )
    observation = a.allocation(
        query(["scontrol", "-o", "show", "job", job], command=command),
        job,
        os.getuid(),
        envelope(p),
    )
    d.write_new(target / "allocation.json", observation)
    d.write_new(target / "batch-called.json", {"plan_sha256": a.digest(p)})
    requested = 4 if p["stage"] == "native_miniature" else 1
    argv = [
        "srun",
        "--exclusive",
        "--exact",
        "--nodes=1",
        "--ntasks=1",
        f"--cpus-per-task={requested}",
        "--cpu-bind=threads",
        "--export=ALL",
        sys.executable,
        "-B",
        "-I",
        str(root / ENTRY),
        "worker",
        str(target),
    ]
    # Private logs may contain solver/connection diagnostics; they never enter Git/archive.
    with (target / "worker.out").open("xb") as out, (target / "worker.err").open("xb") as err:
        child = popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err, shell=False)
        supervise(target, p, job, child, command=command)


def collect(target, *, command=d.command):
    """Read-only with respect to the original run; cache is exclusive and replayed."""
    target = d.safe(target)
    p = a.validate_plan(a.c.read_json(target / "plan.json"))
    job = a.c.read_json(target / "job.json")["job_id"]
    archive_path = target / "s2-academic-evidence.tar.gz"
    sidecar = archive_path.with_suffix(archive_path.suffix + ".sha256")
    if archive_path.exists():
        checksum = sidecar.read_text().split()[0]
        return (
            archive_path,
            checksum,
            a.audit(archive_path, checksum, p["source_commit"], a.digest(p), job),
        )
    accounting = query(
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
    rows = a.old.accounting(accounting, job)
    if not all(
        x in rows and rows[x]["state"] in a.old.TERMINAL
        for x in (job, job + ".batch", job + ".extern")
    ) or not all(x["state"] in a.old.TERMINAL for x in rows.values()):
        raise AccountingPending("Accounting not terminal; no submission.")
    records = {}
    for name in a.RECORDS:
        path = target / name
        if path.exists():
            records[name] = d.decode(d.read(path, a.LIMIT // 2))
    result = a.review(p, job, records, accounting)
    files = {
        "plan.json": a.c.encoded(p),
        "job.json": a.c.encoded({"job_id": job, "plan_sha256": a.digest(p)}),
        "records.json": a.c.encoded(records),
        "accounting.txt": accounting.encode(),
        "review.json": a.c.encoded(result),
    }
    a.require(sum(map(len, files.values())) < a.LIMIT // 2, "Evidence volume; preserve originals.")
    # An interrupted/corrupted collection is preserved, never repaired in place.
    with archive_path.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, raw in files.items():
            member = tarfile.TarInfo(name)
            member.size = len(raw)
            archive.addfile(member, io.BytesIO(raw))
    checksum = a.sha(archive_path.read_bytes())
    with sidecar.open("x", encoding="ascii") as stream:
        stream.write(checksum + "  " + archive_path.name + "\n")
    a.audit(archive_path, checksum, p["source_commit"], a.digest(p), job)
    return archive_path, checksum, result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "describe",
            "start",
            "batch",
            "worker",
            "status",
            "collect",
            "audit",
        ),
    )
    parser.add_argument("args", nargs="*")
    parser.add_argument("--one-reviewed-academic-slot", action="store_true")
    args = parser.parse_intermixed_args(argv)
    if args.action == "start":
        if len(args.args) < 2 or not args.one_reviewed_academic_slot:
            public_execute()
        a.require(sys.platform == "linux" and os.getuid() != 0, "Unprivileged Linux operator.")
        a.require((len(args.args) - 2) % 5 == 0, "Five anchors per predecessor.")
        certs = [args.args[i : i + 5] for i in range(2, len(args.args), 5)]
        target = claim_path(args.args[0])
        if target.exists():
            p = a.validate_plan(a.c.read_json(target / "plan.json"))
            a.require(p["source_commit"] == args.args[1], "Use original source; never reset claim.")
            path, checksum, result = collect(target)
            print(f"STATUS={result['disposition']}\nSHA256={checksum}\nDOWNLOAD={path}")
        else:
            target, job = submit(args.args[0], args.args[1], certs)
            print(f"PRESERVE_CLAIM={target}\nJOB_ID={job}\nNO_FOLLOW_ON_OR_REPEAT_ADMITTED")
    elif args.action in {"batch", "worker"}:
        a.require(
            len(args.args) == 1
            and sys.platform == "linux"
            and os.environ.get("SLURM_JOB_ID", "").isdecimal(),
            "Slurm role required.",
        )
        target = d.safe(args.args[0])
        p = a.validate_plan(a.c.read_json(target / "plan.json"))
        a.require(target == claim_path(p["stage"]), "Exact claim required.")
        if args.action == "batch":
            batch(target)
        else:
            check_source(p, a.ROOT)
            job = a.c.read_json(target / "job.json")["job_id"]
            return w.run(target, p, job)
    elif args.action == "describe":
        a.require(not args.args, "describe takes no arguments.")
        print(a.c.encoded(a.profile()).decode(), end="")
    elif args.action == "status":
        a.require(len(args.args) == 1, "Require exact academic stage.")
        target = claim_path(args.args[0])
        p = a.validate_plan(a.c.read_json(target / "plan.json"))
        job = a.c.read_json(target / "job.json")["job_id"]
        print(f"PRESERVE_CLAIM={target}\nJOB_ID={job}\nPLAN_SHA256={a.digest(p)}")
        print(
            query(
                [
                    "sacct",
                    "-j",
                    job,
                    "--noheader",
                    "--parsable2",
                    "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
                ]
            )
        )
    elif args.action == "collect":
        a.require(len(args.args) == 1, "Require exact academic stage.")
        try:
            path, checksum, report = collect(claim_path(args.args[0]))
        except AccountingPending:
            print("STATUS=accounting_pending; preserve claim; no submission")
            return 2
        print(f"STATUS={report['disposition']}\nSHA256={checksum}\nDOWNLOAD={path}")
        print(f"TRANSFER_CHECKSUM={path}.sha256\nPLAN_SHA256={report['plan_sha256']}")
    else:
        a.require(len(args.args) == 5, "Require archive, checksum, source, plan SHA and job.")
        print(a.c.encoded(a.audit(*args.args)).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
