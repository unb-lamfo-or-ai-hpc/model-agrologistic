"""Bounded retry contracts and safe execution without a licensed optimization."""

import json
import subprocess
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts import run_pr25_nine_scenario_retry as retry
from src.logic.experiment_runner import ExperimentManifest, load_experiment_manifest
from src.logic.run_integrity import implementation_identity
from tests.test_experiment_runner import experiment

ROOT = Path(__file__).resolve().parents[1]


def test_retry_changes_only_budget_name_and_declared_provenance():
    original = load_experiment_manifest(ROOT / "experiments/v020_policy_mvp.yaml")
    retries = load_experiment_manifest(ROOT / retry.MANIFEST)
    assert len(retries.experiments) == 2
    for old_index, new in zip((14, 15), retries.experiments, strict=True):
        old = original.experiments[old_index]
        assert new.name == old.name + "_t14400"
        assert new.solver.time_limit == 14400
        assert old.solver.time_limit == 3600
        assert new.metadata == {
            **old.metadata, "retry_of": old.name,
            "retry_reason": "incomplete_lexicographic_hierarchy_at_3600_seconds",
            "time_limit_seconds": 14400,
        }
        normalized = replace(new, name=old.name, metadata=old.metadata,
                             solver=replace(new.solver, time_limit=old.solver.time_limit))
        assert asdict(normalized) == asdict(old)
        assert retries.output_dir != original.output_dir


def reference_entries(filename):
    plan = yaml.safe_load((ROOT / "experiments" / filename).read_text())
    entries = {}
    for campaign in plan["campaigns"]:
        manifest = load_experiment_manifest(ROOT / campaign["manifest"])
        for index in campaign["indices"]:
            spec = manifest.experiments[index]
            assert spec.name not in entries
            entries[spec.name] = (asdict(spec), campaign["output_dir"])
    return entries


def test_final_plan_preserves_eight_references_and_retains_two_nine_scenario_cases():
    old = reference_entries("v020_validation_reference_t3600.yaml")
    new = reference_entries("v020_validation_reference_t14400.yaml")
    assert len(old) == len(new) == 10
    shared = old.keys() & new.keys()
    assert len(shared) == 8
    assert all(old[name] == new[name] for name in shared)
    assert new.keys() - old.keys() == {
        "policy_sto9_p20_warehouse_t14400", "policy_sto9_p20_direct_t14400",
    }
    assert all(new[name][1].endswith("policy-nine-t14400") for name in new.keys() - old.keys())


@pytest.fixture
def context(tmp_path, monkeypatch):
    import src.logic.experiment_runner as runner
    import src.logic.v020_validation as validation

    workbook = tmp_path / "input.xlsx"
    workbook.write_bytes(b"not loaded by the submission guard")
    spec = replace(experiment(), workbook=workbook)
    output = tmp_path / "new-results"
    manifest = ExperimentManifest([spec, replace(spec, name="second")], output)
    monkeypatch.setattr(runner, "load_experiment_manifest", lambda _: manifest)
    quality = tmp_path / retry.QUALITY
    quality.parent.mkdir(parents=True)
    quality.write_text(json.dumps({"status": "accepted", "skipped_tests": 0,
                                  "implementation_sha256": implementation_identity()["sha256"]}))
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (
        calls.append((a, kw)) or SimpleNamespace(returncode=0)
    ))
    monkeypatch.setattr(validation, "assess_run", lambda *_: {"status": "accepted"})
    monkeypatch.setenv("SLURM_JOB_ID", "fixture")
    return SimpleNamespace(root=tmp_path, quality=quality, output=output,
                           spec=spec, calls=calls, validation=validation)


@pytest.mark.parametrize("field,value", [("status", "rejected"), ("skipped_tests", 1),
                                         ("implementation_sha256", "wrong")])
def test_mismatched_quality_never_launches(context, field, value):
    quality = json.loads(context.quality.read_text())
    quality[field] = value
    context.quality.write_text(json.dumps(quality))
    with pytest.raises(ValueError, match="Quality/runtime mismatch"):
        retry.run_retry(0, project_root=context.root)
    assert not context.calls


def test_check_only_never_launches(context):
    assert retry.run_retry(0, check_only=True, project_root=context.root) == 0
    assert not context.calls
    assert not context.output.exists()


def test_login_node_cannot_start_solver(context, monkeypatch):
    monkeypatch.delenv("SLURM_JOB_ID")
    with pytest.raises(ValueError, match="not the login node"):
        retry.run_retry(0, project_root=context.root)
    assert not context.calls


def test_existing_partial_output_is_preserved(context, monkeypatch):
    directory = context.output / context.spec.name
    directory.mkdir(parents=True)
    artifact = directory / "result.json"
    artifact.write_text("historical partial result")
    monkeypatch.setattr(context.validation, "assess_run", lambda *_: {"status": "rejected"})
    with pytest.raises(ValueError, match="Existing unaccepted output preserved"):
        retry.run_retry(0, project_root=context.root)
    assert artifact.read_text() == "historical partial result"
    assert not context.calls


def test_existing_accepted_result_is_not_resolved(context):
    (context.output / context.spec.name).mkdir(parents=True)
    assert retry.run_retry(0, project_root=context.root) == 0
    assert not context.calls


@pytest.mark.parametrize("status,code", [("accepted", 0), ("pending", 1), ("rejected", 1)])
def test_post_solve_acceptance_controls_exit(context, monkeypatch, status, code):
    monkeypatch.setattr(context.validation, "assess_run", lambda *_: {"status": status})
    assert retry.run_retry(0, project_root=context.root) == code
    command = context.calls[0][0][0]
    assert command[-4:] == ["--index", "0", "--output-dir", str(context.output)]


def test_child_failure_propagates_without_claiming_acceptance(context, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=7))
    assert retry.run_retry(0, project_root=context.root) == 7


def test_unknown_index_is_rejected(context):
    with pytest.raises(ValueError, match="Only retry indices"):
        retry.run_retry(9, project_root=context.root)
    assert not context.calls


def test_missing_workbook_never_launches(context):
    context.spec.workbook.unlink()
    with pytest.raises(FileNotFoundError, match="OSRM workbook"):
        retry.run_retry(0, project_root=context.root)
    assert not context.calls


def test_batch_launcher_is_isolated_lf_and_bounded():
    path = ROOT / "scripts/run_pr25_nine_scenario_retry.slurm"
    content = path.read_bytes()
    assert b"\r" not in content
    assert b"PYTHONNOUSERSITE=1" in content
    assert b"--array=0-1%2" in content
    assert b"--mem=96G" in content
    assert b"--time=06:00:00" in content


def test_memory_retry_changes_only_memory_and_declared_retry_identity():
    original = load_experiment_manifest(ROOT / retry.MANIFEST)
    current = load_experiment_manifest(ROOT / retry.MEMORY_MANIFEST)
    assert len(current.experiments) == 1
    old, new = original.experiments[0], current.experiments[0]
    assert new.name == old.name + "_mem128"
    assert old.solver.solver_options["SoftMemLimit"] == 56
    assert new.solver.solver_options == {**old.solver.solver_options, "SoftMemLimit": 128}
    normalized = replace(
        new, name=old.name, metadata=old.metadata,
        solver=replace(new.solver, solver_options=old.solver.solver_options),
    )
    assert asdict(normalized) == asdict(old)
    assert new.metadata["retry_of"] == old.name
    assert new.metadata["prior_slurm_job_id"] == "2088823_0"
    assert new.metadata["requested_memory_gib"] == 192
    assert current.output_dir != original.output_dir


def test_memory_reference_plan_preserves_all_nine_accepted_cases():
    old = reference_entries("v020_validation_reference_t14400.yaml")
    new = reference_entries("v020_validation_reference.yaml")
    assert len(old) == len(new) == 10
    shared = old.keys() & new.keys()
    assert len(shared) == 9
    assert all(old[name] == new[name] for name in shared)
    assert old.keys() - new.keys() == {"policy_sto9_p20_warehouse_t14400"}
    assert new.keys() - old.keys() == {"policy_sto9_p20_warehouse_t14400_mem128"}


@pytest.fixture
def memory_context(context, monkeypatch):
    import src.logic.experiment_runner as runner

    manifest = ExperimentManifest([context.spec], context.output)
    monkeypatch.setattr(runner, "load_experiment_manifest", lambda _: manifest)
    monkeypatch.setenv("SLURM_MEM_PER_NODE", "196608")
    monkeypatch.setenv("SLURM_CPUS_PER_TASK", "16")
    return context


@pytest.mark.parametrize("memory,cpus", [("98304", "16"), ("196608", "8"), ("0", "16")])
def test_memory_retry_rejects_undersized_allocation(memory_context, monkeypatch, memory, cpus):
    monkeypatch.setenv("SLURM_MEM_PER_NODE", memory)
    monkeypatch.setenv("SLURM_CPUS_PER_TASK", cpus)
    with pytest.raises(ValueError, match="requires --mem=192G"):
        retry.run_retry(0, memory_retry=True, project_root=memory_context.root)
    assert not memory_context.calls


def test_memory_retry_uses_only_new_manifest(memory_context):
    assert retry.run_retry(0, memory_retry=True, project_root=memory_context.root) == 0
    command = memory_context.calls[0][0][0]
    assert command[2] == str(memory_context.root / retry.MEMORY_MANIFEST)


def test_memory_retry_preflight_does_not_require_compute_allocation(memory_context, monkeypatch):
    for name in ("SLURM_JOB_ID", "SLURM_MEM_PER_NODE", "SLURM_CPUS_PER_TASK"):
        monkeypatch.delenv(name)
    assert retry.run_retry(0, memory_retry=True, check_only=True,
                           project_root=memory_context.root) == 0
    assert not memory_context.calls


def test_memory_retry_cannot_select_direct_case(memory_context):
    with pytest.raises(ValueError, match="only warehouse index 0"):
        retry.run_retry(1, memory_retry=True, project_root=memory_context.root)
    assert not memory_context.calls


def test_memory_launcher_is_single_job_and_preserves_time_and_thread_budget():
    content = (ROOT / "scripts/run_pr25_warehouse_memory_retry.slurm").read_bytes()
    assert b"\r" not in content
    assert b"--array" not in content
    for setting in (b"--mem=192G", b"--cpus-per-task=16", b"--time=06:00:00",
                    b"PYTHONNOUSERSITE=1", b"--memory-retry --index 0"):
        assert setting in content
