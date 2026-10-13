"""Fixed recovery reference for one normal-only successor; no scheduler effects."""

from __future__ import annotations

import copy
import gzip
import hashlib
import io
import tarfile
from pathlib import Path

from scripts import mvp2_h300_controls as c
from scripts import mvp2_s2_accounting_recovery as recovery
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_compute_integration as x
from scripts import mvp2_s2_node_predecessor as node
from scripts import mvp2_s2_operational as o
from scripts import mvp2_s2_slurm_step as s
from scripts import mvp2_s2_slurm_synthetic as q

SCHEMA = "s2-step-normal-release-v1"
# Existing public history is unchanged; the recovered immediate attempt is separate.
prior, PREDECESSOR, DIAGNOSTIC = node.prior, node.PREDECESSOR, node.DIAGNOSTIC
RECOVERY = {
    "source_commit": recovery.SOURCE,
    "job_id": recovery.JOB,
    "release_sha256": recovery.RELEASE,
    "archive_sha256": "64617380256e8cf3c5031ef87fb3d71d9526d923e69e100c5140879a60ad34e3",
    "replay_sha256": "67fd0db5c0087a4aba8693166412946d9b2966d05c9d7c17ea176a03f5bcc0f5",
}
NAME = "s2-node-accounting-recovery-2208459.tar.gz"


def validate_reference(record):
    q._keys(record, {"identity", "archive"})
    s.require(record["identity"] == RECOVERY, "Recovery identity drift.")
    path = Path(record["archive"])
    s.require(
        path.name == NAME
        and path.parent.parent == Path(o.BASE)
        and path.parent.name.startswith("s2-node-recovery-2208459-"),
        "Recovery location drift.",
    )
    return copy.deepcopy(record)


def read_recovery(path):
    """Bounded forensic reader, including legitimate empty stderr; no extraction."""
    raw = a._file(path, recovery.LIMIT)
    s.require(
        hashlib.sha256(raw).hexdigest() == RECOVERY["archive_sha256"], "Recovery checksum drift."
    )
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as zipped:
        expanded = zipped.read(recovery.LIMIT + 1)
    s.require(len(expanded) <= recovery.LIMIT, "Recovery expansion bound.")
    records, end = {}, 0
    with tarfile.open(fileobj=io.BytesIO(expanded), mode="r:") as archive:
        for member in archive:
            s.require(
                member.isfile()
                and not member.pax_headers
                and a.safe_repo_name(member.name)
                and member.name not in records
                and 0 <= member.size <= recovery.LIMIT
                and len(records) < 32,
                "Recovery member grammar.",
            )
            records[member.name] = archive.extractfile(member).read()
            end = member.offset_data + ((member.size + 511) // 512) * 512
    s.require(not any(expanded[end:]), "Recovery trailing data.")
    manifest = c.decode_json(records["recovery.json"])
    s.require(
        manifest["job_id"] == recovery.JOB
        and manifest["release_sha256"] == recovery.RELEASE
        and manifest["execution_source"] == recovery.SOURCE
        and manifest["status"] == "captured_not_live_qualified",
        "Recovered negative identity drift.",
    )
    s.require(
        set(records) == set(manifest["files"]) | {"recovery.json"}, "Recovery inventory drift."
    )
    for name, desc in manifest["files"].items():
        s.require(
            desc
            == {"sha256": hashlib.sha256(records[name]).hexdigest(), "bytes": len(records[name])},
            "Recovery member drift.",
        )
    s.require(
        hashlib.sha256(records["replay/s2-node-normal-evidence.tar.gz"]).hexdigest()
        == RECOVERY["replay_sha256"],
        "Recovered replay drift.",
    )
    return records, manifest


def verify_reference(record):
    """Read existing carrier and originals; never execute a historical checkout."""
    record = validate_reference(record)
    path = Path(record["archive"])
    q._safe_path(path)
    records, manifest = read_recovery(path)
    release = recovery.bound_release(recovery.y.claim_path())
    observed, missing = recovery.snapshot(
        recovery.y.claim_path(), Path(release["plan"]["specification"]["run"])
    )
    original_names = set(records) - {
        "recovery.json",
        "accounting.txt",
        "replay/s2-node-normal-evidence.tar.gz",
    }
    s.require(
        set(observed) == original_names and missing == manifest["missing"],
        "Original inventory drift.",
    )
    s.require(all(observed[k] == records[k] for k in observed), "Original evidence drift.")
    return release


def discover_reference():
    candidates = sorted(Path(o.BASE).glob("s2-node-recovery-2208459-*/" + NAME))
    s.require(len(candidates) == 1, "Expected one preserved recovery carrier; do not guess.")
    record = {"identity": copy.deepcopy(RECOVERY), "archive": str(candidates[0])}
    verify_reference(record)
    return record


def validate_release(release, commit, digest):
    s.require(
        s.digest(release) == digest and release["schema_version"] == SCHEMA, "Step release drift."
    )
    s.require(len(c.encoded(release)) <= x.RELEASE_LIMIT, "Step release bound.")
    core = copy.deepcopy(release)
    validate_reference(core.pop("recovery"))
    core["schema_version"] = node.SCHEMA
    node.validate_release(core, commit, s.digest(core))
    spec = release["plan"]["specification"]
    s.require(
        spec["source_commit"] != recovery.SOURCE and spec["job_id"] != recovery.JOB,
        "Recovered identity reuse.",
    )
    required = {
        "scripts/mvp2_s2_step_normal.py",
        "scripts/npad_s2_step_normal.sh",
        "scripts/mvp2_s2_step_predecessor.py",
        "tests/test_mvp2_s2_step_identity.py",
    }
    s.require(required <= release["manifest"]["files"].keys(), "Step gate source closure drift.")
    return copy.deepcopy(release)


def seal_release(envelope, plan):
    release = node.seal_release(envelope, plan)
    release["schema_version"] = SCHEMA
    release["recovery"] = discover_reference()
    return validate_release(release, envelope["source_commit"], s.digest(release))
