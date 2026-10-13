"""Recovery-bound normal gate qualification, with no live scheduler effects."""

import copy
import hashlib
from pathlib import Path

import pytest

from scripts import mvp2_h300_controls as c
from scripts import mvp2_s2_step_normal as gate
from scripts import mvp2_s2_step_predecessor as p
from tests.test_mvp2_s2_step_normal import proposal  # noqa: F401


@pytest.fixture
def carrier(tmp_path, monkeypatch):
    monkeypatch.setattr(p.o, "BASE", str(tmp_path))
    destination = tmp_path / "s2-node-recovery-2208459-test"
    destination.mkdir()
    original = {"claim/slurm-2208459.err": b"", "run/attempt.json": b'{"status":"blocked_unbound"}'}
    records = {
        **original,
        "accounting.txt": b"2208459.0|CANCELLED by 1271|0:9|4\n",
        "replay/s2-node-normal-evidence.tar.gz": b"frozen replay fixture",
    }
    missing = ["run/contract.json"]
    manifest = {
        "job_id": p.recovery.JOB,
        "release_sha256": p.recovery.RELEASE,
        "execution_source": p.recovery.SOURCE,
        "status": "captured_not_live_qualified",
        "missing": missing,
        "files": {
            k: {"bytes": len(v), "sha256": hashlib.sha256(v).hexdigest()}
            for k, v in records.items()
        },
    }
    records["recovery.json"] = c.encoded(manifest)
    path, checksum = p.recovery.pack(destination, records)
    monkeypatch.setitem(p.RECOVERY, "archive_sha256", checksum)
    monkeypatch.setitem(
        p.RECOVERY,
        "replay_sha256",
        hashlib.sha256(records["replay/s2-node-normal-evidence.tar.gz"]).hexdigest(),
    )
    old = {"plan": {"specification": {"run": str(tmp_path / "old-run")}}}
    monkeypatch.setattr(p.recovery, "bound_release", lambda _: copy.deepcopy(old))
    monkeypatch.setattr(
        p.recovery, "snapshot", lambda *args: (copy.deepcopy(original), list(missing))
    )
    return path, old, original, missing


def test_real_archive_reader_preserves_empty_stderr_and_negative_originals(carrier):
    path, old, original, _ = carrier
    before = path.read_bytes()
    record = p.discover_reference()
    assert p.verify_reference(record) == old
    records, manifest = p.read_recovery(path)
    assert records["claim/slurm-2208459.err"] == b""
    assert records["run/attempt.json"] == original["run/attempt.json"]
    assert manifest["status"] == "captured_not_live_qualified" and path.read_bytes() == before


@pytest.mark.parametrize("kind", ["checksum", "changed", "missing", "new_product", "replay"])
def test_carrier_or_original_drift_blocks(carrier, monkeypatch, kind):
    path, _, original, missing = carrier
    record = {"identity": copy.deepcopy(p.RECOVERY), "archive": str(path)}
    if kind == "checksum":
        path.write_bytes(b"bad")
    elif kind == "changed":
        original["run/attempt.json"] = b"different"
    elif kind == "missing":
        missing.append("run/worker/terminal.json")
    elif kind == "new_product":
        original["run/contract.json"] = b"{}"
    else:
        monkeypatch.setitem(p.RECOVERY, "replay_sha256", "0" * 64)
        record["identity"] = copy.deepcopy(p.RECOVERY)
    with pytest.raises(ValueError):
        p.verify_reference(record)


@pytest.mark.parametrize("count", [0, 2])
def test_absent_or_ambiguous_reference_is_not_guessed(tmp_path, monkeypatch, count):
    monkeypatch.setattr(p.o, "BASE", str(tmp_path))
    for i in range(count):
        folder = tmp_path / f"s2-node-recovery-2208459-{i}"
        folder.mkdir()
        (folder / p.NAME).write_bytes(b"x")
    monkeypatch.setattr(p, "verify_reference", lambda _: pytest.fail("Must not choose a carrier"))
    with pytest.raises(ValueError, match="Expected one"):
        p.discover_reference()


@pytest.mark.parametrize(
    "field", ["job_id", "source_commit", "release_sha256", "archive_sha256", "replay_sha256"]
)
def test_frozen_reference_identity_fields(field):
    record = {
        "identity": copy.deepcopy(p.RECOVERY),
        "archive": str(Path(p.o.BASE) / "s2-node-recovery-2208459-test" / p.NAME),
    }
    record["identity"][field] = "wrong"
    with pytest.raises(ValueError, match="identity"):
        p.validate_reference(record)


@pytest.mark.parametrize(
    "path", ["/tmp/carrier.tar.gz", "/outside/s2-node-recovery-2208459-x/" + p.NAME]
)
def test_reference_location_is_bounded(path):
    with pytest.raises(ValueError, match="location"):
        p.validate_reference({"identity": p.RECOVERY, "archive": path})


def test_release_dispatch_and_distinct_claim(proposal):  # noqa: F811
    assert p.x.validate_release(proposal, "a" * 40, p.s.digest(proposal)) == proposal
    assert p.x.release_claim(proposal) == gate.CLAIM != p.recovery.y.CLAIM
    broken = copy.deepcopy(proposal)
    broken["recovery"]["identity"]["job_id"] = "1"
    with pytest.raises(ValueError):
        p.x.validate_release(broken, "a" * 40, p.s.digest(broken))


@pytest.mark.parametrize("role", ["batch", "worker"])
def test_compute_rechecks_recovery_without_git_or_scheduler(proposal, monkeypatch, role):  # noqa: F811
    release = gate.derive_release(proposal, "a" * 40, p.s.digest(proposal), "500000")
    checksums = {
        path: sha for entry in release["history"] for path, sha in entry["records"].items()
    }
    checksums.update(
        {entry["archive"]: entry["identity"]["archive_sha256"] for entry in release["history"]}
    )
    calls = []
    monkeypatch.setattr(p.a, "sha_file", lambda path, *args: checksums[path])
    monkeypatch.setattr(p.node, "verify_diagnostic", lambda _: calls.append("diagnostic"))

    def verify(record):
        assert record == release["recovery"]
        calls.append("recovery")
        return {
            "plan": {
                "specification": {
                    "source_commit": p.recovery.SOURCE,
                    "job_id": p.recovery.JOB,
                    "run": "/old-run",
                    "checkout": "/old-source",
                }
            }
        }

    monkeypatch.setattr(p, "verify_reference", verify)
    monkeypatch.setattr(p.x.identity, "verify_historical_source", lambda *args: None)
    monkeypatch.setattr(p.x.identity, "verify_compute_source", lambda *args: {"source": True})
    monkeypatch.setattr(p.x.identity, "verify_compute_runtime", lambda spec, role: {"role": role})
    assert p.x.verify_release(
        release, "a" * 40, p.s.digest(release), role=role, deadline=10, clock=lambda: 0
    )[2] == {"role": role}
    assert calls == ["diagnostic", "recovery"]


@pytest.mark.parametrize("stage", ["launch", "handshake", "observe"])
def test_operation_diagnostic_is_exportable_and_strict(stage):
    item = {
        "schema_version": "s2-operation-diagnostic-v1",
        "specification_sha256": "a" * 64,
        "stage": stage,
        "diagnostic": gate.n.batch_diagnostic("supervise", ValueError()),
        **p.o.FLAGS,
    }
    gate.review_diagnostic(item, "a" * 64)
    item["diagnostic"]["message"] = "private path or environment"
    with pytest.raises(ValueError):
        gate.review_diagnostic(item, "a" * 64)


def test_portable_anchor_keeps_diagnostic_without_admission(proposal, tmp_path, monkeypatch):  # noqa: F811
    release = gate.derive_release(proposal, "a" * 40, p.s.digest(proposal), "500000")
    original_spec = copy.deepcopy(release["plan"]["specification"])
    runtime = {
        role: gate.identity.expected_compute_runtime(original_spec, role)
        for role in ("batch", "worker")
    }
    monkeypatch.setattr(gate.identity, "expected_compute_runtime", lambda spec, role: runtime[role])
    release["plan"]["specification"]["run"] = str(tmp_path)
    spec_hash = p.s.digest(release["plan"]["specification"])
    item = {
        "schema_version": "s2-operation-diagnostic-v1",
        "specification_sha256": spec_hash,
        "stage": "handshake",
        "diagnostic": gate.n.batch_diagnostic("supervise", ValueError()),
        **p.o.FLAGS,
    }
    c.write_once(tmp_path / "operation-diagnostic.json", item)
    anchor = gate.anchor(release, p.s.digest(release), None)
    assert anchor["operation_diagnostic"] == item
    assert all(anchor[k] is False for k in gate.n.FUTURE)
