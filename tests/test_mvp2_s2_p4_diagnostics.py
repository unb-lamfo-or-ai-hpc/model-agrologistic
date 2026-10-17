"""P4 prospective diagnostic qualification; no real license, native model or Slurm."""

import copy
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_s2_p4_diagnostics as q


def identity(threads=4):
    return {
        "source_commit": "a" * 40,
        "plan_sha256": "b" * 64,
        "step_id": "123.0",
        "threads": threads,
    }


def select(tmp_path, monkeypatch, *, ident=None, check=None):
    ident = identity() if ident is None else ident
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setenv("SLURM_STEP_ID", "0")
    calls = []

    def checker():
        assert os.environ["GRB_LICENSE_FILE"] == q.license_probe.LICENSE_FILE
        calls.append("metadata_only")
        if check is not None:
            return check()

    record = q._select_worker_license(tmp_path, ident, check=checker)
    return record, calls


@pytest.mark.parametrize("previous", [None, "wrong-file", q.license_probe.LICENSE_FILE])
def test_worker_selection_before_metadata_without_probe(tmp_path, monkeypatch, previous):
    if previous is None:
        monkeypatch.delenv("GRB_LICENSE_FILE", raising=False)
    else:
        monkeypatch.setenv("GRB_LICENSE_FILE", previous)
    monkeypatch.setattr(q.license_probe, "probe", lambda: pytest.fail("capability probe"))
    record, calls = select(tmp_path, monkeypatch)
    assert calls == ["metadata_only"]
    assert record == q._license_record(identity(), True)
    text = (tmp_path / q.NAMES[0]).read_text()
    assert q.license_probe.LICENSE_FILE not in text
    assert "WLSSecret" not in text
    assert all(record[k] is False for k in q.CLOSED)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("source_commit", "a" * 39),
        ("source_commit", True),
        ("plan_sha256", "b" * 63),
        ("plan_sha256", None),
        ("step_id", "123.batch"),
        ("step_id", "123"),
        ("step_id", "123.00"),
        ("step_id", "0.0"),
        ("step_id", "123.0; scancel 123"),
        ("threads", True),
        ("threads", 3),
        ("threads", "4"),
    ],
)
def test_bad_binding_before_license_or_publication(tmp_path, field, bad):
    ident = {**identity(), field: bad}
    with pytest.raises(ValueError, match="binding schema"):
        q._select_worker_license(tmp_path, ident, check=lambda: pytest.fail("license"))
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("step", ["1", "batch", "", "00"])
def test_worker_step_mismatch_before_license(tmp_path, monkeypatch, step):
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setenv("SLURM_STEP_ID", step)
    with pytest.raises(ValueError, match="numeric-step"):
        q._select_worker_license(tmp_path, identity(), check=lambda: pytest.fail("license"))
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("failure", [OSError, ValueError, RuntimeError])
def test_metadata_failure_preserves_safe_negative_receipt(tmp_path, monkeypatch, failure):
    def fail():
        raise failure("PRIVATE-WLS-SECRET /private/license")

    with pytest.raises(ValueError, match="metadata check failed") as caught:
        select(tmp_path, monkeypatch, check=fail)
    assert "PRIVATE" not in str(caught.value)
    text = (tmp_path / q.NAMES[0]).read_text()
    assert "PRIVATE" not in text and "/private" not in text
    assert q.products.read(tmp_path / q.NAMES[0]) == q._license_record(identity(), False)
    assert q.catalogue(tmp_path, identity())["native_return_observed"] is False
    with pytest.raises(ValueError):
        q.NativeSeams(tmp_path, identity(), None, q.native.solver_profile(4))


def test_existing_receipt_never_selects_again(tmp_path, monkeypatch):
    select(tmp_path, monkeypatch)
    before = (tmp_path / q.NAMES[0]).read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        q._select_worker_license(tmp_path, identity(), check=lambda: pytest.fail("repeat"))
    assert (tmp_path / q.NAMES[0]).read_bytes() == before


def fixture(tmp_path, monkeypatch, threads=4):
    ident = identity(threads)
    directory = tmp_path / "diagnostics"
    directory.mkdir()
    select(directory, monkeypatch, ident=ident)
    journal = q.controls.PhaseJournal(
        tmp_path / "native", q.design.digest({"plan": ident["plan_sha256"], "threads": threads})
    )
    journal.enter("build")
    tick = [0.0]
    hook = q.NativeSeams(
        directory, ident, journal, q.native.solver_profile(threads), clock=lambda: tick[0]
    )
    params = SimpleNamespace(
        TimeLimit=1800,
        Threads=threads,
        Seed=42,
        MIPGap=0.1,
        SoftMemLimit=128,
        NumericFocus=1,
        OutputFlag=0,
    )
    model = SimpleNamespace(Params=params, SolCount=0, Status=9, Runtime=1801, MaxMemUsed=1)
    grb = SimpleNamespace(OPTIMAL=2, TIME_LIMIT=9, MEM_LIMIT=17)
    return directory, ident, journal, tick, hook, model, grb


@pytest.mark.parametrize("threads", q.design.GRID)
def test_typed_milestones_delegate_actual_native_hooks(tmp_path, monkeypatch, threads):
    directory, ident, journal, tick, hook, model, grb = fixture(tmp_path, monkeypatch, threads)
    before = vars(model.Params).copy()
    for at, phase in [(1, "native_ready"), (2, "optimization"), (1803, "export_validation")]:
        tick[0] = at
        hook(phase, model, grb)
    assert vars(model.Params) == before  # No parameter change/callback installed.
    assert journal.index == 3 and hook.terminal["solution_count"] == 0
    assert hook.terminal["native_status_code"] == 9
    receipt = q.catalogue(directory, ident)
    assert receipt["native_return_observed"] is True
    assert receipt["scientific_validation_performed"] is False
    assert receipt["total_bytes"] < q.LIMIT
    assert len(receipt["files"]) == 4
    terminal = q.products.read(directory / q.NAMES[3])
    assert terminal["terminal_sha256"] == q.design.digest(hook.terminal)
    assert q.products.read(directory / q.NAMES[2])["observed_seconds"] == 2


@pytest.mark.parametrize(
    "field,bad", [("TimeLimit", 1801), ("Threads", 8), ("MIPGap", 0.01), ("OutputFlag", 1)]
)
def test_bad_effective_parameter_cannot_publish_ready(tmp_path, monkeypatch, field, bad):
    directory, ident, journal, tick, hook, model, grb = fixture(tmp_path, monkeypatch)
    setattr(model.Params, field, bad)
    with pytest.raises(ValueError):
        hook("native_ready", model, grb)
    assert not (directory / q.NAMES[1]).exists()
    assert q.catalogue(directory, ident)["native_return_observed"] is False


@pytest.mark.parametrize("phase", ["export_validation", "optimization", "unknown", "build"])
def test_wrong_first_seam_no_forged_phase(tmp_path, monkeypatch, phase):
    directory, ident, journal, tick, hook, model, grb = fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        hook(phase, model, grb)
    assert journal.index == 1
    assert len(q.catalogue(directory, ident)["files"]) == 1


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True, -1])
def test_clock_rejected_before_phase_mutation(tmp_path, monkeypatch, bad):
    directory, ident, journal, tick, hook, model, grb = fixture(tmp_path, monkeypatch)
    tick[0] = bad
    with pytest.raises(ValueError):
        hook("native_ready", model, grb)
    assert not (directory / q.NAMES[1]).exists()


def test_changed_profile_or_native_journal_rejected(tmp_path, monkeypatch):
    directory, ident, journal, tick, hook, model, grb = fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="profile drift"):
        q.NativeSeams(directory, ident, journal, replace(hook.hooks.solver, tee=True))
    journal.identity = "0" * 64
    with pytest.raises(ValueError, match="journal binding"):
        q.NativeSeams(directory, ident, journal, q.native.solver_profile(4))


@pytest.mark.parametrize(
    "tamper",
    [
        "extra",
        "directory",
        "gap",
        "foreign",
        "elapsed",
        "permission",
        "profile",
        "large",
        "duplicate",
        "secret",
    ],
)
def test_catalogue_rejects_malformed_or_unexpected_data(tmp_path, monkeypatch, tamper):
    directory, ident, journal, tick, hook, model, grb = fixture(tmp_path, monkeypatch)
    hook("native_ready", model, grb)
    path = directory / q.NAMES[1]
    value = q.products.read(path)
    if tamper == "extra":
        (directory / "worker.out").write_bytes(b"PRIVATE")
    elif tamper == "directory":
        (directory / "nested").mkdir()
    elif tamper == "gap":
        path.rename(directory / q.NAMES[2])
    elif tamper == "large":
        path.write_bytes(b" " * 2049)
    elif tamper == "duplicate":
        path.write_bytes(b'{"phase":"native_ready","phase":"optimization"}')
    else:
        if tamper == "foreign":
            value["binding_sha256"] = "0" * 64
        elif tamper == "elapsed":
            value["observed_seconds"] = -1
        elif tamper == "permission":
            value["h300_execution_admitted"] = True
        elif tamper == "profile":
            value["profile_sha256"] = "0" * 64
        else:
            value["WLSSecret"] = "PRIVATE"
        path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        q.catalogue(directory, ident)


@pytest.mark.parametrize(
    "return_seconds,strict",
    [
        (1799, None),
        (1800, "optimization_watchdog"),
        (1800.01, "optimization_watchdog"),
        (1850, "optimization_watchdog"),
        (None, "optimization_watchdog"),
    ],
)
def test_actual_strict_guard_return_boundary(return_seconds, strict):
    value = q.handoff_case(530.824824, return_seconds, 10, 10)
    assert value["installed_strict_stop"] == strict
    assert value["proposal_approved"] is False
    assert value["native_time_limit_seconds"] == 1800
    assert value["block_ledger"]["block_seconds"] == 21600
    assert all(value[key] is False for key in q.CLOSED)


@pytest.mark.parametrize(
    "build,returned,export,cleanup,expected",
    [
        (530, 1850, 100, 10, "bounded_fit_only_not_admitted"),
        (899, 1800, 899, 299, "bounded_fit_only_not_admitted"),
        (900, 1800, 100, 10, "build_watchdog"),
        (530, None, 0, 0, "no_return_requires_bounded_stop"),
        (530, 1850, 850, 10, "return_export_reserve_exhausted"),
        (530, 2700, 0, 0, "return_export_reserve_exhausted"),
        (530, 1800, 900, 10, "return_export_reserve_exhausted"),
        (530, 1850, 100, 300, "cleanup_watchdog"),
    ],
)
def test_reserve_is_shared_never_additional_optimization_budget(
    build, returned, export, cleanup, expected
):
    value = q.handoff_case(build, returned, export, cleanup)
    assert value["proposal_arithmetic"] == expected
    assert value["native_subphase_after_limit"] == "unknown"
    assert value["arm_ceiling_seconds"] == 3900


@pytest.mark.parametrize("index", range(4))
@pytest.mark.parametrize("bad", [True, -1, float("nan"), float("inf"), "1800"])
def test_invalid_handoff_durations(index, bad):
    values = [530, 1800, 10, 10]
    values[index] = bad
    with pytest.raises(ValueError):
        q.handoff_case(*values)


@pytest.mark.parametrize("action", ["start", "batch", "worker", "collect"])
def test_public_entry_denies_before_any_effect(tmp_path, monkeypatch, action):
    monkeypatch.setattr(q.license_probe, "check_file", lambda: pytest.fail("license"))
    monkeypatch.setattr(q.license_probe, "probe", lambda: pytest.fail("probe"))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("scheduler"))
    with pytest.raises(PermissionError):
        q.main([action])
    assert not list(tmp_path.iterdir())


def test_public_check_fresh_process_no_native_import_or_claim(tmp_path):
    root = Path(__file__).resolve().parents[1]
    code = (
        "import sys;sys.dont_write_bytecode=True;sys.path.insert(0,sys.argv[1]);"
        "from scripts import mvp2_s2_p4_diagnostics as q;"
        "assert 'gurobipy' not in sys.modules;assert q.main(['check'])==0;"
        "assert 'gurobipy' not in sys.modules"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-I", "-c", code, str(root)],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    assert b"INSTALLED_GUARD_UNCHANGED" in result.stdout
    assert not list(tmp_path.iterdir())


def test_no_changes_to_policy_object_from_comparison():
    policy = copy.deepcopy(q.design.policy())
    q.handoff_case(530, 1850, 100, 10)
    assert q.design.policy() == policy
