"""Complete closed P4 pipeline using local scheduler/native doubles, never NPAD."""

import gzip
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_s2_h300_products as p
from scripts import mvp2_s2_h300_runtime as r
from tests.test_mvp2_h300_native_worker import install_backend
from tests.test_mvp2_h300_partial import fixture


def plan():
    runtime = {"python_version": "3.13.15", "distributions": {"gurobipy": "13.0.3"}}
    identity = {"workbook_sha256": r.d.WORKBOOK, "reference_sha256": r.REFERENCE}
    protected = {"src/fixed.py": "a" * 64}
    return {
        "schema_version": "s2-h300-academic-plan-v1",
        "preparation": r.entry.preparation(
            "b" * 40, r.d.digest(runtime), r.d.digest(identity), r.d.digest(protected)
        ),
        "files": {r.ENTRY: "c" * 64, **protected},
        "protected": protected,
        "runtime": runtime,
        "input": identity,
        "export_limit_bytes": p.LIMIT,
        "h300_execution_admitted": False,
        "repeats_admitted": False,
    }


def command_result(text="", code=0, status="complete"):
    return {"status": status, "returncode": code}, text.encode()


@pytest.mark.parametrize("action", ["start", "batch", "worker"])
def test_public_denial_before_effects(action, tmp_path, monkeypatch):
    monkeypatch.setattr(r, "_submit", lambda *a, **k: pytest.fail("submission"))
    with pytest.raises(PermissionError):
        r.main([action, "--claim", str(tmp_path / "absent")])
    assert not list(tmp_path.iterdir())


def test_wrapper_python_check_no_solver_or_cache(tmp_path):
    root = Path(__file__).resolve().parents[1]
    code = (
        "import runpy,sys;sys.dont_write_bytecode=True;sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('scripts.mvp2_s2_h300_runtime',run_name='__main__',alter_sys=True)"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-I", "-c", code, str(root), "check"],
        capture_output=True,
        check=True,
    )
    assert b"H300_AND_REPEATS_BLOCKED" in result.stdout


@pytest.mark.parametrize(
    "change", ["permission", "repeat", "runtime", "input", "protected", "limit"]
)
def test_plan_drift(change):
    value = plan()
    if change == "permission":
        value["h300_execution_admitted"] = True
    elif change == "repeat":
        value["repeats_admitted"] = True
    elif change == "runtime":
        value["runtime"]["python_version"] = "3.14.0"
    elif change == "input":
        value["input"]["workbook_sha256"] = "x" * 64
    elif change == "protected":
        value["files"]["src/fixed.py"] = "d" * 64
    else:
        value["export_limit_bytes"] += 1
    with pytest.raises(ValueError):
        r._validate(value)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), {1, 2}])
def test_non_json_or_nonfinite_never_published(bad, tmp_path):
    with pytest.raises((ValueError, TypeError)):
        p.publish(tmp_path / "result.json", bad)
    assert not list(tmp_path.iterdir())


def test_stream_exact_size_overflow_and_existing(tmp_path):
    value = {"unicode": "á" * 9000, "rows": list(range(100))}
    length = len(b"".join(p.chunks(value)))
    assert p.size(value, length) == length
    with pytest.raises(ValueError):
        p.publish(tmp_path / "overflow.json", value, limit=length - 1)
    assert not list(tmp_path.iterdir())
    p.publish(tmp_path / "result.json", value, limit=length)
    before = (tmp_path / "result.json").read_bytes()
    with pytest.raises(ValueError):
        p.publish(tmp_path / "result.json", {"replacement": True})
    assert (tmp_path / "result.json").read_bytes() == before


@pytest.mark.parametrize(
    "native,count,stages",
    [
        ("OPTIMAL", 1, 3),
        ("TIME_LIMIT", 1, 1),
        ("MEM_LIMIT", 1, 1),
        ("TIME_LIMIT", 0, 0),
        ("MEM_LIMIT", 0, 0),
    ],
)
def test_streamed_partial_fresh_residuals(native, count, stages, tmp_path):
    result, data, config, anchor = fixture(native, count, stages)
    report = p.export(tmp_path / "products", result, data, config, anchor, remaining=p.LIMIT)
    assert p.review(tmp_path / "products", data, config, anchor) == report
    assert report["classification"]["independently_feasible"] is bool(count)
    assert (tmp_path / "products/incumbent.json").exists() is bool(count)


@pytest.mark.parametrize("change", ["hash", "extra", "validation", "anchor", "size"])
def test_product_tampering(change, tmp_path):
    result, data, config, anchor = fixture()
    root = tmp_path / "products"
    p.export(root, result, data, config, anchor, remaining=p.LIMIT)
    if change in {"hash", "validation"}:
        name = "incumbent.json" if change == "hash" else "independent_validation.json"
        (root / name).write_bytes(b"{}")
    elif change == "extra":
        (root / "extra.json").write_bytes(b"{}")
    elif change == "anchor":
        anchor = {**anchor, "threads": 8}
    else:
        value = p.read(root / "closure.json")
        value["sizes"]["incumbent.json"] += 1
        (root / "closure.json").write_text(json.dumps(value))
    with pytest.raises(ValueError):
        p.review(root, data, config, anchor)


def test_export_budget_precedes_large_publication(tmp_path):
    result, data, config, anchor = fixture()
    result.flows = result.flows * 1000
    # Too little block budget: no large product or completion marker is written.
    with pytest.raises(ValueError):
        p.export(tmp_path / "products", result, data, config, anchor, remaining=p.RESERVE + 1)
    assert not (tmp_path / "products").exists()


@pytest.mark.parametrize("raw", ["", "0", "nonsense\n", "123\n456\n"])
def test_unknown_submission_consumes_claim(raw, tmp_path):
    target = tmp_path / r.CLAIM
    calls = []

    def command(argv, **kwargs):
        calls.append(argv)
        assert (target / "submission-intent.json").is_file()
        return command_result(raw)

    with pytest.raises(ValueError, match="Unknown acknowledgement"):
        r._submit(target, plan(), r.ROOT, "private", command=command)
    assert r._submit(target, plan(), r.ROOT, "private", command=command)["submitted"] is False
    assert len(calls) == 1


def test_submission_exact_resources_and_origin_not_portable(tmp_path):
    calls = []
    value = r._submit(
        tmp_path / r.CLAIM,
        plan(),
        r.ROOT,
        "/private/workbook-reference",
        command=lambda argv, **kwargs: calls.append(argv) or command_result("123;cluster\n"),
    )
    assert value["job_id"] == "123"
    for option in ("--account=sxdsouza", "--cpus-per-task=16", "--mem=196608M", "--time=06:00:00"):
        assert option in calls[0]
    assert not any("exclusive" in item for item in calls[0])
    assert (tmp_path / r.CLAIM / "origin.json").is_file()


@pytest.mark.parametrize("suffix", ["CANCELLED", "CANCELLED by 1271"])
def test_eight_accounting_rows_and_cancellation(suffix):
    steps = [f"123.{i}" for i in range(5)]
    raw = "\n".join(
        f"{name}|{suffix if name == steps[0] else 'COMPLETED'}|0:0|4"
        for name in ["123", "123.batch", "123.extern", *steps]
    )
    rows = r.accounting(raw, "123", steps)
    assert len(rows) == 8 and rows[steps[0]]["state"] == "CANCELLED"


@pytest.mark.parametrize("bad", ["CANCELLED+", "CANCELLED by root", "COMPLETED extra", "RUNNING"])
def test_invalid_nonterminal_accounting(bad):
    raw = f"123|{bad}|0:0|4\n123.batch|COMPLETED|0:0|4\n123.extern|COMPLETED|0:0|4"
    with pytest.raises(ValueError):
        r.accounting(raw, "123", [])


class Clock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def test_scheduler_resource_scopes_missing_values_and_drift():
    expected = r.accounting(
        "123|COMPLETED|0:0|8\n123.batch|COMPLETED|0:0|8\n123.extern|COMPLETED|0:0|8", "123", []
    )
    text = (
        "123|COMPLETED|0:0|8|00:00:03.5||16|192Gn\n"
        "123.batch|COMPLETED|0:0|8|00:00:01|1024K|16|\n"
        "123.extern|COMPLETED|0:0|8||||"
    )
    values = r.resource_accounting(text, expected)
    assert values["123"]["max_rss_slurm"] is None
    assert values["123.batch"]["max_rss_slurm"] == "1024K"
    assert values["123.extern"]["total_cpu_slurm"] is None
    with pytest.raises(ValueError):
        r.resource_accounting(text.replace("|8|", "|9|", 1), expected)


def test_unbound_worker_stops_without_broad_cancel(tmp_path):
    clock, calls = Clock(), []
    process = SimpleNamespace(
        returncode=None,
        poll=lambda: None,
        terminate=lambda: None,
        wait=lambda **kwargs: setattr(process, "returncode", -9),
    )
    attempt = r._supervise(
        process,
        tmp_path,
        plan(),
        4,
        "123",
        {},
        100,
        command=lambda argv, **kwargs: calls.append(argv) or command_result(),
        clock=clock,
        pause=clock.sleep,
        sample=lambda pid: {},
    )
    assert attempt["stop_reason"] == "unbound_startup"
    assert attempt["local_client_reaped"] and not calls
    assert not attempt["global_cleanup_proven"]


@pytest.mark.parametrize("mode", ["fast", "late", "wrong_step", "query_failure"])
def test_bound_control_exact_step_and_fast_exit(mode, tmp_path, monkeypatch):
    clock, calls = Clock(), []
    monkeypatch.setattr(r.os, "getuid", lambda: 1271, raising=False)
    value = plan()
    env = {"allocation": {"node": "r1i3n5"}}
    p.publish(
        tmp_path / "worker-start.json",
        {
            "plan_sha256": r.d.digest(value),
            "uid": 1271,
            "threads": 4,
            "environment_sha256": r.d.digest(env),
            "step_id": "123.7",
            "pid": 999,
        },
    )
    journal = r.c.PhaseJournal(
        tmp_path / "native", r.d.digest({"plan": r.d.digest(value), "threads": 4})
    )
    for phase in r.c.PHASES if mode == "fast" else ["build"]:
        journal.enter(phase)
    process = SimpleNamespace(returncode=0 if mode == "fast" else None)
    process.poll = lambda: process.returncode
    process.wait = lambda **kwargs: setattr(
        process, "returncode", -9 if process.returncode is None else process.returncode
    )

    def command(argv, **kwargs):
        calls.append(argv)
        if argv[0] == "scontrol":
            if mode == "query_failure":
                return command_result("", code=1)
            return command_result(
                "StepId=123.7 UserId=1271 State=RUNNING Nodes=1 "
                "NodeList=r1i3n5 Tasks=1 CPUs=" + ("1" if mode == "wrong_step" else "16")
            )
        return command_result()

    attempt = r._supervise(
        process,
        tmp_path,
        value,
        4,
        "123",
        env,
        1000,
        command=command,
        clock=clock,
        pause=clock.sleep,
        sample=lambda pid: {"process_tree_cpu_seconds": 1},
    )
    if mode == "fast":
        assert attempt["stop_reason"] is None
        assert attempt["return_code"] == 0
        assert not any(x[0] == "scancel" for x in calls)
    else:
        assert attempt["stop_reason"] is not None
        assert [x for x in calls if x[0] == "scancel"] == [
            ["scancel", "--signal=TERM", "123.7"],
            ["scancel", "--signal=KILL", "123.7"],
        ]
    assert attempt["local_client_reaped"]
    assert not attempt["global_cleanup_proven"]


def test_independent_validation_timeout_is_not_acceptance(tmp_path):
    with pytest.raises(subprocess.TimeoutExpired):
        r._independent(
            tmp_path,
            1,
            run=lambda *a, **k: (_ for _ in ()).throw(
                subprocess.TimeoutExpired("fixed_validator", 1)
            ),
        )
    assert not (tmp_path / "independent.json").exists()


def test_missing_batch_terminal_forensics(tmp_path, monkeypatch):
    target = tmp_path / r.CLAIM
    value = plan()
    r._submit(target, value, r.ROOT, "reference", command=lambda *a, **k: command_result("123\n"))
    report = r._collect(
        target,
        r.d.digest(value),
        "123",
        command=lambda *a, **k: command_result(
            "123|FAILED|2:0|2\n123.batch|FAILED|2:0|2\n123.extern|COMPLETED|0:0|2"
        ),
        recheck=lambda *a: (_ for _ in ()).throw(ValueError("source drift")),
    )
    assert report["status"] == "forensic_partial_block"
    assert report["unrun"] == [] and report["unaccounted"] == list(r.d.ORDER)
    assert report["validation_error"] == "ValueError"
    assert (target / "s2-h300-academic-evidence.tar.gz").is_file()


def test_nonterminal_collection_does_not_invent_batch(tmp_path):
    target = tmp_path / r.CLAIM
    value = plan()
    r._submit(target, value, r.ROOT, "reference", command=lambda *a, **k: command_result("123\n"))
    with pytest.raises(ValueError, match="Accounting not terminal"):
        r._collect(
            target,
            r.d.digest(value),
            "123",
            command=lambda *a, **k: command_result(
                "123|RUNNING|0:0|2\n123.batch|RUNNING|0:0|2\n123.extern|RUNNING|0:0|2"
            ),
        )
    assert not (target / "batch.json").exists()
    assert not (target / "review.json").exists()


def test_recheck_source_runtime_and_input_independently(monkeypatch):
    value = plan()
    monkeypatch.setattr(r.source, "verify_tree", lambda *a: None)
    with pytest.raises(ValueError, match="Runtime drift"):
        r._recheck(
            value,
            r.ROOT,
            "unused",
            runtime=lambda: {},
            load=lambda *a: pytest.fail("Input read despite wrong runtime"),
        )
    with pytest.raises(ValueError, match="scientific input drift"):
        r._recheck(
            value,
            r.ROOT,
            "unused",
            runtime=lambda: value["runtime"],
            load=lambda *a: (None, None, {}),
        )


def test_wrong_reference_fails_before_workbook_access(monkeypatch):
    monkeypatch.setattr(p, "sha_file", lambda *a: "0" * 64)
    with pytest.raises(ValueError, match="Reference manifest drift"):
        r._input("not-a-workbook")


@pytest.mark.parametrize("failure", [None, "optimization", "construction", "extraction"])
def test_native_disposal_and_phase_failure(failure, monkeypatch, tmp_path):
    result, data, config, _anchor = fixture("OPTIMAL", 1, 3)
    calls = []
    install_backend(monkeypatch, result, calls, fail=failure)
    monkeypatch.setattr(r.worker_tools, "resources", lambda: {"scope": "test_root"})
    if failure:
        with pytest.raises(ValueError):
            r._native(
                tmp_path, plan(), 4, "reference", p.LIMIT, recheck=lambda *args: (data, config)
            )
        assert (tmp_path / "native/failure.json").is_file()
    else:
        report = r._native(
            tmp_path, plan(), 4, "reference", p.LIMIT, recheck=lambda *args: (data, config)
        )
        assert report["classification"]["disposition"] == "complete_accepted_hierarchy"
    assert calls[-1] == "dispose"


def block_fixture(tmp_path, monkeypatch, *, stop_index=None):
    target = tmp_path / r.CLAIM
    value = plan()
    r._submit(target, value, r.ROOT, "reference", command=lambda *a, **k: command_result("123\n"))
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setattr(r.worker_tools, "resources", lambda: {"scope": "test_root"})
    _result, data, config, _anchor = fixture("OPTIMAL", 1, 3)
    executed = []

    def arm(path, p4, threads, job, env, reference, remaining, hard, **kwargs):
        index = len(executed)
        executed.append(threads)
        path.mkdir()
        result, _data, _config, _ = fixture("OPTIMAL", 1, 3)
        install_backend(monkeypatch, result, [])
        r._native(path, p4, threads, reference, remaining, recheck=lambda *a: (data, config))
        attempt = {
            "step_id": f"123.{index}",
            "stop_reason": "test_failure" if index == stop_index else None,
            "local_client_reaped": True,
            "return_code": 0,
            "threads": threads,
        }
        p.publish(path / "attempt.json", attempt)
        return attempt

    def command(argv, **kwargs):
        job = argv[argv.index("-j") + 1]
        if "." in job:
            return command_result(f"{job}|COMPLETED|0:0|4\n")
        return command_result(
            "\n".join(
                f"{name}|COMPLETED|0:0|8"
                for name in [
                    "123",
                    "123.batch",
                    "123.extern",
                    *(f"123.{i}" for i in range(len(executed))),
                ]
            )
        )

    def recheck(*a):
        return data, config

    batch = r._batch(
        target,
        recheck=recheck,
        environment=lambda *a, **k: {"same": True},
        license_check=lambda: {"status": "accepted"},
        run_arm=arm,
        independent=lambda path, data, config, anchor, remaining: p.review(
            path / "native/products", data, config, anchor
        ),
        command=command,
        clock=Clock(),
    )
    return target, value, batch, command, recheck


@pytest.mark.parametrize("stop", [None, 0, 2, 4])
def test_full_block_and_partial_prefix_fresh_collection(stop, tmp_path, monkeypatch):
    target, value, batch, command, recheck = block_fixture(tmp_path, monkeypatch, stop_index=stop)
    count = 5 if stop is None else stop + 1
    assert [arm["threads"] for arm in batch["arms"]] == list(r.d.ORDER[:count])
    assert batch["unrun"] == list(r.d.ORDER[count:])
    report = r._collect(target, r.d.digest(value), "123", command=command, recheck=recheck)
    assert report["status"] == (
        "five_arms_accounted_not_s2_closure" if stop is None else "forensic_partial_block"
    )
    assert not report["scientific_configuration_selected"]
    transfer = p.read(target / "transfer.json")
    assert all(
        "private" not in name and "origin" not in name and "slurm" not in name
        for name in transfer["files"]
    )
    assert any("native/products/incumbent.json" in name for name in transfer["files"])
    assert r._collect(target, r.d.digest(value), "123", command=command, recheck=recheck) == report


@pytest.mark.parametrize("tamper", ["archive", "review", "accounting"])
def test_corrupt_collection_cache_not_replaced(tamper, tmp_path, monkeypatch):
    target, value, batch, command, recheck = block_fixture(tmp_path, monkeypatch)
    r._collect(target, r.d.digest(value), "123", command=command, recheck=recheck)
    name = "s2-h300-academic-evidence.tar.gz" if tamper == "archive" else tamper + ".json"
    (target / name).write_bytes(b"corrupt")
    with pytest.raises((ValueError, json.JSONDecodeError)):
        r._collect(target, r.d.digest(value), "123", command=command, recheck=recheck)
    assert (target / name).read_bytes() == b"corrupt"


@pytest.mark.parametrize("kind", ["duplicate", "link", "extra", "tail"])
def test_hostile_archive(kind, tmp_path):
    archive = tmp_path / "bad.tar.gz"
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:", format=tarfile.USTAR_FORMAT) as stream:
        for name in (
            ["plan.json", "plan.json"]
            if kind == "duplicate"
            else ["extra.json"]
            if kind == "extra"
            else ["plan.json"]
        ):
            member = tarfile.TarInfo(name)
            if kind == "link":
                member.type = tarfile.SYMTYPE
                member.linkname = "private"
            else:
                member.size = 2
            stream.addfile(member, io.BytesIO(b"{}"))
    payload = raw.getvalue() + (b"evil" if kind == "tail" else b"")
    archive.write_bytes(gzip.compress(payload))
    expected = {"plan.json": {"size": 2, "sha256": r.academic.sha(b"{}")}}
    with pytest.raises(ValueError):
        p.unpack_review(archive, p.sha_file(archive), expected)


@pytest.mark.skipif(sys.platform != "linux", reason="Bash wrapper semantics require Linux")
def test_actual_bash_wrapper_denies_and_checks(tmp_path):
    root = Path(__file__).resolve().parents[1]
    wrapper = root / "scripts/npad_s2_h300_academic.sh"
    env = {**os.environ, "MVP2_P4_PYTHON": sys.executable}
    for action in ("start", "worker", "batch"):
        result = subprocess.run(["bash", str(wrapper), action], env=env, capture_output=True)
        assert result.returncode == 2 and b"H300_AND_REPEATS_BLOCKED" in result.stderr
    subprocess.run(["bash", "-n", str(wrapper)], env=env, check=True)
    result = subprocess.run(
        ["bash", str(wrapper), "check"], env=env, capture_output=True, check=True
    )
    assert b"H300_AND_REPEATS_BLOCKED" in result.stdout
"""Complete closed P4 pipeline using local scheduler/native doubles, never NPAD."""

import gzip
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_s2_h300_products as p
from scripts import mvp2_s2_h300_runtime as r
from tests.test_mvp2_h300_native_worker import install_backend
from tests.test_mvp2_h300_partial import fixture


def plan():
    runtime = {"python_version": "3.13.15", "distributions": {"gurobipy": "13.0.3"}}
    identity = {"workbook_sha256": r.d.WORKBOOK, "reference_sha256": r.REFERENCE}
    protected = {"src/fixed.py": "a" * 64}
    return {
        "schema_version": "s2-h300-academic-plan-v1",
        "preparation": r.entry.preparation(
            "b" * 40, r.d.digest(runtime), r.d.digest(identity), r.d.digest(protected)
        ),
        "files": {r.ENTRY: "c" * 64, **protected},
        "protected": protected,
        "runtime": runtime,
        "input": identity,
        "export_limit_bytes": p.LIMIT,
        "h300_execution_admitted": False,
        "repeats_admitted": False,
    }


def command_result(text="", code=0, status="complete"):
    return {"status": status, "returncode": code}, text.encode()


@pytest.mark.parametrize("action", ["start", "batch", "worker"])
def test_public_denial_before_effects(action, tmp_path, monkeypatch):
    monkeypatch.setattr(r, "_submit", lambda *a, **k: pytest.fail("submission"))
    with pytest.raises(PermissionError):
        r.main([action, "--claim", str(tmp_path / "absent")])
    assert not list(tmp_path.iterdir())


def test_wrapper_python_check_no_solver_or_cache(tmp_path):
    root = Path(__file__).resolve().parents[1]
    code = (
        "import runpy,sys;sys.dont_write_bytecode=True;sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('scripts.mvp2_s2_h300_runtime',run_name='__main__',alter_sys=True)"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-I", "-c", code, str(root), "check"],
        capture_output=True,
        check=True,
    )
    assert b"H300_AND_REPEATS_BLOCKED" in result.stdout


@pytest.mark.parametrize(
    "change", ["permission", "repeat", "runtime", "input", "protected", "limit"]
)
def test_plan_drift(change):
    value = plan()
    if change == "permission":
        value["h300_execution_admitted"] = True
    elif change == "repeat":
        value["repeats_admitted"] = True
    elif change == "runtime":
        value["runtime"]["python_version"] = "3.14.0"
    elif change == "input":
        value["input"]["workbook_sha256"] = "x" * 64
    elif change == "protected":
        value["files"]["src/fixed.py"] = "d" * 64
    else:
        value["export_limit_bytes"] += 1
    with pytest.raises(ValueError):
        r._validate(value)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), {1, 2}])
def test_non_json_or_nonfinite_never_published(bad, tmp_path):
    with pytest.raises((ValueError, TypeError)):
        p.publish(tmp_path / "result.json", bad)
    assert not list(tmp_path.iterdir())


def test_stream_exact_size_overflow_and_existing(tmp_path):
    value = {"unicode": "á" * 9000, "rows": list(range(100))}
    length = len(b"".join(p.chunks(value)))
    assert p.size(value, length) == length
    with pytest.raises(ValueError):
        p.publish(tmp_path / "overflow.json", value, limit=length - 1)
    assert not list(tmp_path.iterdir())
    p.publish(tmp_path / "result.json", value, limit=length)
    before = (tmp_path / "result.json").read_bytes()
    with pytest.raises(ValueError):
        p.publish(tmp_path / "result.json", {"replacement": True})
    assert (tmp_path / "result.json").read_bytes() == before


@pytest.mark.parametrize(
    "native,count,stages",
    [
        ("OPTIMAL", 1, 3),
        ("TIME_LIMIT", 1, 1),
        ("MEM_LIMIT", 1, 1),
        ("TIME_LIMIT", 0, 0),
        ("MEM_LIMIT", 0, 0),
    ],
)
def test_streamed_partial_fresh_residuals(native, count, stages, tmp_path):
    result, data, config, anchor = fixture(native, count, stages)
    report = p.export(tmp_path / "products", result, data, config, anchor, remaining=p.LIMIT)
    assert p.review(tmp_path / "products", data, config, anchor) == report
    assert report["classification"]["independently_feasible"] is bool(count)
    assert (tmp_path / "products/incumbent.json").exists() is bool(count)


@pytest.mark.parametrize("change", ["hash", "extra", "validation", "anchor", "size"])
def test_product_tampering(change, tmp_path):
    result, data, config, anchor = fixture()
    root = tmp_path / "products"
    p.export(root, result, data, config, anchor, remaining=p.LIMIT)
    if change in {"hash", "validation"}:
        name = "incumbent.json" if change == "hash" else "independent_validation.json"
        (root / name).write_bytes(b"{}")
    elif change == "extra":
        (root / "extra.json").write_bytes(b"{}")
    elif change == "anchor":
        anchor = {**anchor, "threads": 8}
    else:
        value = p.read(root / "closure.json")
        value["sizes"]["incumbent.json"] += 1
        (root / "closure.json").write_text(json.dumps(value))
    with pytest.raises(ValueError):
        p.review(root, data, config, anchor)


def test_export_budget_precedes_large_publication(tmp_path):
    result, data, config, anchor = fixture()
    result.flows = result.flows * 1000
    # Too little block budget: no large product or completion marker is written.
    with pytest.raises(ValueError):
        p.export(tmp_path / "products", result, data, config, anchor, remaining=p.RESERVE + 1)
    assert not (tmp_path / "products").exists()


@pytest.mark.parametrize("raw", ["", "0", "nonsense\n", "123\n456\n"])
def test_unknown_submission_consumes_claim(raw, tmp_path):
    target = tmp_path / r.CLAIM
    calls = []

    def command(argv, **kwargs):
        calls.append(argv)
        assert (target / "submission-intent.json").is_file()
        return command_result(raw)

    with pytest.raises(ValueError, match="Unknown acknowledgement"):
        r._submit(target, plan(), r.ROOT, "private", command=command)
    assert r._submit(target, plan(), r.ROOT, "private", command=command)["submitted"] is False
    assert len(calls) == 1


def test_submission_exact_resources_and_origin_not_portable(tmp_path):
    calls = []
    value = r._submit(
        tmp_path / r.CLAIM,
        plan(),
        r.ROOT,
        "/private/workbook-reference",
        command=lambda argv, **kwargs: calls.append(argv) or command_result("123;cluster\n"),
    )
    assert value["job_id"] == "123"
    for option in ("--account=sxdsouza", "--cpus-per-task=16", "--mem=196608M", "--time=06:00:00"):
        assert option in calls[0]
    assert not any("exclusive" in item for item in calls[0])
    assert (tmp_path / r.CLAIM / "origin.json").is_file()


@pytest.mark.parametrize("suffix", ["CANCELLED", "CANCELLED by 1271"])
def test_eight_accounting_rows_and_cancellation(suffix):
    steps = [f"123.{i}" for i in range(5)]
    raw = "\n".join(
        f"{name}|{suffix if name == steps[0] else 'COMPLETED'}|0:0|4"
        for name in ["123", "123.batch", "123.extern", *steps]
    )
    rows = r.accounting(raw, "123", steps)
    assert len(rows) == 8 and rows[steps[0]]["state"] == "CANCELLED"


@pytest.mark.parametrize("bad", ["CANCELLED+", "CANCELLED by root", "COMPLETED extra", "RUNNING"])
def test_invalid_nonterminal_accounting(bad):
    raw = f"123|{bad}|0:0|4\n123.batch|COMPLETED|0:0|4\n123.extern|COMPLETED|0:0|4"
    with pytest.raises(ValueError):
        r.accounting(raw, "123", [])


class Clock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def test_unbound_worker_stops_without_broad_cancel(tmp_path):
    clock, calls = Clock(), []
    process = SimpleNamespace(
        returncode=None,
        poll=lambda: None,
        terminate=lambda: None,
        wait=lambda **kwargs: setattr(process, "returncode", -9),
    )
    attempt = r._supervise(
        process,
        tmp_path,
        plan(),
        4,
        "123",
        {},
        100,
        command=lambda argv, **kwargs: calls.append(argv) or command_result(),
        clock=clock,
        pause=clock.sleep,
        sample=lambda pid: {},
    )
    assert attempt["stop_reason"] == "unbound_startup"
    assert attempt["local_client_reaped"] and not calls
    assert not attempt["global_cleanup_proven"]


@pytest.mark.parametrize("mode", ["fast", "late", "wrong_step", "query_failure"])
def test_bound_control_exact_step_and_fast_exit(mode, tmp_path, monkeypatch):
    clock, calls = Clock(), []
    monkeypatch.setattr(r.os, "getuid", lambda: 1271, raising=False)
    value = plan()
    env = {"allocation": {"node": "r1i3n5"}}
    p.publish(
        tmp_path / "worker-start.json",
        {
            "plan_sha256": r.d.digest(value),
            "uid": 1271,
            "threads": 4,
            "environment_sha256": r.d.digest(env),
            "step_id": "123.7",
            "pid": 999,
        },
    )
    journal = r.c.PhaseJournal(
        tmp_path / "native", r.d.digest({"plan": r.d.digest(value), "threads": 4})
    )
    for phase in r.c.PHASES if mode == "fast" else ["build"]:
        journal.enter(phase)
    process = SimpleNamespace(returncode=0 if mode == "fast" else None)
    process.poll = lambda: process.returncode
    process.wait = lambda **kwargs: setattr(
        process, "returncode", -9 if process.returncode is None else process.returncode
    )

    def command(argv, **kwargs):
        calls.append(argv)
        if argv[0] == "scontrol":
            if mode == "query_failure":
                return command_result("", code=1)
            return command_result(
                "StepId=123.7 UserId=1271 State=RUNNING Nodes=1 "
                "NodeList=r1i3n5 Tasks=1 CPUs=" + ("1" if mode == "wrong_step" else "16")
            )
        return command_result()

    attempt = r._supervise(
        process,
        tmp_path,
        value,
        4,
        "123",
        env,
        1000,
        command=command,
        clock=clock,
        pause=clock.sleep,
        sample=lambda pid: {"process_tree_cpu_seconds": 1},
    )
    if mode == "fast":
        assert attempt["stop_reason"] is None
        assert attempt["return_code"] == 0
        assert not any(x[0] == "scancel" for x in calls)
    else:
        assert attempt["stop_reason"] is not None
        assert [x for x in calls if x[0] == "scancel"] == [
            ["scancel", "--signal=TERM", "123.7"],
            ["scancel", "--signal=KILL", "123.7"],
        ]
    assert attempt["local_client_reaped"]
    assert not attempt["global_cleanup_proven"]


def test_independent_validation_timeout_is_not_acceptance(tmp_path):
    with pytest.raises(subprocess.TimeoutExpired):
        r._independent(
            tmp_path,
            1,
            run=lambda *a, **k: (_ for _ in ()).throw(
                subprocess.TimeoutExpired("fixed_validator", 1)
            ),
        )
    assert not (tmp_path / "independent.json").exists()


def test_missing_batch_terminal_forensics(tmp_path, monkeypatch):
    target = tmp_path / r.CLAIM
    value = plan()
    r._submit(target, value, r.ROOT, "reference", command=lambda *a, **k: command_result("123\n"))
    report = r._collect(
        target,
        r.d.digest(value),
        "123",
        command=lambda *a, **k: command_result(
            "123|FAILED|2:0|2\n123.batch|FAILED|2:0|2\n123.extern|COMPLETED|0:0|2"
        ),
        recheck=lambda *a: (_ for _ in ()).throw(ValueError("source drift")),
    )
    assert report["status"] == "forensic_partial_block"
    assert report["unrun"] == [] and report["unaccounted"] == list(r.d.ORDER)
    assert report["validation_error"] == "ValueError"
    assert (target / "s2-h300-academic-evidence.tar.gz").is_file()


def test_nonterminal_collection_does_not_invent_batch(tmp_path):
    target = tmp_path / r.CLAIM
    value = plan()
    r._submit(target, value, r.ROOT, "reference", command=lambda *a, **k: command_result("123\n"))
    with pytest.raises(ValueError, match="Accounting not terminal"):
        r._collect(
            target,
            r.d.digest(value),
            "123",
            command=lambda *a, **k: command_result(
                "123|RUNNING|0:0|2\n123.batch|RUNNING|0:0|2\n123.extern|RUNNING|0:0|2"
            ),
        )
    assert not (target / "batch.json").exists()
    assert not (target / "review.json").exists()


def test_recheck_source_runtime_and_input_independently(monkeypatch):
    value = plan()
    monkeypatch.setattr(r.source, "verify_tree", lambda *a: None)
    with pytest.raises(ValueError, match="Runtime drift"):
        r._recheck(
            value,
            r.ROOT,
            "unused",
            runtime=lambda: {},
            load=lambda *a: pytest.fail("Input read despite wrong runtime"),
        )
    with pytest.raises(ValueError, match="scientific input drift"):
        r._recheck(
            value,
            r.ROOT,
            "unused",
            runtime=lambda: value["runtime"],
            load=lambda *a: (None, None, {}),
        )


def test_wrong_reference_fails_before_workbook_access(monkeypatch):
    monkeypatch.setattr(p, "sha_file", lambda *a: "0" * 64)
    with pytest.raises(ValueError, match="Reference manifest drift"):
        r._input("not-a-workbook")


@pytest.mark.parametrize("failure", [None, "optimization", "construction", "extraction"])
def test_native_disposal_and_phase_failure(failure, monkeypatch, tmp_path):
    result, data, config, _anchor = fixture("OPTIMAL", 1, 3)
    calls = []
    install_backend(monkeypatch, result, calls, fail=failure)
    monkeypatch.setattr(r.worker_tools, "resources", lambda: {"scope": "test_root"})
    if failure:
        with pytest.raises(ValueError):
            r._native(
                tmp_path, plan(), 4, "reference", p.LIMIT, recheck=lambda *args: (data, config)
            )
        assert (tmp_path / "native/failure.json").is_file()
    else:
        report = r._native(
            tmp_path, plan(), 4, "reference", p.LIMIT, recheck=lambda *args: (data, config)
        )
        assert report["classification"]["disposition"] == "complete_accepted_hierarchy"
    assert calls[-1] == "dispose"


def block_fixture(tmp_path, monkeypatch, *, stop_index=None):
    target = tmp_path / r.CLAIM
    value = plan()
    r._submit(target, value, r.ROOT, "reference", command=lambda *a, **k: command_result("123\n"))
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setattr(r.worker_tools, "resources", lambda: {"scope": "test_root"})
    _result, data, config, _anchor = fixture("OPTIMAL", 1, 3)
    executed = []

    def arm(path, p4, threads, job, env, reference, remaining, hard, **kwargs):
        index = len(executed)
        executed.append(threads)
        path.mkdir()
        result, _data, _config, _ = fixture("OPTIMAL", 1, 3)
        install_backend(monkeypatch, result, [])
        r._native(path, p4, threads, reference, remaining, recheck=lambda *a: (data, config))
        attempt = {
            "step_id": f"123.{index}",
            "stop_reason": "test_failure" if index == stop_index else None,
            "local_client_reaped": True,
            "return_code": 0,
            "threads": threads,
        }
        p.publish(path / "attempt.json", attempt)
        return attempt

    def command(argv, **kwargs):
        job = argv[argv.index("-j") + 1]
        if "." in job:
            return command_result(f"{job}|COMPLETED|0:0|4\n")
        return command_result(
            "\n".join(
                f"{name}|COMPLETED|0:0|8"
                for name in [
                    "123",
                    "123.batch",
                    "123.extern",
                    *(f"123.{i}" for i in range(len(executed))),
                ]
            )
        )

    def recheck(*a):
        return data, config

    batch = r._batch(
        target,
        recheck=recheck,
        environment=lambda *a, **k: {"same": True},
        license_check=lambda: {"status": "accepted"},
        run_arm=arm,
        independent=lambda path, data, config, anchor, remaining: p.review(
            path / "native/products", data, config, anchor
        ),
        command=command,
        clock=Clock(),
    )
    return target, value, batch, command, recheck


@pytest.mark.parametrize("stop", [None, 0, 2, 4])
def test_full_block_and_partial_prefix_fresh_collection(stop, tmp_path, monkeypatch):
    target, value, batch, command, recheck = block_fixture(tmp_path, monkeypatch, stop_index=stop)
    count = 5 if stop is None else stop + 1
    assert [arm["threads"] for arm in batch["arms"]] == list(r.d.ORDER[:count])
    assert batch["unrun"] == list(r.d.ORDER[count:])
    report = r._collect(target, r.d.digest(value), "123", command=command, recheck=recheck)
    assert report["status"] == (
        "five_arms_accounted_not_s2_closure" if stop is None else "forensic_partial_block"
    )
    assert not report["scientific_configuration_selected"]
    transfer = p.read(target / "transfer.json")
    assert all(
        "private" not in name and "origin" not in name and "slurm" not in name
        for name in transfer["files"]
    )
    assert any("native/products/incumbent.json" in name for name in transfer["files"])
    assert r._collect(target, r.d.digest(value), "123", command=command, recheck=recheck) == report


@pytest.mark.parametrize("tamper", ["archive", "review", "accounting"])
def test_corrupt_collection_cache_not_replaced(tamper, tmp_path, monkeypatch):
    target, value, batch, command, recheck = block_fixture(tmp_path, monkeypatch)
    r._collect(target, r.d.digest(value), "123", command=command, recheck=recheck)
    name = "s2-h300-academic-evidence.tar.gz" if tamper == "archive" else tamper + ".json"
    (target / name).write_bytes(b"corrupt")
    with pytest.raises((ValueError, json.JSONDecodeError)):
        r._collect(target, r.d.digest(value), "123", command=command, recheck=recheck)
    assert (target / name).read_bytes() == b"corrupt"


@pytest.mark.parametrize("kind", ["duplicate", "link", "extra", "tail"])
def test_hostile_archive(kind, tmp_path):
    archive = tmp_path / "bad.tar.gz"
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:", format=tarfile.USTAR_FORMAT) as stream:
        for name in (
            ["plan.json", "plan.json"]
            if kind == "duplicate"
            else ["extra.json"]
            if kind == "extra"
            else ["plan.json"]
        ):
            member = tarfile.TarInfo(name)
            if kind == "link":
                member.type = tarfile.SYMTYPE
                member.linkname = "private"
            else:
                member.size = 2
            stream.addfile(member, io.BytesIO(b"{}"))
    payload = raw.getvalue() + (b"evil" if kind == "tail" else b"")
    archive.write_bytes(gzip.compress(payload))
    expected = {"plan.json": {"size": 2, "sha256": r.academic.sha(b"{}")}}
    with pytest.raises(ValueError):
        p.unpack_review(archive, p.sha_file(archive), expected)


@pytest.mark.skipif(sys.platform != "linux", reason="Bash wrapper semantics require Linux")
def test_actual_bash_wrapper_denies_and_checks(tmp_path):
    root = Path(__file__).resolve().parents[1]
    wrapper = root / "scripts/npad_s2_h300_academic.sh"
    env = {**os.environ, "MVP2_P4_PYTHON": sys.executable}
    for action in ("start", "worker", "batch"):
        result = subprocess.run(["bash", str(wrapper), action], env=env, capture_output=True)
        assert result.returncode == 2 and b"H300_AND_REPEATS_BLOCKED" in result.stderr
    subprocess.run(["bash", "-n", str(wrapper)], env=env, check=True)
    result = subprocess.run(
        ["bash", str(wrapper), "check"], env=env, capture_output=True, check=True
    )
    assert b"H300_AND_REPEATS_BLOCKED" in result.stdout
