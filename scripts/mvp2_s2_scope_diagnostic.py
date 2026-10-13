"""One bounded supervisor/leaf cgroup observation; never admit a normal workload."""

from __future__ import annotations

import argparse
import os
import re
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
from scripts import mvp2_s2_first_normal as n  # noqa: E402
from scripts import mvp2_s2_slurm_step as s  # noqa: E402
from scripts import mvp2_s2_slurm_synthetic as q  # noqa: E402

BASE = d.BASE
CLAIM = ".mvp2-s2-scope-observation-v1"
ENTRY = "scripts/mvp2_s2_scope_diagnostic.py"
PARENT = {
    "job_id": "2209138",
    "archive_sha256": "4f0f4bc20337d5bc7b42283afd5de620d0500509d6a7010938b18425214a14a1",
}
FLAGS = {**d.FLAGS, "remote_cleanup_proven": False}
RELATIONS = {"equal", "supervisor_ancestor", "worker_ancestor", "disjoint", "different_mount"}
QUERY_KEYS = {
    "JobId",
    "JobState",
    "NumNodes",
    "NumCPUs",
    "NodeList",
    "BatchHost",
    "TimeLimit",
    "MinMemoryNode",
    "MinMemoryCPU",
    "ReqTRES",
    "AllocTRES",
    "StepId",
    "Nodes",
    "State",
    "CPUs",
    "Tasks",
}


def public_query(kind, raw):
    if kind == "members":
        # Grammar from the existing numeric Slurm listpids adapter, not arbitrary output.
        try:
            text = raw.decode("ascii")
        except UnicodeError:
            return {"parse_error": True}
        lines = text.strip().splitlines()
        if member_lines(lines):
            return {"listpids": lines}
        return {"parse_error": True}
    try:
        fields = a.fields(raw.decode("ascii"))
    except (ValueError, UnicodeError):
        return {"parse_error": True}
    return {
        k: v
        for k, v in fields.items()
        if k in QUERY_KEYS and len(v) <= 256 and re.fullmatch(r"[A-Za-z0-9_.(),=:+\[\]/-]*", v)
    }


def member_lines(lines):
    return (
        type(lines) is list
        and 1 <= len(lines) <= 65
        and type(lines[0]) is str
        and lines[0].split() == ["PID", "JOBID", "STEPID", "LOCALID", "GLOBALID"]
        and all(
            type(x) is str and re.fullmatch(r"[0-9 \t-]{1,256}", x) and len(x.split()) == 5
            for x in lines[1:]
        )
    )


def limits(private):
    result = {}
    for role in ("worker", "supervisor"):
        result[role] = {
            "memory_limit_bytes": None,
            "hierarchical_memory_limit_bytes": None,
            "cpuset_cpu_count": None,
            "error_kind": None,
        }
        try:
            raw = private[role]["raw"]
            maps = s.mapped_scopes(raw["cgroup"], raw["mountinfo"])
            memory = Path(maps["memory"]["scope"])
            result[role]["memory_limit_bytes"] = s._uint(
                d.read(memory / "memory.limit_in_bytes").decode().strip()
            )
            pairs = q.r._pairs(d.read(memory / "memory.stat").decode())
            ceiling = pairs.get("hierarchical_memory_limit")
            d.require(type(ceiling) is int and ceiling >= 0, "Memory ceiling missing.")
            result[role]["hierarchical_memory_limit_bytes"] = ceiling
            result[role]["cpuset_cpu_count"] = s._cpus(
                d.read(Path(maps["cpuset"]["scope"]) / "cpuset.cpus").decode().strip()
            )
        except (ValueError, OSError) as exc:
            result[role]["error_kind"] = error_kind(exc)
    return result


def claim_path():
    return d.safe(BASE / CLAIM)


def error_kind(error):
    return (
        type(error).__name__
        if type(error).__name__
        in {"ValueError", "FileNotFoundError", "PermissionError", "TimeoutError", "OSError"}
        else "other"
    )


def relations(worker, supervisor):
    """Describe all controllers without invoking or relaxing the separation gate."""
    d.require(set(worker) == set(supervisor) == set(s.CONTROLLERS), "Controller inventory.")
    result = {}
    for key in s.CONTROLLERS:
        w, p = worker[key], supervisor[key]
        s._validate_scope(w)
        s._validate_scope(p)
        wp, pp = Path(w["scope"]), Path(p["scope"])
        relation = (
            "different_mount"
            if w["mount"] != p["mount"]
            else "equal"
            if wp == pp
            else "supervisor_ancestor"
            if pp in wp.parents
            else "worker_ancestor"
            if wp in pp.parents
            else "disjoint"
        )
        result[key] = {
            "relation": relation,
            "worker_scope_sha256": d.digest(w["scope"].encode()),
            "supervisor_scope_sha256": d.digest(p["scope"].encode()),
        }
    return result


def capture(pid):
    """Private bounded originals first; mapping failure must not erase raw evidence."""
    root = Path("/proc") / str(pid)
    raw = {
        name: d.read(root / name, 1024**2).decode()
        for name in ("stat", "status", "cgroup", "mountinfo")
    }
    # Proc pseudo-files report size zero; read() still bounds actual bytes.
    uid_lines = [x.split()[1:] for x in raw["status"].splitlines() if x.startswith("Uid:")]
    d.require(
        len(uid_lines) == 1 and len(uid_lines[0]) == 4 and len(set(uid_lines[0])) == 1,
        "UID transition.",
    )
    uid = int(uid_lines[0][0])
    ident = q.proc_identity(raw["stat"], uid, pid)
    second = q.proc_identity(d.read(root / "stat").decode(), uid, pid)
    d.require(
        q._stable_identity(ident) == q._stable_identity(second)
        and raw["cgroup"] == d.read(root / "cgroup").decode()
        and raw["mountinfo"] == d.read(root / "mountinfo", 1024**2).decode(),
        "Process/membership drift.",
    )
    return {"identity": second, "raw": raw}


def summarize(private):
    """No raw proc text, usernames, paths, environment or arbitrary errors exported."""
    summary = {"processes": {}, "relations": None, "mapping_error": None}
    maps = {}
    for role in ("supervisor", "worker"):
        record = private[role]
        summary["processes"][role] = {
            "identity": record["identity"],
            "raw_sha256": {k: d.digest(v.encode()) for k, v in record["raw"].items()},
        }
        try:
            maps[role] = s.mapped_scopes(record["raw"]["cgroup"], record["raw"]["mountinfo"])
        except (ValueError, OSError) as exc:
            summary["mapping_error"] = error_kind(exc)
    if len(maps) == 2:
        summary["relations"] = relations(maps["worker"], maps["supervisor"])
    return summary


def runtime(plan, role):
    d.verify_tree(Path(plan["checkout"]), plan["files"])
    d.require(
        str(Path(sys.executable).resolve()) == plan["python"]
        and d.digest(d.read(Path(plan["python"]), 64 * 1024**2)) == plan["python_sha256"],
        "Python drift.",
    )
    for name in ("srun", "scontrol") if role == "batch" else ():
        d.require(
            d.digest(d.read(Path(plan["tools"][name]), 64 * 1024**2)) == plan["tools_sha256"][name],
            "Compute tool drift.",
        )


def load_plan(commit, expected=None):
    plan = d.load(claim_path() / "plan.json", 1024**2)
    sha = d.digest(d.encode(plan))
    d.require(
        plan["source_commit"] == commit
        and plan["predecessor"] == PARENT
        and plan["schema_version"] == "s2-scope-plan-v1"
        and all(plan[k] is False for k in FLAGS),
        "Plan binding.",
    )
    d.require(expected is None or sha == expected, "Plan digest.")
    d.require(Path(plan["checkout"]) / ENTRY == Path(__file__).resolve(), "Original source only.")
    run = d.safe(plan["run"])
    d.require(run.parent == BASE and re.fullmatch(r"s2cg-[a-z0-9_]{8}", run.name), "Run path.")
    return plan, sha


def submit_argv(plan):
    claim = claim_path()
    return [
        plan["tools"]["sbatch"],
        "--parsable",
        "--job-name=mvp2-s2-scope-observation",
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


def start(commit):
    d.host()
    claim = claim_path()
    if claim.exists():
        return collect(commit)
    root = Path(__file__).resolve().parents[1]
    d.require(
        root.name == "source"
        and root.parent.parent == BASE
        and root.parent.name.startswith("s2-scope-driver-"),
        "Checkout location.",
    )
    files = d.source_files(root, commit)
    tools = {k: d.tool(k) for k in ("sbatch", "srun", "scontrol", "sacct")}
    run = Path(tempfile.mkdtemp(prefix="s2cg-", dir=BASE))
    plan = {
        "schema_version": "s2-scope-plan-v1",
        "source_commit": commit,
        "checkout": str(root),
        "files": files,
        "run": str(run),
        "python": str(Path(sys.executable).resolve()),
        "python_sha256": d.digest(d.read(Path(sys.executable).resolve(), 64 * 1024**2)),
        "tools": tools,
        "tools_sha256": {k: d.digest(d.read(Path(v), 64 * 1024**2)) for k, v in tools.items()},
        "predecessor": PARENT,
        **FLAGS,
    }
    sha = d.digest(d.encode(plan))
    claim.mkdir(mode=0o700)  # Exclusive claim before scheduler effect; never reset.
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
            **FLAGS,
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
    print("SCOPE_STATUS=submitted_observation_only\nJOB_ID=" + job)
    print("PRESERVE_CLAIM=" + str(claim) + "\nPRESERVE_RUN=" + str(run))
    return 0


def acknowledged(plan, sha):
    deadline = time.monotonic() + 30
    while not (claim_path() / "job.json").exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    job = d.load(claim_path() / "job.json")
    d.require(
        job
        == {
            "job_id": os.environ.get("SLURM_JOB_ID"),
            "source_commit": plan["source_commit"],
            "plan_sha256": sha,
        },
        "Job binding.",
    )
    return job["job_id"]


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
        plan["checkout"] + "/" + ENTRY,
        "leaf",
        "--source-sha",
        plan["source_commit"],
        "--plan-sha",
        sha,
    ]


def leaf(commit, expected):
    """Only own identity handshake and finite socket wait; no workload or descendants."""
    d.host()
    plan, sha = load_plan(commit, expected)
    runtime(plan, "leaf")
    job = acknowledged(plan, sha)
    step = os.environ.get("SLURM_STEP_ID", "")
    d.require(re.fullmatch(r"[0-9]{1,10}", step), "Numeric step required.")
    with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as sock:
        sock.settimeout(45)
        sock.connect(str(Path(plan["run"]) / "ipc.sock"))
        sock.sendall(d.encode({"job_id": job, "step_id": step, "plan_sha256": sha}))
        d.require(d.decode(sock.recv(4096)) == {"observation_finished": True}, "Observation ended.")
    return 0


def batch(commit, expected):
    d.host()
    plan, sha = load_plan(commit, expected)
    run = Path(plan["run"])
    report = {
        "schema_version": "s2-scope-observation-v1",
        "source_commit": commit,
        "plan_sha256": sha,
        "job_id": None,
        "step_id": None,
        "status": "incomplete",
        "phase": "identity",
        "error_kind": None,
        "summary": None,
        "limits": None,
        "queries": {},
        "local_client_returncode": None,
        **FLAGS,
    }
    server = child = None
    try:
        job = acknowledged(plan, sha)
        report["job_id"] = job
        runtime(plan, "batch")
        supervisor = capture(os.getpid())
        d.write_new(run / "supervisor-private.json", supervisor)
        server = a.BarrierServer(run / "ipc.sock")
        argv = worker_argv(plan, sha, job)
        d.write_new(run / "launch-intent.json", {"argv": argv, "plan_sha256": sha, **FLAGS})
        report["phase"] = "handshake"
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
            child = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=error,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
            )
            try:
                hello, peer = server.accept(30)
                d.require(
                    set(hello) == {"job_id", "step_id", "plan_sha256"}
                    and hello["job_id"] == job
                    and hello["plan_sha256"] == sha
                    and re.fullmatch(r"[0-9]{1,10}", hello["step_id"])
                    and peer["uid"] == os.getuid(),
                    "Peer binding.",
                )
                report["step_id"] = hello["step_id"]
                private = {"supervisor": capture(os.getpid()), "worker": capture(peer["pid"])}
                d.require(
                    q._stable_identity(private["supervisor"]["identity"])
                    == q._stable_identity(supervisor["identity"])
                    and private["worker"]["identity"]["uid"] == peer["uid"],
                    "PID drift.",
                )
                d.write_new(run / "pair-private.json", private)
                report["phase"] = "observation"
                report["summary"] = summarize(private)
                report["limits"] = limits(private)
                for kind, args in {
                    "job": ["-o", "show", "job", job],
                    "step": ["-o", "show", "step", job + "." + hello["step_id"]],
                    "members": ["listpids", job + "." + hello["step_id"]],
                }.items():
                    meta, raw = d.command([plan["tools"]["scontrol"], *args])
                    d.write_new(
                        run / (kind + "-private.json"), {"meta": meta, "text": raw.decode()}
                    )
                    report["queries"][kind] = {"meta": meta, "fields": public_query(kind, raw)}
                server.release({"observation_finished": True}, 5)
                report["status"] = "observed_not_qualified"
            finally:
                if server is not None:
                    server.close()
                try:
                    report["local_client_returncode"] = child.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    child.kill()  # Owned local srun only; never claim remote cleanup.
                    report["local_client_returncode"] = child.wait(timeout=5)
                for name, stream in (("stdout", output), ("stderr", error)):
                    stream.seek(0)
                    raw = stream.read(65536)
                    d.write_new(
                        run / ("srun-" + name + "-private.json"),
                        {
                            "prefix": raw.decode(errors="replace"),
                            "total_bytes": os.fstat(stream.fileno()).st_size,
                        },
                    )
    except (Exception, KeyboardInterrupt) as exc:
        report["error_kind"] = error_kind(exc)
        report["status"] = "incomplete"
    finally:
        if server is not None:
            server.close()
        d.write_new(claim_path() / "observation.json", report)
    print("SCOPE_STATUS=" + report["status"])
    return 0 if report["status"] == "observed_not_qualified" else 2


def accounting(raw, job):
    rows = a.accounting(raw.decode("ascii"), job)
    done = (
        job in rows
        and job + ".batch" in rows
        and all(x["state"] in a.TERMINAL for x in rows.values())
    )
    return rows, done


def collect(commit):
    d.host()
    plan, sha = load_plan(commit)
    job_record = d.load(claim_path() / "job.json")
    job = job_record["job_id"]
    d.require(
        job_record == {"job_id": job, "source_commit": commit, "plan_sha256": sha}
        and re.fullmatch(r"[1-9][0-9]{0,9}", job),
        "Job binding.",
    )
    cached = claim_path() / "collection.json"
    if cached.exists():
        saved = d.load(cached)
        archive = d.safe(saved["archive"])
        d.require(
            archive.parent.parent == claim_path()
            and archive.parent.name.startswith("collection-")
            and archive.name == "s2-scope-evidence.tar.gz",
            "Collection path.",
        )
        d.require(d.digest(d.read(archive, 1024**2)) == saved["sha256"], "Archive drift.")
        d.require(
            d.read(Path(str(archive) + ".sha256")).decode("ascii")
            == saved["sha256"] + "  " + archive.name + "\n",
            "Sidecar drift.",
        )
        audit(archive, saved["sha256"], commit, job, sha)
    else:
        tool = plan["tools"]["sacct"]
        d.require(
            d.digest(d.read(Path(tool), 64 * 1024**2)) == plan["tools_sha256"]["sacct"],
            "Accounting tool drift.",
        )
        meta, raw = d.command(
            [
                tool,
                "--noheader",
                "--parsable2",
                "--jobs=" + job,
                "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
            ]
        )
        d.require(meta["status"] == "complete" and meta["returncode"] == 0, "Collect later.")
        rows, done = accounting(raw, job)
        if not done:
            print("SCOPE_STATUS=accounting_pending; repeat collect only\nJOB_ID=" + job)
            return 0
        observation = claim_path() / "observation.json"
        obs = d.load(observation) if observation.exists() else None
        if obs is not None:
            validate_observation(obs, commit, sha, job)
        records = {
            "anchor.json": {
                "source_commit": commit,
                "job_id": job,
                "plan_sha256": sha,
                "predecessor": PARENT,
                **FLAGS,
            },
            "observation.json": obs,
            "accounting.json": rows,
        }
        directory = Path(tempfile.mkdtemp(prefix="collection-", dir=claim_path()))
        archive = directory / "s2-scope-evidence.tar.gz"
        d.pack(archive, records)
        saved = {"archive": str(archive), "sha256": d.digest(d.read(archive, 1024**2))}
        audit(archive, saved["sha256"], commit, job, sha)
        with Path(str(archive) + ".sha256").open("x", encoding="ascii", newline="\n") as stream:
            stream.write(saved["sha256"] + "  " + archive.name + "\n")
        d.write_new(cached, saved)
    print("SCOPE_STATUS=terminal_evidence_preserved_not_qualified\nJOB_ID=" + job)
    print("SHA256=" + saved["sha256"] + "\nDOWNLOAD=" + saved["archive"])
    print("TRANSFER_CHECKSUM=" + saved["archive"] + ".sha256")
    return 0


def audit(path, checksum, commit, job, plan_sha):
    raw = d.read(path, 1024**2)
    d.require(d.digest(raw) == checksum, "Archive checksum.")
    records = n.read_tar(raw, 1024**2, {"anchor.json", "observation.json", "accounting.json"})
    anchor = d.decode(records["anchor.json"])
    d.require(
        anchor
        == {
            "source_commit": commit,
            "job_id": job,
            "plan_sha256": plan_sha,
            "predecessor": PARENT,
            **FLAGS,
        },
        "Anchor drift.",
    )
    rows = d.decode(records["accounting.json"])
    rebuilt, done = accounting(
        (
            "\n".join(
                "|".join([k, v["state"], v["exit_code"], str(v["elapsed_seconds"])])
                for k, v in rows.items()
            )
        ).encode(),
        job,
    )
    d.require(done and rows == rebuilt, "Terminal accounting.")
    obs = d.decode(records["observation.json"])
    if obs is not None:
        validate_observation(obs, commit, plan_sha, job)
    return {
        "status": "missing_observation" if obs is None else obs["status"],
        "job_id": job,
        "source_commit": commit,
        "plan_sha256": plan_sha,
        **FLAGS,
    }


def validate_observation(obs, commit, sha, job):
    d.require(
        set(obs)
        == {
            "schema_version",
            "source_commit",
            "plan_sha256",
            "job_id",
            "step_id",
            "status",
            "phase",
            "error_kind",
            "summary",
            "limits",
            "queries",
            "local_client_returncode",
            *FLAGS,
        },
        "Observation schema.",
    )
    d.require(
        obs["schema_version"] == "s2-scope-observation-v1"
        and obs["source_commit"] == commit
        and obs["plan_sha256"] == sha
        and obs["job_id"] in (None, job)
        and all(obs[k] is False for k in FLAGS),
        "Observation identity/flags.",
    )
    d.require(
        obs["status"] in {"incomplete", "observed_not_qualified"}
        and obs["phase"] in {"identity", "handshake", "observation"}
        and obs["error_kind"]
        in {
            None,
            "ValueError",
            "FileNotFoundError",
            "PermissionError",
            "TimeoutError",
            "OSError",
            "other",
        },
        "Disposition.",
    )
    # Reject arbitrary data before public export, including nested private path/text fields.
    summary = obs["summary"]
    if summary is not None:
        d.require(set(summary) == {"processes", "relations", "mapping_error"}, "Summary schema.")
        d.require(set(summary["processes"]) == {"worker", "supervisor"}, "Process roles.")
        for record in summary["processes"].values():
            d.require(set(record) == {"identity", "raw_sha256"}, "Process schema.")
            q._identity(record["identity"])
            d.require(
                set(record["raw_sha256"]) == {"stat", "status", "cgroup", "mountinfo"},
                "Raw hash inventory.",
            )
            for value in record["raw_sha256"].values():
                q._hash(value)
        if summary["relations"] is not None:
            d.require(set(summary["relations"]) == set(s.CONTROLLERS), "Relation inventory.")
            for value in summary["relations"].values():
                d.require(
                    set(value) == {"relation", "worker_scope_sha256", "supervisor_scope_sha256"}
                    and value["relation"] in RELATIONS,
                    "Relation schema.",
                )
                q._hash(value["worker_scope_sha256"])
                q._hash(value["supervisor_scope_sha256"])
        d.require(
            summary["mapping_error"] in {None, "ValueError", "OSError", "other"},
            "Mapping disposition.",
        )
    d.require(set(obs["queries"]) <= {"job", "step", "members"}, "Query inventory.")
    for kind, query in obs["queries"].items():
        d.require(set(query) == {"meta", "fields"}, "Query record.")
        fields = query["fields"]
        d.require(type(fields) is dict, "Query fields.")
        if fields != {"parse_error": True}:
            if kind == "members":
                d.require(
                    set(fields) == {"listpids"} and member_lines(fields["listpids"]),
                    "Membership export.",
                )
            else:
                d.require(
                    set(fields) <= QUERY_KEYS
                    and all(
                        type(v) is str
                        and len(v) <= 256
                        and re.fullmatch(r"[A-Za-z0-9_.(),=:+\[\]/-]*", v)
                        for v in fields.values()
                    ),
                    "Field export.",
                )
        meta = query["meta"]
        d.require(
            set(meta)
            == {
                "status",
                "returncode",
                "stdout_bytes",
                "stderr_bytes",
                "stdout_prefix_sha256",
                "stderr_prefix_sha256",
            }
            and meta["status"] in {"complete", "timeout", "output_limit"},
            "Query schema.",
        )
        for key in ("returncode", "stdout_bytes", "stderr_bytes"):
            d.require(type(meta[key]) is int, "Query count.")
        for key in ("stdout_prefix_sha256", "stderr_prefix_sha256"):
            q._hash(meta[key])
    d.require(obs["step_id"] is None or re.fullmatch(r"[0-9]{1,10}", obs["step_id"]), "Step id.")
    d.require(
        obs["local_client_returncode"] is None or type(obs["local_client_returncode"]) is int,
        "Local status.",
    )
    if obs["limits"] is not None:
        d.require(set(obs["limits"]) == {"worker", "supervisor"}, "Limit roles.")
        for value in obs["limits"].values():
            d.require(
                set(value)
                == {
                    "memory_limit_bytes",
                    "hierarchical_memory_limit_bytes",
                    "cpuset_cpu_count",
                    "error_kind",
                },
                "Limit schema.",
            )
            for k in ("memory_limit_bytes", "hierarchical_memory_limit_bytes", "cpuset_cpu_count"):
                d.require(
                    value[k] is None or (type(value[k]) is int and 0 <= value[k] <= s.MAX_COUNTER),
                    "Limit counter.",
                )
            d.require(
                value["error_kind"]
                in {
                    None,
                    "ValueError",
                    "FileNotFoundError",
                    "PermissionError",
                    "TimeoutError",
                    "OSError",
                    "other",
                },
                "Limit error.",
            )
    return obs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "collect", "batch", "leaf"))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--plan-sha")
    args = parser.parse_args()
    d.require(re.fullmatch(r"[0-9a-f]{40}", args.source_sha), "Source commit.")
    try:
        if args.action in ("batch", "leaf"):
            d.require(args.plan_sha is not None, "Plan pin required.")
            return {"batch": batch, "leaf": leaf}[args.action](args.source_sha, args.plan_sha)
        return {"start": start, "collect": collect}[args.action](args.source_sha)
    finally:
        print("NO_NORMAL_ADVERSE_NATIVE_H300_OR_REPEAT_ADMITTED")


if __name__ == "__main__":
    raise SystemExit(main())
