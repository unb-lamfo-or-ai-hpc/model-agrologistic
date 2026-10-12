"""Closed normal components: sealed history, role checks and versioned collection.

No start command, scheduler submission or public worker dispatch is provided.
A separately reviewed immutable driver must bind the release digest before use.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Closed integration; no job or worker admission.")

import copy
import gzip
import hashlib
import io
import json
import os
import sys
import tarfile
import time
from pathlib import Path

from scripts import mvp2_h300_controls as c
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_compute_identity as identity
from scripts import mvp2_s2_first_normal as n
from scripts import mvp2_s2_normal_recovery as r
from scripts import mvp2_s2_operational as o
from scripts import mvp2_s2_slurm_step as s
from scripts import mvp2_s2_slurm_synthetic as q

ENTRY = "scripts/mvp2_s2_compute_integration.py"
HISTORY = (
    r.PREDECESSOR,
    {
        "source_commit": "c74f316e30a1b034368ce15b4877d03f31c5d09b",
        "job_id": "2207181",
        "archive_sha256": "264037fafd7ef52a74e3854b35213228a257d2f3f98f8f55e5ec29fc4eab8b8f",
    },
)
CLAIMS = (o.CLAIM, r.CLAIM)
PREFIX = "S2_COMPUTE_ENTRY_DIAGNOSTIC="
LOG_LIMIT = 16384
RELEASE_LIMIT = 1024**2
ERRORS = (n.DIAGNOSTIC_ERRORS - {"none"}) | {"unexpected_error"}


def seal_history():
    """Login only. Audit original archives, then seal their original source trees."""
    result = []
    for index, expected in enumerate(HISTORY):
        claim = Path(o.BASE) / CLAIMS[index]
        names = (
            r.PREDECESSOR_FILES
            if index == 0
            else (
                "intent.json",
                "private-envelope.json",
                "normal-plan.json",
                "job.json",
                "submission-intent.json",
                "batch.sh",
                "collection.json",
                "predecessor.json",
            )
        )
        records = {str(claim / name): a.sha_file(claim / name, r.LIMIT) for name in names}
        envelope = o.validate_envelope(
            n.read_json(claim / "private-envelope.json"), expected["source_commit"]
        )
        n.checked_baseline(envelope)
        plan = o.validate_normal_plan(
            n.read_json(claim / "normal-plan.json"),
            envelope,
            s.digest(envelope),
            expected["source_commit"],
        )
        spec = plan["specification"]
        s.require(spec["job_id"] == expected["job_id"], "Historical job drift.")
        s.require(
            n.read_json(claim / "job.json")
            == {
                "source_commit": expected["source_commit"],
                "job_id": expected["job_id"],
                "specification_sha256": s.digest(spec),
            },
            "Historical job receipt drift.",
        )
        intent = n.read_json(claim / "intent.json")
        s.require(
            intent.get("source_commit") == expected["source_commit"]
            and intent.get("envelope_sha256") == s.digest(envelope)
            and intent.get("run") == spec["run"]
            and intent.get("nonce") == spec["nonce"],
            "Historical intent drift.",
        )
        saved = n.read_json(claim / "collection.json")
        archive = Path(saved["download"])
        s.require(
            archive.parent.parent == claim
            and archive.parent.name.startswith("collection-")
            and saved["sha256"] == expected["archive_sha256"],
            "History location drift.",
        )
        review = (n.audit if index == 0 else r.audit)(
            archive, expected["archive_sha256"], expected["source_commit"], expected["job_id"]
        )
        normal = review if index == 0 else review["normal"]
        s.require(
            saved["review"] == review and normal["specification_sha256"] == s.digest(spec),
            "History release drift.",
        )
        n.recheck(envelope)  # Deliberately login-only; never called by compute verification.
        manifest = identity.seal_historical_source(spec, a.RealTransport(spec).source_command)
        s.require(manifest["source"] == envelope["source"], "History source drift.")
        s.require(
            records == {path: a.sha_file(path, r.LIMIT) for path in records},
            "History changed during sealing.",
        )
        result.append(
            {
                "identity": copy.deepcopy(expected),
                "specification": spec,
                "manifest": manifest,
                "records": records,
                "archive": str(archive),
            }
        )
    return result


def seal_release(envelope, plan):
    """Read-only login preparation; no claim reservation, write or scheduler effect."""
    commit = envelope["source_commit"]
    envelope = o.validate_envelope(envelope, commit)
    n.checked_baseline(envelope)
    plan = o.validate_normal_plan(plan, envelope, s.digest(envelope), commit)
    spec = plan["specification"]
    n.recheck(envelope)
    manifest = identity.seal_login_source(spec, a.RealTransport(spec).source_command)
    result = {
        "schema_version": "s2-compute-release-v1",
        "envelope": envelope,
        "plan": plan,
        "manifest": manifest,
        "history": seal_history(),
        **n.FUTURE,
    }
    return validate_release(result, commit, s.digest(result))


def validate_release(release, commit, expected_digest):
    if release.get("schema_version") == "s2-node-normal-release-v1":
        from scripts import mvp2_s2_node_predecessor as node

        return node.validate_release(release, commit, expected_digest)
    if release.get("schema_version") == "s2-normal-successor-release-v1":
        from scripts import mvp2_s2_normal_predecessor as successor

        return successor.validate_release(release, commit, expected_digest)
    q._hash(expected_digest)
    s.require(len(c.encoded(release)) <= RELEASE_LIMIT, "Compute release byte bound.")
    q._keys(release, {"schema_version", "envelope", "plan", "manifest", "history", *n.FUTURE})
    s.require(
        release["schema_version"] == "s2-compute-release-v1"
        and s.digest(release) == expected_digest
        and all(release[k] is False for k in n.FUTURE),
        "Compute release binding drift.",
    )
    env = o.validate_envelope(release["envelope"], commit)
    n.checked_baseline(env)
    plan = o.validate_normal_plan(release["plan"], env, s.digest(env), commit)
    spec = plan["specification"]
    manifest = identity.validate_manifest(
        release["manifest"], commit, s.digest(release["manifest"])
    )
    s.require(
        manifest["source"] == env["source"] and ENTRY in manifest["files"],
        "Integration source closure drift.",
    )
    s.require(
        type(release["history"]) is list and len(release["history"]) == 2,
        "Both historical attempts are required.",
    )
    for index, entry in enumerate(release["history"]):
        q._keys(entry, {"identity", "specification", "manifest", "records", "archive"})
        old = a.validate_spec(entry["specification"])
        s.require(
            entry["identity"] == HISTORY[index]
            and old["source_commit"] == HISTORY[index]["source_commit"]
            and old["job_id"] == HISTORY[index]["job_id"]
            and old["case"] == "normal"
            and all(spec[k] != old[k] for k in ("source_commit", "job_id", "run", "checkout")),
            "Historical identity/reuse drift.",
        )
        identity.validate_historical_manifest(
            entry["manifest"], old["source_commit"], s.digest(entry["manifest"])
        )
        claim = Path(o.BASE) / CLAIMS[index]
        names = (
            set(r.PREDECESSOR_FILES)
            if index == 0
            else (set(r.PREDECESSOR_FILES) - {"batch-outcome.json"} | {"predecessor.json"})
        )
        q._keys(entry["records"], {str(claim / name) for name in names})
        for checksum in entry["records"].values():
            q._hash(checksum)
        archive = Path(entry["archive"])
        s.require(
            archive.parent.parent == claim
            and archive.parent.name.startswith("collection-")
            and archive.name
            == (
                "s2-first-normal-evidence.tar.gz"
                if index == 0
                else "s2-normal-recovery-evidence.tar.gz"
            ),
            "Historical archive path drift.",
        )
    return copy.deepcopy(release)


def release_claim(item):
    # Called only after full release validation; never a caller-selectable path.
    if item["schema_version"] == "s2-node-normal-release-v1":
        return ".mvp2-s2-node-normal-v1"
    return (
        ".mvp2-s2-normal-successor-v1"
        if item["schema_version"] == "s2-normal-successor-release-v1"
        else ".mvp2-s2-compute-integration-v1"
    )


def verify_release(release, commit, expected_digest, *, role, deadline, clock=time.monotonic):
    """Compute path: file reads only. Never rerun a predecessor or its Git checks."""
    item = validate_release(release, commit, expected_digest)
    spec = item["plan"]["specification"]
    s.require(clock() < deadline, "Compute identity deadline.")
    if item["schema_version"] == "s2-node-normal-release-v1":
        from scripts import mvp2_s2_node_predecessor as node

        node.verify_diagnostic(item["diagnostic"])
    for entry in item["history"]:
        for path, checksum in entry["records"].items():
            s.require(a.sha_file(path, r.LIMIT) == checksum, "Preserved record byte drift.")
        s.require(
            a.sha_file(entry["archive"], r.LIMIT) == entry["identity"]["archive_sha256"],
            "Preserved archive byte drift.",
        )
        old = entry["specification"]
        identity.verify_historical_source(
            old["checkout"], entry["manifest"], old["source_commit"], s.digest(entry["manifest"])
        )
        s.require(clock() < deadline, "Compute identity deadline.")
    source = identity.verify_compute_source(
        spec["checkout"], item["manifest"], commit, s.digest(item["manifest"])
    )
    runtime = identity.verify_compute_runtime(spec, role)
    s.require(clock() < deadline, "Compute identity deadline.")
    return item, source, runtime


def worker_argv(spec, release_digest):
    q._hash(release_digest)
    argv = n.normal_worker_argv(spec)
    return tuple(
        spec["checkout"] + "/" + ENTRY if x == spec["checkout"] + "/" + n.ENTRY else x for x in argv
    ) + ("--release-sha", release_digest)


def verify_local_entry(spec):
    s.require(
        Path(__file__).resolve() == Path(spec["checkout"]) / ENTRY
        and Path(sys.executable).resolve() == Path(spec["python"]),
        "Compute entry/runtime location drift.",
    )


class ComputeTransport(n.NormalTransport):
    def __init__(self, item, *, release_digest, **kwargs):
        super().__init__(item, **kwargs)
        self.release_digest = release_digest

    def source_command(self, *args, **kwargs):
        raise PermissionError("No Git command in compute transport.")

    def worker_command(self):
        return worker_argv(self.item, self.release_digest)


class ComputeAdapter(n.NormalAdapter):
    def verify_runtime(self, tool_sha256, python_sha256):
        s.require(
            tool_sha256 == self.item["tools_sha256"]
            and python_sha256 == self.item["python_sha256"],
            "Expected runtime drift.",
        )
        return identity.verify_compute_runtime(self.item, "batch")

    def attempt_schema(self):
        return "s2-batch-attempt-v2"

    def worker_command(self):
        return self.transport.worker_command()


def entry_diagnostic(role, phase, error):
    s.require(
        role in {"batch", "worker"}
        and phase in {"host", "identity", "release", "claim", "dispatch", "complete"},
        "Entry diagnostic scope.",
    )
    try:
        kind = n.batch_diagnostic("preflight", error)["error_kind"]
    except ValueError:
        kind = "unexpected_error"
    return {
        "schema_version": "s2-compute-entry-v1",
        "role": role,
        "phase": phase,
        "error_kind": kind,
        **n.FUTURE,
    }


def emit_error(role, phase, error):
    record = entry_diagnostic(role, phase, error)
    print(PREFIX + json.dumps(record, sort_keys=True), file=sys.stderr, flush=True)
    return record


def batch_components(
    claim, release, commit, release_digest, allocation_started, *, transport_factory=None
):
    """Internal composition only; public execution stays denied pending a fresh driver."""
    phase = "host"
    try:
        n.require_host()
        phase = "identity"
        item, _source, _runtime = verify_release(
            release, commit, release_digest, role="batch", deadline=allocation_started + 120
        )
        spec = item["plan"]["specification"]
        phase = "release"
        verify_local_entry(spec)
        claim = Path(claim)
        q._safe_path(claim)
        s.require(
            claim.parent == Path(o.BASE)
            and claim.name == release_claim(item)
            and n.read_json(claim / "release.json", RELEASE_LIMIT) == item
            and n.read_json(claim / "job.json")
            == {
                "source_commit": commit,
                "job_id": spec["job_id"],
                "specification_sha256": s.digest(spec),
                "release_sha256": release_digest,
            }
            and os.environ.get("SLURM_JOB_ID") == spec["job_id"],
            "Immutable release drift.",
        )
        phase = "claim"
        (claim / "batch-claim").mkdir(mode=0o700, exist_ok=False)
        phase = "dispatch"

        def load(_commit):
            s.require(_commit == commit, "Commit drift.")
            checked, _, _ = verify_release(
                release, commit, release_digest, role="batch", deadline=allocation_started + 120
            )
            s.require(n.read_json(claim / "release.json", RELEASE_LIMIT) == checked, "Claim drift.")
            return claim, checked["envelope"], checked["plan"]["specification"]

        return n.batch_components(
            commit,
            claim,
            item["envelope"],
            {"run": spec["run"]},
            allocation_started,
            plan_loader=load,
            transport_factory=transport_factory
            or (lambda spec, **kw: ComputeTransport(spec, release_digest=release_digest, **kw)),
            adapter_factory=ComputeAdapter,
            runtime_verifier=lambda _env: identity.verify_compute_runtime(spec, "batch"),
            source_verifier=lambda actual, _command: identity.verify_compute_source(
                actual["checkout"], item["manifest"], commit, s.digest(item["manifest"])
            ),
        )
    except (Exception, KeyboardInterrupt) as error:
        emit_error("batch", phase, error)
        raise SystemExit(2) from None


def worker_components(release, commit, release_digest, specification_digest):
    phase = "host"
    try:
        started = time.monotonic()
        n.require_host()
        phase = "identity"
        item, source, runtime = verify_release(
            release, commit, release_digest, role="worker", deadline=started + 120
        )
        spec = item["plan"]["specification"]
        phase = "release"
        verify_local_entry(spec)
        s.require(
            s.digest(spec) == specification_digest
            and os.environ.get("SLURM_JOB_ID") == spec["job_id"],
            "Worker release drift.",
        )
        phase = "dispatch"
        # The existing dispatcher validates the durable worker plan and kernel peer.
        receipt = {
            "schema_version": "s2-compute-worker-identity-v1",
            "source": source,
            "runtime": runtime,
            "release_sha256": release_digest,
            "specification_sha256": specification_digest,
            **n.FUTURE,
        }
        root = Path(spec["run"])
        q._safe_path(root)
        s.require(
            n.read_json(root / "claim.json")
            == {"specification_sha256": specification_digest, **a.FLAGS},
            "Worker run claim drift.",
        )
        c.write_once(root / "worker-identity.json", receipt)
        return o.worker_dispatch_components(
            spec, specification_digest, spec["run"] + "/worker-plan.json"
        )
    except (Exception, KeyboardInterrupt) as error:
        emit_error("worker", phase, error)
        raise SystemExit(2) from None


def collect_entry_log(path):
    """Only bounded message-free structured diagnostics leave the private log."""
    try:
        raw = a._file(path, LOG_LIMIT)
    except FileNotFoundError:
        return {"status": "missing", "sha256": None, "bytes": None, "diagnostics": []}
    # Oversize/unsafe files reject collection, never truncate and call it complete.
    records = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        if line.startswith(PREFIX):
            record = c.decode_json(line[len(PREFIX) :].encode())
            q._keys(record, {"schema_version", "role", "phase", "error_kind", *n.FUTURE})
            s.require(
                record["error_kind"] in ERRORS
                and record["schema_version"] == "s2-compute-entry-v1"
                and record["role"] in {"batch", "worker"}
                and record["phase"] in {"host", "identity", "release", "claim", "dispatch"}
                and all(record[k] is False for k in n.FUTURE),
                "Entry diagnostic drift.",
            )
            records.append(record)
    s.require(len(records) <= 2, "Diagnostic count bound.")
    return {
        "status": "captured" if records else "no_structured_diagnostic",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "diagnostics": records,
    }


def review_compute_collection(records, spec, contract, release_digest, expected_source):
    """New carrier semantics; legacy runtime receipts are never promoted."""
    spec = a.validate_spec(spec)
    return review_portable_collection(
        records,
        s.digest(spec),
        identity.expected_compute_runtime(spec, "batch"),
        identity.expected_compute_runtime(spec, "worker"),
        contract,
        release_digest,
        expected_source,
        spec["source_commit"],
        spec["job_id"],
    )


def review_portable_collection(
    records,
    specification_digest,
    batch_runtime,
    worker_runtime,
    contract,
    release_digest,
    expected_source,
    commit,
    job,
):
    """Replay against public digests; never reconstruct or export private paths."""
    q._hash(release_digest)
    q._hash(specification_digest)
    q._hash(commit, 40)
    identity.review_compute_runtime(batch_runtime)
    identity.review_compute_runtime(worker_runtime, "worker")
    q._keys(
        records,
        {
            "release_sha256",
            "batch",
            "operation",
            "early_logs",
            "accounting",
            "worker_identity",
            "wrapper",
        },
    )
    s.require(records["release_sha256"] == release_digest, "Collection release drift.")
    rows = records["accounting"]
    text = "".join(
        f"{key}|{row['state']}|{row['exit_code']}|{row['elapsed_seconds']}\n"
        for key, row in rows.items()
    )
    s.require(
        a.accounting(text, job) == rows
        and job in rows
        and job + ".batch" in rows
        and all(row["state"] in a.TERMINAL for row in rows.values()),
        "Terminal accounting required.",
    )
    wrapper = records["wrapper"]
    if wrapper is not None:
        q._keys(wrapper, {"schema_version", "status", "source_commit", "diagnostic", *n.FUTURE})
        s.require(
            wrapper["schema_version"] == "s2-first-normal-batch-v2"
            and wrapper["source_commit"] == commit
            and wrapper["status"]
            in {"blocked_before_launch", "attempt_preserved", "incomplete_attempt_preserved"}
            and all(wrapper[k] is False for k in n.FUTURE),
            "Wrapper drift.",
        )
        n.review_batch_diagnostic(wrapper["diagnostic"])
    q._keys(records["early_logs"], {"stdout", "stderr"})
    for log in records["early_logs"].values():
        q._keys(log, {"status", "sha256", "bytes", "diagnostics"})
        s.require(
            log["status"] in {"missing", "captured", "no_structured_diagnostic"},
            "Log status drift.",
        )
        if log["status"] == "missing":
            s.require(
                log == {"status": "missing", "sha256": None, "bytes": None, "diagnostics": []},
                "Missing log drift.",
            )
        else:
            q._hash(log["sha256"])
            s.require(
                type(log["bytes"]) is int and 0 <= log["bytes"] <= LOG_LIMIT, "Log byte bound."
            )
            s.require(
                type(log["diagnostics"]) is list
                and len(log["diagnostics"]) <= 2
                and bool(log["diagnostics"]) == (log["status"] == "captured"),
                "Log diagnostic status drift.",
            )
            for record in log["diagnostics"]:
                q._keys(record, {"schema_version", "role", "phase", "error_kind", *n.FUTURE})
                s.require(
                    record["schema_version"] == "s2-compute-entry-v1"
                    and record["role"] in {"batch", "worker"}
                    and record["phase"] in {"host", "identity", "release", "claim", "dispatch"}
                    and record["error_kind"] in ERRORS
                    and all(record[k] is False for k in n.FUTURE),
                    "Diagnostic drift.",
                )
    batch, operation = records["batch"], records["operation"]
    s.require((batch is None) == (operation is None), "Incomplete operational carrier.")
    replay = None
    if batch is not None:
        replay = a.review_portable_bundle(
            batch, specification_digest, batch_runtime, contract, job, compute=True
        )
        s.require(
            batch["review.json"] == replay and batch["accounting.json"] == rows,
            "Compute replay drift.",
        )
        source = batch["adapter.json"]["attempt"]["source"]
        s.require(source is None or source == expected_source, "Compute source drift.")
        o.review_operation_digest(operation, specification_digest)
    else:
        s.require(
            contract is None and (wrapper is None or wrapper["status"] != "attempt_preserved"),
            "Missing expected attempt.",
        )
    worker = records["worker_identity"]
    if worker is not None:
        s.require(
            worker
            == {
                "schema_version": "s2-compute-worker-identity-v1",
                "source": expected_source,
                "runtime": worker_runtime,
                "release_sha256": release_digest,
                "specification_sha256": specification_digest,
                **n.FUTURE,
            },
            "Worker identity drift.",
        )
    s.require(contract is None or worker is not None, "Bound worker identity missing.")
    return {
        "schema_version": "s2-compute-collection-review-v1",
        "status": "integrity_replayed_not_live_qualified" if replay else "no_attempt_receipt",
        "release_sha256": release_digest,
        "batch": replay,
        "early_logs": copy.deepcopy(records["early_logs"]),
        **n.FUTURE,
    }


def collect_components(claim, destination, release, commit, release_digest, terminal_text):
    """Exclusive output only; no scheduler query, source execution or resubmission."""
    item = validate_release(release, commit, release_digest)
    spec = item["plan"]["specification"]
    claim = Path(claim)
    q._safe_path(claim)
    s.require(
        claim.parent == Path(o.BASE)
        and claim.name == release_claim(item)
        and n.read_json(claim / "release.json", RELEASE_LIMIT) == item,
        "Collection claim drift.",
    )
    root = Path(spec["run"])
    q._safe_path(root)

    def optional(path):
        try:
            return n.read_json(path)
        except FileNotFoundError:
            return None

    contract = optional(root / "contract.json")
    records = {
        "release_sha256": release_digest,
        "batch": None,
        "operation": None,
        "accounting": a.accounting(terminal_text, spec["job_id"]),
        "wrapper": optional(claim / "batch-outcome.json"),
        "worker_identity": optional(root / "worker-identity.json"),
        "early_logs": {
            kind: collect_entry_log(claim / f"slurm-{spec['job_id']}.{ext}")
            for kind, ext in (("stdout", "out"), ("stderr", "err"))
        },
    }
    # Validate terminal identity/logs before creating the exclusive output directory.
    rows = records["accounting"]
    s.require(
        spec["job_id"] in rows
        and spec["job_id"] + ".batch" in rows
        and all(row["state"] in a.TERMINAL for row in rows.values()),
        "Not terminal.",
    )
    destination = Path(destination)
    q._safe_path(destination)
    destination.mkdir(mode=0o700, exist_ok=False)
    if (root / "attempt.json").exists():
        result = o.collect_normal_components(
            root, destination / "attempt", spec, contract, terminal_text, compute=True
        )
        records["batch"] = a.read_bundle(
            destination / "attempt/batch-evidence.tar.gz", result["sha256"]
        )
        records["operation"] = n.read_json(destination / "attempt/operation.json")["operation"]
    else:
        s.require(
            not (root / "operation.json").exists() and contract is None,
            "Partial attempt needs forensic preservation; no complete carrier fabricated.",
        )
    review = review_compute_collection(
        records, spec, contract, release_digest, item["manifest"]["source"]
    )
    payload = {"collection.json": c.encoded(records), "review.json": c.encoded(review)}
    s.require(sum(map(len, payload.values())) < n.LIMIT - 16384, "Compute carrier bound.")
    target = destination / "s2-compute-evidence.tar.gz"
    with target.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for name, data in sorted(payload.items()):
                info = tarfile.TarInfo(name)
                info.size, info.mode = len(data), 0o600
                archive.addfile(info, io.BytesIO(data))
    checksum = a.sha_file(target, n.LIMIT)
    s.require(
        audit_collection(
            target, checksum, spec, contract, release_digest, item["manifest"]["source"]
        )
        == review,
        "Published replay drift.",
    )
    with target.with_name(target.name + ".sha256").open("x", encoding="ascii") as stream:
        stream.write(checksum + "  " + target.name + "\n")
    return {"sha256": checksum, "download": str(target), "review": review, **n.FUTURE}


def audit_collection(path, checksum, spec, contract, release_digest, expected_source):
    q._hash(checksum)
    raw = a._file(path, n.LIMIT)
    s.require(hashlib.sha256(raw).hexdigest() == checksum, "Compute archive checksum drift.")
    records = n.read_tar(raw, n.LIMIT, {"collection.json", "review.json"})
    q._keys(records, {"collection.json", "review.json"})
    review = review_compute_collection(
        c.decode_json(records["collection.json"]), spec, contract, release_digest, expected_source
    )
    s.require(c.decode_json(records["review.json"]) == review, "Compute review drift.")
    return review
