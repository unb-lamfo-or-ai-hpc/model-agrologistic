"""Slurm22.05 regression and v2 recovery; no real scheduler or native effects."""

from __future__ import annotations

import copy
import os
import sys

import pytest

from scripts import mvp2_s2_academic as a
from scripts import mvp2_s2_academic_runtime as r
from tests.test_mvp2_s2_academic import JOB, SOURCE, accounting, plan, records, scheduler_text


def legacy_text():
    # Redacted projection of the maintainer's terminal scontrol job2212000.
    # RUNNING below is a synthetic admission fixture, not a rewritten certificate.
    return (
        f"JobId={JOB} UserId=researcher(1271) JobState=RUNNING Account=sxdsouza "
        "Partition=intel-256 NodeList=r1i3n5 BatchHost=r1i3n5 NumNodes=1 NumCPUs=2 "
        "NumTasks=1 CPUs/Task=2 TRES=cpu=2,mem=2G,energy=701,node=1,billing=2 "
        "MinCPUsNode=2 MinMemoryNode=2G TimeLimit=00:12:00"
    )


def test_actual_slurm22_format_is_not_requested_tres():
    value = a.allocation(legacy_text(), JOB, 1271, r.envelope(plan()))
    assert value["requested_resource_basis"] == "CPUs/Task+MinMemoryNode"
    assert "ReqTRES" not in value["scheduler_fields"]
    assert value["allocated_tres"] == "cpu=2,mem=2G,energy=701,node=1,billing=2"


def test_terminal_capture_is_not_relabelled_running():
    with pytest.raises(ValueError, match="Allocation identity"):
        a.allocation(legacy_text().replace("RUNNING", "FAILED"), JOB, 1271, r.envelope(plan()))


@pytest.mark.parametrize("cpu,mem", [(2, 2048), (4, 16384)])
def test_legacy_synthetic_and_native_requests(cpu, mem):
    p = plan("native_miniature" if cpu == 4 else "normal")
    text = legacy_text().replace("NumCPUs=2", f"NumCPUs={cpu}")
    text = text.replace("CPUs/Task=2", f"CPUs/Task={cpu}")
    text = text.replace("cpu=2,mem=2G", f"cpu={cpu},mem={mem}M")
    text = text.replace("MinMemoryNode=2G", f"MinMemoryNode={mem}M")
    text = text.replace("00:12:00", "00:40:00" if cpu == 4 else "00:12:00")
    assert a.allocation(text, JOB, 1271, r.envelope(p))["requested"] == r.envelope(p)


def test_allocated_cpu_rounding_does_not_change_request():
    text = legacy_text().replace("NumCPUs=2", "NumCPUs=4").replace("TRES=cpu=2", "TRES=cpu=4")
    assert a.allocation(text, JOB, 1271, r.envelope(plan()))["allocated_cpus"] == 4


@pytest.mark.parametrize(
    "old,new",
    [
        ("CPUs/Task=2", "CPUs/Task=4"),
        ("MinMemoryNode=2G", "MinMemoryNode=4G"),
        ("MinMemoryNode=2G", "MinMemoryCPU=1G"),
        ("NumTasks=1", "NumTasks=2"),
        ("CPUs/Task=2", "CPUs/Task=N/A"),
        ("TRES=cpu=2", "TRES=cpu=4"),
        ("mem=2G", "mem=4G"),
        ("node=1", "node=2"),
        ("cpu=2,mem=2G", "cpu=2,cpu=2,mem=2G"),
        ("cpu=2,mem=2G", "cpu=2,mem=2G,mem=2G"),
        ("NumCPUs=2", "NumCPUs=2 NumCPUs=2"),
        ("CPUs/Task=2", ""),
        ("MinMemoryNode=2G", ""),
        ("TRES=cpu=2,mem=2G,energy=701,node=1,billing=2", ""),
    ],
)
def test_legacy_wrong_missing_or_ambiguous_resources_still_block(old, new):
    with pytest.raises(ValueError):
        a.allocation(legacy_text().replace(old, new), JOB, 1271, r.envelope(plan()))


@pytest.mark.parametrize(
    "extra",
    [
        "ReqTRES=cpu=4,mem=2G,node=1",
        "ReqTRES=cpu=2,mem=4G,node=1",
        "AllocTRES=cpu=4,mem=2G,node=1",
        "AllocTRES=cpu=2,mem=4G,node=1",
    ],
)
def test_contradictory_optional_alias_is_not_ignored(extra):
    with pytest.raises(ValueError):
        a.allocation(legacy_text() + " " + extra, JOB, 1271, r.envelope(plan()))


def test_modern_and_legacy_formats_agree_on_scoped_values():
    left = a.allocation(scheduler_text(), JOB, 1271, r.envelope(plan()))
    right = a.allocation(legacy_text(), JOB, 1271, r.envelope(plan()))
    assert all(
        left[k] == right[k] for k in ("job_id", "uid", "requested", "allocated_cpus", "node")
    )


def test_redaction_and_resource_replay():
    p = plan()
    values = records(p)
    values["allocation.json"] = a.allocation(
        legacy_text() + " Command=/private/path StdErr=/private/log", JOB, 1271, r.envelope(p)
    )
    assert "Command" not in values["allocation.json"]["scheduler_fields"]
    assert a.review(p, JOB, values, accounting())["disposition"] == "academic_stage_accepted"
    changed = copy.deepcopy(values)
    changed["allocation.json"]["scheduler_fields"]["MinMemoryNode"] = "4G"
    assert a.review(p, JOB, changed, accounting())["disposition"] == "evidence_not_accepted"


def prepare_batch(tmp_path, monkeypatch):
    monkeypatch.setattr(r, "BASE", tmp_path)
    monkeypatch.setattr(os, "getuid", lambda: 1271, raising=False)
    monkeypatch.setenv("SLURM_JOB_ID", JOB)
    monkeypatch.setattr(r, "check_source", lambda *x: None)
    target = r.claim_path("normal")
    target.mkdir()
    p = plan()
    for name, value in {
        "plan.json": p,
        "job.json": {"job_id": JOB, "plan_sha256": a.digest(p)},
        "origin.json": {"checkout": str(a.ROOT), "python": sys.executable},
    }.items():
        r.d.write_new(target / name, value)
    return target, p


def test_installed_format_reaches_launch_and_preserves_diagnostic(tmp_path, monkeypatch):
    target, p = prepare_batch(tmp_path, monkeypatch)
    launched = []
    monkeypatch.setattr(r, "supervise", lambda *x, **k: None)
    r.batch(
        target,
        command=lambda *x, **k: ({"status": "complete", "returncode": 0}, legacy_text().encode()),
        popen=lambda argv, **k: launched.append(argv) or object(),
    )
    assert len(launched) == 1 and launched[0][0] == "srun"
    assert "--cpus-per-task=1" in launched[0]
    diagnostic = a.c.read_json(target / "batch-diagnostic.json")
    assert diagnostic["phase"] == "complete" and diagnostic["status"] == "returned"
    assert diagnostic["plan_sha256"] == a.digest(p)


def test_bad_allocation_diagnostic_is_portable_without_worker(tmp_path, monkeypatch):
    target, p = prepare_batch(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="Requested resources"):
        r.batch(
            target,
            command=lambda *x, **k: (
                {"status": "complete", "returncode": 0},
                legacy_text().replace("MinMemoryNode=2G", "MinMemoryNode=4G").encode(),
            ),
            popen=lambda *x, **k: pytest.fail("Worker must not launch"),
        )
    diagnostic = a.c.read_json(target / "batch-diagnostic.json")
    assert diagnostic["phase"] == "allocation_validation"
    assert diagnostic["scheduler_fields"]["MinMemoryNode"] == "4G"
    assert "message" not in diagnostic and "traceback" not in diagnostic
    _, _, result = r.collect(
        target,
        command=lambda *x, **k: (
            {"status": "complete", "returncode": 0},
            f"{JOB}|FAILED|1:0|4\n{JOB}.batch|FAILED|1:0|4\n{JOB}.extern|COMPLETED|0:0|4\n".encode(),
        ),
    )
    assert result["disposition"] == "evidence_not_accepted"
    assert not (target / "worker.out").exists()
    assert a.c.read_json(target / "plan.json") == p


@pytest.mark.parametrize("phase", ["source_runtime", "allocation_query", "worker_launch"])
def test_early_exception_phase_survives(tmp_path, monkeypatch, phase):
    target, _ = prepare_batch(tmp_path, monkeypatch)

    def fail(*args, **kwargs):
        raise OSError("PRIVATE diagnostic must not enter archive")

    if phase == "source_runtime":
        monkeypatch.setattr(r, "check_source", fail)
    command = (
        fail
        if phase == "allocation_query"
        else lambda *x, **k: ({"status": "complete", "returncode": 0}, legacy_text().encode())
    )
    with pytest.raises(OSError):
        r.batch(target, command=command, popen=fail)
    value = a.c.read_json(target / "batch-diagnostic.json")
    assert value["phase"] == phase and value["error_kind"] == "OSError"
    assert "PRIVATE" not in (target / "batch-diagnostic.json").read_text()


def test_missing_predecessor_stops_before_claim_or_scheduler(tmp_path, monkeypatch):
    monkeypatch.setattr(r, "BASE", tmp_path)
    with pytest.raises(OSError):
        r.submit("normal", SOURCE, [], command=lambda *x, **k: pytest.fail("Submission reached"))
    assert not r.claim_path("normal").exists()


def test_successor_namespace_and_original_history_pins(tmp_path, monkeypatch):
    monkeypatch.setattr(r, "BASE", tmp_path)
    assert r.claim_path("normal").name == ".mvp2-s2-academic-v2-normal"
    assert r.PREDECESSOR == {
        "source": "faa7ec6ee2629a34210917f81a34193ad7fc6c6c",
        "checksum": "52f4e69ad527972f253cd81a1e9cdcc0925ca2fad30b14e2fbf19918c1b4f533",
        "plan": "66f911b103a7d62d4016d8e3baf1253399c7009fb108140cb23652efd7411131",
        "job": "2212000",
    }


def test_rejected_history_is_replayed_readonly(tmp_path, monkeypatch):
    monkeypatch.setattr(r, "BASE", tmp_path)
    path = tmp_path / ".mvp2-s2-academic-v1-normal"
    path.mkdir()
    p = plan()
    r.d.write_new(path / "plan.json", p)
    r.d.write_new(path / "job.json", {"job_id": JOB, "plan_sha256": a.digest(p)})
    archive, checksum, result = r.collect(
        path,
        command=lambda *x, **k: (
            {"status": "complete", "returncode": 0},
            f"{JOB}|FAILED|1:0|4\n{JOB}.batch|FAILED|1:0|4\n{JOB}.extern|COMPLETED|0:0|4\n".encode(),
        ),
    )
    monkeypatch.setattr(
        r, "PREDECESSOR", {"source": SOURCE, "checksum": checksum, "plan": a.digest(p), "job": JOB}
    )
    before = archive.read_bytes()
    assert r.verify_rejected_normal() == result
    assert archive.read_bytes() == before
    monkeypatch.setitem(r.PREDECESSOR, "checksum", "0" * 64)
    with pytest.raises(ValueError, match="Archive checksum"):
        r.verify_rejected_normal()
