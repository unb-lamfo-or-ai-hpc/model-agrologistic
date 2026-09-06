from pathlib import Path

import pytest
import yaml

from src.logic.artur_adapter import ArturSolverAdapterConfig
from src.logic.model_config import ModelConfig


MANIFEST = Path("experiments/artur_stochastic_extension.yaml")


def test_three_scenario_manifest_preserves_the_validated_model_profile():
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
    ]
    assert experiments[1]["resume_evpi_vss"] is True
    assert all(
        experiment["metadata"]["comparison_status"] == "controlled_extension"
        for experiment in experiments
    )
    assert all(
        "comparison_group" not in experiment["metadata"]
        for experiment in experiments
    )


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
