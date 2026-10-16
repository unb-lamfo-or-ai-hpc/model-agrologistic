"""Operational prerequisites with no cluster access or licensed/native solve."""

import ast
import gzip
import io
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_s2_p4_admission as a
from tests.test_mvp2_s2_h300_runtime import command_result
from tests.test_mvp2_s2_h300_runtime import plan as p4_plan


def plan():
    p4 = p4_plan()
    reviewed = a.p.read(a.ROOT / "docs/mvp2_h300_input_size_review.json")
    p4["input"].update(
        data_sha256="d" * 64,
        config_sha256="e" * 64,
        counts=reviewed["counts"],
        size=reviewed["snapshot_fields"],
    )
    p4["files"].update(a.TRANSPORT)
    p4["preparation"]["input_sha256"] = a.d.digest(p4["input"])
    return {
        "schema_version": "s2-p4-admission-plan-v1",
        "p4_head": a.P4_HEAD,
        "p4_merge": a.P4_MERGE,
        "transport": dict(a.TRANSPORT),
        "p3": dict(a.entry.P3),
        "p4_plan": p4,
        "export_budget": dict(a.EXPORT),
        "observer_seconds": 580,
        "cleanup_seconds": 20,
        **a.FLAGS,
    }


def prepared(tmp_path, monkeypatch):
    value = plan()
    target = tmp_path / a.CLAIM
    monkeypatch.setattr(
        a.p,
        "sha_file",
        lambda path: a.TRANSPORT.get(Path(path).relative_to(a.ROOT).as_posix(), "0" * 64),
    )
    a.prepare(target, "b" * 40, "p3", "private_reference", planner=lambda *args: value["p4_plan"])
    return target, value


def environment(value):
    text = (
        "JobId=123 JobState=RUNNING UserId=researcher(1271) NumNodes=1 NumCPUs=16 "
        "NumTasks=1 CPUs/Task=16 Partition=intel-256 Account=sxdsouza NodeList=r1i3n5 "
        "BatchHost=r1i3n5 MinMemoryNode=192G TRES=cpu=16,mem=192G,node=1 "
        "TimeLimit=06:00:00"
    )
    return {
        "allocation": a.r.academic.allocation(
            text, "123", 1271, {"cpus": 16, "memory_mib": 196608, "wall_seconds": 21600}
        ),
        "affinity": list(range(16)),
        "topology": [{"cpu": x} for x in range(16)],
        "runtime_sha256": a.d.digest(value["p4_plan"]["runtime"]),
        "native_thread_environment": dict.fromkeys(a.r.ENVIRONMENT),
        "exclusive_node": False,
        "production_isolation_certified": False,
    }


def records(value):
    observation = {
        "admission_plan_sha256": a.d.digest(value),
        "job_id": "123",
        "environment": environment(value),
        "license": {"status": "accepted", "gurobi_version": [13, 0, 3]},
        "input_sha256": a.d.digest(value["p4_plan"]["input"]),
        "runtime_sha256": a.d.digest(value["p4_plan"]["runtime"]),
        "export_budget": dict(a.EXPORT),
        "capability_model_variables": 2001,
        "agricultural_model_built": False,
        **a.FLAGS,
    }
    supervisor = {
        "status": "complete",
        "admission_plan_sha256": a.d.digest(value),
        "job_id": "123",
        "term_sent": False,
        "kill_sent": False,
        "local_client_reaped": True,
        "return_code": 0,
        "error_kind": None,
        "elapsed_seconds": 8,
        "global_cleanup_proven": False,
        **a.FLAGS,
    }
    return {"observation.json": observation, "supervision.json": supervisor}


def accounting(state="COMPLETED", code="0:0"):
    return "\n".join(f"{x}|{state}|{code}|8" for x in ("123", "123.batch", "123.extern"))


@pytest.mark.parametrize("action", ["start", "batch", "worker", "solve", "repeat"])
def test_public_h300_repeat_denial_before_every_effect(action, monkeypatch, tmp_path):
    monkeypatch.setattr(a.r, "_submit", lambda *a, **k: pytest.fail("h300 submission reached"))
    monkeypatch.setattr(a.r, "_native", lambda *a, **k: pytest.fail("h300 worker reached"))
    with pytest.raises(PermissionError):
        a.main([action, "--record-dir", str(tmp_path / "absent")])
    assert not list(tmp_path.iterdir())


def test_no_submission_or_agricultural_executor_references():
    module = ast.parse(Path(a.__file__).read_text())
    names = {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    assert not names & {
        "_submit",
        "_batch",
        "_dispatch",
        "_native",
        "_arm",
        "execute_native_worker",
    }
    strings = {
        node.value
        for node in ast.walk(module)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert not strings & {"sbatch", "srun", "scancel"}


@pytest.mark.parametrize(
    "change", [*a.FLAGS, "transport", "budget", "p3", "count", "source", "binary"]
)
def test_contract_drift_denied(change):
    value = plan()
    if change in a.FLAGS:
        value[change] = True
    elif change == "transport":
        value["transport"][next(iter(a.TRANSPORT))] = "0" * 64
    elif change == "budget":
        value["export_budget"]["whole_block_bytes"] += 1
    elif change == "p3":
        value["p3"]["job"] = "1"
    elif change == "count":
        value["p4_plan"]["input"]["counts"]["warehouses"] = 400
    elif change == "source":
        value["p4_plan"]["preparation"]["source_commit"] = "invalid"
    else:
        value["p4_plan"]["files"][next(iter(a.TRANSPORT))] = "0" * 64
    with pytest.raises(ValueError):
        a.validate(value)


def test_runtime_version_and_integer_lookalikes_not_approved():
    value = plan()
    value["p4_plan"]["runtime"]["python_version"] = "3.14.0"
    value["p4_plan"]["preparation"]["runtime_sha256"] = a.d.digest(value["p4_plan"]["runtime"])
    for arm in value["p4_plan"]["preparation"]["arms"]:
        arm["runtime_sha256"] = value["p4_plan"]["preparation"]["runtime_sha256"]
    with pytest.raises(ValueError):
        a.validate(value)
    value = plan()
    value["p4_plan"]["input"]["size"]["routes_oc"] = False
    value["p4_plan"]["preparation"]["input_sha256"] = a.d.digest(value["p4_plan"]["input"])
    with pytest.raises(ValueError):
        a.validate(value)


def test_preparation_once_preserves_origin_and_optimization_claim(tmp_path, monkeypatch):
    legacy = tmp_path / a.r.CLAIM
    legacy.mkdir()
    (legacy / "old.json").write_bytes(b"original")
    target, value = prepared(tmp_path, monkeypatch)
    before = {p.name: p.read_bytes() for p in target.iterdir()}
    result = a.prepare(
        target,
        "b" * 40,
        "other",
        "other",
        planner=lambda *args: pytest.fail("replayed preparation"),
    )
    assert result["status"] == "existing_record_no_new_admission"
    assert before == {p.name: p.read_bytes() for p in target.iterdir()}
    assert (legacy / "old.json").read_bytes() == b"original"
    assert not (target / "job.json").exists()


def test_bad_preparation_creates_no_record(tmp_path, monkeypatch):
    monkeypatch.setattr(a.p, "sha_file", lambda path: "0" * 64)
    with pytest.raises(ValueError):
        a.prepare(tmp_path / a.CLAIM, "b" * 40, "p3", "reference")
    assert not list(tmp_path.iterdir())


def test_record_cannot_select_old_claim_or_source_root(tmp_path):
    for path in (tmp_path / a.r.CLAIM, a.ROOT / a.CLAIM):
        with pytest.raises(ValueError):
            a.record_dir(path)


@pytest.mark.parametrize("failure", [None, "input", "allocation", "license"])
def test_worker_observes_only_reviewed_prerequisites(failure, tmp_path, monkeypatch):
    target, value = prepared(tmp_path, monkeypatch)
    a.p.publish(target / "job.json", {"job_id": "123", "admission_plan_sha256": a.d.digest(value)})
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    calls = []

    def check(*args):
        calls.append("input")
        if failure == "input":
            raise ValueError("PRIVATE PATH MUST NOT BE EXPORTED")

    def allocation(*args):
        calls.append("allocation")
        if failure == "allocation":
            raise ValueError("private scheduler details")
        return environment(value)

    def license_probe():
        calls.append("license")
        if failure == "license":
            raise ValueError("private license details")
        return {"status": "accepted", "gurobi_version": [13, 0, 3]}

    status = a._observe_worker(
        target,
        recheck=check,
        environment=allocation,
        probe=license_probe,
        close_source=lambda *args: calls.append("source_close"),
    )
    if failure:
        assert status == 2
        assert not (target / "observation.json").exists()
        assert "private" not in (target / "diagnostic.json").read_text().lower()
    else:
        assert status == 0 and calls == ["input", "allocation", "license", "source_close"]
        report = a.review(value, "123", records(value), accounting())
        assert report["status"] == "prerequisites_observed_execution_closed"
        assert not report["h300_execution_admitted"]
        assert not report["future_allocation_admitted"]
        assert not report["export_fit_established"]


def test_no_acknowledgement_before_record_or_native(monkeypatch, tmp_path):
    with pytest.raises(ValueError, match="acknowledgement"):
        a.observe(tmp_path / a.CLAIM, "0" * 64, "123")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("mode", ["normal", "failure", "term", "kill", "launch"])
def test_supervised_local_observer_and_no_repeat(mode, tmp_path, monkeypatch):
    target, value = prepared(tmp_path, monkeypatch)
    monkeypatch.setattr(a.sys, "platform", "linux")
    monkeypatch.setattr(a.os, "getuid", lambda: 1271, raising=False)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    calls, waits = [], []
    child = SimpleNamespace(returncode=None)

    def wait(**kwargs):
        waits.append(kwargs["timeout"])
        if mode in {"term", "kill"} and len(waits) <= (2 if mode == "kill" else 1):
            raise subprocess.TimeoutExpired("trusted_observer", kwargs["timeout"])
        child.returncode = 0 if mode == "normal" else 2

    child.wait = wait
    child.poll = lambda: child.returncode
    child.terminate = lambda: calls.append("term")
    child.kill = lambda: calls.append("kill")

    def popen(argv, **kwargs):
        calls.append("spawn")
        assert argv[:3] == [sys.executable, "-B", "-I"] and kwargs["shell"] is False
        if mode == "launch":
            raise OSError("private launch error")
        return child

    result = a.observe(
        target, a.d.digest(value), "123", acknowledged=True, popen=popen, clock=lambda: 0
    )
    assert (
        result["status"]
        == {
            "normal": "complete",
            "failure": "worker_failed",
            "term": "observer_timeout",
            "kill": "observer_timeout",
            "launch": "launch_failed",
        }[mode]
    )
    assert result["kill_sent"] is (mode == "kill")
    assert result["term_sent"] is (mode in {"term", "kill"})
    old = len(calls)
    assert (
        a.observe(target, a.d.digest(value), "123", acknowledged=True, popen=popen)["status"]
        == "existing_observation_collect_only"
    )
    assert len(calls) == old


@pytest.mark.parametrize(
    "change", ["job", "runtime", "input", "license", "affinity", "allocation", "fit", "flag"]
)
def test_positive_report_cannot_be_relabelled(change):
    value = plan()
    data = records(value)
    obs = data["observation.json"]
    if change == "job":
        obs["job_id"] = "124"
    elif change == "runtime":
        obs["runtime_sha256"] = "0" * 64
    elif change == "input":
        obs["input_sha256"] = "0" * 64
    elif change == "license":
        obs["license"]["status"] = "rejected"
    elif change == "affinity":
        obs["environment"]["affinity"] = [0]
    elif change == "allocation":
        obs["environment"]["allocation"]["scheduler_fields"]["TimeLimit"] = "00:12:00"
    elif change == "fit":
        obs["export_budget"]["actual_incumbent_fit"] = True
    else:
        obs["h300_execution_admitted"] = True
    with pytest.raises(ValueError):
        a.review(value, "123", data, accounting())


@pytest.mark.parametrize("kind", ["positive", "missing", "failed", "timeout"])
def test_terminal_transfer_fresh_audit_and_idempotence(kind, tmp_path, monkeypatch):
    target, value = prepared(tmp_path, monkeypatch)
    monkeypatch.undo()  # Restore real file hashing before archive production.
    digest = a.d.digest(value)
    a.p.publish(target / "job.json", {"job_id": "123", "admission_plan_sha256": digest})
    data = records(value)
    if kind == "missing":
        data = {}
    elif kind == "failed":
        data["supervision.json"]["return_code"] = 2
        data["supervision.json"]["status"] = "worker_failed"
    elif kind == "timeout":
        data["supervision.json"]["status"] = "observer_timeout"
        data["supervision.json"]["term_sent"] = True
    for name, record in data.items():
        a.p.publish(target / name, record)

    def command(*args, **kwargs):
        return command_result(accounting())

    result = a.collect(target, digest, "123", command=command)
    assert (
        a.audit(result["download"], result["sha256"], "b" * 40, digest, "123") == result["review"]
    )
    assert result["review"]["status"] == (
        "prerequisites_observed_execution_closed"
        if kind == "positive"
        else "negative_or_incomplete_evidence_preserved"
    )
    assert a.collect(target, digest, "123", command=command) == result
    for checksum, commit, external, job in [
        ("0" * 64, "b" * 40, digest, "123"),
        (result["sha256"], "c" * 40, digest, "123"),
        (result["sha256"], "b" * 40, "c" * 64, "123"),
        (result["sha256"], "b" * 40, digest, "124"),
    ]:
        with pytest.raises(ValueError):
            a.audit(result["download"], checksum, commit, external, job)
    with tarfile.open(result["download"], "r:gz") as stream:
        assert set(stream.getnames()) == a.FILES
        assert all(b"private_reference" not in stream.extractfile(x).read() for x in a.FILES)


@pytest.mark.parametrize("corruption", ["archive", "record", "sidecar"])
def test_cached_source_or_transfer_corruption_preserved(corruption, tmp_path, monkeypatch):
    target, value = prepared(tmp_path, monkeypatch)
    monkeypatch.undo()
    expected = a.d.digest(value)
    a.p.publish(target / "job.json", {"job_id": "123", "admission_plan_sha256": expected})
    for name, record in records(value).items():
        a.p.publish(target / name, record)

    def command(*args, **kwargs):
        return command_result(accounting())

    result = a.collect(target, expected, "123", command=command)
    archive = Path(result["download"])
    if corruption == "archive":
        altered = archive
        altered.write_bytes(b"corrupt")
    elif corruption == "sidecar":
        altered = archive.with_suffix(archive.suffix + ".sha256")
        altered.write_bytes(b"corrupt")
    else:
        altered = target / "supervision.json"
        value = a.p.read(altered)
        value["elapsed_seconds"] = 9
        altered.write_bytes(a.c.encoded(value))
    before = altered.read_bytes()
    with pytest.raises((ValueError, tarfile.TarError)):
        a.collect(target, expected, "123", command=command)
    assert altered.read_bytes() == before


def test_nonterminal_collection_creates_no_archive(tmp_path, monkeypatch):
    target, value = prepared(tmp_path, monkeypatch)
    a.p.publish(target / "job.json", {"job_id": "123", "admission_plan_sha256": a.d.digest(value)})
    with pytest.raises(ValueError, match="Accounting not terminal"):
        a.collect(
            target,
            a.d.digest(value),
            "123",
            command=lambda *a, **k: command_result(accounting("RUNNING")),
        )
    assert not (target / "s2-p4-admission-evidence.tar.gz").exists()


@pytest.mark.parametrize("mutation", ["duplicate", "link", "tail", "extra", "oversized"])
def test_hostile_metadata_archive(mutation, tmp_path):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:", format=tarfile.USTAR_FORMAT) as stream:
        names = (
            ["plan.json", "plan.json"]
            if mutation == "duplicate"
            else ["not-allowed" if mutation == "extra" else "plan.json"]
        )
        for name in names:
            item = tarfile.TarInfo(name)
            item.size = 2
            if mutation == "link":
                item.type = tarfile.SYMTYPE
                item.linkname = "private"
                item.size = 0
            stream.addfile(item, io.BytesIO(b"{}"))
    payload = raw.getvalue() + (b"evil" if mutation == "tail" else b"")
    if mutation == "oversized":
        payload = b"0" * (a.LIMIT + 1)
    path = tmp_path / "hostile.tar.gz"
    path.write_bytes(gzip.compress(payload))
    with pytest.raises((ValueError, KeyError)):
        a.audit(path, a.p.sha_file(path), "b" * 40, "c" * 64, "123")


@pytest.mark.skipif(sys.platform != "linux", reason="Actual Bash semantics qualified in Linux CI")
def test_real_bash_wrapper_denies_campaign_and_checks_only():
    wrapper = a.ROOT / "scripts/npad_s2_p4_admission.sh"
    env = {**os.environ, "MVP2_P4_PYTHON": sys.executable}
    subprocess.run(["bash", "-n", str(wrapper)], check=True)
    for action in ("start", "batch", "worker", "solve", "repeat"):
        result = subprocess.run(["bash", str(wrapper), action], env=env, capture_output=True)
        assert result.returncode == 2 and b"H300_AND_REPEATS_BLOCKED" in result.stderr
    result = subprocess.run(
        ["bash", str(wrapper), "check"], env=env, capture_output=True, check=True
    )
    assert b"H300_AND_REPEATS_BLOCKED" in result.stdout
