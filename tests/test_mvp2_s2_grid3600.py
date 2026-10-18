"""Complete requested five-thread package; public native double, never NPAD."""

import copy
import gzip
import io
import subprocess
import sys
import tarfile
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from scripts import mvp2_s2_grid_products as g
from scripts import mvp2_s2_grid_release as q
from scripts import mvp2_s2_grid_runtime as r
from tests.test_mvp2_h300_partial import fixture
from tests.test_mvp2_s2_h300_runtime import Clock, command_result
from tests.test_mvp2_s2_p4_terminal import SOURCE, install_backend
from tests.test_mvp2_s2_p4_terminal import plan as historical_plan

p, d, native = q.p, q.d, q.native


def plan():
    value = historical_plan()
    for name in (
        "scripts/mvp2_s2_grid_products.py",
        "scripts/mvp2_s2_grid_runtime.py",
        "scripts/mvp2_s2_grid_release.py",
        "scripts/npad_s2_grid3600.sh",
    ):
        value["files"][name] = p.sha_file(q.ROOT / name)
    return value


def submit(tmp_path, monkeypatch, reply="456\n"):
    value = plan()
    old = tmp_path / "original"
    old.mkdir()
    p.publish(old / "plan.json", value)
    (old / "prior.gz").write_bytes(b"ORIGINAL PRESERVED")
    monkeypatch.setattr(q, "BASE", tmp_path)
    monkeypatch.setattr(q.replay, "original", lambda: old)
    monkeypatch.setattr(q.replay, "carrier", lambda: old / "prior.gz")
    monkeypatch.setattr(q.replay, "authenticated", lambda _: {})
    monkeypatch.setitem(q.replay.ANCHORS, "native_plan_sha256", d.digest(value))
    monkeypatch.setattr(q, "historical_plan", lambda _: copy.deepcopy(value))
    calls = []

    def command(argv, **kwargs):
        assert (q.directory() / "submission-intent.json").exists()
        calls.append(argv)
        return command_result(reply)

    result = q.start(SOURCE, acknowledged=True, planner=lambda *a: value, command=command)
    return q.directory(), value, result, calls


@pytest.mark.parametrize("threads", d.ORDER)
def test_requested_budget_global_not_per_priority(threads):
    value = plan()
    release = q.sealed(value)
    solver = native.solver_profile(threads)
    assert solver.time_limit == 3600 and solver.threads == threads
    assert all("TimeLimit" not in opts for opts in solver.multiobjective_stage_options.values())
    assert release["order"] == [4, 1, 8, 2, 16]
    assert release["enforcement"] == native.CONTRACT
    assert release["enforcement"]["block_seconds"] == 43200
    assert release["expanded_transfer_limit_bytes"] == 1024**3
    assert release["per_arm_product_limit_bytes"] == p.LIMIT == 256 * 1024**2
    assert all(release[k] is False for k in q.FLAGS)


def test_one_new_12h_allocation_no_resubmit_or_original_edit(tmp_path, monkeypatch):
    target, _plan, result, calls = submit(tmp_path, monkeypatch)
    before = {f.name: f.read_bytes() for f in q.replay.original().iterdir()}
    assert result["job_id"] == "456"
    assert "--time=12:00:00" in calls[0]
    assert "--cpus-per-task=16" in calls[0] and "--mem=196608M" in calls[0]
    assert target.name != q.replay.prior.runtime.CLAIM
    with pytest.raises(ValueError, match="collect only"):
        q.start(SOURCE, acknowledged=True, command=lambda *a, **k: pytest.fail("resubmitted"))
    assert before == {f.name: f.read_bytes() for f in q.replay.original().iterdir()}


def test_no_acknowledgement_before_any_effect(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "BASE", tmp_path)
    with pytest.raises(ValueError, match="acknowledgement"):
        q.start(SOURCE)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("reply", ["", "warning\n456\n", "0\n", "456 bad\n"])
def test_unknown_ack_consumes_new_grid_slot(tmp_path, monkeypatch, reply):
    with pytest.raises(ValueError, match="Unknown acknowledgement"):
        submit(tmp_path, monkeypatch, reply)
    assert q.directory().exists() and not (q.directory() / "job.json").exists()
    with pytest.raises(ValueError, match="collect only"):
        q.start(SOURCE, acknowledged=True)


@pytest.mark.parametrize("passed", [True, False])
def test_old_vector_check_in_same_allocation_before_native_admission(tmp_path, passed):
    calls = []

    def run(argv, **kwargs):
        calls.append("read_only_preflight")
        assert kwargs["timeout"] == 900 and kwargs["shell"] is False
        p.publish(
            tmp_path / "prerequisite/outcome.json",
            {"status": "existing_vector_replay_qualified" if passed else "blocked"},
        )
        return SimpleNamespace(returncode=0)

    def block(path, **kwargs):
        calls.append("native_block")
        assert path == tmp_path
        assert kwargs["run_arm"] is r.arm and kwargs["independent"] is r.independent
        assert kwargs["allocation_deadline"] == 43200
        assert kwargs["export_limit"] == g.LIMIT - g.RESERVE
        return {"stop_reason": None, "arms": [], "unrun": []}

    if passed:
        r.execute(tmp_path, run=run, block=block, clock=lambda: 0)
        assert calls == ["read_only_preflight", "native_block"]
    else:
        with pytest.raises(ValueError, match="no new optimization"):
            r.execute(tmp_path, run=run, block=block, clock=lambda: 0)
        assert calls == ["read_only_preflight"]


@pytest.mark.parametrize("budget", [1, 3600, 9000])
def test_preflight_timeout_never_extends_optimizer_budget(tmp_path, budget):
    def run(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

    with pytest.raises(subprocess.TimeoutExpired):
        r.execute(
            tmp_path,
            run=run,
            block=lambda *a, **k: pytest.fail("optimization"),
            clock=lambda: budget,
        )


@pytest.mark.parametrize("count,stages", [(1, 3), (1, 1), (0, 0)])
def test_canonical_products_keep_raw_validation_and_partial_classification(tmp_path, count, stages):
    result, data, config, anchor = fixture("TIME_LIMIT", count, stages)
    directory = tmp_path / "products"
    original = p.export(directory, result, data, config, anchor, remaining=p.LIMIT)
    raw = {f.name: f.read_bytes() for f in directory.iterdir()}
    evidence = {}
    report = g.review(
        directory,
        data,
        config,
        anchor,
        capture=lambda name, value, limit: evidence.update({name: copy.deepcopy(value)}),
    )
    assert report["classification"] == original["classification"]
    assert g.review(directory, data, config, anchor) == report
    if count:
        assert evidence["worker-validation.json"] == original["validation"]
        assert evidence["fresh-report.json"] == original
        assert report["derived_validation_equivalence"]["scientific_tolerances_changed"] is False
    else:
        assert report["validation"]["status"] == "not_applicable_no_incumbent" and not evidence
    assert raw == {f.name: f.read_bytes() for f in directory.iterdir()}


def test_fresh_rejected_report_saved_before_strict_comparison_failure(tmp_path, monkeypatch):
    result, data, config, anchor = fixture()
    directory = tmp_path / "products"
    p.export(directory, result, data, config, anchor, remaining=p.LIMIT)
    evaluate = q.replay.products

    def changed(*args):
        worker, fresh = evaluate(*args)
        fresh["validation"]["failed_check_count"] = 1
        fresh["validation"]["status"] = "rejected"
        return worker, fresh

    monkeypatch.setattr(q.replay, "products", changed)
    saved = {}
    with pytest.raises(ValueError):
        g.review(
            directory,
            data,
            config,
            anchor,
            capture=lambda name, value, limit: saved.update({name: value}),
        )
    assert saved["fresh-report.json"]["validation"]["status"] == "rejected"
    assert "comparison.json" not in saved


def terminal_grid(tmp_path, monkeypatch, stop=None, count=1):
    target, value, _result, _calls = submit(tmp_path, monkeypatch)
    monkeypatch.setenv("SLURM_JOB_ID", "456")
    monkeypatch.setattr(native.old.worker_tools, "resources", lambda: {"scope": "fixture-root"})
    data, config = fixture("TIME_LIMIT", count, 1 if count else 0)[1:3]
    executed = []

    def run_arm(path, plan, threads, job, env, reference, remaining, hard, **kwargs):
        assert 0 < remaining <= p.LIMIT
        assert asdict(native.solver_profile(threads))["time_limit"] == 3600
        index = len(executed)
        executed.append(threads)
        path.mkdir()
        monkeypatch.setenv("SLURM_STEP_ID", str(index))
        result = fixture("TIME_LIMIT", count, 1 if count else 0)[0]
        install_backend(monkeypatch, result, [])
        native._native(
            path,
            plan,
            threads,
            reference,
            remaining,
            recheck=lambda *a: (data, config),
            check=lambda: None,
        )
        attempt = {
            "step_id": f"456.{index}",
            "stop_reason": "fixture_watchdog" if index == stop else None,
            "local_client_reaped": True,
            "return_code": 0,
            "threads": threads,
            "enforcement_contract_sha256": d.digest(native.CONTRACT),
        }
        p.publish(path / "attempt.json", attempt)
        return attempt

    def command(argv, **kwargs):
        job = argv[argv.index("-j") + 1]
        names = (
            [job]
            if "." in job
            else ["456", "456.batch", "456.extern", *(f"456.{i}" for i in range(len(executed)))]
        )
        return command_result("\n".join(f"{name}|COMPLETED|0:0|8" for name in names))

    def independent(path, data, config, anchor, remaining):
        folder = path / "derived-review"
        folder.mkdir()
        report = g.review(
            path / "native/products",
            data,
            config,
            anchor,
            capture=lambda name, value, limit: p.publish(folder / name, value, limit=limit),
        )
        p.publish(path / "independent.json", report)
        return report

    prerequisite = target / "prerequisite"
    prerequisite.mkdir()
    # Genuine public residual check, separate from the explicit native/scheduler doubles.
    public_result, public_data, public_config, public_anchor = fixture()
    original_products = tmp_path / "prior-products"
    original_report = p.export(
        original_products,
        public_result,
        public_data,
        public_config,
        public_anchor,
        remaining=p.LIMIT,
    )
    g.review(
        original_products,
        public_data,
        public_config,
        public_anchor,
        capture=lambda name, value, limit: p.publish(prerequisite / name, value, limit=limit),
    )
    monkeypatch.setattr(q.replay, "original_validation", lambda _: original_report["validation"])
    block = native._batch(
        target,
        recheck=lambda *a: (data, config),
        environment=lambda *a, **k: {"same": True},
        license_check=lambda: {"status": "accepted"},
        run_arm=run_arm,
        independent=independent,
        command=command,
        clock=Clock(),
        export_limit=g.LIMIT - g.RESERVE,
        allocation_deadline=43200,
    )
    p.publish(
        target / "driver.json",
        {
            "status": "block_returned" if stop is None else "blocked_or_partial",
            "source_commit": SOURCE,
            "phase": "fixture",
            "error_kind": None,
            **q.FLAGS,
        },
    )
    monkeypatch.setattr(native, "_recheck", lambda *a: (data, config))
    return target, value, block, command


@pytest.mark.parametrize("stop", [None, 0, 2, 4])
def test_complete_requested_cohort_and_negative_prefix_portable_collection(
    tmp_path, monkeypatch, stop
):
    target, value, block, command = terminal_grid(tmp_path, monkeypatch, stop)
    # Inject fresh public input, not current private NPAD input, into the real collector.
    actual = native._collect
    monkeypatch.setattr(
        native, "_collect", lambda *a, **k: actual(*a, recheck=native._recheck, **k)
    )
    result = q.collect(SOURCE, command=command)
    assert [a["threads"] for a in block["arms"]] == list(d.ORDER[: len(block["arms"])])
    assert result["five_arm_evidence_accounted"] is (stop is None)
    assert result["unrun"] == list(d.ORDER[len(block["arms"]) :])
    assert result["s2_closed"] is False and result["scientific_configuration_selected"] is False
    before = (target / q.ARCHIVE).read_bytes()
    assert q.collect(SOURCE, command=command) == result
    assert (target / q.ARCHIVE).read_bytes() == before
    for index, bad in ((1, "f" * 64), (2, "e" * 40), (3, "d" * 64), (4, "999")):
        args = [result["download"], result["sha256"], SOURCE, result["release_sha256"], "456"]
        args[index] = bad
        with pytest.raises(ValueError):
            q.audit(*args)


def test_no_incumbent_still_accounted_not_infeasibility(tmp_path, monkeypatch):
    _target, _value, _block, command = terminal_grid(tmp_path, monkeypatch, count=0)
    actual = native._collect
    monkeypatch.setattr(
        native, "_collect", lambda *a, **k: actual(*a, recheck=native._recheck, **k)
    )
    result = q.collect(SOURCE, command=command)
    assert result["five_arm_evidence_accounted"] is True
    assert all(
        a["review"]["classification"]["disposition"] == "no_incumbent"
        for a in result["reported_arms"]
    )
    assert result["scientific_configuration_selected"] is False


@pytest.mark.parametrize("kind", ["extra", "duplicate", "link", "tail", "missing"])
def test_outer_archive_scope_closed(tmp_path, kind):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as stream:
        names = sorted(q.MEMBERS)
        if kind == "missing":
            names.pop()
        if kind == "extra":
            names.append("../escape")
        if kind == "duplicate":
            names.append(names[0])
        for index, name in enumerate(names):
            info = tarfile.TarInfo(name)
            info.size = 1
            if kind == "link" and index == 0:
                info.type, info.linkname, info.size = tarfile.SYMTYPE, "outside", 0
            stream.addfile(info, io.BytesIO(b"x"))
    path = tmp_path / "bad.gz"
    path.write_bytes(gzip.compress(buffer.getvalue() + (b"evil" if kind == "tail" else b"")))
    destination = tmp_path / "out"
    destination.mkdir()
    with pytest.raises(ValueError):
        q.extract_outer(path, destination)


def test_full_size_five_observed_length_vectors_fit_new_not_old_envelope(tmp_path):
    # Streaming public byte-size fixture, not fabricated scientific solution evidence.
    for name in ("plan", "job", "batch", "accounting", "review"):
        p.publish(tmp_path / (name + ".json"), {})
    length = 81589895
    for threads in d.ORDER:
        directory = tmp_path / "arms" / f"t{threads}" / "native/products"
        directory.mkdir(parents=True)
        with (directory / "incumbent.json").open("xb") as output:
            output.write(b'"')
            remaining, chunk = length - 2, b"A" * (1024**2)
            while remaining:
                output.write(chunk[: min(remaining, len(chunk))])
                remaining -= min(remaining, len(chunk))
            output.write(b'"')
    files = g.inventory(tmp_path)
    assert sum(v["size"] for v in files.values()) > p.LIMIT
    with pytest.raises(ValueError, match="envelope"):
        p.inventory(tmp_path)
    archive = tmp_path / "size-fixture.tar.gz"
    checksum, packed = g.pack(tmp_path, archive)
    assert packed == files and g.unpack(archive, checksum, packed) == files


@pytest.mark.parametrize("action", ["worker", "repeat", "batch", "optimize"])
@pytest.mark.skipif(
    sys.platform != "linux", reason="Actual Bash closed-action semantics; no cluster"
)
def test_actual_wrapper_rejects_additional_execution(action):
    wrapper = q.ROOT / "scripts/npad_s2_grid3600.sh"
    subprocess.run(["bash", "-n", str(wrapper)], check=True)
    result = subprocess.run(["bash", str(wrapper), action, SOURCE], capture_output=True)
    assert result.returncode == 64
