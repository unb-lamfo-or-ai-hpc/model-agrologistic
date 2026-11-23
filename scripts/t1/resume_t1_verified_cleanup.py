"""Resume authorized finite cleanup using the existing verified backup only."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "retention_probe", HERE / "inspect_t1_cleanup_retention.py"
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
m = probe.m
DIAG_SHA = "7be1b4a77bdc13a1dedc3080f9d2e5aff6af1fe68b8a2371afb34add8e9a71b5"
MANIFEST_SHA = "13c3309d59189ae7196f13c3c98736492f58676bebab985a9a7e115716475f7f"
BACKUP_SHA = "d093e7defbca502ccc3c7e27a827f6baab13c1bdf14370cc9fca3133c7df1dd0"
EXPECTED_MEMBERS = 110705
EXPECTED_TARGETS = 8449


def proc_status(pid):
    m.require(re.fullmatch("[0-9]+", str(pid)) is not None, "Invalid PID")
    p = Path("/proc") / str(pid)
    try:
        raw = (p / "status").read_text()[:65536]
        fields = {
            k: v.strip()
            for line in raw.splitlines()
            if ":" in line
            for k, v in [line.split(":", 1)]
            if k in {"Name", "PPid", "Uid", "State"}
        }
        fields["pid"] = str(pid)
        fields["proc_directory_uid"] = p.stat().st_uid
        return fields
    except FileNotFoundError:
        return {"pid": str(pid), "gone": True}
    except OSError as exc:
        return {"pid": str(pid), "error": type(exc).__name__}


def user_session_exception(child, parent, uid):
    """Explicit bounded infrastructure exception; never a general PID-name allowlist."""
    try:
        child_uids = [int(x) for x in child["Uid"].split()]
        parent_uids = [int(x) for x in parent["Uid"].split()]
        if len(child_uids) != 4 or any(x != uid for x in child_uids):
            return None
        if child["proc_directory_uid"] != uid or child["PPid"] != parent["pid"]:
            return None
        if (
            child["Name"] == "sshd"
            and parent["Name"] == "sshd"
            and len(parent_uids) == 4
            and all(x == 0 for x in parent_uids)
            and parent["proc_directory_uid"] == 0
        ):
            return "user_ssh_session_with_root_sshd_parent"
        if (
            child["Name"] == "(sd-pam)"
            and parent["Name"] == "systemd"
            and len(parent_uids) == 4
            and all(x == uid for x in parent_uids)
            and parent["proc_directory_uid"] == uid
        ):
            return "user_pam_helper_with_same_user_systemd_parent"
    except (KeyError, TypeError, ValueError):
        pass
    return None


def active_sftp_processes():
    found = []
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():
            continue
        try:
            if p.stat().st_uid != os.getuid():
                continue
        except FileNotFoundError:
            continue
        item = proc_status(p.name)
        if item.get("Name") == "sftp-server":
            found.append(item)
    return found


def classify_process_errors(errors):
    result = []
    for pid in sorted({x["pid"] for x in errors}):
        child = proc_status(pid)
        if child.get("gone"):
            result.append({"pid": pid, "classification": "no_longer_visible"})
            continue
        parent = proc_status(child["PPid"]) if child.get("PPid") else {}
        why = user_session_exception(child, parent, os.getuid())
        result.append(
            {
                "pid": pid,
                "child": child,
                "parent": parent,
                "classification": why or "unresolved_inaccessible_process",
            }
        )
    return result


def digest_path(path):
    with m.opened(path.relative_to(m.PARENT).as_posix()) as f:
        before = os.fstat(f.fileno())
        sha = m.digest_stream(f)
        after = os.fstat(f.fileno())
        m.require(
            m.identity(before) == m.identity(after)
            and before.st_ctime_ns == after.st_ctime_ns,
            "File changed while hashing",
        )
    return sha, before


def read_diagnosis(path):
    m.require(digest_path(path)[0] == DIAG_SHA, "Unexpected targeted diagnosis archive")
    files = {}
    with (
        m.opened(path.relative_to(m.PARENT).as_posix()) as f,
        tarfile.open(fileobj=f, mode="r:gz") as t,
    ):
        for item in t:
            m.require(
                item.isfile()
                and item.name
                in {"retention-diagnosis.json", "source-identity.json", "SHA256SUMS"}
                and item.name not in files
                and item.size <= 2 * 1024**2,
                "Invalid diagnosis member",
            )
            files[item.name] = t.extractfile(item).read()
    m.require(
        set(files)
        == {"retention-diagnosis.json", "source-identity.json", "SHA256SUMS"},
        "Incomplete diagnosis",
    )
    names = set()
    for line in files["SHA256SUMS"].decode().splitlines():
        sha, name = line.split("  ", 1)
        m.require(
            name in files and name not in names and name != "SHA256SUMS",
            "Invalid diagnosis ledger",
        )
        m.require(
            hashlib.sha256(files[name]).hexdigest() == sha, "Diagnosis ledger mismatch"
        )
        names.add(name)
    m.require(
        names == {"retention-diagnosis.json", "source-identity.json"},
        "Diagnosis ledger scope",
    )
    result = json.loads(files["retention-diagnosis.json"])
    m.require(
        result["original_report_sha256"] == probe.REPORT_SHA
        and result["cleanup_invoked"] is False,
        "Diagnosis lineage mismatch",
    )
    return result


def known_omissions(omissions, diagnosis):
    known = {r["id"]: r for r in diagnosis["current_control_metadata"]}
    result = []
    for row in omissions:
        old = known.get(row["id"])
        m.require(old is not None, "New/unclassified control omission")
        current = probe.control_metadata(row)
        m.require(
            current.get("sha256") == old.get("sha256")
            and current.get("bytes") == old.get("bytes"),
            "Omitted control changed",
        )
        if current.get("bytes") == 0:
            m.require(
                current["sha256"] == hashlib.sha256(b"").hexdigest(),
                "Invalid empty control",
            )
            kind = "verified_empty_historical_output_preserved"
        else:
            m.require(
                row["test_fixture_path"] and old["test_fixture_path"],
                "Unknown nonempty invalid control",
            )
            m.require(
                old.get("current_status") == "nonempty_invalid_json_preserved",
                "Invalid fixture provenance",
            )
            kind = "exact_hash_known_malformed_test_fixture_preserved"
        result.append(
            {"id": row["id"], "classification": kind, "sha256": current["sha256"]}
        )
    return result


def eligible(row, gate, controlled_omissions, process_classifications):
    if m.referenced(row["id"], gate["process_references"]):
        return "specific_process_reference"
    if row["action"] == "duplicate":
        if m.referenced(row["id"], gate["references"]):
            return "specific_control_or_symlink_reference"
        if len(controlled_omissions) != len(gate["control_omissions"]):
            return "unresolved_control_omission"
        if any(
            x["classification"] == "unresolved_inaccessible_process"
            for x in process_classifications
        ):
            return "unresolved_inaccessible_process"
    return None


def run(args):
    m.require(
        sys.platform == "linux"
        and sys.flags.isolated
        and sys.flags.no_site
        and sys.dont_write_bytecode
        and not os.environ.get("SLURM_JOB_ID"),
        "Linux login shell with -B -I -S only",
    )
    original = Path(args.original_run)
    package = Path(args.original_package)
    diagnosis_path = Path(args.diagnosis_archive)
    for path in (original, package, diagnosis_path.parent):
        m.require(
            path.is_absolute() and path.parent == m.BASE,
            "Paths must be direct audit-root children",
        )
    m.require(args.apply, "Explicit --apply required")
    import fcntl

    lock = (m.BASE / ".t1-authorized-cleanup.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    m.queue_empty()
    transfers = active_sftp_processes()
    if transfers:
        print(
            json.dumps(
                {
                    "status": "withheld_before_cleanup",
                    "reason": "active_sftp_sessions",
                    "sftp_session_count": len(transfers),
                    "instruction": "Close SFTP/WinSCP transfer sessions; keep the SSH terminal.",
                    "files_removed": 0,
                    "backup_recreated": False,
                }
            ),
            flush=True,
        )
        return 3

    with m.opened(
        (package / "package-manifest.json").relative_to(m.PARENT).as_posix()
    ) as f:
        m.require(m.digest_stream(f) == MANIFEST_SHA, "Original plan manifest mismatch")
    _, rows, controls = m.load_inputs(package)
    # Read only the original package; never import/run its old cleanup helper.
    files, _ = probe.read_report(original / "cleanup-reports.tar.gz")
    m.require(
        files["selection.csv"] == (package / "selection.csv").read_bytes(),
        "Original selection differs from accepted report",
    )
    receipt = json.loads(files["verified-backup.json"])
    m.require(
        receipt["sha256"] == BACKUP_SHA
        and receipt["members"] == EXPECTED_MEMBERS
        and receipt["independent_member_hash_check"] is True,
        "Backup receipt mismatch",
    )
    m.require(
        json.loads(files["cleanup-result.json"])["logical_bytes_unlinked"] == 0,
        "Unexpected original removal history",
    )
    diagnosis = read_diagnosis(diagnosis_path)
    out = Path(tempfile.mkdtemp(prefix="t1-reuse-backup-cleanup-", dir=m.BASE))
    os.chmod(out, 0o700)
    print("PRESERVE_CLEANUP=" + str(out), flush=True)
    m.save(
        out / "source-identity.json",
        {
            "original_manifest_sha256": MANIFEST_SHA,
            "original_report_sha256": probe.REPORT_SHA,
            "diagnosis_sha256": DIAG_SHA,
            "files": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (
                    Path(__file__),
                    HERE / "authorized_t1_cleanup.py",
                    HERE / "inspect_t1_cleanup_retention.py",
                )
            },
            "scope": "Authorized caches/disposable copies only; no new source archive",
        },
    )

    def gate_snapshot(index):
        m.queue_empty()
        m.require(not active_sftp_processes(), "SFTP session appeared; stop pruning")
        g = m.dependency_gate(controls)
        omitted = known_omissions(g["control_omissions"], diagnosis)
        classes = classify_process_errors(g["process_errors"])
        m.save(
            out / f"gate-{index:05d}.json",
            {
                "gate": g,
                "classified_control_omissions": omitted,
                "classified_process_errors": classes,
                "limitations": "SSH/PAM lineage exceptions are bounded infrastructure exceptions, not global dependency clearance",
            },
        )
        return g, omitted, classes

    gate, omitted, classes = gate_snapshot(0)
    backup = original / "historical-files-and-cache.tar.gz"
    print(
        '{"phase":"verify_existing_backup_sha256","new_compression":false}', flush=True
    )
    checksum, backup_stat = digest_path(backup)
    m.require(
        checksum == BACKUP_SHA and backup_stat.st_size == receipt["archive_bytes"],
        "Existing backup content/size mismatch",
    )
    m.save(
        out / "reused-backup.json",
        {
            "path": str(backup),
            "sha256": checksum,
            "identity": list(m.identity(backup_stat)),
            "members": receipt["members"],
            "original_member_hash_check": True,
            "current_whole_archive_hash_check": True,
            "new_backup_created": False,
        },
    )
    gate, omitted, classes = gate_snapshot(1)
    lookup = {r["id"]: r for r in rows}
    counts = {
        "cache_unlinked": 0,
        "duplicate_unlinked": 0,
        "retained": 0,
        "logical_bytes_unlinked": 0,
    }
    target_rows = [r for r in rows if r["action"] in {"cache", "duplicate"}]
    m.require(len(target_rows) == EXPECTED_TARGETS, "Target cardinality changed")
    stopped = None
    with (out / "actions.jsonl").open("x", encoding="utf-8") as journal:
        for i, row in enumerate(target_rows):
            try:
                if i % 1000 == 0:
                    if i:
                        gate, omitted, classes = gate_snapshot(i)
                    # Detect changes/replacement of the backup without rehashing it for each file.
                    with m.opened(backup.relative_to(m.PARENT).as_posix()) as f:
                        now = os.fstat(f.fileno())
                        m.require(
                            m.identity(now) == m.identity(backup_stat)
                            and now.st_ctime_ns == backup_stat.st_ctime_ns,
                            "Verified backup identity changed",
                        )
                reason = eligible(row, gate, omitted, classes)
                m.require(reason is None, reason or "retained")
                keeper = lookup[row["keeper"]] if row["action"] == "duplicate" else None
                m.remove_one(row, keeper, journal, BACKUP_SHA)
                counts[row["action"] + "_unlinked"] += 1
                counts["logical_bytes_unlinked"] += int(row["logical_bytes"])
            except (OSError, ValueError, KeyError) as exc:
                counts["retained"] += 1
                m.event(
                    journal, {"status": "retained", "id": row["id"], "reason": str(exc)}
                )
                if "SFTP session appeared" in str(exc) or "User jobs present" in str(
                    exc
                ):
                    stopped = str(exc)
                    break
            if (i + 1) % 100 == 0:
                print(
                    json.dumps({"phase": "prune", "processed": i + 1, **counts}),
                    flush=True,
                )
    result = {
        "status": m.cleanup_outcome(counts)
        if not stopped
        else "cleanup_interrupted_preserved",
        **counts,
        "unprocessed": len(target_rows)
        - sum(counts[k] for k in ("cache_unlinked", "duplicate_unlinked", "retained")),
        "stop_reason": stopped,
        "new_backup_created": False,
        "backup_preserved": str(backup),
        "environment_changed": False,
        "jobs_submitted": 0,
        "scientific_originals_pruned": False,
        "space_note": "Logical removed bytes; not a filesystem free-space measurement",
    }
    m.save(out / "cleanup-result.json", result)
    names = sorted(p.name for p in out.iterdir() if p.is_file())
    (out / "SHA256SUMS").write_text(
        "".join(
            hashlib.sha256((out / n).read_bytes()).hexdigest() + "  " + n + "\n"
            for n in names
        ),
        encoding="utf-8",
    )
    archive = out / "reused-backup-cleanup-reports.tar.gz"
    with tarfile.open(archive, "x:gz") as t:
        for n in names + ["SHA256SUMS"]:
            t.add(out / n, arcname=n, recursive=False)
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(archive.name + ".sha256").write_text(
        sha + "  " + archive.name + "\n", encoding="utf-8"
    )
    print(
        json.dumps({"archive": str(archive), "sha256": sha, **result}, indent=2),
        flush=True,
    )
    return 0 if result["status"] == "bounded_cleanup_completed" else 2


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--original-run", required=True)
    p.add_argument("--original-package", required=True)
    p.add_argument("--diagnosis-archive", required=True)
    p.add_argument("--apply", action="store_true")
    raise SystemExit(run(p.parse_args()))


if __name__ == "__main__":
    main()
