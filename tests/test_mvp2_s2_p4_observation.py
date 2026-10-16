"""Complete human observation wrapper and forensic gate; no cluster/native access."""

import ast
import gzip
import io
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from scripts import mvp2_s2_p4_observation as o
from tests.test_mvp2_s2_h300_runtime import command_result as scheduler_result
from tests.test_mvp2_s2_p4_admission import accounting, plan, records

SOURCE = "b" * 40


def command_result(raw):
    return scheduler_result(raw.decode())


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(o, "BASE", tmp_path)
    value = plan()

    def prepare(path, commit, p3, reference):
        assert commit == SOURCE and path == tmp_path / o.a.CLAIM
        assert not (tmp_path / o.CLAIM).exists()
        path.mkdir()
        o.a.p.publish(path / "plan.json", value)

    return value, prepare


def submitted(tmp_path, monkeypatch, *, reply=b"123\n"):
    value, prepare = fixture(tmp_path, monkeypatch)
    calls = []

    def command(argv, **kwargs):
        calls.append(argv)
        assert (tmp_path / o.CLAIM / "submission-intent.json").is_file()
        assert kwargs == {"timeout": 30, "limit": 1024}
        return command_result(reply)

    result = o.start(SOURCE, acknowledged=True, prepare=prepare, command=command)
    return value, result, calls


def complete(tmp_path, monkeypatch, *, outcome=True, worker=True):
    value, _, _ = submitted(tmp_path, monkeypatch)
    target, driver, _ = o.load(tmp_path / o.CLAIM, SOURCE)
    if outcome:
        o.a.p.publish(
            target / "batch-outcome.json",
            {
                "status": "observation_returned",
                "phase": "complete",
                "error_kind": None,
                "job_id": "123",
                "driver_plan_sha256": o.a.d.digest(driver),
                **o.a.FLAGS,
            },
        )
    if worker:
        record = tmp_path / o.a.CLAIM
        o.a.p.publish(
            record / "job.json", {"job_id": "123", "admission_plan_sha256": o.a.d.digest(value)}
        )
        for name, data in records(value).items():
            o.a.p.publish(record / name, data)
    return value


@pytest.mark.parametrize("action", ["solve", "worker", "repeat", "h300"])
def test_agricultural_routes_always_deny(action, monkeypatch):
    monkeypatch.setattr(o, "start", lambda *a, **k: pytest.fail("start reached"))
    with pytest.raises(PermissionError):
        o.main([action, SOURCE])


def test_no_agricultural_dispatch_or_srun_scancel():
    tree = ast.parse(Path(o.__file__).read_text())
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not attributes & {"_submit", "_native", "_arm", "_worker", "_dispatch"}
    literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert not literals & {"srun", "scancel"}


def test_start_requires_ack_before_effect(tmp_path, monkeypatch):
    _, prepare = fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="reviewed observation"):
        o.start(SOURCE, prepare=prepare)
    assert not list(tmp_path.iterdir())


def test_start_exact_allocation_one_submission_and_preserve_old(tmp_path, monkeypatch):
    old = tmp_path / ".mvp2-s2-academic-v2-native_miniature"
    old.mkdir()
    (old / "evidence").write_bytes(b"original")
    _, result, calls = submitted(tmp_path, monkeypatch)
    assert result["job_id"] == "123" and len(calls) == 1
    argv = calls[0]
    assert argv[0] == "sbatch"
    for item in (
        "--cpus-per-task=16",
        "--mem=196608M",
        "--time=06:00:00",
        "--no-requeue",
        "--export=NONE",
        "--nodes=1",
        "--ntasks=1",
        "--partition=intel-256",
        "--account=sxdsouza",
    ):
        assert item in argv
    assert not any("exclusive" in x for x in argv)
    resumed = o.start(SOURCE, acknowledged=True, command=lambda *a, **k: pytest.fail("resubmit"))
    assert resumed["status"] == "existing_job_collect_only"
    assert (old / "evidence").read_bytes() == b"original"
    assert not (tmp_path / o.a.r.CLAIM).exists()


@pytest.mark.parametrize("raw", [b"", b"warning\n123\n", b"0\n", b"123 extra\n"])
def test_ambiguous_submit_consumes_slot(tmp_path, monkeypatch, raw):
    _, prepare = fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="Unknown submission"):
        o.start(
            SOURCE, acknowledged=True, prepare=prepare, command=lambda *a, **k: command_result(raw)
        )
    with pytest.raises(ValueError, match="Consumed slot"):
        o.start(SOURCE, acknowledged=True, command=lambda *a, **k: pytest.fail("retry"))
    assert (tmp_path / o.CLAIM / "submission-intent.json").exists()
    assert not (tmp_path / o.CLAIM / "job.json").exists()


def test_prepare_failure_submits_nothing(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)

    def failed(*args):
        raise ValueError("input")

    with pytest.raises(ValueError):
        o.start(
            SOURCE, acknowledged=True, prepare=failed, command=lambda *a, **k: pytest.fail("sbatch")
        )
    assert not list(tmp_path.iterdir())


def test_orphan_prerequisite_never_reused(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    (tmp_path / o.a.CLAIM).mkdir()
    with pytest.raises(ValueError, match="Existing prerequisite"):
        o.start(SOURCE, acknowledged=True)


@pytest.mark.parametrize("fault", ["none", "source", "observer"])
def test_batch_no_git_bound_observer_and_type_only_failure(tmp_path, monkeypatch, fault):
    value, _, _ = submitted(tmp_path, monkeypatch)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    calls = []

    def verify(root, files):
        calls.append("verify")
        assert files == value["p4_plan"]["files"]
        if fault == "source":
            raise OSError("PRIVATE_LICENSE_OR_PATH")

    def observe(path, digest, job, **kwargs):
        calls.append("observe")
        assert job == "123" and digest == o.a.d.digest(value)
        assert path == tmp_path / o.a.CLAIM and kwargs == {"acknowledged": True}
        assert all(os.environ[k] == "1" for k in o.a.r.ENVIRONMENT)
        if fault == "observer":
            raise RuntimeError("PRIVATE_LICENSE_OR_PATH")
        return {"status": "complete", "local_client_reaped": True}

    target = tmp_path / o.CLAIM
    rc = o.batch(target, SOURCE, observer=observe, verify=verify)
    outcome = o.a.p.read(target / "batch-outcome.json")
    assert rc == (0 if fault == "none" else 2)
    assert "PRIVATE" not in (target / "batch-outcome.json").read_text()
    assert outcome["h300_execution_admitted"] is False
    assert calls == (["verify"] if fault == "source" else ["verify", "observe"])
    with pytest.raises(FileExistsError):
        o.batch(
            target, SOURCE, observer=lambda *a, **k: pytest.fail("second observer"), verify=verify
        )


@pytest.mark.parametrize("missing", ["none", "batch", "worker", "both"])
def test_terminal_positive_and_early_failure_transfer(tmp_path, monkeypatch, missing):
    complete(
        tmp_path,
        monkeypatch,
        outcome=missing not in ("batch", "both"),
        worker=missing not in ("worker", "both"),
    )

    def command(*args, **kwargs):
        return command_result(accounting().encode())

    result = o.collect(SOURCE, command=command)
    expected = (
        "prerequisites_observed_execution_closed"
        if missing == "none"
        else "negative_or_incomplete_evidence_preserved"
    )
    assert result["status"] == expected
    archive = Path(result["download"])
    raw = archive.read_bytes()
    assert o.collect(SOURCE, command=command) == result
    assert archive.read_bytes() == raw
    assert (
        o.audit(archive, result["sha256"], SOURCE, result["driver_plan_sha256"], "123")["status"]
        == expected
    )
    with tarfile.open(archive) as stream:
        assert set(stream.getnames()) == o.MEMBERS
    assert str(tmp_path).encode() not in gzip.decompress(raw)
    assert not result["h300_execution_admitted"] and not result["repeats_admitted"]


@pytest.mark.parametrize(
    "state,code", [("FAILED", "2:0"), ("TIMEOUT", "0:9"), ("CANCELLED by 1271", "0:9")]
)
def test_terminal_failure_not_success(tmp_path, monkeypatch, state, code):
    complete(tmp_path, monkeypatch)
    result = o.collect(
        SOURCE, command=lambda *a, **k: command_result(accounting(state, code).encode())
    )
    assert result["status"] == "negative_or_incomplete_evidence_preserved"


def test_nonterminal_no_archive(tmp_path, monkeypatch):
    complete(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="not terminal"):
        o.collect(SOURCE, command=lambda *a, **k: command_result(accounting("RUNNING").encode()))
    assert not list((tmp_path / o.CLAIM).glob("*.tar.gz"))


@pytest.mark.parametrize("change", ["archive", "sidecar", "record"])
def test_cache_drift_rejected_without_replacement(tmp_path, monkeypatch, change):
    complete(tmp_path, monkeypatch)

    def command(*args, **kwargs):
        return command_result(accounting().encode())

    result = o.collect(SOURCE, command=command)
    archive = Path(result["download"])
    if change == "archive":
        damaged = archive
        damaged.write_bytes(b"changed")
    elif change == "sidecar":
        damaged = archive.with_suffix(".gz.sha256")
        damaged.write_bytes(b"changed")
    else:
        damaged = tmp_path / o.a.CLAIM / "supervision.json"
        value = o.a.p.read(damaged)
        value["elapsed_seconds"] = 9
        damaged.write_bytes(o.a.c.encoded(value))
    altered = damaged.read_bytes()
    with pytest.raises((ValueError, KeyError)):
        o.collect(SOURCE, command=command)
    assert damaged.read_bytes() == altered


@pytest.mark.parametrize("anchor", ["archive", "source", "plan", "job"])
def test_external_anchors(tmp_path, monkeypatch, anchor):
    complete(tmp_path, monkeypatch)
    result = o.collect(SOURCE, command=lambda *a, **k: command_result(accounting().encode()))
    anchors = [result["sha256"], SOURCE, result["driver_plan_sha256"], "123"]
    anchors[["archive", "source", "plan", "job"].index(anchor)] = "9" * (
        40 if anchor == "source" else 3 if anchor == "job" else 64
    )
    with pytest.raises(ValueError):
        o.audit(Path(result["download"]), *anchors)


@pytest.mark.parametrize("kind", ["link", "extra", "duplicate", "bomb"])
def test_hostile_archive_rejected(tmp_path, kind):
    archive = tmp_path / "hostile.tar.gz"
    if kind == "bomb":
        archive.write_bytes(gzip.compress(b"0" * (o.LIMIT + 1)))
    else:
        with tarfile.open(archive, "w:gz") as stream:
            item = tarfile.TarInfo("plan.json" if kind != "extra" else "../private")
            item.size = 2
            if kind == "link":
                item.type, item.linkname = tarfile.SYMTYPE, "/private"
                stream.addfile(item)
            else:
                stream.addfile(item, io.BytesIO(b"{}"))
                if kind == "duplicate":
                    stream.addfile(item, io.BytesIO(b"{}"))
    with pytest.raises(ValueError):
        o.audit(archive, o.a.p.sha_file(archive), SOURCE, "a" * 64, "123")


@pytest.mark.skipif(sys.platform != "linux", reason="Actual Bash operational semantics in Linux CI")
def test_real_wrapper_syntax_and_denials():
    script = o.ROOT / "scripts/npad_s2_p4_observation.sh"
    subprocess.run(["bash", "-n", str(script)], check=True)
    for action in ("solve", "worker", "repeat", "h300", "batch", "unknown"):
        result = subprocess.run(["bash", str(script), action, SOURCE], capture_output=True)
        assert result.returncode == 64
        assert b"Usage:" in result.stderr


def test_wrapper_preserves_raw_source_and_compute_boundary():
    raw = (o.ROOT / "scripts/npad_s2_p4_observation.sh").read_text()
    for token in (
        "core.autocrlf=false",
        "-text",
        "merge-base --is-ancestor",
        "verify",
        "PYTHONDONTWRITEBYTECODE=1",
        "-B -I",
        "-p no:cacheprovider",
        "regression.xml",
        "ACTION=collect",
    ):
        assert token in raw
    assert "pip install" not in raw and "scancel" not in raw and "srun" not in raw
