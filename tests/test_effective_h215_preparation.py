"""Public witnesses and preparation barriers; no numerical solver is executed."""

import json
from pathlib import Path
from types import SimpleNamespace

import pyomo.environ as pyo
import pytest

from scripts import effective_h215_public as public
from scripts.effective_ci_scope import classify
from scripts.effective_h215_protocol import PROTOCOL, cases
from scripts.effective_h215_public_controls import control_specs, expected, make_control
from src.logic.effective_baseline import build_effective_model, sha256
from src.logic.effective_gurobi_execution import export_effective_solution, settings
from src.logic.optimization import OptimizationResult


def test_finite_protocol_and_public_inventory_are_separate():
    protocol = json.loads(PROTOCOL.read_text())
    records, controls = cases(), control_specs()
    assert len(records) == len({r["id"] for r in records}) == 18
    assert len(controls) == len({r["id"] for r in controls}) == 48
    assert not protocol["execution_authorized"]
    assert all(r["job_id"] is None and r["status"] == "not_submitted" for r in records)
    assert sum(r["beta"] is None and r["alpha"] is None for r in records) == 2
    assert {r["mode"] for r in records} == {"det", "sto"}
    assert {c["threads"] for c in controls} == {1, 4}
    assert sum(c["kind"] == "infeasible" for c in controls) == 4
    assert protocol["proposed_execution_profile"]["memory_mib"] == 196608
    assert protocol["proposed_execution_profile"]["ConcurrentMIP"] == 1


@pytest.mark.parametrize("control", control_specs(), ids=lambda c: c["id"])
def test_public_analytical_witnesses_and_exact_export(control):
    data, cfg, _ = make_control(control)
    built = build_effective_model(data, cfg, max_variables=256)
    try:
        wanted = expected(control)
        if control["kind"] == "infeasible":
            # Hard shipping is zero; beta requires nine delivered tonnes.
            assert data.shipping_capacity["W"] == 0
            assert control["beta"] * 10 == 9
            assert len(built.model.effective_policy.service_floor) == len(built.data.scenarios)
            return
        for var in built.model.component_data_objects(pyo.Var):
            var.set_value(0)
        if control["kind"] == "candidate":
            built.first["open_candidate"]["W"].set_value(1)
            built.first["candidate_capacity"]["W"].set_value(10 / 6)
        for s in built.data.scenarios:
            built.flows["OD"][s, "O", "W", "P", "t"].set_value(10)
            built.flows["DC"][s, "W", "C", "P", "t"].set_value(wanted["served_t"])
            built.flows["DC"][s, "W", "X", "P", "t"].set_value(wanted["export_t"])
            built.unmet[s, "C", "P", "t"].set_value(wanted["unmet_t"])
        for row in built.model.component_data_objects(pyo.Constraint, active=True):
            value = pyo.value(row.body)
            if row.has_lb():
                assert value >= pyo.value(row.lower) - 1e-8, row.name
            if row.has_ub():
                assert value <= pyo.value(row.upper) + 1e-8, row.name
        assert pyo.value(built.model.objective) == pytest.approx(wanted["objective"])
        result = OptimizationResult(
            status="optimal",
            solver_backend="pyomo",
            solver_name="manual_witness",
            model_mode=cfg.mode,
            metadata={"objective_bound": wanted["objective"], "timings": {}},
        )
        result = export_effective_solution(built, data, cfg, result)
        assert result.metadata["effective_validation"]["status"] == "accepted"
        assert result.objective_value == pytest.approx(wanted["objective"])
        assert len(result.unmet_demand) == len(built.data.scenarios)
        exports = [r for r in result.flows if r.get("customer") == "X"]
        assert len(exports) == len(built.data.scenarios)
        assert all(r["value"] == pytest.approx(wanted["export_t"]) for r in exports)
        assert all(r["value"] == pytest.approx(wanted["unmet_t"]) for r in result.unmet_demand)
        if control["kind"] == "endpoint":
            assert all(r["value"] == 0 for r in exports + result.unmet_demand)
    finally:
        built.model.clear()


@pytest.mark.parametrize(
    "override",
    [
        dict(threads=2),
        dict(threads=True),
        dict(native_seconds=0),
        dict(native_seconds=28801),
        dict(native_seconds=float("nan")),
        dict(mip_gap=0.1),
        dict(mip_gap=True),
    ],
)
def test_unqualified_native_settings_rejected_before_construction(override):
    kwargs = dict(threads=4, native_seconds=30, mip_gap=0)
    kwargs.update(override)
    with pytest.raises(ValueError):
        settings(**kwargs)


def test_future_profile_and_negative_control_are_explicit():
    profile = settings(threads=4, native_seconds=28800, mip_gap=0.01)
    assert profile["Method"] == -1 and profile["ConcurrentMIP"] == 1
    assert profile["DualReductions"] == 1
    assert (
        settings(threads=1, native_seconds=30, mip_gap=0, diagnostic_infeasible=True)[
            "DualReductions"
        ]
        == 0
    )


def test_public_paths_and_plan_tampering_fail_without_execution(tmp_path, monkeypatch):
    monkeypatch.setattr(public, "BASE", tmp_path)
    claim = tmp_path / public.CLAIM
    assert public.location(claim) == claim.absolute()
    for path in (tmp_path, tmp_path / "other", tmp_path / "sub" / public.CLAIM):
        with pytest.raises(ValueError):
            public.location(path)
    claim.mkdir()
    public.write_new(claim / "plan.json", {"original": True})
    before = sha256(claim / "plan.json")
    with pytest.raises(FileExistsError):
        public.write_new(claim / "plan.json", {})
    with pytest.raises(ValueError):
        public.execute(claim, before, "wrong acknowledgment")
    with pytest.raises(ValueError):
        public.execute(claim, "0" * 64, public.ACK)
    assert sha256(claim / "plan.json") == before
    assert not (claim / "started.json").exists()


def test_bad_archive_rejected_before_claim_creation(tmp_path, monkeypatch):
    monkeypatch.setattr(public, "BASE", tmp_path)
    monkeypatch.setattr(public.platform, "system", lambda: "Linux")
    archive = tmp_path / "source.tar.gz"
    archive.write_bytes(b"not an admitted archive")
    with pytest.raises(ValueError):
        public.prepare(tmp_path / public.CLAIM, archive, "a" * 40, "0" * 64)
    assert not (tmp_path / public.CLAIM).exists()


def test_prepare_is_one_shot_metadata_only_and_binds_inventory(tmp_path, monkeypatch):
    monkeypatch.setattr(public, "BASE", tmp_path)
    monkeypatch.setattr(public.platform, "system", lambda: "Linux")
    monkeypatch.setattr(public, "runtime", lambda: {"test": "metadata-only"})
    monkeypatch.setattr(
        public,
        "extract_source",
        lambda *args: {"scripts/effective_h215_public.py": sha256(public.__file__)},
    )
    archive = tmp_path / "source.tar.gz"
    archive.write_bytes(b"mocked extraction; no external process")
    claim = tmp_path / public.CLAIM
    receipt = public.prepare(claim, archive, "a" * 40, sha256(archive))
    assert receipt["status"] == "prepared_no_job"
    assert receipt["submission_performed"] is False
    plan = json.loads((claim / "plan.json").read_text())
    assert plan["controls"] == control_specs()
    assert plan["software_test_count"] == 181
    assert "tests/test_effective_h215_preparation.py" in plan["software_test_inventory"]
    assert plan["private_execution_allowed"] is False
    assert not (claim / "started.json").exists()
    with pytest.raises(FileExistsError):
        public.prepare(claim, archive, "a" * 40, sha256(archive))
    assert sha256(claim / "plan.json") == receipt["plan_sha256"]


@pytest.mark.parametrize("invalid", [None, "smt", "memory", "shared"])
def test_compute_allocation_affinity_and_memory_barriers(monkeypatch, invalid):
    from scripts import npad_pyomo_h400_e1_cgroup_probe as cg
    from scripts import pyomo_gurobi_license_gate as license

    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setenv("SLURM_STEP_ID", "0")
    monkeypatch.setattr(license, "compute_context", lambda: None)
    monkeypatch.setattr(public.os, "sched_getaffinity", lambda pid: set(range(16)), raising=False)
    monkeypatch.setattr(
        public.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            stdout=(
                "Partition=intel-256 NumNodes=1 OverSubscribe="
                + ("YES" if invalid == "shared" else "NO")
            )
        ),
    )
    monkeypatch.setattr(cg, "cgroup_locations", lambda *a: (1, 2, 3, 4))
    monkeypatch.setattr(
        cg,
        "memory_snapshot",
        lambda *a: {
            "status": ("rejected" if invalid == "memory" else "cgroup_memory_capabilities_present")
        },
    )

    def fake_read(path, *args, **kwargs):
        if path.name == "physical_package_id":
            return "0"
        if path.name == "core_id":
            cpu = int(path.parent.parent.name[3:])
            return str(cpu % 8 if invalid == "smt" else cpu)
        return "mocked /proc"

    monkeypatch.setattr(Path, "read_text", fake_read)
    if invalid:
        with pytest.raises(ValueError):
            public.compute_snapshot()
    else:
        receipt = public.compute_snapshot()
        assert receipt["job_id"] == "123"
        assert len(set(receipt["topology"])) == 16


def test_generated_batch_has_finite_public_limits_and_no_submission():
    claim = public.BASE / public.CLAIM
    batch = public.batch_text(claim, claim / "source", "a" * 64)
    assert "--mem=192G" in batch and "--hint=nomultithread" in batch
    assert "--exclusive" in batch and "--time=01:00:00" in batch
    assert "sbatch " not in batch and "scancel " not in batch
    assert public.ACK in batch and str(public.BASE) in batch
    code = Path(public.__file__).read_text()
    assert 'add_parser("submit")' not in code
    assert 'add_parser("private")' not in code


@pytest.mark.parametrize(
    "path",
    [
        "src/logic/effective_gurobi_execution.py",
        "scripts/effective_h215_public.py",
        "scripts/effective_h215_public_controls.py",
        "scripts/effective_h215_protocol.py",
        "tests/test_effective_h215_preparation.py",
        "experiments/h215_policy_protocol_v1.json",
    ],
)
def test_preparation_routes_to_guarded_ci(path):
    assert classify([path])["data_only"]
