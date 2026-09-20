"""Reporting must retain negative evidence without fabricating performance."""

import io
import json
import tarfile

import pytest

from scripts.build_solver_comparison import archive_files, collect, digest, normalize


def example():
    row = {"name": "nine_h215_direct_scip", "warehouses": 215,
           "status": "independent_validation_not_accepted", "target_gap": 0.1,
           "time_budget_seconds": 28800, "independent_validation_status": "rejected",
           "peak_rss_mb": 1024, "minimum_scenario_service_level": 1.0,
           "maximum_scenario_service_level": 1.0}
    stages = [{"name": row["name"], "status": "TIME_LIMIT", "stage_role": "unmet_demand",
               "solution_count": 0, "objective_value": None, "mip_gap": None}]
    return row, stages


@pytest.mark.parametrize("stop", ["TIME_LIMIT", "MEM_LIMIT"])
def test_no_incumbent_suppresses_service_defaults_and_costs(stop):
    row, stages = example()
    stages[0]["status"] = stop
    row["economic_cost"] = 0.0
    result = normalize(row, stages, "SCIP")
    assert result["outcome"] == f"{stop.lower()}_without_incumbent"
    assert result["economic_cost"] is None
    assert result["minimum_scenario_service_level"] is None
    assert result["maximum_scenario_service_level"] is None
    assert result["suppressed_unsubstantiated_metrics"]["minimum_scenario_service_level"] == 1
    assert result["stage_gaps"]["unmet_demand"] is None
    assert result["application_peak_rss_gib"] == 1
    assert result["raw_audit_status"] == row["status"]


def test_valid_but_uncertified_incumbent_is_not_suppressed():
    row, stages = example()
    stages[0].update(solution_count=1, objective_value=0)
    row.update(independent_validation_status="accepted", economic_cost=123)
    result = normalize(row, stages, "Gurobi")
    assert result["outcome"] == "valid_incumbent_not_certified"
    assert result["economic_cost"] == 123


@pytest.mark.parametrize("defect", ["identity", "missing", "objective", "acceptance"])
def test_inconsistent_evidence_rejected(defect):
    row, stages = example()
    if defect == "identity":
        stages[0]["name"] = "other"
    elif defect == "missing":
        stages = []
    elif defect == "objective":
        stages[0]["objective_value"] = 123
    else:
        row["status"] = "accepted_at_ten_percent"
        stages[0].update(solution_count=1, objective_value=0)
    with pytest.raises(ValueError):
        normalize(row, stages, "SCIP")


def make_archive(path, files):
    with tarfile.open(path, "w:gz") as archive:
        for name, raw in files.items():
            member = tarfile.TarInfo(name)
            member.size = len(raw)
            archive.addfile(member, io.BytesIO(raw))


@pytest.mark.parametrize("tamper", [False, True])
def test_manifest_hash_checked_before_comparison(tmp_path, tamper):
    row, stages = example()
    manifest = b"version: 1\n"
    audit = {"selected_instance_count": 1, "accepted_instance_count": 0,
             "manifest_sha256": digest(manifest)}
    files = {"case/campaign.yaml": b"changed" if tamper else manifest,
             "case/audit/nine_audit_manifest.json": json.dumps(audit).encode(),
             "case/audit/nine_results.json": json.dumps([row]).encode(),
             "case/audit/nine_stage_gaps.json": json.dumps(stages).encode()}
    path = tmp_path / "evidence.tar.gz"
    make_archive(path, files)
    if tamper:
        with pytest.raises(ValueError, match="hash mismatch"):
            collect(path, "SCIP")
    else:
        records, _, inventory, _ = collect(path, "SCIP")
        assert len(records) == 1
        assert inventory["campaign_checks"][0]["manifest_bytes_verified"]


def test_archive_traversal_rejected_without_extraction(tmp_path):
    path = tmp_path / "unsafe.tar.gz"
    make_archive(path, {"../outside.json": b"{}"})
    with pytest.raises(ValueError, match="Unsafe"):
        archive_files(path)
    assert not (tmp_path.parent / "outside.json").exists()
