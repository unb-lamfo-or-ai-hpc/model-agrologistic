"""One separately reviewed normal observation after failed job 2207167; no retry loop."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import io
import secrets
import sys
import tarfile
import time
from pathlib import Path

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in {"start", "collect", "batch", "worker", "audit"}:
        raise PermissionError("Only the normal-recovery scoped wrapper entries are available.")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mvp2_h300_controls as c  # noqa: E402
from scripts import mvp2_s2_batch_adapter as a  # noqa: E402
from scripts import mvp2_s2_first_normal as n  # noqa: E402
from scripts import mvp2_s2_operational as o  # noqa: E402
from scripts import mvp2_s2_slurm_step as s  # noqa: E402
from scripts import mvp2_s2_slurm_synthetic as q  # noqa: E402

ENTRY = "scripts/mvp2_s2_normal_recovery.py"
CLAIM = ".mvp2-s2-normal-recovery-pr67-v1"
PREDECESSOR = {
    "source_commit": "12691638cd85d5218725bf704dc6b9452b1ca90c",
    "job_id": "2207167",
    "archive_sha256": "03ee4d87bf69994fc4f0401e206a67109539ad2dfe0770cd3246b7415e952007",
}
PREDECESSOR_FILES = (
    "intent.json",
    "private-envelope.json",
    "normal-plan.json",
    "job.json",
    "batch-outcome.json",
    "submission-intent.json",
    "batch.sh",
    "collection.json",
)
LIMIT = n.LIMIT + 64 * 1024
MEMBERS = {"lineage.json", "normal-evidence.tar.gz", "review.json"}


def claim_path():
    result = Path(o.BASE) / CLAIM
    q._safe_path(result)
    return result


def verify_predecessor():
    """Read/replay only: never dispatch the old entry or mutate its consumed claim."""
    old = n.claim_path()
    snapshot = {name: a.sha_file(old / name, n.LIMIT) for name in PREDECESSOR_FILES}
    intent = n.read_json(old / "intent.json", 8192)
    envelope = o.validate_envelope(
        n.read_json(old / "private-envelope.json"), PREDECESSOR["source_commit"]
    )
    n.checked_baseline(envelope)
    plan = o.validate_normal_plan(
        n.read_json(old / "normal-plan.json"),
        envelope,
        s.digest(envelope),
        PREDECESSOR["source_commit"],
    )
    spec = plan["specification"]
    expected_intent = {
        "source_commit": PREDECESSOR["source_commit"],
        "envelope_sha256": s.digest(envelope),
        "nonce": spec["nonce"],
        "run": spec["run"],
        "campaign": copy.deepcopy(o.CAMPAIGN),
        **o.FLAGS,
    }
    s.require(intent == expected_intent, "Preserved predecessor intent drift.")
    s.require(
        n.read_json(old / "job.json")
        == {
            "source_commit": PREDECESSOR["source_commit"],
            "job_id": PREDECESSOR["job_id"],
            "specification_sha256": s.digest(spec),
        },
        "Preserved predecessor job drift.",
    )
    s.require(spec["job_id"] == PREDECESSOR["job_id"], "Predecessor plan job drift.")
    script = n.batch_script(envelope, PREDECESSOR["source_commit"])
    s.require(a._file(old / "batch.sh", 8192) == script, "Predecessor script drift.")
    s.require(
        n.read_json(old / "submission-intent.json")
        == {
            "argv_sha256": s.digest(n.submit_argv(envelope, old)),
            "script_sha256": hashlib.sha256(script).hexdigest(),
            "source_commit": PREDECESSOR["source_commit"],
            "envelope_sha256": s.digest(envelope),
            "scope": "first_normal_only",
            **n.FUTURE,
        },
        "Predecessor submission binding drift.",
    )
    saved = n.read_json(old / "collection.json")
    archive = Path(saved["download"])
    q._safe_path(archive)
    s.require(
        archive.name == "s2-first-normal-evidence.tar.gz"
        and archive.parent.parent == old
        and archive.parent.name.startswith("collection-")
        and saved["sha256"] == PREDECESSOR["archive_sha256"]
        and saved["transfer_checksum"] == str(archive) + ".sha256",
        "Predecessor collection location/hash drift.",
    )
    original = n.audit(
        archive, PREDECESSOR["archive_sha256"], PREDECESSOR["source_commit"], PREDECESSOR["job_id"]
    )
    public = n.read_json(
        Path(__file__).resolve().parents[1] / "docs/evidence/s2-first-normal-2207167/records.json"
    )
    s.require(
        original == public["review.json"] == saved["review"]
        and s.digest(spec) == original["specification_sha256"]
        and envelope["source"] == public["anchor.json"]["source"]
        and s.digest(envelope) == public["anchor.json"]["envelope_sha256"]
        and saved["status"] == original["status"]
        and saved["job_id"] == PREDECESSOR["job_id"]
        and n.read_json(old / "batch-outcome.json") == public["wrapper.json"],
        "Preserved negative predecessor drift.",
    )
    # Old checkout is inspected through the existing raw-byte Git reader, never executed.
    transport = a.RealTransport(spec)
    s.require(
        a.verify_checkout(spec, transport.source_command) == envelope["source"],
        "Preserved predecessor checkout drift.",
    )
    s.require(
        snapshot == {name: a.sha_file(old / name, n.LIMIT) for name in PREDECESSOR_FILES},
        "Predecessor changed during observation.",
    )
    return {**PREDECESSOR, "snapshot_sha256": s.digest(snapshot)}


def validate_local(envelope, commit):
    envelope = o.validate_envelope(envelope, commit)
    s.require(
        Path(__file__).resolve() == Path(envelope["checkout"]) / ENTRY
        and Path(sys.executable).resolve() == Path(envelope["python"]),
        "Recovery entry/runtime mismatch.",
    )
    n.checked_baseline(envelope)
    return envelope


def load_claim(commit):
    q._hash(commit, 40)
    claim = claim_path()
    predecessor = n.read_json(claim / "predecessor.json", 4096)
    s.require(predecessor == verify_predecessor(), "Preserved predecessor snapshot drift.")
    intent = n.read_json(claim / "intent.json", 8192)
    envelope = validate_local(n.read_json(claim / "private-envelope.json"), commit)
    proposal = o.normal_plan(
        envelope, s.digest(envelope), commit, run=intent["run"], nonce=intent["nonce"], job_id="1"
    )
    spec = proposal["specification"]
    s.require(
        intent
        == {
            "source_commit": commit,
            "envelope_sha256": s.digest(envelope),
            "nonce": spec["nonce"],
            "run": spec["run"],
            "campaign": copy.deepcopy(o.CAMPAIGN),
            "predecessor": predecessor,
            "scope": "normal_recovery_only",
            **o.FLAGS,
        },
        "Incomplete/drifted recovery claim; preserve, never retry.",
    )
    s.require(
        intent["run"] != n.read_json(n.claim_path() / "intent.json")["run"],
        "Cannot reuse predecessor worker run.",
    )
    return claim, envelope, intent


def load_plan(commit):
    claim, envelope, intent = load_claim(commit)
    plan = o.validate_normal_plan(
        n.read_json(claim / "normal-plan.json"), envelope, s.digest(envelope), commit
    )
    spec = plan["specification"]
    s.require(
        n.read_json(claim / "job.json", 4096)
        == {
            "source_commit": commit,
            "job_id": spec["job_id"],
            "specification_sha256": s.digest(spec),
        }
        and spec["run"] == intent["run"]
        and spec["nonce"] == intent["nonce"]
        and spec["job_id"] != PREDECESSOR["job_id"],
        "Recovery release binding drift.",
    )
    script = batch_script(envelope, commit)
    s.require(
        n.read_json(claim / "submission-intent.json")
        == {
            "argv_sha256": s.digest(submit_argv(envelope, claim)),
            "script_sha256": hashlib.sha256(script).hexdigest(),
            "source_commit": commit,
            "envelope_sha256": s.digest(envelope),
            "scope": "normal_recovery_only",
            **n.FUTURE,
        }
        and a._file(claim / "batch.sh", 8192) == script,
        "Recovery submission release drift.",
    )
    return claim, envelope, spec


def submit_argv(envelope, claim):
    s.require(Path(claim) == claim_path(), "Recovery submission path drift.")
    old = n.submit_argv(envelope, n.claim_path())
    return (
        old[0],
        old[1],
        "--job-name=mvp2-s2-normal-recovery",
        *old[3:-3],
        "--output=" + str(claim / "slurm-%j.out"),
        "--error=" + str(claim / "slurm-%j.err"),
        str(claim / "batch.sh"),
    )


def batch_script(envelope, commit):
    return n.batch_script(envelope, commit).replace(n.ENTRY.encode("ascii"), ENTRY.encode("ascii"))


def start(commit):
    n.require_host()
    q._hash(commit, 40)
    claim = claim_path()
    if claim.exists():
        return collect(commit)
    predecessor = verify_predecessor()
    envelope = validate_local(
        o.observe_envelope(Path(__file__).resolve().parents[1], commit), commit
    )
    run, nonce = o.BASE + "/s2n-" + secrets.token_hex(4), secrets.token_hex(32)
    dummy = o.normal_plan(
        envelope, s.digest(envelope), commit, run=str(run), nonce=nonce, job_id="1"
    )["specification"]
    s.require(
        not Path(run).exists() and run != n.read_json(n.claim_path() / "intent.json")["run"],
        "Worker run collision; no submission.",
    )
    claim.mkdir(mode=0o700, exist_ok=False)
    c.write_once(claim / "predecessor.json", predecessor)
    c.write_once(claim / "private-envelope.json", envelope)
    intent = {
        "source_commit": commit,
        "envelope_sha256": s.digest(envelope),
        "nonce": nonce,
        "run": str(run),
        "campaign": copy.deepcopy(o.CAMPAIGN),
        "predecessor": predecessor,
        "scope": "normal_recovery_only",
        **o.FLAGS,
    }
    c.write_once(claim / "intent.json", intent)
    load_claim(commit)
    transport, allowed = a.RealTransport(dummy), submit_argv(envelope, claim)

    def submit(argv):
        s.require(
            argv == allowed and verify_predecessor() == predecessor,
            "Recovery descriptor/predecessor drift before effect.",
        )
        return transport._open(argv).query_result(10, 4096)

    with o.StopLatch().installed() as latch:
        return n.submit_components(
            claim,
            envelope,
            commit,
            intent,
            latch,
            submit,
            descriptor=submit_argv,
            script_builder=batch_script,
            scope="normal_recovery_only",
        )


def worker_argv(spec):
    old = n.normal_worker_argv(spec)
    return tuple(
        spec["checkout"] + "/" + ENTRY if value == spec["checkout"] + "/" + n.ENTRY else value
        for value in old
    )


class RecoveryTransport(n.NormalTransport):
    def worker_command(self):
        return worker_argv(self.item)


class RecoveryAdapter(n.NormalAdapter):
    def worker_command(self):
        return worker_argv(self.item)


def batch(commit):
    n.require_host()
    started = time.monotonic()
    claim, envelope, intent = load_claim(commit)
    (claim / "batch-claim").mkdir(mode=0o700, exist_ok=False)
    return n.batch_components(
        commit,
        claim,
        envelope,
        intent,
        started,
        plan_loader=load_plan,
        transport_factory=RecoveryTransport,
        adapter_factory=RecoveryAdapter,
    )


def worker(commit, specification_sha):
    n.require_host()
    _claim, envelope, spec = load_plan(commit)
    q._hash(specification_sha)
    s.require(
        s.digest(spec) == specification_sha and n.os.environ.get("SLURM_JOB_ID") == spec["job_id"],
        "Recovery worker identity drift.",
    )
    n.recheck(envelope)
    return o.worker_dispatch_components(spec, specification_sha, spec["run"] + "/worker-plan.json")


def review_records(records, commit, job):
    q._keys(records, MEMBERS)
    q._hash(commit, 40)
    lineage = c.decode_json(records["lineage.json"])
    q._keys(
        lineage,
        {
            "schema_version",
            "scope",
            "predecessor",
            "normal_archive_sha256",
            "source_commit",
            "job_id",
            *n.FUTURE,
        },
    )
    inner = records["normal-evidence.tar.gz"]
    s.require(
        lineage
        == {
            "schema_version": "s2-normal-recovery-lineage-v1",
            "scope": "normal_recovery_only",
            "predecessor": PREDECESSOR,
            "normal_archive_sha256": hashlib.sha256(inner).hexdigest(),
            "source_commit": commit,
            "job_id": job,
            **n.FUTURE,
        }
        and job != PREDECESSOR["job_id"]
        and commit != PREDECESSOR["source_commit"],
        "Recovery source/job/predecessor/scope drift.",
    )
    decoded = n.read_tar(
        inner,
        n.LIMIT,
        {
            "anchor.json",
            "accounting.json",
            "wrapper.json",
            "review.json",
            "batch-evidence.tar.gz",
            "operation.json",
        },
    )
    normal = n.review_records(decoded, commit, job)
    s.require(c.decode_json(decoded["review.json"]) == normal, "Recovery inner review drift.")
    wrapper = c.decode_json(decoded["wrapper.json"])
    s.require(
        wrapper["schema_version"] == "s2-first-normal-batch-v2"
        or wrapper["status"] == "missing_terminal_batch_receipt",
        "Recovery requires new diagnostics; never relabel a legacy attempt.",
    )
    return {
        "schema_version": "s2-normal-recovery-review-v1",
        "scope": "normal_recovery_only",
        "status": "integrity_replayed_not_live_qualified",
        "source_commit": commit,
        "job_id": job,
        "predecessor": copy.deepcopy(PREDECESSOR),
        "normal": normal,
        **n.FUTURE,
    }


def audit(path, checksum, commit, job):
    q._hash(checksum)
    raw = a._file(path, LIMIT)
    s.require(hashlib.sha256(raw).hexdigest() == checksum, "Recovery archive checksum drift.")
    records = n.read_tar(raw, LIMIT, MEMBERS)
    review = review_records(records, commit, job)
    s.require(c.decode_json(records["review.json"]) == review, "Recovery review drift.")
    return review


def pack(destination, records, commit, job):
    normal = n.pack(destination, records, commit, job)
    inner = a._file(normal["download"], n.LIMIT)
    payload = {
        "normal-evidence.tar.gz": inner,
        "lineage.json": c.encoded(
            {
                "schema_version": "s2-normal-recovery-lineage-v1",
                "scope": "normal_recovery_only",
                "predecessor": PREDECESSOR,
                "normal_archive_sha256": normal["sha256"],
                "source_commit": commit,
                "job_id": job,
                **n.FUTURE,
            }
        ),
        "review.json": b"null",
    }
    review = review_records(payload, commit, job)
    payload["review.json"] = c.encoded(review)
    target = Path(destination) / "s2-normal-recovery-evidence.tar.gz"
    with target.open("xb") as stream, gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for name, data in sorted(payload.items()):
                info = tarfile.TarInfo(name)
                info.size, info.mode = len(data), 0o600
                archive.addfile(info, io.BytesIO(data))
    checksum = a.sha_file(target, LIMIT)
    s.require(audit(target, checksum, commit, job) == review, "Published recovery audit drift.")
    with target.with_name(target.name + ".sha256").open("x", encoding="ascii") as stream:
        stream.write(checksum + "  " + target.name + "\n")
    return {
        "status": review["status"],
        "job_id": job,
        "sha256": checksum,
        "download": str(target),
        "transfer_checksum": str(target) + ".sha256",
        "review": review,
    }


def collect(commit):
    n.require_host()
    claim, envelope, spec = load_plan(commit)
    return n.collect_components(commit, claim, envelope, spec, packer=pack, auditor=audit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    for action in ("start", "collect", "batch", "worker", "audit"):
        child = subs.add_parser(action)
        child.add_argument("--source-sha", required=True)
        if action == "worker":
            child.add_argument("--specification-sha", required=True)
        if action == "audit":
            for name in ("archive", "sha256", "job"):
                child.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if args.action == "worker":
        worker(args.source_sha, args.specification_sha)
        return 0
    result = (
        audit(args.archive, args.sha256, args.source_sha, args.job)
        if args.action == "audit"
        else {"start": start, "collect": collect, "batch": batch}[args.action](args.source_sha)
    )
    print("RECOVERY_STATUS=" + result["status"])
    normal = result.get("review", result).get("normal", {})
    diagnostic = result.get("diagnostic", normal.get("batch_diagnostic"))
    if diagnostic is not None:
        print("BATCH_PHASE=" + diagnostic["phase"])
        print("BATCH_ERROR_KIND=" + diagnostic["error_kind"])
        site = diagnostic["site"]
        print(
            "BATCH_ERROR_SITE=" + (site["module"] + ":" + str(site["line"]) if site else "unknown")
        )
    if args.action != "audit":
        print("PRESERVE_CLAIM=" + str(claim_path()))
        if (claim_path() / "intent.json").exists():
            print("PRESERVE_RUN=" + n.read_json(claim_path() / "intent.json")["run"])
    for key in ("job_id", "sha256", "download", "transfer_checksum"):
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
            "integrity_replayed_not_live_qualified",
        }
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
