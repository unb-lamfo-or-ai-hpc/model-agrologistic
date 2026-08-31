import pytest

from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import solve_model
from tests.test_gurobipy_transshipment import require_gurobi_available


def base_expansion_data(
    *,
    supply: float = 100.0,
    static_capacity: float = 40.0,
    max_expand_capacity: float = 100.0,
    expand_fixed_cost: float = 10.0,
    expand_variable_cost: float = 2.0,
    emergency_static_penalty: float = 1_000_000.0,
    periods=None,
) -> ModelData:
    if periods is None:
        periods = ["t1"]

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
        periods=periods,
        routes_od={("O1", "W1", "soy")},
        routes_dc={("W1", "C1", "soy")},
        routes_dd=set(),
        routes_oc=set(),
        supply={("O1", "soy", periods[0]): supply},
        demand_dom={("C1", "soy", period): 0.0 for period in periods},
        demand_exp={},
        dist_od={("O1", "W1"): 1.0},
        dist_dc={("W1", "C1"): 1.0},
        dist_dd={},
        dist_oc={},
        freight_origin={"O1": 1.0},
        freight_dest={"C1": 1.0},
        freight_warehouse={"W1": 1.0},
        transshipment_cost={"W1": 0.0},
        storage_tariff={("W1", "soy"): 1.0},
        static_capacity={"W1": static_capacity},
        reception_capacity={"W1": 500.0},
        shipping_capacity={"W1": 500.0},
        max_expand_capacity={"W1": max_expand_capacity},
        expand_fixed_cost={"W1": expand_fixed_cost},
        expand_variable_cost={"W1": expand_variable_cost},
        unmet_demand_penalty={("C1", "soy"): 1_000_000.0},
        emergency_static_capacity_penalty={
            "W1": emergency_static_penalty,
        },
        emergency_reception_capacity_penalty={"W1": 1_000_000.0},
    )


def solve_expansion_data(data: ModelData, *, enabled: bool = True):
    return solve_model(
        data=data,
        model_config=ModelConfig(
            mode="det",
            allow_capacity_expansion=enabled,
            allow_bulkification=False,
            days_per_period=1.0,
            allow_unmet_domestic_demand=True,
            allow_emergency_static_capacity=True,
            allow_emergency_reception_capacity=True,
        ),
        solver_config=SolverConfig(
            backend="gurobipy",
            solver_name="gurobi",
            mip_gap=0.0,
            time_limit=60,
            threads=1,
            tee=False,
        ),
    )


def warehouse_decision(result, warehouse: str):
    return next(
        decision
        for decision in result.warehouse_decisions
        if decision["warehouse"] == warehouse
    )


def emergency_static_capacity(result, warehouse: str) -> float:
    return sum(
        record["value"]
        for record in result.emergency_capacity
        if record["warehouse"] == warehouse
        and record["capacity_type"] == "static"
    )


def inventory_by_period(result, warehouse: str) -> dict[str, float]:
    return {
        record["period"]: record["value"]
        for record in result.inventories
        if record["warehouse"] == warehouse
    }


def test_expansion_is_used_when_static_capacity_is_insufficient():
    require_gurobi_available()

    result = solve_expansion_data(base_expansion_data())
    decision = warehouse_decision(result, "W1")

    assert result.status == "optimal"
    assert decision["expand"] == pytest.approx(1.0)
    assert decision["expansion_capacity"] == pytest.approx(60.0)
    assert decision["effective_static_capacity"] == pytest.approx(100.0)
    assert result.cost_breakdown["expansion_fixed"] == pytest.approx(10.0)
    assert result.cost_breakdown["expansion_variable"] == pytest.approx(120.0)
    assert emergency_static_capacity(result, "W1") == pytest.approx(0.0)


def test_expansion_respects_the_installed_capacity_limit():
    require_gurobi_available()

    result = solve_expansion_data(
        base_expansion_data(max_expand_capacity=30.0)
    )
    decision = warehouse_decision(result, "W1")

    assert result.status == "optimal"
    assert decision["expansion_capacity"] == pytest.approx(30.0)
    assert decision["effective_static_capacity"] == pytest.approx(70.0)
    assert emergency_static_capacity(result, "W1") == pytest.approx(30.0)


def test_disabled_expansion_preserves_the_previous_capacity_behavior():
    require_gurobi_available()

    result = solve_expansion_data(base_expansion_data(), enabled=False)
    decision = warehouse_decision(result, "W1")

    assert result.status == "optimal"
    assert decision["expand"] == pytest.approx(0.0)
    assert decision["expansion_capacity"] == pytest.approx(0.0)
    assert decision["effective_static_capacity"] == pytest.approx(40.0)
    assert result.cost_breakdown["expansion_fixed"] == pytest.approx(0.0)
    assert result.cost_breakdown["expansion_variable"] == pytest.approx(0.0)
    assert emergency_static_capacity(result, "W1") == pytest.approx(60.0)


def test_expansion_is_not_opened_when_existing_capacity_is_sufficient():
    require_gurobi_available()

    result = solve_expansion_data(
        base_expansion_data(supply=40.0, static_capacity=40.0)
    )
    decision = warehouse_decision(result, "W1")

    assert result.status == "optimal"
    assert decision["expand"] == pytest.approx(0.0)
    assert decision["expansion_capacity"] == pytest.approx(0.0)
    assert emergency_static_capacity(result, "W1") == pytest.approx(0.0)


def test_one_expansion_decision_applies_to_every_period():
    require_gurobi_available()

    result = solve_expansion_data(
        base_expansion_data(periods=["t1", "t2"])
    )
    decision = warehouse_decision(result, "W1")

    assert result.status == "optimal"
    assert decision["expansion_capacity"] == pytest.approx(60.0)
    assert inventory_by_period(result, "W1") == pytest.approx(
        {"t1": 100.0, "t2": 100.0}
    )
    assert result.cost_breakdown["expansion_fixed"] == pytest.approx(10.0)
    assert result.cost_breakdown["expansion_variable"] == pytest.approx(120.0)

