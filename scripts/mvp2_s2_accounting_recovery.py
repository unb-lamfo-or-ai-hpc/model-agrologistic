"""Collect job 2208459 from a separate reader; never mutate its frozen claim.

No start, worker, signal or retry entry. The raw, bounded forensic carrier is
available even when semantic replay rejects the original partial observation.
This is a new analysis identity, not a replacement execution certificate.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import re
import sys
import tarfile
import tempfile
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mvp2_h300_controls as c  # noqa: E402
from scripts import mvp2_s2_allocation_diagnostic as d  # noqa: E402
from scripts import mvp2_s2_batch_adapter as a  # noqa: E402
from scripts import mvp2_s2_compute_identity as identity  # noqa: E402
from scripts import mvp2_s2_compute_integration as x  # noqa: E402
from scripts import mvp2_s2_first_normal as n  # noqa: E402
from scripts import mvp2_s2_node_normal as y  # noqa: E402
from scripts import mvp2_s2_operational as o  # noqa: E402
from scripts import mvp2_s2_slurm_step as s  # noqa: E402
from scripts import mvp2_s2_slurm_synthetic as q  # noqa: E402

JOB = "2208459"
SOURCE = "9911bd68db480fccea2fd774ac0a969238300ece"
PROPOSAL = "ef93f3ebc9327902d65496940a65346b60090b93ce27c89f974c3669b3bc1c06"
RELEASE = "3bc4a50afa926fdd811e7e4f09cb5a76fbb6d16f1e333e4d20a7bc6500ced4e8"
LIMIT = 16 * 1024**2
CLAIM_FILES = (
    "proposal.json",
    "intent.json",
    "submission-intent.json",
    "batch.sh",
    "release.json",
    "job.json",
    "batch-outcome.json",
    "slurm-2208459.out",
    "slurm-2208459.err",
    "stop.json",
)
RUN_FILES = (
    "claim.json",
    "worker-plan.json",
    "launch-intent.json",
    "binding.json",
    "contract.json",
    "worker-identity.json",
    "attempt.json",
    "operation.json",
    "operation-diagnostic.json",
    "term-intent.json",
    "kill-intent.json",
    "local-client-stop-intent.json",
    "heartbeat.json",
    "heartbeat.pending",
)


def bound_release(claim):
    """Verify the original immutable receipts without executing their checkout."""
    s.require(Path(claim) == y.claim_path(), "Wrong preserved claim.")
    proposal = n.read_json(claim / "proposal.json", x.RELEASE_LIMIT)
    y.validate_proposal(proposal, SOURCE, PROPOSAL)
    s.require(
        n.read_json(claim / "intent.json")
        == {"source_commit": SOURCE, "proposal_sha256": PROPOSAL, **n.FUTURE}
        and n.read_json(claim / "submission-intent.json") == y.submission_record(proposal, PROPOSAL)
        and a._file(claim / "batch.sh", 8192) == y.batch_script(proposal, PROPOSAL),
        "Preserved submission drift.",
    )
    release = y.derive_release(proposal, SOURCE, PROPOSAL, JOB)
    s.require(
        s.digest(release) == RELEASE
        and n.read_json(claim / "release.json", x.RELEASE_LIMIT) == release
        and n.read_json(claim / "job.json")
        == {
            "source_commit": SOURCE,
            "job_id": JOB,
            "release_sha256": RELEASE,
            "specification_sha256": s.digest(release["plan"]["specification"]),
        },
        "Preserved release drift.",
    )
    spec = release["plan"]["specification"]
    source, run = Path(spec["checkout"]), Path(spec["run"])
    s.require(
        source.name == "source"
        and source.parent.parent == claim.parent
        and source.parent.name.startswith("s2-node-driver-")
        and run.parent == claim.parent
        and run.name.startswith("s2n-"),
        "Original source/run location drift.",
    )
    identity.verify_compute_source(
        source, release["manifest"], SOURCE, s.digest(release["manifest"])
    )
    return release


def snapshot(claim, run):
    """Read only explicitly named products, never recursively collect a source/license."""
    records, missing = {}, []
    selections = [("claim/" + name, claim / name) for name in CLAIM_FILES]
    selections += [("run/" + name, run / name) for name in RUN_FILES]
    selections += [("run/worker/" + name, run / "worker" / name) for name in q.WORKER_FILES]
    q._safe_path(run)
    for path in sorted(run.iterdir()):
        if path.name.startswith(("sample-", "event-")):
            match = re.fullmatch(r"(sample|event)-([0-9]{4})\.json", path.name)
            s.require(
                match is not None
                and int(match[2]) < (a.MAX_SAMPLES if match[1] == "sample" else 1024),
                "Indexed product bound.",
            )
            selections.append(("run/" + path.name, path))
    for name, path in selections:
        try:
            records[name] = a._file(
                path,
                x.RELEASE_LIMIT
                if name.endswith("/release.json") or name.endswith("/proposal.json")
                else 1024**2,
            )
        except FileNotFoundError:
            missing.append(name)
        s.require(sum(map(len, records.values())) <= LIMIT, "Forensic carrier bound.")
    return records, missing


def pack(destination, records):
    """Exclusive, regular-member archive with deterministic contents and a sidecar."""
    s.require(sum(map(len, records.values())) <= LIMIT, "Forensic carrier bound.")
    target = destination / "s2-node-accounting-recovery-2208459.tar.gz"
    with target.open("xb") as stream, gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for name, data in sorted(records.items()):
                s.require(a.safe_repo_name(name), "Unsafe member name.")
                member = tarfile.TarInfo(name)
                member.size, member.mode = len(data), 0o600
                archive.addfile(member, io.BytesIO(data))
    digest = a.sha_file(target, LIMIT + 1024**2)
    # Verify bytes and every member before exposing the transfer path.
    with tarfile.open(target, "r:gz") as archive:
        members = archive.getmembers()
        s.require(len(members) == len(records), "Archive member drift.")
        for member in members:
            s.require(
                member.isfile() and archive.extractfile(member).read() == records[member.name],
                "Archive byte drift.",
            )
    with Path(str(target) + ".sha256").open("x", encoding="ascii", newline="\n") as stream:
        stream.write(digest + "  " + target.name + "\n")
    return target, digest


def collect(analysis_sha):
    n.require_host()
    # Qualify the NEW reader separately; never substitute it for the execution identity.
    root = Path(__file__).resolve().parents[1]
    files = d.source_files(root, analysis_sha)
    claim = y.claim_path()
    release = bound_release(claim)
    spec = release["plan"]["specification"]
    s.require(
        a.sha_file(spec["tools"]["sacct"]) == spec["tools_sha256"]["sacct"],
        "Accounting tool drift.",
    )
    argv = (
        spec["tools"]["sacct"],
        "--noheader",
        "--parsable2",
        "--jobs=" + JOB,
        "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
    )
    text = a.RealTransport(spec).command(argv)
    rows = a.accounting(text, JOB)
    s.require(
        JOB in rows
        and JOB + ".batch" in rows
        and all(row["state"] in a.TERMINAL for row in rows.values()),
        "Accounting pending/nonterminal; no new execution admitted.",
    )
    records, missing = snapshot(claim, Path(spec["run"]))
    destination = Path(tempfile.mkdtemp(prefix="s2-node-recovery-2208459-", dir=o.BASE))
    print("PRESERVE_COLLECTION=" + str(destination), flush=True)
    replay, error = None, None
    try:
        inner = x.collect_components(claim, destination / "replay", release, SOURCE, RELEASE, text)
        contract_path = Path(spec["run"]) / "contract.json"
        contract = n.read_json(contract_path) if contract_path.exists() else None
        inner = y.pack(destination, inner, release, RELEASE, contract)
        records["replay/s2-node-normal-evidence.tar.gz"] = a._file(inner["download"], n.LIMIT)
        replay = inner["review"]
    except (ValueError, KeyError, TypeError, OSError, UnicodeError) as exc:
        # Preserve the actual raw partial evidence; never manufacture a successful review.
        error = type(exc).__name__
    after, after_missing = snapshot(claim, Path(spec["run"]))
    s.require(
        records.keys() - {"replay/s2-node-normal-evidence.tar.gz"} == after.keys()
        and all(records[key] == value for key, value in after.items())
        and missing == after_missing,
        "Original evidence changed during collection.",
    )
    records["accounting.txt"] = text.encode("utf-8")
    manifest = {
        "schema_version": "s2-node-accounting-recovery-v1",
        "status": "captured_not_live_qualified",
        "execution_source": SOURCE,
        "analysis_source": analysis_sha,
        "analysis_files_sha256": s.digest(files),
        "job_id": JOB,
        "proposal_sha256": PROPOSAL,
        "release_sha256": RELEASE,
        "accounting_argv": list(argv[1:]),
        "accounting": rows,
        "files": {
            name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
            for name, data in records.items()
        },
        "missing": missing,
        "semantic_review": replay,
        "replay_error_kind": error,
        **n.FUTURE,
    }
    records["recovery.json"] = c.encoded(manifest)
    target, digest = pack(destination, records)
    print("RECOVERY_STATUS=" + manifest["status"])
    print("SEMANTIC_REPLAY=" + ("replayed_not_live_qualified" if replay else "rejected_preserved"))
    print("SHA256=" + digest)
    print("DOWNLOAD=" + str(target))
    print("TRANSFER_CHECKSUM=" + str(target) + ".sha256")
    print("NO_JOB_SUBMITTED_OR_REPEATED; ORIGINAL_CLAIM_UNCHANGED")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-sha", required=True)
    args = parser.parse_args()
    collect(args.analysis_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
