"""Offline qualification only; no scheduler, solver, signal or NPAD effect."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_s2_fast_exit as f
from scripts import mvp2_s2_fast_exit_observation as o
from scripts import mvp2_s2_followup_inventory as followup

C = "c" * 40
J = "12345"
H = "a" * 64
BINDING = {
    "job_id": J,
    "worker_step_id": "0",
    "supervisor_step_id": "batch",
    "source_commit": C,
    "nonce": H,
}
HEADER = "PID JOBID STEPID LOCALID GLOBALID\n"


def unavailable():
    return {"status": "unavailable", "value": None}


def report():
    value = o.new_report(C, J, H)
    value.update(
        status="observed_not_admitted",
        phase="complete",
        step_id="0",
        initial_sha256=H,
        local_client_returncode=0,
        samples=[
            {
                "offset_seconds": offset,
                "elapsed_seconds": offset + 0.1,
                "channels": {key: unavailable() for key in f.CHANNELS},
            }
            for offset in f.OFFSETS
        ],
    )
    return value


@pytest.mark.parametrize(
    "exc,status",
    [
        (FileNotFoundError(), "missing"),
        (PermissionError(), "denied"),
        (ValueError(), "invalid"),
        (UnicodeError(), "invalid"),
        (OSError(), "unavailable"),
        (TimeoutError(), "unavailable"),
    ],
)
def test_error_classes_no_messages(exc, status):
    def fail():
        raise exc

    assert f.channel(fail) == {"status": status, "value": None}


def test_available_zero_and_empty_are_not_unknown():
    assert f.channel(lambda: 0) == {"status": "available", "value": 0}
    assert f.channel(lambda: []) == {"status": "available", "value": []}
    with pytest.raises(ValueError):
        f.validate_channel({"status": "missing", "value": []}, f.pids)


def make_scope(tmp_path, name="memory"):
    root = tmp_path / name
    root.mkdir()
    for filename in f.FILES[name]:
        text = (
            "" if filename == "cgroup.procs" else "THAWED" if filename == "freezer.state" else "0"
        )
        (root / filename).write_text(text, encoding="ascii")
    return root


@pytest.mark.parametrize("name", f.s.CONTROLLERS)
def test_controller_regular_fixture_and_missing_file_independent(tmp_path, name):
    root = make_scope(tmp_path, name)
    good = f.controller(root, f.FILES[name])
    assert good["files"]["cgroup.procs"]["value"] == []
    (root / "cgroup.procs").unlink()
    partial = f.controller(root, f.FILES[name], good["identity"])
    assert partial["files"]["cgroup.procs"]["status"] == "missing"
    assert all(
        v["status"] == "available" for k, v in partial["files"].items() if k != "cgroup.procs"
    )
    f.validate_controllers(
        {
            key: f.channel(lambda: partial) if key == name else unavailable()
            for key in f.s.CONTROLLERS
        }
    )


def test_missing_directory_distinct_from_missing_file(tmp_path):
    root = make_scope(tmp_path)
    ident = f.controller(root, f.FILES["memory"])["identity"]
    for path in root.iterdir():
        path.unlink()
    root.rmdir()
    assert f.channel(lambda: f.controller(root, f.FILES["memory"], ident))["status"] == "missing"


def test_replaced_directory_not_retained_empty(tmp_path):
    root = make_scope(tmp_path)
    with pytest.raises(ValueError, match="Replaced"):
        f.controller(root, f.FILES["memory"], [0, 0])


@pytest.mark.parametrize("text", ["-1", "NaN", "1\n1", "0", "nobody"])
def test_invalid_members_do_not_become_empty(tmp_path, text):
    root = make_scope(tmp_path)
    (root / "cgroup.procs").write_text(text, encoding="ascii")
    assert f.controller(root, f.FILES["memory"])["files"]["cgroup.procs"]["status"] == "invalid"


def query_command(stdout, *, rc=0, status="complete"):
    def call(argv, **kwargs):
        assert kwargs["timeout"] == 2
        return {"status": status, "returncode": rc}, stdout

    return call


@pytest.mark.parametrize(
    "raw", [b"No job steps found\n", b"", b"PID JOBID STEPID LOCALID GLOBALID\n1 99 0 0 0\n"]
)
def test_bad_listpids_never_empty(raw):
    result = f.channel(
        lambda: f.query(
            ["scontrol"], lambda text: sorted(f.q.parse_listpids(text, BINDING)), query_command(raw)
        )
    )
    assert result["status"] == "invalid" and result["value"] is None


def test_header_only_is_observed_empty_not_cleanup():
    result = f.query(
        ["scontrol"],
        lambda text: sorted(f.q.parse_listpids(text, BINDING)),
        query_command(HEADER.encode()),
    )
    assert result["data"] == []
    assert all(v is False for v in f.FLAGS.values())


@pytest.mark.parametrize("rc,status", [(1, "complete"), (0, "timeout"), (0, "output_limit")])
def test_failed_query_unknown(rc, status):
    assert f.channel(
        lambda: f.query([], lambda text: [], query_command(b"", rc=rc, status=status))
    ) == {"status": "unavailable", "value": None}


def test_products_prefix_preserved_and_nonce_checked(tmp_path):
    root = tmp_path / "worker"
    root.mkdir()
    (root / "phase-0.json").write_text(json.dumps({"nonce": H, "phase": "build"}))
    (root / "phase-1.json").write_text(json.dumps({"nonce": "b" * 64, "phase": "optimization"}))
    value = f.products(root, H)
    assert value["phase-0.json"]["status"] == "available"
    assert value["phase-1.json"]["status"] == "invalid"
    assert value["terminal.json"]["status"] == "missing"
    f.validate_products(value)


def test_four_phases_immediate_return_no_nested(tmp_path):
    def forbidden():
        raise AssertionError("No nested process allowed")

    o.worker.exercise_components(
        "normal", tmp_path / "worker", H, release=lambda: True, nested_factory=forbidden
    )
    assert all(v["status"] == "available" for v in f.products(tmp_path / "worker", H).values())


def test_known_pid_absence_and_reuse_not_descendants(tmp_path):
    identity = {"pid": 12, "uid": 1, "starttime": 100, "state": "S"}
    assert f.leader(identity, tmp_path) == "known_pid_absent"
    root = tmp_path / "12"
    root.mkdir()
    (root / "stat").write_text("12 (leaf) S " + "0 " * 18 + "101\n")
    assert f.leader(identity, tmp_path) == "pid_reused"


def test_independent_channels_survive_missing_scopes(monkeypatch, tmp_path):
    monkeypatch.setattr(f, "leader", lambda identity: "known_pid_absent")
    tools = {"scontrol": "control", "sacct": "acct"}

    def command(argv, **kwargs):
        if "listpids" in argv:
            return {"status": "complete", "returncode": 0}, b"No job steps found\n"
        if argv[0] == "acct":
            return {"status": "complete", "returncode": 0}, f"{J}.0|COMPLETED|0:0|1\n".encode()
        return {"status": "complete", "returncode": 0}, b"StepId=12345.0 State=COMPLETED"

    scopes = {k: {"scope": str(tmp_path / k)} for k in f.s.CONTROLLERS}
    actual = f.sample(
        BINDING,
        scopes,
        dict.fromkeys(f.s.CONTROLLERS, [0, 0]),
        {},
        tmp_path,
        tools,
        command=command,
    )
    assert actual["members"]["status"] == "invalid"
    assert all(x["status"] == "missing" for x in actual["controllers"]["value"].values())
    assert actual["accounting"]["value"]["data"][J + ".0"]["state"] == "COMPLETED"
    assert actual["leader"]["value"] == "known_pid_absent"
    value = report()
    value["samples"][0]["channels"] = actual
    f.validate_report(value, C, J, H)


@pytest.mark.parametrize(
    "key,value",
    [
        ("source_commit", "b" * 40),
        ("job_id", "54321"),
        ("plan_sha256", "b" * 64),
        ("step_id", "batch"),
        ("local_client_returncode", 2),
        ("error_kind", "private message"),
        ("phase", "identity"),
        ("live_containment_qualified", True),
    ],
)
def test_report_rejects_anchor_or_admission_drift(key, value):
    item = report()
    item[key] = value
    with pytest.raises(ValueError):
        f.validate_report(item, C, J, H)


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True, 241])
def test_report_rejects_bad_actual_time(value):
    item = report()
    item["samples"][0]["elapsed_seconds"] = value
    with pytest.raises(ValueError):
        f.validate_report(item, C, J, H)


def test_report_requires_full_bounded_sequence():
    item = report()
    item["samples"].pop()
    with pytest.raises(ValueError):
        f.validate_report(item, C, J, H)
    item["status"] = "blocked_environment"
    f.validate_report(item, C, J, H)


def records(value=None):
    return {
        "anchor.json": {
            "schema_version": "s2-fast-exit-carrier-v1",
            "source_commit": C,
            "job_id": J,
            "plan_sha256": H,
            **f.FLAGS,
        },
        "observation.json": value,
        "accounting.json": f.a.accounting(
            f"{J}|COMPLETED|0:0|20\n{J}.batch|COMPLETED|0:0|20\n{J}.0|COMPLETED|0:0|1", J
        ),
        "entry.json": {
            "invalid_observation_sha256": None,
            "leaf": {"status": "missing", "value": None},
            **{
                key: {
                    "status": "available",
                    "value": {"bytes": 0, "sha256": f.d.digest(b""), "diagnostics": []},
                }
                for key in ("stdout", "stderr", "client_stdout", "client_stderr")
            },
        },
    }


@pytest.mark.parametrize("value", [None, report()])
def test_portable_complete_or_forensic_replay_no_promotion(tmp_path, value):
    archive = tmp_path / "evidence.tar.gz"
    f.d.pack(archive, records(value))
    result = f.audit(archive, f.a.sha_file(archive), C, J, H)
    assert "not_qualified" in result["status"]
    assert all(result[key] is False for key in f.FLAGS)


@pytest.mark.parametrize("status", ["missing", "denied", "invalid", "unavailable"])
def test_unknown_channel_cannot_carry_observed_value(status):
    with pytest.raises(ValueError):
        f.validate_channel({"status": status, "value": 0}, lambda v: None)


@pytest.mark.parametrize("kind", ["foreign", "duplicate", "truncated", "nonterminal"])
def test_accounting_does_not_accept_foreign_or_partial_final(kind):
    text = f"{J}|COMPLETED|0:0|20\n{J}.batch|COMPLETED|0:0|20"
    if kind == "foreign":
        text += "\n99|COMPLETED|0:0|2"
    if kind == "duplicate":
        text += f"\n{J}|COMPLETED|0:0|20"
    if kind == "truncated":
        text = text.replace("COMPLETED", "COMPLET+")
    if kind == "nonterminal":
        text = text.replace("COMPLETED", "RUNNING")
        rows = f.a.accounting(text, J)
        assert any(row["state"] not in f.a.TERMINAL for row in rows.values())
    else:
        with pytest.raises(ValueError):
            f.a.accounting(text, J)


def test_cancellation_attribution_is_terminal_not_success():
    rows = f.a.accounting(f"{J}.0|CANCELLED by 1271|0:9|4", J)
    assert rows[J + ".0"]["state"] == "CANCELLED"
    assert rows[J + ".0"]["exit_code"] == "0:9"


def test_structured_entry_diagnostic_no_message_or_path(tmp_path):
    record = {
        "schema_version": "s2-fast-exit-entry-v1",
        "role": "leaf",
        "error_kind": "missing",
        "site": {"module": "mvp2_s2_fast_exit_observation", "line": 12},
        **f.FLAGS,
    }
    path = tmp_path / "stderr"
    path.write_bytes(b"private unstructured traceback\n" + f.d.encode(record))
    value = f.entry_log(path)
    assert value["value"]["diagnostics"] == [record]
    assert "private" not in json.dumps(value)
    record["message"] = "secret"
    path.write_bytes(f.d.encode(record))
    assert f.entry_log(path)["status"] == "invalid"


def test_oversized_entry_does_not_prevent_other_evidence(tmp_path):
    path = tmp_path / "large"
    path.write_bytes(b"x" * 65537)
    assert f.entry_log(path) == {"status": "invalid", "value": None}


def test_early_compute_entry_emits_redacted_diagnostic(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(o, "BASE", tmp_path)

    def fail(*args):
        raise FileNotFoundError("do not export private path")

    monkeypatch.setattr(o, "batch", fail)
    assert o.main(["batch", "--source-sha", C, "--plan-sha", H]) == 2
    stderr = capsys.readouterr().err
    record = f.d.decode(stderr.encode())
    f.validate_entry(record)
    assert record["error_kind"] == "missing" and "private" not in stderr


def plan_fixture(tmp_path):
    root = tmp_path / "s2-fast-exit-driver-Ab12Cd34" / "source"
    return {
        "schema_version": "s2-fast-exit-plan-v1",
        "source_commit": C,
        "checkout": str(root),
        "files": {o.ENTRY: H},
        "run": str(tmp_path / "s2fx-ab123456"),
        "python": str(tmp_path / "python"),
        "python_sha256": H,
        "nonce": H,
        "tools": {k: str(tmp_path / k) for k in o.TOOLS},
        "tools_sha256": dict.fromkeys(o.TOOLS, H),
        "predecessor": o.PARENT,
        **f.FLAGS,
    }


@pytest.mark.parametrize(
    "kind", ["source", "parent", "nonce", "authority", "extra", "run", "tool", "digest"]
)
def test_plan_rejects_identity_and_location_drift(monkeypatch, tmp_path, kind):
    monkeypatch.setattr(o, "BASE", tmp_path)
    plan = plan_fixture(tmp_path)
    sha = o.validate_plan(plan, C)
    if kind == "source":
        plan["source_commit"] = "d" * 40
    elif kind == "parent":
        plan["predecessor"] = {}
    elif kind == "nonce":
        plan["nonce"] = "bad"
    elif kind == "authority":
        plan["production_admitted"] = True
    elif kind == "extra":
        plan["command"] = "arbitrary"
    elif kind == "run":
        plan["run"] = str(tmp_path / "old-claim")
    elif kind == "tool":
        plan["tools"]["git"] = str(tmp_path / "git")
    else:
        sha = "0" * 64
    with pytest.raises(ValueError):
        o.validate_plan(plan, C, sha)


def test_job_acknowledgement_exact_source_plan_and_batch_identity(monkeypatch, tmp_path):
    monkeypatch.setattr(o, "BASE", tmp_path)
    o.claim_path().mkdir()
    o.d.write_new(o.claim_path() / "job.json", {"job_id": J, "source_commit": C, "plan_sha256": H})
    assert o.job_receipt({"source_commit": C}, H) == J
    monkeypatch.setenv("SLURM_JOB_ID", "99999")
    with pytest.raises(ValueError):
        o.job_receipt({"source_commit": C}, H, batch=True)


@pytest.mark.parametrize(
    "kind", ["job", "uid", "node", "cpus", "step", "limits", "affinity", "members"]
)
def test_initial_gate_rejects_without_release(monkeypatch, tmp_path, kind):
    job = (
        f"JobId={J} UserId=user(1) JobState=RUNNING NumNodes=1 NumCPUs=2 "
        "NodeList=node BatchHost=node TimeLimit=00:05:00 MinMemoryNode=2G"
    )
    step = (
        f"StepId={J}.0 UserId=1 Nodes=1 NodeList=node State=RUNNING "
        "CPUs=1 Tasks=1 TimeLimit=00:02:00"
    )
    private = {
        role: {
            "raw": {"status": "Cpus_allowed_list:\t0\n", "cgroup": "", "mountinfo": ""},
            "identity": {"pid": 12},
        }
        for role in ("worker", "supervisor")
    }
    limits = {
        role: {
            "error_kind": None,
            "cpuset_cpu_count": 2,
            "memory_limit_bytes": ceiling,
            "hierarchical_memory_limit_bytes": ceiling,
        }
        for role, ceiling in (("worker", 256 * 1024**2), ("supervisor", 2048 * 1024**2))
    }
    if kind == "job":
        job = job.replace("JobId=" + J, "JobId=99999")
    elif kind == "uid":
        job = job.replace("user(1)", "user(2)")
    elif kind == "node":
        job = job.replace("NodeList=node", "NodeList=other")
    elif kind == "cpus":
        job = job.replace("NumCPUs=2", "NumCPUs=3")
    elif kind == "step":
        step = step.replace("StepId=" + J + ".0", "StepId=" + J + ".1")
    elif kind == "limits":
        limits["worker"]["cpuset_cpu_count"] = 3
    elif kind == "affinity":
        private["worker"]["raw"]["status"] = "Cpus_allowed_list:\t0,32\n"
    monkeypatch.setattr(f.scope, "limits", lambda private: limits)
    members = HEADER + f"{13 if kind == 'members' else 12} {J} 0 0 0\n"
    with pytest.raises(ValueError):
        f.review_initial(private, job, step, members, BINDING, 1, "node")


def test_full_terminal_collection_replays_unchanged_originals(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(o, "BASE", tmp_path)
    monkeypatch.setattr(o.d, "host", lambda: None)
    claim = o.claim_path()
    claim.mkdir()
    run = tmp_path / "s2fx-ab123456"
    run.mkdir()
    original = f.d.encode(report())
    (run / "observation.json").write_bytes(original)
    (claim / "slurm-12345.err").write_text("")
    plan = {"run": str(run), "source_commit": C, "tools": {"sacct": "acct"}}
    monkeypatch.setattr(o, "load_plan", lambda commit: (plan, H))
    monkeypatch.setattr(o, "runtime", lambda *args: None)
    monkeypatch.setattr(o, "job_receipt", lambda *args: J)
    (claim / "job.json").write_text("{}")
    queries = []

    def command(argv, **kwargs):
        queries.append(argv)
        return {"status": "complete", "returncode": 0}, (
            f"{J}|COMPLETED|0:0|20\n{J}.batch|COMPLETED|0:0|20\n{J}.0|COMPLETED|0:0|1"
        ).encode()

    monkeypatch.setattr(o.d, "command", command)
    assert o.collect(C) == 0
    assert o.collect(C) == 0 and len(queries) == 1
    assert (run / "observation.json").read_bytes() == original
    assert "DOWNLOAD=" in capsys.readouterr().out


def test_source_requires_no_follow_on_admission():
    assert o.CLAIM != ".mvp2-s2-resource-normal-v1"
    assert (
        o.PARENT["archive_sha256"]
        == "0239bbec7edd29cf384e7949d441ec6fb3e8474f77c735799978620fc74aa642"
    )
    source = Path(o.__file__).read_text()
    assert "scancel" not in source and "afterok" not in source


def test_forensic_leaf_binding_survives_missing_observation(monkeypatch, tmp_path):
    monkeypatch.setattr(o, "BASE", tmp_path)
    run = tmp_path / "run"
    run.mkdir()
    o.claim_path().mkdir()
    f.d.write_new(run / "leaf-role.json", {"job_id": J, "step_id": "0", "plan_sha256": H})
    value = o.capture_collection({"source_commit": C, "run": str(run)}, H, J)
    assert value["observation.json"] is None
    assert value["entry.json"]["leaf"]["value"]["step_id"] == "0"


def test_forensic_leaf_requires_numeric_step_even_without_observation(tmp_path):
    value = records(None)
    value["entry.json"]["leaf"] = {"status": "available", "value": {"step_id": "0", "sha256": H}}
    value["accounting.json"].pop(J + ".0")
    archive = tmp_path / "incomplete.tar.gz"
    f.d.pack(archive, value)
    with pytest.raises(ValueError, match="exact-step"):
        f.audit(archive, f.a.sha_file(archive), C, J, H)


def test_bad_nested_report_types_collect_as_forensic(monkeypatch, tmp_path):
    monkeypatch.setattr(o, "BASE", tmp_path)
    run = tmp_path / "run"
    run.mkdir()
    o.claim_path().mkdir()
    for key, value in (("status", []), ("initial", 1), ("error_site", {"module": [], "line": 1})):
        item = report()
        item[key] = value
        (run / "observation.json").write_bytes(f.d.encode(item))
        result = o.capture_collection({"source_commit": C, "run": str(run)}, H, J)
        assert result["observation.json"] is None
        assert result["entry.json"]["invalid_observation_sha256"] is not None


def test_downstream_inventory_preserves_grid_and_five_cases():
    value = followup.planned_slots()
    assert [x["arm"] for x in value if x["package"] == "P2"] == list(followup.ADVERSE)
    assert [x["threads"] for x in value if x["package"] == "P4"] == [4, 1, 8, 2, 16]
    assert followup.review_inventory(value)["slots"] == 11
    assert all(x["state"] == "unrun" and x["production_admitted"] is False for x in value)


@pytest.mark.parametrize("change", ["reorder", "omit", "completed", "admit"])
def test_downstream_inventory_cannot_promote_missing_experiments(change):
    value = followup.planned_slots()
    if change == "reorder":
        value.reverse()
    elif change == "omit":
        value.pop()
    elif change == "completed":
        value[0]["state"] = "completed"
    else:
        value[0]["production_admitted"] = True
    with pytest.raises(ValueError):
        followup.review_inventory(value)


@pytest.mark.parametrize(
    "kind", ["checksum", "source", "job", "plan", "extra", "step_missing", "active"]
)
def test_archive_rejects_drift(tmp_path, kind):
    value = records(report())
    if kind == "extra":
        value["private.json"] = {"message": "do not export"}
    if kind == "step_missing":
        value["accounting.json"].pop(J + ".0")
    if kind == "active":
        value["accounting.json"][J]["state"] = "RUNNING"
    archive = tmp_path / "bad.tar.gz"
    f.d.pack(archive, value)
    with pytest.raises(ValueError):
        f.audit(
            archive,
            "0" * 64 if kind == "checksum" else f.a.sha_file(archive),
            "b" * 40 if kind == "source" else C,
            "23456" if kind == "job" else J,
            "b" * 64 if kind == "plan" else H,
        )


@pytest.mark.parametrize(
    "action", ["normal", "adverse", "native", "h300", "retry", "admit", "reset"]
)
def test_unadmitted_cli_verbs_deny_before_host(monkeypatch, action):
    monkeypatch.setattr(o.d, "host", lambda: pytest.fail("No host/effect permitted"))
    with pytest.raises(SystemExit):
        o.main([action, "--source-sha", C])


def test_descriptors_fixed_no_solver_no_scancel(monkeypatch, tmp_path):
    monkeypatch.setattr(o, "BASE", tmp_path)
    plan = {
        "tools": {"sbatch": "sbatch", "srun": "srun"},
        "python": "/python",
        "source_commit": C,
        "checkout": "/source",
    }
    submit, leaf = o.submit_argv(plan), o.worker_argv(plan, H, J)
    assert "--time=00:05:00" in submit and "--mem=2048M" in submit
    assert "--cpus-per-task=2" in submit and "--export=NONE" in submit
    assert "--time=00:02:00" in leaf and "--cpus-per-task=1" in leaf and "--mem=256M" in leaf
    assert "--cpu-bind=threads" in leaf and "--exact" in leaf
    assert not any("scancel" in x or "gurobi" in x.lower() for x in submit + leaf)


def test_existing_claim_start_is_collect_only(monkeypatch, tmp_path):
    monkeypatch.setattr(o, "BASE", tmp_path)
    monkeypatch.setattr(o.d, "host", lambda: None)
    o.claim_path().mkdir()
    monkeypatch.setattr(o, "collect", lambda commit: 17)
    monkeypatch.setattr(o.d, "command", lambda *a, **k: pytest.fail("No resubmission"))
    assert o.start(C) == 17


def test_no_acknowledgement_never_guesses_job(monkeypatch, tmp_path):
    monkeypatch.setattr(o, "BASE", tmp_path)
    monkeypatch.setattr(o.d, "host", lambda: None)
    monkeypatch.setattr(o, "load_plan", lambda commit: ({}, H))
    monkeypatch.setattr(o, "runtime", lambda *args: None)
    monkeypatch.setattr(o.d, "command", lambda *a, **k: pytest.fail("No guessed query"))
    assert o.collect(C) == 3


def test_cache_collection_does_not_query_or_recapture(monkeypatch, tmp_path):
    monkeypatch.setattr(o, "BASE", tmp_path)
    monkeypatch.setattr(o.d, "host", lambda: None)
    o.claim_path().mkdir()
    o.d.write_new(o.claim_path() / "job.json", {"placeholder": True})
    o.d.write_new(o.claim_path() / "collection.json", {"cached": True})
    monkeypatch.setattr(o, "load_plan", lambda commit: ({}, H))
    monkeypatch.setattr(o, "runtime", lambda *args: None)
    monkeypatch.setattr(o, "job_receipt", lambda *args: J)
    monkeypatch.setattr(
        o, "show_collection", lambda receipt, *args: 0 if receipt == {"cached": True} else 9
    )
    monkeypatch.setattr(o.d, "command", lambda *a, **k: pytest.fail("No query on replay"))
    monkeypatch.setattr(
        o, "capture_collection", lambda *a, **k: pytest.fail("No recapture on replay")
    )
    assert o.collect(C) == 0


def test_terminal_capture_missing_and_invalid_reports_preserved(monkeypatch, tmp_path):
    monkeypatch.setattr(o, "BASE", tmp_path)
    run = tmp_path / "run"
    run.mkdir()
    o.claim_path().mkdir()
    plan = {"source_commit": C, "run": str(run)}
    diagnostic = {
        "schema_version": "s2-fast-exit-entry-v1",
        "role": "leaf",
        "error_kind": "missing",
        "site": None,
        **f.FLAGS,
    }
    (run / "srun.err").write_bytes(f.d.encode(diagnostic))
    assert o.capture_collection(plan, H, J)["entry.json"]["client_stderr"]["value"][
        "diagnostics"
    ] == [diagnostic]
    assert o.capture_collection(plan, H, J)["observation.json"] is None
    (run / "observation.json").write_text('{"broken":true}')
    result = o.capture_collection(plan, H, J)
    assert result["observation.json"] is None
    assert result["entry.json"]["invalid_observation_sha256"] == f.a.sha_file(
        run / "observation.json"
    )


def test_runtime_batch_never_reads_login_only_git_or_sbatch(monkeypatch, tmp_path):
    reads = []
    monkeypatch.setattr(o.d, "verify_tree", lambda *args: None)
    monkeypatch.setattr(o.a, "sha_file", lambda path, *args: reads.append(str(path)) or H)
    plan = {
        "checkout": str(tmp_path),
        "files": {},
        "python": str(Path(o.sys.executable).resolve()),
        "python_sha256": H,
        "tools": {k: "/" + k for k in o.TOOLS},
        "tools_sha256": dict.fromkeys(o.TOOLS, H),
    }
    o.runtime(plan, "batch")
    assert set(reads[1:]) == {"/srun", "/scontrol", "/sacct"}


def test_wrapper_one_shot_and_no_cache_contract():
    text = (Path(__file__).parents[1] / "scripts/npad_s2_fast_exit_observation.sh").read_text()
    assert "PYTHONDONTWRITEBYTECODE=1" in text and "no:cacheprovider" in text
    assert "ACTION=collect" in text and "verify_source" in text
    assert '--basetemp="$BOOTSTRAP/tests"' in text
    assert "rm -" not in text and "git reset" not in text


def test_batch_fake_fast_exit_five_independent_samples(monkeypatch, tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    monkeypatch.setattr(o.d, "host", lambda: None)
    monkeypatch.setattr(o, "runtime", lambda *args: None)
    monkeypatch.setattr(
        o,
        "load_plan",
        lambda *args: (
            {"run": str(run), "nonce": H, "source_commit": C, "tools": {"scontrol": "control"}},
            H,
        ),
    )
    monkeypatch.setattr(o, "job_receipt", lambda *a, **k: J)
    monkeypatch.setattr(o, "worker_argv", lambda *args: ["fixed-leaf"])
    monkeypatch.setattr(o.os, "getuid", lambda: 1, raising=False)
    monkeypatch.setattr(o.os, "uname", lambda: SimpleNamespace(nodename="node"), raising=False)
    peer = {"pid": 12, "uid": 1}
    private = {"identity": {**peer, "starttime": 1, "state": "S"}}
    monkeypatch.setattr(o.scope, "capture", lambda pid: copy.deepcopy(private))
    monkeypatch.setattr(o.f, "initial_record", lambda private: {"summary": None, "limits": None})
    monkeypatch.setattr(o.f, "review_initial", lambda *args: ({}, {}))
    monkeypatch.setattr(
        o.d, "command", lambda *a, **k: ({"status": "complete", "returncode": 0}, b"safe")
    )
    clock = [0.0]
    monkeypatch.setattr(o.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(o.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))

    class Server:
        def __init__(self, path):
            self.released = False

        def accept(self, timeout):
            return {"job_id": J, "step_id": "0", "plan_sha256": H}, peer

        def release(self, value, timeout):
            assert value == {"observe_fast_exit": H}
            self.released = True

        def close(self):
            pass

    monkeypatch.setattr(o.a, "BarrierServer", Server)

    class Child:
        returncode = 0

        def __init__(self, *args, **kwargs):
            assert args[0] == ["fixed-leaf"]

        def wait(self, timeout):
            assert timeout == 60
            return self.returncode

        def poll(self):
            return 0

    monkeypatch.setattr(o.subprocess, "Popen", Child)
    monkeypatch.setattr(
        o.f, "sample", lambda *args, **kwargs: {key: unavailable() for key in f.CHANNELS}
    )
    assert o.batch(C, H) == 0
    result = o.d.load(run / "observation.json")
    assert result["status"] == "observed_not_admitted" and len(result["samples"]) == 5
    assert [sample["elapsed_seconds"] for sample in result["samples"]] == list(f.OFFSETS)
    assert all(result[key] is False for key in f.FLAGS)
    run = tmp_path / "failed-run"
    run.mkdir()
    Child.returncode = 2
    assert o.batch(C, H) == 2
    failed = o.d.load(run / "observation.json")
    assert failed["status"] == "incomplete" and failed["local_client_returncode"] == 2
    assert len(failed["samples"]) == 5
