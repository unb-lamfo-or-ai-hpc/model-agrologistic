from pathlib import Path

import pytest

from src.logic.excel_loader import ExcelLoaderConfig, load_model_data_from_excel
from src.logic.model_config import ModelConfig
from src.logic.model_validation import validate_model_data


TEMPLATE_PATH = Path("data/templates/model_agrologistic_padrao_ouro.xlsx")


@pytest.mark.skipif(
    not TEMPLATE_PATH.exists(),
    reason="Golden Excel template is not available in data/templates.",
)
def test_golden_excel_template_can_be_loaded_and_validated():
    data = load_model_data_from_excel(TEMPLATE_PATH)

    result = validate_model_data(
        data=data,
        config=ModelConfig(mode="det", candidate_capacity_mode="scalable"),
        require_distances=True,
    )

    assert result.is_valid, [issue.message for issue in result.errors]

    assert len(data.origins) > 0
    assert len(data.warehouses) > 0
    assert len(data.customers) > 0
    assert len(data.products) > 0
    assert len(data.periods) > 0

    assert len(data.routes_od) > 0
    assert len(data.routes_dc) > 0

    assert sum(data.supply.values()) > 0
    assert sum(data.demand_dom.values()) >= 0
    assert sum(data.demand_exp.values()) >= 0

    assert set(data.domestic_customers).isdisjoint(set(data.export_customers))

    assert data.metadata["loader_warnings"] == []


@pytest.mark.skipif(
    not TEMPLATE_PATH.exists(),
    reason="Golden Excel template is not available in data/templates.",
)
def test_golden_excel_template_populates_expansion_and_bulkification():
    data = load_model_data_from_excel(TEMPLATE_PATH)
    warehouse = "35.0287.0002-6"

    assert warehouse in data.existing_warehouses
    assert warehouse in data.bulk_eligible_warehouses

    assert data.max_expand_capacity[warehouse] == pytest.approx(222.5)
    assert data.expand_fixed_cost[warehouse] == pytest.approx(0.0)
    assert data.expand_variable_cost[warehouse] == pytest.approx(900.0)

    assert data.max_bulk_capacity[warehouse] == pytest.approx(890.0)
    assert data.bulk_fixed_cost[warehouse] == pytest.approx(0.0)
    assert data.bulk_variable_cost[warehouse] == pytest.approx(520.0)


@pytest.mark.skipif(
    not TEMPLATE_PATH.exists(),
    reason="Golden Excel template is not available in data/templates.",
)
def test_golden_excel_template_prices_candidate_capacity_per_ton():
    data = load_model_data_from_excel(TEMPLATE_PATH)

    for warehouse in data.candidate_warehouses:
        maximum = data.max_candidate_capacity[warehouse]
        reported_total = data.metadata["reported_candidate_total_opening_cost"][
            warehouse
        ]

        assert reported_total > 0.0
        assert data.opening_fixed_cost[warehouse] == pytest.approx(0.0)
        assert data.candidate_capacity_cost[warehouse] == pytest.approx(
            reported_total / maximum
        )


@pytest.mark.skipif(
    not TEMPLATE_PATH.exists(),
    reason="Golden Excel template is not available in data/templates.",
)
def test_golden_excel_template_loads_active_stochastic_scenarios():
    data = load_model_data_from_excel(
        TEMPLATE_PATH,
        config=ExcelLoaderConfig(include_stochastic_scenarios=True),
    )

    assert data.scenarios == ["base"]
    assert data.scenario_prob == {"base": 1.0}
    assert len(data.supply_s) == (
        len(data.scenarios)
        * len(data.origins)
        * len(data.products)
        * len(data.periods)
    )
    assert len(data.demand_dom_s) == (
        len(data.scenarios)
        * len(data.domestic_customers)
        * len(data.products)
        * len(data.periods)
    )

    result = validate_model_data(
        data=data,
        config=ModelConfig(mode="sto", candidate_capacity_mode="scalable"),
        require_distances=True,
    )
    assert result.is_valid, [issue.message for issue in result.errors]
