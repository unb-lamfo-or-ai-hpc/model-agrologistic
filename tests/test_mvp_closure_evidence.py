"""Keep bounded development closure distinct from scientific acceptance."""
import json
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parents[1] / "docs/evidence/pr25-final"


def test_original_ten_case_certificate_is_preserved():
    report = json.loads((EVIDENCE / "v020_validation_report.json").read_text())
    closure = json.loads((EVIDENCE / "closure.json").read_text())
    assert report["overall_status"] == closure["original_validation_outcome"] == "rejected"
    assert [row["status"] for row in report["levels"]] == closure["level_statuses"]
    assert sum(row["status"] == "accepted" for row in report["runs"]) == 9
    assert len(report["runs"]) == 10
    assert report["implementation"]["sha256"] == closure["implementation_sha256"]
    last = next(row for row in report["runs"] if row["name"] == closure["last_trial"]["run_name"])
    assert last["run_identity"] == closure["last_trial"]["run_identity"]
    assert last["checks"]["independent_local_residuals_and_costs"]
    assert not last["checks"]["three_completed_passes"]


def test_failure_is_not_infeasibility_or_economic_optimality():
    trial = json.loads((EVIDENCE / "closure.json").read_text())["last_trial"]
    assert trial["service_stage"]["objective"] == 0
    assert trial["capacity_stage"]["status"] == "TIME_LIMIT"
    assert trial["capacity_stage"]["relative_gap"] == 1.0
    assert trial["configured_mip_gap"] == 0.01
    assert trial["economic_stage"]["objective"] is None
    assert trial["economic_stage"]["relative_gap"] is None
    assert trial["elapsed_seconds"] == 4 * 3600 + 5 * 60 + 46
