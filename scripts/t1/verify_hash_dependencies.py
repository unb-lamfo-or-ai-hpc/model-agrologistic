"""Read-only, bounded source-hash and dependency evidence for T1; no cleanup."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import time
import uuid

PARENT = pathlib.Path("/home/vrrcelestino")
BASE = PARENT / "model-agrologistic-hygiene-audit"
ROOTS = {
    "model-agrologistic",
    "model-agrologistic-hygiene-audit",
    "model-agrologistic-inputs",
    "model-agrologistic-quarantine",
    "model-agrologistic-scientific-archive",
    "osrm-agrologistic",
}
ARCHIVE_SHA = "c0127ce8c9fe76409ab192f877eaf05213d39eb560a78579db95fb116a8d59d0"
OPAQUE = {
    ".git",
    ".ssh",
    ".aws",
    "secrets",
    ".venv",
    "venv",
    "venv313",
    "venv313_g14",
    "node_modules",
    "site-packages",
}
CANDIDATES = {"ARCHIVE_PROPOSAL", "DELETION_CANDIDATE"}
JOBS_TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"}
MAX_SOURCE_FILE = 512 * 1024**2


def digest(path):
    with pathlib.Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def publish(path, obj):
    raw = (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with pathlib.Path(path).open("xb") as stream:
        stream.write(raw)


def load(path):
    return json.loads(pathlib.Path(path).read_bytes())


def key(row):
    return row["root"] + "/" + row["relative_path"]


def workspace(path):
    p = pathlib.Path(path)
    if p.is_symlink() or not p.is_dir() or BASE.is_symlink():
        raise ValueError("invalid_audit_workspace")
    if p.resolve().parent != BASE.resolve():
        raise ValueError("workspace_outside_audit_project")
    return p


def fingerprint(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def expected_metadata(s, row):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns) == tuple(
        int(row[n]) for n in ("device", "inode", "logical_bytes", "mtime_ns")
    )


def source_path(row):
    if row["root"] not in ROOTS:
        raise ValueError("unapproved_root")
    rel = pathlib.PurePosixPath(row["relative_path"])
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError("unsafe_relative_path")
    if any(p in OPAQUE for p in rel.parts):
        raise ValueError("opaque_or_sensitive_scope")
    name = rel.name.lower()
    if name.endswith((".lic", ".key", ".pem")) or name.startswith(".env"):
        raise ValueError("sensitive_file")
    return PARENT / row["root"] / pathlib.Path(*rel.parts)


def open_source(row):
    """Linux: open every directory and final regular file without following links."""
    path = source_path(row)
    if sys.platform != "linux":
        raise ValueError("linux_source_verification_only")
    root = PARENT / row["root"]
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open(root, flags)
    try:
        rel = pathlib.PurePosixPath(row["relative_path"])
        for part in rel.parts[:-1]:
            child = os.open(part, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(rel.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            os.close(fd)
            raise ValueError("source_not_regular")
        return fd, info, path
    finally:
        os.close(directory)


def stable_read(row, *, want_bytes=False):
    fd, before, path = open_source(row)
    try:
        if not expected_metadata(before, row):
            return None, "changed_since_inventory", 0
        if before.st_size > (4 * 1024**2 if want_bytes else MAX_SOURCE_FILE):
            return None, "source_size_guard", 0
        h = hashlib.sha256()
        content = bytearray()
        count = 0
        while chunk := os.read(fd, 1024**2):
            count += len(chunk)
            if count > before.st_size:
                return None, "source_grew_during_read", count
            h.update(chunk)
            if want_bytes:
                content.extend(chunk)
        after = os.fstat(fd)
        current = path.lstat()
        if (
            fingerprint(before) != fingerprint(after)
            or fingerprint(after) != fingerprint(current)
            or count != before.st_size
        ):
            return None, "changed_during_read", count
        return (bytes(content) if want_bytes else h.hexdigest()), "stable", count
    finally:
        os.close(fd)


def prepare(args):
    out = workspace(args.workspace)
    if any(out.iterdir()):
        raise ValueError("preserve_existing_workspace_use_verify_or_collect")
    if digest(args.inventory) != ARCHIVE_SHA:
        raise ValueError("inventory_archive_hash_mismatch")
    source = pathlib.Path(__file__).resolve().parent
    names = (
        "audit_inventory_bundle.py",
        "classify_inventory_metadata.py",
        pathlib.Path(__file__).name,
    )
    identities = {n: digest(source / n) for n in names}
    review = out / "metadata"
    for script, extra in (
        ("audit_inventory_bundle.py", [str(args.inventory), str(review)]),
        ("classify_inventory_metadata.py", [str(review)]),
    ):
        result = subprocess.run(
            [sys.executable, "-B", "-I", "-S", str(source / script), *extra],
            capture_output=True,
            check=False,
            timeout=600,
        )
        (out / (script + ".stdout")).write_bytes(result.stdout)
        (out / (script + ".stderr")).write_bytes(result.stderr)
        if result.returncode:
            raise ValueError("metadata_review_failed_preserve_outputs")
    with (review / "path-classification.csv").open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["type"] == "file"]
    selected = [r for r in rows if r["classification"] in CANDIDATES]
    signatures = {
        (pathlib.PurePosixPath(r["relative_path"]).name, r["logical_bytes"]) for r in selected
    }
    comparisons = [
        r
        for r in rows
        if r["classification"] == "ACTIVE_KEEP"
        and (pathlib.PurePosixPath(r["relative_path"]).name, r["logical_bytes"]) in signatures
    ]
    plan = {
        "schema": "npad-t1-hash-dependency-plan-v1",
        "source_sha": args.source_sha,
        "source_directory": str(source),
        "source_files": identities,
        "inventory_sha256": ARCHIVE_SHA,
        "classification_csv_sha256": digest(review / "path-classification.csv"),
        "target_count": len(selected),
        "comparison_count": len(comparisons),
        "hash_scope": "Archival/cache candidates plus equal-name/size retained comparisons",
        "source_root_allowlist": sorted(ROOTS),
        "original_contents_exported": False,
        "deletion_authorized": False,
        "archive_action_authorized": False,
    }
    publish(out / "plan.json", plan)
    print(
        json.dumps(
            {
                "status": "prepared_no_job",
                "workspace": str(out),
                "plan_sha256": digest(out / "plan.json"),
                "targets": len(selected),
                "comparisons": len(comparisons),
            },
            indent=2,
        )
    )


def read_rows(out, plan):
    source = pathlib.Path(plan["source_directory"])
    for name, expected in plan["source_files"].items():
        if digest(source / name) != expected:
            raise ValueError("source_changed")
    csvpath = out / "metadata" / "path-classification.csv"
    if digest(csvpath) != plan["classification_csv_sha256"]:
        raise ValueError("classification_changed")
    with csvpath.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def command(argv):
    if not argv or argv[0] not in {"squeue", "scontrol"}:
        raise ValueError("only_readonly_scheduler_commands")
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def read_symlink(row):
    path = source_path(row)
    directory = os.open(PARENT / row["root"], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    rel = pathlib.PurePosixPath(row["relative_path"])
    try:
        for part in rel.parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        before = os.stat(rel.name, dir_fd=directory, follow_symlinks=False)
        if not stat.S_ISLNK(before.st_mode) or not expected_metadata(before, row):
            raise ValueError("symlink_changed_since_inventory")
        target = os.readlink(rel.name, dir_fd=directory)
        after = os.stat(rel.name, dir_fd=directory, follow_symlinks=False)
        if fingerprint(before) != fingerprint(after):
            raise ValueError("symlink_changed_during_read")
        return os.path.normpath(str(path.parent / target)) if not target.startswith("/") else target
    finally:
        os.close(directory)


def completed_records(out):
    done, incomplete = set(), []
    for old in sorted(out.glob("readback-*/hashes.jsonl")):
        raw = old.read_bytes()
        lines = raw.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if i == len(lines) - 1 and not line.endswith(b"\n"):
                incomplete.append(old.relative_to(out).as_posix())
                continue
            done.add(json.loads(line)["id"])
    return done, incomplete


def dependency_snapshot(out, rows):
    """Partial evidence only: own visible processes, queue and bounded control JSONs."""
    refs = []
    dependency_started = time.monotonic()
    coverage = {
        "proc_processes_seen": 0,
        "proc_unreadable_entries": 0,
        "control_jsons_read": 0,
        "control_bytes_read": 0,
        "control_jsons_omitted": 0,
        "symlink_references_read": 0,
        "symlink_references_unreadable": 0,
        "dependency_time_guard": False,
    }

    def add(kind, origin, value):
        if not isinstance(value, str):
            return
        for root in ROOTS:
            prefix = str(PARENT / root)
            # Only retain an actual absolute path, not arbitrary command/credential text.
            if value == prefix or value.startswith(prefix + "/"):
                if "\n" not in value and "\x00" not in value and len(value) <= 4096:
                    refs.append({"kind": kind, "origin": origin, "path": value})
                return

    queue = command(
        ["squeue", "-u", __import__("pwd").getpwuid(os.getuid()).pw_name, "-h", "-o", "%i|%T|%j"]
    )
    ids = []
    if queue is not None:
        coverage["queue_unparsed_lines"] = 0
        coverage["queue_array_group_tokens"] = 0
        for line in queue.splitlines():
            job = line.split("|", 1)[0]
            if re.fullmatch(r"[0-9]+(?:_[0-9]+)?", job):
                ids.append(job)
            elif re.fullmatch(r"[0-9]+_\[[0-9,%: -]+\]", job):
                ids.append(job.split("_", 1)[0])
                coverage["queue_array_group_tokens"] += 1
            else:
                coverage["queue_unparsed_lines"] += 1
        ids = sorted(set(ids))
        coverage["queue_jobs_not_inspected"] = max(0, len(ids) - 10)
        for job in ids[:10]:
            text = command(["scontrol", "show", "job", "--oneliner", job])
            if text:
                fields = dict(re.findall(r"(\w+)=(.*?)(?=\s+\w+=|$)", text.strip()))
                for name in ("WorkDir", "StdOut", "StdErr"):
                    add("slurm_" + name, job, fields.get(name))
                command_path = fields.get("Command", "").split(" ", 1)[0]
                add("slurm_command_path", job, command_path)
    proc = pathlib.Path("/proc")
    if proc.is_dir():
        for process in proc.iterdir():
            if time.monotonic() - dependency_started > 90:
                coverage["dependency_time_guard"] = True
                break
            if not process.name.isdigit():
                continue
            try:
                if process.stat().st_uid != os.getuid() or int(process.name) == os.getpid():
                    continue
                coverage["proc_processes_seen"] += 1
                for name in ("cwd", "exe"):
                    try:
                        add("proc_" + name, process.name, os.readlink(process / name))
                    except OSError:
                        coverage["proc_unreadable_entries"] += 1
                try:
                    for fd_number, fd in enumerate((process / "fd").iterdir()):
                        if fd_number >= 10000 or time.monotonic() - dependency_started > 90:
                            coverage["dependency_time_guard"] = True
                            break
                        try:
                            add("proc_fd", process.name, os.readlink(fd))
                        except OSError:
                            coverage["proc_unreadable_entries"] += 1
                except OSError:
                    coverage["proc_unreadable_entries"] += 1
            except OSError:
                coverage["proc_unreadable_entries"] += 1
    for row in rows:
        if time.monotonic() - dependency_started > 300:
            coverage["dependency_time_guard"] = True
            break
        if row["type"] == "symlink":
            try:
                target = read_symlink(row)
                add("inventory_symlink_target", key(row), target)
                coverage["symlink_references_read"] += 1
            except (OSError, ValueError):
                coverage["symlink_references_unreadable"] += 1
            continue
        if row["rule"] not in {"consumed_claim_control", "migration_or_inventory_dependency"}:
            continue
        if not row["relative_path"].endswith(".json"):
            continue
        if coverage["control_bytes_read"] + int(row["logical_bytes"]) > 64 * 1024**2:
            coverage["control_jsons_omitted"] += 1
            continue
        try:
            raw, status, count = stable_read(row, want_bytes=True)
            coverage["control_bytes_read"] += count
            if status != "stable":
                coverage["control_jsons_omitted"] += 1
                continue
            data = json.loads(raw)
            coverage["control_jsons_read"] += 1
            pending = [data]
            nodes = 0
            while pending and nodes < 50000:
                v = pending.pop()
                nodes += 1
                if isinstance(v, str):
                    add("declared_control_path", key(row), v)
                elif isinstance(v, dict):
                    pending.extend(
                        value
                        for k, value in v.items()
                        if not any(
                            x in str(k).lower() for x in ("secret", "password", "token", "wls")
                        )
                    )
                elif isinstance(v, list):
                    pending.extend(v)
            if pending:
                coverage["control_jsons_omitted"] += 1
        except (OSError, ValueError):
            coverage["control_jsons_omitted"] += 1
    result = {
        "scope": "Partial evidence, never dependency clearance",
        "observed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "queue_query_succeeded": queue is not None,
        "queue_job_ids": ids,
        "coverage": coverage,
        "references": refs,
        "git_clean_or_tracked_status": "not qualified; Git is not invoked",
        "remote_nodes_other_users_containers_and_closed_dependencies": "not fully observable",
        "deletion_authorized": False,
        "archive_action_authorized": False,
    }
    publish(out / "dependencies.json", result)
    return result


def intersects(path, reference):
    return path == reference or path.startswith(reference.rstrip("/") + "/")


def has_reference(path, references):
    p = pathlib.PurePosixPath(path)
    return any(parent.as_posix() in references for parent in (p, *p.parents))


def verify(args):
    out = workspace(args.workspace)
    plan = load(out / "plan.json")
    rows = read_rows(out, plan)
    selected = [r for r in rows if r["classification"] in CANDIDATES]
    signatures = {
        (pathlib.PurePosixPath(r["relative_path"]).name, r["logical_bytes"]) for r in selected
    }
    selected += [
        r
        for r in rows
        if r["classification"] == "ACTIVE_KEEP"
        and (pathlib.PurePosixPath(r["relative_path"]).name, r["logical_bytes"]) in signatures
    ]
    import fcntl  # Linux standard library; no package installation or source modification.

    with (out / "workspace.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run = out / ("readback-" + uuid.uuid4().hex[:12])
        run.mkdir()
        deps = dependency_snapshot(run, rows)
        done, incomplete_journals = completed_records(out)
        current_paths = {os.path.normpath(r["path"]).rstrip("/") for r in deps["references"]}
        start, used, count = time.monotonic(), 0, 0
        statuses = {}
        with (run / "hashes.jsonl").open("x", encoding="utf-8") as journal:
            for row in selected:
                if key(row) in done:
                    continue
                n = int(row["logical_bytes"])
                if (
                    count >= args.max_files
                    or time.monotonic() - start >= args.max_seconds
                    or used + n > args.max_gib * 1024**3
                ):
                    break
                status, checksum, readbytes = "not_read", None, 0
                name = pathlib.PurePosixPath(row["relative_path"]).name.lower()
                if name.endswith((".db", ".sqlite", ".sqlite3", "-wal", "-shm")):
                    status = "database_requires_consistent_snapshot"
                elif n > MAX_SOURCE_FILE:
                    status = "source_size_guard"
                else:
                    try:
                        checksum, status, readbytes = stable_read(row)
                    except (OSError, ValueError) as ex:
                        status = "unreadable_or_unsafe_" + type(ex).__name__
                used += readbytes
                count += 1
                path = str(PARENT / row["root"] / row["relative_path"])
                rec = {
                    "id": key(row),
                    "classification": row["classification"],
                    "status": status,
                    "sha256": checksum,
                    "bytes_read": readbytes,
                    "inventory_device": row["device"],
                    "inventory_inode": row["inode"],
                    "inventory_bytes": n,
                    "possible_dependency_reference": has_reference(path, current_paths),
                    "deletion_authorized": False,
                    "archive_action_authorized": False,
                }
                journal.write(json.dumps(rec, sort_keys=True) + "\n")
                journal.flush()
                done.add(rec["id"])
                statuses[status] = statuses.get(status, 0) + 1
        summary = {
            "status": "finite_scope_read_complete"
            if len(done) == len(selected)
            else "partial_readback_resume_same_verify_command",
            "targets_and_retained_comparisons": len(selected),
            "records_observed_across_readbacks": len(done),
            "this_readback_records": count,
            "bytes_read_this_readback": used,
            "this_readback_statuses": statuses,
            "incomplete_prior_journals": incomplete_journals,
            "readback": str(run),
            "plan_sha256": digest(out / "plan.json"),
            "proof_scope": "Stable observed hashes at read time; references are partial",
            "repeat_warning": (
                "Existing journal records are preserved and not retried automatically"
            ),
            "deletion_authorized": False,
            "archive_action_authorized": False,
        }
        publish(run / "summary.json", summary)
        print(json.dumps(summary, indent=2))


def collect(args):
    out = workspace(args.workspace)
    plan = load(out / "plan.json")
    read_rows(out, plan)
    # Only derived reports, not original source data.
    import tarfile

    name = "t1-hashdeps-reports-" + uuid.uuid4().hex[:12] + ".tar.gz"
    target = out / name
    files = [out / "plan.json"]
    files += list(out.glob("*.stdout")) + list(out.glob("*.stderr"))
    for run in sorted(out.glob("readback-*")):
        files += [p for p in run.iterdir() if p.is_file() and not p.is_symlink()]
    manifest = out / ("report-manifest-" + uuid.uuid4().hex[:12] + ".txt")
    with manifest.open("x") as stream:
        for p in sorted(files):
            stream.write(digest(p) + "  " + p.relative_to(out).as_posix() + "\n")
    files.append(manifest)
    with tarfile.open(target, "x:gz") as archive:
        for p in files:
            archive.add(p, arcname=str(p.relative_to(out)), recursive=False)
    checksum = digest(target)
    with target.with_name(name + ".sha256").open("x") as stream:
        stream.write(checksum + "  " + name + "\n")
    print(
        json.dumps(
            {
                "archive": str(target),
                "sha256": checksum,
                "sidecar": str(target) + ".sha256",
                "original_source_files_included": False,
            },
            indent=2,
        )
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("prepare", "verify", "collect"))
    p.add_argument("--workspace", type=pathlib.Path, required=True)
    p.add_argument("--inventory", type=pathlib.Path)
    p.add_argument("--source-sha")
    p.add_argument("--max-gib", type=int, default=24)
    p.add_argument("--max-files", type=int, default=150000)
    p.add_argument("--max-seconds", type=int, default=900)
    args = p.parse_args()
    if sys.platform != "linux" or os.environ.get("SLURM_JOB_ID"):
        p.error("Run from the Linux login shell only; no job or solver is started.")
    if args.action == "prepare" and (
        args.inventory is None
        or not args.source_sha
        or re.fullmatch(r"[0-9a-f]{40}", args.source_sha) is None
    ):
        p.error("Prepare requires a pinned inventory and full source SHA.")
    if min(args.max_gib, args.max_files, args.max_seconds) <= 0:
        p.error("Positive finite read budgets required.")
    {"prepare": prepare, "verify": verify, "collect": collect}[args.action](args)


if __name__ == "__main__":
    main()
