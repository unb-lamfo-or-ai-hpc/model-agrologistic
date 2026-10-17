"""Public operational release with synthetic predecessors; never NPAD/native effects."""

import copy
import gzip
import io
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from scripts import mvp2_s2_p4_release as q
from tests.test_mvp2_s2_h300_runtime import block_fixture, command_result
from tests.test_mvp2_s2_p4_admission import accounting
from tests.test_mvp2_s2_p4_observation import complete

SOURCE = "c" * 40


def fixture(tmp_path, monkeypatch):
    old = complete(tmp_path, monkeypatch)
    receipt = q.o.collect("b" * 40, command=lambda *a, **k: command_result(accounting()))
    monkeypatch.setattr(q, "BASE", tmp_path)
    monkeypatch.setattr(
        q,
        "OBS",
        {
            "source": "b" * 40,
            "job": "123",
            "archive": receipt["sha256"],
            "plan": receipt["driver_plan_sha256"],
        },
    )
    value = copy.deepcopy(old["p4_plan"])
    value["preparation"] = q.r.entry.preparation(
        SOURCE,
        q.d.digest(value["runtime"]),
        q.d.digest(value["input"]),
        q.d.digest(value["protected"]),
    )
    assert q.predecessor(Path(receipt["download"])) == old["p4_plan"]
    return value


def submit(tmp_path, monkeypatch, *, reply="456\n"):
    value = fixture(tmp_path, monkeypatch)
    calls = []

    def command(argv, **kwargs):
        assert kwargs == {"timeout": 30, "limit": 1024}
        assert (q.directory() / "submission-intent.json").exists()
        calls.append(argv)
        return command_result(reply)

    result = q.start(SOURCE, acknowledged=True, planner=lambda *a: value, command=command)
    return value, result, calls


def test_exact_one_slot_and_no_repeated_predecessors(tmp_path, monkeypatch):
    value, result, calls = submit(tmp_path, monkeypatch)
    assert len(calls) == 1 and result["job_id"] == "456"
    for flag in (
        "--cpus-per-task=16",
        "--mem=196608M",
        "--time=06:00:00",
        "--no-requeue",
        "--export=NONE",
        "--account=sxdsouza",
        "--nodes=1",
        "--ntasks=1",
    ):
        assert flag in calls[0]
    assert not any("exclusive" in x for x in calls[0])
    assert all(result[k] is False for k in q.FLAGS)
    assert value["h300_execution_admitted"] is False  # Legacy certificate remains closed.
    assert "mvp2_s2_p4_release import batch" in (q.directory() / "batch.sh").read_text()
    resumed = q.start(SOURCE, acknowledged=True, command=lambda *a, **k: pytest.fail("repeat"))
    assert resumed["status"] == "existing_job_collect_only"


def test_ack_required_before_any_effect(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "BASE", tmp_path)
    with pytest.raises(ValueError, match="acknowledgement"):
        q.start(SOURCE)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("reply", ["", "warning\n456\n", "0\n", "456 unexpected\n"])
def test_ambiguous_ack_consumes_claim(tmp_path, monkeypatch, reply):
    with pytest.raises(ValueError, match="Unknown submission"):
        submit(tmp_path, monkeypatch, reply=reply)
    with pytest.raises(ValueError, match="Consumed slot"):
        q.start(SOURCE, acknowledged=True, command=lambda *a, **k: pytest.fail("retry"))
    assert not (q.directory() / "job.json").exists()


@pytest.mark.parametrize("field", ["runtime", "input", "protected"])
def test_observed_identity_drift_never_creates_claim(tmp_path, monkeypatch, field):
    value = fixture(tmp_path, monkeypatch)
    value[field]["unexpected"] = "drift"
    # Maintain its internal digest so this tests external predecessor binding.
    digest_key = {
        "runtime": "runtime_sha256",
        "input": "input_sha256",
        "protected": "protected_source_sha256",
    }[field]
    value["preparation"][digest_key] = q.d.digest(value[field])
    with pytest.raises(ValueError):
        q.start(
            SOURCE,
            acknowledged=True,
            planner=lambda *a: value,
            command=lambda *a, **k: pytest.fail("submit"),
        )
    assert not q.directory().exists()


def test_predecessor_missing_no_effect(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "BASE", tmp_path)
    with pytest.raises(FileNotFoundError):
        q.start(SOURCE, acknowledged=True, planner=lambda *a: pytest.fail("planner"))
    assert not q.directory().exists()


def test_source_drift_resume_denied(tmp_path, monkeypatch):
    submit(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="Release/source"):
        q.start("d" * 40, acknowledged=True)


@pytest.mark.parametrize("stage", ["origin", "verify", "execute", "success"])
def test_batch_dispatch_failures_preserved_without_repeat(tmp_path, monkeypatch, stage):
    submit(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(os, "getuid", lambda: 1271, raising=False)
    if stage == "origin":
        (q.directory() / "origin.json").write_text("{}")

    def verify(*a):
        if stage == "verify":
            raise ValueError("source")

    def execute(target):
        assert all(os.environ[k] == "1" for k in q.r.ENVIRONMENT)
        if stage == "execute":
            raise ValueError("early batch")
        return {"arms": [None] * 5, "unrun": [], "stop_reason": None}

    result = q.batch(q.directory(), SOURCE, execute=execute, verify=verify)
    assert result == (0 if stage == "success" else 2)
    receipt = q.p.read(q.directory() / "driver-outcome.json")
    assert receipt["status"] == (
        "block_returned" if stage == "success" else "blocked_or_interrupted"
    )
    with pytest.raises(FileExistsError):
        q.batch(q.directory(), SOURCE, execute=execute, verify=verify)


def closed_block(tmp_path, monkeypatch, stop):
    # Reuse the real five-arm native/export/control/review fixture; no solver/Slurm.
    pred = tmp_path / "predecessor"
    pred.mkdir()
    fixture(pred, monkeypatch)
    predecessor_path = pred / q.o.CLAIM / "s2-p4-observation-evidence.tar.gz"
    target, value, batch, command, recheck = block_fixture(tmp_path, monkeypatch, stop_index=stop)
    old = q.predecessor(predecessor_path)
    # Fixture's native solver uses a minimal input. Explicit external metadata
    # doubles here isolate carrier qualification from private workbook access.
    monkeypatch.setattr(q, "predecessor", lambda path: old)
    old.update({key: value[key] for key in ("runtime", "input", "protected")})
    monkeypatch.setattr(q, "BASE", tmp_path)
    observation = tmp_path / q.o.CLAIM
    observation.mkdir()
    (observation / "s2-p4-observation-evidence.tar.gz").write_bytes(predecessor_path.read_bytes())
    # The minimal native fixture has no real source transport. Keep its existing
    # hash-bound receipts, while the other fixture exercises actual predecessor
    # and transport pins separately.
    monkeypatch.setattr(q.o.a, "TRANSPORT", {})
    sealed = q.release(value)
    q.p.publish(target / "release.json", sealed)
    report = q.r._collect(target, q.d.digest(value), "123", command=command, recheck=recheck)
    return target, value, sealed, report, command, recheck


@pytest.mark.parametrize("stop", [None, 0, 2, 4])
def test_complete_and_partial_block_bundle_roundtrip(tmp_path, monkeypatch, stop):
    target, value, sealed, report, command, recheck = closed_block(tmp_path, monkeypatch, stop)
    result = q.bundle(target, sealed, report)
    assert result["reported_native_status"] == (
        "five_arms_accounted_not_s2_closure" if stop is None else "forensic_partial_block"
    )
    assert all(result[k] is False for k in q.FLAGS)
    assert result["fresh_private_input_revalidated_by_portable_auditor"] is False
    assert q.audit(
        result["download"],
        result["sha256"],
        value["preparation"]["source_commit"],
        q.d.digest(sealed),
        "123",
    ) == q.summary(sealed, report)
    assert q.bundle(target, sealed, report) == result
    assert (
        q.collect(value["preparation"]["source_commit"], command=command, recheck=recheck) == result
    )


@pytest.mark.parametrize("field", ["sha256", "source", "release", "job"])
def test_external_anchor_drift(tmp_path, monkeypatch, field):
    target, value, sealed, report, _, _ = closed_block(tmp_path, monkeypatch, None)
    result = q.bundle(target, sealed, report)
    anchors = [result["sha256"], value["preparation"]["source_commit"], q.d.digest(sealed), "123"]
    anchors[{"sha256": 0, "source": 1, "release": 2, "job": 3}[field]] = (
        "d" * (40 if field == "source" else 64) if field != "job" else "999"
    )
    with pytest.raises(ValueError):
        q.audit(result["download"], *anchors)


@pytest.mark.parametrize("kind", ["extra", "duplicate", "link", "missing", "tail", "nan"])
def test_hostile_outer_carriers_rejected(tmp_path, monkeypatch, kind):
    target, value, sealed, report, _, _ = closed_block(tmp_path, monkeypatch, 0)
    result = q.bundle(target, sealed, report)
    with tarfile.open(result["download"], "r:gz") as stream:
        files = [(x.name, stream.extractfile(x).read()) for x in stream]
    if kind == "extra":
        files.append(("../escape", b"x"))
    elif kind == "duplicate":
        files.append(files[0])
    elif kind == "missing":
        files.pop()
    elif kind == "nan":
        files = [(name, b'{"bad":NaN}' if name == "release.json" else raw) for name, raw in files]
    archive = tmp_path / "bad.tar.gz"
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:", format=tarfile.USTAR_FORMAT) as stream:
        for index, (name, raw) in enumerate(files):
            item = tarfile.TarInfo(name)
            item.size = len(raw)
            if kind == "link" and index == 0:
                item.type, item.linkname, item.size = tarfile.SYMTYPE, "../escape", 0
            stream.addfile(item, io.BytesIO(raw))
    archive.write_bytes(gzip.compress(output.getvalue() + (b"bad" if kind == "tail" else b"")))
    with pytest.raises(ValueError):
        q.audit(
            archive,
            q.p.sha_file(archive),
            value["preparation"]["source_commit"],
            q.d.digest(sealed),
            "123",
        )


@pytest.mark.parametrize("action", ["repeat", "worker"])
def test_public_repeat_worker_stay_denied(action):
    with pytest.raises(PermissionError):
        q.main([action, SOURCE])


def test_early_batch_failure_real_predecessor_and_forensic_collection(tmp_path, monkeypatch):
    value, _, _ = submit(tmp_path, monkeypatch)

    # The worker was never observed, so these are UNACCOUNTED, not known unrun.
    def command(argv, **kwargs):
        return command_result(
            "456|FAILED|2:0|4\n456.batch|FAILED|2:0|4\n456.extern|COMPLETED|0:0|4\n"
        )

    result = q.collect(SOURCE, command=command, recheck=lambda *a: (None, None))
    assert result["reported_native_status"] == "forensic_partial_block"
    assert result["unaccounted"] == list(q.d.ORDER) and result["unrun"] == []
    assert result["driver"] == {"outcome": None}
    assert q.audit(
        result["download"], result["sha256"], SOURCE, result["release_sha256"], "456"
    ) == q.summary(q.release(value), q.p.read(q.directory() / "review.json"))


@pytest.mark.parametrize("field", ["order", "scope", "repeats_admitted", "native_plan_sha256"])
def test_release_field_drift_denies_before_collection(tmp_path, monkeypatch, field):
    submit(tmp_path, monkeypatch)
    path = q.directory() / "release.json"
    value = q.p.read(path)
    value[field] = "changed"
    path.write_bytes(q.c.encoded(value))
    with pytest.raises(ValueError, match="Release/source drift"):
        q.collect(SOURCE, command=lambda *a, **k: pytest.fail("scheduler"))


def test_outer_export_budget_does_not_truncate_or_replace_native(tmp_path, monkeypatch):
    target, _, sealed, report, _, _ = closed_block(tmp_path, monkeypatch, 0)
    original = (target / "s2-h300-academic-evidence.tar.gz").read_bytes()
    q.p.publish(target / "portable-driver.json", {"outcome": None})
    q.p.publish(target / "portable-review.json", q.summary(sealed, report))
    monkeypatch.setattr(q.p, "LIMIT", 1024)
    with pytest.raises(ValueError, match="export bound"):
        q.bundle(target, sealed, report)
    assert (target / "s2-h300-academic-evidence.tar.gz").read_bytes() == original
    assert not (target / q.ARCHIVE).exists()


@pytest.mark.skipif(
    sys.platform != "linux", reason="Actual Bash wrapper gate; no cluster or solver"
)
@pytest.mark.parametrize("action", ["status", "collect", "wait"])
def test_real_wrapper_absent_claim_has_no_effect(tmp_path, action):
    script = (Path(q.__file__).parent / "npad_s2_p4_release.sh").read_text()
    script = script.replace(str(q.BASE), str(tmp_path))
    target = tmp_path / "wrapper.sh"
    target.write_text(script)
    output = subprocess.run(["bash", str(target), action, SOURCE], capture_output=True, text=True)
    assert output.returncode == 2 and "not_submitted" in output.stderr
    assert list(tmp_path.iterdir()) == [target]
