"""Scoped pilot reports preserve evidence and never certify unexecuted cases."""

import json
from types import SimpleNamespace

import pytest

from scripts.audit_nine_campaign import (
    classify_stages,
    main,
    selected_indices,
    stage_termination_details,
)
from src.logic.run_integrity import write_completion


@pytest.mark.parametrize("indices", [[], [0, 0], [-1], [2]])
def test_invalid_selection(indices):
    with pytest.raises(ValueError):
        selected_indices(indices, 2)


def test_indices_preserve_original_identity():
    assert selected_indices(None, 3) == [0, 1, 2]
    assert selected_indices([2, 0], 3) == [2, 0]


def stages():
    return [{"stage_role": role, "final_objective_value": 0.0,
             "mip_gap": 0.01, "within_mip_degradation_limit": True}
            for role in ("unmet_demand", "emergency_capacity", "economic_cost")]


def test_duplicate_stage_cannot_be_certified():
    rows = stages()
    assert classify_stages(rows + [rows[0]], "accepted") == "incomplete_hierarchy"


def test_memory_limited_capacity_pass_preserves_missing_economic_gap():
    rows = stages()[:2]
    rows[0].update(status="OPTIMAL", status_code=2)
    rows[1].update(status="MEM_LIMIT", status_code=17, mip_gap=1.0)
    before = json.dumps(rows)
    details = stage_termination_details(rows)
    assert classify_stages(rows, "accepted") == "incomplete_hierarchy"
    assert details["memory_limit_reported"] is True
    assert details["emergency_capacity_stage_status"] == "MEM_LIMIT"
    assert details["emergency_capacity_stage_mip_gap"] == 1.0
    assert details["economic_cost_stage_status"] is None
    assert details["economic_cost_stage_mip_gap"] is None
    assert details["unreported_stage_roles"] == ["economic_cost"]
    assert json.dumps(rows) == before


def test_termination_details_do_not_invent_missing_or_duplicate_status():
    assert stage_termination_details([])["reported_stage_count"] == 0
    rows = stages()
    rows[2].update(status="TIME_LIMIT", status_code=9, mip_gap=0.5052)
    details = stage_termination_details(rows)
    assert details["memory_limit_reported"] is False
    assert details["economic_cost_stage_status"] == "TIME_LIMIT"
    assert classify_stages(rows, "accepted") == "gap_target_not_attained"
    details = stage_termination_details(rows + [rows[2]])
    assert details["economic_cost_stage_status"] is None
    assert details["economic_cost_stage_mip_gap"] is None


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    from src.logic import experiment_runner

    manifest_path = tmp_path / "campaign.yaml"
    manifest_path.write_text("fixture: immutable\n")
    run_root = tmp_path / "runs"
    specs = [SimpleNamespace(name=f"case_{i}", metadata={"warehouse_population": 215},
                             solver=SimpleNamespace(mip_gap=0.1, time_limit=28800))
             for i in range(2)]
    manifest = SimpleNamespace(experiments=specs, output_dir=run_root)
    monkeypatch.setattr(experiment_runner, "load_experiment_manifest", lambda _: manifest)
    monkeypatch.setattr(experiment_runner, "_checkpoint_identity", lambda _: "fixture")
    run = run_root / "case_0"
    run.mkdir(parents=True)
    payloads = {
        "result.json": {"result": {"status": "optimal", "metadata": {
            "lexicographic_stages": stages(), "timings": {"optimization_seconds": 12.0}}}},
        "independent_validation.json": {"status": "accepted"},
        "run_summary.json": {"material_balance_ok": True, "domestic_service_level": 1.0,
                             "total_unmet_demand": 0, "economic_cost": 123.0},
    }
    for name, payload in payloads.items():
        (run / name).write_text(json.dumps(payload))
    write_completion(run, "fixture", [run / name for name in payloads])
    return manifest_path, run


def test_scoped_snapshot_does_not_modify_source_or_certify_missing_cases(evidence, tmp_path):
    manifest, run = evidence
    before = {path.name: path.read_bytes() for path in run.iterdir()}
    output = tmp_path / "pilot-report"
    assert main([str(manifest), "--indices", "0", "--output-dir", str(output),
                 "--require-accepted"]) == 0
    receipt = json.loads((output / "nine_audit_manifest.json").read_text())
    assert receipt["overall_status"] == "accepted"
    assert receipt["selected_indices"] == [0]
    assert receipt["unassessed_indices"] == [1]
    assert receipt["campaign_instance_count"] == 2
    rows = json.loads((output / "nine_results.json").read_text())
    assert rows[0]["material_balance_ok"] is True
    assert rows[0]["economic_cost"] == 123.0
    assert rows[0]["independent_validation_status"] == "accepted"
    assert rows[0]["reported_stage_count"] == 3
    assert rows[0]["economic_cost_stage_mip_gap"] == 0.01
    assert rows[0]["unreported_stage_roles"] == []
    assert before == {path.name: path.read_bytes() for path in run.iterdir()}
    with pytest.raises(SystemExit):
        main([str(manifest), "--output-dir", str(output)])


def test_missing_case_is_reported_before_nonzero_exit(evidence, tmp_path):
    manifest, _ = evidence
    output = tmp_path / "whole-report"
    assert main([str(manifest), "--output-dir", str(output), "--require-accepted"]) == 1
    receipt = json.loads((output / "nine_audit_manifest.json").read_text())
    assert receipt["overall_status"] == "not_accepted"
    assert receipt["accepted_instance_count"] == 1
    assert receipt["unassessed_indices"] == []


def test_modified_independent_report_cannot_bypass_integrity(evidence, tmp_path):
    manifest, run = evidence
    (run / "independent_validation.json").write_text('{"status": "rejected"}')
    output = tmp_path / "tampered-report"
    assert main([str(manifest), "--indices", "0", "--output-dir", str(output),
                 "--require-accepted"]) == 1
    row = json.loads((output / "nine_results.json").read_text())[0]
    assert row["reason"] == "artifact_integrity_failure"


def test_report_cannot_write_inside_source_runs(evidence):
    manifest, run = evidence
    with pytest.raises(SystemExit):
        main([str(manifest), "--output-dir", str(run / "new-report")])
    assert not (run / "new-report").exists()
