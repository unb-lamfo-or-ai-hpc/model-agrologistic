"""Closed operational gate, terminal transfer and negative portable replay.

Scheduler, source declarations, runtime and kernel observations are fakes.
There is no NPAD submission or licensed solver exercise in this qualification.
"""

import copy
import gzip
import hashlib
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from scripts import mvp2_s2_diagnostic_gate as g
from tests import test_mvp2_s2_diagnostic_normal as diagnostics
from tests import test_mvp2_s2_resource_launcher as releases

adapter = diagnostics.adapter
diagnostic = diagnostics.diagnostic
proposal = releases.proposal


def terminal(job="500000", state="COMPLETED"):
    return f"{job}|{state}|0:0|20\n{job}.batch|{state}|0:0|20\n{job}.7|COMPLETED|0:0|1\n"


@pytest.fixture
def gate(diagnostic):
    return {
        "schema_version": "s2-diagnostic-operational-gate-v1",
        "source_commit": diagnostic.item["source_commit"],
        "release_sha256": "d" * 64,
        "source": copy.deepcopy(diagnostic.source),
        "binding": g.n.portable_binding(diagnostic.item),
        "claim_name": g.CLAIM,
        "entry": g.ENTRY,
        "resource_policy": copy.deepcopy(g.p.POLICY),
        "profile": copy.deepcopy(g.q.PROFILE),
        "preserved_negative": {"job_id": g.NEGATIVE_JOB, "archive_sha256": g.NEGATIVE_ARCHIVE},
        **g.p.FLAGS,
    }


def external(gate):
    return {
        "commit": gate["source_commit"],
        "job": gate["binding"]["job_id"],
        "release_digest": gate["release_sha256"],
    }


def finish(diagnostic):
    diagnostics.old.start_fixture(diagnostic)
    diagnostics.phases(diagnostic)
    diagnostic.transport.count = 0
    diagnostic.transport.handle.process.poll = lambda: 0
    for seconds in (1, 3, 5, 8):
        diagnostic.test_clock[0] = seconds
        diagnostic.tick()
    return diagnostics.preserve(diagnostic)


def transfer(diagnostic, tmp_path):
    finish(diagnostic)
    return g.d.collect_components(diagnostic.root, tmp_path / "component", diagnostic.item)


def test_sealed_release_gate_requires_new_source_closure_without_effects(proposal, tmp_path):
    value = copy.deepcopy(proposal)
    value["manifest"]["files"].update(dict.fromkeys(g.CLOSURE, "d" * 64))
    value["manifest"]["source"] = g.l.identity.source_summary(value["manifest"]["files"])
    value["envelope"]["source"] = value["manifest"]["source"]
    value["plan"]["envelope_sha256"] = g.s.digest(value["envelope"])
    value = g.l.acknowledged(value, "500000")
    result = g.qualify_release(
        value, commit=value["envelope"]["source_commit"], release_digest=g.s.digest(value)
    )
    assert g.review_gate(result, **external(result)) == result
    assert g.CLAIM != g.l.CLAIM and not list(tmp_path.iterdir())
    del value["manifest"]["files"][g.ENTRY]
    value["manifest"]["source"] = g.l.identity.source_summary(value["manifest"]["files"])
    value["envelope"]["source"] = value["manifest"]["source"]
    value["plan"]["envelope_sha256"] = g.s.digest(value["envelope"])
    with pytest.raises(ValueError):
        g.qualify_release(value, commit=result["source_commit"], release_digest=g.s.digest(value))


@pytest.mark.parametrize(
    "field",
    [
        *g.p.FLAGS,
        "entry",
        "claim_name",
        "resource_policy",
        "profile",
        "source_commit",
        "release_sha256",
        "preserved_negative",
    ],
)
def test_gate_rejects_authority_historical_claim_or_policy_drift(gate, field):
    value = copy.deepcopy(gate)
    value[field] = True if field in g.p.FLAGS else "drift"
    with pytest.raises((ValueError, TypeError)):
        g.review_gate(value, **external(gate))


@pytest.mark.parametrize("job", ["1", g.NEGATIVE_JOB, "2208459", "2209138", "2209770"])
def test_consumed_or_placeholder_job_never_becomes_new_gate(gate, job):
    gate["binding"]["job_id"] = job
    with pytest.raises(ValueError):
        g.review_gate(gate, **external(gate))


def test_portable_replay_same_as_bound_spec_and_no_private_paths(diagnostic, tmp_path, gate):
    value = finish(diagnostic)
    assert g.d.review(value, diagnostic.item) == g.d.review_portable(value, gate["binding"])
    result = g.d.collect_components(diagnostic.root, tmp_path / "component", diagnostic.item)
    carrier = g.build_carrier(result, gate, terminal())
    reviewed = g.review_public(carrier, **external(gate))
    assert reviewed["controller_state"] == "candidate_closed"
    assert all(reviewed[k] is False for k in g.p.FLAGS)
    assert str(diagnostic.root) not in json.dumps(carrier)
    assert diagnostic.item["checkout"] not in json.dumps(carrier)


@pytest.mark.parametrize("text", ["", "500000|COMPLETED|0:0|20\n", terminal(state="RUNNING")])
def test_pending_root_only_or_nonterminal_does_not_create_collection(
    diagnostic, tmp_path, gate, monkeypatch, text
):
    monkeypatch.setattr(g, "qualify_release", lambda *args, **kwargs: gate)
    output = tmp_path / "pending"
    result = g.collect_components(
        diagnostic.item["run"],
        output,
        {"plan": {"specification": diagnostic.item}},
        text,
        commit=gate["source_commit"],
        release_digest=gate["release_sha256"],
    )
    assert result["status"] == "nonterminal_or_accounting_pending" and not output.exists()


def test_missing_bound_step_downgrades_terminal_complete_not_cleanup(diagnostic, tmp_path, gate):
    item = transfer(diagnostic, tmp_path)
    carrier = g.build_carrier(
        item, gate, "500000|COMPLETED|0:0|20\n500000.batch|COMPLETED|0:0|20\n"
    )
    assert carrier["disposition"] == "rejected_final"
    assert carrier["transfer"]["evidence"] is None
    assert g.review_public(carrier, **external(gate))["controller_state"] is None


@pytest.mark.parametrize("kind", ["missing", "truncated", "journal"])
def test_partial_and_rejected_evidence_is_preserved_not_repaired(diagnostic, tmp_path, gate, kind):
    finish(diagnostic)
    target = diagnostic.root / (
        "sample-0000.json" if kind == "journal" else "diagnostic-evidence.json"
    )
    if kind == "missing":
        target.unlink()
    else:
        target.write_bytes(b"{")
    before = {p: p.read_bytes() for p in diagnostic.root.rglob("*") if p.is_file()}
    item = g.d.collect_components(diagnostic.root, tmp_path / "partial", diagnostic.item)
    carrier = g.build_carrier(item, gate, terminal())
    result = g.review_public(carrier, **external(gate))
    assert result["status"] == "terminal_forensic_preserved_not_qualified"
    assert all(result[k] is False for k in g.p.FLAGS)
    assert before == {p: p.read_bytes() for p in diagnostic.root.rglob("*") if p.is_file()}


@pytest.mark.parametrize(
    "drift", ["diagnostic", "tail", "claim", "product", "source", "step", "flag", "nonce"]
)
def test_portable_tampering_never_certifies_complete(diagnostic, tmp_path, gate, drift):
    carrier = g.build_carrier(transfer(diagnostic, tmp_path), gate, terminal())
    inv = carrier["transfer"]["inventory"]
    if drift == "diagnostic":
        inv["diagnostic-sample-0000.json"]["semantic_sha256"] = "f" * 64
    elif drift == "tail":
        inv["sample-9999.json"] = copy.deepcopy(inv["sample-0000.json"])
    elif drift == "claim":
        inv["claim.json"]["semantic_sha256"] = "f" * 64
    elif drift == "product":
        inv["worker/terminal.json"]["semantic_sha256"] = "f" * 64
    elif drift == "source":
        carrier["gate"]["source"]["source_sha256"] = "f" * 64
    elif drift == "step":
        carrier["accounting"].pop("500000.7")
    elif drift == "flag":
        carrier[next(iter(g.p.FLAGS))] = True
    else:
        carrier["gate"]["binding"]["nonce"] = "f" * 64
    with pytest.raises(ValueError):
        g.review_public(carrier, **external(gate))


def test_terminal_archive_checksum_external_binding_and_immutable_collection(
    diagnostic, tmp_path, gate, monkeypatch
):
    finish(diagnostic)
    monkeypatch.setattr(g, "qualify_release", lambda *args, **kwargs: gate)
    monkeypatch.setattr(g.l, "claim_path", lambda: pytest.fail("Consumed claim fallback"))
    before = {p: p.read_bytes() for p in diagnostic.root.rglob("*") if p.is_file()}
    release = {"plan": {"specification": diagnostic.item}}
    output = tmp_path / "terminal"
    result = g.collect_components(
        diagnostic.root,
        output,
        release,
        terminal(),
        commit=gate["source_commit"],
        release_digest=gate["release_sha256"],
    )
    checksum = hashlib.sha256(Path(result["download"]).read_bytes()).hexdigest()
    assert result["sha256"] == checksum
    assert g.audit(result["download"], checksum, **external(gate)) == result["review"]
    assert Path(result["transfer_checksum"]).read_text().startswith(checksum + "  ")
    for key, wrong in (("commit", "f" * 40), ("job", "500001"), ("release_digest", "f" * 64)):
        args = {**external(gate), key: wrong}
        with pytest.raises(ValueError):
            g.audit(result["download"], checksum, **args)
    with pytest.raises(ValueError):
        g.audit(result["download"], "f" * 64, **external(gate))
    with pytest.raises(FileExistsError):
        g.collect_components(
            diagnostic.root,
            output,
            release,
            terminal(),
            commit=gate["source_commit"],
            release_digest=gate["release_sha256"],
        )
    assert before == {p: p.read_bytes() for p in diagnostic.root.rglob("*") if p.is_file()}


def test_attributed_cancelled_step_terminal_does_not_imply_success(diagnostic, tmp_path, gate):
    item = transfer(diagnostic, tmp_path)
    carrier = g.build_carrier(
        item, gate, terminal().replace(".7|COMPLETED|0:0|1", ".7|CANCELLED by 1271|0:9|1")
    )
    result = g.review_public(carrier, **external(gate))
    assert carrier["accounting"]["500000.7"]["state"] == "CANCELLED"
    assert not result["live_containment_qualified"]


@pytest.mark.parametrize("mode", ["review", "duplicate", "extra", "symlink", "missing"])
def test_archive_rehashed_tampering_is_rejected(diagnostic, tmp_path, gate, mode):
    carrier = g.build_carrier(transfer(diagnostic, tmp_path), gate, terminal())
    result = g.review_public(carrier, **external(gate))
    if mode == "review":
        result["controller_state"] = "invented"
    records = [("carrier.json", g.c.encoded(carrier)), ("review.json", g.c.encoded(result))]
    if mode == "duplicate":
        records.append(records[0])
    elif mode in {"extra", "symlink"}:
        records.append(("unexpected.json", b"{}"))
    elif mode == "missing":
        records.pop()
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for name, raw in records:
                item = tarfile.TarInfo(name)
                if mode == "symlink" and name == "unexpected.json":
                    item.type, item.linkname = tarfile.SYMTYPE, "carrier.json"
                    archive.addfile(item)
                else:
                    item.size = len(raw)
                    archive.addfile(item, io.BytesIO(raw))
    path = tmp_path / "tampered.tar.gz"
    path.write_bytes(output.getvalue())
    with pytest.raises(ValueError):
        g.audit(path, hashlib.sha256(output.getvalue()).hexdigest(), **external(gate))


def test_missing_membership_remains_blocked_in_terminal_replay(diagnostic, tmp_path, gate):
    diagnostics.old.start_fixture(diagnostic)
    diagnostics.phases(diagnostic)
    diagnostic.transport.count = 0
    diagnostic.transport.handle.process.poll = lambda: 0

    def unavailable():
        raise FileNotFoundError("not exported")

    diagnostic._members = unavailable
    for seconds in (1, 3, 8, 391):
        diagnostic.test_clock[0] = seconds
        diagnostic.tick()
    diagnostics.preserve(diagnostic)
    item = g.d.collect_components(diagnostic.root, tmp_path / "negative", diagnostic.item)
    carrier = g.build_carrier(item, gate, terminal())
    result = g.review_public(carrier, **external(gate))
    assert result["controller_state"] == "blocked"
    assert all(result[k] is False for k in g.p.FLAGS)


def test_output_inside_preserved_claim_is_denied_before_capture(
    diagnostic, tmp_path, gate, monkeypatch
):
    monkeypatch.setattr(g, "qualify_release", lambda *args, **kwargs: gate)
    monkeypatch.setattr(
        g.d, "collect_components", lambda *args: pytest.fail("Capture inside claim")
    )
    output = tmp_path / ".mvp2-s2-old-claim" / "collection"
    with pytest.raises(ValueError):
        g.collect_components(
            diagnostic.item["run"],
            output,
            {"plan": {"specification": diagnostic.item}},
            terminal(),
            commit=gate["source_commit"],
            release_digest=gate["release_sha256"],
        )
    assert not output.exists()


@pytest.mark.parametrize("argv", [[], ["start"], ["batch"], ["worker"], ["collect"], ["--admit"]])
def test_every_public_entry_denies_before_effects(argv):
    result = subprocess.run(
        [sys.executable, "-B", "-I", str(Path(g.__file__).resolve()), *argv],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode != 0 and b"Diagnostic operational gate closed" in result.stderr
    assert b"ModuleNotFoundError" not in result.stderr
    with pytest.raises(PermissionError):
        g.execute_normal(admit=True)
