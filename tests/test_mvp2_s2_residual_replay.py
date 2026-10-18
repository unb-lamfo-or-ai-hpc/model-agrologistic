"""Existing-vector replay: genuine residuals plus explicit scheduler/archive doubles."""

import copy
import gzip
import io
import json
import math
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from scripts import mvp2_s2_academic as academic
from scripts import mvp2_s2_residual_replay as q
from tests.s2_residual_fixture import fixture, report
from tests.test_mvp2_h300_partial import fixture as native_fixture

SOURCE, JOB = "a" * 40, "777"
KEY = "cost_reconstruction_sparse_rounding_budgets"


def plan():
    return {
        "schema_version": "s2-residual-replay-plan-v1",
        "source_commit": SOURCE,
        "files": {"scripts/mvp2_s2_residual_replay.py": "a" * 64},
        "origin_sha256": "b" * 64,
        "original_products": {},
        "prior": dict(q.ANCHORS),
        "allocation": dict(q.ALLOCATION),
        **q.FLAGS,
    }


def allocation():
    text = (
        "JobId=777 UserId=researcher(1271) JobState=RUNNING NumNodes=1 "
        "Partition=intel-256 Account=sxdsouza NodeList=node1 BatchHost=node1 "
        "NumCPUs=4 NumTasks=1 CPUs/Task=4 MinMemoryNode=16G "
        "TRES=cpu=4,mem=16G,node=1 TimeLimit=00:30:00"
    )
    return academic.allocation(text, JOB, 1271, q.ALLOCATION)


def raw_accounting(state="COMPLETED", code="0:0"):
    return "".join(f"{JOB}{suffix}|{state}|{code}|21\n" for suffix in ("", ".batch", ".extern"))


def certificate():
    data, config, _result = fixture()
    value = report()
    return value, q.witness(data, config)


def test_real_separate_process_original_validator_last_bit_difference():
    code = (
        "import sys;sys.path.insert(0,sys.argv[1]);from tests.s2_residual_fixture import report;"
        "import json;print(json.dumps(report(),sort_keys=True,allow_nan=False))"
    )
    outputs = []
    # Fixed seeds make the public regression reproducible. HPC uses -I; it
    # deliberately ignores PYTHONHASHSEED and is NOT modified by this test.
    for seed in ("11", "23", "47"):
        env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run(
            [sys.executable, "-B", "-c", code, str(q.ROOT)],
            env=env,
            capture_output=True,
            check=True,
            timeout=30,
        )
        outputs.append(json.loads(result.stdout))
    assert len({v[KEY]["transport_od"] for v in outputs}) > 1
    for other in outputs[1:]:
        expected = copy.deepcopy(other)
        expected[KEY] = outputs[0][KEY]
        assert expected == outputs[0]
        value = q.compare(outputs[0], other, certificate()[1])
        assert value["status"] in {"strict_identical", "bounded_transport_budget_order_difference"}
        assert value["scientific_tolerances_changed"] is False


def test_actual_export_and_unchanged_evaluator_read_only(tmp_path):
    result, data, config, anchor = native_fixture()
    directory = tmp_path / "products"
    original = q.p.export(directory, result, data, config, anchor, remaining=q.p.LIMIT)
    before = {f.name: f.read_bytes() for f in directory.iterdir()}
    inventory = {
        f.name: {"size": f.stat().st_size, "sha256": q.p.sha_file(f)} for f in directory.iterdir()
    }
    worker, fresh = q.products(directory, data, config, anchor, inventory)
    assert fresh == original and worker == original["validation"]
    assert (
        q.compare(worker, fresh["validation"], q.witness(data, config))["status"]
        == "strict_identical"
    )
    assert {f.name: f.read_bytes() for f in directory.iterdir()} == before
    inventory["incumbent.json"]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="original transferred"):
        q.products(directory, data, config, anchor, inventory)


@pytest.mark.parametrize(
    "field",
    [
        "status",
        "failed_check_count",
        "absolute_tolerance",
        "relative_tolerance",
        "family_count",
        "unknown",
        "reconstructed_costs",
        "service",
    ],
)
def test_any_non_diagnostic_change_rejected(field):
    original, terms = certificate()
    changed = copy.deepcopy(original)
    if field == "status":
        changed[field] = "rejected"
    elif field == "failed_check_count":
        changed[field] = 1
    elif field.endswith("tolerance"):
        changed[field] *= 2
    else:
        changed[field] = "different"
    with pytest.raises(ValueError):
        q.compare(original, changed, terms)


@pytest.mark.parametrize("component", ["storage", "unmet_demand", "emergency_static_capacity"])
def test_other_rounding_budgets_not_exempt(component):
    original, terms = certificate()
    changed = copy.deepcopy(original)
    changed[KEY][component] = 99.0
    with pytest.raises(ValueError, match="Non-derived"):
        q.compare(original, changed, terms)


@pytest.mark.parametrize("bad", [True, -1.0, math.nan, math.inf, "1", {}, None, 5e-324])
def test_bad_coefficient_terms_rejected(bad):
    with pytest.raises(ValueError):
        q.order_bound([bad])


def test_analytic_bound_does_not_use_arbitrary_decimal_tolerance():
    original, terms = certificate()
    canonical, bound = q.order_bound(terms["transport_od"])
    changed = copy.deepcopy(original)
    changed[KEY]["transport_od"] = math.nextafter(canonical + bound, math.inf)
    with pytest.raises(ValueError, match="analytic"):
        q.compare(original, changed, terms)
    assert q.order_bound([]) == (0, 0)
    assert q.order_bound([0.0]) == (0, 0)
    with pytest.raises(ValueError):
        q.order_bound([1e308, 1e308])


@pytest.mark.parametrize(
    "change", ["source", "prior", "cpus", "memory", "wall", "flags", "path", "hash"]
)
def test_plan_drift_denied(change):
    value = plan()
    if change == "source":
        value["source_commit"] = "c" * 40
    elif change == "prior":
        value["prior"]["job_id"] = "1"
    elif change in {"cpus", "memory", "wall"}:
        value["allocation"][
            {"cpus": "cpus", "memory": "memory_mib", "wall": "wall_seconds"}[change]
        ] += 1
    elif change == "flags":
        value["optimization_performed"] = True
    elif change == "path":
        value["files"]["../escape"] = "a" * 64
    else:
        value["origin_sha256"] = "no"
    with pytest.raises(ValueError):
        q.validate_plan(value, SOURCE)


def batch_fixture(tmp_path, monkeypatch, *, drift=False):
    folder, old = tmp_path / "new", tmp_path / "old"
    folder.mkdir()
    old.mkdir()
    value = plan()
    origin = {"root": "preserved", "reference": "private"}
    value["origin_sha256"] = q.d.digest(origin)
    old_plan = {"runtime": {}, "files": {}}
    monkeypatch.setitem(q.ANCHORS, "native_plan_sha256", q.d.digest(old_plan))
    for root, name, payload in (
        (folder, "job.json", {"job_id": JOB, "plan_sha256": q.d.digest(value)}),
        (folder, "origin.json", origin),
        (old, "origin.json", origin),
        (old, "plan.json", old_plan),
    ):
        q.p.publish(root / name, payload)
    data, config, _result = fixture()
    worker, terms = certificate()
    fresh = {
        "validation": copy.deepcopy(worker),
        "classification": {"disposition": "feasible_partial_hierarchy"},
    }
    if drift:
        fresh["validation"]["failed_check_count"] = 1
        fresh["validation"]["status"] = "rejected"
    monkeypatch.setattr(q, "load", lambda _: (folder, value))
    monkeypatch.setattr(q, "original", lambda: old)
    monkeypatch.setattr(q, "authenticated", lambda _: {})
    monkeypatch.setattr(q.r.source, "verify_tree", lambda *a: None)
    monkeypatch.setattr(q.prior.runtime, "validate", lambda x: x)
    monkeypatch.setattr(q.prior.runtime, "_recheck", lambda *a: (data, config))
    monkeypatch.setattr(
        q.r,
        "query",
        lambda _: " ".join(k + "=" + v for k, v in allocation()["scheduler_fields"].items()),
    )
    monkeypatch.setattr(q.os, "getuid", lambda: 1271, raising=False)
    monkeypatch.setenv("SLURM_JOB_ID", JOB)
    monkeypatch.setattr(q, "products", lambda *a: (worker, fresh))
    monkeypatch.setattr(q, "witness", lambda *a: terms)
    monkeypatch.setattr(q.r.partial, "anchor", lambda *a, **k: {})
    return folder, old, fresh


@pytest.mark.parametrize("drift", [False, True])
def test_batch_preserves_fresh_report_before_comparison_failure(tmp_path, monkeypatch, drift):
    folder, old, fresh = batch_fixture(tmp_path, monkeypatch, drift=drift)
    before = {f.name: f.read_bytes() for f in old.iterdir()}
    q.batch(SOURCE)
    outcome = q.p.read(folder / "result.json")
    assert q.p.read(folder / "fresh-report.json") == fresh
    assert outcome["status"] == ("observed_error" if drift else "existing_vector_replay_qualified")
    assert outcome["phase"] == "derived_budget_comparison"
    assert outcome["fresh_failed_checks"] == int(drift)
    assert all(outcome[k] is False for k in q.FLAGS)
    assert before == {f.name: f.read_bytes() for f in old.iterdir()}
    with pytest.raises(FileExistsError):
        q.batch(SOURCE)


def test_early_failure_is_typed_and_preserved(tmp_path, monkeypatch):
    folder, _old, _fresh = batch_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        q.r.source, "verify_tree", lambda *a: (_ for _ in ()).throw(ValueError("private detail"))
    )
    q.batch(SOURCE)
    outcome = q.p.read(folder / "result.json")
    assert outcome["phase"] == "source_and_prior" and outcome["error_kind"] == "ValueError"
    assert "private detail" not in (folder / "result.json").read_text()


@pytest.mark.parametrize("ack", ["777\n", "777;cluster\n", "invalid", ""])
def test_submission_is_one_shot_and_unknown_ack_consumes_claim(tmp_path, monkeypatch, ack):
    old = tmp_path / "old"
    old.mkdir()
    old_plan = {"runtime": {}, "files": {}}
    q.p.publish(old / "plan.json", old_plan)
    q.p.publish(old / "origin.json", {"root": str(tmp_path / "preserved/source")})
    before = {f.name: f.read_bytes() for f in old.iterdir()}
    monkeypatch.setitem(q.ANCHORS, "native_plan_sha256", q.d.digest(old_plan))
    monkeypatch.setattr(q, "BASE", tmp_path)
    monkeypatch.setattr(q, "original", lambda: old)
    monkeypatch.setattr(q, "authenticated", lambda _: {})
    monkeypatch.setattr(q, "product_inventory", lambda _: {})
    monkeypatch.setattr(q.prior.runtime, "validate", lambda x: x)
    monkeypatch.setattr(q.r.entry, "source_parity", lambda *a: None)
    monkeypatch.setattr(q.r.source, "source_files", lambda *a: plan()["files"])
    monkeypatch.setattr(q.r.source, "verify_tree", lambda *a: None)
    calls = []

    def command(argv, **kwargs):
        calls.append(argv)
        assert kwargs == {"timeout": 30, "limit": 1024}
        assert (q.target() / "submission-intent.json").exists()
        return {"status": "complete", "returncode": 0}, ack.encode()

    if ack.startswith("777"):
        result = q.start(SOURCE, command=command)
        assert result["job_id"] == "777"
        assert q.load(SOURCE)[1]["allocation"] == q.ALLOCATION
    else:
        with pytest.raises(ValueError, match="Unknown submission"):
            q.start(SOURCE, command=command)
        assert not (q.target() / "job.json").exists()
    with pytest.raises(ValueError, match="collect only"):
        q.start(SOURCE, command=command)
    assert len(calls) == 1
    assert "--mem=16384M" in calls[0] and "--time=00:30:00" in calls[0]
    assert before == {f.name: f.read_bytes() for f in old.iterdir()}


@pytest.mark.parametrize("missing", [False, True])
def test_terminal_collection_is_idempotent_and_includes_forensics(tmp_path, monkeypatch, missing):
    folder = tmp_path / "new"
    folder.mkdir()
    source = tmp_path / "prior.gz"
    source.write_bytes(b"original")
    monkeypatch.setattr(q, "load", lambda _: (folder, plan()))
    monkeypatch.setattr(q, "carrier", lambda: source)
    monkeypatch.setattr(q, "status", lambda _: {"job_id": JOB, "accounting": raw_accounting()})
    monkeypatch.setattr(q, "audit", lambda *a: {"job_id": JOB, **q.FLAGS})
    if not missing:
        q.p.publish(folder / "result.json", {"status": "observed_error"})
    first = q.collect(SOURCE)
    before = (folder / q.ARCHIVE).read_bytes()
    assert q.collect(SOURCE) == first
    assert (folder / q.ARCHIVE).read_bytes() == before
    if missing:
        assert q.p.read(folder / "result.json")["phase"] == "missing_batch_receipt"
    assert source.read_bytes() == b"original"
    monkeypatch.setattr(
        q, "status", lambda _: {"job_id": JOB, "accounting": raw_accounting("RUNNING")}
    )
    with pytest.raises(ValueError, match="Not terminal"):
        q.collect(SOURCE)


def build_archive(tmp_path, monkeypatch, *, failed=False, comparison=True):
    value = plan()
    worker, terms = certificate()
    fresh = {"validation": worker, "classification": {"disposition": "feasible_partial_hierarchy"}}
    result = {
        "source_commit": SOURCE,
        "prior": dict(q.ANCHORS),
        "phase": "derived_budget_comparison",
        "status": "existing_vector_replay_qualified" if comparison else "observed_error",
        "error_kind": None,
        "comparison": q.compare(worker, worker, terms) if comparison else None,
        **q.FLAGS,
    }
    raw = raw_accounting("FAILED" if failed else "COMPLETED", "2:0" if failed else "0:0")
    values = {
        "plan.json": value,
        "job.json": {"job_id": JOB, "plan_sha256": q.d.digest(value)},
        "result.json": result,
        "worker-validation.json": worker,
        "fresh-report.json": fresh,
        "witness.json": terms,
        "allocation.json": allocation(),
        "accounting.json": {"raw": raw, "rows": q.r.scheduler.accounting(raw, JOB)},
    }
    monkeypatch.setattr(q, "authenticated", lambda _: {})
    monkeypatch.setattr(q, "product_inventory", lambda _: {})
    monkeypatch.setattr(q, "original_validation", lambda _: worker)
    path = tmp_path / "evidence.tar.gz"
    with tarfile.open(path, "w:gz", format=tarfile.USTAR_FORMAT) as archive:
        for name, payload in values.items():
            encoded = q.c.encoded(payload)
            info = tarfile.TarInfo(name)
            info.size = len(encoded)
            archive.addfile(info, io.BytesIO(encoded))
        info = tarfile.TarInfo("prior.tar.gz")
        info.size = 3
        archive.addfile(info, io.BytesIO(b"OLD"))
    return path


@pytest.mark.parametrize("failed,comparison", [(False, True), (True, True), (False, False)])
def test_portable_audit_separates_integrity_qualification_and_failed_job(
    tmp_path, monkeypatch, failed, comparison
):
    path = build_archive(tmp_path, monkeypatch, failed=failed, comparison=comparison)
    result = q.audit(path, q.p.sha_file(path), SOURCE, JOB)
    assert result["existing_vector_replay_qualified"] is (comparison and not failed)
    assert result["fresh_private_residuals_recomputed_by_portable_auditor"] is False
    assert all(result[k] is False for k in q.FLAGS)
    with pytest.raises(ValueError):
        q.audit(path, "f" * 64, SOURCE, JOB)


def test_portable_audit_rejects_report_not_bound_to_original(tmp_path, monkeypatch):
    path = build_archive(tmp_path, monkeypatch)
    monkeypatch.setattr(q, "original_validation", lambda _: {"fake": "accepted"})
    with pytest.raises(ValueError, match="Original worker"):
        q.audit(path, q.p.sha_file(path), SOURCE, JOB)


@pytest.mark.parametrize(
    "name", ["../escape", "/absolute", "slurm.err", "origin.json", "license.lic"]
)
def test_archive_scope_rejects_private_unknown_or_unsafe_member(tmp_path, name):
    path = tmp_path / "bad.tar.gz"
    with tarfile.open(path, "w:gz", format=tarfile.USTAR_FORMAT) as archive:
        info = tarfile.TarInfo(name)
        info.size = 1
        archive.addfile(info, io.BytesIO(b"x"))
    destination = tmp_path / "out"
    destination.mkdir()
    with pytest.raises(ValueError, match="member scope"):
        q.members(path, destination)
    assert not list(destination.iterdir())


@pytest.mark.parametrize("bad", ["link", "duplicate", "oversize", "tail"])
def test_archive_links_duplicates_caps_and_trailing_payload(tmp_path, monkeypatch, bad):
    path = tmp_path / "bad.tar.gz"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for _ in range(2 if bad == "duplicate" else 1):
            info = tarfile.TarInfo("plan.json")
            info.size = 1
            if bad == "link":
                info.type, info.linkname, info.size = tarfile.SYMTYPE, "outside", 0
            archive.addfile(info, io.BytesIO(b"x"))
    raw = buffer.getvalue() + (b"not-zero" if bad == "tail" else b"")
    path.write_bytes(gzip.compress(raw))
    destination = tmp_path / "out"
    destination.mkdir()
    if bad == "oversize":
        monkeypatch.setattr(q.p, "LIMIT", 11000)
        monkeypatch.setattr(q.p, "METADATA", 0)
    with pytest.raises(ValueError):
        q.members(path, destination)


@pytest.mark.parametrize("action", ["optimize", "repeat"])
def test_no_native_execution_from_cli(action, monkeypatch):
    monkeypatch.setattr(q, "start", lambda *a: pytest.fail("submitted"))
    with pytest.raises(ValueError, match="No optimization"):
        q.main([action, SOURCE])


def test_module_does_not_call_solver_or_license_probe():
    import ast

    tree = ast.parse(Path(q.__file__).read_text())
    names = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert not names & {"optimize", "solve", "gurobipy.Env", "gurobipy.Model", "probe"}
    wrapper = (q.ROOT / "scripts/npad_s2_residual_replay.sh").read_text()
    assert "--one-reviewed-replacement-block-only" not in wrapper
    assert "ACTION=collect" in wrapper and "233abebe97b111fea5f5bbe4cdd4c9f527988e72" in wrapper


@pytest.mark.skipif(sys.platform != "linux", reason="Actual Bash syntax gate; no NPAD lookup")
def test_actual_bash_rejects_bad_actions_before_host_access():
    wrapper = q.ROOT / "scripts/npad_s2_residual_replay.sh"
    subprocess.run(["bash", "-n", str(wrapper)], check=True)
    for action in ("repeat", "optimize", "worker", "batch"):
        done = subprocess.run(["bash", str(wrapper), action, SOURCE], capture_output=True)
        assert done.returncode == 64
