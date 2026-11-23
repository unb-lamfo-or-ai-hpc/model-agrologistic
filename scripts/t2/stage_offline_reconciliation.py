"""Stage private T2 review inputs and capture an OSRM source-image candidate.

No live SQLite connection. No source mutation, optimizer, environment edit or job.
An engine-consistent backup of a stable file image is NOT certification that
the original shared cache was atomically snapshotted or had no remote writers.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
import os
import sqlite3
import sys
import tarfile
import tempfile
import time
from pathlib import Path

HELPER_SHA = "d27936d62242b83b78d60cf333400c3710d662e9996da33fa2b500ddbb140024"
HELPER_PATH = Path(__file__).with_name("reconcile_inputs.py")
if hashlib.sha256(HELPER_PATH.read_bytes()).hexdigest() != HELPER_SHA:
    raise ValueError("Original reconciliation helper hash differs.")
SPEC = importlib.util.spec_from_file_location("t2_preserved", HELPER_PATH)
T2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(T2)
CACHE = Path("/home/vrrcelestino/osrm-agrologistic/cache/policy-pairs-v020.sqlite3")
SUPPORT = {
    "arcs.csv",
    "configs.json",
    "metadata.json",
    "nodes.json",
    "parameters.csv",
    "sets.csv",
    "sources.json",
    "manifest.json",
}
ALLOW = {"workbooks/" + name for name in T2.PINS} | {"support/" + n for n in SUPPORT}
EXPECTED_HEADER = "08310875937ba24d6eb133bf4d6442b8f430de7eb55a33751e4309f9d8d203fd"


def stage_inputs(archive, sha, destination):
    raw = T2.read_stable(archive, limit=64 * 1024**2)
    T2.require(T2.digest(raw) == sha, "Private transfer archive SHA differs.")
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
        members = tar.getmembers()
        T2.require(
            {m.name for m in members} == ALLOW | {"transfer-manifest.json"}
            and len(members) == len(ALLOW) + 1,
            "Unexpected transfer members.",
        )
        T2.require(
            all(m.isfile() for m in members)
            and sum(m.size for m in members) <= 256 * 1024**2,
            "Unsafe or oversized transfer.",
        )
        manifest = json.loads(tar.extractfile("transfer-manifest.json").read())
        T2.require(set(manifest["files"]) == ALLOW, "Transfer ledger differs.")
        for member in members:
            if member.name == "transfer-manifest.json":
                continue
            payload = tar.extractfile(member).read()
            T2.require(
                T2.digest(payload) == manifest["files"][member.name],
                "Private transfer member hash differs.",
            )
            target = destination / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(payload)
    support = destination / "support"
    metadata = json.loads(T2.read_stable(support / "manifest.json"))
    T2.require(
        set(metadata["files"]) == SUPPORT - {"manifest.json"},
        "Effective bundle ledger differs.",
    )
    for name, expected in metadata["files"].items():
        T2.require(
            T2.digest(T2.read_stable(support / name)) == expected,
            "Effective bundle hash differs.",
        )
    result = T2.reconcile_workbooks(
        destination / "workbooks/agrologistic_effective_baseline_v1.xlsx",
        destination / "workbooks/agrologistic_warehouse_registry_v1.xlsx",
        support,
    )
    return result


def no_sidecars(source):
    for suffix in ("-wal", "-shm", "-journal"):
        p = Path(str(source) + suffix)
        T2.require(
            not p.exists() and not p.is_symlink(),
            "Source sidecar observed; capture withheld.",
        )


def capture_image(source, destination, expected_header=EXPECTED_HEADER):
    """Two full stable reads and metadata/sidecar guards, never an atomicity claim."""
    source = T2.clean_path(source)
    no_sidecars(source)
    before = T2.stamp(source.stat())
    raw = T2.read_stable(source, limit=512 * 1024**2)
    T2.require(T2.digest(raw[:100]) == expected_header, "Source header changed.")
    no_sidecars(source)
    with destination.open("xb") as stream:
        stream.write(raw)
    image_sha = T2.digest(raw)
    del raw
    second = T2.read_stable(source, limit=512 * 1024**2)
    T2.require(T2.digest(second) == image_sha, "Source changed between capture reads.")
    no_sidecars(source)
    T2.require(T2.stamp(source.stat()) == before, "Source metadata changed.")
    del second
    return {
        "source_path": str(source),
        "captured_image_sha256": image_sha,
        "source_metadata_before_after_equal": True,
        "source_stat": list(before),
        "full_reads_equal": True,
        "sidecars_observed": False,
        "source_engine_opened": False,
        "source_consistency_certified": False,
        "limitation": "No cross-host writer exclusion or atomic source snapshot proven.",
    }


def offline_backup(image, expected_sha, target, *, deadline_seconds=120):
    """immutable=1 applies ONLY to the newly created private captured image."""
    T2.require(
        image.parent == target.parent
        and image.name == "captured-main.sqlite3"
        and not target.exists(),
        "Unexpected private backup paths.",
    )
    T2.require(
        T2.digest(T2.read_stable(image, limit=512 * 1024**2)) == expected_sha,
        "Private captured image SHA differs.",
    )
    no_sidecars(image)
    started = time.monotonic()

    def progress(status, remaining, total):
        T2.require(
            time.monotonic() - started <= deadline_seconds,
            "Private SQLite backup deadline exceeded.",
        )

    uri = image.as_uri() + "?mode=ro&immutable=1"
    with contextlib.closing(sqlite3.connect(uri, uri=True)) as source:
        source.execute("PRAGMA query_only=ON")
        with contextlib.closing(sqlite3.connect(target)) as dest:
            source.backup(dest, pages=256, progress=progress)
            # Only the fresh derived database is normalized to a standalone file.
            dest.execute("PRAGMA journal_mode=DELETE")
            T2.require(
                dest.execute("PRAGMA quick_check").fetchall() == [("ok",)],
                "Private backup structural check failed.",
            )
    T2.require(
        T2.digest(T2.read_stable(image, limit=512 * 1024**2)) == expected_sha,
        "Captured image changed during backup.",
    )
    no_sidecars(target)
    return T2.digest(T2.read_stable(target, limit=512 * 1024**2))


def finalize(output, report):
    T2.dump(output / "stage-review.json", report)
    members = [output / "stage-review.json"]
    members += [p for p in output.iterdir() if p.is_file() and p.suffix == ".sqlite3"]
    receipt = output / "acquisition.json"
    if receipt.exists():
        members.append(receipt)
    ledger = "".join(T2.digest(p.read_bytes()) + "  " + p.name + "\n" for p in members)
    (output / "SHA256SUMS").write_text(ledger, encoding="utf-8")
    archive = output / "t2-offline-reconciliation-readback.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for p in [*members, output / "SHA256SUMS"]:
            tar.add(p, arcname=p.name, recursive=False)
    sha = T2.digest(archive.read_bytes())
    (output / (archive.name + ".sha256")).write_text(
        sha + "  " + archive.name + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "transfer_dir": str(output),
                "archive": str(archive),
                "sha256": sha,
                "status": report["status"],
                "source_consistency_certified": False,
                "jobs_submitted": 0,
                "shared_environment_changed": False,
            }
        )
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", required=True)
    p.add_argument("--inputs-sha256", required=True)
    p.add_argument("--controller-sha256", required=True)
    args = p.parse_args()
    T2.require(
        T2.digest(T2.read_stable(__file__)) == args.controller_sha256,
        "Capture controller SHA differs.",
    )
    T2.clean_path(T2.AUDIT)
    archive = T2.clean_path(args.inputs)
    T2.require(archive.is_relative_to(T2.AUDIT), "Transfer must be in audit custody.")
    output = Path(tempfile.mkdtemp(prefix="t2-offline-reconciliation-", dir=T2.AUDIT))
    os.chmod(output, 0o700)
    report = {
        "status": "verification_failed",
        "jobs_submitted": 0,
        "optimizer_calls": 0,
        "sources_modified": False,
        "source_consistency_certified": False,
        "final_mvp3_input_accepted": False,
        "sqlite_runtime": sqlite3.sqlite_version,
        "controller_sha256": args.controller_sha256,
        "helper_sha256": HELPER_SHA,
        "inputs_archive_sha256": args.inputs_sha256,
    }
    try:
        report["workbooks"] = stage_inputs(archive, args.inputs_sha256, output)
        report["source_before"] = T2.cache_header(CACHE)
        image = output / "captured-main.sqlite3"
        report["capture"] = capture_image(CACHE, image)
        snapshot = output / "offline-backup.sqlite3"
        sha = offline_backup(
            image, report["capture"]["captured_image_sha256"], snapshot
        )
        acquisition = {
            "method": "sqlite_backup",
            "source_path": str(image),
            "historical_source_path": str(CACHE),
            "snapshot_sha256": sha,
            "consistent_snapshot": True,
            "source_consistency_certified": False,
            "scope": "Engine-consistent backup of private stable-read image only.",
            "captured_utc": datetime.datetime.now(datetime.UTC).isoformat(),
            "sqlite_version": sqlite3.sqlite_version,
        }
        T2.dump(output / "acquisition.json", acquisition)
        report["crosswalk"] = T2.cache_crosswalk(
            snapshot, sha, output / "support", output / "acquisition.json"
        )
        report["source_after"] = T2.cache_header(CACHE)
        no_sidecars(CACHE)
        T2.require(
            T2.digest(T2.read_stable(CACHE, limit=512 * 1024**2))
            == report["capture"]["captured_image_sha256"],
            "Source changed during analysis.",
        )
        T2.require(
            list(T2.stamp(CACHE.stat())) == report["capture"]["source_stat"],
            "Source metadata changed during analysis.",
        )
        report["status"] = "exploratory_crosswalk_complete_source_consistency_pending"
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        sqlite3.Error,
        tarfile.TarError,
    ) as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finalize(output, report)
    return 1 if report["status"] == "verification_failed" else 0


if __name__ == "__main__":
    sys.exit(main())
