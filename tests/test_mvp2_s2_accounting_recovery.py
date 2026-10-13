"""Cancellation grammar and read-only recovery; all scheduler effects are injected."""

import hashlib
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from scripts import mvp2_s2_accounting_recovery as r
from scripts import mvp2_s2_batch_adapter as a
from tests import test_mvp2_s2_node_normal as node
from tests import test_mvp2_s2_operational as operational
from tests.test_mvp2_s2_batch_adapter import adapter, plan  # noqa: F401


@pytest.mark.parametrize("uid", ["0", "1271", "4294967294", "4294967295"])
def test_exact_cancelled_uid_remains_cancelled(uid):
    text = f"2208459.0|CANCELLED by {uid}|0:9|4\n"
    assert a.accounting(text, "2208459") == {
        "2208459.0": {"state": "CANCELLED", "exit_code": "0:9", "elapsed_seconds": 4}
    }


@pytest.mark.parametrize("state", sorted(a.TERMINAL | {"RUNNING", "PENDING", "COMPLETING"}))
def test_canonical_state_unchanged(state):
    assert a.accounting_state(state) == state


@pytest.mark.parametrize(
    "state",
    [
        "CANCELLED+",
        "COMPLETED+",
        "CANCELLED by",
        "CANCELLED by -1",
        "CANCELLED by 01",
        "CANCELLED by 4294967296",
        "CANCELLED by 99999999999",
        "CANCELLED by ١٢",
        "CANCELLED by user",
        "CANCELLED by 1271 extra",
        "CANCELLED by 1271\n",
        "CANCELLED  by 1271",
        "CANCELLED by  1271",
        "COMPLETED by 1271",
        "FAILED by 1271",
        "cancelled by 1271",
        " CANCELLED",
        "CANCELLED ",
        "",
        None,
        1,
    ],
)
def test_unknown_suffix_truncation_and_bad_uid_rejected(state):
    with pytest.raises(ValueError, match="state grammar"):
        a.accounting_state(state)


def test_actual_reported_four_rows():
    rows = a.accounting(
        "2208459|COMPLETED|0:0|20\n2208459.batch|COMPLETED|0:0|20\n"
        "2208459.extern|COMPLETED|0:0|20\n2208459.0|CANCELLED by 1271|0:9|4\n",
        "2208459",
    )
    assert rows["2208459"]["state"] == "COMPLETED"
    assert rows["2208459.0"]["state"] == "CANCELLED"
    assert rows["2208459.0"]["exit_code"] == "0:9"


def test_cancelled_metadata_does_not_fault_controller_observation(adapter):  # noqa: F811
    adapter.launch()
    adapter.handshake()
    original = adapter.transport.command

    def command(argv, **kwargs):
        if argv[0].endswith("/sacct"):
            assert "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw" in argv
            return "500000|RUNNING|0:0|20\n500000.7|CANCELLED by 1271|0:9|4\n"
        return original(argv, **kwargs)

    adapter.transport.command = command
    adapter.test_clock[0] = 2
    adapter.tick()
    assert adapter.samples[-1]["fault"] is False


def test_snapshot_keeps_raw_bytes_missing_products_and_excludes_other_files(tmp_path):
    claim, run = tmp_path / "claim", tmp_path / "run"
    claim.mkdir()
    run.mkdir()
    (claim / "batch-outcome.json").write_bytes(b'{"raw": 1}\r\n')
    (run / "attempt.json").write_bytes(b'{"failed":true}\n')
    (run / "secret.lic").write_bytes(b"must-not-export")
    records, missing = r.snapshot(claim, run)
    assert records == {
        "claim/batch-outcome.json": b'{"raw": 1}\r\n',
        "run/attempt.json": b'{"failed":true}\n',
    }
    assert "run/worker/terminal.json" in missing
    assert "secret.lic" not in str(records)


def test_snapshot_size_bound(tmp_path, monkeypatch):
    (tmp_path / "attempt.json").write_bytes(b"1234")
    monkeypatch.setattr(r, "LIMIT", 3)
    with pytest.raises(ValueError, match="bound"):
        r.snapshot(tmp_path, tmp_path)


def test_archive_byte_replay_checksum_and_exclusive_output(tmp_path):
    records = {"accounting.txt": b"CANCELLED by 1271\r\n", "run/attempt.json": b"{}\n"}
    target, checksum = r.pack(tmp_path, records)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == checksum
    assert Path(str(target) + ".sha256").read_text() == checksum + "  " + target.name + "\n"
    with tarfile.open(target) as archive:
        assert {m.name: archive.extractfile(m).read() for m in archive} == records
    with pytest.raises(FileExistsError):
        r.pack(tmp_path, records)


@pytest.mark.parametrize("name", ["../secret", "/absolute", "run/../../secret"])
def test_unsafe_archive_member_rejected(tmp_path, name):
    with pytest.raises(ValueError):
        r.pack(tmp_path, {name: b"x"})


@pytest.mark.parametrize("action", ["start", "worker", "batch", "retry", "adverse", "h300"])
def test_cli_has_no_execution_route(action):
    result = subprocess.run(
        [sys.executable, "-B", "-I", r.__file__, action], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 2 and "usage:" in result.stderr


@pytest.fixture
def recovery(tmp_path, monkeypatch):
    claim, run = tmp_path / "claim", tmp_path / "run"
    claim.mkdir()
    run.mkdir()
    (run / "attempt.json").write_bytes(b'{"status":"blocked"}\n')
    monkeypatch.setattr(r.n, "require_host", lambda: None)
    monkeypatch.setattr(r.d, "source_files", lambda *args: {"reader": "a" * 64})
    monkeypatch.setattr(r.y, "claim_path", lambda: claim)
    monkeypatch.setattr(r.o, "BASE", str(tmp_path))
    spec = {
        "run": str(run),
        "tools": {"sacct": "/fixed/sacct"},
        "tools_sha256": {"sacct": "a" * 64},
    }
    monkeypatch.setattr(r, "bound_release", lambda _: {"plan": {"specification": spec}})
    original = r.a.sha_file
    monkeypatch.setattr(
        r.a,
        "sha_file",
        lambda path, *args: "a" * 64 if str(path) == "/fixed/sacct" else original(path, *args),
    )
    calls = []

    class Transport:
        def __init__(self, _):
            pass

        def command(self, argv):
            calls.append(argv)
            assert argv == (
                "/fixed/sacct",
                "--noheader",
                "--parsable2",
                "--jobs=2208459",
                "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
            )
            return (
                "2208459|COMPLETED|0:0|20\n2208459.batch|COMPLETED|0:0|20\n"
                "2208459.0|CANCELLED by 1271|0:9|4\n"
            )

    monkeypatch.setattr(r.a, "RealTransport", Transport)
    return claim, run, calls


def test_semantic_rejection_still_exports_raw_negative_evidence(recovery, monkeypatch):
    claim, run, calls = recovery

    def reject(*args):
        raise ValueError("private exception text must not leak")

    monkeypatch.setattr(r.x, "collect_components", reject)
    result = r.collect("b" * 40)
    assert result["status"] == "captured_not_live_qualified"
    assert result["semantic_review"] is None and result["replay_error_kind"] == "ValueError"
    assert len(calls) == 1 and list(claim.iterdir()) == []
    assert (run / "attempt.json").read_bytes() == b'{"status":"blocked"}\n'
    target = next(claim.parent.glob("s2-node-recovery-*/s2-node-accounting*.tar.gz"))
    with tarfile.open(target) as archive:
        assert b"CANCELLED by 1271" in archive.extractfile("accounting.txt").read()
        manifest = json.loads(archive.extractfile("recovery.json").read())
        assert manifest == result and "private exception" not in str(manifest)


def test_evidence_drift_blocks_publication(recovery, monkeypatch):
    claim, run, _ = recovery

    def drift(*args):
        (run / "attempt.json").write_bytes(b"changed")
        raise ValueError("changed")

    monkeypatch.setattr(r.x, "collect_components", drift)
    with pytest.raises(ValueError, match="changed during"):
        r.collect("b" * 40)
    assert not list(claim.parent.glob("s2-node-recovery-*/*.tar.gz"))


def test_pending_accounting_never_creates_output(recovery, monkeypatch):
    claim, _, _ = recovery
    monkeypatch.setattr(r.a.RealTransport, "command", lambda *args: "2208459|RUNNING|0:0|2\n")
    with pytest.raises(ValueError, match="pending/nonterminal"):
        r.collect("b" * 40)
    assert not list(claim.parent.glob("s2-node-recovery-*"))


@pytest.mark.parametrize(
    "failure,stage", [("launch", "launch"), ("handshake", "handshake"), ("tick", "observe")]
)
def test_supervisor_failure_has_bounded_diagnostic_after_cleanup(tmp_path, failure, stage):
    latch = r.o.StopLatch()
    subject = operational.Adapter(tmp_path, latch, failure)
    result = r.o.supervise_normal_components(subject, latch, sleep=lambda _: None)
    diagnostic = json.loads((subject.root / "operation-diagnostic.json").read_bytes())
    assert diagnostic["stage"] == stage
    assert diagnostic["diagnostic"]["error_kind"] == "os_error"
    assert "private failure" not in str(diagnostic)
    assert subject.handle.process.killed == 1
    assert result["operation"]["reason"] == "adapter_failure_unknown_effect"
    assert result["operation"]["remote_cleanup_proven"] is False


@pytest.mark.parametrize(
    "tamper", [None, "proposal", "intent", "submission", "script", "release", "job", "source"]
)
def test_bound_reader_keeps_execution_identity(monkeypatch, tamper):
    # Fixed NPAD paths are data in this offline test, not local filesystem targets.
    monkeypatch.setattr(r.q, "_safe_path", lambda _: None)
    proposal = node.proposal.__wrapped__(monkeypatch)
    proposal["envelope"]["checkout"] = r.o.BASE + "/s2-node-driver-test/source"
    proposal["plan"] = r.o.normal_plan(
        proposal["envelope"],
        r.s.digest(proposal["envelope"]),
        "a" * 40,
        run=r.o.BASE + "/s2n-12345678",
        nonce="f" * 64,
        job_id="1",
    )
    digest = r.s.digest(proposal)
    release = r.y.derive_release(proposal, "a" * 40, digest, r.JOB)
    monkeypatch.setattr(r, "SOURCE", "a" * 40)
    monkeypatch.setattr(r, "PROPOSAL", digest)
    monkeypatch.setattr(r, "RELEASE", r.s.digest(release))
    claim = Path(r.o.BASE) / r.y.CLAIM
    monkeypatch.setattr(r.y, "claim_path", lambda: claim)
    records = {
        "proposal.json": proposal,
        "intent.json": {"source_commit": r.SOURCE, "proposal_sha256": digest, **r.n.FUTURE},
        "submission-intent.json": r.y.submission_record(proposal, digest),
        "release.json": release,
        "job.json": {
            "source_commit": r.SOURCE,
            "job_id": r.JOB,
            "release_sha256": r.RELEASE,
            "specification_sha256": r.s.digest(release["plan"]["specification"]),
        },
    }
    script = r.y.batch_script(proposal, digest)
    names = {
        "proposal": "proposal.json",
        "intent": "intent.json",
        "submission": "submission-intent.json",
        "release": "release.json",
        "job": "job.json",
    }
    if tamper in names:
        records[names[tamper]] = {"drift": True}
    original_json, original_file = r.n.read_json, r.a._file
    monkeypatch.setattr(
        r.n,
        "read_json",
        lambda path, *args: (
            records[Path(path).name] if Path(path).parent == claim else original_json(path, *args)
        ),
    )
    monkeypatch.setattr(
        r.a,
        "_file",
        lambda path, *args: (
            (b"drift" if tamper == "script" else script)
            if Path(path) == claim / "batch.sh"
            else original_file(path, *args)
        ),
    )
    calls = []

    def source(*args):
        calls.append(args)
        if tamper == "source":
            raise ValueError("sealed source drift")

    monkeypatch.setattr(r.identity, "verify_compute_source", source)
    monkeypatch.setattr(r.y, "local_entry", lambda *args: pytest.fail("historical execution"))
    if tamper:
        with pytest.raises((ValueError, KeyError)):
            r.bound_release(claim)
    else:
        assert r.bound_release(claim) == release
        assert calls[0][2:] == (r.SOURCE, r.s.digest(release["manifest"]))
