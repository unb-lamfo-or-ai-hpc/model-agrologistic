"""Public controls for a fresh claim, predecessor preservation and exact requalification."""

import copy
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

from scripts import mvp2_pyomo_h215_w as engine
from scripts import pyomo_gurobi_retry_contract as policy
from scripts import qualify_pyomo_gurobi_license_v2 as qualifier
from scripts.mvp2_pyomo_gurobi_license_v2 import LicenseCampaign


def encoded(value):
    return (json.dumps(value, sort_keys=True) + "\n").encode()


@pytest.mark.parametrize("solver", engine.SOLVERS)
def test_original_claim_dispatch_is_unchanged(solver):
    claim = Path(f".mvp2-pyomo-{solver}-h215-w-native8h-v1")
    arm = engine.campaign_for_claim(solver, claim)
    assert type(arm) is engine.Campaign
    assert arm.operational_contract is engine.contract
    assert arm.CLAIM == claim.name


def test_new_claim_reuses_science_parameters_and_phase_budgets(monkeypatch):
    arm = engine.campaign_for_claim("gurobi", Path(policy.PRIVATE_CLAIM))
    old = engine.Campaign("gurobi")
    assert isinstance(arm, LicenseCampaign)
    assert arm.CLAIM != old.CLAIM and arm.CASE != old.CASE and arm.ARCHIVE != old.ARCHIVE
    assert arm.operational_contract is policy
    assert arm.budget() == old.budget()
    assert {k: v for k, v in arm.PROFILE.items() if k != "status"} == {
        k: v for k, v in old.PROFILE.items() if k != "status"
    }
    from src.logic.experiment_runner import load_experiment_manifest

    templates = load_experiment_manifest(engine.r.MANIFEST).experiments
    monkeypatch.setattr(engine.o, "specs", lambda _: templates)
    spec, previous = arm.spec(Path("public.xlsx")), old.spec(Path("public.xlsx"))
    assert spec.solver == previous.solver and spec.loader == previous.loader
    assert spec.model == previous.model and spec.workbook == previous.workbook


@pytest.mark.parametrize("solver", ("scip", "cbc"))
def test_new_claim_cannot_select_another_solver(solver):
    with pytest.raises(ValueError, match="Gurobi only"):
        engine.campaign_for_claim(solver, Path(policy.PRIVATE_CLAIM))


def test_existing_new_claim_refuses_before_qualification_or_scheduler(tmp_path, monkeypatch):
    arm = LicenseCampaign()
    claim = tmp_path / arm.CLAIM
    claim.mkdir()
    (claim / "original").write_bytes(b"preserve")
    monkeypatch.setattr(arm, "output_location", lambda _: None)
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    monkeypatch.setattr(arm, "prepare", lambda *a, **k: pytest.fail("No new preparation"))
    with pytest.raises(ValueError, match="Existing Pyomo claim"):
        arm.start(claim, "a" * 40, True, {}, command=lambda *a: pytest.fail("No scheduler"))
    assert (claim / "original").read_bytes() == b"preserve"
    assert not (claim / "submission_intent.json").exists()


def qualified():
    plan = {
        "schema_version": policy.QUALIFICATION_SCHEMA, "source_commit": "a" * 40,
        "packages": engine.PACKAGES, "source_files": {"scripts/new.py": "b" * 64},
        "expected_test_count": policy.EXPECTED_TESTS,
        "preserved_originals": policy.preserved_identity(),
        "private_h215_execution_admitted": False,
    }
    raw = encoded(plan)
    result = {
        "source_commit": plan["source_commit"], "plan_sha256": hashlib.sha256(raw).hexdigest(),
        "job_id": "456", "status": "accepted", "pytest_exit": 0,
        "counts": {"tests": policy.EXPECTED_TESTS, "failures": 0, "errors": 0, "skipped": 0},
        "expected_test_count": policy.EXPECTED_TESTS,
        "source_verified_after": True, "preserved_originals_verified_after": True,
        "public_license_capacity_accepted": True, "failed_tests": [],
        "private_h215_execution_admitted": False,
    }
    return plan, result


def test_new_public_qualification_accepts_exact_executables_and_document_only_changes():
    plan, result = qualified()
    files = {**plan["source_files"], "docs/new.md": "c" * 64}
    assert policy.operational_qualification(encoded(plan), encoded(result), files) == plan


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "rejected"), ("pytest_exit", 1), ("private_h215_execution_admitted", True),
        ("source_verified_after", False), ("preserved_originals_verified_after", False),
        ("public_license_capacity_accepted", False), ("source_commit", "c" * 40),
        ("counts", {"tests": 282, "failures": 0, "errors": 0, "skipped": 0}),
        ("counts", {"tests": 1, "failures": 0, "errors": 0, "skipped": 1}),
    ],
)
def test_old_or_incomplete_public_result_never_qualifies_new_runtime(field, value):
    plan, result = qualified()
    result[field] = value
    with pytest.raises(ValueError, match="not accepted"):
        policy.operational_qualification(encoded(plan), encoded(result), plan["source_files"])


@pytest.mark.parametrize("kind", ("schema", "predecessor", "execution", "source"))
def test_mutated_plan_or_runtime_cannot_reuse_requalification(kind):
    plan, result = qualified()
    files = copy.deepcopy(plan["source_files"])
    if kind == "schema":
        plan["schema_version"] = "public-pyomo-operational-qualification-v1"
    elif kind == "predecessor":
        plan["preserved_originals"]["failed_original"]["archive_sha256"] = "0" * 64
    elif kind == "execution":
        plan["private_h215_execution_admitted"] = True
    else:
        files["scripts/new.py"] = "0" * 64
    result["plan_sha256"] = hashlib.sha256(encoded(plan)).hexdigest()
    with pytest.raises(ValueError):
        policy.operational_qualification(encoded(plan), encoded(result), files)


@pytest.mark.parametrize("fault", (None, "license"))
def test_new_profile_portable_success_and_partial_license_failure(tmp_path, monkeypatch, fault):
    from tests import test_pyomo_h215_operational as controls

    arm = LicenseCampaign()
    monkeypatch.setattr(controls, "m", arm)
    files, plan = controls.operational_files(tmp_path)
    monkeypatch.setattr(arm, "design", lambda _: plan)
    if fault:
        del files["control/sto/gurobi_license.json"]
    report = arm.portable_review(files)
    assert report["operational_receipts_closed"] is (fault is None)
    assert report["status"] == (
        "pyomo_quality_target_met" if fault is None else "pyomo_forensic_partial_preserved"
    )
    assert report["additional_gurobi_execution_admitted"] is False


@pytest.mark.parametrize("fail", (False, True))
@pytest.mark.skipif(sys.platform != "linux", reason="Linux /proc cold worker")
def test_new_claim_cold_bootstrap_preserves_early_identity_and_failure(tmp_path, monkeypatch, fail):
    from tests import test_pyomo_h215_operational as controls

    monkeypatch.setattr(controls, "m", LicenseCampaign())
    controls.test_cold_bootstrap_publishes_before_import_and_retains_failed_stage(tmp_path, fail)


@pytest.mark.parametrize("member", ("../escape", "/absolute", "linked"))
def test_public_preparer_refuses_unsafe_source_members(tmp_path, member):
    archive = tmp_path / "source.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        entry = tarfile.TarInfo(
            member if member.startswith("/") else "model-agrologistic-" + "a" * 40 + "/" + member
        )
        if member == "linked":
            entry.type = tarfile.SYMTYPE
            entry.linkname = "/elsewhere"
        else:
            entry.size = 1
        tar.addfile(entry, io.BytesIO(b"x") if entry.isfile() else None)
    with pytest.raises(ValueError, match="Unsafe"):
        qualifier.extract_source(archive, tmp_path / "out", "a" * 40)


def test_launcher_keeps_original_claim_and_default_strategy_separate():
    wrapper = (engine.ROOT / "scripts/npad_pyomo_gurobi_h215_w_native8h_license_v2.sh").read_text(
        encoding="utf-8"
    )
    assert policy.PRIVATE_CLAIM in wrapper and "SOLVER=gurobi" in wrapper
    assert wrapper.index("Existing Pyomo claim") < wrapper.index("export GRB_LICENSE_FILE=")
    assert "npad_pyomo_h215_w_native8h.sh" not in wrapper
    assert engine.contract.PARAMETERS["gurobi"]["Method"] == -1
    assert engine.contract.PARAMETERS["gurobi"]["Seed"] == 42


def test_public_qualification_cannot_run_on_login(tmp_path, monkeypatch):
    # Failure occurs before any license probe, optimizer or private construction.
    claim = tmp_path / qualifier.CLAIM_NAME
    claim.mkdir()
    plan = {
        "source_commit": "a" * 40, "tests": list(qualifier.TESTS),
        "source_files": {}, "schema_version": policy.QUALIFICATION_SCHEMA,
        "expected_test_count": policy.EXPECTED_TESTS,
    }
    (claim / "plan.json").write_bytes(encoded(plan))
    monkeypatch.setattr(qualifier, "location", lambda p: p)
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    with pytest.raises(ValueError, match="binding"):
        qualifier.run(claim, "a" * 40)
    assert not (claim / "license-capability.json").exists()


def preserved_fixture(tmp_path, monkeypatch):
    def put(directory, name, value):
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = value if isinstance(value, bytes) else encoded(value)
        path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    failed = tmp_path / policy.FAILED_CLAIM
    sha = put(failed, "plan.json", {"source_commit": policy.FAILED_SOURCE})
    monkeypatch.setattr(policy, "FAILED_PLAN_SHA", sha)
    put(failed, "job.json", {
        "source_commit": policy.FAILED_SOURCE, "job_id": "2228189", "plan_sha256": sha,
    })
    sha = put(failed, policy.FAILED_ARCHIVE, b"preserved original archive")
    monkeypatch.setattr(policy, "FAILED_ARCHIVE_SHA", sha)
    old = tmp_path / policy.original.OPERATIONAL_CLAIM
    plan = {
        "schema_version": "public-pyomo-operational-qualification-v1",
        "predecessor": {"plan_sha256": policy.original.PLAN},
        "source_commit": "57204e0b076cf9a52dadab35b089520ba98e0d46",
        "source_files": {"scripts/old.py": "c" * 64},
        "private_h215_execution_admitted": False,
    }
    sha = put(old, "plan.json", plan)
    monkeypatch.setattr(policy, "OLD_QUAL_PLAN_SHA", sha)
    result = {
        "source_commit": plan["source_commit"], "plan_sha256": sha, "job_id": "2227480",
        "status": "accepted", "pytest_exit": 0, "source_verified_after": True,
        "failed_tests": [], "private_h215_execution_admitted": False,
        "counts": {"tests": 282, "failures": 0, "errors": 0, "skipped": 0},
        "cbc_capability": {
            "binary_sha256": policy.original.CBC_SHA,
            "threads_option_accepted": False, "cbc_arm_cancelled": True,
        },
    }
    monkeypatch.setattr(policy, "OLD_QUAL_RESULT_SHA", put(old, "result.json", result))
    proof = tmp_path / policy.LICENSE_CLAIM
    report = {
        "compute_identity": {"job_id": "2228385", "step_id": "0"},
        "status": "accepted", "large_model_construction_allowed": True,
        "private_input_accessed": False, "gurobi_version": [13, 0, 3],
        "environment_scope": "gurobipy_default_environment_as_used_by_appsi",
        "probe_variable_count": 2001, "probe_constraint_count": 2001,
        "solver_status_code": 2, "objective_value": 2001.0,
    }
    monkeypatch.setattr(policy, "LICENSE_REPORT_SHA", put(proof, "license-capability.json", report))
    put(
        proof, "source-identity.txt",
        ("SOURCE_COMMIT=" + policy.LICENSE_SOURCE
         + "\nPUBLIC_LICENSE_PROOF_ONLY; NO_H215_START\n").encode(),
    )
    scripts = {name: put(proof, name, b"preserved public script") for name in policy.LICENSE_FILES}
    monkeypatch.setattr(policy, "LICENSE_FILES", scripts)
    return failed, old, proof


@pytest.mark.parametrize(
    "fault", (None, "archive", "qualification", "license", "identity", "public_script", "job")
)
def test_original_files_are_read_only_and_changed_predecessors_refuse(tmp_path, monkeypatch, fault):
    failed, old, proof = preserved_fixture(tmp_path, monkeypatch)
    targets = {
        "archive": failed / policy.FAILED_ARCHIVE,
        "qualification": old / "result.json",
        "license": proof / "license-capability.json",
        "identity": proof / "source-identity.txt",
        "public_script": proof / next(iter(policy.LICENSE_FILES)),
        "job": failed / "job.json",
    }
    if fault:
        target = targets[fault]
        if fault == "job":
            value = json.loads(target.read_bytes())
            value["job_id"] = "999"
            target.write_bytes(encoded(value))
        else:
            target.write_bytes(target.read_bytes() + b"changed")
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    if fault:
        with pytest.raises((ValueError, json.JSONDecodeError)):
            policy.read_preserved(tmp_path)
    else:
        assert policy.read_preserved(tmp_path) == policy.preserved_identity()
    assert {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before
