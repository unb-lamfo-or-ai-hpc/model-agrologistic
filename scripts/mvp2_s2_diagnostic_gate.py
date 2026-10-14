"""Closed operational identity gate and terminal diagnostic transfer components.

No scheduler, transport factory, reservation, worker entry or admission exists.
The previous release format is a validated input only, never its consumed claim.
Portable replay verifies semantics and inventory bindings, not installed cleanup.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Diagnostic operational gate closed; no execution admitted.")

import copy
import gzip
import hashlib
import io
import re
import tarfile
from pathlib import Path

from scripts import mvp2_s2_diagnostic_normal as d
from scripts import mvp2_s2_resource_launcher as l

a, c, f, n, p, q, s = d.a, d.c, d.f, d.n, d.p, d.q, d.s
ENTRY = "scripts/mvp2_s2_diagnostic_gate.py"
CLAIM = ".mvp2-s2-diagnostic-normal-v1"
CLOSURE = l.CLOSURE | {
    ENTRY,
    "scripts/mvp2_s2_diagnostic_normal.py",
    "scripts/mvp2_s2_normal_audit.py",
    "scripts/mvp2_s2_compute_identity.py",
    "scripts/mvp2_s2_synthetic_resources.py",
}
NEGATIVE_JOB = "2210506"
NEGATIVE_ARCHIVE = "0239bbec7edd29cf384e7949d441ec6fb3e8474f77c735799978620fc74aa642"
MEMBERS = {"carrier.json", "review.json"}


def execute_normal(*_args, **_kwargs):
    raise PermissionError("Diagnostic operational gate closed; no execution admitted.")


def qualify_release(release, *, commit, release_digest):
    """Pure qualification of a sealed declaration; never reserve a claim or job."""
    release = l.validate_release(release, commit, release_digest)
    spec = release["plan"]["specification"]
    s.require(
        CLOSURE <= release["manifest"]["files"].keys()
        and spec["job_id"] != NEGATIVE_JOB
        and Path(spec["run"]).name.startswith("s2n-")
        and Path(spec["run"]).name != CLAIM
        and Path(spec["checkout"]).name != CLAIM,
        "Diagnostic source/run closure.",
    )
    return {
        "schema_version": "s2-diagnostic-operational-gate-v1",
        "source_commit": commit,
        "release_sha256": release_digest,
        "source": copy.deepcopy(release["manifest"]["source"]),
        "binding": n.portable_binding(spec),
        "claim_name": CLAIM,
        "entry": ENTRY,
        "resource_policy": copy.deepcopy(p.POLICY),
        "profile": copy.deepcopy(q.PROFILE),
        "preserved_negative": {"job_id": NEGATIVE_JOB, "archive_sha256": NEGATIVE_ARCHIVE},
        **p.FLAGS,
    }


def review_gate(gate, *, commit, job, release_digest):
    q._hash(commit, 40)
    q._hash(release_digest)
    q._keys(
        gate,
        {
            "schema_version",
            "source_commit",
            "release_sha256",
            "source",
            "binding",
            "claim_name",
            "entry",
            "resource_policy",
            "profile",
            "preserved_negative",
            *p.FLAGS,
        },
    )
    binding = n.validate_portable_binding(gate["binding"])
    s.require(
        gate["schema_version"] == "s2-diagnostic-operational-gate-v1"
        and gate["source_commit"] == binding["source_commit"] == commit
        and gate["release_sha256"] == release_digest
        and binding["job_id"] == job
        and job not in {"1", NEGATIVE_JOB, *(v["job_id"] for v in l.HISTORY)}
        and gate["claim_name"] == CLAIM
        and gate["entry"] == ENTRY
        and gate["resource_policy"] == p.POLICY
        and gate["profile"] == q.PROFILE
        and gate["preserved_negative"]
        == {"job_id": NEGATIVE_JOB, "archive_sha256": NEGATIVE_ARCHIVE}
        and all(gate[k] is False for k in p.FLAGS),
        "External operational binding/authority drift.",
    )
    source = gate["source"]
    q._keys(source, {"source_sha256", "worker_sha256", "tracked_count"})
    for key in ("source_sha256", "worker_sha256"):
        q._hash(source[key])
    s.require(
        type(source["tracked_count"]) is int and 1 <= source["tracked_count"] <= 1024,
        "Source count.",
    )
    return copy.deepcopy(gate)


def valid_name(name):
    if f.valid_name(name) or name == "diagnostic-evidence.json":
        return True
    match = re.fullmatch(r"diagnostic-sample-([0-9]{4})\.json", name)
    return bool(match and int(match[1]) < a.MAX_SAMPLES)


def review_inventory(inventory):
    s.require(
        type(inventory) is dict and len(inventory) <= f.MAX_FILES + a.MAX_SAMPLES + 1,
        "Diagnostic inventory bound.",
    )
    total = 0
    for name, value in inventory.items():
        s.require(valid_name(name), "Unexpected inventory member.")
        q._keys(value, {"sha256", "semantic_sha256", "bytes", "status"})
        q._hash(value["sha256"])
        s.require(
            type(value["bytes"]) is int and 0 <= value["bytes"] <= n.LIMIT, "Inventory byte bound."
        )
        total += value["bytes"]
        if value["status"] == "json":
            q._hash(value["semantic_sha256"])
        else:
            s.require(
                value["status"] == "invalid_json" and value["semantic_sha256"] is None,
                "Inventory JSON status.",
            )
    s.require(total <= f.LIMIT, "Total inventory bound.")


def same(inventory, name, value):
    s.require(
        name in inventory
        and inventory[name]["status"] == "json"
        and inventory[name]["semantic_sha256"] == s.digest(value),
        "Portable inventory/semantic drift.",
    )


def complete_transfer(transfer, gate, rows):
    """Revalidate all replayed semantics, journal tails and bound step accounting."""
    value, inventory = transfer["evidence"], transfer["inventory"]
    replay = d.review_portable(value, gate["binding"])
    s.require(transfer["review"] == replay, "Diagnostic review drift.")
    base = value["base_evidence"]
    s.require(base["attempt"]["source"] == gate["source"], "Attempt release source drift.")
    same(inventory, "diagnostic-evidence.json", value)
    same(inventory, "resource-evidence.json", base)
    same(inventory, "attempt.json", base["attempt"])
    for prefix, items in (
        ("sample", value["samples"]),
        ("diagnostic-sample", value["diagnostics"]),
        ("event", base["events"]),
        ("resource-barrier", base["barriers"]),
        ("resource-sample", base["resources"]),
    ):
        expected = {}
        for index, item in enumerate(items):
            index = item["index"] if prefix == "resource-sample" else index
            suffix = str(index) if prefix == "resource-barrier" else f"{index:04d}"
            expected[f"{prefix}-{suffix}.json"] = item
        s.require(
            {v for v in inventory if v.startswith(prefix + "-")} == expected.keys(),
            "Portable journal tail/hole.",
        )
        for name, item in expected.items():
            same(inventory, name, item)
    contract = base["contract"]
    if contract is not None:
        same(inventory, "resource-contract.json", contract)
        same(inventory, "contract.json", contract["legacy_contract"])
        step = (
            gate["binding"]["job_id"]
            + "."
            + contract["legacy_contract"]["binding"]["worker_step_id"]
        )
        s.require(step in rows, "Missing bound numeric step accounting.")
        # Products observed by the adapter cannot disagree with the terminal files.
        for record in reversed(value["diagnostics"]):
            if "products" in record["payloads"]:
                products = record["payloads"]["products"]["products"]
                s.require(
                    {v[7:] for v in inventory if v.startswith("worker/")} == products.keys(),
                    "Terminal product inventory drift.",
                )
                for name, item in products.items():
                    same(inventory, "worker/" + name, item)
                break
    return replay


def review_public(carrier, *, commit, job, release_digest):
    q._keys(
        carrier,
        {
            "schema_version",
            "gate",
            "accounting_text",
            "accounting",
            "transfer",
            "disposition",
            *p.FLAGS,
        },
    )
    s.require(
        carrier["schema_version"] == "s2-diagnostic-terminal-carrier-v1"
        and all(carrier[k] is False for k in p.FLAGS),
        "Terminal carrier authority.",
    )
    gate = review_gate(carrier["gate"], commit=commit, job=job, release_digest=release_digest)
    text = carrier["accounting_text"]
    s.require(type(text) is str and len(text.encode()) <= 65536, "Accounting text bound.")
    rows, ready = f.terminal_rows(text, job)
    s.require(ready and rows == carrier["accounting"], "Terminal accounting required/drift.")
    transfer = carrier["transfer"]
    q._keys(
        transfer,
        {"schema_version", "specification_sha256", "inventory", "evidence", "review", *p.FLAGS},
    )
    s.require(
        transfer["schema_version"] == "s2-normal-diagnostic-transfer-v1"
        and transfer["specification_sha256"] == gate["binding"]["specification_sha256"]
        and all(transfer[k] is False for k in p.FLAGS),
        "Transfer authority/binding.",
    )
    inventory = transfer["inventory"]
    review_inventory(inventory)
    same(
        inventory,
        "claim.json",
        {"specification_sha256": transfer["specification_sha256"], **a.FLAGS},
    )
    state = None
    if carrier["disposition"] == "complete_replayed":
        state = complete_transfer(transfer, gate, rows)["controller_state"]
        status = "terminal_integrity_replayed_not_live_qualified"
    else:
        s.require(
            carrier["disposition"] in {"missing_final", "rejected_final"}
            and transfer["evidence"] is None,
            "Forensic disposition drift.",
        )
        expected = (
            "forensic_preserved_not_qualified"
            if carrier["disposition"] == "missing_final"
            else "forensic_rejected_not_qualified"
        )
        s.require(
            transfer["review"] == {"status": expected, **p.FLAGS}
            and (
                ("diagnostic-evidence.json" not in inventory)
                == (carrier["disposition"] == "missing_final")
            ),
            "Forensic final inventory drift.",
        )
        status = "terminal_forensic_preserved_not_qualified"
    return {
        "schema_version": "s2-diagnostic-terminal-review-v1",
        "status": status,
        "disposition": carrier["disposition"],
        "controller_state": state,
        "source_commit": commit,
        "job_id": job,
        "release_sha256": release_digest,
        "carrier_sha256": s.digest(carrier),
        "worker_cpu_usage_ns": None,
        **p.FLAGS,
    }


def build_carrier(transfer, gate, text):
    rows, ready = f.terminal_rows(text, gate["binding"]["job_id"])
    s.require(ready, "Terminal accounting required.")
    disposition = (
        "complete_replayed"
        if transfer["evidence"] is not None
        else (
            "missing_final"
            if "diagnostic-evidence.json" not in transfer["inventory"]
            else "rejected_final"
        )
    )
    carrier = {
        "schema_version": "s2-diagnostic-terminal-carrier-v1",
        "gate": copy.deepcopy(gate),
        "accounting_text": text,
        "accounting": rows,
        "transfer": copy.deepcopy(transfer),
        "disposition": disposition,
        **p.FLAGS,
    }
    try:
        review_public(
            carrier,
            commit=gate["source_commit"],
            job=gate["binding"]["job_id"],
            release_digest=gate["release_sha256"],
        )
    except (ValueError, KeyError, TypeError, IndexError, UnicodeError):
        if disposition != "complete_replayed":
            raise
        # Preserve metadata rather than certify inconsistent terminal semantics.
        carrier["transfer"]["evidence"] = None
        carrier["transfer"]["review"] = {"status": "forensic_rejected_not_qualified", **p.FLAGS}
        carrier["disposition"] = "rejected_final"
    return carrier


def collect_components(run, destination, release, text, *, commit, release_digest):
    """No live query: terminal text is explicit; old claim loaders are never used."""
    gate = qualify_release(release, commit=commit, release_digest=release_digest)
    job = gate["binding"]["job_id"]
    review_gate(gate, commit=commit, job=job, release_digest=release_digest)
    s.require(type(text) is str and len(text.encode()) <= 65536, "Accounting text bound.")
    _rows, ready = f.terminal_rows(text, job)
    if not ready:
        return {"status": "nonterminal_or_accounting_pending", **p.FLAGS}
    spec = release["plan"]["specification"]
    destination = Path(destination)
    q._safe_path(destination)
    s.require(
        not any(part.startswith(".mvp2-") for part in destination.parts),
        "Output inside a preserved campaign claim.",
    )
    for name in (CLAIM, l.CLAIM):
        preserved = Path(l.o.BASE) / name
        s.require(
            destination != preserved
            and preserved not in destination.parents
            and destination not in preserved.parents,
            "Output covers preserved claim.",
        )
    transfer = d.collect_components(run, destination, spec)
    carrier = build_carrier(transfer, gate, text)
    result = review_public(carrier, commit=commit, job=job, release_digest=release_digest)
    records = {"carrier.json": c.encoded(carrier), "review.json": c.encoded(result)}
    s.require(sum(map(len, records.values())) <= f.LIMIT - 16384, "Archive bound.")
    target = destination / "s2-diagnostic-normal-evidence.tar.gz"
    with target.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for name, data in sorted(records.items()):
                item = tarfile.TarInfo(name)
                item.size, item.mode = len(data), 0o600
                archive.addfile(item, io.BytesIO(data))
    checksum = hashlib.sha256(a._file(target, f.LIMIT)).hexdigest()
    s.require(
        audit(target, checksum, commit=commit, job=job, release_digest=release_digest) == result,
        "Transferred archive replay drift.",
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
    s.require(hashlib.sha256(raw).hexdigest() == checksum, "Archive checksum drift.")
    records = l.first.read_tar(raw, f.LIMIT, MEMBERS)
    s.require(records.keys() == MEMBERS, "Archive member set.")
    result = review_public(
        c.decode_json(records["carrier.json"]),
        commit=commit,
        job=job,
        release_digest=release_digest,
    )
    s.require(c.decode_json(records["review.json"]) == result, "Stored review drift.")
    return result
