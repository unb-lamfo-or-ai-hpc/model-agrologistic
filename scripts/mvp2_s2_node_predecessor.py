"""Fixed negative predecessor binding for one successor normal-only release.

No scheduler effect or execution entry. Original claims are read-only data.
"""

from __future__ import annotations

import copy
from pathlib import Path

from scripts import mvp2_s2_allocation_diagnostic as diagnostic
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_compute_identity as identity
from scripts import mvp2_s2_compute_integration as x
from scripts import mvp2_s2_first_normal as n
from scripts import mvp2_s2_normal_predecessor as prior
from scripts import mvp2_s2_normal_successor as old
from scripts import mvp2_s2_operational as o
from scripts import mvp2_s2_slurm_step as s
from scripts import mvp2_s2_slurm_synthetic as q

SCHEMA = "s2-node-normal-release-v1"
DIAGNOSTIC = {
    "source_commit": "1c33692f9affdf3ec5dece387a9425cf5b2fd671",
    "job_id": "2208438",
    "plan_sha256": "5cc0032835331416b588351af404973c131c9fa702d28876c12a09f57cb14d90",
    "archive_sha256": "7042a46430a2bac242080306e86a5a81f6c165949ca537abba4c5d329980157e",
}
PREDECESSOR = {
    "source_commit": "f96d9729f2a3bf7a8310094aa8a675b224b203d1",
    "job_id": "2208339",
    "archive_sha256": "b10d4e4c2930a4dce0ea685b8aa0af4a1effff815da878e652c50712e4f3cc95",
    "release_sha256": "baeed8c999179e36f824b9faf9fa2f5caac3885b1099c385c59b3db302f40e46",
}
SOURCE = {
    "source_sha256": "926f6e2bfffd2b0c5c6743cecf389fdd19ad37afd1d103fae6892490fc71dfcb",
    "worker_sha256": "e97d15965fd16936d7e5d5a1bc0abb1fe38fb82dedb8ae599c42cfe9136c4bfe",
    "tracked_count": 507,
}
SPECIFICATION = "77abb5143e713cc6b2fc5f15d2cad6afbe4afc76725e206a35e7829ae6774664"
NAMES = {
    "intent.json",
    "proposal.json",
    "release.json",
    "job.json",
    "submission-intent.json",
    "batch.sh",
    "collection.json",
    "batch-outcome.json",
    "slurm-2208339.out",
    "slurm-2208339.err",
}


def validate_release(release, commit, digest):
    q._hash(digest)
    s.require(s.digest(release) == digest, "Successor release digest drift.")
    s.require(len(x.c.encoded(release)) <= x.RELEASE_LIMIT, "Successor release bound.")
    s.require(release["schema_version"] == SCHEMA, "Successor schema drift.")
    s.require(
        type(release["history"]) is list and len(release["history"]) == 4,
        "Four preserved attempts required.",
    )
    core = copy.deepcopy(release)
    validate_diagnostic(core.pop("diagnostic"))
    core["schema_version"] = "s2-normal-successor-release-v1"
    entry = core["history"].pop()
    # All original schema, two-history, source and runtime restrictions still apply.
    x.validate_release(core, commit, s.digest(core))
    q._keys(entry, {"identity", "specification", "manifest", "records", "archive"})
    spec = release["plan"]["specification"]
    predecessor = a.validate_spec(entry["specification"])
    s.require(
        entry["identity"] == PREDECESSOR
        and predecessor["source_commit"] == PREDECESSOR["source_commit"]
        and predecessor["job_id"] == PREDECESSOR["job_id"]
        and s.digest(predecessor) == SPECIFICATION
        and all(spec[k] != predecessor[k] for k in ("source_commit", "job_id", "run", "checkout")),
        "Successor predecessor identity/reuse drift.",
    )
    manifest = identity.validate_historical_manifest(
        entry["manifest"], PREDECESSOR["source_commit"], s.digest(entry["manifest"])
    )
    s.require(manifest["source"] == SOURCE, "Frozen predecessor source drift.")
    claim = Path(o.BASE) / old.CLAIM
    q._keys(entry["records"], {str(claim / name) for name in NAMES})
    for checksum in entry["records"].values():
        q._hash(checksum)
    archive = Path(entry["archive"])
    s.require(
        archive.parent.parent == claim
        and archive.parent.name.startswith("collection-")
        and archive.name == "s2-normal-successor-evidence.tar.gz",
        "Successor predecessor archive location drift.",
    )
    required = {
        "scripts/mvp2_s2_node_normal.py",
        "scripts/npad_s2_node_normal.sh",
        "scripts/mvp2_s2_node_predecessor.py",
    }
    s.require(required <= release["manifest"]["files"].keys(), "Successor source closure drift.")
    return copy.deepcopy(release)


def seal_predecessor():
    """Login read-only audit; never execute/import the preserved checkout."""
    claim = Path(o.BASE) / old.CLAIM
    q._safe_path(claim)
    records = {str(claim / name): a.sha_file(claim / name, n.LIMIT) for name in NAMES}
    commit = PREDECESSOR["source_commit"]
    release = x.validate_release(
        n.read_json(claim / "release.json", x.RELEASE_LIMIT), commit, PREDECESSOR["release_sha256"]
    )
    s.require(
        release["schema_version"] == "s2-normal-successor-release-v1", "Historical schema drift."
    )
    spec = release["plan"]["specification"]
    s.require(
        spec["job_id"] == PREDECESSOR["job_id"] and s.digest(spec) == SPECIFICATION,
        "Frozen predecessor specification drift.",
    )
    proposal = n.read_json(claim / "proposal.json", x.RELEASE_LIMIT)
    digest = s.digest(proposal)
    s.require(
        old.derive_release(proposal, commit, digest, PREDECESSOR["job_id"]) == release,
        "Preserved proposal/release drift.",
    )
    s.require(
        n.read_json(claim / "intent.json")
        == {
            "source_commit": commit,
            "proposal_sha256": digest,
            **n.FUTURE,
        }
        and n.read_json(claim / "submission-intent.json") == old.submission_record(proposal, digest)
        and a._file(claim / "batch.sh", 8192) == old.batch_script(proposal, digest),
        "Preserved submission binding drift.",
    )
    s.require(
        n.read_json(claim / "job.json")
        == {
            "source_commit": commit,
            "job_id": PREDECESSOR["job_id"],
            "specification_sha256": SPECIFICATION,
            "release_sha256": PREDECESSOR["release_sha256"],
        },
        "Preserved acknowledgement drift.",
    )
    saved = n.read_json(claim / "collection.json")
    archive = Path(saved["download"])
    q._safe_path(archive)
    s.require(
        archive.parent.parent == claim
        and archive.parent.name.startswith("collection-")
        and archive.name == "s2-normal-successor-evidence.tar.gz"
        and saved["sha256"] == PREDECESSOR["archive_sha256"]
        and saved["job_id"] == PREDECESSOR["job_id"]
        and saved["release_sha256"] == PREDECESSOR["release_sha256"]
        and saved["transfer_checksum"] == str(archive) + ".sha256",
        "Predecessor carrier drift.",
    )
    review = old.audit(
        archive,
        PREDECESSOR["archive_sha256"],
        commit,
        PREDECESSOR["job_id"],
        PREDECESSOR["release_sha256"],
    )
    s.require(
        saved["review"] == review
        and saved["status"] == review["status"]
        and review["status"] == "no_attempt_receipt",
        "Predecessor negative audit drift.",
    )
    public = n.read_tar(a._file(archive, n.LIMIT), n.LIMIT, old.MEMBERS)
    meta = x.c.decode_json(public["anchor.json"])
    collected = x.c.decode_json(public["collection.json"])
    s.require(
        meta["source"] == release["manifest"]["source"] == SOURCE
        and meta["specification_sha256"] == SPECIFICATION
        and meta["contract"] is None
        and collected["batch"] is None
        and collected["operation"] is None
        and collected["worker_identity"] is None,
        "Negative precursor is not the reviewed prelaunch failure.",
    )
    s.require(
        n.read_json(claim / "batch-outcome.json") == collected["wrapper"],
        "Preserved wrapper drift.",
    )
    for kind, suffix in (("stdout", "out"), ("stderr", "err")):
        log = x.collect_entry_log(claim / f"slurm-2208339.{suffix}")
        s.require(log == collected["early_logs"][kind], "Preserved early-log drift.")
    # Reuse the original sealed raw-HEAD inventory as immutable historical data.
    # Do not require historical Git on compute, or clean historical ignored caches.
    manifest = copy.deepcopy(release["manifest"])
    manifest["schema_version"] = "s2-historical-tracked-source-v1"
    identity.verify_historical_source(spec["checkout"], manifest, commit, s.digest(manifest))
    s.require(
        records == {path: a.sha_file(path, n.LIMIT) for path in records},
        "Predecessor changed during audit.",
    )
    return {
        "identity": copy.deepcopy(PREDECESSOR),
        "specification": spec,
        "manifest": manifest,
        "records": records,
        "archive": str(archive),
    }


def seal_release(envelope, plan):
    release = prior.seal_release(envelope, plan)
    release["schema_version"] = SCHEMA
    release["history"].append(seal_predecessor())
    release["diagnostic"] = seal_diagnostic()
    return validate_release(release, envelope["source_commit"], s.digest(release))


def validate_diagnostic(record):
    q._keys(record, {"identity", "archive"})
    s.require(record["identity"] == DIAGNOSTIC, "Diagnostic identity drift.")
    archive = Path(record["archive"])
    s.require(
        archive.parent.parent == Path(o.BASE) / diagnostic.CLAIM_NAME
        and archive.parent.name.startswith("collection-")
        and archive.name == "s2-allocation-diagnostic-evidence.tar.gz",
        "Diagnostic archive location drift.",
    )


def verify_diagnostic(record):
    """Original negative reader, no scheduler query or historical code execution."""
    validate_diagnostic(record)
    path = Path(record["archive"])
    q._safe_path(path)
    result = diagnostic.audit(
        path,
        DIAGNOSTIC["archive_sha256"],
        DIAGNOSTIC["source_commit"],
        DIAGNOSTIC["job_id"],
        DIAGNOSTIC["plan_sha256"],
    )
    s.require(result["status"] == "observed_mismatch_or_query_failure", "Diagnostic status drift.")
    return record


def seal_diagnostic():
    claim = Path(o.BASE) / diagnostic.CLAIM_NAME
    q._safe_path(claim)
    saved = n.read_json(claim / "collection.json")
    s.require(saved["sha256"] == DIAGNOSTIC["archive_sha256"], "Diagnostic receipt drift.")
    return verify_diagnostic({"identity": copy.deepcopy(DIAGNOSTIC), "archive": saved["archive"]})
