"""Academic A/P2/P3 qualification: injected scheduler/native effects, no NPAD calls."""

from __future__ import annotations

import copy
import io
import os
import subprocess
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_s2_academic as a
from scripts import mvp2_s2_academic_runtime as r
from scripts import mvp2_s2_academic_worker as w

SOURCE = "a" * 40
JOB = "12345"


def plan(stage="normal"):
    return a.plan(
        stage,
        SOURCE,
        {"scripts/mvp2_s2_allocation_diagnostic.py": "f" * 64},
        {"qualified_test_runtime": True},
    )


def accounting(stage="normal", *, root="COMPLETED", step=None):
    state, code = ("FAILED", "3:0") if stage.endswith("_failure") else ("COMPLETED", "0:0")
    if stage == "nested_setsid_term_ignore":
        state, code = "CANCELLED by 1271", "0:9"
    state = step or state
    return (
        f"{JOB}|{root}|0:0|8\n{JOB}.batch|{root}|0:0|8\n"
        f"{JOB}.extern|COMPLETED|0:0|8\n{JOB}.0|{state}|{code}|4\n"
    )


def records(p):
    h = a.digest(p)
    stage = p["stage"]
    values = {
        "worker-start.json": {
            "plan_sha256": h,
            "job_id": JOB,
            "step_id": JOB + ".0",
            "uid": 1271,
            "runtime_sha256": a.digest(p["runtime"]),
            "affinity": [0, 1, 2, 3] if stage == "native_miniature" else [0],
        },
        "allocation.json": {"job_id": JOB, "requested": r.envelope(p), "uid": 1271},
        "attempt.json": {
            "plan_sha256": h,
            "step_id": JOB + ".0",
            "local_client_reaped": True,
            "stop_reason": None,
        },
        "worker-result.json": {
            "plan_sha256": h,
            "phases": a.expected_phases(stage),
            "outcome": "expected_phase_failure"
            if stage.endswith("_failure")
            else "synthetic_complete",
        },
    }
    if stage == "nested_setsid_term_ignore":
        values.pop("worker-result.json")
        values["nested.json"] = {"plan_sha256": h, "extra_processes": 2}
        values["attempt.json"].update(
            stop_reason="planned_nested_stop",
            term_sent=True,
            kill_sent=True,
            descendants_absent_observed=True,
        )
    return values


@pytest.fixture(autouse=True)
def no_native_or_scheduler(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Uninjected scheduler/native effect")

    monkeypatch.setattr(d := r.d, "command", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    # Default arguments were bound at import; tested effect seams always explicitly inject.
    assert d is r.d
    monkeypatch.setattr(w, "resources", lambda: {"scope": "test_not_measured"})


@pytest.mark.parametrize("stage", a.STAGES)
def test_profile_and_plan(stage):
    p = plan(stage)
    assert a.validate_plan(p) == p
    assert not p["h300_execution_admitted"]
    assert not p["production_isolation_certified"]
    assert p["profile"]["not_required"] == [
        "host_user_namespaces_disabled",
        "pid1_namespace_access",
        "whole_host_hierarchy_scan",
        "hostile_worker_no_escape_proof",
        "filesystem_crash_durability_proof",
        "continuous_peak_coverage",
    ]


@pytest.mark.parametrize("stage", a.STAGES[:-1])
def test_independent_synthetic_review(stage):
    p = plan(stage)
    result = a.review(p, JOB, records(p), accounting(stage))
    assert result["disposition"] == "academic_stage_accepted"
    assert all(result["checks"].values())
    assert not result["production_isolation_certified"] and not result["h300_execution_admitted"]


@pytest.mark.parametrize(
    "missing", ("worker-start.json", "allocation.json", "attempt.json", "worker-result.json")
)
def test_missing_products_cannot_accept(missing):
    p = plan()
    values = records(p)
    del values[missing]
    assert a.review(p, JOB, values, accounting())["disposition"] == "evidence_not_accepted"


@pytest.mark.parametrize(
    "field,value",
    [
        ("plan_sha256", "0" * 64),
        ("runtime_sha256", "0" * 64),
        ("job_id", "777"),
        ("step_id", JOB + ".1"),
        ("uid", 42),
        ("affinity", [0, 32]),
    ],
)
def test_worker_identity_drift(field, value):
    p = plan()
    values = records(p)
    values["worker-start.json"][field] = value
    assert a.review(p, JOB, values, accounting())["disposition"] == "evidence_not_accepted"


@pytest.mark.parametrize("state", ("FAILED", "TIMEOUT", "OUT_OF_MEMORY", "PREEMPTED", "CANCELLED"))
def test_root_failure_never_success(state):
    p = plan()
    assert (
        a.review(p, JOB, records(p), accounting(root=state))["disposition"]
        == "evidence_not_accepted"
    )


def test_unplanned_watchdog_cannot_accept_completed_worker():
    p = plan()
    values = records(p)
    values["attempt.json"]["stop_reason"] = "build_watchdog"
    assert a.review(p, JOB, values, accounting())["disposition"] == "evidence_not_accepted"


def test_unknown_extra_step_rejected():
    p = plan()
    result = a.review(p, JOB, records(p), accounting() + f"{JOB}.1|COMPLETED|0:0|1\n")
    assert result["disposition"] == "evidence_not_accepted"
    assert not result["checks"]["accounting_scope"]


@pytest.mark.parametrize("field", ("kill_sent", "term_sent", "descendants_absent_observed"))
def test_nested_requires_each_observation(field):
    p = plan("nested_setsid_term_ignore")
    values = records(p)
    values["attempt.json"][field] = False
    assert (
        a.review(p, JOB, values, accounting(p["stage"]))["disposition"] == "evidence_not_accepted"
    )


def scheduler_text():
    return (
        f"JobId={JOB} UserId=researcher(1271) JobState=RUNNING Partition=intel-256 "
        "Account=sxdsouza NumNodes=1 NumCPUs=2 NodeList=r1i3n5 BatchHost=r1i3n5 "
        "ReqTRES=cpu=2,mem=2G,node=1 AllocTRES=cpu=2,mem=2G,node=1 TimeLimit=00:12:00"
    )


def test_minimal_allocation_needs_no_host_or_cgroup_inspection():
    result = a.allocation(scheduler_text(), JOB, 1271, r.envelope(plan()))
    assert result["scheduler_observation_only"]
    assert result["allocated_cpus"] == 2


@pytest.mark.parametrize(
    "old,new",
    [
        ("JobState=RUNNING", "JobState=PENDING"),
        ("NumNodes=1", "NumNodes=2"),
        ("NumCPUs=2", "NumCPUs=1"),
        ("mem=2G", "mem=4G"),
        ("TimeLimit=00:12:00", "TimeLimit=00:20:00"),
        ("Account=sxdsouza", "Account=other"),
        ("BatchHost=r1i3n5", "BatchHost=r1i3n4"),
    ],
)
def test_allocation_drift(old, new):
    with pytest.raises(ValueError):
        a.allocation(scheduler_text().replace(old, new), JOB, 1271, r.envelope(plan()))


@pytest.mark.parametrize("stage", a.STAGES[:-2])
def test_fixed_worker_outcome_prefix(stage, tmp_path):
    p = plan(stage)
    code = w.exercise(stage, tmp_path, p)
    value = a.c.read_json(tmp_path / "worker-result.json")
    assert code == (0 if stage == "normal" else 3)
    assert value["phases"] == a.expected_phases(stage)
    assert value["resources"]["scope"] == "test_not_measured"


def test_nested_exercise_is_explicitly_injected(tmp_path):
    calls = []
    p = plan("nested_setsid_term_ignore")
    w.exercise(p["stage"], tmp_path, p, nested_factory=lambda *x: calls.append(x))
    assert len(calls) == 1


def test_exact_step_signal_only():
    calls = []

    def command(argv, **kwargs):
        calls.append(argv)
        return {"status": "complete", "returncode": 0}, b""

    assert r.stop_step(JOB, JOB + ".0", command=command, pause=lambda _: None) == [True, True]
    assert calls == [
        ["scancel", "--signal=TERM", JOB + ".0"],
        ["scancel", "--signal=KILL", JOB + ".0"],
    ]
    with pytest.raises(ValueError):
        r.stop_step(JOB, "777.0", command=command)
    assert len(calls) == 2


def test_public_start_without_one_slot_ack_is_denied(monkeypatch):
    monkeypatch.setattr(r, "submit", lambda *x: pytest.fail("submission reached"))
    with pytest.raises(PermissionError):
        r.main(["start", "normal", SOURCE])


def test_native_and_h300_are_not_implicit_permissions():
    with pytest.raises(ValueError):
        a.prerequisites("native_miniature", [], SOURCE)
    with pytest.raises(PermissionError):
        a.execute_h300(accepted=True, profile=a.profile())


def test_no_normal_predecessor_needed_but_native_needs_all_six(monkeypatch):
    a.prerequisites("normal", [], SOURCE)
    monkeypatch.setattr(
        a,
        "audit",
        lambda *x: {
            "stage": x[0],
            "source_commit": SOURCE,
            "disposition": "academic_stage_accepted",
        },
    )
    a.prerequisites("build_failure", [["normal"]], SOURCE)
    a.prerequisites("native_miniature", [[x] for x in a.STAGES[:-1]], SOURCE)
    with pytest.raises(ValueError):
        a.prerequisites("native_miniature", [[x] for x in reversed(a.STAGES[:-1])], SOURCE)


def test_unknown_submission_consumes_slot(tmp_path, monkeypatch):
    monkeypatch.setattr(r, "BASE", tmp_path)
    monkeypatch.setattr(r.d, "source_files", lambda *x: plan()["files"])
    monkeypatch.setattr(a, "runtime", lambda: plan()["runtime"])
    count = []

    def command(*args, **kwargs):
        count.append(args)
        return {"status": "timeout", "returncode": -9}, b""

    with pytest.raises(ValueError, match="Submission unknown"):
        r.submit("normal", SOURCE, [], root=tmp_path, command=command)
    with pytest.raises(FileExistsError):
        r.submit("normal", SOURCE, [], root=tmp_path, command=command)
    assert len(count) == 1
    assert (r.claim_path("normal") / "submission-called.json").is_file()


def test_failure_cleanup_is_published_atomically(tmp_path, monkeypatch):
    journal = a.c.PhaseJournal(tmp_path / "phase", "f" * 64)
    journal.enter("build")
    original = a.c.write_once
    seen = []

    def interrupted_visibility(path, value):
        seen.append((Path(path).name, (journal.directory / "failure-cleanup.json").exists()))
        original(path, value)
        assert not (journal.directory / "failure-cleanup.json").exists()

    monkeypatch.setattr(a.c, "write_once", interrupted_visibility)
    journal.failure_cleanup()
    assert seen == [("failure-cleanup.pending", False)]
    assert a.c.failure_cleanup_event(journal.directory, "f" * 64, ["build"])


def write_run(tmp_path, stage="normal"):
    target = tmp_path / "run"
    target.mkdir()
    p = plan(stage)
    r.d.write_new(target / "plan.json", p)
    r.d.write_new(target / "job.json", {"job_id": JOB, "plan_sha256": a.digest(p)})
    for name, value in records(p).items():
        r.d.write_new(target / name, value)
    return target, p


def test_collection_cache_roundtrip_without_new_query(tmp_path):
    target, p = write_run(tmp_path)
    count = []

    def command(*args, **kwargs):
        count.append(args)
        return {"status": "complete", "returncode": 0}, accounting().encode()

    archive, checksum, result = r.collect(target, command=command)
    assert result["disposition"] == "academic_stage_accepted"
    assert a.audit(archive, checksum, SOURCE, a.digest(p), JOB) == result
    assert r.collect(target, command=command) == (archive, checksum, result)
    assert len(count) == 1


def test_negative_collection_retains_originals(tmp_path):
    target, p = write_run(tmp_path)
    (target / "attempt.json").unlink()  # Disposable test fixture only.
    before = {x.name: x.read_bytes() for x in target.iterdir()}
    archive, checksum, result = r.collect(
        target,
        command=lambda *x, **k: ({"status": "complete", "returncode": 0}, accounting().encode()),
    )
    assert result["disposition"] == "evidence_not_accepted"
    assert a.audit(archive, checksum, SOURCE, a.digest(p), JOB) == result
    assert all((target / name).read_bytes() == raw for name, raw in before.items())


@pytest.mark.parametrize(
    "kind",
    (
        "wrong_sha",
        "wrong_source",
        "wrong_plan",
        "wrong_job",
        "duplicate",
        "extra",
        "symlink",
        "trailing",
        "corrupt_review",
    ),
)
def test_hostile_or_corrupt_archive(tmp_path, kind):
    target, p = write_run(tmp_path)
    archive, checksum, _ = r.collect(
        target,
        command=lambda *x, **k: ({"status": "complete", "returncode": 0}, accounting().encode()),
    )
    source, h, job = SOURCE, a.digest(p), JOB
    if kind == "wrong_sha":
        checksum = "0" * 64
    elif kind == "wrong_source":
        source = "b" * 40
    elif kind == "wrong_plan":
        h = "0" * 64
    elif kind == "wrong_job":
        job = "777"
    else:
        with tarfile.open(archive) as handle:
            files = {x.name: handle.extractfile(x).read() for x in handle}
        if kind == "corrupt_review":
            files["review.json"] = b"{}"
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w:gz") as handle:
            items = list(files.items())
            if kind == "duplicate":
                items.append(items[0])
            if kind in {"extra", "symlink"}:
                items.append(("surprise", b"{}"))
            for name, raw in items:
                member = tarfile.TarInfo(name)
                member.size = len(raw)
                if kind == "symlink" and name == "surprise":
                    member.type = tarfile.SYMTYPE
                    member.linkname = "/tmp/outside"
                handle.addfile(member, io.BytesIO(raw))
        raw = stream.getvalue()
        if kind == "trailing":
            import gzip

            raw = gzip.compress(gzip.decompress(raw) + b"not zero")
        archive = tmp_path / "changed.tar.gz"
        archive.write_bytes(raw)
        checksum = a.sha(raw)
    with pytest.raises(ValueError):
        a.audit(archive, checksum, source, h, job)


def test_partial_accounting_is_pending_not_retry(tmp_path):
    target, _ = write_run(tmp_path)
    with pytest.raises(r.AccountingPending):
        r.collect(
            target,
            command=lambda *x, **k: (
                {"status": "complete", "returncode": 0},
                f"{JOB}|RUNNING|0:0|3\n".encode(),
            ),
        )
    assert not (target / "s2-academic-evidence.tar.gz").exists()


def test_native_worker_and_fresh_residual_replay(tmp_path, monkeypatch):
    from scripts import probe_npad_gurobi_license as license_probe
    from tests.test_mvp2_h300_native_worker import install_backend
    from tests.test_mvp2_h300_partial import fixture

    p = plan("native_miniature")
    result, data, config, _ = fixture("OPTIMAL", 1, 3)
    assert a.fixture() == (data, config)
    calls = []
    install_backend(monkeypatch, result, calls)
    monkeypatch.setattr(
        license_probe,
        "probe",
        lambda: {
            "status": "accepted",
            "gurobi_version": [13, 0, 3],
        },
    )
    w.native(tmp_path, p)
    values = records(p)
    for name in a.RECORDS:
        path = tmp_path / name
        if path.exists():
            values[name] = a.c.read_json(path)
    reviewed = a.review(p, JOB, values, accounting("native_miniature"))
    assert reviewed["disposition"] == "academic_stage_accepted"
    assert reviewed["native"]["validation"]["status"] == "accepted"
    altered = copy.deepcopy(values)
    altered["native/products/incumbent.json"]["objective_value"] = 999
    assert (
        a.review(p, JOB, altered, accounting("native_miniature"))["disposition"]
        == "evidence_not_accepted"
    )
    assert calls == ["build", "optimize", "extract", "dispose"]


def test_supervisor_normal_release_and_reap(tmp_path, monkeypatch):
    p = plan()
    start = records(p)["worker-start.json"]
    monkeypatch.setattr(os, "getuid", lambda: 1271, raising=False)
    r.d.write_new(tmp_path / "worker-start.json", start)
    polls = iter([None, 0])
    child = SimpleNamespace(poll=lambda: next(polls), wait=lambda **k: 0, returncode=0)
    r.supervise(
        tmp_path,
        p,
        JOB,
        child,
        clock=lambda: 0.0,
        pause=lambda _: None,
        command=lambda *x, **k: pytest.fail("Unexpected signal"),
    )
    assert a.c.read_json(tmp_path / "worker-release.json")["step_id"] == JOB + ".0"
    attempt = a.c.read_json(tmp_path / "attempt.json")
    assert attempt["local_client_reaped"] and not attempt["global_cleanup_proven"]


def test_batch_worker_dispatch_outside_slurm_denied(monkeypatch):
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    with pytest.raises(ValueError):
        r.main(["worker", "/unused"])
    with pytest.raises(ValueError):
        r.main(["batch", "/unused"])


def test_native_budget_and_h300_policy_remain_distinct():
    p = a.profile()
    assert sum(p["native"]["phase_seconds"]) == 2340
    assert p["native"]["wall_seconds"] - 2340 == 60
    assert a.design.policy()["budget"]["cleanup_grace_seconds"] == 300
    assert a.design.policy()["allocation"]["walltime_seconds"] == 21600


def test_old_negative_observer_not_reclassified():
    assert "max_user_namespaces" not in a.profile()["required"]
    assert a.profile()["purpose"] == "trusted_fixed_research_code_not_production_isolation"
    assert "blocked_environment" in (a.ROOT / "docs/mvp2_s2_profile_operational.md").read_text()


def test_explicit_cli_ack_and_grouped_predecessor_anchors(monkeypatch, tmp_path):
    monkeypatch.setattr(r, "BASE", tmp_path)
    monkeypatch.setattr(r.sys, "platform", "linux")
    monkeypatch.setattr(os, "getuid", lambda: 1271, raising=False)
    calls = []
    monkeypatch.setattr(r, "submit", lambda *x: calls.append(x) or (tmp_path, JOB))
    r.main(
        [
            "start",
            "build_failure",
            SOURCE,
            "--one-reviewed-academic-slot",
            "/archive",
            "b" * 64,
            SOURCE,
            "c" * 64,
            JOB,
        ]
    )
    assert calls == [("build_failure", SOURCE, [["/archive", "b" * 64, SOURCE, "c" * 64, JOB]])]


@pytest.mark.parametrize("action", ("start", "batch", "worker"))
def test_no_generic_admission_boolean_or_unbound_cli(action):
    with pytest.raises((PermissionError, ValueError)):
        r.main([action])


def test_worker_fresh_runtime_and_release(tmp_path, monkeypatch):
    p = plan()
    monkeypatch.setenv("SLURM_JOB_ID", JOB)
    monkeypatch.setenv("SLURM_STEP_ID", "0")
    monkeypatch.setattr(a, "runtime", lambda: p["runtime"])
    monkeypatch.setattr(os, "getuid", lambda: 1271, raising=False)
    monkeypatch.setattr(os, "sched_getaffinity", lambda _: {0, 32}, raising=False)
    affinity_calls = []
    monkeypatch.setattr(os, "sched_setaffinity", lambda *x: affinity_calls.append(x), raising=False)
    monkeypatch.setattr(w, "process_identity", lambda pid: {"pid": pid, "start_ticks": 10})
    r.d.write_new(
        tmp_path / "worker-release.json",
        {
            "job_id": JOB,
            "step_id": JOB + ".0",
            "plan_sha256": a.digest(p),
        },
    )
    assert w.run(tmp_path, p, JOB) == 0
    assert affinity_calls == [(0, [0])]
    assert a.c.read_json(tmp_path / "worker-start.json")["runtime_sha256"] == a.digest(p["runtime"])


@pytest.mark.parametrize("kind", ("job", "step", "runtime", "release"))
def test_worker_rejects_unbound_execution(tmp_path, monkeypatch, kind):
    p = plan()
    monkeypatch.setenv("SLURM_JOB_ID", "777" if kind == "job" else JOB)
    monkeypatch.setenv("SLURM_STEP_ID", "batch" if kind == "step" else "0")
    monkeypatch.setattr(a, "runtime", lambda: {} if kind == "runtime" else p["runtime"])
    monkeypatch.setattr(os, "getuid", lambda: 1271, raising=False)
    monkeypatch.setattr(os, "sched_getaffinity", lambda _: {0}, raising=False)
    monkeypatch.setattr(os, "sched_setaffinity", lambda *x: None, raising=False)
    monkeypatch.setattr(w, "process_identity", lambda pid: {"pid": pid, "start_ticks": 10})
    r.d.write_new(tmp_path / "worker-release.json", {"job_id": "777"})
    with pytest.raises(ValueError):
        w.run(tmp_path, p, JOB)
    assert not (tmp_path / "worker-result.json").exists()


def test_successful_submission_binds_receipt_and_request(tmp_path, monkeypatch):
    monkeypatch.setattr(r, "BASE", tmp_path)
    monkeypatch.setattr(r.d, "source_files", lambda *x: plan()["files"])
    monkeypatch.setattr(a, "runtime", lambda: plan()["runtime"])
    calls = []

    def command(argv, **kwargs):
        calls.append(argv)
        assert (r.claim_path("normal") / "submission-called.json").exists()
        return {"status": "complete", "returncode": 0}, JOB.encode()

    target, job = r.submit("normal", SOURCE, [], root=tmp_path, command=command)
    assert job == JOB
    assert "--mem=2048M" in calls[0] and "--cpus-per-task=2" in calls[0]
    assert "--time=12" in calls[0] and "--no-requeue" in calls[0]
    assert a.c.read_json(target / "job.json")["job_id"] == JOB


@pytest.mark.parametrize("ack", (b"12345;cluster", b"12345\n777", b"", b"not a job"))
def test_ambiguous_ack_never_guesses_job(tmp_path, monkeypatch, ack):
    monkeypatch.setattr(r, "BASE", tmp_path)
    monkeypatch.setattr(r.d, "source_files", lambda *x: plan()["files"])
    monkeypatch.setattr(a, "runtime", lambda: plan()["runtime"])
    with pytest.raises(ValueError, match="Ambiguous acknowledgement"):
        r.submit(
            "normal",
            SOURCE,
            [],
            root=tmp_path,
            command=lambda *x, **k: ({"status": "complete", "returncode": 0}, ack),
        )
    assert not (r.claim_path("normal") / "job.json").exists()
    assert (r.claim_path("normal") / "submission-called.json").exists()


def test_corrupted_cached_sidecar_stops_without_query(tmp_path):
    target, _ = write_run(tmp_path)
    archive, _, _ = r.collect(
        target,
        command=lambda *x, **k: ({"status": "complete", "returncode": 0}, accounting().encode()),
    )
    archive.with_suffix(archive.suffix + ".sha256").write_text("0" * 64)
    with pytest.raises(ValueError, match="Archive checksum"):
        r.collect(target, command=lambda *x, **k: pytest.fail("Cached archive queried scheduler"))


def test_cleanup_command_failure_keeps_local_reap_receipt(tmp_path, monkeypatch):
    p = plan("nested_setsid_term_ignore")
    values = records(p)
    monkeypatch.setattr(os, "getuid", lambda: 1271, raising=False)
    r.d.write_new(tmp_path / "worker-start.json", values["worker-start.json"])
    r.d.write_new(tmp_path / "nested.json", {"identities": []})
    child = SimpleNamespace(poll=lambda: None, wait=lambda **k: 0, returncode=0)
    r.supervise(
        tmp_path,
        p,
        JOB,
        child,
        clock=lambda: 0.0,
        pause=lambda _: None,
        command=lambda *x, **k: (_ for _ in ()).throw(OSError()),
    )
    value = a.c.read_json(tmp_path / "attempt.json")
    assert value["stop_reason"] == "cleanup_query_failure"
    assert value["local_client_reaped"] and not value["global_cleanup_proven"]
