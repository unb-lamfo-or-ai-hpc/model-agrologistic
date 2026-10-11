"""One fresh normal synthetic observation; no adverse/native/production/repeat route."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import io
import secrets
import shlex
import sys
import tarfile
import tempfile
import time
from pathlib import Path

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in {"start", "collect", "batch", "worker", "audit"}:
        raise PermissionError("Normal synthetic entries only.")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mvp2_h300_controls as c  # noqa: E402
from scripts import mvp2_s2_batch_adapter as a  # noqa: E402
from scripts import mvp2_s2_compute_identity as identity  # noqa: E402
from scripts import mvp2_s2_compute_integration as x  # noqa: E402
from scripts import mvp2_s2_first_normal as n  # noqa: E402
from scripts import mvp2_s2_operational as o  # noqa: E402
from scripts import mvp2_s2_slurm_step as s  # noqa: E402
from scripts import mvp2_s2_slurm_synthetic as q  # noqa: E402

ENTRY = "scripts/mvp2_s2_compute_normal.py"
DRIVER = "scripts/npad_s2_compute_normal.sh"
CLAIM = ".mvp2-s2-compute-integration-v1"
MEMBERS = {"anchor.json", "collection.json", "review.json"}


def claim_path():
    path = Path(o.BASE) / CLAIM
    q._safe_path(path)
    return path


def local_entry(envelope):
    s.require(
        Path(__file__).resolve() == Path(envelope["checkout"]) / ENTRY
        and Path(sys.executable).resolve() == Path(envelope["python"]),
        "Frozen entry/runtime mismatch.",
    )


def validate_proposal(proposal, commit, digest):
    item = x.validate_release(proposal, commit, digest)
    s.require(
        item["plan"]["specification"]["job_id"] == "1"
        and {ENTRY, DRIVER} <= set(item["manifest"]["files"]),
        "Unreviewed operational proposal.",
    )
    return item


def derive_release(proposal, commit, proposal_digest, job):
    item = validate_proposal(proposal, commit, proposal_digest)
    # Only the acknowledged job changes. Never reseal history or adapt runtime after sbatch.
    item["plan"]["specification"]["job_id"] = job
    return x.validate_release(item, commit, s.digest(item))


def submit_argv(envelope, claim):
    s.require(Path(claim) == claim_path(), "Submission claim drift.")
    old = n.submit_argv(envelope, n.claim_path())
    return (
        old[0],
        old[1],
        "--job-name=mvp2-s2-compute-normal",
        *old[3:-3],
        "--output=" + str(claim / "slurm-%j.out"),
        "--error=" + str(claim / "slurm-%j.err"),
        str(claim / "batch.sh"),
    )


def batch_script(proposal, digest):
    env = proposal["envelope"]
    return (
        "#!/bin/sh\nexec "
        + shlex.join(
            (
                env["python"],
                "-B",
                "-I",
                env["checkout"] + "/" + ENTRY,
                "batch",
                "--source-sha",
                env["source_commit"],
                "--proposal-sha",
                digest,
            )
        )
        + "\n"
    ).encode("ascii")


def submission_record(proposal, digest):
    return {
        "source_commit": proposal["envelope"]["source_commit"],
        "proposal_sha256": digest,
        "argv_sha256": s.digest(submit_argv(proposal["envelope"], claim_path())),
        "script_sha256": hashlib.sha256(batch_script(proposal, digest)).hexdigest(),
        "scope": "compute_normal_only",
        **n.FUTURE,
    }


def load_release(commit, *, proposal_digest=None, release_digest=None):
    """Read-only, Git-free binding from pre-effect proposal to acknowledged release."""
    claim = claim_path()
    proposal = n.read_json(claim / "proposal.json", x.RELEASE_LIMIT)
    intent = n.read_json(claim / "intent.json")
    digest = proposal_digest or intent["proposal_sha256"]
    proposal = validate_proposal(proposal, commit, digest)
    s.require(
        intent == {"source_commit": commit, "proposal_sha256": digest, **n.FUTURE},
        "Proposal intent drift.",
    )
    s.require(
        n.read_json(claim / "submission-intent.json") == submission_record(proposal, digest)
        and a._file(claim / "batch.sh", 8192) == batch_script(proposal, digest),
        "Submission byte binding drift.",
    )
    job = n.read_json(claim / "job.json")
    release = derive_release(proposal, commit, digest, job["job_id"])
    final_digest = s.digest(release)
    s.require(
        (release_digest is None or final_digest == release_digest)
        and n.read_json(claim / "release.json", x.RELEASE_LIMIT) == release
        and job
        == {
            "source_commit": commit,
            "job_id": job["job_id"],
            "specification_sha256": s.digest(release["plan"]["specification"]),
            "release_sha256": final_digest,
        },
        "Acknowledged release drift.",
    )
    local_entry(release["envelope"])
    return release, final_digest


def submit_components(proposal, commit, latch, submit):
    """Reserve before effect; uncertain acknowledgement consumes the claim forever."""
    digest = s.digest(proposal)
    proposal = validate_proposal(proposal, commit, digest)
    claim = claim_path()
    spec = proposal["plan"]["specification"]
    q._safe_path(Path(spec["run"]))
    s.require(not Path(spec["run"]).exists(), "Worker run already exists.")
    claim.mkdir(mode=0o700, exist_ok=False)
    c.write_once(
        claim / "intent.json", {"source_commit": commit, "proposal_sha256": digest, **n.FUTURE}
    )
    c.write_once(claim / "proposal.json", proposal)
    with (claim / "batch.sh").open("xb") as stream:
        stream.write(batch_script(proposal, digest))
    c.write_once(claim / "submission-intent.json", submission_record(proposal, digest))
    if latch.reason is not None:
        c.write_once(claim / "stop.json", {"reason": "interrupted_before_submit", **n.FUTURE})
        return {"status": "stopped_before_submit"}
    try:
        acknowledgement = submit(submit_argv(proposal["envelope"], claim))
        job = n.parse_acknowledgement(acknowledgement)
        release = derive_release(proposal, commit, digest, job)
        final_digest = s.digest(release)
        c.write_once(claim / "release.json", release)
        if latch.reason is not None:
            c.write_once(claim / "stop.json", {"reason": "interrupted_after_submit", **n.FUTURE})
        receipt = {
            "source_commit": commit,
            "job_id": job,
            "release_sha256": final_digest,
            "specification_sha256": s.digest(release["plan"]["specification"]),
        }
        # Publish last: a fast batch waits for this complete release, never for a guessed job.
        c.write_once(claim / "job.json", receipt)
        return {"status": "submitted_normal_only", "proposal_sha256": digest, **receipt}
    except (Exception, KeyboardInterrupt):
        c.write_once(
            claim / "submission-unknown.json", {"status": "unknown_effect_no_retry", **n.FUTURE}
        )
        return {"status": "unknown_effect_no_retry"}


def start(commit):
    n.require_host()
    q._hash(commit, 40)
    if claim_path().exists():
        return collect(commit)
    envelope = o.observe_envelope(Path(__file__).resolve().parents[1], commit)
    local_entry(envelope)
    plan = o.normal_plan(
        envelope,
        s.digest(envelope),
        commit,
        run=o.BASE + "/s2n-" + secrets.token_hex(4),
        nonce=secrets.token_hex(32),
        job_id="1",
    )
    # All Git checks, historical replay and raw HEAD sealing happen on the login node.
    proposal = x.seal_release(envelope, plan)
    transport = a.RealTransport(plan["specification"])
    allowed = submit_argv(envelope, claim_path())

    def submit(argv):
        s.require(argv == allowed, "Submission descriptor drift.")
        n.recheck(envelope)
        # Recheck bytes, not a new seal, immediately before the single scheduler effect.
        x.verify_release(
            proposal, commit, s.digest(proposal), role="batch", deadline=time.monotonic() + 120
        )
        s.require(latch.reason is None, "Interrupted before scheduler effect.")
        return transport._open(argv).query_result(10, 4096)

    with o.StopLatch().installed() as latch:
        return submit_components(proposal, commit, latch, submit)


class NormalTransport(x.ComputeTransport):
    def worker_command(self):
        return tuple(
            self.item["checkout"] + "/" + ENTRY
            if value == self.item["checkout"] + "/" + x.ENTRY
            else value
            for value in x.worker_argv(self.item, self.release_digest)
        )


def await_release(claim, latch, *, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + 30
    while not (claim / "job.json").exists():
        s.require(
            clock() < deadline
            and latch.reason is None
            and not (claim / "stop.json").exists()
            and not (claim / "submission-unknown.json").exists(),
            "No acknowledged release; never launch.",
        )
        sleep(0.2)
    s.require(latch.reason is None and not (claim / "stop.json").exists(), "Release stopped.")


def batch(commit, proposal_digest):
    started = time.monotonic()
    try:
        n.require_host()
        with o.StopLatch().installed() as latch:
            await_release(claim_path(), latch)
            release, digest = load_release(commit, proposal_digest=proposal_digest)
    except (Exception, KeyboardInterrupt) as error:
        x.emit_error("batch", "release", error)
        raise SystemExit(2) from None
    return x.batch_components(
        claim_path(),
        release,
        commit,
        digest,
        started,
        transport_factory=lambda spec, **kw: NormalTransport(spec, release_digest=digest, **kw),
    )


def worker(commit, specification_digest, release_digest):
    try:
        n.require_host()
        release, digest = load_release(commit, release_digest=release_digest)
        s.require(not (claim_path() / "stop.json").exists(), "Worker release stopped.")
    except (Exception, KeyboardInterrupt) as error:
        x.emit_error("worker", "release", error)
        raise SystemExit(2) from None
    return x.worker_components(release, commit, digest, specification_digest)


def anchor(release, digest, contract):
    spec = release["plan"]["specification"]
    return {
        "schema_version": "s2-compute-normal-anchor-v1",
        "source_commit": spec["source_commit"],
        "job_id": spec["job_id"],
        "release_sha256": digest,
        "specification_sha256": s.digest(spec),
        "source": release["manifest"]["source"],
        "batch_runtime": identity.expected_compute_runtime(spec, "batch"),
        "worker_runtime": identity.expected_compute_runtime(spec, "worker"),
        "contract": contract,
        "history": copy.deepcopy(list(x.HISTORY)),
        **n.FUTURE,
    }


def review_public(records, commit, job, release_digest):
    q._keys(records, MEMBERS)
    meta = c.decode_json(records["anchor.json"])
    q._keys(
        meta,
        {
            "schema_version",
            "source_commit",
            "job_id",
            "release_sha256",
            "specification_sha256",
            "source",
            "batch_runtime",
            "worker_runtime",
            "contract",
            "history",
            *n.FUTURE,
        },
    )
    s.require(
        meta["schema_version"] == "s2-compute-normal-anchor-v1"
        and meta["source_commit"] == commit
        and meta["job_id"] == job
        and meta["release_sha256"] == release_digest
        and meta["history"] == list(x.HISTORY)
        and all(meta[k] is False for k in n.FUTURE),
        "Public anchor drift.",
    )
    q._keys(meta["source"], {"source_sha256", "worker_sha256", "tracked_count"})
    q._hash(meta["source"]["source_sha256"])
    q._hash(meta["source"]["worker_sha256"])
    s.require(
        type(meta["source"]["tracked_count"]) is int
        and 1 <= meta["source"]["tracked_count"] <= 1024,
        "Source count drift.",
    )
    baseline = n.read_json(
        Path(__file__).resolve().parents[1] / "docs/evidence/s2-envelope-pr63/receipt.json"
    )
    for role in ("batch", "worker"):
        expected = {
            "schema_version": "s2-compute-runtime-v1",
            "role": role,
            "python_sha256": baseline["python_sha256"],
            "verified_tools_sha256": {
                k: baseline["tool_sha256"][k]
                for k in (identity.COMPUTE_TOOLS if role == "batch" else ())
            },
            "login_only_tools": ["git", "sbatch"],
            "execution_admitted": False,
        }
        s.require(meta[role + "_runtime"] == expected, "Frozen public runtime drift.")
    if meta["contract"] is not None:
        contract = q.validate_contract(meta["contract"])
        s.require(
            contract["case"] == "normal"
            and contract["binding"]["source_commit"] == commit
            and contract["binding"]["job_id"] == job,
            "Contract identity drift.",
        )
    review = x.review_portable_collection(
        c.decode_json(records["collection.json"]),
        meta["specification_sha256"],
        meta["batch_runtime"],
        meta["worker_runtime"],
        meta["contract"],
        release_digest,
        meta["source"],
        commit,
        job,
    )
    return {
        "schema_version": "s2-compute-normal-review-v1",
        "status": review["status"],
        "source_commit": commit,
        "job_id": job,
        "release_sha256": release_digest,
        "collection": review,
        **n.FUTURE,
    }


def audit(path, checksum, commit, job, release_digest):
    q._hash(checksum)
    raw = a._file(path, n.LIMIT)
    s.require(hashlib.sha256(raw).hexdigest() == checksum, "Archive checksum drift.")
    records = n.read_tar(raw, n.LIMIT, MEMBERS)
    review = review_public(records, commit, job, release_digest)
    s.require(c.decode_json(records["review.json"]) == review, "Portable review drift.")
    return review


def pack(destination, inner, release, digest, contract):
    spec = release["plan"]["specification"]
    raw = a._file(inner["download"], n.LIMIT)
    s.require(hashlib.sha256(raw).hexdigest() == inner["sha256"], "Inner checksum drift.")
    original = n.read_tar(raw, n.LIMIT, {"collection.json", "review.json"})
    records = {
        "anchor.json": c.encoded(anchor(release, digest, contract)),
        "collection.json": original["collection.json"],
        "review.json": b"null",
    }
    review = review_public(records, spec["source_commit"], spec["job_id"], digest)
    records["review.json"] = c.encoded(review)
    s.require(sum(map(len, records.values())) < n.LIMIT - 16384, "Public archive bound.")
    target = Path(destination) / "s2-compute-normal-evidence.tar.gz"
    with target.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for name, data in sorted(records.items()):
                info = tarfile.TarInfo(name)
                info.size, info.mode = len(data), 0o600
                archive.addfile(info, io.BytesIO(data))
    checksum = a.sha_file(target, n.LIMIT)
    s.require(
        audit(target, checksum, spec["source_commit"], spec["job_id"], digest) == review,
        "Published replay drift.",
    )
    with target.with_name(target.name + ".sha256").open("x", encoding="ascii") as stream:
        stream.write(checksum + "  " + target.name + "\n")
    return {
        "status": review["status"],
        "job_id": spec["job_id"],
        "release_sha256": digest,
        "sha256": checksum,
        "download": str(target),
        "transfer_checksum": str(target) + ".sha256",
        "review": review,
    }


def collect(commit):
    n.require_host()
    claim = claim_path()
    if not (claim / "job.json").exists():
        return {"status": "unreleased_claim_no_retry"}
    release, digest = load_release(commit)
    spec = release["plan"]["specification"]
    saved = claim / "collection.json"
    if saved.exists():
        result = n.read_json(saved)
        target = Path(result["download"])
        q._safe_path(target)
        s.require(
            target.parent.parent == claim
            and target.parent.name.startswith("collection-")
            and target.name == "s2-compute-normal-evidence.tar.gz"
            and result["transfer_checksum"] == str(target) + ".sha256"
            and result["job_id"] == spec["job_id"]
            and result["release_sha256"] == digest
            and audit(target, result["sha256"], commit, spec["job_id"], digest) == result["review"]
            and result["status"] == result["review"]["status"],
            "Cached collection drift.",
        )
        return result
    n.recheck(release["envelope"])  # Login only; terminal evidence is never a compute preflight.
    text = a.RealTransport(spec).command(
        (
            spec["tools"]["sacct"],
            "--noheader",
            "--parsable2",
            "--jobs=" + spec["job_id"],
            "--format=JobIDRaw,State,ExitCode,ElapsedRaw",
        )
    )
    rows = a.accounting(text, spec["job_id"])
    if (
        spec["job_id"] not in rows
        or spec["job_id"] + ".batch" not in rows
        or not all(row["state"] in a.TERMINAL for row in rows.values())
    ):
        return {"status": "nonterminal_or_accounting_pending", "job_id": spec["job_id"]}
    destination = Path(tempfile.mkdtemp(prefix="collection-", dir=claim))
    inner = x.collect_components(claim, destination / "replay", release, commit, digest, text)
    contract_path = Path(spec["run"]) / "contract.json"
    contract = n.read_json(contract_path) if contract_path.exists() else None
    result = pack(destination, inner, release, digest, contract)
    c.write_once(saved, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    for action in ("start", "collect", "batch", "worker", "audit"):
        child = subs.add_parser(action)
        child.add_argument("--source-sha", required=True)
        if action == "batch":
            child.add_argument("--proposal-sha", required=True)
        if action in {"worker", "audit"}:
            child.add_argument("--release-sha", required=True)
        if action == "worker":
            child.add_argument("--specification-sha", required=True)
        if action == "audit":
            for name in ("archive", "sha256", "job"):
                child.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if args.action == "worker":
        worker(args.source_sha, args.specification_sha, args.release_sha)
        return 0
    if args.action == "batch":
        result = batch(args.source_sha, args.proposal_sha)
    elif args.action == "audit":
        result = audit(args.archive, args.sha256, args.source_sha, args.job, args.release_sha)
    else:
        result = {"start": start, "collect": collect}[args.action](args.source_sha)
    print("COMPUTE_NORMAL_STATUS=" + result["status"])
    if args.action != "audit":
        print("PRESERVE_CLAIM=" + str(claim_path()))
    for key in (
        "job_id",
        "proposal_sha256",
        "release_sha256",
        "sha256",
        "download",
        "transfer_checksum",
    ):
        if result.get(key) is not None:
            print(key.upper() + "=" + result[key])
    print("NO_ADVERSE_NATIVE_MINIATURE_H300_OR_REPEAT_ADMITTED")
    return (
        0
        if result["status"]
        in {
            "submitted_normal_only",
            "attempt_preserved",
            "nonterminal_or_accounting_pending",
            "no_attempt_receipt",
            "integrity_replayed_not_live_qualified",
        }
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
