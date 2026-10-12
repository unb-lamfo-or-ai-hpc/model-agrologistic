"""Closed login/compute identity components; no launcher or execution admission.

Login proves raw Git HEAD. Compute rechecks every sealed file without Git and
reports only tools actually checked for its role. This is a future integration
component, not a replacement for existing v1 runtime or containment receipts.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Compute identity components only; no execution admitted.")

import copy
import hashlib
import os
from pathlib import Path

from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_slurm_step as s
from scripts import mvp2_s2_slurm_synthetic as q

COMPUTE_TOOLS = ("srun", "scontrol", "scancel", "sacct")
REQUIRED = {
    "scripts/mvp2_s2_batch_adapter.py",
    "scripts/mvp2_s2_synthetic_worker.py",
    "scripts/mvp2_s2_slurm_synthetic.py",
}
FILE_LIMIT = 8 * 1024**2
TREE_LIMIT = 32 * 1024**2


def source_summary(files):
    return {
        "source_sha256": s.digest(files),
        "tracked_count": len(files),
        "worker_sha256": files["scripts/mvp2_s2_synthetic_worker.py"],
    }


def validate_manifest(manifest, commit, expected_digest):
    return _validate_manifest(manifest, commit, expected_digest, "s2-sealed-source-v1")


def validate_historical_manifest(manifest, commit, expected_digest):
    """Historical tracked bytes are evidence, never executable-tree admission."""
    return _validate_manifest(manifest, commit, expected_digest, "s2-historical-tracked-source-v1")


def _validate_manifest(manifest, commit, expected_digest, schema):
    q._hash(commit, 40)
    q._hash(expected_digest)
    q._keys(manifest, {"schema_version", "source_commit", "files", "source"})
    s.require(
        manifest["schema_version"] == schema
        and manifest["source_commit"] == commit
        and s.digest(manifest) == expected_digest,
        "Sealed source binding drift.",
    )
    files = manifest["files"]
    s.require(type(files) is dict and 1 <= len(files) <= 1024, "Source file count.")
    s.require(REQUIRED <= files.keys(), "Missing source closure.")
    for name, checksum in files.items():
        s.require(a.safe_repo_name(name), "Unsafe source name.")
        q._hash(checksum)
    s.require(manifest["source"] == source_summary(files), "Source summary drift.")
    return copy.deepcopy(manifest)


def inspect_tree(checkout, files):
    """No subprocesses; reject shadow files, links and unreviewed directories."""
    root = Path(checkout)
    q._safe_path(root)
    s.require(root.is_dir(), "Missing source root.")
    parents = {str(p).replace("\\", "/") for name in files for p in Path(name).parents}
    observed, total = {}, 0
    for directory, dirs, names in os.walk(root, followlinks=False, onerror=_walk_error):
        base = Path(directory)
        for name in list(dirs):
            child = base / name
            q._safe_path(child)
            if child == root / ".git":
                dirs.remove(name)
            else:
                relative = child.relative_to(root).as_posix()
                s.require(relative in parents, f"Extra source directory: {relative!r}.")
        for name in names:
            child = base / name
            relative = child.relative_to(root).as_posix()
            s.require(relative in files, f"Extra source file: {relative!r}.")
            raw = a._file(child, FILE_LIMIT)
            total += len(raw)
            s.require(total <= TREE_LIMIT, "Source tree byte bound.")
            observed[relative] = hashlib.sha256(raw).hexdigest()
    s.require(observed == files, "Missing or changed source bytes.")
    return source_summary(observed)


def _walk_error(error):
    raise error


def seal_login_source(spec, command):
    """Only after login raw-HEAD validation; seal full inventory, not an allowlist."""
    return _seal_login_source(spec, command, historical=False)


def seal_historical_source(spec, command):
    """Retain original raw-Git proof without executing or cleaning historical trees."""
    return _seal_login_source(spec, command, historical=True)


def inspect_historical_source(checkout, files):
    """Check every bound tracked byte; untracked history is neither read nor trusted.

    Callers must bind a fixed predecessor and must never execute/import this tree.
    Original receipts did not certify absence of ignored files. Their caches stay
    untouched and outside this manifest; current executable trees use inspect_tree.
    """
    root = Path(checkout)
    q._safe_path(root)
    s.require(root.is_dir(), "Missing historical source root.")
    observed, total = {}, 0
    for name in files:
        path = root / name
        q._safe_path(path)
        raw = a._file(path, FILE_LIMIT)
        total += len(raw)
        s.require(total <= TREE_LIMIT, "Historical source tree byte bound.")
        observed[name] = hashlib.sha256(raw).hexdigest()
    s.require(observed == files, "Missing or changed historical source bytes.")
    return source_summary(observed)


def _seal_login_source(spec, command, *, historical):
    spec = a.validate_spec(spec)
    q._safe_path(Path(spec["checkout"]))
    s.require(
        a.sha_file(spec["tools"]["git"]) == spec["tools_sha256"]["git"],
        "Login Git byte drift.",
    )
    verified = a.verify_checkout(spec, command)
    prefix = (spec["tools"]["git"], "--no-optional-locks", "-C", spec["checkout"])
    listing = command(
        prefix + ("ls-files", "--stage", "-z"),
        timeout_seconds=10,
        max_output_bytes=1024**2,
    )
    s.require(type(listing) is str and listing.endswith("\0"), "Incomplete sealed index.")
    files = {}
    for entry in listing[:-1].split("\0"):
        metadata, name = entry.split("\t", 1)
        fields = metadata.split()
        s.require(
            len(fields) == 3
            and fields[0] in {"100644", "100755"}
            and fields[2] == "0"
            and a.safe_repo_name(name)
            and name not in files
            and len(files) < 1024,
            "Sealed index drift.",
        )
        q._hash(fields[1], 40)
        files[name] = a.sha_file(Path(spec["checkout"]) / name, FILE_LIMIT)
    s.require(REQUIRED <= files.keys(), "Missing sealed closure.")
    s.require(source_summary(files) == verified, "Source changed while sealing.")
    inspect = inspect_historical_source if historical else inspect_tree
    s.require(inspect(spec["checkout"], files) == verified, "Source inventory drift.")
    s.require(
        command(prefix + ("rev-parse", "HEAD"), timeout_seconds=10, max_output_bytes=65536).strip()
        == spec["source_commit"],
        "HEAD changed while sealing.",
    )
    return {
        "schema_version": (
            "s2-historical-tracked-source-v1" if historical else "s2-sealed-source-v1"
        ),
        "source_commit": spec["source_commit"],
        "files": files,
        "source": verified,
    }


def verify_compute_source(checkout, manifest, commit, expected_digest):
    item = validate_manifest(manifest, commit, expected_digest)
    return inspect_tree(checkout, item["files"])


def verify_historical_source(checkout, manifest, commit, expected_digest):
    item = validate_historical_manifest(manifest, commit, expected_digest)
    return inspect_historical_source(checkout, item["files"])


def expected_compute_runtime(spec, role="batch"):
    item = a.validate_spec(spec)
    s.require(role in {"batch", "worker"} and type(role) is str, "Compute role drift.")
    keys = COMPUTE_TOOLS if role == "batch" else ()
    return {
        "schema_version": "s2-compute-runtime-v1",
        "role": role,
        "python_sha256": item["python_sha256"],
        "verified_tools_sha256": {key: item["tools_sha256"][key] for key in keys},
        "login_only_tools": ["git", "sbatch"],
        "execution_admitted": False,
    }


def review_compute_runtime(item, role="batch"):
    q._keys(
        item,
        {
            "schema_version",
            "role",
            "python_sha256",
            "verified_tools_sha256",
            "login_only_tools",
            "execution_admitted",
        },
    )
    s.require(role in {"batch", "worker"} and type(role) is str, "Compute role drift.")
    s.require(
        item["schema_version"] == "s2-compute-runtime-v1"
        and item["role"] == role
        and item["login_only_tools"] == ["git", "sbatch"]
        and item["execution_admitted"] is False,
        "Compute runtime schema drift.",
    )
    q._hash(item["python_sha256"])
    q._keys(item["verified_tools_sha256"], COMPUTE_TOOLS if role == "batch" else ())
    for value in item["verified_tools_sha256"].values():
        q._hash(value)
    return copy.deepcopy(item)


def verify_compute_runtime(spec, role="batch"):
    """Retain exact expected hashes; absence/drift of an actually used tool blocks."""
    item = a.validate_spec(spec)
    s.require(a.sha_file(item["python"]) == item["python_sha256"], "Compute Python byte drift.")
    expected = expected_compute_runtime(item, role)
    for key in expected["verified_tools_sha256"]:
        s.require(
            a.sha_file(item["tools"][key]) == item["tools_sha256"][key],
            "Compute tool byte drift.",
        )
    return expected
