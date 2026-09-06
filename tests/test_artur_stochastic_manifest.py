from pathlib import Path

import pytest
import yaml

from src.logic.artur_adapter import ArturSolverAdapterConfig
from src.logic.model_config import ModelConfig


MANIFEST = Path("experiments/artur_stochastic_extension.yaml")


def test_stochastic_extension_manifest_preserves_the_validated_model_profile():
    payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    defaults = payload["defaults"]
    experiments = payload["experiments"]

    config = ModelConfig(**defaults["model"])
    assert config.mode == "sto"
    assert config.objective_policy == "penalty"
    assert config.capacity_coupling_policy == "daily_factors"
    assert config.use_direct_origin_customer is False
    assert config.use_warehouse_transshipment is True

    loader = defaults["loader"]
    assert loader["stochastic_combinations"] == [
        ["baixo", "alto"],
        ["base", "base"],
        ["alto", "baixo"],
    ]
    assert sum(loader["stochastic_probabilities"]) == pytest.approx(1.0)

    assert [experiment["calculate_evpi_vss"] for experiment in experiments] == [
        False,
        True,
        False,
        True,
    ]
    assert experiments[1]["resume_evpi_vss"] is True
    assert experiments[3]["resume_evpi_vss"] is True
    assert all(
        experiment["metadata"]["comparison_status"] == "controlled_extension"
        for experiment in experiments
    )
    assert all(
        "comparison_group" not in experiment["metadata"]
        for experiment in experiments
    )
    assert experiments[0]["metadata"]["slack_interpretation"] == (
        "complete_recourse_infrastructure_gap"
    )
    assert experiments[1]["metadata"]["monetary_interpretation"] == (
        "decomposed_penalty_dependent_evpi_vss"
    )


def test_nine_scenario_runs_use_the_full_factorial_design():
    payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    rp, evpi_vss = payload["experiments"][2:]
    loader = rp["loader"]

    assert rp["name"] == "artur_legacy_i001_sto_9_rp"
    assert evpi_vss["name"] == "artur_legacy_i001_sto_9_evpi_vss"
    assert loader["stochastic_combinations"] is None
    assert loader["stochastic_probabilities"] is None
    assert loader["stochastic_supply_levels"] == ["baixo", "base", "alto"]
    assert loader["stochastic_demand_levels"] == ["baixo", "base", "alto"]
    assert rp["calculate_evpi_vss"] is False
    assert evpi_vss["calculate_evpi_vss"] is True
    assert evpi_vss["resume_evpi_vss"] is True
    assert rp["max_estimated_variables"] == 2_000_000
    assert evpi_vss["max_estimated_variables"] == 2_000_000
    assert rp["metadata"]["campaign_gate"] == "gate_2d_nine_scenario_rp"
    assert (
        evpi_vss["metadata"]["campaign_gate"]
        == "gate_2d_nine_scenario_evpi_vss"
    )
    assert rp["metadata"]["probability_policy"] == "equal_experimental_weights"
    assert evpi_vss["loader"] == loader


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("low_supply_multiplier", 0.0),
        ("high_supply_multiplier", 0.99),
        ("low_domestic_demand_multiplier", -0.01),
        ("high_domestic_demand_multiplier", 0.99),
    ],
)
def test_artur_scenario_multiplier_ranges_are_validated(field, value):
    with pytest.raises(ValueError):
        ArturSolverAdapterConfig(**{field: value})
