import pytest

from src.logic.model_audit import build_model_audit
from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData
from src.logic.optimization import OptimizationResult


def auditable_data() -> ModelData:
    return ModelData(
        origins=["O1"],
        warehouses=["W1", "W2"],
        existing_warehouses=["W1"],
        candidate_warehouses=["W2"],
        bulk_eligible_warehouses=["W1"],
        customers=["C1"],
        domestic_customers=["C1"],
        export_customers=[],
        products=["soy"],
        periods=["t1"],
        demand_exp={("E1", "soy", "t1"): 1_000_000_000.0},
        static_capacity={"W1": 100.0},
        reception_capacity={"W1": 10.0},
        shipping_capacity={"W1": 8.0},
        max_candidate_capacity={"W2": 50.0},
        opening_fixed_cost={"W2": 0.0},
        candidate_capacity_cost={"W2": 0.0},
        max_expand_capacity={"W1": 20.0},
        expand_fixed_cost={"W1": 0.0},
        expand_variable_cost={"W1": 2.0},
        max_bulk_capacity={"W1": 5.0},
        bulk_fixed_cost={"W1": 0.0},
        bulk_variable_cost={"W1": 3.0},
    )


def solved_stochastic_result() -> OptimizationResult:
    return OptimizationResult(
        status="optimal",
        objective_value=1_000.0,
        cost_breakdown={"unmet_demand": 950.0, "transport": 50.0},
        warehouse_decisions=[
            {
                "warehouse": "W1",
                "is_candidate": False,
                "open": 1.0,
                "expand": 1.0,
                "expansion_capacity": 10.0,
                "bulkify": 1.0,
                "bulk_capacity": 5.0,
            },
            {
                "warehouse": "W2",
                "is_candidate": True,
                "open": 1.0,
                "candidate_capacity": 50.0,
            },
        ],
        flows=[
            {
                "scenario": "low",
                "customer_type": "domestic",
                "value": 80.0,
            },
            {
                "scenario": "high",
                "customer_type": "domestic",
                "value": 60.0,
            },
        ],
        unmet_demand=[
            {"scenario": "low", "value": 20.0},
            {"scenario": "high", "value": 40.0},
        ],
        metadata={"scenario_probabilities": {"low": 0.5, "high": 0.5}},
    )


def test_input_audit_reports_zero_costs_scales_and_period_capacity():
    audit = build_model_audit(
        auditable_data(),
        ModelConfig(days_per_period=30.0),
    )

    capacity = audit["input"]["capacity_totals"]
    zero_cost = audit["input"]["zero_cost_opportunities"]
    codes = {finding["code"] for finding in audit["findings"]}

    assert capacity["reception_daily"] == pytest.approx(10.0)
    assert capacity["reception_per_period"] == pytest.approx(300.0)
    assert capacity["shipping_per_period"] == pytest.approx(240.0)
    assert zero_cost["candidate_opening"]["count"] == 1
    assert zero_cost["candidate_capacity"]["count"] == 1
    assert zero_cost["expansion_fixed"]["sample"] == ["W1"]
    assert zero_cost["bulkification_fixed"]["sample"] == ["W1"]
    assert "LARGE_INPUT_VALUE" in codes


def test_solution_audit_reports_dominance_service_and_free_decisions():
    audit = build_model_audit(
        auditable_data(),
        ModelConfig(days_per_period=30.0),
        solved_stochastic_result(),
    )

    solution = audit["solution"]
    service = solution["service"]
    active = solution["zero_cost_active_investments"]
    codes = {finding["code"] for finding in audit["findings"]}

    assert solution["cost_component_shares"]["unmet_demand"] == pytest.approx(
        0.95
    )
    assert service["expected"] == pytest.approx(0.7)
    assert service["minimum_scenario"] == pytest.approx(0.6)
    assert service["maximum_scenario"] == pytest.approx(0.8)
    assert active["candidate_opening"]["sample"] == ["W2"]
    assert active["expansion_fixed"]["sample"] == ["W1"]
    assert active["bulkification_fixed"]["sample"] == ["W1"]
    assert "DOMINANT_OBJECTIVE_COMPONENT" in codes
    assert "ZERO_COST_ACTIVE_INVESTMENT" in codes
