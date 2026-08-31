import pytest

from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import solve_model
from tests.test_gurobipy_transshipment import require_gurobi_available


def two_scenario_data() -> ModelData:
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
        periods=["t1"],
        routes_od={("O1", "W1", "soy")},
        routes_dc={("W1", "C1", "soy")},
        supply={("O1", "soy", "t1"): 40.0},
        demand_dom={("C1", "soy", "t1"): 0.0},
        scenarios=["base", "otimista"],
        scenario_prob={"base": 0.25, "otimista": 0.75},
        supply_s={
            ("base", "O1", "soy", "t1"): 40.0,
            ("otimista", "O1", "soy", "t1"): 100.0,
        },
        demand_dom_s={
            ("base", "C1", "soy", "t1"): 0.0,
            ("otimista", "C1", "soy", "t1"): 0.0,
        },
        dist_od={("O1", "W1"): 1.0},
        dist_dc={("W1", "C1"): 1.0},
        freight_origin={"O1": 1.0},
        freight_dest={"C1": 1.0},
        freight_warehouse={"W1": 1.0},
        transshipment_cost={"W1": 0.0},
        storage_tariff={("W1", "soy"): 1.0},
        static_capacity={"W1": 40.0},
        reception_capacity={"W1": 500.0},
        shipping_capacity={"W1": 500.0},
        max_expand_capacity={"W1": 100.0},
        expand_fixed_cost={"W1": 10.0},
        expand_variable_cost={"W1": 2.0},
        unmet_demand_penalty={("C1", "soy"): 1_000_000.0},
        emergency_static_capacity_penalty={"W1": 1_000_000.0},
        emergency_reception_capacity_penalty={"W1": 1_000_000.0},
    )


def solve_two_scenario_model():
    return solve_model(
        data=two_scenario_data(),
        model_config=ModelConfig(
            mode="sto",
            allow_capacity_expansion=True,
            allow_bulkification=False,
            days_per_period=1.0,
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


def test_extensive_form_uses_one_shared_first_stage_expansion():
    require_gurobi_available()

    result = solve_two_scenario_model()
    decision = result.warehouse_decisions[0]

    assert result.status == "optimal"
    assert result.model_mode == "sto"
    assert decision["expand"] == pytest.approx(1.0)
    assert decision["expansion_capacity"] == pytest.approx(60.0)
    assert decision["effective_static_capacity"] == pytest.approx(100.0)
    assert "scenario" not in decision
    assert result.metadata["formulation"] == "two_stage_extensive_form"


def test_extensive_form_separates_recourse_records_by_scenario():
    require_gurobi_available()

    result = solve_two_scenario_model()
    inventories = {
        record["scenario"]: record["value"] for record in result.inventories
    }

    assert inventories == pytest.approx({"base": 40.0, "otimista": 100.0})
    assert {record["scenario"] for record in result.flows} == {
        "base",
        "otimista",
    }
    assert all("scenario" in record for record in result.flows)


def test_extensive_form_weights_operating_costs_by_probability():
    require_gurobi_available()

    result = solve_two_scenario_model()

    # Investment: 10 fixed + 60 * 2 variable.
    assert result.metrics["investment_cost"] == pytest.approx(130.0)
    # Per scenario: OD transport + storage = 2 * supply.
    assert result.metrics["scenario_metrics"]["base"][
        "operating_cost"
    ] == pytest.approx(80.0)
    assert result.metrics["scenario_metrics"]["otimista"][
        "operating_cost"
    ] == pytest.approx(200.0)
    assert result.metrics["expected_operating_cost"] == pytest.approx(170.0)
    assert result.objective_value == pytest.approx(300.0)


def test_extensive_form_reports_scenario_probabilities():
    require_gurobi_available()

    result = solve_two_scenario_model()

    assert result.metadata["scenario_probabilities"] == {
        "base": 0.25,
        "otimista": 0.75,
    }
    assert result.metrics["scenario_metrics"]["base"][
        "probability"
    ] == pytest.approx(0.25)
