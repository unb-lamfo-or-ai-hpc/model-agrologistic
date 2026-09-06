from types import SimpleNamespace

import pytest

from src.logic.model_config import ModelConfig
from src.logic.model_config import SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import solve_model
from src.logic.optimization_gurobipy import (
    _effective_reception_capacity_expr,
    _effective_shipping_capacity_expr,
    _effective_static_capacity_expr,
)
from tests.test_gurobipy_transshipment import require_gurobi_available


def capacity_data():
    return SimpleNamespace(
        static_capacity={"W1": 100.0, "C1": 0.0},
        reception_capacity={"W1": 10.0, "C1": 0.0},
        shipping_capacity={"W1": 12.0, "C1": 0.0},
        candidate_warehouses=["C1"],
    )


def test_period_equivalent_policy_preserves_existing_mvp_semantics():
    data = capacity_data()
    config = ModelConfig(days_per_period=30.0)
    candidate = {"C1": 50.0}
    expansion = {"W1": 20.0}
    bulkification = {"W1": 5.0}

    assert _effective_static_capacity_expr(
        data, config, candidate, expansion, bulkification, "W1"
    ) == pytest.approx(125.0)
    assert _effective_reception_capacity_expr(
        data, config, candidate, expansion, bulkification, "W1", "t1"
    ) == pytest.approx(300.0)
    assert _effective_shipping_capacity_expr(
        data, config, candidate, expansion, bulkification, "C1", "t1"
    ) == pytest.approx(50.0)


def test_daily_factor_policy_matches_historical_capacity_coupling():
    data = capacity_data()
    config = ModelConfig(
        capacity_coupling_policy="daily_factors",
        days_per_period=30.0,
        candidate_reception_daily_factor=0.20,
        candidate_shipping_daily_factor=0.20,
        expansion_reception_daily_factor=0.20,
        expansion_shipping_daily_factor=0.20,
        bulkification_reception_daily_factor=1.0,
        bulkification_shipping_daily_factor=1.0,
    )
    candidate = {"C1": 50.0}
    expansion = {"W1": 20.0}
    bulkification = {"W1": 5.0}

    assert _effective_static_capacity_expr(
        data, config, candidate, expansion, bulkification, "W1"
    ) == pytest.approx(120.0)
    assert _effective_reception_capacity_expr(
        data, config, candidate, expansion, bulkification, "W1", "t1"
    ) == pytest.approx(570.0)
    assert _effective_shipping_capacity_expr(
        data, config, candidate, expansion, bulkification, "W1", "t1"
    ) == pytest.approx(630.0)
    assert _effective_reception_capacity_expr(
        data, config, candidate, expansion, bulkification, "C1", "t1"
    ) == pytest.approx(300.0)
    assert _effective_shipping_capacity_expr(
        data, config, candidate, expansion, bulkification, "C1", "t1"
    ) == pytest.approx(300.0)


def test_capacity_coupling_policy_and_factors_are_validated():
    with pytest.raises(ValueError, match="capacity_coupling_policy"):
        ModelConfig(capacity_coupling_policy="unsupported")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="must be non-negative"):
        ModelConfig(expansion_reception_daily_factor=-0.01)


def candidate_throughput_data() -> ModelData:
    return ModelData(
        origins=["O1"],
        warehouses=["W1"],
        existing_warehouses=[],
        candidate_warehouses=["W1"],
        bulk_eligible_warehouses=[],
        customers=["C1"],
        domestic_customers=["C1"],
        export_customers=[],
        products=["soy"],
        periods=["t1"],
        routes_od={("O1", "W1", "soy")},
        routes_dc={("W1", "C1", "soy")},
        supply={("O1", "soy", "t1"): 60.0},
        demand_dom={("C1", "soy", "t1"): 60.0},
        scenarios=["base"],
        scenario_prob={"base": 1.0},
        supply_s={("base", "O1", "soy", "t1"): 60.0},
        demand_dom_s={("base", "C1", "soy", "t1"): 60.0},
        dist_od={("O1", "W1"): 1.0},
        dist_dc={("W1", "C1"): 1.0},
        freight_origin={"O1": 1.0},
        freight_dest={"C1": 1.0},
        freight_warehouse={"W1": 1.0},
        transshipment_cost={"W1": 0.0},
        storage_tariff={("W1", "soy"): 1.0},
        static_capacity={"W1": 0.0},
        reception_capacity={"W1": 0.0},
        shipping_capacity={"W1": 0.0},
        max_candidate_capacity={"W1": 10.0},
        opening_fixed_cost={"W1": 0.0},
        candidate_capacity_cost={"W1": 1.0},
        unmet_demand_penalty={("C1", "soy"): 1_000_000.0},
        emergency_static_capacity_penalty={"W1": 1_000_000.0},
        emergency_reception_capacity_penalty={"W1": 1_000_000.0},
    )


@pytest.mark.parametrize("mode", ["det", "sto"])
def test_daily_candidate_factor_is_applied_by_both_gurobi_formulations(mode):
    require_gurobi_available()

    result = solve_model(
        data=candidate_throughput_data(),
        model_config=ModelConfig(
            mode=mode,
            capacity_coupling_policy="daily_factors",
            days_per_period=30.0,
            allow_capacity_expansion=False,
            allow_bulkification=False,
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

    decision = result.warehouse_decisions[0]
    assert result.status == "optimal"
    assert decision["open"] == pytest.approx(1.0)
    assert decision["candidate_capacity"] == pytest.approx(10.0)
    assert sum(record["value"] for record in result.unmet_demand) == pytest.approx(0.0)
    assert sum(record["value"] for record in result.emergency_capacity) == pytest.approx(
        0.0
    )
    assert result.metadata["capacity_coupling_policy"] == "daily_factors"
