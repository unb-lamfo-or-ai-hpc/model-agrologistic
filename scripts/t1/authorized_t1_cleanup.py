"""Authorized T1 file-level backup, conditional cache and disposable-copy cleanup.

No recursive removal, scheduler mutation, solver or environment operation.
Scientific originals, claims, controls, active inputs and OSRM are never pruned.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath

PARENT = Path("/home/vrrcelestino")
BASE = PARENT / "model-agrologistic-hygiene-audit"
ROOTS = {
    "model-agrologistic",
    "model-agrologistic-hygiene-audit",
    "model-agrologistic-inputs",
    "model-agrologistic-quarantine",
    "model-agrologistic-scientific-archive",
    "osrm-agrologistic",
}
FORBIDDEN = {
    ".git",
    "secrets",
    ".ssh",
    ".aws",
    ".venv",
    "venv",
    "venv313",
    "venv313_g14",
    "site-packages",
    "node_modules",
}
CACHES = {".ruff_cache", ".pytest_cache", "__pycache__"}
DISPOSABLE = re.compile(
    r"^(?:s2-.*-driver-|scalar-.*-driver-|pyomo-.*-driver-|"
    r"pyomo-scaling-public-cli-|h300-root-cpu(?:-v2)?-source-)"
)
CODE_SUFFIXES = {".py", ".md", ".rst", ".toml", ".yml", ".yaml"}
PROTECTED_PARTS = {
    "data",
    "results",
    "evidence",
    "control",
    "controls",
    "receipts",
    "claims",
    "inputs",
    "outputs",
    "manuscript",
    "supplements",
}
LIMIT = 20 * 1024**3


def require(value, message):
    if not value:
        raise ValueError(message)


def path_parts(name):
    q = PurePosixPath(name)
    require(not q.is_absolute() and len(q.parts) >= 2, "Nonrelative file path")
    require(q.parts[0] in ROOTS, "Root outside approved inventory")
    require(all(s not in ("", ".", "..") for s in q.parts), "Traversal")
    require("\\" not in name and "\x00" not in name, "Invalid path")
    require(not (set(q.parts) & FORBIDDEN), "Protected directory")
    require(
        not any(s == ".env" or s.endswith(".lic") for s in q.parts),
        "Protected credentials",
    )
    require(q.as_posix() == name, "Noncanonical path")
    return q.parts


def cache_path(name):
    return bool(set(path_parts(name)) & CACHES)


def disposable_path(name):
    p = path_parts(name)
    if p[0] != "model-agrologistic-hygiene-audit" or not DISPOSABLE.match(p[1]):
        return False
    if any(s.startswith(".mvp") or s.lower() in PROTECTED_PARTS for s in p[2:]):
        return False
    return PurePosixPath(name).suffix.lower() in CODE_SUFFIXES or p[-1] in {
        "source.tar.gz",
        "cbc.tar.gz",
    }


def parent_fd(name):
    parts = path_parts(name)
    fd = os.open(PARENT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd, parts[-1]
    except BaseException:
        os.close(fd)
        raise


def opened(name):
    parent, leaf = parent_fd(name)
    try:
        fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), "Not a regular file")
        return os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise


def identity(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)


def expected_identity(row):
    return tuple(int(row[k]) for k in ("device", "inode", "logical_bytes", "mtime_ns"))


def checked(row):
    f = opened(row["id"])
    try:
        require(
            identity(os.fstat(f.fileno())) == expected_identity(row),
            "File differs from accepted inventory",
        )
        return f
    except BaseException:
        f.close()
        raise


def digest_stream(f):
    h = hashlib.sha256()
    for block in iter(lambda: f.read(1024**2), b""):
        h.update(block)
    return h.hexdigest()


def hash_row(row):
    with checked(row) as f:
        before = os.fstat(f.fileno())
        checksum = digest_stream(f)
        after = os.fstat(f.fileno())
        require(
            identity(before) == identity(after)
            and before.st_ctime_ns == after.st_ctime_ns,
            "Mutation while reading",
        )
    require(checksum == row["sha256"], "Source hash changed")
    return checksum


def save(path, obj):
    with path.open("x", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def event(stream, obj):
    stream.write(json.dumps(obj, sort_keys=True) + "\n")
    stream.flush()
    os.fsync(stream.fileno())


def queue_empty():
    p = subprocess.run(
        ["squeue", "-u", str(os.getuid()), "-h", "-o", "%i|%T"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    require(p.returncode == 0, "Cannot check scheduler")
    require(
        not p.stdout.strip(), "User jobs present; cleanup retained, no cancellation"
    )


def dependency_gate(controls):
    """Fresh known-control, symlink and same-user process references; no clearance claim."""
    queue_empty()
    refs, omissions = [], []
    used = 0

    def add(value):
        if (
            isinstance(value, str)
            and "\n" not in value
            and "\x00" not in value
            and any(
                value == str(PARENT / r) or value.startswith(str(PARENT / r) + "/")
                for r in ROOTS
            )
        ):
            refs.append(value.rstrip("/"))

    for row in controls:
        try:
            if row["type"] == "symlink":
                fd, leaf = parent_fd(row["id"])
                try:
                    target = os.readlink(leaf, dir_fd=fd)
                finally:
                    os.close(fd)
                if not target.startswith("/"):
                    target = os.path.normpath(str((PARENT / row["id"]).parent / target))
                add(target)
                continue
            with opened(row["id"]) as f:
                s = os.fstat(f.fileno())
                require(
                    s.st_size <= 2 * 1024**2 and used + s.st_size <= 64 * 1024**2,
                    "Control-size budget",
                )
                raw = f.read()
                require(
                    identity(s) == identity(os.fstat(f.fileno())), "Changing control"
                )
                used += len(raw)
            value = json.loads(raw)
            pending, nodes = [value], 0
            while pending:
                nodes += 1
                require(nodes <= 50000, "Control nesting budget")
                v = pending.pop()
                if isinstance(v, str):
                    add(v)
                elif isinstance(v, list):
                    pending.extend(v)
                elif isinstance(v, dict):
                    pending.extend(
                        val
                        for k, val in v.items()
                        if not any(
                            x in str(k).lower()
                            for x in ("secret", "password", "token", "wls")
                        )
                    )
        except (OSError, ValueError) as exc:
            fixture = "tests" in PurePosixPath(row["id"]).parts or any(
                s.startswith("test_") for s in PurePosixPath(row["id"]).parts
            )
            omissions.append(
                {
                    "id": row["id"],
                    "reason": type(exc).__name__,
                    "test_fixture_path": fixture,
                }
            )
    process_refs, process_errors, process_observations = [], [], []
    for p in Path("/proc").iterdir():
        if not p.name.isdigit() or int(p.name) == os.getpid():
            continue
        try:
            if p.stat().st_uid != os.getuid():
                continue
            for key in ("cwd", "exe"):
                try:
                    value = os.readlink(p / key)
                    item = process_reference(
                        "proc_" + key,
                        p.name,
                        value,
                        "directory" if key == "cwd" else "file",
                    )
                    process_observations.append(item)
                    if item["blocks_target_prefix"]:
                        process_refs.append(item["path"])
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    process_errors.append(
                        {"pid": p.name, "scope": key, "reason": type(exc).__name__}
                    )
            try:
                for fd in (p / "fd").iterdir():
                    try:
                        value = os.readlink(fd)
                        target = os.stat(fd)
                        target_type = (
                            "directory"
                            if stat.S_ISDIR(target.st_mode)
                            else "file"
                            if stat.S_ISREG(target.st_mode)
                            else "other"
                        )
                        item = process_reference("proc_fd", p.name, value, target_type)
                        item["fd"] = fd.name
                        process_observations.append(item)
                        if item["blocks_target_prefix"]:
                            process_refs.append(item["path"])
                    except FileNotFoundError:
                        pass
                    except OSError as exc:
                        process_errors.append(
                            {"pid": p.name, "scope": "fd", "reason": type(exc).__name__}
                        )
            except FileNotFoundError:
                pass
            except OSError as exc:
                process_errors.append(
                    {
                        "pid": p.name,
                        "scope": "fd_directory",
                        "reason": type(exc).__name__,
                    }
                )
        except FileNotFoundError:
            pass
        except OSError as exc:
            process_errors.append(
                {"pid": p.name, "scope": "process", "reason": type(exc).__name__}
            )
    return {
        "references": sorted(set(refs)),
        "process_references": sorted(set(process_refs)),
        "process_observations": process_observations,
        "control_omissions": omissions,
        "process_errors": process_errors,
        "scope": "Partial known-control/local same-user observation, not global clearance",
    }


def canonical_reference(value):
    """Reject non-path/ambiguous values without turning root into an empty prefix."""
    if (
        not isinstance(value, str)
        or not value
        or any(c in value for c in ("\x00", "\n", "\r"))
    ):
        return None
    if not value.startswith("/") or value.startswith("//"):
        return None
    q = PurePosixPath(value)
    if ".." in q.parts:
        return None
    return q.as_posix()


def process_reference(kind, pid, value, target_type="unknown"):
    path = canonical_reference(value)
    broad = {"/", PARENT.as_posix(), *((PARENT / r).as_posix() for r in ROOTS)}
    inside = path is not None and any(
        path == (PARENT / r).as_posix()
        or path.startswith((PARENT / r).as_posix() + "/")
        for r in ROOTS
    )
    scope = (
        "not_a_filesystem_path"
        if path is None
        else "broad_directory"
        if path in broad
        else "inventory_path"
        if inside
        else "outside_inventory"
    )
    return {
        "kind": kind,
        "pid": str(pid),
        "path": path,
        "target_type": target_type,
        "scope": scope,
        "blocks_target_prefix": scope == "inventory_path",
    }


def referenced(name, values):
    p = (PARENT / name).as_posix()
    for value in values:
        x = canonical_reference(value)
        if x and x != "/" and (p == x or p.startswith(x.rstrip("/") + "/")):
            return True
    return False


def cleanup_outcome(counts):
    removed = counts["cache_unlinked"] + counts["duplicate_unlinked"]
    if counts["retained"] and not removed:
        return "backup_verified_cleanup_withheld"
    if counts["retained"]:
        return "backup_verified_cleanup_partial"
    return "bounded_cleanup_completed"


def make_archive(path, rows):
    """Ordinary tar members; recovery does not depend on another deduplicated file."""
    with path.open("xb") as raw:
        with (
            gzip.GzipFile(
                filename="", fileobj=raw, mode="wb", compresslevel=1, mtime=0
            ) as gz,
            tarfile.open(fileobj=gz, mode="w|", format=tarfile.PAX_FORMAT) as tar,
        ):
            for i, row in enumerate(rows, 1):
                with checked(row) as f:
                    before = os.fstat(f.fileno())
                    info = tarfile.TarInfo(row["id"])
                    info.size = before.st_size
                    info.mode = stat.S_IMODE(before.st_mode)
                    info.mtime = before.st_mtime_ns // 10**9
                    tar.addfile(info, f)
                    after = os.fstat(f.fileno())
                    require(
                        identity(before) == identity(after)
                        and before.st_ctime_ns == after.st_ctime_ns,
                        "Mutation during backup; no deletion permitted",
                    )
                if i % 1000 == 0:
                    print(json.dumps({"phase": "archive", "files": i}), flush=True)
        raw.flush()
        os.fsync(raw.fileno())


def verify_archive(path, rows):
    expected = {r["id"]: r for r in rows}
    seen = set()
    with tarfile.open(path, "r|gz") as t:
        for m in t:
            require(
                m.isfile() and m.name in expected and m.name not in seen,
                "Unexpected/duplicate/nonregular backup member",
            )
            row = expected[m.name]
            require(m.size == int(row["logical_bytes"]), "Backup size mismatch")
            require(
                digest_stream(t.extractfile(m)) == row["sha256"], "Backup hash mismatch"
            )
            seen.add(m.name)
            if len(seen) % 5000 == 0:
                print(
                    json.dumps({"phase": "verify_archive", "files": len(seen)}),
                    flush=True,
                )
    require(seen == set(expected), "Incomplete backup")
    return seen


def remove_one(row, keeper, journal, backup_sha):
    """Final no-follow, identity/hash checks; never remove a directory or keeper."""
    if keeper:
        require(keeper["id"] != row["id"], "Keeper equals removal target")
        require(keeper["sha256"] == row["sha256"], "Different keeper payload")
        hash_row(keeper)
        require(
            expected_identity(keeper)[:2] != expected_identity(row)[:2],
            "Already hard-linked; no independent allocation to remove",
        )
    hash_row(row)
    fd, leaf = parent_fd(row["id"])
    try:
        require(
            identity(os.stat(leaf, dir_fd=fd, follow_symlinks=False))
            == expected_identity(row),
            "Final target changed",
        )
        event(
            journal,
            {
                "status": "unlink_intent",
                "id": row["id"],
                "sha256": row["sha256"],
                "backup_sha256": backup_sha,
                "keeper": keeper["id"] if keeper else None,
            },
        )
        os.unlink(leaf, dir_fd=fd)
        os.fsync(fd)
        event(
            journal,
            {
                "status": "unlinked",
                "id": row["id"],
                "logical_bytes": int(row["logical_bytes"]),
            },
        )
    finally:
        os.close(fd)


def load_inputs(package):
    manifest = json.loads((package / "package-manifest.json").read_text())
    for name, checksum in manifest["sha256"].items():
        require(
            name
            in {"selection.csv", "dependency-controls.csv", "authorized_t1_cleanup.py"},
            "Unexpected input",
        )
        with (package / name).open("rb") as f:
            require(digest_stream(f) == checksum, "Package member hash mismatch")
    with (package / "selection.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    require(
        len(rows) <= 120000 and len({r["id"] for r in rows}) == len(rows),
        "Invalid selection cardinality",
    )
    require(
        sum(int(r["logical_bytes"]) for r in rows if r["action"] != "keep") <= LIMIT,
        "Backup byte budget",
    )
    for r in rows:
        path_parts(r["id"])
        require(re.fullmatch("[a-f0-9]{64}", r["sha256"]), "Invalid hash")
        require(
            r["action"] in {"keep", "cache", "duplicate", "archive"}, "Unknown action"
        )
        if r["action"] == "cache":
            require(cache_path(r["id"]), "Cache action outside cache")
        if r["action"] == "duplicate":
            require(disposable_path(r["id"]), "Protected scientific/original duplicate")
    with (package / "dependency-controls.csv").open(newline="", encoding="utf-8") as f:
        controls = list(csv.DictReader(f))
    require(len(controls) <= 20000, "Dependency control budget")
    lookup = {r["id"]: r for r in rows}
    for r in rows:
        if r["action"] == "duplicate":
            k = lookup[r["keeper"]]
            require(
                k["action"] in {"keep", "archive"} and k["sha256"] == r["sha256"],
                "Keeper must be retained and content-identical",
            )
    return manifest, rows, controls


def run(args):
    require(
        sys.platform == "linux" and not os.environ.get("SLURM_JOB_ID"),
        "Linux login shell only",
    )
    require(BASE.is_dir() and not BASE.is_symlink(), "Invalid audit base")
    package = Path(__file__).resolve().parent
    with (package / "package-manifest.json").open("rb") as f:
        require(digest_stream(f) == args.manifest_sha256, "Unpinned private plan")
    manifest, rows, controls = load_inputs(package)
    import fcntl

    lock = (BASE / ".t1-authorized-cleanup.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    import tempfile

    out = Path(tempfile.mkdtemp(prefix="t1-authorized-cleanup-", dir=BASE))
    os.chmod(out, 0o700)
    print("PRESERVE_CLEANUP=" + str(out), flush=True)
    save(
        out / "authorization.json",
        {
            "date": "2026-11-23",
            "scope": manifest["scope"],
            "manifest_sha256": args.manifest_sha256,
            "source": "Researcher explicitly requested cache/duplicate deletion and compression",
            "automatic_job_or_merge": False,
        },
    )
    gate = dependency_gate(controls)
    save(out / "dependencies-before.json", gate)
    archive_rows = [r for r in rows if r["action"] != "keep"]
    required = sum(int(r["logical_bytes"]) for r in archive_rows)
    require(
        shutil.disk_usage(BASE).free > required + 1024**3,
        "Insufficient free filesystem space",
    )
    # A complete, independently verified backup is mandatory before any unlink.
    archive = out / "historical-files-and-cache.tar.gz"
    make_archive(archive, archive_rows)
    verified = verify_archive(archive, archive_rows)
    with archive.open("rb") as f:
        backup_sha = digest_stream(f)
    (out / "historical-files-and-cache.tar.gz.sha256").write_text(
        backup_sha + "  " + archive.name + "\n", encoding="utf-8"
    )
    save(
        out / "verified-backup.json",
        {
            "sha256": backup_sha,
            "members": len(verified),
            "source_logical_bytes": required,
            "archive_bytes": archive.stat().st_size,
            "independent_member_hash_check": True,
            "coverage": "Listed regular files only; not a complete directory or SQLite snapshot",
        },
    )
    # Keep a path/hash/metadata inventory next to the archive.
    shutil.copyfile(package / "selection.csv", out / "selection.csv")
    gate = dependency_gate(controls)
    save(out / "dependencies-after-backup.json", gate)
    lookup = {r["id"]: r for r in rows}
    counts = {
        "cache_unlinked": 0,
        "duplicate_unlinked": 0,
        "retained": 0,
        "logical_bytes_unlinked": 0,
    }
    with (out / "actions.jsonl").open("x", encoding="utf-8") as journal:
        for i, row in enumerate(
            r for r in rows if r["action"] in {"cache", "duplicate"}
        ):
            try:
                if i % 1000 == 0:
                    gate = dependency_gate(controls)
                    save(out / f"dependencies-prune-{i:06d}.json", gate)
                require(row["id"] in verified, "Target lacks verified backup")
                require(
                    not referenced(row["id"], gate["process_references"]),
                    "Observed process dependency",
                )
                if row["action"] == "duplicate":
                    require(not gate["process_errors"], "Incomplete process visibility")
                    require(
                        not any(
                            not x["test_fixture_path"]
                            for x in gate["control_omissions"]
                        ),
                        "Unresolved non-test control omissions",
                    )
                    require(
                        not referenced(row["id"], gate["references"]),
                        "Observed control or symlink dependency",
                    )
                    keeper = lookup[row["keeper"]]
                else:
                    keeper = None
                remove_one(row, keeper, journal, backup_sha)
                counts[row["action"] + "_unlinked"] += 1
                counts["logical_bytes_unlinked"] += int(row["logical_bytes"])
            except (OSError, ValueError, KeyError) as exc:
                counts["retained"] += 1
                event(
                    journal, {"status": "retained", "id": row["id"], "reason": str(exc)}
                )
    save(
        out / "cleanup-result.json",
        {
            "status": cleanup_outcome(counts),
            **counts,
            "backup": str(archive),
            "backup_sha256": backup_sha,
            "environment_changed": False,
            "jobs_submitted": 0,
            "original_claims_and_scientific_vectors_pruned": False,
            "space_note": "Logical bytes unlinked are not measured physical free-space gain",
        },
    )
    files = sorted(p for p in out.iterdir() if p.is_file() and p.name != archive.name)
    ledger = ""
    for p in files:
        with p.open("rb") as f:
            ledger += digest_stream(f) + "  " + p.name + "\n"
    (out / "REPORT_SHA256SUMS").write_text(ledger, encoding="utf-8")
    with tarfile.open(out / "cleanup-reports.tar.gz", "x:gz") as t:
        for p in files + [out / "REPORT_SHA256SUMS"]:
            t.add(p, arcname=p.name, recursive=False)
    with (out / "cleanup-reports.tar.gz").open("rb") as f:
        report_sha = digest_stream(f)
    (out / "cleanup-reports.tar.gz.sha256").write_text(
        report_sha + "  cleanup-reports.tar.gz\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "report_sha256": report_sha,
                "result": str(out / "cleanup-result.json"),
                "reports": str(out / "cleanup-reports.tar.gz"),
                "preserve_backup": str(archive),
                **counts,
            },
            indent=2,
        ),
        flush=True,
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest-sha256", required=True)
    p.add_argument(
        "--apply",
        action="store_true",
        help="Explicit mutation mode; use the separate read-only probe first",
    )
    args = p.parse_args()
    require(re.fullmatch("[a-f0-9]{64}", args.manifest_sha256), "Invalid manifest SHA")
    require(args.apply, "No implicit cleanup; run the read-only retention probe first")
    run(args)


if __name__ == "__main__":
    main()
