"""Bounded terminal/forensic carrier and independent pure replay; no extraction.

The release/digest is external input, never trusted from an archive. Unknown or
missing attempts stay negative. All returned reviews remain non-admitting.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Lifecycle transfer CLI remains closed; no execution admitted.")

import base64
import copy
import gzip
import hashlib
import io
import os
import tarfile
from pathlib import Path
from types import SimpleNamespace

from scripts import mvp2_s2_lifecycle_release as r

m, lc, s, q, a, c = r.m, r.lc, r.s, r.q, r.a, r.c
LIMIT = 48 * 1024**2
FILES = {"package.json", "carrier.json", "accounting.txt", "review.json", "claim-records.json"}
CLAIM_FILES = {
    "submission-intent.json",
    "submission-called.json",
    "job.json",
    "submission-unknown.json",
    "stop-latched.json",
    "batch.sh",
    "slurm.out",
    "slurm.err",
    "launcher-intent.json",
    "launcher-result.json",
    "launcher-unknown.json",
}


def claim_record(raw):
    s.require(type(raw) is bytes and len(raw) <= 65536, "Raw claim record bound.")
    return {
        "encoding": "base64",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "payload": base64.b64encode(raw).decode("ascii"),
    }


def validate_claim_records(records):
    s.require(
        type(records) is dict and records.keys() <= CLAIM_FILES,
        "Only fixed new-claim metadata/logs can be transferred.",
    )
    for value in records.values():
        q._keys(value, {"encoding", "sha256", "payload"})
        s.require(
            value["encoding"] == "base64"
            and type(value["payload"]) is str
            and len(value["payload"]) <= 90000,
            "Claim record encoding bound.",
        )
        q._hash(value["sha256"])
        raw = base64.b64decode(value["payload"], validate=True)
        s.require(claim_record(raw) == value, "Raw claim record integrity drift.")
    return records


def execute(*_args, **_kwargs):
    raise PermissionError("Lifecycle transfer operational route remains closed.")


def capture_components(adapter, session):
    return {
        "schema_version": "s2-lifecycle-operational-carrier-v1",
        "frames": copy.deepcopy(adapter.frames),
        "observations": copy.deepcopy(adapter.observations),
        "journal": copy.deepcopy(adapter.protocol.journal),
        "failures": copy.deepcopy(adapter.failures),
        "fixture": adapter.kernel.fixture,
        "session": copy.deepcopy(session),
        **lc.FLAGS,
    }


def review_effects(value, item, journal):
    """Recompute fixed effect ordering/bindings; an acknowledgement is not cleanup."""
    q._keys(
        value,
        {
            "schema_version",
            "events",
            "release_sent_not_admitted",
            "unknown_effect",
            "adapter",
            *lc.FLAGS,
        },
    )
    s.require(
        value["schema_version"] == "s2-lifecycle-session-review-v1"
        and all(value[k] is False for k in lc.FLAGS)
        and type(value["events"]) is list
        and len(value["events"]) <= 16
        and type(value["release_sent_not_admitted"]) is bool
        and type(value["unknown_effect"]) is bool,
        "Session grammar/authority drift.",
    )
    previous, seen, term_at, last_seconds = s.digest(item), set(), None, 0
    binding = item["resource_contract"]["legacy_contract"]["binding"]
    for event in value["events"]:
        q._keys(event, {"name", "value", "previous_sha256"})
        name, payload = event["name"], event["value"]
        s.require(
            name not in seen and event["previous_sha256"] == previous,
            "Effect event order/hash/duplicate drift.",
        )
        s.require(all(payload.get(k) is False for k in lc.FLAGS), "Admitting effect receipt.")
        if name == "release-intent":
            q._keys(payload, {"token", "barrier_sha256", *lc.FLAGS})
            s.require(
                "stop-latched" not in seen
                and journal
                and journal[0]["kind"] == "bind"
                and payload["barrier_sha256"] == s.digest(journal[:1]),
                "Release without initial barrier or after stop.",
            )
            token = payload["token"]
            q._keys(
                token,
                {
                    "schema_version",
                    "source_commit",
                    "job_id",
                    "nonce",
                    "manifest_sha256",
                    "contract_sha256",
                    *lc.FLAGS,
                },
            )
            s.require(
                token["schema_version"] == "s2-lifecycle-wire-release-v1"
                and token["source_commit"] == binding["source_commit"]
                and token["job_id"] == binding["job_id"]
                and token["nonce"] == binding["nonce"]
                and token["contract_sha256"] == s.digest(item)
                and all(token[k] is False for k in lc.FLAGS),
                "Release token drift.",
            )
            q._hash(token["manifest_sha256"])
        elif name in {"release-result", "release-unknown"}:
            q._keys(payload, {"status", *lc.FLAGS})
            s.require(
                "release-intent" in seen
                and not {"release-result", "release-unknown"} & seen
                and payload["status"]
                == ("sent_not_admitted" if name == "release-result" else "unknown_effect_no_retry"),
                "Release acknowledgement order.",
            )
        elif name == "stop-latched":
            q._keys(payload, {"reason", "seconds", *lc.FLAGS})
            s.require(
                payload["reason"] in {"operator_stop", "observation_failure", "exercise_deadline"},
                "Stop reason drift.",
            )
            q._number(payload["seconds"])
            s.require(last_seconds <= payload["seconds"] < 660, "Stop clock/deadline drift.")
            last_seconds = payload["seconds"]
        elif name in {"signal-TERM-intent", "signal-KILL-intent"}:
            q._keys(payload, {"binding", "seconds", *lc.FLAGS})
            now = q._number(payload["seconds"])
            s.require(now >= last_seconds, "Effect clock rollback.")
            last_seconds = now
            s.require(
                "stop-latched" in seen and payload["binding"] == binding and now < 660,
                "Signal without latched exact binding/deadline.",
            )
            if name == "signal-TERM-intent":
                term_at = now
            else:
                s.require(
                    term_at is not None and 5 <= now - term_at < 390,
                    "Unqualified signal escalation.",
                )
        else:
            s.require(
                name
                in {
                    "signal-TERM-result",
                    "signal-TERM-unknown",
                    "signal-KILL-result",
                    "signal-KILL-unknown",
                },
                "Unknown effect.",
            )
            q._keys(payload, {"status", *lc.FLAGS})
            prefix = name.rsplit("-", 1)[0]
            s.require(
                prefix + "-intent" in seen
                and not {prefix + "-result", prefix + "-unknown"} & seen
                and payload["status"]
                == (
                    "acknowledged_not_cleanup"
                    if name.endswith("result")
                    else "unknown_effect_no_retry"
                ),
                "Signal acknowledgement order.",
            )
        previous = s.digest(event)
        seen.add(name)
    s.require(
        not any(name.endswith("-unknown") for name in seen) or value["unknown_effect"],
        "Unknown effect cannot be hidden by a false outcome flag.",
    )
    s.require(
        value["release_sent_not_admitted"] == ("release-result" in seen) or value["unknown_effect"],
        "Unrecomputable release outcome.",
    )
    return {"event_count": len(seen), "events_sha256": previous, **lc.FLAGS}


def restore_protocol(item, journal):
    expected = lc.replay(item, journal)
    protocol = lc.Protocol(item)
    for event in journal:
        payload, now = event["payload"], event["seconds"]
        if event["kind"] == "bind":
            protocol.bind(now, payload["boundary"], payload["first"], payload["second"])
        elif event["kind"] == "register":
            protocol.register(
                now, payload["process"], payload["parent"], payload["ownership_evidence_sha256"]
            )
        elif event["kind"] == "end":
            protocol.end(now)
        else:
            protocol.sample(now, payload["packet"])
    s.require(protocol.receipt() == expected, "Restored protocol drift.")
    return protocol


class ReviewState:
    """Inert state only: exposes receipt/replay, no launch, observe or role entry."""

    def receipt(self):
        return m.OperationalAdapter.receipt(self)

    def terminal_review(self, text):
        return m.OperationalAdapter.terminal_review(self, text)


def replay_components(value, expected_release_sha256, carrier, accounting_text):
    value = r.validate(value)
    q._hash(expected_release_sha256)
    s.require(s.digest(value) == expected_release_sha256, "External release digest drift.")
    spec = value["specification"]
    s.require(
        spec["job_id"] != "1"
        and type(accounting_text) is str
        and len(accounting_text.encode()) <= 65536,
        "Bound terminal accounting required.",
    )
    rows = a.accounting(accounting_text, spec["job_id"])
    s.require(
        all(
            key in rows and rows[key]["state"] in a.TERMINAL
            for key in (spec["job_id"], spec["job_id"] + ".batch")
        ),
        "Nonterminal/unknown root or batch; preserve and collect later.",
    )
    review, effects, disposition = None, None, "missing_attempt_preserved"
    if carrier is not None:
        try:
            q._keys(
                carrier,
                {
                    "schema_version",
                    "frames",
                    "observations",
                    "journal",
                    "failures",
                    "fixture",
                    "session",
                    *lc.FLAGS,
                },
            )
            s.require(
                carrier["schema_version"] == "s2-lifecycle-operational-carrier-v1"
                and all(carrier[k] is False for k in lc.FLAGS)
                and type(carrier["fixture"]) is bool
                and len(c.encoded(carrier)) <= 40 * 1024**2,
                "Carrier grammar/bound.",
            )
            state = ReviewState()
            state.spec, state.item = spec, value["contract"]
            state.manifest_sha256 = value["manifest_sha256"]
            state.frames, state.observations = carrier["frames"], carrier["observations"]
            s.require(
                type(state.frames) is list
                and len(state.frames) <= 2
                and type(state.observations) is list
                and len(state.observations) <= 1024,
                "Frame sequence bound.",
            )
            state.failures = carrier["failures"]
            s.require(
                type(state.failures) is list and len(state.failures) <= 8,
                "Failure inventory bound.",
            )
            allowed_phases = {
                "source_runtime",
                "ipc_receive",
                "kernel_peer",
                "first_environment",
                "worker_and_launcher_identity",
                "second_environment",
                "software_barrier",
                "independent_observation",
            }
            for failure in state.failures:
                q._keys(failure, {"phase", "error_kind"})
                s.require(
                    failure["phase"] in allowed_phases
                    and failure["error_kind"] == "invalid_or_unavailable_evidence",
                    "Uncontrolled failure diagnostic.",
                )
            s.require(
                all(
                    frame["fixture"] is carrier["fixture"]
                    for frame in [*state.frames, *state.observations]
                ),
                "Observation provenance drift.",
            )
            state.kernel = SimpleNamespace(fixture=carrier["fixture"])
            state.protocol = restore_protocol(state.item, carrier["journal"])
            state.original = state.frames[0]["result"] if state.protocol.bound is not None else None
            if state.original is not None:
                s.require(
                    len(state.frames) == 2
                    and state.frames[1]["result"] is not None
                    and state.protocol.journal[0]["payload"]["boundary"]
                    == state.original["boundary"],
                    "Missing/unbound startup frames.",
                )
            review = state.terminal_review(accounting_text)
            s.require(
                review["disposition"] != "rejected_evidence_preserved", "Rejected adapter replay."
            )
            s.require(
                carrier["session"]["adapter"] == state.receipt(), "Session/adapter receipt drift."
            )
            effects = review_effects(carrier["session"], state.item, carrier["journal"])
            for event in carrier["session"]["events"]:
                if event["name"] == "release-intent":
                    s.require(
                        event["value"]["token"]["manifest_sha256"] == state.manifest_sha256,
                        "Effect/source manifest drift.",
                    )
            disposition = "negative_or_partial_preserved"
            if (
                state.protocol.state == "software_candidate_closed"
                and carrier["session"]["release_sent_not_admitted"]
                and not carrier["session"]["unknown_effect"]
                and not state.failures
            ):
                disposition = "software_candidate_replayed_not_live_qualified"
        except (ValueError, TypeError, KeyError, AttributeError, IndexError):
            review, effects, disposition = None, None, "rejected_attempt_preserved"
    return {
        "schema_version": "s2-lifecycle-terminal-transfer-review-v1",
        "source_commit": spec["source_commit"],
        "job_id": spec["job_id"],
        "release_sha256": expected_release_sha256,
        "carrier_sha256": s.digest(carrier),
        "accounting_sha256": s.digest(rows),
        "disposition": disposition,
        "adapter_review": review,
        "effects_review": effects,
        "original_inputs_preserved": True,
        **lc.FLAGS,
    }


def collect_components(
    value, expected_release_sha256, carrier, accounting_text, destination, *, claim_records=None
):
    review = replay_components(value, expected_release_sha256, carrier, accounting_text)
    records = validate_claim_records({} if claim_records is None else claim_records)
    payloads = {
        "package.json": c.encoded(value),
        "carrier.json": c.encoded(carrier),
        "accounting.txt": accounting_text.encode(),
        "review.json": c.encoded(review),
        "claim-records.json": c.encoded(records),
    }
    s.require(sum(map(len, payloads.values())) <= LIMIT, "Transfer byte bound.")
    root = Path(destination)
    q._safe_path(root)
    root.mkdir(mode=0o700, exist_ok=False)
    r.sync_directory(root.parent)
    archive = root / "s2-lifecycle-normal-evidence.tar.gz"
    with archive.open("xb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as tar:
                for name in sorted(FILES):
                    info = tarfile.TarInfo(name)
                    info.size, info.mode = len(payloads[name]), 0o600
                    tar.addfile(info, io.BytesIO(payloads[name]))
        raw.flush()
        os.fsync(raw.fileno())
    checksum = a.sha_file(archive)
    with (root / "s2-lifecycle-normal-evidence.tar.gz.sha256").open(
        "x", encoding="ascii"
    ) as stream:
        stream.write(checksum + "  s2-lifecycle-normal-evidence.tar.gz\n")
        stream.flush()
        os.fsync(stream.fileno())
    r.sync_directory(root)
    result = audit_archive(archive, checksum, value, expected_release_sha256)
    return {"archive": str(archive), "sha256": checksum, "review": result, **lc.FLAGS}


def audit_archive(path, expected_sha256, value, expected_release_sha256):
    q._hash(expected_sha256)
    path = Path(path)
    q._safe_path(path)
    raw = a._file(path, LIMIT + 1024**2)
    s.require(hashlib.sha256(raw).hexdigest() == expected_sha256, "Archive checksum drift.")
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as zipped:
        unpacked = zipped.read(LIMIT + 1024**2 + 1)
    s.require(len(unpacked) <= LIMIT + 1024**2, "Decompression bound.")
    records, end = {}, 0
    with tarfile.open(fileobj=io.BytesIO(unpacked), mode="r:") as tar:
        for member in tar:
            s.require(
                member.name in FILES
                and member.name not in records
                and member.isfile()
                and not member.pax_headers
                and 0 < member.size <= LIMIT,
                "Archive allowlist/type/size drift.",
            )
            records[member.name] = tar.extractfile(member).read()
            end = member.offset_data + ((member.size + 511) // 512) * 512
    s.require(set(records) == FILES and not any(unpacked[end:]), "Missing/trailing archive data.")
    s.require(
        c.decode_json(records["package.json"]) == r.validate(value),
        "External operational package mismatch.",
    )
    validate_claim_records(c.decode_json(records["claim-records.json"]))
    review = replay_components(
        value,
        expected_release_sha256,
        c.decode_json(records["carrier.json"]),
        records["accounting.txt"].decode("utf-8"),
    )
    s.require(review == c.decode_json(records["review.json"]), "Nonrecomputable review.")
    return review
