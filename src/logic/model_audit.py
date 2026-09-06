"""Solver-independent methodological audits for model inputs and solutions."""

from __future__ import annotations

from typing import Any, Mapping

from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData
from src.logic.optimization import OptimizationResult


AUDIT_SCHEMA_VERSION = 2
LARGE_VALUE_THRESHOLD = 1_000_000_000.0
DOMINANT_OBJECTIVE_SHARE = 0.9
SAMPLE_LIMIT = 20
ACTIVE_CAPACITY_TOL = 1e-7
MATERIAL_QUANTITY_TOLERANCE_TONS = 1.0
BALANCE_RELATIVE_TOLERANCE = 1e-8
SATURATION_RELATIVE_TOLERANCE = 1e-8


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
            "objective_policy": config.objective_policy,
            "days_per_period": config.days_per_period,
            "effective_days_per_period": {
                period: config.operating_days(period) for period in data.periods
            },
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
        solution, solution_findings = _solution_audit(data, config, result)
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
    return {
        "candidate_total": sorted(
            warehouse
            for warehouse in data.candidate_warehouses
            if data.max_candidate_capacity.get(warehouse, 0.0) > 0.0
            and data.opening_fixed_cost.get(warehouse, 0.0) == 0.0
            and (
                config.candidate_capacity_mode != "scalable"
                or data.candidate_capacity_cost.get(warehouse, 0.0) == 0.0
            )
        ),
        "expansion_total": sorted(
            warehouse
            for warehouse, maximum in data.max_expand_capacity.items()
            if maximum > 0.0
            and data.expand_fixed_cost.get(warehouse, 0.0) == 0.0
            and data.expand_variable_cost.get(warehouse, 0.0) == 0.0
        ),
        "bulkification_total": sorted(
            warehouse
            for warehouse, maximum in data.max_bulk_capacity.items()
            if maximum > 0.0
            and data.bulk_fixed_cost.get(warehouse, 0.0) == 0.0
            and data.bulk_variable_cost.get(warehouse, 0.0) == 0.0
        ),
    }


def _capacity_totals(data: ModelData, config: ModelConfig) -> dict[str, Any]:
    reception_daily = sum(map(float, data.reception_capacity.values()))
    shipping_daily = sum(map(float, data.shipping_capacity.values()))
    return {
        "static": sum(map(float, data.static_capacity.values())),
        "reception_daily": reception_daily,
        "reception_per_period": reception_daily * float(config.days_per_period),
        "reception_per_period_by_period": {
            period: reception_daily * config.operating_days(period)
            for period in data.periods
        },
        "shipping_daily": shipping_daily,
        "shipping_per_period": shipping_daily * float(config.days_per_period),
        "shipping_per_period_by_period": {
            period: shipping_daily * config.operating_days(period)
            for period in data.periods
        },
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
    config: ModelConfig,
    result: OptimizationResult,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    objective = float(result.objective_value or 0.0)
    cost_components = {
        name: float(value) for name, value in result.cost_breakdown.items()
    }
    penalized_cost_total = sum(cost_components.values())
    cost_shares = {
        name: value / penalized_cost_total if penalized_cost_total else None
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
                    "A single component represents at least 90% of the "
                    "penalized cost total; verify the intended economic or "
                    "service interpretation."
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
    material_balance = _material_balance_audit(data, result)
    capacity_adequacy = _capacity_adequacy_audit(data, config, result)
    investment_saturation = _investment_saturation_audit(data, result)

    if material_balance["available"] and not material_balance["all_within_tolerance"]:
        failed_scenarios = [
            str(record["scenario"])
            for record in material_balance["by_scenario"]
            if not record["within_tolerance"]
        ]
        findings.append(
            _finding(
                "warning",
                "MATERIAL_BALANCE_RESIDUAL",
                (
                    "At least one scenario does not reconcile supply and initial "
                    "inventory with domestic flow, export flow, and terminal "
                    "inventory within the configured audit tolerance."
                ),
                failed_scenarios,
            )
        )

    adequacy_status = capacity_adequacy["status"]
    if adequacy_status == "domestic_service_shortfall":
        findings.append(
            _finding(
                "warning",
                "DOMESTIC_SERVICE_SHORTFALL",
                (
                    "Domestic demand uses material unmet-demand recourse. The "
                    "solution remains mathematically usable, but the service "
                    "target is not physically attained."
                ),
                capacity_adequacy["affected_scenarios"],
            )
        )
    elif adequacy_status == "emergency_capacity_required":
        findings.append(
            _finding(
                "warning",
                "EMERGENCY_CAPACITY_REQUIRED",
                (
                    "Domestic service is preserved through emergency capacity. "
                    "Treat the physical gap as an infrastructure finding and the "
                    "Big-M contribution as a penalty-dependent value, not an "
                    "observed monetary cost."
                ),
                capacity_adequacy["affected_scenarios"],
            )
        )

    saturated_types = [
        name
        for name, values in investment_saturation.items()
        if values["eligible_facilities"] > 0
        and values["facilities_at_maximum"] == values["eligible_facilities"]
    ]
    if saturated_types:
        findings.append(
            _finding(
                "info",
                "INVESTMENT_CAPACITY_SATURATED",
                (
                    "Every eligible facility reaches its configured upper bound "
                    "for at least one investment type. Residual emergency capacity "
                    "therefore identifies a gap outside the current decision set."
                ),
                saturated_types,
            )
        )
    return (
        {
            "objective_value": objective,
            "objective_policy": result.metadata.get("objective_policy", "penalty"),
            "penalized_cost_total": penalized_cost_total,
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
            "material_balance": material_balance,
            "capacity_adequacy": capacity_adequacy,
            "investment_saturation": investment_saturation,
        },
        findings,
    )


def _zero_cost_active_investments(
    data: ModelData,
    result: OptimizationResult,
) -> dict[str, list[str]]:
    candidate_mode = result.metadata.get("candidate_capacity_mode", "scalable")
    active = {
        "candidate_total": [],
        "expansion_total": [],
        "bulkification_total": [],
    }
    for decision in result.warehouse_decisions:
        warehouse = str(decision.get("warehouse"))
        candidate_capacity = float(decision.get("candidate_capacity", 0.0))
        expansion_capacity = float(decision.get("expansion_capacity", 0.0))
        bulk_capacity = float(decision.get("bulk_capacity", 0.0))
        if (
            candidate_capacity > ACTIVE_CAPACITY_TOL
            and warehouse in data.candidate_warehouses
            and data.opening_fixed_cost.get(warehouse, 0.0) == 0.0
            and (
                candidate_mode != "scalable"
                or data.candidate_capacity_cost.get(warehouse, 0.0) == 0.0
            )
        ):
            active["candidate_total"].append(warehouse)
        if (
            expansion_capacity > ACTIVE_CAPACITY_TOL
            and data.expand_fixed_cost.get(warehouse, 0.0) == 0.0
            and data.expand_variable_cost.get(warehouse, 0.0) == 0.0
        ):
            active["expansion_total"].append(warehouse)
        if (
            bulk_capacity > ACTIVE_CAPACITY_TOL
            and data.bulk_fixed_cost.get(warehouse, 0.0) == 0.0
            and data.bulk_variable_cost.get(warehouse, 0.0) == 0.0
        ):
            active["bulkification_total"].append(warehouse)
    return active


def _investment_decision_summary(result: OptimizationResult) -> dict[str, float]:
    decisions = result.warehouse_decisions
    return {
        "candidates_opened": sum(
            float(decision.get("candidate_capacity", 0.0)) > ACTIVE_CAPACITY_TOL
            and bool(decision.get("is_candidate", False))
            for decision in decisions
        ),
        "warehouses_expanded": sum(
            float(decision.get("expansion_capacity", 0.0)) > ACTIVE_CAPACITY_TOL
            for decision in decisions
        ),
        "warehouses_bulkified": sum(
            float(decision.get("bulk_capacity", 0.0)) > ACTIVE_CAPACITY_TOL
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


def _material_balance_audit(
    data: ModelData,
    result: OptimizationResult,
) -> dict[str, Any]:
    """Reconcile total available grain with its final disposition."""

    stochastic = bool(data.scenarios and data.supply_s)
    if not data.supply and not stochastic:
        return {
            "available": False,
            "all_within_tolerance": None,
            "by_scenario": [],
        }

    initial_inventory = sum(map(float, data.initial_inventory.values()))
    terminal_period = data.periods[-1] if data.periods else None
    scenarios: list[str | None] = list(data.scenarios) if stochastic else [None]
    records: list[dict[str, Any]] = []
    for scenario in scenarios:
        if scenario is None:
            supply = sum(map(float, data.supply.values()))
        else:
            supply = sum(
                float(value)
                for (record_scenario, *_), value in data.supply_s.items()
                if record_scenario == scenario
            )
        domestic_flow = _record_total_for_scenario(
            result.flows,
            scenario,
            customer_type="domestic",
        )
        export_flow = _record_total_for_scenario(
            result.flows,
            scenario,
            customer_type="export",
        )
        terminal_inventory = _record_total_for_scenario(
            result.inventories,
            scenario,
            period=terminal_period,
        )
        available = supply + initial_inventory
        residual = available - domestic_flow - export_flow - terminal_inventory
        scale = max(
            abs(available),
            abs(domestic_flow) + abs(export_flow) + abs(terminal_inventory),
        )
        tolerance = max(
            MATERIAL_QUANTITY_TOLERANCE_TONS,
            BALANCE_RELATIVE_TOLERANCE * scale,
        )
        records.append(
            {
                "scenario": scenario or "deterministic",
                "supply_tons": supply,
                "initial_inventory_tons": initial_inventory,
                "domestic_flow_tons": domestic_flow,
                "export_flow_tons": export_flow,
                "terminal_inventory_tons": terminal_inventory,
                "balance_residual_tons": residual,
                "absolute_residual_tons": abs(residual),
                "tolerance_tons": tolerance,
                "within_tolerance": abs(residual) <= tolerance,
            }
        )
    return {
        "available": True,
        "all_within_tolerance": all(
            record["within_tolerance"] for record in records
        ),
        "by_scenario": records,
    }


def _capacity_adequacy_audit(
    data: ModelData,
    config: ModelConfig,
    result: OptimizationResult,
) -> dict[str, Any]:
    """Classify recourse use without treating emergency capacity as solver failure."""

    scenarios: list[str | None] = list(data.scenarios) if data.scenarios else [None]
    probabilities = result.metadata.get("scenario_probabilities", {})
    records: list[dict[str, Any]] = []
    for scenario in scenarios:
        unmet = _record_total_for_scenario(result.unmet_demand, scenario)
        static = _record_total_for_scenario(
            result.emergency_capacity,
            scenario,
            capacity_type="static",
        )
        reception = _record_total_for_scenario(
            result.emergency_capacity,
            scenario,
            capacity_type="reception",
        )
        reception_records = [
            record
            for record in result.emergency_capacity
            if record.get("capacity_type") == "reception"
            and _record_matches_scenario(record, scenario)
        ]
        static_records = [
            record
            for record in result.emergency_capacity
            if record.get("capacity_type") == "static"
            and _record_matches_scenario(record, scenario)
        ]
        peak_reception = max(
            reception_records,
            key=lambda record: float(record.get("value", 0.0))
            / float(config.operating_days(str(record.get("period")))),
            default=None,
        )
        peak_static = max(
            static_records,
            key=lambda record: float(record.get("value", 0.0)),
            default=None,
        )
        if unmet > MATERIAL_QUANTITY_TOLERANCE_TONS:
            status = "domestic_service_shortfall"
        elif max(static, reception) > MATERIAL_QUANTITY_TOLERANCE_TONS:
            status = "emergency_capacity_required"
        else:
            status = "nominally_adequate"
        records.append(
            {
                "scenario": scenario or "deterministic",
                "probability": probabilities.get(scenario) if scenario else 1.0,
                "status": status,
                "unmet_demand_tons": unmet,
                "emergency_static_tons_over_periods": static,
                "emergency_reception_tons_over_periods": reception,
                "peak_emergency_static_tons": (
                    float(peak_static.get("value", 0.0)) if peak_static else 0.0
                ),
                "peak_static_warehouse": (
                    peak_static.get("warehouse") if peak_static else None
                ),
                "peak_static_period": (
                    peak_static.get("period") if peak_static else None
                ),
                "peak_emergency_reception_tons_per_day": (
                    float(peak_reception.get("value", 0.0))
                    / float(config.operating_days(str(peak_reception.get("period"))))
                    if peak_reception
                    else 0.0
                ),
                "peak_reception_warehouse": (
                    peak_reception.get("warehouse") if peak_reception else None
                ),
                "peak_reception_period": (
                    peak_reception.get("period") if peak_reception else None
                ),
            }
        )

    if any(record["status"] == "domestic_service_shortfall" for record in records):
        overall_status = "domestic_service_shortfall"
    elif any(record["status"] == "emergency_capacity_required" for record in records):
        overall_status = "emergency_capacity_required"
    else:
        overall_status = "nominally_adequate"
    return {
        "status": overall_status,
        "materiality_tolerance_tons": MATERIAL_QUANTITY_TOLERANCE_TONS,
        "affected_scenarios": [
            str(record["scenario"])
            for record in records
            if record["status"] == overall_status
            and overall_status != "nominally_adequate"
        ],
        "by_scenario": records,
    }


def _investment_saturation_audit(
    data: ModelData,
    result: OptimizationResult,
) -> dict[str, dict[str, Any]]:
    """Compare selected first-stage capacities with their configured bounds."""

    selected = {
        str(decision.get("warehouse")): decision
        for decision in result.warehouse_decisions
    }
    categories = {
        "candidate_capacity": data.max_candidate_capacity,
        "expansion_capacity": data.max_expand_capacity,
        "bulk_capacity": data.max_bulk_capacity,
    }
    audit: dict[str, dict[str, Any]] = {}
    for field, bounds in categories.items():
        eligible = {
            warehouse: float(maximum)
            for warehouse, maximum in bounds.items()
            if float(maximum) > 0.0
        }
        at_maximum: list[str] = []
        selected_total = 0.0
        maximum_total = sum(eligible.values())
        for warehouse, maximum in eligible.items():
            value = float(selected.get(warehouse, {}).get(field, 0.0))
            selected_total += value
            tolerance = max(
                ACTIVE_CAPACITY_TOL,
                SATURATION_RELATIVE_TOLERANCE * maximum,
            )
            if value >= maximum - tolerance:
                at_maximum.append(warehouse)
        audit[field] = {
            "selected_capacity_tons": selected_total,
            "maximum_capacity_tons": maximum_total,
            "selected_fraction": (
                selected_total / maximum_total if maximum_total else None
            ),
            "facilities_at_maximum": len(at_maximum),
            "eligible_facilities": len(eligible),
            "all_eligible_at_maximum": bool(eligible)
            and len(at_maximum) == len(eligible),
            "facilities_at_maximum_sample": at_maximum[:SAMPLE_LIMIT],
        }
    return audit


def _record_total_for_scenario(
    records: list[dict[str, Any]],
    scenario: str | None,
    **filters: Any,
) -> float:
    return sum(
        float(record.get("value", 0.0))
        for record in records
        if _record_matches_scenario(record, scenario)
        and all(record.get(key) == value for key, value in filters.items())
    )


def _record_matches_scenario(record: dict[str, Any], scenario: str | None) -> bool:
    record_scenario = record.get("scenario")
    return (
        record_scenario == scenario
        if scenario is not None
        else record_scenario is None
    )


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
