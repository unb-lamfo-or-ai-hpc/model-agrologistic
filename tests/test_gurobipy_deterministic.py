import pytest

from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import configure_gurobi_wls_license, solve_model


def require_gurobi_available() -> None:
    gp = pytest.importorskip("gurobipy")

    configure_gurobi_wls_license(SolverConfig())

    try:
        env = gp.Env(empty=True)
        env.setParam("OutputFlag", 0)
        env.start()
        env.dispose()
    except gp.GurobiError as exc:
        pytest.skip(f"Gurobi is installed, but no usable license is available: {exc}")


def tiny_data(
    *,
    supply: float = 100.0,
    demand: float = 100.0,
    existing_static_capacity: float = 200.0,
    existing_reception_capacity: float = 200.0,
    existing_shipping_capacity: float = 200.0,
    candidate_opening_cost: float = 1_000_000.0,
    candidate_capacity_cost: float = 1_000.0,
) -> ModelData:
    return ModelData(
        origins=["O1"],
        warehouses=["W1", "W2"],
        existing_warehouses=["W1"],
        candidate_warehouses=["W2"],
        bulk_eligible_warehouses=[],
        customers=["C1"],
        domestic_customers=["C1"],
        export_customers=[],
        products=["soy"],
        periods=["t1"],
        routes_od={
            ("O1", "W1", "soy"),
            ("O1", "W2", "soy"),
        },
        routes_dc={
            ("W1", "C1", "soy"),
            ("W2", "C1", "soy"),
        },
        supply={
            ("O1", "soy", "t1"): supply,
        },
        demand_dom={
            ("C1", "soy", "t1"): demand,
        },
        dist_od={
            ("O1", "W1"): 100.0,
            ("O1", "W2"): 50.0,
        },
        dist_dc={
            ("W1", "C1"): 100.0,
            ("W2", "C1"): 50.0,
        },
        freight_origin={
            "O1": 1.0,
        },
        freight_dest={
            "C1": 1.0,
        },
        storage_tariff={
            ("W1", "soy"): 1.0,
            ("W2", "soy"): 1.0,
        },
        static_capacity={
            "W1": existing_static_capacity,
        },
        reception_capacity={
            "W1": existing_reception_capacity,
        },
        shipping_capacity={
            "W1": existing_shipping_capacity,
        },
        max_candidate_capacity={
            "W2": 300.0,
        },
        opening_fixed_cost={
            "W2": candidate_opening_cost,
        },
        candidate_capacity_cost={
            "W2": candidate_capacity_cost,
        },
        unmet_demand_penalty={
            ("C1", "soy"): 1_000_000.0,
        },
        emergency_static_capacity_penalty={
            "W1": 1_000_000.0,
            "W2": 1_000_000.0,
        },
        emergency_reception_capacity_penalty={
            "W1": 1_000_000.0,
            "W2": 1_000_000.0,
        },
    )


def solve_tiny(data: ModelData, model_config: ModelConfig | None = None):
    if model_config is None:
        model_config = ModelConfig(
            mode="det",
            candidate_capacity_mode="scalable",
            capacity_coupling_policy="period_equivalent",
            days_per_period=1.0,
        )

    return solve_model(
        data=data,
        model_config=model_config,
        solver_config=SolverConfig(
            backend="gurobipy",
            solver_name="gurobi",
            mip_gap=0.0,
            time_limit=60,
            threads=1,
            tee=False,
        ),
    )


def total_flow(result, route_type: str) -> float:
    return sum(
        record["value"]
        for record in result.flows
        if record["route_type"] == route_type
    )


def warehouse_decision(result, warehouse: str):
    return next(
        record
        for record in result.warehouse_decisions
        if record["warehouse"] == warehouse
    )


def test_gurobipy_solves_tiny_deterministic_instance():
    require_gurobi_available()

    result = solve_tiny(tiny_data())

    assert result.status == "optimal"
    assert result.objective_value is not None
    assert result.solver_backend == "gurobipy"
    assert result.model_mode == "det"

    assert total_flow(result, "OD") == pytest.approx(100.0)
    assert total_flow(result, "DC") == pytest.approx(100.0)
    assert result.metrics["total_unmet_demand"] == pytest.approx(0.0)
    assert result.metrics["total_emergency_capacity"] == pytest.approx(0.0)


def test_zero_supply_and_zero_demand_do_not_create_artificial_flow():
    require_gurobi_available()

    data = tiny_data(supply=0.0, demand=0.0)

    result = solve_tiny(data)

    assert result.status == "optimal"
    assert total_flow(result, "OD") == pytest.approx(0.0)
    assert total_flow(result, "DC") == pytest.approx(0.0)
    assert result.metrics["total_unmet_demand"] == pytest.approx(0.0)


def test_zero_domestic_demand_is_not_artificial_sink():
    require_gurobi_available()

    data = tiny_data(supply=25.0, demand=0.0)

    result = solve_tiny(data)

    assert result.status == "optimal"
    assert total_flow(result, "OD") == pytest.approx(25.0)
    assert total_flow(result, "DC") == pytest.approx(0.0)

    total_inventory = sum(record["value"] for record in result.inventories)
    assert total_inventory == pytest.approx(25.0)


def test_closed_candidate_cannot_use_emergency_capacity():
    require_gurobi_available()

    data = tiny_data(
        supply=50.0,
        demand=50.0,
        existing_static_capacity=200.0,
        existing_reception_capacity=200.0,
        existing_shipping_capacity=200.0,
        candidate_opening_cost=1_000_000_000.0,
        candidate_capacity_cost=1_000_000.0,
    )

    result = solve_tiny(data)

    assert result.status == "optimal"

    w2 = warehouse_decision(result, "W2")
    assert w2["open"] == pytest.approx(0.0)
    assert w2["candidate_capacity"] == pytest.approx(0.0)

    candidate_emergency = [
        record for record in result.emergency_capacity
        if record["warehouse"] == "W2"
    ]

    assert candidate_emergency == []


def test_candidate_opens_when_existing_shipping_capacity_is_insufficient():
    require_gurobi_available()

    data = tiny_data(
        supply=100.0,
        demand=100.0,
        existing_static_capacity=200.0,
        existing_reception_capacity=20.0,
        existing_shipping_capacity=20.0,
        candidate_opening_cost=10.0,
        candidate_capacity_cost=1.0,
    )

    result = solve_tiny(data)

    assert result.status == "optimal"
    assert result.metrics["total_unmet_demand"] == pytest.approx(0.0)

    w2 = warehouse_decision(result, "W2")
    assert w2["open"] == pytest.approx(1.0)
    assert w2["candidate_capacity"] > 0.0

    flow_through_candidate = sum(
        record["value"]
        for record in result.flows
        if record["warehouse"] == "W2"
    )

    assert flow_through_candidate > 0.0