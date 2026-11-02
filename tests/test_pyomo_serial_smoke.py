"""Real-smoke harness uses five bounded public jobs; tests never contact Slurm."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


Q = module("serial_smoke_queue_unit", ROOT / "scripts/pyomo_serial_queue.py")
S = module("serial_smoke_unit", ROOT / "scripts/pyomo_serial_smoke.py")


@pytest.fixture
def context(tmp_path, monkeypatch):
    public = tmp_path / "public"
    (public / "source").mkdir(parents=True)
    monkeypatch.setattr(Q, "PUBLIC", public)
    monkeypatch.setattr(Q, "ROOT", public / "source")
    monkeypatch.setattr(Q, "login", lambda: None)
    monkeypatch.setattr(Q.os, "getuid", lambda: 123, raising=False)
    monkeypatch.setattr(Q, "verify_sources", lambda *a: None)
    monkeypatch.setattr(
        Q, "load_engine", lambda: SimpleNamespace(o=SimpleNamespace(fields=json.loads))
    )
    Q.write(public / "plan.json", {"source_commit": "a" * 40, "controller_files": {}})
    return SimpleNamespace(public=public, q=Q)


class Scheduler:
    def __init__(self, context):
        self.ctx = context
        self.calls = []
        self.jobs = []
        self.fail_at = None
        self.bad_afterany = False
        self.blocked_allocated = False
        self.existing_gurobi_state = "COMPLETED"

    def __call__(self, argv):
        self.calls.append(argv)
        if argv[0] == "squeue":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if argv[0] == "sbatch":
            self.jobs.append(argv)
            return SimpleNamespace(
                returncode=int(len(self.jobs) == self.fail_at),
                stdout=str(20000 + len(self.jobs)),
                stderr="",
            )
        if argv[:2] == ["scontrol", "release"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if argv[0] == "scontrol":
            job_id = argv[-1]
            for label, *_ in S.SMOKE:
                directory = self.ctx.public / "smoke" / label
                p = directory / "job.json"
                if p.is_file():
                    job = Q.read(p)
                    if job["job_id"] == job_id:
                        # Slurm may expand a colon list into comma-separated clauses.
                        pairs = Q.dependency_pairs(job["dependency"] or "")
                        dependency = (
                            ",".join(
                                kind + ":" + value + "(unfulfilled)"
                                for kind, value in sorted(pairs)
                            )
                            or "(null)"
                        )
                        fields = {
                            "JobId": job_id,
                            "JobState": "PENDING",
                            "Priority": "0",
                            "Reason": "JobHeldUser",
                            "UserId": "fixture(123)",
                            "WorkDir": str(directory),
                            "Command": str(directory / "batch.sh"),
                            "Partition": "intel-256",
                            "Account": "sxdsouza",
                            "QOS": "preempt",
                            "Requeue": "0",
                            "Dependency": dependency,
                            "TimeLimit": "00:05:00",
                            "MinMemoryNode": "1G",
                            "NumNodes": "1",
                            "NumCPUs": "1",
                        }
                        return SimpleNamespace(returncode=0, stdout=json.dumps(fields), stderr="")
        if argv[0] == "sacct":
            job_id = argv[2]
            if job_id == "2231593":
                return SimpleNamespace(
                    returncode=0,
                    stdout=f"2231593|{self.existing_gurobi_state}|0:0|100|\n",
                    stderr="",
                )
            receipts = Q.read(self.ctx.public / "smoke-jobs.json")
            label = next(k for k, v in receipts.items() if v["job_id"] == job_id)
            if "--format=JobIDRaw,Start,ElapsedRaw,AllocCPUS" in argv:
                line = (
                    f"{job_id}|2026-11-01T00:00:01|1|1\n"
                    if self.blocked_allocated
                    else f"{job_id}|Unknown|0|0\n"
                )
                return SimpleNamespace(returncode=0, stdout=line, stderr="")
            state = (
                "FAILED" if label == "fail" else "CANCELLED" if label == "blocked" else "COMPLETED"
            )
            if self.bad_afterany and label == "any":
                state = "CANCELLED"
            exit_code = "1:0" if label == "fail" else "0:0"
            return SimpleNamespace(
                returncode=0, stdout=f"{job_id}|{state}|{exit_code}|0|\n", stderr=""
            )
        raise AssertionError(argv)


def test_five_public_jobs_held_verified_released_once_and_expected_negative_states(context):
    scheduler = Scheduler(context)
    result = S.submit(Q, context.public, "a" * 40, command=scheduler)
    assert len(result["job_ids"]) == len(scheduler.jobs) == 5
    assert all("--hold" in args and "--kill-on-invalid-dep=yes" in args for args in scheduler.jobs)
    assert len([a for a in scheduler.calls if a[:2] == ["scontrol", "release"]]) == 1
    assert S.verify(Q, context.public, command=scheduler)["fail"]["state"] == "FAILED"
    assert S.verify(Q, context.public, command=scheduler)["blocked"]["state"] == "CANCELLED"
    with pytest.raises(ValueError, match="Existing smoke intent"):
        S.submit(Q, context.public, "a" * 40, command=scheduler)
    assert len(scheduler.jobs) == 5


def test_partial_public_submission_preserves_intent_and_never_releases(context):
    scheduler = Scheduler(context)
    scheduler.fail_at = 2
    with pytest.raises(ValueError, match="uncertain"):
        S.submit(Q, context.public, "a" * 40, command=scheduler)
    assert (context.public / "smoke-intent.json").exists()
    assert not any(a[:2] == ["scontrol", "release"] for a in scheduler.calls)


@pytest.mark.parametrize("fault", ["afterany", "allocated", "script"])
def test_live_smoke_proof_rejects_wrong_scheduler_behavior_or_modified_scripts(context, fault):
    scheduler = Scheduler(context)
    S.submit(Q, context.public, "a" * 40, command=scheduler)
    if fault == "afterany":
        scheduler.bad_afterany = True
    elif fault == "allocated":
        scheduler.blocked_allocated = True
    else:
        (context.public / "smoke/ok/batch.sh").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError):
        S.verify(Q, context.public, command=scheduler)


@pytest.mark.parametrize("text", ["afterok:1?afterany:2", "singleton", "afterok:0", "afterok:x"])
def test_dependency_normalization_does_not_accept_OR_or_unowned_forms(text):
    with pytest.raises(ValueError):
        Q.dependency_pairs(text)


def test_dependency_normalization_accepts_equivalent_slurm_colon_and_comma_lists():
    assert Q.dependency_pairs("afterany:10:20") == Q.dependency_pairs(
        "afterany:20(unfulfilled),afterany:10(unfulfilled)"
    )


@pytest.mark.parametrize("state", ["RUNNING", "COMPLETED"])
def test_native_public_qualification_waits_for_active_gurobi_without_releasing_it(context, state):
    scheduler = Scheduler(context)
    scheduler.existing_gurobi_state = state
    result = S.submit(Q, context.public, "a" * 40, command=scheduler)
    dependency = (context.public / "qualification-dependency.txt").read_text().strip()
    assert ("2231593" in dependency) is (state == "RUNNING")
    assert (result["qualification_waits_for_existing_gurobi"] == "2231593") is (state == "RUNNING")
    released = next(a for a in scheduler.calls if a[:2] == ["scontrol", "release"])
    assert "2231593" not in released[2]
