"""One immutable, bounded NPAD post-fast-exit observation; no downstream admission."""

from __future__ import annotations

import argparse
import os
import re
import secrets
import shlex
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mvp2_s2_allocation_diagnostic as d  # noqa: E402
from scripts import mvp2_s2_batch_adapter as a  # noqa: E402
from scripts import mvp2_s2_fast_exit as f  # noqa: E402
from scripts import mvp2_s2_scope_diagnostic as scope  # noqa: E402
from scripts import mvp2_s2_slurm_step as s  # noqa: E402
from scripts import mvp2_s2_synthetic_worker as worker  # noqa: E402

BASE = d.BASE
CLAIM = ".mvp2-s2-fast-exit-observation-v1"
ENTRY = "scripts/mvp2_s2_fast_exit_observation.py"
PARENT = {
    "job_id": "2210506",
    "archive_sha256": "0239bbec7edd29cf384e7949d441ec6fb3e8474f77c735799978620fc74aa642",
}
TOOLS = {"sbatch", "srun", "scontrol", "sacct"}


def claim_path():
    return d.safe(BASE / CLAIM)


def validate_plan(plan, commit, expected=None):
    f.keys(
        plan,
        {
            "schema_version",
            "source_commit",
            "checkout",
            "files",
            "run",
            "python",
            "python_sha256",
            "tools",
            "tools_sha256",
            "predecessor",
            "nonce",
            *f.FLAGS,
        },
    )
    d.require(
        plan["schema_version"] == "s2-fast-exit-plan-v1"
        and plan["source_commit"] == commit
        and re.fullmatch(r"[0-9a-f]{40}", commit)
        and plan["predecessor"] == PARENT
        and all(plan[k] is False for k in f.FLAGS),
        "Plan identity/authority.",
    )
    f.sha(plan["nonce"])
    f.sha(plan["python_sha256"])
    f.keys(plan["tools"], TOOLS)
    f.keys(plan["tools_sha256"], TOOLS)
    for name in TOOLS:
        d.safe(plan["tools"][name])
        f.sha(plan["tools_sha256"][name])
    root, run = d.safe(plan["checkout"]), d.safe(plan["run"])
    d.safe(plan["python"])
    d.require(
        root.name == "source"
        and root.parent.parent == BASE
        and re.fullmatch(r"s2-fast-exit-driver-[A-Za-z0-9]{8}", root.parent.name)
        and run.parent == BASE
        and re.fullmatch(r"s2fx-[a-z0-9_]{8}", run.name),
        "Plan locations.",
    )
    d.require(type(plan["files"]) is dict and ENTRY in plan["files"], "Source inventory.")
    digest = d.digest(d.encode(plan))
    d.require(expected is None or expected == digest, "Plan digest.")
    return digest


def load_plan(commit, expected=None):
    plan = d.load(claim_path() / "plan.json", 1024**2)
    sha = validate_plan(plan, commit, expected)
    d.require(Path(plan["checkout"]) / ENTRY == Path(__file__).resolve(), "Original source only.")
    return plan, sha


def runtime(plan, role):
    d.require(role in {"login", "batch", "leaf"}, "Runtime role.")
    d.verify_tree(Path(plan["checkout"]), plan["files"])
    d.require(
        str(Path(sys.executable).resolve()) == plan["python"]
        and a.sha_file(plan["python"], 64 * 1024**2) == plan["python_sha256"],
        "Python drift.",
    )
    for key in (
        TOOLS if role == "login" else {"srun", "scontrol", "sacct"} if role == "batch" else ()
    ):
        d.require(
            a.sha_file(plan["tools"][key], 64 * 1024**2) == plan["tools_sha256"][key],
            "Role tool drift.",
        )


def submit_argv(plan):
    claim = claim_path()
    return [
        plan["tools"]["sbatch"],
        "--parsable",
        "--job-name=mvp2-s2-fast-exit-observation",
        "--account=sxdsouza",
        "--partition=intel-256",
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=2",
        "--mem=2048M",
        "--time=00:05:00",
        "--no-requeue",
        "--export=NONE",
        "--chdir=" + str(claim),
        "--output=" + str(claim / "slurm-%j.out"),
        "--error=" + str(claim / "slurm-%j.err"),
        str(claim / "batch.sh"),
    ]


def worker_argv(plan, sha, job):
    return [
        plan["tools"]["srun"],
        "--jobid=" + job,
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=1",
        "--exact",
        "--mem=256M",
        "--cpu-bind=threads",
        "--immediate=10",
        "--time=00:02:00",
        "--kill-on-bad-exit=1",
        "--export=NONE",
        plan["python"],
        "-B",
        "-I",
        str(Path(plan["checkout"]) / ENTRY),
        "leaf",
        "--source-sha",
        plan["source_commit"],
        "--plan-sha",
        sha,
    ]


def start(commit):
    d.host()
    claim = claim_path()
    if claim.exists():
        return collect(commit)
    root = Path(__file__).resolve().parents[1]
    d.require(
        root.name == "source"
        and root.parent.parent == BASE
        and re.fullmatch(r"s2-fast-exit-driver-[A-Za-z0-9]{8}", root.parent.name),
        "Checkout location.",
    )
    files = d.source_files(root, commit)
    tools = {name: d.tool(name) for name in TOOLS}
    run = Path(tempfile.mkdtemp(prefix="s2fx-", dir=BASE))
    plan = {
        "schema_version": "s2-fast-exit-plan-v1",
        "source_commit": commit,
        "checkout": str(root),
        "files": files,
        "run": str(run),
        "nonce": secrets.token_hex(32),
        "python": str(Path(sys.executable).resolve()),
        "tools": tools,
        "python_sha256": a.sha_file(Path(sys.executable).resolve(), 64 * 1024**2),
        "tools_sha256": {k: a.sha_file(v, 64 * 1024**2) for k, v in tools.items()},
        "predecessor": PARENT,
        **f.FLAGS,
    }
    sha = validate_plan(plan, commit)
    runtime(plan, "login")
    claim.mkdir(mode=0o700)  # Exclusive before intent/submission; never reset.
    d.write_new(claim / "plan.json", plan)
    script = (
        "#!/bin/sh\nexec "
        + shlex.join(
            [
                plan["python"],
                "-B",
                "-I",
                str(root / ENTRY),
                "batch",
                "--source-sha",
                commit,
                "--plan-sha",
                sha,
            ]
        )
        + "\n"
    )
    with (claim / "batch.sh").open("x", encoding="ascii", newline="\n") as stream:
        stream.write(script)
        stream.flush()
        os.fsync(stream.fileno())
    d.write_new(
        claim / "submission-intent.json",
        {
            "plan_sha256": sha,
            "argv_sha256": d.digest(d.encode(submit_argv(plan))),
            "script_sha256": d.digest(script.encode()),
            **f.FLAGS,
        },
    )
    meta, raw = d.command(submit_argv(plan), timeout=30)
    d.write_new(claim / "submission-result.json", meta)
    d.require(
        meta["status"] == "complete" and meta["returncode"] == 0,
        "Unknown submission effect; preserve claim, never repeat.",
    )
    job = raw.decode("ascii").strip()
    d.require(re.fullmatch(r"[1-9][0-9]{0,9}", job), "Unknown acknowledgement; never repeat.")
    d.write_new(claim / "job.json", {"job_id": job, "source_commit": commit, "plan_sha256": sha})
    print("FAST_EXIT_STATUS=submitted_observation_only\nJOB_ID=" + job + "\nPLAN_SHA256=" + sha)
    print("PRESERVE_RUN=" + str(run))
    return 0


def job_receipt(plan, sha, *, batch=False):
    if batch:
        deadline = time.monotonic() + 30
        while not (claim_path() / "job.json").exists() and time.monotonic() < deadline:
            time.sleep(0.1)
    receipt = d.load(claim_path() / "job.json")
    f.keys(receipt, {"job_id", "source_commit", "plan_sha256"})
    d.require(
        type(receipt["job_id"]) is str
        and re.fullmatch(r"[1-9][0-9]{0,9}", receipt["job_id"])
        and receipt["source_commit"] == plan["source_commit"]
        and receipt["plan_sha256"] == sha
        and (not batch or receipt["job_id"] == os.environ.get("SLURM_JOB_ID")),
        "Job binding.",
    )
    return receipt["job_id"]


def binding(plan, job, step):
    return s.binding(
        {
            "job_id": job,
            "worker_step_id": step,
            "supervisor_step_id": "batch",
            "nonce": plan["nonce"],
            "source_commit": plan["source_commit"],
        }
    )


def leaf(commit, expected):
    d.host()
    plan, sha = load_plan(commit, expected)
    runtime(plan, "leaf")
    job = job_receipt(plan, sha, batch=True)
    step = os.environ.get("SLURM_STEP_ID", "")
    binding(plan, job, step)
    d.write_new(
        Path(plan["run"]) / "leaf-role.json", {"job_id": job, "step_id": step, "plan_sha256": sha}
    )
    with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as sock:
        sock.settimeout(45)
        sock.connect(str(Path(plan["run"]) / "ipc.sock"))
        sock.sendall(d.encode({"job_id": job, "step_id": step, "plan_sha256": sha}))
        d.require(d.decode(sock.recv(4097)) == {"observe_fast_exit": sha}, "Observation release.")

    def denied():
        raise PermissionError("Nested processes are not admitted.")

    worker.exercise_components(
        "normal",
        Path(plan["run"]) / "worker",
        plan["nonce"],
        release=lambda: True,
        nested_factory=denied,
    )
    return 0  # No linger, heartbeat, solver, normal adapter or cleanup assertion.


def new_report(commit, job, sha):
    return {
        "schema_version": "s2-fast-exit-observation-v1",
        "source_commit": commit,
        "job_id": job,
        "plan_sha256": sha,
        "step_id": None,
        "status": "incomplete",
        "phase": "identity",
        "error_kind": None,
        "local_client_returncode": None,
        "error_site": None,
        "initial_sha256": None,
        "initial": None,
        "samples": [],
        **f.FLAGS,
    }


def batch(commit, expected):
    d.host()
    plan, sha = load_plan(commit, expected)
    job = job_receipt(plan, sha, batch=True)
    run = Path(plan["run"])
    d.write_new(run / "batch-role.json", {"job_id": job, "plan_sha256": sha})
    report = new_report(commit, job, sha)
    server = child = None
    output = error = None
    try:
        runtime(plan, "batch")
        server = a.BarrierServer(run / "ipc.sock")
        argv = worker_argv(plan, sha, job)
        d.write_new(
            run / "launch-intent.json", {"argv_sha256": d.digest(d.encode(argv)), **f.FLAGS}
        )
        output = (run / "srun.out").open("xb")
        error = (run / "srun.err").open("xb")
        child = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=error,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )
        report["phase"] = "handshake"
        hello, peer = server.accept(30)
        f.keys(hello, {"job_id", "step_id", "plan_sha256"})
        d.require(
            hello["job_id"] == job and hello["plan_sha256"] == sha and peer["uid"] == os.getuid(),
            "Peer binding.",
        )
        bound = binding(plan, job, hello["step_id"])
        report["step_id"] = hello["step_id"]
        private = {"supervisor": scope.capture(os.getpid()), "worker": scope.capture(peer["pid"])}
        d.require(private["worker"]["identity"]["uid"] == peer["uid"], "Peer UID drift.")
        d.write_new(run / "pair-private.json", private)
        report["initial"] = f.initial_record(private)
        report["phase"] = "initial"
        queries = {}
        for name, args in {
            "job": ["-o", "show", "job", job],
            "step": ["-o", "show", "step", job + "." + hello["step_id"]],
            "members": ["listpids", job + "." + hello["step_id"]],
        }.items():
            meta, raw = d.command([plan["tools"]["scontrol"], *args], timeout=2)
            d.write_new(
                run / ("initial-" + name + ".json"), {"meta": meta, "raw": raw.decode("ascii")}
            )
            d.require(meta["status"] == "complete" and meta["returncode"] == 0, "Initial query.")
            queries[name] = raw.decode("ascii")
        maps, identities = f.review_initial(
            private,
            queries["job"],
            queries["step"],
            queries["members"],
            bound,
            os.getuid(),
            os.uname().nodename,
        )
        d.write_new(run / "initial-scopes-private.json", {"maps": maps, "identities": identities})
        report["initial_sha256"] = a.sha_file(run / "pair-private.json", 4 * 1024**2)
        server.release({"observe_fast_exit": sha}, 5)
        report["phase"] = "exit"
        report["local_client_returncode"] = child.wait(timeout=60)
        # A nonzero fast exit must not erase post-exit products/scope/accounting.
        # Observe it independently and preserve an incomplete, never promoted outcome.
        reaped = time.monotonic()
        report["phase"] = "samples"
        query_number = 0

        def observed_query(argv, **kwargs):
            nonlocal query_number
            meta, raw = d.command(argv, **kwargs)
            d.require(query_number < 15, "Post-exit query count.")
            d.write_new(
                run / f"query-{query_number}-private.json",
                {"meta": meta, "stdout": raw.decode("ascii", errors="replace")},
            )
            query_number += 1
            return meta, raw

        for index, offset in enumerate(f.OFFSETS):
            time.sleep(max(0, reaped + offset - time.monotonic()))
            item = {
                "offset_seconds": offset,
                "elapsed_seconds": time.monotonic() - reaped,
                "channels": f.sample(
                    bound,
                    maps,
                    identities,
                    private["worker"]["identity"],
                    run / "worker",
                    plan["tools"],
                    command=observed_query,
                ),
            }
            report["samples"].append(item)
            d.write_new(run / f"sample-{index}.json", item)
        report.update(
            status="observed_not_admitted" if child.returncode == 0 else "incomplete",
            phase="complete",
        )
    except (OSError, ValueError, TimeoutError, UnicodeError) as exc:
        report["error_kind"] = f.failure(exc)
        report["status"] = "blocked_environment"
        report["error_site"] = f.error_site(exc)
    finally:
        if server is not None:
            server.close()
        if child is not None and child.poll() is None:
            child.kill()  # Local client only. Remote cleanup remains unproven.
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                report["error_kind"] = "unavailable"
        for stream in (output, error):
            if stream is not None:
                stream.close()
        f.validate_report(report, commit, job, sha)
        d.write_new(run / "observation.json", report)
    print("FAST_EXIT_STATUS=" + report["status"])
    return 0 if report["status"] == "observed_not_admitted" else 2


def capture_collection(plan, sha, job):
    run, claim = Path(plan["run"]), claim_path()
    raw = None
    try:
        raw = a._file(run / "observation.json", 1024**2)
        report = d.decode(raw)
        f.validate_report(report, plan["source_commit"], job, sha)
        invalid = None
    except FileNotFoundError:
        report, invalid = None, None
    except (ValueError, OSError, UnicodeError, TypeError, KeyError, OverflowError, RecursionError):
        report, invalid = None, d.digest(raw) if raw is not None else None
    entry = {"invalid_observation_sha256": invalid}

    def leaf_binding():
        raw = a._file(run / "leaf-role.json", 4096)
        role = d.decode(raw)
        f.keys(role, {"job_id", "step_id", "plan_sha256"})
        d.require(
            role["job_id"] == job
            and role["plan_sha256"] == sha
            and type(role["step_id"]) is str
            and re.fullmatch(r"[0-9]{1,10}", role["step_id"])
            and int(role["step_id"]) < 0xFFFFFFFA,
            "Forensic leaf binding.",
        )
        d.require(
            report is None or report["step_id"] is None or report["step_id"] == role["step_id"],
            "Leaf/report binding drift.",
        )
        return {"step_id": role["step_id"], "sha256": d.digest(raw)}

    entry["leaf"] = f.channel(leaf_binding)
    for key, suffix in (("stdout", "out"), ("stderr", "err")):
        entry[key] = f.entry_log(claim / f"slurm-{job}.{suffix}")
        entry["client_" + key] = f.entry_log(run / ("srun." + suffix))
    return {"observation.json": report, "entry.json": entry}


def show_collection(receipt, plan, sha, job):
    archive = d.safe(receipt["archive"])
    d.require(
        archive.parent.parent == claim_path()
        and archive.name == "s2-fast-exit-evidence.tar.gz"
        and re.fullmatch(r"collection-[a-z0-9_]{8}", archive.parent.name),
        "Collection location.",
    )
    review = f.audit(archive, receipt["sha256"], plan["source_commit"], job, sha)
    d.require(
        d.read(Path(str(archive) + ".sha256"))
        == (receipt["sha256"] + "  " + archive.name + "\n").encode(),
        "Checksum sidecar drift.",
    )
    print("FAST_EXIT_STATUS=" + review["status"] + "\nJOB_ID=" + job + "\nPLAN_SHA256=" + sha)
    print("SHA256=" + receipt["sha256"] + "\nDOWNLOAD=" + str(archive))
    print("TRANSFER_CHECKSUM=" + str(archive) + ".sha256")
    return 0


def collect(commit, *, status_only=False):
    d.host()
    plan, sha = load_plan(commit)
    runtime(plan, "login")
    if not (claim_path() / "job.json").exists():
        print("FAST_EXIT_STATUS=acknowledgement_unknown_preserve_claim_no_resubmission")
        return 3
    job = job_receipt(plan, sha)
    cache = claim_path() / "collection.json"
    if cache.exists() and not status_only:
        return show_collection(d.load(cache), plan, sha, job)
    meta, raw = d.command(f.accounting_argv(plan["tools"]["sacct"], job), timeout=5)
    if meta["status"] != "complete" or meta["returncode"] != 0:
        print("FAST_EXIT_STATUS=accounting_unavailable_preserve_claim\nJOB_ID=" + job)
        return 4
    rows = a.accounting(raw.decode("ascii"), job)
    if not {job, job + ".batch"} <= set(rows) or any(
        row["state"] not in a.TERMINAL for row in rows.values()
    ):
        print("FAST_EXIT_STATUS=nonterminal_or_accounting_pending\nJOB_ID=" + job)
        return 4
    if status_only:
        print("FAST_EXIT_STATUS=terminal_collect_next\nJOB_ID=" + job)
        return 0
    records = capture_collection(plan, sha, job)
    d.require(records == capture_collection(plan, sha, job), "Collection capture drift.")
    observed = records["observation.json"]
    leaf = records["entry.json"]["leaf"]
    if leaf["status"] == "available" and job + "." + leaf["value"]["step_id"] not in rows:
        print("FAST_EXIT_STATUS=forensic_step_accounting_pending\nJOB_ID=" + job)
        return 4
    if observed is not None and observed["step_id"] is not None:
        if job + "." + observed["step_id"] not in rows:
            print("FAST_EXIT_STATUS=exact_step_accounting_pending\nJOB_ID=" + job)
            return 4
    records.update(
        {
            "anchor.json": {
                "schema_version": "s2-fast-exit-carrier-v1",
                "source_commit": commit,
                "job_id": job,
                "plan_sha256": sha,
                **f.FLAGS,
            },
            "accounting.json": rows,
        }
    )
    output = Path(tempfile.mkdtemp(prefix="collection-", dir=claim_path()))
    archive = output / "s2-fast-exit-evidence.tar.gz"
    d.pack(archive, records)
    checksum = a.sha_file(archive, f.LIMIT)
    f.audit(archive, checksum, commit, job, sha)
    with Path(str(archive) + ".sha256").open("xb") as stream:
        stream.write((checksum + "  " + archive.name + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())
    receipt = {"archive": str(archive), "sha256": checksum}
    d.write_new(cache, receipt)
    return show_collection(receipt, plan, sha, job)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "status", "collect", "wait", "batch", "leaf"))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--plan-sha")
    args = parser.parse_args(argv)
    d.require(re.fullmatch(r"[0-9a-f]{40}", args.source_sha), "Full reviewed source required.")
    try:
        if args.action in {"batch", "leaf"}:
            f.sha(args.plan_sha)
            return {"batch": batch, "leaf": leaf}[args.action](args.source_sha, args.plan_sha)
        if args.action == "start":
            return start(args.source_sha)
        if args.action == "wait":
            while True:
                result = collect(args.source_sha)
                if result != 4:
                    return result
                time.sleep(20)  # Human wait is interruptible; no resubmission.
        return collect(args.source_sha, status_only=args.action == "status")
    except (OSError, ValueError, TimeoutError, UnicodeError) as exc:
        if args.action not in {"batch", "leaf"}:
            raise
        diagnostic = {
            "schema_version": "s2-fast-exit-entry-v1",
            "role": args.action,
            "error_kind": f.failure(exc),
            "site": f.error_site(exc),
            **f.FLAGS,
        }
        f.validate_entry(diagnostic)
        print(d.encode(diagnostic).decode().strip(), file=sys.stderr, flush=True)
        return 2
    finally:
        print("PRESERVE_CLAIM=" + str(claim_path()))
        print("NO_NORMAL_ADVERSE_NATIVE_MINIATURE_H300_OR_REPEAT_ADMITTED")


if __name__ == "__main__":
    raise SystemExit(main())
