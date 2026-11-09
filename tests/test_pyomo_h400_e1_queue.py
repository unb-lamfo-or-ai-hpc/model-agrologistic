import contextlib
import json
from types import SimpleNamespace

import pytest

from scripts import pyomo_h400_e1_queue as queue
from scripts import pyomo_serial_queue as serial


@pytest.fixture
def session(tmp_path, monkeypatch):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    (campaign / "campaign.json").write_text("frozen", encoding="utf-8")
    first = campaign / queue.CELLS[0]
    first.mkdir()
    original = {
        "job_id": queue.FIRST_JOB, "plan_sha256": queue.FIRST_PLAN,
        "source_commit": queue.ENGINE_SHA,
    }
    serial.write(first / "job.json", original)
    monkeypatch.setattr(queue, "CAMPAIGN", campaign)
    monkeypatch.setattr(queue, "QUEUE", tmp_path / "queue")
    monkeypatch.setattr(queue, "CAMPAIGN_SHA", queue.digest(campaign / "campaign.json"))
    monkeypatch.setattr(queue.os, "getuid", lambda: 42, raising=False)
    monkeypatch.setenv("GRB_LICENSE_FILE", queue.LICENSE)
    monkeypatch.setattr(
        queue.importlib, "import_module", lambda _: SimpleNamespace(check_file=lambda: None),
    )
    manifest = {
        "cells": [{"id": cell} for cell in queue.CELLS],
        "inputs": {"400": {"workbook": "frozen.xlsx"}}, "profile": queue.SOLVE_PROFILE,
    }
    engine = SimpleNamespace(
        ROOT=tmp_path / "source",
        c=SimpleNamespace(
            SCHEMA="test", digest=lambda _: "a" * 64, specification=lambda *_: {},
        ),
        o=SimpleNamespace(job_receipt=lambda *_: original, fields=json.loads),
        r=SimpleNamespace(spec_payload=lambda value: value),
        login=lambda: None, load_campaign=lambda *_: manifest, load_run=lambda *_: None,
        submission_lock=lambda _: contextlib.nullcontext(), e1_storage=lambda _: {},
        selection=lambda *_: {}, scheduler_arguments=lambda: [
            "--nodes=1", "--cpus-per-task=24", "--time=12:00:00", "--mem=196608M", "--exclusive",
        ],
    )
    return engine, original


class FakeSlurm:
    def __init__(self, state="RUNNING", fail=None):
        self.state = state
        self.fail = fail
        self.jobs = {}
        self.releases = []
        self.submissions = 0

    def __call__(self, argv, **_kwargs):
        if argv[0] == "sacct":
            return self.result(f"{queue.FIRST_JOB}|{self.state}|0:0|90|100K\n")
        if argv[0] == "sbatch":
            self.submissions += 1
            assert "--hold" in argv and "--kill-on-invalid-dep=yes" in argv
            if self.submissions == self.fail:
                return self.result("ambiguous\n", code=1)
            options = dict(arg[2:].split("=", 1) for arg in argv if "=" in arg)
            identifier = str(100 + self.submissions)
            self.jobs[identifier] = {
                "JobId": identifier, "JobState": "PENDING", "Priority": "0",
                "Reason": "JobHeldUser", "UserId": "user(42)", "NumNodes": "1-1",
                "WorkDir": options["chdir"], "Command": argv[-1], "Partition": "intel-256",
                "Account": "sxdsouza", "QOS": "preempt", "Requeue": "0",
                "TimeLimit": options["time"], "NumCPUs": options["cpus-per-task"],
                "MinMemoryNode": options["mem"], "OverSubscribe": "NO",
                "Dependency": options.get("dependency", "(null)"),
            }
            return self.result(identifier + "\n")
        if argv[:3] == ["scontrol", "-o", "show"]:
            return self.result(json.dumps(self.jobs[argv[-1]]))
        assert argv[:2] == ["scontrol", "release"]
        assert (queue.QUEUE / "submitted.json").is_file()
        self.releases.append(argv[2].split(","))
        return self.result("")

    @staticmethod
    def result(output, code=0):
        return SimpleNamespace(stdout=output, stderr="", returncode=code)


@pytest.mark.parametrize("state", ["RUNNING", "COMPLETED"])
def test_one_release_attaches_original_and_submits_exact_chain(session, state):
    engine, original = session
    slurm = FakeSlurm(state=state)
    receipt = queue.submit(engine, serial, queue.FIRST_JOB, "a" * 64, command=slurm)
    assert receipt["jobs"]["solve-1"] == original
    assert receipt["new_jobs"] == 7
    assert slurm.releases == [list(slurm.jobs)]
    dependencies = [job["Dependency"] for job in slurm.jobs.values()]
    first = "(null)" if state == "COMPLETED" else "afterany:" + queue.FIRST_JOB
    assert dependencies == [first, "afterok:101", "afterany:102", "afterok:103",
                            "afterany:104", "afterok:105", "afterany:106"]
    first_path = queue.CAMPAIGN / queue.CELLS[0]
    assert list(first_path.iterdir()) == [first_path / "job.json"]


def test_ambiguous_submission_preserves_claim_and_never_releases(session):
    engine, _ = session
    slurm = FakeSlurm(fail=3)
    with pytest.raises(ValueError, match="Submission uncertain"):
        queue.submit(engine, serial, queue.FIRST_JOB, "a" * 64, command=slurm)
    with pytest.raises(ValueError, match="Existing claim"):
        queue.submit(engine, serial, queue.FIRST_JOB, "a" * 64, command=slurm)
    assert slurm.submissions == 3 and not slurm.releases


def test_hold_with_wrong_dependency_prevents_release(session):
    engine, _ = session
    slurm = FakeSlurm()

    def command(argv, **kwargs):
        if argv == ["scontrol", "-o", "show", "job", "102"]:
            slurm.jobs["102"]["Dependency"] = "(null)"
        return slurm(argv, **kwargs)

    with pytest.raises(ValueError, match="Queued dependency differs"):
        queue.submit(engine, serial, queue.FIRST_JOB, "a" * 64, command=command)
    assert slurm.submissions == 7 and not slurm.releases


def test_failed_first_job_creates_no_continuation_claim(session):
    engine, _ = session
    slurm = FakeSlurm(state="FAILED")
    with pytest.raises(ValueError, match="First pilot already failed"):
        queue.submit(engine, serial, queue.FIRST_JOB, "a" * 64, command=slurm)
    assert not queue.QUEUE.exists() and slurm.submissions == 0


@pytest.mark.parametrize("accepted", [True, False])
def test_collection_gate_checks_entire_prefix(tmp_path, accepted):
    node = queue.graph()[-1]
    checked = []

    def evaluate(records, campaign, source, *, prefix):
        checked.extend(records)
        assert campaign == queue.CAMPAIGN_SHA and source == queue.ENGINE_SHA and not prefix
        suffix = "met" if accepted else "rejected"
        return {"status": "e1_resource_criteria_" + suffix}

    engine = SimpleNamespace(
        e1_storage=lambda _: None,
        e1=SimpleNamespace(read_cell=lambda _, cell: cell, evaluate=evaluate),
    )
    collector = SimpleNamespace(collect=lambda *_a, **_k: {"status": "observation_collected"})
    assert queue.collect_gate(engine, serial, collector, node, tmp_path) == int(not accepted)
    assert checked == list(queue.CELLS)
    assert serial.read(tmp_path / "gate_result.json")["status"] == (
        "accepted" if accepted else "rejected"
    )
