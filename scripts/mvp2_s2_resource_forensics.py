"""Terminal/forensic collector for the closed normal resource launcher.

Reads only fixed receipts and bounded journals; exports verified redacted
semantics or hash/size metadata. Missing/truncated final carriers never become
complete attempts. No scheduler commands, signals, repairs or retries exist.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Resource collection CLI remains closed pending a pinned driver.")

import copy
import gzip
import hashlib
import io
import re
import tarfile
from pathlib import Path

from scripts import mvp2_h300_controls as c
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_compute_identity as identity
from scripts import mvp2_s2_compute_integration as integration
from scripts import mvp2_s2_resource_launcher as launcher
from scripts import mvp2_s2_resource_normal as normal
from scripts import mvp2_s2_slurm_step as s
from scripts import mvp2_s2_slurm_synthetic as q

LIMIT = 32 * 1024**2
FILE_LIMIT = normal.LIMIT
FIXED = {
    "claim.json",
    "worker-plan.json",
    "launch-intent.json",
    "binding.json",
    "contract.json",
    "resource-contract.json",
    "attempt.json",
    "operation.json",
    "operation-diagnostic.json",
    "resource-evidence.json",
    "worker-identity.json",
    "term-intent.json",
    "kill-intent.json",
    *("worker/" + name for name in q.WORKER_FILES),
}
MEMBERS = {"carrier.json", "review.json"}
MAX_FILES = len(FIXED) + q.PROFILE["maximum_events"] + 2 * a.MAX_SAMPLES


def valid_name(name):
    if name in FIXED:
        return True
    match = re.fullmatch(
        r"(event|sample|resource-sample|resource-barrier)-([0-9]{4}|[01])\.json", name
    )
    if not match:
        return False
    kind, index = match[1], int(match[2])
    bound = {
        "event": q.PROFILE["maximum_events"],
        "sample": a.MAX_SAMPLES,
        "resource-sample": a.MAX_SAMPLES,
        "resource-barrier": 2,
    }[kind]
    width = 1 if kind == "resource-barrier" else 4
    return len(match[2]) == width and index < bound


def read_records(run):
    """Bounded allowlist, no recursive traversal or export of arbitrary files."""
    run = Path(run)
    q._safe_path(run)
    if not run.exists():
        return {}
    s.require(run.is_dir(), "Run is not a directory.")
    names = set(FIXED)
    for index, path in enumerate(run.iterdir()):
        s.require(index < MAX_FILES + 32, "Run directory bound.")
        if valid_name(path.name):
            names.add(path.name)
    result, total = {}, 0
    for name in sorted(names):
        path = run / name
        q._safe_path(path)
        try:
            raw = a._file(path, FILE_LIMIT)
        except FileNotFoundError:
            continue
        total += len(raw)
        s.require(total <= LIMIT // 2 and len(result) < MAX_FILES, "Forensic inventory bound.")
        result[name] = raw
    return result


def metadata(raw):
    try:
        semantic = s.digest(c.decode_json(raw))
        status = "json"
    except (ValueError, UnicodeError, RecursionError):
        semantic = None
        status = "invalid_json"
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "semantic_sha256": semantic,
        "bytes": len(raw),
        "status": status,
    }


CLAIM_FILES = {
    "proposal.json",
    "release.json",
    "submission-intent.json",
    "job.json",
    "stop.json",
    "submission-unknown.json",
    "batch.sh",
    "batch-outcome.json",
}


def claim_records(job):
    """Capture only this release's claim and message-free bounded entry logs."""
    root, result = launcher.claim_path(), {}
    for name in sorted(CLAIM_FILES):
        try:
            result[name] = metadata(a._file(root / name, launcher.LIMIT))
        except FileNotFoundError:
            pass
    logs = {
        suffix: integration.collect_entry_log(root / ("slurm-" + job + "." + suffix))
        for suffix in ("out", "err")
    }
    return {"files": result, "logs": logs}


def anchor(release):
    release = launcher.validate_release(
        release, release["envelope"]["source_commit"], s.digest(release)
    )
    spec = release["plan"]["specification"]
    s.require(spec["job_id"] != "1", "Unacknowledged collection.")
    return {
        "schema_version": "s2-resource-launcher-anchor-v1",
        "source_commit": spec["source_commit"],
        "job_id": spec["job_id"],
        "release_sha256": s.digest(release),
        "binding": normal.portable_binding(spec),
        "source": copy.deepcopy(release["manifest"]["source"]),
        "worker_runtime": identity.expected_compute_runtime(spec, "worker"),
        "base_commit": launcher.BASE_COMMIT,
        "history": copy.deepcopy(list(launcher.HISTORY)),
        **normal.p.FLAGS,
    }


def terminal_rows(text, job):
    """A successful root alone is insufficient; retain exact attributed cancellation."""
    rows = a.accounting(text, job)
    ready = {job, job + ".batch"} <= rows.keys() and all(
        v["state"] in a.TERMINAL for v in rows.values()
    )
    return rows, ready


def same(records, name, expected):
    s.require(
        name in records and c.decode_json(records[name]) == expected, "Durable receipt mismatch."
    )


def review_samples(samples, evidence):
    s.require(
        type(samples) is list and len(samples) == evidence["attempt"]["sample_count"],
        "Durable lifecycle sample count.",
    )
    for sample, event in zip(samples, evidence["events"][1:], strict=True):
        q._keys(sample, {"seconds", "snapshot", "fault", "accounting_sha256", "writes_sha256"})
        inputs = event["payload"]["inputs"]
        s.require(
            sample["seconds"] == event["seconds"]
            and sample["fault"] is inputs["fault"]
            and sample["writes_sha256"] == inputs["writes_sha256"],
            "Lifecycle sample/event drift.",
        )
        q._hash(sample["accounting_sha256"])
        if sample["writes_sha256"] is not None:
            q._hash(sample["writes_sha256"])
        snapshot = sample["snapshot"]
        if snapshot is not None:
            q._keys(
                snapshot,
                {
                    "schema_version",
                    "synthetic_observation",
                    "status",
                    "errors",
                    "scopes",
                    "counters",
                    *s.FLAGS,
                },
            )
            s.require(
                snapshot["schema_version"] == "s2-cgroup-v1-observation-v1"
                and snapshot["synthetic_observation"] is False
                and snapshot["errors"] == []
                and snapshot["status"] == "observed_not_qualified"
                and all(snapshot[k] is False for k in s.FLAGS),
                "Portable snapshot schema.",
            )
            q._keys(snapshot["scopes"], s.CONTROLLERS)
            for scope in snapshot["scopes"].values():
                q._keys(scope, {"path_sha256", "inode"})
                q._hash(scope["path_sha256"])
                s.require(
                    type(scope["inode"]) is list
                    and len(scope["inode"]) == 2
                    and all(type(v) is int and v >= 0 for v in scope["inode"]),
                    "Scope inode.",
                )
            q._keys(snapshot["counters"], normal.p.COUNTERS)
            s.require(
                all(type(v) is int and v >= 0 for v in snapshot["counters"].values()),
                "Counter grammar.",
            )
        if not inputs["fault"]:
            s.require(
                snapshot is not None
                and s.digest(snapshot["scopes"]) == inputs["scope_hash"]
                and snapshot["counters"]["freezer_unique_process_count"] == inputs["members"],
                "Lifecycle snapshot binding.",
            )


def complete_evidence(records, spec, release):
    value = c.decode_json(records["resource-evidence.json"])
    review = normal.review(value, spec)
    s.require(
        value["attempt"]["source"] == release["manifest"]["source"], "Attempt release source drift."
    )
    same(records, "claim.json", {"specification_sha256": s.digest(spec), **a.FLAGS})
    same(records, "attempt.json", value["attempt"])
    for index, barrier in enumerate(value["barriers"]):
        same(records, f"resource-barrier-{index}.json", barrier)
    for item in value["resources"]:
        same(records, f"resource-sample-{item['index']:04d}.json", item)
    for item in value["events"]:
        same(records, f"event-{item['index']:04d}.json", item)
    for prefix, expected in (
        ("resource-barrier", {f"resource-barrier-{i}.json" for i in range(len(value["barriers"]))}),
        ("resource-sample", {f"resource-sample-{v['index']:04d}.json" for v in value["resources"]}),
        ("event", {f"event-{v['index']:04d}.json" for v in value["events"]}),
        ("sample", {f"sample-{i:04d}.json" for i in range(value["attempt"]["sample_count"])}),
    ):
        s.require(
            {name for name in records if name.startswith(prefix + "-")} == expected,
            "Final carrier omits or invents durable journal records.",
        )
    if value["events"]:
        same(records, "resource-contract.json", value["contract"])
    samples = [
        c.decode_json(records[f"sample-{i:04d}.json"])
        for i in range(value["attempt"]["sample_count"])
    ]
    review_samples(samples, value)
    return value, review, samples


def worker_records(records, release, contract):
    spec = release["plan"]["specification"]
    products = {
        name: c.decode_json(records["worker/" + name])
        for name in q.WORKER_FILES
        if "worker/" + name in records
    }
    receipt = None
    if "worker-identity.json" in records:
        receipt = c.decode_json(records["worker-identity.json"])
        expected = {
            "schema_version": "s2-resource-launcher-worker-v1",
            "source": release["manifest"]["source"],
            "runtime": identity.expected_compute_runtime(spec, "worker"),
            "release_sha256": s.digest(release),
            "specification_sha256": s.digest(spec),
            **normal.p.FLAGS,
        }
        s.require(receipt == expected, "Worker entry/source/runtime drift.")
    if contract is None:
        s.require(not products, "Unbound worker products.")
    else:
        q.verify_worker_products(contract["legacy_contract"], products)
    return receipt, products


def build_carrier(records, release, text, claim=None):
    spec = release["plan"]["specification"]
    rows, ready = terminal_rows(text, spec["job_id"])
    s.require(ready, "Terminal accounting required.")
    evidence, replay, worker, products, samples = None, None, None, {}, []
    final = records.get("resource-evidence.json")
    disposition = "missing_final"
    if final is not None:
        disposition = (
            "invalid_final_json" if metadata(final)["status"] != "json" else "rejected_final"
        )
        if disposition == "rejected_final":
            try:
                evidence, replay, samples = complete_evidence(records, spec, release)
                worker, products = worker_records(records, release, evidence["contract"])
                if evidence["contract"] is not None:
                    step = (
                        spec["job_id"]
                        + "."
                        + evidence["contract"]["legacy_contract"]["binding"]["worker_step_id"]
                    )
                    s.require(step in rows, "Missing bound numeric-step accounting.")
                disposition = "complete_replayed"
            except (ValueError, KeyError, TypeError, IndexError, UnicodeError, RecursionError):
                evidence, replay, worker, products, samples = None, None, None, {}, []
    return {
        "schema_version": "s2-resource-launcher-carrier-v1",
        "anchor": anchor(release),
        "accounting_text": text,
        "accounting": rows,
        "inventory": {name: metadata(raw) for name, raw in sorted(records.items())},
        "claim_capture": claim if claim is not None else claim_records(spec["job_id"]),
        "disposition": disposition,
        "evidence": evidence,
        "semantic_replay": replay,
        "samples": samples,
        "worker_identity": worker,
        "worker_products": products,
        **normal.p.FLAGS,
    }


def review_public(value, *, commit, job, release_digest):
    """External source/job/release required; copied hashes are not kernel attestation."""
    q._hash(commit, 40)
    q._hash(release_digest)
    q._keys(
        value,
        {
            "schema_version",
            "anchor",
            "accounting_text",
            "accounting",
            "inventory",
            "claim_capture",
            "disposition",
            "evidence",
            "semantic_replay",
            "samples",
            "worker_identity",
            "worker_products",
            *normal.p.FLAGS,
        },
    )
    s.require(
        value["schema_version"] == "s2-resource-launcher-carrier-v1"
        and all(value[k] is False for k in normal.p.FLAGS),
        "Carrier authority drift.",
    )
    meta = value["anchor"]
    q._keys(
        meta,
        {
            "schema_version",
            "source_commit",
            "job_id",
            "release_sha256",
            "binding",
            "source",
            "worker_runtime",
            "base_commit",
            "history",
            *normal.p.FLAGS,
        },
    )
    s.require(
        meta["schema_version"] == "s2-resource-launcher-anchor-v1"
        and meta["source_commit"] == commit
        and meta["job_id"] == job != "1"
        and meta["release_sha256"] == release_digest
        and meta["base_commit"] == launcher.BASE_COMMIT
        and meta["history"] == list(launcher.HISTORY)
        and meta["binding"]["source_commit"] == commit
        and meta["binding"]["job_id"] == job
        and all(meta[k] is False for k in normal.p.FLAGS),
        "External anchor drift.",
    )
    q._keys(meta["source"], {"source_sha256", "worker_sha256", "tracked_count"})
    for key in ("source_sha256", "worker_sha256"):
        q._hash(meta["source"][key])
    s.require(
        type(meta["source"]["tracked_count"]) is int
        and 1 <= meta["source"]["tracked_count"] <= 1024,
        "Source count.",
    )
    identity.review_compute_runtime(meta["worker_runtime"], "worker")
    normal.validate_portable_binding(meta["binding"])
    capture = value["claim_capture"]
    q._keys(capture, {"files", "logs"})
    s.require(
        type(capture["files"]) is dict and set(capture["files"]) <= CLAIM_FILES, "Claim inventory."
    )
    q._keys(capture["logs"], {"out", "err"})
    for log in capture["logs"].values():
        q._keys(log, {"status", "sha256", "bytes", "diagnostics"})
        s.require(
            log["status"] in {"missing", "captured", "no_structured_diagnostic"}
            and type(log["diagnostics"]) is list
            and len(log["diagnostics"]) <= 2,
            "Log capture schema.",
        )
        if log["status"] == "missing":
            s.require(
                log["sha256"] is None and log["bytes"] is None and not log["diagnostics"],
                "Missing log drift.",
            )
        else:
            q._hash(log["sha256"])
            s.require(
                type(log["bytes"]) is int
                and 0 <= log["bytes"] <= integration.LOG_LIMIT
                and bool(log["diagnostics"]) == (log["status"] == "captured"),
                "Log capture bound.",
            )
        for diagnostic in log["diagnostics"]:
            q._keys(
                diagnostic, {"schema_version", "role", "phase", "error_kind", *integration.n.FUTURE}
            )
            s.require(
                diagnostic["schema_version"] == "s2-compute-entry-v1"
                and diagnostic["role"] in {"batch", "worker"}
                and diagnostic["phase"] in {"host", "identity", "release", "claim", "dispatch"}
                and diagnostic["error_kind"] in integration.ERRORS
                and all(diagnostic[k] is False for k in integration.n.FUTURE),
                "Diagnostic drift.",
            )
    rows, ready = terminal_rows(value["accounting_text"], job)
    s.require(ready and rows == value["accounting"], "Terminal accounting replay drift.")
    inventory = value["inventory"]
    s.require(type(inventory) is dict and len(inventory) <= MAX_FILES, "Inventory bound.")
    total = 0
    for name, record in {
        **inventory,
        **{"claim/" + k: v for k, v in capture["files"].items()},
    }.items():
        s.require(
            valid_name(name) or name.startswith("claim/") and name[6:] in CLAIM_FILES,
            "Unexpected forensic member.",
        )
        q._keys(record, {"sha256", "semantic_sha256", "bytes", "status"})
        q._hash(record["sha256"])
        if record["status"] == "json":
            q._hash(record["semantic_sha256"])
        else:
            s.require(record["semantic_sha256"] is None, "Invalid JSON has no semantic hash.")
        s.require(
            type(record["bytes"]) is int
            and 0 <= record["bytes"] <= FILE_LIMIT
            and record["status"] in {"json", "invalid_json"},
            "Inventory metadata drift.",
        )
        total += record["bytes"]
    s.require(total <= LIMIT // 2, "Total inventory bound.")
    disposition, state = value["disposition"], None
    s.require(
        disposition
        in {"missing_final", "invalid_final_json", "rejected_final", "complete_replayed"},
        "Final disposition.",
    )
    if disposition == "missing_final":
        s.require("resource-evidence.json" not in inventory, "Final absence drift.")
    else:
        s.require("resource-evidence.json" in inventory, "Missing final metadata.")
        s.require(
            inventory["resource-evidence.json"]["status"]
            == ("invalid_json" if disposition == "invalid_final_json" else "json"),
            "JSON status drift.",
        )
    if disposition == "complete_replayed":
        evidence = value["evidence"]
        replay = normal.review_portable(evidence, meta["binding"])
        s.require(
            replay == value["semantic_replay"] and evidence["attempt"]["source"] == meta["source"],
            "Semantic/source replay drift.",
        )
        exported = {
            "resource-evidence.json": evidence,
            "attempt.json": evidence["attempt"],
            "claim.json": {
                "specification_sha256": meta["binding"]["specification_sha256"],
                **a.FLAGS,
            },
        }
        exported.update(
            {f"resource-barrier-{i}.json": v for i, v in enumerate(evidence["barriers"])}
        )
        exported.update(
            {f"resource-sample-{v['index']:04d}.json": v for v in evidence["resources"]}
        )
        exported.update({f"event-{v['index']:04d}.json": v for v in evidence["events"]})
        review_samples(value["samples"], evidence)
        exported.update({f"sample-{i:04d}.json": v for i, v in enumerate(value["samples"])})
        exported.update({"worker/" + k: v for k, v in value["worker_products"].items()})
        if value["worker_identity"] is not None:
            exported["worker-identity.json"] = value["worker_identity"]
        if evidence["events"]:
            exported["resource-contract.json"] = evidence["contract"]
        s.require(
            all(
                name in inventory and inventory[name]["semantic_sha256"] == s.digest(v)
                for name, v in exported.items()
            ),
            "Exported semantics/inventory drift.",
        )
        # The original JSON's byte hash may differ from canonical JSON formatting;
        # preserve its raw hash while separately binding the exported semantics.
        state = replay["controller_state"]
        worker = value["worker_identity"]
        if worker is not None:
            s.require(
                worker
                == {
                    "schema_version": "s2-resource-launcher-worker-v1",
                    "source": meta["source"],
                    "runtime": meta["worker_runtime"],
                    "release_sha256": release_digest,
                    "specification_sha256": meta["binding"]["specification_sha256"],
                    **normal.p.FLAGS,
                },
                "Portable worker identity drift.",
            )
        contract = evidence["contract"]
        if contract is None:
            s.require(value["worker_products"] == {}, "Unbound products.")
        else:
            q.verify_worker_products(contract["legacy_contract"], value["worker_products"])
            step = job + "." + contract["legacy_contract"]["binding"]["worker_step_id"]
            s.require(step in rows, "Bound numeric step missing from terminal accounting.")
        status = "terminal_integrity_replayed_not_live_qualified"
    else:
        s.require(
            all(value[k] is None for k in ("evidence", "semantic_replay", "worker_identity"))
            and value["worker_products"] == {}
            and value["samples"] == [],
            "Forensic carrier cannot synthesize semantics.",
        )
        status = (
            "terminal_evidence_rejected"
            if disposition == "rejected_final"
            else "terminal_forensic_preserved"
        )
    return {
        "schema_version": "s2-resource-launcher-review-v1",
        "status": status,
        "disposition": disposition,
        "controller_state": state,
        "source_commit": commit,
        "job_id": job,
        "release_sha256": release_digest,
        "carrier_sha256": s.digest(value),
        "worker_cpu_usage_ns": None,
        **normal.p.FLAGS,
    }


def collect_components(run, destination, release, terminal_text, *, release_loader=None):
    """Collect after terminal accounting into a fresh derived directory only."""
    meta = anchor(release)
    _rows, ready = terminal_rows(terminal_text, meta["job_id"])
    if not ready:
        return {"status": "nonterminal_or_accounting_pending", **normal.p.FLAGS}
    spec = release["plan"]["specification"]
    s.require(
        (release_loader or launcher.load_release)() == release, "Collection claim/release drift."
    )
    run, destination = Path(run), Path(destination)
    s.require(run == Path(spec["run"]), "Collection run drift.")
    q._safe_path(destination)
    for preserved in (run, Path(spec["checkout"]), launcher.claim_path()):
        s.require(
            destination != preserved and destination not in preserved.parents,
            "Output covers preserved data.",
        )
        if preserved != launcher.claim_path():
            s.require(preserved not in destination.parents, "Output inside run/source.")
    first = read_records(run)
    captured_claim = claim_records(spec["job_id"])
    value = build_carrier(first, release, terminal_text, captured_claim)
    # Two complete reads detect changed bytes, disappearance and new journal tails.
    second = read_records(run)
    s.require(
        first == second and captured_claim == claim_records(spec["job_id"]),
        "Evidence changed during collection.",
    )
    result = review_public(
        value,
        commit=meta["source_commit"],
        job=meta["job_id"],
        release_digest=meta["release_sha256"],
    )
    records = {"carrier.json": c.encoded(value), "review.json": c.encoded(result)}
    s.require(sum(map(len, records.values())) <= LIMIT - 16384, "Archive bound.")
    destination.mkdir(mode=0o700, exist_ok=False)
    target = destination / "s2-resource-normal-evidence.tar.gz"
    with target.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for name, data in sorted(records.items()):
                item = tarfile.TarInfo(name)
                item.size, item.mode = len(data), 0o600
                archive.addfile(item, io.BytesIO(data))
    checksum = hashlib.sha256(a._file(target, LIMIT)).hexdigest()
    s.require(
        audit(
            target,
            checksum,
            commit=meta["source_commit"],
            job=meta["job_id"],
            release_digest=meta["release_sha256"],
        )
        == result,
        "Archive replay drift.",
    )
    with target.with_name(target.name + ".sha256").open(
        "x", encoding="ascii", newline="\n"
    ) as stream:
        stream.write(checksum + "  " + target.name + "\n")
    return {
        "status": result["status"],
        "download": str(target),
        "sha256": checksum,
        "transfer_checksum": str(target) + ".sha256",
        "review": result,
        **normal.p.FLAGS,
    }


def audit(path, checksum, *, commit, job, release_digest):
    q._hash(checksum)
    raw = a._file(path, LIMIT)
    s.require(hashlib.sha256(raw).hexdigest() == checksum, "Archive checksum drift.")
    records = launcher.first.read_tar(raw, LIMIT, MEMBERS)
    result = review_public(
        c.decode_json(records["carrier.json"]),
        commit=commit,
        job=job,
        release_digest=release_digest,
    )
    s.require(c.decode_json(records["review.json"]) == result, "Stored review drift.")
    return result
