"""Read-only post-backup diagnosis. Writes fresh derived reports, never prunes."""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
import stat
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[2]
HELPER = Path(__file__).with_name("authorized_t1_cleanup.py")
spec = importlib.util.spec_from_file_location("t1_cleanup_reference", HELPER)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
REPORT_SHA = "29d5df4f4c65a1b92219a27e773e04e67790782692d5eabc5abf88eb6ada87a6"


def read_report(path):
    with m.opened(path.relative_to(m.PARENT).as_posix()) as f:
        raw = f.read(16 * 1024**2 + 1)
    m.require(len(raw) <= 16 * 1024**2, "Report archive byte guard")
    m.require(
        hashlib.sha256(raw).hexdigest() == REPORT_SHA, "Original report SHA mismatch"
    )
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as t:
        for member in t:
            m.require(
                member.isfile() and member.name == PurePosixPath(member.name).name,
                "Non-flat or nonregular report member",
            )
            m.require(
                member.name not in files and member.size <= 64 * 1024**2,
                "Report size/duplicate guard",
            )
            m.require(len(files) < 64, "Report member-count guard")
            m.require(
                sum(map(len, files.values())) + member.size <= 128 * 1024**2,
                "Report expanded-byte guard",
            )
            files[member.name] = t.extractfile(member).read()
    m.require(sum(map(len, files.values())) <= 128 * 1024**2, "Report total byte guard")
    ledger = {}
    for line in files["REPORT_SHA256SUMS"].decode().splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  ([^/]+)", line)
        m.require(match is not None, "Invalid report ledger")
        sha, name = match.groups()
        m.require(name not in ledger and name in files, "Invalid ledger membership")
        m.require(hashlib.sha256(files[name]).hexdigest() == sha, "Ledger mismatch")
        ledger[name] = sha
    m.require(set(ledger) == set(files) - {"REPORT_SHA256SUMS"}, "Incomplete ledger")
    return files, ledger


def prefix_matches(name, references):
    target = (m.PARENT / name).as_posix()
    parents = {
        p.as_posix() for p in (PurePosixPath(target), *PurePosixPath(target).parents)
    }
    good = {m.canonical_reference(x) for x in references}
    good.discard(None)
    good.discard("/")
    return bool(parents & good)


def summarize(files):
    actions = [json.loads(line) for line in files["actions.jsonl"].splitlines()]
    rows = list(csv.DictReader(io.StringIO(files["selection.csv"].decode())))
    targets = {r["id"]: r for r in rows if r["action"] in {"cache", "duplicate"}}
    m.require(
        len(actions) == 8449 and len({r["id"] for r in actions}) == 8449,
        "Action cardinality",
    )
    m.require({r["id"] for r in actions} == set(targets), "Action selection mismatch")
    statuses = collections.Counter(r["status"] for r in actions)
    m.require(statuses == {"retained": 8449}, "Unexpected original action statuses")
    target_parents = {
        name: {
            p.as_posix()
            for p in (
                PurePosixPath((m.PARENT / name).as_posix()),
                *PurePosixPath((m.PARENT / name).as_posix()).parents,
            )
        }
        for name in targets
    }
    snapshots = []
    omissions, errors = {}, {}
    for name, raw in sorted(files.items()):
        if not name.startswith("dependencies-"):
            continue
        d = json.loads(raw)
        for o in d["control_omissions"]:
            omissions[o["id"]] = o
        for e in d["process_errors"]:
            errors[(e["pid"], e["scope"], e["reason"])] = e
        normalized = {m.canonical_reference(x) for x in d["process_references"]}
        normalized.discard(None)
        normalized.discard("/")
        counts = {}
        for kind in ("cache", "duplicate"):
            group = [r for r in targets.values() if r["action"] == kind]
            counts[kind] = {
                "targets": len(group),
                "old_empty_reference_present": "" in d["process_references"],
                "normalized_observed_process_matches": sum(
                    bool(target_parents[r["id"]] & normalized) for r in group
                ),
            }
        snapshots.append(
            {
                "name": name,
                "counts": counts,
                "process_error_count": len(d["process_errors"]),
                "non_test_control_omissions": sum(
                    not o["test_fixture_path"] for o in d["control_omissions"]
                ),
            }
        )
    return {
        "statuses": dict(statuses),
        "retention_reasons": dict(collections.Counter(r["reason"] for r in actions)),
        "snapshots": snapshots,
        "omissions": list(omissions.values()),
        "process_errors": list(errors.values()),
        "scope": "Historical counterfactual only, not current dependency clearance",
        "pruning_allowed": False,
    }


def process_metadata(pid):
    m.require(re.fullmatch("[0-9]+", pid) is not None, "Invalid PID")
    p = Path("/proc") / pid
    result = {"pid": pid, "observations": [], "errors": []}
    try:
        result["proc_directory_uid"] = p.stat().st_uid
        allowed = {
            "Name",
            "State",
            "PPid",
            "Uid",
            "Gid",
            "NSpid",
            "TracerPid",
            "NoNewPrivs",
            "Seccomp",
        }
        with (p / "status").open() as f:
            raw = f.read(65537)
        m.require(len(raw) <= 65536, "Proc status byte guard")
        result["status"] = {
            key: value.strip()
            for line in raw.splitlines()
            if ":" in line
            for key, value in [line.split(":", 1)]
            if key in allowed
        }
    except FileNotFoundError:
        result["state"] = "no_longer_visible"
        return result
    except (OSError, ValueError) as exc:
        result["errors"].append({"scope": "status", "reason": type(exc).__name__})
    for key in ("cwd", "exe"):
        try:
            value = os.readlink(p / key)
            result["observations"].append(
                m.process_reference(
                    "proc_" + key, pid, value, "directory" if key == "cwd" else "file"
                )
            )
        except OSError as exc:
            result["errors"].append({"scope": key, "reason": type(exc).__name__})
    try:
        for i, fd in enumerate((p / "fd").iterdir()):
            if i >= 2048:
                result["errors"].append(
                    {"scope": "fd", "reason": "descriptor_count_guard"}
                )
                break
            try:
                value = os.readlink(fd)
                mode = os.stat(fd).st_mode
                item = m.process_reference(
                    "proc_fd",
                    pid,
                    value,
                    "directory"
                    if stat.S_ISDIR(mode)
                    else "file"
                    if stat.S_ISREG(mode)
                    else "other",
                )
                item["fd"] = fd.name
                result["observations"].append(item)
            except FileNotFoundError:
                continue
            except OSError as exc:
                result["errors"].append({"scope": "fd", "reason": type(exc).__name__})
    except OSError as exc:
        result["errors"].append({"scope": "fd_directory", "reason": type(exc).__name__})
    result["scope"] = (
        "Previously inaccessible PID only; no process exclusion authorized"
    )
    return result


def control_metadata(row):
    result = dict(row)
    try:
        with m.opened(row["id"]) as f:
            before = os.fstat(f.fileno())
            m.require(before.st_size <= 2 * 1024**2, "Control byte guard")
            raw = f.read()
            m.require(
                m.identity(before) == m.identity(os.fstat(f.fileno())),
                "Changing control",
            )
        result.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        if not raw:
            result["current_status"] = "empty_original_preserved_no_encoded_paths"
        else:
            try:
                json.loads(raw)
                result["current_status"] = "currently_valid_json"
            except (ValueError, UnicodeError):
                result["current_status"] = "nonempty_invalid_json_preserved"
    except (OSError, ValueError) as exc:
        result["current_status"] = "read_error_preserved"
        result["current_error"] = type(exc).__name__
    return result


def run(args):
    m.require(
        sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
        "Invoke with -B -I -S; shared initialization is not allowed",
    )
    m.require(
        os.name == "posix" and not os.environ.get("SLURM_JOB_ID"),
        "Linux login shell only; no job is used",
    )
    original = Path(args.original_run)
    m.require(
        original.is_absolute() and original.parent == m.BASE,
        "Original run must be a direct audit-root child",
    )
    files, ledger = read_report(original / "cleanup-reports.tar.gz")
    review = summarize(files)
    pids = sorted({e["pid"] for e in review["process_errors"]})
    current_processes = [process_metadata(pid) for pid in pids]
    current_controls = [control_metadata(o) for o in review["omissions"]]
    result = {
        "status": "read_only_retention_diagnosis_complete",
        "original_report_sha256": REPORT_SHA,
        "internal_manifest_entries_verified": len(ledger),
        "backup_receipt": json.loads(files["verified-backup.json"]),
        "historical_findings": review,
        "current_process_metadata": current_processes,
        "current_control_metadata": current_controls,
        "current_scope": "Original error PIDs and omitted controls only; not a new global scan",
        "original_backup_rehashed": False,
        "original_sources_modified": False,
        "cleanup_invoked": False,
        "pruning_allowed": False,
    }
    out = Path(tempfile.mkdtemp(prefix="t1-retention-probe-", dir=m.BASE))
    os.chmod(out, 0o700)
    m.save(out / "retention-diagnosis.json", result)
    m.save(
        out / "source-identity.json",
        {
            "files": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (Path(__file__), HELPER)
            },
            "optimizer_imported": any(
                n.startswith(("gurobipy", "pyomo", "highspy")) for n in sys.modules
            ),
            "shared_site_initialized": False,
        },
    )
    names = ["retention-diagnosis.json", "source-identity.json"]
    ledger = "".join(
        hashlib.sha256((out / n).read_bytes()).hexdigest() + "  " + n + "\n"
        for n in names
    )
    (out / "SHA256SUMS").write_text(ledger, encoding="utf-8")
    archive = out / "retention-diagnosis-reports.tar.gz"
    with tarfile.open(archive, "x:gz") as t:
        for name in names + ["SHA256SUMS"]:
            t.add(out / name, arcname=name, recursive=False)
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(archive.name + ".sha256").write_text(
        sha + "  " + archive.name + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(out),
                "archive": str(archive),
                "sha256": sha,
                "original_retained": 8449,
                "previous_inaccessible_pids": len(pids),
                "empty_controls_now": sum(
                    c.get("current_status")
                    == "empty_original_preserved_no_encoded_paths"
                    for c in current_controls
                ),
                "cleanup_invoked": False,
                "no_new_backup_or_job": True,
            },
            indent=2,
        )
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--original-run", required=True)
    run(p.parse_args())


if __name__ == "__main__":
    main()
