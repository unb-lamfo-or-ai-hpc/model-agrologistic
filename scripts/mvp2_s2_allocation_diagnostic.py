"""One-shot allocation observation. No worker, solver, signal or admission route."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

BASE = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
CLAIM_NAME = ".mvp2-s2-allocation-diagnostic-v1"
ENTRY = "scripts/mvp2_s2_allocation_diagnostic.py"
PARENT = {
    "job_id": "2208339",
    "source_commit": "f96d9729f2a3bf7a8310094aa8a675b224b203d1",
    "archive_sha256": "b10d4e4c2930a4dce0ea685b8aa0af4a1effff815da878e652c50712e4f3cc95",
    "release_sha256": "baeed8c999179e36f824b9faf9fa2f5caac3885b1099c385c59b3db302f40e46",
}
FLAGS = {
    k: False
    for k in (
        "normal_worker_admitted",
        "live_containment_qualified",
        "adverse_execution_admitted",
        "native_miniature_admitted",
        "production_admitted",
        "repeats_admitted",
    )
}
KEYS = (
    "JobId",
    "UserId",
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
)
LIMIT = 65536


def require(ok, message):
    if not ok:
        raise ValueError(message)


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def safe(path):
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts, "Absolute path required.")
    require(not any(p.is_symlink() for p in (path, *path.parents)), "Linked path.")
    return path


def read(path, limit=LIMIT):
    path = safe(path)
    require(path.is_file() and path.stat().st_size <= limit, "File bound/type.")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, "Read bound.")
    return raw


def load(path, limit=LIMIT):
    return json.loads(read(path, limit))


def write_new(path, value):
    path = safe(path)
    fd, temporary = tempfile.mkstemp(prefix=".writing-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encode(value))
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == "nt":
            os.rename(temporary, path)  # Windows rename is no-replace.
        else:
            os.link(temporary, path)  # Atomic publication, fails if destination exists.
        if os.name == "posix":
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def command(argv, timeout=5, limit=LIMIT):
    """Bound output and wall time; never expose raw command/error text in receipts."""
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        child = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )
        status = "complete"
        deadline = time.monotonic() + timeout
        try:
            while child.poll() is None:
                if os.fstat(out.fileno()).st_size > limit or os.fstat(err.fileno()).st_size > limit:
                    status = "output_limit"
                    break
                if time.monotonic() >= deadline:
                    status = "timeout"
                    break
                time.sleep(0.01)
        finally:
            if child.poll() is None:
                child.kill()  # Only the local command process, never a Slurm job/step.
            child.wait(timeout=5)
        sizes = [os.fstat(f.fileno()).st_size for f in (out, err)]
        if max(sizes) > limit:
            status = "output_limit"
        out.seek(0)
        err.seek(0)
        stdout, stderr = out.read(limit), err.read(limit)
    meta = {
        "status": status,
        "returncode": child.returncode,
        "stdout_bytes": sizes[0],
        "stderr_bytes": sizes[1],
        "stdout_prefix_sha256": digest(stdout),
        "stderr_prefix_sha256": digest(stderr),
    }
    return meta, stdout if status == "complete" else b""


def checked(argv, limit=LIMIT):
    meta, raw = command(argv, timeout=30, limit=limit)
    require(meta["status"] == "complete" and meta["returncode"] == 0, "Command failed.")
    return raw


def source_files(root, commit):
    """Login only: match every tracked working byte to Git, reject extra files."""
    git = shutil.which("git")
    require(git is not None, "Login Git unavailable.")
    prefix = [git, "--no-optional-locks", "-C", str(root)]
    require(checked(prefix + ["rev-parse", "HEAD"]).decode().strip() == commit, "HEAD drift.")
    require(
        not checked(prefix + ["status", "--porcelain", "--untracked-files=all", "--ignored"]),
        "Source not clean.",
    )
    listing = checked(prefix + ["ls-files", "--stage", "-z"], 1024**2)
    files = {}
    for record in listing.rstrip(b"\0").split(b"\0"):
        metadata, name = record.split(b"\t", 1)
        mode, oid, stage = metadata.split()
        require(mode in (b"100644", b"100755") and stage == b"0", "Index type.")
        name = name.decode()
        raw = checked(prefix + ["cat-file", "blob", oid.decode()], 8 * 1024**2)
        require(read(root / name, 8 * 1024**2) == raw, "HEAD bytes differ.")
        files[name] = digest(raw)
    verify_tree(root, files)
    return files


def verify_tree(root, files):
    root = safe(root)
    require(type(files) is dict and 1 <= len(files) <= 1024 and ENTRY in files, "Source inventory.")
    for name, sha in files.items():
        require(
            re.fullmatch(r"[A-Za-z0-9_. /-]+", name)
            and "\\" not in name
            and not Path(name).is_absolute()
            and ".." not in Path(name).parts,
            "Source name.",
        )
        require(re.fullmatch("[0-9a-f]{64}", sha), "Source checksum.")
    found, total = {}, 0
    parents = {p.as_posix() for name in files for p in Path(name).parents}
    for directory, dirs, names in os.walk(
        root, followlinks=False, onerror=lambda e: (_ for _ in ()).throw(e)
    ):
        base = Path(directory)
        for name in list(dirs):
            path = safe(base / name)
            if path == root / ".git":
                dirs.remove(name)
            else:
                require(path.relative_to(root).as_posix() in parents, "Extra source directory.")
        for name in names:
            path = safe(base / name)
            relative = path.relative_to(root).as_posix()
            require(relative in files, "Extra source file.")
            raw = read(path, 8 * 1024**2)
            total += len(raw)
            require(total <= 32 * 1024**2, "Source size.")
            found[relative] = digest(raw)
    require(found == files, "Source bytes differ.")


def field_observation(raw):
    """Allowlist only; retain invalid/duplicate disposition, never arbitrary values."""
    result = dict.fromkeys(KEYS)
    errors = []
    try:
        text = raw.decode("ascii")
    except UnicodeError:
        return result, ["non_ascii"]
    if not 0 < len(raw) <= LIMIT or len(text.strip().splitlines()) != 1:
        return result, ["line_or_size"]
    for key, value in re.findall(r"(?:^|\s)([A-Za-z][A-Za-z0-9_]*)=(\S*)", text.strip()):
        if key not in result:
            continue
        if result[key] is not None:
            errors.append("duplicate:" + key)
        if len(value) > 256 or not re.fullmatch(r"[A-Za-z0-9_.(),=:+\[\]/-]*", value):
            errors.append("redacted:" + key)
            result[key] = "<redacted>"
        else:
            result[key] = value
    return result, errors


def comparisons(fields, job, uid, node):
    expected = {
        "JobId": job,
        "UserId": uid,
        "JobState": "RUNNING",
        "NumNodes": "1",
        "NumCPUs": "2",
        "NodeList": node,
        "BatchHost": node,
        "TimeLimit": "00:12:00",
        "MinMemoryNode": ["2048M", "2G"],
    }
    results = {}
    for key, wanted in expected.items():
        value = fields[key]
        if key == "UserId":
            match = re.fullmatch(r"[A-Za-z0-9_.-]+\(([0-9]+)\)", value or "")
            passed = match is not None and int(match[1]) == uid
        elif key == "MinMemoryNode":
            passed = value in wanted
        else:
            passed = value == wanted
        results[key] = {"expected": wanted, "observed": value, "matches": passed}
    return results


def observe(meta, raw, job, uid, node):
    fields, errors = field_observation(raw)
    checks = comparisons(fields, job, uid, node)
    complete = meta["status"] == "complete" and meta["returncode"] == 0 and not errors
    return {
        "schema_version": "s2-allocation-observation-v1",
        "job_id": job,
        "local_uid": uid,
        "local_hostname": node,
        "query": meta,
        "fields": fields,
        "parse_errors": errors,
        "checks": checks,
        "status": (
            "observed_matching_not_admitted"
            if complete and all(x["matches"] for x in checks.values())
            else "observed_mismatch_or_query_failure"
        ),
        **FLAGS,
    }


def claim_path():
    return safe(BASE / CLAIM_NAME)


def host():
    require(
        sys.platform == "linux" and sys.version_info[:2] == (3, 13), "Linux/Python 3.13 required."
    )
    require(os.getuid() != 0, "Non-root required.")


def tool(name):
    value = shutil.which(name)
    require(value is not None, "Required login tool absent.")
    return str(Path(value).resolve())


def submit_argv(plan):
    claim = claim_path()
    return [
        plan["tools"]["sbatch"],
        "--parsable",
        "--job-name=mvp2-s2-allocation-diagnostic",
        "--account=sxdsouza",
        "--partition=intel-256",
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=2",
        "--mem=2048M",
        "--time=00:12:00",
        "--no-requeue",
        "--export=NONE",
        "--chdir=" + str(claim),
        "--output=" + str(claim / "slurm-%j.out"),
        "--error=" + str(claim / "slurm-%j.err"),
        str(claim / "batch.sh"),
    ]


def start(commit):
    host()
    claim = claim_path()
    if claim.exists():
        return collect(commit)
    root = Path(__file__).resolve().parents[1]
    require(
        root.name == "source"
        and root.parent.parent == BASE
        and root.parent.name.startswith("s2-allocation-driver-"),
        "Unreviewed source location.",
    )
    files = source_files(root, commit)
    tools = {name: tool(name) for name in ("sbatch", "scontrol", "sacct")}
    plan = {
        "schema_version": "s2-allocation-plan-v1",
        "source_commit": commit,
        "checkout": str(root),
        "files": files,
        "python": str(Path(sys.executable).resolve()),
        "python_sha256": digest(read(Path(sys.executable).resolve(), 64 * 1024**2)),
        "tools": tools,
        "tools_sha256": {k: digest(read(Path(v), 64 * 1024**2)) for k, v in tools.items()},
        "predecessor": PARENT,
        **FLAGS,
    }
    sha = digest(encode(plan))
    claim.mkdir(mode=0o700)  # Exclusive reservation before any scheduler effect.
    write_new(claim / "plan.json", plan)
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
    write_new(
        claim / "submission-intent.json",
        {
            "plan_sha256": sha,
            "argv_sha256": digest(encode(submit_argv(plan))),
            "script_sha256": digest(script.encode()),
            **FLAGS,
        },
    )
    # Any exception, timeout or ambiguous acknowledgement consumes this claim.
    meta, raw = command(submit_argv(plan), timeout=30)
    write_new(claim / "submission-result.json", meta)
    require(
        meta["status"] == "complete" and meta["returncode"] == 0,
        "Unknown submission effect; preserve claim.",
    )
    acknowledgement = raw.decode("ascii").strip()
    require(
        re.fullmatch(r"[1-9][0-9]{0,9}", acknowledgement),
        "Unknown acknowledgement; never resubmit.",
    )
    write_new(
        claim / "job.json", {"job_id": acknowledgement, "source_commit": commit, "plan_sha256": sha}
    )
    print("DIAGNOSTIC_STATUS=submitted_observation_only")
    print("JOB_ID=" + acknowledgement)
    print("PLAN_SHA256=" + sha)
    print("PRESERVE_CLAIM=" + str(claim))
    return 0


def load_plan(commit, expected=None):
    plan = load(claim_path() / "plan.json", 1024**2)
    sha = digest(encode(plan))
    require(
        plan["source_commit"] == commit
        and plan["schema_version"] == "s2-allocation-plan-v1"
        and plan["predecessor"] == PARENT
        and all(plan[k] is False for k in FLAGS),
        "Plan binding.",
    )
    require(expected is None or expected == sha, "Plan digest.")
    require(
        Path(plan["checkout"]) / ENTRY == Path(__file__).resolve(),
        "Use original diagnostic source.",
    )
    return plan, sha


def batch(commit, expected):
    host()
    report = {
        "schema_version": "s2-allocation-error-v1",
        "source_commit": commit,
        "phase": "plan",
        "status": "diagnostic_incomplete",
        **FLAGS,
    }
    claim = claim_path()
    try:
        plan, sha = load_plan(commit, expected)
        deadline = time.monotonic() + 30
        while not (claim / "job.json").exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        job = load(claim / "job.json")
        require(
            job
            == {
                "job_id": os.environ.get("SLURM_JOB_ID"),
                "source_commit": commit,
                "plan_sha256": sha,
            },
            "Acknowledged job binding.",
        )
        report["phase"] = "source_runtime"
        verify_tree(Path(plan["checkout"]), plan["files"])
        require(
            str(Path(sys.executable).resolve()) == plan["python"]
            and digest(read(Path(plan["python"]), 64 * 1024**2)) == plan["python_sha256"],
            "Python drift.",
        )
        control = Path(plan["tools"]["scontrol"])
        require(
            digest(read(control, 64 * 1024**2)) == plan["tools_sha256"]["scontrol"],
            "Compute scontrol drift.",
        )
        report["phase"] = "query"
        # Exact query used by the normal adapter. No srun, worker, solver or signal.
        meta, raw = command([str(control), "-o", "show", "job", job["job_id"]])
        node = os.uname().nodename
        require(re.fullmatch(r"[A-Za-z0-9_.-]{1,255}", node), "Hostname grammar.")
        report = observe(meta, raw, job["job_id"], os.getuid(), node)
        report.update(source_commit=commit, plan_sha256=sha)
    except (Exception, KeyboardInterrupt) as exc:
        report["error_kind"] = (
            type(exc).__name__
            if type(exc).__name__
            in {
                "ValueError",
                "FileNotFoundError",
                "PermissionError",
                "TimeoutError",
                "KeyboardInterrupt",
            }
            else "other"
        )
    write_new(claim / "observation.json", report)
    print("DIAGNOSTIC_STATUS=" + report["status"])
    return 0 if report["schema_version"] == "s2-allocation-observation-v1" else 2


def accounting(raw, job):
    rows = {}
    for line in raw.decode("ascii").splitlines():
        cells = line.split("|")
        require(
            len(cells) == 4 and cells[0] in {job, job + ".batch", job + ".extern"},
            "Accounting cohort.",
        )
        key, state, code, elapsed = cells
        require(
            key not in rows
            and re.fullmatch(r"[A-Z_]+(?: by [0-9]+)?", state)
            and re.fullmatch(r"[0-9]+:[0-9]+", code)
            and elapsed.isdigit(),
            "Accounting grammar.",
        )
        rows[key] = {"state": state, "exit_code": code, "elapsed_seconds": int(elapsed)}
    terminal = {
        "COMPLETED",
        "FAILED",
        "CANCELLED",
        "TIMEOUT",
        "OUT_OF_MEMORY",
        "NODE_FAIL",
        "PREEMPTED",
        "BOOT_FAIL",
        "DEADLINE",
        "REVOKED",
    }
    done = (
        job in rows
        and job + ".batch" in rows
        and all(x["state"].split(" ")[0] in terminal for x in rows.values())
    )
    return rows, done


def review(records, commit, job, plan_sha):
    require(
        re.fullmatch("[0-9a-f]{40}", commit)
        and re.fullmatch("[0-9a-f]{64}", plan_sha)
        and re.fullmatch(r"[1-9][0-9]{0,9}", job),
        "Review identity.",
    )
    require(
        set(records) == {"anchor.json", "observation.json", "accounting.json"}, "Archive members."
    )
    anchor = records["anchor.json"]
    require(
        anchor
        == {
            "schema_version": "s2-allocation-anchor-v1",
            "source_commit": commit,
            "job_id": job,
            "plan_sha256": plan_sha,
            "predecessor": PARENT,
            **FLAGS,
        },
        "Anchor drift.",
    )
    rows = records["accounting.json"]
    rebuilt, done = accounting(
        (
            "\n".join(
                "|".join([k, v["state"], v["exit_code"], str(v["elapsed_seconds"])])
                for k, v in rows.items()
            )
        ).encode(),
        job,
    )
    require(done and rebuilt == rows, "Terminal accounting required.")
    obs = records["observation.json"]
    status = "missing_observation"
    if obs is not None:
        require(
            obs["source_commit"] == commit and all(obs[k] is False for k in FLAGS),
            "Observation flags/source.",
        )
        if obs["schema_version"] == "s2-allocation-observation-v1":
            require(
                set(obs)
                == {
                    "schema_version",
                    "source_commit",
                    "plan_sha256",
                    "job_id",
                    "local_uid",
                    "local_hostname",
                    "query",
                    "fields",
                    "parse_errors",
                    "checks",
                    "status",
                    *FLAGS,
                },
                "Observation keys.",
            )
            require(
                type(obs["local_uid"]) is int
                and 0 < obs["local_uid"] < 2**32
                and type(obs["local_hostname"]) is str
                and re.fullmatch(r"[A-Za-z0-9_.-]{1,255}", obs["local_hostname"]),
                "Local identity.",
            )
            require(obs["job_id"] == job and obs["plan_sha256"] == plan_sha, "Observation binding.")
            require(set(obs["fields"]) == set(KEYS), "Observed field set.")
            for value in obs["fields"].values():
                require(
                    value is None
                    or (
                        type(value) is str
                        and len(value) <= 256
                        and (
                            value == "<redacted>"
                            or re.fullmatch(r"[A-Za-z0-9_.(),=:+\[\]/-]*", value)
                        )
                    ),
                    "Field export bound.",
                )
            query = obs["query"]
            require(
                set(query)
                == {
                    "status",
                    "returncode",
                    "stdout_bytes",
                    "stderr_bytes",
                    "stdout_prefix_sha256",
                    "stderr_prefix_sha256",
                }
                and query["status"] in {"complete", "timeout", "output_limit"}
                and type(query["returncode"]) is int,
                "Query schema.",
            )
            for key in ("stdout_bytes", "stderr_bytes"):
                require(type(query[key]) is int and query[key] >= 0, "Query byte count.")
            for key in ("stdout_prefix_sha256", "stderr_prefix_sha256"):
                require(re.fullmatch("[0-9a-f]{64}", query[key]), "Query checksum.")
            require(
                type(obs["parse_errors"]) is list
                and len(obs["parse_errors"]) <= 1024
                and all(
                    e in {"non_ascii", "line_or_size"}
                    or e in {prefix + key for prefix in ("duplicate:", "redacted:") for key in KEYS}
                    for e in obs["parse_errors"]
                ),
                "Parse error schema.",
            )
            rebuilt_checks = comparisons(
                obs["fields"], job, obs["local_uid"], obs["local_hostname"]
            )
            require(obs["checks"] == rebuilt_checks, "Comparison drift.")
            matches = (
                obs["query"]["status"] == "complete"
                and obs["query"]["returncode"] == 0
                and not obs["parse_errors"]
                and all(x["matches"] for x in rebuilt_checks.values())
            )
            status = (
                "observed_matching_not_admitted"
                if matches
                else "observed_mismatch_or_query_failure"
            )
            require(obs["status"] == status, "Observation status drift.")
        else:
            require(
                set(obs)
                == {"schema_version", "source_commit", "phase", "status", "error_kind", *FLAGS}
                and obs["phase"] in {"plan", "source_runtime", "query"}
                and obs["error_kind"]
                in {
                    "ValueError",
                    "FileNotFoundError",
                    "PermissionError",
                    "TimeoutError",
                    "KeyboardInterrupt",
                    "other",
                },
                "Diagnostic error schema.",
            )
            require(
                obs["schema_version"] == "s2-allocation-error-v1"
                and obs["status"] == "diagnostic_incomplete",
                "Unknown observation.",
            )
            status = "diagnostic_incomplete"
    return {
        "status": status,
        "source_commit": commit,
        "job_id": job,
        "plan_sha256": plan_sha,
        **FLAGS,
    }


def pack(path, records):
    with path.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, value in records.items():
            raw = encode(value)
            member = tarfile.TarInfo(name)
            member.size = len(raw)
            member.mode = 0o600
            archive.addfile(member, io.BytesIO(raw))


def audit(path, sha, commit, job, plan_sha):
    raw = read(path, 1024**2)
    require(digest(raw) == sha, "Archive checksum.")
    records = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for member in archive:
            require(
                len(records) < 3
                and member.name in {"anchor.json", "observation.json", "accounting.json"}
                and member.name not in records
                and member.isfile()
                and member.size <= LIMIT,
                "Unsafe archive.",
            )
            records[member.name] = json.loads(archive.extractfile(member).read(LIMIT + 1))
    return review(records, commit, job, plan_sha)


def collect(commit):
    host()
    plan, sha = load_plan(commit)
    job_record = load(
        claim_path() / "job.json"
    )  # Absent/ambiguous acknowledgement never guesses a job.
    job = job_record["job_id"]
    require(
        re.fullmatch(r"[1-9][0-9]{0,9}", job)
        and job_record == {"source_commit": commit, "plan_sha256": sha, "job_id": job},
        "Job binding.",
    )
    receipt = claim_path() / "collection.json"
    if receipt.exists():
        saved = load(receipt)
        outcome = audit(Path(saved["archive"]), saved["sha256"], commit, job, sha)
    else:
        acct = Path(plan["tools"]["sacct"])
        require(
            digest(read(acct, 64 * 1024**2)) == plan["tools_sha256"]["sacct"],
            "Accounting tool drift.",
        )
        meta, raw = command(
            [
                str(acct),
                "--noheader",
                "--parsable2",
                "--jobs=" + job,
                "--format=JobIDRaw,State,ExitCode,ElapsedRaw",
            ]
        )
        require(
            meta["status"] == "complete" and meta["returncode"] == 0,
            "Accounting query failed; collect later.",
        )
        rows, done = accounting(raw, job)
        if not done:
            print("DIAGNOSTIC_STATUS=accounting_pending; repeat collect only")
            return 0
        obs = claim_path() / "observation.json"
        records = {
            "anchor.json": {
                "schema_version": "s2-allocation-anchor-v1",
                "source_commit": commit,
                "job_id": job,
                "plan_sha256": sha,
                "predecessor": PARENT,
                **FLAGS,
            },
            "observation.json": load(obs) if obs.exists() else None,
            "accounting.json": rows,
        }
        outcome = review(records, commit, job, sha)
        directory = Path(tempfile.mkdtemp(prefix="collection-", dir=claim_path()))
        archive = directory / "s2-allocation-diagnostic-evidence.tar.gz"
        pack(archive, records)
        saved = {"archive": str(archive), "sha256": digest(read(archive, 1024**2))}
        require(audit(archive, saved["sha256"], commit, job, sha) == outcome, "Archive roundtrip.")
        with Path(str(archive) + ".sha256").open("x", encoding="ascii") as stream:
            stream.write(saved["sha256"] + "  " + archive.name + "\n")
        write_new(receipt, saved)
    print("DIAGNOSTIC_STATUS=" + outcome["status"])
    print("JOB_ID=" + job)
    print("PLAN_SHA256=" + sha)
    print("SHA256=" + saved["sha256"])
    print("DOWNLOAD=" + saved["archive"])
    print("TRANSFER_CHECKSUM=" + saved["archive"] + ".sha256")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "batch", "collect", "audit"))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--plan-sha")
    parser.add_argument("--job")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--sha256")
    args = parser.parse_args()
    require(re.fullmatch("[0-9a-f]{40}", args.source_sha), "Source commit.")
    if args.action == "audit":
        print(
            json.dumps(
                audit(args.archive, args.sha256, args.source_sha, args.job, args.plan_sha), indent=2
            )
        )
        return 0
    try:
        if args.action == "batch":
            require(args.plan_sha is not None, "Batch plan digest required.")
            return batch(args.source_sha, args.plan_sha)
        return {"start": start, "collect": collect}[args.action](args.source_sha)
    finally:
        print("NO_NORMAL_ADVERSE_NATIVE_H300_OR_REPEAT_ADMITTED")


if __name__ == "__main__":
    raise SystemExit(main())
