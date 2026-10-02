"""Adversarial checks for stale runs, altered artifacts and value bounds."""

import json
from dataclasses import replace

import pytest

from src.logic.experiment_runner import (
    ExperimentManifest,
    _checkpoint_identity,
    aggregate_experiment_summaries,
    run_experiment,
)
from src.logic.objective_diagnostics import stage_degradation_records
from src.logic.optimization import OptimizationResult
from src.logic.run_integrity import scientific_identity, verify_completion, write_completion
from src.logic.stochastic_analysis_gurobipy import _solver_objective_interval
from tests.test_experiment_runner import experiment, fake_loader, fake_solver


def test_completion_rejects_stale_or_modified_artifacts(tmp_path):
    names = ["result.json", "run_summary.json", "independent_validation.json"]
    paths = [tmp_path / name for name in names]
    for path in paths:
        path.write_text("{}", encoding="utf-8")
    assert not verify_completion(tmp_path, "a")[0]
    write_completion(tmp_path, "a", paths)
    assert verify_completion(tmp_path, "a")[0]
    assert verify_completion(tmp_path, "b") == (False, "run_contract_mismatch")
    paths[0].write_text('{"changed": true}', encoding="utf-8")
    assert verify_completion(tmp_path, "a") == (False, "artifact_integrity_failure")


def test_manifest_aggregation_excludes_old_contract_without_deleting_it(tmp_path):
    spec = experiment()
    run_experiment(spec, tmp_path, loader=fake_loader, solver=fake_solver)
    changed = replace(spec, model=replace(spec.model, days_per_period=31))
    manifest = ExperimentManifest([changed], tmp_path)
    aggregate_experiment_summaries(tmp_path, manifest=manifest)
    audit = json.loads((tmp_path / "aggregation_audit.json").read_text())
    assert audit["excluded_count"] == 1
    assert (tmp_path / spec.name / "result.json").exists()
    aggregate_experiment_summaries(tmp_path, manifest=ExperimentManifest([spec], tmp_path))
    audit = json.loads((tmp_path / "aggregation_audit.json").read_text())
    assert audit["excluded_count"] == 0


def test_checkpoint_changes_with_model_but_not_resume_flag():
    spec = experiment()
    assert _checkpoint_identity(spec) != _checkpoint_identity(
        replace(spec, model=replace(spec.model, days_per_period=31))
    )
    assert scientific_identity({("a", "b"): 1, "c": 2}) == scientific_identity(
        {"c": 2, ("a", "b"): 1}
    )


def test_stage_final_drift_uses_configured_gap_not_only_objn_tolerances():
    stages = [
        {
            "stage_role": "emergency_capacity",
            "objective_value": 416362286.0465711,
            "objective_bound": 416300000.0,
            "status": "OPTIMAL",
        }
    ]
    records = stage_degradation_records(
        stages,
        {"expected_emergency_capacity": 420424935.6313212},
        mip_gap=0.01,
        mip_gap_abs=1e-10,
        objective_abs_tol=1e-6,
    )
    row = records[0]
    assert row["final_minus_pass_objective"] > 4e6
    assert row["within_mip_degradation_limit"] is True
    assert row["objective_relative_tolerance"] == 0.0


@pytest.mark.parametrize("bound,objective", [(float("nan"), 1), (0, float("inf"))])
def test_nonfinite_value_intervals_are_unavailable(bound, objective):
    result = OptimizationResult(
        status="optimal",
        metadata={
            "gurobi_objective_value": objective,
            "gurobi_objective_bound": bound,
        },
    )
    assert _solver_objective_interval(result) is None


def test_reversed_minimization_interval_is_not_silently_sorted():
    result = OptimizationResult(
        status="optimal",
        metadata={
            "gurobi_objective_value": 10.0,
            "gurobi_objective_bound": 12.0,
        },
    )
    with pytest.raises(ValueError, match="bound exceeds"):
        _solver_objective_interval(result)
