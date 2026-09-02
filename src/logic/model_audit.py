"""Solver-independent methodological audits for model inputs and solutions."""

from __future__ import annotations

from typing import Any, Mapping

from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData
from src.logic.optimization import OptimizationResult


AUDIT_SCHEMA_VERSION = 1
LARGE_VALUE_THRESHOLD = 1_000_000_000.0
DOMINANT_OBJECTIVE_SHARE = 0.9
SAMPLE_LIMIT = 20


def build_model_audit(
    data: ModelData,
    config: ModelConfig,
    result: OptimizationResult | None = None,
) -> dict[str, Any]:
    """Return a JSON-serializable audit without changing model behavior."""

    findings: list[dict[str, Any]] = []
    parameter_profiles = {
        name: _parameter_profile(values)
        for name, values in _audited_parameters(data).items()
    }
    zero_cost_opportunities = _zero_cost_opportunities(data, config)

    for category, warehouses in zero_cost_opportunities.items():
        if warehouses:
            findings.append(
                _finding(
                    "warning",
                    f"ZERO_COST_{category.upper()}",
                    (
                        f"{len(warehouses)} investment opportunities have a "
                        "zero configured cost. Confirm that this is intentional."
                    ),
                    warehouses,
                )
            )

    large_parameters = [
        name
        for name, profile in parameter_profiles.items()
        if profile["maximum"] is not None
        and profile["maximum"] >= LARGE_VALUE_THRESHOLD
    ]
    if large_parameters:
        findings.append(
            _finding(
                "warning",
                "LARGE_INPUT_VALUE",
                (
                    "At least one audited parameter reaches 1e9 or more; "
                    "review sentinel values, units, and numerical scaling."
                ),
                large_parameters,
            )
        )

    audit: dict[str, Any] = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "input": {
            "model_mode": config.mode,
            "candidate_capacity_mode": config.candidate_capacity_mode,
            "days_per_period": config.days_per_period,
            "set_counts": {
                "origins": len(data.origins),
                "warehouses": len(data.warehouses),
                "existing_warehouses": len(data.existing_warehouses),
                "candidate_warehouses": len(data.candidate_warehouses),
                "bulk_eligible_warehouses": len(data.bulk_eligible_warehouses),
                "customers": len(data.customers),
                "products": len(data.products),
                "periods": len(data.periods),
                "scenarios": len(data.scenarios),
            },
            "capacity_totals": _capacity_totals(data, config),
            "parameter_profiles": parameter_profiles,
            "zero_cost_opportunities": {
                name: {
                    "count": len(warehouses),
                    "sample": warehouses[:SAMPLE_LIMIT],
                }
                for name, warehouses in zero_cost_opportunities.items()
            },
        },
        "findings": findings,
    }

    if result is not None and result.has_solution:
        solution, solution_findings = _solution_audit(data, result)
        audit["solution"] = solution
        findings.extend(solution_findings)

    audit["summary"] = {
        "warning_count": sum(
            finding["severity"] == "warning" for finding in findings
        ),
        "info_count": sum(
            finding["severity"] == "info" for finding in findings
        ),
    }
    return audit


def _audited_parameters(data: ModelData) -> dict[str, Mapping[Any, float]]:
    return {
        "supply": data.supply,
        "demand_dom": data.demand_dom,
        "demand_exp": data.demand_exp,
        "supply_s": data.supply_s,
        "demand_dom_s": data.demand_dom_s,
        "demand_exp_s": data.demand_exp_s,
        "static_capacity": data.static_capacity,
        "reception_capacity": data.reception_capacity,
        "shipping_capacity": data.shipping_capacity,
        "max_candidate_capacity": data.max_candidate_capacity,
        "max_expand_capacity": data.max_expand_capacity,
        "max_bulk_capacity": data.max_bulk_capacity,
        "opening_fixed_cost": data.opening_fixed_cost,
        "candidate_capacity_cost": data.candidate_capacity_cost,
        "expand_fixed_cost": data.expand_fixed_cost,
        "expand_variable_cost": data.expand_variable_cost,
        "bulk_fixed_cost": data.bulk_fixed_cost,
        "bulk_variable_cost": data.bulk_variable_cost,
        "unmet_demand_penalty": data.unmet_demand_penalty,
        "emergency_static_capacity_penalty": (
            data.emergency_static_capacity_penalty
        ),
        "emergency_reception_capacity_penalty": (
            data.emergency_reception_capacity_penalty
        ),
    }


def _parameter_profile(values: Mapping[Any, float]) -> dict[str, Any]:
    numbers = [float(value) for value in values.values()]
    positive = [value for value in numbers if value > 0.0]
    minimum_positive = min(positive) if positive else None
    maximum = max(numbers) if numbers else None
    return {
        "count": len(numbers),
        "zero_count": sum(value == 0.0 for value in numbers),
        "minimum": min(numbers) if numbers else None,
        "minimum_positive": minimum_positive,
        "maximum": maximum,
        "positive_scale_ratio": (
            maximum / minimum_positive
            if maximum is not None and minimum_positive is not None
            else None
        ),
    }


def _zero_cost_opportunities(
    data: ModelData,
    config: ModelConfig,
) -> dict[str, list[str]]:
    opportunities = {
        "candidate_opening": sorted(
            warehouse
            for warehouse in data.candidate_warehouses
            if data.max_candidate_capacity.get(warehouse, 0.0) > 0.0
            and data.opening_fixed_cost.get(warehouse, 0.0) == 0.0
        ),
        "candidate_capacity": [],
        "expansion_fixed": sorted(
            warehouse
            for warehouse, maximum in data.max_expand_capacity.items()
            if maximum > 0.0
            and data.expand_fixed_cost.get(warehouse, 0.0) == 0.0
        ),
        "expansion_variable": sorted(
            warehouse
            for warehouse, maximum in data.max_expand_capacity.items()
            if maximum > 0.0
            and data.expand_variable_cost.get(warehouse, 0.0) == 0.0
        ),
        "bulkification_fixed": sorted(
            warehouse
            for warehouse, maximum in data.max_bulk_capacity.items()
            if maximum > 0.0
            and data.bulk_fixed_cost.get(warehouse, 0.0) == 0.0
        ),
        "bulkification_variable": sorted(
            warehouse
            for warehouse, maximum in data.max_bulk_capacity.items()
            if maximum > 0.0
            and data.bulk_variable_cost.get(warehouse, 0.0) == 0.0
        ),
    }
    if config.candidate_capacity_mode == "scalable":
        opportunities["candidate_capacity"] = sorted(
            warehouse
            for warehouse in data.candidate_warehouses
            if data.max_candidate_capacity.get(warehouse, 0.0) > 0.0
            and data.candidate_capacity_cost.get(warehouse, 0.0) == 0.0
        )
    return opportunities


def _capacity_totals(data: ModelData, config: ModelConfig) -> dict[str, float]:
    days = float(config.days_per_period)
    return {
        "static": sum(map(float, data.static_capacity.values())),
        "reception_daily": sum(map(float, data.reception_capacity.values())),
        "reception_per_period": (
            sum(map(float, data.reception_capacity.values())) * days
        ),
        "shipping_daily": sum(map(float, data.shipping_capacity.values())),
        "shipping_per_period": (
            sum(map(float, data.shipping_capacity.values())) * days
        ),
        "maximum_candidate": sum(
            map(float, data.max_candidate_capacity.values())
        ),
        "maximum_expansion": sum(map(float, data.max_expand_capacity.values())),
        "maximum_bulkification": sum(
            map(float, data.max_bulk_capacity.values())
        ),
    }


def _solution_audit(
    data: ModelData,
    result: OptimizationResult,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    objective = float(result.objective_value or 0.0)
    cost_components = {
        name: float(value) for name, value in result.cost_breakdown.items()
    }
    cost_shares = {
        name: value / objective if objective else None
        for name, value in cost_components.items()
    }
    dominant_components = [
        name
        for name, share in cost_shares.items()
        if share is not None and share >= DOMINANT_OBJECTIVE_SHARE
    ]

    findings: list[dict[str, Any]] = []
    if dominant_components:
        findings.append(
            _finding(
                "warning",
                "DOMINANT_OBJECTIVE_COMPONENT",
                (
                    "A single objective component represents at least 90% "
                    "of the objective; verify that the intended economic or "
                    "service priority is correctly scaled."
                ),
                dominant_components,
            )
        )

    zero_cost_active = _zero_cost_active_investments(data, result)
    if any(zero_cost_active.values()):
        findings.append(
            _finding(
                "warning",
                "ZERO_COST_ACTIVE_INVESTMENT",
                (
                    "The optimal solution activates first-stage investments "
                    "whose corresponding configured cost is zero."
                ),
                [
                    f"{category}:{warehouse}"
                    for category, warehouses in zero_cost_active.items()
                    for warehouse in warehouses
                ],
            )
        )

    service = _service_audit(result)
    return (
        {
            "objective_value": objective,
            "cost_components": cost_components,
            "cost_component_shares": cost_shares,
            "investment_decisions": _investment_decision_summary(result),
            "zero_cost_active_investments": {
                name: {
                    "count": len(warehouses),
                    "sample": warehouses[:SAMPLE_LIMIT],
                }
                for name, warehouses in zero_cost_active.items()
            },
            "service": service,
        },
        findings,
    )


def _zero_cost_active_investments(
    data: ModelData,
    result: OptimizationResult,
) -> dict[str, list[str]]:
    active = {
        "candidate_opening": [],
        "expansion_fixed": [],
        "bulkification_fixed": [],
    }
    for decision in result.warehouse_decisions:
        warehouse = str(decision.get("warehouse"))
        if (
            float(decision.get("open", 0.0)) > 0.5
            and warehouse in data.candidate_warehouses
            and data.opening_fixed_cost.get(warehouse, 0.0) == 0.0
        ):
            active["candidate_opening"].append(warehouse)
        if (
            float(decision.get("expand", 0.0)) > 0.5
            and data.expand_fixed_cost.get(warehouse, 0.0) == 0.0
        ):
            active["expansion_fixed"].append(warehouse)
        if (
            float(decision.get("bulkify", 0.0)) > 0.5
            and data.bulk_fixed_cost.get(warehouse, 0.0) == 0.0
        ):
            active["bulkification_fixed"].append(warehouse)
    return active


def _investment_decision_summary(result: OptimizationResult) -> dict[str, float]:
    decisions = result.warehouse_decisions
    return {
        "candidates_opened": sum(
            float(decision.get("open", 0.0)) > 0.5
            and bool(decision.get("is_candidate", False))
            for decision in decisions
        ),
        "warehouses_expanded": sum(
            float(decision.get("expand", 0.0)) > 0.5
            for decision in decisions
        ),
        "warehouses_bulkified": sum(
            float(decision.get("bulkify", 0.0)) > 0.5
            for decision in decisions
        ),
        "candidate_capacity": sum(
            float(decision.get("candidate_capacity", 0.0))
            for decision in decisions
        ),
        "expansion_capacity": sum(
            float(decision.get("expansion_capacity", 0.0))
            for decision in decisions
        ),
        "bulk_capacity": sum(
            float(decision.get("bulk_capacity", 0.0))
            for decision in decisions
        ),
    }


def _service_audit(result: OptimizationResult) -> dict[str, Any]:
    probabilities = result.metadata.get("scenario_probabilities", {})
    scenarios = list(probabilities)
    if not scenarios:
        served = _record_total(result.flows, customer_type="domestic")
        unmet = _record_total(result.unmet_demand)
        total = served + unmet
        return {
            "expected": served / total if total > 0.0 else 1.0,
            "minimum_scenario": None,
            "maximum_scenario": None,
            "by_scenario": {},
        }

    by_scenario: dict[str, float] = {}
    expected_served = 0.0
    expected_unmet = 0.0
    for scenario in scenarios:
        served = _record_total(
            result.flows,
            scenario=scenario,
            customer_type="domestic",
        )
        unmet = _record_total(result.unmet_demand, scenario=scenario)
        total = served + unmet
        by_scenario[scenario] = served / total if total > 0.0 else 1.0
        probability = float(probabilities[scenario])
        expected_served += probability * served
        expected_unmet += probability * unmet
    expected_total = expected_served + expected_unmet
    return {
        "expected": (
            expected_served / expected_total if expected_total > 0.0 else 1.0
        ),
        "minimum_scenario": min(by_scenario.values()),
        "maximum_scenario": max(by_scenario.values()),
        "by_scenario": by_scenario,
    }


def _record_total(records: list[dict[str, Any]], **filters: Any) -> float:
    return sum(
        float(record.get("value", 0.0))
        for record in records
        if all(record.get(key) == value for key, value in filters.items())
    )


def _finding(
    severity: str,
    code: str,
    message: str,
    affected: list[str],
) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "affected_count": len(affected),
        "affected_sample": affected[:SAMPLE_LIMIT],
    }
