"""Post-solve performance metrics for agricultural storage facilities."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.logic.model_data import ModelData
from src.logic.optimization import OptimizationResult


@dataclass(slots=True)
class StorageMetricsConfig:
    """Configuration for the thesis-aligned DynCap and Turnover metrics."""

    annualization_months: float = 12.0
    deterministic_scenario_id: str = "deterministic"
    tolerance: float = 1e-7

    def __post_init__(self) -> None:
        if self.annualization_months <= 0.0:
            raise ValueError("annualization_months must be positive.")
        if not self.deterministic_scenario_id:
            raise ValueError("deterministic_scenario_id must not be empty.")
        if self.tolerance < 0.0:
            raise ValueError("tolerance must be non-negative.")


@dataclass(slots=True)
class StorageMetricsResult:
    """Warehouse, scenario, and probability-weighted storage metrics."""

    warehouse_metrics: list[dict[str, Any]]
    scenario_metrics: dict[str, dict[str, float | None]]
    expected_metrics: dict[str, float | None]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calculate_storage_metrics(
    data: ModelData,
    result: OptimizationResult,
    config: StorageMetricsConfig | None = None,
) -> StorageMetricsResult:
    """Calculate DynCap and Turnover according to thesis Eqs. (1.63)-(1.67).

    DynCap annualizes warehouse outbound flow plus terminal inventory using
    ``12 / |T|``. Outbound flow comprises warehouse-to-customer shipments and
    warehouse-to-warehouse shipments at their source warehouse. Turnover is
    DynCap divided by the effective static capacity from Eq. (1.64): existing
    capacity or opened candidate capacity, plus executed expansion.

    Bulkification capacity is deliberately excluded from this denominator to
    preserve the cited equation, even though the optimization model includes
    it in its operational storage-capacity constraint.
    """

    if config is None:
        config = StorageMetricsConfig()
    if not result.has_solution:
        raise ValueError(
            "Storage metrics require a usable optimization solution; "
            f"received status={result.status!r}."
        )
    if not data.periods:
        raise ValueError("Storage metrics require at least one period in ModelData.")

    decisions = {
        str(decision["warehouse"]): decision
        for decision in result.warehouse_decisions
    }
    missing_decisions = sorted(set(data.warehouses) - set(decisions))
    if missing_decisions:
        raise ValueError(
            "OptimizationResult.warehouse_decisions is missing warehouses: "
            f"{missing_decisions}."
        )

    scenarios, probabilities, stochastic = _scenario_structure(
        data, result, config
    )
    outbound = _zero_warehouse_scenario_map(data, scenarios)
    terminal_inventory = _zero_warehouse_scenario_map(data, scenarios)

    for flow in result.flows:
        scenario = _record_scenario(flow, config, stochastic)
        if scenario not in probabilities:
            raise ValueError(f"Flow record contains unknown scenario {scenario!r}.")

        value = float(flow.get("value", 0.0))
        if value <= config.tolerance:
            continue

        route_type = str(flow.get("route_type", "")).upper()
        if route_type == "DC":
            outbound[scenario, str(flow["warehouse"])] += value
        elif route_type == "DD":
            outbound[scenario, str(flow["warehouse_from"])] += value
        elif route_type in {"OD", "OC"}:
            continue
        else:
            raise ValueError(f"Unsupported route_type in metrics: {route_type!r}.")

    final_period = str(data.periods[-1])
    for inventory in result.inventories:
        scenario = _record_scenario(inventory, config, stochastic)
        if scenario not in probabilities:
            raise ValueError(
                f"Inventory record contains unknown scenario {scenario!r}."
            )
        if str(inventory["period"]) != final_period:
            continue
        terminal_inventory[scenario, str(inventory["warehouse"])] += float(
            inventory.get("value", 0.0)
        )

    annualization_factor = config.annualization_months / len(data.periods)
    warehouse_metrics: list[dict[str, Any]] = []
    excluded_warehouses: list[str] = []

    for warehouse in data.warehouses:
        decision = decisions[warehouse]
        effective_static_capacity = _thesis_effective_static_capacity(
            data=data,
            warehouse=warehouse,
            decision=decision,
        )
        if effective_static_capacity <= config.tolerance:
            excluded_warehouses.append(warehouse)
            continue

        for scenario in scenarios:
            total_outbound = outbound[scenario, warehouse]
            ending_inventory = terminal_inventory[scenario, warehouse]
            dynamic_capacity = annualization_factor * (
                total_outbound + ending_inventory
            )
            warehouse_metrics.append(
                {
                    "scenario": scenario,
                    "probability": probabilities[scenario],
                    "warehouse": warehouse,
                    "total_outbound": total_outbound,
                    "terminal_inventory": ending_inventory,
                    "annualization_factor": annualization_factor,
                    "effective_static_capacity": effective_static_capacity,
                    "dynamic_capacity": dynamic_capacity,
                    "turnover": dynamic_capacity / effective_static_capacity,
                }
            )

    scenario_metrics = {
        scenario: _aggregate_scenario_metrics(
            scenario=scenario,
            warehouse_metrics=warehouse_metrics,
            tolerance=config.tolerance,
        )
        for scenario in scenarios
    }
    expected_metrics = _expected_scenario_metrics(
        scenario_metrics,
        probabilities,
    )

    return StorageMetricsResult(
        warehouse_metrics=warehouse_metrics,
        scenario_metrics=scenario_metrics,
        expected_metrics=expected_metrics,
        metadata={
            "source_equations": ["1.63", "1.64", "1.65", "1.66", "1.67"],
            "period_count": len(data.periods),
            "annualization_months": config.annualization_months,
            "annualization_factor": annualization_factor,
            "dynamic_capacity_formula": (
                "(12 / |T|) * (total_outbound + terminal_inventory)"
            ),
            "outbound_definition": (
                "warehouse-to-customer plus warehouse-to-warehouse at source"
            ),
            "effective_static_capacity_formula": (
                "existing_static_or_opened_candidate_capacity + expansion_capacity"
            ),
            "bulkification_capacity_in_denominator": False,
            "turnover_formula": "dynamic_capacity / effective_static_capacity",
            "excluded_nonpositive_capacity_warehouses": excluded_warehouses,
        },
    )


def attach_storage_metrics(
    data: ModelData,
    result: OptimizationResult,
    config: StorageMetricsConfig | None = None,
) -> StorageMetricsResult:
    """Calculate storage metrics and attach their serializable form to a result."""

    storage_metrics = calculate_storage_metrics(data, result, config)
    result.metrics["storage"] = storage_metrics.to_dict()
    result.metrics["DynCap"] = storage_metrics.expected_metrics[
        "dynamic_capacity"
    ]
    result.metrics["Turnover"] = storage_metrics.expected_metrics["turnover"]
    return storage_metrics


def _scenario_structure(
    data: ModelData,
    result: OptimizationResult,
    config: StorageMetricsConfig,
) -> tuple[list[str], dict[str, float], bool]:
    stochastic = result.model_mode == "sto" or bool(data.scenarios)
    if stochastic:
        scenarios = list(data.scenarios)
        if not scenarios:
            raise ValueError("Stochastic metrics require scenarios in ModelData.")
        probabilities = {
            scenario: float(data.scenario_prob[scenario])
            for scenario in scenarios
        }
        return scenarios, probabilities, True

    return (
        [config.deterministic_scenario_id],
        {config.deterministic_scenario_id: 1.0},
        False,
    )


def _record_scenario(
    record: dict[str, Any],
    config: StorageMetricsConfig,
    stochastic: bool,
) -> str:
    if stochastic and "scenario" not in record:
        raise ValueError("Stochastic flow and inventory records require a scenario.")
    return str(record.get("scenario", config.deterministic_scenario_id))


def _zero_warehouse_scenario_map(
    data: ModelData,
    scenarios: list[str],
) -> dict[tuple[str, str], float]:
    return {
        (scenario, warehouse): 0.0
        for scenario in scenarios
        for warehouse in data.warehouses
    }


def _thesis_effective_static_capacity(
    *,
    data: ModelData,
    warehouse: str,
    decision: dict[str, Any],
) -> float:
    expansion_capacity = float(decision.get("expansion_capacity", 0.0))
    if warehouse in data.existing_warehouses:
        return float(data.static_capacity.get(warehouse, 0.0)) + expansion_capacity
    if warehouse in data.candidate_warehouses:
        return float(decision.get("candidate_capacity", 0.0)) + expansion_capacity
    raise ValueError(
        f"Warehouse {warehouse!r} is neither existing nor candidate."
    )


def _aggregate_scenario_metrics(
    *,
    scenario: str,
    warehouse_metrics: list[dict[str, Any]],
    tolerance: float,
) -> dict[str, float | None]:
    records = [
        record for record in warehouse_metrics if record["scenario"] == scenario
    ]
    effective_static_capacity = sum(
        float(record["effective_static_capacity"]) for record in records
    )
    dynamic_capacity = sum(float(record["dynamic_capacity"]) for record in records)

    return {
        "effective_static_capacity": effective_static_capacity,
        "total_outbound": sum(float(record["total_outbound"]) for record in records),
        "terminal_inventory": sum(
            float(record["terminal_inventory"]) for record in records
        ),
        "dynamic_capacity": dynamic_capacity,
        "turnover": (
            dynamic_capacity / effective_static_capacity
            if effective_static_capacity > tolerance
            else None
        ),
    }


def _expected_scenario_metrics(
    scenario_metrics: dict[str, dict[str, float | None]],
    probabilities: dict[str, float],
) -> dict[str, float | None]:
    metric_names = next(iter(scenario_metrics.values())).keys()
    expected: dict[str, float | None] = {}
    for metric_name in metric_names:
        values = {
            scenario: metrics[metric_name]
            for scenario, metrics in scenario_metrics.items()
        }
        if any(value is None for value in values.values()):
            expected[metric_name] = None
            continue
        expected[metric_name] = sum(
            probabilities[scenario] * float(value)
            for scenario, value in values.items()
        )
    return expected

