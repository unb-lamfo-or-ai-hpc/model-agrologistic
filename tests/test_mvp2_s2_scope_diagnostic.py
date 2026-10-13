"""Scope observation qualification: injected kernel/scheduler; no NPAD access."""

import copy
import json
from pathlib import Path

import pytest

from scripts import mvp2_s2_scope_diagnostic as p

COMMIT, SHA, JOB = "a" * 40, "b" * 64, "123456"


def maps(leaf):
    return {
        key: {"scope": "/cg/" + key + "/job/" + leaf, "mount": "/cg/" + key}
        for key in p.s.CONTROLLERS
    }


def obs():
    return {
        "schema_version": "s2-scope-observation-v1",
        "source_commit": COMMIT,
        "plan_sha256": SHA,
        "job_id": JOB,
        "step_id": None,
        "status": "incomplete",
        "phase": "identity",
        "error_kind": None,
        "summary": None,
        "limits": None,
        "queries": {},
        "local_client_returncode": None,
        **p.FLAGS,
    }


def plan():
    return {
        "source_commit": COMMIT,
        "checkout": "/source",
        "python": "/python",
        "tools": {"sbatch": "/bin/sbatch", "srun": "/bin/srun"},
    }


@pytest.mark.parametrize("controller", p.s.CONTROLLERS)
@pytest.mark.parametrize(
    "relation,worker_path,supervisor_path",
    [
        ("equal", "/job/a", "/job/a"),
        ("supervisor_ancestor", "/job/a/leaf", "/job/a"),
        ("worker_ancestor", "/job/a", "/job/a/leaf"),
        ("disjoint", "/job/a", "/job/ab"),
    ],
)
def test_all_controller_relations(controller, relation, worker_path, supervisor_path):
    worker, supervisor = maps("worker"), maps("batch")
    worker[controller]["scope"] = "/cg/" + controller + worker_path
    supervisor[controller]["scope"] = "/cg/" + controller + supervisor_path
    report = p.relations(worker, supervisor)
    assert set(report) == set(p.s.CONTROLLERS)
    assert report[controller]["relation"] == relation
    assert "/cg/" not in json.dumps(report)


def test_different_mount_and_incomplete_inventory():
    worker, supervisor = maps("worker"), maps("batch")
    worker["cpuacct"] = {"scope": "/other/job/w", "mount": "/other"}
    assert p.relations(worker, supervisor)["cpuacct"]["relation"] == "different_mount"
    del worker["memory"]
    with pytest.raises(ValueError):
        p.relations(worker, supervisor)


def test_existing_separation_gate_is_not_relaxed():
    with pytest.raises(ValueError, match="Shared/nested"):
        p.s.separated_scopes(maps("batch"), maps("batch"))
    assert all(x["relation"] == "equal" for x in p.relations(maps("batch"), maps("batch")).values())


@pytest.mark.parametrize(
    "raw", [b"secret token", b"\xff", b"PID JOBID STEPID LOCALID GLOBALID\nsecret"]
)
def test_membership_export_rejects_arbitrary_text(raw):
    assert p.public_query("members", raw) == {"parse_error": True}


def test_numeric_membership_and_allowlisted_fields():
    assert p.public_query("members", b"PID JOBID STEPID LOCALID GLOBALID\n20 123456 0 - -")[
        "listpids"
    ]
    public = p.public_query(
        "job", b"JobId=123456 UserId=test(1000) WorkDir=/private License=secret"
    )
    assert public == {"JobId": JOB}


@pytest.mark.parametrize("key", p.FLAGS)
def test_no_admission_or_cleanup_claim_can_be_promoted(key):
    value = obs()
    value[key] = True
    with pytest.raises(ValueError):
        p.validate_observation(value, COMMIT, SHA, JOB)


@pytest.mark.parametrize(
    "key,value",
    [
        ("raw", "private"),
        ("phase", "admit"),
        ("source_commit", "c" * 40),
        ("job_id", "999"),
        ("error_kind", "/secret/path"),
        ("step_id", "batch"),
    ],
)
def test_observation_schema_drift(key, value):
    item = obs()
    item[key] = value
    with pytest.raises(ValueError):
        p.validate_observation(item, COMMIT, SHA, JOB)


def test_terminal_numeric_step_and_cancellation_suffix():
    raw = f"{JOB}|COMPLETED|0:0|8\n{JOB}.batch|COMPLETED|0:0|8\n{JOB}.0|CANCELLED by 1271|0:9|4\n"
    rows, done = p.accounting(raw.encode(), JOB)
    assert done and rows[JOB + ".0"]["state"] == "CANCELLED"
    assert not p.accounting(f"{JOB}|RUNNING|0:0|1".encode(), JOB)[1]


def test_fixed_observation_resource_and_command_boundaries(monkeypatch, tmp_path):
    monkeypatch.setattr(p, "BASE", tmp_path)
    submit = p.submit_argv(plan())
    assert "--time=00:05:00" in submit and "--mem=2048M" in submit
    assert "--cpus-per-task=2" in submit and "--no-requeue" in submit
    argv = p.worker_argv(plan(), SHA, JOB)
    assert "--time=00:02:00" in argv and "--mem=256M" in argv
    assert "--cpus-per-task=1" in argv and "--export=NONE" in argv
    assert "leaf" in argv and not any("synthetic_worker" in x or "gurobi" in x for x in argv)


def test_existing_claim_routes_to_collection_without_submission(monkeypatch, tmp_path):
    monkeypatch.setattr(p, "BASE", tmp_path)
    monkeypatch.setattr(p.d, "host", lambda: None)
    (tmp_path / p.CLAIM).mkdir()
    calls = []
    monkeypatch.setattr(p, "collect", lambda commit: calls.append(commit) or 0)
    monkeypatch.setattr(p.d, "command", lambda *a, **k: pytest.fail("No scheduler on resume"))
    assert p.start(COMMIT) == 0 and calls == [COMMIT]


def test_archive_roundtrip_negative_missing_and_corruption(tmp_path):
    for index, observation in enumerate([None, obs()]):
        path = tmp_path / f"evidence-{index}.tar.gz"
        records = {
            "anchor.json": {
                "source_commit": COMMIT,
                "job_id": JOB,
                "plan_sha256": SHA,
                "predecessor": p.PARENT,
                **p.FLAGS,
            },
            "observation.json": observation,
            "accounting.json": {
                k: {"state": "COMPLETED", "exit_code": "0:0", "elapsed_seconds": 2}
                for k in (JOB, JOB + ".batch")
            },
        }
        p.d.pack(path, records)
        sha = p.d.digest(path.read_bytes())
        result = p.audit(path, sha, COMMIT, JOB, SHA)
        assert all(result[k] is False for k in p.FLAGS)
        with pytest.raises(ValueError):
            p.audit(path, "0" * 64, COMMIT, JOB, SHA)


def test_summary_does_not_export_private_mount_paths(monkeypatch):
    private = {
        role: {
            "identity": {"pid": pid, "uid": 1000, "starttime": 1, "state": "S"},
            "raw": {k: "private" for k in ("stat", "status", "cgroup", "mountinfo")},
        }
        for role, pid in (("worker", 20), ("supervisor", 10))
    }
    monkeypatch.setattr(p.s, "mapped_scopes", lambda *args: maps("shared"))
    public = p.summarize(private)
    assert "private" not in json.dumps(public) and "/cg/" not in json.dumps(public)
    value = obs()
    value["summary"] = public
    p.validate_observation(value, COMMIT, SHA, JOB)
    broken = copy.deepcopy(value)
    broken["summary"]["processes"]["worker"]["raw"] = "private"
    with pytest.raises(ValueError):
        p.validate_observation(broken, COMMIT, SHA, JOB)


def test_mapping_failure_is_evidence_not_admission(monkeypatch):
    record = {
        "identity": {"pid": 20, "uid": 1, "starttime": 1, "state": "S"},
        "raw": {k: "private" for k in ("stat", "status", "cgroup", "mountinfo")},
    }
    monkeypatch.setattr(
        p.s, "mapped_scopes", lambda *args: (_ for _ in ()).throw(ValueError("private"))
    )
    summary = p.summarize({"worker": record, "supervisor": record})
    assert summary["relations"] is None and summary["mapping_error"] == "ValueError"
    assert "private" not in json.dumps(summary)


def test_driver_keeps_original_claims_and_no_license():
    root = Path(p.__file__).parents[1]
    script = (root / "scripts/npad_s2_scope_diagnostic.sh").read_text()
    assert "5bf509a6db90b09eef8e1e13529f5039d934a9e1" in script
    assert "--no-checkout" in script and "--basetemp=" in script
    assert "GRB_LICENSE" not in script and "scancel" not in script
    assert "rm -" not in script and "reset" not in script


@pytest.mark.parametrize("failure", [None, "peer", "mapping", "query"])
def test_batch_preserves_observation_and_private_originals(monkeypatch, tmp_path, failure):
    monkeypatch.setattr(p, "BASE", tmp_path)
    claim = tmp_path / p.CLAIM
    claim.mkdir()
    run = tmp_path / "s2cg-12345678"
    run.mkdir()
    value = {**plan(), "run": str(run)}
    value["tools"]["scontrol"] = "/bin/scontrol"
    monkeypatch.setattr(p.d, "host", lambda: None)
    monkeypatch.setattr(p, "load_plan", lambda *args: (value, SHA))
    monkeypatch.setattr(p, "acknowledged", lambda *args: JOB)
    monkeypatch.setattr(p, "runtime", lambda *args: None)
    monkeypatch.setattr(p.os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(
        p,
        "capture",
        lambda pid: {
            "identity": {"pid": pid, "uid": 1000, "starttime": 1, "state": "S"},
            "raw": {key: "private" for key in ("stat", "status", "cgroup", "mountinfo")},
        },
    )

    def mapping(*args):
        assert (run / "pair-private.json").exists()
        if failure == "mapping":
            raise ValueError("private path")
        return maps("shared")

    monkeypatch.setattr(p.s, "mapped_scopes", mapping)
    monkeypatch.setattr(p, "limits", lambda *args: None)
    events = []

    class Server:
        def __init__(self, path):
            assert path == run / "ipc.sock"

        def accept(self, timeout):
            assert timeout == 30
            return {
                "job_id": "999" if failure == "peer" else JOB,
                "step_id": "0",
                "plan_sha256": SHA,
            }, {"pid": 20, "uid": 1000}

        def release(self, message, timeout):
            assert message == {"observation_finished": True}
            events.append("release")

        def close(self):
            events.append("close")

    class Child:
        def wait(self, timeout):
            events.append("wait")
            return 0

    monkeypatch.setattr(p.a, "BarrierServer", Server)
    monkeypatch.setattr(p.subprocess, "Popen", lambda *args, **kwargs: Child())

    def command(argv):
        if failure == "query":
            raise OSError("private path")
        raw = (
            b"PID JOBID STEPID LOCALID GLOBALID\n20 123456 0 - -"
            if "listpids" in argv
            else b"JobId=123456 WorkDir=/secret"
        )
        return {
            "status": "complete",
            "returncode": 0,
            "stdout_bytes": len(raw),
            "stderr_bytes": 0,
            "stdout_prefix_sha256": p.d.digest(raw),
            "stderr_prefix_sha256": p.d.digest(b""),
        }, raw

    monkeypatch.setattr(p.d, "command", command)
    result = p.batch(COMMIT, SHA)
    public = p.d.load(claim / "observation.json")
    p.validate_observation(public, COMMIT, SHA, JOB)
    assert "private" not in json.dumps(public) and "/secret" not in json.dumps(public)
    assert all(public[key] is False for key in p.FLAGS)
    assert "wait" in events and "close" in events
    assert result == (2 if failure in {"peer", "query"} else 0)
    if failure != "peer":
        assert (run / "pair-private.json").exists()
    if failure is None:
        assert all(x["relation"] == "equal" for x in public["summary"]["relations"].values())
    if failure == "mapping":
        assert public["summary"]["mapping_error"] == "ValueError"
        assert public["summary"]["relations"] is None


def test_collection_is_cached_and_never_queries_after_preservation(monkeypatch, tmp_path):
    monkeypatch.setattr(p, "BASE", tmp_path)
    claim = tmp_path / p.CLAIM
    claim.mkdir()
    tool = tmp_path / "sacct"
    tool.write_bytes(b"fixture")
    value = {"tools": {"sacct": str(tool)}, "tools_sha256": {"sacct": p.d.digest(b"fixture")}}
    monkeypatch.setattr(p.d, "host", lambda: None)
    monkeypatch.setattr(p, "load_plan", lambda *args: (value, SHA))
    p.d.write_new(claim / "job.json", {"job_id": JOB, "source_commit": COMMIT, "plan_sha256": SHA})
    raw = f"{JOB}|FAILED|2:0|8\n{JOB}.batch|FAILED|2:0|8\n".encode()
    monkeypatch.setattr(
        p.d, "command", lambda *args, **kwargs: ({"status": "complete", "returncode": 0}, raw)
    )
    assert p.collect(COMMIT) == 0
    saved = p.d.load(claim / "collection.json")
    before = Path(saved["archive"]).read_bytes()
    monkeypatch.setattr(p.d, "command", lambda *args, **kwargs: pytest.fail("Cached only"))
    assert p.collect(COMMIT) == 0
    assert Path(saved["archive"]).read_bytes() == before
