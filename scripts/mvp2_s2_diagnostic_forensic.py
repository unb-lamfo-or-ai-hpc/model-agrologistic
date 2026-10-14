"""Bounded terminal metadata when the normal run has no trustworthy binding.

This preserves evidence, not a reconstructed attempt or proof of no execution.
No tool calls, original writes, archive extraction or admission are provided.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Operational forensic component only; no execution admitted.")

import gzip
import hashlib
import io
import tarfile
from pathlib import Path

from scripts import mvp2_s2_diagnostic_gate as g

a, c, f, n, p, q, s = g.a, g.c, g.f, g.n, g.p, g.q, g.s
SCHEMA = "s2-diagnostic-operational-forensic-v1"


def capture(run, claim, job):
    run, claim = Path(run), Path(claim)
    q._safe_path(run)
    q._safe_path(claim)
    records = f.read_records(run)
    if run.exists():
        for index, path in enumerate(run.iterdir()):
            s.require(index < f.MAX_FILES + a.MAX_SAMPLES + 32, "Forensic run bound.")
            if path.name.startswith("diagnostic-"):
                s.require(g.valid_name(path.name), "Diagnostic forensic member.")
                records[path.name] = a._file(path, n.LIMIT)
    s.require(sum(map(len, records.values())) <= f.LIMIT, "Forensic byte bound.")
    claim_records = {}
    for name in sorted(f.CLAIM_FILES):
        try:
            claim_records[name] = f.metadata(a._file(claim / name, g.l.LIMIT))
        except FileNotFoundError:
            pass
    return {
        "inventory": {name: f.metadata(raw) for name, raw in sorted(records.items())},
        "claim_inventory": claim_records,
        "entry_logs": {
            key: n.x.collect_entry_log(claim / f"slurm-{job}.{key}") for key in ("out", "err")
        },
    }


def review(value, *, commit, job, release_digest):
    q._keys(
        value,
        {
            "schema_version",
            "gate",
            "accounting_text",
            "accounting",
            "capture",
            "disposition",
            *p.FLAGS,
        },
    )
    s.require(
        value["schema_version"] == SCHEMA and all(value[k] is False for k in p.FLAGS),
        "Forensic authority/schema.",
    )
    gate = g.review_gate(value["gate"], commit=commit, job=job, release_digest=release_digest)
    text = value["accounting_text"]
    s.require(type(text) is str and len(text.encode()) <= 65536, "Forensic accounting bound.")
    rows, ready = f.terminal_rows(text, job)
    s.require(ready and rows == value["accounting"], "Forensic terminal accounting.")
    captured = value["capture"]
    q._keys(captured, {"inventory", "claim_inventory", "entry_logs"})
    g.review_inventory(captured["inventory"])
    s.require(
        value["disposition"] in {"no_bound_attempt", "run_binding_rejected"},
        "Forensic disposition.",
    )
    if value["disposition"] == "no_bound_attempt":
        s.require("claim.json" not in captured["inventory"], "Bound claim incorrectly missing.")
    files = captured["claim_inventory"]
    s.require(type(files) is dict and files.keys() <= f.CLAIM_FILES, "Claim member bound.")
    for record in files.values():
        g.review_inventory({"claim.json": record})
        s.require(record["bytes"] <= g.l.LIMIT, "Claim byte bound.")
    s.require(
        "release.json" in files and files["release.json"]["semantic_sha256"] == release_digest,
        "Forensic external release drift.",
    )
    g.same(
        files,
        "job.json",
        {
            "source_commit": commit,
            "job_id": job,
            "release_sha256": release_digest,
            "specification_sha256": gate["binding"]["specification_sha256"],
        },
    )
    q._keys(captured["entry_logs"], {"out", "err"})
    for log in captured["entry_logs"].values():
        q._keys(log, {"status", "sha256", "bytes", "diagnostics"})
        s.require(
            type(log["diagnostics"]) is list and len(log["diagnostics"]) <= 2,
            "Diagnostic log count.",
        )
        if log["status"] == "missing":
            s.require(
                log == {"status": "missing", "sha256": None, "bytes": None, "diagnostics": []},
                "Missing log drift.",
            )
        else:
            q._hash(log["sha256"])
            s.require(
                log["status"] in {"captured", "no_structured_diagnostic"}
                and type(log["bytes"]) is int
                and 0 <= log["bytes"] <= n.x.LOG_LIMIT
                and bool(log["diagnostics"]) == (log["status"] == "captured"),
                "Log metadata drift.",
            )
        for record in log["diagnostics"]:
            q._keys(record, {"schema_version", "role", "phase", "error_kind", *n.x.n.FUTURE})
            s.require(
                record["schema_version"] == "s2-compute-entry-v1"
                and record["role"] in {"batch", "worker"}
                and record["phase"] in {"host", "identity", "release", "claim", "dispatch"}
                and record["error_kind"] in n.x.ERRORS
                and all(record[k] is False for k in n.x.n.FUTURE),
                "Structured log drift.",
            )
    return {
        "schema_version": "s2-diagnostic-operational-forensic-review-v1",
        "status": "terminal_no_bound_attempt_preserved_not_qualified",
        "disposition": value["disposition"],
        "controller_state": None,
        "source_commit": commit,
        "job_id": job,
        "release_sha256": release_digest,
        "carrier_sha256": s.digest(value),
        "worker_cpu_usage_ns": None,
        **p.FLAGS,
    }


def pack(destination, value, *, commit, job, release_digest):
    result = review(value, commit=commit, job=job, release_digest=release_digest)
    records = {"carrier.json": c.encoded(value), "review.json": c.encoded(result)}
    s.require(sum(map(len, records.values())) <= f.LIMIT - 16384, "Forensic archive bound.")
    target = Path(destination) / "s2-diagnostic-normal-evidence.tar.gz"
    q._safe_path(target)
    with target.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for name, data in sorted(records.items()):
                item = tarfile.TarInfo(name)
                item.size, item.mode = len(data), 0o600
                archive.addfile(item, io.BytesIO(data))
    checksum = hashlib.sha256(a._file(target, f.LIMIT)).hexdigest()
    s.require(
        audit(target, checksum, commit=commit, job=job, release_digest=release_digest) == result,
        "Forensic archive replay drift.",
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
        **p.FLAGS,
    }


def audit(path, checksum, *, commit, job, release_digest):
    q._hash(checksum)
    raw = a._file(path, f.LIMIT)
    s.require(hashlib.sha256(raw).hexdigest() == checksum, "Forensic archive checksum drift.")
    records = g.l.first.read_tar(raw, f.LIMIT, g.MEMBERS)
    s.require(records.keys() == g.MEMBERS, "Archive member set.")
    value = c.decode_json(records["carrier.json"])
    if value.get("schema_version") != SCHEMA:
        return g.audit(path, checksum, commit=commit, job=job, release_digest=release_digest)
    result = review(value, commit=commit, job=job, release_digest=release_digest)
    s.require(c.decode_json(records["review.json"]) == result, "Stored forensic review drift.")
    return result
