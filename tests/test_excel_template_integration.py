from pathlib import Path

import pytest

from src.logic.excel_loader import load_model_data_from_excel
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