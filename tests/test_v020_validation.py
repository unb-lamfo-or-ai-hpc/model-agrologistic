"""Four-level acceptance rejects missing, unlicensed and corrupted evidence."""

from dataclasses import replace

from src.logic.experiment_runner import ExperimentManifest, run_experiment
from src.logic.run_integrity import implementation_identity
from src.logic.v020_validation import assess_run, build_validation_report, report_markdown
from tests.test_experiment_runner import experiment
from tests.test_solution_validation import analytical_solution


def test_analytical_reference_is_accepted_but_changed_contract_is_not(tmp_path, monkeypatch):
    monkeypatch.setenv("SLURM_JOB_ID", "fixture-not-a-real-hpc-execution")
    data, config, result = analytical_solution()
    result.metadata["timings"] = {
        "model_build_seconds": 0.1,
        "optimization_seconds": 0.2,
        "result_extraction_seconds": 0.01,
    }
    spec = replace(experiment(), model=config)
    run_experiment(spec, tmp_path, loader=lambda *_: data, solver=lambda **_: result)
    report = assess_run(spec, tmp_path)
    assert report["status"] == "accepted", report
    changed = replace(spec, model=replace(config, days_per_period=31))
    assert assess_run(changed, tmp_path)["status"] == "pending"
    (tmp_path / spec.name / "flows.csv").write_text("changed", encoding="utf-8")
    assert assess_run(spec, tmp_path)["status"] == "pending"


def test_old_trl6_or_local_skips_cannot_certify_v020(tmp_path, monkeypatch):
    import src.logic.v020_validation as validation

    spec = experiment()
    monkeypatch.setattr(
        validation, "load_experiment_manifest", lambda _: ExperimentManifest([spec], tmp_path)
    )
    plan = {
        "scope": "test fixture",
        "campaigns": [
            {"profile": "fixture", "manifest": "unused.yaml", "indices": [0], "output_dir": "."}
        ],
    }
    quality = {
        "implementation_sha256": implementation_identity()["sha256"],
        "status": "accepted",
        "skipped_tests": 1,
    }
    report = build_validation_report(plan, tmp_path, quality)
    assert report["overall_status"] == "pending"
    assert report["levels"][1]["status"] == "pending"
    assert report["historical_numerical_replication"] == "not_established"
    assert "pending" in report_markdown(report)


def test_all_levels_are_required_even_when_quality_passed(tmp_path, monkeypatch):
    import src.logic.v020_validation as validation

    spec = experiment()
    monkeypatch.setattr(
        validation, "load_experiment_manifest", lambda _: ExperimentManifest([spec], tmp_path)
    )
    plan = {
        "scope": "fixture",
        "campaigns": [
            {"profile": "fixture", "manifest": "unused", "indices": [0], "output_dir": "."}
        ],
    }
    quality = {
        "implementation_sha256": implementation_identity()["sha256"],
        "status": "accepted",
        "skipped_tests": 0,
    }
    report = build_validation_report(plan, tmp_path, quality)
    assert report["levels"][1]["status"] == "accepted"
    assert report["overall_status"] == "pending"
