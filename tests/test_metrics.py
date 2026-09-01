import pytest

from src.logic.metrics import (
    StorageMetricsConfig,
    attach_storage_metrics,
    calculate_storage_metrics,
)
from src.logic.model_data import ModelData
from src.logic.optimization import OptimizationResult


def metrics_data(*, stochastic: bool = False) -> ModelData:
    scenarios = ["baixo", "alto"] if stochastic else []
    probabilities = {"baixo": 0.5, "alto": 0.5} if stochastic else {}
    return ModelData(
        origins=["O1"],
        warehouses=["W1"],
        existing_warehouses=["W1"],
        candidate_warehouses=[],
        bulk_eligible_warehouses=[],
        customers=["C1"],
        domestic_customers=["C1"],
        export_customers=[],
        products=["soy"],
        periods=["t1", "t2"],
        scenarios=scenarios,
        scenario_prob=probabilities,
        static_capacity={"W1": 100.0},
    )


def warehouse_decision(
    warehouse: str = "W1",
    *,
    candidate: bool = False,
    candidate_capacity: float = 0.0,
    expansion_capacity: float = 0.0,
    bulk_capacity: float = 0.0,
) -> dict:
    static_capacity = 0.0 if candidate else 100.0
    return {
        "warehouse": warehouse,
        "is_existing": not candidate,
        "is_candidate": candidate,
        "open": 1.0 if (not candidate or candidate_capacity > 0.0) else 0.0,
        "candidate_capacity": candidate_capacity,
        "expand": float(expansion_capacity > 0.0),
        "expansion_capacity": expansion_capacity,
        "bulkify": float(bulk_capacity > 0.0),
        "bulk_capacity": bulk_capacity,
        "static_capacity": static_capacity,
        "effective_static_capacity": (
            static_capacity
            + candidate_capacity
            + expansion_capacity
            + bulk_capacity
        ),
    }


def deterministic_result() -> OptimizationResult:
    return OptimizationResult(
        status="optimal",
        objective_value=0.0,
        solver_backend="gurobipy",
        solver_name="gurobi",
        model_mode="det",
        warehouse_decisions=[warehouse_decision()],
        flows=[
            {
                "route_type": "OD",
                "warehouse": "W1",
                "period": "t1",
                "value": 100.0,
            },
            {
                "route_type": "DC",
                "warehouse": "W1",
                "period": "t1",
                "value": 50.0,
            },
            {
                "route_type": "DC",
                "warehouse": "W1",
                "period": "t2",
                "value": 30.0,
            },
        ],
        inventories=[
            {
                "warehouse": "W1",
                "product": "soy",
                "period": "t1",
                "value": 50.0,
            },
            {
                "warehouse": "W1",
                "product": "soy",
                "period": "t2",
                "value": 20.0,
            },
        ],
    )


def test_deterministic_metrics_follow_equations_1_63_to_1_65():
    metrics = calculate_storage_metrics(metrics_data(), deterministic_result())
    warehouse = metrics.warehouse_metrics[0]

    assert warehouse["total_outbound"] == pytest.approx(80.0)
    assert warehouse["terminal_inventory"] == pytest.approx(20.0)
    assert warehouse["annualization_factor"] == pytest.approx(6.0)
    assert warehouse["dynamic_capacity"] == pytest.approx(600.0)
    assert warehouse["effective_static_capacity"] == pytest.approx(100.0)
    assert warehouse["turnover"] == pytest.approx(6.0)
    assert metrics.metadata["source_equations"] == [
        "1.63",
        "1.64",
        "1.65",
        "1.66",
        "1.67",
    ]


def test_transshipment_is_outbound_only_at_its_source():
    data = metrics_data()
    data.warehouses = ["W1", "W2"]
    data.existing_warehouses = ["W1", "W2"]
    data.static_capacity["W2"] = 100.0
    result = OptimizationResult(
        status="optimal",
        model_mode="det",
        warehouse_decisions=[
            warehouse_decision("W1"),
            warehouse_decision("W2"),
        ],
        flows=[
            {
                "route_type": "DD",
                "warehouse_from": "W1",
                "warehouse_to": "W2",
                "value": 60.0,
            },
            {"route_type": "DC", "warehouse": "W2", "value": 60.0},
        ],
    )

    metrics = calculate_storage_metrics(data, result)
    by_warehouse = {
        record["warehouse"]: record for record in metrics.warehouse_metrics
    }

    assert by_warehouse["W1"]["total_outbound"] == pytest.approx(60.0)
    assert by_warehouse["W2"]["total_outbound"] == pytest.approx(60.0)
    assert by_warehouse["W1"]["dynamic_capacity"] == pytest.approx(360.0)
    assert by_warehouse["W2"]["dynamic_capacity"] == pytest.approx(360.0)


def test_terminal_inventory_sums_products_only_in_last_period():
    data = metrics_data()
    data.products = ["soy", "corn"]
    result = deterministic_result()
    result.inventories.extend(
        [
            {
                "warehouse": "W1",
                "product": "corn",
                "period": "t1",
                "value": 200.0,
            },
            {
                "warehouse": "W1",
                "product": "corn",
                "period": "t2",
                "value": 10.0,
            },
        ]
    )

    metrics = calculate_storage_metrics(data, result)

    assert metrics.warehouse_metrics[0]["terminal_inventory"] == pytest.approx(
        30.0
    )
    assert metrics.warehouse_metrics[0]["dynamic_capacity"] == pytest.approx(
        660.0
    )


def test_effective_capacity_uses_base_or_candidate_plus_expansion():
    data = metrics_data()
    data.warehouses = ["W1", "W2"]
    data.candidate_warehouses = ["W2"]
    result = OptimizationResult(
        status="optimal",
        model_mode="det",
        warehouse_decisions=[
            warehouse_decision("W1", expansion_capacity=20.0),
            warehouse_decision(
                "W2",
                candidate=True,
                candidate_capacity=80.0,
                expansion_capacity=10.0,
            ),
        ],
    )

    metrics = calculate_storage_metrics(data, result)
    by_warehouse = {
        record["warehouse"]: record for record in metrics.warehouse_metrics
    }

    assert by_warehouse["W1"]["effective_static_capacity"] == pytest.approx(
        120.0
    )
    assert by_warehouse["W2"]["effective_static_capacity"] == pytest.approx(
        90.0
    )


def test_bulkification_is_excluded_from_equation_1_64_denominator():
    result = deterministic_result()
    result.warehouse_decisions = [warehouse_decision(bulk_capacity=50.0)]

    metrics = calculate_storage_metrics(metrics_data(), result)

    assert metrics.warehouse_metrics[0][
        "effective_static_capacity"
    ] == pytest.approx(100.0)
    assert metrics.warehouse_metrics[0]["turnover"] == pytest.approx(6.0)
    assert metrics.metadata["bulkification_capacity_in_denominator"] is False


def test_closed_candidate_warehouse_is_excluded():
    data = metrics_data()
    data.warehouses = ["W1", "W2"]
    data.candidate_warehouses = ["W2"]
    result = deterministic_result()
    result.warehouse_decisions.append(warehouse_decision("W2", candidate=True))

    metrics = calculate_storage_metrics(data, result)

    assert [record["warehouse"] for record in metrics.warehouse_metrics] == [
        "W1"
    ]
    assert metrics.metadata[
        "excluded_nonpositive_capacity_warehouses"
    ] == ["W2"]


def test_stochastic_metrics_follow_equations_1_66_and_1_67():
    data = metrics_data(stochastic=True)
    result = OptimizationResult(
        status="optimal",
        model_mode="sto",
        warehouse_decisions=[warehouse_decision()],
        flows=[
            {
                "scenario": "baixo",
                "route_type": "DC",
                "warehouse": "W1",
                "value": 20.0,
            },
            {
                "scenario": "alto",
                "route_type": "DC",
                "warehouse": "W1",
                "value": 80.0,
            },
        ],
        inventories=[
            {
                "scenario": "baixo",
                "warehouse": "W1",
                "product": "soy",
                "period": "t2",
                "value": 10.0,
            },
            {
                "scenario": "alto",
                "warehouse": "W1",
                "product": "soy",
                "period": "t2",
                "value": 20.0,
            },
        ],
    )

    metrics = calculate_storage_metrics(data, result)

    assert metrics.scenario_metrics["baixo"][
        "dynamic_capacity"
    ] == pytest.approx(180.0)
    assert metrics.scenario_metrics["baixo"]["turnover"] == pytest.approx(1.8)
    assert metrics.scenario_metrics["alto"][
        "dynamic_capacity"
    ] == pytest.approx(600.0)
    assert metrics.scenario_metrics["alto"]["turnover"] == pytest.approx(6.0)
    assert metrics.expected_metrics["dynamic_capacity"] == pytest.approx(390.0)
    assert metrics.expected_metrics["turnover"] == pytest.approx(3.9)


def test_attach_storage_metrics_adds_compact_kpis_to_result():
    result = deterministic_result()

    metrics = attach_storage_metrics(metrics_data(), result)

    assert result.metrics["DynCap"] == pytest.approx(600.0)
    assert result.metrics["Turnover"] == pytest.approx(6.0)
    assert result.metrics["storage"] == metrics.to_dict()


def test_metrics_require_periods_and_a_usable_solution():
    data = metrics_data()
    data.periods = []
    with pytest.raises(ValueError, match="at least one period"):
        calculate_storage_metrics(data, deterministic_result())

    with pytest.raises(ValueError, match="usable optimization solution"):
        calculate_storage_metrics(
            metrics_data(),
            OptimizationResult(status="infeasible"),
        )


def test_stochastic_records_must_identify_their_scenario():
    result = deterministic_result()
    result.model_mode = "sto"

    with pytest.raises(ValueError, match="require a scenario"):
        calculate_storage_metrics(metrics_data(stochastic=True), result)


def test_config_rejects_invalid_values():
    with pytest.raises(ValueError, match="annualization_months"):
        StorageMetricsConfig(annualization_months=0.0)
    with pytest.raises(ValueError, match="deterministic_scenario_id"):
        StorageMetricsConfig(deterministic_scenario_id="")
    with pytest.raises(ValueError, match="tolerance"):
        StorageMetricsConfig(tolerance=-1.0)

