"""Read-only checks of historical records; no retired campaign generation."""

from copy import deepcopy
from pathlib import Path

from scripts.audit_nine_campaign import classify_stages
from scripts.inventory_zenodo_data import inventory


def test_materialization_keeps_existing_outputs_protected():
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts/materialize_policy_osrm_population.slurm").read_text()
    assert 'FINAL_OUTPUT="${FINAL_OUTPUT:-' in script
    assert 'if [ -e "$FINAL_OUTPUT" ]; then' in script
    assert '--overwrite' not in script
    assert '_validate_distance_table(saved_distances, sheets)' in script


def test_acceptance_requires_complete_hierarchy_and_feasibility():
    stages = [{"stage_role": role, "final_objective_value": 0,
               "mip_gap": 0.1, "within_mip_degradation_limit": True}
              for role in ("unmet_demand", "emergency_capacity", "economic_cost")]
    assert classify_stages(stages, "accepted") == "accepted_at_ten_percent"
    assert classify_stages(stages[:2], "accepted") == "incomplete_hierarchy"
    assert classify_stages(stages, "rejected") == "independent_validation_not_accepted"
    for gap in (None, float("nan"), 1.0, -0.01):
        changed = deepcopy(stages)
        changed[1]["mip_gap"] = gap
        assert classify_stages(changed, "accepted") == "gap_target_not_attained"
    changed = deepcopy(stages)
    changed[0]["final_objective_value"] = 1
    assert classify_stages(changed, "accepted") == "service_shortfall"


def test_inventory_never_approves_or_reads_sensitive_files(tmp_path):
    (tmp_path / "sample.csv").write_text("value\n1\n")
    (tmp_path / ".env.production").write_text("credential")
    rows = {r["path"]: r for r in inventory(tmp_path)}
    assert rows["sample.csv"]["approved_for_upload"] is False
    assert len(rows["sample.csv"]["sha256"]) == 64
    assert "sha256" not in rows[".env.production"]
