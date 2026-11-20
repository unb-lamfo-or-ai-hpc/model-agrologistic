import contextlib
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts import pyomo_h400_e1 as e1
from scripts import pyomo_h400_e1_queue as transport
from scripts import pyomo_h400_e2 as e2
from scripts import pyomo_h400_e2_queue as queue
from scripts import pyomo_scaling_campaign as engine
from scripts import pyomo_serial_queue as serial
from scripts import qualify_pyomo_scaling as qualify
from tests.test_pyomo_h400_e1_queue import FakeSlurm

SOURCE = "a" * 40
PLAN = "b" * 64
CONTROLLER = "c" * 64


def test_e2_cells_and_profiles(tmp_path):
    assert [(item["solver"], item["threads"]) for item in e2.CASES] == [
        ("gurobi", 2), ("highs", 2), ("gurobi", 4), ("highs", 4), ("gurobi", 8), ("highs", 8),
    ]
    assert all(
        (item["population"], item["repetition"], item["seed"], item["native_seconds"],
         item["mip_gap_target"]) == (400, 1, 42, 28800, 0.01)
        for item in e2.CASES
    )
    campaign = tmp_path / e2.CAMPAIGN
    assert engine.campaign_cells(campaign) == list(e2.CASES)
    assert engine.campaign_limit(campaign) == 1
    assert engine.qualification(campaign).name == e2.QUALIFICATION
    assert engine.c.PROFILE["memory_mib"] == transport.SOLVE_PROFILE["memory_mib"] == 196608


@pytest.fixture
def anchor(tmp_path):
    campaign = tmp_path / e2.E1_CAMPAIGN
    queue_dir = tmp_path / e2.E1_QUEUE
    gate_dir = queue_dir / "gate-4"
    campaign.mkdir()
    gate_dir.mkdir(parents=True)
    gate = {
        "status": "accepted", "cell": e1.CASES[-1]["id"],
        "proof": {
            "status": "e1_resource_criteria_met",
            "cells": {
                item["id"]: {"job_id": job}
                for item, job in zip(e1.CASES, e2.E1_SOLVE_JOBS, strict=True)
            },
        },
    }
    paths = {
        "campaign": campaign / "campaign.json",
        "gate": gate_dir / "gate_result.json",
        "job": queue_dir / "gate-4.json",
    }
    serial.write(paths["campaign"], {})
    serial.write(paths["gate"], gate)
    serial.write(paths["job"], {"job_id": e2.E1_GATE_JOB})
    for item, sha in zip(e1.CASES, e2.E1_ARCHIVES, strict=True):
        claim = campaign / item["id"]
        claim.mkdir()
        serial.write(claim / "collection.json", {"sha256": sha})
    paths["archive"] = campaign / e1.CASES[0]["id"] / "collection.json"
    return paths, gate


def bind_hashes(anchor, monkeypatch):
    paths, _ = anchor
    monkeypatch.setattr(e2, "E1_CAMPAIGN_SHA", serial.digest(paths["campaign"]))
    monkeypatch.setattr(e2, "E1_GATE_SHA", serial.digest(paths["gate"]))


def test_e2_requires_original_e1_closure(tmp_path, anchor, monkeypatch):
    bind_hashes(anchor, monkeypatch)
    _, gate = anchor
    monkeypatch.setattr(e1, "read_bundle", Mock(return_value="archived receipts"))
    monkeypatch.setattr(e1, "evaluate", Mock(return_value=gate["proof"]))
    proof = e2.predecessor(tmp_path, digest=serial.digest, read=serial.read, audit=True)
    assert proof["gate_job_id"] == e2.E1_GATE_JOB
    assert proof["solve_jobs"] == list(e2.E1_SOLVE_JOBS)
    e1.evaluate.assert_called_once_with("archived receipts", e2.E1_CAMPAIGN_SHA, e2.E1_SOURCE)


@pytest.mark.parametrize("changed", ["campaign", "gate", "job"])
def test_e2_rejects_changed_e1_bindings(tmp_path, anchor, monkeypatch, changed):
    bind_hashes(anchor, monkeypatch)
    paths, _ = anchor
    paths[changed].write_text(json.dumps({"job_id": "1"}), encoding="utf-8")
    with pytest.raises(ValueError, match="closing gate differs"):
        e2.predecessor(tmp_path, digest=serial.digest, read=serial.read)


def test_e2_rejects_changed_archived_e1_proof(tmp_path, anchor, monkeypatch):
    bind_hashes(anchor, monkeypatch)
    monkeypatch.setattr(e1, "read_bundle", Mock(return_value={}))
    monkeypatch.setattr(e1, "evaluate", Mock(return_value={}))
    with pytest.raises(ValueError, match="closure replay differs"):
        e2.predecessor(tmp_path, digest=serial.digest, read=serial.read, audit=True)


def test_e2_rejects_changed_e1_archive_digest(tmp_path, anchor, monkeypatch):
    bind_hashes(anchor, monkeypatch)
    paths, _ = anchor
    paths["archive"].write_text(json.dumps({"sha256": "a" * 64}), encoding="utf-8")
    with pytest.raises(ValueError, match="Preserved E1 archive digest differs"):
        e2.predecessor(tmp_path, digest=serial.digest, read=serial.read)


@pytest.fixture
def controller(tmp_path, monkeypatch):
    campaign = tmp_path / e2.CAMPAIGN
    queue_dir = tmp_path / e2.QUEUE
    campaign.mkdir()
    manifest = {
        "cells": list(e2.CASES), "inputs": {"400": {"workbook": "frozen.xlsx"}},
        "profile": engine.c.PROFILE, "source_commit": SOURCE, "e2_predecessor": {"gate": "2247728"},
    }
    serial.write(campaign / "campaign.json", manifest)
    monkeypatch.setattr(queue, "CAMPAIGN", campaign)
    monkeypatch.setattr(queue, "QUEUE", queue_dir)
    monkeypatch.setattr(transport, "QUEUE", queue_dir)  # FakeSlurm checks the submission record.
    monkeypatch.setattr(queue.os, "getuid", lambda: 42, raising=False)
    monkeypatch.setenv("GRB_LICENSE_FILE", transport.LICENSE)
    monkeypatch.setattr(
        queue.importlib, "import_module", lambda _: SimpleNamespace(check_file=lambda: None),
    )
    fake_engine = SimpleNamespace(
        ROOT=tmp_path / "source", e2=e2, c=engine.c,
        o=SimpleNamespace(fields=json.loads),
        r=SimpleNamespace(spec_payload=lambda value: value),
        login=Mock(), load_campaign=Mock(return_value=manifest), load_run=Mock(),
        submission_lock=lambda _: contextlib.nullcontext(), e1_storage=lambda _: {},
        selection=lambda *_: {}, scheduler_arguments=engine.scheduler_arguments,
        admit_cell=Mock(), batch=Mock(),
    )
    monkeypatch.setattr(engine.c, "specification", lambda *_: {})
    return fake_engine


def test_e2_releases_exactly_six_solves_and_six_gates(controller):
    slurm = FakeSlurm()
    receipt = queue.submit(controller, serial, transport, SOURCE, PLAN, CONTROLLER, command=slurm)
    ids = list(slurm.jobs)
    assert receipt["new_jobs"] == len(ids) == 12 and slurm.releases == [ids]
    assert list(receipt["jobs"]) == [node["id"] for node in queue.graph(e2.CASES, transport)]
    expected = ["(null)"] + [
        f"{'afterany' if i % 2 == 0 else 'afterok'}:{job}"
        for i, job in enumerate(ids[:-1])
    ]
    assert [row["Dependency"] for row in slurm.jobs.values()] == expected
    assert all(serial.read(queue.CAMPAIGN / item["id"] / "job.json")["source_commit"] == SOURCE
               for item in e2.CASES)


@pytest.mark.parametrize("problem", ["uncertain", "dependency"])
def test_e2_preserves_unreleased_claim_on_failure(controller, problem):
    slurm = FakeSlurm(fail=3 if problem == "uncertain" else None)

    def command(argv):
        if problem == "dependency" and argv == ["scontrol", "-o", "show", "job", "103"]:
            slurm.jobs["103"]["Dependency"] = "(null)"
        return slurm(argv)

    with pytest.raises(ValueError, match="Submission uncertain|Queued dependency differs"):
        queue.submit(controller, serial, transport, SOURCE, PLAN, CONTROLLER, command=command)
    with pytest.raises(ValueError, match="Existing claim"):
        queue.submit(controller, serial, transport, SOURCE, PLAN, CONTROLLER, command=command)
    assert not slurm.releases


def test_e2_refuses_direct_start(monkeypatch, tmp_path):
    monkeypatch.setattr(engine, "login", Mock())
    with pytest.raises(ValueError, match="finite E2 queue"):
        engine.start(tmp_path / e2.CAMPAIGN, SOURCE, e2.CASES[0]["id"], True)


def test_e2_gate_replays_frozen_cells_and_excludes_e1_ids(controller, monkeypatch):
    read = Mock(side_effect=lambda _, cell: cell)
    audit = Mock(return_value={"status": "e1_resource_criteria_met"})
    monkeypatch.setattr(e1, "read_cell", read)
    monkeypatch.setattr(e1, "evaluate", audit)
    campaign = controller.load_campaign()
    engine.admit_cell(queue.CAMPAIGN, e2.CASES[2], [], campaign)
    cells = [cell["id"] for cell in e2.CASES[:2]]
    assert [call.args for call in read.call_args_list] == [(queue.CAMPAIGN, cell) for cell in cells]
    args, kwargs = audit.call_args
    assert args == ({cell: cell for cell in cells}, engine.c.digest(campaign), SOURCE)
    assert kwargs == {
        "prefix": True, "cases": list(e2.CASES), "excluded_jobs": e2.E1_SOLVE_JOBS,
    }


def test_e2_qualification_requires_the_new_public_profile():
    with pytest.raises(ValueError, match="Exact public qualification"):
        qualify.accepted({"schema_version": engine.c.SCHEMA + "-e1-public"}, {}, e2_profile=True)


def test_e2_compute_will_not_run_after_rejected_gate(controller, monkeypatch):
    slurm = FakeSlurm()
    jobs = queue.submit(controller, serial, transport, SOURCE, PLAN, CONTROLLER, command=slurm)
    serial.write(queue.QUEUE / "gate-1/gate_result.json", {"status": "rejected"})
    monkeypatch.setenv("SLURM_JOB_ID", jobs["jobs"]["solve-2"]["job_id"])
    monkeypatch.setattr(serial, "run", slurm)
    monkeypatch.setattr(serial, "verify_running", Mock())
    with pytest.raises(ValueError, match="Predecessor gate"):
        queue.compute(controller, serial, transport, None, "solve-2", SOURCE, PLAN, CONTROLLER)
    controller.batch.assert_not_called()
