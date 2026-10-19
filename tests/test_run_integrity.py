"""Adversarial checks for stale runs, altered artifacts and value bounds."""

import json
from dataclasses import replace

from src.logic.experiment_runner import (
    ExperimentManifest,
    _checkpoint_identity,
    aggregate_experiment_summaries,
    run_experiment,
)
from src.logic.run_integrity import scientific_identity, verify_completion, write_completion
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
