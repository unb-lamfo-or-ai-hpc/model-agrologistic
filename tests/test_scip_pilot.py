"""Fail-closed qualification, configuration and population admission for SCIP."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from scripts import prepare_scip_pilot as pilot
from src.logic.experiment_runner import load_experiment_manifest
from src.logic.run_integrity import file_sha256


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    identity = {"sha256": "fixture"}
    monkeypatch.setattr(pilot, "implementation_identity", lambda: identity)
    qualified = tmp_path / "qualification"
    qualified.mkdir()
    for name in pilot.REQUIRED_ARTIFACTS:
        (qualified / name).write_text("fixture", encoding="utf-8")
    write_json(qualified / "runtime.json", {
        "status": "runtime_available", "platform": "Linux", "machine": "x86_64",
        "user_site_disabled": True, "pyscipopt_version": "6.2.1", "scip_version": "10.0.2",
        "lp_backend": None, "large_instance_submission_allowed": False,
    })
    (qualified / "native_build.log").write_text(
        "SCIP version 10.0.2 [precision: 8 byte] [LP solver: SoPlex 8.0.2]",
        encoding="utf-8")
    report = {
        "schema_version": "scip-backend-qualification-v1", "status": "accepted",
        "scope": "analytical_and_licensed_parity", "implementation_unchanged": True,
        "skipped_tests": 0, "test_count": 42, "implementation_identity": identity,
        "steps": [{"name": n, "return_code": 0}
                  for n in ("ruff", "native_build", "dependencies", "pytest")],
        "artifacts": {n: file_sha256(qualified / n) for n in pilot.REQUIRED_ARTIFACTS},
    }
    write_json(qualified / "qualification_report.json", report)
    workbook = tmp_path / "model_input.xlsx"
    workbook.write_bytes(b"fixture; preflight deliberately has not loaded this workbook")
    return tmp_path / "pilot", workbook, qualified


def test_prepare_one_pilot_preserves_evidence_and_native_configuration(inputs):
    destination, workbook, qualified = inputs
    old = (qualified / "qualification_report.json").read_bytes()
    manifest = pilot.prepare(*inputs)
    pilot.check(manifest)
    parsed = load_experiment_manifest(manifest)
    assert len(parsed.experiments) == 1
    spec = parsed.experiments[0]
    assert spec.solver.backend == "pyscipopt"
    assert spec.solver.solver_options == {"limits/memory": 131072}
    assert spec.solver.time_limit == 28800
    assert spec.solver.mip_gap == 0.1
    assert spec.solver.threads == 4
    assert not spec.solver.compute_iis
    assert spec.model.mode == "sto"
    assert spec.model.interhub_strong_connectivity
    assert spec.model.pareto_fraction == 0.2
    assert not spec.model.use_direct_origin_customer
    assert not spec.calculate_evpi_vss
    assert spec.workbook == workbook
    assert (qualified / "qualification_report.json").read_bytes() == old
    assert not (destination / "runs").exists()  # No solver/preflight hidden in admission.
    with pytest.raises(FileExistsError):
        pilot.prepare(*inputs)


@pytest.mark.parametrize("field,value", [
    ("status", "rejected"), ("scope", "analytical_only"), ("test_count", 0),
    ("skipped_tests", 1), ("implementation_unchanged", False),
    ("implementation_identity", {"sha256": "changed"}), ("steps", []), ("artifacts", {}),
])
def test_unqualified_or_changed_evidence_rejected(inputs, field, value):
    path = inputs[2] / "qualification_report.json"
    report = json.loads(path.read_text())
    report[field] = value
    write_json(path, report)
    with pytest.raises(ValueError):
        pilot.prepare(*inputs)
    assert not inputs[0].exists()


def test_artifact_modification_rejected(inputs):
    (inputs[2] / "pytest.log").write_text("changed")
    with pytest.raises(ValueError, match="artifact changed"):
        pilot.prepare(*inputs)


@pytest.mark.parametrize("artifact,content", [
    ("native_build.log", "SCIP version 10.0.2 [precision: 8 byte] [LP solver: Gurobi]"),
    ("runtime.json", json.dumps({"status": "runtime_available", "platform": "Windows"})),
])
def test_unreviewed_build_rejected_even_with_matching_hash(inputs, artifact, content):
    directory = inputs[2]
    (directory / artifact).write_text(content)
    report = json.loads((directory / "qualification_report.json").read_text())
    report["artifacts"][artifact] = file_sha256(directory / artifact)
    write_json(directory / "qualification_report.json", report)
    with pytest.raises(ValueError):
        pilot.prepare(*inputs)


@pytest.mark.parametrize("target", ["workbook", "manifest"])
def test_worker_rejects_mutation_after_preparation(inputs, target):
    manifest = pilot.prepare(*inputs)
    if target == "workbook":
        inputs[1].write_bytes(b"changed")
    else:
        doc = yaml.safe_load(manifest.read_text())
        doc["defaults"]["solver"]["time_limit"] = 57600
        manifest.write_text(yaml.safe_dump(doc))
        # Even a changed manifest hash cannot authorize a different experiment.
        receipt_path = inputs[0] / "pilot_admission.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["manifest_sha256"] = file_sha256(manifest)
        write_json(receipt_path, receipt)
    with pytest.raises(ValueError, match="changed"):
        pilot.check(manifest)


@pytest.mark.parametrize("field,value", [
    ("scenario_count", 3), ("period_count", 1), ("routes_oc", 1),
    ("total_variables", 16_000_001), ("workbook_sha256", "changed"),
    ("data_signature", {"counts": {"warehouses": 300}}),
])
def test_preflight_rejects_wrong_dimensions(field, value):
    payload = {
        "workbook_sha256": "frozen", "data_signature": {"counts": {"warehouses": 215}},
        "scenario_count": 9, "period_count": 60, "routes_oc": 0, "total_variables": 14_000_000,
    }
    pilot.validate_preflight(payload, {"workbook_sha256": "frozen"})
    modified = deepcopy(payload)
    modified[field] = value
    with pytest.raises(ValueError, match="outside"):
        pilot.validate_preflight(modified, {"workbook_sha256": "frozen"})


def test_worker_has_no_qos_and_no_automatic_expansion():
    worker = (Path(pilot.__file__).parent / "run_scip_pilot.slurm").read_text()
    assert "#SBATCH --qos" not in worker
    assert "#SBATCH --array" not in worker
    assert "#SBATCH --time=12:00:00" in worker
    assert "#SBATCH --mem=192G" in worker
    assert '--check-preflight' in worker
    assert '.execution-claimed' in worker
    assert '|| solve_rc=$?' in worker  # Still audit an ordinary solver failure.
