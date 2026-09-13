"""Analytical fixtures and adversarial mutations, independent of a solver license."""

from copy import deepcopy
from dataclasses import replace

import pytest

from src.logic.mathematical_contract import prepare_model_data
from src.logic.model_config import ModelConfig
from src.logic.optimization import OptimizationResult
from src.logic.solution_validation import COST_NAMES, validate_solution
from tests.test_mathematical_contract import tiny_data


def analytical_solution(days=30):
    config = ModelConfig(days_per_period=days)
    data = prepare_model_data(tiny_data(), config)
    overflow = max(0.0, 3030.0 - 100.0 * days)
    costs = dict.fromkeys(COST_NAMES, 0.0)
    costs.update(transport_od=3030.0, transport_dc=3030.0, emergency_reception=overflow * 100)
    result = OptimizationResult(
        status="optimal",
        objective_value=sum(costs.values()),
        model_mode="det",
        warehouse_decisions=[
            {
                "warehouse": "W",
                "open": 1.0,
                "candidate_capacity": 0.0,
                "expand": 0.0,
                "expansion_capacity": 0.0,
                "bulkify": 0.0,
                "bulk_capacity": 0.0,
            }
        ],
        flows=[
            {
                "route_type": "OD",
                "origin": "O",
                "warehouse": "W",
                "product": "P",
                "period": "t",
                "value": 3030.0,
            },
            {
                "route_type": "DC",
                "warehouse": "W",
                "customer": "C",
                "product": "P",
                "period": "t",
                "value": 3030.0,
            },
        ],
        emergency_capacity=[
            {"warehouse": "W", "period": "t", "capacity_type": "reception", "value": overflow}
        ],
        cost_breakdown=costs,
    )
    return data, config, result


@pytest.mark.parametrize("days", [28, 30, 31])
def test_hand_calculated_period_overflow_and_costs(days):
    data, config, result = analytical_solution(days)
    report = validate_solution(data, config, result)
    assert report["status"] == "accepted", report["failure_samples"]
    assert report["reconstructed_costs"] == result.cost_breakdown
    assert report["service_by_scenario"][0]["service_level"] == 1.0


@pytest.mark.parametrize(
    "mutation,family",
    [
        ("negative", "finite_nonnegative"),
        ("nan", "finite_nonnegative"),
        ("duplicate", "duplicate_flow"),
        ("unknown", "flow_indices"),
        ("missing_decision", "decision_complete"),
        ("closed", "closed_facility_operation"),
        ("daily_slack", "reception_capacity"),
        ("shipping", "shipping_capacity"),
        ("wrong_cost", "cost_reconstruction"),
        ("wrong_objective", "objective_reconstruction"),
        ("disabled_slack", "disabled_reception_slack"),
        ("binary", "binary_decision"),
        ("stock", "static_capacity"),
        ("zero_supply", "supply_balance"),
        ("zero_demand", "domestic_balance"),
        ("expansion", "expansion_bound"),
        ("bulk", "bulkification_bound"),
    ],
)
def test_adversarial_mutations_are_rejected(mutation, family):
    data, config, result = analytical_solution()
    if mutation in ("negative", "nan"):
        result.flows[0]["value"] = -1.0 if mutation == "negative" else float("nan")
    elif mutation == "duplicate":
        result.flows.append(dict(result.flows[0]))
    elif mutation == "unknown":
        result.flows[0]["origin"] = "unknown"
    elif mutation == "missing_decision":
        result.warehouse_decisions = []
    elif mutation == "closed":
        result.warehouse_decisions[0]["open"] = 0
    elif mutation == "daily_slack":
        result.emergency_capacity[0]["value"] /= 30.0
    elif mutation == "shipping":
        data.shipping_capacity["W"] = 1.0
    elif mutation == "wrong_cost":
        result.cost_breakdown["transport_dc"] += 10.0
    elif mutation == "wrong_objective":
        result.objective_value += 10.0
    elif mutation == "disabled_slack":
        config = replace(config, allow_emergency_reception_capacity=False)
    elif mutation == "binary":
        result.warehouse_decisions[0]["open"] = 0.25
    elif mutation == "stock":
        result.inventories = [{"warehouse": "W", "product": "P", "period": "t", "value": 10}]
    elif mutation == "zero_supply":
        data.supply["O", "P", "t"] = 0.0
    elif mutation == "zero_demand":
        data.demand_dom["C", "P", "t"] = 0.0
    elif mutation == "expansion":
        result.warehouse_decisions[0]["expansion_capacity"] = 10.0
    elif mutation == "bulk":
        result.warehouse_decisions[0]["bulk_capacity"] = 10.0
    report = validate_solution(data, config, result)
    assert report["status"] == "rejected"
    assert report["families"][family]["failed"] > 0


def test_local_residuals_cannot_cancel_in_national_material_balance():
    data, config, result = analytical_solution()
    data.domestic_customers.append("C2")
    data.customers.append("C2")
    data.demand_dom["C", "P", "t"] -= 10
    data.demand_dom["C2", "P", "t"] = 10
    report = validate_solution(data, config, result)
    assert report["families"]["domestic_balance"]["failed"] == 2
    assert sum(data.supply.values()) == sum(data.demand_dom.values())


def test_probabilities_weight_recourse_but_not_investment():
    data, config, result = analytical_solution()
    config = replace(config, mode="sto")
    data.scenarios = ["a", "b"]
    data.scenario_prob = {"a": 0.25, "b": 0.75}
    data.supply_s = {(s, *k): v for s in data.scenarios for k, v in data.supply.items()}
    data.demand_dom_s = {(s, *k): v for s in data.scenarios for k, v in data.demand_dom.items()}
    data.max_expand_capacity["W"] = 10
    data.expand_fixed_cost["W"] = 7
    result.warehouse_decisions[0]["expand"] = 1
    result.cost_breakdown["expansion_fixed"] = 7
    result.objective_value += 7
    result.flows = [{**r, "scenario": s} for s in data.scenarios for r in result.flows]
    result.emergency_capacity = [
        {**r, "scenario": s} for s in data.scenarios for r in result.emergency_capacity
    ]
    report = validate_solution(data, config, result)
    assert report["status"] == "accepted", report["failure_samples"]
    assert report["reconstructed_costs"]["expansion_fixed"] == 7
    assert report["reconstructed_costs"]["emergency_reception"] == 3000
    data.scenario_prob["b"] = 0.8
    assert validate_solution(data, config, result)["families"]["probabilities"]["failed"] == 1


def test_transshipment_is_local_not_new_supply():
    data, config, result = analytical_solution(31)
    data.warehouses.append("W2")
    data.existing_warehouses.append("W2")
    data.reception_capacity["W2"] = 1000
    data.shipping_capacity["W2"] = 1000
    data.dist_dd["W", "W2"] = 2
    data.dist_dc["W2", "C"] = 1
    data.freight_warehouse["W2"] = 1
    data.metadata["_frozen_routes"]["dd"] = [["W", "W2", "P"]]
    data.metadata["_frozen_routes"]["dc"].append(["W2", "C", "P"])
    decision = deepcopy(result.warehouse_decisions[0])
    decision["warehouse"] = "W2"
    result.warehouse_decisions.append(decision)
    result.flows[1]["warehouse"] = "W2"
    result.flows.append(
        {
            "route_type": "DD",
            "warehouse_from": "W",
            "warehouse_to": "W2",
            "product": "P",
            "period": "t",
            "value": 3030,
        }
    )
    result.cost_breakdown["transport_dd"] = 6060
    result.objective_value += 6060
    report = validate_solution(data, config, result)
    assert report["status"] == "accepted", report["failure_samples"]


def test_input_denominator_exposes_lost_domestic_flow():
    data, config, result = analytical_solution()
    result.flows[1]["value"] -= 30
    report = validate_solution(data, config, result)
    assert report["service_by_scenario"][0]["service_level"] == pytest.approx(3000 / 3030)
    assert report["status"] == "rejected"


def test_candidate_capacity_requires_opening():
    data, config, result = analytical_solution()
    data.existing_warehouses = []
    data.candidate_warehouses = ["W"]
    data.max_candidate_capacity["W"] = 100
    result.warehouse_decisions[0].update(open=0, candidate_capacity=100)
    report = validate_solution(data, config, result)
    assert report["families"]["candidate_activation"]["failed"] == 1
