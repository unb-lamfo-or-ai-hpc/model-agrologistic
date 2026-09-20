"""Campaign isolation, conservative certification, and data curation checks."""

from copy import deepcopy
from pathlib import Path

from scripts.audit_nine_campaign import classify_stages
from scripts.inventory_zenodo_data import inventory
from scripts.prepare_nine_scenario_campaign import campaign


def test_campaign_does_not_change_accepted_configurations(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source = root / "experiments/v020_policy_mvp.yaml"
    before = source.read_bytes()
    document = campaign(root, tmp_path)
    assert len(document["experiments"]) == 8
    assert document["defaults"]["solver"]["time_limit"] == 28800
    assert {r["metadata"]["warehouse_population"] for r in document["experiments"]} == {
        215, 300, 400, 500,
    }
    assert all(r["metadata"]["optimization_budget_seconds"] == 28800
               for r in document["experiments"])
    assert document["defaults"]["solver"]["mip_gap"] == 0.10
    assert document["defaults"]["model"]["interhub_strong_connectivity"] is True
    assert all("sto9" not in r["name"] or r["calculate_evpi_vss"] is False
               for r in document["experiments"])
    assert all(r["calculate_evpi_vss"] is False for r in document["experiments"])
    assert source.read_bytes() == before


def test_slurm_budget_includes_pipeline_overhead():
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts/run_nine_connectivity.slurm").read_text()
    assert "#SBATCH --time=12:00:00" in script
    assert "#SBATCH --qos=qos1" in script


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
